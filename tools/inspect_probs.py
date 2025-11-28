import numpy as np
import os
import json

out_dir = 'outputs'
results = {}
for fname in ['probs.npy', 'probs_smoothed.npy']:
    path = os.path.join(out_dir, fname)
    if not os.path.exists(path):
        results[fname] = {'exists': False}
        continue
    arr = np.load(path)
    # arr shape (T, num_classes) or (T,)
    stats = {}
    stats['shape'] = arr.shape
    if arr.ndim == 2:
        stats['max_per_class'] = arr.max(axis=0).tolist()
        stats['argmax_per_class'] = arr.argmax(axis=0).tolist()
        stats['global_max'] = float(arr.max())
        # top peaks per class
        top_per_class = []
        for c in range(arr.shape[1]):
            col = arr[:, c]
            idx = int(col.argmax())
            top_per_class.append({'class': c, 'idx': idx, 'value': float(col[idx])})
        stats['top_per_class'] = top_per_class
    else:
        stats['global_max'] = float(arr.max())
    results[fname] = stats

print(json.dumps(results, indent=2))
