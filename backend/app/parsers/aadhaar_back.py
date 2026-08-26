"""
Aadhaar Card Back Side Parser.

Extracts:
- aadhaar_number (12 digits, validated via Verhoeff algorithm)
- relation_type (S/O, D/O, W/O, C/O, M/O, etc.)
- relation_name (Name of father/husband/mother/guardian)
- address (Clean formatted full address string, strictly bounded and validated)
- state (Standardized Indian State / UT)
- pincode (6-digit Indian PIN code)

Follows strict 'no guessing' rules:
- Low-confidence, ambiguous, or unvalidated fields return None.
- Fuzzy footer detection catches OCR variations of UIDAI headers, email, web, helpline, and P.O. Box.
- Rejects address if footer/signature text is detected or boundary is invalid.
"""

import re
from typing import List, Optional, Tuple, Dict
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.extractors.verhoeff import validate_verhoeff
from app.core.config import settings
from app.validators.field_validators import (
    clean_name_text,
    validate_name,
    extract_state_from_text,
    extract_pincode_from_text,
    validate_pincode,
    validate_address,
)

# Comprehensive UIDAI footer / header regex pattern for OCR variations
FOOTER_REGEX = re.compile(
    r'(?:'
    # Unique Identification Authority of India (English & OCR variations)
    r'(?:unique|unlque|uniqe|ldontif|ldentif|identif|1dentif)\w*[\s\-_]*(?:authorit|authorlt|authorty|authorityoftndia|authorityofindia)\w*|'
    r'(?:unique|unlque|uniqe)[\s\-_]*(?:identif|ldontif|ldentif|1dentif|ident|ldent)\w*|'
    r'(?:authorit|authorlt|authorty|wity|wityofindia|thorityofindia)\w*[\s\-_]*(?:of)?[\s\-_]*(?:india|lndia|tndia|1ndia)?|'
    r'authority\s*of\s*india|'
    r'wity\s*of\s*india|'
    r'unique\s*identification|'
    # Hindi Authority Header
    r'(?:भारतीय\s*)?विशिष्ट\s*पहचान\s*प्राधिकरण|'
    r'विशिष्ट\s*पहचान|'
    r'पहचान\s*प्राधिकरण|'
    # Help Email (help@uidai, helpouidai, heip@uidai, he1p@uidai, etc.)
    r'(?:help|heip|he1p|helpdesk)[@ou0\.\-_\s]*(?:uidai|u1da1|ulda)|'
    r'help[@ou0][a-z0-9\.\-_]*gov[\.\-_]?in|'
    r'\bhelp@|'
    # Website (www.uidai, www-uidai, uidai.gov.in, uidai-gov.in, etc.)
    r'(?:www|http|https)[\.\-_\s]*(?:uidai|u1da1|ulda)|'
    r'uidai[\.\-_\s]*(?:gov|nic)[\.\-_\s]*in|'
    r'www[\.\-_\s]*[a-z0-9\-]+[\.\-_\s]*gov[\.\-_\s]*in|'
    # Helpline (1947, 1800 300 1947, 1800-300-1947, toll free, helpline)
    r'\b1947\b|'
    r'1800[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}|'
    r'\b(?:toll[\s\-]*free|helpline)\b|'
    # P.O. Box & UIDAI Regional Hubs
    r'p[\.\s]*o[\.\s]*box|'
    r'post[\s]*box|'
    r'p\.o\.\s*box\s*no\.?\s*\d*|'
    r'(?:gpo|bengaluru|bangalore|ranchi|chhindwara|manesar)[\s\-]*(?:560\s*001|834\s*002|480\s*001|122\s*050)?|'
    # Virtual ID (VID)
    r'\bvid\b|'
    r'vid\s*[:\-]?\s*\d{4}|'
    r'vid\d{16}|'
    # Signature & metadata
    r'signature\s*valid|'
    r'digitally\s*signed|'
    r'हस्ताक्षर|'
    r'प्रमाणित'
    r')',
    re.I
)

# Address keywords that must NOT be part of a relation name
ADDRESS_STOPWORDS = {
    "village", "post", "po", "dist", "district", "tehsil", "taluka", "ward", "block",
    "street", "road", "marg", "nagar", "colony", "enclave", "society", "apartment",
    "floor", "flat", "house", "plot", "khasra", "sector", "lane", "gali", "mohalla",
    "puram", "pincode", "pin", "state", "near", "behind", "opposite", "opp", "dav",
    "bulandshahr", "fatehabad", "basti", "lucknow", "delhi", "haryana", "patna"
}


def is_footer_or_header_line(text: str) -> bool:
    """
    Returns True if the line is purely or predominantly UIDAI header, footer,
    helpline, email, website, PO box, VID, or signature.
    """
    if not text or not text.strip():
        return False

    cleaned = text.strip()

    # Direct regex match
    if FOOTER_REGEX.search(cleaned):
        return True

    # Check 12-digit Aadhaar number line
    digits = re.sub(r'[^\d]', '', cleaned)
    if len(digits) == 12 and validate_verhoeff(digits):
        return True

    # Check 16-digit VID line
    if len(digits) == 16:
        return True

    # Fuzzy check for authority name variations
    lower = cleaned.lower()
    authority_keywords = {"unique", "identification", "authority", "india", "ldontificalion", "ldentificalion", "authorityoftndia", "authorityofindia", "wityofindia", "wity", "tndia", "lndia"}
    words = set(re.findall(r'[a-z]+', lower))
    if len(words & authority_keywords) >= 2 or any(w in {"wityofindia", "authorityoftndia", "authorityofindia", "thorityofindia"} for w in words):
        return True

    return False


def contains_footer_text(text: str) -> bool:
    """
    Returns True if the text contains any UIDAI header/footer tokens or keywords.
    """
    if not text:
        return False
    if FOOTER_REGEX.search(text):
        return True
    lower = text.lower()
    authority_keywords = {"unique", "identification", "authority", "india", "ldontificalion", "ldentificalion", "authorityoftndia", "authorityofindia", "wityofindia", "wity", "tndia", "lndia"}
    words = set(re.findall(r'[a-z]+', lower))
    if len(words & authority_keywords) >= 2 or any(w in {"wityofindia", "authorityoftndia", "authorityofindia", "thorityofindia"} for w in words):
        return True
    return False


class AadhaarBackParser(BaseDocParser):
    MANDATORY_FIELDS = ["aadhaar_number", "address", "state", "pincode"]
    OPTIONAL_FIELDS = ["relation_type", "relation_name"]

    RELATION_PATTERNS = [
        (r'(?:^|[\s,;])\b(?:S/O|S/0|SO|S\\O|SON\s*OF|आत्मज|सुपुत्र|पुत्र)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "S/O"),
        (r'(?:^|[\s,;])\b(?:D/O|D/0|DO|D\\O|DAUGHTER\s*OF|सुपुत्री|पुत्री|आत्मजा)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "D/O"),
        (r'(?:^|[\s,;])\b(?:W/O|W/0|WO|W\\O|WIFE\s*OF|पत्नी)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "W/O"),
        (r'(?:^|[\s,;])\b(?:C/O|C/0|CO|C\\O|CARE\s*OF)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "C/O"),
        (r'(?:^|[\s,;])\b(?:F/O|F/0|FO|FATHER\s*OF|पिता)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "S/O"),
        (r'(?:^|[\s,;])\b(?:M/O|M/0|MOTHER\s*OF|माता)\b\s*[:\-\.,]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "M/O"),
    ]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        if not ocr_lines:
            return self._build_result({})

        fields: Dict[str, FieldResult] = {}
        # Filter out footer lines for global text search
        non_footer_lines = [l for l in ocr_lines if not is_footer_or_header_line(l.text)]
        non_footer_text = " ".join([l.text for l in non_footer_lines])

        # 1. Extract Aadhaar Number (Verhoeff validated 12 digits)
        fields["aadhaar_number"] = self._extract_aadhaar_number(ocr_lines)

        # 2. Extract Relation Type and Relation Name
        r_type_res, r_name_res = self._extract_relation(non_footer_lines, non_footer_text)
        fields["relation_type"] = r_type_res
        fields["relation_name"] = r_name_res

        # 3. Extract State (only from non-footer lines)
        fields["state"] = self._extract_state(non_footer_lines, non_footer_text)

        # 4. Extract PIN Code (only from non-footer lines)
        fields["pincode"] = self._extract_pincode(non_footer_lines, non_footer_text)

        # 5. Extract Address String (strictly bounded and validated)
        fields["address"] = self._extract_address(ocr_lines)

        return self._build_result(fields)

    def _extract_aadhaar_number(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extracts 12-digit Aadhaar number validated by Verhoeff checksum.
        Strictly ignores 16-digit VIDs and helpline numbers (1947).
        """
        pattern = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')
        best_num = None
        best_conf = 0.0

        for line in ocr_lines:
            text = line.text
            # Skip explicit VID lines
            if re.search(r'\bVID\b', text, re.I):
                continue

            matches = pattern.finditer(text)
            for m in matches:
                raw_str = m.group(0)
                clean_str = re.sub(r'[Oo]', '0', raw_str)
                clean_str = re.sub(r'[^\d]', '', clean_str)
                if len(clean_str) == 12 and validate_verhoeff(clean_str):
                    if line.confidence > best_conf:
                        best_conf = line.confidence
                        best_num = clean_str

            # Check unspaced digits in line
            digits = re.sub(r'[^\d]', '', text)
            if len(digits) == 12 and validate_verhoeff(digits):
                if line.confidence > best_conf:
                    best_conf = line.confidence
                    best_num = digits

        if best_num and best_conf >= settings.field_confidence_threshold:
            return FieldResult(
                value=best_num,
                confidence=round(best_conf, 4),
                status="ok"
            )
        elif best_num:
            return FieldResult(
                value=None,
                confidence=round(best_conf, 4),
                status="low_confidence"
            )
        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_relation(self, non_footer_lines: List[OCRLine], all_text: str) -> Tuple[FieldResult, FieldResult]:
        """
        Extracts relation type and relation name strictly.
        Rejects names containing address keywords, numbers, or footer tokens.
        """
        for line in non_footer_lines:
            for pattern, r_type in self.RELATION_PATTERNS:
                match = re.search(pattern, line.text, re.I)
                if match:
                    raw_name = match.group(1).strip()
                    cleaned_name = clean_name_text(raw_name)
                    if self._is_valid_relation_name(cleaned_name):
                        conf = line.confidence
                        status = "ok" if conf >= settings.field_confidence_threshold else "low_confidence"
                        val = cleaned_name if status == "ok" else None
                        return (
                            FieldResult(value=r_type if val else None, confidence=round(conf, 4), status=status),
                            FieldResult(value=val, confidence=round(conf, 4), status=status)
                        )

        # Fallback search across concatenated non-footer text
        for pattern, r_type in self.RELATION_PATTERNS:
            match = re.search(pattern, all_text, re.I)
            if match:
                raw_name = match.group(1).strip()
                cleaned_name = clean_name_text(raw_name)
                if self._is_valid_relation_name(cleaned_name):
                    return (
                        FieldResult(value=r_type, confidence=0.85, status="ok"),
                        FieldResult(value=cleaned_name, confidence=0.85, status="ok")
                    )

        return (
            FieldResult(value=None, confidence=0.0, status="not_found"),
            FieldResult(value=None, confidence=0.0, status="not_found")
        )

    def _is_valid_relation_name(self, name: str) -> bool:
        """Validates relation name string strictly."""
        if not name or len(name) < 3 or not validate_name(name):
            return False
        if contains_footer_text(name):
            return False
        # Reject if name contains distorted authority/header artifacts
        if re.search(r'(?:wity|india|authority|unique|identif|uidai|ofindia|oftndia|oflndia)', name, re.I):
            return False
        # Reject if name contains address words
        name_words = set(re.findall(r'[a-zA-Z\u0900-\u097F]+', name.lower()))
        if any(w in ADDRESS_STOPWORDS for w in name_words):
            return False
        return True

    def _extract_state(self, non_footer_lines: List[OCRLine], all_text: str) -> FieldResult:
        """Extracts Indian State/UT strictly from non-footer lines."""
        for line in non_footer_lines:
            state = extract_state_from_text(line.text)
            if state:
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(
                    value=state if status == "ok" else None,
                    confidence=round(line.confidence, 4),
                    status=status
                )

        state = extract_state_from_text(all_text)
        if state:
            return FieldResult(value=state, confidence=0.85, status="ok")

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_pincode(self, non_footer_lines: List[OCRLine], all_text: str) -> FieldResult:
        """Extracts 6-digit Indian PIN code strictly from non-footer lines."""
        for line in non_footer_lines:
            pin = extract_pincode_from_text(line.text)
            if pin and validate_pincode(pin) and pin != "1947":
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(
                    value=pin if status == "ok" else None,
                    confidence=round(line.confidence, 4),
                    status=status
                )

        pin = extract_pincode_from_text(all_text)
        if pin and validate_pincode(pin) and pin != "1947":
            return FieldResult(value=pin, confidence=0.85, status="ok")

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_address(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extracts address string with strict boundary detection and validation.
        - Identifies start anchor (Address / पता / Relation prefix).
        - Stops immediately upon encountering UIDAI header, footer, 12-digit ID, VID, or signature.
        - Rejects the entire address if footer/signature text is detected or if validation fails.
        """
        address_segments: List[str] = []
        confidences: List[float] = []
        is_collecting = False

        for line in ocr_lines:
            text = line.text.strip()
            if not text:
                continue

            # Check if this line is a footer / header line
            if is_footer_or_header_line(text):
                if is_collecting:
                    # Reached end of address block
                    break
                else:
                    # Ignore header lines before address
                    continue

            # Match Address header line start anchor
            if re.search(r'^(?:Address|पता|पत्ता|निवासाचा\s*पत्ता)\s*[:\-]?', text, re.I):
                is_collecting = True
                after = re.sub(r'^(?:Address|पता|पत्ता|निवासाचा\s*पत्ता)\s*[:\-]?\s*', '', text, flags=re.I).strip()
                if after and not is_footer_or_header_line(after):
                    address_segments.append(after)
                    confidences.append(line.confidence)
                continue

            # Match Relation prefix line as start anchor if Address label was missing
            if not is_collecting and re.search(r'^(?:S/O|S/0|D/O|D/0|W/O|W/0|C/O|C/0|आत्मज|सुपुत्र|पुत्र|पत्नी|पती)\s*[:\-]', text, re.I):
                is_collecting = True
                address_segments.append(text)
                confidences.append(line.confidence)
                continue

            if is_collecting:
                # Stop if reached bottom section / footer / aadhaar number / VID / uidai
                if is_footer_or_header_line(text) or contains_footer_text(text):
                    break
                # Skip duplicate / distorted pincode fragments (e.g. 3R-202394, UP-202394) if we already have segments with a pincode
                if address_segments and re.match(r'^(?:[0-9A-Za-z]{1,4}[\s\-:]*)?\b[1-9]\d{5}\b$', text):
                    if any(re.search(r'\b[1-9]\d{5}\b', seg) for seg in address_segments):
                        break
                address_segments.append(text)
                confidences.append(line.confidence)

        # If no address segments were collected from anchors, check for a clean contiguous block with relation & state
        if not address_segments:
            temp_segments: List[str] = []
            temp_confs: List[float] = []
            for line in ocr_lines:
                text = line.text.strip()
                if is_footer_or_header_line(text) or contains_footer_text(text):
                    continue
                # Line containing relation or state/pincode
                if re.search(r'(?:S/O|D/O|W/O|C/O|आत्मज|सुपुत्र|पुत्र|पत्नी|पती|Haryana|Uttar\s*Pradesh|Maharashtra|Delhi|\b[1-9][0-9]{5}\b)', text, re.I):
                    temp_segments.append(text)
                    temp_confs.append(line.confidence)

            if temp_segments:
                combined_candidate = ", ".join(temp_segments)
                if validate_address(combined_candidate):
                    address_segments = temp_segments
                    confidences = temp_confs

        if not address_segments:
            return FieldResult(value=None, confidence=0.0, status="not_found")

        # Combine segments cleanly
        raw_combined = ", ".join(address_segments)

        # Normalize relation prefix at start of address
        cleaned = re.sub(r'^(?:S/0|S\\0|SO|S/O)\s*[:\-]?', 'S/O: ', raw_combined, flags=re.I)
        cleaned = re.sub(r'^(?:D/0|D\\0|DO|D/O)\s*[:\-]?', 'D/O: ', cleaned, flags=re.I)
        cleaned = re.sub(r'^(?:W/0|W\\0|WO|W/O)\s*[:\-]?', 'W/O: ', cleaned, flags=re.I)
        cleaned = re.sub(r'^(?:C/0|C\\0|CO|C/O)\s*[:\-]?', 'C/O: ', cleaned, flags=re.I)

        # Truncate duplicate trailing OCR fragments after the first complete PIN code
        # e.g., "S/O: Ramveer Singh, Davkora, Bulandshahr, Uttar Pradesh - 202394, 3R-202394"
        # -> "S/O: Ramveer Singh, Davkora, Bulandshahr, Uttar Pradesh - 202394"
        pin_matches = list(re.finditer(r'\b([1-9]\d{5})\b', cleaned))
        if len(pin_matches) >= 1:
            first_pin = pin_matches[0]
            after_first = cleaned[first_pin.end():].strip(' ,.-')
            if after_first and (
                re.search(r'\b\d{6}\b', after_first)
                or re.search(r'^(?:[0-9A-Za-z]{1,4}[\s\-:]*)?\d{6}$', after_first)
                or len(after_first.split()) <= 2
                or contains_footer_text(after_first)
            ):
                cleaned = cleaned[:first_pin.end()].strip(' ,.-')

        # Split joined camelCase/PascalCase words (e.g. "RamveerSingh" -> "Ramveer Singh", "UttarPradesh" -> "Uttar Pradesh")
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)

        # Standardize state and pincode spacing: e.g. "Uttar Pradesh-202394" -> "Uttar Pradesh - 202394"
        cleaned = re.sub(r'([A-Za-z]+)\s*[\-:]\s*(\d{6})\b', r'\1 - \2', cleaned)

        # Clean delimiters, double commas, and excessive spaces
        cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
        cleaned = re.sub(r',\s*,+', ', ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,.-')

        # Strict validation: reject entire address if footer text leaked or validation fails
        if contains_footer_text(cleaned) or not validate_address(cleaned):
            return FieldResult(value=None, confidence=0.0, status="not_found")

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.85
        if avg_conf < settings.field_confidence_threshold:
            return FieldResult(value=None, confidence=round(avg_conf, 4), status="low_confidence")

        return FieldResult(value=cleaned, confidence=round(avg_conf, 4), status="ok")
