"""
Unit tests for document parsers.
Tests all 4 parsers (Aadhaar, PAN, Voter ID, ABHA) with synthetic OCR line data.
Also tests edge cases: missing labels, low-confidence lines, OCR noise.
"""
import pytest
from app.extractors.line_reconstructor import OCRLine
from app.parsers.aadhaar import AadhaarParser
from app.parsers.pan import PANParser
from app.parsers.voter_id import VoterIDParser
from app.parsers.abha import ABHAParser


def _make_line(text, confidence=0.95, y_mid=0.0, x_start=0.0, x_end=100.0, line_index=0):
    """Helper to create an OCRLine for testing."""
    return OCRLine(
        text=text,
        confidence=confidence,
        y_mid=y_mid,
        x_start=x_start,
        x_end=x_end,
        line_index=line_index,
        bbox=[[x_start, y_mid - 10], [x_end, y_mid - 10], [x_end, y_mid + 10], [x_start, y_mid + 10]],
    )


# ── Aadhaar Parser Tests ────────────────────────────────────────

class TestAadhaarParser:
    def setup_method(self):
        self.parser = AadhaarParser()

    def test_full_extraction(self):
        lines = [
            _make_line("Government of India", 0.95, y_mid=20, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=60, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=2),
            _make_line("Male", 0.97, y_mid=140, line_index=3),
            _make_line("8253 9563 3085", 0.98, y_mid=200, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["name"].status == "ok"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["dob"].status == "ok"
        assert result.fields["gender"].value == "Male"
        assert result.fields["gender"].status == "ok"
        assert result.overall_status == "ok"
        assert result.failed_fields == []

    def test_name_with_label_anchor(self):
        lines = [
            _make_line("Name", 0.90, y_mid=40, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=60, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=2),
            _make_line("Gender", 0.90, y_mid=130, line_index=3),
            _make_line("Male", 0.97, y_mid=150, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["name"].status == "ok"

    def test_hindi_gender(self):
        lines = [
            _make_line("Hari Om Patel", 0.94, y_mid=60, line_index=0),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=1),
            _make_line("पुरुष", 0.92, y_mid=140, line_index=2),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["gender"].value == "Male"

    def test_missing_dob_triggers_rescan(self):
        lines = [
            _make_line("Hari Om Patel", 0.94, y_mid=60, line_index=0),
            _make_line("Male", 0.97, y_mid=140, line_index=1),
        ]
        result = self.parser.extract_fields(lines)

        assert result.overall_status == "rescan_required"
        assert "dob" in result.failed_fields

    def test_low_confidence_name(self):
        lines = [
            _make_line("Name", 0.90, y_mid=40, line_index=0),
            _make_line("Hari Om Patel", 0.55, y_mid=60, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=2),
            _make_line("Male", 0.97, y_mid=140, line_index=3),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].status == "low_confidence"
        assert result.overall_status == "rescan_required"
        assert "name" in result.failed_fields


# ── PAN Parser Tests ─────────────────────────────────────────────

class TestPANParser:
    def setup_method(self):
        self.parser = PANParser()

    def test_full_extraction(self):
        lines = [
            _make_line("INCOME TAX DEPARTMENT", 0.95, y_mid=20, line_index=0),
            _make_line("ABCDE1234F", 0.99, y_mid=60, line_index=1),
            _make_line("Name", 0.90, y_mid=100, line_index=2),
            _make_line("Hari Om Patel", 0.95, y_mid=130, line_index=3),
            _make_line("Father's Name", 0.88, y_mid=170, line_index=4),
            _make_line("Ramesh Patel", 0.92, y_mid=200, line_index=5),
            _make_line("Date of Birth", 0.91, y_mid=240, line_index=6),
            _make_line("28/12/2004", 0.93, y_mid=270, line_index=7),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["name"].status == "ok"
        assert result.fields["father_name"].value == "Ramesh Patel"
        assert result.fields["father_name"].status == "ok"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["dob"].status == "ok"
        assert result.overall_status == "ok"

    def test_missing_father_name_triggers_rescan(self):
        lines = [
            _make_line("Name", 0.90, y_mid=100, line_index=0),
            _make_line("Hari Om Patel", 0.95, y_mid=130, line_index=1),
            _make_line("Date of Birth", 0.91, y_mid=240, line_index=2),
            _make_line("28/12/2004", 0.93, y_mid=270, line_index=3),
        ]
        result = self.parser.extract_fields(lines)

        assert result.overall_status == "rescan_required"
        assert "father_name" in result.failed_fields

    def test_inline_name_extraction(self):
        """Test extracting name when label and value are on the same line."""
        lines = [
            _make_line("INCOME TAX DEPARTMENT", 0.95, y_mid=20, line_index=0),
            _make_line("Name: Hari Om Patel", 0.94, y_mid=100, line_index=1),
            _make_line("Father's Name: Ramesh Patel", 0.90, y_mid=170, line_index=2),
            _make_line("Date of Birth: 28/12/2004", 0.91, y_mid=240, line_index=3),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["father_name"].value == "Ramesh Patel"


# ── Voter ID Parser Tests ───────────────────────────────────────

class TestVoterIDParser:
    def setup_method(self):
        self.parser = VoterIDParser()

    def test_full_extraction(self):
        lines = [
            _make_line("ELECTION COMMISSION", 0.95, y_mid=20, line_index=0),
            _make_line("Name", 0.90, y_mid=60, line_index=1),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=2),
            _make_line("Father's Name", 0.88, y_mid=130, line_index=3),
            _make_line("Ramesh Patel", 0.92, y_mid=160, line_index=4),
            _make_line("Gender", 0.90, y_mid=200, line_index=5),
            _make_line("Male", 0.97, y_mid=230, line_index=6),
            _make_line("Date of Birth", 0.91, y_mid=270, line_index=7),
            _make_line("28/12/2004", 0.93, y_mid=300, line_index=8),
            _make_line("ABC1234567", 0.98, y_mid=350, line_index=9),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["relation_name"].value == "Ramesh Patel"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.overall_status == "ok"

    def test_age_instead_of_dob(self):
        """Older Voter IDs show Age instead of DOB."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=1),
            _make_line("Father's Name", 0.88, y_mid=130, line_index=2),
            _make_line("Ramesh Patel", 0.92, y_mid=160, line_index=3),
            _make_line("Gender", 0.90, y_mid=200, line_index=4),
            _make_line("Male", 0.97, y_mid=230, line_index=5),
            _make_line("Age: 35", 0.91, y_mid=270, line_index=6),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["dob"].value == "Age: 35"
        assert result.fields["dob"].status == "ok"

    def test_husband_relation(self):
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Sita Patel", 0.94, y_mid=90, line_index=1),
            _make_line("Husband's Name", 0.88, y_mid=130, line_index=2),
            _make_line("Ramesh Patel", 0.92, y_mid=160, line_index=3),
            _make_line("Female", 0.97, y_mid=200, line_index=4),
            _make_line("DOB: 15/06/1985", 0.91, y_mid=240, line_index=5),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["relation_name"].value == "Ramesh Patel"
        assert result.fields["gender"].value == "Female"


# ── ABHA Parser Tests ───────────────────────────────────────────

class TestABHAParser:
    def setup_method(self):
        self.parser = ABHAParser()

    def test_full_extraction(self):
        lines = [
            _make_line("ABHA", 0.95, y_mid=20, line_index=0),
            _make_line("Name", 0.90, y_mid=60, line_index=1),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=2),
            _make_line("Gender", 0.90, y_mid=130, line_index=3),
            _make_line("Male", 0.97, y_mid=160, line_index=4),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=200, line_index=5),
            _make_line("Mobile: 9876543210", 0.93, y_mid=240, line_index=6),
            _make_line("12-3456-7890-1234", 0.99, y_mid=300, line_index=7),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Hari Om Patel"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["mobile"].value == "9876543210"
        assert result.overall_status == "ok"

    def test_masked_mobile_not_extracted(self):
        """Masked mobile numbers should NOT be extracted."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=1),
            _make_line("Gender: Male", 0.97, y_mid=130, line_index=2),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=200, line_index=3),
            _make_line("Mobile: XXXXXX3210", 0.93, y_mid=240, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["mobile"].status == "not_found"
        # Mobile is optional, so overall should still be "ok"
        assert result.overall_status == "ok"

    def test_missing_mobile_does_not_block(self):
        """Mobile is optional — missing mobile should NOT trigger rescan."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=1),
            _make_line("Gender", 0.90, y_mid=130, line_index=2),
            _make_line("Male", 0.97, y_mid=160, line_index=3),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=200, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["mobile"].status == "not_found"
        assert result.overall_status == "ok"
        assert "mobile" not in result.failed_fields

    def test_missing_gender_triggers_rescan(self):
        """Gender is mandatory — missing it should trigger rescan."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=200, line_index=2),
        ]
        result = self.parser.extract_fields(lines)

        assert result.overall_status == "rescan_required"
        assert "gender" in result.failed_fields

    def test_abha_address_skipped_as_name(self):
        """ABHA address pattern should not be extracted as a name."""
        lines = [
            _make_line("ABHA", 0.95, y_mid=20, line_index=0),
            _make_line("john.doe@abdm", 0.93, y_mid=50, line_index=1),
            _make_line("Hari Om Patel", 0.94, y_mid=90, line_index=2),
            _make_line("Male", 0.97, y_mid=130, line_index=3),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=170, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        # The name should be "Hari Om Patel", not the ABHA address
        assert result.fields["name"].value == "Hari Om Patel"


# ── Cross-Parser Tests ──────────────────────────────────────────

class TestParserInterface:
    """Verify all parsers implement the same interface correctly."""

    @pytest.mark.parametrize("parser_class", [AadhaarParser, PANParser, VoterIDParser, ABHAParser])
    def test_empty_input_returns_rescan(self, parser_class):
        parser = parser_class()
        result = parser.extract_fields([])
        assert result.overall_status == "rescan_required"
        assert len(result.failed_fields) > 0

    @pytest.mark.parametrize("parser_class", [AadhaarParser, PANParser, VoterIDParser, ABHAParser])
    def test_has_mandatory_fields(self, parser_class):
        parser = parser_class()
        assert len(parser.MANDATORY_FIELDS) > 0
