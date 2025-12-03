# fault_detectors.py
import numpy as np
from math import acos, degrees

def _center_hip(kps):
    # MediaPipe: left_hip ~= 23, right_hip ~= 24 (best-effort)
    if kps.shape[1] > 24:
        lh = kps[:,23,:2]; rh = kps[:,24,:2]
    else:
        lh = kps[:,11,:2]; rh = kps[:,12,:2]
    return (lh + rh) / 2.0

def detect_head_movement(kps_seq, address_frame=0, impact_frame=None, head_threshold=0.04):
    T = kps_seq.shape[0]
    impact = T-1 if impact_frame is None else impact_frame
    nose_addr = kps_seq[address_frame, 0, :2]
    nose_imp = kps_seq[impact, 0, :2]
    dist = np.linalg.norm(nose_imp - nose_addr)
    # normalize by shoulder width
    if kps_seq.shape[1] > 12:
        ls = kps_seq[address_frame,11,:2]; rs = kps_seq[address_frame,12,:2]
    else:
        ls = kps_seq[address_frame,5,:2]; rs = kps_seq[address_frame,6,:2]
    norm = np.linalg.norm(ls - rs) + 1e-8
    score = dist / norm
    return (score > head_threshold), float(score)

def detect_slide_or_sway(kps_seq, address_frame=0, impact_frame=None, lateral_threshold=0.12):
    T = kps_seq.shape[0]
    impact = T-1 if impact_frame is None else impact_frame
    if kps_seq.shape[1] > 24:
        lh = kps_seq[:,23,0]; rh = kps_seq[:,24,0]
        hips = (lh + rh) / 2.0
    else:
        # fallback to shoulders
        ls = kps_seq[:,11,0]; rs = kps_seq[:,12,0]
        hips = (ls + rs) / 2.0
    addr = hips[address_frame]; imp = hips[impact]
    dx = imp - addr
    # normalize by shoulder width
    if kps_seq.shape[1] > 12:
        ls = kps_seq[address_frame,11,:2]; rs = kps_seq[address_frame,12,:2]
    else:
        ls = kps_seq[address_frame,5,:2]; rs = kps_seq[address_frame,6,:2]
    norm = np.linalg.norm(ls - rs) + 1e-8
    score = abs(dx) / norm
    if score > lateral_threshold:
        # naive split
        return ("slide", float(score))
    return (None, float(score))
