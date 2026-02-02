"""Biomechanics metrics and rule-based fault detection."""
from __future__ import annotations

import numpy as np
from math import acos, degrees


def _has_mediapipe_format(kps: np.ndarray) -> bool:
    return kps.shape[1] > 24


def compute_hip_centers(kps_seq: np.ndarray) -> np.ndarray:
    if _has_mediapipe_format(kps_seq):
        left_hip = kps_seq[:, 23, :2]
        right_hip = kps_seq[:, 24, :2]
    else:
        left_hip = kps_seq[:, 11, :2]
        right_hip = kps_seq[:, 12, :2]
    return (left_hip + right_hip) / 2.0


def compute_shoulder_width(kps_seq: np.ndarray, frame_index: int = 0) -> float:
    if kps_seq.shape[1] > 12:
        left_shoulder = kps_seq[frame_index, 11, :2]
        right_shoulder = kps_seq[frame_index, 12, :2]
    else:
        left_shoulder = kps_seq[frame_index, 5, :2]
        right_shoulder = kps_seq[frame_index, 6, :2]
    width = np.linalg.norm(left_shoulder - right_shoulder)
    return float(width + 1e-8)


def detect_head_movement(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    impact_frame: int | None = None,
    head_threshold: float = 0.04,
):
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
    T = kps_seq.shape[0]
    impact = T - 1 if impact_frame is None else impact_frame
    hips = compute_hip_centers(kps_seq)
    hip_x_address = hips[address_frame, 0]
    hip_x_impact = hips[impact, 0]
    dx = hip_x_impact - hip_x_address
    norm = compute_shoulder_width(kps_seq, address_frame)
    score = float(abs(dx) / norm)
    if score > lateral_threshold:
        return ("slide", score)
    return (None, score)


def compute_swing_metrics(
    kps_seq: np.ndarray,
    address_frame: int = 0,
    impact_frame: int | None = None,
):
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
    return {
        "swing_duration_frames": swing_duration,
        "x_factor_degrees": angle_degrees,
    }
