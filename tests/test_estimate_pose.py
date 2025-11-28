import importlib
import pathlib
import cv2
import numpy as np
import pytest
import tempfile


try:
    estimate_pose = importlib.import_module('estimate_pose')
except Exception as e:
    estimate_pose = None


@pytest.mark.skipif(estimate_pose is None, reason="estimate_pose (or mediapipe) not available")
def test_extract_pose_keypoints_on_short_video(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    src_video = repo_root / 'golfdb' / 'test_video.mp4'
    if not src_video.exists():
        pytest.skip(f"Source test video not found at {src_video}")

    cap = cv2.VideoCapture(str(src_video))
    if not cap.isOpened():
        pytest.skip(f"Could not open source video {src_video}")

    # Read a small number of frames and write to a temporary short video to limit runtime
    max_frames = 8
    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    for i in range(max_frames):
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frames.append(frame)
    cap.release()

    if len(frames) == 0:
        pytest.skip("No frames available in source video to run test")

    out_path = tmp_path / 'short_test.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps), (width, height))
    for f in frames:
        writer.write(f)
    writer.release()

    # Run the pose extraction
    keypoints_seq, frames_seq = estimate_pose.extract_pose_keypoints(str(out_path))

    # Basic sanity checks
    assert keypoints_seq.ndim == 3 and keypoints_seq.shape[1:] == (33, 3)
    assert frames_seq.ndim == 4 and frames_seq.shape[1:] == (3, 224, 224)
    assert keypoints_seq.shape[0] == frames_seq.shape[0]

    # Frames_seq should be normalized between 0 and 1
    assert frames_seq.min() >= 0.0
    assert frames_seq.max() <= 1.0 + 1e-6

    # Keypoints should be finite and within a reasonable range.
    # MediaPipe can occasionally return coordinates slightly outside [0,1]
    # (when landmarks fall outside the image). Accept small out-of-bounds values.
    assert np.isfinite(keypoints_seq).all()
    xy = keypoints_seq[..., :2]
    vis = keypoints_seq[..., 2]
    # x,y should be roughly within [-0.1, 1.5]
    assert np.all((xy >= -0.1) & (xy <= 1.5))
    # visibility should be in [0, 1] (allow tiny numerical slack)
    assert np.all((vis >= 0.0) & (vis <= 1.05))
