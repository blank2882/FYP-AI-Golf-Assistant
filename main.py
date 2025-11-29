# main.py
import sys
import os
import json
from pathlib import Path
import numpy as np

from estimate_pose import extract_pose_and_swing_frames
from swingnet_inference import load_swingnet, run_swingnet, get_best_event_frames, save_debug_frames
from fault_detectors import (detect_early_extension,
                             detect_sway_or_slide,
                             detect_over_the_top,
                             detect_casting,
                             detect_chicken_wing,
                             detect_head_movement)
from llm_feedback import generate_feedback


OUTPUT_DIR = "pipeline_out"
SWINGNET_CKPT = "models/swingnet_1800.pth.tar"
SWINGNET_MIN_CONF = 0.10


def swing_was_detected(event_frames):
    required = {"Address", "Top", "Impact"}
    return required.issubset(event_frames.keys())


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main(video_path, seq_len=128, device="cpu"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n🎬 Step 1 — Extracting frames & pose keypoints…")
    keypoints_seq, frames_for_swingnet = extract_pose_and_swing_frames(video_path, seq_len=seq_len)

    if keypoints_seq is None:
        print("❌ ERROR: Could not extract video frames.")
        return

    print("Keypoints:", keypoints_seq.shape)
    print("SwingNet frames:", frames_for_swingnet.shape)

    save_debug_frames(frames_for_swingnet, out_dir=os.path.join(OUTPUT_DIR, "debug_frames"))


    print("\n⛳ Step 2 — Loading SwingNet")
    model = load_swingnet(SWINGNET_CKPT, device=device)


    print("\n🔎 Step 3 — Running SwingNet inference…")
    probs, preds = run_swingnet(model, frames_for_swingnet, device=device)


    print("\n📌 Step 4 — Selecting event frames…")
    event_frames = get_best_event_frames(probs, min_confidence=SWINGNET_MIN_CONF)
    print("Detected events:", dict(event_frames))

    save_json(dict(event_frames), os.path.join(OUTPUT_DIR, "event_frames.json"))


    if not swing_was_detected(event_frames):
        print("\n⚠ No valid full swing detected. Skipping LLM phase.")
        return


    print("\n🧠 Step 5 — Rule-based biomechanics analysis…")
    faults = []

    # early extension
    ee, ee_score = detect_early_extension(keypoints_seq, event_frames.get("Top"), event_frames.get("Impact"))
    if ee: faults.append(("early_extension", ee_score))

    # sway/slide
    sw, sw_score = detect_sway_or_slide(keypoints_seq, event_frames.get("Address"), event_frames.get("Impact"))
    if sw: faults.append((sw, sw_score))

    # OTT
    ott, ott_score = detect_over_the_top(keypoints_seq, event_frames.get("Top"))
    if ott: faults.append(("over_the_top", ott_score))

    # casting
    cast, cast_score = detect_casting(keypoints_seq, event_frames.get("Top"))
    if cast: faults.append(("casting", cast_score))

    # chicken wing
    wing, wing_score = detect_chicken_wing(keypoints_seq, event_frames.get("Impact"))
    if wing: faults.append(("chicken_wing", wing_score))

    # head movement
    head, head_score = detect_head_movement(keypoints_seq, event_frames.get("Address"), event_frames.get("Impact"))
    if head: faults.append(("head_movement", head_score))

    print("Biomechanics faults:", faults)
    save_json({"faults": faults}, os.path.join(OUTPUT_DIR, "rule_faults.json"))


    print("\n💬 Step 6 — Generating LLM feedback…")
    coaching = generate_feedback(event_frames, keypoints_seq)

    with open(os.path.join(OUTPUT_DIR, "coaching.txt"), "w", encoding="utf-8") as f:
        f.write(coaching)

    print("\n✅ Pipeline complete! Results saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <video>")
        sys.exit(1)

    video_path = sys.argv[1]
    main(video_path)
