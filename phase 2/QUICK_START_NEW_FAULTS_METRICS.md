# Quick Start: Adding New Faults and Metrics

This guide shows exactly how to add new features to your refactored golf assistant.

---

## Adding a New Fault: Complete Example

### Step 1: Create the Fault File

**File: `src/faults/fault_detectors/over_the_top.py`**

```python
import numpy as np
from src.faults.base_fault import BaseFault, FaultResult


class OverTheTopFault(BaseFault):
    """Detects when club passes above shoulder plane at top of swing
    
    When the club head goes above the shoulder plane at the top of the
    backswing, it indicates poor swing plane and can lead to slices.
    """
    
    def __init__(self, threshold: float = 0.30):
        super().__init__(threshold=threshold)
    
    def detect(self, 
               keypoints_seq: np.ndarray,
               address_frame: int = 0,
               impact_frame: None = None,
               **kwargs) -> FaultResult:
        """Detect if club passes over shoulder plane"""
        super().detect(keypoints_seq, address_frame, impact_frame)
        
        T = keypoints_seq.shape[0]
        peak_frame = address_frame + int((T - address_frame) * 0.4)
        
        # Shoulder and wrist positions (MediaPipe indices)
        left_shoulder = keypoints_seq[peak_frame, 11, :2]
        right_shoulder = keypoints_seq[peak_frame, 12, :2]
        shoulder_height = max(left_shoulder[1], right_shoulder[1])
        shoulder_width = np.linalg.norm(right_shoulder - left_shoulder)
        
        left_wrist = keypoints_seq[peak_frame, 15, :2]
        right_wrist = keypoints_seq[peak_frame, 16, :2]
        wrist_height = min(left_wrist[1], right_wrist[1])
        
        excess_height = shoulder_height - wrist_height
        normalized_score = float(max(excess_height / shoulder_width, 0.0))
        
        wrist_visibility = max(
            keypoints_seq[peak_frame, 15, 2],
            keypoints_seq[peak_frame, 16, 2]
        )
        
        severity = "high" if normalized_score > 0.50 else \
                   "medium" if normalized_score > 0.25 else "low"
        
        return FaultResult(
            detected=normalized_score > self.threshold,
            score=min(normalized_score, 1.0),
            confidence=float(wrist_visibility),
            severity=severity,
            details={
                'excess_height': float(excess_height),
                'normalized_height': normalized_score,
                'peak_frame': int(peak_frame)
            }
        )
    
    def get_name(self) -> str:
        return "over_the_top"
    
    def get_description(self) -> str:
        return "Club head position at top exceeds shoulder plane"
```

### Step 2: Register the Fault

**File: `src/faults/__init__.py`**

Add these lines:
```python
from src.faults.fault_detectors.over_the_top import OverTheTopFault

FaultRegistry.register('over_the_top', OverTheTopFault)
```

### Step 3: Update Configuration

**File: `config/default_config.yaml`**

```yaml
faults:
  enabled:
    - head_movement
    - slide_sway
    - over_the_top  # ← ADD THIS
  
  thresholds:
    head_movement: 0.04
    slide_sway: 0.12
    over_the_top: 0.30  # ← ADD THIS
```

### Step 4: Write Tests

**File: `test/unit/test_faults/test_over_the_top.py`**

```python
import pytest
import numpy as np
from src.faults.fault_detectors.over_the_top import OverTheTopFault


@pytest.fixture
def normal_swing_keypoints():
    """Keypoints with proper swing plane"""
    kps = np.random.rand(30, 33, 3) * 0.1 + 0.45
    for t in range(30):
        kps[t, 11, 1] = 0.35  # Left shoulder
        kps[t, 12, 1] = 0.35  # Right shoulder
        kps[t, 15, 1] = 0.40  # Left wrist (below shoulder)
        kps[t, 16, 1] = 0.40  # Right wrist (below shoulder)
    return kps


@pytest.fixture
def over_the_top_keypoints():
    """Keypoints with over-the-top position"""
    kps = np.random.rand(30, 33, 3) * 0.1 + 0.45
    for t in range(30):
        kps[t, 11, 1] = 0.35  # Left shoulder
        kps[t, 12, 1] = 0.35  # Right shoulder
        kps[t, 15, 1] = 0.20  # Left wrist (above shoulder)
        kps[t, 16, 1] = 0.20  # Right wrist (above shoulder)
    return kps


def test_normal_swing(normal_swing_keypoints):
    """Test normal swing doesn't trigger fault"""
    detector = OverTheTopFault(threshold=0.30)
    result = detector.detect(normal_swing_keypoints)
    assert not result.detected
    assert result.score < detector.threshold


def test_over_the_top(over_the_top_keypoints):
    """Test over-the-top position is detected"""
    detector = OverTheTopFault(threshold=0.30)
    result = detector.detect(over_the_top_keypoints)
    assert result.detected
    assert result.score > detector.threshold
    assert 0 <= result.confidence <= 1
```

### Step 5: Use in Pipeline

```python
from src.faults import FaultRegistry

detector = FaultRegistry.get('over_the_top', threshold=0.30)
result = detector.detect(keypoints_sequence)

print(f"Over the top detected: {result.detected}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Severity: {result.severity}")
```

**That's it!** You've added a new fault with:
- ✅ Zero impact on existing code
- ✅ Automatically integrated into pipeline
- ✅ Tested in isolation
- ✅ Configured via YAML

---

## Adding a New Metric: Complete Example

### Step 1: Create the Metric File

**File: `src/metrics/swing_metrics/tempo.py`**

```python
import numpy as np
from src.metrics.base_metric import BaseMetric, MetricResult


class TempoMetric(BaseMetric):
    """Computes swing tempo (backswing time / downswing time)
    
    Ideal tempo is typically 3:1 or slower.
    """
    
    def compute(self,
                keypoints_seq: np.ndarray,
                address_frame: int = 0,
                impact_frame: None = None,
                fps: float = 30.0,
                **kwargs) -> MetricResult:
        """Compute swing tempo ratio"""
        T = keypoints_seq.shape[0]
        if impact_frame is None:
            impact_frame = T - 1
        
        # Find peak of swing (highest wrist position)
        wrist_heights = []
        for t in range(address_frame, impact_frame + 1):
            left_wrist_y = keypoints_seq[t, 15, 1]
            right_wrist_y = keypoints_seq[t, 16, 1]
            highest = min(left_wrist_y, right_wrist_y)
            wrist_heights.append(highest)
        
        peak_frame = address_frame + np.argmin(wrist_heights)
        
        # Compute times
        backswing_frames = peak_frame - address_frame
        downswing_frames = impact_frame - peak_frame
        
        backswing_time = backswing_frames / fps
        downswing_time = downswing_frames / fps
        
        if downswing_time < 0.01:
            tempo_ratio = 0.0
            confidence = 0.0
        else:
            tempo_ratio = backswing_time / downswing_time
            confidence = 1.0
        
        # Ideal tempo is 3:1 to 4:1
        ideal_ratio = 3.5
        deviation = abs(tempo_ratio - ideal_ratio)
        
        if deviation < 0.5:
            confidence = 1.0
        elif deviation < 1.5:
            confidence = 0.7
        else:
            confidence = 0.4
        
        return MetricResult(
            name=self.get_name(),
            value=tempo_ratio,
            unit="ratio",
            confidence=confidence,
            details={
                'backswing_time_ms': float(backswing_time * 1000),
                'downswing_time_ms': float(downswing_time * 1000),
                'peak_frame': int(peak_frame),
                'ideal_ratio': ideal_ratio
            }
        )
    
    def get_name(self) -> str:
        return "swing_tempo"
    
    def get_description(self) -> str:
        return "Swing tempo ratio (backswing / downswing time)"
    
    def get_unit(self) -> str:
        return "ratio"
```

### Step 2: Register the Metric

**File: `src/metrics/__init__.py`**

```python
from src.metrics.swing_metrics.tempo import TempoMetric

MetricRegistry.register('swing_tempo', TempoMetric)
```

### Step 3: Update Configuration

**File: `config/default_config.yaml`**

```yaml
metrics:
  enabled:
    - swing_tempo  # ← ADD THIS
```

### Step 4: Write Tests

**File: `test/unit/test_metrics/test_tempo.py`**

```python
import pytest
import numpy as np
from src.metrics.swing_metrics.tempo import TempoMetric


@pytest.fixture
def ideal_tempo_keypoints():
    """Keypoints with ~3:1 tempo"""
    kps = np.random.rand(60, 33, 3) * 0.1 + 0.45
    for t in range(60):
        if t < 45:  # Backswing - wrist rises gradually
            kps[t, 15, 1] = 0.45 - (t / 45) * 0.15
            kps[t, 16, 1] = 0.45 - (t / 45) * 0.15
        else:  # Downswing - wrist falls quickly
            kps[t, 15, 1] = 0.30 + ((t - 45) / 15) * 0.30
            kps[t, 16, 1] = 0.30 + ((t - 45) / 15) * 0.30
    return kps


def test_tempo_computation(ideal_tempo_keypoints):
    """Test tempo calculation"""
    metric = TempoMetric()
    result = metric.compute(ideal_tempo_keypoints, fps=30.0)
    
    assert result.name == "swing_tempo"
    assert result.unit == "ratio"
    assert 2.5 < result.value < 3.5  # ~3:1 ratio
    assert 0 <= result.confidence <= 1
```

### Step 5: Use in Pipeline

```python
from src.metrics import MetricRegistry

metric = MetricRegistry.get('swing_tempo')
result = metric.compute(keypoints_sequence, fps=30.0)

print(f"Tempo Ratio: {result.value:.2f}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Backswing Time: {result.details['backswing_time_ms']:.0f}ms")
print(f"Downswing Time: {result.details['downswing_time_ms']:.0f}ms")
```

---

## FastAPI Integration Example

### Add an API Endpoint for Your New Fault

**File: `api/routes/analysis_routes.py`**

```python
from fastapi import APIRouter, UploadFile, File
from src.faults import FaultRegistry
from src.core.pipeline import GolfAssistant

router = APIRouter()

@router.post("/api/analyze/{fault_name}")
async def analyze_specific_fault(fault_name: str, video: UploadFile = File(...)):
    """Analyze a specific fault in uploaded video"""
    
    # Get fault detector
    fault = FaultRegistry.get(fault_name)
    
    # Process video
    pipeline = GolfAssistant()
    keypoints = await pipeline.process_video(video.file)
    
    # Detect fault
    result = fault.detect(keypoints)
    
    return {
        "fault": fault_name,
        "description": fault.get_description(),
        "detected": result.detected,
        "score": result.score,
        "confidence": result.confidence,
        "severity": result.severity,
        "details": result.details
    }
```

---

## Personalized Feedback Example

### Generate Baseline-Aware Feedback

**File: `src/feedback/personalized_feedback.py`**

```python
from typing import Dict, List, Any
from src.core.database import get_user_baseline

class PersonalizedFeedback:
    @staticmethod
    def generate(user_id: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized feedback without grading"""
        
        # Get user's baseline
        baseline = get_user_baseline(user_id)
        
        # Compare current to baseline
        insights = []
        for metric_name, current_value in analysis['metrics'].items():
            if metric_name in baseline.swing_metrics:
                baseline_value = baseline.swing_metrics[metric_name]
                change_percent = ((current_value - baseline_value) / baseline_value) * 100
                
                insights.append({
                    "metric": metric_name,
                    "current": current_value,
                    "baseline": baseline_value,
                    "change_percent": change_percent,
                    "insight": f"{metric_name} changed by {change_percent:.1f}%"
                })
        
        # Generate body-type-aware recommendations
        recommendations = generate_recommendations(
            analysis['faults'],
            insights,
            body_type=baseline.body_type
        )
        
        return {
            "insights": insights,
            "recommendations": recommendations,
            "baseline": baseline.swing_metrics,
            # NOTE: No "score" or "grade" field!
        }

def generate_recommendations(faults: Dict, insights: List, body_type: str) -> List[str]:
    """Generate body-type-aware recommendations"""
    
    recommendations = []
    
    # Example: different feedback for different body types
    if "over_the_top" in faults and faults["over_the_top"].detected:
        if body_type == "ectomorph":
            recommendations.append(
                "Your lean frame benefits from a steeper swing plane. "
                "Focus on keeping the club on plane through the peak."
            )
        elif body_type == "mesomorph":
            recommendations.append(
                "Your athletic build can handle more plane variation. "
                "Try rotating more aggressively."
            )
    
    return recommendations
```

---

## Summary

| Task | File | Changes |
|------|------|---------|
| Add new fault | Create `src/faults/fault_detectors/{name}.py` | 1 file, implement detect() |
| Register fault | Update `src/faults/__init__.py` | Add 1 import + 1 register line |
| Configure | Update `config/default_config.yaml` | Add name to enabled list + threshold |
| Test | Create `test/unit/test_faults/test_{name}.py` | Write unit tests |
| Add to FastAPI | Create/update `api/routes/{name}_routes.py` | Add endpoint(s) |

**Total time: <1 hour for a complete, tested, deployed feature!**

---

## Templates for Copy-Paste

### Fault Template
```python
import numpy as np
from src.faults.base_fault import BaseFault, FaultResult

class MyFault(BaseFault):
    def __init__(self, threshold: float = 0.5):
        super().__init__(threshold=threshold)
    
    def detect(self, keypoints_seq, address_frame=0, impact_frame=None, **kwargs) -> FaultResult:
        # Your implementation
        score = ...  # 0-1
        confidence = ...  # 0-1
        severity = "low" | "medium" | "high"
        
        return FaultResult(
            detected=score > self.threshold,
            score=score,
            confidence=confidence,
            severity=severity,
            details={...}
        )
    
    def get_name(self) -> str:
        return "my_fault"
    
    def get_description(self) -> str:
        return "Description of what this fault detects"
```

### Metric Template
```python
import numpy as np
from src.metrics.base_metric import BaseMetric, MetricResult

class MyMetric(BaseMetric):
    def compute(self, keypoints_seq, address_frame=0, impact_frame=None, **kwargs) -> MetricResult:
        # Your implementation
        value = ...  # Float
        confidence = ...  # 0-1
        unit = "..."  # e.g., "seconds", "degrees"
        
        return MetricResult(
            name=self.get_name(),
            value=value,
            unit=unit,
            confidence=confidence,
            details={...}
        )
    
    def get_name(self) -> str:
        return "my_metric"
    
    def get_description(self) -> str:
        return "Description of what this metric measures"
    
    def get_unit(self) -> str:
        return "unit_name"
```

Use these templates as starting points for your new features!
