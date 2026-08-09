"""Phase 4 read-only TrainingPeaks worker boundary.

This module intentionally contains no HTTP client or browser implementation.
The only executable operations are probe/inspect against an injected transport.
Mutation capabilities are parsed and checked here for Phase 5 reuse, while all
mutation operation entrypoints refuse before consulting a transport.
"""

from __future__ import annotations

import base64
import binascii
import copy
import fcntl
import hashlib
import hmac
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


PROBE_ACTIONS = {"probe", "inspect"}
MUTATION_ACTIONS = {"apply", "verify", "rollback"}
ALL_ACTIONS = PROBE_ACTIONS | MUTATION_ACTIONS
SUBJECT_LOCATORS = {"email", "tp_athlete_id", "candidate_list_ref"}
PROBE_CAPABILITY_TYPE = "trainingpeaks_probe_capability/v1"
MUTATION_CAPABILITY_TYPE = "trainingpeaks_mutation_capability/v1"
INSPECTION_EVIDENCE_TYPE = "trainingpeaks_inspection_evidence/v1"
TOKEN_ALGORITHM = "HS256"
MAX_CAPABILITY_TTL_SECONDS = 15 * 60
JTI_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")


class WorkerAuthorizationError(ValueError):
    """A signed capability is malformed, invalid, stale, or replayed."""


class WorkerMutationRefused(PermissionError):
    """Phase 4's zero-write gate refused a mutation operation."""


class WorkerTransportError(RuntimeError):
    """The injected read-only transport could not complete a probe."""


class ReadOnlyWorkerTransport(Protocol):
    def probe_athlete(self, identity: Mapping[str, str]) -> Mapping[str, Any]: ...
    def inspect_account(self, tp_athlete_id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class VerifiedCapability:
    capability_type: str
    claims: dict[str, Any]
    kid: str

    @property
    def action(self) -> str:
        return str(self.claims["action"])


@dataclass(frozen=True)
class VerifiedInspectionEvidence:
    """Provenance returned only after a signed inspect capability executes."""

    order_id: str
    tp_athlete_id: str
    capability_jti: str
    capability_kid: str
    request_digest: str
    observed_at: str
    result: dict[str, Any]


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _require_string(claims: Mapping[str, Any], field: str) -> str:
    value = claims.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WorkerAuthorizationError(f"capability {field} is required")
    return value.strip()


def _validate_common_claims(
    claims: Mapping[str, Any], *, audience: str, now: int,
) -> None:
    _require_string(claims, "order_id")
    if _require_string(claims, "audience") != audience:
        raise WorkerAuthorizationError("capability audience mismatch")
    action = _require_string(claims, "action")
    if action not in ALL_ACTIONS:
        raise WorkerAuthorizationError("unknown capability action")
    jti = _require_string(claims, "jti")
    if not JTI_PATTERN.fullmatch(jti):
        raise WorkerAuthorizationError("capability jti is invalid")
    iat, exp = claims.get("iat"), claims.get("exp")
    if isinstance(iat, bool) or not isinstance(iat, int):
        raise WorkerAuthorizationError("capability iat is invalid")
    if isinstance(exp, bool) or not isinstance(exp, int):
        raise WorkerAuthorizationError("capability exp is invalid")
    if iat > now or exp <= now:
        raise WorkerAuthorizationError("capability is not currently valid")
    if exp <= iat or exp - iat > MAX_CAPABILITY_TTL_SECONDS:
        raise WorkerAuthorizationError("capability lifetime is invalid")


def _validate_probe_claims(claims: Mapping[str, Any]) -> None:
    expected = {"order_id", "subject", "action", "audience", "iat", "exp", "jti"}
    if set(claims) != expected:
        raise WorkerAuthorizationError("probe capability shape is invalid")
    if claims["action"] not in PROBE_ACTIONS:
        raise WorkerAuthorizationError("probe capability cannot authorize a mutation")
    subject = claims.get("subject")
    if not isinstance(subject, dict) or subject.get("kind") != "identity_query":
        raise WorkerAuthorizationError("probe subject must be an identity_query")
    locators = SUBJECT_LOCATORS & set(subject)
    if set(subject) != {"kind"} | locators or len(locators) != 1:
        raise WorkerAuthorizationError("probe subject requires exactly one identity locator")
    _require_string(subject, next(iter(locators)))


def _validate_mutation_claims(claims: Mapping[str, Any]) -> None:
    expected = {
        "order_id", "tp_athlete_id", "generation_revision", "model_seal",
        "action", "audience", "iat", "exp", "jti",
    }
    if set(claims) != expected:
        raise WorkerAuthorizationError("mutation capability shape is invalid")
    if claims["action"] not in MUTATION_ACTIONS:
        raise WorkerAuthorizationError("mutation capability action is invalid")
    _require_string(claims, "tp_athlete_id")
    model_seal = _require_string(claims, "model_seal")
    if not re.fullmatch(r"[0-9a-f]{64}", model_seal):
        raise WorkerAuthorizationError("mutation model_seal is invalid")
    revision = claims.get("generation_revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise WorkerAuthorizationError("mutation generation_revision is invalid")


class CapabilityCodec:
    """Small rotating-key HMAC capability codec with exact claim schemas."""

    def __init__(self, keys: Mapping[str, bytes | str], *, audience: str):
        normalized: dict[str, bytes] = {}
        for kid, secret in keys.items():
            if not isinstance(kid, str) or not kid.strip():
                raise ValueError("capability key id is invalid")
            raw = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
            if len(raw) < 32:
                raise ValueError("capability signing secrets must be at least 32 bytes")
            normalized[kid] = raw
        if not normalized:
            raise ValueError("at least one capability signing key is required")
        self._keys = normalized
        self.audience = str(audience or "").strip()
        if not self.audience:
            raise ValueError("capability audience is required")

    def issue(self, claims: Mapping[str, Any], *, kid: str) -> str:
        if kid not in self._keys:
            raise WorkerAuthorizationError("unknown capability signing key")
        header = {"alg": TOKEN_ALGORITHM, "kid": kid, "typ": "GG-WORKER-CAP"}
        encoded_header = _b64encode(_canonical_json(header))
        encoded_claims = _b64encode(_canonical_json(dict(claims)))
        signed = f"{encoded_header}.{encoded_claims}".encode("ascii")
        signature = hmac.new(self._keys[kid], signed, hashlib.sha256).digest()
        return f"{encoded_header}.{encoded_claims}.{_b64encode(signature)}"

    def verify(
        self, token: str, *, now: int, expected_action: str | None = None,
    ) -> VerifiedCapability:
        try:
            encoded_header, encoded_claims, encoded_signature = str(token).split(".")
            header = json.loads(_b64decode(encoded_header))
            claims = json.loads(_b64decode(encoded_claims))
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError,
                binascii.Error) as exc:
            raise WorkerAuthorizationError("invalid capability encoding") from exc
        if not isinstance(header, dict) or set(header) != {"alg", "kid", "typ"}:
            raise WorkerAuthorizationError("invalid capability header")
        if header.get("alg") != TOKEN_ALGORITHM or header.get("typ") != "GG-WORKER-CAP":
            raise WorkerAuthorizationError("unsupported capability header")
        kid = str(header.get("kid") or "")
        secret = self._keys.get(kid)
        if secret is None:
            raise WorkerAuthorizationError("unknown capability signing key")
        signed = f"{encoded_header}.{encoded_claims}".encode("ascii")
        expected = hmac.new(secret, signed, hashlib.sha256).digest()
        try:
            supplied = _b64decode(encoded_signature)
        except (ValueError, binascii.Error) as exc:
            raise WorkerAuthorizationError("invalid capability signature") from exc
        if not hmac.compare_digest(supplied, expected):
            raise WorkerAuthorizationError("invalid capability signature")
        if not isinstance(claims, dict):
            raise WorkerAuthorizationError("capability claims must be an object")
        _validate_common_claims(claims, audience=self.audience, now=int(now))
        action = str(claims["action"])
        if expected_action is not None and action != expected_action:
            raise WorkerAuthorizationError("capability action mismatch")
        if action in PROBE_ACTIONS:
            _validate_probe_claims(claims)
            capability_type = PROBE_CAPABILITY_TYPE
        else:
            _validate_mutation_claims(claims)
            capability_type = MUTATION_CAPABILITY_TYPE
        return VerifiedCapability(capability_type, copy.deepcopy(claims), kid)


def mutation_exchange_predicate(
    capability: VerifiedCapability, authoritative_state: Mapping[str, Any],
    *, attempt: Mapping[str, Any] | None = None, request_digest: str = "",
    operator_authorized: bool = False,
) -> tuple[bool, str]:
    """Pure Phase 5 predicate table; it never issues an execution grant."""
    if capability.capability_type != MUTATION_CAPABILITY_TYPE:
        return False, "mutation exchange requires a mutation capability"
    claims = capability.claims
    if authoritative_state.get("order_id") != claims["order_id"]:
        return False, "order mismatch"
    if authoritative_state.get("generation_revision") != claims["generation_revision"]:
        return False, "revision mismatch"
    if authoritative_state.get("model_seal") != claims["model_seal"]:
        return False, "model seal mismatch"
    identity = authoritative_state.get("platform_identity") or {}
    if identity.get("tp_athlete_id") != claims["tp_athlete_id"]:
        return False, "platform identity mismatch"
    action, status = claims["action"], authoritative_state.get("status")
    if authoritative_state.get("cancel_requested"):
        return False, "cancellation requested"
    if action == "apply":
        if status == "APPROVED":
            return True, "apply-initial"
        same_attempt = bool(
            status == "APPLYING" and attempt
            and attempt.get("jti") == claims["jti"]
            and attempt.get("request_digest") == request_digest
            and attempt.get("status") in {"accepted", "running"}
        )
        return (True, "apply-resume") if same_attempt else (False, "apply resume mismatch")
    if action == "verify":
        allowed = status in {"APPLYING", "APPLIED", "APPLIED_ATTESTED"}
        return allowed, "verify" if allowed else "verify status is ineligible"
    if action == "rollback":
        pending = bool(
            status in {"APPLYING", "APPLIED"}
            or (status == "CANCELLED" and authoritative_state.get("compensation_pending"))
        )
        allowed = pending and operator_authorized
        return allowed, "rollback" if allowed else "rollback requires eligible status and operator action"
    return False, "unknown mutation action"


class ProbeExecutionStore:
    """Atomic, order-scoped replay records for read-only probe capabilities."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _paths(self, order_id: str, jti: str) -> tuple[Path, Path]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", order_id):
            raise WorkerAuthorizationError("capability order_id is unsafe")
        if not JTI_PATTERN.fullmatch(jti):
            raise WorkerAuthorizationError("capability jti is invalid")
        record = self.root / order_id / f"{jti}.json"
        return record, record.with_suffix(".lock")

    def run(
        self, claims: Mapping[str, Any], request: Mapping[str, Any], operation,
        *, evidence_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return copy.deepcopy(self.run_record(
            claims, request, operation, evidence_context=evidence_context,
        )["results"])

    def run_record(
        self, claims: Mapping[str, Any], request: Mapping[str, Any], operation,
        *, evidence_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run or replay an operation and return its complete durable record."""
        record_path, lock_path = self._paths(str(claims["order_id"]), str(claims["jti"]))
        record_path.parent.mkdir(parents=True, exist_ok=True)
        request_digest = _digest(request)
        context = copy.deepcopy(dict(evidence_context)) if evidence_context is not None else None
        evidence_requested = context is not None
        if context is not None:
            _canonical_json(context)
        with open(lock_path, "a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            existing = None
            if record_path.exists():
                try:
                    existing = json.loads(record_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise WorkerAuthorizationError("probe replay record is malformed") from exc
            if existing:
                if existing.get("request_digest") != request_digest:
                    raise WorkerAuthorizationError("capability jti replay request differs")
                if evidence_requested and not existing.get("evidence_context"):
                    raise WorkerAuthorizationError(
                        "probe replay record lacks inspection provenance")
                if existing.get("status") == "succeeded":
                    return copy.deepcopy(existing)
                if existing.get("status") == "failed":
                    raise WorkerTransportError("recorded probe attempt failed")
                # Read-only accepted/running attempts are safe to resume.
                context = copy.deepcopy(existing.get("evidence_context"))
            else:
                self._write(record_path, {
                    "status": "accepted", "order_id": claims["order_id"],
                    "jti": claims["jti"], "request_digest": request_digest,
                    "results": None, "evidence_context": context,
                })
            self._write(record_path, {
                "status": "running", "order_id": claims["order_id"],
                "jti": claims["jti"], "request_digest": request_digest,
                "results": None, "evidence_context": context,
            })
            try:
                results = dict(operation())
                _canonical_json(results)
            except Exception as exc:
                self._write(record_path, {
                    "status": "failed", "order_id": claims["order_id"],
                    "jti": claims["jti"], "request_digest": request_digest,
                    "results": {"error_type": type(exc).__name__},
                    "evidence_context": context,
                })
                raise WorkerTransportError("read-only worker transport failed") from exc
            succeeded = {
                "status": "succeeded", "order_id": claims["order_id"],
                "jti": claims["jti"], "request_digest": request_digest,
                "results": results, "evidence_context": context,
            }
            self._write(record_path, succeeded)
            return copy.deepcopy(succeeded)

    def verify_inspection_evidence(
        self, evidence: VerifiedInspectionEvidence,
    ) -> None:
        """Require exact equality with a durable succeeded inspection record."""
        if not isinstance(evidence, VerifiedInspectionEvidence):
            raise WorkerAuthorizationError("worker inspection evidence type is invalid")
        record_path, lock_path = self._paths(
            evidence.order_id, evidence.capability_jti)
        if not record_path.exists():
            raise WorkerAuthorizationError(
                "worker inspection evidence has no durable execution record")
        with open(lock_path, "a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkerAuthorizationError(
                    "probe replay record is malformed") from exc
        expected_request = {
            "operation": "inspect_account",
            "tp_athlete_id": evidence.tp_athlete_id,
        }
        expected_context = {
            "evidence_type": INSPECTION_EVIDENCE_TYPE,
            "operation": "inspect_account",
            "tp_athlete_id": evidence.tp_athlete_id,
            "capability_kid": evidence.capability_kid,
            "observed_at": evidence.observed_at,
        }
        if (record.get("status") != "succeeded"
                or record.get("order_id") != evidence.order_id
                or record.get("jti") != evidence.capability_jti
                or record.get("request_digest") != evidence.request_digest
                or evidence.request_digest != _digest(expected_request)
                or record.get("evidence_context") != expected_context
                or record.get("results") != evidence.result):
            raise WorkerAuthorizationError(
                "worker inspection evidence does not match durable execution record")

    @staticmethod
    def request_digest(request: Mapping[str, Any]) -> str:
        """Return the canonical digest bound into a probe execution record."""
        return _digest(request)

    @staticmethod
    def _write(path: Path, value: Mapping[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


class CannedProbeTransport:
    """No-network transport for ``worker_probes.json`` fixture responses."""

    def __init__(self, fixture: Mapping[str, Any], *, tp_athlete_id: str = "fixture-athlete-m"):
        self.fixture = copy.deepcopy(dict(fixture))
        self.tp_athlete_id = str(tp_athlete_id)
        self.calls: list[tuple[str, Any]] = []

    @classmethod
    def from_path(cls, path: Path | str, **kwargs: Any) -> "CannedProbeTransport":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), **kwargs)

    def probe_athlete(self, identity: Mapping[str, str]) -> Mapping[str, Any]:
        self.calls.append(("probe", dict(identity)))
        explicit = self.fixture.get("probe_athlete")
        if isinstance(explicit, dict):
            return copy.deepcopy(explicit)
        if not self.fixture.get("account_found"):
            return {"outcome": "not-found", "candidates": []}
        if not self.fixture.get("coached"):
            return {
                "outcome": "not-coached", "tp_athlete_id": self.tp_athlete_id,
                "candidates": [],
            }
        return {
            "outcome": "bound", "tp_athlete_id": self.tp_athlete_id,
            "candidates": [],
        }

    def inspect_account(self, tp_athlete_id: str) -> Mapping[str, Any]:
        self.calls.append(("inspect", tp_athlete_id))
        explicit = self.fixture.get("inspect_account")
        if isinstance(explicit, dict):
            return copy.deepcopy(explicit)
        result = copy.deepcopy(self.fixture)
        result["tp_athlete_id"] = str(tp_athlete_id)
        return result


class ReadOnlyWorkerService:
    def __init__(
        self, codec: CapabilityCodec, replay_store: ProbeExecutionStore,
        transport: ReadOnlyWorkerTransport,
    ):
        self.codec = codec
        self.replay_store = replay_store
        self.transport = transport

    def probe_athlete(self, identity: Mapping[str, str], capability: str, *, now: int) -> dict[str, Any]:
        verified = self.codec.verify(capability, now=now, expected_action="probe")
        normalized = {str(key): str(value) for key, value in identity.items()}
        subject = verified.claims["subject"]
        locator = next(iter(SUBJECT_LOCATORS & set(subject)))
        if normalized != {locator: subject[locator]}:
            raise WorkerAuthorizationError("probe request does not match capability subject")
        request = {"operation": "probe_athlete", "identity": normalized}
        return self.replay_store.run(
            verified.claims, request,
            lambda: self.transport.probe_athlete(normalized),
        )

    def inspect_account(self, tp_athlete_id: str, capability: str, *, now: int) -> dict[str, Any]:
        return copy.deepcopy(
            self.inspect_account_evidence(
                tp_athlete_id, capability, now=now,
            ).result
        )

    def inspect_account_evidence(
        self, tp_athlete_id: str, capability: str, *, now: int,
    ) -> VerifiedInspectionEvidence:
        """Inspect once and return capability/request-bound readback provenance."""
        verified = self.codec.verify(capability, now=now, expected_action="inspect")
        subject = verified.claims["subject"]
        if subject.get("tp_athlete_id") != str(tp_athlete_id):
            raise WorkerAuthorizationError("inspection request does not match capability subject")
        request = {"operation": "inspect_account", "tp_athlete_id": str(tp_athlete_id)}
        observed_at = datetime.fromtimestamp(
            int(now), tz=timezone.utc,
        ).isoformat().replace("+00:00", "Z")
        record = self.replay_store.run_record(
            verified.claims, request,
            lambda: self.transport.inspect_account(str(tp_athlete_id)),
            evidence_context={
                "evidence_type": INSPECTION_EVIDENCE_TYPE,
                "operation": "inspect_account",
                "tp_athlete_id": str(tp_athlete_id),
                "capability_kid": verified.kid,
                "observed_at": observed_at,
            },
        )
        context = record.get("evidence_context")
        if not isinstance(context, dict):
            raise WorkerAuthorizationError(
                "probe replay record has malformed inspection provenance")
        required_context = {
            "evidence_type", "operation", "tp_athlete_id",
            "capability_kid", "observed_at",
        }
        if set(context) != required_context:
            raise WorkerAuthorizationError(
                "probe replay record has malformed inspection provenance")
        evidence = VerifiedInspectionEvidence(
            order_id=str(record["order_id"]),
            tp_athlete_id=str(context["tp_athlete_id"]),
            capability_jti=str(record["jti"]),
            capability_kid=str(context["capability_kid"]),
            request_digest=str(record["request_digest"]),
            observed_at=str(context["observed_at"]),
            result=copy.deepcopy(record["results"]),
        )
        self.replay_store.verify_inspection_evidence(evidence)
        return evidence

    @staticmethod
    def _refuse(operation: str) -> None:
        raise WorkerMutationRefused(
            f"{operation} is REFUSED: Phase 4 worker is read-only; mutation execution starts in Phase 5"
        )

    def apply(self, *_args: Any, **_kwargs: Any) -> None:
        self._refuse("apply")

    def verify(self, *_args: Any, **_kwargs: Any) -> None:
        self._refuse("verify")

    def rollback(self, *_args: Any, **_kwargs: Any) -> None:
        self._refuse("rollback")


def exchange_mutation_capability_phase4(*_args: Any, **_kwargs: Any) -> None:
    """Explicit zero-grant Phase 4 online-exchange stub."""
    raise WorkerMutationRefused(
        "execution grant issuance is REFUSED in Phase 4 (zero remote writes)"
    )
