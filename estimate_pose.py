# pose_extractor.py
import cv2
import numpy as np
import os
import mediapipe as mp

from smart_crop import preprocess_for_mediapipe

mp_pose = mp.solutions.pose


# ==========================================================
# 1) Detect if video frame is already well-framed (GolfDB-style)
# ==========================================================
def detect_if_good_frame(frame, min_visible=26, border_threshold=0.05):
    """
    Returns True if the frame is well-suited for SwingNet/MediaPipe.
    Criteria:
      - At least 26/33 visible landmarks
      - No body parts near image border
      - Golfer occupies a reasonable portion of the frame
    """
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(static_image_mode=True,
                      model_complexity=1,
                      enable_segmentation=False,
                      min_detection_confidence=0.40) as pose:

        res = pose.process(rgb)
        if not res.pose_landmarks:
            return False

        kps = res.pose_landmarks.landmark

        # A) Min number of visible landmarks
        visible = [lm.visibility > 0.4 for lm in kps]
        if sum(visible) < min_visible:
            return False

        # B) No landmarks near borders
        for lm in kps:
            if lm.visibility < 0.4:
                continue
            if lm.x < border_threshold or lm.x > 1-border_threshold:
                return False
            if lm.y < border_threshold or lm.y > 1-border_threshold:
                return False

        # C) Check bounding box area
        xs = [lm.x for lm in kps if lm.visibility > 0.4]
        ys = [lm.y for lm in kps if lm.visibility > 0.4]

        box_w = max(xs) - min(xs)
        box_h = max(ys) - min(ys)

        if not (0.30 < box_w < 0.90 and 0.30 < box_h < 0.90):
            return False

    return True


# ==========================================================
# 2) Main extractor: full-frame for SwingNet, conditional SmartCrop for MediaPipe
# ==========================================================
def extract_pose_and_swing_frames(video_path, seq_len=None, downsample=1):
    """
    Returns:
      keypoints_seq: (T,33,3)
      frames_for_swingnet: (T,3,224,224)
    """

    cap = cv2.VideoCapture(video_path)
    frames_raw = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames_raw.append(frame)
    cap.release()

    if len(frames_raw) == 0:
        return None, None

    # Optional sequence limit
    if seq_len and len(frames_raw) > seq_len:
        idxs = np.linspace(0, len(frames_raw)-1, seq_len).astype(int)
        frames_raw = [frames_raw[i] for i in idxs]

    # -----------------------------------------------------
    # Step 1 — Detect framing using the FIRST frame
    # -----------------------------------------------------
    first_frame = frames_raw[0]
    good_framing = detect_if_good_frame(first_frame)

    print("▶ Framing check:", "GOOD (no crop)" if good_framing else "BAD (SmartCrop enabled)")

    # -----------------------------------------------------
    # Step 2 — Build SwingNet frames (always full-frame)
    # -----------------------------------------------------
    frames_for_swingnet = []
    for f in frames_raw:
        rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        r224 = cv2.resize(rgb, (224, 224))
        frames_for_swingnet.append(r224.transpose(2, 0, 1).astype("float32") / 255.0)

    frames_for_swingnet = np.stack(frames_for_swingnet)
    # Save frames_for_swingnet (raw 0..1 RGB) for manual inspection
    try:
        out_dir = os.path.join('pipeline_out', 'swingnet_frames')
        os.makedirs(out_dir, exist_ok=True)
        np.save(os.path.join(out_dir, 'frames_for_swingnet_raw.npy'), frames_for_swingnet)
        for i in range(frames_for_swingnet.shape[0]):
            img = (frames_for_swingnet[i].transpose(1, 2, 0) * 255.0).astype('uint8')
            # frames_for_swingnet is RGB; convert to BGR for OpenCV saving
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(os.path.join(out_dir, f'frame_{i:04d}.jpg'), img_bgr)
    except Exception as e:
        print('Warning: could not save swingnet frames for inspection:', e)
    # Apply the same normalization used during training (ToTensor + Normalize)
    # Training used means [0.485,0.456,0.406] and stds [0.229,0.224,0.225]
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
    frames_for_swingnet = (frames_for_swingnet - mean) / std

    # -----------------------------------------------------
    # Step 3 — MediaPipe keypoint extraction (conditional crop)
    # -----------------------------------------------------
    pose = mp_pose.Pose(static_image_mode=False,
                        model_complexity=1,
                        enable_segmentation=False,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)

    keypoints_list = []

    for f in frames_raw:

        if good_framing:
            # No cropping at all → only resize
            crop = cv2.resize(f, (256, 256))
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        else:
            # Apply SmartCrop
            crop = preprocess_for_mediapipe(f, crop_ratio=0.70, sharpen=True)
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        res = pose.process(rgb_crop)

        kps = np.zeros((33, 3), dtype=np.float32)
        if res.pose_landmarks:
            for i, lm in enumerate(res.pose_landmarks.landmark):
                kps[i] = [lm.x, lm.y, lm.visibility]

        keypoints_list.append(kps)

    keypoints_seq = np.stack(keypoints_list)

    return keypoints_seq, frames_for_swingnet
