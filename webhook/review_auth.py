"""Revision-bound review links and durable browser sessions for Phase 2.

Review links are delivered in URL fragments, so the bearer never appears in
HTTP access logs or Referer headers.  The browser exchanges the bearer in a
POST body for an opaque, server-side session.  Opening a link consumes no
approval authority; only a CSRF-protected action is audited as a decision.
"""

from __future__ import annotations

import base64
import binascii
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict


REVIEW_TOKEN_VERSION = "review_token/v1"
REVIEW_ACTION = "review"
REVIEW_AUDIENCE = "coach"
MAX_REVIEW_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
REVIEW_SESSION_TTL_SECONDS = 12 * 60 * 60


class ReviewAuthError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _review_keyring() -> Dict[str, str]:
    raw = os.environ.get("REVIEW_TOKEN_KEYS", "").strip()
    if raw:
        try:
            keys = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReviewAuthError("REVIEW_TOKEN_KEYS is invalid") from exc
        if not isinstance(keys, dict) or not keys:
            raise ReviewAuthError("REVIEW_TOKEN_KEYS is invalid")
        if any(not isinstance(kid, str) or not isinstance(key, str) or not key
               for kid, key in keys.items()):
            raise ReviewAuthError("REVIEW_TOKEN_KEYS is invalid")
        return keys

    root = os.environ.get("REVIEW_TOKEN_SECRET", "").strip()
    if root:
        kid = os.environ.get("REVIEW_TOKEN_KID", "phase2-v1")
        return {kid: root}

    # Existing deployments already carry the Phase 1 typed-token keys.  A
    # domain-separated derivation keeps the review credential distinct while
    # avoiding a rollout window in which paid orders receive dead links.
    download_root = os.environ.get("DOWNLOAD_TOKEN_SECRET", "").strip()
    if download_root:
        kid = os.environ.get(
            "REVIEW_TOKEN_KID",
            os.environ.get("DOWNLOAD_TOKEN_COACH_KID",
                           os.environ.get("DOWNLOAD_TOKEN_KID", "phase1-v1")),
        )
        derived = hmac.new(
            download_root.encode("utf-8"), b"review-link",
            hashlib.sha256,
        ).hexdigest()
        return {kid: derived}

    download_keys_raw = os.environ.get("DOWNLOAD_TOKEN_KEYS", "").strip()
    if download_keys_raw:
        try:
            download_keys = json.loads(download_keys_raw)
            coach_keys = download_keys["coach"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ReviewAuthError("DOWNLOAD_TOKEN_KEYS has no coach keys") from exc
        if not isinstance(coach_keys, dict) or not coach_keys:
            raise ReviewAuthError("DOWNLOAD_TOKEN_KEYS has no coach keys")
        return {
            str(kid): hmac.new(
                str(key).encode("utf-8"), b"review-link", hashlib.sha256,
            ).hexdigest()
            for kid, key in coach_keys.items()
            if str(kid) and str(key)
        }

    raise ReviewAuthError(
        "review token keys are not configured; set REVIEW_TOKEN_KEYS, "
        "REVIEW_TOKEN_SECRET, or the typed download-token keys"
    )


def _current_kid() -> str:
    keys = _review_keyring()
    configured = os.environ.get("REVIEW_TOKEN_KID", "").strip()
    if (not configured and not os.environ.get("REVIEW_TOKEN_KEYS", "").strip()
            and not os.environ.get("REVIEW_TOKEN_SECRET", "").strip()):
        configured = os.environ.get(
            "DOWNLOAD_TOKEN_COACH_KID",
            os.environ.get("DOWNLOAD_TOKEN_KID", ""),
        ).strip()
    if configured:
        if configured not in keys:
            raise ReviewAuthError("configured review token kid is unknown")
        return configured
    if len(keys) != 1:
        raise ReviewAuthError("current review token kid is ambiguous")
    return next(iter(keys))


def _key(kid: str) -> bytes:
    try:
        return _review_keyring()[kid].encode("utf-8")
    except KeyError as exc:
        raise ReviewAuthError("unknown review token key") from exc


def _read_revocations(path: Path | None) -> Dict[str, list[str]]:
    if path is None or not path.exists():
        return {"jti": [], "kid": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewAuthError("token revocation store unavailable") from exc
    if not isinstance(value, dict):
        raise ReviewAuthError("token revocation store unavailable")
    return {
        "jti": list(value.get("jti") or []),
        "kid": list(value.get("kid") or []),
    }


def _validate_scope(
    claims: Dict[str, Any], *, order_id: str, athlete_id: str, revision: int,
    now: int, revocation_path: Path | None,
) -> None:
    if claims.get("version") != REVIEW_TOKEN_VERSION:
        raise ReviewAuthError("unsupported review token version")
    if claims.get("action") != REVIEW_ACTION or claims.get("audience") != REVIEW_AUDIENCE:
        raise ReviewAuthError("invalid review token scope")
    expected = {
        "order_id": order_id,
        "athlete_id": athlete_id,
        "generation_revision": revision,
    }
    for key, expected_value in expected.items():
        if claims.get(key) != expected_value:
            raise ReviewAuthError(f"review token {key} mismatch")
    iat, exp = claims.get("iat"), claims.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int) or exp <= iat:
        raise ReviewAuthError("invalid review token timestamps")
    if exp - iat > MAX_REVIEW_TOKEN_TTL_SECONDS:
        raise ReviewAuthError("review token lifetime exceeds maximum")
    if now < iat or now >= exp:
        raise ReviewAuthError("review token expired or not yet valid")
    jti = str(claims.get("jti") or "")
    kid = str(claims.get("kid") or "")
    issued_to = str(claims.get("issued_to") or "")
    if not jti or not kid or not issued_to:
        raise ReviewAuthError("review token identity is incomplete")
    revoked = _read_revocations(revocation_path)
    if jti in revoked["jti"] or kid in revoked["kid"]:
        raise ReviewAuthError("review token revoked")


def issue_review_token(
    *, order_id: str, athlete_id: str, generation_revision: int,
    issued_to: str, ttl_seconds: int = MAX_REVIEW_TOKEN_TTL_SECONDS,
    now: int | None = None, jti: str | None = None,
) -> str:
    if not order_id or not athlete_id or not issued_to:
        raise ReviewAuthError("review token identity is required")
    if not isinstance(generation_revision, int) or generation_revision < 1:
        raise ReviewAuthError("invalid generation revision")
    if (not isinstance(ttl_seconds, int) or ttl_seconds < 1
            or ttl_seconds > MAX_REVIEW_TOKEN_TTL_SECONDS):
        raise ReviewAuthError("invalid review token lifetime")
    issued_at = int(time.time() if now is None else now)
    kid = _current_kid()
    claims = {
        "version": REVIEW_TOKEN_VERSION,
        "action": REVIEW_ACTION,
        "audience": REVIEW_AUDIENCE,
        "order_id": str(order_id),
        "athlete_id": str(athlete_id),
        "generation_revision": generation_revision,
        "issued_to": str(issued_to),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": jti or uuid.uuid4().hex,
        "kid": kid,
    }
    payload = _b64(_canonical(claims))
    signature = _b64(hmac.new(_key(kid), payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_review_token(
    token: str, *, order_id: str, athlete_id: str, generation_revision: int,
    revocation_path: Path | str | None = None, now: int | None = None,
) -> Dict[str, Any]:
    try:
        payload, supplied_signature = str(token or "").split(".", 1)
        claims = json.loads(_unb64(payload))
        if not isinstance(claims, dict):
            raise ValueError("claims")
        kid = str(claims.get("kid") or "")
        expected_signature = _b64(hmac.new(
            _key(kid), payload.encode("ascii"), hashlib.sha256,
        ).digest())
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError,
            binascii.Error) as exc:
        raise ReviewAuthError("malformed review token") from exc
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ReviewAuthError("invalid review token signature")
    _validate_scope(
        claims, order_id=order_id, athlete_id=athlete_id,
        revision=generation_revision,
        now=int(time.time() if now is None else now),
        revocation_path=Path(revocation_path) if revocation_path else None,
    )
    return claims


def review_credential_id(claims: Dict[str, Any]) -> str:
    """Honest possession credential; never claims a named human logged in."""
    return (
        f"review-link:{claims['kid']}:"
        f"{claims['jti']}-{claims['issued_to']}"
    )


def _atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".review-session.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _session_path(root: Path | str, session_id: str) -> Path:
    digest = hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()
    return Path(root) / f"{digest}.json"


def create_review_session(
    root: Path | str, claims: Dict[str, Any], *, now: int | None = None,
) -> tuple[str, Dict[str, Any]]:
    current = int(time.time() if now is None else now)
    expires_at = min(int(claims["exp"]), current + REVIEW_SESSION_TTL_SECONDS)
    if expires_at <= current:
        raise ReviewAuthError("review token expired")
    session_id = secrets.token_urlsafe(32)
    session = {
        "version": "review_session/v1",
        "order_id": claims["order_id"],
        "athlete_id": claims["athlete_id"],
        "generation_revision": claims["generation_revision"],
        "credential": review_credential_id(claims),
        "jti": claims["jti"],
        "kid": claims["kid"],
        "issued_to": claims["issued_to"],
        "csrf_token": secrets.token_urlsafe(32),
        "created_at": current,
        "expires_at": expires_at,
    }
    path = _session_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _atomic_json(path, session)
    return session_id, session


def load_review_session(
    root: Path | str, session_id: str, *, order_id: str,
    revocation_path: Path | str | None = None, now: int | None = None,
) -> Dict[str, Any]:
    if not session_id:
        raise ReviewAuthError("review session is required")
    path = _session_path(root, session_id)
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewAuthError("review session is unavailable") from exc
    current = int(time.time() if now is None else now)
    if (not isinstance(session, dict)
            or session.get("version") != "review_session/v1"
            or session.get("order_id") != order_id
            or not isinstance(session.get("expires_at"), int)
            or current >= session["expires_at"]):
        raise ReviewAuthError("review session expired or mismatched")
    revoked = _read_revocations(Path(revocation_path) if revocation_path else None)
    if session.get("jti") in revoked["jti"] or session.get("kid") in revoked["kid"]:
        raise ReviewAuthError("review credential revoked")
    # Removing a signing kid is also an immediate session revocation point.
    _key(str(session.get("kid") or ""))
    return session
