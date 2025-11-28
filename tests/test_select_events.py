import sys
import pathlib
import numpy as np

# Ensure project root is on sys.path so top-level modules can be imported
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from swingnet_inference import select_events_from_probs


def test_select_events_increasing():
    # Create synthetic per-frame probabilities for 7 classes over 30 frames.
    T = 30
    C = 7
    probs = np.zeros((T, C), dtype=float)

    # Create overlapping peaks: classes 0 and 1 both peak early, 2 and 3 mid,
    # 4..6 late. This simulates raw ties/conflicts that smoothing should resolve
    # while selection enforces strictly increasing frames.
    probs[2, 0] = 1.0
    probs[2, 1] = 0.9
    probs[10, 2] = 1.0
    probs[10, 3] = 0.95
    probs[18, 4] = 1.0
    probs[20, 5] = 1.0
    probs[20, 6] = 0.8

    # Add some background noise
    rng = np.random.RandomState(0)
    probs += rng.rand(T, C) * 0.01

    ev = select_events_from_probs(probs, smoothing_sigma=1.0, min_frame_separation=1)

    # Expect one entry per event and strictly increasing frames
    frames = [ev[name] for name in [
        'Address', 'Toe-Up', 'Mid-Backswing', 'Top',
        'Mid-Downswing', 'Impact', 'Follow-Through'
    ]]

    assert len(frames) == 7
    for i in range(1, len(frames)):
        assert frames[i] > frames[i - 1], f"frames not strictly increasing: {frames}"
