"""SwingNet temporal segmentation helpers.

Given a sequence of cropped frames, this module predicts golf swing
event probabilities over time.
"""
from __future__ import annotations

import numpy as np
import torch

from golfdb.model import EventDetector

EVENT_LIST = [
    "Address",
    "Toe-Up",
    "Mid-Backswing",
    "Top",
    "Mid-Downswing",
    "Impact",
    "Follow-Through",
    "Finish",
]


class SwingNetInferer:
    """Wrapper around SwingNet model and inference utilities."""

    def __init__(self, weight_path, device: str | torch.device | None = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = EventDetector(
            pretrain=True,
            width_mult=1.0,
            lstm_layers=1,
            lstm_hidden=256,
            bidirectional=True,
            dropout=False,
        )

        save_dict = torch.load(weight_path, map_location=self.device)
        self.model.load_state_dict(save_dict["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    def run_window(self, window_frames: np.ndarray) -> np.ndarray:
        x = torch.from_numpy(window_frames).unsqueeze(0).float().to(self.device)
        with torch.no_grad():
            out = self.model(x)
            logits = out[0] if isinstance(out, (list, tuple)) else out
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
        return probs

    def run_sliding(self, frames_np: np.ndarray, model_seq_len: int = 64, stride: int | None = None) -> np.ndarray:
        # Sliding-window inference supports clips longer than the model sequence length.
        T = frames_np.shape[0]
        if stride is None:
            stride = max(1, model_seq_len // 2)

        if T <= model_seq_len:
            pad_n = model_seq_len - T
            last = frames_np[-1][None, ...]
            pad = np.repeat(last, pad_n, axis=0)
            frames_p = np.concatenate([frames_np, pad], axis=0)
            probs = self.run_window(frames_p)
            return probs[:T]

        agg = None
        counts = np.zeros((T,), dtype=np.int32)
        starts = list(range(0, max(1, T - model_seq_len + 1), stride))
        if starts[-1] != T - model_seq_len:
            starts.append(T - model_seq_len)
        for s in starts:
            # Average overlapping window predictions for smoother per-frame probabilities.
            e = s + model_seq_len
            window = frames_np[s:e]
            probs_w = self.run_window(window)
            if agg is None:
                C = probs_w.shape[1]
                agg = np.zeros((T, C), dtype=np.float32)
            for i in range(probs_w.shape[0]):
                idx = s + i
                if idx >= T:
                    break
                agg[idx] += probs_w[i]
                counts[idx] += 1
        counts = np.maximum(counts, 1)
        agg_probs = agg / counts[:, None]
        return agg_probs
