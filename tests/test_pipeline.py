import unittest
import numpy as np

from app.services.pose_estimation import DetectorPipeline


class DummyObjectDetector:
    def detect_for_video(self, mp_image, timestamp_ms):
        class BBox:
            origin_x = 10
            origin_y = 20
            width = 50
            height = 40

        class Category:
            category_name = "club"
            score = 0.9

        class Detection:
            bounding_box = BBox()
            categories = [Category()]

        class Result:
            detections = [Detection()]

        return Result()


class DummyLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class DummyPoseDetector:
    def detect_for_video(self, mp_image, timestamp_ms):
        landmarks = [DummyLandmark(0.5 + i * 0.001, 0.5 + i * 0.001, 0.0) for i in range(33)]

        class Result:
            pose_landmarks = [landmarks]

        return Result()


class TestDetectorPipeline(unittest.TestCase):
    def test_process_frame_with_mocks(self):
        obj = DummyObjectDetector()
        pose = DummyPoseDetector()
        pipeline = DetectorPipeline(obj_detector=obj, pose_detector=pose)

        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        annotated = pipeline.process_frame(frame, timestamp_ms=0)

        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, frame.shape)
        self.assertEqual(annotated.dtype, frame.dtype)
        self.assertTrue(np.any(annotated != 0), "Annotated frame should not be all zeros")


if __name__ == '__main__':
    unittest.main()
