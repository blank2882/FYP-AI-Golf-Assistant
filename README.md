# Golf Assistant Prototype

This repository contains a full golf-swing analysis pipeline (object + pose detection, SwingNet event segmentation, rule-based faults, optional LLM feedback, and optional TTS output) with a FastAPI web UI.

## Quick start

For the virtual environment, it is imperative to use python version 3.10.19 as some of the dependencies are not suitable for newer versions. 

### 1) Create and Activate the virtual environment

Use the existing environment name:

- Windows (PowerShell):
  - `conda activate golfAssist`

### 2)  Install Pytorch, ensure that it is the CPU ONLY version!

  - `pip install torch torchvision`

### 3) Install dependencies

- `pip install -r requirements.txt`

### 4) (Optional) Install and run Ollama

If you want LLM feedback:

- Install Ollama: https://ollama.com/
- Pull a model: `ollama pull qwen2.5`

### 5) Run the web app

- `uvicorn app.main:app --reload`

Open http://127.0.0.1:8000 in your browser, upload a golf swing video, and wait for the annotated video + feedback.

## Project structure

- app/: FastAPI app, services, templates, static assets
- uploads/: raw uploaded videos
- outputs/: annotated videos, feedback audio, JSON outputs

## Notes

- The pipeline uses CPU-only MediaPipe and OpenCV by default. GPU support requires an NVIDIA setup.
- On Windows, keep paths short and avoid moving model files unless you update paths in app/core/config.py.

