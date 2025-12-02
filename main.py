# file that orchestrates the golf assistant by combining various modules

# import the necessary libraries
from detector_pipeline import DetectorPipeline
import os

video_path = "./data/test_video.mp4"

""" Main function to run the golf assistant video processing."""
def main():
    """ Step 1: Process the video input using MediaPipe Object and Pose Detection"""
    # load in the combined detector pipeline to handle both object and pose detection
    # set the model paths for object and pose detection
    detObj_model_path = "./models/efficientdet_lite2.tflite"
    detPose_model_path = "./models/pose_landmarker_heavy.task"
    
    # create a combined detector pipeline
    pipeline = DetectorPipeline(obj_model_path=detObj_model_path, pose_model_path=detPose_model_path)

    # ensure output directory exists and save annotated video instead of displaying it
    os.makedirs("./out", exist_ok=True)
    # process the video frames using the pipeline (do not display), write annotated video to out
    processed, metadata = pipeline.process_video(
        video_path,
        display=False,
        output_path="./out/annotated.mp4",
        collect_metadata=True,
        metadata_output_path="./out/metadata.json"
    )

    # Print a concise summary and the first few metadata entries to the terminal
    print(f"video processing completed. frames processed: {processed}")
    if metadata:
        print(f"collected metadata entries: {len(metadata)}")
        # Print first 3 entries for quick inspection
        # import json
        # preview = metadata[:3]
        # print("\n--- Metadata preview (first 3 entries) ---")
        # print(json.dumps(preview, indent=2))
        # print("--- End preview ---\n")
        # print(f"Full metadata written to ./out/metadata.json")
    
    """ Step 2: golfdb analysis """
    


if __name__ == "__main__":
    main()