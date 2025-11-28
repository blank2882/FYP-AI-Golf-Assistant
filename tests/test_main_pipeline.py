import sys
import pathlib
import cv2
import numpy as np
import types
import json


def test_main_runs_with_short_video(monkeypatch, tmp_path):
    # ensure repo root importable
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import main

    # Prepare a short temp video (reuse frames from golfdb/test_video.mp4)
    src = repo_root / 'golfdb' / 'test_video.mp4'
    if not src.exists():
        pytest.skip('source test video missing')

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    for _ in range(8):
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    if len(frames) == 0:
        pytest.skip('no frames in source video')

    out_vid = tmp_path / 'short.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(str(out_vid), fourcc, float(fps), (width, height))
    for f in frames:
        writer.write(f)
    writer.release()

    # Monkeypatch swingnet_inference to avoid loading large model
    import swingnet_inference as sni

    def fake_load_swingnet(*args, **kwargs):
        return types.SimpleNamespace()

    def fake_detect_events(frames_seq, model):
        N = frames_seq.shape[0]
        preds = np.zeros(N, dtype=int)
        probs = np.zeros((N, 9), dtype=float)
        probs[:, 0] = 1.0
        return ({'Address': 0}, preds, probs)

    monkeypatch.setattr(sni, 'load_swingnet', fake_load_swingnet)
    monkeypatch.setattr(sni, 'detect_events', fake_detect_events)

    # Monkeypatch subprocess.run used by feedback_llm to avoid calling external LLM
    import subprocess

    def fake_run(cmd, input=None, capture_output=False, **kwargs):
        return types.SimpleNamespace(stdout=b"Test feedback output")

    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Run main with the short video
    main.main(str(out_vid))
