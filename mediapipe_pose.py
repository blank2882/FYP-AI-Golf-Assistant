import cv2
import mediapipe as mp
import numpy as np

class PoseExtractor:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()

    def extract_keypoints(self, frame):
        result = self.pose.process(frame)
        if not result.pose_landmarks:
            return None
        
        keypoints = []
        for lm in result.pose_landmarks.landmark:
            keypoints.append([lm.x, lm.y])  # normalized coordinates
        
        return np.array(keypoints)

    def video_to_keypoints(self, video_path):
        cap = cv2.VideoCapture(video_path)
        pose_sequence = []

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            keypoints = self.extract_keypoints(frame_rgb)

            if keypoints is not None:
                pose_sequence.append(keypoints)

        cap.release()
        return np.array(pose_sequence)  # shape: (T, 33, 2)
