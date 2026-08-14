import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webhook"))

import app as webhook_app
from fulfillment_state import finalize_transitional_release, load, write_generation
from tools import daily_order_drill as drill


DAY = date(2026, 8, 12)
SECRET = "woo-drill-secret"
CRON_SECRET = "cron-drill-secret"


class FlaskTransport:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def _target(url):
        parsed = urlsplit(url)
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")

    def get(self, url, **kwargs):
        return self.client.get(
            self._target(url), headers=kwargs.get("headers") or {})

    def post(self, url, **kwargs):
        return self.client.post(
            self._target(url), data=kwargs.get("data"), json=kwargs.get("json"),
            headers=kwargs.get("headers") or {})


def _configure_app(tmp_path, monkeypatch):
    data = tmp_path / "data"
    athletes = tmp_path / "athletes"
    athletes.mkdir()
    data.mkdir()
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data / "deliveries"))
    monkeypatch.setattr(webhook_app, "JOBS_DIR", str(data / "jobs"))
    monkeypatch.setattr(webhook_app, "ATHLETES_DIR", str(athletes))
    monkeypatch.setattr(webhook_app, "WOOCOMMERCE_SECRET", SECRET)
    monkeypatch.setattr(webhook_app, "CRON_SECRET", CRON_SECRET)
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    webhook_app.app.config["TESTING"] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client()


def _seed_order(order_id, *, blocker=True, job_status=None):
    path = webhook_app._fulfillment_status_path(order_id)
    issues = []
    if blocker:
        issues = [{
            "id": "RACE_UNMATCHED", "source": "fixture",
            "severity": "CRITICAL", "message": "synthetic race is unmatched",
        }]
    state = write_generation(
        path, "daily_drill", issues, order_id=order_id,
        delivery_platform="manual")
    revision = (webhook_app._order_dir(order_id) / "revisions"
                / f"r{state['generation_revision']}")
    (revision / "artifacts").mkdir(parents=True)
    (revision / "artifacts" / "plan_preview.html").write_text("review")
    (revision / f"{order_id}-review-bundle.zip").write_bytes(b"review bundle")
    (revision / f"{order_id}-customer-bundle.zip").write_bytes(b"customer bundle")
    finalize_transitional_release(
        path, revision, expected_revision=state["generation_revision"])
    webhook_app._record_order_lookup(order_id, "daily_drill")
    if job_status:
        webhook_app._write_job({
            "athlete_id": "daily_drill", "order_id": order_id,
            "status": job_status, "attempts": 1, "max_attempts": 2,
            "order_data": {},
        })
    return path


def _config():
    return drill.DrillConfig(
        webhook_url="https://local.test/webhook/woocommerce",
        webhook_secret=SECRET,
        customer_email="operator@example.com",
        cron_secret=CRON_SECRET,
    )


def test_payload_is_deterministic_realistic_and_future_dated():
    first = drill.build_payload(DAY, "operator+anything@example.com")
    second = drill.build_payload(DAY, "operator@example.com")
    assert first == second
    assert first["id"] == "drill-20260812"
    assert first["billing"]["first_name"] == "Daily"
    assert first["billing"]["last_name"] == "Drill"
    assert first["billing"]["email"] == "operator+drill@example.com"
    meta = {item["key"]: item["value"] for item in first["meta_data"]}
    assert meta["race_date"] == "2026-12-30"
    assert meta["delivery_platform"] == "manual"
    assert meta["intake_complete"] is True


def test_signature_matches_webhook_verifier(monkeypatch):
    payload_bytes = drill.encode_payload(
        drill.build_payload(DAY, "operator@example.com"))
    signature = drill.sign_payload(payload_bytes, SECRET)
    monkeypatch.setattr(webhook_app, "WOOCOMMERCE_SECRET", SECRET)
    assert webhook_app.verify_woocommerce_signature(payload_bytes, signature)
    assert not webhook_app.verify_woocommerce_signature(payload_bytes + b" ", signature)


def test_drill_assertions_use_local_flask_app_end_to_end(tmp_path, monkeypatch):
    client = _configure_app(tmp_path, monkeypatch)
    order_id = drill.order_id_for(DAY)
    _seed_order(order_id, job_status="succeeded")
    spawn = Mock(return_value=({"status": "queued"}, None))
    monkeypatch.setattr(webhook_app, "_spawn_plan_job", spawn)

    assertions = drill.send_and_verify_order(
        _config(), DAY, transport=FlaskTransport(client),
        timeout_seconds=2, poll_interval_seconds=0.01,
        sleep=lambda _: None)

    assert assertions
    assert all(item["passed"] for item in assertions), assertions
    intake = spawn.call_args.kwargs["intake_data"]
    assert intake["name"] == "Daily Drill"
    assert intake["races"][0]["name"] == "Daily Drill Gravel Challenge"


def test_cleanup_cancels_previous_order_and_verifies_state(tmp_path, monkeypatch):
    client = _configure_app(tmp_path, monkeypatch)
    previous = drill.order_id_for(DAY.replace(day=11))
    path = _seed_order(previous, blocker=False)
    webhook_app.mark_order_processed(previous, "daily_drill")

    assertions = drill.cleanup_previous_order(
        _config(), DAY, transport=FlaskTransport(client))

    assert all(item["passed"] for item in assertions), assertions
    state = load(path)
    assert state["status"] == "CANCELLED"
    assert state["cancellation"]["worker_stop_acknowledged"] is True


def test_cleanup_passes_when_previous_drill_never_existed(tmp_path, monkeypatch):
    """First-run case: /api/order-status answers 200 "processing" (never 404)
    for session refs the webhook has not processed, so cleanup must treat a
    missing fulfillment state as nothing-to-cancel, not an error."""
    client = _configure_app(tmp_path, monkeypatch)

    assertions = drill.cleanup_previous_order(
        _config(), DAY, transport=FlaskTransport(client))

    assert len(assertions) == 1
    assert assertions[0]["passed"] is True
    assert "nothing to cancel" in assertions[0]["detail"]


def test_request_retry_survives_cold_start_then_succeeds():
    """Railway cold starts answer 502/503 on the first request; the drill
    must retry instead of failing the whole run."""
    responses = [Mock(status_code=503), Mock(status_code=502), Mock(status_code=200)]
    calls = iter(responses)
    naps: list[float] = []

    result = drill._request_with_retry(
        lambda: next(calls), sleep=naps.append)

    assert result.status_code == 200
    assert naps == [5.0, 10.0]


def test_request_retry_gives_up_after_bounded_attempts():
    attempts = []

    def send():
        attempts.append(1)
        return Mock(status_code=503)

    result = drill._request_with_retry(send, sleep=lambda _: None)

    assert result.status_code == 503
    assert len(attempts) == 4


def test_artifact_redacts_all_configured_values():
    assertions = [{
        "name": "failure", "passed": False,
        "detail": "operator@example.com woo-drill-secret https://secret.test/path",
    }]
    artifact = drill.build_artifact(
        day=DAY, assertions=assertions,
        now=datetime(2026, 8, 12, 12, tzinfo=timezone.utc),
        secrets={
            "operator@example.com", "woo-drill-secret",
            "https://secret.test/path",
        },
    )
    encoded = json.dumps(artifact)
    assert "operator@example.com" not in encoded
    assert "woo-drill-secret" not in encoded
    assert "secret.test" not in encoded
    assert encoded.count("[REDACTED]") == 3
