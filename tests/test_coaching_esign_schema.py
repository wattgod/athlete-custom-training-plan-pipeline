import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA = Path(__file__).parents[1] / "schemas" / "coaching_esign_packet_v1.schema.json"


def test_adult_esign_packet_contract_is_valid():
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate({
        "schema": "coaching_esign_packet/v1",
        "case_id": "2ad5853c-186d-4ac2-87f6-8dc43e490929",
        "brand": "gravelgod",
        "athlete": {
            "name": "Test Rider",
            "email": "rider@example.com",
            "is_minor": False,
        },
        "documents": [
            {
                "gate": "coaching_agreement",
                "template_id": "agreement-template",
                "document_version": "v1",
                "signer_role": "athlete",
            },
            {
                "gate": "data_consent",
                "template_id": "data-template",
                "document_version": "v1",
                "signer_role": "athlete",
            },
        ],
        "legal_approval_receipt": "counsel-approval-2026-01",
    })


def test_minor_packet_requires_guardian():
    schema = json.loads(SCHEMA.read_text())
    errors = list(Draft202012Validator(schema).iter_errors({
        "schema": "coaching_esign_packet/v1",
        "case_id": "97937815-c072-4cc2-9966-906485cab5f0",
        "brand": "roadielabs",
        "athlete": {
            "name": "Junior Rider",
            "email": "junior@example.com",
            "is_minor": True,
        },
        "documents": [
            {
                "gate": "coaching_agreement",
                "template_id": "agreement-template",
                "document_version": "v1",
                "signer_role": "athlete",
            },
            {
                "gate": "data_consent",
                "template_id": "data-template",
                "document_version": "v1",
                "signer_role": "athlete",
            },
        ],
        "legal_approval_receipt": "counsel-approval-2026-01",
    }))
    assert any("guardian" in error.message for error in errors)
