# Architecture Recommendations - Detailed Technical Design

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [API Design](#api-design)
5. [Database Schema](#database-schema)
6. [Design Patterns](#design-patterns)
7. [Performance Considerations](#performance-considerations)
8. [Security Architecture](#security-architecture)

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend Layer                         │
│  (React/Vue - Phase 6: Web UI, Mobile: Future)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │/users (CRUD) │  │/videos       │  │/feedback     │          │
│  │/auth (JWT)   │  │/upload       │  │/personalized │          │
│  │/stats        │  │/status       │  │/suggestions  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              WebSocket Streaming Handler                │  │
│  │  /ws/stream (real-time frame analysis)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
    ┌─────────────┐ ┌──────────────┐ ┌──────────┐
    │  Pipeline   │ │  Baseline    │ │ Database │
    │  Execution  │ │  Tracker     │ │ (Phase 6)│
    │  (Batch &   │ │  (In-mem or  │ └──────────┘
    │   Real-time)│ │   Database)  │
    └─────┬───────┘ └──────────────┘
          │
      ┌───┴───┬───────────────┬──────────────┬─────────────┐
      ↓       ↓               ↓              ↓             ↓
   ┌────┐ ┌──────┐      ┌──────────┐  ┌─────────┐  ┌──────────┐
   │Input│ │Pose  │      │Fault     │  │Metrics  │  │Feedback  │
   │Mgmt │ │Object│      │Registry  │  │Registry │  │Engine    │
   │     │ │Detect│      │          │  │         │  │          │
   └────┘ └──────┘      └──────────┘  └─────────┘  └──────────┘
      │       │               │            │            │
      └───┬───┴───────────────┴────────────┴────────────┘
          │
   ┌──────┴──────┐
   ↓             ↓
┌──────────┐ ┌────────────┐
│ OpenCV   │ │ MediaPipe  │
│ Models   │ │  Models    │
└──────────┘ └────────────┘
```

### Layered Architecture

```
┌────────────────────────────────────┐
│       Presentation Layer           │  FastAPI endpoints, WebSocket
│  (api/routes, api/schemas)         │
└────────────────┬───────────────────┘
                 │
┌────────────────v───────────────────┐
│       Business Logic Layer         │  Fault detection, metrics,
│  (src/faults, src/metrics)         │  personalization, feedback
└────────────────┬───────────────────┘
                 │
┌────────────────v───────────────────┐
│       Data Access Layer            │  Baseline tracking, user
│  (src/core, src/feedback)          │  profiles, configuration
└────────────────┬───────────────────┘
                 │
┌────────────────v───────────────────┐
│       Integration Layer            │  OpenCV, MediaPipe, LLM,
│  (src/input, src/preprocessing)    │  TTS, models
└────────────────────────────────────┘
```

---

## Component Design

### 1. Fault Detection System

#### Architecture

```
FaultRegistry (Factory)
    │
    ├── BaseFault (Abstract)
    │   └── FaultDetector implementations
    │       ├── HeadMovementFault
    │       ├── SlideSway Fault
    │       ├── OverTheTopFault
    │       ├── EarlyExtensionFault
    │       └── [Custom faults...]
    │
    └── FaultResult (Data class)
        ├── detected: bool
        ├── score: float [0-1]
        ├── confidence: float [0-1]
        ├── severity: str (low|medium|high)
        └── details: Dict[str, Any]
```

#### Interface Design

```python
class BaseFault(ABC):
    
    @abstractmethod
    def detect(self,
               keypoints_seq: np.ndarray,        # (T, J, 3)
               address_frame: int = 0,
               impact_frame: Optional[int] = None,
               **kwargs) -> FaultResult:
        """
        Returns: FaultResult with standardized format
        - Keypoint sequence is normalized to [0, 1]
        - Address frame is start of swing
        - Impact frame is end of swing
        - Additional context via **kwargs
        """
        pass
```

#### Keypoint Coordinate System

```
MediaPipe 33-point model:
- Indices 0-10: Head region (nose, eyes, ears)
- Indices 11-16: Upper body (shoulders, elbows, wrists)
- Indices 17-22: Right side (hip, knee, ankle)
- Indices 23-28: Left side (hip, knee, ankle)
- Indices 29-32: Misc (palms)

Normalization: [0, 1] range
- x: 0 = left edge, 1 = right edge
- y: 0 = top edge, 1 = bottom edge
- z: 0 = camera plane, 1 = far from camera
```

#### Extending with New Faults

1. **Create class inheriting from `BaseFault`**
   - Implement `detect()` method
   - Implement `get_name()`, `get_description()`
   
2. **Return standardized `FaultResult`**
   - `detected`: bool
   - `score`: raw detection score [0, 1]
   - `confidence`: from keypoint visibility
   - `severity`: "low"/"medium"/"high"
   
3. **Register in fault registry**
   ```python
   FaultRegistry.register('fault_name', FaultClass)
   ```

4. **Enable in configuration**
   ```yaml
   faults:
     enabled:
       - fault_name
     thresholds:
       fault_name: 0.5
   ```

---

### 2. Metrics System

#### Architecture

```
MetricRegistry (Factory)
    │
    ├── BaseMetric (Abstract)
    │   └── Metric implementations
    │       ├── SwingTempoMetric
    │       ├── HipRotationMetric
    │       ├── ShoulderTurnMetric
    │       ├── WeightShiftMetric
    │       └── [Custom metrics...]
    │
    └── MetricResult (Data class)
        ├── name: str
        ├── value: float
        ├── unit: str
        ├── confidence: float [0-1]
        └── details: Dict[str, Any]
```

#### Design Philosophy

**No "ideal" values**: Metrics are descriptive, not prescriptive.

- "Swing tempo: 1.35 seconds" (descriptive)
- NOT: "Tempo too slow (2/10)" (prescriptive grading)

**Body-type aware**: Same metric value interpreted differently.

- Hip rotation 45°: Normal for ectomorph, limited for mesomorph
- Early extension timing: Varies by flexibility

**Confidence scoring**: Based on keypoint visibility.

- All metrics include confidence [0, 1]
- LLM feedback adjusts recommendations based on confidence

#### Extending with New Metrics

1. **Create class inheriting from `BaseMetric`**
   - Implement `compute()` method
   - Implement `get_name()`, `get_description()`, `get_unit()`
   
2. **Return standardized `MetricResult`**
   - `name`: metric identifier
   - `value`: computed value
   - `unit`: measurement unit (seconds, degrees, etc.)
   - `confidence`: from keypoint visibility
   
3. **Register in metric registry**
   ```python
   MetricRegistry.register('metric_name', MetricClass)
   ```

---

### 3. Baseline Tracking System

#### Architecture

```
BaselineTracker (In-memory or Database)
    │
    ├── UserBaseline
    │   ├── user_id: str
    │   ├── body_type: Optional[str]
    │   ├── height: Optional[float]
    │   ├── swing_metrics: Dict[str, float]
    │   ├── swing_patterns: Dict[str, float]
    │   └── last_updated: datetime
    │
    └── Methods
        ├── get_or_create_baseline(user_id)
        ├── set_user_info(user_id, body_type, height)
        ├── update_metrics(user_id, metrics)
        └── get_progression(user_id)
```

#### Metric Update Strategy

**Exponential Moving Average (EMA)**:

```
new_baseline = α * current_value + (1 - α) * old_baseline

where α = 0.3 (30% weight on new data)

Example:
- Baseline: 1.40 seconds
- Current swing: 1.25 seconds
- Updated baseline: 0.3*1.25 + 0.7*1.40 = 1.355 seconds
```

**Benefits**:
- Recent swings weighted more heavily
- Gradual adaptation to improvements
- Outliers don't dramatically shift baseline
- Smooth progression tracking

#### Database Schema (Phase 6)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  username VARCHAR(100) UNIQUE,
  email VARCHAR(100) UNIQUE,
  body_type VARCHAR(50),  -- ectomorph, mesomorph, endomorph
  height_cm FLOAT,
  age INT,
  experience_level VARCHAR(50),  -- beginner, intermediate, advanced
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE swing_baselines (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  metric_name VARCHAR(100),
  value FLOAT,
  unit VARCHAR(50),
  sample_count INT,
  last_updated TIMESTAMP,
  UNIQUE(user_id, metric_name)
);

CREATE TABLE swing_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_timestamp TIMESTAMP,
  video_path VARCHAR(255),
  duration_seconds FLOAT,
  faults_detected JSONB,
  metrics JSONB,
  feedback TEXT,
  created_at TIMESTAMP
);
```

---

### 4. Feedback Generation System

#### Architecture

```
PersonalizedFeedbackEngine
    │
    ├── _generate_baseline_swing_feedback()
    │   └── For first swing: establish baseline
    │
    └── _generate_comparison_feedback()
        ├── Compare metrics to user baseline
        ├── Detect improvements/regressions
        ├── Identify fault changes
        └── Generate LLM prompt
            │
            ├── Body-type context
            ├── Baseline comparison
            ├── Fault/metric changes
            │
            └── LLM (Ollama/phi3)
                │
                └── PersonalizedFeedback
                    ├── general_observations: str
                    ├── strengths: List[str]
                    ├── areas_to_improve: List[str]
                    ├── suggestions: List[str]
                    └── comparison_to_baseline: Dict
```

#### No-Grading Principle

**Bad feedback**: "Your swing scored 6/10. You need to improve your head movement."
- Uses numeric grading
- Doesn't acknowledge individual differences
- Discouraging without actionable guidance

**Good feedback**: "You've made great progress on your hip rotation! Focus this session on keeping your head steady through impact. Here's a drill that works well for your body type..."
- No numeric grading
- Acknowledges individual variation
- Specific, actionable, encouraging
- References body type

#### LLM Prompt Structure

```python
prompt = """
Golfer swing analysis (comparing to THEIR personal baseline):

Current metrics vs baseline:
- Swing tempo: {current} vs {baseline}
- Hip rotation: {current} vs {baseline}
...

Faults detected (if any):
- {fault_name}: {severity}
...

User body type: {body_type}

IMPORTANT CONSTRAINTS:
1. Do NOT grade the swing numerically
2. Do NOT compare to professional standards
3. DO compare to this user's baseline
4. DO acknowledge that "good swing" varies by body type
5. DO provide specific, actionable suggestions
6. DO highlight what's working well

Generate feedback that is:
- Positive and encouraging
- Specific to this individual
- Actionable (drills, focus areas)
- Respectful of body type differences
"""
```

---

### 5. FastAPI Integration

#### Endpoint Structure

**Video Processing**:
- `POST /api/videos/upload` - Upload video for analysis
- `GET /api/videos/{job_id}/status` - Check processing status
- `GET /api/videos/{job_id}/results` - Retrieve results

**Frame Analysis**:
- `POST /api/frame/analyze` - Single frame analysis
- `POST /api/frame/batch` - Batch frame analysis

**Real-time Streaming**:
- `WebSocket /api/ws/stream?user_id={id}` - Real-time feedback

**User Management**:
- `POST /api/users` - Create profile
- `GET /api/users/{user_id}` - Get profile
- `PUT /api/users/{user_id}` - Update profile
- `DELETE /api/users/{user_id}` - Delete profile

**Feedback & Analytics**:
- `GET /api/feedback/suggestions?user_id={id}` - Next practice focus
- `GET /api/users/{user_id}/history` - Swing history
- `GET /api/users/{user_id}/progression` - Progression chart data

#### Request/Response Schemas

```python
# Video Upload
class VideoUploadRequest(BaseModel):
    file: UploadFile
    user_id: str
    swing_type: str = "full_swing"  # driver, iron, chip, putt

class VideoUploadResponse(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    message: str
    estimated_wait_seconds: Optional[float]

# Frame Analysis
class FrameAnalysisRequest(BaseModel):
    frame_base64: str
    user_id: Optional[str] = None
    include_feedback: bool = False
    image_format: str = "jpg"

class FrameAnalysisResponse(BaseModel):
    frame_annotated_base64: str  # With keypoints/detections
    pose_landmarks: List[List[float]]  # [[x,y,z], ...]
    faults: List[FaultDetectionResult]
    inference_time_ms: float

# Feedback
class PersonalizedFeedback(BaseModel):
    general_observations: str
    strengths: List[str]
    areas_to_improve: List[str]
    suggestions: List[str]
    comparison_to_baseline: Optional[Dict[str, Any]] = None
    body_type_adjusted: bool
    generated_at: datetime
```

#### WebSocket Message Protocol

**Client → Server**:
```json
{
  "type": "frame",
  "frame_base64": "...",
  "timestamp_ms": 1000
}
```

**Server → Client**:
```json
{
  "type": "analysis",
  "frame_annotated": "...",
  "faults": [...],
  "latency_ms": 45,
  "user_baseline": {...}
}
```

---

### 6. Configuration System

#### Configuration Hierarchy

```
1. Default Config (default_config.yaml)
   ↓
2. Environment Variables (override defaults)
   ↓
3. User Config (per-user settings)
   ↓
4. Runtime Overrides (API parameters)
```

#### Configuration Sections

```yaml
pipeline:
  input:
    type: video_file|webcam|stream
    fps: 30
  detectors:
    pose:
      model_path: ./models/pose_landmarker_heavy.task
  processing:
    frame_skip: 1
    target_size: [224, 224]

faults:
  enabled: [head_movement, slide_sway, over_the_top]
  thresholds:
    head_movement: 0.04
    slide_sway: 0.12
  confidence_required: 0.7

metrics:
  enabled: [swing_tempo, hip_rotation, shoulder_turn]

feedback:
  personalization_enabled: true
  body_type_aware: true
  grading_enabled: false
  min_confidence_for_suggestion: 0.6

output:
  directory: ./out
  format: json|csv|xml
  include_video_annotated: true
```

---

## Data Flow

### Batch Processing Flow

```
Input Video (MP4)
    ↓
[Input Manager]
    └─> Decode frames @ FPS
        └─> Queue frames
            ↓
[Pose Detection]
    └─> MediaPipe Landmark extraction
        └─> Normalize keypoints [0,1]
            ↓
[Object Detection]
    └─> Golf club, ball detection
        └─> Bounding boxes + confidence
            ↓
[Swing Phase Classification]
    └─> SwingNet: address → backswing → downswing → impact → follow-through
        └─> Frame segmentation
            ↓
[Fault Detection] (Parallel faults)
    ├─> HeadMovementFault.detect()
    ├─> SlideSway Fault.detect()
    ├─> OverTheTopFault.detect()
    └─> ... (all enabled faults)
        └─> FaultResult[] with scores
            ↓
[Metrics Computation] (Parallel metrics)
    ├─> SwingTempoMetric.compute()
    ├─> HipRotationMetric.compute()
    └─> ... (all enabled metrics)
        └─> MetricResult[] with units
            ↓
[Baseline Comparison]
    └─> Compare current metrics to user baseline
        └─> Detect improvements/regressions
            ↓
[Feedback Generation]
    └─> PersonalizedFeedbackEngine.generate()
        ├─> Build LLM prompt
        ├─> Query LLM (Ollama)
        └─> PersonalizedFeedback
            ↓
[Output & Storage]
    ├─> Annotated video
    ├─> JSON results
    ├─> Feedback text
    └─> Update user baseline
        ↓
Client Response
```

### Real-Time Processing Flow

```
Webcam Frame (30 FPS)
    ↓
[Input Queue] (buffer 3 frames)
    ↓
[Priority Pipeline]
    ├─> Pose Detection (process every frame)
    ├─> Light Faults (head_movement: every frame)
    └─> Heavy Faults (over_the_top: every 5th frame)
        ↓
[Lightweight Feedback]
    └─> Simple observations (no LLM)
        └─> "Head moved 5cm" (real-time message)
            ↓
[Batch LLM Feedback]
    └─> Every 30 frames: full analysis + LLM feedback
        └─> Queued update to client
            ↓
Client Display
    ├─> Real-time annotations
    ├─> Live metrics
    └─> Periodic feedback
```

---

## API Design

### RESTful Principles

**Base URL**: `http://localhost:8000/api`

**Versioning**: `/v1/` (future-proof)

**Resource Organization**:
```
/users              - User profiles
/users/{id}/swings  - User's swings
/videos             - Video processing jobs
/feedback           - Feedback generation
```

### Error Handling

**Standard Error Response**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Descriptive error message",
    "details": {
      "field": "user_id",
      "issue": "must be UUID format"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_12345"
}
```

**HTTP Status Codes**:
- `200`: Success
- `202`: Accepted (async processing)
- `400`: Bad request (validation error)
- `401`: Unauthorized (missing auth)
- `403`: Forbidden (no permission)
- `404`: Not found
- `429`: Rate limited
- `500`: Server error

### Rate Limiting

```python
from fastapi_limiter import FastAPILimiter

# Per user: 100 uploads/hour
@limiter.limit("100/hour")
async def upload_video():
    pass

# Per IP: 1000 requests/hour
@limiter.limit("1000/hour")
async def get_all_users():
    pass
```

### Pagination

```python
class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

@router.get("/users/{user_id}/swings")
async def get_user_swings(user_id: str, params: PaginationParams):
    # Returns: {
    #   "items": [...],
    #   "total": 1234,
    #   "skip": 0,
    #   "limit": 100,
    #   "has_more": true
    # }
    pass
```

---

## Database Schema

### Core Tables (Phase 6)

**Users**:
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  
  -- Personalization
  body_type ENUM('ectomorph', 'mesomorph', 'endomorph'),
  height_cm FLOAT,
  age INT,
  experience_level ENUM('beginner', 'intermediate', 'advanced'),
  
  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP,
  is_active BOOLEAN DEFAULT true,
  
  INDEX (email),
  INDEX (username)
);
```

**Swing Sessions**:
```sql
CREATE TABLE swing_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Session info
  session_timestamp TIMESTAMP DEFAULT NOW(),
  session_type ENUM('driver', 'iron', 'chip', 'putt') DEFAULT 'driver',
  video_file_path VARCHAR(255),
  video_duration_seconds FLOAT,
  
  -- Analysis results
  faults_detected JSONB,  -- {fault_name: {detected, score, confidence, ...}}
  metrics JSONB,          -- {metric_name: {value, unit, confidence, ...}}
  swing_phases JSONB,     -- {phase: frame_count}
  
  -- Feedback
  feedback_text TEXT,
  feedback_generated_at TIMESTAMP,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  processing_time_seconds FLOAT,
  
  INDEX (user_id),
  INDEX (session_timestamp)
);
```

**Swing Baselines**:
```sql
CREATE TABLE swing_baselines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Metric tracking
  metric_name VARCHAR(100) NOT NULL,
  metric_value FLOAT,
  metric_unit VARCHAR(50),
  
  -- Tracking
  sample_count INT DEFAULT 1,
  last_updated TIMESTAMP DEFAULT NOW(),
  confidence FLOAT,  -- Average confidence from samples
  
  UNIQUE(user_id, metric_name),
  INDEX (user_id)
);
```

### Queries for Common Operations

**Get user's latest 10 swings**:
```sql
SELECT * FROM swing_sessions
WHERE user_id = $1
ORDER BY session_timestamp DESC
LIMIT 10;
```

**Get progression over time**:
```sql
SELECT 
  DATE(session_timestamp) as day,
  AVG((metrics->>'swing_tempo')::float) as avg_tempo,
  COUNT(*) as swings_per_day
FROM swing_sessions
WHERE user_id = $1
  AND session_timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(session_timestamp)
ORDER BY day;
```

**Detect fault trends**:
```sql
SELECT 
  faults_detected,
  COUNT(*) as occurrence_count,
  AVG((faults_detected->>fault_name->>'score')::float) as avg_score
FROM swing_sessions
WHERE user_id = $1
GROUP BY faults_detected
ORDER BY occurrence_count DESC;
```

---

## Design Patterns

### 1. Registry Pattern (Faults & Metrics)

**Purpose**: Dynamic instantiation of detectors/metrics

```python
class FaultRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, name, fault_class):
        cls._registry[name] = fault_class
    
    @classmethod
    def get(cls, name, **kwargs):
        return cls._registry[name](**kwargs)
```

**Usage**:
```python
# Register
FaultRegistry.register('head_movement', HeadMovementFault)

# Use
detector = FaultRegistry.get('head_movement')
result = detector.detect(keypoints)
```

### 2. Strategy Pattern (Input Sources)

**Purpose**: Pluggable input strategies (file, webcam, stream)

```python
class InputSource(ABC):
    @abstractmethod
    def read(self) -> Tuple[bool, np.ndarray, float]:
        """(success, frame, timestamp)"""
        pass

class VideoFileInput(InputSource):
    def read(self):
        # Decode from file
        pass

class WebcamInput(InputSource):
    def read(self):
        # Read from webcam
        pass
```

### 3. Observer Pattern (WebSocket Updates)

**Purpose**: Notify clients of analysis progress

```python
class AnalysisObserver:
    async def on_frame_analyzed(self, frame_num, faults, metrics):
        # Send to client via WebSocket
        await websocket.send_json({
            "frame": frame_num,
            "faults": faults,
            "metrics": metrics
        })
```

### 4. Decorator Pattern (Fault Confidence)

**Purpose**: Automatically add confidence scoring

```python
def add_confidence_scoring(detect_func):
    def wrapper(self, keypoints_seq, **kwargs):
        result = detect_func(self, keypoints_seq, **kwargs)
        confidence = self._compute_confidence(keypoints_seq)
        result.confidence = confidence
        return result
    return wrapper
```

### 5. Factory Pattern (Feedback Engine)

**Purpose**: Create appropriate feedback generator

```python
class FeedbackFactory:
    @staticmethod
    def create(user_baseline):
        if user_baseline is None:
            return BaselineFeedbackGenerator()
        else:
            return ComparisonFeedbackGenerator()
```

---

## Performance Considerations

### Bottleneck Analysis

| Stage | Time (ms) | Optimization |
|-------|-----------|--------------|
| Input decoding | 10-15 | Hardware acceleration |
| Pose detection | 50-100 | Model quantization |
| Object detection | 30-50 | Reduce image size |
| Fault detection | 20-40 | Cache stable values |
| Metrics | 10-20 | Vectorized ops |
| LLM feedback | 2000-5000 | Batch/async |
| **Total** | **2150-5225** | - |

### Target Metrics

**Batch processing** (video file): 
- Frame: ~150-200ms → suitable for video analysis

**Real-time** (webcam):
- Frame: <33ms (30 FPS) → requires optimization
  - Skip heavy faults (every 5th frame)
  - Lightweight detections only
  - LLM feedback async

### Memory Optimization

```python
# Load models once
pose_model = load_mediapipe()  # ~20MB
object_model = load_tflite()   # ~10MB
swingnet_model = load_torch()  # ~40MB
# Total: ~70MB

# Frame processing
frame = cv2.imread(path)  # ~6MB (1920x1080)
process_and_discard()     # Don't accumulate frames
```

### Batch Optimization

```python
# Instead of processing frames one-by-one:
# Bad: for i in range(T):
#     result = detect(frame[i:i+1])

# Good: vectorize across multiple faults
fault_results = {
    name: FaultRegistry.get(name).detect_batch(keypoints_seq)
    for name in enabled_faults
}
```

---

## Security Architecture

### Authentication & Authorization

**JWT-based authentication**:

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import JWTError, jwt

class JWTBearer(HTTPBearer):
    async def __call__(self, request):
        credentials = await super().__call__(request)
        token = credentials.credentials
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("sub")
        except JWTError:
            raise HTTPException(status_code=401)
        
        return user_id

# Usage:
@router.get("/users/me")
async def get_current_user(user_id: str = Depends(JWTBearer())):
    return {"user_id": user_id}
```

**Role-based access control (RBAC)**:

```python
class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"

async def check_role(user_id: str, required_role: Role):
    user = await db.users.get(user_id)
    if user.role != required_role:
        raise HTTPException(status_code=403)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user_id: str = Depends(JWTBearer()),
    _: None = Depends(check_role(Role.ADMIN))
):
    pass
```

### Input Validation

**Pydantic models** (automatic validation):

```python
class VideoUploadRequest(BaseModel):
    file: UploadFile = File(...)
    
    @field_validator('file')
    def validate_video(cls, file):
        # Check MIME type
        if file.content_type not in ['video/mp4', 'video/quicktime']:
            raise ValueError("Only MP4 and MOV supported")
        
        # Check file size
        if file.size > 500 * 1024 * 1024:  # 500MB
            raise ValueError("File too large")
        
        return file
```

### Secrets Management

**Environment variables**:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    ollama_url: str
    jwt_secret: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**.env file** (git-ignored):
```
DATABASE_URL=postgresql://user:pass@localhost/golfdb
SECRET_KEY=your-secret-key-here
OLLAMA_URL=http://localhost:11434
JWT_SECRET=your-jwt-secret-here
```

### Rate Limiting & DDoS Protection

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Per IP rate limiting
@app.post("/api/videos/upload")
@limiter.limit("10/minute")
async def upload_video(request: Request):
    pass

# Per user rate limiting (requires auth)
@app.post("/api/feedback/personalized")
@limiter.limit("100/hour")
async def get_feedback(request: Request, user_id: str = Depends(JWTBearer())):
    pass
```

### Data Privacy

**Data retention policy**:

```python
# Delete old analysis results
DELETE FROM swing_sessions
WHERE created_at < NOW() - INTERVAL '90 days'
AND user_id NOT IN (
    SELECT id FROM users WHERE is_active = true
);

# Anonymize user data on request
UPDATE users
SET email = 'deleted-' || id,
    username = 'deleted-' || id
WHERE id = $1;
```

---

## Next Steps

1. **Phase 1**: Implement architecture (registry pattern, base classes)
2. **Phase 2**: Add new faults/metrics using established patterns
3. **Phase 3-6**: Extend as needed

**This architecture supports all 6 planned enhancements!**
