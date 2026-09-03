import pytest
from typing import Dict, Any
from app.parsers.models import FieldResult, ValidationResult, ConsistencyResult, FieldConfidence
from app.parsers.candidate import FieldCandidate
from app.parsers.validation import ValidationEngine
from app.parsers.consistency import ConsistencyEngine
from app.parsers.decision import ConfidenceEngine

def test_aadhaar_validator_valid():
    fields = {
        "aadhaar_number": FieldResult(value="100000000004"), 
        "name": FieldResult(value="John Doe"),
        "dob": FieldResult(value="01/01/1990")
    }
    res = ValidationEngine.validate_document("aadhaar_card", fields)
    assert res["aadhaar_number"].status == "VALID"
    assert res["name"].status == "VALID"
    assert res["dob"].status == "VALID"

def test_aadhaar_validator_invalid_verhoeff():
    fields = {
        "aadhaar_number": FieldResult(value="123456789012"),
    }
    res = ValidationEngine.validate_document("aadhaar_card", fields)
    assert res["aadhaar_number"].status == "INVALID"
    assert res["aadhaar_number"].rule == "verhoeff"

def test_pan_validator_valid():
    fields = {
        "pan_number": FieldResult(value="ABCDE1234F")
    }
    res = ValidationEngine.validate_document("pan_card", fields)
    assert res["pan_number"].status == "VALID"
    
def test_pan_validator_invalid():
    fields = {
        "pan_number": FieldResult(value="ABC1234F")
    }
    res = ValidationEngine.validate_document("pan_card", fields)
    assert res["pan_number"].status == "INVALID"

def test_consistency_date_conflicts():
    fields = {
        "dob": FieldResult(value="01/01/2000"),
        "date_of_issue": FieldResult(value="01/01/1990"), # Issued before birth
        "date_of_expiry": FieldResult(value="01/01/1980") # Expiry before issue
    }
    res = ConsistencyEngine.check_consistency("passport", fields)
    assert res.status == "INCONSISTENT"
    assert len(res.conflicts) == 3

def test_consistency_candidate_conflict():
    fc1 = FieldCandidate(value="01/01/1990", raw_value="01/01/1990", confidence=0.9, source="pattern", score=0.9)
    fc2 = FieldCandidate(value="02/02/1992", raw_value="02/02/1992", confidence=0.8, source="pattern", score=0.8)
    
    fields = {
        "dob": FieldResult(value="01/01/1990", candidates=[fc1, fc2])
    }
    res = ConsistencyEngine.check_consistency("pan_card", fields)
    assert res.status == "INCONSISTENT"
    assert "Candidate conflict" in res.conflicts[0]

def test_decision_engine_accept():
    fields = {
        "name": FieldResult(value="John Doe", status="ok", field_confidence=FieldConfidence(extraction_confidence=0.9), validation=ValidationResult(status="VALID")),
        "dob": FieldResult(value="01/01/1990", status="ok", field_confidence=FieldConfidence(extraction_confidence=0.9), validation=ValidationResult(status="VALID"))
    }
    consistency = ConsistencyResult(status="CONSISTENT")
    doc_conf = ConfidenceEngine.calculate_document_confidence(fields, ["name", "dob"], consistency)
    
    assert doc_conf.decision == "ACCEPT"
    assert doc_conf.overall_confidence == 0.9

def test_decision_engine_review_inconsistent():
    fields = {
        "name": FieldResult(value="John Doe", status="ok", field_confidence=FieldConfidence(extraction_confidence=1.0), validation=ValidationResult(status="VALID")),
        "dob": FieldResult(value="01/01/1990", status="ok", field_confidence=FieldConfidence(extraction_confidence=1.0), validation=ValidationResult(status="VALID"))
    }
    consistency = ConsistencyResult(status="INCONSISTENT", conflicts=["Conflict"])
    doc_conf = ConfidenceEngine.calculate_document_confidence(fields, ["name", "dob"], consistency)
    
    assert doc_conf.decision == "REVIEW"

def test_decision_engine_recapture_missing():
    fields = {
        "name": FieldResult(value="John Doe", status="ok", field_confidence=FieldConfidence(extraction_confidence=0.9), validation=ValidationResult(status="VALID")),
    }
    consistency = ConsistencyResult(status="CONSISTENT")
    doc_conf = ConfidenceEngine.calculate_document_confidence(fields, ["name", "dob"], consistency)
    
    assert doc_conf.decision == "RECAPTURE"

def test_decision_engine_invalid():
    fields = {
        "name": FieldResult(value="John Doe", status="ok", field_confidence=FieldConfidence(extraction_confidence=0.9), validation=ValidationResult(status="INVALID")),
        "dob": FieldResult(value="01/01/1990", status="ok", field_confidence=FieldConfidence(extraction_confidence=0.9), validation=ValidationResult(status="VALID"))
    }
    consistency = ConsistencyResult(status="CONSISTENT")
    doc_conf = ConfidenceEngine.calculate_document_confidence(fields, ["name", "dob"], consistency)
    
    assert doc_conf.decision == "INVALID"
