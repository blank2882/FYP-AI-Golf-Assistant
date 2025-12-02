# code adapted from mediapipe documentation (https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/python#video_2)

# import necessary libraries
import mediapipe as mp
import cv2 
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

# visualization parameters
MARGIN = 10  # pixels
ROW_SIZE = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)  # red

# create the object detector
def create_object_detector(detObj_model_path):
    # The create_from_options function accepts configuration options including running mode, display names locale, max number of results, confidence threshold, category allow list, and deny list.
    baseOptions = mp.tasks.BaseOptions

    # The Object Detector task supports several input data types: still images, video files and live video streams.
    objectDetector = mp.tasks.vision.ObjectDetector
    objectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
    visionRunningMode = mp.tasks.vision.RunningMode

    # set the model path and other options for the object detector
    options = objectDetectorOptions(
        base_options=baseOptions(model_asset_path=detObj_model_path),
        max_results=1,
        running_mode=visionRunningMode.VIDEO,
        category_allowlist=['person']
    )
    # initialize the object detector as per the specified options
    detector = objectDetector.create_from_options(options)
    return detector

# # prepare to process video frames
# def process_frame(detector, frame=None, timestamp=None, video_path=None):
#     """Process either a single frame or an entire video.

#     If `frame` is provided (an OpenCV BGR numpy array), this function runs
#     detection for that single frame using `timestamp` (ms) and returns the
#     visualized frame. If `frame` is None, it will read and process the
#     video at `video_path` (or the module-level `video_path` if not provided)
#     and display frames in a window.
#     """
#     # If a single frame was provided, process and return it.
#     if frame is not None:
#         # Accept timestamps in seconds or milliseconds; test provides integer 0.
#         ts_ms = int(timestamp) if timestamp is not None else 0
#         # Convert the OpenCV BGR image to RGB for MediaPipe
#         numpy_frame_from_opencv = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=numpy_frame_from_opencv)

#         detection_result = detector.detect_for_video(mp_image, ts_ms)
#         out_frame = visualize(frame, detection_result)
#         return out_frame

#     # Otherwise, process the full video from the given path.
#     vp = video_path if video_path else globals().get("video_path")
#     if not vp:
#         raise ValueError("No video path provided for full-video processing")

#     # Use OpenCV’s VideoCapture to load the input video.
#     cap = cv2.VideoCapture(vp)

#     # Load the frame rate of the video using OpenCV’s CV_CAP_PROP_FPS
#     # You’ll need it to calculate the timestamp for each frame.
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     frame_index = 0

#     # Loop through each frame in the video using VideoCapture#read()
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break
#         # Calculate the timestamp (in milliseconds) for the current frame.
#         frame_timestamp_ms = int(1000 * frame_index / fps) if fps and fps > 0 else 0
#         # Convert the OpenCV BGR image to RGB.
#         numpy_frame_from_opencv = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         # Convert the frame received from OpenCV to a MediaPipe’s Image object.
#         mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=numpy_frame_from_opencv)

#         detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)
#         frame = visualize(frame, detection_result)

#         cv2.imshow('MediaPipe Object Detection', frame)
#         if cv2.waitKey(5) & 0xFF == 27:
#             break
#         frame_index += 1
#     cap.release()
#     cv2.destroyAllWindows()
    
def visualize(image, detection_result) -> np.ndarray:
    """Draws bounding boxes on the input image and return it.
    Args:
    image: The input RGB image.
    detection_result: The list of all "Detection" entities to be visualize.
    Returns:
    Image with bounding boxes.
    """
    if detection_result is None:
        return image

    for detection in getattr(detection_result, "detections", []):
        # Draw bounding_box
        bbox = detection.bounding_box
        start_point = (int(bbox.origin_x), int(bbox.origin_y))
        end_point = (int(bbox.origin_x + bbox.width), int(bbox.origin_y + bbox.height))
        cv2.rectangle(image, start_point, end_point, TEXT_COLOR, 3)

        # Draw label and score
        if detection.categories:
            category = detection.categories[0]
            category_name = category.category_name
            probability = round(category.score, 2)
            result_text = category_name + ' (' + str(probability) + ')'
            text_location = (int(MARGIN + bbox.origin_x),
                                int(MARGIN + ROW_SIZE + bbox.origin_y))
            cv2.putText(image, result_text, text_location, cv2.FONT_HERSHEY_PLAIN,
                        FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)

    return image