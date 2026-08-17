"""Consultation record store: atomic write/read/update, timeline, readiness.

Records live at ``<deliveries_dir>/consultations/<safe_order_id>.json`` —
beside ``orders/`` (the pipeline job records) but in a directory
``sweep_stuck_jobs()`` never walks. See docs/CONSULT_ENGINE_SPEC.md §1.

This module has zero Flask dependency (mirrors download_tokens.py /
fulfillment_state.py) so it can be imported by app.py and by tests without
pulling in the web app. Callers pass ``deliveries_dir`` explicitly rather
than reading DATA_DIR/DELIVERIES_DIR from the environment, so tests can
point at a tmp_path per-test the same way the rest of the webhook does.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Pipeline state ONLY — never a proxy for "is the athlete happy" or similar.
STATUSES = {"open", "analysis_running", "report_ready", "needs_attention", "closed"}

# Every mutation appends one of these to the record's timeline.
TIMELINE_EVENTS = {
    "paid", "welcome_sent", "intake_received", "tp_linked", "claimed",
    "report", "error", "call_set", "addon_paid", "closed",
}

GIVE_UP_DAYS = 30


class ConsultationError(ValueError):
    """Raised for invalid order ids, unknown timeline events, or missing records."""


def safe_order_id(order_id: str) -> str:
    """Filesystem-safe order id — mirrors app.py's ``_safe_order_id`` (:1976)."""
    value = str(order_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ConsultationError("invalid order_id")
    return value


# Leading-underscore alias kept for call sites (webhook/app.py) that were
# written against app.py's own private ``_safe_order_id`` naming
# convention; both names resolve to the same function.
_safe_order_id = safe_order_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_now_iso = now_iso


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


_parse_iso = parse_iso


def consultations_root(deliveries_dir: Path | str) -> Path:
    return Path(deliveries_dir) / "consultations"


def record_path(deliveries_dir: Path | str, order_id: str) -> Path:
    return consultations_root(deliveries_dir) / f"{_safe_order_id(order_id)}.json"


def new_record(
    *,
    order_id: str,
    brand: str,
    athlete_name: str = "",
    athlete_email: str = "",
    hours: int = 1,
    amount_cents: int = 15000,
    plan_addon: bool = False,
    plan_addon_amount_cents: int = 10000,
    intake_id: str = "",
) -> Dict[str, Any]:
    """Build a fresh consultation record. Caller persists it with write_record."""
    now = _now_iso()
    return {
        "order_id": _safe_order_id(order_id),
        "brand": brand,
        "created_at": now,
        "status": "open",
        "welcome_sent_at": None,
        "athlete": {
            "name": athlete_name,
            "email": athlete_email,
            "tp_athlete_id": None,
            "tp_matched_at": None,
        },
        "products": {
            "consult": {"hours": hours, "amount": amount_cents},
            "plan_addon": {
                "purchased": bool(plan_addon),
                "amount": plan_addon_amount_cents,
                "purchased_at": now if plan_addon else None,
                "offer_expires_at": None,
            },
        },
        "intake": {"intake_id": intake_id or None, "received_at": None},
        "call_at": None,
        "analysis": {
            "claimed_by": None,
            "lease_expires_at": None,
            "attempts": 0,
            "started_at": None,
            "finished_at": None,
            "report_path": None,
            "error": None,
        },
        "closed_reason": None,
        # Not in the spec's literal JSON shape but required by §3 rule 5
        # ("each [nudge] at most once (record nudges_sent)"). Tracks which
        # follow-up nudges have already fired so the cron never repeats one.
        "nudges_sent": [],
        "timeline": [{"at": now, "event": "paid", "detail": ""}],
    }


def append_timeline(record: Dict[str, Any], event: str, detail: str = "") -> None:
    if event not in TIMELINE_EVENTS:
        raise ConsultationError(f"unknown timeline event: {event}")
    record.setdefault("timeline", []).append(
        {"at": _now_iso(), "event": event, "detail": detail}
    )


def write_record(deliveries_dir: Path | str, record: Dict[str, Any]) -> None:
    """Atomically persist a record (temp file + os.replace), mirroring _write_job."""
    path = record_path(deliveries_dir, record["order_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def read_record(deliveries_dir: Path | str, order_id: str) -> Optional[Dict[str, Any]]:
    try:
        path = record_path(deliveries_dir, order_id)
    except ConsultationError:
        return None
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def update_record(
    deliveries_dir: Path | str,
    order_id: str,
    mutate: Callable[[Dict[str, Any]], None],
) -> Dict[str, Any]:
    """Read-modify-write a record under an exclusive lock.

    ``mutate(record)`` mutates the dict in place; its return value is
    ignored. Raises ConsultationError if the record does not exist.
    """
    path = record_path(deliveries_dir, order_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            record = read_record(deliveries_dir, order_id)
            if record is None:
                raise ConsultationError(f"consultation not found: {order_id}")
            mutate(record)
            write_record(deliveries_dir, record)
            return record
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def list_records(deliveries_dir: Path | str) -> List[Dict[str, Any]]:
    """All consultation records, sorted by order_id. Skips unreadable files."""
    root = consultations_root(deliveries_dir)
    if not root.exists():
        return []
    records = []
    for path in sorted(root.glob("*.json")):
        try:
            records.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return records


def is_ready_for_analysis(record: Dict[str, Any]) -> bool:
    """Readiness is DERIVED, not stored: tp_matched_at set (intake optional but preferred)."""
    return bool((record.get("athlete") or {}).get("tp_matched_at"))


def should_give_up(record: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """Give-up rule: no TP link 30 days after paid → caller should close the record."""
    if record.get("status") == "closed":
        return False
    if (record.get("athlete") or {}).get("tp_matched_at"):
        return False
    created = _parse_iso(record.get("created_at"))
    if created is None:
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - created) >= timedelta(days=GIVE_UP_DAYS)
