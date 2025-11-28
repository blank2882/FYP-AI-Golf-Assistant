import importlib
import pathlib
import cv2
import numpy as np
import pytest
import smart_crop


try:
    estimate_pose = importlib.import_module('estimate_pose')
except Exception:
    estimate_pose = None


@pytest.mark.skipif(estimate_pose is None, reason="estimate_pose (or mediapipe) not available")
def test_smartcrop_then_estimate_pose_pipeline(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    src_video = repo_root / 'golfdb' / 'test_video.mp4'
    if not src_video.exists():
        pytest.skip(f"Source test video not found at {src_video}")

    cap = cv2.VideoCapture(str(src_video))
    if not cap.isOpened():
        pytest.skip(f"Could not open source video {src_video}")

    max_frames = 8
    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    for _ in range(max_frames):
        ok, fr = cap.read()
        if not ok or fr is None:
            break
        frames.append(fr)
    cap.release()

    if len(frames) == 0:
        pytest.skip("No frames available in source video to run test")

    # Apply smart center crop to each frame and write a temporary cropped video
    cropped_frames = [smart_crop.smart_center_crop(f) for f in frames]
    ch, cw = cropped_frames[0].shape[:2]

    out_path = tmp_path / 'cropped.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps), (cw, ch))
    for f in cropped_frames:
        writer.write(f)
    writer.release()

    # Run pose estimation on the cropped video
    keypoints_seq, frames_seq = estimate_pose.extract_pose_keypoints(str(out_path))

    # Basic sanity checks
    assert keypoints_seq.ndim == 3 and keypoints_seq.shape[1:] == (33, 3)
    assert frames_seq.ndim == 4 and frames_seq.shape[1:] == (3, 224, 224)
    assert keypoints_seq.shape[0] == frames_seq.shape[0]

    # Clipped keypoints should be within [0,1]
    assert np.isfinite(keypoints_seq).all()
    assert keypoints_seq.min() >= 0.0
    assert keypoints_seq.max() <= 1.0 + 1e-6
