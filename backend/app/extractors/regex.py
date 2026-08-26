import re
from typing import Optional, Dict, Any, List
from app.extractors.verhoeff import validate_verhoeff

class BaseExtractor:
    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class AadhaarExtractor(BaseExtractor):
    def __init__(self):
        # Captures 12 digits, possibly separated by spaces or hyphens, or common OCR noise
        # Aadhaar numbers often have formatting like XXXX XXXX XXXX
        self.pattern = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # If document has explicit Farmer ID / Agri record banner, Aadhaar is a secondary field
        all_text = " ".join([l.get('text', '') for l in ocr_results])
        if re.search(r'(agri\s*record|farmer\s*id|farmerid|kisan\s*id|kisan\s*card|agrirecord)', all_text, re.I):
            return None

        # If document is clearly the back side (has Address / S/O / P.O. Box), yield to AadhaarBackExtractor
        is_back = bool(re.search(r'(address\s*:|पता\s*:|p\.o\.\s*box|help@uidai|www\.uidai|s/o|d/o|w/o|c/o)', all_text, re.I))
        has_front_markers = bool(re.search(r'(dob|date\s*of\s*birth|जन्म\s*तिथि|male|female|पुरुष|महिला)', all_text, re.I))
        if is_back and not has_front_markers:
            return None

        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            matches = self.pattern.finditer(text)
            for match in matches:
                # Normalize string to purely 12 digits, handling OCR O/o -> 0 confusion
                raw_str = match.group(0)
                # First swap O/o to 0
                clean_str = re.sub(r'[Oo]', '0', raw_str)
                # Then remove all non-digits
                clean_str = re.sub(r'[^\d]', '', clean_str)
                if len(clean_str) == 12:
                    if validate_verhoeff(clean_str):
                        if conf > highest_conf:
                            highest_conf = conf
                            best_candidate = clean_str

        if best_candidate:
            return {
                "document_type": "AADHAAR_CARD",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None

class AadhaarBackExtractor(BaseExtractor):
    def __init__(self):
        self.pattern = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        all_text = " ".join([l.get('text', '') for l in ocr_results])
        if re.search(r'(agri\s*record|farmer\s*id|farmerid|kisan\s*id|kisan\s*card|agrirecord)', all_text, re.I):
            return None

        is_back = bool(re.search(
            r'(?:address|पता|पत्ता|निवासाचा|unique|unlque|ldontif|ldentif|identif|authorit|uidai|p[\.\s]*o[\.\s]*box|help[@ou0]|www[\.\-_]|1947|1800[\s\-]?[0-9]{3}|s/o|s/0|d/o|d/0|w/o|w/0|c/o|c/0|आत्मज|सुपुत्र|पुत्र|पत्नी|पती)',
            all_text,
            re.I
        ))
        
        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            matches = self.pattern.finditer(text)
            for match in matches:
                raw_str = match.group(0)
                clean_str = re.sub(r'[Oo]', '0', raw_str)
                clean_str = re.sub(r'[^\d]', '', clean_str)
                if len(clean_str) == 12:
                    if validate_verhoeff(clean_str):
                        if conf > highest_conf:
                            highest_conf = conf
                            best_candidate = clean_str

        # Also check unspaced 12-digit lines
        if not best_candidate:
            for line in ocr_results:
                text = line.get('text', '')
                conf = line.get('confidence', 0.0)
                digits = re.sub(r'[^\d]', '', text)
                if len(digits) == 12 and validate_verhoeff(digits):
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = digits

        if best_candidate and is_back:
            return {
                "document_type": "AADHAAR_CARD_BACK",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None

class PANExtractor(BaseExtractor):
    def __init__(self):
        # PAN format: 5 Letters, 4 Digits, 1 Letter
        self.pattern = re.compile(r'\b([A-Z]{5})(\d{4})([A-Z])\b', re.IGNORECASE)

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            # Common OCR fixes before match for PAN specific structure
            # e.g., if it reads 0 instead of O in the first 5 chars
            match = self.pattern.search(text)
            if match:
                candidate = match.group(0).upper()
                # Document context check (ensure it's not a generic ID but specifically a PAN)
                # This could be enhanced with checking adjacent lines for "Permanent Account Number"
                if conf > highest_conf:
                    highest_conf = conf
                    best_candidate = candidate

        if best_candidate:
            return {
                "document_type": "PAN_CARD",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None

class VoterIDExtractor(BaseExtractor):
    def __init__(self):
        # Typical EPIC is 3 Letters + 7 Digits (e.g. ABC1234567)
        # Some legacy formats exist. We will support standard + common older state prefixes
        self.patterns = [
            re.compile(r'\b[A-Z]{3}[0-9]{7}\b', re.IGNORECASE),
            re.compile(r'\b[A-Z]{2}\/[0-9]{2}\/[0-9]{3}\/[0-9]{6}\b', re.IGNORECASE) # Legacy format
        ]

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            for p in self.patterns:
                match = p.search(text)
                if match:
                    candidate = match.group(0).upper()
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = candidate

        if best_candidate:
            return {
                "document_type": "VOTER_ID",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None

class ABHAExtractor(BaseExtractor):
    """
    Extracts ABHA (Ayushman Bharat Health Account) identifiers.

    Strict 'no guessing' rules:
    - ABHA Address (health ID) must use a verified ABHA handle domain
      (@abdm, @sbx, @hpr.abdm, @eua, @ndhm, @facility, @dev.abdm, @facility.sbx)
      OR the document must contain explicit Ayushman/ABHA card context.
    - Government/support emails (help@uidai, @gov.in, @nic.in, support@, info@,
      contact@, helpdesk@) are NEVER valid ABHA addresses.
    - If the document contains an Aadhaar back-side marker (Address:, S/O, P.O. Box,
      help@uidai, 1947, www.uidai) WITHOUT explicit ABHA context, classification is rejected.
    """

    # Verified ABHA handle domains — only these are accepted as abha_address
    _ABHA_DOMAINS = {
        "abdm", "sbx", "hpr.abdm", "eua", "ndhm", "facility", "dev.abdm", "facility.sbx",
    }

    # Email domains / patterns that are known non-ABHA government / support emails
    _REJECTED_EMAIL_DOMAINS = re.compile(
        r'@(uidai|gov\.in|nic\.in|gmail\.com|yahoo\.com|yahoo\.co\.in|outlook\.com|hotmail\.com'
        r'|incometax\.gov|election\.gov|epfo\.gov|esi\.gov|mca\.gov|mospi\.gov|mohfw\.gov'
        r'|mahaonline\.gov|pmjay\.gov|nhm\.gov|nhp\.gov)',
        re.I
    )
    _REJECTED_EMAIL_PREFIXES = re.compile(
        r'^(help|support|info|contact|helpdesk|care|service|noreply|no-reply|admin|webmaster|postmaster)@',
        re.I
    )

    # Keywords indicating explicit ABHA / Ayushman card context
    _ABHA_CONTEXT_PATTERN = re.compile(
        r'(ayushman\s*bharat|national\s*health\s*authority|abha|health\s*id|health\s*account'
        r'|abdm|ndhm|आयुष्मान\s*भारत)',
        re.I
    )

    # Aadhaar back-side markers that must NOT be on an ABHA card
    _AADHAAR_BACK_MARKERS = re.compile(
        r'(address\s*:|पता\s*:|unique\s*identification\s*authority|p\.o\.?\s*box'
        r'|help@uidai|www\.uidai|s/o|d/o|w/o|c/o|\b1947\b)',
        re.I
    )

    def _is_valid_abha_address(self, addr: str, has_abha_context: bool) -> bool:
        """Return True only if addr is a genuine ABHA health handle."""
        if not addr or "@" not in addr:
            return False

        addr_lower = addr.lower().strip()

        # Hard reject: known government/support email domains
        if self._REJECTED_EMAIL_DOMAINS.search(addr_lower):
            return False

        # Hard reject: known support email prefixes (help@, support@, info@, etc.)
        if self._REJECTED_EMAIL_PREFIXES.match(addr_lower):
            return False

        # The domain part must be a verified ABHA handle OR we need explicit ABHA card context
        _, _, domain = addr_lower.partition("@")
        domain = domain.strip(".")

        if domain in self._ABHA_DOMAINS:
            return True

        # If it's some other custom handle and the document has strong ABHA context, accept it
        if has_abha_context and re.match(r'^[a-z0-9._\-]+$', domain):
            return True

        return False

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        all_text = " ".join([l.get("text", "") for l in ocr_results])
        # Text without email addresses to check for genuine card-level context
        all_text_no_emails = re.sub(r'\S+@\S+', ' ', all_text)

        # Check for Aadhaar back markers and genuine ABHA card context
        has_aadhaar_back = bool(self._AADHAAR_BACK_MARKERS.search(all_text))
        has_abha_context = bool(self._ABHA_CONTEXT_PATTERN.search(all_text_no_emails))

        # If Aadhaar back markers are present without genuine card-level ABHA context, skip entirely
        if has_aadhaar_back and not has_abha_context:
            return None

        # If Farmer ID context is present, skip
        if re.search(r'(agri\s*record|farmer\s*id|farmerid|kisan\s*id|kisan\s*card)', all_text, re.I):
            return None

        best_number = None
        highest_number_conf = 0.0
        best_address = None
        highest_address_conf = 0.0

        for line in ocr_results:
            text = line.get("text", "")
            conf = line.get("confidence", 0.0)

            # Look for 14-digit ABHA Number (XX-XXXX-XXXX-XXXX)
            num_match = self.number_pattern.search(text)
            if num_match:
                raw_num = re.sub(r"[^\d]", "", num_match.group(0))
                if len(raw_num) == 14:
                    norm_num = f"{raw_num[0:2]}-{raw_num[2:6]}-{raw_num[6:10]}-{raw_num[10:14]}"
                    if conf > highest_number_conf:
                        highest_number_conf = conf
                        best_number = norm_num

            # Look for ABHA Address — only valid ABHA handles
            addr_match = re.search(r'\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\b', text)
            if addr_match:
                addr_candidate = addr_match.group(0)
                if self._is_valid_abha_address(addr_candidate, has_abha_context):
                    if conf > highest_address_conf:
                        highest_address_conf = conf
                        best_address = addr_candidate.lower()

        # Only return if we have at minimum a 14-digit ABHA number, OR a valid ABHA address
        # with strong ABHA context on the document
        if best_number:
            return {
                "document_type": "ABHA_NUMBER",
                "identifier": best_number,
                "abha_number": best_number,
                "abha_address": best_address,
                "confidence": highest_number_conf,
            }

        if best_address and has_abha_context:
            return {
                "document_type": "ABHA_NUMBER",
                "identifier": best_address,
                "abha_number": None,
                "abha_address": best_address,
                "confidence": highest_address_conf,
            }

        return None

    # Keep attribute for backward compatibility
    @property
    def number_pattern(self):
        return self.__dict__.get("_number_pattern") or re.compile(r'\b\d{2}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b')

    @number_pattern.setter
    def number_pattern(self, value):
        self.__dict__["_number_pattern"] = value

class FarmerIDExtractor(BaseExtractor):
    def __init__(self):
        self.explicit_pattern = re.compile(
            r'(?:Farmer\s*ID|FarmerID|Kisan\s*ID|Agri\s*ID)[\s:\-]*([0-9\s]{9,16})',
            re.IGNORECASE
        )
        self.digits_pattern = re.compile(r'\b(\d{3})\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b')

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0
        has_farmer_context = False

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)

            if re.search(r'(agri|farmer|kisan|record|कृषि|किसान)', text, re.I):
                has_farmer_context = True

            # 1. Check explicit label (e.g. Farmer ID 195 36 94 77 21)
            match = self.explicit_pattern.search(text)
            if match:
                raw_digits = re.sub(r'[^\d]', '', match.group(1))
                if len(raw_digits) == 11:
                    formatted = f"{raw_digits[0:3]} {raw_digits[3:5]} {raw_digits[5:7]} {raw_digits[7:9]} {raw_digits[9:11]}"
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = formatted

            # 2. Check 11-digit pattern
            d_match = self.digits_pattern.search(text)
            if d_match:
                raw_digits = "".join(d_match.groups())
                if len(raw_digits) == 11:
                    formatted = f"{raw_digits[0:3]} {raw_digits[3:5]} {raw_digits[5:7]} {raw_digits[7:9]} {raw_digits[9:11]}"
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = formatted

        if best_candidate and (has_farmer_context or highest_conf > 0.7):
            return {
                "document_type": "FARMER_ID",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None

class PassportExtractor(BaseExtractor):
    def __init__(self):
        # Indian & standard ICAO passports: 1 letter + 7 digits (e.g. Z1234567) or 1-2 letters + 7 digits
        self.passport_pattern = re.compile(r'\b([A-PR-WYZ][0-9]{7})\b', re.IGNORECASE)
        self.mrz_line2_pattern = re.compile(r'\b([A-PR-WYZ0-9]{8,9})[<0-9][A-Z]{3}', re.IGNORECASE)
        self.explicit_pattern = re.compile(
            r'(?:Passport\s*(?:No|Number|#)?|पासपोर्ट\s*(?:नं|संख्या)?)[\s:\-]*([A-Z][0-9]{7,8})\b',
            re.IGNORECASE
        )

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0
        has_passport_context = False

        # First check overall document context for passport indicators
        all_text = " ".join([l.get('text', '') for l in ocr_results])
        if re.search(r'(passport|republic\s*of\s*india|भारत\s*गणराज्य|पासपोर्ट|given\s*name|surname|nationality|type\s*p|p<ind|p<)', all_text, re.I):
            has_passport_context = True

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)

            # 1. Explicit Anchor match
            m_exp = self.explicit_pattern.search(text)
            if m_exp:
                cand = m_exp.group(1).upper()
                if conf > highest_conf:
                    highest_conf = conf
                    best_candidate = cand

            # 2. MRZ Line 2 extraction
            m_mrz = self.mrz_line2_pattern.search(text)
            if m_mrz:
                cand = m_mrz.group(1).replace('<', '').upper()
                if len(cand) == 8 and re.match(r'^[A-Z][0-9]{7}$', cand):
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = cand

            # 3. Standard 1 letter + 7 digits pattern
            for match in self.passport_pattern.finditer(text):
                cand = match.group(1).upper()
                # Exclude common PAN prefixes or other collisions if no passport context
                if has_passport_context or conf > 0.85:
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = cand

        if best_candidate and (has_passport_context or highest_conf > 0.8):
            return {
                "document_type": "PASSPORT",
                "identifier": best_candidate,
                "confidence": highest_conf
            }
        return None



