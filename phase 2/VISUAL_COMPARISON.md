# Visual Comparisons & Directory Structure

## Current vs. Proposed Architecture

### Current Architecture (Monolithic)

```
assistant.py (354 lines)
  ├─ imports main()
  ├─ imports run_detector()        ← detector_pipeline.py
  ├─ imports run_swingnet()        ← swingnet_inference.py
  ├─ imports fault functions       ← faultDetect.py
  ├─ imports LLM feedback          ← llm_feedback.py
  └─ imports TTS                   ← tts.py

main.py (23 lines)
  └─ calls GolfAssistant.run()

Problem: Everything flows through assistant.py
- Adding fault = modify faultDetect.py + assistant.py
- Adding metric = modify faultDetect.py + assistant.py
- Changing feedback = modify llm_feedback.py + assistant.py
- Hard to test components independently
- Configuration hardcoded
```

### Proposed Architecture (Modular)

```
src/
├── faults/
│   ├── base_fault.py              ← Abstract interface
│   ├── fault_registry.py           ← Factory pattern
│   └── fault_detectors/
│       ├── head_movement.py        ← Plugin 1
│       ├── slide_sway.py           ← Plugin 2
│       ├── over_the_top.py         ← Plugin 3 (NEW)
│       └── early_extension.py      ← Plugin 4 (NEW)
│
├── metrics/
│   ├── base_metric.py              ← Abstract interface
│   ├── metric_registry.py          ← Factory pattern
│   └── swing_metrics/
│       ├── swing_tempo.py          ← Plugin 1 (NEW)
│       ├── hip_rotation.py         ← Plugin 2 (NEW)
│       ├── shoulder_turn.py        ← Plugin 3 (NEW)
│       └── weight_shift.py         ← Plugin 4 (NEW)
│
├── core/
│   └── baseline_tracker.py         ← User baselines
│
├── feedback/
│   ├── personalized_feedback.py    ← No-grading engine
│   └── feedback_registry.py        ← Template registry
│
├── camera/
│   ├── angle_classifier.py         ← Phase 3
│   └── angle_correction.py         ← Phase 3
│
├── input/
│   ├── input_source.py             ← Abstract interface
│   ├── video_file_input.py         ← Batch processing
│   └── webcam_input.py             ← Real-time
│
├── preprocessing/
│   └── normalization.py            ← Data preprocessing
│
└── utils/
    ├── constants.py
    └── helpers.py

api/
├── app.py                          ← FastAPI application
├── routes/
│   ├── users.py                    ← User CRUD
│   ├── videos.py                   ← Video upload/status
│   └── feedback.py                 ← Feedback generation
├── schemas.py                      ← Pydantic models
└── middleware/
    └── auth.py                     ← JWT authentication

config/
├── default_config.yaml             ← Default settings
├── beginner.yaml                   ← Beginner profile
├── intermediate.yaml               ← Intermediate profile
└── advanced.yaml                   ← Advanced profile

test/
├── unit/
│   ├── test_faults/
│   │   ├── test_head_movement.py
│   │   ├── test_slide_sway.py
│   │   ├── test_over_the_top.py    ← Phase 2
│   │   └── test_early_extension.py ← Phase 2
│   │
│   ├── test_metrics/
│   │   ├── test_swing_tempo.py     ← Phase 2
│   │   ├── test_hip_rotation.py    ← Phase 2
│   │   └── ...
│   │
│   ├── test_detectors/
│   │   └── test_detector_pipeline.py
│   │
│   └── test_input/
│       ├── test_video_file_input.py
│       └── test_webcam_input.py
│
├── integration/
│   ├── test_full_pipeline.py
│   ├── test_api_endpoints.py
│   └── test_feedback_generation.py
│
└── fixtures/
    ├── sample_keypoints.npy
    ├── sample_video.mp4
    └── sample_frames.json

Benefits:
✅ Adding fault = create 1 file + register (5 min)
✅ Components independently testable
✅ Configuration-driven behavior
✅ Easy to enable/disable features
✅ Parallel development possible
```

---

## Current Directory Tree

```
FYP-AI-Golf-Assistant/
│
├── Python Source Files
│   ├── main.py                     (entry point)
│   ├── assistant.py                (orchestrator, 354 lines)
│   ├── detector_pipeline.py        (pose/object detection)
│   ├── faultDetect.py              (fault detection)
│   ├── objDetect.py                (object detection wrapper)
│   ├── poseDetect.py               (pose detection wrapper)
│   ├── swingnet_inference.py       (swing phase classification)
│   ├── llm_feedback.py             (LLM feedback generation)
│   ├── tts.py                      (text-to-speech)
│   └── __pycache__/
│
├── HTML/CSS/JS (Legacy Web Interface)
│   ├── index.html
│   ├── analysis.html
│   ├── index.js
│   └── style.css
│
├── Model Weights
│   └── models/
│       ├── efficientdet_lite2.tflite       (object detection)
│       └── pose_landmarker_heavy.task      (pose estimation)
│
├── Data Directories
│   ├── data/
│   │   ├── amateur_swings/                 (sample videos)
│   │   └── videos_160/
│   └── golfdb/
│       ├── models/                        (SwingNet model)
│       ├── data/
│       │   ├── golfDB.mat
│       │   ├── videos_160/
│       │   ├── generate_splits.py
│       │   └── preprocess_videos.py
│       ├── dataloader.py
│       ├── eval.py
│       ├── train.py
│       ├── model.py
│       ├── test_video.py
│       ├── util.py
│       ├── README.md
│       └── __pycache__/
│
├── Testing
│   └── test/
│       ├── test_detector_pipeline.py
│       ├── test_objDetect.py
│       ├── test_poseDetect.py
│       ├── test_swingnet_inference.py
│       └── ...
│
├── Configuration
│   ├── requirements.txt             (dependencies)
│   └── README.md                    (documentation)
│
└── Root Files
    └── ... (project config files)
```

---

## Proposed Directory Tree (Phase 1)

```
FYP-AI-Golf-Assistant/
│
├── src/                            ← New: source code
│   ├── __init__.py
│   │
│   ├── faults/
│   │   ├── __init__.py
│   │   ├── base_fault.py
│   │   ├── fault_registry.py
│   │   └── fault_detectors/
│   │       ├── __init__.py
│   │       ├── head_movement.py
│   │       └── slide_sway.py
│   │
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── base_metric.py
│   │   ├── metric_registry.py
│   │   └── swing_metrics/
│   │       ├── __init__.py
│   │       └── (empty for Phase 1)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── baseline_tracker.py
│   │   └── pipeline.py
│   │
│   ├── feedback/
│   │   ├── __init__.py
│   │   └── personalized_feedback.py
│   │
│   ├── input/
│   │   ├── __init__.py
│   │   ├── input_source.py
│   │   ├── video_file_input.py
│   │   └── webcam_input.py
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   └── normalization.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   └── helpers.py
│   │
│   └── __pycache__/
│
├── api/                            ← New: FastAPI
│   ├── app.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── videos.py
│   │   └── feedback.py
│   ├── middleware/
│   │   └── auth.py
│   └── __pycache__/
│
├── config/                         ← New: configuration
│   ├── default_config.yaml
│   ├── beginner.yaml
│   ├── intermediate.yaml
│   └── advanced.yaml
│
├── test/                           ← Reorganized: testing
│   ├── unit/
│   │   ├── test_faults/
│   │   │   ├── test_head_movement.py
│   │   │   └── test_slide_sway.py
│   │   ├── test_metrics/
│   │   ├── test_detectors/
│   │   └── test_input/
│   ├── integration/
│   ├── fixtures/
│   └── conftest.py
│
├── logs/                           ← New: logging
│   └── (empty, populated at runtime)
│
├── out/                            ← New: outputs
│   ├── videos/
│   ├── json/
│   ├── uploads/
│   └── (populated at runtime)
│
├── models/                         ← Existing: weights
│   ├── efficientdet_lite2.tflite
│   └── pose_landmarker_heavy.task
│
├── data/                           ← Existing: sample data
│   ├── amateur_swings/
│   └── videos_160/
│
├── golfdb/                         ← Existing: SwingNet
│   ├── models/
│   ├── data/
│   ├── dataloader.py
│   ├── eval.py
│   ├── train.py
│   ├── model.py
│   ├── test_video.py
│   ├── util.py
│   ├── README.md
│   └── __pycache__/
│
├── frontend/                       ← New: React/Vue (Phase 6)
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ... (React app structure)
│
├── Main Entry Points
│   ├── main.py                     (refactored)
│   ├── assistant.py                (refactored)
│   ├── run_api.py                  (FastAPI server)
│   │
│   ├── detector_pipeline.py        (kept for compatibility)
│   ├── faultDetect.py              (deprecated, refactored)
│   ├── objDetect.py                (kept for compatibility)
│   ├── poseDetect.py               (kept for compatibility)
│   ├── swingnet_inference.py       (kept for compatibility)
│   ├── llm_feedback.py             (refactored)
│   └── tts.py                      (kept for compatibility)
│
├── Web Interface (Legacy)
│   ├── index.html
│   ├── analysis.html
│   ├── index.js
│   └── style.css
│
├── Documentation
│   ├── README.md                   (updated)
│   ├── README_DOCUMENTATION.md
│   ├── ANALYSIS_COMPLETE.md
│   ├── COMPLETE_OVERVIEW.md
│   ├── REFACTORING_SUMMARY.md
│   ├── PHASE1_IMPLEMENTATION.md
│   ├── CODE_EXAMPLES.md
│   ├── QUICK_START_NEW_FAULTS_METRICS.md
│   ├── FASTAPI_INTEGRATION.md
│   ├── ARCHITECTURE_RECOMMENDATIONS.md
│   ├── VISUAL_COMPARISON.md
│   ├── IMPLEMENTATION_CHECKLIST.md
│   └── DOCUMENTATION_INDEX.md
│
├── Configuration Files
│   ├── requirements.txt             (updated with FastAPI)
│   ├── .env                         (new, secrets)
│   ├── .env.example                 (new, template)
│   ├── .gitignore                   (updated)
│   ├── docker-compose.yml           (new, Phase 6)
│   ├── Dockerfile                   (new, Phase 6)
│   └── pytest.ini                   (new, testing)
│
└── Root Files
    └── (project config files)
```

---

## Class Diagram: Fault Detection System

```
┌─────────────────────────────────┐
│         BaseFault (ABC)         │
├─────────────────────────────────┤
│ - threshold: float              │
├─────────────────────────────────┤
│ + detect(...)→ FaultResult      │
│ + get_name() → str              │
│ + get_description() → str       │
│ + set_threshold(float) → None   │
└────────────┬────────────────────┘
             △
             │ implements
    ┌────────┴──────────────────────────────────┬──────────────┐
    │                                           │              │
┌───┴──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│ HeadMovementFault    │  │SlideSway Fault   │  │OverTheTopFault
├──────────────────────┤  ├──────────────────┤  ├──────────────┐
│ - threshold: 0.04    │  │ - threshold: 0.12│  │ - threshold: │
├──────────────────────┤  ├──────────────────┤  │   0.15       │
│ detect(...)          │  │ detect(...)      │  ├──────────────┤
│ → FaultResult        │  │ → FaultResult    │  │ detect(...)  │
└──────────────────────┘  └──────────────────┘  │ → FaultResult│
                                                 └──────────────┘

      ┌──────────────────────────────────┐
      │       FaultRegistry (Factory)    │
      ├──────────────────────────────────┤
      │ _registry: Dict[str, Type]       │
      ├──────────────────────────────────┤
      │ + register(name, fault_class)    │
      │ + get(name, **kwargs)→ BaseFault │
      │ + list_all() → List[str]         │
      │ + describe_all() → Dict[str,str] │
      └──────────────────────────────────┘
               │ creates
               └─> [BaseFault implementations]

┌─────────────────────────────────┐
│      FaultResult (Dataclass)    │
├─────────────────────────────────┤
│ - detected: bool                │
│ - score: float [0, 1]           │
│ - confidence: float [0, 1]      │
│ - severity: str                 │
│ - details: Dict[str, Any]       │
└─────────────────────────────────┘
```

---

## Sequence Diagram: Fault Detection Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ Pipeline Running                                                    │
└────────────────────────────────────────────────────────────────────┘

Assistant.run()
  │
  ├─> detector_pipeline.process_video()
  │     └─> Returns: (annotated_frames, keypoints_seq)
  │
  ├─> FOR each enabled fault in FaultRegistry:
  │     │
  │     ├─> fault = FaultRegistry.get(fault_name)
  │     │
  │     └─> fault.detect(keypoints_seq, address_frame, impact_frame)
  │           │
  │           ├─> Compute fault-specific features
  │           │     (e.g., head displacement for head_movement)
  │           │
  │           ├─> Compute score [0, 1]
  │           │
  │           ├─> Extract confidence from keypoint visibility
  │           │
  │           ├─> Classify severity (low/medium/high)
  │           │
  │           └─> Return FaultResult
  │                 {
  │                   detected: bool,
  │                   score: float,
  │                   confidence: float,
  │                   severity: str,
  │                   details: dict
  │                 }
  │
  └─> Aggregate all FaultResult objects into pipeline output
```

---

## API Endpoint Hierarchy

```
HTTP://localhost:8000/api
│
├── /users
│   ├── POST         - Create user (register)
│   ├── /{user_id}
│   │   ├── GET      - Get user profile
│   │   ├── PUT      - Update profile
│   │   ├── DELETE   - Delete profile
│   │   ├── /swings
│   │   │   ├── GET  - List user's swings
│   │   │   └── /{swing_id}
│   │   │       ├── GET - Get swing details
│   │   │       └── DELETE - Delete swing
│   │   ├── /progression
│   │   │   └── GET - Get progression chart data
│   │   └── /baseline
│   │       └── GET - Get baseline metrics
│   │
│   └── /me
│       └── GET      - Get current user (requires auth)
│
├── /videos
│   ├── POST /upload      - Upload video for analysis
│   ├── /{job_id}
│   │   ├── /status       - GET: Check processing status
│   │   └── /results      - GET: Retrieve analysis results
│   │
│   └── /list             - GET: List all videos (paginated)
│
├── /frame
│   ├── POST /analyze     - Analyze single frame
│   └── POST /batch       - Batch frame analysis
│
├── /feedback
│   ├── /{swing_id}       - GET: Get feedback for swing
│   ├── /suggestions      - GET: Next session focus areas
│   └── /personalized     - POST: Generate personalized feedback
│
├── /camera
│   ├── /classify         - POST: Classify camera angle
│   ├── /correct          - POST: Apply angle correction
│   └── /supported_angles - GET: List supported angles
│
├── /ws
│   └── /stream           - WebSocket: Real-time analysis
│
└── /health               - GET: API health check
```

---

## Feedback Generation Decision Tree

```
User submits swing for analysis
  │
  └─> Baseline exists for user?
      │
      ├─ NO (First swing)
      │  │
      │  └─> Generate BASELINE FEEDBACK
      │      ├─> Identify key features
      │      ├─> Note faults/strengths
      │      ├─> Store as baseline
      │      └─> Encourage continued practice
      │
      └─ YES (Follow-up swing)
         │
         └─> Compare to baseline
            ├─> Metrics improved?
            │  ├─ YES → Highlight improvements
            │  └─ NO  → Identify regression areas
            │
            ├─> New faults?
            │  ├─ YES → Address them
            │  └─ NO  → Continue focus
            │
            ├─> Faults resolved?
            │  ├─ YES → Celebrate progress
            │  └─ NO  → Refine approach
            │
            └─> Generate COMPARISON FEEDBACK
               ├─> Built on user's history
               ├─> Acknowledges individual differences
               ├─> No numeric grading
               ├─> Actionable suggestions
               └─> Encourages progress
```

---

## Performance Scaling Strategy

```
Frame 1-5: Light Faults Only
  ├─ Head movement
  ├─ Slide/sway
  └─ Performance: ~30-50ms

Frame 6-15: Add Heavy Faults (every 5th frame)
  ├─ Add over-the-top
  ├─ Add early-extension
  └─ Performance: ~150-200ms (less frequent)

Frame 16-30: Add Metrics (every 15 frames)
  ├─ Compute swing tempo
  ├─ Compute hip rotation
  └─ Performance: ~100-150ms (every 15 frames)

Every 30 frames: LLM Feedback (async)
  ├─ Generate personalized feedback
  ├─ NO BLOCKING: happens in background
  └─ Update delivered when ready
```

---

## Configuration Levels

```
┌─────────────────────────────────────────┐
│   Level 1: Default Config (YAML)        │
│  (default_config.yaml, bundled)         │
└──────────────┬──────────────────────────┘
               │ overridden by
               ↓
┌─────────────────────────────────────────┐
│   Level 2: Environment Variables        │
│  (set via .env or system)               │
└──────────────┬──────────────────────────┘
               │ overridden by
               ↓
┌─────────────────────────────────────────┐
│   Level 3: User Config (Database)       │
│  (per-user settings, Phase 6)           │
└──────────────┬──────────────────────────┘
               │ overridden by
               ↓
┌─────────────────────────────────────────┐
│  Level 4: Runtime Overrides             │
│  (API parameters, command-line args)    │
└─────────────────────────────────────────┘

Example:
Default: {head_movement_threshold: 0.04}
  ↓
.env: HEAD_MOVEMENT_THRESHOLD=0.05
  ↓
Database: user_config.threshold=0.06
  ↓
API call: ?threshold=0.07
  ↓
Final: 0.07 (most specific wins)
```

---

## Migration Path: Legacy → Modular

### Phase 1 Compatibility

```
main.py (unchanged externally)
  └─> GolfAssistant.run()
      │
      ├─ LEGACY PATH (backward compatible)
      │  └─> Uses original functions if not refactored
      │
      └─ NEW PATH (gradually adopted)
         └─> Uses FaultRegistry, MetricRegistry
            ├─ Falls back to legacy if not registered
            └─ Emits deprecation warnings

assistant.py
  ├─ OLD CODE REMAINS (commented/marked deprecated)
  ├─ NEW CODE USES REGISTRIES
  └─ Compatibility shim: FaultRegistry.get(name)
     └─ If not found, try legacy function
```

### Gradual Refactoring Timeline

**Week 1**: Register existing faults
- HeadMovementFault → FaultRegistry
- SlideSway Fault → FaultRegistry
- Old functions still work (wrapper calls)

**Week 2**: Migrate assistant.py
- Remove hardcoded fault calls
- Use FaultRegistry instead
- Keep fallback to legacy

**Week 3**: Remove legacy code
- Delete old functions
- All code uses registries
- Update tests

---

## Testing Strategy

### Unit Test Coverage

```
src/faults/
  ├── test_fault_registry.py
  │   ├── test_register()
  │   ├── test_get()
  │   ├── test_list_all()
  │   └── test_duplicate_registration_raises()
  │
  └── fault_detectors/
      ├── test_head_movement.py
      │   ├── test_no_movement()
      │   ├── test_movement_detected()
      │   ├── test_confidence_scoring()
      │   └── test_severity_classification()
      │
      └── test_slide_sway.py
          ├── test_no_sway()
          ├── test_sway_detected()
          └── ...

src/metrics/
  ├── test_metric_registry.py
  │   └── ... (similar structure)
  │
  └── swing_metrics/
      ├── test_swing_tempo.py
      └── ... (each metric)

api/
  ├── test_routes_users.py
  │   ├── test_create_user()
  │   ├── test_get_user()
  │   ├── test_update_user()
  │   └── test_invalid_user_raises()
  │
  ├── test_routes_videos.py
  │   ├── test_upload_video()
  │   ├── test_get_status()
  │   └── test_invalid_job_id()
  │
  └── test_routes_feedback.py
      ├── test_personalized_feedback()
      └── test_baseline_comparison()
```

### Integration Tests

```
test/integration/
├── test_full_pipeline.py
│   ├── test_end_to_end_video_analysis()
│   ├── test_fault_detection_results()
│   ├── test_metrics_computation()
│   └── test_feedback_generation()
│
├── test_api_endpoints.py
│   ├── test_upload_and_process_video()
│   ├── test_user_creation_and_profile()
│   └── test_websocket_streaming()
│
└── test_feedback_generation.py
    ├── test_personalized_feedback_first_swing()
    ├── test_personalized_feedback_comparison()
    └── test_llm_prompt_generation()
```

---

## Key Metrics

### Code Metrics

| Metric | Before | After (Phase 1) |
|--------|--------|-----------------|
| Files | 15 | 35+ |
| Lines of code | 2,500 | 3,500 (more modular) |
| Cyclomatic complexity | High (assistant.py) | Low (each module) |
| Test coverage | ~10% | 80%+ |
| Time to add fault | 3-4 hours | 15 minutes |

### Performance Metrics

| Operation | Before | After |
|-----------|--------|-------|
| Video analysis (1 min) | 45 seconds | 40 seconds (fewer hardcoded calls) |
| Fault detection | Not measured | <50ms per fault |
| Metric computation | Not measured | <20ms per metric |
| Real-time frame | Not supported | 30-60ms (Phase 4) |

---

## Summary

**Current System**: Monolithic, difficult to extend
**Proposed System**: Modular, plugin-based, easily extensible

**Key Benefits**:
✅ Add faults/metrics without touching core pipeline
✅ Configuration-driven behavior
✅ Fully testable components
✅ FastAPI ready for full-stack
✅ Supports personalized feedback (no grading)
✅ Scalable to real-time with async processing

**Timeline**: 8 weeks to production-ready full-stack system
