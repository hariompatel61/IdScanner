import re
from typing import Optional, Dict, Any, List
from app.extractors.verhoeff import validate_verhoeff

# ── Pre-compiled Module Patterns ──────────────────────────────────────────
_FARMER_CONTEXT_RE = re.compile(r'(agri\s*record|farmer\s*id|farmerid|kisan\s*id|kisan\s*card|agrirecord)', re.I)
_AADHAAR_FRONT_MARKERS_RE = re.compile(r'(dob|date\s*of\s*birth|जन्म\s*तिथि|male|female|पुरुष|महिला)', re.I)
_AADHAAR_BACK_SUMMARY_RE = re.compile(r'(address\s*:|पता\s*:|p\.o\.\s*box|help@uidai|www\.uidai|s/o|d/o|w/o|c/o)', re.I)
_AADHAAR_BACK_MARKERS_RE = re.compile(
    r'(?:address|पता|पत्ता|निवासाचा|unique|unlque|ldontif|ldentif|identif|authorit|uidai|p[\.\s]*o[\.\s]*box|help[@ou0]|www[\.\-_]|1947|1800[\s\-]?[0-9]{3}|s/o|s/0|d/o|d/0|w/o|w/0|c/o|c/0|आत्मज|सुपुत्र|पुत्र|पत्नी|पती)',
    re.I
)
_ABHA_CONTEXT_RE = re.compile(
    r'(ayushman\s*bharat|national\s*health\s*authority|abha|health\s*id|health\s*account|abdm|ndhm|आयुष्मान\s*भारत)',
    re.I
)
_ABHA_AADHAAR_BACK_RE = re.compile(
    r'(address\s*:|पता\s*:|unique\s*identification\s*authority|p\.o\.?\s*box|help@uidai|www\.uidai|s/o|d/o|w/o|c/o|\b1947\b)',
    re.I
)
_REJECTED_EMAIL_DOMAINS_RE = re.compile(
    r'@(uidai|gov\.in|nic\.in|gmail\.com|yahoo\.com|yahoo\.co\.in|outlook\.com|hotmail\.com'
    r'|incometax\.gov|election\.gov|epfo\.gov|esi\.gov|mca\.gov|mospi\.gov|mohfw\.gov'
    r'|mahaonline\.gov|pmjay\.gov|nhm\.gov|nhp\.gov)',
    re.I
)
_REJECTED_EMAIL_PREFIXES_RE = re.compile(
    r'^(help|support|info|contact|helpdesk|care|service|noreply|no-reply|admin|webmaster|postmaster)@',
    re.I
)
_ABHA_EMAIL_HANDLE_RE = re.compile(r'\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\b')
_EMAIL_STRIP_RE = re.compile(r'\S+@\S+')
_FARMER_LINE_MARKERS_RE = re.compile(r'(agri|farmer|kisan|record|कृषि|किसान)', re.I)
_PASSPORT_DOC_MARKERS_RE = re.compile(
    r'(passport|republic\s*of\s*india|भारत\s*गणराज्य|पासपोर्ट|given\s*name|surname|nationality|type\s*p|p<ind|p<)',
    re.I
)
_DIGITS_ONLY_RE = re.compile(r'[^\d]')
_OO_SWAP_RE = re.compile(r'[Oo]')
_PASSPORT_CLEAN_RE = re.compile(r'^[A-Z][0-9]{7}$')
_DOMAIN_CHAR_RE = re.compile(r'^[a-z0-9._\-]+$')


class BaseExtractor:
    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class AadhaarExtractor(BaseExtractor):
    def __init__(self):
        self.pattern = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if all_text is None:
            all_text = " ".join([l.get('text', '') for l in ocr_results])

        if _FARMER_CONTEXT_RE.search(all_text):
            return None

        is_back = bool(_AADHAAR_BACK_SUMMARY_RE.search(all_text))
        has_front_markers = bool(_AADHAAR_FRONT_MARKERS_RE.search(all_text))
        if is_back and not has_front_markers:
            return None

        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            for match in self.pattern.finditer(text):
                raw_str = match.group(0)
                clean_str = _DIGITS_ONLY_RE.sub('', _OO_SWAP_RE.sub('0', raw_str))
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

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if all_text is None:
            all_text = " ".join([l.get('text', '') for l in ocr_results])

        if _FARMER_CONTEXT_RE.search(all_text):
            return None

        is_back = bool(_AADHAAR_BACK_MARKERS_RE.search(all_text))
        
        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            for match in self.pattern.finditer(text):
                raw_str = match.group(0)
                clean_str = _DIGITS_ONLY_RE.sub('', _OO_SWAP_RE.sub('0', raw_str))
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
                digits = _DIGITS_ONLY_RE.sub('', text)
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
        self.pattern = re.compile(r'\b([A-Z]{5})(\d{4})([A-Z])\b', re.IGNORECASE)

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            match = self.pattern.search(text)
            if match:
                candidate = match.group(0).upper()
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
        self.patterns = [
            re.compile(r'\b[A-Z]{3}[0-9]{7}\b', re.IGNORECASE),
            re.compile(r'\b[A-Z]{2}\/[0-9]{2}\/[0-9]{3}\/[0-9]{6}\b', re.IGNORECASE)
        ]

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
    """
    _ABHA_DOMAINS = {
        "abdm", "sbx", "hpr.abdm", "eua", "ndhm", "facility", "dev.abdm", "facility.sbx",
    }

    def _is_valid_abha_address(self, addr: str, has_abha_context: bool) -> bool:
        if not addr or "@" not in addr:
            return False

        addr_lower = addr.lower().strip()

        if _REJECTED_EMAIL_DOMAINS_RE.search(addr_lower):
            return False

        if _REJECTED_EMAIL_PREFIXES_RE.match(addr_lower):
            return False

        _, _, domain = addr_lower.partition("@")
        domain = domain.strip(".")

        if domain in self._ABHA_DOMAINS:
            return True

        if has_abha_context and _DOMAIN_CHAR_RE.match(domain):
            return True

        return False

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if all_text is None:
            all_text = " ".join([l.get("text", "") for l in ocr_results])
            
        all_text_no_emails = _EMAIL_STRIP_RE.sub(' ', all_text)

        has_aadhaar_back = bool(_ABHA_AADHAAR_BACK_RE.search(all_text))
        has_abha_context = bool(_ABHA_CONTEXT_RE.search(all_text_no_emails))

        if has_aadhaar_back and not has_abha_context:
            return None

        if _FARMER_CONTEXT_RE.search(all_text):
            return None

        best_number = None
        highest_number_conf = 0.0
        best_address = None
        highest_address_conf = 0.0

        for line in ocr_results:
            text = line.get("text", "")
            conf = line.get("confidence", 0.0)

            num_match = self.number_pattern.search(text)
            if num_match:
                raw_num = _DIGITS_ONLY_RE.sub("", num_match.group(0))
                if len(raw_num) == 14:
                    norm_num = f"{raw_num[0:2]}-{raw_num[2:6]}-{raw_num[6:10]}-{raw_num[10:14]}"
                    if conf > highest_number_conf:
                        highest_number_conf = conf
                        best_number = norm_num

            addr_match = _ABHA_EMAIL_HANDLE_RE.search(text)
            if addr_match:
                addr_candidate = addr_match.group(0)
                if self._is_valid_abha_address(addr_candidate, has_abha_context):
                    if conf > highest_address_conf:
                        highest_address_conf = conf
                        best_address = addr_candidate.lower()

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

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        best_candidate = None
        highest_conf = 0.0
        has_farmer_context = False

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)

            if _FARMER_LINE_MARKERS_RE.search(text):
                has_farmer_context = True

            match = self.explicit_pattern.search(text)
            if match:
                raw_digits = _DIGITS_ONLY_RE.sub('', match.group(1))
                if len(raw_digits) == 11:
                    formatted = f"{raw_digits[0:3]} {raw_digits[3:5]} {raw_digits[5:7]} {raw_digits[7:9]} {raw_digits[9:11]}"
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = formatted

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
        self.passport_pattern = re.compile(r'\b([A-PR-WYZ][0-9]{7})\b', re.IGNORECASE)
        self.mrz_line2_pattern = re.compile(r'\b([A-PR-WYZ0-9]{8,9})[<0-9][A-Z]{3}', re.IGNORECASE)
        self.explicit_pattern = re.compile(
            r'(?:Passport\s*(?:No|Number|#)?|पासपोर्ट\s*(?:नं|संख्या)?)[\s:\-]*([A-Z][0-9]{7,8})\b',
            re.IGNORECASE
        )

    def extract(self, ocr_results: List[Dict[str, Any]], all_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if all_text is None:
            all_text = " ".join([l.get('text', '') for l in ocr_results])
            
        has_passport_context = bool(_PASSPORT_DOC_MARKERS_RE.search(all_text))

        best_candidate = None
        highest_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)

            m_exp = self.explicit_pattern.search(text)
            if m_exp:
                cand = m_exp.group(1).upper()
                if conf > highest_conf:
                    highest_conf = conf
                    best_candidate = cand

            m_mrz = self.mrz_line2_pattern.search(text)
            if m_mrz:
                cand = m_mrz.group(1).replace('<', '').upper()
                if len(cand) == 8 and _PASSPORT_CLEAN_RE.match(cand):
                    if conf > highest_conf:
                        highest_conf = conf
                        best_candidate = cand

            for match in self.passport_pattern.finditer(text):
                cand = match.group(1).upper()
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




