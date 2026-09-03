import sys

with open('app/api/v1/scan.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Remove EXTRACTOR_MAP and PARSER_MAP imports and logic
content = content.replace('from app.extractors import EXTRACTOR_MAP, _aadhaar_ext, _aadhaar_back_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, _passport_ext', 'from app.parsers.registry import document_registry\nfrom app.extractors import _aadhaar_ext, _aadhaar_back_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, _passport_ext')
content = content.replace('from app.parsers import PARSER_MAP\n', '')

# Update extractor logic
old_ext_logic = '''    target_doc_type = (document_type or "").strip().lower()
    if target_doc_type and target_doc_type in EXTRACTOR_MAP:
        selected_extractors = [EXTRACTOR_MAP[target_doc_type]]
    else:
        selected_extractors = [_aadhaar_ext, _aadhaar_back_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, _passport_ext]'''

new_ext_logic = '''    target_doc_type = (document_type or "").strip().lower()
    
    # We maintain the legacy extractor list for fallback logic
    all_legacy_exts = [_aadhaar_ext, _aadhaar_back_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, _passport_ext]
    
    if target_doc_type and document_registry.supports(target_doc_type):
        target_plugin = document_registry.get(target_doc_type)
        if target_plugin.document_id == "aadhaar_card": selected_extractors = [_aadhaar_ext]
        elif target_plugin.document_id == "aadhaar_card_back": selected_extractors = [_aadhaar_back_ext]
        elif target_plugin.document_id == "pan_card": selected_extractors = [_pan_ext]
        elif target_plugin.document_id == "voter_id": selected_extractors = [_voter_ext]
        elif target_plugin.document_id == "abha_card": selected_extractors = [_abha_ext]
        elif target_plugin.document_id == "farmer_id": selected_extractors = [_farmer_ext]
        elif target_plugin.document_id == "passport": selected_extractors = [_passport_ext]
        else: selected_extractors = all_legacy_exts
    else:
        selected_extractors = all_legacy_exts'''

content = content.replace(old_ext_logic, new_ext_logic)

# Update parser logic
old_parser_logic = '        parser = PARSER_MAP.get(doc_type)'
new_parser_logic = '        parser = document_registry.get(doc_type)'
content = content.replace(old_parser_logic, new_parser_logic)

with open('app/api/v1/scan.py', 'w', encoding='utf-8') as f:
    f.write(content)
