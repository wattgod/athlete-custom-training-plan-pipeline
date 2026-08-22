"""Canonical Phase 5 mutation boundary for TrainingPeaks delivery.

The module owns authorization exchange, athlete-scoped fencing, durable
attempts, mutation intents, receipts, cancellation quiescence, and the final
APPLIED transition.  Network/browser details remain behind an injected
executor; an executor cannot mark an order applied without returning an exact
contract-wide readback receipt.
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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from athletes.scripts.apply_contract import ApplyContractError, validate_contract
from delivery.trainingpeaks.worker_service import (
    CapabilityCodec,
    MUTATION_OPERATION_BY_ACTION,
    MUTATION_CAPABILITY_TYPE,
    VerifiedCapability,
    WorkerAuthorizationError,
    mutation_exchange_predicate,
)


EXECUTION_GRANT_TYPE = "trainingpeaks_execution_grant/v2"
EXECUTION_RECORD_TYPE = "trainingpeaks_mutation_execution/v2"
EXECUTION_RECEIPT_TYPE = "trainingpeaks_apply_receipt/v1"
MAX_GRANT_TTL_SECONDS = 5 * 60
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


class Phase5Error(RuntimeError):
    """The Phase 5 state machine refused or could not finish an action."""


class Phase5AuthorizationError(Phase5Error):
    """Capability, grant, identity, seal, epoch, or fencing validation failed."""


class Phase5ReadbackMismatch(Phase5Error):
    """Remote readback did not exactly prove the requested contract."""


class Phase5Interrupted(Phase5Error):
    """Execution stopped in a resumable state after durable checkpointing."""


def _replace_or_append_prefix(
    rows: list[dict[str, Any]], row: Mapping[str, Any], expected_ids: list[str],
) -> list[dict[str, Any]]:
    """Idempotently checkpoint one row without ever accepting a gap/reorder."""
    op_id = str(row.get("op_id") or "")
    existing_ids = [str(item.get("op_id") or "") for item in rows]
    if op_id in existing_ids:
        index = existing_ids.index(op_id)
        if index >= len(expected_ids) or expected_ids[index] != op_id:
            raise Phase5AuthorizationError("mutation checkpoint order is invalid")
        updated = copy.deepcopy(rows)
        updated[index] = copy.deepcopy(dict(row))
        return updated
    if len(rows) >= len(expected_ids) or expected_ids[len(rows)] != op_id:
        raise Phase5AuthorizationError("mutation checkpoint is not the next operation")
    return copy.deepcopy(rows) + [copy.deepcopy(dict(row))]


def _proven_compensation_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only apply receipts that prove a mutating operation landed."""
    return [
        copy.deepcopy(item) for item in rows
        if ((item.get("disposition") in {"create", "update"}
             and item.get("status") == "landed")
            or (item.get("disposition") == "delete"
                and item.get("status") == "absent"))
    ]


@dataclass(frozen=True)
class CanaryPolicy:
    """Server-owned, exact-target lane used before global writes are enabled."""

    allowed_tp_athlete_ids: frozenset[str]
    allowed_kinds: frozenset[str] = frozenset({
        "workout_upsert", "calendar_note_upsert",
    })
    max_mutating_operations: int = 6
    required_order_prefix: str = "canary_"

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "CanaryPolicy | None":
        values = os.environ if environ is None else environ
        if str(values.get("GG_TP_CANARY_ENABLED") or "").strip() != "1":
            return None
        athlete_ids = frozenset(
            item.strip() for item in
            str(values.get("GG_TP_CANARY_ATHLETE_IDS") or "").split(",")
            if item.strip()
        )
        if not athlete_ids:
            raise Phase5AuthorizationError(
                "canary mode requires an exact athlete allowlist")
        return cls(allowed_tp_athlete_ids=athlete_ids)

    def authorize(
        self, contract: Mapping[str, Any], claims: Mapping[str, Any],
    ) -> None:
        athlete_id = str(claims.get("tp_athlete_id") or "")
        if athlete_id not in self.allowed_tp_athlete_ids:
            raise Phase5AuthorizationError("target is not allowlisted for canary writes")
        if not str(claims.get("order_id") or "").startswith(self.required_order_prefix):
            raise Phase5AuthorizationError("canary order identity is invalid")
        operations = contract.get("operations") or []
        if any(operation.get("kind") not in self.allowed_kinds for operation in operations):
            raise Phase5AuthorizationError("canary contract contains a forbidden operation kind")
        mutating = [
            operation for operation in operations
            if operation.get("disposition") != "keep"
        ]
        if not mutating or len(mutating) > self.max_mutating_operations:
            raise Phase5AuthorizationError("canary mutation count is outside policy")
        if not any(operation.get("disposition") == "keep" for operation in operations):
            raise Phase5AuthorizationError(
                "canary contract must prove protected-item preservation")


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


def _timestamp(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z")


@dataclass(frozen=True)
class VerifiedExecutionGrant:
    claims: dict[str, Any]
    kid: str


class ExecutionGrantCodec:
    """Rotating-key HMAC codec for the short-lived post-exchange grant."""

    def __init__(self, keys: Mapping[str, bytes | str], *, audience: str):
        self._keys: dict[str, bytes] = {}
        for kid, secret in keys.items():
            raw = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
            if not str(kid).strip() or len(raw) < 32:
                raise ValueError("execution-grant keys require an id and 32-byte secret")
            self._keys[str(kid)] = raw
        self.audience = str(audience or "").strip()
        if not self._keys or not self.audience:
            raise ValueError("execution-grant keys and audience are required")

    @staticmethod
    def _validate_claims(claims: Mapping[str, Any], *, audience: str, now: int) -> None:
        required = {
            "grant_type", "order_id", "tp_athlete_id", "generation_revision",
            "model_seal", "action", "audience", "capability_jti",
            "authorization_id", "actor", "scope", "approval_digest",
            "release_manifest_digest", "request_digest", "execution_epoch",
            "fencing_token", "iat", "exp", "grant_id",
        }
        if set(claims) != required or claims.get("grant_type") != EXECUTION_GRANT_TYPE:
            raise Phase5AuthorizationError("execution grant shape is invalid")
        for field in (
            "order_id", "tp_athlete_id", "action", "audience",
            "capability_jti", "authorization_id", "actor", "scope", "grant_id",
        ):
            if not isinstance(claims.get(field), str) or not claims[field].strip():
                raise Phase5AuthorizationError(f"execution grant {field} is invalid")
        if claims["audience"] != audience:
            raise Phase5AuthorizationError("execution grant audience mismatch")
        if claims["action"] not in {"apply", "verify", "rollback"}:
            raise Phase5AuthorizationError("execution grant action is invalid")
        for field in (
            "model_seal", "approval_digest", "release_manifest_digest",
            "request_digest",
        ):
            if not isinstance(claims.get(field), str) or not _HEX_64.fullmatch(claims[field]):
                raise Phase5AuthorizationError(f"execution grant {field} is invalid")
        for field in (
            "generation_revision", "execution_epoch", "fencing_token", "iat", "exp",
        ):
            if isinstance(claims.get(field), bool) or not isinstance(claims.get(field), int):
                raise Phase5AuthorizationError(f"execution grant {field} is invalid")
        if claims["generation_revision"] < 1 or claims["fencing_token"] < 1:
            raise Phase5AuthorizationError("execution grant revision or fence is invalid")
        if claims["iat"] > now or claims["exp"] <= now:
            raise Phase5AuthorizationError("execution grant is not currently valid")
        if (claims["exp"] <= claims["iat"]
                or claims["exp"] - claims["iat"] > MAX_GRANT_TTL_SECONDS):
            raise Phase5AuthorizationError("execution grant lifetime is invalid")

    def issue(self, claims: Mapping[str, Any], *, kid: str) -> str:
        secret = self._keys.get(kid)
        if secret is None:
            raise Phase5AuthorizationError("unknown execution-grant key")
        self._validate_claims(claims, audience=self.audience, now=int(claims["iat"]))
        header = {"alg": "HS256", "kid": kid, "typ": "GG-TP-GRANT"}
        encoded_header = _b64encode(_canonical_json(header))
        encoded_claims = _b64encode(_canonical_json(dict(claims)))
        signed = f"{encoded_header}.{encoded_claims}".encode("ascii")
        signature = hmac.new(secret, signed, hashlib.sha256).digest()
        return f"{encoded_header}.{encoded_claims}.{_b64encode(signature)}"

    def verify(self, token: str, *, now: int) -> VerifiedExecutionGrant:
        try:
            encoded_header, encoded_claims, encoded_signature = str(token).split(".")
            header = json.loads(_b64decode(encoded_header))
            claims = json.loads(_b64decode(encoded_claims))
            supplied = _b64decode(encoded_signature)
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError,
                binascii.Error) as exc:
            raise Phase5AuthorizationError("invalid execution-grant encoding") from exc
        if (not isinstance(header, dict)
                or header.get("alg") != "HS256"
                or header.get("typ") != "GG-TP-GRANT"):
            raise Phase5AuthorizationError("invalid execution-grant header")
        kid = str(header.get("kid") or "")
        secret = self._keys.get(kid)
        if secret is None:
            raise Phase5AuthorizationError("unknown execution-grant key")
        signed = f"{encoded_header}.{encoded_claims}".encode("ascii")
        expected = hmac.new(secret, signed, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            raise Phase5AuthorizationError("invalid execution-grant signature")
        if not isinstance(claims, dict):
            raise Phase5AuthorizationError("execution-grant claims must be an object")
        self._validate_claims(claims, audience=self.audience, now=int(now))
        return VerifiedExecutionGrant(copy.deepcopy(claims), kid)


def _validate_contract_binding(
    contract: Mapping[str, Any], capability: VerifiedCapability,
) -> str:
    if capability.capability_type != MUTATION_CAPABILITY_TYPE:
        raise Phase5AuthorizationError("a mutation capability is required")
    claims = capability.claims
    try:
        validate_contract(copy.deepcopy(dict(contract)))
    except (ApplyContractError, TypeError, ValueError) as exc:
        raise Phase5AuthorizationError(
            "apply contract failed canonical schema or semantic validation"
        ) from exc
    if not contract.get("operations"):
        raise Phase5AuthorizationError("apply contract operations are required")
    for field in ("order_id", "tp_athlete_id", "generation_revision", "model_seal"):
        if contract.get(field) != claims.get(field):
            raise Phase5AuthorizationError(f"apply contract {field} mismatch")
    contract_digest = _digest(contract)
    if claims.get("contract_digest") != contract_digest:
        raise Phase5AuthorizationError("apply contract digest mismatch")
    return contract_digest


def _validate_state_authorization_binding(
    state: Mapping[str, Any], claims: Mapping[str, Any],
) -> None:
    """Bind the signed action decision to the exact current approval/release."""
    if _digest(state.get("approval")) != claims.get("approval_digest"):
        raise Phase5AuthorizationError("authorization approval snapshot is stale")
    release_digest = state.get("release_manifest_digest")
    if release_digest != claims.get("release_manifest_digest"):
        raise Phase5AuthorizationError("authorization release manifest is stale")


class MutationExecutionContext:
    """Checkpoint API exposed to the one injected transport execution."""

    def __init__(
        self, service: "Phase5MutationService", grant: VerifiedExecutionGrant,
        state_path: Path, record_path: Path, contract: Mapping[str, Any], now: int,
    ):
        self.service = service
        self.grant = grant
        self.state_path = state_path
        self.record_path = record_path
        self.contract = copy.deepcopy(dict(contract))
        self.now = int(now)

    @property
    def prior_receipts(self) -> list[dict[str, Any]]:
        from fulfillment_state import load

        state = load(self.state_path)
        self.service._assert_state_matches_grant(state, self.grant.claims)
        attempt = state.get("application_attempt") or {}
        key = ("compensation_targets"
               if self.grant.claims.get("action") == "rollback" else "landed")
        return copy.deepcopy(attempt.get(key) or [])

    @property
    def rollback_receipts(self) -> list[dict[str, Any]]:
        if self.grant.claims.get("action") != "rollback":
            return []
        from fulfillment_state import load

        state = load(self.state_path)
        self.service._assert_state_matches_grant(state, self.grant.claims)
        attempt = state.get("application_attempt") or {}
        return copy.deepcopy(attempt.get("compensation_receipts") or [])

    def persist_intent(self, operation: Mapping[str, Any]) -> None:
        """Persist the exact intent before a remote mutation is attempted."""
        op_id = str(operation.get("op_id") or "")
        authoritative = next(
            (item for item in self.contract["operations"] if item.get("op_id") == op_id),
            None,
        )
        if authoritative is None or dict(operation) != authoritative:
            raise Phase5AuthorizationError("mutation intent is not contract-exact")
        if operation.get("disposition") == "keep":
            raise Phase5AuthorizationError("keep operations do not create mutation intents")
        self.service._checkpoint(self, "intent", operation=authoritative)

    def record_receipt(
        self, operation: Mapping[str, Any], *, status: str,
        remote_id: str | None, observed_digest: str | None,
        reconciled_after_error: bool = False,
    ) -> None:
        """Persist remote identity/readback immediately after classification."""
        op_id = str(operation.get("op_id") or "")
        authoritative = next(
            (item for item in self.contract["operations"] if item.get("op_id") == op_id),
            None,
        )
        if authoritative is None or dict(operation) != authoritative:
            raise Phase5AuthorizationError("mutation receipt is not contract-exact")
        action = self.grant.claims.get("action")
        remote = str(remote_id or "").strip()
        if action == "rollback":
            target = next(
                (item for item in self.prior_receipts if item.get("op_id") == op_id),
                None,
            )
            strategy = (authoritative.get("rollback") or {}).get("strategy")
            if target is None:
                raise Phase5AuthorizationError(
                    "rollback receipt is not a frozen compensation target")
            if strategy == "delete_by_remote_id":
                valid = (status == "absent" and remote
                         and remote == str(target.get("remote_id") or "")
                         and observed_digest is None)
            elif strategy in {"restore_prior_payload", "restore_before_image"}:
                prior = authoritative.get("prior_payload") or authoritative.get("before_image")
                valid = (status == "restored" and remote
                         and remote == str(target.get("remote_id") or "")
                         and observed_digest == _digest(prior))
            elif strategy == "recreate_from_prior_payload":
                prior = authoritative.get("prior_payload") or authoritative.get("before_image")
                valid = (status == "restored" and remote
                         and observed_digest == _digest(prior))
            else:
                valid = False
            if not valid:
                raise Phase5ReadbackMismatch(
                    "rollback receipt does not match its frozen target")
        else:
            disposition = authoritative.get("disposition")
            if disposition == "keep":
                valid = (status == "kept" and remote
                         and observed_digest == authoritative.get("expected_digest"))
            elif disposition == "delete":
                valid = status == "absent" and remote and observed_digest is None
            else:
                valid = (status == "landed" and remote
                         and observed_digest == authoritative.get("expected_digest"))
            if not valid:
                raise Phase5ReadbackMismatch(
                    "apply receipt does not exactly match the contract operation")
        receipt = {
            "op_id": op_id,
            "logical_id": authoritative.get("logical_id"),
            "kind": authoritative.get("kind"),
            "disposition": authoritative.get("disposition"),
            "status": str(status),
            "remote_id": (str(remote_id) if remote_id is not None else None),
            "observed_digest": observed_digest,
            "reconciled_after_error": bool(reconciled_after_error),
        }
        self.service._checkpoint(self, "receipt", receipt=receipt)

    def record_failure(
        self, *, op_id: str | None, code: str, at: str, receipt_digest: str,
    ) -> None:
        """Persist bounded failure evidence without retaining provider output."""
        failure = {
            "op_id": (str(op_id) if op_id is not None else None),
            "code": str(code), "at": str(at),
            "receipt_digest": str(receipt_digest),
        }
        self.service._checkpoint(self, "failure", failure=failure)


class Phase5MutationService:
    """Stateful, crash-safe mutation orchestrator with no embedded credentials."""

    def __init__(
        self, capability_codec: CapabilityCodec, grant_codec: ExecutionGrantCodec,
        root: Path | str, *, grant_kid: str,
        live_writes_enabled: bool = False,
        canary_policy: CanaryPolicy | None = None,
    ):
        self.capability_codec = capability_codec
        self.grant_codec = grant_codec
        self.root = Path(root).resolve()
        self.grant_kid = str(grant_kid)
        self.live_writes_enabled = bool(live_writes_enabled)
        self.canary_policy = canary_policy

    def _safe_paths(self, order_id: str, jti: str) -> tuple[Path, Path]:
        if not _SAFE_ID.fullmatch(order_id) or not _SAFE_ID.fullmatch(jti):
            raise Phase5AuthorizationError("unsafe mutation record identity")
        order_dir = self.root / "attempts" / order_id
        order_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if order_dir.is_symlink() or order_dir.resolve() != order_dir:
            raise Phase5AuthorizationError("unsafe mutation record directory")
        record = order_dir / f"{jti}.json"
        if record.is_symlink():
            raise Phase5AuthorizationError("unsafe mutation record path")
        return record, record.with_suffix(".lock")

    def _athlete_lock(self, tp_athlete_id: str) -> Path:
        digest = hashlib.sha256(str(tp_athlete_id).encode("utf-8")).hexdigest()
        directory = self.root / "leases"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        return directory / f"{digest}.lock"

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _read_record(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Phase5AuthorizationError("mutation execution record is unavailable") from exc
        if not isinstance(value, dict) or value.get("record_type") != EXECUTION_RECORD_TYPE:
            raise Phase5AuthorizationError("mutation execution record is malformed")
        return value

    def exchange(
        self, capability_token: str, contract: Mapping[str, Any], state_path: Path | str,
        *, now: int,
    ) -> str:
        """Exchange a sealed capability for one short-lived fenced grant."""
        try:
            capability = self.capability_codec.verify(capability_token, now=int(now))
        except WorkerAuthorizationError as exc:
            raise Phase5AuthorizationError(str(exc)) from exc
        request_digest = _validate_contract_binding(contract, capability)
        claims = capability.claims
        action = MUTATION_OPERATION_BY_ACTION[claims["action"]]
        if not self.live_writes_enabled:
            if self.canary_policy is None:
                raise Phase5AuthorizationError(
                    "live TrainingPeaks writes are disabled and no canary lane is active")
            self.canary_policy.authorize(contract, claims)
        state_path = Path(state_path)
        record_path, record_lock = self._safe_paths(claims["order_id"], claims["jti"])

        from fulfillment_state import (
            APPLYING, _atomic_write, _history, approval_matches_release, locked_state,
        )

        with open(record_lock, "a+", encoding="utf-8") as attempt_lock:
            fcntl.flock(attempt_lock.fileno(), fcntl.LOCK_EX)
            with locked_state(state_path) as (locked_path, state):
                if state is None:
                    raise Phase5AuthorizationError("authoritative fulfillment state is unavailable")
                if state.get("delivery_platform") != "trainingpeaks":
                    raise Phase5AuthorizationError("delivery platform is not TrainingPeaks")
                rollback_compensation = bool(
                    action == "rollback"
                    and state.get("status") == "CANCELLED"
                    and state.get("compensation_pending")
                    and (state.get("approval") or {}).get("model_seal")
                    == state.get("model_seal")
                    and (state.get("approval") or {}).get("release_manifest_digest")
                    == state.get("release_manifest_digest")
                )
                if not approval_matches_release(state) and not rollback_compensation:
                    raise Phase5AuthorizationError("approval is not bound to the current seal")
                _validate_state_authorization_binding(state, claims)
                if any(
                    item.get("event") == "TP_MUTATION_GRANT_ISSUED"
                    and item.get("authorization_id") == claims["authorization_id"]
                    for item in state.get("history") or []
                    if isinstance(item, dict)
                ):
                    raise Phase5AuthorizationError(
                        "mutation authorization was already exchanged")
                attempt = state.get("application_attempt")
                allowed, reason = mutation_exchange_predicate(
                    capability, state, attempt=attempt,
                    request_digest=request_digest,
                )
                if not allowed:
                    raise Phase5AuthorizationError(reason)
                existing = None
                if record_path.exists():
                    existing = self._read_record(record_path)
                    if (existing.get("request_digest") != request_digest
                            or existing.get("claims_digest") != _digest(claims)):
                        raise Phase5AuthorizationError("mutation jti replay differs")
                    raise Phase5AuthorizationError(
                        "mutation authorization was already exchanged")
                fence = int(state.get("execution_fence") or 0) + 1
                epoch = int(state.get("execution_epoch") or 0)
                prior_landed = copy.deepcopy((attempt or {}).get("landed") or [])
                compensation_targets = copy.deepcopy(
                    (attempt or {}).get("compensation_targets") or [])
                if action == "rollback":
                    derived_targets = _proven_compensation_targets(prior_landed)
                    if compensation_targets and compensation_targets != derived_targets:
                        raise Phase5AuthorizationError(
                            "frozen compensation target set differs from landed work")
                    compensation_targets = compensation_targets or derived_targets
                    if not compensation_targets:
                        raise Phase5AuthorizationError(
                            "rollback has no durably landed compensation target")
                    state["compensation_pending"] = True
                if action == "apply":
                    state["status"] = APPLYING
                state["execution_fence"] = fence
                state["application_attempt"] = {
                    "jti": claims["jti"],
                    "action": action,
                    "request_digest": request_digest,
                    "status": "accepted",
                    "execution_epoch": epoch,
                    "fencing_token": fence,
                    "lease": {
                        "athlete_key_digest": hashlib.sha256(
                            claims["tp_athlete_id"].encode("utf-8")).hexdigest(),
                        "expires_at": _timestamp(int(now) + MAX_GRANT_TTL_SECONDS),
                    },
                    "landed": prior_landed,
                    "intents": copy.deepcopy((attempt or {}).get("intents") or []),
                    "failure": copy.deepcopy((attempt or {}).get("failure")),
                    "compensation_targets": compensation_targets,
                    "compensation_receipts": copy.deepcopy(
                        (attempt or {}).get("compensation_receipts") or []),
                    "receipt_ref": str(record_path),
                }
                _history(
                    state, "TP_MUTATION_GRANT_ISSUED", action=action,
                    capability_jti=claims["jti"], request_digest=request_digest,
                    authorization_id=claims["authorization_id"],
                    actor=claims["actor"],
                    execution_epoch=epoch, fencing_token=fence, reason=reason,
                )
                _atomic_write(locked_path, state)

            record = existing or {
                "record_type": EXECUTION_RECORD_TYPE,
                "status": "accepted", "order_id": claims["order_id"],
                "capability_jti": claims["jti"], "action": action,
                "authorization_id": claims["authorization_id"],
                "actor": claims["actor"], "scope": claims["scope"],
                "approval_digest": claims["approval_digest"],
                "release_manifest_digest": claims["release_manifest_digest"],
                "request_digest": request_digest, "claims_digest": _digest(claims),
                "execution_epoch": epoch, "fencing_token": fence,
                "intents": [], "receipts": [], "failure": None, "result": None,
            }
            record.setdefault("failure", None)
            record.update({"status": "accepted", "execution_epoch": epoch,
                           "fencing_token": fence})
            self._write_json(record_path, record)

        grant_claims = {
            "grant_type": EXECUTION_GRANT_TYPE,
            "order_id": claims["order_id"],
            "tp_athlete_id": claims["tp_athlete_id"],
            "generation_revision": claims["generation_revision"],
            "model_seal": claims["model_seal"], "action": action,
            "audience": self.grant_codec.audience,
            "capability_jti": claims["jti"], "request_digest": request_digest,
            "authorization_id": claims["authorization_id"],
            "actor": claims["actor"], "scope": claims["scope"],
            "approval_digest": claims["approval_digest"],
            "release_manifest_digest": claims["release_manifest_digest"],
            "execution_epoch": epoch, "fencing_token": fence,
            "iat": int(now), "exp": int(now) + MAX_GRANT_TTL_SECONDS,
            "grant_id": uuid.uuid4().hex,
        }
        return self.grant_codec.issue(grant_claims, kid=self.grant_kid)

    def _guard_state(self, context: MutationExecutionContext) -> dict[str, Any]:
        claims = context.grant.claims
        from fulfillment_state import load
        state = load(context.state_path)
        self._assert_state_matches_grant(state, claims)
        return state

    @staticmethod
    def _assert_state_matches_grant(
        state: Mapping[str, Any], claims: Mapping[str, Any],
    ) -> None:
        attempt = state.get("application_attempt") or {}
        if state.get("cancel_requested") and claims.get("action") != "rollback":
            raise Phase5Interrupted("cancellation epoch revoked the execution grant")
        expected = {
            "jti": claims["capability_jti"],
            "request_digest": claims["request_digest"],
            "execution_epoch": claims["execution_epoch"],
            "fencing_token": claims["fencing_token"],
        }
        actual = {
            "jti": attempt.get("jti"),
            "request_digest": attempt.get("request_digest"),
            "execution_epoch": state.get("execution_epoch", 0),
            "fencing_token": state.get("execution_fence", 0),
        }
        if actual != expected:
            raise Phase5AuthorizationError("execution grant is stale or fenced")

    def _checkpoint(self, context: MutationExecutionContext, event: str, **value: Any) -> None:
        self._guard_state(context)
        record_path, record_lock = self._safe_paths(
            context.grant.claims["order_id"], context.grant.claims["capability_jti"])
        from fulfillment_state import _atomic_write, _history, locked_state

        def write_record(*, authoritative_receipts: list[dict[str, Any]] | None = None,
                         failure: Mapping[str, Any] | None = None) -> None:
            with open(record_lock, "a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                record = self._read_record(record_path)
                if event == "intent":
                    operation = value["operation"]
                    if operation["op_id"] not in {
                        item["op_id"] for item in record["intents"]
                    }:
                        record["intents"].append({
                            "op_id": operation["op_id"],
                            "logical_id": operation.get("logical_id"),
                            "kind": operation.get("kind"),
                            "disposition": operation["disposition"],
                            "expected_digest": operation.get("expected_digest"),
                            "status": "persisted-before-mutation",
                        })
                elif event == "receipt":
                    receipt = value["receipt"]
                    operation = next(
                        item for item in context.contract["operations"]
                        if item["op_id"] == receipt["op_id"])
                    intent_ids = {item["op_id"] for item in record["intents"]}
                    if (operation["disposition"] != "keep"
                            and receipt["op_id"] not in intent_ids):
                        raise Phase5AuthorizationError(
                            "mutation receipt has no durable pre-mutation intent")
                    if authoritative_receipts is None:
                        raise Phase5Error("authoritative receipt journal is unavailable")
                    record["receipts"] = copy.deepcopy(authoritative_receipts)
                elif event == "failure":
                    if failure is None:
                        raise Phase5Error("authoritative failure checkpoint is unavailable")
                    record["failure"] = copy.deepcopy(dict(failure))
                else:
                    raise Phase5Error("unknown mutation checkpoint event")
                record["status"] = "running"
                self._write_json(record_path, record)

        # Intents must reach durable storage before any caller can mutate.
        # Landed receipts take the inverse order: state first, so cancellation
        # always sees compensation work even if the receipt-file write crashes.
        if event == "intent":
            write_record()
        authoritative_receipts: list[dict[str, Any]] | None = None
        authoritative_failure: dict[str, Any] | None = None
        with locked_state(context.state_path) as (state_path, state):
            if state is None:
                raise Phase5AuthorizationError("authoritative state disappeared")
            self._assert_state_matches_grant(state, context.grant.claims)
            attempt = state.get("application_attempt") or {}
            if event == "intent":
                op_id = value["operation"]["op_id"]
                if op_id not in {item.get("op_id") for item in attempt.get("intents", [])}:
                    attempt.setdefault("intents", []).append({
                        "op_id": op_id, "status": "persisted-before-mutation"})
            else:
                if event == "receipt":
                    receipt = value["receipt"]
                    if (receipt.get("disposition") != "keep"
                            and receipt.get("op_id") not in {
                                item.get("op_id") for item in attempt.get("intents", [])
                            }):
                        raise Phase5AuthorizationError(
                            "mutation receipt has no durable pre-mutation intent")
                    if context.grant.claims.get("action") == "rollback":
                        target_ids = [
                            item["op_id"]
                            for item in reversed(attempt.get("compensation_targets") or [])
                        ]
                        key = "compensation_receipts"
                    else:
                        target_ids = [item["op_id"] for item in context.contract["operations"]]
                        key = "landed"
                    attempt[key] = _replace_or_append_prefix(
                        attempt.get(key) or [], receipt, target_ids)
                    authoritative_receipts = copy.deepcopy(attempt[key])
                elif event == "failure":
                    failure = value["failure"]
                    if (failure.get("op_id") is not None
                            and failure.get("op_id") not in {
                                item["op_id"] for item in context.contract["operations"]
                            }):
                        raise Phase5AuthorizationError(
                            "failure checkpoint operation is not contract-bound")
                    if (not re.fullmatch(r"[A-Z0-9_]{1,80}", failure.get("code") or "")
                            or not str(failure.get("at") or "").strip()
                            or not _HEX_64.fullmatch(
                                str(failure.get("receipt_digest") or ""))):
                        raise Phase5AuthorizationError(
                            "failure checkpoint metadata is invalid")
                    attempt["failure"] = copy.deepcopy(failure)
                    authoritative_failure = copy.deepcopy(failure)
                else:
                    raise Phase5Error("unknown mutation checkpoint event")
            attempt["status"] = "running"
            state["application_attempt"] = attempt
            checkpoint_value = (
                value.get("operation") or value.get("receipt") or value.get("failure")
            )
            _history(state, "TP_MUTATION_CHECKPOINT", checkpoint=event,
                     op_id=checkpoint_value.get("op_id"))
            _atomic_write(state_path, state)
        if event == "receipt":
            write_record(authoritative_receipts=authoritative_receipts)
        elif event == "failure":
            write_record(failure=authoritative_failure)

    @staticmethod
    def _verify_receipts(contract: Mapping[str, Any], receipts: list[dict[str, Any]]) -> None:
        by_id = {item.get("op_id"): item for item in receipts if isinstance(item, dict)}
        if len(by_id) != len(contract["operations"]):
            raise Phase5ReadbackMismatch("receipt count does not match apply contract")
        for operation in contract["operations"]:
            receipt = by_id.get(operation["op_id"])
            if receipt is None:
                raise Phase5ReadbackMismatch("apply operation has no receipt")
            disposition = operation["disposition"]
            if disposition == "keep":
                if receipt.get("status") != "kept":
                    raise Phase5ReadbackMismatch("keep operation is not verified")
            elif disposition == "delete":
                if receipt.get("status") != "absent":
                    raise Phase5ReadbackMismatch("delete operation remains present")
            else:
                if (receipt.get("status") != "landed"
                        or not str(receipt.get("remote_id") or "").strip()
                        or receipt.get("observed_digest") != operation.get("expected_digest")):
                    raise Phase5ReadbackMismatch("written operation readback mismatches contract")

    @staticmethod
    def _verify_rollback_receipts(
        contract: Mapping[str, Any], targets: list[dict[str, Any]],
        receipts: list[dict[str, Any]],
    ) -> None:
        operation_by_id = {item["op_id"]: item for item in contract["operations"]}
        target_ids = [item.get("op_id") for item in targets]
        if (not target_ids or len(set(target_ids)) != len(target_ids)
                or any(op_id not in operation_by_id for op_id in target_ids)):
            raise Phase5ReadbackMismatch("frozen compensation targets are invalid")
        expected_ids = list(reversed(target_ids))
        if [item.get("op_id") for item in receipts] != expected_ids:
            raise Phase5ReadbackMismatch("rollback receipt set is incomplete")
        by_id = {item["op_id"]: item for item in receipts}
        for op_id in expected_ids:
            operation = operation_by_id[op_id]
            receipt = by_id[op_id]
            strategy = (operation.get("rollback") or {}).get("strategy")
            if strategy == "delete_by_remote_id":
                if (receipt.get("status") != "absent"
                        or receipt.get("remote_id") != targets[target_ids.index(op_id)].get(
                            "remote_id")):
                    raise Phase5ReadbackMismatch("created resource was not removed")
            elif strategy in {
                "restore_prior_payload", "restore_before_image",
            }:
                prior = operation.get("prior_payload") or operation.get("before_image")
                if (receipt.get("status") != "restored"
                        or receipt.get("remote_id") != targets[target_ids.index(op_id)].get(
                            "remote_id")
                        or receipt.get("observed_digest") != _digest(prior)):
                    raise Phase5ReadbackMismatch("prior resource was not restored exactly")
            elif strategy == "recreate_from_prior_payload":
                prior = operation.get("prior_payload") or operation.get("before_image")
                if (receipt.get("status") != "restored"
                        or not str(receipt.get("remote_id") or "").strip()
                        or receipt.get("observed_digest") != _digest(prior)):
                    raise Phase5ReadbackMismatch("prior resource was not recreated exactly")
            else:
                raise Phase5ReadbackMismatch(
                    "operation has no automatically verifiable rollback strategy")

    def execute(
        self, grant_token: str, contract: Mapping[str, Any], state_path: Path | str,
        executor: Callable[[MutationExecutionContext], Mapping[str, Any]], *, now: int,
    ) -> dict[str, Any]:
        """Execute/replay one grant; only exact complete readback reaches APPLIED."""
        grant = self.grant_codec.verify(grant_token, now=int(now))
        claims = grant.claims
        if _digest(contract) != claims["request_digest"]:
            raise Phase5AuthorizationError("execution request does not match grant")
        record_path, record_lock = self._safe_paths(
            claims["order_id"], claims["capability_jti"])
        athlete_lock_path = self._athlete_lock(claims["tp_athlete_id"])
        context = MutationExecutionContext(
            self, grant, Path(state_path), record_path, contract, int(now))

        with open(athlete_lock_path, "a+", encoding="utf-8") as athlete_lock:
            fcntl.flock(athlete_lock.fileno(), fcntl.LOCK_EX)
            self._guard_state(context)
            with open(record_lock, "a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                existing = self._read_record(record_path)
                if existing.get("status") == "succeeded":
                    return copy.deepcopy(existing["result"])
                existing["status"] = "running"
                self._write_json(record_path, existing)
            try:
                result = dict(executor(context))
                self._guard_state(context)
                state = self._guard_state(context)
                attempt = state.get("application_attempt") or {}
                if claims["action"] == "rollback":
                    self._verify_rollback_receipts(
                        contract, attempt.get("compensation_targets") or [],
                        attempt.get("compensation_receipts") or [])
                    if result.get("rollback_verified") is not True:
                        raise Phase5ReadbackMismatch(
                            "executor did not attest exact rollback readback")
                else:
                    self._verify_receipts(contract, attempt.get("landed") or [])
                    if result.get("readback_verified") is not True:
                        raise Phase5ReadbackMismatch("executor did not attest exact readback")
            except Phase5Interrupted:
                self._acknowledge_quiescence(Path(state_path))
                raise
            except Exception as exc:
                with open(record_lock, "a+", encoding="utf-8") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    record = self._read_record(record_path)
                    record["status"] = (
                        "running" if isinstance(exc, Phase5Interrupted) else "failed")
                    record["result"] = {"error_type": type(exc).__name__}
                    self._write_json(record_path, record)
                raise

            from fulfillment_state import (
                APPLIED, APPROVED, CANCELLED, _atomic_write, _history, locked_state,
            )
            with locked_state(state_path) as (locked_path, state):
                if state is None:
                    raise Phase5AuthorizationError("authoritative state disappeared")
                self._assert_state_matches_grant(state, claims)
                attempt = state.get("application_attempt") or {}
                receipts = copy.deepcopy(
                    attempt.get("compensation_receipts") or []
                    if claims["action"] == "rollback"
                    else attempt.get("landed") or [])
                if claims["action"] == "rollback":
                    state["status"] = (
                        CANCELLED if state.get("cancel_requested") else APPROVED)
                    state["compensation_pending"] = False
                    if isinstance(state.get("cancellation"), dict):
                        state["cancellation"]["worker_stop_acknowledged"] = True
                        state["cancellation"]["worker_stop_basis"] = (
                            "rollback readback verified")
                    state["application"] = None
                elif claims["action"] == "apply":
                    state["status"] = APPLIED
                else:
                    state["status"] = APPLIED
                state["application_attempt"]["status"] = "succeeded"
                if claims["action"] == "apply":
                    state["application"] = {
                        "at": _timestamp(int(now)), "platform": "trainingpeaks",
                        "receipt_type": EXECUTION_RECEIPT_TYPE,
                        "receipt_digest": _digest(receipts),
                        "operation_count": len(receipts),
                    }
                elif claims["action"] == "verify":
                    state["verification"] = {
                        "at": _timestamp(int(now)),
                        "receipt_digest": _digest(receipts),
                        "operation_count": len(receipts),
                    }
                _history(
                    state,
                    ("TP_ROLLBACK_VERIFIED" if claims["action"] == "rollback"
                     else "TP_APPLICATION_VERIFIED"),
                    receipt_digest=_digest(receipts), operation_count=len(receipts),
                )
                _atomic_write(locked_path, state)
            final = {
                "receipt_type": EXECUTION_RECEIPT_TYPE,
                "status": (
                    "rolled_back" if claims["action"] == "rollback"
                    else "verified" if claims["action"] == "verify"
                    else "applied"),
                "operation_count": len(receipts),
                "receipt_digest": _digest(receipts), "receipts": receipts,
            }
            with open(record_lock, "a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                record = self._read_record(record_path)
                record["status"] = "succeeded"
                record["result"] = final
                self._write_json(record_path, record)
            return copy.deepcopy(final)

    @staticmethod
    def _acknowledge_quiescence(state_path: Path) -> None:
        from fulfillment_state import _atomic_write, _history, locked_state
        with locked_state(state_path) as (locked_path, state):
            if state is None:
                raise Phase5AuthorizationError("authoritative state disappeared")
            cancellation = state.get("cancellation")
            if isinstance(cancellation, dict):
                cancellation["worker_stop_acknowledged"] = True
                cancellation["worker_stop_basis"] = "worker observed revoked execution epoch"
                state["cancellation"] = cancellation
                _history(state, "TP_WORKER_QUIESCED")
                _atomic_write(locked_path, state)


def request_application_cancellation(
    state_path: Path | str, *, actor: str, reason: str,
) -> dict[str, Any]:
    """Revoke the epoch immediately; landed writes require compensation."""
    from fulfillment_state import (
        CANCELLED, _atomic_write, _history, locked_state,
    )
    if not str(actor).strip() or not str(reason).strip():
        raise Phase5AuthorizationError("cancellation actor and reason are required")
    with locked_state(state_path) as (locked_path, state):
        if state is None:
            raise Phase5AuthorizationError("authoritative state is unavailable")
        attempt = state.get("application_attempt") or {}
        landed = attempt.get("landed") or []
        targets = _proven_compensation_targets(landed)
        frozen = attempt.get("compensation_targets") or []
        if frozen and frozen != targets:
            raise Phase5AuthorizationError(
                "frozen compensation target set differs from landed work")
        attempt["compensation_targets"] = copy.deepcopy(frozen or targets)
        attempt.setdefault("compensation_receipts", [])
        state["application_attempt"] = attempt
        state["cancel_requested"] = True
        state["execution_epoch"] = int(state.get("execution_epoch") or 0) + 1
        state["status"] = CANCELLED
        state["compensation_pending"] = bool(targets)
        state["cancellation"] = {
            "requested_by": str(actor).strip(), "at": _timestamp(
                int(datetime.now(timezone.utc).timestamp())),
            "reason": str(reason).strip(),
            "worker_stop_acknowledged": False,
            "worker_stop_basis": None,
        }
        _history(state, "TP_APPLICATION_CANCEL_REQUESTED",
                 compensation_pending=bool(targets))
        _atomic_write(locked_path, state)
        return copy.deepcopy(state)


def compile_browser_dry_run(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Generate a credential-free browser plan; this function performs zero I/O."""
    operations = []
    for operation in contract.get("operations") or []:
        operations.append({
            "op_id": operation.get("op_id"),
            "kind": operation.get("kind"),
            "disposition": operation.get("disposition"),
            "would_mutate": operation.get("disposition") != "keep",
            "requires_intent_checkpoint": operation.get("disposition") != "keep",
            "requires_exact_readback": True,
        })
    return {
        "dry_run_type": "trainingpeaks_browser_transport_dry_run/v1",
        "contract_digest": _digest(contract),
        "external_writes_performed": False,
        "operation_count": len(operations),
        "operations": operations,
    }
