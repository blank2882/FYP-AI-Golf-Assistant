from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel


class FaultItem(BaseModel):
    # One detected swing fault with its raw severity score and confidence.
    name: str
    score: float
    confidence: float  # 0-1 confidence score (how confident the detection is)


class AnalysisResponse(BaseModel):
    # Full response contract returned by /api/analyze.
    job_id: str
    annotated_video: Optional[str]
    json_path: Optional[str]
    feedback_text: str
    audio_feedback: Optional[str]
    event_frames: List[int]
    confidences: List[float]
    faults: List[FaultItem]
    metrics: dict
    valid: bool = True
    validation_message: Optional[str] = None
    validation_score: Optional[float] = None
    validation_signals: Optional[dict] = None
