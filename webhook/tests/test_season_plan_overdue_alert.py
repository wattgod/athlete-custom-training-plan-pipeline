"""Tests for the Season Plan overdue alert (docs/specs/goals-2027-funnel-spec.md,
Matti ruling 2026-09-23).

Season Plan orders never get a fulfillment_state.py record — no ZWO
pipeline runs for them — so they're invisible to the existing paid-order
stale audit (test_state_audit_endpoint.py). These tests cover the parallel
mechanism: same hourly /api/cron/state-audit endpoint, same private coach
email channel, same atomic-locked-ledger-before-email discipline, sized
for a product with no closable status of its own (fires once per order,
ever — not a repeating daily nag).
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "")

import app as webhook_app

SECRET = "season-plan-overdue-test-secret"


@pytest.fixture
def audit_client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "deliveries" / "orders").mkdir(parents=True)
    (data / ".logs").mkdir(parents=True)
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data / "deliveries"))
    monkeypatch.setattr(webhook_app, "CRON_SECRET", SECRET)
    webhook_app.app.config["TESTING"] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client(), data


def _post(client, secret=SECRET):
    headers = {"X-Cron-Secret": secret} if secret is not None else {}
    return client.post("/api/cron/state-audit", json={}, headers=headers)


def _write_season_plan_log(data_dir: Path, order_id: str, purchase_date=None,
                           _raw_purchase_date=None, **overrides):
    """purchase_date: a datetime (isoformat()'d for convenience). Pass
    _raw_purchase_date instead for an already-formatted string, e.g. the
    real production shape (date.today().isoformat(), no time component)."""
    stored_date = _raw_purchase_date if _raw_purchase_date is not None else purchase_date.isoformat()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product_type": "season_plan",
        "order_id": order_id,
        "name": "Season Buyer",
        "email": "season@example.test",
        "brand": "gravelgod",
        "price_cents": 49900,
        "purchase_date": stored_date,
        "rebuild_dates": [],
        "intake_id": "intake-123",
        "races": [],
        "success": True,
    }
    entry.update(overrides)
    log_file = data_dir / ".logs" / f"{datetime.now().strftime('%Y-%m')}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


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


class TestSeasonPlanOverdueAlert:
    def test_real_date_only_purchase_date_format_is_parsed_correctly(
            self, audit_client, sent_emails):
        """_handle_season_plan_webhook actually stores purchase_date as
        date.today().isoformat() — a bare "YYYY-MM-DD", not a full
        datetime. Every other test in this file uses a full-datetime
        isoformat for convenience; this one pins the real production
        shape so a date-vs-datetime parsing mismatch can't hide."""
        client, data = audit_client
        real_shape = (date.today() - timedelta(days=4)).isoformat()
        assert len(real_shape) == 10  # "YYYY-MM-DD", no time component
        _write_season_plan_log(data, "cs_live_real_shape", purchase_date=None,
                                _raw_purchase_date=real_shape)
        resp = _post(client)
        assert resp.get_json()["season_plan_overdue_count"] == 1
        assert len(sent_emails) == 1

    def test_overdue_order_emails_the_coach_once(self, audit_client, sent_emails):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=4)
        _write_season_plan_log(data, "cs_live_overdue_1", purchased)

        resp = _post(client)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["season_plan_overdue_count"] == 1
        assert body["season_plan_alert_ledger"] == "ok"

        [email] = sent_emails
        assert email["to"] == "coach@example.test"
        assert email["subject"].startswith("[GG] OVERDUE: Season Plan order cs_live_overdue_1")
        assert "cs_live_overdue_1" in email["body"]
        assert "intake-123" in email["body"]

    def test_not_yet_overdue_order_sends_nothing(self, audit_client, sent_emails):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=1)
        _write_season_plan_log(data, "cs_live_fresh", purchased)

        resp = _post(client)
        assert resp.get_json()["season_plan_overdue_count"] == 0
        assert sent_emails == []

    def test_alert_fires_only_once_ever_not_a_daily_repeat(
            self, audit_client, sent_emails):
        """Unlike the race-plan stale-order alert (which re-fires every
        24h until the order reaches a terminal status), Season Plan orders
        have no closable status at all — repeating forever would just be
        noise. One alert per order, permanently."""
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=5)
        _write_season_plan_log(data, "cs_live_once", purchased)

        assert _post(client).status_code == 200
        assert len(sent_emails) == 1

        # A later run — even many days later — must not re-alert.
        assert _post(client).status_code == 200
        assert len(sent_emails) == 1

    def test_email_states_the_same_prerequisite_as_the_customer_promise(
            self, audit_client, sent_emails):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=4)
        _write_season_plan_log(data, "cs_live_caveat", purchased)
        _post(client)
        [email] = sent_emails
        assert "complete questionnaire" in email["body"]
        assert "TrainingPeaks connection" in email["body"]
        assert str(webhook_app.SEASON_PLAN_BUILD_WINDOW_DAYS) in email["body"]

    def test_failed_orders_are_never_counted(self, audit_client, sent_emails):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=10)
        _write_season_plan_log(data, "cs_live_failed", purchased, success=False)
        resp = _post(client)
        assert resp.get_json()["season_plan_overdue_count"] == 0
        assert sent_emails == []

    def test_ledger_failure_sends_no_email(self, audit_client, sent_emails, monkeypatch):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=4)
        _write_season_plan_log(data, "cs_live_ledgerfail", purchased)

        ledger_path = webhook_app._season_plan_alert_ledger_path()
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.mkdir()  # a directory where a file is expected breaks the write

        resp = _post(client)
        assert resp.get_json()["season_plan_alert_ledger"] == "failed"
        assert sent_emails == []

    def test_multiple_overdue_orders_all_alert_in_one_run(
            self, audit_client, sent_emails):
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=4)
        _write_season_plan_log(data, "cs_live_multi_1", purchased)
        _write_season_plan_log(data, "cs_live_multi_2", purchased)
        resp = _post(client)
        assert resp.get_json()["season_plan_overdue_count"] == 2
        assert len(sent_emails) == 2

    def test_race_plan_stale_audit_unaffected_by_season_plan_orders(
            self, audit_client, sent_emails):
        """Season Plan overdue orders must not appear in the existing
        PAID_ORDER_STALE anomalies list (different mechanism, different
        product) and must not turn a clean race-plan run red."""
        client, data = audit_client
        purchased = datetime.now(timezone.utc) - timedelta(days=4)
        _write_season_plan_log(data, "cs_live_separate", purchased)
        resp = _post(client)
        assert resp.status_code == 200
        assert resp.get_json().get("anomalies") in (None, [])
