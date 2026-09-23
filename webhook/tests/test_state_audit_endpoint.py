import json
import os
import sys
from datetime import datetime, timedelta, timezone
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


# --- Stale paid orders --------------------------------------------------------

PAID_ORDER_ID = "cs_live_a1PrivateCheckout"


def _paid_state(order_id=PAID_ORDER_ID, hours_ago=26, **overrides):
    paid_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    fields = {
        "athlete_id": "jane_doe",
        "delivery_platform": "trainingpeaks",
        "status": "BLOCKED_REVIEW",
        "legacy": False,
        "blocking_issues": [{"id": "FTP_ESTIMATED"}, {"id": "R05"}],
        "history": [{"at": paid_at.isoformat(), "event": "GENERATED"}],
    }
    fields.update(overrides)
    return _minimal_state(order_id, **fields)


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []

    def fake_send(to, subject, body, *args, **kwargs):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(webhook_app, "NOTIFICATION_EMAIL", "coach@example.test")
    monkeypatch.setattr(webhook_app, "RESEND_API_KEY", "re_fixture")
    monkeypatch.setattr(webhook_app, "_send_email", fake_send)
    return sent


def test_stale_paid_order_goes_red_and_emails_coach_once(audit_client, sent_emails):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())

    first = _post(client)

    assert first.status_code == 500
    data = first.get_json()
    [item] = data["anomalies"]
    assert item["code"] == "PAID_ORDER_STALE"
    assert item["severity"] == "CRITICAL"
    assert item["status"] == "BLOCKED_REVIEW"
    assert item["hours_since_payment"] == 26
    assert item["blocker_count"] == 2
    assert item["alert"] == "new"
    assert item["coach_email"] == "sent"
    # Response is printed in the public workflow log: hashed ref only.
    body = first.get_data(as_text=True)
    assert PAID_ORDER_ID not in body and "jane_doe" not in body

    [email] = sent_emails
    assert email["to"] == "coach@example.test"
    assert email["subject"].startswith("[GG] OVERDUE: paid order ")
    assert item["state_ref"] in email["subject"]
    assert PAID_ORDER_ID not in email["subject"]
    assert f"Order:           {PAID_ORDER_ID}" in email["body"]
    assert "Blockers:        2 (FTP_ESTIMATED, R05)" in email["body"]
    assert (f"/api/fulfillment/{PAID_ORDER_ID}/transition" in email["body"])
    assert '"to": "FULFILLED_EXTERNALLY"' in email["body"]

    # The hourly re-run the same day stays listed but green, with no email.
    second = _post(client)
    assert second.status_code == 200
    [repeat] = second.get_json()["anomalies"]
    assert repeat["severity"] == "WARNING"
    assert repeat["alert"] == "repeat_within_24h"
    assert len(sent_emails) == 1


def test_stale_alert_repeats_after_a_day(audit_client, sent_emails):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())
    assert _post(client).status_code == 500
    ledger_path = webhook_app._stale_alert_ledger_path()
    ledger = json.loads(ledger_path.read_text())
    [entry] = ledger["alerts"].values()
    entry["alerted_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    ledger_path.write_text(json.dumps(ledger))

    assert _post(client).status_code == 500
    assert len(sent_emails) == 2
    # The ledger keeps hashed refs only.
    assert PAID_ORDER_ID not in ledger_path.read_text()


def test_email_failure_still_alerts_once_via_red_run(
        audit_client, sent_emails, monkeypatch):
    client, root = audit_client
    monkeypatch.setattr(webhook_app, "_send_email", lambda *a, **k: False)
    _write(root, PAID_ORDER_ID, _paid_state())
    first = _post(client)
    assert first.status_code == 500
    assert first.get_json()["anomalies"][0]["coach_email"] == "failed"
    assert _post(client).status_code == 200


@pytest.mark.parametrize("closed", [
    {"status": "CONFIRMED"},
    {"status": "CANCELLED", "cancellation": {"worker_stop_acknowledged": True}},
    {"status": "FULFILLED_EXTERNALLY", "external_fulfillment": {
        "coach": "Matti", "at": "2026-09-23T00:00:00Z",
        "reason": "hand-built", "from_status": "BLOCKED_REVIEW"}},
], ids=["confirmed", "cancelled", "fulfilled-externally"])
def test_closed_paid_orders_stay_green(audit_client, sent_emails, closed):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state(**closed))
    response = _post(client)
    assert response.status_code == 200
    assert response.get_json()["summary"]["anomalies"] == 0
    assert sent_emails == []


def test_fresh_paid_order_and_drill_stay_green(audit_client, sent_emails):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state(hours_ago=3))
    _write(root, "drill-20260922", _paid_state(
        order_id="drill-20260922", hours_ago=30))
    response = _post(client)
    assert response.status_code == 200
    assert response.get_json()["summary"]["stale_paid_orders"] == 0
    assert sent_emails == []


# --- Ledger failures (review finding: an OSError used to drop every finding
# and, because emails went out before the ledger save, re-send hourly) -------

def _other_critical(root):
    _write(root, "cancelled-order", _minimal_state(
        "synthetic-order", status="CANCELLED",
        cancellation={"worker_stop_acknowledged": False}))


def test_ledger_write_failure_keeps_findings_and_sends_no_email(
        audit_client, sent_emails, monkeypatch):
    from tools import audit_fulfillment_states as audit_tool
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())
    _other_critical(root)

    def broken_save(path, ledger):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(audit_tool, "save_alert_ledger", broken_save)
    for _ in range(3):  # hourly runs while the volume is broken
        response = _post(client)
        assert response.status_code == 500
        data = response.get_json()
        assert data["alert_ledger"] == "failed"
        codes = {item["code"]: item for item in data["anomalies"]}
        assert set(codes) == {"PAID_ORDER_STALE", "CANCELLED_STOP_UNACKNOWLEDGED"}
        stale = codes["PAID_ORDER_STALE"]
        assert stale["severity"] == "CRITICAL"
        assert stale["alert"] == "ledger_unavailable"
        assert stale["coach_email"] == "suppressed_ledger_unavailable"
    assert sent_emails == []


@pytest.mark.parametrize("breakage", ["unreadable_ledger", "unlockable"])
def test_ledger_read_or_lock_failure_sends_no_email(
        audit_client, sent_emails, breakage):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())
    ledger_path = webhook_app._stale_alert_ledger_path()
    if breakage == "unreadable_ledger":
        ledger_path.mkdir(parents=True)  # read raises IsADirectoryError
    else:
        ledger_path.with_name(ledger_path.name + ".lock").mkdir(parents=True)
    response = _post(client)
    assert response.status_code == 500
    assert response.get_json()["alert_ledger"] == "failed"
    assert response.get_json()["summary"]["stale_paid_orders"] == 1
    assert sent_emails == []


def test_ledger_is_durable_before_any_email_is_sent(
        audit_client, monkeypatch):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())
    ledger_path = webhook_app._stale_alert_ledger_path()
    seen = []

    def send(to, subject, body, *args, **kwargs):
        seen.append(json.loads(ledger_path.read_text())["alerts"])
        return True

    monkeypatch.setattr(webhook_app, "NOTIFICATION_EMAIL", "coach@example.test")
    monkeypatch.setattr(webhook_app, "RESEND_API_KEY", "re_fixture")
    monkeypatch.setattr(webhook_app, "_send_email", send)
    assert _post(client).status_code == 500
    [alerts_at_send_time] = seen
    ref = _post(client).get_json()["anomalies"][0]["state_ref"]
    assert ref in alerts_at_send_time


def test_corrupt_ledger_is_reset_with_at_most_one_repeat(
        audit_client, sent_emails):
    client, root = audit_client
    _write(root, PAID_ORDER_ID, _paid_state())
    ledger_path = webhook_app._stale_alert_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("{truncated")
    first = _post(client)
    assert first.status_code == 500
    assert first.get_json()["alert_ledger"] == "reset_corrupt"
    second = _post(client)
    assert second.status_code == 200
    assert second.get_json()["alert_ledger"] == "ok"
    assert len(sent_emails) == 1
