import re
from .constants import COMMON_INDIAN_NAME_SUFFIXES, SPECIFIC_NAME_REPLACEMENTS

def clean_ocr_name(text):
    if not text:
        return text
        
    # Fix missing spaces in camel case, e.g. "OmPatel" -> "Om Patel"
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Fix common ALL CAPS merged words in OCR using constants dictionary
    for suffix in COMMON_INDIAN_NAME_SUFFIXES:
        # Split when the common name is at the end (e.g., PRAKASHCHAUDHARY -> PRAKASH CHAUDHARY)
        pattern1 = r'([A-Za-z])(' + suffix + r')\b'
        text = re.sub(pattern1, r'\1 \2', text, flags=re.IGNORECASE)
        # Split when the common name is at the beginning (e.g., SINGHGARIYA -> SINGH GARIYA)
        pattern2 = r'\b(' + suffix + r')([A-Za-z])'
        text = re.sub(pattern2, r'\1 \2', text, flags=re.IGNORECASE)
        
    for merged, split in SPECIFIC_NAME_REPLACEMENTS.items():
        text = re.sub(rf'\b({merged})\b', split, text, flags=re.IGNORECASE)
        
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_center(box):
    if not box or len(box) != 4: return 0, 0
    return sum(p[0] for p in box)/4, sum(p[1] for p in box)/4

def _find_closest_value(label_idx, ocr_results, exclude_texts=None):
    if exclude_texts is None: exclude_texts = set()
    
    label_box = ocr_results[label_idx].get('box')
    if not label_box:
        return None
    
    lx, ly = _get_center(label_box)
    best_dist = float('inf')
    best_text = None
    
    for i, res in enumerate(ocr_results):
        if i == label_idx:
            continue
        text = res['text'].strip()
        if len(text) < 3 or re.search(r'\d', text):
            continue
        if re.search(r'Name|DOB|Date|Department|Govt|India|Permanent|Signature|Tax|Birth|Year|Issue|Male|Female|Blood|Address', text, re.IGNORECASE):
            continue
        if text in exclude_texts:
            continue
            
        box = res.get('box')
        if not box:
            continue
            
        bx, by = _get_center(box)
        # Use Euclidean distance
        dist = ((lx - bx)**2 + (ly - by)**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_text = text
            
    return best_text

def extract_demographics(ocr_results):
    details = {
        "document_type": None,
        "id_number": None,
        "name": None,
        "father_name": None,
        "dob": None,
        "gender": None,
        "mobile_number": None,
        "abha_number": None,
        "abha_address": None
    }

    if not ocr_results:
        return details

    texts = [res['text'] for res in ocr_results]
    full_text = " ".join(texts)

    # 1. Document Type & ID Number
    # ABHA
    abha_num_match = re.search(r'\b\d{2}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b', full_text)
    if abha_num_match:
        details["document_type"] = "ABHA_NUMBER"
        raw_num = re.sub(r'[^\d]', '', abha_num_match.group(0))
        if len(raw_num) == 14:
            details["abha_number"] = f"{raw_num[0:2]}-{raw_num[2:6]}-{raw_num[6:10]}-{raw_num[10:14]}"
            details["id_number"] = details["abha_number"]
    
    # PAN
    if not details["document_type"]:
        pan_match = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', full_text, re.IGNORECASE)
        if pan_match and re.search(r'INCOME\s*TAX|GOVT\.?\s*OF\s*INDIA|Permanent\s*Account', full_text, re.IGNORECASE):
            details["document_type"] = "PAN_CARD"
            details["id_number"] = pan_match.group(0).upper()
            
    # Aadhaar (12 digits, simple heuristic)
    if not details["document_type"]:
        aadhaar_match = re.search(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', full_text)
        if aadhaar_match and re.search(r'Government\s*of\s*India|Aadhaar|UIDAI', full_text, re.IGNORECASE):
            details["document_type"] = "AADHAAR_CARD"
            details["id_number"] = re.sub(r'[\s\-]', '', aadhaar_match.group(0))
            
    # Voter ID (EPIC)
    if not details["document_type"]:
        voter_match = re.search(r'\b[A-Z]{3}\d{7}\b', full_text, re.IGNORECASE)
        if voter_match and re.search(r'ELECTION\s*COMMISSION|EPIC|Elector', full_text, re.IGNORECASE):
            details["document_type"] = "VOTER_ID"
            details["id_number"] = voter_match.group(0).upper()

    # Early return if document type is not recognized (e.g. invalid photo, menu, etc)
    if not details["document_type"]:
        raise ValueError("Invalid Document: Please rescan with a correct document (Aadhaar, PAN, Voter ID, or ABHA).")

    # 2. Gender
    if re.search(r'\b(?:Male|MALE|Purush)\b', full_text, re.IGNORECASE):
        details["gender"] = "MALE"
    elif re.search(r'\b(?:Female|FEMALE|Mahila)\b', full_text, re.IGNORECASE):
        details["gender"] = "FEMALE"
    elif re.search(r'\b(?:Transgender)\b', full_text, re.IGNORECASE):
        details["gender"] = "TRANSGENDER"

    # 3. DOB
    dob_match = re.search(r'(?:DOB|Date of Birth|Birth|Year of Birth|YOB)[^\d]{0,10}?([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4}|[0-9]{4})\b', full_text, re.IGNORECASE)
    if dob_match:
        details["dob"] = dob_match.group(1)
    else:
        # Fallback raw date
        for m in re.finditer(r'\b([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})\b', full_text):
            start_pos = max(0, m.start() - 20)
            prefix = full_text[start_pos:m.start()].lower()
            if "download" not in prefix and "issue" not in prefix:
                details["dob"] = m.group(1)
                break

    # 4. Mobile Number
    mob_match = re.search(r'\b(?:Mobile|Ph|Phone|Mobile No)[:\-\s]*([6-9]\d{9})\b', full_text, re.IGNORECASE)
    if not mob_match:
        # Just any isolated 10 digit number starting with 6-9
        mob_match = re.search(r'\b([6-9]\d{9})\b', full_text)
    if mob_match:
        details["mobile_number"] = mob_match.group(1)

    # 5. ABHA Address
    abha_addr = re.search(r'\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+\b', full_text)
    if abha_addr:
        details["abha_address"] = abha_addr.group(0).lower()

    # 6. Father Name
    father_label_idx = -1
    for i, line_dict in enumerate(ocr_results):
        text = line_dict['text']
        if re.search(r"Father'?s?\s*Name|Father|Husband", text, re.IGNORECASE):
            father_label_idx = i
            name_part = re.split(r"Father'?s?\s*Name|Father|Husband|:|;", text, flags=re.IGNORECASE)[-1].strip()
            name_part = re.sub(r'^[^a-zA-Z]+', '', name_part)
            if name_part.lower() in ["", "name", "sname", "'sname"]:
                name_part = ""
                
            if len(name_part) > 2:
                details["father_name"] = name_part
            elif 'box' in line_dict:
                details["father_name"] = _find_closest_value(i, ocr_results)
            elif i + 1 < len(ocr_results):
                details["father_name"] = ocr_results[i+1]['text'].strip()
            break
            
    # 7. Name
    for i, line_dict in enumerate(ocr_results):
        if i == father_label_idx:
            continue
        text = line_dict['text']
        if re.search(r"\bName\b", text, re.IGNORECASE) and not re.search(r"Father", text, re.IGNORECASE):
            name_part = re.split(r"\bName\b|:|;", text, flags=re.IGNORECASE)[-1].strip()
            name_part = re.sub(r'^[^a-zA-Z]+', '', name_part)
            if name_part.lower() in ["", "name", "sname", "'sname"]:
                name_part = ""
                
            if len(name_part) > 2:
                details["name"] = name_part
            elif 'box' in line_dict:
                excludes = set([details["father_name"]]) if details["father_name"] else set()
                details["name"] = _find_closest_value(i, ocr_results, excludes)
            elif i + 1 < len(ocr_results):
                details["name"] = ocr_results[i+1]['text'].strip()
            break
            
    if not details["name"]:
        # Fallback for Name: usually the first string that is uppercase, no digits, and not generic
        for text in texts:
            clean = text.strip()
            if len(clean) > 3 and not re.search(r'\d', clean) and not re.search(r'GOVERNMENT|INCOME TAX|DEPARTMENT|INDIA|REPUBLIC|ELECTION|COMMISSION|SIGNATURE|DOB|DATE|BIRTH', clean, re.IGNORECASE):
                if clean != details.get("father_name"):
                    details["name"] = clean
                    break

    details["name"] = clean_ocr_name(details["name"])
    details["father_name"] = clean_ocr_name(details["father_name"])
    
    return details

