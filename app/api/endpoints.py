from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core import config
from app.services.video_service import save_upload, create_run_dir
from app.services.pipeline import GolfAssistant
from app.api.schemas import AnalysisResponse, FaultItem

router = APIRouter()
templates = Jinja2Templates(directory=str(config.APP_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/analyze", response_class=HTMLResponse)
def analyze(request: Request, video: UploadFile = File(...)):
    config.ensure_directories()
    video_path = save_upload(video)
    run_dir = create_run_dir()

    assistant = GolfAssistant(video_path=str(video_path), out_dir=str(run_dir))
    result = assistant.run(allow_trim=False)

    validation = result.get("validation") or {}
    is_valid = bool(validation.get("valid", True))
    if not is_valid:
        message = validation.get("message") or "Unable to detect a valid golf swing."
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "annotated_video": None,
                "feedback_text": message,
                "faults": [],
                "metrics": result.get("metrics") or {},
                "audio_feedback": None,
                "event_frames": [],
                "event_frame_images": [],
                "confidences": [],
                "validation": validation,
            },
        )

    faults = result.get("faults", [])
    fault_items = [{"name": f[0], "score": float(f[1]), "confidence": float(f[2])} for f in faults]

    annotated_video = None
    if result.get("annotated_video"):
        annotated_video = _to_static_url(result["annotated_video"])

    audio_feedback = None
    if result.get("audio_feedback"):
        audio_feedback = _to_static_url(result["audio_feedback"])

    event_frame_images = []
    for item in result.get("event_frame_images") or []:
        image_url = _to_static_url(item.get("image_path"))
        if not image_url:
            continue
        event_frame_images.append(
            {
                "event_name": item.get("event_name"),
                "frame_index": item.get("frame_index"),
                "confidence": item.get("confidence"),
                "image_url": image_url,
            }
        )

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "annotated_video": annotated_video,
            "feedback_text": result.get("feedback") or "No feedback generated.",
            "faults": fault_items,
            "metrics": result.get("metrics") or {},
            "audio_feedback": audio_feedback,
            "event_frames": result.get("event_frames") or [],
            "event_frame_images": event_frame_images,
            "confidences": result.get("confidences") or [],
            "validation": validation,
        },
    )


@router.post("/analyze-live", response_class=HTMLResponse)
def analyze_live(request: Request, video: UploadFile = File(...)):
    config.ensure_directories()
    video_path = save_upload(video)
    run_dir = create_run_dir()

    assistant = GolfAssistant(video_path=str(video_path), out_dir=str(run_dir))
    result = assistant.run(allow_trim=True)

    validation = result.get("validation") or {}
    is_valid = bool(validation.get("valid", True))
    if not is_valid:
        message = validation.get("message") or "Unable to detect a valid golf swing."
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "annotated_video": None,
                "feedback_text": message,
                "faults": [],
                "metrics": result.get("metrics") or {},
                "audio_feedback": None,
                "event_frames": [],
                "event_frame_images": [],
                "confidences": [],
                "validation": validation,
            },
        )

    faults = result.get("faults", [])
    fault_items = [{"name": f[0], "score": float(f[1]), "confidence": float(f[2])} for f in faults]

    annotated_video = None
    if result.get("annotated_video"):
        annotated_video = _to_static_url(result["annotated_video"])

    audio_feedback = None
    if result.get("audio_feedback"):
        audio_feedback = _to_static_url(result["audio_feedback"])

    event_frame_images = []
    for item in result.get("event_frame_images") or []:
        image_url = _to_static_url(item.get("image_path"))
        if not image_url:
            continue
        event_frame_images.append(
            {
                "event_name": item.get("event_name"),
                "frame_index": item.get("frame_index"),
                "confidence": item.get("confidence"),
                "image_url": image_url,
            }
        )

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "annotated_video": annotated_video,
            "feedback_text": result.get("feedback") or "No feedback generated.",
            "faults": fault_items,
            "metrics": result.get("metrics") or {},
            "audio_feedback": audio_feedback,
            "event_frames": result.get("event_frames") or [],
            "event_frame_images": event_frame_images,
            "confidences": result.get("confidences") or [],
            "validation": validation,
        },
    )


@router.post("/api/analyze", response_model=AnalysisResponse)
def analyze_api(video: UploadFile = File(...)):
    config.ensure_directories()
    video_path = save_upload(video)
    run_dir = create_run_dir()

    assistant = GolfAssistant(video_path=str(video_path), out_dir=str(run_dir))
    result = assistant.run(allow_trim=False)

    validation = result.get("validation") or {}
    is_valid = bool(validation.get("valid", True))

    faults = result.get("faults", [])
    fault_items = [FaultItem(name=f[0], score=float(f[1]), confidence=float(f[2])) for f in faults]

    response = AnalysisResponse(
        job_id=Path(run_dir).name,
        annotated_video=_to_static_url(result.get("annotated_video")),
        json_path=_to_static_url(result.get("json")),
        feedback_text=result.get("feedback") or "No feedback generated.",
        audio_feedback=_to_static_url(result.get("audio_feedback")),
        event_frames=result.get("event_frames") or [],
        confidences=[float(c) for c in result.get("confidences") or []],
        faults=fault_items,
        metrics=result.get("metrics") or {},
        valid=is_valid,
        validation_message=validation.get("message"),
        validation_score=validation.get("score"),
        validation_signals=validation.get("signals") or {},
    )
    return response


def _to_static_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    p = Path(path_value)
    try:
        rel = p.relative_to(config.BASE_DIR)
    except ValueError:
        return str(p)
    return f"/{rel.as_posix()}"
