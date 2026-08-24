"""
End-to-end integration tests using the 4 real sample images:
- aadharcard.jpeg
- pancard.jpeg
- voterid.jpeg
- ABHA_Card_91-2748-8665-1315 (40).png
"""

import os
import cv2
import pytest
from app.ocr.engine import ocr_engine
from app.extractors.line_reconstructor import reconstruct_lines
from app.api.v1.scan import _aadhaar_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, PARSER_MAP, DOC_TYPE_NORMAL_MAP

TEST_IMAGE_DIR = r"C:\Users\Hariom_patel\Documents\IDScanner\test_image"


@pytest.fixture(scope="module", autouse=True)
def setup_ocr():
    ocr_engine.initialize()


class TestRealImages:
    def test_aadhaar_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "aadharcard.jpeg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)
        
        ext_res = _aadhaar_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "825395633085"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["aadhaar_card"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "Hari Om Patel"
        assert parsed.fields["dob"].value == "28/12/2004"
        assert parsed.fields["gender"].value == "Male"

    def test_pan_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "pancard.jpeg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)
        
        ext_res = _pan_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "GDTPP3272F"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["pan_card"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "HARI OM PATEL"
        assert parsed.fields["father_name"].value == "JAI PRAKASH CHAUDHARY"
        assert parsed.fields["dob"].value == "28/12/2004"

    def test_voter_id(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "voterid.jpeg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)
        
        ext_res = _voter_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "NUG2923662"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["voter_id"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "Hari Om Patel"
        assert parsed.fields["relation_name"].value == "Harishankar Patel"
        assert parsed.fields["gender"].value == "Male"
        assert parsed.fields["dob"].value == "28/12/2004"

    def test_abha_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "ABHA_Card_91-2748-8665-1315 (40).png")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)
        
        ext_res = _abha_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "91-2748-8665-1315"
        assert ext_res["abha_address"] == "patelhari282004@sbx"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["abha_number"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "Hari Om Patel"
        assert parsed.fields["gender"].value == "Male"
        assert parsed.fields["dob"].value == "28/12/2004"
        assert parsed.fields["mobile"].value == "6307643369"

    def test_pann_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "PANN.jpeg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)

        ext_res = _pan_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "LGSPK7071C"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["pan_card"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "SHASHI RANJAN KUMAR"
        assert parsed.fields["father_name"].value == "NAVEEN KUMAR JHA"
        assert parsed.fields["dob"].value == "24/10/2003"

    def test_voterrr_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "VOTERRR.jpeg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)

        ext_res = _voter_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "UBV2991586"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["voter_id"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "SHASHI RANJAN KUMAR"
        assert parsed.fields["relation_name"].value == "NAVEEN KUMAR JHA"

    def test_voterttttt_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "VOTERTTTTT.png")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)

        ext_res = _voter_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "AXZ0003210"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["voter_id"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value in ("ROHTASH KUMAR", "ROHTASHKUMAR")
        assert parsed.fields["relation_name"].value in ("GOPI RAM", "GOPIRAM")
        assert parsed.fields["gender"].value == "Male"

    def test_voteriddd_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "VOTERIDDD.png")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)

        ext_res = _voter_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "RIW7626286"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["voter_id"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "Shubham Darekar"
        assert parsed.fields["relation_name"].value == "Nandini Darekar"
        assert parsed.fields["relation_type"].value == "Mother"

    def test_farmer_id_card(self):
        img_path = os.path.join(TEST_IMAGE_DIR, "farmer_id.jpg")
        assert os.path.exists(img_path), f"File missing: {img_path}"

        img = cv2.imread(img_path)
        raw_results = ocr_engine.process_image(img)

        ext_res = _farmer_ext.extract(raw_results)
        assert ext_res is not None
        assert ext_res["identifier"] == "195 36 94 77 21"

        lines = reconstruct_lines(raw_results)
        parser = PARSER_MAP["farmer_id"]
        parsed = parser.extract_fields(lines)

        assert parsed.overall_status == "ok"
        assert parsed.fields["name"].value == "Pramod Kumar"
        assert parsed.fields["dob"].value == "10/06/1991"
        assert parsed.fields["gender"].value == "Male"
        assert parsed.fields["mobile"].value == "9027956097"
        assert parsed.fields["aadhaar_number"].value == "527613815535"

