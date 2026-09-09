"""Regression tests for order-bound delivery follow-up eligibility."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webhook"))

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("WOOCOMMERCE_SECRET", "")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("SYNC_PIPELINE", "1")

import app as app_module  # noqa: E402
from delivery.trainingpeaks.test_phase5_service import (  # noqa: E402
    NOW, _approved_state, _capability, _contract, _service,
    _successful_executor,
)
from fulfillment_state import APPLIED, confirm_after_send, transition  # noqa: E402


def _digest(value) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verified_state(order_id: str, athlete_id: str, delivered_at: datetime) -> dict:
    landed = [{
        "op_id": f"{order_id}:workout_upsert:fixture@r1",
        "status": "landed",
        "remote_id": "tp-fixture-workout",
        "observed_digest": "a" * 64,
        "disposition": "create",
    }]
    return {
        "order_id": order_id,
        "athlete_id": athlete_id,
        "delivery_platform": "trainingpeaks",
        "generation_revision": 1,
        "status": "CONFIRMED",
        "legacy": False,
        "approval": {"fixture": True},
        "application": {
            "at": delivered_at.isoformat(),
            "platform": "trainingpeaks",
            "receipt_type": "trainingpeaks_apply_receipt/v1",
            "receipt_digest": _digest(landed),
            "operation_count": len(landed),
        },
        "application_attempt": {"status": "succeeded", "landed": landed},
        "confirmation": {
            "at": delivered_at.isoformat(),
            "provider": "resend",
        },
    }


def _order(order_id: str, athlete_id: str = "fixture-athlete", **overrides) -> dict:
    value = {
        "product_type": "training_plan",
        "order_id": order_id,
        "athlete_id": athlete_id,
        "email": "rider@example.com",
        "name": "Rider Example",
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "success": True,
        "delivery_platform": "trainingpeaks",
        "race_name": "Fixture Gravel",
    }
    value.update(overrides)
    return value


@pytest.fixture
def followup_env(tmp_path, monkeypatch):
    log_dir = tmp_path / ".logs"
    log_dir.mkdir()
    monkeypatch.setattr(app_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "DELIVERIES_DIR", str(tmp_path / "deliveries"))
    monkeypatch.setattr(app_module, "ATHLETES_DIR", str(tmp_path / "athletes"))
    monkeypatch.setattr(app_module, "approval_matches_release", lambda state: True)

    def write_orders(*orders):
        path = log_dir / datetime.now(timezone.utc).strftime("%Y-%m.jsonl")
        path.write_text("".join(json.dumps(order) + "\n" for order in orders))

    return tmp_path, write_orders


def _install_states(monkeypatch, states: dict[str, dict], plan_dates: dict | None = None):
    def load_state(path):
        order_id = Path(path).parent.name
        if order_id not in states:
            raise app_module.FulfillmentStateError("missing")
        return states[order_id]

    monkeypatch.setattr(app_module, "load_fulfillment_state", load_state)
    if plan_dates is not None:
        encoded = yaml.safe_dump(plan_dates).encode("utf-8")
        monkeypatch.setattr(
            app_module, "open_verified_release_artifact",
            lambda state, root, relative: BytesIO(encoded),
        )


def test_context_accepts_actual_phase5_readback_and_confirmation(tmp_path, monkeypatch):
    order_id = "order-phase5-followup"
    order_root = tmp_path / "deliveries" / "orders" / order_id
    state_path, state = _approved_state(order_root, order_id=order_id)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    service.execute(
        grant, contract, state_path, _successful_executor, now=NOW + 1)
    confirm_after_send(
        state_path, lambda: True, metadata={"provider": "resend"})
    monkeypatch.setattr(app_module, "DELIVERIES_DIR", str(tmp_path / "deliveries"))

    status, context, reason = app_module._trainingpeaks_followup_context(
        _order(order_id))

    assert status == "eligible", reason
    assert context["delivered_at"].tzinfo == timezone.utc


def test_generated_order_waits_for_both_senders_without_sending(
        followup_env, monkeypatch):
    _root, write_orders = followup_env
    order = _order("order-generated")
    state = _verified_state(order["order_id"], order["athlete_id"], datetime.now(timezone.utc))
    state.update(status="BLOCKED_REVIEW", application=None, application_attempt=None,
                 confirmation=None)
    write_orders(order)
    _install_states(monkeypatch, {order["order_id"]: state})

    with patch.object(app_module, "_send_followup_email") as fixed_send, \
         patch.object(app_module, "_send_email") as lifecycle_send:
        fixed = app_module.process_followup_emails()
        lifecycle = app_module.process_touchpoint_emails()

    fixed_send.assert_not_called()
    lifecycle_send.assert_not_called()
    assert fixed["waiting_for_delivery"] == 1
    assert fixed["eligibility_unavailable"] == 0
    assert lifecycle["waiting_for_delivery"] == 1
    assert lifecycle["eligibility_unavailable"] == 0


def test_actual_phase5_applying_state_waits_without_completed_receipt(
        tmp_path, monkeypatch):
    order_id = "order-phase5-applying"
    order_root = tmp_path / "deliveries" / "orders" / order_id
    state_path, state = _approved_state(order_root, order_id=order_id)
    contract = _contract(state)
    service = _service(tmp_path)
    service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    monkeypatch.setattr(app_module, "DELIVERIES_DIR", str(tmp_path / "deliveries"))

    status, context, reason = app_module._trainingpeaks_followup_context(
        _order(order_id))

    assert status == "waiting", reason
    assert context is None
    assert reason == "Phase 5 provider application is in progress"


def test_phase1_applied_state_is_unavailable_to_both_senders(
        followup_env, monkeypatch):
    root, write_orders = followup_env
    order = _order("order-phase1-applied")
    order_root = root / "deliveries" / "orders" / order["order_id"]
    state_path, _state = _approved_state(order_root, order_id=order["order_id"])
    applied = transition(
        state_path, APPLIED, "fixture-coach", platform="trainingpeaks",
        evidence="historical manual evidence",
    )
    assert set(applied["application"]) == {"coach", "at", "platform", "evidence"}
    assert applied["application_attempt"] is None
    write_orders(order)

    with patch.object(app_module, "_send_followup_email") as fixed_send, \
         patch.object(app_module, "_send_email") as lifecycle_send:
        fixed = app_module.process_followup_emails()
        lifecycle = app_module.process_touchpoint_emails()

    fixed_send.assert_not_called()
    lifecycle_send.assert_not_called()
    assert fixed["eligibility_unavailable"] == 1
    assert fixed["waiting_for_delivery"] == 0
    assert lifecycle["eligibility_unavailable"] == 1
    assert lifecycle["waiting_for_delivery"] == 0


def test_missing_processing_outcome_is_unavailable(followup_env, monkeypatch):
    _root, write_orders = followup_env
    order = _order("order-missing-success")
    order.pop("success")
    write_orders(order)
    monkeypatch.setattr(
        app_module, "load_fulfillment_state",
        lambda path: pytest.fail("unproven processing must stop before state lookup"),
    )

    with patch.object(app_module, "_send_followup_email") as send:
        stats = app_module.process_followup_emails()

    send.assert_not_called()
    assert stats["eligibility_unavailable"] == 1


@pytest.mark.parametrize("delivery_age", [1, 3, 7])
def test_fixed_sequence_uses_verified_delivery_for_day_1_3_7(
        followup_env, monkeypatch, delivery_age):
    _root, write_orders = followup_env
    order = _order(f"order-delayed-{delivery_age}")
    delivered = datetime.now(timezone.utc) - timedelta(days=delivery_age)
    write_orders(order)
    _install_states(monkeypatch, {
        order["order_id"]: _verified_state(order["order_id"], order["athlete_id"], delivered),
    })

    with patch.object(app_module, "_send_followup_email", return_value=True) as send:
        stats = app_module.process_followup_emails()

    expected_days = 2 if delivery_age == 3 else 1
    assert stats["sent"] == expected_days
    assert any(call.args[0] == "rider@example.com" for call in send.call_args_list)


def test_fixed_sequence_preserves_order_scoped_dedupe_on_retry(
        followup_env, monkeypatch):
    root, write_orders = followup_env
    order = _order("order-dedupe")
    delivered = datetime.now(timezone.utc) - timedelta(days=3)
    write_orders(order)
    _install_states(monkeypatch, {
        order["order_id"]: _verified_state(order["order_id"], order["athlete_id"], delivered),
    })

    with patch.object(app_module, "_send_followup_email", return_value=True) as send:
        first = app_module.process_followup_emails()
        second = app_module.process_followup_emails()

    # Day 1's two-day catch-up overlaps day 3; both remain intentional.
    assert first["sent"] == 2
    assert second["sent"] == 0
    assert send.call_count == 2
    sent = [json.loads(line) for line in (root / ".logs" / "followup_sent.jsonl").read_text().splitlines()]
    assert [(item["order_id"], item["day"]) for item in sent] == [
        (order["order_id"], 1), (order["order_id"], 3),
    ]


@pytest.mark.parametrize(
    "mutation", ["order", "athlete", "legacy", "manual", "receipt"],
)
def test_unproven_or_unbound_delivery_is_explicitly_unavailable(
        followup_env, monkeypatch, mutation):
    _root, write_orders = followup_env
    order = _order(f"order-{mutation}")
    state = _verified_state(
        order["order_id"], order["athlete_id"],
        datetime.now(timezone.utc) - timedelta(days=1),
    )
    if mutation == "order":
        state["order_id"] = "different-order"
    elif mutation == "athlete":
        state["athlete_id"] = "different-athlete"
    elif mutation == "legacy":
        state["legacy"] = True
    elif mutation == "manual":
        state["delivery_platform"] = "manual"
    else:
        state["application"].pop("receipt_type")
    write_orders(order)
    _install_states(monkeypatch, {order["order_id"]: state})

    with patch.object(app_module, "_send_followup_email") as send:
        stats = app_module.process_followup_emails()

    send.assert_not_called()
    assert stats["eligibility_unavailable"] == 1
    assert stats["waiting_for_delivery"] == 0


def test_endure_order_remains_excluded(followup_env, monkeypatch):
    _root, write_orders = followup_env
    order = _order("order-endure", delivery_platform="endure")
    write_orders(order)
    monkeypatch.setattr(
        app_module, "load_fulfillment_state",
        lambda path: pytest.fail("Endure exclusion must precede TP state lookup"),
    )

    with patch.object(app_module, "_send_followup_email") as send:
        stats = app_module.process_followup_emails()

    send.assert_not_called()
    assert stats["checked"] == 0


def test_touchpoints_use_sealed_order_calendar_not_latest_athlete_file(
        followup_env, monkeypatch):
    root, write_orders = followup_env
    order = _order("order-calendar")
    delivered = datetime.now(timezone.utc) - timedelta(days=1)
    today = datetime.now(timezone.utc).date()
    sealed_dates = {
        "plan_start": (today - timedelta(days=1)).isoformat(),
        "race_date": (today + timedelta(days=30)).isoformat(),
        "weeks": [{
            "week": 1,
            "monday": (today - timedelta(days=1)).isoformat(),
            "sunday": (today + timedelta(days=5)).isoformat(),
            "is_recovery_week": False,
        }],
    }
    mutable_path = root / "athletes" / order["athlete_id"] / "plan_dates.yaml"
    mutable_path.parent.mkdir(parents=True)
    mutable_path.write_text(yaml.safe_dump({
        "plan_start": (today + timedelta(days=20)).isoformat(), "weeks": [],
    }))
    write_orders(order)
    _install_states(monkeypatch, {
        order["order_id"]: _verified_state(order["order_id"], order["athlete_id"], delivered),
    }, sealed_dates)

    with patch.object(app_module, "_send_email", return_value=True) as send:
        stats = app_module.process_touchpoint_emails()

    assert stats["sent"] == 1
    assert send.call_args.kwargs["subject"] == "Quick check — did everything load OK?"


def test_touchpoint_failed_send_is_retryable(followup_env, monkeypatch):
    root, write_orders = followup_env
    order = _order("order-touch-retry")
    delivered = datetime.now(timezone.utc) - timedelta(days=1)
    today = datetime.now(timezone.utc).date()
    plan_dates = {
        "plan_start": (today - timedelta(days=1)).isoformat(),
        "race_date": (today + timedelta(days=30)).isoformat(),
        "weeks": [{
            "week": 1,
            "monday": (today - timedelta(days=1)).isoformat(),
            "sunday": (today + timedelta(days=5)).isoformat(),
            "is_recovery_week": False,
        }],
    }
    write_orders(order)
    _install_states(monkeypatch, {
        order["order_id"]: _verified_state(order["order_id"], order["athlete_id"], delivered),
    }, plan_dates)

    with patch.object(app_module, "_send_email", side_effect=[False, True]) as send:
        first = app_module.process_touchpoint_emails()
        second = app_module.process_touchpoint_emails()

    assert first["sent"] == 0
    assert first["errors"] == 1
    assert second["sent"] == 1
    assert send.call_count == 2
    assert (root / ".logs" / "followup_sent.jsonl").exists()
