# Centralized Validation, Confidence, and Consistency Engine (Phase 5)

## Overview

Phase 5 introduces a robust, transparent, and multi-layered validation and decision engine that sits on top of the Document Intelligence architecture (Phase 4). 

The primary goal is to **clearly separate OCR confidence from semantic field validation** and provide deterministic decision states (ACCEPT, REVIEW, RECAPTURE, INVALID) based on configurable thresholds.

> [!WARNING]  
> **Extraction Confidence != Authenticity**
> 
> High extraction confidence, format validity, and checksum validity DO NOT imply that the document is authentic or verified by a government source. It simply means the system is highly confident that it correctly extracted validly-formatted data from the image provided.

## Architecture

The extraction flow now follows this sequence:

1. **OCR** -> 2. **Document Classification** -> 3. **Document Plugin** (generates Field Candidates) -> 4. **Candidate Resolver** (picks best candidates based on layout/source) -> 5. **Validation Engine** -> 6. **Consistency Engine** -> 7. **Confidence Engine** -> 8. **Decision Engine** -> **Final Document Result**.

### 1. Validation Engine (ValidationEngine)
Provides centralized, document-specific format and checksum validation.
- **Aadhaar**: Verhoeff checksum validation and date/name format validation.
- **PAN**: Regex syntax validation (^[A-Z]{5}\d{4}[A-Z]$).
- **Voter ID / Passport / etc.**: Document-specific syntax validation.

Validation states: VALID, INVALID, UNKNOWN.

### 2. Consistency Engine (ConsistencyEngine)
Checks for cross-field consistency and candidate conflicts:
- **Date Consistency**: E.g., date_of_expiry must be after date_of_issue, and dob must be logically valid.
- **Candidate Conflicts**: Detects when multiple strong candidates disagree on a value (e.g., OCR found "01/01/1990" and "02/02/1992" with high confidence).
- **Front/Back & Passport MRZ**: Flags conflicts if visual data contradicts MRZ data or front side contradicts back side.

### 3. Confidence Engine (ConfidenceEngine)
Calculates deterministic confidence without inventing "magic" percentages.
- **Base Score**: Average extraction_confidence of mandatory fields.
- **Validation Penalty**: -0.5 per invalid mandatory field.
- **Consistency Penalty**: -0.2 if ConsistencyEngine detects conflicts.

### 4. Decision Engine
Maps the resulting document confidence and validation states to a final actionable decision:
- **RECAPTURE**: Triggered if a mandatory field is missing OR if the overall confidence drops below settings.retry_threshold.
- **INVALID**: Triggered if any successfully extracted field strictly fails formatting or checksum validation (e.g., a PAN card with an impossible letter/number sequence).
- **REVIEW**: Triggered if cross-field consistency checks fail (e.g., conflicting candidates) OR if the overall confidence is between etry_threshold and high_confidence_threshold.
- **ACCEPT**: Triggered if all mandatory fields are present, valid, and the overall confidence is above settings.high_confidence_threshold.

## Sensitive Data Logging
To comply with security requirements, the ScanLogger uses partial redaction for sensitive identifiers (Aadhaar, PAN, Passport). Only the last 4 digits are logged (e.g., XXXXXXXX1234).
