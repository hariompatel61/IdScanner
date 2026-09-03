import os
import json
import cv2
import numpy as np
import uuid

DATASET_DIR = os.path.join("tests", "fixtures", "benchmarks", "dataset")

def create_synthetic_id(doc_type, fields, condition="clean"):
    # Base clean image
    img = np.zeros((600, 1000, 3), dtype=np.uint8)
    img.fill(240) # Off-white background
    
    cv2.rectangle(img, (10, 10), (990, 590), (0, 0, 0), 2)
    
    y = 50
    for k, v in fields.items():
        if k == 'header':
            cv2.putText(img, v, (200, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
            y += 80
            continue
            
        cv2.putText(img, f"{k}:", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
        cv2.putText(img, v, (350, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        y += 60

    # Apply conditions
    if condition == "blur":
        img = cv2.GaussianBlur(img, (15, 15), 0)
    elif condition == "glare":
        overlay = img.copy()
        cv2.circle(overlay, (500, 300), 200, (255, 255, 255), -1)
        img = cv2.addWeighted(overlay, 0.4, img, 0.6, 0)
    elif condition == "low_light":
        img = cv2.convertScaleAbs(img, alpha=0.3, beta=0)
    elif condition == "rotation":
        M = cv2.getRotationMatrix2D((500, 300), 5, 1.0) # 5 degrees
        img = cv2.warpAffine(img, M, (1000, 600), borderValue=(255,255,255))
        
    return img

def generate_samples():
    templates = {
        "aadhaar_card": [
            {
                "fields": {
                    "header": "Government of India",
                    "Name": "John Doe",
                    "DOB": "01/01/1990",
                    "Gender": "MALE",
                    "Aadhaar": "1234 5678 9010"
                },
                "expected": {
                    "name": "John Doe",
                    "dob": "01/01/1990",
                    "gender": "MALE",
                    "aadhaar_number": "123456789010"
                }
            }
        ],
        "pan_card": [
            {
                "fields": {
                    "header": "INCOME TAX DEPARTMENT",
                    "Name": "Jane Smith",
                    "Father's Name": "Robert Smith",
                    "DOB": "15/05/1985",
                    "PAN": "ABCDE1234F"
                },
                "expected": {
                    "name": "Jane Smith",
                    "fathers_name": "Robert Smith",
                    "dob": "15/05/1985",
                    "pan_number": "ABCDE1234F"
                }
            }
        ],
        "voter_id": [
            {
                "fields": {
                    "header": "ELECTION COMMISSION OF INDIA",
                    "Elector's Name": "Michael Scott",
                    "Father's Name": "Edward Scott",
                    "Sex": "Male",
                    "Date of Birth": "20/06/1980",
                    "Voter ID": "XYZ1234567"
                },
                "expected": {
                    "name": "Michael Scott",
                    "relation_name": "Edward Scott",
                    "relation_type": "Father",
                    "gender": "Male",
                    "dob": "20/06/1980",
                    "voter_id": "XYZ1234567"
                }
            }
        ],
        "abha_card": [
            {
                "fields": {
                    "header": "Health ID",
                    "Name": "Dwight Schrute",
                    "ABHA Number": "12-3456-7890-1234",
                    "Year of Birth": "1978",
                    "Gender": "M"
                },
                "expected": {
                    "name": "Dwight Schrute",
                    "abha_number": "12-3456-7890-1234",
                    "yob": "1978",
                    "gender": "M"
                }
            }
        ],
        "farmer_id": [
            {
                "fields": {
                    "header": "FARMER ID CARD",
                    "Name": "Jim Halpert",
                    "Father Name": "Gerald Halpert",
                    "ID": "FRM-987654",
                    "State": "Pennsylvania"
                },
                "expected": {
                    "name": "Jim Halpert",
                    "fathers_name": "Gerald Halpert",
                    "farmer_id": "FRM-987654"
                }
            }
        ],
        "passport": [
            {
                "fields": {
                    "header": "REPUBLIC OF INDIA",
                    "Type": "P",
                    "Given Name(s)": "Pamela",
                    "Surname": "Beesly",
                    "Passport No": "Z1234567",
                    "Date of Birth": "15/10/1985",
                    "Sex": "F"
                },
                "expected": {
                    "given_name": "Pamela",
                    "surname": "Beesly",
                    "passport_number": "Z1234567",
                    "dob": "15/10/1985",
                    "gender": "F"
                }
            }
        ]
    }
    
    conditions = ["clean", "blur", "glare", "low_light", "rotation"]
    
    for doc_type, samples in templates.items():
        for i, sample in enumerate(samples):
            for condition in conditions:
                img = create_synthetic_id(doc_type, sample['fields'], condition)
                
                sample_id = uuid.uuid4().hex[:8]
                dir_path = os.path.join(DATASET_DIR, doc_type, condition, sample_id)
                os.makedirs(dir_path, exist_ok=True)
                
                img_path = os.path.join(dir_path, "image.jpg")
                cv2.imwrite(img_path, img)
                
                gt = {
                    "document_type": doc_type,
                    "condition": condition,
                    "expected_fields": sample['expected'],
                    "expected_status": "ACCEPT" if condition in ["clean", "rotation"] else "REVIEW"
                }
                
                with open(os.path.join(dir_path, "ground_truth.json"), "w") as f:
                    json.dump(gt, f, indent=2)

if __name__ == "__main__":
    print("Generating synthetic benchmark dataset...")
    generate_samples()
    print("Done.")
