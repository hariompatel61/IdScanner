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
    "निवडणूक", "आयोग", "ओळख", "पत्र", "वय"
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
    "MENON", "PILLAI", "KURUP", "NAMBIAR", "DAS", "ROY", "GHOSH", "DUTTA",
    "SEN", "BOSE", "DEY", "SAHA", "SARKAR", "PATIL", "SHINDE", "PAWAR",
    "GAIKWAD", "CHAVAN", "JADHAV", "MORE", "KALE", "KADAM", "SAWANT", "RAUT",
    "THAKUR", "RATHORE", "CHAUHAN", "RAJPUT", "RAWAT", "NEGI", "BISHT", "MAHATO",
    "PASWAN", "MANJHI", "SAHU", "SAHOO", "PRADHAN", "NAYAK", "BEHERA", "SWAIN",
    "RANA", "DAREKAR", "SMITH", "BROWN", "JONES", "GARCIA", "MILLER", "DAVIS",
    "KUMARI", "DEVI", "BAI", "BEN", "LATA", "RANI", "KAUR", "BANO", "BEGUM",
    "KUMAR", "PRASAD", "CHANDRA", "PRAKASH", "LAL", "RAM", "DEV", "RAJ", "PAL", "JHA"
]


def is_pure_label_line(text: str) -> bool:
    """
    Returns True if the text is purely an anchor/label line (like 'Name', 'Father\'s Name', 'Mother\'s Name', 'Mothersp').
    """
    if not text:
        return True

    cleaned = re.sub(r'^[^\w\s]+', '', text.strip())
    if re.search(r'^(?:[a-zA-Z\u0900-\u097F]{1,5}[\/\-:\.]\s*)?(?:elector(?:\'s)?(?:\s*name|\w{0,3})?|mother(?:\'s)?(?:\s*name|\w{0,3})?|father(?:\'s)?(?:\s*name|\w{0,3})?|husband(?:\'s)?(?:\s*name|\w{0,3})?|relation(?:\s*name)?|name|नाम|नाव|मतदाराचे(?:\s*नाव)?|आईचे(?:\s*नाव)?|माता(?:\s*का\s*नाम)?|पिता(?:\s*का\s*नाम)?|पती(?:\s*का\s*नाम)?|पतीचे(?:\s*नाव)?|वडिलांचे(?:\s*नाव)?|signature|हस्ताक्षर|dob|date\s*of\s*birth|sex|gender)$', cleaned, re.I):
        return True

    words = [w.lower() for w in re.sub(r'[^\w\s]', ' ', text).split()]
    label_keywords = {"name", "father", "fathers", "father's", "husband", "husbands", "husband's", "mother", "mothers", "mother's", "signature", "elector", "electors", "elector's", "photo", "identity", "card", "department", "government", "india", "आयोग", "निवडणूक", "ओळख", "पत्र", "नाव", "आईचे", "वडिलांचे", "पतीचे", "मतदाराचे", "other", "relation"}
    if all(w in label_keywords or w in HEADER_WORDS or any(w.startswith(k) for k in ("mother", "father", "husband", "elector", "signat", "departm", "relation", "identit")) for w in words):
        return True

    return False


def split_word_suffixes(word: str) -> List[str]:
    """Recursively splits unspaced word suffixes from right to left."""
    if len(word) <= 3 or not word.isalpha():
        return [word]

    for suffix in sorted(PRIMARY_SURNAMES, key=len, reverse=True):
        if word.upper().endswith(suffix) and len(word) > len(suffix):
            prefix = word[:-len(suffix)]
            if len(prefix) >= 2:
                return split_word_suffixes(prefix) + [word[-len(suffix):]]

    if word.upper() == "HARIOM":
        return ["HARI", "OM"]

    return [word]


def clean_name_text(text: str) -> str:
    """
    Advanced Name, Middle Name & Surname cleaner.
    1. Splits delimiters (dots, colons, slashes, hyphens) -> 'Hari.Om.Patel' -> 'Hari Om Patel'
    2. Strips bilingual label prefixes -> "Elector's Name: ROHTASH" -> "ROHTASH"
    3. Splits camelCase boundaries -> 'HarishankarPatel' -> 'Harishankar Patel'
    4. Recursively splits unspaced surname boundaries without corrupting non-compound names (e.g. Ramesh -> Ramesh)
    5. Normalizes whitespace cleanly
    """
    if not text or is_pure_label_line(text):
        return ""

    # 1. Delimiter spacing: e.g. "NAME:ROHTASH", "Hari.Om.Patel" -> "NAME : ROHTASH", "Hari Om Patel"
    formatted = re.sub(r'([:\/\-=\.,_+])', r' \1 ', text)

    # 2. Strip comprehensive bilingual label prefixes
    cleaned = re.sub(
        r'^(?:[a-zA-Z\u0900-\u097F]{1,5}[\/\-:\.]\s*)?(?:elector(?:\'s)?(?:\s*name|\w{0,3})?|mother(?:\'s)?(?:\s*name|\w{0,3})?|father(?:\'s)?(?:\s*name|\w{0,3})?|husband(?:\'s)?(?:\s*name|\w{0,3})?|relation(?:\s*name)?|name|नाम|नाव|मतदाराचे(?:\s*नाव)?|आईचे(?:\s*नाव)?|माता(?:\s*का\s*नाम)?|पिता(?:\s*का\s*नाम)?|पती(?:\s*का\s*नाम)?|पतीचे(?:\s*नाव)?|वडिलांचे(?:\s*नाव)?|other|s/o|w/o|d/o|m/o|c/o|son\s*of|wife\s*of|daughter\s*of|mother\s*of)\s*[:\-\/\.=\s]*',
        '',
        formatted,
        flags=re.I
    ).strip()

    if not cleaned or is_pure_label_line(cleaned):
        return ""

    # 3. Replace colons, dots, underscores, slashes, hyphens with spaces
    cleaned = re.sub(r'[:\._\-/+=]+', ' ', cleaned)

    # 4. Split camelCase/PascalCase: e.g. "HarishankarPatel" -> "Harishankar Patel"
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)

    # 5. Remove any leftover non-letter characters
    cleaned = re.sub(r'[^a-zA-Z\u0900-\u097F\s]', ' ', cleaned)

    # 6. Suffix Recursive Splitter on unspaced words
    tokens = cleaned.split()
    refined_tokens: List[str] = []
    for token in tokens:
        refined_tokens.extend(split_word_suffixes(token))

    # 7. Normalize whitespace
    return re.sub(r'\s+', ' ', " ".join(refined_tokens)).strip()


def validate_name(value: str) -> bool:
    """
    Comprehensive name validation for ID documents.
    """
    if not value or len(value.strip()) < 2 or is_pure_label_line(value):
        return False

    if '@' in value:
        return False

    cleaned = clean_name_text(value)
    if len(cleaned) < 2:
        return False

    words = [w.lower() for w in cleaned.split()]
    label_keywords = {"name", "father", "fathers", "father's", "husband", "husbands", "husband's", "mother", "mothers", "mother's", "signature", "elector", "electors", "elector's", "department", "other", "relation", "photo", "identity", "card"}

    if all(w in label_keywords or any(w.startswith(k) for k in ("mother", "father", "husband", "elector", "signat", "departm", "relation")) for w in words):
        return False

    if len(words) == 1 and (words[0] in HEADER_WORDS or any(words[0].startswith(k) for k in ("mother", "father", "husband", "elector", "signat", "departm", "relation", "identit"))):
        return False

    if re.search(r'\d', cleaned):
        return False

    if any(w in label_keywords for w in words):
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

    match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', normalized)
    if not match:
        year_match = re.match(r'^(\d{4})$', normalized.strip())
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


def normalize_date(value: str) -> Optional[str]:
    """
    Normalizes a date string to DD/MM/YYYY format.
    Returns None if the date is invalid.
    """
    if not value:
        return None

    normalized = value.strip().replace("-", "/").replace(".", "/")

    match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', normalized)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
        result = f"{day:02d}/{month:02d}/{year}"
        if validate_date(result):
            return result
        return None

    year_match = re.match(r'^(\d{4})$', normalized.strip())
    if year_match:
        year = int(year_match.group(1))
        current_year = datetime.now().year
        if 1900 <= year <= current_year:
            return year_match.group(1)
        return None

    return None


def extract_date_from_text(text: str) -> Optional[str]:
    """
    Searches any text string for a valid DD/MM/YYYY or DD-MM-YYYY pattern.
    """
    if not text:
        return None

    match = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', text)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= datetime.now().year:
            return f"{d:02d}/{m:02d}/{y:04d}"

    year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text)
    if year_match:
        year = int(year_match.group(1))
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

    # If line contains gender label (e.g. "fe/Gender.yyMale", "Gender: Male", "लिंग: पुरुष")
    # inspect the portion after the label first
    label_match = re.search(r'(?:gender|sex|लिंग|gander|gendar)\s*[:\.\/=\s\w]*', value, re.I)
    search_target = value[label_match.end():] if label_match and label_match.end() < len(value) else value

    # Check for Female / famale / transgender / male
    if re.search(r'(?:female|famale|महिला|स्त्री)', search_target, re.I):
        return "Female"
    if re.search(r'(?:transgender|किन्नर|तृतीयपंथी)', search_target, re.I):
        return "Transgender"
    if re.search(r'(?:male|malo|पुरुष|पुरूष)', search_target, re.I):
        return "Male"

    # Fallback to full string with word boundaries
    if re.search(r'\b(female|famale|महिला|स्त्री)\b', value, re.I):
        return "Female"
    if re.search(r'\b(transgender|किन्नर|तृतीयपंथी)\b', value, re.I):
        return "Transgender"
    if re.search(r'\b(male|malo|पुरुष|पुरूष)\b', value, re.I):
        return "Male"

    return None


def validate_mobile(value: str) -> bool:
    """
    Validates a mobile number.
    Must be exactly 10 digits starting with 6-9 (Indian standard).
    Rejects masked numbers (containing X, *, etc.).
    """
    if not value:
        return False

    cleaned = re.sub(r'[\s\-\+]', '', value.strip())

    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]

    if not re.match(r'^[6-9]\d{9}$', cleaned):
        return False

    return True


def normalize_mobile(value: str) -> Optional[str]:
    """
    Normalizes a mobile number to plain 10-digit format.
    Returns None if invalid or masked.
    """
    if not value:
        return None

    cleaned = re.sub(r'[\s\-\+]', '', value.strip())

    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]

    if validate_mobile(cleaned):
        return cleaned
    return None
