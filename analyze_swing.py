# combine the swingNet and LSTM model into a single model for inference
import torch

class SwingAnalyzer:
    def __init__(self, swingnet, lstm_model):
        self.swingnet = swingnet
        self.lstm = lstm_model

    def detect_swing_events(self, frames_tensor):
        with torch.no_grad():
            outputs = self.swingnet(frames_tensor)
        swing_events = torch.argmax(outputs, dim=2).tolist()[0]
        return swing_events

    def detect_swing_errors(self, keypoints):
        # Handle empty keypoints (e.g., pose extraction failed)
        try:
            if keypoints is None or keypoints.size == 0:
                return []
        except Exception:
            # If keypoints does not have numpy-like interface, continue and let reshape fail normally
            pass

        keypoints_flat = keypoints.reshape(keypoints.shape[0], -1)
        keypoints_tensor = torch.tensor(keypoints_flat).float().unsqueeze(0)

        with torch.no_grad():
            preds = self.lstm(keypoints_tensor)

        return preds[0].tolist()
