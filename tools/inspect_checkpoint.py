#!/usr/bin/env python3
"""Small utility to inspect a PyTorch checkpoint (keys and a few tensor shapes).

Run from the repo root, e.g.:
  conda activate "E:\year 3\FYP\prototype git\FYP-AI-Golf-Assistant\.conda"; python tools/inspect_checkpoint.py
"""
import sys
from pathlib import Path

try:
    import torch
except Exception as e:
    print('ERROR: torch not available:', e)
    sys.exit(2)

CKPT = Path('models/swingnet_1800.pth.tar')

if not CKPT.exists():
    print('Checkpoint not found at', CKPT)
    sys.exit(1)

try:
    ckpt = torch.load(str(CKPT), map_location='cpu')
except Exception as e:
    print('ERROR loading checkpoint:', e)
    raise

print('Loaded checkpoint type:', type(ckpt))

if isinstance(ckpt, dict):
    keys = list(ckpt.keys())
    print('Top-level keys:', keys)

    for candidate in ('model_state_dict', 'state_dict'):
        if candidate in ckpt:
            sd = ckpt[candidate]
            print(f"Found '{candidate}' with {len(sd)} entries")
            print('First 20 parameter keys and shapes:')
            for i, (name, v) in enumerate(sd.items()):
                shape = getattr(v, 'shape', None)
                print(f"  {i:2d}: {name} -> {shape}")
                if i >= 19:
                    break
            break
    else:
        print('No model_state_dict/state_dict found — printing sample top-level entries:')
        for i, (k, v) in enumerate(ckpt.items()):
            print(f"  {i:2d}: {k} -> {type(v)}")
            if i >= 19:
                break
else:
    print('Checkpoint is not a dict; repr (truncated):')
    print(repr(ckpt)[:1000])

print('\nDone.')
