"""MediaPipe-based object and pose detection utilities."""
from __future__ import annotations

import json
import os
from typing import Optional, Tuple, List, Dict, Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2

from app.core import config

# Visualization parameters
MARGIN = 10
ROW_SIZE = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)


def create_object_detector(det_obj_model_path: Optional[str | os.PathLike] = None):
    if det_obj_model_path is None:
        det_obj_model_path = str(config.MEDIAPIPE_OBJ_MODEL)

    base_options = mp.tasks.BaseOptions
    object_detector = mp.tasks.vision.ObjectDetector
    object_detector_options = mp.tasks.vision.ObjectDetectorOptions
    vision_running_mode = mp.tasks.vision.RunningMode

    options = object_detector_options(
        base_options=base_options(model_asset_path=str(det_obj_model_path)),
        max_results=1,
        running_mode=vision_running_mode.VIDEO,
        category_allowlist=["person"],
    )
    detector = object_detector.create_from_options(options)
    return detector


def visualize(image: np.ndarray, detection_result, scale_x: float = 1.0, scale_y: float = 1.0) -> np.ndarray:
    if detection_result is None:
        return image

    for detection in getattr(detection_result, "detections", []):
        bbox = detection.bounding_box
        start_point = (int(bbox.origin_x * scale_x), int(bbox.origin_y * scale_y))
        end_point = (
            int((bbox.origin_x + bbox.width) * scale_x),
            int((bbox.origin_y + bbox.height) * scale_y),
        )
        cv2.rectangle(image, start_point, end_point, TEXT_COLOR, 3)

        if detection.categories:
            category = detection.categories[0]
            category_name = category.category_name
            probability = round(category.score, 2)
            result_text = category_name + " (" + str(probability) + ")"
            text_location = (
                int(MARGIN + bbox.origin_x * scale_x),
                int(MARGIN + ROW_SIZE + bbox.origin_y * scale_y),
            )
            cv2.putText(
                image,
                result_text,
                text_location,
                cv2.FONT_HERSHEY_PLAIN,
                FONT_SIZE,
                TEXT_COLOR,
                FONT_THICKNESS,
            )

    return image


def create_pose_detector(model_path: Optional[str | os.PathLike] = None):
    if model_path is None:
        model_path = str(config.MEDIAPIPE_POSE_MODEL)

    base_options = mp.tasks.BaseOptions
    pose_landmarker = mp.tasks.vision.PoseLandmarker
    pose_landmarker_options = mp.tasks.vision.PoseLandmarkerOptions
    vision_running_mode = mp.tasks.vision.RunningMode

    options = pose_landmarker_options(
        base_options=base_options(model_asset_path=str(model_path)),
        running_mode=vision_running_mode.VIDEO,
    )
    detector = pose_landmarker.create_from_options(options)
    return detector


def draw_landmarks_on_image(rgb_image: np.ndarray, detection_result) -> np.ndarray:
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    for idx in range(len(pose_landmarks_list)):
        pose_landmarks = pose_landmarks_list[idx]

        pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()  # type: ignore[attr-defined]
        pose_landmarks_proto.landmark.extend(
            [
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z)  # type: ignore[attr-defined]
                for landmark in pose_landmarks
            ]
        )
        solutions.drawing_utils.draw_landmarks(  # type: ignore[attr-defined]
            annotated_image,
            pose_landmarks_proto,
            solutions.pose.POSE_CONNECTIONS,  # type: ignore[attr-defined]
            solutions.drawing_styles.get_default_pose_landmarks_style(),  # type: ignore[attr-defined]
        )
    return annotated_image


class DetectorPipeline:
    """Wrapper to run object + pose detectors together."""

    def __init__(
        self,
        obj_model_path: Optional[str | os.PathLike] = None,
        pose_model_path: Optional[str | os.PathLike] = None,
        input_scale: float = 1.0,
        obj_detector=None,
        pose_detector=None,
    ):
        if obj_detector is not None:
            self.obj_detector = obj_detector
        else:
            self.obj_detector = create_object_detector(obj_model_path)

        if pose_detector is not None:
            self.pose_detector = pose_detector
        else:
            self.pose_detector = create_pose_detector(pose_model_path)

        self.input_scale = float(input_scale)

    def process_frame(self, bgr_frame: np.ndarray, timestamp_ms: int = 0, return_metadata: bool = False):
        if bgr_frame is None:
            raise ValueError("bgr_frame must be a valid OpenCV image")

        orig_h, orig_w = bgr_frame.shape[:2]
        scale = self.input_scale if 0.5 <= self.input_scale <= 1.0 else 1.0
        if scale != 1.0:
            det_w = max(1, int(orig_w * scale))
            det_h = max(1, int(orig_h * scale))
            det_bgr = cv2.resize(bgr_frame, (det_w, det_h))
        else:
            det_bgr = bgr_frame
            det_w, det_h = orig_w, orig_h

        rgb_frame = cv2.cvtColor(det_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        obj_result = self.obj_detector.detect_for_video(mp_image, int(timestamp_ms))
        pose_result = self.pose_detector.detect_for_video(mp_image, int(timestamp_ms))

        annotated_rgb = draw_landmarks_on_image(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB), pose_result)
        annotated_bgr = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)
        scale_x = orig_w / float(det_w)
        scale_y = orig_h / float(det_h)
        annotated_bgr = visualize(annotated_bgr, obj_result, scale_x=scale_x, scale_y=scale_y)

        if not return_metadata:
            return annotated_bgr

        metadata = {"pose": [], "objects": []}

        pose_landmarks_list = getattr(pose_result, "pose_landmarks", []) or []
        for pose_landmarks in pose_landmarks_list:
            lm_list = []
            for lm in pose_landmarks:
                lm_list.append(
                    {
                        "x": float(getattr(lm, "x", 0.0)),
                        "y": float(getattr(lm, "y", 0.0)),
                        "z": float(getattr(lm, "z", 0.0)),
                        "visibility": float(getattr(lm, "visibility", 1.0)),
                    }
                )
            metadata["pose"].append(lm_list)

        for det in getattr(obj_result, "detections", []) or []:
            bbox = getattr(det, "bounding_box", None)
            cats = getattr(det, "categories", []) or []
            category = cats[0] if cats else None
            metadata["objects"].append(
                {
                    "bbox": {
                        "origin_x": float(getattr(bbox, "origin_x", 0.0)) * scale_x,
                        "origin_y": float(getattr(bbox, "origin_y", 0.0)) * scale_y,
                        "width": float(getattr(bbox, "width", 0.0)) * scale_x,
                        "height": float(getattr(bbox, "height", 0.0)) * scale_y,
                    },
                    "category_name": getattr(category, "category_name", None) if category else None,
                    "score": float(getattr(category, "score", 0.0)) if category else None,
                }
            )

        return annotated_bgr, metadata

    def process_video(
        self,
        input_path: str,
        display: bool = True,
        output_path: Optional[str] = None,
        every_n: int = 1,
        collect_metadata: bool = False,
        metadata_output_path: Optional[str] = None,
    ) -> Tuple[int, Optional[List[Dict[str, Any]]]]:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_index = 0
        processed = 0
        metadata_list: Optional[List[Dict[str, Any]]] = [] if collect_metadata else None
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index % every_n == 0:
                ts_ms = int(1000 * frame_index / fps) if fps and fps > 0 else 0
                if collect_metadata:
                    annotated, md = self.process_frame(frame, ts_ms, return_metadata=True)
                    if metadata_list is not None:
                        metadata_list.append(
                        {"frame_index": frame_index, "timestamp_ms": ts_ms, "metadata": md}
                        )
                else:
                    annotated = self.process_frame(frame, ts_ms)

                if display:
                    cv2.imshow("DetectorPipeline", annotated)  # type: ignore[arg-type]
                    if cv2.waitKey(5) & 0xFF == 27:
                        break

                if writer:
                    writer.write(annotated)  # type: ignore[arg-type]

                processed += 1

            frame_index += 1

        cap.release()
        if writer:
            writer.release()
        if display:
            cv2.destroyAllWindows()

        if collect_metadata and metadata_output_path:
            out_dir = os.path.dirname(metadata_output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(metadata_output_path, "w", encoding="utf-8") as f:
                json.dump(metadata_list, f, indent=2)

        return processed, metadata_list
