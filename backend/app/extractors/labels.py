"""
Shared bilingual label anchor dictionary.

Used by all document parsers to locate field anchors in OCR output.
Includes English, Hindi, Marathi, and common OCR misread variants.
"""

LABELS = {
    # --- Common across documents ---
    "name": [
        "name", "नाम", "nane", "narne", "namo", "elector's name", "electors name", "elector name",
        "मतदाराचे नाव", "मतदाराचे", "नाव"
    ],
    "dob": [
        "dob", "date of birth", "dateof birth", "date of bith", "जन्म तिथि", "जन्म की तारीख",
        "year of birth", "d.o.b", "birth date", "date of birth/age", "dob/age", "आयु/dob",
        "date of birth/upfaffr", "birth", "तारीख", "जन्मतारीख"
    ],
    "gender": [
        "gender", "sex", "लिंग", "gander", "gendar", "fe/gender", "gender/लिंग", "sex/लिंग",
        "fe/gender:y", "gender/ frr"
    ],

    # --- PAN / Voter ID specific ---
    "father_name": [
        "father's name", "पिता का नाम", "father name", "father's nane", "fathers name",
        "वडिलांचे नाव", "वडिलांचे", "s/o", "son of", "father", "पिता"
    ],
    "mother_name": [
        "mother's name", "mothers name", "mother name", "आईचे नाव", "आईचे", "माता का नाम", "माता", "mother"
    ],
    "husband_name": [
        "husband's name", "पति का नाम", "पतीचे नाव", "पतीचे", "w/o", "wife of", "husband name", "husband"
    ],
    "daughter_of": [
        "d/o", "daughter of"
    ],
    "relation_name": [
        "mother's name", "mothers name", "mother name", "आईचे नाव", "आईचे", "माता का नाम",
        "father/husband name", "relation name", "father's name", "father name",
        "husband's name", "husband name", "पिता/पति का नाम", "पिता का नाम", "पति का नाम",
        "वडिलांचे नाव", "पतीचे नाव", "other", "relation", "संबंधी का नाम", "नातेदाराचे नाव",
        "s/o", "d/o", "w/o", "m/o", "c/o"
    ],

    # --- ABHA specific ---
    "mobile": [
        "mobile", "मोबाइल", "phone", "mobile no", "mobile number", "contact", "mob", "mobile/ sa"
    ],
    "abha_address": [
        "abha address", "health id", "abha id", "abha address/ anr q"
    ],

    # --- Headers ---
    "aadhaar_header": [
        "government of india", "भारत सरकार", "unique identification", "uidai", "आधार", "aadhaar"
    ],
    "pan_header": [
        "income tax department", "income tax", "permanent account number", "govt. of india", "आयकर विभाग"
    ],
    "voter_header": [
        "election commission of india", "election commission", "भारत निर्वाचन आयोग", "भारत निवडणूक आयोग", "epic", "elector",
        "electors photo identity card", "elector photo identity card", "मतदार फोटो ओळख पत्र"
    ],
    "abha_header": [
        "ayushman bharat health account", "national health authority", "abha", "ayushman bharat", "आयुष्मान भारत"
    ],

    # --- Age ---
    "age": [
        "age", "आयु", "उम्र", "वय", "age as on"
    ],
}

# Gender value normalization map
GENDER_MAP = {
    # English
    "male": "Male",
    "m": "Male",
    "female": "Female",
    "f": "Female",
    "transgender": "Transgender",
    "trans": "Transgender",
    "third gender": "Transgender",
    "others": "Transgender",
    # Hindi / Marathi
    "पुरुष": "Male",
    "पुरूष": "Male",
    "महिला": "Female",
    "स्त्री": "Female",
    "किन्नर": "Transgender",
    "तृतीयपंथी": "Transgender",
    "ट्रांसजेंडर": "Transgender",
    # OCR misreads
    "malo": "Male",
    "famale": "Female",
    "femal": "Female",
    "fermale": "Female",
    "mal": "Male",
    "maie": "Male",
}
