"""LLM feedback generation (Ollama)."""
from __future__ import annotations

import json
import requests
import shutil
import subprocess


def ollama_http_available(url: str = "http://localhost:11434") -> bool:
    try:
        r = requests.get(url + "/ping", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def _kp_snippet_for_events(kps, events):
    num_frames = kps.shape[0]
    snippet = {}
    for ev, idx in events.items():
        start_idx = int(idx)
        end_idx = max(0, idx - 1)
        e = min(num_frames - 1, idx + 1)
        snippet[ev] = kps[start_idx : end_idx + 1].tolist()
    return snippet


def build_prompt(events, kps, faults):
    snippet = _kp_snippet_for_events(kps, events)
    prompt = f"""You are an evidence-based golf coach. Inputs:
1) Detected event frames (chronological): {json.dumps(events, indent=2)}
2) Keypoint snippets near each event (x,y,vis normalized): {json.dumps(snippet, indent=2)}
3) Rule-based faults detected: {json.dumps(faults, indent=2)}

Task:
- For each fault, write 2-3 short sentences: (1) a concise, evidence-based justification (why this is a problem), (2) a short coaching cue (one short sentence), and (3) one short drill (one sentence).
- If there are no faults, write one reinforcement sentence and one short improvement drill.

Response format requirements (IMPORTANT):
- Return plain English sentences only. Do NOT return JSON, code fences, or symbolic markup.
- Keep the entire response under 200 words and use short, clear sentences suitable for text-to-speech.
- Avoid long numeric sequences; round numeric evidence to two decimals if needed.

Example (acceptable):
"Head movement: Excessive head movement during the downswing reduces transfer of energy. Cue: Keep your head steady and eyes on the ball. Drill: Practice half-swings while holding a coin on your head."

Be concise, evidence-grounded, and avoid fabricating data.
"""
    return prompt


def generate_feedback_ollama_http(events, kps, faults, url: str = "http://localhost:11434", model: str = "qwen2.5"):
    prompt = build_prompt(events, kps, faults)
    payload = {"model": model, "prompt": prompt, "temperature": 0.0, "max_tokens": 400}
    resp = requests.post(url + "/api/generate", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        if "response" in data:
            return data["response"]
        if "generated" in data:
            return data["generated"]
    return json.dumps(data)


def generate_feedback_ollama_cli(events, kps, faults, model: str = "qwen2.5"):
    prompt = build_prompt(events, kps, faults)
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama CLI not found")
    proc = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError("ollama CLI failed: " + proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout.decode("utf-8")


def generate_feedback(events, kps, faults, prefer_http: bool = True, model: str = "qwen2.5"):
    if prefer_http and ollama_http_available():
        try:
            return generate_feedback_ollama_http(events, kps, faults, model=model)
        except Exception:
            pass
    return generate_feedback_ollama_cli(events, kps, faults, model=model)
