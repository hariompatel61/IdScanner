import json
from app.extractors import extract_demographics

data = {
    "demographics": {
        "document_type": "PAN_CARD",
        "id_number": "CMMPG0565J",
        "name": "Capture Document",
        "father_name": None,
        "dob": None,
        "gender": None,
        "mobile_number": None,
        "abha_number": None,
        "abha_address": None
    },
    "raw_results": [
        {
            "box": [[101.0, 34.0], [228.0, 34.0], [228.0, 75.0], [101.0, 75.0]],
            "text": "11:42",
            "confidence": "0.757101039091746"
        },
        {
            "box": [[70.0, 94.0], [238.0, 100.0], [236.0, 133.0], [69.0, 127.0]],
            "text": "WhatsApp",
            "confidence": "0.8119027680820889"
        },
        {
            "box": [[109.0, 184.0], [1032.0, 184.0], [1032.0, 230.0], [109.0, 230.0]],
            "text": "...fixed-nonsubversively.ngrok-free.dev",
            "confidence": "0.9275985687971116"
        },
        {
            "box": [[377.0, 337.0], [846.0, 337.0], [846.0, 386.0], [377.0, 386.0]],
            "text": "Capture Document",
            "confidence": "0.8423589292694541"
        },
        {
            "box": [[248.0, 408.0], [968.0, 411.0], [968.0, 445.0], [248.0, 442.0]],
            "text": "Frame the document within the rectangle",
            "confidence": "0.8604062929749489"
        },
        {
            "box": [[151.0, 1019.0], [527.0, 1024.0], [526.0, 1060.0], [151.0, 1056.0]],
            "text": "INCOMETAXDEPARTMENT",
            "confidence": "0.9167935967445373"
        },
        {
            "box": [[740.0, 1026.0], [1040.0, 1026.0], [1040.0, 1059.0], [740.0, 1059.0]],
            "text": "GOVT.OFINDIA",
            "confidence": "0.8693986076575059"
        },
        {
            "box": [[338.0, 1110.0], [746.0, 1113.0], [746.0, 1140.0], [338.0, 1137.0]],
            "text": "e-Permanent Account Number Card",
            "confidence": "0.8578442502766848"
        },
        {
            "box": [[409.0, 1156.0], [653.0, 1160.0], [653.0, 1193.0], [408.0, 1189.0]],
            "text": "CMMPG0565J",
            "confidence": "0.8641591017896478"
        },
        {
            "box": [[131.0, 1253.0], [268.0, 1253.0], [268.0, 1277.0], [131.0, 1277.0]],
            "text": "/Name",
            "confidence": "0.594356914361318"
        },
        {
            "box": [[127.0, 1281.0], [420.0, 1282.0], [420.0, 1308.0], [126.0, 1307.0]],
            "text": "GOKUL SINGHGARIYA",
            "confidence": "0.8926110400093926"
        },
        {
            "box": [[126.0, 1329.0], [483.0, 1334.0], [483.0, 1360.0], [125.0, 1355.0]],
            "text": "a可IFathersName",
            "confidence": "0.7548476755619049"
        },
        {
            "box": [[121.0, 1363.0], [433.0, 1364.0], [433.0, 1390.0], [121.0, 1389.0]],
            "text": "SUNDAR SINGHGARIYA",
            "confidence": "0.8891202148638273"
        },
        {
            "box": [[115.0, 1443.0], [276.0, 1441.0], [277.0, 1465.0], [115.0, 1467.0]],
            "text": "Date of Birth",
            "confidence": "0.8011494789804731"
        },
        {
            "box": [[110.0, 1482.0], [246.0, 1482.0], [246.0, 1506.0], [110.0, 1506.0]],
            "text": "06/03/1998",
            "confidence": "0.8267738602378152"
        },
        {
            "box": [[502.0, 1497.0], [730.0, 1497.0], [730.0, 1524.0], [502.0, 1524.0]],
            "text": "/Signature",
            "confidence": "0.885177568955855"
        }
    ]
}

res = extract_demographics(data["raw_results"])
print(res)
