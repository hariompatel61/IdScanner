import sys

def update_file(filepath, replacements, append_text):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    content += append_text
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# ABHA
update_file(
    'app/parsers/abha.py',
    [
        ('from app.parsers.base import BaseDocParser', 'from app.parsers.base import DocumentPlugin, DocumentSchema\nfrom app.parsers.registry import document_registry'),
        ('class ABHAParser(BaseDocParser):', 'class ABHAPlugin(DocumentPlugin):\n    document_id = "abha_card"\n    display_name = "ABHA Card"\n    aliases = ["abha"]\n    supported_sides = ["front"]\n    schema = DocumentSchema(expected_fields=["name", "abha_number", "dob", "gender", "mobile", "abha_address"], mandatory_fields=["name", "abha_number", "dob", "gender"])\n'),
        ('        return self._build_result(fields)', '        fields["abha_number"] = self._extract_abha_number(ocr_lines)\n        return self._build_result(fields)')
    ],
    '''
    def _extract_abha_number(self, ocr_lines):
        import re
        _ABHA_NUMBER_PATTERN = re.compile(r"\\b(\d{2})[\s\-]?(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\\b")
        best_value, best_conf = None, 0.0
        for line in ocr_lines:
            for match in _ABHA_NUMBER_PATTERN.finditer(line.text):
                val = match.group(0)
                if line.confidence > best_conf:
                    best_conf = line.confidence
                    best_value = val
        if best_value:
            status = "ok" if best_conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best_value, confidence=round(best_conf, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

ABHAParser = ABHAPlugin
document_registry.register(ABHAPlugin())
'''
)

# Farmer ID
update_file(
    'app/parsers/farmer_id.py',
    [
        ('from app.parsers.base import BaseDocParser', 'from app.parsers.base import DocumentPlugin, DocumentSchema\nfrom app.parsers.registry import document_registry'),
        ('class FarmerIDParser(BaseDocParser):', 'class FarmerIDPlugin(DocumentPlugin):\n    document_id = "farmer_id"\n    display_name = "Farmer ID"\n    aliases = ["farmer"]\n    supported_sides = ["front"]\n    schema = DocumentSchema(expected_fields=["name", "dob", "gender", "farmer_id"], mandatory_fields=["name", "dob", "gender"])\n')
    ],
    '\nFarmerIDParser = FarmerIDPlugin\ndocument_registry.register(FarmerIDPlugin())\n'
)

# Passport
update_file(
    'app/parsers/passport.py',
    [
        ('from app.parsers.base import BaseDocParser', 'from app.parsers.base import DocumentPlugin, DocumentSchema\nfrom app.parsers.registry import document_registry'),
        ('class PassportParser(BaseDocParser):', 'class PassportPlugin(DocumentPlugin):\n    document_id = "passport"\n    display_name = "Passport"\n    aliases = ["passport"]\n    supported_sides = ["front"]\n    schema = DocumentSchema(expected_fields=["name", "dob", "gender", "passport_number", "surname", "given_name", "nationality", "date_of_issue", "date_of_expiry", "mrz"], mandatory_fields=["name", "dob", "gender", "passport_number"])\n')
    ],
    '\nPassportParser = PassportPlugin\ndocument_registry.register(PassportPlugin())\n'
)
