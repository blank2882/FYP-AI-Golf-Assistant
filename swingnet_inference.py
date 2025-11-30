# swingnet_inference.py
import torch
import numpy as np
from pathlib import Path

# EventDetector import (wmcnally/golfdb)
try:
    from golfdb.model import EventDetector
except Exception as e:
    raise ImportError("Could not import EventDetector from golfdb.model. Ensure golfdb repo is on PYTHONPATH.") from e

EVENT_LIST = [
    'Address', 'Toe-Up', 'Mid-Backswing', 'Top',
    'Mid-Downswing', 'Impact', 'Follow-Through', 'Finish'
]


def load_swingnet(model_path='models/swingnet_1800.pth.tar', device='cpu'):
    ckpt_path = Path(model_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"SwingNet checkpoint not found at {model_path}.\n"
            "Download a trained checkpoint (e.g. place 'models/swingnet_1800.pth.tar') or train one with 'golfdb/train.py'."
        )
    ckpt = torch.load(str(ckpt_path), map_location=device)
    sd = ckpt.get('model_state_dict') or ckpt.get('state_dict') or ckpt
    if isinstance(sd, dict):
        sd = {k.replace('module.', ''): v for k, v in sd.items()}
    # instantiate EventDetector with defaults used by the repo
    # width_mult=1.0, lstm_layers=1, lstm_hidden=256, bidirectional=True, dropout=False
    model = EventDetector(pretrain=False,
                          width_mult=1.0,
                          lstm_layers=1,
                          lstm_hidden=256,
                          bidirectional=True,
                          dropout=False)
    model.load_state_dict(sd, strict=False)
    model.to(device)
    model.eval()
    return model


def run_swingnet_window(model, window_frames, device='cpu'):
    """
    Run SwingNet on one window.
    window_frames: (W,3,224,224) float32
    returns: probs (W, C) numpy
    """
    dev = next(model.parameters()).device
    x = torch.from_numpy(window_frames).unsqueeze(0).float().to(dev)  # (1,W,3,H,W)
    with torch.no_grad():
        out = model(x)
        if isinstance(out, (list, tuple)):
            logits = out[0]
        else:
            logits = out
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()  # (W, C)
    return probs


def run_swingnet_sliding(model, frames_np, model_seq_len=64, stride=None, device='cpu'):
    """
    frames_np: (T,3,224,224)
    Run sliding windows of length model_seq_len and aggregate overlapping predictions.

    Returns:
      agg_probs: (T, C) aggregated probabilities (averaged over windows covering each frame)
    """
    T = frames_np.shape[0]
    if stride is None:
        stride = max(1, model_seq_len // 2)

    # If T <= model_seq_len: pad/repeat last frame to fit exactly one window
    if T <= model_seq_len:
        pad_n = model_seq_len - T
        last_frame = frames_np[-1][None, ...]
        pad_frames = np.repeat(last_frame, pad_n, axis=0)
        frames_p = np.concatenate([frames_np, pad_frames], axis=0)
        probs = run_swingnet_window(model, frames_p, device=device)  # (model_seq_len, C)
        probs = probs[:T]  # use first T frames
        return probs

    # sliding windows
    C = None
    agg = None
    counts = np.zeros((T,), dtype=np.int32)

    # windows start at 0..T-model_seq_len with stride
    starts = list(range(0, max(1, T - model_seq_len + 1), stride))
    # ensure last window covers end
    if starts[-1] != T - model_seq_len:
        starts.append(T - model_seq_len)

    for s in starts:
        e = s + model_seq_len
        window = frames_np[s:e]  # (model_seq_len,3,224,224)
        probs_w = run_swingnet_window(model, window, device=device)  # (model_seq_len, C)
        if agg is None:
            T_total = T
            C = probs_w.shape[1]
            agg = np.zeros((T_total, C), dtype=np.float32)
        # accumulate
        for i in range(model_seq_len):
            frame_idx = s + i
            if frame_idx >= T:
                break
            agg[frame_idx] += probs_w[i]
            counts[frame_idx] += 1

    # avoid divide by zero
    counts = np.maximum(counts, 1)
    agg_probs = agg / counts[:, None]
    return agg_probs


def run_swingnet(model, frames_np, device='cpu', model_seq_len=64, stride=None):
    """
    Convenience wrapper: run sliding-window SwingNet over `frames_np` and return
    probabilities and predictions per frame.
    frames_np: (T,3,224,224)
    returns: probs (T,C), preds (T,)
    """
    probs = run_swingnet_sliding(model, frames_np, model_seq_len=model_seq_len, stride=stride, device=device)
    preds = probs.argmax(axis=1)
    return probs, preds


def get_best_event_frames(probs, event_list=EVENT_LIST, min_confidence=0.12):
    """
    Choose best frame (peak) per event class, keep only if peak >= min_confidence.
    Returns ordered dict of event_name -> frame_idx sorted chronologically.
    """
    from collections import OrderedDict
    T, C = probs.shape
    event_frames = {}
    for cid in range(min(C, len(event_list))):
        col = probs[:, cid]
        best_idx = int(np.argmax(col))
        best_conf = float(np.max(col))
        if best_conf >= min_confidence:
            event_frames[event_list[cid]] = best_idx
    ordered = OrderedDict(sorted(event_frames.items(), key=lambda kv: kv[1]))
    return ordered


def save_debug_frames(frames_np, out_dir="pipeline_out/debug_frames", max_save=60):
    import os, cv2
    os.makedirs(out_dir, exist_ok=True)
    n = min(frames_np.shape[0], max_save)
    for i in range(n):
        img = (frames_np[i].transpose(1,2,0) * 255.0).astype('uint8')
        cv2.imwrite(f"{out_dir}/frame_{i:04d}.jpg", img)
    return out_dir
