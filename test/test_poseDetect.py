# import the necessary libraries
import unittest
import sys, pathlib
# move to the parent directory to access objDetect module
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import poseDetect

video_path = "./data/test_video.mp4"

class TestposeDetect(unittest.TestCase):
    def test_create_pose_detector(self):
        detector = poseDetect.create_pose_detector(poseDetect.model_path)
        self.assertIsNotNone(detector)
    

if __name__ == '__main__':
    unittest.main()