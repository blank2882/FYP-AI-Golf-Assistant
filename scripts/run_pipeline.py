"""Run smart crop -> estimate_pose pipeline and save outputs for inspection.

Usage:
    python scripts/run_pipeline.py --input golfdb/test_video.mp4 --out outputs

This script will:
 - read up to `--max-frames` frames from the input video
 - apply `smart_crop.smart_center_crop` to each frame
 - write a temporary cropped video to the output folder
 - call `estimate_pose.extract_pose_keypoints` on the cropped video
 - save `keypoints.npy` and `frames.npy` to the output folder
"""
import argparse
import pathlib
import sys
import cv2
import numpy as np
import torch
import json

# Ensure repository root is on sys.path so project modules can be imported
# when this script is executed from the repo root as `python scripts/run_pipeline.py`.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', help='Input video path', default='golfdb/test_video.mp4')
    parser.add_argument('--out', '-o', help='Output directory', default='outputs')
    parser.add_argument('--max-frames', '-n', type=int, default=128, help='Maximum number of frames to process')
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    input_path = pathlib.Path(args.input)
    if not input_path.is_absolute():
        input_path = repo_root / input_path

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import smart_crop
    except Exception as e:
        print('Failed to import smart_crop:', e)
        sys.exit(1)

    try:
        import estimate_pose
    except Exception as e:
        print('Failed to import estimate_pose (is mediapipe installed?):', e)
        sys.exit(1)

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print('Could not open input video:', input_path)
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames = []
    count = 0
    while count < args.max_frames:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frames.append(frame)
        count += 1
    cap.release()

    if len(frames) == 0:
        print('No frames read from input video; exiting')
        sys.exit(1)

    # Crop frames
    cropped = [smart_crop.smart_center_crop(f) for f in frames]
    ch, cw = cropped[0].shape[:2]

    cropped_video_path = out_dir / 'cropped.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(str(cropped_video_path), fourcc, float(fps), (cw, ch))
    for f in cropped:
        writer.write(f)
    writer.release()

    print(f'Wrote cropped video: {cropped_video_path} (frames={len(cropped)})')

    # Run pose estimation
    print('Running pose estimation...')
    keypoints, frames_seq = estimate_pose.extract_pose_keypoints(str(cropped_video_path))

    # Save outputs
    kp_path = out_dir / 'keypoints.npy'
    fr_path = out_dir / 'frames.npy'
    np.save(kp_path, keypoints)
    np.save(fr_path, frames_seq)

    print(f'Saved keypoints -> {kp_path} (shape={keypoints.shape})')
    print(f'Saved frames -> {fr_path} (shape={frames_seq.shape})')

    # --- SwingNet inference step ---
    try:
        import swingnet_inference as sni
    except Exception as e:
        sni = None
        print('swingnet_inference not available:', e)

    if sni is not None:
        # Try to load real model; if unavailable, fall back to a dummy model
        try:
            model = sni.load_swingnet()
            print('Loaded SwingNet model')
        except Exception as e:
            print('Could not load SwingNet model, using dummy model:', e)

            class _DummySwingNet(torch.nn.Module):
                def forward(self, x):
                    batch_size, timesteps, C, H, W = x.shape
                    out = torch.zeros(batch_size * timesteps, 9)
                    # Mark 'Impact' (index 5) on first frame
                    out[0, 5] = 20.0
                    return out

            model = _DummySwingNet()

        print('Running SwingNet inference...')
        event_frames, preds, probs = sni.detect_events(frames_seq, model)

        events_path = out_dir / 'events.json'
        with open(events_path, 'w') as fh:
            json.dump(event_frames, fh)
        np.save(out_dir / 'preds.npy', preds)
        np.save(out_dir / 'probs.npy', probs)

        print(f'Saved events -> {events_path}')
        print('Detected events:', event_frames)
    else:
        print('Skipping SwingNet step (module not available)')

    # Optional: save first few frames as JPEGs with landmarks overlay for quick inspection
    try:
        import matplotlib.pyplot as plt
        vis_dir = out_dir / 'vis'
        vis_dir.mkdir(exist_ok=True)
        for i in range(min(5, keypoints.shape[0])):
            img = np.transpose(frames_seq[i], (1,2,0)) * 255.0
            img = img.astype(np.uint8)[:,:,::-1]  # RGB->BGR
            kps = keypoints[i]
            for (x,y,v) in kps:
                cx = int(x * img.shape[1])
                cy = int(y * img.shape[0])
                cv2.circle(img, (cx, cy), 2, (0,255,0), -1)
            cv2.imwrite(str(vis_dir / f'frame_{i:02d}.jpg'), img)
        print(f'Wrote visualizations to {vis_dir}')
    except Exception:
        # matplotlib may not be installed; skip visualizations silently
        pass

if __name__ == '__main__':
    main()
