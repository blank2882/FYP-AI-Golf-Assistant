"""DetectorPipeline: object-oriented wrapper to run object + pose detectors together.

This class provides a simple API:
  - process_frame(bgr_frame, timestamp_ms=0) -> annotated_bgr_frame
  - process_video(input_path, display=True, output_path=None, every_n=1)

It uses the existing `objDetect` and `poseDetect` modules in the repository.
"""
import cv2
import mediapipe as mp
import numpy as np
import json
import os
import objDetect
import poseDetect


class DetectorPipeline:
    def __init__(self, obj_model_path=None, pose_model_path=None, obj_detector=None, pose_detector=None):
        # Accept pre-created detectors or create from model paths
        if obj_detector is not None:
            self.obj_detector = obj_detector
        else:
            if obj_model_path is None:
                obj_model_path = getattr(objDetect, "model_path", None)
            self.obj_detector = objDetect.create_object_detector(obj_model_path)

        if pose_detector is not None:
            self.pose_detector = pose_detector
        else:
            if pose_model_path is None:
                pose_model_path = getattr(poseDetect, "model_path", None)
            self.pose_detector = poseDetect.create_pose_detector(pose_model_path)

    def process_frame(self, bgr_frame, timestamp_ms=0, return_metadata=False):
        """Run both detectors on a single BGR OpenCV frame and return annotated BGR frame.

        If `return_metadata` is True, also return a dictionary with:
          - 'pose': list of poses; each pose is list of {'x','y','z'} normalized landmarks
          - 'objects': list of detections with bbox (origin_x, origin_y, width, height),
                       category_name and score
        """
        if bgr_frame is None:
            raise ValueError("bgr_frame must be a valid OpenCV image")

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        obj_result = self.obj_detector.detect_for_video(mp_image, int(timestamp_ms))
        pose_result = self.pose_detector.detect_for_video(mp_image, int(timestamp_ms))

        # Draw pose landmarks on RGB image
        annotated_rgb = poseDetect.draw_landmarks_on_image(rgb_frame, pose_result)

        # Convert back to BGR for OpenCV drawing (object boxes)
        annotated_bgr = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)

        # Draw object detection boxes on BGR image
        annotated_bgr = objDetect.visualize(annotated_bgr, obj_result)

        if not return_metadata:
            return annotated_bgr

        # Build metadata
        metadata = {
            'pose': [],
            'objects': []
        }

        # Extract pose landmarks
        pose_landmarks_list = getattr(pose_result, 'pose_landmarks', []) or []
        for pose_landmarks in pose_landmarks_list:
            lm_list = []
            for lm in pose_landmarks:
                lm_list.append({'x': float(getattr(lm, 'x', 0.0)),
                                 'y': float(getattr(lm, 'y', 0.0)),
                                 'z': float(getattr(lm, 'z', 0.0))})
            metadata['pose'].append(lm_list)

        # Extract object detections
        for det in getattr(obj_result, 'detections', []) or []:
            bbox = getattr(det, 'bounding_box', None)
            cats = getattr(det, 'categories', []) or []
            category = cats[0] if cats else None
            metadata['objects'].append({
                'bbox': {
                    'origin_x': float(getattr(bbox, 'origin_x', 0.0)),
                    'origin_y': float(getattr(bbox, 'origin_y', 0.0)),
                    'width': float(getattr(bbox, 'width', 0.0)),
                    'height': float(getattr(bbox, 'height', 0.0))
                },
                'category_name': getattr(category, 'category_name', None) if category else None,
                'score': float(getattr(category, 'score', 0.0)) if category else None
            })

        # end process_frame
        return annotated_bgr, metadata

    def process_video(self, input_path, display=True, output_path=None, every_n=1, collect_metadata=False, metadata_output_path=None):
        """Process an entire video file and optionally display or write output.

        - `every_n` lets you process every Nth frame for speed.
        - If `collect_metadata` is True, returns (processed_count, metadata_list).
          If `metadata_output_path` is provided, metadata is dumped to JSON at that path.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_index = 0
        processed = 0
        metadata_list = [] if collect_metadata else None
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index % every_n == 0:
                ts_ms = int(1000 * frame_index / fps) if fps and fps > 0 else 0
                if collect_metadata:
                    annotated, md = self.process_frame(frame, ts_ms, return_metadata=True)
                    metadata_list.append({'frame_index': frame_index, 'timestamp_ms': ts_ms, 'metadata': md})
                else:
                    annotated = self.process_frame(frame, ts_ms)

                if display:
                    cv2.imshow("DetectorPipeline", annotated)
                    if cv2.waitKey(5) & 0xFF == 27:
                        break

                if writer:
                    writer.write(annotated)

                processed += 1

            frame_index += 1

        cap.release()
        if writer:
            writer.release()
        if display:
            cv2.destroyAllWindows()

        # write metadata file if requested
        if collect_metadata and metadata_output_path:
            out_dir = os.path.dirname(metadata_output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(metadata_output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_list, f, indent=2)

        if collect_metadata:
            return processed, metadata_list

        return processed
