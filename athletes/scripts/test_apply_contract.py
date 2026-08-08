"""Offline D0 gates: schema, supersession positions, and fake-server parity."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from apply_contract import (ApplyContractError, assert_checked_schema_current,
                            build_contract, digest_payload, validate_contract)
from fulfillment_manifest import build_manifest_from_plan_ir
from fake_remote_parity import FakeRemoteModel, legacy_desired_state


def _ir():
    return {
        "athlete": {"id": "athlete-m"},
        "race_snapshot": {"name": "Test Race", "date": "2026-09-01"},
        "weeks": [{"number": 1, "sessions": [{
            "date": "2026-08-14", "title": "LTHR Field Test",
            "description": "Use the prescribed HR effort.",
            "workout_type_value_id": 2, "duration_s": 3600,
            "tss_planned": 48.0, "structure": {
                "structure": [{"type": "step", "length": 3600,
                               "intensityClass": "active",
                               "targets": [{"minValue": 0.8, "maxValue": 0.9,
                                            "targetType": "percentOfThresholdHr"}]}]},
            "type": "field_test", "sport": "cycling", "segments": [],
        }]}],
        "notes": [{"kind": "mental_task", "id": "focus", "date": "2026-08-14",
                   "title": "Focus cue", "text": "Steady breathing"}],
        "attachments": [{"id": "guide", "kind": "guide", "path": "guide.html"}],
        "entitlements": [{"kind": "course", "product_id": "course:test-race"}],
    }


def _contract(tmp_path, **kwargs):
    (tmp_path / "guide.html").write_text("guide")
    return build_contract(
        _ir(), order_id="cs_phase3", tp_athlete_id="fake-42",
        generation_revision=kwargs.pop("generation_revision", 1),
        canonical_model={"model_version": "canonical_training_model/v1"},
        review_items=[{"item_id": "FACT", "value": 1}],
        guide_sources={"profile.yaml": "abc"}, athlete_dir=tmp_path, **kwargs)


def test_checked_schema_is_generated_definition_and_every_emission_validates(tmp_path):
    assert_checked_schema_current()
    contract = _contract(tmp_path)
    assert validate_contract(contract) is contract
    broken = copy.deepcopy(contract)
    broken["operations"][0]["rollback"]["strategy"] = "none"
    with pytest.raises(ApplyContractError, match="schema validation"):
        validate_contract(broken)


def test_three_identities_are_stable_and_revision_scoped(tmp_path):
    first = _contract(tmp_path, generation_revision=1)
    second = _contract(tmp_path, generation_revision=2)
    assert [op["logical_id"] for op in first["operations"]] == [
        op["logical_id"] for op in second["operations"]]
    assert all(op["op_id"].endswith("@r1") for op in first["operations"])
    assert all(op["op_id"].endswith("@r2") for op in second["operations"])
    for op in first["operations"]:
        if op["kind"] in {"threshold_update", "zone_update", "course_entitlement_grant"}:
            assert op["remote_marker"] is None
        else:
            assert op["logical_id"] in op["remote_marker"]
    attachment = next(op for op in first["operations"]
                      if op["kind"] == "attachment_upsert")
    assert attachment["logical_id"] == (
        "cs_phase3:attachment_upsert:2026-08-14#1:guide.html")
    assert attachment["payload"]["parent_logical_id"] == (
        "cs_phase3:workout_upsert:2026-08-14#1")


def test_per_kind_logical_key_grammar_rejects_nested_parent_id(tmp_path):
    contract = _contract(tmp_path)
    attachment = next(op for op in contract["operations"]
                      if op["kind"] == "attachment_upsert")
    bad_key = ("cs_phase3:workout_upsert:2026-08-14#1:guide.html")
    attachment["logical_id"] = f"cs_phase3:attachment_upsert:{bad_key}"
    attachment["op_id"] = attachment["logical_id"] + "@r1"
    attachment["remote_marker"] = attachment["logical_id"]
    with pytest.raises(ApplyContractError, match="logical key grammar"):
        validate_contract(contract)


@pytest.mark.parametrize("kind,name,payload,current", [
    ("threshold_update", "lthr", {"metric": "lthr", "after_value": 171, "unit": "bpm"},
     {"metric": "lthr", "after_value": 171, "unit": "bpm"}),
    ("zone_update", "hr_zones", {"zone_set": "hr_zones", "after_table": [{"max": 140}]},
     {"zone_set": "hr_zones", "after_table": [{"max": 140}]}),
])
def test_first_and_subsequent_adopted_singleton_keep_positions(
    tmp_path, kind, name, payload, current,
):
    desire = {name: {"kind": kind, "payload": payload}}
    first = _contract(tmp_path, singleton_desires=desire,
                      inspection={"singletons": {name: current}})
    first_op = next(op for op in first["operations"] if op["kind"] == kind)
    assert first_op["disposition"] == "keep"
    assert first_op["predecessor"] is None
    inventory = {first_op["logical_id"]: {
        "kind": kind, "remote_id": None, "desired_digest": first_op["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": first_op["op_id"],
    }}
    subsequent = _contract(
        tmp_path, generation_revision=2, singleton_desires=desire,
        inspection={"singletons": {name: current}},
        effective_remote_inventory=inventory)
    op = next(op for op in subsequent["operations"] if op["kind"] == kind)
    assert op["disposition"] == "keep"
    assert op["predecessor"] == {"op_id": first_op["op_id"], "remote_id": None}


def test_first_and_subsequent_preexisting_entitlement_keep_positions(tmp_path):
    first = _contract(tmp_path, inspection={"entitlements": ["course:test-race"]})
    first_op = next(op for op in first["operations"]
                    if op["kind"] == "course_entitlement_grant")
    assert first_op["disposition"] == "keep" and first_op["predecessor"] is None
    inventory = {first_op["logical_id"]: {
        "kind": first_op["kind"], "remote_id": None,
        "desired_digest": first_op["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": first_op["op_id"],
    }}
    second = _contract(tmp_path, generation_revision=2,
                       inspection={"entitlements": ["course:test-race"]},
                       effective_remote_inventory=inventory)
    second_op = next(op for op in second["operations"]
                     if op["kind"] == "course_entitlement_grant")
    assert second_op["predecessor"] == {"op_id": first_op["op_id"], "remote_id": None}


def test_supersession_serializes_update_delete_prior_payloads(tmp_path):
    first = _contract(tmp_path)
    workout = next(op for op in first["operations"] if op["kind"] == "workout_upsert")
    stale_id = "cs_phase3:calendar_note_upsert:old-note"
    old_workout = {**workout["payload"], "title": "old"}
    old_note = {"date": "2026-01-01", "title": "old", "body": "old"}
    snapshots = {
        "payloads/old.json": old_workout,
        "payloads/n-old.json": old_note,
    }
    inventory = {
        workout["logical_id"]: {"kind": workout["kind"], "remote_id": "w-1",
            "desired_digest": digest_payload(old_workout),
            "payload_snapshot_ref": "payloads/old.json", "last_op_id": workout["op_id"]},
        stale_id: {"kind": "calendar_note_upsert", "remote_id": "n-old",
            "desired_digest": digest_payload(old_note),
            "payload_snapshot_ref": "payloads/n-old.json", "last_op_id": "old-note@r1"},
    }
    second = _contract(tmp_path, generation_revision=2,
                       effective_remote_inventory=inventory,
                       payload_snapshot_reader=snapshots.__getitem__)
    updated = next(op for op in second["operations"] if op["logical_id"] == workout["logical_id"])
    deleted = next(op for op in second["operations"] if op["logical_id"] == stale_id)
    assert updated["disposition"] == "update"
    assert updated["rollback"]["strategy"] == "restore_prior_payload"
    assert updated["prior_payload"]["title"] == "old"
    assert deleted["disposition"] == "delete"
    assert deleted["rollback"]["strategy"] == "recreate_from_prior_payload"


def test_inventory_rejects_inline_payload_and_requires_snapshot_reader(tmp_path):
    first = _contract(tmp_path)
    workout = next(op for op in first["operations"] if op["kind"] == "workout_upsert")
    old = {**workout["payload"], "title": "old"}
    exact = {workout["logical_id"]: {
        "kind": workout["kind"], "remote_id": "w-1",
        "desired_digest": digest_payload(old),
        "payload_snapshot_ref": "snapshots/w-1.json",
        "last_op_id": workout["op_id"],
    }}
    with pytest.raises(ApplyContractError, match="snapshot reader"):
        _contract(tmp_path, generation_revision=2,
                  effective_remote_inventory=exact)
    inline = copy.deepcopy(exact)
    inline[workout["logical_id"]]["payload"] = old
    with pytest.raises(ApplyContractError, match="exactly the normative five"):
        _contract(tmp_path, generation_revision=2,
                  effective_remote_inventory=inline,
                  payload_snapshot_reader=lambda _: old)


def test_fake_server_migration_parity_retains_every_legacy_operation_class(tmp_path):
    """The two offline projections express equivalent fake-server effects."""
    ir = _ir()
    (tmp_path / "guide.html").write_text("guide")
    legacy = build_manifest_from_plan_ir(ir, tmp_path)
    contract = _contract(tmp_path)
    by_kind = {}
    for op in contract["operations"]:
        by_kind.setdefault(op["kind"], []).append(op)
    assert len(by_kind["workout_upsert"]) == len(legacy["workouts"])
    assert len(by_kind["calendar_note_upsert"]) == len(legacy["native_notes"])
    assert len(by_kind["attachment_upsert"]) == len(legacy["attachments"])
    assert len(by_kind["mental_task_upsert"]) == len(legacy["mental_training_tasks"])
    assert len(by_kind["course_entitlement_grant"]) == 1
    assert sorted(op["payload"]["date"] for op in by_kind["workout_upsert"]) == legacy["calendar_dates"]
    # The pinned TP-native payload survives byte-for-byte in D0.
    workout = by_kind["workout_upsert"][0]
    session = ir["weeks"][0]["sessions"][0]
    assert workout["payload"]["structure"] == session["structure"]
    assert workout["payload"]["description"] == session["description"]
    assert workout["expected_digest"] == digest_payload(workout["payload"])


def test_field_aware_remote_effect_parity_all_dispositions_and_kinds(tmp_path):
    """Legacy desired-state and D0 diff land the same complete remote state."""
    (tmp_path / "guide.html").write_text("guide")
    first_ir = _ir()
    template = copy.deepcopy(first_ir["weeks"][0]["sessions"][0])
    second_session = {**copy.deepcopy(template), "date": "2026-08-15",
                      "title": "Kept Session"}
    third_session = {**copy.deepcopy(template), "date": "2026-08-16",
                     "title": "Deleted Session"}
    first_ir["weeks"][0]["sessions"].extend([second_session, third_session])
    singleton_desires = {
        "lthr": {"kind": "threshold_update", "payload": {
            "metric": "lthr", "after_value": 170, "unit": "bpm"}}
    }
    inspection = {
        "singletons": {"lthr": singleton_desires["lthr"]["payload"]},
        "entitlements": ["course:test-race"],
    }
    first_legacy = build_manifest_from_plan_ir(first_ir, tmp_path)
    first_contract = build_contract(
        first_ir, order_id="cs_phase3", tp_athlete_id="fake-42",
        generation_revision=1,
        canonical_model={"model_version": "canonical_training_model/v1"},
        review_items=[], guide_sources={}, athlete_dir=tmp_path,
        inspection=inspection, singleton_desires=singleton_desires)

    positional_seed = legacy_desired_state(
        {"course_entitlement": first_legacy["course_entitlement"]},
        singletons=singleton_desires)
    old_remote, new_remote = FakeRemoteModel(), FakeRemoteModel()
    old_remote.seed(positional_seed)
    new_remote.seed(positional_seed)
    old_remote.reconcile_legacy(legacy_desired_state(
        first_legacy, singletons=singleton_desires))
    new_remote.apply_contract(first_contract)
    assert old_remote.snapshot() == new_remote.snapshot()

    snapshots = {}
    inventory = {}
    for index, operation in enumerate(first_contract["operations"], 1):
        ref = None
        if operation["payload"] is not None:
            ref = f"snapshots/{index}.json"
            snapshots[ref] = copy.deepcopy(operation["payload"])
        inventory[operation["logical_id"]] = {
            "remote_id": (f"remote-{index}"
                          if operation["kind"] in {
                              "workout_upsert", "calendar_note_upsert",
                              "attachment_upsert", "mental_task_upsert"}
                          else None),
            "desired_digest": operation["expected_digest"],
            "payload_snapshot_ref": ref,
            "kind": operation["kind"],
            "last_op_id": operation["op_id"],
        }

    second_ir = copy.deepcopy(first_ir)
    sessions = second_ir["weeks"][0]["sessions"]
    sessions[0]["title"] = "Updated Session"
    sessions.pop(2)
    sessions.append({**copy.deepcopy(template), "date": "2026-08-17",
                     "title": "Created Session"})
    second_legacy = build_manifest_from_plan_ir(second_ir, tmp_path)
    second_contract = build_contract(
        second_ir, order_id="cs_phase3", tp_athlete_id="fake-42",
        generation_revision=2,
        canonical_model={"model_version": "canonical_training_model/v1"},
        review_items=[], guide_sources={}, athlete_dir=tmp_path,
        effective_remote_inventory=inventory,
        payload_snapshot_reader=snapshots.__getitem__,
        inspection=inspection, singleton_desires=singleton_desires)
    dispositions = {operation["disposition"] for operation in second_contract["operations"]}
    assert dispositions == {"create", "update", "delete", "keep"}

    old_remote.reconcile_legacy(legacy_desired_state(
        second_legacy, singletons=singleton_desires))
    new_remote.apply_contract(second_contract)
    assert old_remote.snapshot() == new_remote.snapshot()


def test_module_has_no_execution_or_network_surface():
    source = __import__("apply_contract").__file__
    text = open(source, encoding="utf-8").read()
    assert "requests" not in text and "selenium" not in text
    assert "def apply(" not in text and "def execute" not in text
