import json
from datetime import datetime, timedelta, timezone

import pytest

from tools import audit_fulfillment_states as audit


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _state(**overrides):
    state = {
        "order_id": "synthetic-order",
        "status": "GENERATED",
        "generation_revision": 1,
        "updated_at": _iso(NOW),
        "approval": None,
        "model_seal": None,
        "release_manifest_digest": None,
        "d2_pending_requirements": {},
    }
    state.update(overrides)
    return state


def _write(root, name, state):
    path = root / name / "fulfillment_status.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(state))
    return path


def _codes(state, tmp_path):
    path = _write(tmp_path, "order", state)
    return {
        item["code"] for item in audit.audit_state(
            state, path=path, now=NOW, max_age_days=3)
    }


def test_flags_old_blocked_review(tmp_path):
    codes = _codes(_state(
        status="BLOCKED_REVIEW", updated_at=_iso(NOW - timedelta(days=4))), tmp_path)
    assert "BLOCKED_REVIEW_OLD" in codes


def test_drill_orders_skip_age_noise_but_not_criticals(tmp_path):
    seal = "a" * 64
    codes = _codes(_state(
        order_id="drill-20260811",
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=10)),
        d2_pending_requirements={
            "D2_THRESHOLD": {
                "requested_at": _iso(NOW - timedelta(days=10)),
            }
        },
        approval={"revision": 1},
        model_seal=seal,
        release_manifest_digest="b" * 64,
    ), tmp_path)
    assert "BLOCKED_REVIEW_OLD" not in codes
    assert "D2_READBACK_OLD" not in codes
    assert "UNSEALED_APPROVAL" in codes


def test_cancelled_drill_with_no_worker_to_stop_is_clean(tmp_path):
    codes = _codes(_state(
        order_id="drill-20260811", status="CANCELLED",
        cancellation={
            "worker_stop_acknowledged": True,
            "worker_stop_basis": "no application attempt or landed operation",
        },
    ), tmp_path)
    assert "CANCELLED_STOP_UNACKNOWLEDGED" not in codes


def test_flags_applying_with_expired_grant_and_lease(tmp_path):
    codes = _codes(_state(
        status="APPLYING",
        application_attempt={
            "execution_grant": {"expires_at": _iso(NOW - timedelta(minutes=1))},
            "lease": {"expires_at": _iso(NOW - timedelta(seconds=1))},
        },
    ), tmp_path)
    assert {"APPLYING_EXPIRED_GRANT", "APPLYING_EXPIRED_LEASE"} <= codes


def test_flags_cancelled_without_worker_stop_acknowledgement(tmp_path):
    codes = _codes(_state(
        status="CANCELLED", cancellation={"worker_stop_acknowledged": False}), tmp_path)
    assert "CANCELLED_STOP_UNACKNOWLEDGED" in codes


def test_flags_unsealed_approval(tmp_path):
    codes = _codes(_state(
        status="APPROVED", approval={"revision": 1}), tmp_path)
    assert "UNSEALED_APPROVAL" in codes


def test_accepts_seal_bound_approval(tmp_path):
    seal = "a" * 64
    digest = "b" * 64
    codes = _codes(_state(
        status="APPROVED", model_seal=seal, release_manifest_digest=digest,
        approval={
            "revision": 1, "model_seal": seal,
            "release_manifest_digest": digest,
        },
    ), tmp_path)
    assert "UNSEALED_APPROVAL" not in codes


def test_flags_old_pending_d2_readback(tmp_path):
    codes = _codes(_state(
        d2_pending_requirements={
            "D2_THRESHOLD": {
                "kind": "worker-readback",
                "requested_at": _iso(NOW - timedelta(days=5)),
            }
        }), tmp_path)
    assert "D2_READBACK_OLD" in codes


def test_cli_writes_projected_artifact_and_exits_on_critical(tmp_path, monkeypatch):
    sensitive = "real-person-secret-value"
    root = tmp_path / "orders"
    _write(root, "order", _state(
        status="CANCELLED", athlete_name=sensitive,
        cancellation={"worker_stop_acknowledged": False},
    ))
    out = tmp_path / "audit.json"
    monkeypatch.setattr(audit, "_utc_now", lambda: NOW)
    assert audit.main([
        "--root", str(root), "--out", str(out),
    ]) == 1
    artifact_text = out.read_text()
    assert sensitive not in artifact_text
    assert json.loads(artifact_text)["summary"]["critical"] == 1


# --- Stale paid orders (2026-09-22 incident: a paid order sat in
# BLOCKED_REVIEW and nothing but the first coach email noticed) ---------------

PAID_ORDER_ID = "cs_live_a1PrivateCheckout"


def _paid_state(hours_ago=26, **overrides):
    paid_at = NOW - timedelta(hours=hours_ago)
    state = _state(
        order_id=PAID_ORDER_ID,
        athlete_id="jane_doe",
        delivery_platform="trainingpeaks",
        status="BLOCKED_REVIEW",
        legacy=False,
        # updated_at moves with every event; the payment clock must not.
        updated_at=_iso(NOW - timedelta(minutes=5)),
        blocking_issues=[
            {"id": "FTP_ESTIMATED", "waivable": False},
            {"id": "R05", "waivable": True},
        ],
        history=[
            {"at": _iso(paid_at), "event": "GENERATED"},
            {"at": _iso(NOW - timedelta(minutes=5)), "event": "REGENERATED"},
        ],
    )
    state.update(overrides)
    return state


def _stale(artifact):
    return [item for item in artifact["anomalies"]
            if item["code"] == audit.PAID_ORDER_STALE]


def test_stuck_paid_order_fires_critical_with_masked_ref(tmp_path):
    state = _paid_state()
    _write(tmp_path, "order", state)

    artifact, private = audit.build_audit_report(tmp_path, now=NOW)

    [item] = _stale(artifact)
    assert item["severity"] == audit.CRITICAL
    assert item["state_ref"] == audit.order_ref(PAID_ORDER_ID)
    assert item["status"] == "BLOCKED_REVIEW"
    assert item["hours_since_payment"] == 26
    assert item["blocker_count"] == 2
    assert item["sla_hours"] == 24
    assert item["order_kind"] == "stripe_live_checkout"
    assert artifact["summary"]["stale_paid_orders"] == 1
    assert artifact["summary"]["critical"] == 1
    # Public artifact (printed in a public repo's workflow log) never
    # carries the raw order id or athlete id; the private record does.
    text = json.dumps(artifact)
    assert PAID_ORDER_ID not in text and "jane_doe" not in text
    [record] = private
    assert record["order_id"] == PAID_ORDER_ID
    assert record["athlete_id"] == "jane_doe"
    assert record["blocker_ids"] == ["FTP_ESTIMATED", "R05"]


def test_paid_order_inside_sla_does_not_fire(tmp_path):
    _write(tmp_path, "order", _paid_state(hours_ago=23))
    artifact, private = audit.build_audit_report(tmp_path, now=NOW)
    assert _stale(artifact) == [] and private == []


def test_every_open_status_counts_as_stuck(tmp_path):
    for status in ("GENERATED", "APPROVED", "APPLIED", "APPLIED_ATTESTED"):
        root = tmp_path / status
        _write(root, "order", _paid_state(status=status, blocking_issues=[]))
        [item] = _stale(audit.build_audit_artifact(root, now=NOW))
        assert item["status"] == status
        assert item["blocker_count"] == 0


def test_confirmed_paid_order_does_not_fire(tmp_path):
    _write(tmp_path, "order", _paid_state(status="CONFIRMED"))
    assert _stale(audit.build_audit_artifact(tmp_path, now=NOW)) == []


def test_externally_fulfilled_paid_order_does_not_fire(tmp_path):
    _write(tmp_path, "order", _paid_state(
        status="FULFILLED_EXTERNALLY",
        external_fulfillment={
            "coach": "Matti", "at": _iso(NOW), "reason": "hand-built",
            "from_status": "BLOCKED_REVIEW"},
    ))
    artifact = audit.build_audit_artifact(tmp_path, now=NOW)
    assert artifact["summary"]["anomalies"] == 0


def test_cancelled_paid_order_does_not_fire(tmp_path):
    _write(tmp_path, "order", _paid_state(
        status="CANCELLED",
        cancellation={"worker_stop_acknowledged": True},
    ))
    artifact = audit.build_audit_artifact(tmp_path, now=NOW)
    assert artifact["summary"]["anomalies"] == 0


def test_synthetic_and_unpaid_identities_never_fire(tmp_path):
    for name, overrides in {
        "drill": {"order_id": "drill-20260922"},
        "canary": {"order_id": "canary_0123abcd"},
        "manual": {"order_id": "manual_0123abcd"},
        "stripe-test": {"order_id": "cs_test_a1Fixture"},
        "test": {"order_id": "test_session"},
        "legacy": {"order_id": "legacy_0123abcd", "legacy": True},
        "bound-legacy": {"legacy": True},
    }.items():
        _write(tmp_path, name, _paid_state(hours_ago=24 * 30, **overrides))
    artifact = audit.build_audit_artifact(tmp_path, now=NOW)
    assert _stale(artifact) == []


def test_woocommerce_order_numbers_are_paid_orders(tmp_path):
    _write(tmp_path, "order", _paid_state(order_id="10423"))
    [item] = _stale(audit.build_audit_artifact(tmp_path, now=NOW))
    assert item["order_kind"] == "woocommerce_order"


def test_alert_ledger_allows_one_alert_per_order_status_per_day(tmp_path):
    _write(tmp_path, "order", _paid_state())
    ref = audit.order_ref(PAID_ORDER_ID)

    first = audit.build_audit_artifact(tmp_path, now=NOW)
    new, ledger = audit.apply_alert_ledger(first, {}, now=NOW)
    assert new == [ref]
    assert _stale(first)[0]["alert"] == "new"
    assert first["summary"]["critical"] == 1
    assert ledger == {ref: {"status": "BLOCKED_REVIEW", "alerted_at": _iso(NOW)}}

    # Next hourly run: still listed, but a WARNING repeat (workflow stays green).
    later = NOW + timedelta(hours=1)
    second = audit.build_audit_artifact(tmp_path, now=later)
    new, ledger_2 = audit.apply_alert_ledger(second, ledger, now=later)
    assert new == []
    [item] = _stale(second)
    assert item["severity"] == audit.WARNING
    assert item["alert"] == "repeat_within_24h"
    assert item["last_alerted_at"] == _iso(NOW)
    assert second["summary"] == {
        "anomalies": 1, "critical": 0, "warning": 1, "stale_paid_orders": 1}
    assert ledger_2 == ledger

    # Just short of 24h: still suppressed. At 24h: alerts again.
    edge = NOW + timedelta(hours=23, minutes=59)
    assert audit.apply_alert_ledger(
        audit.build_audit_artifact(tmp_path, now=edge), ledger, now=edge)[0] == []
    day = NOW + timedelta(hours=24)
    new, _ = audit.apply_alert_ledger(
        audit.build_audit_artifact(tmp_path, now=day), ledger, now=day)
    assert new == [ref]


def test_alert_ledger_realerts_on_status_change_and_prunes_resolved(tmp_path):
    ref = audit.order_ref(PAID_ORDER_ID)
    ledger = {ref: {"status": "BLOCKED_REVIEW", "alerted_at": _iso(NOW)}}
    _write(tmp_path, "order", _paid_state(status="APPROVED"))
    moved = audit.build_audit_artifact(tmp_path, now=NOW)
    new, next_ledger = audit.apply_alert_ledger(moved, ledger, now=NOW)
    assert new == [ref]
    assert next_ledger[ref]["status"] == "APPROVED"

    resolved = tmp_path / "resolved"
    _write(resolved, "order", _paid_state(status="CONFIRMED"))
    artifact = audit.build_audit_artifact(resolved, now=NOW)
    new, next_ledger = audit.apply_alert_ledger(artifact, ledger, now=NOW)
    assert new == [] and next_ledger == {}


def test_alert_ledger_round_trips_and_reports_corruption(tmp_path):
    path = tmp_path / "ledger.json"
    assert audit.load_alert_ledger(path) == ({}, "ok")
    audit.save_alert_ledger(path, {"abc": {"status": "GENERATED", "alerted_at": "x"}})
    assert audit.load_alert_ledger(path) == (
        {"abc": {"status": "GENERATED", "alerted_at": "x"}}, "ok")
    assert [item.name for item in tmp_path.iterdir()] == ["ledger.json"]
    path.write_text("{not json")
    assert audit.load_alert_ledger(path) == ({}, "reset_corrupt")


def test_alert_ledger_read_errors_raise_instead_of_resetting(tmp_path):
    path = tmp_path / "ledger.json"
    path.mkdir()
    with pytest.raises(OSError):
        audit.load_alert_ledger(path)


def test_alert_ledger_save_failure_raises_and_leaves_no_temp_file(
        tmp_path, monkeypatch):
    path = tmp_path / "ledger.json"

    def fail_replace(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(audit.os, "replace", fail_replace)
    with pytest.raises(OSError):
        audit.save_alert_ledger(path, {"abc": {"status": "GENERATED"}})
    assert list(tmp_path.iterdir()) == []


def test_ledger_unavailable_keeps_every_stale_order_critical(tmp_path):
    _write(tmp_path, "order", _paid_state())
    artifact = audit.build_audit_artifact(tmp_path, now=NOW)
    ref = audit.order_ref(PAID_ORDER_ID)
    audit.apply_alert_ledger(
        artifact, {ref: {"status": "BLOCKED_REVIEW", "alerted_at": _iso(NOW)}},
        now=NOW + timedelta(hours=1))
    assert artifact["summary"]["critical"] == 0  # downgraded as a repeat
    audit.mark_alert_ledger_unavailable(artifact)
    [item] = _stale(artifact)
    assert item["severity"] == audit.CRITICAL
    assert item["alert"] == "ledger_unavailable"
    assert "last_alerted_at" not in item
    assert artifact["alert_ledger"] == "failed"
    assert artifact["summary"]["critical"] == 1


def test_list_open_paid_orders_includes_fresh_and_stale_without_raw_ids(tmp_path):
    _write(tmp_path, "stale", _paid_state())
    _write(tmp_path, "fresh", _paid_state(
        order_id="cs_live_b2Fresh", hours_ago=2, status="GENERATED",
        blocking_issues=[]))
    _write(tmp_path, "done", _paid_state(order_id="cs_live_c3Done", status="CONFIRMED"))
    _write(tmp_path, "drill", _paid_state(order_id="drill-20260922"))

    listed = audit.list_open_paid_orders(tmp_path, now=NOW)

    assert [(item["order_ref"], item["stale"]) for item in listed] == [
        (audit.order_ref(PAID_ORDER_ID), True),
        (audit.order_ref("cs_live_b2Fresh"), False),
    ]
    assert listed[0]["hours_since_payment"] == 26
    assert listed[0]["blocker_count"] == 2
    text = json.dumps(listed)
    assert "cs_live_" not in text and "jane_doe" not in text


def test_cli_exits_red_on_stale_paid_order(tmp_path, monkeypatch):
    root = tmp_path / "orders"
    _write(root, "order", _paid_state())
    out = tmp_path / "audit.json"
    monkeypatch.setattr(audit, "_utc_now", lambda: NOW)
    assert audit.main(["--root", str(root), "--out", str(out)]) == 1
    assert json.loads(out.read_text())["summary"]["stale_paid_orders"] == 1
