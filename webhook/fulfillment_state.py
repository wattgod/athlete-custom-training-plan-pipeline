"""Durable, locked fulfillment state for manually reviewed plan delivery.

This module intentionally has no Flask or project imports.  Both the pipeline
and the webhook use it, so it is the sole owner of state schema and transitions.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

SCHEMA_VERSION = 1
GENERATED = "GENERATED"
BLOCKED_REVIEW = "BLOCKED_REVIEW"
APPROVED = "APPROVED"
APPLIED = "APPLIED"
CONFIRMED = "CONFIRMED"
VALID_STATUSES = {GENERATED, BLOCKED_REVIEW, APPROVED, APPLIED, CONFIRMED}


class FulfillmentStateError(ValueError):
    """A malformed state or an invalid operator request."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_path(path: os.PathLike[str] | str) -> Path:
    return Path(path)


def _validate_issue(issue: Dict[str, Any]) -> Dict[str, str]:
    required = ("id", "source", "severity", "message")
    if not isinstance(issue, dict) or any(not str(issue.get(key, "")).strip() for key in required):
        raise FulfillmentStateError("blocking issue requires id, source, severity, and message")
    return {key: str(issue[key]).strip() for key in required}


def _validate_state(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        raise FulfillmentStateError("fulfillment state must be an object")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise FulfillmentStateError("unsupported fulfillment state schema")
    if not str(state.get("athlete_id", "")).strip():
        raise FulfillmentStateError("fulfillment state has no athlete_id")
    if state.get("status") not in VALID_STATUSES:
        raise FulfillmentStateError("unknown fulfillment status")
    if not isinstance(state.get("generation_revision"), int) or state["generation_revision"] < 1:
        raise FulfillmentStateError("invalid generation revision")
    issues = state.get("blocking_issues")
    if not isinstance(issues, list):
        raise FulfillmentStateError("blocking_issues must be a list")
    state["blocking_issues"] = [_validate_issue(issue) for issue in issues]
    for key in ("approval", "waiver", "application", "confirmation"):
        if key not in state:
            raise FulfillmentStateError(f"fulfillment state missing {key}")
    if not isinstance(state.get("history"), list) or not state.get("updated_at"):
        raise FulfillmentStateError("fulfillment state missing history or updated_at")
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
def locked_state(path: os.PathLike[str] | str) -> Iterator[Tuple[Path, Optional[Dict[str, Any]]]]:
    """Lock an athlete state; malformed/missing state is returned as ``None``.

    Callers may keep this context open while sending confirmation mail. That is
    deliberate: two gunicorn workers must not send two confirmations.
    """
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
    state["history"].append({"at": now_iso(), "event": event, **details})
    state["updated_at"] = now_iso()


def write_generation(path: os.PathLike[str] | str, athlete_id: str,
                     blocking_issues: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Start a new generation revision, invalidating prior operator actions."""
    issues = [_validate_issue(issue) for issue in (blocking_issues or [])]
    with locked_state(path) as (state_path, previous):
        revision = (previous.get("generation_revision", 0) if previous else 0) + 1
        history = list(previous.get("history", []) if previous else [])
        if previous:
            history.append({"at": now_iso(), "event": "REGENERATED",
                            "prior_status": previous.get("status"),
                            "prior_revision": previous.get("generation_revision")})
        state = {
            "schema_version": SCHEMA_VERSION,
            "athlete_id": athlete_id,
            "generation_revision": revision,
            "status": BLOCKED_REVIEW if issues else GENERATED,
            "blocking_issues": issues,
            "approval": None,
            "waiver": None,
            "application": None,
            "confirmation": None,
            "history": history,
            "updated_at": now_iso(),
        }
        _history(state, "GENERATED", status=state["status"], blocker_ids=[x["id"] for x in issues])
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def set_generation_blockers(path: os.PathLike[str] | str,
                            blocking_issues: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Attach late pipeline blockers without pretending a regeneration occurred."""
    issues = [_validate_issue(issue) for issue in blocking_issues]
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["status"] not in (GENERATED, BLOCKED_REVIEW):
            raise FulfillmentStateError("cannot alter blockers after review begins")
        state["blocking_issues"] = issues
        state["status"] = BLOCKED_REVIEW if issues else GENERATED
        _history(state, "BLOCKERS_UPDATED", blocker_ids=[x["id"] for x in issues])
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def transition(path: os.PathLike[str] | str, to: str, coach: str = "", *,
               waiver: Optional[Dict[str, Any]] = None, platform: str = "",
               evidence: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Apply an authenticated operator transition and persist it atomically."""
    if to not in VALID_STATUSES:
        raise FulfillmentStateError("unknown destination status")
    if not str(coach).strip():
        raise FulfillmentStateError("coach is required")
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        current = state["status"]
        if to == CONFIRMED and current == CONFIRMED:
            return copy.deepcopy(state)
        if to == APPROVED:
            if current == GENERATED:
                state["approval"] = {"coach": coach.strip(), "at": now_iso()}
            elif current == BLOCKED_REVIEW:
                if not isinstance(waiver, dict):
                    raise FulfillmentStateError("complete waiver is required for blocked review")
                rule_ids = waiver.get("rule_ids")
                reason = str(waiver.get("reason", "")).strip()
                blockers = {issue["id"] for issue in state["blocking_issues"]}
                if not isinstance(rule_ids, list) or not reason or set(rule_ids) != blockers:
                    raise FulfillmentStateError("waiver must cover every blocking issue exactly")
                state["waiver"] = {"coach": coach.strip(), "at": now_iso(),
                                   "rule_ids": sorted(blockers), "reason": reason}
                state["approval"] = {"coach": coach.strip(), "at": now_iso()}
            else:
                raise FulfillmentStateError(f"illegal transition {current} -> {to}")
        elif to == APPLIED:
            if current != APPROVED:
                raise FulfillmentStateError("application requires APPROVED status")
            if not str(platform).strip() or not str(evidence).strip():
                raise FulfillmentStateError("platform and nonempty evidence are required")
            state["application"] = {"coach": coach.strip(), "at": now_iso(),
                                    "platform": platform.strip(), "evidence": evidence.strip()}
        else:
            raise FulfillmentStateError(f"illegal transition {current} -> {to}")
        state["status"] = to
        _history(state, "TRANSITION", from_status=current, to_status=to,
                 coach=coach.strip(), **(metadata or {}))
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def confirm_after_send(path: os.PathLike[str] | str,
                       send: Callable[[], bool], metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """Send exactly once while serialized, then mark confirmation on success.

    Returns ``("confirmed" | "idempotent", state)`` and raises for a state
    that is absent, malformed, or not ready to confirm.
    """
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        if state["status"] == CONFIRMED:
            return "idempotent", copy.deepcopy(state)
        if state["status"] != APPLIED:
            raise FulfillmentStateError("confirmation requires APPLIED status")
        if not send():
            raise RuntimeError("confirmation email failed")
        state["status"] = CONFIRMED
        state["confirmation"] = {"at": now_iso(), **(metadata or {})}
        _history(state, "TRANSITION", from_status=APPLIED, to_status=CONFIRMED)
        _atomic_write(state_path, state)
        return "confirmed", copy.deepcopy(state)
