"""Narrow, signed Endure-to-Motoren coach-review capability.

The shared key authenticates one request at a time. It is deliberately not the
general ``CRON_SECRET``: Endure may read a sealed review and submit the exact
human confirmation snapshot, but it receives no apply, cancel, or delivery
authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping


SIGNATURE_VERSION = "endure-approval/v1"
MAX_CLOCK_SKEW_SECONDS = 300
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class EndureApprovalAuthError(ValueError):
    """The caller did not present a valid narrow bridge capability."""


@dataclass(frozen=True)
class VerifiedEndureRequest:
    key_id: str
    timestamp: int
    body_digest: str
    command_digest: str


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def request_message(
    method: str,
    path: str,
    timestamp: int,
    body: Any | None,
) -> tuple[bytes, str, str]:
    body_bytes = b"" if body is None else canonical_json(body)
    body_digest = hashlib.sha256(body_bytes).hexdigest()
    message = (
        f"{SIGNATURE_VERSION}\n{method.upper()}\n{path}\n{timestamp}\n"
        f"{body_digest}"
    ).encode("utf-8")
    # Authentication binds the clock and transport scope. The durable command
    # identity binds only canonical content so an exact retry with a fresh
    # timestamp remains idempotent.
    return message, body_digest, body_digest


def verify_endure_request(
    *,
    method: str,
    path: str,
    body: Any | None,
    headers: Mapping[str, str],
    secret: str,
    expected_key_id: str,
    now: int | None = None,
) -> VerifiedEndureRequest:
    if len(secret) < 32 or len(expected_key_id) < 8:
        raise EndureApprovalAuthError("Endure approval bridge is unavailable")
    key_id = str(headers.get("X-Endure-Key-Id") or "").strip()
    timestamp_text = str(headers.get("X-Endure-Timestamp") or "").strip()
    signature = str(headers.get("X-Endure-Signature") or "").strip().lower()
    if key_id != expected_key_id or not _HEX_DIGEST.fullmatch(signature):
        raise EndureApprovalAuthError("Endure approval capability is invalid")
    try:
        timestamp = int(timestamp_text)
    except ValueError as exc:
        raise EndureApprovalAuthError(
            "Endure approval capability timestamp is invalid",
        ) from exc
    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp) > MAX_CLOCK_SKEW_SECONDS:
        raise EndureApprovalAuthError("Endure approval capability is stale")

    message, body_digest, command_digest = request_message(
        method, path, timestamp, body,
    )
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise EndureApprovalAuthError("Endure approval capability is invalid")
    return VerifiedEndureRequest(
        key_id=key_id,
        timestamp=timestamp,
        body_digest=body_digest,
        command_digest=command_digest,
    )
