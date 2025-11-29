"""golfdb package initializer.

Expose the main model class for convenient imports.
"""
from .model import EventDetector
from .MobileNetV2 import MobileNetV2

__all__ = ["EventDetector", "MobileNetV2"]
