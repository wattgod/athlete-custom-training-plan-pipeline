#!/usr/bin/env python3
"""Audit durable fulfilment states for stalled or unsafe lifecycle conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from webhook.fulfillment_state import (  # noqa: E402
    TERMINAL_STATUSES,
    external_state_projection,
)


CRITICAL = "CRITICAL"
WARNING = "WARNING"
PAID_ORDER_STALE = "PAID_ORDER_STALE"
# The coach notification tells the coach what the customer was promised: "the
# plan or a specific blocker update within 24 hours after payment" (webhook
# app.py, TrainingPeaks timeline copy; the Endure copy promises delivery
# "within 24 hours"). A paid order still open past that window is overdue.
PAID_ORDER_SLA_HOURS = 24
# A stale paid order alerts (CRITICAL) at most once per this window per
# order+status; runs in between report it as a WARNING repeat.
STALE_ALERT_REPEAT_WINDOW = timedelta(hours=24)
# Only real money: live-mode Stripe Checkout sessions and WooCommerce order
# numbers. Drill (drill-*), canary, manual_*, legacy_*, test_* and cs_test_*
# identities are synthetic or unpaid and never page anyone.
PAID_ORDER_ID_KINDS = (
    ("stripe_live_checkout", re.compile(r"cs_live_[A-Za-z0-9]+")),
    ("woocommerce_order", re.compile(r"[0-9]+")),
)
RESOURCE_KEYS = {
    "grant", "execution_grant", "active_grant", "last_grant",
    "lease", "worker_lease", "active_lease",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _configured_root(environ: Mapping[str, str]) -> Path:
    explicit = str(environ.get("GG_FULFILLMENT_ORDERS_ROOT") or "").strip()
    if explicit:
        return Path(explicit)
    data_dir = str(environ.get("DATA_DIR") or "").strip()
    if data_dir:
        return Path(data_dir) / "deliveries" / "orders"
    return REPO_ROOT / "athletes" / "deliveries" / "orders"


def _default_out(now: datetime) -> Path:
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "reports" / "audits" / f"fulfillment-states-{stamp}.json"


def order_ref(order_id: str) -> str:
    """Stable, non-reversible 12-hex reference for an order id."""
    return hashlib.sha256(str(order_id).encode("utf-8")).hexdigest()[:12]


def _state_ref(state: Mapping[str, Any], path: Path) -> str:
    return order_ref(str(state.get("order_id") or path.parent.name or path.name))


def _anomaly(
    state_ref: str, code: str, severity: str, detail: str, *, age_days: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state_ref": state_ref,
        "code": code,
        "severity": severity,
        "detail": detail,
    }
    if age_days is not None:
        result["age_days"] = age_days
    return result


def _age_days(value: Any, now: datetime) -> int | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return max(0, (now - parsed).days)


def _resource_expirations(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, datetime]]:
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _resource_expirations(child, path + (str(index),))
        return
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        normalized = str(key).strip().lower()
        child_path = path + (normalized,)
        if normalized in RESOURCE_KEYS and isinstance(child, dict):
            expiry = _parse_time(child.get("expires_at") or child.get("expiry"))
            if expiry is not None:
                kind = "lease" if "lease" in normalized else "grant"
                yield kind, expiry
        yield from _resource_expirations(child, child_path)


def _worker_stop_acknowledged(state: Mapping[str, Any]) -> bool:
    cancellation = state.get("cancellation")
    worker_stop = state.get("worker_stop")
    attempt = state.get("application_attempt")
    values = [
        state.get("worker_stop_acknowledged"),
        cancellation.get("worker_stop_acknowledged") if isinstance(cancellation, dict) else None,
        cancellation.get("stop_acknowledged_at") if isinstance(cancellation, dict) else None,
        worker_stop.get("acknowledged") if isinstance(worker_stop, dict) else None,
        worker_stop.get("acknowledged_at") if isinstance(worker_stop, dict) else None,
        attempt.get("worker_stop_acknowledged") if isinstance(attempt, dict) else None,
    ]
    return any(value is True or (isinstance(value, str) and bool(value.strip())) for value in values)


def paid_order_kind(state: Mapping[str, Any]) -> str | None:
    """Return the payment source for a real paid order, else ``None``."""
    if state.get("legacy") is True:
        # Quarantined v1 records carry an opaque legacy_* id and cannot be
        # transitioned; BLOCKED_REVIEW_OLD already covers them.
        return None
    order_id = str(state.get("order_id") or "").strip()
    for kind, pattern in PAID_ORDER_ID_KINDS:
        if pattern.fullmatch(order_id):
            return kind
    return None


def payment_clock(state: Mapping[str, Any]) -> datetime | None:
    """Earliest durable state event: a lower bound on time since payment.

    The state file is first written when generation finishes, minutes after
    the paid checkout webhook; history survives regeneration.
    """
    times = [
        parsed for parsed in (
            _parse_time(event.get("at"))
            for event in (state.get("history") or [])
            if isinstance(event, dict)
        ) if parsed is not None
    ]
    if times:
        return min(times)
    return _parse_time(state.get("updated_at"))


def open_paid_order(
    state: Mapping[str, Any], *, now: datetime,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> dict[str, Any] | None:
    """Facts for a paid order not yet in a terminal status, else ``None``."""
    status = str(state.get("status") or "")
    kind = paid_order_kind(state)
    if kind is None or status in TERMINAL_STATUSES:
        return None
    paid_at = payment_clock(state)
    blockers = state.get("blocking_issues")
    blockers = blockers if isinstance(blockers, list) else []
    return {
        "order_kind": kind,
        "status": status,
        "hours_since_payment": (
            int((now - paid_at).total_seconds() // 3600)
            if paid_at is not None else None),
        "payment_clock": "first_state_event",
        "blocker_count": len(blockers),
        "blocker_ids": sorted(
            str(item.get("id")) for item in blockers
            if isinstance(item, dict) and item.get("id")),
        "sla_hours": stale_after_hours,
        "stale": bool(
            paid_at is not None
            and now - paid_at > timedelta(hours=stale_after_hours)),
    }


def stale_paid_order(
    state: Mapping[str, Any], *, now: datetime,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> dict[str, Any] | None:
    """Facts for a paid, still-open order past the SLA, else ``None``."""
    facts = open_paid_order(
        state, now=now, stale_after_hours=stale_after_hours)
    return facts if facts is not None and facts["stale"] else None


def list_open_paid_orders(
    root: Path, *, now: datetime,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> list[dict[str, Any]]:
    """Every paid order still owed fulfilment, oldest first, hashed refs only."""
    found = []
    for path in _state_paths(Path(root)):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(state, dict):
            continue
        facts = open_paid_order(
            state, now=now, stale_after_hours=stale_after_hours)
        if facts is None:
            continue
        facts.pop("blocker_ids")
        found.append({
            "order_ref": _state_ref(state, path),
            "delivery_platform": str(state.get("delivery_platform") or ""),
            **facts,
        })
    found.sort(key=lambda item: -(item["hours_since_payment"] or 0))
    return found


def _approval_is_sealed(state: Mapping[str, Any]) -> bool:
    approval = state.get("approval")
    if not isinstance(approval, dict) or not approval:
        return True
    model_seal = str(state.get("model_seal") or "")
    release_digest = str(state.get("release_manifest_digest") or "")
    return bool(
        model_seal and release_digest
        and approval.get("model_seal") == model_seal
        and approval.get("release_manifest_digest") == release_digest
        and approval.get("revision") == state.get("generation_revision")
    )


def audit_state(
    state: Mapping[str, Any], *, path: Path, now: datetime, max_age_days: int,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    ref = _state_ref(state, path)
    status = str(state.get("status") or "")
    threshold = timedelta(days=max_age_days)
    updated = _parse_time(state.get("updated_at"))
    is_drill_order = str(state.get("order_id") or "").startswith("drill-")

    stale = stale_paid_order(
        state, now=now, stale_after_hours=stale_after_hours)
    if stale is not None:
        anomaly = _anomaly(
            ref, PAID_ORDER_STALE, CRITICAL,
            (f"paid order is still {stale['status']} "
             f"{stale['hours_since_payment']}h after payment "
             f"(SLA {stale_after_hours}h, {stale['blocker_count']} blockers)"),
        )
        anomaly.update({
            key: stale[key] for key in (
                "status", "hours_since_payment", "blocker_count",
                "sla_hours", "order_kind", "payment_clock")
        })
        anomalies.append(anomaly)

    if (
        status == "BLOCKED_REVIEW"
        and not is_drill_order
        and updated is not None
        and now - updated > threshold
    ):
        anomalies.append(_anomaly(
            ref, "BLOCKED_REVIEW_OLD", WARNING,
            "order has remained in BLOCKED_REVIEW beyond the review-age threshold",
            age_days=(now - updated).days,
        ))

    if status == "APPLYING":
        expired = {kind for kind, expiry in _resource_expirations(state) if expiry <= now}
        for kind in sorted(expired):
            anomalies.append(_anomaly(
                ref, f"APPLYING_EXPIRED_{kind.upper()}", CRITICAL,
                f"APPLYING state has an expired worker {kind}",
            ))

    if status == "CANCELLED" and not _worker_stop_acknowledged(state):
        anomalies.append(_anomaly(
            ref, "CANCELLED_STOP_UNACKNOWLEDGED", CRITICAL,
            "CANCELLED state lacks durable worker-stop acknowledgement",
        ))

    if not _approval_is_sealed(state):
        anomalies.append(_anomaly(
            ref, "UNSEALED_APPROVAL", CRITICAL,
            "approval is missing or contradicts its revision/model/release seal",
        ))

    pending = state.get("d2_pending_requirements")
    if not is_drill_order and isinstance(pending, dict) and pending:
        ages = []
        for requirement in pending.values():
            if isinstance(requirement, dict):
                requested = _parse_time(requirement.get("requested_at")) or updated
                if requested is not None and now - requested > threshold:
                    ages.append((now - requested).days)
        if ages:
            anomalies.append(_anomaly(
                ref, "D2_READBACK_OLD", WARNING,
                "one or more pending D2 worker readbacks exceed the age threshold",
                age_days=max(ages),
            ))
    return anomalies


def _state_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("fulfillment_status.json")) if root.is_dir() else []


def audit_states(
    root: Path, *, now: datetime, max_age_days: int,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
    stale_orders: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Audit every state under ``root``.

    ``stale_orders`` (optional) receives one private record per stale paid
    order, including the raw order id the coach needs to act. It never
    enters the redacted artifact.
    """
    if not root.exists():
        return [
            _anomaly(
                hashlib.sha256(str(root).encode()).hexdigest()[:12],
                "STATE_ROOT_UNAVAILABLE", CRITICAL,
                "configured fulfilment orders root is unavailable",
            )
        ], 0
    anomalies: list[dict[str, Any]] = []
    scanned = 0
    for path in _state_paths(root):
        scanned += 1
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                raise ValueError("state is not an object")
        except (OSError, json.JSONDecodeError, ValueError):
            anomalies.append(_anomaly(
                hashlib.sha256(str(path).encode()).hexdigest()[:12],
                "STATE_FILE_INVALID", CRITICAL,
                "fulfilment state file is unreadable or malformed",
            ))
            continue
        anomalies.extend(audit_state(
            state, path=path, now=now, max_age_days=max_age_days,
            stale_after_hours=stale_after_hours))
        if stale_orders is not None:
            stale = stale_paid_order(
                state, now=now, stale_after_hours=stale_after_hours)
            if stale is not None:
                stale_orders.append({
                    **stale,
                    "state_ref": _state_ref(state, path),
                    "order_id": str(state.get("order_id") or ""),
                    "athlete_id": str(state.get("athlete_id") or ""),
                    "delivery_platform": str(
                        state.get("delivery_platform") or ""),
                })
    return anomalies, scanned


def _artifact(
    *, root: Path, now: datetime, max_age_days: int,
    anomalies: list[dict[str, Any]], scanned: int,
) -> dict[str, Any]:
    return {
        "artifact_type": "fulfillment_state_audit/v1",
        "generated_at": _timestamp(now),
        "root_configured": True,
        "max_age_days": max_age_days,
        "states_scanned": scanned,
        "summary": _summary(anomalies),
        "anomalies": anomalies,
    }


def _summary(anomalies: list[dict[str, Any]]) -> dict[str, int]:
    critical = sum(item["severity"] == CRITICAL for item in anomalies)
    return {
        "anomalies": len(anomalies),
        "critical": critical,
        "warning": len(anomalies) - critical,
        "stale_paid_orders": sum(
            item["code"] == PAID_ORDER_STALE for item in anomalies),
    }


def build_audit_report(
    root: Path, *, now: datetime | None = None, max_age_days: int = 3,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return ``(redacted artifact, private stale paid order records)``."""
    if max_age_days < 1:
        raise ValueError("max_age_days must be at least 1")
    generated_at = now or _utc_now()
    stale_orders: list[dict[str, Any]] = []
    anomalies, scanned = audit_states(
        Path(root).resolve(), now=generated_at, max_age_days=max_age_days,
        stale_after_hours=stale_after_hours, stale_orders=stale_orders)
    artifact = external_state_projection(_artifact(
        root=Path(root).resolve(), now=generated_at,
        max_age_days=max_age_days, anomalies=anomalies, scanned=scanned,
    ))
    return artifact, stale_orders


def build_audit_artifact(
    root: Path, *, now: datetime | None = None, max_age_days: int = 3,
    stale_after_hours: int = PAID_ORDER_SLA_HOURS,
) -> dict[str, Any]:
    """Run one audit and return the same redacted artifact used by the CLI."""
    artifact, _ = build_audit_report(
        root, now=now, max_age_days=max_age_days,
        stale_after_hours=stale_after_hours)
    return artifact


def load_alert_ledger(path: Path) -> tuple[dict[str, Any], str]:
    """Return ``(ledger, status)`` for the stale-order alert ledger.

    A missing file is an empty ledger (``ok``). Unparseable content is reset
    to empty (``reset_corrupt``): at most one repeat alert, after which the
    save overwrites it. Any other read error raises, so the caller sends no
    email rather than re-alerting from a ledger it cannot see.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, "ok"
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return {}, "reset_corrupt"
    alerts = raw.get("alerts") if isinstance(raw, dict) else None
    if not isinstance(alerts, dict):
        return {}, "reset_corrupt"
    return {
        str(ref): dict(entry) for ref, entry in alerts.items()
        if isinstance(entry, dict)
    }, "ok"


def apply_alert_ledger(
    artifact: dict[str, Any], ledger: Mapping[str, Any], *, now: datetime,
) -> tuple[list[str], dict[str, Any]]:
    """Throttle stale paid-order alerts to one per order+status per window.

    A stale order alerts when it has no ledger entry, its status changed
    since the last alert, or the last alert is at least
    ``STALE_ALERT_REPEAT_WINDOW`` old. Otherwise the anomaly stays in the
    artifact, downgraded to a WARNING repeat, so the hourly workflow goes red
    once per order per state per day instead of every hour. Returns the
    state refs that alert now and the next ledger (entries for orders that
    are no longer stale are dropped). Keys are hashed state refs only.
    """
    new_refs: list[str] = []
    next_ledger: dict[str, Any] = {}
    for item in artifact.get("anomalies") or []:
        if item.get("code") != PAID_ORDER_STALE:
            continue
        ref = str(item["state_ref"])
        previous = ledger.get(ref) if isinstance(ledger.get(ref), dict) else None
        last = _parse_time((previous or {}).get("alerted_at"))
        repeat = bool(
            previous
            and previous.get("status") == item.get("status")
            and last is not None
            and now - last < STALE_ALERT_REPEAT_WINDOW
        )
        if repeat:
            item["severity"] = WARNING
            item["alert"] = "repeat_within_24h"
            item["last_alerted_at"] = _timestamp(last)
            next_ledger[ref] = dict(previous)
        else:
            item["severity"] = CRITICAL
            item["alert"] = "new"
            new_refs.append(ref)
            next_ledger[ref] = {
                "status": item.get("status"),
                "alerted_at": _timestamp(now),
            }
    artifact["summary"] = _summary(artifact.get("anomalies") or [])
    return new_refs, next_ledger


def save_alert_ledger(path: Path, ledger: Mapping[str, Any]) -> None:
    """Atomically replace the ledger; raises on any write failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {"version": 1, "alerts": dict(ledger)}, indent=2,
                sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def mark_alert_ledger_unavailable(artifact: dict[str, Any]) -> None:
    """No ledger, no dedupe: every stale finding is CRITICAL and unemailed."""
    for item in artifact.get("anomalies") or []:
        if item.get("code") != PAID_ORDER_STALE:
            continue
        item["severity"] = CRITICAL
        item["alert"] = "ledger_unavailable"
        item["coach_email"] = "suppressed_ledger_unavailable"
        item.pop("last_alerted_at", None)
    artifact["alert_ledger"] = "failed"
    artifact["summary"] = _summary(artifact.get("anomalies") or [])


def _print_table(artifact: Mapping[str, Any]) -> None:
    anomalies = artifact.get("anomalies") or []
    print(f"{'SEVERITY':8}  {'STATE REF':12}  {'CODE':31}  DETAIL")
    print(f"{'-' * 8}  {'-' * 12}  {'-' * 31}  {'-' * 48}")
    if not anomalies:
        print("OK        -             NONE                             no anomalies")
        return
    for item in anomalies:
        age = f" ({item['age_days']}d)" if "age_days" in item else ""
        if "hours_since_payment" in item:
            age = f" ({item['hours_since_payment']}h since payment)"
        print(
            f"{item['severity']:8}  {item['state_ref']:12}  "
            f"{item['code']:31}  {item['detail']}{age}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="orders root or one state file")
    parser.add_argument("--max-age-days", type=int, default=3)
    parser.add_argument(
        "--stale-after-hours", type=int, default=PAID_ORDER_SLA_HOURS,
        help="paid orders still open after this many hours are CRITICAL")
    parser.add_argument("--out", type=Path, help="JSON artifact path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_age_days < 1:
        build_parser().error("--max-age-days must be at least 1")
    now = _utc_now()
    root = (args.root or _configured_root(os.environ)).resolve()
    out = args.out or _default_out(now)
    if args.stale_after_hours < 1:
        build_parser().error("--stale-after-hours must be at least 1")
    projected = build_audit_artifact(
        root, now=now, max_age_days=args.max_age_days,
        stale_after_hours=args.stale_after_hours)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(projected, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _print_table(projected)
    print(f"JSON artifact: {out}")
    return 1 if projected["summary"]["critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
