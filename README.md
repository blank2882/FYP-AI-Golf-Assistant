# Golf Assistant Prototype

This repository contains a full golf-swing analysis pipeline (object + pose detection, SwingNet event segmentation, rule-based faults, optional LLM feedback, and optional TTS output) with a FastAPI web UI.

## Quick start

For the virtual environment, it is imperative to use python version 3.10.19 as some of the dependencies are not suitable for newer versions. 

### 1) Activate the virtual environment

Use the existing environment name:

- Windows (PowerShell):
  - `conda activate golfAssist`

### 2) Install dependencies

- `pip install -r requirements.txt`

### 3) (Optional) Install and run Ollama

If you want LLM feedback:

- Install Ollama: https://ollama.com/
- Pull a model: `ollama pull qwen2.5`

### 4a) Run the web app on your desktop web browser

- `uvicorn app.main:app --reload`

Open http://127.0.0.1:8000 in your browser, upload a golf swing video, and wait for the annotated video + feedback.

### 4b) Access from a mobile browser using ngrok

If your phone cannot access your PC on local network, you can expose the app with ngrok.

1. Install ngrok: https://ngrok.com/downloads/windows
2. Sign in and set your auth token (one time):
  - `ngrok config add-authtoken <YOUR_NGROK_TOKEN>`
3. Keep your app running on port 8000.
4. In a new terminal, start a tunnel:
  - `ngrok http 8000`
5. Open the generated `https://...ngrok-free.app` URL on your phone browser.

Notes:
- The ngrok URL changes each time you restart the tunnel (free plan).
- Keep the ngrok terminal running while testing from mobile.
- If using Docker, run `docker compose up --build` first, then run `ngrok http 8000`.

## Docker (Python 3.10.19)

This uses a Python 3.10.19 base image and exposes the app on port 8000.

### Build and run

- `docker compose up --build`

Then open http://<YOUR_PC_IP>:8000 on your mobile phone (same Wi‑Fi).

### Stop

- `docker compose down`

## Project structure

- app/: FastAPI app, services, templates, static assets
- uploads/: raw uploaded videos
- outputs/: annotated videos, feedback audio, JSON outputs

## Notes

- The pipeline uses CPU-only MediaPipe and OpenCV by default. GPU support requires an NVIDIA setup.
- On Windows, keep paths short and avoid moving model files unless you update paths in app/core/config.py.

