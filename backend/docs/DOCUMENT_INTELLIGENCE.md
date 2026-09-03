# Document Intelligence Architecture

This document describes the Document Intelligence architecture introduced in Phase 4. 
The system transforms raw OCR spatial data into structured, validated fields through a plugin-based architecture, ensuring deterministic, testable, and highly accurate extractions.

## 1. Core Architecture

The system consists of the following core components:

*   **DocumentRegistry**: A central registry where all supported documents are registered. It maps document types (and aliases) to their respective plugin instances.
*   **DocumentPlugin**: The base class for all document parsers. It provides shared capabilities like candidate generation (_extract_date_candidates, _extract_name_candidates) and layout geometry resolution.
*   **DocumentSchema**: Defines the expected and mandatory fields for a specific document type.
*   **FieldCandidate**: Represents a possible value for a field, including its raw text, bounding box, validation status, and source derivation (e.g., label_match_anchor, pattern_match).
*   **CandidateResolver**: A deterministic scoring engine that evaluates a list of FieldCandidate objects and selects the best one based on confidence, spatial relationships, and validation status.

## 2. The Extraction Flow

1.  **Classification**: scan.py uses the legacy regex extractors (which are now attached to their respective plugins) to identify the document type and extract its primary identifier.
2.  **Plugin Resolution**: scan.py queries the DocumentRegistry to get the appropriate DocumentPlugin for the classified document.
3.  **Candidate Generation**: The plugin processes the reconstructed OCRLine objects. For each field, it generates multiple FieldCandidate objects by looking for explicit labels, inline matches, and fallback regex patterns.
4.  **Candidate Scoring**: The plugin passes the candidates to the CandidateResolver.
5.  **Resolution**: The CandidateResolver scores the candidates (prioritizing clear label matches over raw pattern matches) and returns the highest-scoring valid candidate as a FieldResult.
6.  **Validation**: If any mandatory fields defined in the DocumentSchema are missing or low-confidence, the plugin returns an overall status of escan_required.

## 3. Creating a New Plugin

To add a new document type to the system, create a new plugin class that inherits from DocumentPlugin:

\\\python
from app.parsers.base import DocumentPlugin, DocumentSchema, FieldResult, ParsedDocument
from app.parsers.registry import document_registry
from app.extractors.regex import _custom_ext 

class CustomIDPlugin(DocumentPlugin):
    document_id = "custom_id"
    display_name = "Custom ID Card"
    aliases = ["custom", "custom_id_card"]
    supported_sides = ["front", "back"]
    
    # Attach the regex extractor used for classification
    extractor = _custom_ext 
    
    schema = DocumentSchema(
        expected_fields=["name", "dob", "custom_number"],
        mandatory_fields=["name", "custom_number"]
    )
    
    # Required for backwards compatibility with the legacy BaseDocParser interface
    MANDATORY_FIELDS = ["name", "custom_number"]
    OPTIONAL_FIELDS = ["dob"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}
        
        # 1. Use shared candidate generation for common fields
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")
        fields["name"] = self._extract_name_near_anchor(ocr_lines, "name")
        
        # 2. Add custom logic for specific fields
        fields["custom_number"] = self._extract_custom_number(ocr_lines)
        
        # 3. Build the final result (this handles validation against the schema)
        return self._build_result(fields)

# Register the plugin
document_registry.register(CustomIDPlugin())
\\\

## 4. Candidate Resolution Process

The CandidateResolver uses a deterministic scoring system to pick the best candidate:

1.  **Base Score**: Starts with the raw OCR confidence (0.0 to 1.0).
2.  **Validation Modifier**: 
    *   Adds +0.5 if the candidate passes strict validation (e.g., checksum, date format).
    *   Subtracts -1.0 if the candidate explicitly fails validation.
3.  **Source Modifier**:
    *   +2.0: label_match_inline (Label and value on the same line, e.g., "DOB: 01/01/2000")
    *   +1.5: label_match_same_line (Value is physically adjacent to label horizontally)
    *   +1.5: label_match_anchor (Value is physically below the label)
    *   +1.0: label_match_below (Fallback layout anchor)
    *   +0.5: document_rule (Specific deterministic rule, e.g., MRZ data)
    *   +0.0: pattern_match (Raw regex match anywhere on the document)

This guarantees that explicit layout relationships always outscore random regex matches elsewhere on the card, preventing false positives (e.g., extracting an emergency contact number as a phone number).
