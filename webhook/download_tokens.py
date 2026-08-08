"""Typed, revision-bound download capabilities for Phase 1."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict

TOKEN_VERSION = "download_token/v1"
MAX_TTL_SECONDS = 7 * 24 * 60 * 60
ARTIFACT_AUDIENCE = {
    "review_bundle": "coach",
    "customer_bundle": "customer",
}


class DownloadTokenError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _keyring() -> Dict[str, Dict[str, str]]:
    raw = os.environ.get("DOWNLOAD_TOKEN_KEYS", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DownloadTokenError("DOWNLOAD_TOKEN_KEYS is invalid") from exc
        if not isinstance(parsed, dict):
            raise DownloadTokenError("DOWNLOAD_TOKEN_KEYS is invalid")
        for audience in ARTIFACT_AUDIENCE.values():
            if not isinstance(parsed.get(audience), dict) or not parsed[audience]:
                raise DownloadTokenError(
                    f"DOWNLOAD_TOKEN_KEYS has no {audience} keys")
        return parsed
    root = os.environ.get("DOWNLOAD_TOKEN_SECRET", "").strip()
    if not root:
        raise DownloadTokenError(
            "download token keys are not configured; set DOWNLOAD_TOKEN_KEYS "
            "or DOWNLOAD_TOKEN_SECRET"
        )
    kid = os.environ.get("DOWNLOAD_TOKEN_KID", "phase1-v1")
    return {
        audience: {
            kid: hmac.new(root.encode(), audience.encode(), hashlib.sha256).hexdigest()
        }
        for audience in ("coach", "customer")
    }


def _key(audience: str, kid: str) -> bytes:
    try:
        value = _keyring()[audience][kid]
    except (KeyError, TypeError) as exc:
        raise DownloadTokenError("unknown token key") from exc
    if not isinstance(value, str) or not value:
        raise DownloadTokenError("unknown token key")
    return value.encode()


def _current_kid(audience: str) -> str:
    configured = os.environ.get(f"DOWNLOAD_TOKEN_{audience.upper()}_KID", "")
    keys = _keyring().get(audience) or {}
    kid = configured or os.environ.get("DOWNLOAD_TOKEN_KID", "")
    if kid:
        if kid not in keys:
            raise DownloadTokenError("configured current kid is unknown")
        return kid
    if len(keys) != 1:
        raise DownloadTokenError("current token kid is ambiguous")
    return next(iter(keys))


def issue_download_token(
    *,
    order_id: str,
    athlete_id: str,
    generation_revision: int,
    artifact: str,
    audience: str | None = None,
    ttl_seconds: int = MAX_TTL_SECONDS,
    now: int | None = None,
    jti: str | None = None,
) -> str:
    expected_audience = ARTIFACT_AUDIENCE.get(artifact)
    if not expected_audience:
        raise DownloadTokenError("unknown artifact")
    audience = audience or expected_audience
    if audience != expected_audience:
        raise DownloadTokenError("artifact is not available to that audience")
    if not str(order_id).strip() or not str(athlete_id).strip():
        raise DownloadTokenError("order_id and athlete_id are required")
    if not isinstance(generation_revision, int) or generation_revision < 1:
        raise DownloadTokenError("invalid generation revision")
    if not isinstance(ttl_seconds, int) or ttl_seconds < 1 or ttl_seconds > MAX_TTL_SECONDS:
        raise DownloadTokenError("invalid token lifetime")
    issued_at = int(time.time() if now is None else now)
    kid = _current_kid(audience)
    claims = {
        "version": TOKEN_VERSION,
        "order_id": order_id,
        "athlete_id": athlete_id,
        "generation_revision": generation_revision,
        "artifact": artifact,
        "audience": audience,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": jti or uuid.uuid4().hex,
        "kid": kid,
    }
    payload = _b64(_canonical(claims))
    signature = _b64(hmac.new(_key(audience, kid), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _read_revocations(path: Path | None) -> Dict[str, list[str]]:
    if path is None or not path.exists():
        return {"jti": [], "kid": []}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise DownloadTokenError("token revocation store unavailable") from exc
    return {
        "jti": list(value.get("jti") or []),
        "kid": list(value.get("kid") or []),
    }


def verify_download_token(
    token: str,
    *,
    expected_order_id: str,
    expected_athlete_id: str,
    expected_revision: int,
    expected_artifact: str,
    expected_audience: str,
    revocation_path: Path | str | None = None,
    now: int | None = None,
) -> Dict[str, Any]:
    try:
        payload, signature = token.split(".", 1)
        claims = json.loads(_unb64(payload))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DownloadTokenError("malformed token") from exc
    if claims.get("version") != TOKEN_VERSION:
        raise DownloadTokenError("unsupported token version")
    artifact = claims.get("artifact")
    audience = claims.get("audience")
    if ARTIFACT_AUDIENCE.get(artifact) != audience:
        raise DownloadTokenError("invalid artifact audience")
    kid = str(claims.get("kid") or "")
    expected_signature = _b64(hmac.new(
        _key(str(audience), kid), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected_signature):
        raise DownloadTokenError("invalid token signature")
    current = int(time.time() if now is None else now)
    iat = claims.get("iat")
    exp = claims.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int) or exp <= iat:
        raise DownloadTokenError("invalid token timestamps")
    if exp - iat > MAX_TTL_SECONDS:
        raise DownloadTokenError("token lifetime exceeds maximum")
    if current < iat or current >= exp:
        raise DownloadTokenError("token expired or not yet valid")
    expected = {
        "order_id": expected_order_id,
        "athlete_id": expected_athlete_id,
        "generation_revision": expected_revision,
        "artifact": expected_artifact,
        "audience": expected_audience,
    }
    for key, value in expected.items():
        if claims.get(key) != value:
            raise DownloadTokenError(f"token {key} mismatch")
    revocations = _read_revocations(Path(revocation_path) if revocation_path else None)
    if claims.get("jti") in revocations["jti"] or kid in revocations["kid"]:
        raise DownloadTokenError("token revoked")
    return claims


def revoke_download_token(
    revocation_path: Path | str,
    *,
    jti: str = "",
    kid: str = "",
) -> None:
    if not jti and not kid:
        raise DownloadTokenError("jti or kid is required")
    path = Path(revocation_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        value = _read_revocations(path)
        if jti:
            value["jti"] = sorted(set(value["jti"] + [jti]))
        if kid:
            value["kid"] = sorted(set(value["kid"] + [kid]))
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".revocations.")
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
