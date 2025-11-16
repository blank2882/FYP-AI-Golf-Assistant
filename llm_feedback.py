import requests
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _build_fallback_feedback(faults):
    # Simple, safe textual summary of faults for developer fallback
    if not faults:
        return "No faults detected. Swing looks good."

    parts = []
    events = faults.get("events")
    errors = faults.get("errors")

    if events:
        parts.append(f"Detected events: {events}")
    if errors:
        # If errors is a dict or list, make a compact readable string
        if isinstance(errors, dict):
            for k, v in errors.items():
                parts.append(f"{k}: {v}")
        else:
            parts.append(f"Errors: {errors}")

    parts.append("Suggested fix: practice tempo and keep your head steady. (Fallback advice)")
    return "\n".join(parts)


def generate_feedback(faults):
    # Convert swing faults into a readable prompt
    prompt = (
        "You are a professional golf coach. Explain these swing faults "
        "clearly and give actionable, simple corrections.\n\n"
        f"Swing faults detected: {faults}\n\n"
        "Give personalized advice as if talking directly to the golfer."
    )

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": prompt,
                "temperature": 0.4,
            },
            timeout=15,
        )
    except Exception as e:
        logger.warning("LLM server request failed: %s", e)
        return _build_fallback_feedback(faults)

    # Try to parse JSON robustly; some local servers stream NDJSON or return mixed text
    def _sanitize_text(txt: str) -> str:
        # Remove markdown code fences and surrounding quotes, then trim
        if not txt:
            return txt
        s = txt.strip()
        # remove enclosing triple-backtick fences
        if s.startswith("```") and s.endswith("```"):
            s = s[3:-3].strip()
        # remove single backticks
        s = s.replace('`', '')
        # remove wrapping triple quotes or stray leading/trailing quotes
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()
        return s

    try:
        data = response.json()
        # prefer keys named 'response' or 'text' or the whole body
        if isinstance(data, dict):
            for key in ("response", "text", "result", "output"):
                if key in data:
                    candidate = _sanitize_text(data[key])
                    if candidate and len(candidate) > 10:
                        return candidate
                    # save raw for debugging and continue to try other sources
                    break
            # fallback to stringifying the dict
            candidate = _sanitize_text(json.dumps(data))
            if candidate and len(candidate) > 10:
                return candidate
    except json.JSONDecodeError:
        # not a single JSON object — try to parse line-delimited JSON
        txt = response.text
        logger.debug("LLM raw response text: %s", txt[:1000])
        # save raw response for debugging
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            fname = log_dir / "llm_raw.txt"
            with open(fname, "a", encoding="utf-8") as fh:
                fh.write(f"--- {datetime.utcnow().isoformat()} ---\n")
                fh.write(txt)
                fh.write("\n\n")
        except Exception:
            logger.debug("Failed to write raw LLM response to logs/llm_raw.txt")

        # Many local LLM servers stream small JSON objects (NDJSON) with
        # incremental 'response' fragments. Assemble them in order.
        fragments = []
        done_seen = False
        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except Exception:
                # ignore non-JSON lines
                continue

            if isinstance(parsed, dict):
                # collect incremental response fragments
                if "response" in parsed and parsed["response"] is not None:
                    fragments.append(str(parsed["response"]))
                # if the server indicates the stream is done, stop collecting
                if parsed.get("done") is True:
                    done_seen = True
                    break

        if fragments:
            full = "".join(fragments)
            candidate = _sanitize_text(full)
            if candidate and len(candidate) > 5:
                return candidate
            # if sanitized candidate is too short, fall through to try raw text handling below

        # As a last resort, if the server returned plain text, return the text
        text = response.text.strip()
        if text:
            candidate = _sanitize_text(text)
            if candidate and len(candidate) > 10:
                return candidate
            # save raw and fallthrough to fallback
            try:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                fname = log_dir / "llm_raw.txt"
                with open(fname, "a", encoding="utf-8") as fh:
                    fh.write(f"--- {datetime.utcnow().isoformat()} (plain-text) ---\n")
                    fh.write(text)
                    fh.write("\n\n")
            except Exception:
                logger.debug("Failed to write plain LLM text to logs/llm_raw.txt")

    # If nothing worked, return a safe fallback
    logger.warning("Could not parse LLM response; returning fallback feedback")
    return _build_fallback_feedback(faults)
