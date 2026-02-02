"""Video upload and storage helpers."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.core import config


def create_run_dir() -> Path:
    run_id = uuid.uuid4().hex
    run_dir = config.OUTPUTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_upload(upload_file, dest_dir: Path | None = None) -> Path:
    if dest_dir is None:
        dest_dir = config.RAW_UPLOADS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload_file.filename).suffix or ".mp4"
    filename = f"{uuid.uuid4().hex}{suffix}"
    out_path = dest_dir / filename
    with out_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return out_path
