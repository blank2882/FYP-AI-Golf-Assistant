from TTS.api import TTS
import tempfile
import os
import re
import wave
import shutil
import unicodedata
import logging

logger = logging.getLogger(__name__)

# Load once (faster)
tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")


def _sanitize_text_for_tts(text: str) -> str:
    if not text:
        return text
    # Normalize unicode and remove uncommon characters (em-dash, special bullets)
    s = unicodedata.normalize("NFKD", text)
    # remove markdown bold/italic and square-bracket mentions
    s = re.sub(r"\*\*|\*|__|~~", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    # replace long dashes with hyphen
    s = s.replace("–", "-").replace("—", "-")
    # collapse multiple whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Optionally remove any remaining non-ascii that could break the vocoder
    try:
        s = s.encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass
    return s


def _concatenate_wavs(wav_paths, out_path):
    if not wav_paths:
        raise ValueError("No wav files to concatenate")

    import audioop

    # Read target params from first file
    with wave.open(wav_paths[0], "rb") as w0:
        tgt_nchannels = w0.getnchannels()
        tgt_sampwidth = w0.getsampwidth()
        tgt_framerate = w0.getframerate()
        tgt_params = w0.getparams()
        frames_list = [w0.readframes(w0.getnframes())]

    # Normalize subsequent WAVs to target params
    for p in wav_paths[1:]:
        try:
            with wave.open(p, "rb") as w:
                nch = w.getnchannels()
                sw = w.getsampwidth()
                fr = w.getframerate()
                data = w.readframes(w.getnframes())

                # Convert sample width if needed
                if sw != tgt_sampwidth:
                    try:
                        data = audioop.lin2lin(data, sw, tgt_sampwidth)
                        sw = tgt_sampwidth
                    except Exception as e:
                        logger.debug("Failed to convert sample width for %s: %s", p, e)

                # Convert channels if needed
                if nch != tgt_nchannels:
                    try:
                        if nch == 2 and tgt_nchannels == 1:
                            data = audioop.tomono(data, tgt_sampwidth, 1, 0)
                        elif nch == 1 and tgt_nchannels == 2:
                            data = audioop.tostereo(data, tgt_sampwidth, 1, 1)
                        else:
                            # fallback: attempt to mono then stereo as needed
                            if tgt_nchannels == 1:
                                data = audioop.tomono(data, tgt_sampwidth, 1, 0)
                            else:
                                data = audioop.tostereo(data, tgt_sampwidth, 1, 1)
                        nch = tgt_nchannels
                    except Exception as e:
                        logger.debug("Failed to convert channels for %s: %s", p, e)

                # Resample if needed
                if fr != tgt_framerate:
                    try:
                        data, _ = audioop.ratecv(data, tgt_sampwidth, tgt_nchannels, fr, tgt_framerate, None)
                    except Exception as e:
                        logger.debug("Failed to resample %s from %d to %d: %s", p, fr, tgt_framerate, e)

                frames_list.append(data)
        except Exception as e:
            logger.warning("Skipping wav %s due to read/convert error: %s", p, e)

    # Write concatenated wav
    with wave.open(out_path, "wb") as out:
        out.setnchannels(tgt_nchannels)
        out.setsampwidth(tgt_sampwidth)
        out.setframerate(tgt_framerate)
        for f in frames_list:
            out.writeframes(f)


def generate_audio_feedback(text, output_path="feedback.wav"):
    text = _sanitize_text_for_tts(text)
    if not text:
        logger.warning("Empty text after sanitization; skipping TTS generation")
        return None

    # Split into sentences and group into chunks of ~250-300 chars to avoid tiny fragments
    sentences = re.split(r'(?<=[.!?])\s+', text)
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

    tmpdir = tempfile.mkdtemp(prefix="tts_chunks_")
    wav_paths = []
    try:
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(tmpdir, f"chunk_{i}.wav")
            try:
                # Use tts_to_file which handles file output
                tts.tts_to_file(text=chunk, file_path=chunk_path)
                wav_paths.append(chunk_path)
            except Exception as e:
                logger.warning("TTS chunk generation failed for chunk %d: %s", i, e)
                # try a simpler short fallback: speak the first 200 chars
                try:
                    short = chunk[:200]
                    tts.tts_to_file(text=short, file_path=chunk_path)
                    wav_paths.append(chunk_path)
                except Exception as e2:
                    logger.error("TTS fallback also failed: %s", e2)
                    # stop attempting further chunks
                    break

        if not wav_paths:
            logger.error("No TTS audio produced for any chunk")
            return None

        # concatenate into single file
        _concatenate_wavs(wav_paths, output_path)
        return output_path

    finally:
        # cleanup temporary files
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
