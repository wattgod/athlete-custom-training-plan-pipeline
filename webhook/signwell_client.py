"""Small, fail-closed SignWell API adapter for coaching e-sign packets."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import requests


SIGNWELL_API_BASE = "https://www.signwell.com/api/v1"
MAX_SIGNED_DOCUMENT_BYTES = 25 * 1024 * 1024


class SignWellError(RuntimeError):
    """Raised when SignWell cannot provide a verified provider result."""


def verify_event_hash(payload: dict, webhook_id: str) -> bool:
    """Verify SignWell's documented HMAC-SHA256 event hash."""
    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict) or not webhook_id:
        return False
    event_type = str(event.get("type") or "")
    event_time = event.get("time")
    supplied = str(event.get("hash") or "")
    if not event_type or event_time is None or len(supplied) != 64:
        return False
    try:
        event_time = str(int(event_time))
    except (TypeError, ValueError):
        return False
    expected = hmac.new(
        webhook_id.encode("utf-8"),
        f"{event_type}@{event_time}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(supplied, expected)


class SignWellClient:
    def __init__(self, api_key: str, *, session=None,
                 base_url: str = SIGNWELL_API_BASE):
        if not api_key:
            raise SignWellError("SIGNWELL_API_KEY is required")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}))
        headers["X-Api-Key"] = self.api_key
        headers.setdefault("Accept", "application/json")
        try:
            response = self.session.request(
                method, f"{self.base_url}{path}", headers=headers,
                timeout=(5, 30), **kwargs)
        except requests.RequestException as exc:
            raise SignWellError(f"SignWell request failed: {type(exc).__name__}") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise SignWellError(
                f"SignWell returned HTTP {response.status_code} for {path}")
        return response

    def create_document_from_templates(self, payload: dict) -> dict[str, Any]:
        response = self._request(
            "POST", "/document_templates/documents",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise SignWellError("SignWell returned invalid document JSON") from exc
        document_id = str(data.get("id") or "")
        try:
            import uuid
            uuid.UUID(document_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise SignWellError("SignWell returned an invalid document ID") from exc
        return data

    def get_document(self, document_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/documents/{document_id}")
        try:
            data = response.json()
        except ValueError as exc:
            raise SignWellError("SignWell returned invalid readback JSON") from exc
        if str(data.get("id") or "") != document_id:
            raise SignWellError("SignWell document readback identity mismatch")
        return data

    def get_completed_pdf(self, document_id: str) -> bytes:
        response = self._request(
            "GET", f"/documents/{document_id}/completed_pdf",
            params={"audit_page": "true", "file_format": "pdf"},
            headers={"Accept": "application/pdf"},
            stream=True,
        )
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_SIGNED_DOCUMENT_BYTES:
                raise SignWellError("Completed SignWell PDF exceeds the size limit")
            chunks.append(chunk)
        content = b"".join(chunks)
        if len(content) < 5 or not content.startswith(b"%PDF-"):
            raise SignWellError("SignWell completed document is not a PDF")
        return content

    def get_account(self) -> dict[str, Any]:
        response = self._request("GET", "/me")
        try:
            return response.json()
        except ValueError as exc:
            raise SignWellError("SignWell returned invalid account JSON") from exc
