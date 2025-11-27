# Golf Assistant Prototype

This repository contains a golf-swing pose extraction prototype. The project uses `opencv-python` and `mediapipe` for pose estimation.


## Quick start (recommended)

### Install the local LLM
1. Install ollama (https://ollama.com/)

2. Run '''ollama pull phi3''' in terminal

### Create the Conda virtual environment
1. Create a conda virtual environment
    - Ensure that the python version is either 3.10 or 3.11 to make it compatible for mediapipe pose

2. Activate the conda virtual environment 
    - conda activate "E:\year 3\FYP\prototype git\FYP-AI-Golf-Assistant\.conda"

3. install the dependencies in requirements.txt with pip
    - pip install -r requirements.txt

4. install the pytorch dependencies with conda **depending on the hardware**
    - conda install -c pytorch pytorch torchvision torchaudio cpuonly -y (for CPU only)
    OR
    - conda install -c pytorch -c nvidia pytorch torchvision torchaudio pytorch-cuda=11.8 -y (for GPU)

5. Install coqui TTS 
    - pip install TTS

6. To test that the TTS is working
    - tts --text "Hello golfer!" --model_name tts_models/en/ljspeech/tacotron2-DDC --out_path [audio file path] 

7. Run main.py + the video of choice

 
Notes
- The container uses CPU-only Mediapipe and OpenCV. GPU support requires an NVIDIA host, NVIDIA Container Toolkit, and a CUDA-enabled image — contact me if you want GPU instructions.
- On Windows, be careful with paths that contain spaces when using `-v`; wrap the host path in quotes as shown above.

Troubleshooting
- If `docker compose up` fails, ensure Docker Desktop is running and WSL2 integration is enabled.
- If you need Python 3.11 locally instead of Docker, install Python 3.11 and create a virtual environment, then run `python -m pip install -r requirements.txt`.

