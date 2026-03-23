from __future__ import annotations

from pathlib import Path

# Resolve project root from this file location so paths work regardless of launch folder.
BASE_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BASE_DIR / "app"

# Input and output folders used during request processing.
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
RAW_UPLOADS_DIR = UPLOADS_DIR / "raw"
TRIMMED_UPLOADS_DIR = UPLOADS_DIR / "trimmed"

OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUT_METRICS_DIR = OUTPUTS_DIR / "metrics"
OUTPUT_AUDIO_DIR = OUTPUTS_DIR / "feedback_audio"

# Model assets live in the existing root-level folders
ROOT_MODELS_DIR = BASE_DIR / "models"
GOLFDB_DIR = BASE_DIR / "golfdb"
GOLFDB_MODELS_DIR = GOLFDB_DIR / "models"

MEDIAPIPE_OBJ_MODEL = ROOT_MODELS_DIR / "efficientdet_lite2.tflite"
MEDIAPIPE_POSE_MODEL = ROOT_MODELS_DIR / "pose_landmarker_heavy.task"
SWINGNET_WEIGHTS = GOLFDB_MODELS_DIR / "swingnet_1800.pth.tar"

# Downscale factor for detector input (0.75 preserves accuracy while reducing runtime)
DETECTION_INPUT_SCALE = 0.65


def ensure_directories() -> None:
    # Create all runtime directories if they do not exist (safe to call repeatedly).
    for path in [
        UPLOADS_DIR,
        RAW_UPLOADS_DIR,
        TRIMMED_UPLOADS_DIR,
        OUTPUTS_DIR,
        OUTPUT_METRICS_DIR,
        OUTPUT_AUDIO_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
