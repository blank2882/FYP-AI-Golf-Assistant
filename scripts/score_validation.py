from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.pipeline import GolfAssistant
from app.services.temporal_seg import SwingNetInferer
from app.services.validation import (
    compute_likelihood_score,
    compute_motion_pattern_score,
    compute_pose_presence_ratio,
    compute_swingnet_confidence,
    validate_file_level,
    build_keypoint_array,
)


def score_video(path: Path) -> dict:
    file_ok, file_message, file_info = validate_file_level(str(path))
    if not file_ok:
        return {
            "file": str(path),
            "status": "file_fail",
            "message": file_message,
            "pose_presence": 0.0,
            "motion_pattern": 0.0,
            "swingnet_confidence": 0.0,
            "likelihood": 0.0,
        }

    assistant = GolfAssistant(video_path=str(path))
    metadata = assistant.run_detector(display=False)
    if not metadata:
        return {
            "file": str(path),
            "status": "no_pose",
            "message": "no metadata",
            "pose_presence": 0.0,
            "motion_pattern": 0.0,
            "swingnet_confidence": 0.0,
            "likelihood": 0.0,
        }

    pose_ratio = compute_pose_presence_ratio(metadata)
    collected_rgb, collected_frame_idxs, collected_keypoints = assistant.build_crops_from_metadata(metadata)
    if not collected_rgb:
        return {
            "file": str(path),
            "status": "no_crops",
            "message": "no crops",
            "pose_presence": pose_ratio,
            "motion_pattern": 0.0,
            "swingnet_confidence": 0.0,
            "likelihood": 0.0,
        }

    frames_np = assistant.frames_to_swingnet_np(collected_rgb)
    inferer = SwingNetInferer(assistant.weights_path)
    probs = inferer.run_sliding(frames_np, model_seq_len=64)

    confidences = []
    for c in range(probs.shape[1]):
        idx = int(probs[:, c].argmax())
        confidences.append(float(probs[idx, c]))

    swingnet_conf = compute_swingnet_confidence(confidences)
    kps = build_keypoint_array(collected_keypoints)
    motion_score, _ = compute_motion_pattern_score(
        kps,
        collected_frame_idxs,
        float(file_info.get("fps", 0.0)),
    )
    likelihood = compute_likelihood_score(pose_ratio, motion_score, swingnet_conf)

    return {
        "file": str(path),
        "status": "ok",
        "message": "",
        "pose_presence": pose_ratio,
        "motion_pattern": motion_score,
        "swingnet_confidence": swingnet_conf,
        "likelihood": likelihood,
    }


def scan_dir(dir_path: Path) -> list[dict]:
    if not dir_path.exists():
        return []
    videos = sorted([p for p in dir_path.iterdir() if p.suffix.lower() in {".mp4", ".mov"}])
    return [score_video(p) for p in videos]


def main():
    amateur_dir = ROOT / "data" / "amateur_swings"
    test_dir = ROOT / "data" / "test_videos"

    print("file,status,pose_presence,motion_pattern,swingnet_confidence,likelihood")
    for row in scan_dir(amateur_dir) + scan_dir(test_dir):
        print(
            f"{row['file']},{row['status']},{row['pose_presence']:.4f},"
            f"{row['motion_pattern']:.4f},{row['swingnet_confidence']:.4f},{row['likelihood']:.4f}"
        )


if __name__ == "__main__":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    main()
