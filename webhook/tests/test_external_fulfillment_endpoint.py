"""Operator endpoints for closing a paid order fulfilled outside the pipeline,
and the fulfilment truth the Morning Console reads from /api/intel-stats."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "")

import app as webhook_app
from fulfillment_state import load, write_generation


SECRET = "external-fulfilment-test-secret"
ORDER_ID = "cs_live_a1PrivateCheckout"


@pytest.fixture
def ops_client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "deliveries" / "orders").mkdir(parents=True)
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data / "deliveries"))
    monkeypatch.setattr(webhook_app, "CRON_SECRET", SECRET)
    monkeypatch.setenv("CRON_SECRET", SECRET)
    sent = []
    monkeypatch.setattr(
        webhook_app, "_send_email",
        lambda *args, **kwargs: sent.append((args, kwargs)) or True)
    webhook_app.app.config["TESTING"] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client(), data, sent


def _blocked_order(data, order_id=ORDER_ID):
    path = data / "deliveries" / "orders" / order_id / "fulfillment_status.json"
    write_generation(
        path, "jane_doe", [{
            "id": "FTP_ESTIMATED", "source": "intake", "severity": "CRITICAL",
            "message": "FTP was estimated from weight.",
        }], order_id=order_id, delivery_platform="trainingpeaks")
    return path


def _close(client, payload, secret=SECRET):
    headers = {"X-Cron-Secret": secret} if secret is not None else {}
    return client.post(
        f"/api/fulfillment/{ORDER_ID}/transition", json=payload, headers=headers)


CLOSE = {
    "to": "FULFILLED_EXTERNALLY",
    "coach": "Matti",
    "reason": "Hand-built 16-week TrainingPeaks calendar, placed 2026-09-23",
    "evidence": "TP weeks 1-16 placed by hand",
}


def test_close_requires_operator_secret(ops_client):
    client, data, _ = ops_client
    _blocked_order(data)
    assert _close(client, CLOSE, secret=None).status_code == 401
    assert _close(client, CLOSE, secret="wrong").status_code == 401


def test_close_records_external_fulfilment_and_sends_nothing(ops_client):
    client, data, sent = ops_client
    path = _blocked_order(data)

    response = _close(client, CLOSE)

    assert response.status_code == 200
    assert response.get_json() == {
        "order_id": ORDER_ID, "athlete_id": "jane_doe",
        "status": "FULFILLED_EXTERNALLY", "generation_revision": 1,
    }
    state = load(path)
    assert state["external_fulfillment"]["reason"] == CLOSE["reason"]
    assert state["external_fulfillment"]["evidence"] == CLOSE["evidence"]
    assert state["external_fulfillment"]["coach"] == "Matti"
    assert state["history"][-1]["to_status"] == "FULFILLED_EXTERNALLY"
    assert sent == []

    status = client.get(
        f"/api/fulfillment/{ORDER_ID}/status", headers={"X-Cron-Secret": SECRET})
    assert status.status_code == 200
    body = status.get_json()
    assert body["status"] == "FULFILLED_EXTERNALLY"
    assert body["external_fulfillment"]["from_status"] == "BLOCKED_REVIEW"

    # Idempotent retry; the confirmation route still refuses it.
    assert _close(client, CLOSE).status_code == 200
    confirm = client.post(
        f"/api/confirm/{ORDER_ID}", headers={"X-Cron-Secret": SECRET})
    assert confirm.status_code == 409
    assert sent == []


def test_close_without_reason_is_refused(ops_client):
    client, data, _ = ops_client
    path = _blocked_order(data)
    response = _close(client, {**CLOSE, "reason": ""})
    assert response.status_code == 409
    assert "reason is required" in response.get_json()["error"]
    assert load(path)["status"] == "BLOCKED_REVIEW"


def test_closed_order_leaves_the_stale_audit(ops_client):
    client, data, sent = ops_client
    path = _blocked_order(data)
    raw = json.loads(path.read_text())
    raw["history"][0]["at"] = "2026-09-01T00:00:00Z"
    path.write_text(json.dumps(raw))
    before = client.post(
        "/api/cron/state-audit", json={}, headers={"X-Cron-Secret": SECRET})
    assert before.status_code == 500
    assert before.get_json()["summary"]["stale_paid_orders"] == 1

    assert _close(client, CLOSE).status_code == 200

    after = client.post(
        "/api/cron/state-audit", json={}, headers={"X-Cron-Secret": SECRET})
    assert after.status_code == 200
    assert after.get_json()["summary"]["stale_paid_orders"] == 0


def test_intel_stats_reports_fulfilment_status_not_just_processing(ops_client):
    client, data, _ = ops_client
    _blocked_order(data)
    logs = data / ".logs"
    logs.mkdir()
    (logs / f"{datetime.now():%Y-%m}.jsonl").write_text(json.dumps({
        "timestamp": datetime.now().isoformat(), "order_id": ORDER_ID,
        "product_type": "training_plan", "email": "jane@real.test",
        "name": "Jane", "success": True,
    }) + "\n")

    response = client.get(
        "/api/intel-stats?hours=24", headers={"X-Cron-Secret": SECRET})

    assert response.status_code == 200
    body = response.get_json()
    [order] = body["orders"]
    assert order["success"] is True
    assert order["fulfillment_status"] == "BLOCKED_REVIEW"
    assert order["fulfillment_open"] is True
    assert order["blocker_count"] == 1
    [open_order] = body["open_paid_orders"]
    assert open_order["order_ref"] == order["order_ref"]
    assert open_order["status"] == "BLOCKED_REVIEW"
    assert open_order["stale"] is False
    assert ORDER_ID not in json.dumps(body["open_paid_orders"])

    assert _close(client, CLOSE).status_code == 200
    body = client.get(
        "/api/intel-stats?hours=24", headers={"X-Cron-Secret": SECRET}).get_json()
    assert body["orders"][0]["fulfillment_status"] == "FULFILLED_EXTERNALLY"
    assert body["orders"][0]["fulfillment_open"] is False
    assert body["open_paid_orders"] == []
