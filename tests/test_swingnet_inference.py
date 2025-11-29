import sys
import os
import tempfile
import numpy as np
import cv2
import pytest

# Skip tests if torch not available in this environment; they can be run in the
# project's conda env where torch is installed.
pytest.importorskip('torch')
import torch

# Provide a lightweight fake `golfdb.model.EventDetector` before importing
# `swingnet_inference` so the module import does not pull in the real heavy
# implementation (which requires additional binary dependencies).
import types


class _FakeEventDetector(torch.nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # register a dummy parameter so next(model.parameters()) works
        self.p = torch.nn.Parameter(torch.zeros(1))

    def forward(self, x):
        # x shape: (1, T, 3, H, W) -> produce logits shape (1, T, C)
        batch, T, C, H, W = x.shape
        # produce deterministic logits for testing: class 0 has higher score at frame 0
        logits = torch.zeros(batch, T, len(range(9)), dtype=torch.float32)
        for t in range(T):
            logits[:, t, :] = torch.linspace(0.1 + t * 0.01, 0.9 + t * 0.01, steps=9)
        return logits


fake_mod = types.ModuleType('golfdb.model')
fake_mod.EventDetector = _FakeEventDetector
sys.modules['golfdb.model'] = fake_mod

import swingnet_inference as sni


def test_get_best_event_frames_basic():
    # Create a probs matrix where each class peaks at different frames
    T = 10
    C = len(sni.EVENT_LIST)
    probs = np.zeros((T, C), dtype=float)
    for c in range(C):
        idx = min(T - 1, c * 1)
        probs[idx, c] = 0.5 + c * 0.01

    ordered = sni.get_best_event_frames(probs, min_confidence=0.1)
    # Should return an ordered dict with keys in increasing frame order
    assert isinstance(ordered, dict)
    assert len(ordered) == C
    last_idx = -1
    for v in ordered.values():
        assert v >= last_idx
        last_idx = v


def test_save_debug_frames_creates_files(tmp_path):
    T = 5
    frames = np.zeros((T, 3, 224, 224), dtype=np.float32)
    out_dir = str(tmp_path / "debug_out")
    returned = sni.save_debug_frames(frames, out_dir=out_dir, max_save=10)
    assert returned == out_dir
    # check files exist
    files = os.listdir(out_dir)
    assert len(files) == T


def test_run_swingnet_with_fake_model():
    # Create simple frames and run through run_swingnet with the fake model
    T = 8
    frames = np.random.rand(T, 3, 224, 224).astype('float32')
    model = _FakeEventDetector()
    probs, preds = sni.run_swingnet(model, frames)

    assert probs.shape[0] == T
    assert preds.shape[0] == T
    # probabilities should sum to 1 across classes
    sums = probs.sum(axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)


def test_load_swingnet_missing_checkpoint_raises():
    # Ensure missing checkpoint triggers FileNotFoundError
    with pytest.raises(FileNotFoundError):
        sni.load_swingnet(model_path='nonexistent_checkpoint.pth', device='cpu')
