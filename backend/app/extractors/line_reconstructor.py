"""
Line Reconstructor — Sorts and groups raw OCR bounding-box output
into logical reading order (top-to-bottom, left-to-right within bands).

This is critical because labels ("Name") and values ("Aarav Sharma")
often appear on adjacent lines or adjacent horizontal positions, and
raw OCR order is not guaranteed to be spatially consistent.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from app.core.config import settings


@dataclass
class OCRLine:
    """Represents a single logical line of OCR text with spatial metadata."""
    text: str
    confidence: float
    y_mid: float
    x_start: float
    x_end: float
    line_index: int = 0
    bbox: List[List[float]] = field(default_factory=list)


def _compute_y_mid(bbox: List[List[float]]) -> float:
    """Compute the vertical midpoint of a bounding box (average of all Y coords)."""
    if not bbox or len(bbox) < 4:
        return 0.0
    return sum(point[1] for point in bbox) / len(bbox)


def _compute_x_start(bbox: List[List[float]]) -> float:
    """Compute the leftmost X coordinate of a bounding box."""
    if not bbox or len(bbox) < 4:
        return 0.0
    return min(point[0] for point in bbox)


def _compute_x_end(bbox: List[List[float]]) -> float:
    """Compute the rightmost X coordinate of a bounding box."""
    if not bbox or len(bbox) < 4:
        return 0.0
    return max(point[0] for point in bbox)


def reconstruct_lines(
    raw_ocr_results: List[Dict[str, Any]],
    y_tolerance: int | None = None,
) -> List[OCRLine]:
    """
    Takes raw OCR output and reconstructs logical reading order.

    Args:
        raw_ocr_results: List of dicts with keys: text, confidence, bbox.
            bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        y_tolerance: Pixel tolerance for grouping lines into horizontal bands.
            Defaults to settings.line_merge_y_tolerance.

    Returns:
        List of OCRLine objects in logical reading order (top-to-bottom,
        left-to-right within each band), with line_index assigned.
    """
    if not raw_ocr_results:
        return []

    if y_tolerance is None:
        y_tolerance = settings.line_merge_y_tolerance

    # Step 1: Convert raw dicts to intermediate objects with spatial info
    items = []
    for entry in raw_ocr_results:
        text = entry.get("text", "").strip()
        if not text:
            continue
        confidence = entry.get("confidence", 0.0)
        bbox = entry.get("bbox", [])
        y_mid = _compute_y_mid(bbox)
        x_start = _compute_x_start(bbox)
        x_end = _compute_x_end(bbox)
        items.append(OCRLine(
            text=text,
            confidence=confidence,
            y_mid=y_mid,
            x_start=x_start,
            x_end=x_end,
            bbox=bbox,
        ))

    if not items:
        return []

    # Step 2: Sort by Y midpoint (top-to-bottom)
    items.sort(key=lambda item: item.y_mid)

    # Step 3: Group into horizontal bands using Y tolerance
    bands: List[List[OCRLine]] = []
    current_band: List[OCRLine] = [items[0]]
    current_band_y = items[0].y_mid

    for item in items[1:]:
        if abs(item.y_mid - current_band_y) <= y_tolerance:
            # Same band
            current_band.append(item)
        else:
            # New band
            bands.append(current_band)
            current_band = [item]
            current_band_y = item.y_mid

    # Don't forget the last band
    bands.append(current_band)

    # Step 4: Within each band, sort left-to-right by X start
    result: List[OCRLine] = []
    line_index = 0
    for band in bands:
        band.sort(key=lambda item: item.x_start)
        for item in band:
            item.line_index = line_index
            result.append(item)
            line_index += 1

    return result
