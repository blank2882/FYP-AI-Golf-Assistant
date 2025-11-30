# main.py
import sys
import os
import json
from pathlib import Path
import numpy as np

from estimate_pose import extract_pose_and_swing_frames
from swingnet_inference import (load_swingnet, run_swingnet_sliding,
                                get_best_event_frames, save_debug_frames)
from fault_detectors import (detect_early_extension, detect_sway_or_slide,
                             detect_over_the_top, detect_casting,
                             detect_chicken_wing, detect_head_movement)
from llm_feedback import generate_feedback

# NEW: PRN-Lite
from prn_lite import refine_keypoints_prn_lite, refine_events_with_keypoints

OUTPUT_DIR = "pipeline_out"
SWINGNET_CKPT = "models/swingnet_1800.pth.tar"


def swing_was_detected(event_frames):
    required = {"Address", "Top", "Impact"}
    return required.issubset(set(event_frames.keys()))


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main(video_path, seq_len=None, device="cpu", model_seq_len=64, stride=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Step 1 — Read video, build two streams (swingnet frames + mediapipe crops)")
    keypoints_seq, frames_for_swingnet = extract_pose_and_swing_frames(video_path, seq_len=seq_len)

    if keypoints_seq is None or frames_for_swingnet is None:
        print("Failed to read video or no frames.")
        return

    print("Frames for SwingNet:", frames_for_swingnet.shape)
    print("Keypoints seq shape:", keypoints_seq.shape)

    # Save debug frames for inspection (first N)
    save_debug_frames(frames_for_swingnet, out_dir=os.path.join(OUTPUT_DIR, "debug_frames"))

    print("Step 2 — Load SwingNet")
    model = load_swingnet(SWINGNET_CKPT, device=device)

    print("Step 3 — Sliding window SwingNet inference (seq_len=%d)" % model_seq_len)
    agg_probs = run_swingnet_sliding(model, frames_for_swingnet, model_seq_len=model_seq_len, stride=stride, device=device)
    print("Aggregated probs shape:", agg_probs.shape)
    np.save(os.path.join(OUTPUT_DIR, "agg_probs.npy"), agg_probs)

    print("Step 4 — Peak selection for event frames (SwingNet peaks)")
    swingnet_event_frames = get_best_event_frames(agg_probs, min_confidence=0.10)
    print("SwingNet event frames:", dict(swingnet_event_frames))
    save_json(dict(swingnet_event_frames), os.path.join(OUTPUT_DIR, "swingnet_event_frames_raw.json"))

    # -------------------------
    # PRN-Lite: refine keypoints
    # -------------------------
    print("Step 4b — Refining MediaPipe keypoints with PRN-Lite smoothing...")
    refined_kps = refine_keypoints_prn_lite(keypoints_seq)
    np.save(os.path.join(OUTPUT_DIR, "refined_keypoints.npy"), refined_kps)

    # -------------------------
    # Event refinement using keypoints
    # -------------------------
    print("Step 4c — Refining SwingNet events with keypoint signals...")
    refined_events = refine_events_with_keypoints(swingnet_event_frames, refined_kps)
    print("Refined event frames:", refined_events)
    save_json(refined_events, os.path.join(OUTPUT_DIR, "event_frames_refined.json"))

    if not swing_was_detected(refined_events):
        print("No full swing detected. Saving partial results and aborting LLM.")
        save_json({"event_frames": dict(refined_events)}, os.path.join(OUTPUT_DIR, "result.json"))
        return

    print("Step 5 — Run rule-based detectors for corroboration (use refined keypoints & refined events)")
    faults = []
    ee, ee_score = detect_early_extension(refined_kps, top_frame=refined_events.get("Top"), impact_frame=refined_events.get("Impact"))
    if ee: faults.append(("early_extension", ee_score))
    label, score = detect_sway_or_slide(refined_kps, address_frame=refined_events.get("Address"), impact_frame=refined_events.get("Impact"))
    if label: faults.append((label, score))
    ott, ott_score = detect_over_the_top(refined_kps, top_frame=refined_events.get("Top"))
    if ott: faults.append(("over_the_top", ott_score))
    cast, cast_score = detect_casting(refined_kps, top_frame=refined_events.get("Top"))
    if cast: faults.append(("casting", cast_score))
    ch, ch_score = detect_chicken_wing(refined_kps, impact_frame=refined_events.get("Impact"))
    if ch: faults.append(("chicken_wing", ch_score))
    head, head_score = detect_head_movement(refined_kps, address_frame=refined_events.get("Address"), impact_frame=refined_events.get("Impact"))
    if head: faults.append(("head_movement", head_score))

    print("Rule-based faults:", faults)
    save_json({"rule_faults": faults}, os.path.join(OUTPUT_DIR, "rule_faults.json"))

    print("Step 6 — Generate evidence-grounded feedback via LLM (Ollama/OpenAI)")
    coaching = generate_feedback(refined_events, refined_kps, prefer_http=True, model="qwen2.5")
    print("LLM produced response (truncated):", str(coaching)[:300])

    result = {
        "event_frames": dict(refined_events),
        "rule_faults": faults,
        "coaching": coaching
    }
    save_json(result, os.path.join(OUTPUT_DIR, "result.json"))
    with open(os.path.join(OUTPUT_DIR, "coaching.txt"), "w", encoding="utf-8") as f:
        f.write(str(coaching))

    print("Pipeline complete. Results saved to", OUTPUT_DIR)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py path/to/video.mp4")
        sys.exit(1)
    video = sys.argv[1]
    main(video, seq_len=None, device="cpu", model_seq_len=64, stride=32)
