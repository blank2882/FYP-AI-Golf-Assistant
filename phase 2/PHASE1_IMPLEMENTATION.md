# Phase 1 Implementation - Foundation (Weeks 1-2)

## Overview

Phase 1 establishes the modular foundation that all future features build upon. This guide provides step-by-step implementation with complete Python code examples.

---

## Step 1: Create Directory Structure

```bash
# From workspace root
mkdir -p src/{core,detectors,swing_analysis,faults/fault_detectors,metrics/swing_metrics,preprocessing,camera,input,feedback,utils,models}
mkdir -p api/routes api/schemas api/middleware
mkdir -p config scripts logs out
mkdir -p test/{unit/{test_faults,test_metrics,test_detectors,test_input},integration,fixtures}
mkdir -p frontend
```

---

## Step 2: Create Base Classes for Faults

**File: `src/faults/base_fault.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import numpy as np


@dataclass
class FaultResult:
    """Result of a fault detection operation"""
    detected: bool
    score: float  # 0-1: raw detection score
    confidence: float  # 0-1: model confidence
    severity: str = "low"  # low, medium, high
    details: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0 <= self.score <= 1:
            raise ValueError(f"Score must be in [0,1], got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be in [0,1], got {self.confidence}")


class BaseFault(ABC):
    """Abstract base class for all fault detectors"""
    
    def __init__(self, threshold: float = 0.5):
        if not 0 <= threshold <= 1:
            raise ValueError(f"Threshold must be in [0,1], got {threshold}")
        self.threshold = threshold
    
    @abstractmethod
    def detect(self, 
               keypoints_seq: np.ndarray,
               address_frame: int = 0,
               impact_frame: Optional[int] = None,
               **kwargs) -> FaultResult:
        """Detect fault in keypoint sequence
        
        Args:
            keypoints_seq: Shape (T, num_joints, 3) array
            address_frame: Frame index at address (start)
            impact_frame: Frame index at impact (end)
        
        Returns:
            FaultResult with detection status and confidence
        """
        if keypoints_seq.ndim != 3:
            raise ValueError(f"Expected 3D keypoints, got {keypoints_seq.shape}")
    
    @abstractmethod
    def get_name(self) -> str:
        """Return unique name/ID of this fault"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable description"""
        pass
    
    def set_threshold(self, threshold: float) -> None:
        """Update detection threshold"""
        if not 0 <= threshold <= 1:
            raise ValueError(f"Threshold must be in [0,1], got {threshold}")
        self.threshold = threshold
```

---

## Step 3: Create Fault Registry

**File: `src/faults/fault_registry.py`**

```python
from typing import Dict, Type, List
from src.faults.base_fault import BaseFault


class FaultRegistry:
    """Factory and registry for fault detectors"""
    
    _registry: Dict[str, Type[BaseFault]] = {}
    
    @classmethod
    def register(cls, name: str, fault_class: Type[BaseFault]) -> None:
        """Register a fault detector class"""
        if not issubclass(fault_class, BaseFault):
            raise TypeError(f"{fault_class} must inherit from BaseFault")
        
        if name in cls._registry:
            raise ValueError(f"Fault '{name}' is already registered")
        
        cls._registry[name] = fault_class
        print(f"Registered fault detector: {name}")
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseFault:
        """Get an instance of a registered fault detector"""
        if name not in cls._registry:
            raise KeyError(
                f"Fault '{name}' not found. Available: {cls.list_all()}"
            )
        
        fault_class = cls._registry[name]
        return fault_class(**kwargs)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered fault detector names"""
        return sorted(cls._registry.keys())
    
    @classmethod
    def describe_all(cls) -> Dict[str, str]:
        """Get descriptions of all registered fault detectors"""
        descriptions = {}
        for name in cls.list_all():
            try:
                detector = cls.get(name)
                descriptions[name] = detector.get_description()
            except Exception:
                descriptions[name] = "Description unavailable"
        return descriptions
```

---

## Step 4: Refactor Existing Faults

**File: `src/faults/fault_detectors/head_movement.py`**

```python
import numpy as np
from src.faults.base_fault import BaseFault, FaultResult


class HeadMovementFault(BaseFault):
    """Detects excessive head movement during swing"""
    
    def __init__(self, threshold: float = 0.04):
        super().__init__(threshold=threshold)
    
    def detect(self, 
               keypoints_seq: np.ndarray,
               address_frame: int = 0,
               impact_frame: None = None,
               **kwargs) -> FaultResult:
        """Detect excessive head movement"""
        super().detect(keypoints_seq, address_frame, impact_frame)
        
        T = keypoints_seq.shape[0]
        if impact_frame is None:
            impact_frame = T - 1
        
        # Extract nose keypoint (index 0)
        nose_address = keypoints_seq[address_frame, 0, :2]
        nose_impact = keypoints_seq[impact_frame, 0, :2]
        
        # Compute displacement
        displacement = np.linalg.norm(nose_impact - nose_address)
        
        # Normalize by shoulder width
        norm_factor = self._compute_shoulder_width(keypoints_seq, address_frame)
        normalized_score = float(displacement / norm_factor)
        
        # Confidence from visibility
        confidence = float(keypoints_seq[address_frame, 0, 2])
        
        # Severity
        severity = "low" if normalized_score < 0.06 else \
                   "medium" if normalized_score < 0.15 else "high"
        
        return FaultResult(
            detected=normalized_score > self.threshold,
            score=min(normalized_score, 1.0),
            confidence=confidence,
            severity=severity,
            details={
                'displacement': float(displacement),
                'normalized_displacement': normalized_score,
                'shoulder_width': float(norm_factor)
            }
        )
    
    @staticmethod
    def _compute_shoulder_width(keypoints_seq: np.ndarray, frame_index: int) -> float:
        """Compute shoulder width for normalization"""
        if keypoints_seq.shape[1] > 12:
            left_shoulder = keypoints_seq[frame_index, 11, :2]
            right_shoulder = keypoints_seq[frame_index, 12, :2]
        else:
            left_shoulder = keypoints_seq[frame_index, 5, :2]
            right_shoulder = keypoints_seq[frame_index, 6, :2]
        
        width = np.linalg.norm(right_shoulder - left_shoulder)
        return float(width + 1e-8)
    
    def get_name(self) -> str:
        return "head_movement"
    
    def get_description(self) -> str:
        return "Excessive head movement during swing (loss of posture)"
```

---

## Step 5: Create Metrics Base Class

**File: `src/metrics/base_metric.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np


@dataclass
class MetricResult:
    """Result of a swing metric computation"""
    name: str
    value: float
    unit: str
    confidence: float  # 0-1
    details: Optional[Dict[str, Any]] = None


class BaseMetric(ABC):
    """Abstract base class for swing metrics"""
    
    @abstractmethod
    def compute(self,
                keypoints_seq: np.ndarray,
                address_frame: int = 0,
                impact_frame: Optional[int] = None,
                **kwargs) -> MetricResult:
        """Compute metric from keypoint sequence"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return unique name of this metric"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable description"""
        pass
    
    @abstractmethod
    def get_unit(self) -> str:
        """Return unit of measurement"""
        pass
```

---

## Step 6: Create Metric Registry

**File: `src/metrics/metric_registry.py`**

```python
from typing import Dict, Type, List
from src.metrics.base_metric import BaseMetric


class MetricRegistry:
    """Factory and registry for swing metrics"""
    
    _registry: Dict[str, Type[BaseMetric]] = {}
    
    @classmethod
    def register(cls, name: str, metric_class: Type[BaseMetric]) -> None:
        """Register a metric class"""
        if not issubclass(metric_class, BaseMetric):
            raise TypeError(f"{metric_class} must inherit from BaseMetric")
        
        if name in cls._registry:
            raise ValueError(f"Metric '{name}' is already registered")
        
        cls._registry[name] = metric_class
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseMetric:
        """Get metric instance"""
        if name not in cls._registry:
            raise KeyError(f"Metric '{name}' not found")
        
        metric_class = cls._registry[name]
        return metric_class(**kwargs)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered metrics"""
        return sorted(cls._registry.keys())
```

---

## Step 7: Create Configuration System

**File: `config/default_config.yaml`**

```yaml
pipeline:
  input:
    type: "video_file"  # video_file, webcam, stream
    source: "./data/test_video.mp4"
    fps: 30
  
  detectors:
    object:
      model_path: "./models/efficientdet_lite2.tflite"
      confidence_threshold: 0.5
    pose:
      model_path: "./models/pose_landmarker_heavy.task"
  
  processing:
    crop_expand: 0.25
    target_size: [224, 224]
    frame_skip: 1
    use_gpu: false

faults:
  enabled:
    - head_movement
    - slide_sway
  
  thresholds:
    head_movement: 0.04
    slide_sway: 0.12
  
  compute_confidence: true

metrics:
  enabled: []

output:
  directory: "./out"
  save_video: true
  save_json: true

feedback:
  personalization_enabled: true
  baseline_comparison: true
  body_type_aware: true
  grading_enabled: false

logging:
  level: "INFO"
  file: "./logs/golf_assistant.log"
```

---

## Step 8: Initialize Modules

**File: `src/faults/__init__.py`**

```python
from src.faults.base_fault import BaseFault, FaultResult
from src.faults.fault_registry import FaultRegistry
from src.faults.fault_detectors.head_movement import HeadMovementFault

# Auto-register existing faults
FaultRegistry.register('head_movement', HeadMovementFault)

__all__ = ['BaseFault', 'FaultResult', 'FaultRegistry', 'HeadMovementFault']
```

**File: `src/metrics/__init__.py`**

```python
from src.metrics.base_metric import BaseMetric, MetricResult
from src.metrics.metric_registry import MetricRegistry

__all__ = ['BaseMetric', 'MetricResult', 'MetricRegistry']
```

---

## Step 9: Create Baseline Tracking System

**File: `src/core/baseline_tracker.py`**

```python
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import json


@dataclass
class UserBaseline:
    """Tracks per-user baseline metrics for personalization"""
    user_id: str
    body_type: Optional[str] = None  # e.g., "ectomorph", "mesomorph"
    height: Optional[float] = None
    swing_metrics: Dict[str, float] = field(default_factory=dict)
    swing_patterns: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_metric(self, metric_name: str, value: float) -> None:
        """Update baseline metric with running average"""
        if metric_name not in self.swing_metrics:
            self.swing_metrics[metric_name] = value
        else:
            # Exponential moving average
            alpha = 0.3
            old_value = self.swing_metrics[metric_name]
            self.swing_metrics[metric_name] = (alpha * value) + ((1 - alpha) * old_value)
        
        self.last_updated = datetime.now()


class BaselineTracker:
    """In-memory baseline storage (Phase 1; Phase 6 uses database)"""
    
    def __init__(self):
        self.baselines: Dict[str, UserBaseline] = {}
    
    def get_or_create_baseline(self, user_id: str) -> UserBaseline:
        """Get or create baseline for user"""
        if user_id not in self.baselines:
            self.baselines[user_id] = UserBaseline(user_id=user_id)
        return self.baselines[user_id]
    
    def set_user_info(self, user_id: str, body_type: str, height: float) -> None:
        """Set user physical characteristics"""
        baseline = self.get_or_create_baseline(user_id)
        baseline.body_type = body_type
        baseline.height = height
    
    def update_metrics(self, user_id: str, metrics: Dict[str, float]) -> None:
        """Update baseline with new metrics"""
        baseline = self.get_or_create_baseline(user_id)
        for metric_name, value in metrics.items():
            baseline.update_metric(metric_name, value)
```

---

## Step 10: Create Unit Tests

**File: `test/unit/test_faults/test_head_movement.py`**

```python
import pytest
import numpy as np
from src.faults.fault_detectors.head_movement import HeadMovementFault


@pytest.fixture
def static_keypoints():
    """Keypoints with no head movement"""
    kps = np.random.rand(30, 33, 3) * 0.1 + 0.45
    kps[:, 0, :2] = [0.5, 0.5]  # Nose stays still
    return kps


def test_head_movement_initialization():
    """Test fault detector initialization"""
    detector = HeadMovementFault(threshold=0.05)
    assert detector.threshold == 0.05
    assert detector.get_name() == "head_movement"


def test_head_movement_no_fault(static_keypoints):
    """Test no fault when movement within threshold"""
    detector = HeadMovementFault(threshold=0.04)
    result = detector.detect(static_keypoints)
    
    assert not result.detected
    assert result.score < detector.threshold
    assert 0 <= result.confidence <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## Step 11: Create Input Abstraction

**File: `src/input/input_source.py`**

```python
from abc import ABC, abstractmethod
from typing import Tuple
import numpy as np


class InputSource(ABC):
    """Abstract interface for input sources"""
    
    @abstractmethod
    def open(self):
        """Open the input source"""
        pass
    
    @abstractmethod
    def read(self) -> Tuple[bool, np.ndarray, float]:
        """Read next frame
        
        Returns:
            (success, frame, timestamp_ms)
        """
        pass
    
    @abstractmethod
    def close(self):
        """Close the input source"""
        pass
    
    @property
    @abstractmethod
    def fps(self) -> float:
        """Frames per second"""
        pass
```

---

## Next Steps After Phase 1

1. **Test thoroughly**: Run all unit tests
2. **Verify integration**: Ensure pipeline works with new structure
3. **Document progress**: Update team on new capabilities
4. **Plan Phase 2**: New faults and metrics

---

## Success Criteria for Phase 1

✅ All directories created
✅ Base classes implemented
✅ Registries functional
✅ Existing faults refactored
✅ Configuration system working
✅ Baseline tracking operational
✅ Tests passing (>80% coverage)
✅ Documentation updated

**Completion of Phase 1 means you can easily add new faults/metrics!**
