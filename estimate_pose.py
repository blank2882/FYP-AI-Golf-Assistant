import mediapipe as mp
import numpy as np
import cv2
from smart_crop import preprocess_frame

mp_pose = mp.solutions.pose

def extract_pose_keypoints(video_path):
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)
    cap = cv2.VideoCapture(video_path)

    keypoints_seq = []
    frames_seq = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        processed = preprocess_frame(frame)

        # Normalize to RGB
        rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

        results = pose.process(rgb)

        frame_keypoints = np.zeros((33, 3))

        if results.pose_landmarks:
            for i, lm in enumerate(results.pose_landmarks.landmark):
                frame_keypoints[i] = [lm.x, lm.y, lm.visibility]

        keypoints_seq.append(frame_keypoints)
        
        # For Swingnet we also need normalized frames (224x224)
        swingnet_frame = cv2.resize(rgb, (224, 224)) / 255.0
        frames_seq.append(np.transpose(swingnet_frame, (2,0,1)))

    cap.release()

    keypoints_arr = np.array(keypoints_seq)
    frames_arr = np.array(frames_seq)

    # Clip keypoints to sensible ranges before returning.
    # x,y coordinates are normalized (usually in [0,1]) but MediaPipe may
    # occasionally return values slightly outside that range when landmarks
    # lie outside the image. Visibility is also bounded to [0,1].
    def _clip_keypoints(karr):
        if karr.size == 0:
            return karr
        k = karr.copy()
        # x,y are first two channels, visibility is third
        k[..., :2] = np.clip(k[..., :2], 0.0, 1.0)
        k[..., 2] = np.clip(k[..., 2], 0.0, 1.0)
        return k

    keypoints_arr = _clip_keypoints(keypoints_arr)

    return keypoints_arr, frames_arr
