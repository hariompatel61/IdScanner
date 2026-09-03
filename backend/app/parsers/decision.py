from typing import Dict, Any, List
from app.parsers.models import DocumentConfidence, FieldResult, ConsistencyResult, ValidationResult
from app.core.config import settings

class ConfidenceEngine:
    @classmethod
    def calculate_document_confidence(
        cls, 
        fields: Dict[str, FieldResult], 
        mandatory_fields: List[str],
        consistency: ConsistencyResult
    ) -> DocumentConfidence:
        reasons = []
        
        # Base confidence is average of mandatory fields
        total_conf = 0.0
        mandatory_count = len(mandatory_fields)
        missing_mandatory = False
        
        for m_field in mandatory_fields:
            res = fields.get(m_field)
            if res and res.status != "not_found" and res.value:
                # Add extraction confidence
                total_conf += res.field_confidence.extraction_confidence
                if res.validation.status == "INVALID":
                    total_conf -= 0.5
                    reasons.append(f"{m_field} is invalid format")
            else:
                missing_mandatory = True
                reasons.append(f"Missing mandatory field: {m_field}")
                
        avg_conf = (total_conf / mandatory_count) if mandatory_count > 0 else 0.0
        
        if missing_mandatory:
            avg_conf = min(avg_conf, 0.4) # Cap confidence if missing mandatory
            
        if consistency.status == "INCONSISTENT":
            avg_conf -= 0.2
            reasons.extend(consistency.conflicts)
            
        avg_conf = max(0.0, min(1.0, avg_conf))
        
        # Decision Logic
        if missing_mandatory:
            decision = "RECAPTURE"
        elif any(f.validation.status == "INVALID" for f in fields.values() if f.status != "not_found"):
            decision = "INVALID"
        elif avg_conf < settings.retry_threshold:
            decision = "RECAPTURE"
        elif consistency.status == "INCONSISTENT" or avg_conf < settings.high_confidence_threshold:
            decision = "REVIEW"
        else:
            decision = "ACCEPT"
            
        return DocumentConfidence(
            overall_confidence=round(avg_conf, 4),
            decision=decision,
            reasons=reasons
        )
