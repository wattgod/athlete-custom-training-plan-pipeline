"""Unit tests for the narrow SignWell transport and event verifier."""

import hashlib
import hmac
from unittest.mock import MagicMock

import pytest
import requests

from signwell_client import SignWellClient, SignWellError, verify_event_hash


def _event(webhook_id="webhook-123"):
    event_type = "document_completed"
    event_time = 1787654321
    digest = hmac.new(
        webhook_id.encode(), f"{event_type}@{event_time}".encode(),
        hashlib.sha256).hexdigest()
    return {"event": {
        "type": event_type, "time": event_time, "hash": digest,
    }}


def test_verify_event_hash_accepts_exact_documented_message():
    assert verify_event_hash(_event(), "webhook-123") is True


def test_verify_event_hash_rejects_tampering_and_malformed_values():
    payload = _event()
    payload["event"]["type"] = "document_declined"
    assert verify_event_hash(payload, "webhook-123") is False
    assert verify_event_hash({"event": {"type": "x", "time": "bad"}}, "id") is False
    assert verify_event_hash(_event(), "wrong-webhook") is False


def test_create_document_uses_api_key_and_validates_identity():
    response = MagicMock(status_code=201)
    response.json.return_value = {
        "id": "3f6d240b-7154-4eaa-98a8-93ee4a12c899",
        "status": "sent",
    }
    session = MagicMock()
    session.request.return_value = response
    client = SignWellClient("api-key", session=session, base_url="https://example.test")
    document = client.create_document_from_templates({"template_ids": ["x"]})
    assert document["status"] == "sent"
    kwargs = session.request.call_args.kwargs
    assert kwargs["headers"]["X-Api-Key"] == "api-key"
    assert kwargs["json"] == {"template_ids": ["x"]}
    assert kwargs["timeout"] == (5, 30)


def test_client_fails_closed_on_http_network_and_bad_document_identity():
    session = MagicMock()
    session.request.side_effect = requests.ConnectionError("secret details")
    with pytest.raises(SignWellError, match="ConnectionError"):
        SignWellClient("api-key", session=session).get_account()

    response = MagicMock(status_code=200)
    response.json.return_value = {"id": "wrong"}
    session.request.side_effect = None
    session.request.return_value = response
    with pytest.raises(SignWellError, match="identity mismatch"):
        SignWellClient("api-key", session=session).get_document(
            "3f6d240b-7154-4eaa-98a8-93ee4a12c899")

    response.json.return_value = {"id": "wrong"}
    with pytest.raises(SignWellError, match="template readback identity mismatch"):
        SignWellClient("api-key", session=session).get_template(
            "7a194aa6-b535-4704-999e-767ce62ab9bf")


def test_completed_pdf_requires_pdf_and_size_limit(monkeypatch):
    response = MagicMock(status_code=200)
    response.iter_content.return_value = [b"%PDF-1.7\n", b"synthetic"]
    session = MagicMock()
    session.request.return_value = response
    client = SignWellClient("api-key", session=session)
    assert client.get_completed_pdf(
        "3f6d240b-7154-4eaa-98a8-93ee4a12c899").startswith(b"%PDF-")
    assert session.request.call_args.kwargs["params"]["audit_page"] == "true"

    response.iter_content.return_value = [b"not-a-pdf"]
    with pytest.raises(SignWellError, match="not a PDF"):
        client.get_completed_pdf("3f6d240b-7154-4eaa-98a8-93ee4a12c899")

    monkeypatch.setattr("signwell_client.MAX_SIGNED_DOCUMENT_BYTES", 4)
    response.iter_content.return_value = [b"%PDF-"]
    with pytest.raises(SignWellError, match="size limit"):
        client.get_completed_pdf("3f6d240b-7154-4eaa-98a8-93ee4a12c899")
