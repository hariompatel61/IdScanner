"""
Unit tests for field validators.
Tests date validation, gender normalization, mobile validation, and name validation.
"""
import pytest
from app.validators.field_validators import (
    validate_date,
    normalize_date,
    normalize_gender,
    validate_mobile,
    normalize_mobile,
    validate_name,
)


# ── Date Validation ──────────────────────────────────────────────

class TestValidateDate:
    def test_valid_dd_mm_yyyy_slash(self):
        assert validate_date("28/12/2004") is True

    def test_valid_dd_mm_yyyy_dash(self):
        assert validate_date("28-12-2004") is True

    def test_valid_dd_mm_yyyy_dot(self):
        assert validate_date("28.12.2004") is True

    def test_valid_single_digit_day_month(self):
        assert validate_date("1/1/1990") is True

    def test_valid_year_only(self):
        assert validate_date("1990") is True

    def test_invalid_day_too_high(self):
        assert validate_date("32/01/2000") is False

    def test_invalid_month_too_high(self):
        assert validate_date("01/13/2000") is False

    def test_invalid_year_too_old(self):
        assert validate_date("01/01/1899") is False

    def test_invalid_year_future(self):
        assert validate_date("01/01/2099") is False

    def test_invalid_feb_30(self):
        assert validate_date("30/02/2000") is False

    def test_invalid_empty(self):
        assert validate_date("") is False

    def test_invalid_garbage(self):
        assert validate_date("abc") is False

    def test_invalid_april_31(self):
        assert validate_date("31/04/2000") is False


class TestNormalizeDate:
    def test_normalize_slash(self):
        assert normalize_date("28/12/2004") == "28/12/2004"

    def test_normalize_dash(self):
        assert normalize_date("28-12-2004") == "28/12/2004"

    def test_normalize_dot(self):
        assert normalize_date("28.12.2004") == "28/12/2004"

    def test_normalize_single_digits(self):
        assert normalize_date("1/1/1990") == "01/01/1990"

    def test_normalize_year_only(self):
        assert normalize_date("1990") == "1990"

    def test_normalize_invalid(self):
        assert normalize_date("abc") is None

    def test_normalize_empty(self):
        assert normalize_date("") is None


# ── Gender Normalization ─────────────────────────────────────────

class TestNormalizeGender:
    def test_male_english(self):
        assert normalize_gender("Male") == "Male"

    def test_female_english(self):
        assert normalize_gender("Female") == "Female"

    def test_male_lowercase(self):
        assert normalize_gender("male") == "Male"

    def test_m_shorthand(self):
        assert normalize_gender("M") == "Male"

    def test_f_shorthand(self):
        assert normalize_gender("F") == "Female"

    def test_male_hindi(self):
        assert normalize_gender("पुरुष") == "Male"

    def test_female_hindi(self):
        assert normalize_gender("महिला") == "Female"

    def test_transgender(self):
        assert normalize_gender("Transgender") == "Transgender"

    def test_ocr_misread_malo(self):
        assert normalize_gender("Malo") == "Male"

    def test_ocr_misread_famale(self):
        assert normalize_gender("Famale") == "Female"

    def test_invalid(self):
        assert normalize_gender("xyz") is None

    def test_empty(self):
        assert normalize_gender("") is None


# ── Mobile Validation ────────────────────────────────────────────

class TestValidateMobile:
    def test_valid_10_digit(self):
        assert validate_mobile("9876543210") is True

    def test_valid_starts_6(self):
        assert validate_mobile("6123456789") is True

    def test_valid_with_country_code(self):
        assert validate_mobile("919876543210") is True

    def test_valid_with_plus_country_code(self):
        assert validate_mobile("+919876543210") is True

    def test_invalid_starts_5(self):
        assert validate_mobile("5123456789") is False

    def test_invalid_too_short(self):
        assert validate_mobile("98765432") is False

    def test_invalid_masked(self):
        assert validate_mobile("XXXXXX1234") is False

    def test_invalid_empty(self):
        assert validate_mobile("") is False


class TestNormalizeMobile:
    def test_normalize_plain(self):
        assert normalize_mobile("9876543210") == "9876543210"

    def test_normalize_with_spaces(self):
        assert normalize_mobile("987 654 3210") == "9876543210"

    def test_normalize_with_country_code(self):
        assert normalize_mobile("919876543210") == "9876543210"

    def test_normalize_invalid(self):
        assert normalize_mobile("12345") is None

    def test_normalize_masked(self):
        assert normalize_mobile("XXXXXX1234") is None


# ── Name Validation ──────────────────────────────────────────────

class TestValidateName:
    def test_valid_name(self):
        assert validate_name("Hari Om Patel") is True

    def test_valid_hindi_name(self):
        assert validate_name("हरिओम पटेल") is True

    def test_invalid_too_short(self):
        assert validate_name("A") is False

    def test_invalid_all_digits(self):
        assert validate_name("12345") is False

    def test_invalid_empty(self):
        assert validate_name("") is False

    def test_invalid_known_label(self):
        assert validate_name("DOB") is False

    def test_invalid_header(self):
        assert validate_name("Gender") is False
