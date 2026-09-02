"""
Phase 2 image preprocessing.

The module is deliberately self-contained and never persists an input image.
Every destructive-looking operation has a validated fallback to a copy of the
decoded original, so OCR can continue if boundary detection or enhancement is
not trustworthy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import struct
import time
from typing import Any, Iterable, Optional

import cv2
import numpy as np

from app.core.config import settings


SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_FORMATS = {"jpeg", "png", "webp"}


class ImageDecodeError(ValueError):
    """A safe public decode failure; its message contains no image contents."""


@dataclass(frozen=True)
class PreprocessingConfig:
    max_upload_bytes: int
    max_image_width: int
    max_image_height: int
    max_image_pixels: int
    max_processing_dimension: int
    min_useful_ocr_dimension: int
    crop_padding_ratio: float
    min_crop_dimension: int
    min_document_area_ratio: float
    max_document_area_ratio: float
    enable_enhancement: bool
    min_document_aspect_ratio: float = 1.15
    max_document_aspect_ratio: float = 2.20
    min_corner_area_ratio: float = 0.12
    max_corner_area_ratio: float = 0.98
    low_brightness: float = 75.0
    high_brightness: float = 210.0
    low_contrast: float = 30.0
    noisy_residual: float = 14.0
    soft_text_laplacian: float = 80.0

    @classmethod
    def from_settings(cls) -> "PreprocessingConfig":
        return cls(
            max_upload_bytes=settings.max_image_size_mb * 1024 * 1024,
            max_image_width=settings.max_image_width,
            max_image_height=settings.max_image_height,
            max_image_pixels=settings.max_image_pixels,
            max_processing_dimension=settings.preprocess_max_dimension,
            min_useful_ocr_dimension=settings.preprocess_min_ocr_dimension,
            crop_padding_ratio=settings.preprocess_crop_padding_ratio,
            min_crop_dimension=settings.preprocess_min_crop_dimension,
            min_document_area_ratio=settings.preprocess_min_document_area_ratio,
            max_document_area_ratio=settings.preprocess_max_document_area_ratio,
            enable_enhancement=settings.preprocess_enable_enhancement,
        )


@dataclass
class ImageQuality:
    brightness: float
    contrast: float
    blur_variance: float
    noise_residual: float

    def as_dict(self) -> dict[str, float]:
        return {
            "brightness": round(self.brightness, 3),
            "contrast": round(self.contrast, 3),
            "blur_variance": round(self.blur_variance, 3),
            "noise_residual": round(self.noise_residual, 3),
        }


@dataclass
class DecodedImage:
    image: np.ndarray
    image_format: str
    width: int
    height: int


@dataclass
class PreprocessingResult:
    image: np.ndarray
    success: bool
    original_width: int
    original_height: int
    output_width: int
    output_height: int
    original_orientation: int = 0
    rotation: int = 0
    final_orientation: int = 0
    perspective_corrected: bool = False
    crop_applied: bool = False
    preprocessing_steps: list[str] = field(default_factory=list)
    quality_before: dict[str, float] = field(default_factory=dict)
    quality_after: dict[str, float] = field(default_factory=dict)
    processing_time_ms: int = 0
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    document_corners: Optional[list[list[float]]] = None


def decode_image_bytes(
    content: bytes,
    content_type: Optional[str],
    config: Optional[PreprocessingConfig] = None,
) -> DecodedImage:
    """Validate bytes/header dimensions before OpenCV fully decodes pixels."""
    config = config or PreprocessingConfig.from_settings()
    if content_type and content_type.lower() not in SUPPORTED_MIME_TYPES:
        raise ImageDecodeError("unsupported_media_type")
    if not content:
        raise ImageDecodeError("empty_image")
    if len(content) > config.max_upload_bytes:
        raise ImageDecodeError("image_too_large")

    image_format, width, height = inspect_image_header(content)
    if image_format not in SUPPORTED_FORMATS:
        raise ImageDecodeError("unsupported_image_format")
    validate_dimensions(width, height, config)

    try:
        decoded = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise ImageDecodeError("invalid_image_payload") from exc
    if decoded is None or decoded.size == 0:
        raise ImageDecodeError("invalid_image_payload")

    decoded_height, decoded_width = decoded.shape[:2]
    if decoded_width != width or decoded_height != height:
        # Header/decoder disagreement is suspicious and must not bypass limits.
        validate_dimensions(decoded_width, decoded_height, config)
    return DecodedImage(decoded, image_format, decoded_width, decoded_height)


def inspect_image_header(content: bytes) -> tuple[str, int, int]:
    if content.startswith(b"\xff\xd8"):
        return "jpeg", *_jpeg_dimensions(content)
    if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
        width, height = struct.unpack(">II", content[16:24])
        return "png", width, height
    if content.startswith(b"RIFF") and len(content) >= 16 and content[8:12] == b"WEBP":
        width, height = _webp_dimensions(content)
        return "webp", width, height
    raise ImageDecodeError("unsupported_image_format")


def _jpeg_dimensions(content: bytes) -> tuple[int, int]:
    offset = 2
    while offset + 9 <= len(content):
        if content[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(content):
            break
        segment_length = struct.unpack(">H", content[offset:offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(content):
            break
        if marker in {
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        }:
            if segment_length < 7:
                break
            height, width = struct.unpack(">HH", content[offset + 3:offset + 7])
            return width, height
        offset += segment_length
    raise ImageDecodeError("invalid_jpeg_header")


def _webp_dimensions(content: bytes) -> tuple[int, int]:
    chunk = content[12:16]
    if chunk == b"VP8X" and len(content) >= 30:
        width = int.from_bytes(content[24:27], "little") + 1
        height = int.from_bytes(content[27:30], "little") + 1
        return width, height
    if chunk == b"VP8 " and len(content) >= 30 and content[23:26] == b"\x9d\x01\x2a":
        width, height = struct.unpack("<HH", content[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and len(content) >= 25 and content[20] == 0x2F:
        bits = int.from_bytes(content[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise ImageDecodeError("invalid_webp_header")


def validate_dimensions(width: int, height: int, config: PreprocessingConfig) -> None:
    if width <= 0 or height <= 0:
        raise ImageDecodeError("invalid_image_dimensions")
    if width > config.max_image_width or height > config.max_image_height:
        raise ImageDecodeError("image_dimensions_exceeded")
    if width * height > config.max_image_pixels:
        raise ImageDecodeError("image_pixel_limit_exceeded")


def preprocess_document_image(
    image: np.ndarray,
    config: Optional[PreprocessingConfig] = None,
    rotation_hint: int = 0,
    candidate_corners: Optional[Iterable[Iterable[float]]] = None,
) -> PreprocessingResult:
    """Return an OCR-ready BGR image, or a safely separated original fallback."""
    config = config or PreprocessingConfig.from_settings()
    if image is None or image.size == 0 or len(image.shape) not in {2, 3}:
        raise ValueError("invalid_decoded_image")
    original = ensure_bgr(image)
    original_height, original_width = original.shape[:2]
    started = time.perf_counter()
    before = calculate_image_quality(original)
    working = original.copy()
    steps: list[str] = ["decoded_original"]
    perspective_corrected = False
    crop_applied = False
    corners_used: Optional[np.ndarray] = None
    rotation = 0

    try:
        rotation = normalize_rotation(rotation_hint)
        if rotation:
            working = rotate_image(working, rotation)
            steps.append(f"rotation_{rotation}")

        if candidate_corners is not None:
            raw_corners = np.asarray(list(candidate_corners), dtype=np.float32)
            if validate_document_corners(raw_corners, working.shape[1], working.shape[0], config):
                corners_used = raw_corners

        if corners_used is None:
            detected = estimate_document_corners(working, config)
            if detected is not None:
                corners_used = detected

        if corners_used is not None:
            rectified = perspective_correct(working, corners_used, config)
            if rectified is not None:
                working = rectified
                perspective_corrected = True
                crop_applied = True
                steps.append("perspective_rectification")

        normalized = normalize_resolution(working, config)
        if normalized.shape[:2] != working.shape[:2]:
            working = normalized
            steps.append("resolution_downscale")

        if config.enable_enhancement:
            enhanced, enhancement_steps = adaptive_enhance(working, config)
            if enhancement_steps:
                enhanced_quality = calculate_image_quality(enhanced)
                if quality_utility(enhanced_quality, config) >= quality_utility(calculate_image_quality(working), config):
                    working = enhanced
                    steps.extend(enhancement_steps)
                else:
                    steps.append("enhancement_reverted")

        after = calculate_image_quality(working)
        output_height, output_width = working.shape[:2]
        return PreprocessingResult(
            image=working,
            success=True,
            original_width=original_width,
            original_height=original_height,
            output_width=output_width,
            output_height=output_height,
            rotation=rotation,
            final_orientation=rotation,
            perspective_corrected=perspective_corrected,
            crop_applied=crop_applied,
            preprocessing_steps=steps,
            quality_before=before.as_dict(),
            quality_after=after.as_dict(),
            processing_time_ms=int((time.perf_counter() - started) * 1000),
            document_corners=corners_used.astype(float).tolist() if corners_used is not None else None,
        )
    except Exception as exc:
        output_height, output_width = original.shape[:2]
        return PreprocessingResult(
            image=original.copy(),
            success=True,
            original_width=original_width,
            original_height=original_height,
            output_width=output_width,
            output_height=output_height,
            rotation=0,
            final_orientation=0,
            preprocessing_steps=["decoded_original", "fallback_original"],
            quality_before=before.as_dict(),
            quality_after=before.as_dict(),
            processing_time_ms=int((time.perf_counter() - started) * 1000),
            fallback_used=True,
            fallback_reason=type(exc).__name__,
        )


def ensure_bgr(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def normalize_rotation(rotation: int) -> int:
    if rotation not in {0, 90, 180, 270}:
        raise ValueError("unsupported_rotation")
    return rotation


def rotate_image(image: np.ndarray, rotation: int) -> np.ndarray:
    rotation = normalize_rotation(rotation)
    if rotation == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if rotation == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image.copy()


def order_corners(corners: np.ndarray) -> np.ndarray:
    """Order a known convex quadrilateral clockwise from top-left."""
    points = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    ordered = points[np.argsort(angles)]
    start = int(np.argmin(ordered.sum(axis=1)))
    return np.roll(ordered, -start, axis=0)


def validate_document_corners(
    corners: np.ndarray,
    width: int,
    height: int,
    config: PreprocessingConfig,
) -> bool:
    if corners.shape != (4, 2) or not np.isfinite(corners).all():
        return False
    if (corners[:, 0] < 0).any() or (corners[:, 1] < 0).any():
        return False
    if (corners[:, 0] >= width).any() or (corners[:, 1] >= height).any():
        return False
    contour = corners.astype(np.float32).reshape(-1, 1, 2)
    if not cv2.isContourConvex(contour):
        return False
    area_ratio = abs(cv2.contourArea(contour)) / float(width * height)
    if not config.min_corner_area_ratio <= area_ratio <= config.max_corner_area_ratio:
        return False
    side_lengths = [np.linalg.norm(corners[(index + 1) % 4] - corners[index]) for index in range(4)]
    if min(side_lengths) < config.min_crop_dimension * 0.25:
        return False
    return True


def estimate_document_corners(image: np.ndarray, config: PreprocessingConfig) -> Optional[np.ndarray]:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best: Optional[np.ndarray] = None
    best_area = 0.0
    for contour in contours:
        area = abs(cv2.contourArea(contour))
        area_ratio = area / float(width * height)
        if not config.min_document_area_ratio <= area_ratio <= config.max_document_area_ratio:
            continue
        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approximation) != 4:
            continue
        corners = order_corners(approximation.reshape(4, 2))
        if not validate_document_corners(corners, width, height, config):
            continue
        output_width, output_height = perspective_dimensions(corners)
        aspect = max(output_width / max(output_height, 1), output_height / max(output_width, 1))
        if not config.min_document_aspect_ratio <= aspect <= config.max_document_aspect_ratio:
            continue
        if area > best_area:
            best = corners
            best_area = area
    return best


def perspective_dimensions(corners: np.ndarray) -> tuple[int, int]:
    ordered = order_corners(corners)
    top = np.linalg.norm(ordered[1] - ordered[0])
    bottom = np.linalg.norm(ordered[2] - ordered[3])
    right = np.linalg.norm(ordered[2] - ordered[1])
    left = np.linalg.norm(ordered[3] - ordered[0])
    return max(1, int(round(max(top, bottom)))), max(1, int(round(max(left, right))))


def perspective_correct(image: np.ndarray, corners: np.ndarray, config: PreprocessingConfig) -> Optional[np.ndarray]:
    height, width = image.shape[:2]
    ordered = order_corners(corners)
    if not validate_document_corners(ordered, width, height, config):
        return None
    output_width, output_height = perspective_dimensions(ordered)
    if output_width < config.min_crop_dimension or output_height < config.min_crop_dimension:
        return None
    scale = min(1.0, config.max_processing_dimension / max(output_width, output_height))
    output_width = max(config.min_crop_dimension, int(round(output_width * scale)))
    output_height = max(config.min_crop_dimension, int(round(output_height * scale)))
    destination = np.array(
        [[0, 0], [output_width - 1, 0], [output_width - 1, output_height - 1], [0, output_height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(ordered.astype(np.float32), destination)
    warped = cv2.warpPerspective(image, matrix, (output_width, output_height), flags=cv2.INTER_CUBIC)
    return warped if warped is not None and warped.size else None


def smart_crop(
    image: np.ndarray,
    bounds: tuple[int, int, int, int],
    config: PreprocessingConfig,
) -> Optional[np.ndarray]:
    height, width = image.shape[:2]
    x, y, crop_width, crop_height = bounds
    padding_x = int(round(crop_width * config.crop_padding_ratio))
    padding_y = int(round(crop_height * config.crop_padding_ratio))
    left = max(0, x - padding_x)
    top = max(0, y - padding_y)
    right = min(width, x + crop_width + padding_x)
    bottom = min(height, y + crop_height + padding_y)
    if right <= left or bottom <= top:
        return None
    if right - left < config.min_crop_dimension or bottom - top < config.min_crop_dimension:
        return None
    return image[top:bottom, left:right].copy()


def normalize_resolution(image: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    height, width = image.shape[:2]
    maximum = max(width, height)
    if maximum <= config.max_processing_dimension:
        return image.copy()
    scale = config.max_processing_dimension / float(maximum)
    return cv2.resize(image, (max(1, int(round(width * scale))), max(1, int(round(height * scale)))), interpolation=cv2.INTER_AREA)


def adaptive_enhance(image: np.ndarray, config: PreprocessingConfig) -> tuple[np.ndarray, list[str]]:
    quality = calculate_image_quality(image)
    enhanced = image.copy()
    steps: list[str] = []
    if quality.brightness < config.low_brightness or quality.brightness > config.high_brightness or quality.contrast < config.low_contrast:
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        lightness, a_channel, b_channel = cv2.split(lab)
        lightness = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
        enhanced = cv2.cvtColor(cv2.merge((lightness, a_channel, b_channel)), cv2.COLOR_LAB2BGR)
        steps.append("local_contrast_normalization")
    if quality.noise_residual > config.noisy_residual:
        enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 3, 3, 7, 21)
        steps.append("controlled_denoise")
    if quality.blur_variance < config.soft_text_laplacian:
        softened = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        enhanced = cv2.addWeighted(enhanced, 1.25, softened, -0.25, 0)
        steps.append("controlled_sharpen")
    return enhanced, steps


def calculate_image_quality(image: np.ndarray) -> ImageQuality:
    gray = cv2.cvtColor(ensure_bgr(image), cv2.COLOR_BGR2GRAY)
    brightness, contrast = cv2.meanStdDev(gray)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    residual = cv2.absdiff(gray, cv2.medianBlur(gray, 3))
    return ImageQuality(
        brightness=float(brightness[0][0]),
        contrast=float(contrast[0][0]),
        blur_variance=float(laplacian.var()),
        noise_residual=float(np.mean(residual)),
    )


def quality_utility(quality: ImageQuality, config: PreprocessingConfig) -> float:
    brightness_midpoint = (config.low_brightness + config.high_brightness) / 2
    brightness_range = (config.high_brightness - config.low_brightness) / 2
    brightness_score = max(0.0, 1.0 - abs(quality.brightness - brightness_midpoint) / brightness_range)
    contrast_score = min(1.0, quality.contrast / config.low_contrast)
    sharpness_score = min(1.0, quality.blur_variance / config.soft_text_laplacian)
    noise_score = max(0.0, 1.0 - quality.noise_residual / max(config.noisy_residual * 2, 1))
    return 0.30 * brightness_score + 0.30 * contrast_score + 0.25 * sharpness_score + 0.15 * noise_score
