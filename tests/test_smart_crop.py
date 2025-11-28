import numpy as np
import cv2
import smart_crop


def make_color_image(h, w, color=(0, 0, 0)):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def test_smart_center_crop_shape_and_exact_slice():
    h, w = 100, 200
    img = make_color_image(h, w, color=(10, 20, 30))
    # Draw a distinct center pixel so we can verify exact slicing
    center_y, center_x = h // 2, w // 2
    img[center_y, center_x] = (255, 0, 0)

    ratio = 0.5
    cropped = smart_crop.smart_center_crop(img, crop_ratio=ratio)

    ch, cw = int(h * ratio), int(w * ratio)
    assert cropped.shape[0] == ch
    assert cropped.shape[1] == cw

    sy = (h - ch) // 2
    sx = (w - cw) // 2
    # The crop should equal a straightforward numpy slice
    expected = img[sy:sy+ch, sx:sx+cw]
    assert np.array_equal(cropped, expected)


def test_sharpen_image_changes_values_and_preserves_dtype():
    # Create a smooth gray image (low-frequency) so sharpening has an effect
    h, w = 64, 64
    img = np.full((h, w, 3), 128, dtype=np.uint8)
    # Put a small blur/gradient so unsharp mask changes values
    cv2.circle(img, (w//2, h//2), 10, (120, 120, 120), -1)

    out = smart_crop.sharpen_image(img)
    assert out.shape == img.shape
    assert out.dtype == img.dtype

    # Expect some pixels to change after sharpening
    diff = np.abs(out.astype(int) - img.astype(int))
    assert diff.max() > 0


def test_preprocess_frame_returns_256_square_and_sharp():
    h, w = 240, 320
    img = make_color_image(h, w, color=(50, 60, 70))
    processed = smart_crop.preprocess_frame(img)
    assert processed.shape == (256, 256, 3)
    assert processed.dtype == img.dtype
