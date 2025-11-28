import cv2
import numpy as np

def smart_center_crop(frame, crop_ratio=0.70):
    """ Simple & efficient crop that increases golfer size in frame """
    h, w = frame.shape[:2]
    ch, cw = int(h * crop_ratio), int(w * crop_ratio)
    sy = (h - ch) // 2
    sx = (w - cw) // 2
    return frame[sy:sy+ch, sx:sx+cw]

def sharpen_image(img):
    """Light unsharp masking — very cheap computationally."""
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)

def preprocess_frame(frame):
    """ Full preprocessing pipeline """
    cropped = smart_center_crop(frame, 0.70)
    resized = cv2.resize(cropped, (256, 256), interpolation=cv2.INTER_AREA)
    sharp = sharpen_image(resized)
    return sharp
