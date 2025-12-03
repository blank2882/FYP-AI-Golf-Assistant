# code adapted from mediapipe documentation (https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python)
# import necessary libraries
import mediapipe as mp
import cv2
from mediapipe.tasks import python  
from mediapipe.tasks.python import vision
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
import numpy as np

model_path = "./models/pose_landmarker_heavy.task"

# initialize mediapipe pose landmarker
def create_pose_detector(model_path):
    # The create_from_options function accepts configuration options including running mode, display names locale, and pose landmark model asset path.
    baseOptions = mp.tasks.BaseOptions

    # The Pose Landmarker task supports several input data types: still images, video files and live video streams.
    poseLandmarker = mp.tasks.vision.PoseLandmarker
    poseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    visionRunningMode = mp.tasks.vision.RunningMode

    # set the model path and other options for the pose landmarker
    options = poseLandmarkerOptions(
        base_options=baseOptions(model_asset_path=model_path),
        running_mode=visionRunningMode.VIDEO,
    )
    # initialize the pose landmarker as per the specified options
    detector = poseLandmarker.create_from_options(options)
    return detector

# function to visualize pose landmarks on an image
def draw_landmarks_on_image(rgb_image, detection_result):
  pose_landmarks_list = detection_result.pose_landmarks
  annotated_image = np.copy(rgb_image)

  # Loop through the detected poses to visualize.
  for idx in range(len(pose_landmarks_list)):
    pose_landmarks = pose_landmarks_list[idx]

    # Draw the pose landmarks.
    pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
    pose_landmarks_proto.landmark.extend([
      landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in pose_landmarks
    ])
    solutions.drawing_utils.draw_landmarks(
      annotated_image,
      pose_landmarks_proto,
      solutions.pose.POSE_CONNECTIONS,
      solutions.drawing_styles.get_default_pose_landmarks_style())
  return annotated_image