# swingnet_inference.py
import torch
import numpy as np
from pathlib import Path

# import EventDetector from golfdb repo (must be cloned next to this project or on PYTHONPATH)
try:
    from golfdb.model import EventDetector
except Exception as e:
    raise ImportError("Could not import EventDetector from golfdb.model. Clone wmcnally/golfdb and ensure it's on PYTHONPATH.") from e

EVENT_LIST = [
    'Address', 'Toe-Up', 'Mid-Backswing', 'Top',
    'Mid-Downswing', 'Impact', 'Follow-Through', 'Finish'
]

def load_swingnet(model_path='models/swingnet_1800.pth.tar', device='cpu'):
    ckpt_path = Path(model_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"SwingNet checkpoint not found at {model_path}.\n"
            "You can obtain a trained checkpoint by either: \n"
            "  1) Downloading a pre-trained SwingNet checkpoint and placing it at the path above (e.g. 'models/swingnet_1800.pth.tar').\n"
            "     The original GolfDB codebase may provide checkpoints: https://github.com/wmcnally/golfdb\n"
            "  2) Training a checkpoint locally using the included training script `golfdb/train.py` (requires torchvision and training data).\n"
            "If you only want to run the pipeline for debugging without a trained model, either skip loading SwingNet or provide a small dummy checkpoint.\n"
        )
    ckpt = torch.load(str(ckpt_path), map_location=device)
    # Official checkpoint stores keys in "model_state_dict" or "state_dict"
    sd = ckpt.get('model_state_dict') or ckpt.get('state_dict') or ckpt
    if isinstance(sd, dict):
        sd = {k.replace('module.', ''): v for k, v in sd.items()}
    # instantiate EventDetector with defaults used by the repo's training code
    # (width_mult=1.0, lstm_layers=1, lstm_hidden=256, bidirectional=True, dropout=False)
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

def run_swingnet(model, frames_np, device='cpu'):
    """
    frames_np: (T,3,224,224) float in [0,1]
    returns: probs (T, num_classes), preds (T,)
    """
    model_device = next(model.parameters()).device
    x = torch.from_numpy(frames_np).unsqueeze(0).float().to(model_device)  # (1,T,3,H,W)
    with torch.no_grad():
        out = model(x)
        if isinstance(out, (list, tuple)):
            logits = out[0]
        else:
            logits = out
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()  # (T, C)
        preds = probs.argmax(axis=1)
    return probs, preds

def get_best_event_frames(probs, event_list=EVENT_LIST, min_confidence=0.12):
    """
    Choose best frame (peak) per event class, keep only if peak >= min_confidence.
    Returns ordered dict of event_name -> frame_idx
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
