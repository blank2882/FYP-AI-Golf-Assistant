from mediapipe_pose import PoseExtractor
from analyze_swing import SwingAnalyzer
from swingnet import SwingNet
from lstm import SwingLSTM
from llm_feedback import generate_feedback
from tts import generate_audio_feedback
import torch
import cv2
from pathlib import Path
import os
import numpy as np

def process_golf_swing(video_path):
    # --- 1. Pose Extraction ---
    pe = PoseExtractor()
    keypoints = pe.video_to_keypoints(video_path)

    # --- 2. Load SwingNet + LSTM ---
    swingnet = SwingNet()
    lstm_model = SwingLSTM()

    analyzer = None
    swing_events = []

    # load weights if available; otherwise skip model-based detection
    weights_ok = True
    if not Path("swingnet_weights.pth").exists() or not Path("lstm_weights.pth").exists():
        print("Model weight files not found — skipping SwingNet/LSTM inference.")
        weights_ok = False

    if weights_ok:
        try:
            swingnet.load_state_dict(torch.load("swingnet_weights.pth", map_location="cpu"))
            lstm_model.load_state_dict(torch.load("lstm_weights.pth", map_location="cpu"))
            swingnet.eval()
            lstm_model.eval()
            analyzer = SwingAnalyzer(swingnet, lstm_model)
        except Exception as e:
            print("Failed loading model weights:", e)
            analyzer = None

    # --- 3. Detect swing events using SwingNet (if analyzer available) ---
    frames_tensor = None
    if analyzer is not None:
        # build a simple frames tensor from the video
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # resize to 224x224 and convert to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (224, 224))
            frames.append(frame)
        cap.release()

        if len(frames) > 0:
            arr = np.stack(frames, axis=0)  # (T, H, W, C)
            # convert to (1, T, 3, H, W) and normalize to [0,1]
            arr = arr.astype(np.float32) / 255.0
            arr = np.transpose(arr, (0, 3, 1, 2))
            frames_tensor = torch.from_numpy(arr).unsqueeze(0)

            try:
                with torch.no_grad():
                    swing_events = analyzer.detect_swing_events(frames_tensor)
            except Exception as e:
                print("Error during swing event detection:", e)
                swing_events = []

    # --- 4. Detect swing errors using keypoints ---
    swing_errors = []
    if analyzer is not None:
        try:
            swing_errors = analyzer.detect_swing_errors(keypoints)
        except Exception as e:
            print("Error during swing error detection:", e)

    # --- 5. Generate LLM feedback ---
    # prepare a faults summary to send to the feedback generator
    faults = {
        "events": swing_events,
        "errors": swing_errors,
    }
    try:
        coaching_text = generate_feedback(faults)
    except Exception as e:
        print("Feedback generation failed:", e)
        coaching_text = "(Feedback unavailable)"

    # --- 6. Generate voice feedback ---
    try:
        audio_path = generate_audio_feedback(coaching_text)
    except Exception as e:
        print("Audio generation failed:", e)
        audio_path = None

    return coaching_text, audio_path

if __name__ == "__main__":
    text, audio = process_golf_swing("sample_swing.mp4")
    print("Coaching:", text)
    print("Audio saved at:", audio)
