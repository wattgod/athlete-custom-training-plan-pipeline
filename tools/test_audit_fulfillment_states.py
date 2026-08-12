import json
from datetime import datetime, timedelta, timezone

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
