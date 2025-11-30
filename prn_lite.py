import numpy as np
import warnings

# SciPy's savgol_filter can be unavailable if the conda environment's NumPy/SciPy
# versions are incompatible. Import it defensively and provide a no-op fallback
# so the rest of the pipeline can still run (smoothing will be skipped).
try:
    from scipy.signal import savgol_filter
    _HAS_SAVGOL = True
except Exception as e:
    savgol_filter = None
    _HAS_SAVGOL = False
    warnings.warn(
        "Could not import scipy.signal.savgol_filter (SciPy/NumPy version mismatch). "
        "Savitzky-Golay smoothing will be skipped. To enable it, install a compatible NumPy/SciPy: "
        "e.g. conda install -c conda-forge numpy=1.24 scipy",
        UserWarning,
    )

def _savgol_smooth_sequence(arr, window=9, poly=3):
    """Apply Savitzky-Golay along time axis (T, ...)"""
    T = arr.shape[0]
    if T < window:
        # reduce window if sequence is short
        w = max(3, T//2*2+1)  # make odd
        if _HAS_SAVGOL:
            try:
                return savgol_filter(arr, w, poly, axis=0)
            except Exception:
                return arr
        else:
            return arr
    if _HAS_SAVGOL:
        return savgol_filter(arr, window, poly, axis=0)
    return arr

def _ema(arr, alpha=0.3):
    """Exponential moving average along axis 0 (time)"""
    out = np.empty_like(arr)
    out[0] = arr[0]
    for t in range(1, arr.shape[0]):
        out[t] = alpha * arr[t] + (1-alpha) * out[t-1]
    return out

def fill_missing_by_median(kps_seq, max_gap=3):
    """
    kps_seq: (T, J, 3) with x,y,vis
    Fill short visibility gaps per joint by median interpolation
    """
    T, J, _ = kps_seq.shape
    out = kps_seq.copy()
    for j in range(J):
        vis = out[:, j, 2]
        xs = out[:, j, 0]
        ys = out[:, j, 1]
        # indices where visible
        good = np.where(vis > 0.35)[0]
        if len(good) == 0:
            continue
        # forward/backward fill small gaps
        for t in range(T):
            if vis[t] > 0.35:
                continue
            # find nearest visible on both sides
            left = good[good < t]
            right = good[good > t]
            if len(left) == 0 or len(right) == 0:
                continue
            gap = right[0] - left[-1]
            if gap <= max_gap:
                # linear interp
                a = left[-1]; b = right[0]
                frac = (t - a) / (b - a)
                xs[t] = (1-frac)*xs[a] + frac*xs[b]
                ys[t] = (1-frac)*ys[a] + frac*ys[b]
                vis[t] = (vis[a] + vis[b]) / 2.0
                out[t, j, 0] = xs[t]; out[t, j, 1] = ys[t]; out[t, j, 2] = vis[t]
    return out

def enforce_symmetry_and_clip(kps_seq):
    """
    Simple post-processing to keep values in [0,1] and enforce some symmetry
    We do not change topology — just clip and small blend for left/right joints if both visible.
    """
    out = kps_seq.copy()
    out[..., :2] = np.clip(out[..., :2], 0.0, 1.0)
    # If both shoulders visible, align slight symmetry by averaging x distance about center
    # indices: MediaPipe left_shoulder=11, right_shoulder=12 (approx.)
    try:
        L, R = 11, 12
        visL = out[:, L, 2]; visR = out[:, R, 2]
        mask = (visL > 0.3) & (visR > 0.3)
        for t in np.where(mask)[0]:
            midx = (out[t, L, 0] + out[t, R, 0]) / 2.0
            # small nudge toward mid if shoulders asymmetric
            out[t, L, 0] = 0.9*out[t, L, 0] + 0.1*midx
            out[t, R, 0] = 0.9*out[t, R, 0] + 0.1*midx
    except Exception:
        pass
    return out

def refine_keypoints_prn_lite(keypoints_seq, savgol_window=9, savgol_poly=3, ema_alpha=0.25):
    """
    Input: keypoints_seq (T, J, 3) normalized coords and visibility.
    Output: refined_keypoints_seq (T, J, 3)
    Steps:
      1) Fill short gaps
      2) Smooth x and y with savgol and EMA
      3) Reattach visibilities (smoothed)
      4) Enforce clipping/symmetry
    """
    k = keypoints_seq.copy()  # T,J,3
    T, J, _ = k.shape

    # 1) Fill small gaps
    k = fill_missing_by_median(k, max_gap=4)

    # Apply smoothing per-joint for x and y separately
    xy = k[..., :2].reshape(T, J*2)  # (T, 2J)
    # Savgol smoothing (time-series)
    try:
        xy_sg = _savgol_smooth_sequence(xy, window=savgol_window, poly=savgol_poly)
    except Exception:
        xy_sg = xy
    # EMA smoothing
    xy_ema = _ema(xy_sg, alpha=ema_alpha)
    xy_ema = xy_ema.reshape(T, J, 2)

    # Visibility smoothing (simple EMA on vis)
    vis = k[..., 2]
    vis_smooth = _ema(vis, alpha=ema_alpha)

    refined = np.zeros_like(k)
    refined[..., :2] = xy_ema
    refined[..., 2] = vis_smooth

    # enforce symmetry/clip
    refined = enforce_symmetry_and_clip(refined)
    return refined

# ------------------------------
# Event refinement helpers
# ------------------------------
def wrist_signal(keypoints_seq):
    """
    Returns wrist vertical position and speed signals:
      avg_wrist_y(t), avg_wrist_speed(t)
    MediaPipe indices: left_wrist ~ 15, right_wrist ~ 16 (best effort)
    """
    T = keypoints_seq.shape[0]
    # try common indices, fallback if absent
    if keypoints_seq.shape[1] > 16:
        Lw, Rw = 15, 16
    else:
        Lw, Rw = 9, 10  # fallback COCO-ish
    yL = keypoints_seq[:, Lw, 1]
    yR = keypoints_seq[:, Rw, 1]
    visL = keypoints_seq[:, Lw, 2]
    visR = keypoints_seq[:, Rw, 2]
    # use visible ones; if both invisible, returns nan which we'll handle
    y = np.where(visL > visR, yL, yR)
    # if both visible, average
    both = (visL > 0.3) & (visR > 0.3)
    y[both] = (yL[both] + yR[both]) / 2.0
    # invert y if coordinate system has y down (MediaPipe uses 0..1 from top)
    # For backswing top, wrists highest (smallest y) or largest? In MediaPipe, top often has smaller y (higher on image),
    # but depending on camera it might be reversed. We use raw values and find peaks accordingly by analyzing variance.
    # compute speed (finite diff)
    speed = np.zeros_like(y)
    speed[1:-1] = np.sqrt((y[2:] - y[:-2])**2) / 2.0
    speed[0] = speed[1]
    speed[-1] = speed[-2]
    return y, speed

def refine_events_with_keypoints(event_frames, refined_kps, max_window=30):
    """
    event_frames: ordered dict from SwingNet (event->frame)
    refined_kps: (T,J,3)
    Returns: reordered/adjusted event_frames (dict) with Top and Impact refined using wrist signals.
    Strategy:
      - Find Top: local extremum of wrist vertical position near SwingNet Top (search +/- max_window)
      - Find Impact: local maximum of wrist speed near SwingNet Impact
    """
    from collections import OrderedDict
    T = refined_kps.shape[0]
    # copy
    ev = dict(event_frames)
    # compute wrist signals
    y, speed = wrist_signal(refined_kps)
    # determine whether top should be min or max: check overall trend early->mid backswing
    # We'll assume Top is where wrist y is either global min or max in neighborhood; check both and pick which is more extreme.
    if "Top" in ev:
        t0 = int(ev["Top"])
        s = max(0, t0 - max_window); e = min(T-1, t0 + max_window)
        seg = y[s:e+1]
        if np.isnan(seg).all():
            # no change
            pass
        else:
            # choose extremum by absolute deviation from segment median
            med = np.nanmedian(seg)
            idx_min = np.nanargmin(seg)
            idx_max = np.nanargmax(seg)
            dev_min = abs(seg[idx_min] - med)
            dev_max = abs(seg[idx_max] - med)
            if dev_min >= dev_max:
                new_t = s + int(idx_min)
            else:
                new_t = s + int(idx_max)
            ev["Top"] = int(new_t)

    if "Impact" in ev:
        t0 = int(ev["Impact"])
        s = max(0, t0 - max_window); e = min(T-1, t0 + max_window)
        seg = speed[s:e+1]
        if np.isnan(seg).all():
            pass
        else:
            # impact approx - choose peak speed
            idx_peak = int(np.nanargmax(seg))
            new_t = s + idx_peak
            ev["Impact"] = int(new_t)

    # Optionally ensure chronological ordering: make events strictly increasing by reassigning if necessary
    ordered = OrderedDict(sorted(ev.items(), key=lambda kv: kv[1]))
    # enforce monotonic increasing by nudging tied frames forward by +1
    last = -1
    final = {}
    for k, v in ordered.items():
        v = int(v)
        if v <= last:
            v = last + 1
            if v >= T:
                v = T-1
        final[k] = v
        last = v
    return final
