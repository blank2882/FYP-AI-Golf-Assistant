# swingnet code inspired by https://github.com/wmcnally/golfdb
import torch
import numpy as np
from golfdb.model import EventDetector

EVENT_LIST = [
    'Address', 'Toe-Up', 'Mid-Backswing', 'Top',
    'Mid-Downswing', 'Impact', 'Follow-Through', 'Finish'
]

class SwingNetInferer:
    """Object-oriented wrapper around SwingNet model and inference utilities.

    Usage:
      inferer = SwingNetInferer(weight_path)
      probs = inferer.run_sliding(frames_np)

    The class keeps the loaded model and the chosen device as instance
    attributes so downstream code doesn't have to manage them.
    """

    def __init__(self, weight_path, device: str | torch.device | None = None):
        # choose device automatically if not provided
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        # instantiate the network architecture
        self.model = EventDetector(pretrain=True,
                                   width_mult=1.,
                                   lstm_layers=1,
                                   lstm_hidden=256,
                                   bidirectional=True,
                                   dropout=False)

        # load checkpoint to the chosen device
        save_dict = torch.load(weight_path, map_location=self.device)
        self.model.load_state_dict(save_dict['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

    def run_window(self, window_frames: np.ndarray) -> np.ndarray:
        """Run inference on a single window of frames.

        Args:
          window_frames: numpy array of shape (W,3,224,224) float32

        Returns:
          probs: numpy array of shape (W, C) with per-frame class probabilities
        """
        # convert to tensor and send to model device
        x = torch.from_numpy(window_frames).unsqueeze(0).float().to(self.device)  # (1,W,3,H,W)
        with torch.no_grad():
            out = self.model(x)
            logits = out[0] if isinstance(out, (list, tuple)) else out
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
        return probs

    def run_sliding(self, frames_np: np.ndarray, model_seq_len: int = 64, stride: int | None = None) -> np.ndarray:
        """Run sliding-window inference across a long sequence of frames.

        Args:
          frames_np: numpy array (T,3,224,224)
          model_seq_len: length of SwingNet input sequence
          stride: step between windows; defaults to half the seq_len

        Returns:
          agg_probs: numpy array (T, C) averaged over overlapping windows
        """
        T = frames_np.shape[0]
        if stride is None:
            stride = max(1, model_seq_len // 2)

        # short-circuit: pad if sequence shorter than model expects
        if T <= model_seq_len:
            pad_n = model_seq_len - T
            last = frames_np[-1][None, ...]
            pad = np.repeat(last, pad_n, axis=0)
            frames_p = np.concatenate([frames_np, pad], axis=0)
            probs = self.run_window(frames_p)
            return probs[:T]

        C = None
        agg = None
        counts = np.zeros((T,), dtype=np.int32)
        starts = list(range(0, max(1, T - model_seq_len + 1), stride))
        if starts[-1] != T - model_seq_len:
            starts.append(T - model_seq_len)
        for s in starts:
            e = s + model_seq_len
            window = frames_np[s:e]
            probs_w = self.run_window(window)  # (model_seq_len, C)
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


# Backwards-compatible convenience wrappers (callable like before)
def load_swingnet(weight_path, device: str | torch.device | None = None):
    """Return a `SwingNetInferer` instance (compat wrapper)."""
    return SwingNetInferer(weight_path, device=device)


def run_swingnet_window(inferer: SwingNetInferer, window_frames, device='cpu'):
    """Compatibility wrapper: run window using instance or model-like arg."""
    if isinstance(inferer, SwingNetInferer):
        return inferer.run_window(window_frames)
    # if a raw model was passed, emulate previous behaviour
    dev = next(inferer.parameters()).device
    x = torch.from_numpy(window_frames).unsqueeze(0).float().to(dev)
    with torch.no_grad():
        out = inferer(x)
        logits = out[0] if isinstance(out, (list, tuple)) else out
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
    return probs


def run_swingnet_sliding(inferer, frames_np, model_seq_len=64, stride=None, device='cpu'):
    """Compatibility wrapper: accepts either a SwingNetInferer instance or the old model."""
    if isinstance(inferer, SwingNetInferer):
        return inferer.run_sliding(frames_np, model_seq_len=model_seq_len, stride=stride)
    # otherwise assume inferer is the old style model and fallback to previous implementation
    T = frames_np.shape[0]
    if stride is None:
        stride = max(1, model_seq_len // 2)
    if T <= model_seq_len:
        pad_n = model_seq_len - T
        last = frames_np[-1][None, ...]
        pad = np.repeat(last, pad_n, axis=0)
        frames_p = np.concatenate([frames_np, pad], axis=0)
        probs = run_swingnet_window(inferer, frames_p, device=device)
        return probs[:T]
    C = None
    agg = None
    counts = np.zeros((T,), dtype=np.int32)
    starts = list(range(0, max(1, T - model_seq_len + 1), stride))
    if starts[-1] != T - model_seq_len:
        starts.append(T - model_seq_len)
    for s in starts:
        e = s + model_seq_len
        window = frames_np[s:e]
        probs_w = run_swingnet_window(inferer, window, device=device)  # (model_seq_len, C)
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