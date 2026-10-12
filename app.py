import os
import re
import uuid
import threading
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify, send_file, abort
import yt_dlp

APP_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = APP_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
jobs = {}
jobs_lock = threading.Lock()

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "music.youtube.com", "instagram.com", "www.instagram.com"
}

def valid_media_url(raw):
    try:
        parsed = urlparse(raw.strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme in ("http", "https") and any(
            host == domain or host.endswith("." + domain)
            for domain in ALLOWED_HOSTS
        )
    except Exception:
        return False

def run_download(job_id, url, kind, quality):
    output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
    def hook(data):
        status = data.get("status")
        with jobs_lock:
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                got = data.get("downloaded_bytes") or 0
                percent = round(got * 100 / total) if total else 0
                jobs[job_id].update(status="downloading", progress=min(percent, 99),
                                    message="Downloading media…")
            elif status == "finished":
                jobs[job_id].update(progress=100, message="Preparing file…")

    opts = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "progress_hooks": [hook],
        "socket_timeout": 25,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "socket_timeout": 30,
    
    }
    if kind == "audio":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        formats = {
            "best": "bestvideo*+bestaudio/best",
            "720": "bestvideo*[height<=720]+bestaudio/best[height<=720]",
            "480": "bestvideo*[height<=480]+bestaudio/best[height<=480]",
        }
        opts["format"] = formats.get(quality, formats["best"])
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        matches = list(DOWNLOAD_DIR.glob(job_id + ".*"))
        matches = [p for p in matches if p.is_file() and p.suffix != ".part"]
        if not matches:
            raise RuntimeError("The platform did not provide a downloadable file.")
        final_file = max(matches, key=lambda p: p.stat().st_mtime)
        with jobs_lock:
            jobs[job_id].update(status="done", progress=100, message="Ready to download",
                                filename=final_file.name)
    except Exception as exc:
        msg = str(exc).strip().splitlines()[0] if str(exc).strip() else "Download failed."
        if len(msg) > 220:
            msg = msg[:217] + "..."
        with jobs_lock:
            jobs[job_id].update(status="error", message=msg)

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/download")
def create_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    kind = data.get("kind", "video")
    quality = data.get("quality", "best")
    if not valid_media_url(url):
        return jsonify(error="Paste a valid public YouTube or Instagram URL."), 400
    if kind not in ("video", "audio"):
        return jsonify(error="Choose video or audio."), 400
    job_id = uuid.uuid4().hex[:14]
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "message": "Starting…"}
    thread = threading.Thread(target=run_download, args=(job_id, url, kind, quality), daemon=True)
    thread.start()
    return jsonify(job_id=job_id)

@app.get("/api/status/<job_id>")
def download_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify(error="Job not found."), 404
        return jsonify(job)

@app.get("/file/<job_id>")
def get_file(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job or job.get("status") != "done":
            abort(404)
        filename = job.get("filename", "")
    path = (DOWNLOAD_DIR / filename).resolve()
    if path.parent != DOWNLOAD_DIR.resolve() or not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)

@app.get("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
