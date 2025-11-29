import json
import types
import subprocess
import shutil
import requests
import pytest

import llm_feedback as lf


def test_ollama_http_available_true(monkeypatch):
    class Resp:
        status_code = 200

    monkeypatch.setattr(requests, 'get', lambda url, timeout: Resp())
    assert lf.ollama_http_available(url="http://fake") is True


def test_keypoint_snippet_and_prompt():
    # Create a tiny keypoints_seq (T=3, N=5, 3)
    kp = [[[0.1, 0.2, 0.9]] * 5 for _ in range(3)]
    import numpy as np
    keypoints_seq = np.array(kp, dtype=float)
    event_frames = {'Top': 1}
    snippet = lf._keypoint_snippet_for_events(keypoints_seq, event_frames)
    assert 'Top' in snippet
    prompt = lf.build_grounded_prompt(event_frames, keypoints_seq, user_level='pro')
    assert 'Detected event frames' in prompt
    # prompt contains the event frame mapping (with indentation)
    assert '"Top"' in prompt


def test_generate_feedback_ollama_http(monkeypatch):
    # mock availability
    monkeypatch.setattr(lf, 'ollama_http_available', lambda url=None: True)

    class FakeResp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    def fake_post(url, json, timeout):
        return FakeResp({'response': 'OK'})

    monkeypatch.setattr(requests, 'post', fake_post)

    # call function
    kp = [[[0.1, 0.2, 0.9]] * 5 for _ in range(3)]
    import numpy as np
    keypoints_seq = np.array(kp, dtype=float)
    out = lf.generate_feedback_ollama_http({'Top':1}, keypoints_seq, model='m')
    assert out == 'OK'


def test_generate_feedback_ollama_cli(monkeypatch):
    # pretend ollama exists
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/ollama')

    class Proc:
        returncode = 0
        stdout = b'{"ok":true}'
        stderr = b''

    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: Proc())

    kp = [[[0.1, 0.2, 0.9]] * 5 for _ in range(3)]
    import numpy as np
    keypoints_seq = np.array(kp, dtype=float)
    out = lf.generate_feedback_ollama_cli({'Top':1}, keypoints_seq, model='m')
    assert isinstance(out, str)


def test_generate_feedback_prefers_http_but_falls_back(monkeypatch):
    # case: prefer http but http fails → fallback to CLI
    monkeypatch.setattr(lf, 'ollama_http_available', lambda : True)
    def raise_http(*args, **kwargs):
        raise RuntimeError('http fail')
    monkeypatch.setattr(lf, 'generate_feedback_ollama_http', raise_http)
    monkeypatch.setattr(lf, 'generate_feedback_ollama_cli', lambda ef, kp, model='m': 'CLI')

    kp = [[[0.1,0.2,0.9]]*5 for _ in range(3)]
    import numpy as np
    keypoints_seq = np.array(kp, dtype=float)
    out = lf.generate_feedback({'Top':1}, keypoints_seq, prefer_http=True)
    assert out == 'CLI'
