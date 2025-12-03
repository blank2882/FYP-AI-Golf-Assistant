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
