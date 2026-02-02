# Implementation Checklist - Phase 1 through Phase 6

## Overview

This checklist provides a complete task breakdown for implementing all 6 planned enhancements. Track progress by marking items as you complete them.

---

## PHASE 1: Foundation (Weeks 1-2)

### Directory Structure & Setup
- [ ] Create `src/` directory structure (14 subdirectories)
- [ ] Create `api/` directory structure (routes, schemas, middleware)
- [ ] Create `test/` directory structure (unit, integration, fixtures)
- [ ] Create `config/`, `scripts/`, `logs/`, `out/` directories
- [ ] Initialize all `__init__.py` files in source modules

### Base Classes & Registries
- [ ] Create `src/faults/base_fault.py` with `BaseFault` and `FaultResult`
- [ ] Create `src/faults/fault_registry.py` with registry pattern
- [ ] Create `src/metrics/base_metric.py` with `BaseMetric` and `MetricResult`
- [ ] Create `src/metrics/metric_registry.py` with registry pattern
- [ ] Create `config/default_config.yaml` with configuration schema

### Refactor Existing Faults
- [ ] Move `detect_head_movement` to `src/faults/fault_detectors/head_movement.py`
- [ ] Refactor to inherit from `BaseFault`, return `FaultResult`
- [ ] Add confidence score computation
- [ ] Add severity classification
- [ ] Create unit tests in `test/unit/test_faults/test_head_movement.py`
- [ ] Repeat for `slide_sway` fault

### Baseline Tracking System
- [ ] Create `src/core/baseline_tracker.py` with `UserBaseline` dataclass
- [ ] Implement `BaselineTracker` with in-memory storage
- [ ] Add methods: `get_or_create_baseline()`, `set_user_info()`, `update_metrics()`
- [ ] Implement exponential moving average for metric updates

### Input Abstraction
- [ ] Create `src/input/input_source.py` with abstract `InputSource` class
- [ ] Implement `src/input/video_file_input.py` for batch processing
- [ ] Implement `src/input/webcam_input.py` for real-time capture (basic)
- [ ] Add frame queuing for pipeline stages

### Update Pipeline
- [ ] Update `assistant.py` to use `FaultRegistry` (remove hardcoded calls)
- [ ] Update `assistant.py` to use `MetricRegistry`
- [ ] Update `assistant.py` to integrate `BaselineTracker`
- [ ] Update `main.py` to support configuration file
- [ ] Verify backwards compatibility with existing videos

### API Foundation
- [ ] Create `api/app.py` with FastAPI application
- [ ] Create `api/schemas.py` with Pydantic models
- [ ] Create `api/routes/users.py` with CRUD endpoints
- [ ] Create `api/routes/videos.py` with upload/status endpoints
- [ ] Create `api/routes/feedback.py` with personalization endpoints
- [ ] Add CORS middleware for frontend integration
- [ ] Create `run_api.py` for server startup

### Testing
- [ ] Create unit tests for `FaultRegistry`
- [ ] Create unit tests for `MetricRegistry`
- [ ] Create unit tests for existing faults (refactored)
- [ ] Create integration tests for full pipeline
- [ ] Create API endpoint tests
- [ ] Achieve >80% code coverage

### Documentation
- [ ] Update README with new architecture
- [ ] Create developer guide for adding faults
- [ ] Create API documentation (OpenAPI/Swagger)
- [ ] Document configuration system
- [ ] Document baseline tracking

### Completion Verification
- [ ] All existing functionality works with new structure
- [ ] Video analysis produces same output as before
- [ ] Configuration system functional
- [ ] API server runs without errors
- [ ] Basic WebSocket connection works
- [ ] Unit tests pass (>80% coverage)

**Phase 1 Completion: You can easily add new faults and metrics!**

---

## PHASE 2: New Faults & Metrics (Weeks 3-4)

### New Fault: Over-The-Top
- [ ] Create `src/faults/fault_detectors/over_the_top.py`
- [ ] Implement shoulder plane angle computation
- [ ] Implement club plane approximation
- [ ] Compute plane deviation score
- [ ] Register in `src/faults/__init__.py`
- [ ] Create unit tests
- [ ] Add to configuration as optional
- [ ] Create feedback template for this fault

### New Fault: Early Extension
- [ ] Create `src/faults/fault_detectors/early_extension.py`
- [ ] Compute spine angle at address and impact
- [ ] Compute hip extension pattern
- [ ] Detect early straightening (before impact)
- [ ] Register and test
- [ ] Create feedback template

### New Metric: Swing Tempo
- [ ] Create `src/metrics/swing_metrics/swing_tempo.py`
- [ ] Compute total swing duration
- [ ] Normalize to seconds
- [ ] Add confidence from keypoint visibility
- [ ] Register in `src/metrics/__init__.py`
- [ ] Create unit tests
- [ ] Document "no ideal tempo" (body-type dependent)

### New Metric: Hip Rotation
- [ ] Create `src/metrics/swing_metrics/hip_rotation.py`
- [ ] Compute hip angle at address and peak rotation
- [ ] Measure rotation range in degrees
- [ ] Add confidence scoring
- [ ] Register and test
- [ ] Document variation by flexibility

### New Metric: Shoulder Turn
- [ ] Create `src/metrics/swing_metrics/shoulder_turn.py`
- [ ] Compute shoulder angle at address and peak
- [ ] Normalize by body type
- [ ] Create unit tests

### New Metric: Weight Shift
- [ ] Create `src/metrics/swing_metrics/weight_shift.py`
- [ ] Track hip position from address to impact
- [ ] Measure lateral and forward displacement
- [ ] Add confidence from hip visibility
- [ ] Create unit tests

### Configuration Updates
- [ ] Add thresholds for new faults to `default_config.yaml`
- [ ] Add new metrics to enabled list
- [ ] Create alternative configs (beginner, intermediate, advanced)

### Feedback Engine Enhancement
- [ ] Update `src/feedback/personalized_feedback.py` for new faults
- [ ] Add body-type-specific suggestions for each fault
- [ ] Create feedback templates for each metric
- [ ] Implement improvement detection
- [ ] Test LLM feedback generation

### Testing
- [ ] Create comprehensive test fixtures (various swing styles)
- [ ] Unit tests for each new fault (>5 test cases each)
- [ ] Unit tests for each new metric
- [ ] Integration tests (faults + metrics together)
- [ ] API tests with new endpoints

### Documentation
- [ ] Document each new fault (detection logic, thresholds, severity)
- [ ] Document each new metric (computation, units, interpretation)
- [ ] Create visual guides for fault types
- [ ] Update API documentation

**Phase 2 Completion: Rich fault/metric analysis with personalized feedback!**

---

## PHASE 3: Camera Handling (Week 5)

### Camera Angle Detection
- [ ] Create `src/camera/angle_classifier.py`
- [ ] Implement angle classification (side-on, down-the-line, 45-degree)
- [ ] Train/use lightweight classifier model
- [ ] Add confidence scores

### Camera Angle Correction
- [ ] Create `src/camera/angle_correction.py`
- [ ] Implement perspective transform for down-the-line correction
- [ ] Implement coordinate system adjustment per angle
- [ ] Apply to keypoint landmarks
- [ ] Apply to object detections

### Pipeline Integration
- [ ] Add camera angle detection as first pipeline stage
- [ ] Update fault detection for detected angle
- [ ] Update metric computation for detected angle
- [ ] Document detection confidence thresholds
- [ ] Add warnings for poor angle detection

### API Endpoints
- [ ] POST `/camera/classify` - classify camera angle from frame
- [ ] POST `/camera/correct` - apply angle correction
- [ ] GET `/camera/supported_angles` - list supported angles

### Testing
- [ ] Test classification accuracy on test videos
- [ ] Test coordinate transform correctness
- [ ] Test with various camera angles
- [ ] Create test fixtures for each angle

### Documentation
- [ ] Document supported camera angles
- [ ] Document detection accuracy
- [ ] Document coordinate system transformations
- [ ] Create user guide for optimal camera placement

**Phase 3 Completion: Works with any camera angle!**

---

## PHASE 4: Real-Time Video Capture (Week 6)

### Live Input Implementation
- [ ] Complete `src/input/webcam_input.py`
- [ ] Add frame buffering for pipeline stages
- [ ] Implement thread-safe frame queue
- [ ] Add FPS monitoring and reporting

### Real-Time Pipeline Adaptation
- [ ] Create `src/processing/real_time_pipeline.py`
- [ ] Implement frame skipping (process every Nth frame)
- [ ] Add output buffering for video writing
- [ ] Handle variable frame rates

### WebSocket Enhancement
- [ ] Upgrade `/ws/stream` for video frame streaming
- [ ] Implement client-side frame encoding (base64)
- [ ] Add real-time feedback delivery
- [ ] Implement latency monitoring

### Frontend Integration
- [ ] Create basic web UI for live capture
- [ ] Implement webcam access (HTML5 getUserMedia)
- [ ] Add frame capture and WebSocket sending
- [ ] Display real-time feedback
- [ ] Display current metrics

### Performance Optimization (Real-Time)
- [ ] Profile frame processing time per stage
- [ ] Optimize inference for <33ms (30 FPS)
- [ ] Implement lazy loading for non-critical metrics
- [ ] Add GPU fallback option (if available)

### Testing
- [ ] Test with various webcam resolutions
- [ ] Test network latency impact
- [ ] Test frame drop handling
- [ ] Load test (multiple concurrent streams)

### Documentation
- [ ] Create real-time system architecture guide
- [ ] Document latency requirements
- [ ] Create troubleshooting guide

**Phase 4 Completion: Live swing analysis with real-time feedback!**

---

## PHASE 5: Performance Optimization (Week 7)

### Profiling
- [ ] Profile current pipeline (frame timing breakdown)
- [ ] Identify bottlenecks per stage
- [ ] Measure memory usage
- [ ] Document baseline performance

### Inference Optimization
- [ ] Test quantized pose model (int8)
- [ ] Test model pruning options
- [ ] Benchmark different MediaPipe model sizes
- [ ] Consider lightweight alternatives (FastPose, etc.)

### Pipeline Optimization
- [ ] Implement frame batching where applicable
- [ ] Add caching for stable detections
- [ ] Reduce unnecessary computations
- [ ] Parallel processing for independent stages

### Input/Output Optimization
- [ ] Optimize video decoding (hardware acceleration if available)
- [ ] Implement streaming output (no full-buffer requirement)
- [ ] Optimize JSON serialization

### API Optimization
- [ ] Add response caching (Redis/in-memory)
- [ ] Implement pagination for results
- [ ] Add compression for API responses
- [ ] Optimize database queries (Phase 6)

### Testing
- [ ] Benchmark before and after optimizations
- [ ] Test on low-end hardware (Raspberry Pi, etc.)
- [ ] Load test with concurrent requests
- [ ] Memory leak testing

### Documentation
- [ ] Document performance characteristics
- [ ] Create optimization guide for custom setups
- [ ] Document hardware requirements

**Phase 5 Completion: Real-time performance on modest hardware!**

---

## PHASE 6: Database & Deployment (Week 8)

### Database Setup
- [ ] Choose database (PostgreSQL recommended)
- [ ] Create SQLAlchemy models for users, swings, baselines
- [ ] Create migration scripts (Alembic)
- [ ] Design schema for historical tracking

### API Enhancement
- [ ] Replace in-memory baseline with database
- [ ] Add persistence for user profiles
- [ ] Add swing history storage
- [ ] Implement user authentication (JWT)
- [ ] Add role-based access control

### Analytics
- [ ] Create analytics endpoints (progression over time)
- [ ] Implement dashboard data aggregation
- [ ] Add export functionality (CSV, PDF)
- [ ] Create visualization helpers

### Frontend Development
- [ ] Create React/Vue app
- [ ] Implement user login/registration
- [ ] Implement video upload interface
- [ ] Create live capture interface
- [ ] Create dashboard with progress visualization
- [ ] Implement feedback display

### Deployment
- [ ] Create Docker container for API
- [ ] Create docker-compose for full stack
- [ ] Set up CI/CD pipeline (GitHub Actions, etc.)
- [ ] Deploy to cloud (AWS, Azure, GCP)
- [ ] Set up monitoring and logging

### Security
- [ ] Implement input validation (all endpoints)
- [ ] Add rate limiting
- [ ] Secure database credentials (environment variables)
- [ ] Implement HTTPS/SSL
- [ ] Regular security audits

### Testing
- [ ] Integration tests (full stack)
- [ ] Load testing
- [ ] Security testing
- [ ] UI/UX testing

### Documentation
- [ ] Create deployment guide
- [ ] Create system administrator guide
- [ ] Create user manual
- [ ] Create API reference (final)

**Phase 6 Completion: Production-ready full-stack system!**

---

## Cross-Phase Tasks

### Code Quality
- [ ] Linting (pylint, black)
- [ ] Type checking (mypy)
- [ ] Code review process
- [ ] Refactoring passes

### Testing Throughout
- [ ] Unit tests (every module)
- [ ] Integration tests (every phase)
- [ ] End-to-end tests
- [ ] Performance tests
- [ ] Security tests

### Documentation Throughout
- [ ] Docstrings for all functions
- [ ] README updates per phase
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Developer guides

### Dependency Management
- [ ] Keep requirements.txt updated
- [ ] Monitor security advisories
- [ ] Plan major version upgrades
- [ ] Test dependency changes

---

## Success Metrics

### Phase 1
- ✅ 80%+ test coverage
- ✅ All existing features working
- ✅ New faults can be added with <100 lines of code

### Phase 2
- ✅ 4 new faults implemented
- ✅ 3 new metrics implemented
- ✅ Personalized feedback generation working
- ✅ 90%+ test coverage

### Phase 3
- ✅ Camera angle detection >90% accuracy
- ✅ Fault detection works across all supported angles
- ✅ Minimal performance impact

### Phase 4
- ✅ Live capture working at 30 FPS
- ✅ Feedback latency <500ms
- ✅ Concurrent users supported

### Phase 5
- ✅ Analysis <33ms per frame (30 FPS)
- ✅ Works on low-end hardware
- ✅ Memory usage <500MB

### Phase 6
- ✅ System deployed and accessible
- ✅ 99%+ uptime
- ✅ Full user flow working

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Scope creep | Strict phase adherence |
| Performance issues | Early profiling in Phase 1 |
| Integration problems | Continuous integration testing |
| Deployment challenges | Docker from Phase 1 |
| User adoption | Early frontend feedback |
| Data privacy | Security audit before Phase 6 |

---

## Timeline Summary

```
Week 1-2: Phase 1 (Foundation)
Week 3-4: Phase 2 (Faults + Metrics)
Week 5:   Phase 3 (Camera)
Week 6:   Phase 4 (Real-Time)
Week 7:   Phase 5 (Performance)
Week 8:   Phase 6 (Deployment)

Total: 8 weeks for complete system
```

**You're ready to start Phase 1! Pick the first item on the checklist and get started.**
