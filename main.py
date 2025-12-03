# file that orchestrates the golf assistant by combining various modules

# import the necessary libraries
import os
import json
import cv2
import numpy as np
from assistant import GolfAssistant


def main():
    # create an assistant instance using defaults (easy to override)
    assistant = GolfAssistant()
    # run the pipeline and capture the result summary
    result = assistant.run()
    # if the run produced results, print the output paths
    if result:
        print('Pipeline finished successfully. Outputs:')
        print('  Video:', result['annotated_video'])
        print('  JSON :', result['json'])


if __name__ == '__main__':
    # run main when this script is executed directly
    main()