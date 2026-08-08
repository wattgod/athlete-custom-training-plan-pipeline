"""A3 server-side catalog and redaction boundary tests."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from fulfillment_state import (FulfillmentStateError,
                               finalize_transitional_release,
                               redact_sensitive_review_items, write_generation)
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
