"""
Unit tests for document parsers.
Tests all 4 parsers (Aadhaar, PAN, Voter ID, ABHA) with synthetic OCR line data.
Also tests edge cases: missing labels, low-confidence lines, OCR noise.
"""
import pytest
from app.extractors.line_reconstructor import OCRLine
from app.parsers.aadhaar import AadhaarParser
from app.parsers.aadhaar_back import AadhaarBackParser
from app.parsers.pan import PANParser
from app.parsers.voter_id import VoterIDParser
from app.parsers.abha import ABHAParser
from app.parsers.farmer_id import FarmerIDParser
from app.parsers.passport import PassportParser


def _make_line(text, confidence=0.95, y_mid=0.0, x_start=0.0, x_end=100.0, line_index=0):
    """Helper to create an OCRLine for testing."""
    return OCRLine(
        text=text,
        tokens=[],
        confidence=confidence,
        reading_order=line_index,
        bbox=[[x_start, y_mid - 10], [x_end, y_mid - 10], [x_end, y_mid + 10], [x_start, y_mid + 10]],
    )


# ── Aadhaar Parser Tests ────────────────────────────────────────

class TestAadhaarParser:
    def setup_method(self):
        self.parser = AadhaarParser()

    def test_full_extraction(self):
        lines = [
            _make_line("Government of India", 0.95, y_mid=20, line_index=0),
            _make_line("Aarav Sharma", 0.94, y_mid=60, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=2),
            _make_line("Male", 0.97, y_mid=140, line_index=3),
            _make_line("9999 9999 9910", 0.98, y_mid=200, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
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
            _make_line("Aarav Sharma", 0.94, y_mid=60, line_index=1),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=2),
            _make_line("Gender", 0.90, y_mid=130, line_index=3),
            _make_line("Male", 0.97, y_mid=150, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
        assert result.fields["name"].status == "ok"

    def test_hindi_gender(self):
        lines = [
            _make_line("Aarav Sharma", 0.94, y_mid=60, line_index=0),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=100, line_index=1),
            _make_line("पुरुष", 0.92, y_mid=140, line_index=2),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["gender"].value == "Male"

    def test_missing_dob_triggers_rescan(self):
        lines = [
            _make_line("Aarav Sharma", 0.94, y_mid=60, line_index=0),
            _make_line("Male", 0.97, y_mid=140, line_index=1),
        ]
        result = self.parser.extract_fields(lines)

        assert result.overall_status == "rescan_required"
        assert "dob" in result.failed_fields

    def test_low_confidence_name(self):
        lines = [
            _make_line("Name", 0.90, y_mid=40, line_index=0),
            _make_line("Aarav Sharma", 0.55, y_mid=60, line_index=1),
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
            _make_line("Aarav Sharma", 0.95, y_mid=130, line_index=3),
            _make_line("Father's Name", 0.88, y_mid=170, line_index=4),
            _make_line("Ramesh Sharma", 0.92, y_mid=200, line_index=5),
            _make_line("Date of Birth", 0.91, y_mid=240, line_index=6),
            _make_line("28/12/2004", 0.93, y_mid=270, line_index=7),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
        assert result.fields["name"].status == "ok"
        assert result.fields["father_name"].value == "Ramesh Sharma"
        assert result.fields["father_name"].status == "ok"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["dob"].status == "ok"
        assert result.overall_status == "ok"

    def test_missing_father_name_triggers_rescan(self):
        lines = [
            _make_line("Name", 0.90, y_mid=100, line_index=0),
            _make_line("Aarav Sharma", 0.95, y_mid=130, line_index=1),
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
            _make_line("Name: Aarav Sharma", 0.94, y_mid=100, line_index=1),
            _make_line("Father's Name: Ramesh Sharma", 0.90, y_mid=170, line_index=2),
            _make_line("Date of Birth: 28/12/2004", 0.91, y_mid=240, line_index=3),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
        assert result.fields["father_name"].value == "Ramesh Sharma"


# ── Voter ID Parser Tests ───────────────────────────────────────

class TestVoterIDParser:
    def setup_method(self):
        self.parser = VoterIDParser()

    def test_full_extraction(self):
        lines = [
            _make_line("ELECTION COMMISSION", 0.95, y_mid=20, line_index=0),
            _make_line("Name", 0.90, y_mid=60, line_index=1),
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=2),
            _make_line("Father's Name", 0.88, y_mid=130, line_index=3),
            _make_line("Ramesh Sharma", 0.92, y_mid=160, line_index=4),
            _make_line("Gender", 0.90, y_mid=200, line_index=5),
            _make_line("Male", 0.97, y_mid=230, line_index=6),
            _make_line("Date of Birth", 0.91, y_mid=270, line_index=7),
            _make_line("28/12/2004", 0.93, y_mid=300, line_index=8),
            _make_line("ABC1234567", 0.98, y_mid=350, line_index=9),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
        assert result.fields["relation_name"].value == "Ramesh Sharma"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.overall_status == "ok"

    def test_age_instead_of_dob(self):
        """Older Voter IDs show Age instead of DOB."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=1),
            _make_line("Father's Name", 0.88, y_mid=130, line_index=2),
            _make_line("Ramesh Sharma", 0.92, y_mid=160, line_index=3),
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
            _make_line("Sita Sharma", 0.94, y_mid=90, line_index=1),
            _make_line("Husband's Name", 0.88, y_mid=130, line_index=2),
            _make_line("Ramesh Sharma", 0.92, y_mid=160, line_index=3),
            _make_line("Female", 0.97, y_mid=200, line_index=4),
            _make_line("DOB: 15/06/1985", 0.91, y_mid=240, line_index=5),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["relation_name"].value == "Ramesh Sharma"
        assert result.fields["gender"].value == "Female"


# ── ABHA Parser Tests ───────────────────────────────────────────

class TestABHAParser:
    def setup_method(self):
        self.parser = ABHAParser()

    def test_full_extraction(self):
        lines = [
            _make_line("ABHA", 0.95, y_mid=20, line_index=0),
            _make_line("Name", 0.90, y_mid=60, line_index=1),
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=2),
            _make_line("Gender", 0.90, y_mid=130, line_index=3),
            _make_line("Male", 0.97, y_mid=160, line_index=4),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=200, line_index=5),
            _make_line("Mobile: 9876543210", 0.93, y_mid=240, line_index=6),
            _make_line("12-3456-7890-1234", 0.99, y_mid=300, line_index=7),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Aarav Sharma"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["mobile"].value == "9876543210"
        assert result.overall_status == "ok"

    def test_masked_mobile_not_extracted(self):
        """Masked mobile numbers should NOT be extracted."""
        lines = [
            _make_line("Name", 0.90, y_mid=60, line_index=0),
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=1),
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
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=1),
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
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=1),
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
            _make_line("Aarav Sharma", 0.94, y_mid=90, line_index=2),
            _make_line("Male", 0.97, y_mid=130, line_index=3),
            _make_line("DOB: 28/12/2004", 0.91, y_mid=170, line_index=4),
        ]
        result = self.parser.extract_fields(lines)

        # The name should be "Aarav Sharma", not the ABHA address
        assert result.fields["name"].value == "Aarav Sharma"


from app.parsers.abha import ABHAParser
from app.parsers.farmer_id import FarmerIDParser
from app.parsers.passport import PassportParser


# ── Farmer ID Parser Tests ──────────────────────────────────────

class TestFarmerIDParser:
    def setup_method(self):
        self.parser = FarmerIDParser()

    def test_full_extraction(self):
        lines = [
            _make_line("Agri record", 0.95, y_mid=20, line_index=0),
            _make_line("नाम : प्रमोद कुमार", 0.90, y_mid=50, line_index=1),
            _make_line("Pramod Kumar", 0.94, y_mid=75, line_index=2),
            _make_line("DOB : 10/06/1991", 0.92, y_mid=100, line_index=3),
            _make_line("Gender : Male", 0.96, y_mid=130, line_index=4),
            _make_line("Mobile : 9027956097", 0.95, y_mid=160, line_index=5),
            _make_line("Aadhaar : 527613815535", 0.94, y_mid=190, line_index=6),
            _make_line("Farmer ID 195 36 94 77 21", 0.98, y_mid=230, line_index=7),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "Pramod Kumar"
        assert result.fields["dob"].value == "10/06/1991"
        assert result.fields["gender"].value == "Male"
        assert result.fields["mobile"].value == "9027956097"
        assert result.fields["aadhaar_number"].value == "527613815535"
        assert result.overall_status == "ok"


# ── Passport Parser Tests ───────────────────────────────────────

class TestPassportParser:
    def setup_method(self):
        self.parser = PassportParser()

    def test_viz_extraction(self):
        lines = [
            _make_line("PASSPORT", 0.98, y_mid=20, line_index=0),
            _make_line("REPUBLIC OF INDIA", 0.95, y_mid=40, line_index=1),
            _make_line("Passport No. Z1234567", 0.96, y_mid=70, line_index=2),
            _make_line("Surname: SHARMA", 0.94, y_mid=100, line_index=3),
            _make_line("Given Name(s): AARAV", 0.95, y_mid=130, line_index=4),
            _make_line("Nationality: INDIAN", 0.96, y_mid=160, line_index=5),
            _make_line("Sex: M", 0.95, y_mid=190, line_index=6),
            _make_line("Date of Birth: 28/12/2004", 0.94, y_mid=220, line_index=7),
            _make_line("Date of Expiry: 15/08/2034", 0.93, y_mid=250, line_index=8),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "AARAV SHARMA"
        assert result.fields["surname"].value == "SHARMA"
        assert result.fields["given_name"].value == "AARAV"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["expiry_date"].value == "15/08/2034"
        assert result.fields["nationality"].value == "INDIAN"
        assert result.overall_status == "ok"

    def test_mrz_extraction(self):
        lines = [
            _make_line("P<INDSHARMA<<AARAV<<<<<<<<<<<<<<<<<<<<<<<<<", 0.96, y_mid=400, line_index=0),
            _make_line("Z1234567<0IND0412285M3408151<<<<<<<<<<<<<<02", 0.97, y_mid=430, line_index=1),
        ]
        result = self.parser.extract_fields(lines)

        assert result.fields["name"].value == "AARAV SHARMA"
        assert result.fields["surname"].value == "SHARMA"
        assert result.fields["given_name"].value == "AARAV"
        assert result.fields["gender"].value == "Male"
        assert result.fields["dob"].value == "28/12/2004"
        assert result.fields["expiry_date"].value == "15/08/2034"
        assert result.fields["nationality"].value == "INDIAN"
        assert result.overall_status == "ok"


# ── Aadhaar Back Parser Tests ───────────────────────────────────

class TestAadhaarBackParser:
    def setup_method(self):
        self.parser = AadhaarBackParser()

    def test_clean_aadhaar_back(self):
        lines = [
            _make_line("Unique Identification Authority of India", y_mid=10),
            _make_line("Address:", y_mid=30),
            _make_line("S/O: Sanjay Kumar, 1013, Jamalpur Shekhan,", y_mid=50),
            _make_line("Fatehabad, Haryana - 125120", y_mid=70),
            _make_line("9254 7440 0335", y_mid=90),
            _make_line("VID: 9111 7066 7723 9908", y_mid=110),
        ]
        result = self.parser.extract_fields(lines)
        assert result.fields["aadhaar_number"].value == "925474400335"
        assert result.fields["relation_type"].value == "S/O"
        assert result.fields["relation_name"].value == "Sanjay Kumar"
        assert result.fields["state"].value == "Haryana"
        assert result.fields["pincode"].value == "125120"
        assert "1013, Jamalpur Shekhan" in result.fields["address"].value
        assert result.overall_status == "ok"

    def test_hindi_aadhaar_back(self):
        lines = [
            _make_line("भारतीय विशिष्ट पहचान प्राधिकरण", y_mid=10),
            _make_line("पता:", y_mid=30),
            _make_line("आत्मज: रामवीर सिंह, दावकोरा, बुलंदशहर,", y_mid=50),
            _make_line("उत्तर प्रदेश - 202394", y_mid=70),
            _make_line("5276 1381 5535", y_mid=90),
        ]
        result = self.parser.extract_fields(lines)
        assert result.fields["aadhaar_number"].value == "527613815535"
        assert result.fields["relation_type"].value == "S/O"
        assert result.fields["state"].value == "Uttar Pradesh"
        assert result.fields["pincode"].value == "202394"
        assert result.overall_status == "ok"

    def test_aadhaar_back_with_ocr_noisy_footer_and_header(self):
        lines = [
            _make_line("Unique ldontificalion Authority of india", y_mid=10),
            _make_line("Address:", y_mid=30),
            _make_line("S/O: Ramveer Singh, Davkora, Bulandshahr,", y_mid=50),
            _make_line("Uttar Pradesh - 202394", y_mid=70),
            _make_line("5276 1381 5535", y_mid=90),
            _make_line("VID: 9103 6194 6407 4488", y_mid=110),
            _make_line("1947", y_mid=130),
            _make_line("helpouidai.govin", y_mid=150),
            _make_line("www.uidai-gov.in", y_mid=170),
            _make_line("P.O. Box No. 1947", y_mid=190),
            _make_line("Bengaluru - 560001", y_mid=210),
        ]
        result = self.parser.extract_fields(lines)
        assert result.fields["aadhaar_number"].value == "527613815535"
        assert result.fields["relation_type"].value == "S/O"
        assert result.fields["relation_name"].value == "Ramveer Singh"
        assert result.fields["state"].value == "Uttar Pradesh"
        assert result.fields["pincode"].value == "202394"
        assert result.fields["address"].value is not None
        assert "Ramveer Singh" in result.fields["address"].value
        assert "Unique" not in result.fields["address"].value
        assert "ldontificalion" not in result.fields["address"].value
        assert "helpouidai" not in result.fields["address"].value
        assert "Bengaluru" not in result.fields["address"].value
        assert "560001" not in result.fields["address"].value
        assert "1947" not in result.fields["address"].value
        assert result.overall_status == "ok"

    def test_aadhaar_back_rejects_fragment_and_footer_leak(self):
        lines = [
            _make_line("Unique ldontificalion Authority of india", y_mid=10),
            _make_line("3R-202394", y_mid=30),
            _make_line("helpouidai.govin", y_mid=50),
        ]
        result = self.parser.extract_fields(lines)
        # Address must be rejected under strict 'no guessing' rule
        assert result.fields["address"].value is None
        assert result.overall_status == "rescan_required"

    def test_aadhaar_back_rejects_address_with_footer_text(self):
        lines = [
            _make_line("Address: Unique Identification Authority of India, 1947, help@uidai", y_mid=30),
            _make_line("5276 1381 5535", y_mid=50),
        ]
        result = self.parser.extract_fields(lines)
        assert result.fields["address"].value is None

    def test_aadhaar_back_low_confidence_returns_none(self):
        lines = [
            _make_line("Address:", y_mid=30, confidence=0.50),
            _make_line("S/O: Ramveer Singh, Davkora, Bulandshahr,", y_mid=50, confidence=0.50),
            _make_line("Uttar Pradesh - 202394", y_mid=70, confidence=0.50),
            _make_line("5276 1381 5535", y_mid=90, confidence=0.50),
        ]
        result = self.parser.extract_fields(lines)
        assert result.fields["address"].value is None
        assert result.fields["aadhaar_number"].value is None
        assert result.overall_status == "rescan_required"


# ── Cross-Parser Tests ──────────────────────────────────────────

class TestParserInterface:
    """Verify all parsers implement the same interface correctly."""

    @pytest.mark.parametrize("parser_class", [AadhaarParser, AadhaarBackParser, PANParser, VoterIDParser, ABHAParser, FarmerIDParser, PassportParser])
    def test_empty_input_returns_rescan(self, parser_class):
        parser = parser_class()
        result = parser.extract_fields([])
        assert result.overall_status == "rescan_required"
        assert len(result.failed_fields) > 0

    @pytest.mark.parametrize("parser_class", [AadhaarParser, AadhaarBackParser, PANParser, VoterIDParser, ABHAParser, FarmerIDParser, PassportParser])
    def test_has_mandatory_fields(self, parser_class):
        parser = parser_class()
        assert len(parser.MANDATORY_FIELDS) > 0


# ── Universal "No Guessing" Strict Validation Tests ──────────────

class TestUniversalNoGuessingValidation:
    """
    Verify that no parser ever guesses, fabricates, or cross-contaminates data:
    1. Helpline 1947 is NEVER extracted as a DOB year.
    2. Address lines (with S/O, Village, Davkora, Bulandshahr) are NEVER extracted as person names.
    3. Authority headers (Unique Identification Authority of India, etc.) are NEVER extracted as person names.
    """

    def test_1947_never_extracted_as_dob_in_base_or_parsers(self):
        """Line with '1947' helpline must never be treated as birth year in any parser."""
        lines = [
            _make_line("Unique Identification Authority of India", 0.95, y_mid=20),
            _make_line("help@uidai.gov.in", 0.92, y_mid=50),
            _make_line("1947", 0.96, y_mid=80),
        ]
        
        # Test ABHA parser
        abha_res = ABHAParser().extract_fields(lines)
        assert abha_res.fields["dob"].value is None, f"ABHAParser extracted 1947 as DOB: {abha_res.fields['dob'].value}"

        # Test Aadhaar Front parser
        aadhaar_res = AadhaarParser().extract_fields(lines)
        assert aadhaar_res.fields["dob"].value is None, f"AadhaarParser extracted 1947 as DOB: {aadhaar_res.fields['dob'].value}"

        # Test PAN parser
        pan_res = PANParser().extract_fields(lines)
        assert pan_res.fields["dob"].value is None, f"PANParser extracted 1947 as DOB: {pan_res.fields['dob'].value}"

    def test_relation_address_string_never_extracted_as_name_in_abha(self):
        """Address/relation text like 'S O Ramveer Singh Davkora Bulandshahr' must never become ABHA Name."""
        lines = [
            _make_line("Ayushman Bharat Health Account", 0.95, y_mid=20),
            _make_line("S O Ramveer Singh Davkora Bulandshahr", 0.92, y_mid=60),
            _make_line("1947", 0.90, y_mid=90),
        ]
        abha_res = ABHAParser().extract_fields(lines)
        assert abha_res.fields["name"].value is None, f"ABHAParser accepted relation/address as name: {abha_res.fields['name'].value}"

    def test_authority_header_never_extracted_as_name_in_abha(self):
        """'Unique Identification Authority of India' must never become ABHA Name."""
        lines = [
            _make_line("Unique Identification Authority of India", 0.95, y_mid=20),
            _make_line("ABHA Number: 12-3456-7890-1234", 0.97, y_mid=60),
        ]
        abha_res = ABHAParser().extract_fields(lines)
        assert abha_res.fields["name"].value is None, f"ABHAParser accepted authority header as name: {abha_res.fields['name'].value}"

    def test_relation_address_string_never_extracted_as_name_in_aadhaar_front(self):
        """Address/relation text must never become Aadhaar cardholder name."""
        lines = [
            _make_line("Address:", 0.95, y_mid=20),
            _make_line("S/O: Ramveer Singh, Davkora, Bulandshahr", 0.92, y_mid=50),
            _make_line("5276 1381 5535", 0.98, y_mid=80),
        ]
        aadhaar_res = AadhaarParser().extract_fields(lines)
        assert aadhaar_res.fields["name"].value is None, f"AadhaarParser accepted back address as front name: {aadhaar_res.fields['name'].value}"

    def test_aadhaar_back_comma_relation_and_wityofindia_rejection(self):
        """
        Regression test for req_44103b8d5bba:
        - 'S/O, Paveer Singh' with comma must extract relation_type='S/O' and relation_name='Paveer Singh'.
        - Distorted footer string 'wityofindia' must NEVER be extracted as M/O / wityofindia.
        """
        lines = [
            _make_line("Unique Identification Authority of India", 0.95, y_mid=20),
            _make_line("Address: S/O, Paveer Singh, Davkora, Bulandshahr, Uttar Pradesh - 202394", 0.92, y_mid=50),
            _make_line("5276 1381 5535", 0.98, y_mid=80),
            _make_line("wityofindia", 0.85, y_mid=110),
        ]
        res = AadhaarBackParser().extract_fields(lines)
        assert res.fields["relation_type"].value == "S/O", f"Expected S/O but got {res.fields['relation_type'].value}"
        assert res.fields["relation_name"].value == "Paveer Singh", f"Expected Paveer Singh but got {res.fields['relation_name'].value}"
        assert "wityofindia" not in (res.fields["address"].value or "")

    def test_voter_id_sname_label_artifact_stripped(self):
        """
        Regression test for req_29da6895c64c:
        - 'Father'sName NAVEEN KUMAR JHA' or 'SName NAVEEN KUMAR JHA' must extract 'NAVEEN KUMAR JHA'.
        - Must never extract 'SName NAVEEN KUMAR JHA'.
        """
        lines = [
            _make_line("Elector's Name: SHASHIRANJAN KUMAR", 0.95, y_mid=30),
            _make_line("Father'sName NAVEEN KUMAR JHA", 0.92, y_mid=60),
            _make_line("UBV2991586", 0.98, y_mid=90),
        ]
        res = VoterIDParser().extract_fields(lines)
        assert res.fields["name"].value == "SHASHIRANJAN KUMAR"
        assert res.fields["relation_type"].value == "Father"
        assert res.fields["relation_name"].value == "NAVEEN KUMAR JHA", f"Expected 'NAVEEN KUMAR JHA' but got '{res.fields['relation_name'].value}'"

        # Also test with literal OCR leftover 'SName NAVEEN KUMAR JHA'
        lines2 = [
            _make_line("Name: SHASHIRANJAN KUMAR", 0.95, y_mid=30),
            _make_line("Father: SName NAVEEN KUMAR JHA", 0.92, y_mid=60),
            _make_line("UBV2991586", 0.98, y_mid=90),
        ]
        res2 = VoterIDParser().extract_fields(lines2)
        assert res2.fields["relation_name"].value == "NAVEEN KUMAR JHA"

    def test_aadhaar_back_trailing_3r_pincode_fragment_stripped(self):
        """
        Regression test for req_f9fea3acaca9:
        - Input address has trailing duplicate Hindi/OCR pincode fragment '3R-202394'
          and unspaced words 'RamveerSingh', 'UttarPradesh-202394'.
        - Verifies '3R-202394' is stripped and address is normalized to:
          'S/O: Ramveer Singh, Davkora, Bulandshahr, Uttar Pradesh - 202394'.
        """
        lines = [
            _make_line("Unique Identification Authority of India", 0.95, y_mid=20),
            _make_line("Address: S/O:RamveerSingh, Davkora, Bulandshahr,", 0.92, y_mid=50),
            _make_line("UttarPradesh-202394", 0.92, y_mid=70),
            _make_line("3R-202394", 0.85, y_mid=90),
            _make_line("5276 1381 5535", 0.98, y_mid=110),
        ]
        res = AadhaarBackParser().extract_fields(lines)
        assert res.fields["relation_type"].value == "S/O"
        assert res.fields["relation_name"].value == "Ramveer Singh"
        assert res.fields["state"].value == "Uttar Pradesh"
        assert res.fields["pincode"].value == "202394"
        assert res.fields["address"].value == "S/O: Ramveer Singh, Davkora, Bulandshahr, Uttar Pradesh - 202394"
        assert "3R" not in res.fields["address"].value
        assert res.overall_status == "ok"




