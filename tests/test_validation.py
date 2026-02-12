import unittest
from unittest.mock import patch

import numpy as np

from app.services import validation as val


class TestValidationThresholds(unittest.TestCase):
    def test_validate_file_level_extension(self):
        ok, message, info = val.validate_file_level("swing.avi")
        self.assertFalse(ok)
        self.assertIn("Unsupported file type", message)
        self.assertEqual(info, {})

    @patch("app.services.validation.read_video_info")
    def test_validate_file_level_duration(self, mock_read):
        mock_read.return_value = {
            "fps": 30.0,
            "frame_count": 30.0,
            "width": 640.0,
            "height": 480.0,
            "duration": 1.0,
        }
        ok, message, _ = val.validate_file_level("swing.mp4")
        self.assertFalse(ok)
        self.assertIn("duration", message.lower())

    @patch("app.services.validation.read_video_info")
    def test_validate_file_level_fps(self, mock_read):
        mock_read.return_value = {
            "fps": 15.0,
            "frame_count": 90.0,
            "width": 640.0,
            "height": 480.0,
            "duration": 6.0,
        }
        ok, message, _ = val.validate_file_level("swing.mp4")
        self.assertFalse(ok)
        self.assertIn("frame rate", message.lower())

    @patch("app.services.validation.read_video_info")
    def test_validate_file_level_resolution(self, mock_read):
        mock_read.return_value = {
            "fps": 30.0,
            "frame_count": 90.0,
            "width": 320.0,
            "height": 240.0,
            "duration": 3.0,
        }
        ok, message, _ = val.validate_file_level("swing.mp4")
        self.assertFalse(ok)
        self.assertIn("resolution", message.lower())

    @patch("app.services.validation.read_video_info")
    def test_validate_file_level_ok(self, mock_read):
        mock_read.return_value = {
            "fps": 30.0,
            "frame_count": 120.0,
            "width": 640.0,
            "height": 480.0,
            "duration": 4.0,
        }
        ok, message, info = val.validate_file_level("swing.mp4")
        self.assertTrue(ok)
        self.assertEqual(message, "OK")
        self.assertEqual(info["fps"], 30.0)


class TestValidationScoring(unittest.TestCase):
    def test_pose_presence_ratio(self):
        metadata = [
            {"metadata": {"pose": [[{}] * 33]}},
            {"metadata": {"pose": []}},
            {"metadata": {"pose": [[{}] * 33]}},
        ]
        ratio = val.compute_pose_presence_ratio(metadata)
        self.assertAlmostEqual(ratio, 2.0 / 3.0, places=5)

    def test_swingnet_confidence_mean(self):
        conf = val.compute_swingnet_confidence([0.2, 0.6])
        self.assertAlmostEqual(conf, 0.4, places=5)

    def test_likelihood_score_weights(self):
        score = val.compute_likelihood_score(1.0, 0.5, 0.25)
        self.assertAlmostEqual(score, 0.55, places=5)

    def test_motion_pattern_score_peak(self):
        deltas = [0.01, 0.02, 0.04, 0.06, 0.04, 0.02, 0.01, 0.005, 0.002]
        kps = self._build_kps_with_wrist_motion(deltas)
        frame_idxs = list(range(kps.shape[0]))
        motion_score, details = val.compute_motion_pattern_score(kps, frame_idxs, fps=30.0)
        self.assertGreater(motion_score, 0.35)
        self.assertGreater(details["wrist_score"], 0.35)

    def test_motion_pattern_score_flat(self):
        deltas = [0.0] * 9
        kps = self._build_kps_with_wrist_motion(deltas)
        frame_idxs = list(range(kps.shape[0]))
        motion_score, details = val.compute_motion_pattern_score(kps, frame_idxs, fps=30.0)
        self.assertLess(motion_score, 0.30)
        self.assertLess(details["wrist_score"], 0.30)

    def _build_kps_with_wrist_motion(self, deltas):
        positions = [0.0]
        for delta in deltas:
            positions.append(positions[-1] + delta)

        T = len(positions)
        kps = np.zeros((T, 33, 3), dtype=np.float32)
        for i, pos in enumerate(positions):
            kps[i, 11, :2] = [0.0, 0.0]
            kps[i, 12, :2] = [1.0, 0.0]
            kps[i, 15, :2] = [0.5 + pos, 0.5]
            kps[i, 16, :2] = [0.5 + pos, 0.5]
            kps[i, 23, :2] = [0.0, 1.0]
            kps[i, 24, :2] = [1.0, 1.0]
        return kps


if __name__ == "__main__":
    unittest.main()
