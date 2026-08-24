"""
Unit tests for OCR line reconstructor.
Tests sorting, horizontal band grouping, and line index assignment.
"""
import pytest
from app.extractors.line_reconstructor import reconstruct_lines, OCRLine


def _make_ocr_entry(text, confidence, x1, y1, x2, y2):
    """Helper to create a raw OCR result dict with a bounding box."""
    return {
        "text": text,
        "confidence": confidence,
        "bbox": [
            [x1, y1],       # top-left
            [x2, y1],       # top-right
            [x2, y2],       # bottom-right
            [x1, y2],       # bottom-left
        ]
    }


class TestReconstructLines:
    def test_empty_input(self):
        result = reconstruct_lines([])
        assert result == []

    def test_single_line(self):
        raw = [_make_ocr_entry("Hello", 0.95, 10, 10, 100, 30)]
        result = reconstruct_lines(raw)
        assert len(result) == 1
        assert result[0].text == "Hello"
        assert result[0].line_index == 0

    def test_top_to_bottom_ordering(self):
        """Lines at different Y positions should be sorted top-to-bottom."""
        raw = [
            _make_ocr_entry("Line3", 0.9, 10, 100, 200, 120),  # bottom
            _make_ocr_entry("Line1", 0.9, 10, 10, 200, 30),    # top
            _make_ocr_entry("Line2", 0.9, 10, 50, 200, 70),    # middle
        ]
        result = reconstruct_lines(raw)
        assert [r.text for r in result] == ["Line1", "Line2", "Line3"]

    def test_left_to_right_within_band(self):
        """Lines at the same Y should be sorted left-to-right."""
        raw = [
            _make_ocr_entry("Right", 0.9, 200, 10, 300, 30),
            _make_ocr_entry("Left", 0.9, 10, 10, 100, 30),
        ]
        result = reconstruct_lines(raw, y_tolerance=20)
        assert [r.text for r in result] == ["Left", "Right"]

    def test_band_grouping_within_tolerance(self):
        """Lines within Y tolerance should be in the same band."""
        raw = [
            _make_ocr_entry("A", 0.9, 10, 10, 100, 30),    # y_mid = 20
            _make_ocr_entry("B", 0.9, 200, 15, 300, 35),   # y_mid = 25 (within 15px tolerance)
        ]
        result = reconstruct_lines(raw, y_tolerance=15)
        # Both should be in the same band, sorted left-to-right
        assert len(result) == 2
        assert result[0].text == "A"
        assert result[1].text == "B"
        # Same line_index group (consecutive since same band)
        assert result[0].line_index == 0
        assert result[1].line_index == 1

    def test_separate_bands(self):
        """Lines beyond Y tolerance should be in separate bands."""
        raw = [
            _make_ocr_entry("Top", 0.9, 10, 10, 100, 30),      # y_mid = 20
            _make_ocr_entry("Bottom", 0.9, 10, 100, 100, 120),  # y_mid = 110
        ]
        result = reconstruct_lines(raw, y_tolerance=15)
        assert result[0].text == "Top"
        assert result[1].text == "Bottom"

    def test_confidence_preserved(self):
        raw = [_make_ocr_entry("Test", 0.88, 10, 10, 100, 30)]
        result = reconstruct_lines(raw)
        assert result[0].confidence == 0.88

    def test_empty_text_skipped(self):
        raw = [
            _make_ocr_entry("Valid", 0.9, 10, 10, 100, 30),
            _make_ocr_entry("", 0.5, 10, 50, 100, 70),
            _make_ocr_entry("   ", 0.5, 10, 90, 100, 110),
        ]
        result = reconstruct_lines(raw)
        assert len(result) == 1
        assert result[0].text == "Valid"

    def test_line_index_sequential(self):
        """Line indices should be sequential across all bands."""
        raw = [
            _make_ocr_entry("A", 0.9, 10, 10, 100, 30),
            _make_ocr_entry("B", 0.9, 200, 10, 300, 30),
            _make_ocr_entry("C", 0.9, 10, 100, 100, 120),
            _make_ocr_entry("D", 0.9, 200, 100, 300, 120),
        ]
        result = reconstruct_lines(raw, y_tolerance=15)
        assert [r.line_index for r in result] == [0, 1, 2, 3]

    def test_real_document_layout(self):
        """Simulate a PAN card layout to ensure correct reconstruction."""
        raw = [
            _make_ocr_entry("INCOME TAX DEPARTMENT", 0.95, 200, 20, 700, 50),
            _make_ocr_entry("ABCDE1234F", 0.99, 50, 180, 350, 220),
            _make_ocr_entry("Name", 0.90, 50, 240, 150, 260),
            _make_ocr_entry("HARI OM PATEL", 0.94, 50, 280, 350, 310),
            _make_ocr_entry("Father's Name", 0.88, 50, 330, 250, 350),
            _make_ocr_entry("RAMESH PATEL", 0.92, 50, 370, 300, 400),
            _make_ocr_entry("Date of Birth", 0.91, 50, 420, 250, 440),
            _make_ocr_entry("28/12/2004", 0.93, 50, 460, 250, 490),
        ]
        result = reconstruct_lines(raw, y_tolerance=15)
        texts = [r.text for r in result]
        assert texts[0] == "INCOME TAX DEPARTMENT"
        assert "HARI OM PATEL" in texts
        assert "28/12/2004" in texts
