# import the necessary libraries
import unittest
import sys, pathlib
import numpy as np
# move to the parent directory to access objDetect module
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import swingnet_inference

video_path = "./data/test_video.mp4"

class Testswingnet_inference(unittest.TestCase):
    def test_load_swingnet_model(self):
        model = swingnet_inference.load_swingnet(
            weight_path="E:\year 3\FYP\prototype git\FYP-AI-Golf-Assistant\golfdb\models\swingnet_1800.pth.tar"
        )
        self.assertIsNotNone(model)
    

if __name__ == '__main__':
    unittest.main()