"""Video upload and storage helpers.

Provides small utility functions for storing uploads and trimming clips
to the swing interval.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import cv2

from app.core import config


def create_run_dir() -> Path:
    # Use a UUID folder per request so generated outputs never collide.
    run_id = uuid.uuid4().hex
    run_dir = config.OUTPUTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_upload(upload_file, dest_dir: Path | None = None) -> Path:
    # Persist FastAPI UploadFile stream to disk and return the saved path.
    if dest_dir is None:
        dest_dir = config.RAW_UPLOADS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload_file.filename).suffix or ".mp4"
    filename = f"{uuid.uuid4().hex}{suffix}"
    out_path = dest_dir / filename
    with out_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return out_path


def trim_video_by_frames(
    input_path: str | Path,
    start_frame: int,
    end_frame: int,
    output_dir: Path | None = None,
) -> Path | None:
    # Create a shorter clip between detected start/end frame indices.
    if end_frame <= start_frame:
        return None

    if output_dir is None:
        output_dir = config.TRIMMED_UPLOADS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    in_path = str(input_path)
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    filename = f"{uuid.uuid4().hex}.mp4"
    out_path = output_dir / filename
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_frame))
    frame_idx = int(start_frame)
    while cap.isOpened() and frame_idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    return out_path
