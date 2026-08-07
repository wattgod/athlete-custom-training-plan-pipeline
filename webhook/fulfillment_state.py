"""Durable, order-scoped fulfillment state and transitional release sealing.

The webhook and pipeline both import this module.  It is deliberately free of
Flask/project imports so state validation, migration, blocker policy, and seal
verification have one owner.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, Iterator, Optional, Tuple

SCHEMA_VERSION = 2
GENERATED = "GENERATED"
BLOCKED_REVIEW = "BLOCKED_REVIEW"
APPROVED = "APPROVED"
APPLYING = "APPLYING"
APPLIED = "APPLIED"
APPLIED_ATTESTED = "APPLIED_ATTESTED"
CONFIRMED = "CONFIRMED"
CANCELLED = "CANCELLED"
VALID_STATUSES = {
    GENERATED, BLOCKED_REVIEW, APPROVED, APPLIED, CONFIRMED,
}
DELIVERY_PLATFORMS = {"trainingpeaks", "endure", "manual"}
RELEASE_STATUSES = {APPROVED, APPLIED, CONFIRMED}
TRANSITIONAL_SEAL_VERSION = "transitional_artifact_bytes/v1"

# Server-owned policy.  Structural/quality rules not named here are waivable;
# the non-waivable set is closed and cannot be weakened by caller input.
NON_WAIVABLE_RULES = {
    "FTP_ESTIMATED",
    "COURSE_UNRESOLVED",
    "STATE_UNAVAILABLE",
    "VALIDATOR_CRASH",
    "POST_RENDER_VALIDATOR_CRASH",
    "SEAL_MISMATCH",
}


class FulfillmentStateError(ValueError):
    """A malformed state or an invalid operator request."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    """Canonical serialization used by every Phase 1 digest."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _state_path(path: os.PathLike[str] | str) -> Path:
    return Path(path)


def blocker_is_waivable(rule_id: str) -> bool:
    rule_id = str(rule_id or "").strip().upper()
    return not (
        rule_id in NON_WAIVABLE_RULES
        or rule_id.startswith("VALIDATOR_CRASH")
        or rule_id.startswith("SEAL_MISMATCH")
    )


def _validate_issue(issue: Dict[str, Any], *, source: str = "") -> Dict[str, Any]:
    required = ("id", "source", "severity", "message")
    if source:
        issue = {**(issue or {}), "source": source}
    if not isinstance(issue, dict) or any(
        not str(issue.get(key, "")).strip() for key in required
    ):
        raise FulfillmentStateError(
            "blocking issue requires id, source, severity, and message"
        )
    normalized = {key: str(issue[key]).strip() for key in required}
    normalized["waivable"] = blocker_is_waivable(normalized["id"])
    return normalized


def _validate_confirmation(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict) or not str(item.get("id", "")).strip():
        raise FulfillmentStateError("required confirmation requires id")
    return {
        "id": str(item["id"]).strip(),
        "source": str(item.get("source", "post_render")).strip(),
        "message": str(item.get("message", "")).strip(),
    }


def _validate_state(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        raise FulfillmentStateError("fulfillment state must be an object")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise FulfillmentStateError("unsupported fulfillment state schema")
    if not str(state.get("athlete_id", "")).strip():
        raise FulfillmentStateError("fulfillment state has no athlete_id")
    if not str(state.get("order_id", "")).strip():
        raise FulfillmentStateError("fulfillment state has no order_id")
    if state.get("delivery_platform") not in DELIVERY_PLATFORMS:
        raise FulfillmentStateError("invalid delivery_platform")
    if state.get("status") not in VALID_STATUSES:
        raise FulfillmentStateError("unknown fulfillment status")
    if not isinstance(state.get("generation_revision"), int) or state["generation_revision"] < 1:
        raise FulfillmentStateError("invalid generation revision")
    issues = state.get("blocking_issues")
    if not isinstance(issues, list):
        raise FulfillmentStateError("blocking_issues must be a list")
    state["blocking_issues"] = [_validate_issue(issue) for issue in issues]
    confirmations = state.get("required_confirmations", [])
    if not isinstance(confirmations, list):
        raise FulfillmentStateError("required_confirmations must be a list")
    state["required_confirmations"] = [
        _validate_confirmation(item) for item in confirmations
    ]
    for key in ("approval", "waiver", "application", "confirmation"):
        if key not in state:
            raise FulfillmentStateError(f"fulfillment state missing {key}")
    if not isinstance(state.get("history"), list) or not state.get("updated_at"):
        raise FulfillmentStateError("fulfillment state missing history or updated_at")
    if "release_manifest" not in state or "model_seal" not in state:
        raise FulfillmentStateError("fulfillment state missing release seal fields")
    return state


def _atomic_write(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


@contextlib.contextmanager
def locked_state(
    path: os.PathLike[str] | str,
) -> Iterator[Tuple[Path, Optional[Dict[str, Any]]]]:
    """Lock one order state; malformed/missing/legacy state yields ``None``."""
    state_path = _state_path(path)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            try:
                raw = json.loads(state_path.read_text(encoding="utf-8"))
                state = _validate_state(raw)
            except (OSError, json.JSONDecodeError, FulfillmentStateError):
                state = None
            yield state_path, state
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load(path: os.PathLike[str] | str) -> Dict[str, Any]:
    with locked_state(path) as (_, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        return copy.deepcopy(state)


def _history(state: Dict[str, Any], event: str, **details: Any) -> None:
    state["history"].append({
        "at": now_iso(),
        "event": event,
        "order_id": state["order_id"],
        "generation_revision": state["generation_revision"],
        **details,
    })
    state["updated_at"] = now_iso()


def _opaque_manual_order_id(prefix: str = "manual") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def write_generation(
    path: os.PathLike[str] | str,
    athlete_id: str,
    blocking_issues: Optional[list[Dict[str, Any]]] = None,
    *,
    order_id: str = "",
    delivery_platform: str = "manual",
    required_confirmations: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Start a revision while preserving immutable order identity."""
    issues = [_validate_issue(issue) for issue in (blocking_issues or [])]
    confirmations = [
        _validate_confirmation(item) for item in (required_confirmations or [])
    ]
    delivery_platform = str(delivery_platform or "manual").strip().lower()
    if delivery_platform not in DELIVERY_PLATFORMS:
        raise FulfillmentStateError("invalid delivery_platform")

    with locked_state(path) as (state_path, previous):
        if previous is None and state_path.exists():
            try:
                raw = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = None
            if isinstance(raw, dict) and raw.get("schema_version") == 1:
                raise FulfillmentStateError("legacy v1 state requires quarantine migration")
            if raw is not None:
                raise FulfillmentStateError("refusing to overwrite malformed fulfillment state")

        if previous:
            immutable_order_id = previous["order_id"]
            immutable_platform = previous["delivery_platform"]
            if order_id and order_id != immutable_order_id:
                raise FulfillmentStateError("order_id is immutable")
            if delivery_platform != immutable_platform:
                raise FulfillmentStateError("delivery_platform is immutable")
            order_id = immutable_order_id
            delivery_platform = immutable_platform
        else:
            order_id = str(order_id or _opaque_manual_order_id()).strip()

        revision = (previous.get("generation_revision", 0) if previous else 0) + 1
        history = list(previous.get("history", []) if previous else [])
        state = {
            "schema_version": SCHEMA_VERSION,
            "order_id": order_id,
            "athlete_id": str(athlete_id).strip(),
            "delivery_platform": delivery_platform,
            "generation_revision": revision,
            "status": BLOCKED_REVIEW if issues else GENERATED,
            "blocking_issues": sorted(issues, key=lambda item: item["id"]),
            "required_confirmations": sorted(confirmations, key=lambda item: item["id"]),
            "approval": None,
            "waiver": None,
            "application": None,
            "confirmation": None,
            "model_seal": None,
            "release_manifest_digest": None,
            "release_manifest": None,
            "seal_version": None,
            "legacy": False,
            "history": history,
            "updated_at": now_iso(),
        }
        if previous:
            _history(
                state, "REGENERATED", prior_status=previous.get("status"),
                prior_revision=previous.get("generation_revision"),
            )
        _history(
            state, "GENERATED", status=state["status"],
            blocker_ids=[item["id"] for item in state["blocking_issues"]],
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def set_generation_blockers(
    path: os.PathLike[str] | str,
    blocking_issues: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compatibility replace operation; new callers use namespaced merge."""
    issues = [_validate_issue(issue) for issue in blocking_issues]
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["status"] not in (GENERATED, BLOCKED_REVIEW):
            raise FulfillmentStateError("cannot alter blockers after review begins")
        state["blocking_issues"] = sorted(issues, key=lambda item: item["id"])
        state["status"] = BLOCKED_REVIEW if issues else GENERATED
        _history(state, "BLOCKERS_REPLACED", blocker_ids=[item["id"] for item in issues])
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def merge_generation_blockers(
    path: os.PathLike[str] | str,
    expected_revision: int,
    source: str,
    issues: list[Dict[str, Any]],
    *,
    required_confirmations: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Replace one source namespace without erasing other blockers."""
    source = str(source or "").strip()
    if not source:
        raise FulfillmentStateError("blocker source is required")
    incoming = [_validate_issue(issue, source=source) for issue in issues]
    confirmations = None
    if required_confirmations is not None:
        confirmations = [
            _validate_confirmation({**item, "source": source})
            for item in required_confirmations
        ]
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if state["status"] not in (GENERATED, BLOCKED_REVIEW):
            raise FulfillmentStateError("cannot alter blockers after review begins")
        preserved = [
            issue for issue in state["blocking_issues"] if issue["source"] != source
        ]
        state["blocking_issues"] = sorted(
            preserved + incoming, key=lambda item: item["id"]
        )
        if confirmations is not None:
            preserved_confirmations = [
                item for item in state["required_confirmations"]
                if item.get("source") != source
            ]
            state["required_confirmations"] = sorted(
                preserved_confirmations + confirmations,
                key=lambda item: item["id"],
            )
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _history(
            state, "BLOCKERS_MERGED", source=source,
            blocker_ids=[item["id"] for item in incoming],
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def _artifact_records(artifact_root: Path) -> list[Dict[str, Any]]:
    excluded_names = {
        "fulfillment_status.json",
        "release_manifest.json",
    }
    records = []
    for path in sorted(artifact_root.rglob("*")):
        if not path.is_file() or path.name in excluded_names:
            continue
        if path.name.endswith((".lock", ".tmp")) or path.name.startswith(".release_manifest."):
            continue
        data = path.read_bytes()
        records.append({
            "path": path.relative_to(artifact_root).as_posix(),
            "kind": "file",
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        })
    return records


def finalize_transitional_release(
    path: os.PathLike[str] | str,
    artifact_root: os.PathLike[str] | str,
    *,
    expected_revision: int,
) -> Dict[str, Any]:
    """Seal every eager artifact byte and persist the immutable manifest."""
    artifact_root = Path(artifact_root).resolve()
    if not artifact_root.is_dir():
        raise FulfillmentStateError("artifact root is missing")
    records = _artifact_records(artifact_root)
    if not records:
        raise FulfillmentStateError("cannot seal an empty artifact set")
    model_seal = canonical_digest(records)
    manifest = {
        "seal_version": TRANSITIONAL_SEAL_VERSION,
        "model_seal": model_seal,
        "artifacts": records,
    }
    manifest_path = artifact_root / "release_manifest.json"

    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if state.get("model_seal"):
            raise FulfillmentStateError("release is already sealed")
        _atomic_write(manifest_path, manifest)
        # Verify the exact bytes we just made durable before granting authority.
        persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        if persisted != manifest:
            raise FulfillmentStateError("release manifest verification failed")
        state["model_seal"] = model_seal
        state["release_manifest_digest"] = canonical_digest(records)
        state["release_manifest"] = str(manifest_path)
        state["seal_version"] = TRANSITIONAL_SEAL_VERSION
        _history(
            state, "RELEASE_SEALED", model_seal=model_seal,
            release_manifest_digest=state["release_manifest_digest"],
            artifact_count=len(records),
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def verify_release_manifest(
    state_or_path: Dict[str, Any] | os.PathLike[str] | str,
    artifact_root: os.PathLike[str] | str,
) -> Dict[str, Any]:
    """Verify manifest binding and every artifact; mismatch is fatal."""
    state = state_or_path if isinstance(state_or_path, dict) else load(state_or_path)
    if not state.get("model_seal") or not state.get("release_manifest_digest"):
        raise FulfillmentStateError("release is not sealed")
    manifest_path = Path(state.get("release_manifest") or "")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FulfillmentStateError("release manifest unavailable") from exc
    records = manifest.get("artifacts")
    if not isinstance(records, list) or not records:
        raise FulfillmentStateError("release manifest has no artifacts")
    if (
        manifest.get("seal_version") != TRANSITIONAL_SEAL_VERSION
        or canonical_digest(records) != state["model_seal"]
        or canonical_digest(records) != state["release_manifest_digest"]
    ):
        raise FulfillmentStateError("release manifest seal mismatch")
    root = Path(artifact_root).resolve()
    for record in records:
        candidate = (root / record["path"]).resolve()
        if root not in candidate.parents:
            raise FulfillmentStateError("release manifest path escapes artifact root")
        try:
            data = candidate.read_bytes()
        except OSError as exc:
            raise FulfillmentStateError(
                f"sealed artifact unavailable: {record['path']}"
            ) from exc
        if (
            len(data) != record["bytes"]
            or hashlib.sha256(data).hexdigest() != record["sha256"]
        ):
            raise FulfillmentStateError(
                f"sealed artifact mismatch: {record['path']}"
            )
    return manifest


def approval_matches_release(state: Dict[str, Any]) -> bool:
    """Return whether current authority is bound to the current sealed bytes."""
    approval = state.get("approval") or {}
    return bool(
        not state.get("legacy")
        and state.get("status") in RELEASE_STATUSES
        and approval.get("model_seal") == state.get("model_seal")
        and approval.get("release_manifest_digest")
        == state.get("release_manifest_digest")
    )


def _seal_mismatch_issue(message: str) -> Dict[str, Any]:
    return _validate_issue({
        "id": "SEAL_MISMATCH",
        "source": "seal_verification",
        "severity": "CRITICAL",
        "message": f"Release seal verification failed: {message}",
    })


def _materialize_seal_mismatch(
    state: Dict[str, Any], message: str,
) -> None:
    preserved = [
        issue for issue in state["blocking_issues"]
        if issue["id"] != "SEAL_MISMATCH"
    ]
    state["blocking_issues"] = sorted(
        preserved + [_seal_mismatch_issue(message)], key=lambda item: item["id"])
    state["status"] = BLOCKED_REVIEW
    _history(state, "SEAL_MISMATCH", message=message)


def record_seal_mismatch(
    path: os.PathLike[str] | str, message: str,
) -> Dict[str, Any]:
    """Revoke release authority and durably merge the fatal seal blocker."""
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        _materialize_seal_mismatch(state, str(message))
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def open_verified_release_artifact(
    state_or_path: Dict[str, Any] | os.PathLike[str] | str,
    artifact_root: os.PathLike[str] | str,
    relative_path: str,
    *,
    require_approval: bool = True,
) -> BinaryIO:
    """Verify and return the exact open handle that the caller must serve.

    Keeping the verified descriptor open closes the former hash-then-reopen
    race in the Flask download path.
    """
    state = state_or_path if isinstance(state_or_path, dict) else load(state_or_path)
    if require_approval and not approval_matches_release(state):
        raise FulfillmentStateError("release approval does not match the current seal")
    manifest_path = Path(state.get("release_manifest") or "")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FulfillmentStateError("release manifest unavailable") from exc
    records = manifest.get("artifacts")
    if (
        not isinstance(records, list)
        or not records
        or manifest.get("seal_version") != TRANSITIONAL_SEAL_VERSION
        or canonical_digest(records) != state.get("model_seal")
        or canonical_digest(records) != state.get("release_manifest_digest")
    ):
        raise FulfillmentStateError("release manifest seal mismatch")

    root = Path(artifact_root).resolve()
    served: Optional[BinaryIO] = None
    try:
        for record in records:
            candidate = (root / str(record.get("path") or "")).resolve()
            if root not in candidate.parents:
                raise FulfillmentStateError("release manifest path escapes artifact root")
            handle = candidate.open("rb")
            data = handle.read()
            if (
                len(data) != record.get("bytes")
                or hashlib.sha256(data).hexdigest() != record.get("sha256")
            ):
                handle.close()
                raise FulfillmentStateError(
                    f"sealed artifact mismatch: {record.get('path')}"
                )
            if record.get("path") == relative_path:
                handle.seek(0)
                served = handle
            else:
                handle.close()
        if served is None:
            raise FulfillmentStateError(
                "artifact is not in the approved release manifest")
        return served
    except Exception:
        if served is not None:
            served.close()
        raise


def verify_release_artifact(
    state_or_path: Dict[str, Any] | os.PathLike[str] | str,
    artifact_root: os.PathLike[str] | str,
    relative_path: str,
) -> Path:
    manifest = verify_release_manifest(state_or_path, artifact_root)
    record = next(
        (item for item in manifest["artifacts"] if item["path"] == relative_path),
        None,
    )
    if record is None:
        raise FulfillmentStateError("artifact is not in the approved release manifest")
    return Path(artifact_root) / relative_path


def transition(
    path: os.PathLike[str] | str,
    to: str,
    coach: str = "",
    *,
    waiver: Optional[Dict[str, Any]] = None,
    platform: str = "",
    evidence: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply an authenticated operator transition and persist it atomically."""
    if to not in VALID_STATUSES:
        raise FulfillmentStateError("unknown destination status")
    if not str(coach).strip():
        raise FulfillmentStateError("coach is required")
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state.get("legacy"):
            raise FulfillmentStateError(
                "legacy order is quarantined and must be regenerated after manual binding"
            )
        current = state["status"]
        if to == CONFIRMED and current == CONFIRMED:
            return copy.deepcopy(state)
        if to == APPROVED:
            if not state.get("model_seal") or not state.get("release_manifest_digest"):
                raise FulfillmentStateError("approval requires a sealed release")
            if current == GENERATED:
                pass
            elif current == BLOCKED_REVIEW:
                if not isinstance(waiver, dict):
                    raise FulfillmentStateError("complete waiver is required for blocked review")
                rule_ids = waiver.get("rule_ids")
                reason = str(waiver.get("reason", "")).strip()
                blockers = {issue["id"] for issue in state["blocking_issues"]}
                if not isinstance(rule_ids, list) or not reason or set(rule_ids) != blockers:
                    raise FulfillmentStateError("waiver must cover every blocking issue exactly")
                non_waivable = sorted(
                    issue["id"] for issue in state["blocking_issues"]
                    if not issue["waivable"]
                )
                if non_waivable:
                    raise FulfillmentStateError(
                        "non-waivable blockers require regeneration: "
                        + ", ".join(non_waivable)
                    )
                state["waiver"] = {
                    "coach": coach.strip(), "at": now_iso(),
                    "rule_ids": sorted(blockers), "reason": reason,
                }
            else:
                raise FulfillmentStateError(f"illegal transition {current} -> {to}")
            if state.get("required_confirmations"):
                raise FulfillmentStateError("required confirmations are unresolved")
            artifact_root = Path(str(state.get("release_manifest") or "")).parent
            try:
                verify_release_manifest(state, artifact_root)
            except FulfillmentStateError as exc:
                _materialize_seal_mismatch(state, str(exc))
                _atomic_write(state_path, state)
                raise FulfillmentStateError(
                    f"approval refused: {exc}"
                ) from exc
            state["approval"] = {
                "coach": coach.strip(),
                "at": now_iso(),
                "model_seal": state["model_seal"],
                "release_manifest_digest": state["release_manifest_digest"],
            }
        elif to == APPLIED:
            if current != APPROVED:
                raise FulfillmentStateError("application requires APPROVED status")
            if not str(platform).strip() or not str(evidence).strip():
                raise FulfillmentStateError("platform and nonempty evidence are required")
            if platform.strip() != state["delivery_platform"]:
                raise FulfillmentStateError(
                    "application platform does not match immutable delivery_platform"
                )
            artifact_root = Path(str(state.get("release_manifest") or "")).parent
            try:
                verify_release_manifest(state, artifact_root)
            except FulfillmentStateError as exc:
                _materialize_seal_mismatch(state, str(exc))
                _atomic_write(state_path, state)
                raise FulfillmentStateError(
                    f"application refused: {exc}"
                ) from exc
            state["application"] = {
                "coach": coach.strip(), "at": now_iso(),
                "platform": platform.strip(), "evidence": evidence.strip(),
            }
        else:
            raise FulfillmentStateError(f"illegal transition {current} -> {to}")
        state["status"] = to
        _history(
            state, "TRANSITION", from_status=current, to_status=to,
            coach=coach.strip(), **(metadata or {}),
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def confirm_after_send(
    path: os.PathLike[str] | str,
    send: Callable[[], bool],
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Retained Phase 1 exactly-once send primitive; Phase 5 changes it."""
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state.get("legacy"):
            raise FulfillmentStateError(
                "legacy order is quarantined and must be regenerated before confirmation"
            )
        if state["status"] == CONFIRMED:
            return "idempotent", copy.deepcopy(state)
        if state["status"] != APPLIED:
            raise FulfillmentStateError("confirmation requires APPLIED status")
        if not send():
            raise RuntimeError("confirmation email failed")
        prior = state["status"]
        state["status"] = CONFIRMED
        state["confirmation"] = {"at": now_iso(), **(metadata or {})}
        _history(state, "TRANSITION", from_status=prior, to_status=CONFIRMED)
        _atomic_write(state_path, state)
        return "confirmed", copy.deepcopy(state)


def migrate_v1_to_quarantine(
    old_path: os.PathLike[str] | str,
    destination_root: os.PathLike[str] | str,
    *,
    ledger_candidates: Optional[list[str]] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Move one v1 file write-new -> verify -> tombstone-old, fail closed."""
    old_path = Path(old_path)
    try:
        original = json.loads(old_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FulfillmentStateError("legacy state is unreadable") from exc
    if original.get("schema_version") != 1:
        raise FulfillmentStateError("only schema v1 states can be migrated")
    legacy_order_id = _opaque_manual_order_id("legacy")
    destination = Path(destination_root) / legacy_order_id / "fulfillment_status.json"
    state = {
        "schema_version": SCHEMA_VERSION,
        "order_id": legacy_order_id,
        "athlete_id": str(original.get("athlete_id") or "legacy-order"),
        "delivery_platform": "manual",
        "generation_revision": max(1, int(original.get("generation_revision") or 1)),
        "status": original.get("status") if original.get("status") in VALID_STATUSES else BLOCKED_REVIEW,
        "blocking_issues": [_validate_issue({
            "id": "STATE_UNAVAILABLE",
            "source": "v1_migration",
            "severity": "CRITICAL",
            "message": "Legacy state is quarantined until a coach binds its ledger order.",
        })],
        "required_confirmations": [],
        "approval": original.get("approval"),
        "waiver": original.get("waiver"),
        "application": original.get("application"),
        "confirmation": original.get("confirmation"),
        "model_seal": None,
        "release_manifest_digest": None,
        "release_manifest": None,
        "seal_version": None,
        "legacy": True,
        "legacy_binding": None,
        "legacy_candidates": sorted(set(ledger_candidates or [])),
        "legacy_original_evidence": original,
        "history": list(original.get("history") or []),
        "updated_at": now_iso(),
    }
    _history(state, "LEGACY_QUARANTINED", source_path=str(old_path))
    _atomic_write(destination, state)
    verified = load(destination)
    if verified["legacy_original_evidence"] != original:
        raise FulfillmentStateError("legacy migration verification failed")
    tombstone = {
        "schema_version": "tombstone/v1",
        "migrated_to": str(destination),
        "legacy_order_id": legacy_order_id,
        "at": now_iso(),
    }
    _atomic_write(old_path, tombstone)
    return destination, verified


def bind_legacy_order(
    path: os.PathLike[str] | str,
    ledger_order_id: str,
    coach: str,
) -> Dict[str, Any]:
    """Authenticated manual binding required before any quarantined action."""
    if not str(ledger_order_id).strip() or not str(coach).strip():
        raise FulfillmentStateError("ledger order id and coach are required")
    with locked_state(path) as (state_path, state):
        if state is None or not state.get("legacy"):
            raise FulfillmentStateError("state is not a legacy quarantine")
        candidates = set(state.get("legacy_candidates") or [])
        if candidates and ledger_order_id not in candidates:
            raise FulfillmentStateError("ledger order is not a recorded candidate")
        state["legacy_binding"] = {
            "ledger_order_id": ledger_order_id,
            "coach": coach.strip(),
            "at": now_iso(),
        }
        _history(
            state, "LEGACY_MANUALLY_BOUND", ledger_order_id=ledger_order_id,
            coach=coach.strip(),
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)
