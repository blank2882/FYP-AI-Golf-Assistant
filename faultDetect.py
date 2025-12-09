# import necessary libraries
import numpy as np  
from math import acos, degrees  
# helper to detect MediaPipe-like keypoint indexing
def _has_mediapipe_format(kps: np.ndarray) -> bool: 
    # True if there are more than 24 keypoints (MediaPipe style)
    return kps.shape[1] > 24  

# compute hip center positions for each frame
def compute_hip_centers(kps_seq: np.ndarray) -> np.ndarray:  
    # check for MediaPipe indexing
    if _has_mediapipe_format(kps_seq):  
        # select left hip (index ~23) x,y for all frames
        left_hip = kps_seq[:, 23, :2]  
        # select right hip (index ~24) x,y for all frames
        right_hip = kps_seq[:, 24, :2]  
    # fallback if fewer keypoints (e.g., different detector)
    else:  
        # use alternate index for left hip/hip-like point
        left_hip = kps_seq[:, 11, :2]  
        # use alternate index for right hip/hip-like point
        right_hip = kps_seq[:, 12, :2]  
    # return the midpoint between left and right hip per frame
    return (left_hip + right_hip) / 2.0  

# compute shoulder width used for normalization
def compute_shoulder_width(kps_seq: np.ndarray, frame_index: int = 0) -> float:  
    # if there are dedicated shoulder keypoints
    if kps_seq.shape[1] > 12: 
        # left shoulder 
        left_shoulder = kps_seq[frame_index, 11, :2]  
        # right shoulder
        right_shoulder = kps_seq[frame_index, 12, :2]  
    # fallback to alternative indices if fewer keypoints are present    
    else:  
        # alternate left shoulder index
        left_shoulder = kps_seq[frame_index, 5, :2]  
        # alternate right shoulder index
        right_shoulder = kps_seq[frame_index, 6, :2]  
    # compute shoulder width as euclidean distance
    width = np.linalg.norm(left_shoulder - right_shoulder)  
    # add small epsilon and return as float to avoid division by zero
    return float(width + 1e-8)  

def detect_head_movement(kps_seq: np.ndarray, address_frame: int = 0, impact_frame: int = None, head_threshold: float = 0.04):
    # number of frames in the sequence
    T = kps_seq.shape[0]  
    # default impact frame is last frame if not provided
    impact = T - 1 if impact_frame is None else impact_frame  
    # nose position at address frame (keypoint index 0)
    nose_address = kps_seq[address_frame, 0, :2] 
    # nose position at impact frame
    nose_impact = kps_seq[impact, 0, :2]  
    # euclidean displacement of the nose between frames
    displacement = np.linalg.norm(nose_impact - nose_address)  
    # normalization factor: shoulder width at address frame
    norm = compute_shoulder_width(kps_seq, address_frame)  
    # normalized head movement score
    score = float(displacement / norm)  
    # return boolean indicating fault and the numeric score
    return (score > head_threshold), score  

def detect_slide_or_sway(kps_seq: np.ndarray, address_frame: int = 0, impact_frame: int = None, lateral_threshold: float = 0.12):
    # number of frames in the sequence
    T = kps_seq.shape[0] 
    # default impact frame is last frame if not provided
    impact = T - 1 if impact_frame is None else impact_frame  
    # get hip center per frame (x,y)
    hips = compute_hip_centers(kps_seq)
    # hip center x-coordinate at address frame
    hip_x_address = hips[address_frame, 0]  
    # hip center x-coordinate at impact
    hip_x_impact = hips[impact, 0]  
    # lateral displacement in x direction
    dx = hip_x_impact - hip_x_address  
    # normalization factor: shoulder width at address frame
    norm = compute_shoulder_width(kps_seq, address_frame)  
    # normalized lateral movement score as float
    score = float(abs(dx) / norm)  
    # compare against threshold to decide slide vs no slide
    if score > lateral_threshold:  
        return ("slide", score)  
    return (None, score)  

# calculate the raw metrics such as swing duration and X-factor stretch
def compute_swing_metrics(kps_seq: np.ndarray, address_frame: int = 0, impact_frame: int = None):
    # number of frames in the sequence
    T = kps_seq.shape[0]  
    # default impact frame is last frame if not provided
    impact = T - 1 if impact_frame is None else impact_frame  
    # compute swing duration in frames
    swing_duration = impact - address_frame  
    # get shoulder positions at address and impact frames
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
    # compute shoulder vectors
    shoulder_vec_address = right_shoulder_address - left_shoulder_address  
    shoulder_vec_impact = right_shoulder_impact - left_shoulder_impact  
    # compute angle between shoulder vectors using dot product
    dot_product = np.dot(shoulder_vec_address, shoulder_vec_impact)  
    norm_address = np.linalg.norm(shoulder_vec_address)  
    norm_impact = np.linalg.norm(shoulder_vec_impact)  
    cos_angle = dot_product / (norm_address * norm_impact + 1e-8)  
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  
    angle_degrees = degrees(acos(cos_angle))  
    # return computed metrics as a dictionary
    return {
        "swing_duration_frames": swing_duration,
        "x_factor_degrees": angle_degrees
    }
