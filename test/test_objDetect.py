# import the necessary libraries
import unittest
import sys, pathlib
# move to the parent directory to access objDetect module
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import objDetect

video_path = "./data/test_video.mp4"

class TestMediaPipeObjectDetector(unittest.TestCase):
    def test_create_object_detector(self):
        model_path = "./models/efficientdet_lite2.tflite"
        detector = objDetect.create_object_detector(model_path)
        self.assertIsNotNone(detector, "Object detector should be created successfully.")
        
    def test_process_frame(self):
        model_path = "./models/efficientdet_lite2.tflite"
        detector = objDetect.create_object_detector(model_path)
        timestamp = 0
        frame = None  # Placeholder, actual frame will be read in the function
        try:
            objDetect.process_frame(detector, frame, timestamp, video_path)
        except Exception as e:
            self.fail(f"process_frame raised an exception: {e}")
        
if __name__ == '__main__':
    unittest.main()
