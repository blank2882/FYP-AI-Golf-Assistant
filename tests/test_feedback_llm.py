import json
import subprocess
import types
import sys
import pathlib

# Ensure repo root is on sys.path so tests can import project modules
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import feedback_llm


def test_generate_feedback_calls_ollama_and_returns_output(monkeypatch):
    event_frames = {"Impact": 10, "Top": 5}
    keypoints = 64

    captured = {}

    def fake_run(args, input=None, capture_output=False, **kwargs):
        # record the call
        captured['args'] = args
        captured['input'] = input
        captured['capture_output'] = capture_output
        # return object with stdout attribute (bytes)
        return types.SimpleNamespace(stdout=b"This is fake feedback from the LLM.")

    monkeypatch.setattr(subprocess, 'run', fake_run)

    out = feedback_llm.generate_feedback(event_frames, keypoints)

    # verify return value is decoded stdout
    assert isinstance(out, str)
    assert "fake feedback" in out

    # verify subprocess.run was called with expected command
    assert captured['args'][0] == 'ollama'
    assert 'run' in captured['args']

    # verify the prompt contains the event_frames JSON and keypoints count
    prompt = captured['input'].decode('utf-8')
    assert json.dumps(event_frames, indent=2).splitlines()[0] in prompt
    assert f"({keypoints} pose keypoints per frame)" in prompt
