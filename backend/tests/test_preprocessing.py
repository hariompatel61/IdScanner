from dataclasses import replace
import struct

import cv2
import numpy as np
import pytest

from app.preprocessing import pipeline
from app.preprocessing.pipeline import (
    ImageDecodeError,
    PreprocessingConfig,
    adaptive_enhance,
    decode_image_bytes,
    estimate_document_corners,
    normalize_resolution,
    perspective_correct,
    preprocess_document_image,
    rotate_image,
    smart_crop,
    validate_document_corners,
)


def config(**overrides):
    base = PreprocessingConfig(
        max_upload_bytes=1_000_000,
        max_image_width=1000,
        max_image_height=1000,
        max_image_pixels=800_000,
        max_processing_dimension=600,
        min_useful_ocr_dimension=200,
        crop_padding_ratio=0.02,
        min_crop_dimension=40,
        min_document_area_ratio=0.10,
        max_document_area_ratio=0.95,
        enable_enhancement=True,
    )
    return replace(base, **overrides)


def document_image(width=400, height=260):
    image = np.full((height, width, 3), 35, dtype=np.uint8)
    cv2.rectangle(image, (60, 55), (340, 205), (220, 220, 220), -1)
    cv2.rectangle(image, (60, 55), (340, 205), (5, 5, 5), 3)
    for y in range(85, 180, 20):
        cv2.line(image, (90, y), (280, y), (40, 40, 40), 3)
    return image


def jpeg_bytes(image):
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


class TestSafeImageDecode:
    def test_decodes_a_valid_image_in_memory(self):
        decoded = decode_image_bytes(jpeg_bytes(document_image()), "image/jpeg", config())
        assert decoded.image.shape[:2] == (260, 400)
        assert decoded.image_format == "jpeg"

    def test_rejects_bad_mime_without_decoding(self):
        with pytest.raises(ImageDecodeError, match="unsupported_media_type"):
            decode_image_bytes(b"not an image", "text/plain", config())

    def test_rejects_malformed_image(self):
        with pytest.raises(ImageDecodeError):
            decode_image_bytes(b"\xff\xd8broken", "image/jpeg", config())

    def test_rejects_upload_byte_limit(self):
        with pytest.raises(ImageDecodeError, match="image_too_large"):
            decode_image_bytes(jpeg_bytes(document_image()), "image/jpeg", config(max_upload_bytes=10))

    def test_rejects_huge_pixel_header_before_full_decode(self):
        content = b"\x89PNG\r\n\x1a\n" + struct.pack(">IIBBBBB", 100_000, 100_000, 8, 2, 0, 0, 0)
        with pytest.raises(ImageDecodeError, match="image_dimensions_exceeded|image_pixel_limit_exceeded"):
            decode_image_bytes(content, "image/png", config())

    def test_rejects_unsupported_magic_even_if_mime_is_allowed(self):
        with pytest.raises(ImageDecodeError, match="unsupported_image_format"):
            decode_image_bytes(b"not-a-real-image", "image/jpeg", config())


class TestGeometryAndRectification:
    def test_accepts_normal_ordered_rectangle(self):
        corners = np.array([[60, 55], [340, 55], [340, 205], [60, 205]], dtype=np.float32)
        assert validate_document_corners(corners, 400, 260, config())

    def test_rejects_crossed_and_degenerate_corners(self):
        crossed = np.array([[60, 55], [340, 205], [340, 55], [60, 205]], dtype=np.float32)
        degenerate = np.array([[60, 55], [120, 55], [180, 55], [240, 55]], dtype=np.float32)
        assert not validate_document_corners(crossed, 400, 260, config())
        assert not validate_document_corners(degenerate, 400, 260, config())

    @pytest.mark.parametrize("corners", [
        np.array([[60, 55], [340, 55], [330, 205], [70, 205]], dtype=np.float32),
        np.array([[75, 45], [330, 65], [350, 210], [50, 190]], dtype=np.float32),
    ])
    def test_rectifies_mild_and_strong_perspective(self, corners):
        rectified = perspective_correct(document_image(), corners, config())
        assert rectified is not None
        assert rectified.shape[0] >= 40
        assert rectified.shape[1] >= 40

    def test_detects_document_corners_when_a_clean_boundary_exists(self):
        corners = estimate_document_corners(document_image(), config())
        assert corners is not None
        assert corners.shape == (4, 2)

    def test_partial_or_edge_document_never_crashes_or_returns_empty_image(self):
        image = np.full((260, 400, 3), 30, dtype=np.uint8)
        cv2.rectangle(image, (0, 60), (280, 220), (210, 210, 210), -1)
        result = preprocess_document_image(image, config())
        assert result.image.size > 0
        assert result.output_width > 0 and result.output_height > 0

    def test_supports_quarter_turn_rotations_without_assuming_orientation(self):
        image = document_image()
        assert rotate_image(image, 0).shape[:2] == (260, 400)
        assert rotate_image(image, 90).shape[:2] == (400, 260)
        assert rotate_image(image, 180).shape[:2] == (260, 400)
        assert rotate_image(image, 270).shape[:2] == (400, 260)


class TestCropResizeAndAdaptiveProcessing:
    def test_smart_crop_preserves_safe_bounds_at_image_edge(self):
        image = document_image()
        cropped = smart_crop(image, (0, 0, 180, 120), config())
        assert cropped is not None
        assert cropped.shape[0] >= 40 and cropped.shape[1] >= 40

    def test_smart_crop_rejects_tiny_or_empty_bounds(self):
        image = document_image()
        assert smart_crop(image, (20, 20, 5, 5), config()) is None
        assert smart_crop(image, (500, 500, 20, 20), config()) is None

    def test_resolution_normalization_downscales_but_never_blindly_upscales(self):
        large = np.zeros((1200, 1800, 3), dtype=np.uint8)
        small = np.zeros((100, 150, 3), dtype=np.uint8)
        assert max(normalize_resolution(large, config()).shape[:2]) == 600
        assert normalize_resolution(small, config()).shape[:2] == small.shape[:2]

    def test_adaptive_processing_leaves_good_document_minimally_changed(self):
        enhanced, steps = adaptive_enhance(document_image(), config())
        assert enhanced.shape == document_image().shape
        assert "controlled_denoise" not in steps

    def test_adaptive_processing_selects_exposure_or_contrast_normalization_for_dark_input(self):
        dark = np.full((240, 380, 3), 25, dtype=np.uint8)
        cv2.rectangle(dark, (50, 60), (330, 190), (65, 65, 65), -1)
        _, steps = adaptive_enhance(dark, config())
        assert "local_contrast_normalization" in steps

    def test_adaptive_processing_selects_controlled_denoise_for_noisy_input(self):
        noise = np.random.default_rng(4).integers(0, 256, (240, 380, 3), dtype=np.uint8)
        _, steps = adaptive_enhance(noise, config())
        assert "controlled_denoise" in steps

    def test_preprocessing_falls_back_to_a_separate_original_copy_on_internal_failure(monkeypatch):
        monkeypatch.setattr(pipeline, "estimate_document_corners", lambda *_: (_ for _ in ()).throw(RuntimeError("forced")))
        image = document_image()
        result = preprocess_document_image(image, config())
        assert result.success is True
        assert result.fallback_used is True
        assert result.image.shape == image.shape
        assert result.image is not image


class TestImageEdgeCases:
    @pytest.mark.parametrize("value", [0, 255])
    def test_black_and_overexposed_images_fall_back_safely(self, value):
        result = preprocess_document_image(np.full((200, 300, 3), value, dtype=np.uint8), config())
        assert result.success is True
        assert result.image.size > 0

    def test_blurry_low_contrast_and_very_small_images_are_safe(self):
        soft = cv2.GaussianBlur(document_image(), (19, 19), 0)
        low_contrast = np.full((220, 360, 3), 120, dtype=np.uint8)
        small = np.full((30, 40, 3), 100, dtype=np.uint8)
        for image in (soft, low_contrast, small):
            result = preprocess_document_image(image, config())
            assert result.success is True
            assert result.image.size > 0
