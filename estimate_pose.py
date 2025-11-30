# pose_extractor.py
import cv2
import numpy as np
import mediapipe as mp

from smart_crop import preprocess_for_mediapipe

mp_pose = mp.solutions.pose


def detect_if_good_frame_multi(frames, min_visible=24, border_threshold=0.05, sample_n=5):
    """
    Decide whether the video is already well-framed by checking the first `sample_n` frames.
    Returns True if majority of sampled frames are "good".
    Criteria per frame:
      - Enough visible landmarks (visibility > 0.4)
      - No landmark near the border threshold
      - Human bounding-box reasonably sized in frame (0.30..0.90)
    """
    # sample up to sample_n frames from beginning evenly
    n = min(len(frames), sample_n)
    if n == 0:
        return False
    idxs = np.linspace(0, n-1, n).astype(int)
    good_count = 0
    with mp_pose.Pose(static_image_mode=True,
                      model_complexity=1,
                      enable_segmentation=False,
                      min_detection_confidence=0.40) as pose:
        for i in idxs:
            frame = frames[i]
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            if not res.pose_landmarks:
                continue
            kps = res.pose_landmarks.landmark
            visible = [lm.visibility > 0.4 for lm in kps]
            if sum(visible) < min_visible:
                continue
            # border check
            border_violation = False
            xs = []
            ys = []
            for lm in kps:
                if lm.visibility < 0.4:
                    continue
                if lm.x < border_threshold or lm.x > 1 - border_threshold or lm.y < border_threshold or lm.y > 1 - border_threshold:
                    border_violation = True
                    break
                xs.append(lm.x)
                ys.append(lm.y)
            if border_violation:
                continue
            if len(xs) < 3 or len(ys) < 3:
                continue
            box_w = max(xs) - min(xs)
            box_h = max(ys) - min(ys)
            if not (0.30 < box_w < 0.90 and 0.30 < box_h < 0.90):
                continue
            good_count += 1
    # if majority of sampled frames are good, consider video well framed
    return good_count >= max(1, n // 2)


def extract_pose_and_swing_frames(video_path, seq_len=None, downsample=1, framing_sample_n=5):
    """
    Read video once. Produce:
      - keypoints_seq: np.array (T,33,3) normalized (0..1) per frame w.r.t crop/resized region
      - frames_for_swingnet: np.array (T,3,224,224) float32 in [0,1]

    Decision: smart-crop only if detect_if_good_frame_multi votes 'bad'.
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

    # optionally sample or limit to seq_len (we keep full sequence here, sliding will handle windows)
    if seq_len and len(frames_raw) > seq_len:
        import numpy as _np
        idxs = _np.linspace(0, len(frames_raw)-1, seq_len).astype(int)
        frames_raw = [frames_raw[i] for i in idxs]

    # decide framing using first few frames
    good_framing = detect_if_good_frame_multi(frames_raw, sample_n=framing_sample_n)
    print("▶ Framing check (multi-frame):", "GOOD (no crop)" if good_framing else "BAD (SmartCrop enabled)")

    # prepare swingnet frames (full-frame resized)
    frames_for_swingnet = []
    for f in frames_raw:
        rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        r224 = cv2.resize(rgb, (224, 224))
        r224 = r224.astype("float32") / 255.0
        frames_for_swingnet.append(r224.transpose(2, 0, 1))
    frames_for_swingnet = np.stack(frames_for_swingnet)  # (T,3,224,224)

    # prepare keypoints for MediaPipe
    pose = mp_pose.Pose(static_image_mode=False,
                        model_complexity=1,
                        enable_segmentation=False,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)
    keypoints_list = []
    for f in frames_raw:
        if good_framing:
            # use simple resize (no crop) for pose — less distortion of full-body landmarks
            crop = cv2.resize(f, (256, 256))
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        else:
            crop = preprocess_for_mediapipe(f, crop_ratio=0.70, sharpen=True)
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        res = pose.process(rgb_crop)
        kps = np.zeros((33, 3), dtype=np.float32)
        if res.pose_landmarks:
            for i, lm in enumerate(res.pose_landmarks.landmark):
                # landmarks are normalized to the input crop/resize; keep them that way
                kps[i] = [lm.x, lm.y, lm.visibility if hasattr(lm, "visibility") else 1.0]
        keypoints_list.append(kps)
    keypoints_seq = np.stack(keypoints_list)

    return keypoints_seq, frames_for_swingnet
