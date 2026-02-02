"""End-to-end AI pipeline orchestration."""
from __future__ import annotations

import json
import os
import time
from typing import Dict, Tuple

import cv2
import numpy as np

from app.core import config
from app.services.pose_estimation import DetectorPipeline
from app.services.temporal_seg import SwingNetInferer, EVENT_LIST
from app.services.feedback import generate_feedback
from app.services.biomech import detect_head_movement, detect_slide_or_sway, compute_swing_metrics
from app.services.tts_service import generate_audio_feedback


class GolfAssistant:
    """Orchestrator for the end-to-end golf assistant pipeline."""

    def __init__(
        self,
        video_path: str,
        weights_path: str | os.PathLike | None = None,
        out_dir: str | os.PathLike | None = None,
        det_obj_model_path: str | os.PathLike | None = None,
        det_pose_model_path: str | os.PathLike | None = None,
        crop_expand: float = 0.25,
        target_size: Tuple[int, int] = (224, 224),
    ):
        self.video_path = video_path
        self.weights_path = str(weights_path or config.SWINGNET_WEIGHTS)
        self.out_dir = str(out_dir or config.OUTPUTS_DIR)

        self.annotated_base = os.path.join(self.out_dir, "annotated.mp4")
        self.annotated_out = os.path.join(self.out_dir, "annotated_with_labels.mp4")
        self.pred_json = os.path.join(self.out_dir, "predicted_events.json")
        self.feedback_audio = os.path.join(self.out_dir, "feedback.wav")

        self.detector = DetectorPipeline(
            obj_model_path=det_obj_model_path or config.MEDIAPIPE_OBJ_MODEL,
            pose_model_path=det_pose_model_path or config.MEDIAPIPE_POSE_MODEL,
        )

        self.crop_expand = crop_expand
        self.target_size = target_size

        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        self.timing: Dict[str, float] = {}

    def print_timing_summary(self):
        total_time = 0
        for stage, duration in self.timing.items():
            if stage != "TOTAL":
                total_time += duration
        return total_time

    def run_detector(self, every_n: int = 1, display: bool = False):
        os.makedirs(self.out_dir, exist_ok=True)
        processed_count, metadata = self.detector.process_video(
            self.video_path,
            display=display,
            output_path=self.annotated_base,
            collect_metadata=True,
            metadata_output_path=os.path.join(self.out_dir, "metadata.json"),
        )
        return metadata

    def crop_and_resize(self, frame_bgr: np.ndarray, bbox: dict) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        ox = bbox.get("origin_x", 0.0)
        oy = bbox.get("origin_y", 0.0)
        bw = bbox.get("width", 1.0)
        bh = bbox.get("height", 1.0)

        x = int(ox * w)
        y = int(oy * h)
        ww = max(1, int(bw * w))
        hh = max(1, int(bh * h))

        ex = int(ww * self.crop_expand)
        ey = int(hh * self.crop_expand)
        x1 = max(0, x - ex)
        y1 = max(0, y - ey)
        x2 = min(w, x + ww + ex)
        y2 = min(h, y + hh + ey)

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            crop = cv2.resize(frame_bgr, self.target_size)
        else:
            crop = cv2.resize(crop, (self.target_size[1], self.target_size[0]))
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        return rgb

    def build_crops_from_metadata(self, metadata):
        if not metadata:
            return [], [], []

        meta_map = {m["frame_index"]: m["metadata"] for m in metadata}

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video: {self.video_path}")

        collected_rgb = []
        collected_frame_idxs = []
        collected_keypoints = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in meta_map:
                md = meta_map[frame_idx]
                used_bbox = None
                best_score = 0.0
                for obj in md.get("objects", []):
                    score = obj.get("score", 0.0) or 0.0
                    if score > best_score:
                        best_score = score
                        used_bbox = obj.get("bbox")

                poses = md.get("pose", []) or []
                if len(poses) > 0:
                    primary_pose = poses[0]
                else:
                    primary_pose = [{"x": 0.0, "y": 0.0, "z": 0.0} for _ in range(33)]

                if used_bbox is not None:
                    rgb = self.crop_and_resize(frame, used_bbox)
                    collected_rgb.append(rgb)
                    collected_frame_idxs.append(frame_idx)
                    collected_keypoints.append(primary_pose)
            frame_idx += 1

        cap.release()
        return collected_rgb, collected_frame_idxs, collected_keypoints

    def frames_to_swingnet_np(self, frames_rgb):
        arr = np.stack(frames_rgb, axis=0).astype(np.float32) / 255.0
        arr = arr.transpose(0, 3, 1, 2).copy()
        arr = (arr - self.mean[None, :, None, None]) / self.std[None, :, None, None]
        return arr

    def annotate_video_with_labels(self, base_video_path: str, out_path: str, label_map: dict):
        cap = cv2.VideoCapture(base_video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video {base_video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

        frame_idx = 0
        font = cv2.FONT_HERSHEY_SIMPLEX
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in label_map:
                label_str, conf = label_map[frame_idx]
                text = f"{label_str} ({conf:.2f})"
                cv2.putText(frame, text, (10, 30), font, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
            writer.write(frame)
            frame_idx += 1

        cap.release()
        writer.release()

    def run(self):
        pipeline_start = time.time()

        stage_start = time.time()
        metadata = self.run_detector()
        self.timing["1. Object & Pose Detection"] = time.time() - stage_start

        if not metadata:
            return {}

        stage_start = time.time()
        collected_rgb, collected_frame_idxs, collected_keypoints = self.build_crops_from_metadata(metadata)
        self.timing["2. Crop Extraction"] = time.time() - stage_start

        if len(collected_rgb) == 0:
            return {}

        stage_start = time.time()
        try:
            inferer = SwingNetInferer(self.weights_path)
        except Exception:
            return {}
        self.timing["3. SwingNet Model Loading"] = time.time() - stage_start

        stage_start = time.time()
        frames_np = self.frames_to_swingnet_np(collected_rgb)
        probs = inferer.run_sliding(frames_np, model_seq_len=64)
        self.timing["4. SwingNet Inference"] = time.time() - stage_start

        stage_start = time.time()
        labels = np.argmax(probs, axis=1)
        label_map = {}
        for i, fidx in enumerate(collected_frame_idxs):
            lab = int(labels[i])
            conf = float(probs[i, lab])
            label_str = EVENT_LIST[lab] if lab < len(EVENT_LIST) else "NoEvent"
            label_map[fidx] = (label_str, conf)

        event_frames = []
        confidences = []
        for c in range(min(probs.shape[1], len(EVENT_LIST))):
            idx = int(np.argmax(probs[:, c]))
            frame_for_class = collected_frame_idxs[idx]
            conf = float(probs[idx, c])
            event_frames.append(int(frame_for_class))
            confidences.append(conf)
            label_map[frame_for_class] = (EVENT_LIST[c], conf)
        self.timing["5. Label Processing"] = time.time() - stage_start

        stage_start = time.time()
        summary = {"predicted_events": []}
        for i, ef in enumerate(event_frames):
            summary["predicted_events"].append(
                {
                    "event_index": i,
                    "event_name": EVENT_LIST[i],
                    "frame_index": int(ef),
                    "confidence": float(confidences[i]),
                }
            )
        with open(self.pred_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        self.timing["6. JSON Export"] = time.time() - stage_start

        stage_start = time.time()
        self.annotate_video_with_labels(self.annotated_base, self.annotated_out, label_map)
        self.timing["7. Video Annotation"] = time.time() - stage_start

        stage_start = time.time()
        import numpy as _np

        if len(collected_keypoints) > 0:
            L = len(collected_keypoints[0])
            kps = _np.zeros((len(collected_keypoints), L, 3), dtype=_np.float32)
            for t, pose in enumerate(collected_keypoints):
                for i, lm in enumerate(pose):
                    x = float(lm.get("x", 0.0))
                    y = float(lm.get("y", 0.0))
                    vis = float(lm.get("visibility", 1.0))
                    kps[t, i, 0] = x
                    kps[t, i, 1] = y
                    kps[t, i, 2] = vis
        else:
            kps = _np.zeros((0, 0, 3), dtype=_np.float32)

        events_map = {EVENT_LIST[i]: int(ef) for i, ef in enumerate(event_frames)}

        faults = []
        head_flag, head_score = detect_head_movement(
            kps,
            address_frame=events_map.get("Address", 0),
            impact_frame=events_map.get("Impact"),
        )
        if head_flag:
            faults.append(("head_movement", head_score))
        slide_label, slide_score = detect_slide_or_sway(
            kps,
            address_frame=events_map.get("Address", 0),
            impact_frame=events_map.get("Impact"),
        )
        if slide_label:
            faults.append((slide_label, slide_score))
        swing_metrics = compute_swing_metrics(
            kps,
            address_frame=events_map.get("Address", 0),
            impact_frame=events_map.get("Impact"),
        )
        self.timing["8. Fault Detection"] = time.time() - stage_start

        stage_start = time.time()
        try:
            coaching = generate_feedback(events_map, kps, faults, prefer_http=True, model="qwen2.5")
        except Exception:
            coaching = (
                "AI feedback is currently unavailable. Review the annotated swing video and "
                "aim for a steady head position through impact."
            )
        self.timing["9. LLM Feedback Generation"] = time.time() - stage_start

        stage_start = time.time()
        try:
            audio_path = generate_audio_feedback(coaching, output_path=self.feedback_audio)
        except Exception:
            audio_path = None
        self.timing["10. Audio Synthesis"] = time.time() - stage_start

        self.timing["TOTAL"] = time.time() - pipeline_start

        return {
            "event_frames": event_frames,
            "confidences": confidences,
            "annotated_video": self.annotated_out,
            "json": self.pred_json,
            "faults": faults,
            "metrics": swing_metrics,
            "feedback": coaching,
            "audio_feedback": audio_path,
            "timings": self.timing,
        }
