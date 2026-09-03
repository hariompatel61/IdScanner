"""
Cross-field validation functions with recursive surname, middle name & delimiter detector.

Handles international patient names and standard Indian names accurately.
Cleans OCR noise, punctuation dots, slashes, camelCase and attached surname boundaries.
"""

import re
from datetime import datetime
from typing import Optional, List
from app.extractors.labels import GENDER_MAP

# Generic administrative / document header keywords to exclude from name fields
HEADER_WORDS = {
    "government", "india", "income", "tax", "department", "permanent", "account", "number", "card",
    "election", "commission", "elector", "photo", "identity", "ayushman", "bharat", "health", "authority",
    "national", "instructions", "toll-free", "digital", "records", "download", "issue", "signature",
    "dateof", "date", "birth", "gender", "male", "female", "transgender", "republic", "unique", "identification",
    "uidai", "abha", "www", "com", "gov", "in", "helpdesk", "name", "नाम", "father", "father's", "husband",
    "husband's", "other", "relation", "cop", "sample", "specimen", "dob", "sex", "age", "address",
    "fathers", "husbands", "elector's", "electors", "furt", "signature", "हस्ताक्षर",
    "mother", "mother's", "mothers", "आईचे", "नाव", "मतदाराचे", "वडिलांचे", "पतीचे", "माता",
    "निवडणूक", "आयोग", "ओळख", "पत्र", "वय",
    # UIDAI / Government Authority header words (and common OCR distortions)
    "unique", "identification", "authority", "ldontificalion", "ldentificalion", "authorityoftndia",
    "authorityofindia", "wityofindia", "wity", "thorityofindia", "ofindia", "oflndia", "oftndia",
    "tndia", "lndia", "bengaluru", "bangalore",
    # Ayushman / ABHA header words
    "ayushman", "abdm", "ndhm",
    # Aadhaar helpline / support
    "1947", "helpline",
    # Label leftovers
    "sname", "fname", "mname", "hname", "rname",
}

# Address-related words that must NOT appear in person name fields
ADDRESS_STOPWORDS_IN_NAMES = {
    "village", "post", "po", "dist", "district", "tehsil", "taluka", "ward", "block",
    "street", "road", "marg", "nagar", "colony", "enclave", "society", "apartment",
    "floor", "flat", "house", "plot", "khasra", "sector", "lane", "gali", "mohalla",
    "puram", "near", "behind", "opposite", "opp", "bulandshahr", "fatehabad", "basti",
    "davkora", "jamalpur", "shekhan", "lucknow", "bengaluru", "bangalore",
}

# Relation prefixes that must NOT be part of a person name
RELATION_PREFIX_PATTERN = re.compile(
    r'^(?:S/O|S/0|D/O|D/0|W/O|W/0|C/O|C/0|F/O|M/O|Son\s*of|Daughter\s*of|Wife\s*of|Care\s*of|आत्मज|सुपुत्र|पुत्र|पत्नी|माता|पिता)[\s:\-\.]*',
    re.I
)

# Leading label tokens to strip from beginning of extracted person names
LEADING_LABEL_TOKENS = {
    "sname", "name", "fname", "mname", "hname", "rname",
    "s", "father", "fathers", "mother", "mothers", "husband", "husbands",
    "elector", "electors", "relation", "relative", "so", "do", "wo", "co", "mo", "fo"
}

# Primary Surnames & Standard Suffixes for unspaced word separation
PRIMARY_SURNAMES = [
    "CHAUDHARY", "CHOUDHARY", "MUKHERJEE", "CHATTERJEE", "BANERJEE", "MAJUMDAR",
    "DESHMUKH", "KULKARNI", "MOHAPATRA", "RODRIGUEZ", "WILLIAMS", "JOHNSON",
    "SHARMA", "PATEL", "SINGH", "YADAV", "GUPTA", "VERMA", "MISHRA", "PANDEY",
    "TIWARI", "TRIPATHI", "SHUKLA", "DUBEY", "CHAUBEY", "PATHAK", "JAIN", "SHAH",
    "MEHTA", "DOSHI", "DESAI", "JOSHI", "BHATT", "PANDYA", "DAVE", "AGRAWAL",
    "AGARWAL", "BANSAL", "MITTAL", "GOEL", "GARG", "JINDAL", "SINGHAL", "KHAN",
    "ALI", "AHMED", "SHEIKH", "ANSARI", "SIDDIQUI", "QURESHI", "MALIK", "REDDY",
    "RAO", "NAIDU", "GOUD", "CHOWDARY", "RAJU", "SHETTY", "HEGDE", "NAIR",
    "MENON", "PILLAI", "KURUP", "NAMBIAR", "DAS", "ROY", "GHOSH", "DUTTA", "BOSE", "SAHA", "SARKAR", "PATIL", "SHINDE", "PAWAR",
    "GAIKWAD", "CHAVAN", "JADHAV", "MORE", "KALE", "KADAM", "SAWANT", "RAUT",
    "THAKUR", "RATHORE", "CHAUHAN", "RAJPUT", "RAWAT", "NEGI", "BISHT", "MAHATO",
    "PASWAN", "MANJHI", "SAHU", "SAHOO", "PRADHAN", "NAYAK", "BEHERA", "SWAIN",
    "RANA", "DAREKAR", "SMITH", "BROWN", "JONES", "GARCIA", "MILLER", "DAVIS",
    "KUMARI", "DEVI", "BAI", "BEN", "LATA", "RANI", "KAUR", "BANO", "BEGUM",
    "KUMAR", "PRASAD", "CHANDRA", "PRAKASH", "LAL", "DEV", "PAL", "JHA"
]

# Pre-sorted surname tuple for recursive unspaced suffix splitting
_SORTED_PRIMARY_SURNAMES = tuple(sorted(PRIMARY_SURNAMES, key=len, reverse=True))

# Pre-compiled Module Patterns
_ANCHOR_CLEAN_LEADING_RE = re.compile(r'^[^\w\s]+')
_ANCHOR_MATCH_RE = re.compile(
    r'^(?:[a-zA-Z\u0900-\u097F]{1,5}[\/\-:\.]\s*)?(?:elector(?:\'s)?(?:\s*name|\w{0,3})?|mother(?:\'s)?(?:\s*name|\w{0,3})?|father(?:\'s)?(?:\s*name|\w{0,3})?|husband(?:\'s)?(?:\s*name|\w{0,3})?|relation(?:\s*name)?|name|नाम|नाव|मतदाराचे(?:\s*नाव)?|आईचे(?:\s*नाव)?|माता(?:\s*का\s*नाम)?|पिता(?:\s*का\s*नाम)?|पती(?:\s*का\s*नाम)?|पतीचे(?:\s*नाव)?|वडिलांचे(?:\s*नाव)?|signature|हस्ताक्षर|dob|date\s*of\s*birth|sex|gender)$',
    re.I
)
_NON_WORD_SPACES_RE = re.compile(r'[^\w\s]')
_DELIMITER_SPACING_RE = re.compile(r'([:\/\-=\.,_+’\'"‘“])')
_LABEL_PREFIX_RE = re.compile(
    r'^(?:[a-zA-Z\u0900-\u097F]{1,5}[\/\-:\.]\s*)?(?:elector(?:\s*[\'’]?\s*s)?(?:\s*name|\w{0,3})?|mother(?:\s*[\'’]?\s*s)?(?:\s*name|\w{0,3})?|father(?:\s*[\'’]?\s*s)?(?:\s*name|\w{0,3})?|husband(?:\s*[\'’]?\s*s)?(?:\s*name|\w{0,3})?|relation(?:\s*name)?|name|नाम|नाव|मतदाराचे(?:\s*नाव)?|आईचे(?:\s*नाव)?|माता(?:\s*का\s*नाम)?|पिता(?:\s*का\s*नाम)?|पती(?:\s*का\s*नाम)?|पतीचे(?:\s*नाव)?|वडिलांचे(?:\s*नाव)?|other|s/o|w/o|d/o|m/o|c/o|son\s*of|wife\s*of|daughter\s*of|mother\s*of|s\s*name|sname|fname|mname|hname)\s*[:\-\/\.=\s]*',
    re.I
)
_PUNCTUATION_RE = re.compile(r'[:\._\-/+=’\'"‘“]+')
_CAMEL_CASE_RE = re.compile(r'([a-z])([A-Z])')
_NON_LETTER_RE = re.compile(r'[^a-zA-Z\u0900-\u097F\s]')
_WHITESPACE_RE = re.compile(r'\s+')
_DIGIT_RE = re.compile(r'\d')
_DISTORTED_AUTHORITY_RE = re.compile(r'(?:wity|ofindia|oftndia|oflndia|authorityof|identificalion|authorityoftndia|elector|relation|identit|commission|election)', re.I)
_DATE_FULL_RE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')
_YEAR_ONLY_RE = re.compile(r'^(\d{4})$')
_DATE_SEARCH_RE = re.compile(r'\b(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})\b')
_YEAR_SEARCH_RE = re.compile(r'\b(19\d{2}|20[0-2]\d)\b')
_DIGITS_ONLY_RE = re.compile(r'[^\d]')
_GENDER_ANCHOR_RE = re.compile(r'(?:gender|sex|लिंग|gander|gendar)[\s:\.\/=\-]+([A-Za-z]+|[\u0900-\u097F]+)', re.I)
_GENDER_FEMALE_RE = re.compile(r'(?:female|famale|महिला|स्त्री)', re.I)
_GENDER_TRANS_RE = re.compile(r'(?:transgender|किन्नर|तृतीयपंथी)', re.I)
_GENDER_MALE_RE = re.compile(r'(?:male|malo|पुरुष|पुरूष)', re.I)
_GENDER_F_CHAR_RE = re.compile(r'\b[Ff]\b')
_GENDER_M_CHAR_RE = re.compile(r'\b[Mm]\b')
_MOBILE_CLEAN_RE = re.compile(r'[\s\-\+]')
_MOBILE_MATCH_RE = re.compile(r'^[6-9]\d{9}$')
_PINCODE_MATCH_RE = re.compile(r'^[1-9][0-9]{5}$')
_PINCODE_SEARCH_RE = re.compile(r'\b([1-9][0-9]{5})\b')
_WORD_TOKENS_RE = re.compile(r'[a-zA-Z\u0900-\u097F]{3,}')
_ADDRESS_LABEL_RE = re.compile(r'^(?:address|पता|पत्ता|निवासाचा\s*पत्ता)[\s:\-\.]*$', re.I)
_ADDRESS_PIN_ONLY_RE = re.compile(r'^[A-Za-z0-9\s\-_,.]*?\b\d{6}\b$')
_ADDRESS_FOOTER_LEAK_RE = re.compile(
    r'(?:unique|unlque|uniqe|ldontif|ldentif|identif)\w*[\s\-_]*(?:authorit|authorlt|authorty)\w*|'
    r'unique\s*identification|'
    r'authority\s*of\s*india|'
    r'भारतीय\s*विशिष्ट\s*पहचान\s*प्राधिकरण|'
    r'विशिष्ट\s*पहचान|'
    r'help[@ou0\.\-_\s]*uidai|'
    r'www[\.\-_\s]*uidai|'
    r'uidai[\.\-_\s]*gov|'
    r'p[\.\s]*o[\.\s]*box|'
    r'\b1947\b|'
    r'1800[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}|'
    r'bengaluru[\s\-]*560\s*001|'
    r'bangalore[\s\-]*560\s*001|'
    r'gpo\s*bangalore|'
    r'gpo\s*bengaluru|'
    r'\bvid\b|'
    r'signature\s*valid|'
    r'digitally\s*signed',
    re.I
)

_LABEL_KEYWORDS_SET = {
    "name", "father", "fathers", "father's", "husband", "husbands", "husband's",
    "mother", "mothers", "mother's", "signature", "elector", "electors", "elector's",
    "photo", "identity", "card", "department", "government", "india", "आयोग", "निवडणूक",
    "ओळख", "पत्र", "नाव", "आईचे", "वडिलांचे", "पतीचे", "मतदाराचे", "other", "relation"
}

_LABEL_PREFIXES_TUPLE = ("mother", "father", "husband", "elector", "signat", "departm", "relation", "identit")


def is_pure_label_line(text: str) -> bool:
    """
    Returns True if the text is purely an anchor/label line.
    """
    if not text:
        return True

    cleaned = _ANCHOR_CLEAN_LEADING_RE.sub('', text.strip())
    if _ANCHOR_MATCH_RE.search(cleaned):
        return True

    words = [w.lower() for w in _NON_WORD_SPACES_RE.sub(' ', text).split()]
    if all(w in _LABEL_KEYWORDS_SET or w in HEADER_WORDS or any(w.startswith(k) for k in _LABEL_PREFIXES_TUPLE) for w in words):
        return True

    return False


def split_word_suffixes(word: str) -> List[str]:
    """Recursively splits unspaced word suffixes from right to left using pre-sorted surnames."""
    if len(word) <= 3 or not word.isalpha():
        return [word]

    word_upper = word.upper()
    for suffix in _SORTED_PRIMARY_SURNAMES:
        if word_upper.endswith(suffix) and len(word) > len(suffix):
            prefix = word[:-len(suffix)]
            if len(prefix) >= 2:
                return split_word_suffixes(prefix) + [word[-len(suffix):]]

    return [word]


def clean_name_text(text: str) -> str:
    """
    Advanced Name, Middle Name & Surname cleaner.
    """
    if not text or is_pure_label_line(text):
        return ""

    # 1. Delimiter spacing
    formatted = _DELIMITER_SPACING_RE.sub(r' \1 ', text)

    # 2. Strip comprehensive bilingual label prefixes
    cleaned = _LABEL_PREFIX_RE.sub('', formatted).strip()

    if not cleaned or is_pure_label_line(cleaned):
        return ""

    # 3. Replace delimiters with spaces
    cleaned = _PUNCTUATION_RE.sub(' ', cleaned)

    # 4. Split camelCase/PascalCase
    cleaned = _CAMEL_CASE_RE.sub(r'\1 \2', cleaned)

    # 5. Remove non-letter characters
    cleaned = _NON_LETTER_RE.sub(' ', cleaned)

    # 6. Suffix Recursive Splitter on unspaced words
    tokens = cleaned.split()
    refined_tokens: List[str] = []
    for token in tokens:
        refined_tokens.extend(split_word_suffixes(token))

    # 7. Strip leading leftover label tokens
    while refined_tokens and refined_tokens[0].lower() in LEADING_LABEL_TOKENS:
        refined_tokens.pop(0)

    # 8. Normalize whitespace
    return _WHITESPACE_RE.sub(' ', " ".join(refined_tokens)).strip()


def validate_name(value: str) -> bool:
    """
    Comprehensive name validation for ID documents.
    """
    if not value or len(value.strip()) < 2 or is_pure_label_line(value):
        return False

    if '@' in value:
        return False

    if RELATION_PREFIX_PATTERN.match(value.strip()):
        return False

    cleaned = clean_name_text(value)
    if len(cleaned) < 2:
        return False

    words = [w.lower() for w in cleaned.split()]

    if all(w in _LABEL_KEYWORDS_SET or any(w.startswith(k) for k in _LABEL_PREFIXES_TUPLE) for w in words):
        return False

    if len(words) == 1 and (words[0] in HEADER_WORDS or words[0] in _LABEL_KEYWORDS_SET or any(words[0].startswith(k) for k in _LABEL_PREFIXES_TUPLE)):
        return False

    if _DIGIT_RE.search(cleaned):
        return False

    if any(w in _LABEL_KEYWORDS_SET for w in words):
        return False

    if any(w in HEADER_WORDS for w in words):
        return False

    if any(w in ADDRESS_STOPWORDS_IN_NAMES for w in words):
        return False

    if _DISTORTED_AUTHORITY_RE.search(cleaned):
        return False

    return True


def validate_date(value: str) -> bool:
    """
    Validates a date string in common document formats.
    Accepts: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY
    """
    if not value:
        return False

    normalized = value.strip().replace("-", "/").replace(".", "/")

    match = _DATE_FULL_RE.match(normalized)
    if not match:
        year_match = _YEAR_ONLY_RE.match(normalized.strip())
        if year_match:
            year = int(year_match.group(1))
            current_year = datetime.now().year
            return 1900 <= year <= current_year
        return False

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    current_year = datetime.now().year

    if year < 1900 or year > current_year:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False

    if month in (4, 6, 9, 11) and day > 30:
        return False
    if month == 2 and day > 29:
        return False

    return True


def validate_expiry_date(value: str) -> bool:
    """
    Validates an expiry date string (allows future dates up to 35 years).
    """
    if not value:
        return False

    normalized = value.strip().replace("-", "/").replace(".", "/")
    match = _DATE_FULL_RE.match(normalized)
    if not match:
        return False

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    current_year = datetime.now().year

    if year < 1990 or year > current_year + 35:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False

    if month in (4, 6, 9, 11) and day > 30:
        return False
    if month == 2 and day > 29:
        return False

    return True


def normalize_date(value: str) -> Optional[str]:
    """
    Normalizes a date string to DD/MM/YYYY format.
    """
    if not value:
        return None

    normalized = value.strip().replace("-", "/").replace(".", "/")

    match = _DATE_FULL_RE.match(normalized)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
        result = f"{day:02d}/{month:02d}/{year}"
        if validate_date(result):
            return result
        return None

    year_match = _YEAR_ONLY_RE.match(normalized.strip())
    if year_match:
        year = int(year_match.group(1))
        current_year = datetime.now().year
        if 1900 <= year <= current_year:
            return year_match.group(1)
        return None

    return None


def normalize_expiry_date(value: str) -> Optional[str]:
    """
    Normalizes an expiry date string to DD/MM/YYYY format.
    """
    if not value:
        return None

    normalized = value.strip().replace("-", "/").replace(".", "/")
    match = _DATE_FULL_RE.match(normalized)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
        result = f"{day:02d}/{month:02d}/{year}"
        if validate_expiry_date(result):
            return result
        return None
    return None


validate_dob = validate_date
normalize_dob = normalize_date

_UIDAI_HELPLINE_NUMBERS = {"1947", "18003001947", "18001801947", "1800300", "1800180"}


def extract_date_from_text(text: str) -> Optional[str]:
    """
    Searches text string for a valid DD/MM/YYYY or DD-MM-YYYY pattern.
    """
    if not text:
        return None

    match = _DATE_SEARCH_RE.search(text)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= datetime.now().year:
            return f"{d:02d}/{m:02d}/{y:04d}"

    cleaned_digits = _DIGITS_ONLY_RE.sub('', text.strip())
    if cleaned_digits in _UIDAI_HELPLINE_NUMBERS:
        return None

    year_match = _YEAR_SEARCH_RE.search(text)
    if year_match:
        year_str = year_match.group(1)
        if year_str == "1947":
            return None
        year = int(year_str)
        if 1900 <= year <= datetime.now().year:
            return str(year)

    return None


def normalize_gender(value: str) -> Optional[str]:
    """
    Normalizes a gender string to canonical English: Male, Female, or Transgender.
    """
    if not value:
        return None

    cleaned = value.strip().lower()
    if cleaned in GENDER_MAP:
        return GENDER_MAP[cleaned]

    match = _GENDER_ANCHOR_RE.search(value)
    if match:
        val_part = match.group(1).lower().strip()
        if val_part in GENDER_MAP:
            return GENDER_MAP[val_part]

    if _GENDER_FEMALE_RE.search(cleaned):
        return "Female"
    if _GENDER_TRANS_RE.search(cleaned):
        return "Transgender"
    if _GENDER_MALE_RE.search(cleaned):
        return "Male"

    if _GENDER_F_CHAR_RE.search(cleaned):
        return "Female"
    if _GENDER_M_CHAR_RE.search(cleaned):
        return "Male"

    return None


def validate_mobile(value: str) -> bool:
    """
    Validates a mobile number (10 digits starting with 6-9).
    """
    if not value:
        return False

    cleaned = _MOBILE_CLEAN_RE.sub('', value.strip())

    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]

    return bool(_MOBILE_MATCH_RE.match(cleaned))


def normalize_mobile(value: str) -> Optional[str]:
    """
    Normalizes a mobile number to plain 10-digit format.
    """
    if not value:
        return None

    cleaned = _MOBILE_CLEAN_RE.sub('', value.strip())

    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]

    if validate_mobile(cleaned):
        return cleaned
    return None


INDIAN_STATES_UTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

# Pre-compiled State matching patterns
_STATE_PATTERNS = [
    (state, re.compile(r'\b' + re.escape(state).replace(r'\ ', r'\s*') + r'\b', re.I))
    for state in INDIAN_STATES_UTS
]


def validate_pincode(value: str) -> bool:
    """Validates 6-digit Indian PIN code."""
    if not value:
        return False
    cleaned = _DIGITS_ONLY_RE.sub('', value.strip())
    return bool(_PINCODE_MATCH_RE.match(cleaned))


def normalize_pincode(value: str) -> Optional[str]:
    """Normalizes 6-digit PIN code."""
    if not value:
        return None
    cleaned = _DIGITS_ONLY_RE.sub('', value.strip())
    if validate_pincode(cleaned):
        return cleaned
    return None


STATE_ALIASES_MAP = {
    "उत्तर प्रदेश": "Uttar Pradesh",
    "उत्तरप्रदेश": "Uttar Pradesh",
    "हरियाणा": "Haryana",
    "महाराष्ट्र": "Maharashtra",
    "बिहार": "Bihar",
    "राजस्थान": "Rajasthan",
    "मध्य प्रदेश": "Madhya Pradesh",
    "मध्यप्रदेश": "Madhya Pradesh",
    "गुजरात": "Gujarat",
    "पंजाब": "Punjab",
    "पश्चिम बंगाल": "West Bengal",
    "दिल्ली": "Delhi",
    "उत्तराखंड": "Uttarakhand",
    "झारखंड": "Jharkhand",
    "छत्तीसगढ़": "Chhattisgarh",
    "हिमाचल प्रदेश": "Himachal Pradesh",
    "ओडिशा": "Odisha",
    "उड़ीसा": "Odisha",
    "कर्नाटक": "Karnataka",
    "केरल": "Kerala",
    "तमिलनाडु": "Tamil Nadu",
    "तमिल नाडु": "Tamil Nadu",
    "तेलंगाना": "Telangana",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "असम": "Assam",
    "जम्मू और कश्मीर": "Jammu and Kashmir",
    "लद्दाख": "Ladakh",
    "गोवा": "Goa"
}


def extract_state_from_text(text: str) -> Optional[str]:
    """Matches and normalizes Indian State / UT from text string (Bilingual English/Hindi)."""
    if not text:
        return None

    # Check Hindi aliases first
    for alias, canonical in STATE_ALIASES_MAP.items():
        if alias in text:
            return canonical

    # Check English names with pre-compiled patterns
    for state, pattern in _STATE_PATTERNS:
        if pattern.search(text):
            return state

    return None


def extract_pincode_from_text(text: str) -> Optional[str]:
    """Extracts 6-digit Indian PIN code from address text."""
    if not text:
        return None
    matches = _PINCODE_SEARCH_RE.findall(text)
    if matches:
        return matches[-1]
    return None


def validate_address(value: str) -> bool:
    """
    Validates full address string integrity according to the 'no guessing' rule.
    """
    if not value or len(value.strip()) < 15:
        return False

    cleaned = value.strip()

    if _ADDRESS_LABEL_RE.match(cleaned):
        return False

    if _ADDRESS_PIN_ONLY_RE.match(cleaned) and len(_WORD_TOKENS_RE.findall(cleaned)) < 2:
        return False

    if _ADDRESS_FOOTER_LEAK_RE.search(cleaned):
        return False

    words = _WORD_TOKENS_RE.findall(cleaned)
    if len(words) < 2:
        return False

    return True

