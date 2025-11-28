# swingnet_inference.py
import torch
import numpy as np
from pathlib import Path

# Adjust this import path if your GolfDB repo is in a different folder
try:
    from golfdb.model import EventDetector
except Exception:
    # If the swingnet/golfdb repo isn't on PYTHONPATH, user must add it
    raise ImportError("Could not import EventDetector from golfdb.model. "
                      "Ensure wmcnally/golfdb is cloned and on PYTHONPATH.")

# Event list that corresponds to the training order (adjust if your model differs)
EVENT_LIST = [
    'Address', 'Toe-Up', 'Mid-Backswing', 'Top',
    'Mid-Downswing', 'Impact', 'Follow-Through', 'Finish'
]

def load_swingnet(model_path='models/swingnet_1800.pth.tar', device='cpu', lstm_layers=1,
                  width_mult=1.0, lstm_hidden=256):
    ckpt_path = Path(model_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"SwingNet checkpoint not found at {model_path}")
    ckpt = torch.load(str(ckpt_path), map_location=device)

    # try common keys, be permissive
    sd = ckpt.get('model_state_dict') or ckpt.get('state_dict') or ckpt
    # remove DataParallel prefix if present
    if isinstance(sd, dict):
        sd = {k.replace('module.', ''): v for k, v in sd.items()}

    # create model instance with defaults matching training config
    model = EventDetector(pretrain=False,
                          width_mult=width_mult,
                          lstm_layers=lstm_layers,
                          lstm_hidden=lstm_hidden)
    # load state dict with strict=False to allow slight mismatches
    model.load_state_dict(sd, strict=False)
    model.to(device)
    model.eval()
    return model

def run_swingnet(model, frames_np, device='cpu'):
    """
    frames_np: np.array (T, 3, 224, 224) float in [0,1]
    returns:
      probs: np.array (T, num_events)
      preds: np.array (T,) integer per-frame predicted class
    """
    model_device = next(model.parameters()).device
    x = torch.from_numpy(frames_np).unsqueeze(0).float().to(model_device)  # (1,T,3,H,W)
    with torch.no_grad():
        out = model(x)  # many EventDetector return (logits) with shape (1,T,num_classes)
        # handle tuples
        if isinstance(out, (list, tuple)):
            logits = out[0]
        else:
            logits = out
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()  # (T, num_classes)
        preds = probs.argmax(axis=1)
    return probs, preds

def get_best_event_frames(probs, event_list=EVENT_LIST, min_confidence=0.12):
    """
    For each event (class), pick the frame with the highest confidence.
    Only keep events whose peak confidence exceeds min_confidence.
    Returns an ordered dict (event_name -> frame_idx) sorted by frame index.
    """
    from collections import OrderedDict
    T, num_classes = probs.shape
    event_frames = {}
    for cid in range(min(num_classes, len(event_list))):
        col = probs[:, cid]
        best_idx = int(np.argmax(col))
        best_conf = float(np.max(col))
        if best_conf >= min_confidence:
            event_frames[event_list[cid]] = best_idx
    # sort chronologically
    ordered = OrderedDict(sorted(event_frames.items(), key=lambda kv: kv[1]))
    return ordered

def save_debug_frames(frames_np, out_dir="debug_frames", max_save=50):
    """
    Save first max_save frames to debug_frames/ for visual inspection.
    frames_np: (T,3,H,W), values 0..1
    """
    import os, cv2
    os.makedirs(out_dir, exist_ok=True)
    T = frames_np.shape[0]
    n = min(T, max_save)
    for i in range(n):
        img = (frames_np[i].transpose(1,2,0) * 255.0).astype('uint8')
        cv2.imwrite(os.path.join(out_dir, f"frame_{i:04d}.jpg"), img)
    return out_dir
