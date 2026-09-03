from dataclasses import dataclass, field
from typing import List, Tuple, Any

@dataclass
class OCRToken:
    text: str
    confidence: float
    polygon: List[List[float]]
    bbox: List[float]
    center_x: float
    center_y: float
    width: float
    height: float
    angle: float

@dataclass
class OCRLine:
    text: str
    tokens: List[OCRToken]
    bbox: List[List[float]]  # Polygon to maintain backward compatibility
    confidence: float
    reading_order: int

    @property
    def y_mid(self) -> float:
        if not self.bbox:
            return 0.0
        return sum(pt[1] for pt in self.bbox) / len(self.bbox)

    @property
    def x_start(self) -> float:
        if not self.bbox:
            return 0.0
        return min(pt[0] for pt in self.bbox)

    @property
    def x_end(self) -> float:
        if not self.bbox:
            return 0.0
        return max(pt[0] for pt in self.bbox)

    @property
    def line_index(self) -> int:
        return self.reading_order
    
    @line_index.setter
    def line_index(self, value: int):
        self.reading_order = value

@dataclass
class OCRBlock:
    lines: List[OCRLine]
    bbox: List[float]

@dataclass
class OCRDocument:
    tokens: List[OCRToken]
    lines: List[OCRLine]
    blocks: List[OCRBlock]
    image_dimensions: Tuple[int, int]
    processing_time_ms: int
