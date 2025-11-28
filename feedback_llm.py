# feedback_llm.py
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

def _keypoint_snippet_for_events(keypoints_seq, event_frames, max_frames=5):
    """
    Build a small human-readable snippet of keypoints for each event.
    We'll include only x,y for visible points for a few frames around each event.
    """
    snippet = {}
    T = keypoints_seq.shape[0]
    for ev, idx in event_frames.items():
        idx = int(idx)
        start = max(0, idx - 1)
        end = min(T-1, idx + 1)
        snippet[ev] = keypoints_seq[start:end+1].tolist()
    return snippet

def build_grounded_prompt(event_frames, keypoints_seq, user_level="amateur"):
    """
    Build a prompt that constrains the LLM to use numeric evidence only.
    """
    snippet = _keypoint_snippet_for_events(keypoints_seq, event_frames)
    prompt = f"""
You are an evidence-driven golf swing analyst and teacher.

Inputs (all normalized coordinates 0..1):
1) Detected event frames (chronological)
{json.dumps({k:int(v) for k,v in event_frames.items()}, indent=2)}

2) Keypoint snippets (x,y,visibility) for frames near each detected event:
(only use these numeric values to justify faults)
{json.dumps(snippet, indent=2)}

Task:
- Examine the numeric keypoints and the event frame indices.
- Identify only the faults that are directly inferable from the keypoints (do not guess fitness/strength).
- For each fault found, provide:
   a) A one-line measurable description (e.g., "hip center moved up 0.08 normalized units between Top and Impact")
   b) One simple corrective cue (single sentence)
   c) One short drill (one line)
- If no clear faults are inferable, output a single short positive reinforcement sentence and one drill to practice consistency.

Constraints:
- NEVER invent body conditions (core strength, flexibility, injuries) unless you see direct evidence.
- Use degrees or normalized units when describing magnitudes.
- Keep responses short, factual, and actionable.

Respond as JSON:
{{"faults": [ {{ "name": "...", "evidence": "...", "cue": "...", "drill": "..." }} ], "summary": "..." }}
"""
    return prompt

def generate_feedback_ollama_http(event_frames, keypoints_seq, model="qwen2.5", url="http://localhost:11434"):
    if not ollama_http_available(url):
        raise RuntimeError("Ollama HTTP not available on localhost:11434")
    prompt = build_grounded_prompt(event_frames, keypoints_seq)
    payload = {"model": model, "prompt": prompt, "temperature": 0.0, "max_tokens": 400}
    resp = requests.post(url + "/api/generate", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # try common keys
    if isinstance(data, dict) and "response" in data:
        return data["response"]
    return json.dumps(data)

def generate_feedback_ollama_cli(event_frames, keypoints_seq, model="qwen2.5"):
    prompt = build_grounded_prompt(event_frames, keypoints_seq)
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama CLI not found on PATH")
    proc = subprocess.run(["ollama", "run", model], input=prompt.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("Ollama CLI failed: " + proc.stderr.decode("utf-8"))
    return proc.stdout.decode("utf-8")

def generate_feedback(event_frames, keypoints_seq, prefer_http=True, model="qwen2.5"):
    """
    event_frames: ordered dict or dict mapping event->frame
    keypoints_seq: np.array (T, J, 3)
    """
    if prefer_http and ollama_http_available():
        try:
            return generate_feedback_ollama_http(event_frames, keypoints_seq, model=model)
        except Exception as e:
            # fallback to CLI
            print("Ollama HTTP failed:", e, "falling back to CLI")
    return generate_feedback_ollama_cli(event_frames, keypoints_seq, model=model)
