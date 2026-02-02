# Golf Assistant Prototype

This repository contains a full golf-swing analysis pipeline (object + pose detection, SwingNet event segmentation, rule-based faults, optional LLM feedback, and optional TTS output) with a FastAPI web UI.

## Quick start

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

### 4) Run the web app

- `uvicorn app.main:app --reload`

Open http://127.0.0.1:8000 in your browser, upload a golf swing video, and wait for the annotated video + feedback.

## Project structure

- app/: FastAPI app, services, templates, static assets
- uploads/: raw uploaded videos
- outputs/: annotated videos, feedback audio, JSON outputs

## Notes

- The pipeline uses CPU-only MediaPipe and OpenCV by default. GPU support requires an NVIDIA setup.
- On Windows, keep paths short and avoid moving model files unless you update paths in app/core/config.py.

