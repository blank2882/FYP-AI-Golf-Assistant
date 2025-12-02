import unittest
import sys, pathlib
import numpy as np

# allow importing packages from repo root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from types import SimpleNamespace
from detector_pipeline import DetectorPipeline


class DummyObjectDetector:
    def detect_for_video(self, mp_image, timestamp_ms):
        # simple fake detection with one bounding box and one category
        bbox = SimpleNamespace(origin_x=10, origin_y=20, width=50, height=40)
        category = SimpleNamespace(category_name="club", score=0.9)
        detection = SimpleNamespace(bounding_box=bbox, categories=[category])
        return SimpleNamespace(detections=[detection])


class DummyLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class DummyPoseDetector:
    def detect_for_video(self, mp_image, timestamp_ms):
        # return a single pose with a full set of normalized landmarks
        # MediaPipe pose drawing expects the full landmark set (33). Provide
        # a list of 33 landmarks with reasonable values to avoid index errors.
        landmarks = [DummyLandmark(0.5 + i * 0.001, 0.5 + i * 0.001, 0.0) for i in range(33)]
        return SimpleNamespace(pose_landmarks=[landmarks])


class TestDetectorPipeline(unittest.TestCase):
    def test_process_frame_with_mocks(self):
        obj = DummyObjectDetector()
        pose = DummyPoseDetector()
        pipeline = DetectorPipeline(obj_detector=obj, pose_detector=pose)

        # create a simple blank BGR frame
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        annotated = pipeline.process_frame(frame, timestamp_ms=0)

        # basic assertions
        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, frame.shape)
        self.assertEqual(annotated.dtype, frame.dtype)

        # Expect that some drawing occurred (not all zeros)
        self.assertTrue(np.any(annotated != 0), "Annotated frame should not be all zeros")


if __name__ == '__main__':
    unittest.main()
