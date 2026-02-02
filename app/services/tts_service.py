"""Text-to-speech service wrapper."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import unicodedata
import wave

from TTS.api import TTS

logger = logging.getLogger(__name__)

tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")


def _sanitize_text_for_tts(text: str) -> str:
    if not text:
        return text
    s = unicodedata.normalize("NFKD", text)
    s = re.sub(r"```[a-zA-Z0-9_+-]*\n", "", s)
    s = s.replace("```", "")
    s = re.sub(r"\*\*|\*|__|~~", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    try:
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", s)
        if m:
            jtext = m.group(0)
            try:
                payload = json.loads(jtext)
                out_parts = []
                if isinstance(payload, dict):
                    faults = payload.get("faults") or payload.get("errors")
                    if faults and isinstance(faults, list):
                        for f in faults:
                            name = f.get("name") or f.get("fault") or "Fault"
                            evidence = f.get("evidence") or f.get("desc") or ""
                            cue = f.get("cue") or ""
                            drill = f.get("drill") or f.get("exercise") or ""
                            if name:
                                out_parts.append(f"Fault: {name}.")
                            if evidence:
                                out_parts.append(f"Evidence: {evidence}.")
                            if cue:
                                out_parts.append(f"Cue: {cue}.")
                            if drill:
                                out_parts.append(f"Drill: {drill}.")
                    summary = payload.get("summary") or payload.get("advice")
                    if summary:
                        out_parts.append(f"Summary: {summary}.")
                if not out_parts:
                    s = re.sub(r"[{}\[\]\"']", "", jtext)
                else:
                    s = " ".join(out_parts)
            except Exception:
                s = s
    except Exception:
        pass

    s = re.sub(r"[{}\[\]<>\"\\]", " ", s)

    def _round_float_match(m):
        try:
            v = float(m.group(0))
            return f"{v:.2f}"
        except Exception:
            return m.group(0)

    s = re.sub(r"\d+\.\d{4,}", _round_float_match, s)

    try:
        s = s.encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass

    s = re.sub(r"[.]{2,}", ".", s)
    s = re.sub(r"[!]{2,}", "!", s)
    s = re.sub(r"[?]{2,}", "?", s)
    s = re.sub(r"\s+[.!,?]\s+", ". ", s)
    s = re.sub(r"(?m)^[A-Za-z][A-Za-z0-9 _\-]{0,40}:\s*", "", s)
    s = re.sub(r"\([^\)]{0,100}\)", "", s)
    return s


def _concatenate_wavs(wav_paths, out_path):
    if not wav_paths:
        raise ValueError("No wav files to concatenate")

    import audioop

    with wave.open(wav_paths[0], "rb") as w0:
        tgt_nchannels = w0.getnchannels()
        tgt_sampwidth = w0.getsampwidth()
        tgt_framerate = w0.getframerate()
        frames_list = [w0.readframes(w0.getnframes())]

    for p in wav_paths[1:]:
        try:
            with wave.open(p, "rb") as w:
                nch = w.getnchannels()
                sw = w.getsampwidth()
                fr = w.getframerate()
                data = w.readframes(w.getnframes())

                if sw != tgt_sampwidth:
                    try:
                        data = audioop.lin2lin(data, sw, tgt_sampwidth)
                        sw = tgt_sampwidth
                    except Exception:
                        pass

                if nch != tgt_nchannels:
                    try:
                        if nch == 2 and tgt_nchannels == 1:
                            data = audioop.tomono(data, tgt_sampwidth, 1, 0)
                        elif nch == 1 and tgt_nchannels == 2:
                            data = audioop.tostereo(data, tgt_sampwidth, 1, 1)
                        else:
                            if tgt_nchannels == 1:
                                data = audioop.tomono(data, tgt_sampwidth, 1, 0)
                            else:
                                data = audioop.tostereo(data, tgt_sampwidth, 1, 1)
                        nch = tgt_nchannels
                    except Exception:
                        pass

                if fr != tgt_framerate:
                    try:
                        data, _ = audioop.ratecv(data, tgt_sampwidth, tgt_nchannels, fr, tgt_framerate, None)
                    except Exception:
                        pass
                frames_list.append(data)
        except Exception:
            logger.warning("Skipping wav %s due to read/convert error", p)

    with wave.open(out_path, "wb") as out:
        out.setnchannels(tgt_nchannels)
        out.setsampwidth(tgt_sampwidth)
        out.setframerate(tgt_framerate)
        for f in frames_list:
            out.writeframes(f)


def generate_audio_feedback(text: str, output_path: str) -> str | None:
    text = _sanitize_text_for_tts(text)
    if not text:
        logger.warning("Empty text after sanitization; skipping TTS generation")
        return None
    tmpdir = tempfile.mkdtemp(prefix="tts_chunks_")

    single_path = os.path.join(tmpdir, "single.wav")
    try:
        tts.tts_to_file(text=text, file_path=single_path)
        opened = False
        last_exc = None
        for _ in range(10):
            try:
                with wave.open(single_path, "rb") as w:
                    nframes = w.getnframes()
                    if nframes > 0:
                        opened = True
                        break
            except Exception as e:
                last_exc = e
                import time

                time.sleep(0.15)

        if opened:
            for _ in range(6):
                try:
                    shutil.move(single_path, output_path)
                    break
                except PermissionError:
                    import time

                    time.sleep(0.15)
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
            return output_path
        logger.warning("Single-call TTS produced unreadable WAV: %s", last_exc)
    except Exception as e:
        logger.info("Single-call TTS failed, falling back to chunking: %s", e)

    sentences = re.split(r"(?<=[.!?])\s+", text)
    filtered = []
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        if re.fullmatch(r"[\W_]+", s_strip) or len(s_strip) <= 2:
            continue
        filtered.append(s_strip)
    if not filtered:
        logger.warning("All sentences filtered out as punctuation/short; skipping TTS")
        return None
    sentences = filtered
    chunks = []
    cur = ""
    for s in sentences:
        if not s.strip():
            continue
        if len(cur) + len(s) + 1 <= 300:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = s.strip()
    if cur:
        chunks.append(cur)

    MAX_CHUNKS = 4
    TARGET_CHUNK_CHARS = 200
    if len(chunks) > MAX_CHUNKS:
        merged = ["" for _ in range(MAX_CHUNKS)]
        for c in chunks:
            lens = [len(m) for m in merged]
            idx = int(lens.index(min(lens)))
            merged[idx] = (merged[idx] + " " + c).strip()
        final = []
        cur = ""
        for m in merged:
            if not m:
                continue
            if len(cur) + len(m) + 1 <= TARGET_CHUNK_CHARS:
                cur = (cur + " " + m).strip()
            else:
                if cur:
                    final.append(cur)
                cur = m
        if cur:
            final.append(cur)
        if len(final) > MAX_CHUNKS:
            merged2 = ["" for _ in range(MAX_CHUNKS)]
            for i, c in enumerate(final):
                merged2[i % MAX_CHUNKS] += (" " + c).strip()
            chunks = [m.strip() for m in merged2 if m.strip()]
        else:
            chunks = final

    wav_paths = []
    try:
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(tmpdir, f"chunk_{i}.wav")
            try:
                tts.tts_to_file(text=chunk, file_path=chunk_path)
                wav_paths.append(chunk_path)
            except Exception:
                try:
                    short = chunk[:200]
                    tts.tts_to_file(text=short, file_path=chunk_path)
                    wav_paths.append(chunk_path)
                except Exception:
                    break

        if not wav_paths:
            return None

        _concatenate_wavs(wav_paths, output_path)
        return output_path

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
