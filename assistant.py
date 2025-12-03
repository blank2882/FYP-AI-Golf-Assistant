import os
import json
import cv2
import numpy as np
from detector_pipeline import DetectorPipeline
from swingnet_inference import SwingNetInferer, EVENT_LIST
from llm_feedback import generate_feedback


class GolfAssistant:
    """Orchestrator for the end-to-end golf assistant pipeline.

    This class groups responsibilities into methods so the top-level script
    remains tiny and readable. Each helper method is commented to explain its
    purpose.
    """

    def __init__(
        self,
        video_path='./data/test_video.mp4',
        weights_path='./golfdb/models/swingnet_1800.pth.tar',
        out_dir='./out',
        det_obj_model_path='./models/efficientdet_lite2.tflite',
        det_pose_model_path='./models/pose_landmarker_heavy.task',
        crop_expand=0.25,
        target_size=(224, 224),
    ):
        # store input and model paths
        self.video_path = video_path
        self.weights_path = weights_path
        self.out_dir = out_dir
        # paths for intermediate and final outputs
        self.annotated_base = os.path.join(out_dir, 'annotated.mp4')
        self.annotated_out = os.path.join(out_dir, 'annotated_with_labels.mp4')
        self.pred_json = os.path.join(out_dir, 'predicted_events.json')

        # detector pipeline instance
        self.detector = DetectorPipeline(obj_model_path=det_obj_model_path, pose_model_path=det_pose_model_path)

        # crop and resize configuration
        self.crop_expand = crop_expand
        self.target_size = target_size

        # ImageNet normalization constants used before feeding frames to SwingNet
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    # run the detector pipeline and collect metadata
    def run_detector(self, every_n=1, display=False):
        # ensure output directory exists
        os.makedirs(self.out_dir, exist_ok=True)
        print('Running detector pipeline...')
        # run detector pipeline and collect metadata
        processed_count, metadata = self.detector.process_video(
            self.video_path,
            display=display,
            output_path=self.annotated_base,
            collect_metadata=True,
            metadata_output_path=os.path.join(self.out_dir, 'metadata.json'),
        )
        print(f'Detector processed {processed_count} frames; metadata entries: {len(metadata) if metadata else 0}')
        return metadata

    # crop and resize a frame based on a bounding box
    def crop_and_resize(self, frame_bgr, bbox):
        # convert normalized bbox to pixel coordinates and expand
        h, w = frame_bgr.shape[:2]
        ox = bbox.get('origin_x', 0.0)
        oy = bbox.get('origin_y', 0.0)
        bw = bbox.get('width', 1.0)
        bh = bbox.get('height', 1.0)

        x = int(ox * w)
        y = int(oy * h)
        ww = max(1, int(bw * w))
        hh = max(1, int(bh * h))

        ex = int(ww * self.crop_expand)
        ey = int(hh * self.crop_expand)
        x1 = max(0, x - ex)
        y1 = max(0, y - ey)
        x2 = min(w, x + ww + ex)
        y2 = min(h, y + hh + ey)

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            crop = cv2.resize(frame_bgr, self.target_size)
        else:
            crop = cv2.resize(crop, (self.target_size[1], self.target_size[0]))
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        return rgb

    # build crops from metadata for SwingNet inference
    def build_crops_from_metadata(self, metadata):
        """Return crops, frame indices and keypoints aligned to the crops.

        Returns (collected_rgb, collected_frame_idxs, collected_keypoints)
        where each entry in `collected_keypoints` is a list of landmarks for the
        primary detected pose at that frame. Each landmark is a dict with at
        least 'x','y','z' and optional 'visibility'. If no pose is present a
        zero-filled landmark list (33 points) is returned.
        """
        if not metadata:
            return [], [], []

        meta_map = {m['frame_index']: m['metadata'] for m in metadata}

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f'Unable to open video: {self.video_path}')

        collected_rgb = []
        collected_frame_idxs = []
        collected_keypoints = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in meta_map:
                md = meta_map[frame_idx]
                used_bbox = None
                best_score = 0.0
                for obj in md.get('objects', []):
                    score = obj.get('score', 0.0) or 0.0
                    if score > best_score:
                        best_score = score
                        used_bbox = obj.get('bbox')

                # determine keypoints for this frame: choose first pose if available
                poses = md.get('pose', []) or []
                if len(poses) > 0:
                    primary_pose = poses[0]
                else:
                    # default to 33 zero landmarks (x,y,z) if missing
                    primary_pose = [{'x': 0.0, 'y': 0.0, 'z': 0.0} for _ in range(33)]

                if used_bbox is not None:
                    rgb = self.crop_and_resize(frame, used_bbox)
                    collected_rgb.append(rgb)
                    collected_frame_idxs.append(frame_idx)
                    collected_keypoints.append(primary_pose)
            frame_idx += 1

        cap.release()
        return collected_rgb, collected_frame_idxs, collected_keypoints

    # convert list of RGB frames to normalized numpy array for SwingNet
    def frames_to_swingnet_np(self, frames_rgb):
        arr = np.stack(frames_rgb, axis=0).astype(np.float32) / 255.0
        arr = arr.transpose(0, 3, 1, 2).copy()
        arr = (arr - self.mean[None, :, None, None]) / self.std[None, :, None, None]
        return arr

    # annotate video with predicted labels at specified frames
    def annotate_video_with_labels(self, base_video_path, out_path, label_map):
        cap = cv2.VideoCapture(base_video_path)
        if not cap.isOpened():
            raise RuntimeError(f'Unable to open video {base_video_path}')
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

        frame_idx = 0
        font = cv2.FONT_HERSHEY_SIMPLEX
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in label_map:
                label_str, conf = label_map[frame_idx]
                text = f"{label_str} ({conf:.2f})"
                cv2.putText(frame, text, (10, 30), font, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
            writer.write(frame)
            frame_idx += 1

        cap.release()
        writer.release()

    # orchestrate the full pipeline
    def run(self):
        # 1) detection
        metadata = self.run_detector()
        if not metadata:
            print('No metadata produced by detector; exiting.')
            return {}

        # 2) cropping
        collected_rgb, collected_frame_idxs, collected_keypoints = self.build_crops_from_metadata(metadata)
        if len(collected_rgb) == 0:
            print('No crops extracted; exiting.')
            return {}

        # 3) load model using object-oriented inferer
        try:
            inferer = SwingNetInferer(self.weights_path)
        except Exception as e:
            print(f'Failed to load SwingNet weights: {e}')
            return {}

        # 4) prepare frames and inference
        frames_np = self.frames_to_swingnet_np(collected_rgb)
        probs = inferer.run_sliding(frames_np, model_seq_len=64)

        # 5) per-frame labels and per-class event frames
        labels = np.argmax(probs, axis=1)
        label_map = {}
        for i, fidx in enumerate(collected_frame_idxs):
            lab = int(labels[i])
            conf = float(probs[i, lab])
            label_str = EVENT_LIST[lab] if lab < len(EVENT_LIST) else 'NoEvent'
            label_map[fidx] = (label_str, conf)

        event_frames = []
        confidences = []
        for c in range(min(probs.shape[1], len(EVENT_LIST))):
            idx = int(np.argmax(probs[:, c]))
            frame_for_class = collected_frame_idxs[idx]
            conf = float(probs[idx, c])
            event_frames.append(int(frame_for_class))
            confidences.append(conf)
            label_map[frame_for_class] = (EVENT_LIST[c], conf)

        # 6) save JSON summary
        summary = {'predicted_events': []}
        for i, ef in enumerate(event_frames):
            summary['predicted_events'].append({
                'event_index': i,
                'event_name': EVENT_LIST[i],
                'frame_index': int(ef),
                'confidence': float(confidences[i]),
            })
        with open(self.pred_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        # 7) annotate video with predicted labels and return summary
        print('Predicted event frames:', event_frames)
        print('Confidence:', [float(np.round(c, 3)) for c in confidences])
        print('Writing annotated video with predicted labels to', self.annotated_out)
        self.annotate_video_with_labels(self.annotated_base, self.annotated_out, label_map)
        
        # 8) Prepare keypoints sequence aligned to `collected_frame_idxs` and
        # build an `events` mapping of event_name -> frame_index for the LLM.
        # Convert keypoints to numpy array with shape (T, L, 3) where each
        # landmark is (x, y, visibility). If visibility isn't present set 1.0.
        import numpy as _np
        if len(collected_keypoints) > 0:
            # infer number of landmarks
            L = len(collected_keypoints[0])
            kps = _np.zeros((len(collected_keypoints), L, 3), dtype=_np.float32)
            for t, pose in enumerate(collected_keypoints):
                for i, lm in enumerate(pose):
                    x = float(lm.get('x', 0.0))
                    y = float(lm.get('y', 0.0))
                    vis = float(lm.get('visibility', 1.0))
                    kps[t, i, 0] = x
                    kps[t, i, 1] = y
                    kps[t, i, 2] = vis
        else:
            kps = _np.zeros((0, 0, 3), dtype=_np.float32)

        events_map = {EVENT_LIST[i]: int(ef) for i, ef in enumerate(event_frames)}

        # 9) Generate LLM feedback
        coaching = generate_feedback(events_map, kps, prefer_http=True, model="qwen2.5")
        print("LLM feedback (truncated):", str(coaching)[:500])

        return {
            'event_frames': event_frames,
            'confidences': confidences,
            'annotated_video': self.annotated_out,
            'json': self.pred_json,
        }
