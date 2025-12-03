import json
import requests
import shutil
import subprocess
import os

def ollama_http_available(url="http://localhost:11434"):
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
        end_idx = max(0, idx-1); e = min(num_frames-1, idx+1)
        snippet[ev] = kps[start_idx:end_idx+1].tolist()
    return snippet

def build_prompt(events, kps, faults):
    snippet = _kp_snippet_for_events(kps, events)
    prompt = f"""You are an evidence-based golf coach. Inputs:
1) Detected event frames (chronological): {json.dumps(events, indent=2)}
2) Keypoint snippets near each event (x,y,vis normalized): {json.dumps(snippet, indent=2)}
3) Rule-based faults detected: {json.dumps(faults, indent=2)}

Task:
- For each fault, provide a short measurable justification, a short coaching cue, and one drill.
- If no faults, provide one reinforcement statement and one improvement drill.
Return JSON: {{ "faults":[{{"name":"", "evidence":"", "cue":"", "drill":""}}], "summary":"" }}
Be concise and evidence-grounded. Do not fabricate data and do not include any text outside the JSON structure. Do not include special characters.
"""
    return prompt

def generate_feedback_ollama_http(events, kps, faults, url="http://localhost:11434", model="qwen2.5"):
    prompt = build_prompt(events, kps, faults)
    payload = {"model": model, "prompt": prompt, "temperature":0.0, "max_tokens":400}
    resp = requests.post(url + "/api/generate", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # try to parse response; Ollama HTTP returns 'response' or 'generated' depending on version
    if isinstance(data, dict):
        if "response" in data:
            return data["response"]
        if "generated" in data:
            return data["generated"]
    return json.dumps(data)

def generate_feedback_ollama_cli(events, kps, faults, model="qwen2.5"):
    prompt = build_prompt(events, kps, faults)
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama CLI not found")
    proc = subprocess.run(["ollama", "run", model], input=prompt.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("ollama CLI failed: " + proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout.decode("utf-8")

def generate_feedback(events, kps, faults, prefer_http=True, model="qwen2.5"):
    if prefer_http and ollama_http_available():
        try:
            return generate_feedback_ollama_http(events, kps, faults, model=model)
        except Exception as e:
            # fallback
            pass
    return generate_feedback_ollama_cli(events, kps, faults, model=model)
