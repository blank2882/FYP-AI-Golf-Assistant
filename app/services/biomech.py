"""Biomechanics metrics and rule-based fault detection.

This module converts pose keypoints into interpretable golf metrics.
The checks here are deterministic rules (not ML predictions), which
makes them easier to debug and explain.
"""
from __future__ import annotations

import numpy as np
from math import acos, degrees, atan2, cos, sin


# Threshold values for each fault type (used for confidence calculation)
FAULT_THRESHOLDS = {
    "head_movement": 0.04,
    "slide": 0.12,
    "sway": 0.10,
    "early_extension": 0.06,
    "over_the_top": 0.12,
}


def _score_to_confidence(fault_name: str, score: float, alpha: float = 6.0) -> float:
    """
    Convert a raw biomechanical score to a confidence 0-1.
    This confidence represents  the strength of the fault detection. Not a probability.
    
    Uses sigmoid mapping to reflect:
    - measurement noise near zero score
    - rapid confidence increase once deviation exceeds threshold
    - saturation at larger deviations
    """
    threshold = FAULT_THRESHOLDS.get(fault_name, 0.1)
    if score <= 0:
        return 0.0
    relative_excess = (score - threshold) / (threshold + 1e-8)
    confidence = 1.0 / (1.0 + np.exp(-alpha * relative_excess))
    return float(np.clip(confidence, 0.0, 1.0))


def _has_mediapipe_format(kps: np.ndarray) -> bool:
    # MediaPipe Pose has 33 landmarks, while alternative layouts in this project are smaller.
    return kps.shape[1] > 24


def compute_hip_centers(kps_seq: np.ndarray) -> np.ndarray:
    if _has_mediapipe_format(kps_seq):
        left_hip = kps_seq[:, 23, :2]
        right_hip = kps_seq[:, 24, :2]
    else:
        left_hip = kps_seq[:, 11, :2]
        right_hip = kps_seq[:, 12, :2]
    return (left_hip + right_hip) / 2.0


def compute_shoulder_centers(kps_seq: np.ndarray) -> np.ndarray:
    if _has_mediapipe_format(kps_seq):
        left_shoulder = kps_seq[:, 11, :2]
        right_shoulder = kps_seq[:, 12, :2]
    else:
        left_shoulder = kps_seq[:, 5, :2]
        right_shoulder = kps_seq[:, 6, :2]
    return (left_shoulder + right_shoulder) / 2.0


def compute_shoulder_width(kps_seq: np.ndarray, frame_index: int = 0) -> float:
    if kps_seq.shape[1] > 12:
        left_shoulder = kps_seq[frame_index, 11, :2]
        right_shoulder = kps_seq[frame_index, 12, :2]
    else:
        left_shoulder = kps_seq[frame_index, 5, :2]
        right_shoulder = kps_seq[frame_index, 6, :2]
    width = np.linalg.norm(left_shoulder - right_shoulder)
    return float(width + 1e-8)


def compute_torso_height(kps_seq: np.ndarray, frame_index: int = 0) -> float:
    shoulders = compute_shoulder_centers(kps_seq)
    hips = compute_hip_centers(kps_seq)
    height = np.linalg.norm(shoulders[frame_index] - hips[frame_index])
    return float(height + 1e-8)


def classify_camera_angle(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    face_on_ratio: float = 0.6,
) -> str:
    """Classify camera angle as 'face_on' or 'down_the_line'."""
    shoulder_width = compute_shoulder_width(kps_seq, address_frame)
    torso_height = compute_torso_height(kps_seq, address_frame)
    ratio = shoulder_width / torso_height
    return "face_on" if ratio >= face_on_ratio else "down_the_line"


def _perp_axis_from_shoulders(kps_seq: np.ndarray, frame_index: int = 0) -> np.ndarray:
    if _has_mediapipe_format(kps_seq):
        left = kps_seq[frame_index, 11, :2]
        right = kps_seq[frame_index, 12, :2]
    else:
        left = kps_seq[frame_index, 5, :2]
        right = kps_seq[frame_index, 6, :2]
    vec = right - left
    dx = float(vec[0])
    dy = float(vec[1])
    theta = atan2(dy, dx)
    perp = np.array([-sin(theta), cos(theta)], dtype=np.float32)
    norm = np.linalg.norm(perp) + 1e-8
    return perp / norm


def detect_head_movement(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    impact_frame: int | None = None,
    head_threshold: float = 0.04,
):
    # Compare nose displacement between address and impact, normalized by shoulder width.
    T = kps_seq.shape[0]
    impact = T - 1 if impact_frame is None else impact_frame
    nose_address = kps_seq[address_frame, 0, :2]
    nose_impact = kps_seq[impact, 0, :2]
    displacement = np.linalg.norm(nose_impact - nose_address)
    norm = compute_shoulder_width(kps_seq, address_frame)
    score = float(displacement / norm)
    return (score > head_threshold), score


def detect_slide_or_sway(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    impact_frame: int | None = None,
    lateral_threshold: float = 0.12,
):
    # Lateral hip movement near impact is treated as a "slide" fault.
    T = kps_seq.shape[0]
    impact = T - 1 if impact_frame is None else impact_frame
    hips = compute_hip_centers(kps_seq)
    perp = _perp_axis_from_shoulders(kps_seq, address_frame)
    disp = hips[impact] - hips[address_frame]
    lateral = float(abs(np.dot(disp, perp)))
    norm = compute_shoulder_width(kps_seq, address_frame)
    score = float(lateral / norm)
    if score > lateral_threshold:
        return ("slide", score)
    return (None, score)


def detect_sway(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    top_frame: int | None = None,
    sway_threshold: float = 0.10,
):
    T = kps_seq.shape[0]
    top = T - 1 if top_frame is None else top_frame
    hips = compute_hip_centers(kps_seq)
    perp = _perp_axis_from_shoulders(kps_seq, address_frame)
    disp = hips[top] - hips[address_frame]
    lateral = float(abs(np.dot(disp, perp)))
    norm = compute_shoulder_width(kps_seq, address_frame)
    score = float(lateral / norm)
    if score > sway_threshold:
        return ("sway", score)
    return (None, score)


def detect_early_extension(
    kps_seq: np.ndarray,
    top_frame: int | None = None,
    impact_frame: int | None = None,
    extension_threshold: float = 0.06,
):
    T = kps_seq.shape[0]
    top = 0 if top_frame is None else top_frame
    impact = T - 1 if impact_frame is None else impact_frame
    hips = compute_hip_centers(kps_seq)
    hip_y_top = hips[top, 1]
    hip_y_impact = hips[impact, 1]
    dy = hip_y_impact - hip_y_top
    norm = compute_shoulder_width(kps_seq, top)
    score = float(dy / norm)
    if score > extension_threshold:
        return ("early_extension", score)
    return (None, score)


def detect_over_the_top(
    kps_seq: np.ndarray,
    top_frame: int | None = None,
    impact_frame: int | None = None,
    ott_threshold: float = 0.12,
):
    T = kps_seq.shape[0]
    top = 0 if top_frame is None else top_frame
    impact = T - 1 if impact_frame is None else impact_frame
    if impact <= top:
        return (None, 0.0)

    mid = top + max(1, int((impact - top) * 0.25))
    shoulders = compute_shoulder_centers(kps_seq)
    shoulder_x_top = shoulders[top, 0]
    shoulder_x_mid = shoulders[mid, 0]

    # Use both wrists; if either moves significantly outward early in downswing
    if _has_mediapipe_format(kps_seq):
        left_wrist = kps_seq[:, 15, 0]
        right_wrist = kps_seq[:, 16, 0]
    else:
        left_wrist = kps_seq[:, 7, 0]
        right_wrist = kps_seq[:, 8, 0]

    # Relative x distance from shoulder center
    rel_left_top = abs(left_wrist[top] - shoulder_x_top)
    rel_left_mid = abs(left_wrist[mid] - shoulder_x_mid)
    rel_right_top = abs(right_wrist[top] - shoulder_x_top)
    rel_right_mid = abs(right_wrist[mid] - shoulder_x_mid)

    rel_delta = max(rel_left_mid - rel_left_top, rel_right_mid - rel_right_top)
    norm = compute_shoulder_width(kps_seq, top)
    score = float(rel_delta / norm)
    if score > ott_threshold:
        return ("over_the_top", score)
    return (None, score)


def compute_swing_metrics(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    impact_frame: int | None = None,
    top_frame: int | None = None,
):
    # Derive compact numeric metrics for UI display and downstream logging.
    T = kps_seq.shape[0]
    impact = T - 1 if impact_frame is None else impact_frame
    swing_duration = impact - address_frame
    if _has_mediapipe_format(kps_seq):
        left_shoulder_address = kps_seq[address_frame, 11, :2]
        right_shoulder_address = kps_seq[address_frame, 12, :2]
        left_shoulder_impact = kps_seq[impact, 11, :2]
        right_shoulder_impact = kps_seq[impact, 12, :2]
    else:
        left_shoulder_address = kps_seq[address_frame, 5, :2]
        right_shoulder_address = kps_seq[address_frame, 6, :2]
        left_shoulder_impact = kps_seq[impact, 5, :2]
        right_shoulder_impact = kps_seq[impact, 6, :2]
    shoulder_vec_address = right_shoulder_address - left_shoulder_address
    shoulder_vec_impact = right_shoulder_impact - left_shoulder_impact
    dot_product = np.dot(shoulder_vec_address, shoulder_vec_impact)
    norm_address = np.linalg.norm(shoulder_vec_address)
    norm_impact = np.linalg.norm(shoulder_vec_impact)
    cos_angle = dot_product / (norm_address * norm_impact + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_degrees = degrees(acos(cos_angle))
    metrics = {
        "swing_duration_frames": swing_duration,
        "x_factor_degrees": angle_degrees,
    }

    if top_frame is not None and impact is not None:
        backswing = max(1, int(top_frame) - int(address_frame))
        downswing = max(1, int(impact) - int(top_frame))
        metrics["backswing_frames"] = backswing
        metrics["downswing_frames"] = downswing
        metrics["swing_tempo"] = float(backswing) / float(downswing)

    return metrics
