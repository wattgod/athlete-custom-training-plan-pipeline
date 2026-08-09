"""A3 server-side catalog and redaction boundary tests."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from fulfillment_state import (FulfillmentStateError,
                               APPROVED,
                               external_state_projection,
                               finalize_transitional_release,
                               redact_sensitive_review_items, transition,
                               write_generation)
import app as webhook_app


def _derived(value):
    return {"id": "FUELING_SECRET_TARGET", "field": "fitness.target",
            "class": "inferred", "basis": "seeded sensitive fixture",
            "inputs": {"duration": 4}, "sensitivity": "sensitive",
            "at": "2026-08-08T12:00:00Z", "revision": 1, "value": value}


def test_derived_value_feeds_typed_authoritative_review_catalog(tmp_path):
    state = write_generation(tmp_path / "state.json", "athlete-m",
                             order_id="cs_a3", derived_values=[_derived(67)])
    item = next(item for item in state["review_items"]
                if item["item_id"] == "DERIVED_FUELING_SECRET_TARGET")
    assert item["value"] == 67 and item["value_type"] == "integer"
    assert item["basis"] == "seeded sensitive fixture"
    assert item["sensitivity"] == "sensitive"
    regenerated = write_generation(tmp_path / "state.json", "athlete-m",
                                   order_id="cs_a3", derived_values=[_derived(68)])
    assert regenerated["derived_values"][0]["revision"] == 2
    assert regenerated["derived_values"][0]["value"] == 68


def test_sensitive_value_is_absent_from_external_projection():
    secret = "seeded-secret-987654"
    projected = redact_sensitive_review_items([{
        "item_id": "DERIVED_SECRET", "sensitivity": "sensitive",
        "value": secret, "review_value": {"secret": secret},
        "message": f"target {secret}", "basis": f"source {secret}",
    }])
    output = json.dumps(projected)
    assert secret not in output
    assert "authenticated review" in output


def test_recursive_projection_redacts_archived_evidence():
    secret = "seeded-archive-secret-13579"
    projected = external_state_projection({
        "approval": {"confirmations": [{
            "sensitivity": "sensitive", "value": secret,
            "review_value": {"nested": secret},
        }]},
        "superseded_approvals": [{"approval": {"confirmations": [{
            "sensitivity": "sensitive", "message": secret,
        }]}}],
        "application": {"evidence": {
            "sensitivity": "sensitive", "evidence": secret}},
        "waiver": {"reason": secret, "credential": secret},
    })
    assert secret not in json.dumps(projected)


def test_real_post_approval_status_redacts_live_and_archived_secret(
        tmp_path, monkeypatch):
    secret = "seeded-status-secret-86420"
    data = tmp_path / "data"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data / "deliveries"))
    monkeypatch.setenv("CRON_SECRET", "status-secret")
    order_id = "cs_sensitive_status"
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, "athlete-sensitive", order_id=order_id,
        delivery_platform="trainingpeaks", derived_values=[_derived(secret)])
    revision = webhook_app._order_dir(order_id) / "revisions" / "r1"
    revision.mkdir(parents=True)
    (revision / "artifact.txt").write_text("sealed")
    state = finalize_transitional_release(
        state_path, revision, expected_revision=1)
    state = transition(
        state_path, APPROVED, "coach@example.invalid",
        expected_revision=1,
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=[{
            "item_id": item["item_id"], "revision": 1,
            "disposition": "confirmed",
        } for item in state["review_items"]
          if item["type"] in {"required_confirmation", "verified_fact"}],
        credential="operator-secret")
    webhook_app._record_order_lookup(order_id, "athlete-sensitive")
    response = webhook_app.app.test_client().get(
        f"/api/fulfillment/{order_id}/status",
        headers={"X-Cron-Secret": "status-secret"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert secret not in body
    assert "authenticated review" in body


def test_generation_notification_redacts_seeded_sensitive_blocker():
    secret = "seeded-notification-secret-2468"
    _, text, html = webhook_app._build_phase1_generation_email({
        "name": "Athlete", "order_id": "cs_a3", "fulfillment_status": "BLOCKED_REVIEW",
        "blocking_issues": [{"id": "SEE_REVIEW", "severity": "CRITICAL",
                             "message": secret, "sensitivity": "sensitive",
                             "waivable": True}],
    })
    assert secret not in text + html
    assert "authenticated review" in text + html


def _failed_notification_details(secret):
    return {
        "name": "Athlete", "email": "athlete@example.invalid",
        "order_id": "cs_failed_a3", "athlete_id": "athlete-a3",
        "race_name": "Fixture Race", "ftp": secret,
        "weight_kg": secret, "error": f"pipeline exposed {secret}",
    }


def test_failed_order_email_drops_sensitive_values_from_text_and_html():
    secret = "seeded-failure-secret-97531"
    subject, text, html = webhook_app._build_training_plan_email({
        **_failed_notification_details(secret), "pipeline_success": False,
    })
    assert "FAILED" in subject
    assert secret not in text + html
    assert "authenticated Railway logs" in text + html


def test_unconfigured_email_log_fallback_drops_sensitive_values():
    secret = "seeded-unconfigured-log-secret-86420"
    with patch.object(webhook_app, "NOTIFICATION_EMAIL", ""), \
            patch.object(webhook_app, "RESEND_API_KEY", ""), \
            patch.object(webhook_app, "logger") as logger:
        webhook_app._notify_new_order(
            "training_plan_FAILED", _failed_notification_details(secret))
    logged = logger.critical.call_args.args[0]
    assert secret not in logged
    assert "authenticated Railway logs" in logged


def test_send_failure_log_fallback_drops_sensitive_values():
    secret = "seeded-send-failure-log-secret-75319"
    with patch.object(webhook_app, "NOTIFICATION_EMAIL", "coach@example.invalid"), \
            patch.object(webhook_app, "RESEND_API_KEY", "configured"), \
            patch.object(webhook_app, "_send_email", return_value=False), \
            patch.object(webhook_app, "logger") as logger:
        webhook_app._notify_new_order(
            "training_plan_FAILED", _failed_notification_details(secret))
    logged = logger.critical.call_args.args[0]
    assert secret not in logged
    assert "authenticated Railway logs" in logged


def test_canonical_release_rejects_contract_with_unbound_model_seal(tmp_path):
    state_path = tmp_path / "state.json"
    write_generation(state_path, "athlete-m", order_id="cs_bad_seal")
    release = tmp_path / "release"
    artifacts = release / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "canonical_training_model.json").write_text('{"model_version":"v1"}\n')
    (artifacts / "profile.yaml").write_text("name: athlete-m\n")
    (artifacts / "apply_contract.json").write_text(json.dumps({
        "contract_version": "apply_contract/v1", "order_id": "cs_bad_seal",
        "tp_athlete_id": "fake", "generation_revision": 1,
        "model_seal": "0" * 64, "operations": [],
        "compat": {"min_reader": "apply_contract/v1"},
    }))
    with pytest.raises(FulfillmentStateError, match="model_seal mismatch"):
        finalize_transitional_release(state_path, release, expected_revision=1)
    assert not (release / "release_manifest.json").exists()
