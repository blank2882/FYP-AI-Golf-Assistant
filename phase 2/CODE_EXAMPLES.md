# Code Examples: Monolithic vs. Modular

## Example 1: Adding a New Fault

### BEFORE (Current Monolithic Approach)

**Current: `faultDetect.py`**

```python
def detect_head_movement(kps_seq, address_frame, impact_frame, head_threshold=0.04):
    """Detect head movement during swing"""
    # ... computation ...
    return is_fault, score

def detect_slide_or_sway(kps_seq, address_frame, impact_frame, lateral_threshold=0.12):
    """Detect lateral body movement"""
    # ... computation ...
    return is_fault, score

# To add "over_the_top" fault, you must:
# 1. Write function in faultDetect.py
# 2. Import in assistant.py
# 3. Add call in assistant.run()
# 4. Update faults list in main
# 5. Handle in feedback generation
# 6. Test everywhere

def detect_over_the_top(kps_seq, address_frame, impact_frame, threshold=0.15):
    """Detect over-the-top swing plane (NEW)"""
    # Complex logic mixing detection with orchestration
    shoulder_angle = compute_shoulder_angle(kps_seq, address_frame)
    elbow_angle = compute_elbow_angle(kps_seq, address_frame)
    
    # Hard to test in isolation
    # Hard to reuse in different contexts
    if shoulder_angle > threshold:
        return True, shoulder_angle
    return False, 0.0
```

**In `assistant.py`:**
```python
# Have to manually call each fault detector
def run_fault_detection(self):
    head_fault, head_score = faultDetect.detect_head_movement(...)
    sway_fault, sway_score = faultDetect.detect_slide_or_sway(...)
    over_top_fault, over_top_score = faultDetect.detect_over_the_top(...)  # NEW
    
    # Manual aggregation
    self.faults = {
        'head_movement': {'detected': head_fault, 'score': head_score},
        'slide_sway': {'detected': sway_fault, 'score': sway_score},
        'over_the_top': {'detected': over_top_fault, 'score': over_top_score}  # NEW
    }
```

**Problems with this approach:**
❌ Adding fault requires changes in multiple files
❌ No standardized interface
❌ Confidence scores not consistently handled
❌ Hardcoded in orchestration
❌ Difficult to enable/disable faults dynamically
❌ Testing requires mocking entire pipeline

---

### AFTER (Modular Registry Approach)

**Create: `src/faults/fault_detectors/over_the_top.py`**

```python
import numpy as np
from src.faults.base_fault import BaseFault, FaultResult


class OverTheTopFault(BaseFault):
    """Detects over-the-top swing plane fault
    
    An over-the-top swing occurs when the club shaft angle
    exceeds the shoulder plane at the start of the downswing.
    This results in an out-to-in swing path.
    """
    
    def __init__(self, threshold: float = 0.15):
        super().__init__(threshold=threshold)
    
    def detect(self,
               keypoints_seq: np.ndarray,
               address_frame: int = 0,
               impact_frame: int = None,
               **kwargs) -> FaultResult:
        """Detect over-the-top at top of backswing"""
        super().detect(keypoints_seq, address_frame, impact_frame)
        
        # Find approximate top of swing (highest right elbow)
        right_elbow_idx = 14
        elbow_y_values = keypoints_seq[:, right_elbow_idx, 1]
        top_swing_frame = int(np.argmin(elbow_y_values))
        
        # Compute shoulder plane
        shoulder_angle = self._compute_shoulder_angle(keypoints_seq, address_frame)
        
        # Compute club plane (approximated from elbow-hand angle)
        club_plane = self._compute_club_plane(keypoints_seq, top_swing_frame)
        
        # Compute deviation
        plane_deviation = club_plane - shoulder_angle
        normalized_score = min(abs(plane_deviation) / self.threshold, 1.0)
        
        # Confidence from elbow visibility
        confidence = float(keypoints_seq[top_swing_frame, right_elbow_idx, 2])
        
        # Severity
        severity = "low" if normalized_score < 0.4 else \
                   "medium" if normalized_score < 0.7 else "high"
        
        return FaultResult(
            detected=normalized_score > self.threshold,
            score=normalized_score,
            confidence=confidence,
            severity=severity,
            details={
                'shoulder_angle': float(shoulder_angle),
                'club_plane': float(club_plane),
                'plane_deviation': float(plane_deviation),
                'top_of_swing_frame': int(top_swing_frame)
            }
        )
    
    @staticmethod
    def _compute_shoulder_angle(kps: np.ndarray, frame: int) -> float:
        """Compute shoulder angle relative to horizontal"""
        left_shoulder = kps[frame, 11, :2]
        right_shoulder = kps[frame, 12, :2]
        
        angle = np.arctan2(
            right_shoulder[1] - left_shoulder[1],
            right_shoulder[0] - left_shoulder[0]
        )
        return float(np.degrees(angle))
    
    @staticmethod
    def _compute_club_plane(kps: np.ndarray, frame: int) -> float:
        """Approximate club plane from right arm position"""
        right_elbow = kps[frame, 14, :2]
        right_wrist = kps[frame, 16, :2]
        
        angle = np.arctan2(
            right_wrist[1] - right_elbow[1],
            right_wrist[0] - right_elbow[0]
        )
        return float(np.degrees(angle))
    
    def get_name(self) -> str:
        return "over_the_top"
    
    def get_description(self) -> str:
        return "Over-the-top swing plane (outside-to-in path)"
```

**Register in: `src/faults/__init__.py`**

```python
from src.faults.fault_detectors.over_the_top import OverTheTopFault

# Add one line:
FaultRegistry.register('over_the_top', OverTheTopFault)
```

**Use in pipeline: `assistant.py` (unchanged!)**

```python
def run_fault_detection(self):
    """No changes needed - works with any registered fault!"""
    fault_results = {}
    
    # Dynamically instantiate all registered faults
    for fault_name in FaultRegistry.list_all():
        if fault_name not in self.config['enabled_faults']:
            continue  # Skip disabled faults
        
        detector = FaultRegistry.get(fault_name)
        result = detector.detect(
            keypoints_seq=self.keypoints_seq,
            address_frame=self.address_frame,
            impact_frame=self.impact_frame
        )
        
        fault_results[fault_name] = result.to_dict()
    
    self.faults = fault_results
```

**Unit test: `test/unit/test_faults/test_over_the_top.py`**

```python
import pytest
import numpy as np
from src.faults.fault_detectors.over_the_top import OverTheTopFault


@pytest.fixture
def keypoints_over_the_top():
    """Keypoints simulating over-the-top motion"""
    T, J = 60, 33
    kps = np.random.rand(T, J, 3) * 0.1 + 0.45
    
    # Create artificial over-the-top pattern
    # (club plane > shoulder plane)
    for t in range(30, 45):  # Top of swing
        frame_progress = (t - 30) / 15
        kps[t, 14, 0] = 0.6 - 0.15 * frame_progress  # Elbow moves out
        kps[t, 16, 0] = 0.7 - 0.2 * frame_progress   # Wrist follows
    
    return kps


def test_over_the_top_detection(keypoints_over_the_top):
    """Test fault is detected"""
    detector = OverTheTopFault(threshold=0.12)
    result = detector.detect(keypoints_over_the_top)
    
    assert result.detected
    assert result.score > detector.threshold
    assert result.severity in ["low", "medium", "high"]


def test_over_the_top_confidence(keypoints_over_the_top):
    """Test confidence score reflects visibility"""
    detector = OverTheTopFault()
    result = detector.detect(keypoints_over_the_top)
    
    assert 0 <= result.confidence <= 1
```

**Benefits of modular approach:**
✅ New fault is self-contained, testable in isolation
✅ No changes to existing code required
✅ Fault can be enabled/disabled via configuration
✅ Standardized interface (FaultResult with score + confidence)
✅ Easy to add to pipeline dynamically
✅ Easy to version and package independently

---

## Example 2: Adding a New Metric

### BEFORE (Current Monolithic)

```python
# In faultDetect.py - mixing concerns
def compute_swing_metrics(kps_seq, address_frame, impact_frame):
    """Compute hardcoded set of metrics"""
    # These return simple float values with no metadata
    swing_tempo = compute_tempo(kps_seq, address_frame, impact_frame)
    backswing_time = impact_frame - address_frame
    
    # Hard to add new metric - requires modifying function
    # Hard to test individual metrics
    # Hard to get confidence/unit information
    return {
        'swing_tempo': swing_tempo,
        'backswing_time': backswing_time
    }

def compute_tempo(kps_seq, address_frame, impact_frame):
    """Compute swing tempo (frames per second)"""
    duration = (impact_frame - address_frame) / 30.0  # Hardcoded FPS
    return 1.0 / duration if duration > 0 else 0.0
```

---

### AFTER (Modular Registry)

**Create: `src/metrics/swing_metrics/swing_tempo.py`**

```python
import numpy as np
from src.metrics.base_metric import BaseMetric, MetricResult


class SwingTempoMetric(BaseMetric):
    """Measures swing tempo in seconds
    
    Swing tempo is the total time from address to follow-through.
    Professional golfers typically have tempos of 1.2-1.5 seconds.
    
    This metric is presented WITHOUT judgment - individual factors
    like body type, flexibility, and strength affect ideal tempo.
    """
    
    def __init__(self, fps: float = 30.0):
        self.fps = fps
    
    def compute(self,
                keypoints_seq: np.ndarray,
                address_frame: int = 0,
                impact_frame: int = None,
                **kwargs) -> MetricResult:
        """Compute swing tempo"""
        if impact_frame is None:
            impact_frame = keypoints_seq.shape[0] - 1
        
        duration_frames = impact_frame - address_frame
        duration_seconds = duration_frames / self.fps
        
        # Confidence from keypoint consistency
        nose_confidence = float(np.mean(
            keypoints_seq[address_frame:impact_frame, 0, 2]
        ))
        
        return MetricResult(
            name=self.get_name(),
            value=duration_seconds,
            unit=self.get_unit(),
            confidence=nose_confidence,
            details={
                'duration_frames': int(duration_frames),
                'fps': self.fps,
                'address_frame': int(address_frame),
                'impact_frame': int(impact_frame)
            }
        )
    
    def get_name(self) -> str:
        return "swing_tempo"
    
    def get_description(self) -> str:
        return "Total time from address to impact (seconds)"
    
    def get_unit(self) -> str:
        return "seconds"
```

**Create: `src/metrics/swing_metrics/hip_rotation.py`**

```python
import numpy as np
from src.metrics.base_metric import BaseMetric, MetricResult


class HipRotationMetric(BaseMetric):
    """Measures hip rotation during backswing
    
    Hip rotation varies by flexibility and body type.
    No "ideal" number - context-specific to each golfer.
    """
    
    def compute(self,
                keypoints_seq: np.ndarray,
                address_frame: int = 0,
                impact_frame: int = None,
                **kwargs) -> MetricResult:
        """Compute hip rotation angle"""
        
        # Find peak hip rotation (typically mid-backswing)
        hip_angles = []
        for t in range(address_frame, impact_frame or keypoints_seq.shape[0]):
            angle = self._compute_hip_angle(keypoints_seq, t)
            hip_angles.append(angle)
        
        max_rotation = float(max(hip_angles))
        
        # Confidence from hip visibility
        left_hip_conf = float(keypoints_seq[address_frame, 23, 2])
        right_hip_conf = float(keypoints_seq[address_frame, 24, 2])
        confidence = (left_hip_conf + right_hip_conf) / 2
        
        return MetricResult(
            name=self.get_name(),
            value=max_rotation,
            unit=self.get_unit(),
            confidence=confidence,
            details={
                'rotation_range': [float(min(hip_angles)), max_rotation],
                'peak_frame': int(np.argmax(hip_angles) + address_frame)
            }
        )
    
    @staticmethod
    def _compute_hip_angle(kps: np.ndarray, frame: int) -> float:
        """Compute hip rotation angle"""
        left_hip = kps[frame, 23, :2]  # MediaPipe landmark
        right_hip = kps[frame, 24, :2]
        
        angle = np.arctan2(
            right_hip[1] - left_hip[1],
            right_hip[0] - left_hip[0]
        )
        return float(np.degrees(angle))
    
    def get_name(self) -> str:
        return "hip_rotation"
    
    def get_description(self) -> str:
        return "Maximum hip rotation during backswing (degrees)"
    
    def get_unit(self) -> str:
        return "degrees"
```

**Register in: `src/metrics/__init__.py`**

```python
from src.metrics.swing_metrics.swing_tempo import SwingTempoMetric
from src.metrics.swing_metrics.hip_rotation import HipRotationMetric

MetricRegistry.register('swing_tempo', SwingTempoMetric)
MetricRegistry.register('hip_rotation', HipRotationMetric)
```

**Use in pipeline: `assistant.py`**

```python
def run_metrics_computation(self):
    """Compute all registered metrics"""
    metrics_results = {}
    
    for metric_name in MetricRegistry.list_all():
        if metric_name not in self.config['enabled_metrics']:
            continue
        
        metric = MetricRegistry.get(metric_name, fps=self.fps)
        result = metric.compute(
            keypoints_seq=self.keypoints_seq,
            address_frame=self.address_frame,
            impact_frame=self.impact_frame
        )
        
        metrics_results[metric_name] = {
            'value': result.value,
            'unit': result.unit,
            'confidence': result.confidence,
            'details': result.details
        }
    
    self.metrics = metrics_results
```

---

## Example 3: Personalized Feedback Generation

### BEFORE (No Personalization)

```python
# In llm_feedback.py
def generate_feedback(faults: dict, metrics: dict) -> str:
    """Generate generic feedback"""
    
    feedback = "Your swing analysis:\n\n"
    
    if faults['head_movement']['detected']:
        feedback += "- Head movement detected\n"
    
    if faults['slide_sway']['detected']:
        feedback += "- Body sway detected\n"
    
    return feedback  # Same for everyone!
```

---

### AFTER (Baseline-Aware, Body-Type Aware)

**File: `src/feedback/personalized_feedback.py`**

```python
from typing import Dict, Optional
from src.core.baseline_tracker import UserBaseline
from llm_feedback import generate_feedback as llm_generate


class PersonalizedFeedbackEngine:
    """Generate feedback tailored to individual golfer"""
    
    def __init__(self, baseline_tracker):
        self.baseline_tracker = baseline_tracker
    
    def generate(self,
                 user_id: str,
                 faults: Dict,
                 metrics: Dict,
                 swing_phase: str = "full_swing") -> Dict:
        """Generate personalized feedback
        
        Key principle: Compare to THIS USER'S baseline, not "perfect" form
        """
        
        baseline = self.baseline_tracker.get_or_create_baseline(user_id)
        
        # Step 1: Determine if this is first swing
        is_first_swing = len(baseline.swing_metrics) == 0
        
        if is_first_swing:
            feedback = self._generate_baseline_swing_feedback(
                faults, metrics, baseline
            )
        else:
            feedback = self._generate_comparison_feedback(
                faults, metrics, baseline
            )
        
        return feedback
    
    def _generate_baseline_swing_feedback(self, faults: Dict, 
                                         metrics: Dict,
                                         baseline: UserBaseline) -> Dict:
        """Feedback for user's first swing (establish baseline)"""
        
        fault_list = [
            f"{fault_name} (severity: {fault['severity']})"
            for fault_name, fault in faults.items()
            if fault['detected']
        ]
        
        # Build prompt for LLM
        prompt = f"""
        This is a golfer's FIRST swing analysis. Create a baseline assessment.
        
        Body type: {baseline.body_type or 'not specified'}
        
        Detected issues: {', '.join(fault_list) if fault_list else 'None'}
        
        Key instruction: Do NOT grade this swing. Instead:
        1. Observe what's happening in the swing
        2. Identify 2-3 areas to focus on (not "wrong", just areas for development)
        3. Highlight what's already working well
        4. Give specific, actionable tips
        5. Frame everything positively
        
        Example of GOOD feedback: "Your hip rotation is solid. To improve consistency, 
        focus on keeping your head steady through impact. Try this drill..."
        
        Example of BAD feedback: "Your swing is 6/10. Fix your head movement."
        """
        
        return {
            'type': 'baseline_establishment',
            'general_observations': f"{len(fault_list)} areas identified to work on",
            'strengths': ['Completed a full swing', 'Good swing rhythm'],
            'areas_to_improve': fault_list[:3],  # Top 3 issues
            'suggestions': self._generate_suggestions(faults, baseline),
            'comparison_to_baseline': None  # First swing
        }
    
    def _generate_comparison_feedback(self, faults: Dict,
                                      metrics: Dict,
                                      baseline: UserBaseline) -> Dict:
        """Feedback comparing to user's baseline"""
        
        # Compare metrics to baseline
        improvements = []
        regressions = []
        
        for metric_name, current_value in metrics.items():
            baseline_value = baseline.swing_metrics.get(metric_name)
            
            if baseline_value is None:
                continue
            
            # Simple comparison (directional)
            if self._is_improvement(metric_name, current_value, baseline_value):
                improvements.append(f"{metric_name}: improved")
            elif self._is_regression(metric_name, current_value, baseline_value):
                regressions.append(f"{metric_name}: changed")
        
        # Detect fault changes
        new_faults = self._get_new_faults(faults, baseline)
        resolved_faults = self._get_resolved_faults(faults, baseline)
        
        prompt = f"""
        Golfer swing comparison (current vs their personal baseline):
        
        Improvements: {improvements or 'None'}
        Regressions: {regressions or 'None'}
        
        Faults resolved since last swing: {resolved_faults or 'None'}
        New faults appearing: {new_faults or 'None'}
        
        Body type: {baseline.body_type}
        
        Generate feedback that:
        1. Celebrates improvements made since last swing
        2. Acknowledges work on resolved faults
        3. Recommends focus areas (but don't grade/score)
        4. Avoids comparing to "professional" standard
        5. Gives actionable next steps
        """
        
        return {
            'type': 'progression_tracking',
            'general_observations': self._summarize_progression(improvements, regressions),
            'strengths': improvements + resolved_faults,
            'areas_to_improve': regressions + new_faults,
            'suggestions': self._generate_suggestions(faults, baseline),
            'comparison_to_baseline': {
                'improvements': improvements,
                'regressions': regressions,
                'resolved_faults': resolved_faults,
                'new_faults': new_faults
            }
        }
    
    @staticmethod
    def _is_improvement(metric_name: str, current: float, baseline: float) -> bool:
        """Determine if metric improved (metric-specific)"""
        if metric_name == 'swing_tempo':
            # Closer to 1.3 seconds is better for consistency
            return abs(current - 1.3) < abs(baseline - 1.3)
        # Default: increase is improvement
        return current > baseline
    
    @staticmethod
    def _is_regression(metric_name: str, current: float, baseline: float) -> bool:
        """Determine if metric regressed"""
        return abs(current - baseline) > 0.15  # 15% change = notable
    
    def _get_new_faults(self, current_faults: Dict, baseline: UserBaseline) -> list:
        """Identify faults not seen in baseline"""
        # Would track historical fault presence
        new = [name for name, fault in current_faults.items()
               if fault['detected']]
        return new[:3]  # Top 3
    
    def _get_resolved_faults(self, current_faults: Dict, baseline: UserBaseline) -> list:
        """Identify faults that have been resolved"""
        # Would track historical fault presence
        return []  # Placeholder
    
    @staticmethod
    def _summarize_progression(improvements: list, regressions: list) -> str:
        """Summarize swing progression"""
        if improvements and not regressions:
            return f"Great work! You've improved in {len(improvements)} areas."
        elif regressions and not improvements:
            return f"Focus on {len(regressions)} areas from last swing."
        else:
            return "Your swing is developing. Keep practicing."
    
    @staticmethod
    def _generate_suggestions(faults: Dict, baseline: UserBaseline) -> list:
        """Generate body-type-aware suggestions"""
        suggestions = []
        
        for fault_name, fault in faults.items():
            if not fault['detected']:
                continue
            
            if fault_name == 'head_movement':
                suggestions.append(
                    "Keep your head steady: pick a spot on the ball and maintain focus"
                )
            elif fault_name == 'slide_sway':
                if baseline.body_type == 'ectomorph':
                    suggestions.append(
                        "For your body type, focus on weight shift over full sway. "
                        "Slight shift is normal."
                    )
                else:
                    suggestions.append(
                        "Minimize lateral sway - rotate around your spine instead"
                    )
            elif fault_name == 'over_the_top':
                suggestions.append(
                    "Keep club on plane: video record your swing and compare "
                    "to your address position"
                )
        
        return suggestions
```

**Benefits:**
✅ No numeric grading (0-100 scores)
✅ Acknowledges body type differences
✅ Compares to user's own baseline, not "perfect"
✅ Tracks progression over time
✅ Celebrates improvements
✅ Positive, actionable language

---

## Summary

| Aspect | Monolithic | Modular |
|--------|-----------|---------|
| Adding fault | Modify 3+ files | Create 1 new file + register |
| Testing | Requires full pipeline mock | Test detector in isolation |
| Enabling/disabling | Hardcoded | Configuration-driven |
| Confidence scores | Inconsistent | Standardized FaultResult |
| Feedback | Generic | Personalized + baseline-aware |
| Code reuse | Low | High |
| Extensibility | Hard | Easy |

**This is why Phase 1 matters: it enables everything else!**
