"""Purpose-scoped intake tokens for the CONSULT-ENGINE post-pay flow.

Independent from download_tokens.py's audience-keyed artifact tokens: an
intake token is minted once per consult order, carried in the URL FRAGMENT
of the welcome email (never the query string — query-string credentials
are forbidden, app.py:103-105 / :3286, and only `token=` is log-redacted),
and valid ONLY for POST /api/consult-intake. Its own secret,
CONSULT_INTAKE_TOKEN_SECRET, is deliberately separate from CRON_SECRET,
CONSULT_RUNNER_SECRET, and DOWNLOAD_TOKEN_* — a leaked intake token (30-day
TTL, mailed to an athlete) must not unlock anything else.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict

TOKEN_VERSION = "consult_intake_token/v1"
PURPOSE = "consult_intake"
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


class ConsultIntakeTokenError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _secret() -> bytes:
    value = os.environ.get("CONSULT_INTAKE_TOKEN_SECRET", "").strip()
    if not value:
        raise ConsultIntakeTokenError(
            "CONSULT_INTAKE_TOKEN_SECRET is not configured")
    return value.encode()


def keys_configured() -> bool:
    try:
        _secret()
        return True
    except ConsultIntakeTokenError:
        return False


def issue_intake_token(
    *,
    order_id: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    if not str(order_id).strip():
        raise ConsultIntakeTokenError("order_id is required")
    if not isinstance(ttl_seconds, int) or ttl_seconds < 1 or ttl_seconds > DEFAULT_TTL_SECONDS:
        raise ConsultIntakeTokenError("invalid token lifetime")
    issued_at = int(time.time() if now is None else now)
    claims = {
        "version": TOKEN_VERSION,
        "purpose": PURPOSE,
        "order_id": str(order_id),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }
    payload = _b64(_canonical(claims))
    signature = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_intake_token(
    token: str,
    *,
    expected_order_id: str,
    now: int | None = None,
) -> Dict[str, Any]:
    try:
        payload, signature = str(token or "").split(".", 1)
        claims = json.loads(_unb64(payload))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConsultIntakeTokenError("malformed token") from exc
    if claims.get("version") != TOKEN_VERSION:
        raise ConsultIntakeTokenError("unsupported token version")
    if claims.get("purpose") != PURPOSE:
        raise ConsultIntakeTokenError("wrong token purpose")
    expected_signature = _b64(
        hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected_signature):
        raise ConsultIntakeTokenError("invalid token signature")
    current = int(time.time() if now is None else now)
    iat = claims.get("iat")
    exp = claims.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int) or exp <= iat:
        raise ConsultIntakeTokenError("invalid token timestamps")
    if exp - iat > DEFAULT_TTL_SECONDS:
        raise ConsultIntakeTokenError("token lifetime exceeds maximum")
    if current < iat or current >= exp:
        raise ConsultIntakeTokenError("token expired or not yet valid")
    if str(claims.get("order_id")) != str(expected_order_id):
        raise ConsultIntakeTokenError("order_id mismatch")
    return claims
