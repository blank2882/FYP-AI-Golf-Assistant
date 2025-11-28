import cv2
import pathlib
import pytest
import smart_crop


def test_preprocess_on_test_video_reads_and_processes_frames():
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    video_path = repo_root / 'golfdb' / 'test_video.mp4'
    if not video_path.exists():
        pytest.skip(f"Test video not found at {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        pytest.skip(f"Could not open video {video_path}")

    processed_count = 0
    max_frames = 8
    try:
        for i in range(max_frames):
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            out = smart_crop.preprocess_frame(frame)
            # preprocess_frame should return a 256x256 uint8 image
            assert out.shape == (256, 256, 3)
            assert out.dtype == frame.dtype
            processed_count += 1
    finally:
        cap.release()

    assert processed_count > 0, "No frames were processed from the test video"
