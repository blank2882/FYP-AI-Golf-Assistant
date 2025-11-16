# Golf Assistant Prototype

This repository contains a golf-swing pose extraction prototype. The project uses `opencv-python` and `mediapipe` for pose estimation.


## Quick start (recommended)
1. Activate the conda virtual environment 
    . conda activate "E:\year 3\FYP\golf assistant prototype\.conda"
2. Run main.py + the video of choice



Notes
- The container uses CPU-only Mediapipe and OpenCV. GPU support requires an NVIDIA host, NVIDIA Container Toolkit, and a CUDA-enabled image — contact me if you want GPU instructions.
- On Windows, be careful with paths that contain spaces when using `-v`; wrap the host path in quotes as shown above.

Troubleshooting
- If `docker compose up` fails, ensure Docker Desktop is running and WSL2 integration is enabled.
- If you need Python 3.11 locally instead of Docker, install Python 3.11 and create a virtual environment, then run `python -m pip install -r requirements.txt`.

