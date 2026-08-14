"""Dedicated E1 state, seal-v2, and closed-policy fixtures."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))
sys.path.insert(0, str(ROOT / "webhook"))

from apply_contract import (KINDS, ApplyContractError, build_contract,
                            compute_model_seal, validate_contract)
from earned_selection import VERSION_VECTOR, canonical_digest
from fulfillment_state import (
    APPROVED, EARNED_SELECTION_NON_WAIVABLE_RULES, NON_WAIVABLE_RULES,
    FulfillmentStateError, _canonical_model_seal_from_release,
    finalize_transitional_release, load, merge_quality_findings_v1, transition,
    write_generation,
)


EARNED_CODES = {
    "LIBRARY_UNCERTIFIED", "WORKOUT_DOSE_MISMATCH", "WORKOUT_ORIGIN_UNKNOWN",
    "MANIFEST_PIN_MISSING", "MANIFEST_PIN_MISMATCH",
    "MANIFEST_SNAPSHOT_UNAVAILABLE",
}


def _finding(identifier="QUALITY_R08", *, revision=1, source="report", value=1):
    return {
        "schema_version": "quality_finding/v1", "id": identifier,
        "generation_revision": revision, "source": source,
        "code": "R08_FUEL_TAG_MISSING", "severity": "critical",
        "subject": {"kind": "session", "ids": ["w01.2026-01-05.01"]},
        "metric": {"invalid_count": value},
        "basis": "workout_quality_report/v1 observed Mode A result",
        "sensitivity": "internal", "message": "Observed only in E1.",
        "version_vector": dict(VERSION_VECTOR),
    }


def _seal_transitional(path: Path, root: Path):
    root.mkdir()
    (root / "guide.html").write_text("guide", encoding="utf-8")
    revision = load(path)["generation_revision"]
    return finalize_transitional_release(path, root, expected_revision=revision)


def _confirmation_decisions(state):
    return [{"item_id": item["item_id"],
             "revision": state["generation_revision"],
             "disposition": "confirmed"}
            for item in state["review_items"]
            if item["type"] in {"required_confirmation", "verified_fact"}]


def test_quality_finding_v3_round_trip_replace_and_regeneration_isolation(tmp_path):
    path = tmp_path / "status.json"
    state = write_generation(path, "athlete-e1", order_id="order-e1")
    assert state["schema_version"] == 3 and state["quality_findings"] == []
    first_digest = state["review_catalog_digest"]

    state = merge_quality_findings_v1(
        path, 1, "report", [_finding(value=1)])
    assert state["quality_findings"] == [_finding(value=1)]
    item = next(item for item in state["review_items"]
                if item["type"] == "quality_finding")
    assert item["item_id"] == "QUALITY_R08"
    assert item["value"]["severity"] == "critical"
    assert state["review_catalog_digest"] != first_digest

    replaced = merge_quality_findings_v1(
        path, 1, "report", [_finding(value=2)])
    assert len(replaced["quality_findings"]) == 1
    assert replaced["quality_findings"][0]["metric"] == {"invalid_count": 2}
    assert replaced["review_catalog_digest"] != state["review_catalog_digest"]

    regenerated = write_generation(path, "athlete-e1", order_id="order-e1")
    assert regenerated["generation_revision"] == 2
    assert regenerated["quality_findings"] == []
    assert not any(item["type"] == "quality_finding"
                   for item in regenerated["review_items"])


def test_quality_finding_validation_and_coach_disposition_are_closed(tmp_path):
    path = tmp_path / "status.json"
    write_generation(path, "athlete-e1", order_id="order-e1")
    malformed = _finding()
    malformed["severity"] = "info"
    with pytest.raises(FulfillmentStateError, match="severity"):
        merge_quality_findings_v1(path, 1, "report", [malformed])

    state = merge_quality_findings_v1(path, 1, "report", [_finding()])
    state = _seal_transitional(path, tmp_path / "release")
    quality_decision = {
        "item_id": "QUALITY_R08", "revision": 1, "disposition": "confirmed"}
    with pytest.raises(FulfillmentStateError, match="cannot disposition"):
        transition(
            path, APPROVED, "coach", expected_revision=1,
            expected_catalog_digest=state["review_catalog_digest"],
            review_decisions=_confirmation_decisions(state) + [quality_decision])

    approved = transition(
        path, APPROVED, "coach", expected_revision=1,
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=_confirmation_decisions(state))
    snapshot = next(item for item in approved["approval"]["confirmations"]
                    if item["item_id"] == "QUALITY_R08")
    assert snapshot["disposition"] == "observed"
    assert approved["approval"]["snapshot_version"] == "approval_snapshot/v3"


def test_seal_v2_dual_constructors_and_v1_backward_constructor(tmp_path):
    root = tmp_path / "release"
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    model = {"model_version": "canonical_training_model/v2", "sessions": []}
    review_items = [{"item_id": "FACT", "type": "verified_fact", "value": 1}]
    operations = [{"logical_id": "order:course_entitlement_grant:course:x",
                   "kind": "course_entitlement_grant", "disposition": "create",
                   "payload": {"product_id": "course:x"}}]
    manifest = {"schema_version": "certification_manifest/v1", "rows": []}
    manifest_digest = canonical_digest(manifest)
    (artifacts / "canonical_training_model.json").write_text(json.dumps(model))
    (root / "certification_manifest.json").write_text(json.dumps(manifest))
    pin = {"snapshot_path": "certification_manifest.json",
           "snapshot_digest": manifest_digest,
           "manifest_version": "certification_manifest/v1",
           "version_vector": None, "promotion_digests": []}
    (artifacts / "final_plan_candidate.json").write_text(json.dumps({"manifest_pin": pin}))
    guide_sources = {}
    state = {"review_items": review_items}

    v2 = {"contract_version": "apply_contract/v2",
          "seal_version": "canonical_model_apply_contract/v2",
          "operations": operations}
    expected_v2 = compute_model_seal(
        model, review_items, guide_sources, operations, manifest_digest)
    assert _canonical_model_seal_from_release(root, state, v2) == expected_v2

    v1 = {"contract_version": "apply_contract/v1", "operations": operations}
    expected_v1 = compute_model_seal(model, review_items, guide_sources, operations)
    assert _canonical_model_seal_from_release(root, state, v1) == expected_v1

    (root / "certification_manifest.json").unlink()
    with pytest.raises(FulfillmentStateError, match="manifest unavailable"):
        _canonical_model_seal_from_release(root, state, v2)
    with pytest.raises(FulfillmentStateError, match="unknown apply contract"):
        _canonical_model_seal_from_release(
            root, state, {"contract_version": "apply_contract/v99", "operations": []})


def test_new_e1_apply_and_release_constructors_fail_closed_on_pin_faults(tmp_path):
    athlete = tmp_path / "athlete"
    athlete.mkdir()
    manifest = {"schema_version": "certification_manifest/v1",
                "version_vector": dict(VERSION_VECTOR),
                "promotion_artifacts": [], "rows": []}
    digest = canonical_digest(manifest)
    pin = {"snapshot_path": "certification_manifest.json",
           "snapshot_digest": digest,
           "manifest_version": "certification_manifest/v1",
           "version_vector": dict(VERSION_VECTOR), "promotion_digests": []}
    (athlete / "certification_manifest.json").write_text(json.dumps(manifest))
    (athlete / "final_plan_candidate.json").write_text(json.dumps({"manifest_pin": pin}))
    (athlete / "training_guide.html").write_text("guide")
    ir = {"weeks": [{"number": 1, "sessions": [{
              "date": "2026-08-17", "title": "Endurance", "type": "cycling",
              "duration_s": 3600, "description": "steady",
              "workout_type_value_id": 2, "tss_planned": 40,
              "structure": {"steps": []},
          }]}], "notes": [], "entitlements": [], "attachments": []}
    kwargs = dict(order_id="order-e1", tp_athlete_id="tp-e1",
                  generation_revision=1,
                  canonical_model={"model_version": "canonical_training_model/v2",
                                   "sessions": []},
                  review_items=[], guide_sources={}, athlete_dir=athlete)
    valid = build_contract(ir, **kwargs)
    assert valid["contract_version"] == "apply_contract/v2"
    unknown = {**valid, "contract_version": "apply_contract/v99",
               "compat": {"min_reader": "apply_contract/v99"}}
    with pytest.raises(ApplyContractError, match="unknown apply contract version"):
        validate_contract(unknown)

    # A mutable/global manifest is irrelevant after the revision snapshot pin.
    global_copy = tmp_path / "workout_certification.json"
    global_copy.write_text(json.dumps({"mutated": True}))
    assert build_contract(ir, **kwargs)["model_seal"] == valid["model_seal"]

    snapshot = athlete / "certification_manifest.json"
    snapshot.unlink()
    with pytest.raises(ApplyContractError, match="MANIFEST_SNAPSHOT_UNAVAILABLE"):
        build_contract(ir, **kwargs)
    snapshot.write_text(json.dumps(manifest))

    candidate_path = athlete / "final_plan_candidate.json"
    candidate_path.write_text(json.dumps({}))
    with pytest.raises(ApplyContractError, match="MANIFEST_PIN_MISSING"):
        build_contract(ir, **kwargs)
    candidate_path.write_text(json.dumps({"manifest_pin": {**pin, "snapshot_digest": "f" * 64}}))
    with pytest.raises(ApplyContractError, match="MANIFEST_PIN_MISMATCH"):
        build_contract(ir, **kwargs)

    release = tmp_path / "release"
    artifacts = release / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "canonical_training_model.json").write_text(json.dumps(kwargs["canonical_model"]))
    (release / "certification_manifest.json").write_text(json.dumps(manifest))
    state = {"review_items": []}
    contract = {"contract_version": "apply_contract/v2",
                "seal_version": "canonical_model_apply_contract/v2", "operations": []}
    with pytest.raises(FulfillmentStateError, match="MANIFEST_PIN_MISSING"):
        _canonical_model_seal_from_release(release, state, contract)
    (artifacts / "final_plan_candidate.json").write_text(
        json.dumps({"manifest_pin": {**pin, "snapshot_digest": "e" * 64}}))
    with pytest.raises(FulfillmentStateError, match="MANIFEST_PIN_MISMATCH"):
        _canonical_model_seal_from_release(release, state, contract)
    (artifacts / "final_plan_candidate.json").write_text(json.dumps({"manifest_pin": pin}))
    (release / "certification_manifest.json").unlink()
    with pytest.raises(FulfillmentStateError, match="manifest unavailable"):
        _canonical_model_seal_from_release(release, state, contract)


def test_closed_nonwaivable_amendment_and_q0_tp_kind_inventory():
    assert EARNED_SELECTION_NON_WAIVABLE_RULES == EARNED_CODES
    assert EARNED_CODES <= NON_WAIVABLE_RULES
    assert KINDS == {
        "workout_upsert", "calendar_note_upsert", "attachment_upsert",
        "mental_task_upsert", "course_entitlement_grant", "threshold_update",
        "zone_update",
    }
