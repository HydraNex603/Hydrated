# HYDRA Media Downloader

Premium Flask web UI for preparing downloads from supported **public** YouTube and Instagram URLs.

## Requirements
- Python 3.10+
- FFmpeg installed and available on PATH (needed for MP3 conversion and some video merges)
- Internet access on the server

## Run locally

### Windows
1. Install Python 3.10+ and FFmpeg.
2. Extract this ZIP.
3. Open a terminal in the extracted folder:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   py app.py
   ```
4. Open http://127.0.0.1:5000

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000

## Deploying online
Use a Python web host that supports Flask and FFmpeg. Set the start command to `gunicorn app:app` (add `gunicorn` to requirements first), configure a persistent downloads directory, and add rate limits, a cleanup task, storage quotas, and HTTPS before public launch. Do not expose Flask's development server to the public internet.

## Important limitations
- Platform formats, URLs, and access rules change. No downloader can guarantee every link will work.
- This starter app intentionally supports only YouTube and Instagram hostnames.
- Private, age-restricted, login-required, DRM-protected, or otherwise inaccessible media may fail.
- Only download content you own or have permission to download and follow platform terms and local law.
- Public deployment needs abuse prevention, job limits, file cleanup, and storage limits before production use.
