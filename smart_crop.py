import cv2
import numpy as np

def smart_center_crop(frame, crop_ratio=0.70):
    """
    Fast center crop. Keeps most of the subject while removing background.
    Use only for MediaPipe (pose) stream.
    """
    h, w = frame.shape[:2]
    ch, cw = int(h * crop_ratio), int(w * crop_ratio)
    sy = (h - ch) // 2
    sx = (w - cw) // 2
    return frame[sy:sy+ch, sx:sx+cw]

def smart_crop_with_bbox(frame, bbox=None, pad=0.15):
    """
    If bbox available (x,y,w,h) in absolute pixels, expand by pad fraction and crop.
    bbox = (x, y, w, h)
    """
    h, w = frame.shape[:2]
    if bbox is None:
        return smart_center_crop(frame)
    x, y, bw, bh = bbox
    pad_x = int(bw * pad)
    pad_y = int(bh * pad)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + bw + pad_x)
    y2 = min(h, y + bh + pad_y)
    return frame[y1:y2, x1:x2]

def sharpen_image(img):
    """Light, fast unsharp mask (for small enhancement)."""
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)

def preprocess_for_mediapipe(frame, crop_ratio=0.7, sharpen=True):
    crop = smart_center_crop(frame, crop_ratio=crop_ratio)
    resized = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)
    if sharpen:
        resized = sharpen_image(resized)
    return resized
