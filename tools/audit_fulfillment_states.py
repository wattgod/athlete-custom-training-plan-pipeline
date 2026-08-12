#!/usr/bin/env python3
"""Audit durable fulfilment states for stalled or unsafe lifecycle conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from webhook.fulfillment_state import external_state_projection  # noqa: E402


CRITICAL = "CRITICAL"
WARNING = "WARNING"
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


def _state_ref(state: Mapping[str, Any], path: Path) -> str:
    source = str(state.get("order_id") or path.parent.name or path.name)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


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
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    ref = _state_ref(state, path)
    status = str(state.get("status") or "")
    threshold = timedelta(days=max_age_days)
    updated = _parse_time(state.get("updated_at"))

    if status == "BLOCKED_REVIEW" and updated is not None and now - updated > threshold:
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
    if isinstance(pending, dict) and pending:
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
) -> tuple[list[dict[str, Any]], int]:
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
            state, path=path, now=now, max_age_days=max_age_days))
    return anomalies, scanned


def _artifact(
    *, root: Path, now: datetime, max_age_days: int,
    anomalies: list[dict[str, Any]], scanned: int,
) -> dict[str, Any]:
    critical = sum(item["severity"] == CRITICAL for item in anomalies)
    return {
        "artifact_type": "fulfillment_state_audit/v1",
        "generated_at": _timestamp(now),
        "root_configured": True,
        "max_age_days": max_age_days,
        "states_scanned": scanned,
        "summary": {
            "anomalies": len(anomalies),
            "critical": critical,
            "warning": len(anomalies) - critical,
        },
        "anomalies": anomalies,
    }


def _print_table(artifact: Mapping[str, Any]) -> None:
    anomalies = artifact.get("anomalies") or []
    print(f"{'SEVERITY':8}  {'STATE REF':12}  {'CODE':31}  DETAIL")
    print(f"{'-' * 8}  {'-' * 12}  {'-' * 31}  {'-' * 48}")
    if not anomalies:
        print("OK        -             NONE                             no anomalies")
        return
    for item in anomalies:
        age = f" ({item['age_days']}d)" if "age_days" in item else ""
        print(
            f"{item['severity']:8}  {item['state_ref']:12}  "
            f"{item['code']:31}  {item['detail']}{age}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="orders root or one state file")
    parser.add_argument("--max-age-days", type=int, default=3)
    parser.add_argument("--out", type=Path, help="JSON artifact path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_age_days < 1:
        build_parser().error("--max-age-days must be at least 1")
    now = _utc_now()
    root = (args.root or _configured_root(os.environ)).resolve()
    out = args.out or _default_out(now)
    anomalies, scanned = audit_states(
        root, now=now, max_age_days=args.max_age_days)
    projected = external_state_projection(_artifact(
        root=root, now=now, max_age_days=args.max_age_days,
        anomalies=anomalies, scanned=scanned,
    ))
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
