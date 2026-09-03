from typing import Dict, Any, List, Optional
from app.parsers.models import ValidationResult
from app.validators.field_validators import (
    validate_name, validate_date, validate_mobile, 
    normalize_gender, validate_pincode, validate_address
)
from app.extractors.verhoeff import validate_verhoeff
import re

class DocumentValidator:
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        raise NotImplementedError

class AadhaarValidator(DocumentValidator):
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        results = {}
        if "aadhaar_number" in fields:
            val = fields["aadhaar_number"].value
            if val:
                val_clean = re.sub(r'[^0-9]', '', val)
                if len(val_clean) == 12 and validate_verhoeff(val_clean):
                    results["aadhaar_number"] = ValidationResult(status="VALID", rule="verhoeff")
                else:
                    results["aadhaar_number"] = ValidationResult(status="INVALID", rule="verhoeff", reason="Checksum or length failed")
            else:
                results["aadhaar_number"] = ValidationResult(status="INVALID", rule="presence", reason="Missing value")
                
        if "name" in fields:
            val = fields["name"].value
            if val and validate_name(val):
                results["name"] = ValidationResult(status="VALID", rule="format")
            else:
                results["name"] = ValidationResult(status="INVALID", rule="format", reason="Invalid name format")
                
        if "dob" in fields:
            val = fields["dob"].value
            if val and validate_date(val):
                results["dob"] = ValidationResult(status="VALID", rule="format")
            else:
                results["dob"] = ValidationResult(status="INVALID", rule="format", reason="Invalid date format")

        return results

class PANValidator(DocumentValidator):
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        results = {}
        if "pan_number" in fields:
            val = fields["pan_number"].value
            if val and re.match(r'^[A-Z]{5}\d{4}[A-Z]$', val.upper()):
                results["pan_number"] = ValidationResult(status="VALID", rule="format")
            else:
                results["pan_number"] = ValidationResult(status="INVALID", rule="format", reason="Invalid PAN format")
                
        if "name" in fields:
            val = fields["name"].value
            if val and validate_name(val):
                results["name"] = ValidationResult(status="VALID", rule="format")
            else:
                results["name"] = ValidationResult(status="INVALID", rule="format", reason="Invalid name format")
                
        if "dob" in fields:
            val = fields["dob"].value
            if val and validate_date(val):
                results["dob"] = ValidationResult(status="VALID", rule="format")
            else:
                results["dob"] = ValidationResult(status="INVALID", rule="format", reason="Invalid date format")
                
        return results

class VoterIDValidator(DocumentValidator):
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        results = {}
        if "voter_id" in fields:
            val = fields["voter_id"].value
            # Match 3 letters + 7 digits (standard format)
            if val and re.match(r'^[A-Z]{3}[0-9]{7}$', val.upper()):
                results["voter_id"] = ValidationResult(status="VALID", rule="format")
            else:
                results["voter_id"] = ValidationResult(status="INVALID", rule="format", reason="Invalid Voter ID format")
                
        if "name" in fields:
            val = fields["name"].value
            if val and validate_name(val):
                results["name"] = ValidationResult(status="VALID", rule="format")
            else:
                results["name"] = ValidationResult(status="INVALID", rule="format", reason="Invalid name format")
                
        if "dob" in fields:
            val = fields["dob"].value
            if val and validate_date(val):
                results["dob"] = ValidationResult(status="VALID", rule="format")
            elif val:
                results["dob"] = ValidationResult(status="INVALID", rule="format", reason="Invalid date format")
                
        return results

class PassportValidator(DocumentValidator):
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        results = {}
        if "passport_number" in fields:
            val = fields["passport_number"].value
            if val and re.match(r'^[A-PR-WYZ][1-9]\d\s?\d{4}[1-9]$', val.replace(" ", "").upper()):
                results["passport_number"] = ValidationResult(status="VALID", rule="format")
            else:
                results["passport_number"] = ValidationResult(status="INVALID", rule="format", reason="Invalid Passport format")
                
        if "name" in fields:
            val = fields["name"].value
            if val and validate_name(val):
                results["name"] = ValidationResult(status="VALID", rule="format")
            else:
                results["name"] = ValidationResult(status="INVALID", rule="format", reason="Invalid name format")
                
        if "dob" in fields:
            val = fields["dob"].value
            if val and validate_date(val):
                results["dob"] = ValidationResult(status="VALID", rule="format")
            elif val:
                results["dob"] = ValidationResult(status="INVALID", rule="format", reason="Invalid date format")
                
        return results

class GenericValidator(DocumentValidator):
    def validate(self, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        results = {}
        for k, f in fields.items():
            if k == "name" and f.value:
                results[k] = ValidationResult(status="VALID" if validate_name(f.value) else "INVALID")
            elif "date" in k or k == "dob":
                if f.value:
                    results[k] = ValidationResult(status="VALID" if validate_date(f.value) else "INVALID")
        return results

class ValidationEngine:
    VALIDATORS = {
        "aadhaar_card": AadhaarValidator(),
        "aadhaar_card_back": AadhaarValidator(),
        "pan_card": PANValidator(),
        "voter_id": VoterIDValidator(),
        "passport": PassportValidator()
    }

    @classmethod
    def validate_document(cls, document_id: str, fields: Dict[str, Any]) -> Dict[str, ValidationResult]:
        validator = cls.VALIDATORS.get(document_id, GenericValidator())
        return validator.validate(fields)
