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
    
# function to visualize detection results on an image
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