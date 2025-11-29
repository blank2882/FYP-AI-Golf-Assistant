import numpy as np
import cv2
import pytest

from smart_crop import (
    smart_center_crop,
    smart_crop_with_bbox,
    sharpen_image,
    preprocess_for_mediapipe,
)


def make_frame(h, w, color=(0, 0, 0)):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def test_smart_center_crop_size_and_content():
    frame = make_frame(400, 300, color=(0, 0, 0))
    # draw a distinct pixel at the exact center of the original
    h, w = frame.shape[:2]
    cy, cx = h // 2, w // 2
    frame[cy, cx] = (255, 0, 0)

    cropped = smart_center_crop(frame, crop_ratio=0.5)
    # expected size
    expected_h = int(400 * 0.5)
    expected_w = int(300 * 0.5)
    assert cropped.shape[:2] == (expected_h, expected_w)

    # the red center pixel should now be at the center of the crop
    ccy, ccx = cropped.shape[0] // 2, cropped.shape[1] // 2
    assert tuple(cropped[ccy, ccx]) == (255, 0, 0)


def test_smart_crop_with_bbox_padding_and_bounds():
    frame = make_frame(100, 200, color=(10, 20, 30))
    # bbox close to left/top to test clamping
    x, y, bw, bh = 10, 20, 50, 40
    pad = 0.2
    cropped = smart_crop_with_bbox(frame, bbox=(x, y, bw, bh), pad=pad)

    pad_x = int(bw * pad)
    pad_y = int(bh * pad)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(frame.shape[1], x + bw + pad_x)
    y2 = min(frame.shape[0], y + bh + pad_y)

    assert cropped.shape[0] == y2 - y1
    assert cropped.shape[1] == x2 - x1

    # when bbox is None, falls back to center crop
    center_crop = smart_crop_with_bbox(frame, bbox=None)
    assert center_crop.shape[0] < frame.shape[0]
    assert center_crop.shape[1] < frame.shape[1]


def test_sharpen_image_preserves_shape_and_changes_values():
    # create a smooth gray gradient image
    h, w = 64, 64
    img = np.tile(np.linspace(50, 200, w, dtype=np.uint8), (h, 1))
    img = cv2.merge([img, img, img])

    out = sharpen_image(img)
    assert out.shape == img.shape
    assert out.dtype == img.dtype
    # sharpening should change at least some pixels
    assert not np.array_equal(out, img)


def test_preprocess_for_mediapipe_resize_and_sharpen_flag():
    # use a textured frame (horizontal gradient) so sharpening has an effect
    h, w = 480, 640
    gradient = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    frame = cv2.merge([gradient, gradient, gradient])
    # When sharpen=False the result should equal a plain resize of the center crop
    manual_crop = smart_center_crop(frame, crop_ratio=0.7)
    manual_resized = cv2.resize(manual_crop, (256, 256), interpolation=cv2.INTER_AREA)

    out_no_sharp = preprocess_for_mediapipe(frame, crop_ratio=0.7, sharpen=False)
    assert out_no_sharp.shape == (256, 256, 3)
    assert np.array_equal(out_no_sharp, manual_resized)

    # With default sharpen=True the output should still be 256x256 and differ from the unsharpened
    out_sharp = preprocess_for_mediapipe(frame, crop_ratio=0.7, sharpen=True)
    assert out_sharp.shape == (256, 256, 3)
    assert not np.array_equal(out_sharp, out_no_sharp)
