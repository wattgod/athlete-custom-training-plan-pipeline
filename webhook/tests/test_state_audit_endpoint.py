import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "")

import app as webhook_app


SECRET = "state-audit-test-secret"


@pytest.fixture
def audit_client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "deliveries" / "orders").mkdir(parents=True)
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data))
    monkeypatch.setattr(
        webhook_app, "DELIVERIES_DIR", str(data / "deliveries"))
    monkeypatch.setattr(webhook_app, "CRON_SECRET", SECRET)
    webhook_app.app.config["TESTING"] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client(), data / "deliveries" / "orders"


def _post(client, secret=SECRET):
    headers = {"X-Cron-Secret": secret} if secret is not None else {}
    return client.post("/api/cron/state-audit", json={}, headers=headers)


def _minimal_state(order_id, **overrides):
    state = {
        "order_id": order_id,
        "status": "GENERATED",
        "generation_revision": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "approval": None,
        "model_seal": None,
        "release_manifest_digest": None,
        "d2_pending_requirements": {},
    }
    state.update(overrides)
    return state


def _write(root, order_id, state):
    path = root / order_id / "fulfillment_status.json"
    path.parent.mkdir()
    path.write_text(json.dumps(state))
    return path


def test_state_audit_requires_cron_auth(audit_client):
    client, _ = audit_client
    assert _post(client, secret=None).status_code == 401
    assert _post(client, secret="wrong").status_code == 401


def test_state_audit_returns_redacted_summary(audit_client):
    client, root = audit_client
    sensitive = "real.person+private@example.com"
    path = root / "broken" / "fulfillment_status.json"
    path.parent.mkdir()
    path.write_text('{"private": "' + sensitive + '"')

    response = _post(client)

    assert response.status_code == 500
    body = response.get_data(as_text=True)
    assert sensitive not in body
    data = response.get_json()
    assert data["artifact_type"] == "fulfillment_state_audit/v1"
    assert data["summary"]["critical"] == 1
    assert data["anomalies"][0]["code"] == "STATE_FILE_INVALID"


def test_state_audit_critical_returns_error_status(audit_client):
    client, root = audit_client
    _write(root, "order", _minimal_state(
        "synthetic-order", status="CANCELLED",
        cancellation={"worker_stop_acknowledged": False}))

    response = _post(client)

    assert response.status_code == 500
    assert response.get_json()["summary"]["critical"] == 1


def test_state_audit_handles_cancelled_drill_without_hiding_critical(audit_client):
    client, root = audit_client
    _write(root, "clean-drill", _minimal_state(
        "drill-20260811", status="CANCELLED",
        cancellation={"worker_stop_acknowledged": True}))
    clean = _post(client)
    assert clean.status_code == 200
    assert clean.get_json()["summary"]["anomalies"] == 0

    _write(root, "critical-drill", _minimal_state(
        "drill-20260812", status="APPROVED", approval={"revision": 1}))
    critical = _post(client)
    assert critical.status_code == 500
    codes = {item["code"] for item in critical.get_json()["anomalies"]}
    assert "UNSEALED_APPROVAL" in codes
