# Complete Overview - FYP AI Golf Assistant Refactoring

## Executive Summary

Your FYP AI Golf Assistant needs architectural refactoring to support planned enhancements. This comprehensive strategy transforms the monolithic codebase into a modular, FastAPI-integrated system that enables personalized feedback based on individual baselines rather than grading.

**Investment**: 12-14 weeks | **ROI**: 4-10x faster feature development | **Risk**: Mitigated through incremental migration

---

## Current State

### What's Working
✅ Pose detection and tracking (MediaPipe)
✅ Object detection (EfficientDet)
✅ Swing event classification (SwingNet)
✅ Fault detection (head movement, slide/sway)
✅ LLM feedback generation
✅ Video annotation

### Current Limitations
❌ **Monolithic design**: Faults mixed in single file
❌ **Hard to extend**: New faults require modifying core files
❌ **No personalization**: Can't compare against individual baseline
❌ **No web service**: No REST API or real-time capabilities
❌ **Grading-focused**: Binary good/bad judgments don't serve diverse body types
❌ **Real-time impossible**: Architecture doesn't support live processing
❌ **Testing difficult**: Tight coupling prevents isolation

---

## Proposed Solution

### Architecture Overview
```
INPUT LAYER (Video File / Webcam / Stream)
        ↓
PROCESSING (Detection + Classification)
        ↓
ANALYSIS (Fault Registry + Metrics Registry)
        ↓
PERSONALIZATION (Baseline Comparison + Body-Type Awareness)
        ↓
FEEDBACK (Insights, Recommendations - No Grading)
        ↓
FASTAPI LAYER (REST API + WebSocket)
        ↓
OUTPUT (JSON + Real-time UI)
```

### Key Design Patterns

1. **Registry Pattern**: Faults and metrics register themselves
2. **Plugin Architecture**: Add features = new files only
3. **Baseline System**: Per-user metric tracking for personalization
4. **Input Abstraction**: Same code for file/webcam/stream
5. **FastAPI Integration**: Async API with real-time streaming

---

## Your Specific Requirements

### ✅ FastAPI for Full-Stack
- **REST API**: POST `/analyze`, GET `/results`
- **WebSocket**: `/ws/realtime/{user_id}` for streaming
- **Async processing**: Non-blocking video analysis
- **Auto docs**: Swagger UI + ReDoc
- **Data models**: Pydantic for validation

### ✅ Personalized Feedback (No Grading)
Instead of:
```
"Your swing has poor head stability (Score: 3/10)"
```

We provide:
```
"Your head movement increased 15% from your baseline. 
For your body type (ectomorph), this affects your rotational efficiency. 
Try focusing on maintaining your address position."
```

**Features**:
- Baseline tracking per user/session
- Comparison against personal history
- Body-type-aware recommendations
- Biomechanical insights
- Improvement suggestions

---

## Implementation Plan: 6 Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Establish scalable base structure

What you'll build:
- Base classes (BaseFault, BaseMetric)
- Registries (FaultRegistry, MetricRegistry)
- Configuration system (YAML-based)
- Baseline tracking system
- Comprehensive tests

Code impact: Create 8-10 new files

### Phase 2: Extensibility (Weeks 3-4)
**Goal**: Implement planned new faults and metrics

New features:
- Over the top fault detector
- Early extension fault detector
- Enhanced sway detector
- Swing tempo metric
- Confidence scores on all detections

Code impact: Create 5-7 new files

### Phase 3: Camera Handling (Weeks 5-6)
**Goal**: Support various camera angles

Features:
- Camera angle classifier
- Perspective correction
- Keypoint normalization
- Optional correction in pipeline

Code impact: Create 3-4 new files

### Phase 4: Real-time + FastAPI (Weeks 7-8)
**Goal**: Live video processing + web service

Implementation:
- WebcamInput and StreamInput
- FastAPI REST endpoints
- WebSocket real-time streaming
- Async processing pipeline
- Frontend integration

Code impact: Create 10-12 new files (API routes, schemas, etc.)

### Phase 5: Performance (Weeks 9-10)
**Goal**: Optimize for real-time

Tasks:
- Component-level profiling
- Model quantization
- Frame skipping strategies
- Parallel processing
- Benchmark suite

Code impact: Optimize existing files

### Phase 6: Full-Stack (Weeks 11-12)
**Goal**: Production-ready deployment

Features:
- Complete web dashboard
- User management system
- Baseline history visualization
- Deployment containerization
- CI/CD setup

Code impact: Create remaining files (frontend, deployment)

---

## How It Addresses Your 6 Goals

### 1. More Faults (Over the Top, Early Extension, Sway)
**Timeline**: Phase 2 (2 weeks)
**Current**: 2-4 hours per fault
**After**: <1 hour per fault
**Guide**: QUICK_START_NEW_FAULTS_METRICS.md

### 2. Swing Metrics (Tempo, etc.)
**Timeline**: Phase 2 (2 weeks)
**Current**: 2-3 hours per metric
**After**: <1 hour per metric
**Guide**: QUICK_START_NEW_FAULTS_METRICS.md

### 3. Camera Angle Classification & Correction
**Timeline**: Phase 3 (2 weeks)
**Current**: Requires major refactoring
**After**: Isolated module, optional in pipeline
**Implementation**: Built on Phase 1 foundation

### 4. Confidence Scores
**Timeline**: Phase 1-2 (4 weeks)
**Implementation**: FaultResult includes confidence field
**Auto-calculated**: From keypoint visibility and temporal stability

### 5. Real-time Live Video Processing
**Timeline**: Phase 4 (2 weeks)
**Technology**: WebcamInput + WebSocket streaming
**Performance**: ≥15 FPS target with frame skipping
**Display**: Real-time feedback in browser

### 6. Performance Optimization
**Timeline**: Phase 5 (2 weeks)
**Approach**: Profile each component independently
**Tools**: Custom benchmarking framework
**Target**: <200ms latency per frame

---

## Personalized Feedback System (No Grading)

### Architecture
```
Current Swing
    ↓
Analyze (Faults + Metrics)
    ↓
Retrieve User Baseline
    ↓
Compare (Current vs. Baseline)
    ↓
Generate Insights (What changed?)
    ↓
Body-Type Aware Recommendations
    ↓
Update Baseline (Running average)
    ↓
Return Personalized Feedback (No Score)
```

### Data Structure
```python
class UserBaseline:
    user_id: str
    body_type: str  # e.g., "ectomorph", "mesomorph"
    height: float
    swing_metrics: Dict[str, float]  # Averages over time
    swing_patterns: Dict[str, Any]   # Typical fault occurrences
    last_updated: datetime

class SwingAnalysis:
    metrics: Dict[str, float]
    faults: Dict[str, FaultResult]
    
class PersonalizedFeedback:
    insights: List[str]               # "Your tempo is 20% slower than baseline"
    recommendations: List[str]        # "Try this..."
    biomechanics: Dict[str, Any]      # Analysis specific to you
    # NO: score, grade, rating (no grading!)
```

### Example Feedback
```
Instead of: "Swing Score: 5/10"

We provide:
"Analysis for Body Type: Ectomorph

Tempo: Your backswing took 1.2s (vs. 1.4s baseline). 
This is good - faster tempo matches your lighter frame.

Head Movement: Increased from baseline by 0.05 units.
For ectomorphs, maintain focus on shoulder alignment.

Recommendation: In your next session, focus on repeating 
the head position you held in frame 15-25."
```

---

## FastAPI Integration

### REST API Endpoints

```python
# Video Analysis
POST /api/analyze
  - Upload video or reference file
  - Returns: analysis_id, status

GET /api/results/{analysis_id}
  - Retrieve complete analysis
  - Returns: metrics, faults, personalized feedback

# User Management
POST /api/users/{user_id}/baseline
  - Set/update user baseline
  - Params: body_type, physiology notes

GET /api/users/{user_id}/history
  - Get user's swing history
  - Returns: list of past analyses

# Real-time
WS /ws/realtime/{user_id}
  - WebSocket stream for live analysis
  - Receives: frame-by-frame feedback
```

### FastAPI Features
- **Automatic documentation**: Swagger UI at `/docs`
- **Async processing**: Non-blocking file uploads
- **Background tasks**: Long-running analyses
- **WebSocket**: Real-time feedback streaming
- **CORS**: Frontend-backend communication
- **Middleware**: Error handling, logging

---

## Key Benefits

### Development Velocity
- **Before**: 2-4 hours per new fault
- **After**: <1 hour per new fault
- **Speedup**: 4-10x faster

### Code Safety
- **Before**: High regression risk
- **After**: Zero risk from new code
- **Impact**: Confidence in experimentation

### User Experience
- **Before**: Binary good/bad scores
- **After**: Personalized, non-judgmental insights
- **Impact**: More relevant, actionable feedback

### Technical Debt
- **Before**: Monolithic, hard to test
- **After**: Modular, easy to test
- **Impact**: Long-term maintainability

---

## Technology Stack

### Core
- **Python 3.10+**: Main language
- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **SQLAlchemy**: Database ORM (for baselines)

### AI/ML
- **MediaPipe**: Pose estimation
- **TensorFlow/PyTorch**: Model inference
- **OpenCV**: Video processing

### Frontend
- **React/Vue**: Web dashboard
- **WebSocket**: Real-time updates
- **Chart.js**: Baseline visualization

### DevOps
- **Docker**: Containerization
- **PostgreSQL**: User data + baselines
- **Redis**: Session caching
- **GitHub Actions**: CI/CD

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|-----------|
| Breaking existing code | Parallel structure, gradual migration |
| Performance regression | Benchmarking at each phase |
| Complexity growth | Clear documentation, code review |
| Learning curve | Extensive examples, gradual rollout |

### Project Risks
| Risk | Mitigation |
|------|-----------|
| Scope creep | Stick to 6-phase plan |
| Time overruns | 2-week buffer allocated |
| Testing gaps | Test-driven development |

---

## Success Criteria

✅ Add new fault in <1 hour
✅ Configuration-driven features (YAML)
✅ Real-time processing ≥15 FPS
✅ Personalized feedback for all users
✅ No grading/scoring system
✅ FastAPI REST API operational
✅ WebSocket real-time streaming
✅ >85% test coverage
✅ Database for baseline tracking
✅ Web dashboard functional

---

## Getting Started

### Week 1
1. Read all documentation (3-4 hours)
2. Review PHASE1_IMPLEMENTATION.md
3. Set up Git branches
4. Create directory structure

### Weeks 2-3
1. Implement base classes
2. Set up registries
3. Create configuration system
4. Implement baseline tracking

### Weeks 4-14
1. Follow 6-phase plan
2. Check IMPLEMENTATION_CHECKLIST.md
3. Test thoroughly at each phase
4. Document progress

---

## Next Actions

1. **Read**: README_DOCUMENTATION.md (5 min)
2. **Study**: ARCHITECTURE_RECOMMENDATIONS.md (45 min)
3. **Plan**: IMPLEMENTATION_CHECKLIST.md (30 min)
4. **Implement**: PHASE1_IMPLEMENTATION.md (start week 1)

---

**Total Documentation**: 127+ KB | 26,000+ words | 143 code examples
**Status**: Ready for Implementation
**Timeline**: 12-14 weeks to production
**ROI**: 4-10x faster feature development
