# Golf Assistant Prototype

This repository contains a golf-swing pose extraction prototype. The project uses `opencv-python` and `mediapipe` for pose estimation.


## Quick start (recommended)


### Install the local LLM
1. Install ollama (https://ollama.com/)

2. Run '''ollama pull phi3''' in terminal

### Create the Conda virtual environment
1. Create a conda virtual environment
    - Ensure that the python version is either 3.10 or 3.11 to make it compatible for mediapipe pose

2. Install Pytorch, ensure that it is the CPU ONLY version!
    - pip install torch torchvision

3. Activate the conda virtual environment 
    - conda activate "E:\year 3\FYP\prototype git\FYP-AI-Golf-Assistant\.conda"

4. install the dependencies in requirements.txt with pip
    - pip install -r requirements.txt

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

MediaPipe landmark ranges
-------------------------

MediaPipe reports normalized landmark coordinates (x,y) in the range [0,1] relative to the image. In practice, landmarks that fall outside the image area may occasionally have coordinates slightly below 0 or above 1. Visibility/confidence values are also nominally in [0,1].

The repository tests relax strict [0,1] assumptions (and `estimate_pose.py` clips keypoints before returning) so downstream code receives sane, clipped values. If you need the raw un-clipped values for debugging, modify `estimate_pose.extract_pose_keypoints` accordingly.

