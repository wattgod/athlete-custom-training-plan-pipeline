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
import hmac
import json
import os
import re
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
    GENERATED, BLOCKED_REVIEW, APPROVED, APPLYING, APPLIED,
    APPLIED_ATTESTED, CONFIRMED, CANCELLED,
}
DELIVERY_PLATFORMS = {"trainingpeaks", "endure", "manual"}
PHASE1_APPLIED_PLATFORMS = {"trainingpeaks", "manual"}
RELEASE_STATUSES = {
    APPROVED, APPLYING, APPLIED, APPLIED_ATTESTED, CONFIRMED,
}
TRANSITIONAL_SEAL_VERSION = "transitional_artifact_bytes/v1"
CANONICAL_SEAL_VERSION = "canonical_model_apply_contract/v1"
REVIEW_CATALOG_VERSION = "review_catalog/v1"
APPROVAL_SNAPSHOT_VERSION = "approval_snapshot/v2"
REVIEW_ITEM_TYPES = {
    "blocker", "required_confirmation", "soft_confirmation", "verified_fact",
}
REVIEW_SENSITIVITIES = {"public", "internal", "personal", "sensitive"}
SENSITIVE_REDACTION = "[REDACTED — open authenticated review]"

# Server-owned policy.  Structural/quality rules not named here are waivable;
# the non-waivable set is closed and cannot be weakened by caller input.
NON_WAIVABLE_RULES = {
    "FTP_ESTIMATED",
    "COURSE_UNRESOLVED",
    "STATE_UNAVAILABLE",
    "VALIDATOR_CRASH",
    "POST_RENDER_VALIDATOR_CRASH",
    "SEAL_MISMATCH",
    "APPLY_CONTRACT_INVALID",
    "ATHLETE_UNLINKED",
    "ATHLETE_NO_ACCOUNT",
    "ATHLETE_IDENTITY_UNRESOLVED",
    "D2_REGENERATION_REQUIRED",
    "D2_CANNOT_RESOLVE",
    "D2_INSPECTION_FAILED",
}

NON_WAIVABLE_REMEDIATIONS = {
    "FTP_ESTIMATED": "Supply a measured FTP and regenerate this revision.",
    "COURSE_UNRESOLVED": (
        "Regenerate in athlete-facts-only mode or resolve the exact course."
    ),
    "STATE_UNAVAILABLE": "Repair durable state and regenerate the order.",
    "VALIDATOR_CRASH": "Repair the validator failure and regenerate the order.",
    "POST_RENDER_VALIDATOR_CRASH": (
        "Repair the post-render validator failure and regenerate the order."
    ),
    "SEAL_MISMATCH": "Regenerate from immutable source artifacts and review again.",
    "APPLY_CONTRACT_INVALID": "Repair the offline contract and regenerate this revision.",
    "ATHLETE_UNLINKED": "Bind a currently coached platform account or use manual delivery.",
    "ATHLETE_NO_ACCOUNT": "Bind the athlete's platform account or use manual delivery.",
    "ATHLETE_IDENTITY_UNRESOLVED": "Select and bind exactly one platform account.",
    "D2_REGENERATION_REQUIRED": "Finish regeneration and review the new sealed revision.",
    "D2_CANNOT_RESOLVE": "Correct the account or intake inconsistency before approval.",
    "D2_INSPECTION_FAILED": "Repair the read-only worker inspection and retry.",
}

_REVIEW_METADATA_KEYS = (
    "review_value", "display_unit", "basis", "sensitivity",
    "resolution_choices", "resolved_resolution",
)


class FulfillmentStateError(ValueError):
    """A malformed state or an invalid operator request."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    """Canonical serialization used by every Phase 1 digest."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def review_catalog_digest(
    state_or_items: Dict[str, Any] | list[Dict[str, Any]],
) -> str:
    """Identify the exact versioned catalog presented for one approval."""
    items = (
        state_or_items.get("review_items") or []
        if isinstance(state_or_items, dict) else state_or_items
    )
    return canonical_digest({
        "version": REVIEW_CATALOG_VERSION,
        "items": items,
    })


def external_state_projection(value: Any) -> Any:
    """One recursive redaction boundary for every non-review state surface.

    Approval snapshots and superseded evidence intentionally copy complete
    review items. A shallow live-list helper therefore leaks the archived
    typed value after approval. This projection walks the entire response and
    applies the sensitivity policy wherever that evidence is nested.
    """
    def project(nested: Any, path: tuple[str, ...]) -> Any:
        if isinstance(nested, list):
            return [project(item, path) for item in nested]
        if not isinstance(nested, dict):
            return copy.deepcopy(nested)
        result = copy.deepcopy(nested)
        sensitive_object = result.get("sensitivity") == "sensitive"
        for key, child in list(result.items()):
            child_path = path + (str(key),)
            audit_secret = (
                key == "credential"
                or (key == "evidence" and "application" in path)
                or (key == "reason" and "waiver" in path)
            )
            sensitive_field = sensitive_object and key in {
                "value", "review_value", "message", "basis", "evidence",
                "before_image", "prior_payload", "content_snapshot", "inputs",
            }
            result[key] = (SENSITIVE_REDACTION
                           if audit_secret or sensitive_field
                           else project(child, child_path))
        return result

    return project(value, ())


_SENSITIVE_NOTIFICATION_FIELDS = {
    "ftp", "ftp_watts", "weight", "weight_kg", "weight_lbs", "w_kg",
    "carbohydrates", "hourly_carb_target", "total_carbs", "carb_target",
    "carb_range", "before_image", "prior_payload",
}


def external_notification_projection(value: Any) -> Any:
    """Project arbitrary notification inputs onto the non-review boundary.

    Notification detail dictionaries predate the typed review catalog and use
    flat convenience keys.  This adapter first applies the recursive catalog
    policy, then drops the legacy keys whose owning A3 fields are sensitive.
    Raw pipeline exceptions are also replaced: durable authenticated logs are
    the diagnostic surface, while notification/log fallbacks carry only the
    loud failure fact.
    """
    projected = external_state_projection(value)

    def drop(nested: Any, path: tuple[str, ...]) -> Any:
        if isinstance(nested, list):
            return [drop(item, path) for item in nested]
        if not isinstance(nested, dict):
            return copy.deepcopy(nested)
        result = {}
        for key, child in nested.items():
            normalized = str(key).strip().lower()
            if normalized in _SENSITIVE_NOTIFICATION_FIELDS:
                result[key] = None
            elif normalized == "error" and not path and child:
                result[key] = "See authenticated Railway logs for failure details."
            else:
                result[key] = drop(child, path + (str(key),))
        return result

    return drop(projected, ())


def redact_sensitive_review_items(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Compatibility wrapper over the recursive external-state boundary."""
    return external_state_projection(items)


def _state_path(path: os.PathLike[str] | str) -> Path:
    return Path(path)


def blocker_is_waivable(rule_id: str) -> bool:
    rule_id = str(rule_id or "").strip().upper()
    return not (
        rule_id in NON_WAIVABLE_RULES
        or rule_id.startswith("VALIDATOR_CRASH")
        or rule_id.startswith("SEAL_MISMATCH")
        or rule_id.startswith("D2_CANNOT_RESOLVE")
    )


def blocker_remediation(rule_id: str) -> str:
    """Server-owned remediation copy for non-waivable review findings."""
    normalized = str(rule_id or "").strip().upper()
    if normalized.startswith("VALIDATOR_CRASH"):
        return NON_WAIVABLE_REMEDIATIONS["VALIDATOR_CRASH"]
    if normalized.startswith("SEAL_MISMATCH"):
        return NON_WAIVABLE_REMEDIATIONS["SEAL_MISMATCH"]
    return NON_WAIVABLE_REMEDIATIONS.get(normalized, "")


def _copy_review_metadata(source: Dict[str, Any], target: Dict[str, Any]) -> None:
    for key in _REVIEW_METADATA_KEYS:
        if key in source:
            target[key] = copy.deepcopy(source[key])


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
    _copy_review_metadata(issue, normalized)
    return normalized


def _validate_confirmation(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict) or not str(item.get("id", "")).strip():
        raise FulfillmentStateError("required confirmation requires id")
    normalized = {
        "id": str(item["id"]).strip(),
        "source": str(item.get("source", "post_render")).strip(),
        "message": str(item.get("message", "")).strip(),
    }
    _copy_review_metadata(item, normalized)
    resolved = normalized.get("resolved_resolution")
    if resolved is not None and resolved not in normalized.get("resolution_choices", []):
        raise FulfillmentStateError("resolved confirmation choice is invalid")
    return normalized


def _validate_derived_value(item: Dict[str, Any]) -> Dict[str, Any]:
    """Validate one materialized A3 provenance record stored server-side."""
    required = ("id", "field", "class", "basis", "inputs", "sensitivity", "at", "value")
    if not isinstance(item, dict) or any(key not in item for key in required):
        raise FulfillmentStateError("derived value is missing required fields")
    normalized = copy.deepcopy(item)
    if any(not str(normalized.get(key) or "").strip()
           for key in ("id", "field", "class", "basis", "at")):
        raise FulfillmentStateError("derived value identity and provenance are required")
    if normalized["class"] not in {
        "measured", "athlete_reported", "defaulted", "inferred", "externally_observed",
    }:
        raise FulfillmentStateError("unknown derived value class")
    if normalized["sensitivity"] not in REVIEW_SENSITIVITIES:
        raise FulfillmentStateError("unknown derived value sensitivity")
    _canonical_review_value(normalized["inputs"])
    _canonical_review_value(normalized["value"])
    normalized["revision"] = int(normalized.get("revision", 1))
    if normalized["revision"] < 1:
        raise FulfillmentStateError("derived value revision must be positive")
    return normalized


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise FulfillmentStateError("review item value is not JSON-typed")


def _canonical_review_value(value: Any) -> Any:
    try:
        canonical_json(value)
    except (TypeError, ValueError) as exc:
        raise FulfillmentStateError("review item value is not canonical JSON") from exc
    return copy.deepcopy(value)


def _review_item(
    state: Dict[str, Any], source_item: Dict[str, Any], item_type: str,
) -> Dict[str, Any]:
    if item_type not in REVIEW_ITEM_TYPES:
        raise FulfillmentStateError("unknown review item type")
    item_id = str(source_item.get("id") or "").strip()
    if not item_id:
        raise FulfillmentStateError("review item requires item_id")
    value = _canonical_review_value(
        source_item.get("review_value", source_item.get("message", ""))
    )
    sensitivity = str(source_item.get("sensitivity") or "internal").strip()
    if sensitivity not in REVIEW_SENSITIVITIES:
        raise FulfillmentStateError("unknown review item sensitivity")
    display_unit = source_item.get("display_unit")
    if display_unit is not None:
        display_unit = str(display_unit).strip() or None
    item = {
        "item_id": item_id,
        "type": item_type,
        "value": value,
        "value_type": _value_type(value),
        "display_unit": display_unit,
        "source": str(source_item.get("source") or "state").strip(),
        "basis": str(
            source_item.get("basis") or source_item.get("source") or "state"
        ).strip(),
        "sensitivity": sensitivity,
        "revision": state["generation_revision"],
        "message": str(source_item.get("message") or "").strip(),
    }
    if not item["source"] or not item["basis"]:
        raise FulfillmentStateError("review item source and basis are required")
    choices = source_item.get("resolution_choices", [])
    if not isinstance(choices, list) or any(
        not isinstance(choice, str) or not choice.strip() for choice in choices
    ):
        raise FulfillmentStateError("review item resolution choices are invalid")
    item["resolution_choices"] = sorted(set(choice.strip() for choice in choices))
    if source_item.get("resolved_resolution") is not None:
        resolved = str(source_item["resolved_resolution"]).strip()
        if resolved not in item["resolution_choices"]:
            raise FulfillmentStateError("review item resolution is invalid")
        item["resolved_resolution"] = resolved
    if item_type == "blocker":
        item.update({
            "severity": str(source_item.get("severity") or "CRITICAL").strip(),
            "waivable": blocker_is_waivable(item_id),
            "remediation": blocker_remediation(item_id),
        })
    return item


def _expected_review_catalog(state: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Build the complete server-owned catalog for the current revision."""
    sources: list[tuple[Dict[str, Any], str]] = []
    sources.extend((item, "blocker") for item in state.get("blocking_issues", []))
    sources.extend(
        (item, "required_confirmation")
        for item in state.get("required_confirmations", [])
    )
    sources.extend(
        (item, "soft_confirmation")
        for item in state.get("soft_confirmations", [])
    )
    for derived in state.get("derived_values", []):
        sources.append(({
            "id": f"DERIVED_{derived['id']}",
            "source": "derived_registry",
            "basis": derived["basis"],
            "sensitivity": derived["sensitivity"],
            "message": f"{derived['field']} ({derived['class']}).",
            "review_value": derived["value"],
        }, "verified_fact"))
    sources.append(({
        "id": "FACT_ORDER_CONTEXT",
        "source": "fulfillment_state",
        "basis": "immutable order identity",
        "sensitivity": "personal",
        "message": "Order, athlete, platform, and revision identity.",
        "review_value": {
            "order_id": state["order_id"],
            "athlete_id": state["athlete_id"],
            "delivery_platform": state["delivery_platform"],
            "generation_revision": state["generation_revision"],
        },
    }, "verified_fact"))
    if state.get("model_seal") and state.get("release_manifest_digest"):
        sources.append(({
            "id": "FACT_RELEASE_SEAL",
            "source": "release_manifest",
            "basis": str(state.get("seal_version") or "sealed release"),
            "sensitivity": "internal",
            "message": "Immutable release manifest identity.",
            "review_value": {
                "model_seal": state["model_seal"],
                "release_manifest_digest": state["release_manifest_digest"],
                "artifact_count": state.get("release_artifact_count"),
            },
        }, "verified_fact"))

    items = [_review_item(state, source, item_type) for source, item_type in sources]
    ids = [item["item_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise FulfillmentStateError("duplicate review item id")
    rank = {
        "blocker": 0,
        "required_confirmation": 1,
        "soft_confirmation": 2,
        "verified_fact": 3,
    }
    return sorted(items, key=lambda item: (rank[item["type"]], item["item_id"]))


def _refresh_review_catalog(state: Dict[str, Any]) -> None:
    state["review_catalog_version"] = REVIEW_CATALOG_VERSION
    state["review_items"] = _expected_review_catalog(state)
    state["review_catalog_digest"] = review_catalog_digest(state["review_items"])


def _approval_snapshot_is_complete(state: Dict[str, Any]) -> bool:
    approval = state.get("approval")
    if not isinstance(approval, dict):
        return False
    if approval.get("snapshot_version") != APPROVAL_SNAPSHOT_VERSION:
        return False
    if approval.get("revision") != state.get("generation_revision"):
        return False
    if not str(approval.get("credential") or "").strip():
        return False
    if approval.get("review_catalog_digest") != review_catalog_digest(state):
        return False
    snapshots = approval.get("confirmations")
    catalog = state.get("review_items") or []
    if not isinstance(snapshots, list) or len(snapshots) != len(catalog):
        return False
    by_id = {item.get("item_id"): item for item in snapshots if isinstance(item, dict)}
    if len(by_id) != len(catalog):
        return False
    for item in catalog:
        snapshot = by_id.get(item["item_id"])
        if not snapshot:
            return False
        reviewed_item = {
            key: copy.deepcopy(value)
            for key, value in snapshot.items()
            if key != "disposition"
        }
        if reviewed_item != item:
            return False
        disposition = str(snapshot.get("disposition") or "")
        if item["type"] == "blocker" and disposition != "resolved:waived":
            return False
        resolved_choice = (
            disposition.removeprefix("resolved:")
            if disposition.startswith("resolved:") else ""
        )
        resolution_allowed = resolved_choice in item.get("resolution_choices", [])
        if item["type"] in {"required_confirmation", "verified_fact"} and (
            disposition != "confirmed" and not resolution_allowed
        ):
            return False
        if item["type"] == "soft_confirmation" and (
            disposition not in {"confirmed", "unconfirmed"}
            and not resolution_allowed
        ):
            return False
    return True


def _validate_phase5_state(state: Dict[str, Any]) -> None:
    """Validate optional Phase 5 execution fields on every schema-v2 load."""
    state.setdefault("application_attempt", None)
    state.setdefault("execution_epoch", 0)
    state.setdefault("execution_fence", 0)
    state.setdefault("cancel_requested", False)
    state.setdefault("compensation_pending", False)
    state.setdefault("cancellation", None)
    for field in ("execution_epoch", "execution_fence"):
        value = state[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FulfillmentStateError(f"{field} must be a nonnegative integer")
    for field in ("cancel_requested", "compensation_pending"):
        if not isinstance(state[field], bool):
            raise FulfillmentStateError(f"{field} must be boolean")

    attempt = state["application_attempt"]
    if attempt is not None:
        required = {
            "jti", "action", "request_digest", "status", "execution_epoch",
            "fencing_token", "lease", "landed", "intents", "receipt_ref",
        }
        if not isinstance(attempt, dict) or set(attempt) != required:
            raise FulfillmentStateError("application_attempt shape is invalid")
        if (not str(attempt["jti"]).strip()
                or attempt["action"] not in {"apply", "verify", "rollback"}
                or not re.fullmatch(r"[0-9a-f]{64}", str(attempt["request_digest"]))
                or attempt["status"] not in {
                    "accepted", "running", "succeeded", "failed",
                }):
            raise FulfillmentStateError("application_attempt authority is invalid")
        for field in ("execution_epoch", "fencing_token"):
            value = attempt[field]
            if (isinstance(value, bool) or not isinstance(value, int)
                    or value < (1 if field == "fencing_token" else 0)):
                raise FulfillmentStateError("application_attempt epoch/fence is invalid")
        lease = attempt["lease"]
        if (not isinstance(lease, dict)
                or set(lease) != {"athlete_key_digest", "expires_at"}
                or not re.fullmatch(
                    r"[0-9a-f]{64}", str(lease.get("athlete_key_digest") or ""))
                or not str(lease.get("expires_at") or "").strip()):
            raise FulfillmentStateError("application_attempt lease is invalid")
        if (not isinstance(attempt["landed"], list)
                or not isinstance(attempt["intents"], list)
                or not str(attempt["receipt_ref"]).strip()):
            raise FulfillmentStateError("application_attempt journal is invalid")
    if state.get("status") == APPLYING and attempt is None:
        raise FulfillmentStateError("APPLYING requires an application_attempt")

    cancellation = state["cancellation"]
    if state["cancel_requested"]:
        if (not isinstance(cancellation, dict)
                or not str(cancellation.get("requested_by") or "").strip()
                or not str(cancellation.get("at") or "").strip()
                or not isinstance(cancellation.get("worker_stop_acknowledged"), bool)):
            raise FulfillmentStateError("cancel_requested requires cancellation evidence")
    elif cancellation is not None and not isinstance(cancellation, dict):
        raise FulfillmentStateError("cancellation must be an object or null")
    if state["compensation_pending"]:
        if state.get("status") != CANCELLED or not attempt or not attempt["landed"]:
            raise FulfillmentStateError(
                "compensation_pending requires cancelled landed operations")


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
    soft_confirmations = state.get("soft_confirmations", [])
    if not isinstance(soft_confirmations, list):
        raise FulfillmentStateError("soft_confirmations must be a list")
    state["soft_confirmations"] = [
        _validate_confirmation(item) for item in soft_confirmations
    ]
    derived_values = state.get("derived_values", [])
    if not isinstance(derived_values, list):
        raise FulfillmentStateError("derived_values must be a list")
    state["derived_values"] = [_validate_derived_value(item) for item in derived_values]
    for key in ("approval", "waiver", "application", "confirmation"):
        if key not in state:
            raise FulfillmentStateError(f"fulfillment state missing {key}")
    superseded_approvals = state.get("superseded_approvals", [])
    if not isinstance(superseded_approvals, list):
        raise FulfillmentStateError("superseded_approvals must be a list of records")
    for record in superseded_approvals:
        if (
            not isinstance(record, dict)
            or record.get("authoritative") is not False
            or not isinstance(record.get("generation_revision"), int)
            or record["generation_revision"] < 1
            or not str(record.get("reason") or "").strip()
            or not str(record.get("superseded_at") or "").strip()
            or not isinstance(record.get("approval"), dict)
        ):
            raise FulfillmentStateError("invalid superseded approval record")
    state["superseded_approvals"] = copy.deepcopy(superseded_approvals)
    if not isinstance(state.get("history"), list) or not state.get("updated_at"):
        raise FulfillmentStateError("fulfillment state missing history or updated_at")
    if "release_manifest" not in state or "model_seal" not in state:
        raise FulfillmentStateError("fulfillment state missing release seal fields")
    state.setdefault("release_artifact_count", None)
    _validate_phase5_state(state)
    # D2 remains an optional extension for all pre-Phase-4 schema-v2 files.
    # Importing lazily avoids making the state foundation depend on Flask.
    from d2_identity import validate_d2_state
    validate_d2_state(state)
    expected_catalog = _expected_review_catalog(state)
    existing_catalog = state.get("review_items")
    if existing_catalog is not None and existing_catalog != expected_catalog:
        raise FulfillmentStateError("review catalog does not match authoritative state")
    expected_catalog_digest = review_catalog_digest(expected_catalog)
    existing_catalog_digest = state.get("review_catalog_digest")
    if (existing_catalog_digest is not None
            and existing_catalog_digest != expected_catalog_digest):
        raise FulfillmentStateError("review catalog digest does not match catalog")
    state["review_catalog_version"] = REVIEW_CATALOG_VERSION
    state["review_items"] = expected_catalog
    state["review_catalog_digest"] = expected_catalog_digest
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
    soft_confirmations: Optional[list[Dict[str, Any]]] = None,
    derived_values: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Start a revision while preserving immutable order identity."""
    issues = [_validate_issue(issue) for issue in (blocking_issues or [])]
    confirmations = [
        _validate_confirmation(item) for item in (required_confirmations or [])
    ]
    soft = [_validate_confirmation(item) for item in (soft_confirmations or [])]
    derived = [_validate_derived_value(item) for item in (derived_values or [])]
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
        if previous:
            # D2 inspection is external order evidence. Regeneration replaces
            # generated namespaces while retaining the binding, inspection,
            # and chosen command effects. The temporary regeneration blocker
            # clears only when the producer actually starts this revision.
            issues += [
                copy.deepcopy(issue) for issue in previous.get("blocking_issues", [])
                if issue.get("source") == "d2"
                and issue.get("id") != "D2_REGENERATION_REQUIRED"
                and issue.get("id") not in {item["id"] for item in issues}
            ]
            confirmations += [
                copy.deepcopy(item) for item in previous.get("required_confirmations", [])
                if item.get("source") == "d2"
                and item.get("id") not in {value["id"] for value in confirmations}
            ]
            soft += [
                copy.deepcopy(item) for item in previous.get("soft_confirmations", [])
                if item.get("source") == "d2"
                and item.get("id") not in {value["id"] for value in soft}
            ]
            derived += [
                copy.deepcopy(item) for item in previous.get("derived_values", [])
                if item.get("id", "").startswith("D2_")
                and item.get("id") not in {value["id"] for value in derived}
            ]
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
            "soft_confirmations": sorted(soft, key=lambda item: item["id"]),
            "derived_values": sorted(
                [{**item, "revision": revision} for item in derived],
                key=lambda item: item["id"],
            ),
            "approval": None,
            "waiver": None,
            "application": None,
            "application_attempt": None,
            "execution_epoch": 0,
            "execution_fence": 0,
            "cancel_requested": False,
            "compensation_pending": False,
            "cancellation": None,
            "confirmation": None,
            "superseded_approvals": copy.deepcopy(
                previous.get("superseded_approvals", []) if previous else []
            ),
            "model_seal": None,
            "release_manifest_digest": None,
            "release_manifest": None,
            "release_artifact_count": None,
            "seal_version": None,
            "d2_active": bool(previous.get("d2_active")) if previous else False,
            "platform_identity": copy.deepcopy(
                previous.get("platform_identity") if previous else None),
            "identity_resolution": copy.deepcopy(
                previous.get("identity_resolution") if previous else {
                    "outcome": "unresolved", "candidates": [], "at": None,
                }),
            "account_inspection": copy.deepcopy(
                previous.get("account_inspection") if previous else None),
            "d2_resolutions": copy.deepcopy(
                previous.get("d2_resolutions", {}) if previous else {}),
            "d2_pending_requirements": copy.deepcopy(
                previous.get("d2_pending_requirements", {}) if previous else {}),
            "d2_apply_operations": copy.deepcopy(
                previous.get("d2_apply_operations", {}) if previous else {}),
            "canonical_input_overrides": copy.deepcopy(
                previous.get("canonical_input_overrides", {}) if previous else {}),
            "d2_context": copy.deepcopy(
                previous.get("d2_context", {}) if previous else {}),
            "regeneration_request": None,
            "legacy": False,
            "history": history,
            "updated_at": now_iso(),
        }
        adopted_lthr = (
            state.get("d2_context", {}).get("canonical_control_value")
            if state.get("d2_resolutions", {}).get(
                "D2_THRESHOLD_LTHR_STALE_MISMATCH", {}).get("choice")
            == "use-tp-value" else None
        )
        if adopted_lthr is not None:
            for confirmation in state["required_confirmations"]:
                if confirmation.get("id") == "D2_THRESHOLD_LTHR_STALE_MISMATCH":
                    confirmation.setdefault("review_value", {})["plan_value"] = adopted_lthr
        _refresh_review_catalog(state)
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
        if state.get("model_seal") or state.get("release_manifest"):
            raise FulfillmentStateError(
                "sealed review catalog is immutable; use write_generation"
            )
        state["blocking_issues"] = sorted(issues, key=lambda item: item["id"])
        state["status"] = BLOCKED_REVIEW if issues else GENERATED
        _refresh_review_catalog(state)
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
    soft_confirmations: Optional[list[Dict[str, Any]]] = None,
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
    soft = None
    if soft_confirmations is not None:
        soft = [
            _validate_confirmation({**item, "source": source})
            for item in soft_confirmations
        ]
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if state["status"] not in (GENERATED, BLOCKED_REVIEW):
            raise FulfillmentStateError("cannot alter blockers after review begins")
        if state.get("model_seal") or state.get("release_manifest"):
            raise FulfillmentStateError(
                "sealed review catalog is immutable; use write_generation"
            )
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
            if (state.get("d2_active")
                    and (state.get("account_inspection") or {}).get("lthr_bpm") is not None):
                state["required_confirmations"] = [
                    item for item in state["required_confirmations"]
                    if item.get("id") != "POWER_BASIS_NONE_CONFIRM"
                ]
        if soft is not None:
            preserved_soft = [
                item for item in state["soft_confirmations"]
                if item.get("source") != source
            ]
            state["soft_confirmations"] = sorted(
                preserved_soft + soft, key=lambda item: item["id"]
            )
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _refresh_review_catalog(state)
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


def _canonical_model_seal_from_release(
    artifact_root: Path, state: Dict[str, Any], contract: Dict[str, Any],
) -> str:
    artifact_dir = artifact_root / "artifacts"
    try:
        canonical_model = json.loads(
            (artifact_dir / "canonical_training_model.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FulfillmentStateError("canonical model unavailable for seal") from exc
    guide_sources = {}
    for name in ("profile.yaml", "methodology.yaml", "fueling.yaml", "plan_dates.yaml"):
        candidate = artifact_dir / name
        if candidate.is_file():
            guide_sources[name] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    # FACT_RELEASE_SEAL is added only after this model seal exists; excluding
    # that derived fact keeps the finalization graph acyclic.
    review_items = [item for item in state.get("review_items", [])
                    if item.get("item_id") != "FACT_RELEASE_SEAL"]
    operation_payloads = [{
        "logical_id": op["logical_id"], "kind": op["kind"],
        "disposition": op["disposition"], "payload": op["payload"],
    } for op in contract.get("operations", [])]
    return canonical_digest({
        "canonical_model": canonical_model,
        "review_items": review_items,
        "guide_sources": guide_sources,
        "operation_payloads": operation_payloads,
    })


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
    contract_path = artifact_root / "artifacts" / "apply_contract.json"
    if contract_path.is_file():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FulfillmentStateError("apply contract unavailable for seal") from exc
        seal_version = CANONICAL_SEAL_VERSION
        # State validation under the lock below repeats identity checks before
        # granting authority; this early value only builds the manifest.
        model_seal = None
    else:
        contract = None
        seal_version = TRANSITIONAL_SEAL_VERSION
        model_seal = canonical_digest(records)
    manifest_path = artifact_root / "release_manifest.json"

    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if state.get("model_seal"):
            raise FulfillmentStateError("release is already sealed")
        if contract is not None:
            if (contract.get("order_id") != state["order_id"]
                    or contract.get("generation_revision") != expected_revision):
                raise FulfillmentStateError("apply contract identity mismatch")
            model_seal = _canonical_model_seal_from_release(
                artifact_root, state, contract)
            if contract.get("model_seal") != model_seal:
                raise FulfillmentStateError("apply contract model_seal mismatch")
        manifest = {
            "seal_version": seal_version,
            "model_seal": model_seal,
            "artifacts": records,
        }
        _atomic_write(manifest_path, manifest)
        # Verify the exact bytes we just made durable before granting authority.
        persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        if persisted != manifest:
            raise FulfillmentStateError("release manifest verification failed")
        state["model_seal"] = model_seal
        state["release_manifest_digest"] = canonical_digest(records)
        state["release_manifest"] = str(manifest_path)
        state["release_artifact_count"] = len(records)
        state["seal_version"] = seal_version
        _refresh_review_catalog(state)
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
    manifest_seal_version = manifest.get("seal_version")
    if (manifest_seal_version not in {TRANSITIONAL_SEAL_VERSION, CANONICAL_SEAL_VERSION}
            or manifest.get("model_seal") != state["model_seal"]
            or canonical_digest(records) != state["release_manifest_digest"]):
        raise FulfillmentStateError("release manifest seal mismatch")
    if manifest_seal_version == TRANSITIONAL_SEAL_VERSION:
        if canonical_digest(records) != state["model_seal"]:
            raise FulfillmentStateError("release manifest seal mismatch")
    else:
        try:
            contract = json.loads(
                (Path(artifact_root) / "artifacts" / "apply_contract.json")
                .read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FulfillmentStateError("apply contract unavailable for seal") from exc
        expected_model_seal = _canonical_model_seal_from_release(
            Path(artifact_root), state, contract)
        if (expected_model_seal != state["model_seal"]
                or contract.get("model_seal") != state["model_seal"]):
            raise FulfillmentStateError("canonical model seal mismatch")
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
        and _approval_snapshot_is_complete(state)
    )


def _seal_mismatch_issue(message: str) -> Dict[str, Any]:
    return _validate_issue({
        "id": "SEAL_MISMATCH",
        "source": "seal_verification",
        "severity": "CRITICAL",
        "message": f"Release seal verification failed: {message}",
        "review_value": {"seal_verified": False, "failure": message},
        "basis": "release manifest and artifact-byte verification",
        "sensitivity": "internal",
    })


def _materialize_seal_mismatch(
    state: Dict[str, Any], message: str,
) -> None:
    prior_revision = state["generation_revision"]
    prior_status = state["status"]
    prior_model_seal = state.get("model_seal")
    prior_approval = copy.deepcopy(state.get("approval"))
    prior_waiver = copy.deepcopy(state.get("waiver"))
    prior_application = copy.deepcopy(state.get("application"))
    prior_confirmation = copy.deepcopy(state.get("confirmation"))
    archived_approval = isinstance(prior_approval, dict)
    if archived_approval:
        state.setdefault("superseded_approvals", []).append({
            "authoritative": False,
            "reason": "release seal mismatch",
            "message": str(message),
            "superseded_at": now_iso(),
            "generation_revision": prior_revision,
            "status": prior_status,
            "approval": prior_approval,
            "waiver": prior_waiver,
            "application": prior_application,
            "confirmation": prior_confirmation,
            "model_seal": prior_model_seal,
            "release_manifest_digest": state.get("release_manifest_digest"),
            "release_manifest": state.get("release_manifest"),
            "release_artifact_count": state.get("release_artifact_count"),
            "seal_version": state.get("seal_version"),
        })
    # A detected byte/seal failure supersedes the sealed generation. It must
    # never rewrite that revision's review catalog in place. This creates a
    # fresh, unsealed quarantine revision with the same reset authority shape
    # as write_generation; the producer must regenerate artifacts again.
    state["generation_revision"] = prior_revision + 1
    state["blocking_issues"] = [_seal_mismatch_issue(message)]
    state["required_confirmations"] = []
    state["soft_confirmations"] = []
    state["derived_values"] = []
    state["status"] = BLOCKED_REVIEW
    state["approval"] = None
    state["waiver"] = None
    state["application"] = None
    state["confirmation"] = None
    state["model_seal"] = None
    state["release_manifest_digest"] = None
    state["release_manifest"] = None
    state["release_artifact_count"] = None
    state["seal_version"] = None
    _refresh_review_catalog(state)
    _history(
        state, "SEAL_MISMATCH_REGENERATION_REQUIRED", message=message,
        prior_revision=prior_revision, prior_status=prior_status,
        prior_model_seal=prior_model_seal,
        superseded_approval_archived=archived_approval,
    )


def record_seal_mismatch(
    path: os.PathLike[str] | str, message: str,
) -> Dict[str, Any]:
    """Revoke authority by superseding the failed sealed generation."""
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
    manifest = verify_release_manifest(state, artifact_root)
    records = manifest.get("artifacts")

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
    expected_revision: Optional[int] = None,
    expected_catalog_digest: str = "",
    review_decisions: Optional[list[Dict[str, Any]]] = None,
    credential: str = "",
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
        if (expected_revision is not None
                and expected_revision != state["generation_revision"]):
            raise FulfillmentStateError("generation revision mismatch; review is superseded")
        current = state["status"]
        if to == CONFIRMED and current == CONFIRMED:
            return copy.deepcopy(state)
        if to == CANCELLED:
            if current == CANCELLED:
                return copy.deepcopy(state)
            attempt = state.get("application_attempt")
            landed = (
                attempt.get("landed", [])
                if isinstance(attempt, dict) else []
            )
            if state.get("application") or landed:
                raise FulfillmentStateError(
                    "cancellation requires the Phase 5 compensation workflow "
                    "because application evidence exists"
                )
            state["cancel_requested"] = True
            state["execution_epoch"] = int(state.get("execution_epoch") or 0) + 1
            state["cancellation"] = {
                "requested_by": coach.strip(),
                "credential": str(credential or "operator-secret").strip(),
                "at": now_iso(),
                # No application attempt or landed operation exists, so there
                # is no worker to quiesce. Recording that fact keeps the audit
                # strict without manufacturing a remote acknowledgement.
                "worker_stop_acknowledged": True,
                "worker_stop_basis": "no application attempt or landed operation",
                "reason": str((metadata or {}).get("reason") or "").strip(),
            }
        elif to == APPROVED:
            if state.get("d2_active"):
                from d2_identity import validate_d2_approval
                validate_d2_approval(state)
            if not state.get("model_seal") or not state.get("release_manifest_digest"):
                raise FulfillmentStateError("approval requires a sealed release")
            approval_credential = str(credential or "operator-secret").strip()
            if not approval_credential:
                raise FulfillmentStateError("approving credential is required")
            expected_catalog = _expected_review_catalog(state)
            current_catalog_digest = review_catalog_digest(expected_catalog)
            supplied_catalog_digest = str(expected_catalog_digest or "").strip()
            if (not supplied_catalog_digest
                    or not hmac.compare_digest(
                        supplied_catalog_digest, current_catalog_digest)):
                raise FulfillmentStateError(
                    "review catalog changed; regenerate or review the current catalog"
                )
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
                    "credential": approval_credential,
                    "revision": state["generation_revision"],
                }
            else:
                raise FulfillmentStateError(f"illegal transition {current} -> {to}")
            if state.get("review_items") != expected_catalog:
                raise FulfillmentStateError("review catalog is stale")
            decisions = review_decisions
            if not isinstance(decisions, list):
                raise FulfillmentStateError("review confirmations must be a list")
            decisions_by_id: Dict[str, Dict[str, Any]] = {}
            catalog_by_id = {item["item_id"]: item for item in expected_catalog}
            for decision in decisions:
                if not isinstance(decision, dict):
                    raise FulfillmentStateError("review confirmation is malformed")
                item_id = str(decision.get("item_id") or "").strip()
                if item_id not in catalog_by_id:
                    raise FulfillmentStateError("unknown review item id")
                if item_id in decisions_by_id:
                    raise FulfillmentStateError("duplicate review item decision")
                if decision.get("revision") != state["generation_revision"]:
                    raise FulfillmentStateError("review item revision mismatch")
                decisions_by_id[item_id] = decision

            snapshots = []
            for item in expected_catalog:
                decision = decisions_by_id.get(item["item_id"])
                item_type = item["type"]
                if item_type == "blocker":
                    disposition = "resolved:waived"
                elif item_type == "soft_confirmation" and decision is None:
                    disposition = "unconfirmed"
                elif item_type == "verified_fact" and decision is None:
                    # Approve is the acknowledgment. Per-fact checkboxes
                    # turned a <3 minute exception review into an 80-click
                    # inventory of sealed calendar abbreviations.
                    disposition = "confirmed"
                else:
                    if decision is None:
                        raise FulfillmentStateError(
                            "required confirmation is unresolved: "
                            f"{item['item_id']}"
                        )
                    disposition = str(decision.get("disposition") or "").strip()
                    authoritative_choice = item.get("resolved_resolution")
                    if authoritative_choice is not None:
                        authoritative_disposition = (
                            f"resolved:{authoritative_choice}")
                        if disposition != authoritative_disposition:
                            raise FulfillmentStateError(
                                "submitted review resolution does not match "
                                f"the authoritative command: {item['item_id']}"
                            )
                        disposition = authoritative_disposition
                    resolved_choice = (
                        disposition.removeprefix("resolved:")
                        if disposition.startswith("resolved:") else ""
                    )
                    resolution_allowed = (
                        resolved_choice in item.get("resolution_choices", [])
                    )
                    if item_type in {"required_confirmation", "verified_fact"}:
                        if (disposition != "confirmed"
                                and not resolution_allowed):
                            raise FulfillmentStateError(
                                f"required review item is unresolved: {item['item_id']}"
                            )
                    elif (disposition not in {"confirmed", "unconfirmed"}
                          and not resolution_allowed):
                        raise FulfillmentStateError(
                            f"invalid review disposition: {item['item_id']}"
                        )
                snapshots.append({
                    **copy.deepcopy(item),
                    "disposition": disposition,
                })
            # Identity and D2 consistency are approval-boundary invariants,
            # evaluated after the submitted review snapshot/policy so existing
            # catalog and non-waivable failures keep their precise diagnostics.
            if not state.get("d2_active"):
                from d2_identity import validate_d2_approval
                validate_d2_approval(state)
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
                "credential": approval_credential,
                "at": now_iso(),
                "revision": state["generation_revision"],
                "snapshot_version": APPROVAL_SNAPSHOT_VERSION,
                "review_catalog_digest": current_catalog_digest,
                "model_seal": state["model_seal"],
                "release_manifest_digest": state["release_manifest_digest"],
                "confirmations": snapshots,
            }
        elif to == APPLIED:
            if current != APPROVED:
                raise FulfillmentStateError("application requires APPROVED status")
            if not approval_matches_release(state):
                raise FulfillmentStateError(
                    "application requires a complete seal-bound approval snapshot"
                )
            requested_platform = str(platform).strip()
            delivery_platform = state["delivery_platform"]
            if requested_platform == "endure" or delivery_platform == "endure":
                raise FulfillmentStateError(
                    "Endure APPLIED is disabled in Phase 1 by D4/R9 condition 11"
                )
            if (requested_platform not in PHASE1_APPLIED_PLATFORMS
                    or delivery_platform not in PHASE1_APPLIED_PLATFORMS):
                raise FulfillmentStateError(
                    "Phase 1 APPLIED supports only trainingpeaks or the manual/attested path"
                )
            if not requested_platform or not str(evidence).strip():
                raise FulfillmentStateError("platform and nonempty evidence are required")
            if requested_platform != delivery_platform:
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
                "platform": requested_platform, "evidence": evidence.strip(),
            }
        else:
            raise FulfillmentStateError(f"illegal transition {current} -> {to}")
        state["status"] = to
        _history(
            state, "TRANSITION", from_status=current, to_status=to,
            coach=coach.strip(),
            credential=(str(credential or "operator-secret").strip()
                        if to == APPROVED else ""),
            **(metadata or {}),
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
            "review_value": {
                "legacy_state": True,
                "quarantined": True,
                "candidate_count": len(set(ledger_candidates or [])),
            },
            "basis": "schema-v1 quarantine migration result",
            "sensitivity": "internal",
        })],
        "required_confirmations": [],
        "soft_confirmations": [],
        "derived_values": [],
        "approval": original.get("approval"),
        "waiver": original.get("waiver"),
        "application": original.get("application"),
        "confirmation": original.get("confirmation"),
        "superseded_approvals": [],
        "model_seal": None,
        "release_manifest_digest": None,
        "release_manifest": None,
        "release_artifact_count": None,
        "seal_version": None,
        "legacy": True,
        "legacy_binding": None,
        "legacy_candidates": sorted(set(ledger_candidates or [])),
        "legacy_original_evidence": original,
        "history": list(original.get("history") or []),
        "updated_at": now_iso(),
    }
    _refresh_review_catalog(state)
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
