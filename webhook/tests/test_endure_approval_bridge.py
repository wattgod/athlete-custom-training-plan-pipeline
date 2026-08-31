import hashlib
import hmac
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from endure_approval_bridge import (
    EndureApprovalAuthError,
    request_message,
    verify_endure_request,
)


SECRET = "endure-approval-test-secret-that-is-long-enough"
KEY_ID = "endure-test-key"


def _headers(method, path, body, timestamp=1_800_000_000):
    message, _, _ = request_message(method, path, timestamp, body)
    return {
        "X-Endure-Key-Id": KEY_ID,
        "X-Endure-Timestamp": str(timestamp),
        "X-Endure-Signature": hmac.new(
            SECRET.encode(), message, hashlib.sha256,
        ).hexdigest(),
    }


def test_verified_request_binds_method_path_clock_and_canonical_body():
    body = {"z": [1, 2], "a": {"value": True}}
    verified = verify_endure_request(
        method="POST",
        path="/api/fulfillment/order/endure-approval",
        body=body,
        headers=_headers(
            "POST", "/api/fulfillment/order/endure-approval", body,
        ),
        secret=SECRET,
        expected_key_id=KEY_ID,
        now=1_800_000_000,
    )
    assert verified.key_id == KEY_ID
    assert len(verified.body_digest) == 64
    assert verified.command_digest == verified.body_digest


@pytest.mark.parametrize(
    "changed",
    [
        {"method": "GET"},
        {"path": "/api/fulfillment/other/endure-approval"},
        {"body": {"a": {"value": False}, "z": [1, 2]}},
        {"now": 1_800_000_301},
    ],
)
def test_verified_request_rejects_scope_tampering_and_stale_clock(changed):
    body = {"a": {"value": True}, "z": [1, 2]}
    kwargs = {
        "method": "POST",
        "path": "/api/fulfillment/order/endure-approval",
        "body": body,
        "headers": _headers(
            "POST", "/api/fulfillment/order/endure-approval", body,
        ),
        "secret": SECRET,
        "expected_key_id": KEY_ID,
        "now": 1_800_000_000,
    }
    kwargs.update(changed)
    with pytest.raises(EndureApprovalAuthError):
        verify_endure_request(**kwargs)


def test_verified_request_fails_closed_when_not_configured():
    with pytest.raises(EndureApprovalAuthError, match="unavailable"):
        verify_endure_request(
            method="GET", path="/x", body=None, headers={}, secret="",
            expected_key_id="", now=1_800_000_000,
        )
