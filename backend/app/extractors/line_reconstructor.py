from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.ocr.models import OCRToken, OCRLine, OCRBlock, OCRDocument
import math
import numpy as np
import time

def _compute_angle(bbox: List[List[float]]) -> float:
    if len(bbox) < 4:
        return 0.0
    dx = bbox[1][0] - bbox[0][0]
    dy = bbox[1][1] - bbox[0][1]
    return math.degrees(math.atan2(dy, dx))

def _rotate_point(x: float, y: float, angle_degrees: float, cx: float = 0, cy: float = 0) -> Tuple[float, float]:
    angle_rad = math.radians(angle_degrees)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    nx = cos_a * (x - cx) - sin_a * (y - cy) + cx
    ny = sin_a * (x - cx) + cos_a * (y - cy) + cy
    return nx, ny

def reconstruct_document(raw_ocr_results: List[Dict[str, Any]], image_dimensions: Tuple[int, int] = (0, 0), processing_time_ms: int = 0, y_tolerance: int | None = None) -> OCRDocument:
    """
    Takes raw OCR output and creates a full OCRDocument with tokens, lines, and blocks.
    Uses geometric sorting (handles rotation and multi-column).
    """
    if not raw_ocr_results:
        return OCRDocument(tokens=[], lines=[], blocks=[], image_dimensions=image_dimensions, processing_time_ms=processing_time_ms)

    y_tol = y_tolerance if y_tolerance is not None else settings.line_merge_y_tolerance

    tokens: List[OCRToken] = []
    for entry in raw_ocr_results:
        text = entry.get("text", "").strip()
        if not text:
            continue
        conf = entry.get("confidence", 0.0)
        bbox = entry.get("bbox", [])
        if len(bbox) < 4:
            continue

        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        w = x_max - x_min
        h = y_max - y_min
        cx = x_min + w / 2
        cy = y_min + h / 2
        angle = _compute_angle(bbox)

        tokens.append(OCRToken(
            text=text,
            confidence=conf,
            polygon=bbox,
            bbox=[x_min, y_min, x_max, y_max],
            center_x=cx,
            center_y=cy,
            width=w,
            height=h,
            angle=angle
        ))

    if not tokens:
        return OCRDocument(tokens=[], lines=[], blocks=[], image_dimensions=image_dimensions, processing_time_ms=processing_time_ms)

    angles = [t.angle for t in tokens if abs(t.angle) > 0.1 and abs(t.angle) < 45]
    dominant_angle = float(np.median(angles)) if angles else 0.0

    for t in tokens:
        nx, ny = _rotate_point(t.center_x, t.center_y, -dominant_angle)
        t._sort_x = nx
        t._sort_y = ny

    tokens.sort(key=lambda t: t._sort_y)

    bands: List[List[OCRToken]] = []
    current_band: List[OCRToken] = [tokens[0]]
    current_band_y = tokens[0]._sort_y

    for t in tokens[1:]:
        threshold = max(y_tol, min(t.height, current_band[-1].height) * 0.4)
        if abs(t._sort_y - current_band_y) <= threshold:
            current_band.append(t)
            current_band_y = sum(ct._sort_y for ct in current_band) / len(current_band)
        else:
            bands.append(current_band)
            current_band = [t]
            current_band_y = t._sort_y

    bands.append(current_band)

    lines: List[OCRLine] = []
    blocks: List[OCRBlock] = []
    line_index = 0
    for band in bands:
        band.sort(key=lambda t: t._sort_x)
        # Create an OCRBlock for the band
        band_lines = []
        for t in band:
            line = OCRLine(
                text=t.text,
                tokens=[t],
                bbox=t.polygon,
                confidence=t.confidence,
                reading_order=line_index
            )
            band_lines.append(line)
            lines.append(line)
            line_index += 1
            
        if band_lines:
            pts = [p for l in band_lines for p in l.bbox]
            bx_min = min(p[0] for p in pts)
            by_min = min(p[1] for p in pts)
            bx_max = max(p[0] for p in pts)
            by_max = max(p[1] for p in pts)
            blocks.append(OCRBlock(lines=band_lines, bbox=[bx_min, by_min, bx_max, by_max]))

    return OCRDocument(
        tokens=tokens,
        lines=lines,
        blocks=blocks,
        image_dimensions=image_dimensions,
        processing_time_ms=processing_time_ms
    )

def reconstruct_lines(raw_ocr_results: List[Dict[str, Any]], y_tolerance: int | None = None) -> List[OCRLine]:
    """
    Takes raw OCR output and reconstructs logical reading order.
    Returns just the lines for backwards compatibility with legacy parsers.
    """
    doc = reconstruct_document(raw_ocr_results, y_tolerance=y_tolerance)
    return doc.lines
