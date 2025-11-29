import os
import sys
import types
import tempfile
import numpy as np
import cv2

# Insert a lightweight fake `mediapipe` module so tests can run without the
# real dependency. The fake provides `solutions.pose.Pose` with a `.process()`
# that always returns no landmarks. This keeps behavior deterministic.
def _install_fake_mediapipe():
    if 'mediapipe' in sys.modules:
        return

    class FakePose:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def process(self, image):
            return types.SimpleNamespace(pose_landmarks=None)

    mp = types.ModuleType('mediapipe')
    solutions = types.SimpleNamespace()
    pose_ns = types.SimpleNamespace(Pose=FakePose)
    solutions.pose = pose_ns
    mp.solutions = solutions
    sys.modules['mediapipe'] = mp


_install_fake_mediapipe()

from estimate_pose import detect_if_good_frame, extract_pose_and_swing_frames


def make_frame(h, w, color=(0, 0, 0)):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def write_video(frames, path, fps=10):
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(path, fourcc, float(fps), (w, h))
    for f in frames:
        out.write(f)
    out.release()


def test_detect_if_good_frame_blank():
    # Blank frame should not be considered good framing (no landmarks)
    frame = make_frame(480, 640, color=(0, 0, 0))
    assert detect_if_good_frame(frame) is False


def test_extract_pose_and_swing_frames_on_blank_video(tmp_path):
    # Create a short blank video and ensure function returns well-shaped arrays
    frames = [make_frame(240, 320, color=(10, 20, 30)) for _ in range(6)]
    vid_path = str(tmp_path / "blank_test.avi")
    write_video(frames, vid_path, fps=5)

    keypoints_seq, frames_for_swingnet = extract_pose_and_swing_frames(vid_path)

    # Expect arrays with correct leading dimension equal to number of frames
    assert keypoints_seq is not None and frames_for_swingnet is not None
    T = len(frames)
    assert keypoints_seq.shape == (T, 33, 3)
    assert frames_for_swingnet.shape == (T, 3, 224, 224)

    # Blank frames produce no landmarks → all zeros in keypoints
    assert np.allclose(keypoints_seq, 0.0)

    # Frames for swingnet should be normalized floats in [0,1]
    assert frames_for_swingnet.dtype == np.float32
    assert frames_for_swingnet.min() >= 0.0
    assert frames_for_swingnet.max() <= 1.0
