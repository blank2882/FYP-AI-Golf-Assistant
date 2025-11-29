# fault_detectors.py
import numpy as np
from math import acos, degrees

# MediaPipe 33 landmarks mapping commonly used; indices same as earlier code.
def _center_shoulder(keypoints):
    ls = keypoints[11][:2]  # left_shoulder (MediaPipe index mapping differs slightly)
    rs = keypoints[12][:2]  # right_shoulder
    return (np.array(ls) + np.array(rs)) / 2

def _center_hip(keypoints):
    # MediaPipe: left_hip:23 right_hip:24 (if using 33 landmarks) - check mapping; adapt if needed
    # Here we try multiple likely indices and fallback.
    idx_l = 23 if keypoints.shape[0] > 23 else 11
    idx_r = 24 if keypoints.shape[0] > 24 else 12
    lh = keypoints[idx_l][:2]; rh = keypoints[idx_r][:2]
    return (np.array(lh) + np.array(rh)) / 2

def _norm_ref_dist(keypoints):
    # shoulder width: attempt indices that exist
    if keypoints.shape[0] > 12:
        ls = keypoints[11][:2]; rs = keypoints[12][:2]
    else:
        ls = keypoints[5][:2]; rs = keypoints[6][:2]
    return np.linalg.norm(np.array(ls)-np.array(rs)) + 1e-6

def _angle_between(a, b, c):
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosv = np.dot(ba, bc) / denom
    cosv = np.clip(cosv, -1.0, 1.0)
    return degrees(acos(cosv))

def _frame_index_or_default(idx, seq_len):
    if idx is None:
        return max(0, min(seq_len-1, seq_len//2))
    return idx

def detect_early_extension(keypoints_seq, top_frame=None, impact_frame=None, hip_raise_threshold=0.06):
    T = keypoints_seq.shape[0]
    top = _frame_index_or_default(top_frame, T)
    impact = _frame_index_or_default(impact_frame, T)
    hip_top = _center_hip(keypoints_seq[top])
    hip_imp = _center_hip(keypoints_seq[impact])
    dy = hip_top[1] - hip_imp[1]
    norm = _norm_ref_dist(keypoints_seq[top])
    score = dy / norm
    detected = score > hip_raise_threshold
    return detected, float(score)

def detect_sway_or_slide(keypoints_seq, address_frame=None, impact_frame=None, lateral_threshold=0.12):
    T = keypoints_seq.shape[0]
    addr = _frame_index_or_default(address_frame, 0)
    impact = _frame_index_or_default(impact_frame, T-1)
    hip_addr = _center_hip(keypoints_seq[addr])
    hip_impact = _center_hip(keypoints_seq[impact])
    dx = hip_impact[0] - hip_addr[0]
    norm = _norm_ref_dist(keypoints_seq[addr])
    score = abs(dx) / norm
    hip_x = np.array([_center_hip(kp)[0] for kp in keypoints_seq])
    p2p = hip_x.max() - hip_x.min()
    p2p_score = p2p / (norm + 1e-8)
    if p2p_score > lateral_threshold and score > (lateral_threshold/2):
        pre = hip_x[:max(1, impact)]
        post = hip_x[impact:]
        if len(pre) > 1 and len(post) > 1:
            sign_pre = np.sign(hip_x[impact] - pre.mean())
            sign_post = np.sign(post.mean() - hip_x[impact])
            if sign_pre * sign_post < 0:
                return 'sway', float(p2p_score)
        return 'slide', float(p2p_score)
    return None, float(p2p_score)

def detect_over_the_top(keypoints_seq, top_frame=None, transition_window=8, ott_angle_threshold=18.0):
    T = keypoints_seq.shape[0]
    top = _frame_index_or_default(top_frame, T//2)
    start = top
    end = min(T-1, top + transition_window)
    # choose wrist indices (left/right)
    candidates = []
    for wrist_idx, shoulder_idx in [(15,11),(16,12)]:  # example indices; verify mapping for your layout
        if wrist_idx >= keypoints_seq.shape[1] or shoulder_idx >= keypoints_seq.shape[1]:
            continue
        wrist_top = keypoints_seq[top, wrist_idx, :2]
        wrist_early = keypoints_seq[start:end+1, wrist_idx, :2].mean(axis=0)
        shoulder_top = _center_shoulder(keypoints_seq[top])
        v1 = wrist_top - shoulder_top
        v2 = wrist_early - shoulder_top
        angle = _angle_between(shoulder_top + v1, shoulder_top, shoulder_top + v2)
        candidates.append(angle)
    if not candidates:
        return False, 0.0
    angle = max(candidates)
    detected = angle > ott_angle_threshold
    return detected, float(angle)

def detect_casting(keypoints_seq, top_frame=None, early_down_frames=6, wrist_drop_angle_threshold=20.0):
    T = keypoints_seq.shape[0]
    top = _frame_index_or_default(top_frame, T//2)
    early = min(T-1, top + early_down_frames)
    angles = []
    # elbow, wrist, shoulder indices example pairs (verify mapping per used landmark set)
    pairs = [(13,15,11),(14,16,12)]  # placeholders (should be corrected per mapping)
    for elbow_idx, wrist_idx, shoulder_idx in pairs:
        if max(elbow_idx, wrist_idx, shoulder_idx) >= keypoints_seq.shape[1]:
            continue
        a_top = _angle_between(keypoints_seq[top, elbow_idx,:2], keypoints_seq[top, wrist_idx,:2], keypoints_seq[top, shoulder_idx,:2])
        a_early = _angle_between(keypoints_seq[early, elbow_idx,:2], keypoints_seq[early, wrist_idx,:2], keypoints_seq[early, shoulder_idx,:2])
        angles.append(a_early - a_top)
    if not angles:
        return False, 0.0
    change = max(angles)
    detected = change > wrist_drop_angle_threshold
    return detected, float(change)

def detect_chicken_wing(keypoints_seq, impact_frame=None, post_impact_offset=3, elbow_angle_threshold=30.0):
    T = keypoints_seq.shape[0]
    impact = _frame_index_or_default(impact_frame, T//2)
    post = min(T-1, impact + post_impact_offset)
    changes = []
    pairs = [(11,13,15),(12,14,16)]
    for shoulder_idx, elbow_idx, wrist_idx in pairs:
        if max(shoulder_idx, elbow_idx, wrist_idx) >= keypoints_seq.shape[1]:
            continue
        angle_impact = _angle_between(keypoints_seq[impact, shoulder_idx,:2], keypoints_seq[impact, elbow_idx,:2], keypoints_seq[impact, wrist_idx,:2])
        angle_post = _angle_between(keypoints_seq[post, shoulder_idx,:2], keypoints_seq[post, elbow_idx,:2], keypoints_seq[post, wrist_idx,:2])
        changes.append(angle_impact - angle_post)
    if not changes:
        return False, 0.0
    change = max(changes)
    detected = change > elbow_angle_threshold
    return detected, float(change)

def detect_head_movement(keypoints_seq, address_frame=None, impact_frame=None, head_threshold=0.04):
    T = keypoints_seq.shape[0]
    addr = _frame_index_or_default(address_frame, 0)
    impact = _frame_index_or_default(impact_frame, T-1)
    nose_addr = keypoints_seq[addr, 0, :2]
    nose_impact = keypoints_seq[impact, 0, :2]
    dist = np.linalg.norm(nose_impact - nose_addr)
    norm = _norm_ref_dist(keypoints_seq[addr])
    score = dist / norm
    detected = score > head_threshold
    return detected, float(score)
