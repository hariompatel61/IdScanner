from typing import Dict, Any, List, Optional
from datetime import datetime
from app.parsers.models import ConsistencyResult, FieldResult

class ConsistencyEngine:
    @classmethod
    def check_consistency(cls, document_id: str, fields: Dict[str, FieldResult]) -> ConsistencyResult:
        conflicts = []
        
        # 1. Date consistency
        dob_res = fields.get("dob")
        issue_res = fields.get("date_of_issue")
        expiry_res = fields.get("date_of_expiry")
        
        def parse_date(d_str):
            if not d_str: return None
            try: return datetime.strptime(d_str, "%d/%m/%Y")
            except: return None
            
        dob = parse_date(dob_res.value) if dob_res else None
        issue = parse_date(issue_res.value) if issue_res else None
        expiry = parse_date(expiry_res.value) if expiry_res else None
        
        if dob and issue and dob > issue:
            conflicts.append("DOB is after issue date")
        if issue and expiry and issue > expiry:
            conflicts.append("Issue date is after expiry date")
        if dob and expiry and dob > expiry:
            conflicts.append("DOB is after expiry date")
            
        # 2. Candidate Conflicts
        for field_name, result in fields.items():
            if not hasattr(result, "candidates") or not result.candidates:
                continue
                
            # If the top two candidates are different but both have high extraction confidence
            if len(result.candidates) > 1:
                top = result.candidates[0]
                second = result.candidates[1]
                if top.score > 0.7 and second.score > 0.7 and top.value != second.value:
                    conflicts.append(f"Candidate conflict for {field_name}: '{top.value}' vs '{second.value}'")
                    
        # 3. Passport Visual vs MRZ
        if document_id == "passport":
            mrz_res = fields.get("mrz")
            if mrz_res and mrz_res.value:
                # We would parse MRZ here and compare with visual fields
                pass
                
        status = "INCONSISTENT" if conflicts else "CONSISTENT"
        return ConsistencyResult(status=status, conflicts=conflicts)
