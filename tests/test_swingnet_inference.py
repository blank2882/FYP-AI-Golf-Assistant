import numpy as np
import torch
import pytest
import importlib
import sys
import pathlib

# Ensure repo root is on sys.path so tests can import project modules
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import swingnet_inference as sni


def test_detect_events_with_dummy_model():
    # Create synthetic frames: 10 timesteps, 3x224x224
    T = 10
    frames = np.zeros((T, 3, 224, 224), dtype=np.float32)

    # Dummy model that predicts class = timestep % 7 for each frame
    class DummyModel(torch.nn.Module):
        def forward(self, x):
            # x shape: (1, T, C, H, W)
            batch_size, timesteps, C, H, W = x.shape
            out = torch.zeros(batch_size * timesteps, 9)
            for i in range(batch_size * timesteps):
                cls = i % len(sni.EVENT_LIST)
                out[i, cls] = 10.0  # large logit to force argmax
            return out

    model = DummyModel()
    event_frames, preds, probs = sni.detect_events(frames, model)

    # Ensure preds length equals T
    assert preds.shape[0] == T
    # Ensure probs shape matches (T, num_classes)
    assert probs.shape == (T, 9)
    # Each event in EVENT_LIST should have a first occurrence recorded
    for idx, name in enumerate(sni.EVENT_LIST):
        assert name in event_frames
        assert isinstance(event_frames[name], int)


def _import_estimate_pose():
    try:
        return importlib.import_module('estimate_pose')
    except Exception:
        return None


@pytest.mark.skipif(_import_estimate_pose() is None, reason="estimate_pose (mediapipe) not available")
def test_pipeline_frames_from_estimate_pose_to_swingnet_dummy_model(tmp_path):
    estimate_pose = _import_estimate_pose()

    # Build a short video clip from golfdb/test_video.mp4, reuse previous test pattern
    repo_root = tmp_path
    # We'll call estimate_pose on the repo's test video by resolving relative path from cwd
    import pathlib
    src = pathlib.Path('golfdb') / 'test_video.mp4'
    if not src.exists():
        pytest.skip(f"Source test video not found at {src}")

    # extract frames_seq using estimate_pose
    keypoints_seq, frames_seq = estimate_pose.extract_pose_keypoints(str(src))
    if frames_seq.size == 0:
        pytest.skip('estimate_pose returned no frames')

    # frames_seq shape is (N, 3, 224, 224) according to estimate_pose
    # Use a dummy model that marks the first frame as 'Impact' (index 5)
    class DummyModel2(torch.nn.Module):
        def forward(self, x):
            batch_size, timesteps, C, H, W = x.shape
            out = torch.zeros(batch_size * timesteps, 9)
            # Set high logit for class 5 at first frame
            out[0, 5] = 20.0
            return out

    model = DummyModel2()
    event_frames, preds, probs = sni.detect_events(frames_seq, model)

    # Expect 'Impact' to be present and mapped to frame 0
    assert 'Impact' in event_frames
    assert event_frames['Impact'] == 0
