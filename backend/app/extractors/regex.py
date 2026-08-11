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
                "document_type": "AADHAAR",
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
                "document_type": "PAN",
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
    def __init__(self):
        self.number_pattern = re.compile(r'\b\d{2}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b')
        self.address_pattern = re.compile(r'\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+\b')

    def extract(self, ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_number = None
        highest_number_conf = 0.0
        
        best_address = None
        highest_address_conf = 0.0

        for line in ocr_results:
            text = line.get('text', '')
            conf = line.get('confidence', 0.0)
            
            # Look for ABHA Number
            num_match = self.number_pattern.search(text)
            if num_match:
                # Normalize ABHA number to strict XX-XXXX-XXXX-XXXX
                raw_num = re.sub(r'[^\d]', '', num_match.group(0))
                if len(raw_num) == 14:
                    norm_num = f"{raw_num[0:2]}-{raw_num[2:6]}-{raw_num[6:10]}-{raw_num[10:14]}"
                    if conf > highest_number_conf:
                        highest_number_conf = conf
                        best_number = norm_num

            # Look for ABHA Address
            addr_match = self.address_pattern.search(text)
            if addr_match:
                addr = addr_match.group(0).lower()
                if conf > highest_address_conf:
                    highest_address_conf = conf
                    best_address = addr

        # Return whichever is found, prioritizing ABHA Number
        if best_number or best_address:
            return {
                "document_type": "ABHA",
                "identifier": best_number if best_number else best_address,
                "abha_number": best_number,
                "abha_address": best_address,
                "confidence": min(c for c in [highest_number_conf, highest_address_conf] if c > 0)
            }
        return None
