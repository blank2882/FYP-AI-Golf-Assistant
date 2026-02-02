from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel


class FaultItem(BaseModel):
    name: str
    score: float
    confidence: float  # 0-1 confidence score (how confident the detection is)


class AnalysisResponse(BaseModel):
    job_id: str
    annotated_video: Optional[str]
    json_path: Optional[str]
    feedback_text: str
    audio_feedback: Optional[str]
    event_frames: List[int]
    confidences: List[float]
    faults: List[FaultItem]
    metrics: dict
