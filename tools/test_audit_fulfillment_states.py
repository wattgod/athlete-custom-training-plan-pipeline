import json
from datetime import datetime, timedelta, timezone

from tools import audit_fulfillment_states as audit
from webhook.provider_revenue import provider_record_key


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
RECORD_KEY_SECRET = "audit-ledger-test-secret"


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _state(**overrides):
    state = {
        "schema_version": 2,
        "order_id": "manual_fixture_order",
        "legacy": False,
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


def test_warning_projects_same_checkout_key_as_provider_ledger(tmp_path):
    order_id = "cs_live_privateMarker123"
    state = _state(
        order_id=order_id,
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    )
    _write(tmp_path, "order", state)

    artifact = audit.build_audit_artifact(
        tmp_path, now=NOW, max_age_days=3,
        record_key_secret=RECORD_KEY_SECRET,
    )

    warning = artifact["anomalies"][0]
    assert warning["state_ref"] == audit._state_ref(
        state, tmp_path / "order" / "fulfillment_status.json")
    assert warning["ledger_checkout_session_record_key"] == provider_record_key(
        RECORD_KEY_SECRET, "checkout_session", order_id)
    assert warning["ledger_key_status"] == "candidate_provider_match_required"
    assert warning["legacy"] is False
    assert order_id not in json.dumps(artifact)


def test_distinct_bound_checkouts_have_distinct_keys(tmp_path):
    for name, order_id in (
        ("one", "cs_live_privateOne123"),
        ("two", "cs_test_privateTwo456"),
    ):
        _write(tmp_path, name, _state(
            order_id=order_id,
            status="BLOCKED_REVIEW",
            updated_at=_iso(NOW - timedelta(days=4)),
        ))

    artifact = audit.build_audit_artifact(
        tmp_path, now=NOW, record_key_secret=RECORD_KEY_SECRET)
    keys = {
        item["ledger_checkout_session_record_key"]
        for item in artifact["anomalies"]
    }
    assert len(keys) == 2
    assert None not in keys


def test_missing_secret_leaves_join_key_explicitly_unavailable(tmp_path):
    _write(tmp_path, "order", _state(
        order_id="cs_live_privateMarker123",
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    ))

    warning = audit.build_audit_artifact(
        tmp_path, now=NOW, record_key_secret="")["anomalies"][0]

    assert warning["ledger_checkout_session_record_key"] is None
    assert warning["ledger_key_status"] == "unavailable_missing_secret"
    assert warning["legacy"] is False


def test_manual_v2_state_has_no_checkout_join_key(tmp_path):
    raw_order_id = "manual_0123456789abcdef"
    _write(tmp_path, "manual", _state(
        order_id=raw_order_id,
        legacy=False,
        delivery_platform="manual",
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    ))

    artifact = audit.build_audit_artifact(
        tmp_path, now=NOW, record_key_secret=RECORD_KEY_SECRET)
    warning = artifact["anomalies"][0]

    assert warning["ledger_checkout_session_record_key"] is None
    assert warning["ledger_key_status"] == "unavailable_non_checkout_binding"
    assert warning["legacy"] is False
    assert raw_order_id not in json.dumps(artifact)


def test_unbound_legacy_state_does_not_infer_binding_from_identifier(tmp_path):
    raw_order_id = "cs_live_looksLikeCheckoutButIsLegacy"
    _write(tmp_path, "legacy", _state(
        order_id=raw_order_id,
        legacy=True,
        legacy_binding=None,
        delivery_platform="manual",
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    ))

    artifact = audit.build_audit_artifact(
        tmp_path, now=NOW, record_key_secret=RECORD_KEY_SECRET)
    warning = artifact["anomalies"][0]

    assert warning["ledger_checkout_session_record_key"] is None
    assert warning["ledger_key_status"] == "unavailable_unbound_legacy"
    assert warning["legacy"] is True
    assert not ({"paid", "synthetic", "delivered"} & warning.keys())
    assert raw_order_id not in json.dumps(artifact)


def test_bound_legacy_state_uses_explicit_ledger_binding(tmp_path):
    raw_order_id = "legacy-private-marker"
    checkout_id = "cs_live_boundPrivateMarker123"
    _write(tmp_path, "legacy", _state(
        order_id=raw_order_id,
        legacy=True,
        legacy_binding={
            "ledger_order_id": checkout_id,
            "coach": "coach-private-marker",
            "at": _iso(NOW - timedelta(days=5)),
        },
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    ))

    artifact = audit.build_audit_artifact(
        tmp_path, now=NOW, record_key_secret=RECORD_KEY_SECRET)
    warning = artifact["anomalies"][0]
    encoded = json.dumps(artifact)

    assert warning["ledger_checkout_session_record_key"] == provider_record_key(
        RECORD_KEY_SECRET, "checkout_session", checkout_id)
    assert warning["ledger_key_status"] == "candidate_provider_match_required"
    assert warning["legacy"] is True
    for forbidden in (raw_order_id, checkout_id, "coach-private-marker"):
        assert forbidden not in encoded


def test_legacy_binding_must_be_a_checkout_session_identifier(tmp_path):
    _write(tmp_path, "legacy", _state(
        order_id="legacy-private-marker",
        legacy=True,
        legacy_binding={"ledger_order_id": "woocommerce-order-12345"},
        status="BLOCKED_REVIEW",
        updated_at=_iso(NOW - timedelta(days=4)),
    ))

    warning = audit.build_audit_artifact(
        tmp_path, now=NOW,
        record_key_secret=RECORD_KEY_SECRET)["anomalies"][0]

    assert warning["ledger_checkout_session_record_key"] is None
    assert warning["ledger_key_status"] == "unavailable_non_checkout_binding"
    assert warning["legacy"] is True
