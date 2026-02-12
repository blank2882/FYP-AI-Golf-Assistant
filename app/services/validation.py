"""Video validation utilities for golf swing uploads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np



ALLOWED_EXTENSIONS = {".mp4", ".mov"}

MIN_DURATION_SEC = 2.0
MAX_DURATION_SEC = 10.0
MIN_FPS = 20.0
MIN_WIDTH = 320
MIN_HEIGHT = 240

POSE_MIN_RATIO = 0.65
SWINGNET_MIN_CONF = 0.25
MOTION_MIN_SCORE = 0.35
LIKELIHOOD_MIN_SCORE = 0.63

POSE_WEIGHT = 0.30
MOTION_WEIGHT = 0.30
SWINGNET_WEIGHT = 0.40


@dataclass
class ValidationResult:
    valid: bool
    message: str
    score: float
    signals: Dict[str, float]
    details: Dict[str, object]


def read_video_info(video_path: str) -> Dict[str, float]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"fps": 0.0, "frame_count": 0.0, "width": 0.0, "height": 0.0, "duration": 0.0}

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    width = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0)
    height = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0)
    cap.release()

    duration = frame_count / fps if fps > 0 else 0.0
    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration": duration,
    }


def validate_file_level(video_path: str) -> Tuple[bool, str, Dict[str, float]]:
    ext = Path(video_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Unsupported file type. Please upload an MP4 or MOV video.", {}

    info = read_video_info(video_path)
    if info["fps"] <= 0 or info["frame_count"] <= 0:
        return False, "Unable to read video metadata. Please upload a valid video file.", info

    if info["duration"] < MIN_DURATION_SEC or info["duration"] > MAX_DURATION_SEC:
        return (
            False,
            f"Video duration must be {MIN_DURATION_SEC:.0f} to {MAX_DURATION_SEC:.0f} seconds.",
            info,
        )

    if info["fps"] < MIN_FPS:
        return False, f"Video frame rate must be at least {MIN_FPS:.0f} FPS.", info

    if info["width"] < MIN_WIDTH or info["height"] < MIN_HEIGHT:
        return False, f"Video resolution must be at least {MIN_WIDTH}x{MIN_HEIGHT}.", info

    return True, "OK", info


def compute_pose_presence_ratio(metadata: List[Dict[str, object]]) -> float:
    if not metadata:
        return 0.0

    detected = 0
    for item in metadata:
        md = item.get("metadata", {}) if isinstance(item, dict) else {}
        poses = md.get("pose", []) if isinstance(md, dict) else []
        if not poses:
            continue
        pose = poses[0]
        if isinstance(pose, list) and len(pose) >= 20:
            detected += 1
    return detected / float(len(metadata))


def build_keypoint_array(collected_keypoints: List[List[Dict[str, float]]]) -> np.ndarray:
    if not collected_keypoints:
        return np.zeros((0, 0, 3), dtype=np.float32)

    landmark_count = len(collected_keypoints[0])
    kps = np.zeros((len(collected_keypoints), landmark_count, 3), dtype=np.float32)
    for t, pose in enumerate(collected_keypoints):
        for i, lm in enumerate(pose):
            kps[t, i, 0] = float(lm.get("x", 0.0))
            kps[t, i, 1] = float(lm.get("y", 0.0))
            kps[t, i, 2] = float(lm.get("visibility", 1.0))
    return kps


def _smooth_series(values: np.ndarray, window: int = 3) -> np.ndarray:
    if values.size == 0 or window <= 1:
        return values
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(values, kernel, mode="same")


def _angle_from_points(left: np.ndarray, right: np.ndarray) -> float:
    dx = float(right[0] - left[0])
    dy = float(right[1] - left[1])
    return float(np.degrees(np.arctan2(dy, dx)))


def _angle_diff_deg(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


def compute_motion_pattern_score(
    kps: np.ndarray,
    frame_idxs: List[int],
    fps: float,
) -> Tuple[float, Dict[str, float]]:
    if kps.size == 0 or len(frame_idxs) < 6 or fps <= 0:
        return 0.0, {"wrist_score": 0.0, "separation_score": 0.0}

    if kps.shape[1] <= 16:
        return 0.0, {"wrist_score": 0.0, "separation_score": 0.0}

    speeds: List[float] = []
    for i in range(1, len(frame_idxs)):
        dt = (frame_idxs[i] - frame_idxs[i - 1]) / float(fps)
        if dt <= 0:
            continue

        left_prev = kps[i - 1, 15, :2]
        left_now = kps[i, 15, :2]
        right_prev = kps[i - 1, 16, :2]
        right_now = kps[i, 16, :2]

        speed_left = float(np.linalg.norm(left_now - left_prev) / dt)
        speed_right = float(np.linalg.norm(right_now - right_prev) / dt)
        speed = max(speed_left, speed_right)

        shoulder_width = float(np.linalg.norm(kps[i, 11, :2] - kps[i, 12, :2]))
        speed_norm = speed / (shoulder_width + 1e-8)
        speeds.append(speed_norm)

    speeds_arr = np.array(speeds, dtype=np.float32)
    if speeds_arr.size < 5:
        return 0.0, {"wrist_score": 0.0, "separation_score": 0.0}

    smooth = _smooth_series(speeds_arr, window=3)
    peak_idx = int(np.argmax(smooth))
    peak_val = float(smooth[peak_idx])
    n = smooth.size

    pre = smooth[:peak_idx]
    post = smooth[peak_idx + 1 :]
    base_len = max(1, int(n * 0.2))
    base = float(np.median(smooth[:base_len]))

    prominence = peak_val / (base + 1e-6)
    peak_pos = peak_idx / float(max(1, n - 1))
    peak_pos_score = float(np.clip(1.0 - abs(peak_pos - 0.5) * 2.0, 0.0, 1.0))

    pre_slope = float(np.mean(np.diff(pre))) if pre.size > 1 else 0.0
    post_slope = float(np.mean(np.diff(post))) if post.size > 1 else 0.0

    rise_score = float(1.0 / (1.0 + np.exp(-pre_slope * 8.0)))
    fall_score = float(1.0 / (1.0 + np.exp(post_slope * 8.0)))
    prominence_score = float(np.clip((prominence - 1.5) / 1.5, 0.0, 1.0))

    wrist_score = (
        0.30 * peak_pos_score
        + 0.25 * rise_score
        + 0.25 * fall_score
        + 0.20 * prominence_score
    )

    separation_score = 0.0
    if kps.shape[1] > 24:
        shoulder_angles = []
        hip_angles = []
        for i in range(kps.shape[0]):
            shoulder_angles.append(_angle_from_points(kps[i, 11, :2], kps[i, 12, :2]))
            hip_angles.append(_angle_from_points(kps[i, 23, :2], kps[i, 24, :2]))
        sep = [_angle_diff_deg(s, h) for s, h in zip(shoulder_angles, hip_angles)]
        sep_range = float(np.max(sep) - np.min(sep)) if sep else 0.0
        separation_score = float(np.clip((sep_range - 10.0) / 20.0, 0.0, 1.0))

    motion_score = 0.7 * wrist_score + 0.3 * separation_score
    return float(np.clip(motion_score, 0.0, 1.0)), {
        "wrist_score": float(wrist_score),
        "separation_score": float(separation_score),
    }


def compute_swingnet_confidence(confidences: List[float]) -> float:
    if not confidences:
        return 0.0
    return float(np.mean(np.asarray(confidences, dtype=np.float32)))


def compute_likelihood_score(pose_ratio: float, motion_score: float, swingnet_conf: float) -> float:
    score = (
        POSE_WEIGHT * pose_ratio
        + MOTION_WEIGHT * motion_score
        + SWINGNET_WEIGHT * swingnet_conf
    )
    return float(np.clip(score, 0.0, 1.0))
