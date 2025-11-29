#!/usr/bin/env python3
"""Debug runner: run SwingNet on a video and print per-class max confidences.

Usage:
  conda activate "..."; python tools/debug_swingnet_run.py ./data/videos_160/test_video.mp4
"""
import sys
from pathlib import Path
import numpy as np

# Ensure repo root is on sys.path when running from tools/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from estimate_pose import extract_pose_and_swing_frames
from swingnet_inference import load_swingnet, run_swingnet, EVENT_LIST


def main(video_path):
    keypoints_seq, frames = extract_pose_and_swing_frames(video_path, seq_len=128)
    if keypoints_seq is None:
        print('Failed to extract frames/keypoints')
        return
    print('Frames shape:', frames.shape)
    model = load_swingnet()
    probs, preds = run_swingnet(model, frames)
    print('probs shape:', probs.shape)
    T, C = probs.shape
    for cid, name in enumerate(EVENT_LIST):
        col = probs[:, cid]
        best_idx = int(np.argmax(col))
        best_conf = float(np.max(col))
        print(f"{cid:2d}: {name:15s}  best_idx={best_idx:3d}  best_conf={best_conf:.4f}")

    # print top frames by their max class confidence
    max_per_frame = probs.max(axis=1)
    topk = np.argsort(max_per_frame)[-10:][::-1]
    print('\nTop frames by max confidence:')
    for i in topk:
        print(f" frame {i:3d}: max_conf={max_per_frame[i]:.4f}, pred_class={preds[i]}")

    # save probs for offline inspection
    out = Path('pipeline_out')
    out.mkdir(exist_ok=True)
    np.save(out / 'swingnet_probs.npy', probs)
    print('Saved probs to', out / 'swingnet_probs.npy')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tools/debug_swingnet_run.py <video_path>')
        sys.exit(1)
    main(sys.argv[1])
