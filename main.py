# main.py
import sys
import os
import json
import numpy as np
from pathlib import Path

# local modules (assume these exist from prior steps)
from smart_crop import preprocess_frame   # unchanged
from estimate_pose import extract_pose_keypoints  # returns (keypoints_seq, frames_for_swingnet)
from swingnet_inference import load_swingnet, run_swingnet, get_best_event_frames, save_debug_frames
from feedback_llm import generate_feedback

# fault detectors (optional) — re-use your earlier rule-based detectors if present
try:
    from fault_detectors import (detect_early_extension, detect_sway_or_slide,
                                 detect_over_the_top, detect_casting,
                                 detect_chicken_wing, detect_head_movement)
    HAVE_FAULT_DETECTORS = True
except Exception:
    HAVE_FAULT_DETECTORS = False

OUTPUT_DIR = "pipeline_out"

def swing_was_detected(event_frames):
    # require Address, Top, Impact for a valid full swing
    required = {"Address", "Top", "Impact"}
    return required.issubset(set(event_frames.keys()))

def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def main(video_path, swingnet_ckpt="models/swingnet_1800.pth.tar", seq_len=64, device='cpu'):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("\n▶ Step 1: Extracting pose keypoints and SwingNet frames")
    keypoints_seq, frames_224 = extract_pose_keypoints(video_path)
    # frames_224 shape (T, 3, 224, 224) as float in [0,1] from extractor
    print("Extracted keypoints:", keypoints_seq.shape)
    print("Prepared frames for SwingNet:", frames_224.shape)

    # Save debug frames for visual inspection
    dbg_dir = save_debug_frames(frames_224, out_dir=os.path.join(OUTPUT_DIR, "debug_frames"), max_save=60)
    print("Saved debug frames to", dbg_dir)

    print("\n▶ Step 2: Load SwingNet")
    model = load_swingnet(model_path=swingnet_ckpt, device=device)

    print("\n▶ Step 3: Run SwingNet inference")
    probs, preds = run_swingnet(model, frames_224, device=device)
    print("Raw per-frame preds shape:", preds.shape)

    # Save raw probs and preds for debugging/threshold tuning
    try:
        np.save(os.path.join(OUTPUT_DIR, "probs.npy"), probs)
        np.save(os.path.join(OUTPUT_DIR, "preds.npy"), preds)
    except Exception as e:
        print("Warning: failed to save probs/preds:", e)

    print("\n▶ Step 4: Choose best event frames (peak confidence)")
    event_frames = get_best_event_frames(probs)
    print("Event frames (best peaks):", dict(event_frames))
    save_json(dict(event_frames), os.path.join(OUTPUT_DIR, "event_frames.json"))

    # Swing validity check
    if not swing_was_detected(event_frames):
        print("\n⚠️  No full swing detected — aborting LLM feedback to avoid hallucination.")
        # Still save outputs
        out = {
            "event_frames": dict(event_frames),
            "message": "No full swing detected. Please record a full swing (Address → Top → Impact)."
        }
        save_json(out, os.path.join(OUTPUT_DIR, "result.json"))
        print("Saved result to", os.path.join(OUTPUT_DIR, "result.json"))
        return out

    print("\n▶ Step 5: (Optional) Run rule-based fault detectors for corroboration")
    detected_faults = []
    try:
        if HAVE_FAULT_DETECTORS:
            ee, ee_score = detect_early_extension(keypoints_seq, top_frame=event_frames.get("Top"), impact_frame=event_frames.get("Impact"))
            if ee: detected_faults.append(("early_extension", ee_score))
            sway_label, sway_score = detect_sway_or_slide(keypoints_seq, address_frame=event_frames.get("Address"), impact_frame=event_frames.get("Impact"))
            if sway_label: detected_faults.append((sway_label, sway_score))
            ott, ott_score = detect_over_the_top(keypoints_seq, top_frame=event_frames.get("Top"))
            if ott: detected_faults.append(("over_the_top", ott_score))
            cast, cast_score = detect_casting(keypoints_seq, top_frame=event_frames.get("Top"))
            if cast: detected_faults.append(("casting", cast_score))
            ch, ch_score = detect_chicken_wing(keypoints_seq, impact_frame=event_frames.get("Impact"))
            if ch: detected_faults.append(("chicken_wing", ch_score))
            head, head_score = detect_head_movement(keypoints_seq, address_frame=event_frames.get("Address"), impact_frame=event_frames.get("Impact"))
            if head: detected_faults.append(("head_movement", head_score))
    except Exception as e:
        print("Fault detectors failed or not present:", e)

    print("Rule-based detected faults:", detected_faults)
    save_json({"rule_faults": detected_faults}, os.path.join(OUTPUT_DIR, "rule_faults.json"))

    print("\n▶ Step 6: Generate evidence-grounded coaching with Ollama")
    try:
        coaching = generate_feedback(event_frames, keypoints_seq, prefer_http=True, model="qwen2.5")
    except Exception as e:
        coaching = f"LLM failed: {e}"
    print("LLM generation done.")

    # Save final outputs
    result = {
        "event_frames": dict(event_frames),
        "rule_faults": detected_faults,
        "coaching": coaching
    }
    save_json(result, os.path.join(OUTPUT_DIR, "result.json"))

    # also save coaching text for easy viewing
    with open(os.path.join(OUTPUT_DIR, "coaching.txt"), "w", encoding="utf-8") as f:
        f.write(str(coaching))

    print("\nPipeline finished — results saved to", OUTPUT_DIR)
    return result

if __name__ == "__main__":
    video = sys.argv[1]
    main(video)
