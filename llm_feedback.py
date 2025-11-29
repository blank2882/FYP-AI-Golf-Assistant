# llm_feedback.py
import json
import shutil
import requests
import subprocess

def ollama_http_available(url="http://localhost:11434"):
    try:
        r = requests.get(url + "/ping", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False

def _keypoint_snippet_for_events(keypoints_seq, event_frames):
    snippet = {}
    T = keypoints_seq.shape[0]
    for ev, idx in event_frames.items():
        idx = int(idx)
        start = max(0, idx - 1)
        end = min(T-1, idx + 1)
        snippet[ev] = keypoints_seq[start:end+1].tolist()
    return snippet

def build_grounded_prompt(event_frames, keypoints_seq, user_level="amateur"):
    snippet = _keypoint_snippet_for_events(keypoints_seq, event_frames)
    prompt = f"""
You are an evidence-driven golf swing analyst.

Inputs (normalized coordinates 0..1):
1) Detected event frames (chronological)
{json.dumps({k:int(v) for k,v in event_frames.items()}, indent=2)}

2) Keypoint snippets (x,y,visibility) for frames near each detected event:
{json.dumps(snippet, indent=2)}

Task:
- Identify only faults directly inferable from the numeric keypoints.
- For each fault provide:
  a) Measurable description (use normalized units / degrees)
  b) One concise corrective cue
  c) One short drill

If no faults are clear, return a short reinforcement and one drill.

Return output as JSON:
{{"faults":[{{"name":"...", "evidence":"...", "cue":"...", "drill":"..."}}, ...], "summary":"..."}}
"""
    return prompt

def generate_feedback_ollama_http(event_frames, keypoints_seq, model="qwen2.5", url="http://localhost:11434"):
    if not ollama_http_available(url):
        raise RuntimeError("Ollama HTTP not available")
    prompt = build_grounded_prompt(event_frames, keypoints_seq)
    payload = {"model": model, "prompt": prompt, "temperature": 0.0, "max_tokens": 400}
    resp = requests.post(url + "/api/generate", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "response" in data:
        return data["response"]
    return json.dumps(data)

def generate_feedback_ollama_cli(event_frames, keypoints_seq, model="qwen2.5"):
    prompt = build_grounded_prompt(event_frames, keypoints_seq)
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama CLI not found")
    proc = subprocess.run(["ollama", "run", model], input=prompt.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("Ollama CLI failed: " + proc.stderr.decode("utf-8"))
    return proc.stdout.decode("utf-8")

def generate_feedback(event_frames, keypoints_seq, prefer_http=True, model="qwen2.5"):
    if prefer_http and ollama_http_available():
        try:
            return generate_feedback_ollama_http(event_frames, keypoints_seq, model=model)
        except Exception:
            pass
    return generate_feedback_ollama_cli(event_frames, keypoints_seq, model=model)
