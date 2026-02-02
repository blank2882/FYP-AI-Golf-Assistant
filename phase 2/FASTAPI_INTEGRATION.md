# FastAPI Integration Guide - Full-Stack System

## Architecture Overview

```
Frontend (React/Vue)
        ↓
FastAPI (Python)
        ├── /upload_video (POST)
        ├── /analyze_frame (POST)
        ├── /get_feedback (GET)
        ├── /user_profile (CRUD)
        └── /ws/stream (WebSocket for real-time)
        ↓
Core Pipeline
        ├── Input Abstraction
        ├── Fault Registry
        ├── Metric Registry
        ├── Baseline Tracker
        └── Feedback Engine
```

---

## FastAPI App Structure

**File: `api/app.py`**

```python
from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import Optional
import uuid
import os

from api.schemas import (
    VideoUploadResponse, 
    FrameAnalysisRequest, 
    FeedbackResponse,
    UserProfileRequest
)
from api.routes import users, videos, feedback
from src.core.baseline_tracker import BaselineTracker
from src.faults import FaultRegistry
from src.metrics import MetricRegistry

app = FastAPI(
    title="Golf Assistant API",
    description="Real-time golf swing analysis with personalized feedback",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State management
app.state.baseline_tracker = BaselineTracker()
app.state.processing_jobs = {}

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])


@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "ready",
        "faults": FaultRegistry.list_all(),
        "metrics": MetricRegistry.list_all()
    }


@app.post("/api/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload video file for analysis
    
    Returns job ID for async processing
    """
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_dir = "./out/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = f"{upload_dir}/{job_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Queue for processing
    background_tasks.add_task(process_video_task, job_id, file_path, user_id)
    
    return VideoUploadResponse(
        job_id=job_id,
        status="queued",
        message=f"Video queued for processing. Job ID: {job_id}"
    )


async def process_video_task(job_id: str, file_path: str, user_id: Optional[str]):
    """Background task: process video"""
    try:
        app.state.processing_jobs[job_id] = {"status": "processing"}
        
        from assistant import GolfAssistant
        assistant = GolfAssistant()
        
        # Run analysis
        result = assistant.run(input_video=file_path, user_id=user_id)
        
        app.state.processing_jobs[job_id] = {
            "status": "completed",
            "result": result
        }
    except Exception as e:
        app.state.processing_jobs[job_id] = {
            "status": "failed",
            "error": str(e)
        }


@app.get("/api/videos/{job_id}/status")
async def get_job_status(job_id: str):
    """Get processing status of a video job"""
    if job_id not in app.state.processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return app.state.processing_jobs[job_id]


@app.post("/api/frame/analyze")
async def analyze_single_frame(request: FrameAnalysisRequest):
    """Analyze a single frame for faults"""
    # Decode base64 image
    import base64
    import cv2
    import numpy as np
    
    img_data = base64.b64decode(request.frame_base64)
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    from detector_pipeline import DetectorPipeline
    detector = DetectorPipeline()
    
    annotated, metadata = detector.process_frame(frame)
    
    # Encode response
    _, buffer = cv2.imencode('.jpg', annotated)
    response_img = base64.b64encode(buffer).decode()
    
    return {
        "frame": response_img,
        "keypoints": metadata.get("pose_landmarks", []),
        "detection_time_ms": metadata.get("inference_time_ms", 0)
    }


@app.websocket("/api/ws/stream")
async def websocket_stream(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time frame analysis"""
    await websocket.accept()
    
    baseline = app.state.baseline_tracker.get_or_create_baseline(user_id)
    
    try:
        while True:
            # Receive frame (base64 encoded)
            data = await websocket.receive_json()
            frame_b64 = data.get("frame")
            
            if not frame_b64:
                continue
            
            # Decode and analyze
            import base64
            import cv2
            import numpy as np
            
            img_data = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            from detector_pipeline import DetectorPipeline
            detector = DetectorPipeline()
            annotated, metadata = detector.process_frame(frame)
            
            # Encode response
            _, buffer = cv2.imencode('.jpg', annotated)
            response_img = base64.b64encode(buffer).decode()
            
            # Send feedback
            await websocket.send_json({
                "frame": response_img,
                "keypoints": metadata.get("pose_landmarks", []),
                "user_baseline": baseline.swing_metrics
            })
    
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## API Schemas

**File: `api/schemas.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class VideoUploadResponse(BaseModel):
    """Response from video upload"""
    job_id: str
    status: str  # queued, processing, completed, failed
    message: str


class FrameAnalysisRequest(BaseModel):
    """Single frame analysis request"""
    frame_base64: str = Field(..., description="Base64 encoded image")
    user_id: Optional[str] = None
    include_feedback: bool = False


class FaultDetectionResult(BaseModel):
    """Result of fault detection"""
    fault_name: str
    detected: bool
    score: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    severity: str  # low, medium, high
    details: Optional[Dict] = None


class SwingMetric(BaseModel):
    """Computed swing metric"""
    name: str
    value: float
    unit: str
    confidence: float = Field(..., ge=0, le=1)


class PersonalizedFeedback(BaseModel):
    """Personalized feedback without grading"""
    general_observations: str
    strengths: List[str]
    areas_to_improve: List[str]
    comparison_to_baseline: Optional[Dict[str, str]] = None
    suggestions: List[str]
    body_type_adjusted: bool = False


class FeedbackResponse(BaseModel):
    """Complete analysis feedback"""
    swing_id: str
    faults: List[FaultDetectionResult]
    metrics: List[SwingMetric]
    feedback: PersonalizedFeedback
    processing_time_ms: float


class UserProfileRequest(BaseModel):
    """User profile for personalization"""
    user_id: str
    body_type: Optional[str] = Field(
        None, 
        description="ectomorph, mesomorph, or endomorph"
    )
    height_cm: Optional[float] = None
    age: Optional[int] = None
    experience_level: Optional[str] = Field(
        None,
        description="beginner, intermediate, advanced"
    )


class UserProfile(UserProfileRequest):
    """Full user profile with baseline"""
    baseline_metrics: Dict[str, float] = {}
    created_at: datetime
    last_updated: datetime
```

---

## User Management Router

**File: `api/routes/users.py`**

```python
from fastapi import APIRouter, HTTPException
from api.schemas import UserProfile, UserProfileRequest
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=UserProfile)
async def create_user(profile: UserProfileRequest):
    """Create new user profile"""
    return UserProfile(
        **profile.dict(),
        created_at=datetime.now(),
        last_updated=datetime.now()
    )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, baseline_tracker):
    """Get user profile and baseline"""
    baseline = baseline_tracker.get_or_create_baseline(user_id)
    
    return UserProfile(
        user_id=user_id,
        body_type=baseline.body_type,
        baseline_metrics=baseline.swing_metrics,
        created_at=baseline.last_updated,
        last_updated=baseline.last_updated
    )


@router.put("/{user_id}", response_model=UserProfile)
async def update_user(user_id: str, profile: UserProfileRequest, baseline_tracker):
    """Update user profile"""
    baseline = baseline_tracker.get_or_create_baseline(user_id)
    baseline_tracker.set_user_info(user_id, profile.body_type, profile.height_cm)
    
    return UserProfile(
        **profile.dict(),
        baseline_metrics=baseline.swing_metrics,
        created_at=baseline.last_updated,
        last_updated=datetime.now()
    )
```

---

## Feedback Generation Router

**File: `api/routes/feedback.py`**

```python
from fastapi import APIRouter, HTTPException
from api.schemas import FeedbackResponse, FaultDetectionResult, PersonalizedFeedback
from src.faults import FaultRegistry
from src.core.baseline_tracker import BaselineTracker
from typing import Optional
import numpy as np
from llm_feedback import generate_feedback

router = APIRouter()


@router.post("/personalized")
async def get_personalized_feedback(
    user_id: str,
    faults_detected: list,
    metrics: dict,
    baseline_tracker: BaselineTracker
) -> PersonalizedFeedback:
    """Generate personalized feedback WITHOUT numeric grading
    
    Approach:
    1. Compare current swing to user's baseline (if established)
    2. Identify improvements vs previous swings
    3. Suggest adjustments based on body type
    4. Avoid numeric scores/grades
    """
    
    baseline = baseline_tracker.get_or_create_baseline(user_id)
    
    # Generate feedback using LLM
    feedback_prompt = _build_feedback_prompt(
        user_id=user_id,
        faults=faults_detected,
        metrics=metrics,
        baseline=baseline,
        body_type=baseline.body_type
    )
    
    llm_response = generate_feedback(feedback_prompt)
    
    # Parse LLM response
    parsed_feedback = _parse_llm_feedback(llm_response)
    
    # Update baseline with new metrics
    baseline_tracker.update_metrics(user_id, metrics)
    
    return PersonalizedFeedback(
        general_observations=parsed_feedback['observations'],
        strengths=parsed_feedback['strengths'],
        areas_to_improve=parsed_feedback['improvements'],
        comparison_to_baseline={
            metric: f"{baseline.swing_metrics.get(metric, 0):.2f}"
            for metric in metrics.keys()
        },
        suggestions=parsed_feedback['suggestions'],
        body_type_adjusted=(baseline.body_type is not None)
    )


def _build_feedback_prompt(user_id: str, faults: list, metrics: dict, 
                           baseline, body_type: Optional[str]) -> str:
    """Build LLM prompt for personalized feedback"""
    
    fault_descriptions = ", ".join([f"{f['name']} (severity: {f['severity']})" 
                                   for f in faults])
    
    body_type_context = f"""
    User body type: {body_type}
    - Adjust expectations for range of motion based on body type
    - Consider how body composition affects swing mechanics
    """ if body_type else ""
    
    baseline_context = f"""
    User's baseline metrics:
    {chr(10).join([f"- {k}: {v:.2f}" for k, v in baseline.swing_metrics.items()])}
    
    Current metrics:
    {chr(10).join([f"- {k}: {v:.2f}" for k, v in metrics.items()])}
    """ if baseline.swing_metrics else "First swing analysis - no baseline yet."
    
    prompt = f"""
    Analyze this golf swing and provide PERSONALIZED feedback:
    
    {body_type_context}
    
    Faults detected: {fault_descriptions}
    
    {baseline_context}
    
    Important guidelines:
    - DO NOT grade the swing numerically (0-100, star ratings, etc.)
    - Focus on improvements relative to THIS USER'S baseline
    - Acknowledge that "good swing" varies by body type and physicality
    - Provide actionable suggestions for next swing
    - Highlight what's working well
    - Be encouraging and specific
    
    Structure your response as:
    - General Observations: [brief overview]
    - Strengths: [list what's working]
    - Areas to Improve: [list specific things to work on]
    - Suggestions: [actionable tips for next swing]
    """
    
    return prompt


def _parse_llm_feedback(response: str) -> dict:
    """Parse LLM response into structured feedback"""
    # Simple parsing (production would use more robust NLP)
    sections = {
        'observations': '',
        'strengths': [],
        'improvements': [],
        'suggestions': []
    }
    
    lines = response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if 'observations' in line.lower():
            current_section = 'observations'
        elif 'strength' in line.lower():
            current_section = 'strengths'
        elif 'improve' in line.lower():
            current_section = 'improvements'
        elif 'suggestion' in line.lower():
            current_section = 'suggestions'
        elif line and current_section:
            if current_section == 'observations':
                sections['observations'] += line + " "
            else:
                sections[current_section].append(line)
    
    return sections
```

---

## Running the FastAPI Server

**Create: `run_api.py`**

```python
import uvicorn
import os

if __name__ == "__main__":
    # Enable reload during development
    reload = os.getenv('RELOAD_ON_CHANGE', 'true').lower() == 'true'
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level="info"
    )
```

Run with:
```bash
python run_api.py
```

Visit: http://localhost:8000/docs for interactive Swagger UI

---

## Environment Setup

**Create: `.env`**

```
FASTAPI_ENV=development
RELOAD_ON_CHANGE=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
OLLAMA_URL=http://localhost:11434
DATABASE_URL=sqlite:///./golf_assistant.db  # For Phase 6
```

---

## Key Design Principles for Full-Stack

1. **Async-Ready**: All endpoints support concurrent requests
2. **Job Queuing**: Long-running analysis runs in background
3. **Real-time Capable**: WebSocket support for live streaming
4. **Personalization**: Baseline-aware feedback, not grades
5. **Scalable**: Ready for database migration (Phase 6)
6. **RESTful**: Standard HTTP for all CRUD operations

---

## Next: Frontend Integration

See [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) for React/Vue setup.
