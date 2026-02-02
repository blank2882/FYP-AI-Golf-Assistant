"""Legacy wrapper for biomech functions."""
from app.services.biomech import (  # noqa: F401
    detect_head_movement,
    detect_slide_or_sway,
    detect_sway,
    detect_early_extension,
    detect_over_the_top,
    compute_swing_metrics,
)
