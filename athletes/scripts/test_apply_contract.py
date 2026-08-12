"""Offline D0 gates: schema, supersession positions, and fake-server parity."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from apply_contract import (ApplyContractError, OperationProvenance,
                            assert_checked_schema_current,
                            bind_operation_provenance, build_contract,
                            canonical_json, compute_model_seal, digest_payload,
                            validate_contract)
from fulfillment_manifest import build_manifest_from_plan_ir
from fake_remote_parity import (INTENTIONAL_D0_DIFFERENCES,
                                LEGACY_SUPPORTED_KINDS, FakeRemoteModel,
                                ParityError, classify_migration_differences)
from delivery.trainingpeaks.adapter import legacy_apply_requests


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


def _operation_reader(*contracts):
    operations = {}
    for source in contracts:
        contract = copy.deepcopy(source)
        provenance = bind_operation_provenance(
            contract, contract_digest=digest_payload(contract),
            model_seal=contract["model_seal"])
        for operation in contract["operations"]:
            operations[operation["op_id"]] = provenance
    return operations.__getitem__


def test_checked_schema_is_generated_definition_and_every_emission_validates(tmp_path):
    assert_checked_schema_current()
    contract = _contract(tmp_path)
    assert validate_contract(contract) is contract
    with pytest.raises(ApplyContractError, match="digest mismatch"):
        bind_operation_provenance(
            contract, contract_digest="0" * 64,
            model_seal=contract["model_seal"])
    with pytest.raises(ApplyContractError, match="model seal mismatch"):
        bind_operation_provenance(
            contract, contract_digest=digest_payload(contract),
            model_seal="0" * 64)
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


@pytest.mark.parametrize("tamper", ["filename", "parent", "missing_parent"])
def test_loaded_attachment_identity_is_bound_to_payload_and_parent(tmp_path, tamper):
    contract = _contract(tmp_path)
    attachment = next(op for op in contract["operations"]
                      if op["kind"] == "attachment_upsert")
    if tamper == "filename":
        attachment["payload"]["filename"] = "different.html"
    elif tamper == "parent":
        attachment["payload"]["parent_logical_id"] = (
            "cs_phase3:workout_upsert:2099-01-01#1")
    else:
        contract["operations"] = [
            op for op in contract["operations"]
            if op["kind"] != "workout_upsert"]
    if tamper != "missing_parent":
        attachment["expected_digest"] = digest_payload(attachment["payload"])
    with pytest.raises(ApplyContractError, match="attachment"):
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
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(first))
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
                       effective_remote_inventory=inventory,
                       last_operation_reader=_operation_reader(first))
    second_op = next(op for op in second["operations"]
                     if op["kind"] == "course_entitlement_grant")
    assert second_op["predecessor"] == {"op_id": first_op["op_id"], "remote_id": None}


@pytest.mark.parametrize("resource", ["written_singleton", "created_entitlement"])
def test_written_positional_inventory_rejects_null_snapshot(tmp_path, resource):
    if resource == "written_singleton":
        name = "lthr"
        desired = {"metric": "lthr", "after_value": 171, "unit": "bpm"}
        first = _contract(
            tmp_path,
            singleton_desires={name: {"kind": "threshold_update", "payload": desired}},
            inspection={"singletons": {
                name: {"metric": "lthr", "after_value": 165, "unit": "bpm"}}},
        )
        operation = next(op for op in first["operations"]
                         if op["kind"] == "threshold_update")
        next_kwargs = {
            "singleton_desires": {name: {"kind": "threshold_update", "payload": desired}},
            "inspection": {"singletons": {name: desired}},
        }
    else:
        first = _contract(tmp_path)
        operation = next(op for op in first["operations"]
                         if op["kind"] == "course_entitlement_grant")
        assert operation["disposition"] == "create"
        next_kwargs = {"inspection": {"entitlements": ["course:test-race"]}}

    impossible = {operation["logical_id"]: {
        "kind": operation["kind"], "remote_id": None,
        "desired_digest": operation["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": operation["op_id"],
    }}
    with pytest.raises(ApplyContractError, match="never-written keep"):
        _contract(
            tmp_path, generation_revision=2,
            effective_remote_inventory=impossible,
            last_operation_reader=_operation_reader(first),
            **next_kwargs,
        )


@pytest.mark.parametrize("resource", ["written_singleton", "created_entitlement"])
def test_positional_keep_cannot_erase_written_snapshot_provenance(tmp_path, resource):
    if resource == "written_singleton":
        name = "lthr"
        before = {"metric": "lthr", "after_value": 165, "unit": "bpm"}
        desired = {"metric": "lthr", "after_value": 171, "unit": "bpm"}
        first = _contract(
            tmp_path,
            singleton_desires={name: {"kind": "threshold_update", "payload": desired}},
            inspection={"singletons": {name: before}},
        )
        written = next(op for op in first["operations"]
                       if op["kind"] == "threshold_update")
        assert written["disposition"] == "update"
        next_kwargs = {
            "singleton_desires": {
                name: {"kind": "threshold_update", "payload": desired}},
            "inspection": {"singletons": {name: desired}},
        }
        snapshot_ref = "snapshots/lthr-r1.json"
    else:
        first = _contract(tmp_path)
        written = next(op for op in first["operations"]
                       if op["kind"] == "course_entitlement_grant")
        assert written["disposition"] == "create"
        next_kwargs = {"inspection": {"entitlements": ["course:test-race"]}}
        snapshot_ref = "snapshots/entitlement-r1.json"

    inventory = {written["logical_id"]: {
        "kind": written["kind"], "remote_id": None,
        "desired_digest": written["expected_digest"],
        "payload_snapshot_ref": snapshot_ref, "last_op_id": written["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        effective_remote_inventory=inventory,
        **next_kwargs,
    )
    kept = next(op for op in second["operations"]
                if op["logical_id"] == written["logical_id"])
    assert kept["disposition"] == "keep"

    inventory[written["logical_id"]].update({
        "payload_snapshot_ref": None, "last_op_id": kept["op_id"],
    })
    with pytest.raises(ApplyContractError, match="never-written keep"):
        _contract(
            tmp_path, generation_revision=3,
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(first, second),
            **next_kwargs,
        )


def test_three_revision_adopted_keep_chain_retains_null_snapshot(tmp_path):
    name = "lthr"
    desired = {"metric": "lthr", "after_value": 171, "unit": "bpm"}
    kwargs = {
        "singleton_desires": {
            name: {"kind": "threshold_update", "payload": desired}},
        "inspection": {"singletons": {name: desired}},
    }
    contracts = [_contract(tmp_path, **kwargs)]
    root = next(op for op in contracts[0]["operations"]
                if op["kind"] == "threshold_update")
    assert root["disposition"] == "keep" and root["predecessor"] is None
    inventory = {root["logical_id"]: {
        "kind": root["kind"], "remote_id": None,
        "desired_digest": root["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": root["op_id"],
    }}

    for revision in (2, 3):
        contract = _contract(
            tmp_path, generation_revision=revision,
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(*contracts),
            **kwargs,
        )
        kept = next(op for op in contract["operations"]
                    if op["logical_id"] == root["logical_id"])
        assert kept["disposition"] == "keep"
        inventory[root["logical_id"]]["last_op_id"] = kept["op_id"]
        contracts.append(contract)

    fourth = _contract(
        tmp_path, generation_revision=4,
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(*contracts),
        **kwargs,
    )
    assert next(op for op in fourth["operations"]
                if op["logical_id"] == root["logical_id"])["disposition"] == "keep"


def test_deep_5000_link_adopted_chain_remains_iterative(tmp_path):
    logical_id = "cs_phase3:course_entitlement_grant:course:test-race"
    expected_digest = digest_payload({"product_id": "course:test-race"})
    records = {}
    predecessor = None
    for revision in range(1, 5001):
        op_id = f"{logical_id}@r{revision}"
        operation = {
            "op_id": op_id, "logical_id": logical_id,
            "kind": "course_entitlement_grant", "disposition": "keep",
            "payload": None, "expected_digest": expected_digest,
            "prior_payload": None, "before_image": None,
            "remote_marker": None, "predecessor": predecessor,
            "rollback": {"strategy": "none"},
        }
        model_seal = compute_model_seal({}, [], {}, [operation])
        contract = {
            "contract_version": "apply_contract/v1", "order_id": "cs_phase3",
            "tp_athlete_id": "fake-42", "generation_revision": revision,
            "model_seal": model_seal, "operations": [operation],
            "compat": {"min_reader": "apply_contract/v1"},
        }
        records[op_id] = bind_operation_provenance(
            contract, contract_digest=digest_payload(contract),
            model_seal=model_seal)
        predecessor = {"op_id": op_id, "remote_id": None}

    inventory = {logical_id: {
        "kind": "course_entitlement_grant", "remote_id": None,
        "desired_digest": expected_digest, "payload_snapshot_ref": None,
        "last_op_id": f"{logical_id}@r5000",
    }}
    current = _contract(
        tmp_path, generation_revision=5001,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
        last_operation_reader=records.__getitem__,
    )
    assert next(op for op in current["operations"]
                if op["logical_id"] == logical_id)["disposition"] == "keep"


def test_middle_link_coordinated_forged_op_id_rejects_swapped_contract(tmp_path):
    first = _contract(tmp_path, inspection={"entitlements": ["course:test-race"]})
    root = next(op for op in first["operations"]
                if op["kind"] == "course_entitlement_grant")
    inventory = {root["logical_id"]: {
        "kind": root["kind"], "remote_id": None,
        "desired_digest": root["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": root["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(first),
    )
    tampered = copy.deepcopy(second)
    middle = next(op for op in tampered["operations"]
                  if op["logical_id"] == root["logical_id"])
    middle["op_id"] = "coordinated-forged-middle-link"
    inventory[root["logical_id"]]["last_op_id"] = middle["op_id"]
    swapped = OperationProvenance(
        contract_bytes=canonical_json(tampered),
        contract_digest=digest_payload(second),
        model_seal=second["model_seal"],
    )
    reader = _operation_reader(first)

    with pytest.raises(ApplyContractError, match="contract digest mismatch"):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=lambda op_id: (
                swapped if op_id == middle["op_id"] else reader(op_id)),
        )


def test_schema_invalid_keep_labeled_compensation_middle_link_rejected(tmp_path):
    first = _contract(tmp_path, inspection={"entitlements": ["course:test-race"]})
    root = next(op for op in first["operations"]
                if op["kind"] == "course_entitlement_grant")
    inventory = {root["logical_id"]: {
        "kind": root["kind"], "remote_id": None,
        "desired_digest": root["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": root["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(first),
    )
    middle = next(op for op in second["operations"]
                  if op["logical_id"] == root["logical_id"])
    middle["compensation"] = {"strategy": "restore_before_image"}
    inventory[root["logical_id"]]["last_op_id"] = middle["op_id"]

    with pytest.raises(ApplyContractError, match="schema validation"):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(first, second),
        )


def test_non_monotonic_revision_chain_r5_to_r2_rejected(tmp_path):
    first = _contract(tmp_path, inspection={"entitlements": ["course:test-race"]})
    root = next(op for op in first["operations"]
                if op["kind"] == "course_entitlement_grant")
    inventory = {root["logical_id"]: {
        "kind": root["kind"], "remote_id": None,
        "desired_digest": root["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": root["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(first),
    )
    future_root = _contract(
        tmp_path, generation_revision=5,
        inspection={"entitlements": ["course:test-race"]})
    r5_keep = next(op for op in future_root["operations"]
                   if op["logical_id"] == root["logical_id"])
    r2_keep = next(op for op in second["operations"]
                   if op["logical_id"] == root["logical_id"])
    r2_keep["predecessor"] = {"op_id": r5_keep["op_id"], "remote_id": None}
    inventory[root["logical_id"]]["last_op_id"] = r2_keep["op_id"]

    with pytest.raises(ApplyContractError, match="strictly descending"):
        _contract(
            tmp_path, generation_revision=6,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(second, future_root),
        )


def test_future_predecessor_r99_for_current_r3_rejected(tmp_path):
    future = _contract(
        tmp_path, generation_revision=99,
        inspection={"entitlements": ["course:test-race"]})
    future_keep = next(op for op in future["operations"]
                       if op["kind"] == "course_entitlement_grant")
    inventory = {future_keep["logical_id"]: {
        "kind": future_keep["kind"], "remote_id": None,
        "desired_digest": future_keep["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": future_keep["op_id"],
    }}

    with pytest.raises(ApplyContractError, match="strictly descending"):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(future),
        )


def _created_entitlement_rewired_to_adoption_root(tmp_path, root_revision, root_op_id):
    first = _contract(tmp_path)
    created = next(op for op in first["operations"]
                   if op["kind"] == "course_entitlement_grant")
    inventory = {created["logical_id"]: {
        "kind": created["kind"], "remote_id": None,
        "desired_digest": created["expected_digest"],
        "payload_snapshot_ref": "snapshots/entitlement-r1.json",
        "last_op_id": created["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
    )
    kept = next(op for op in second["operations"]
                if op["logical_id"] == created["logical_id"])
    forged_root = _contract(
        tmp_path, generation_revision=root_revision,
        inspection={"entitlements": ["course:test-race"]})
    adoption = next(op for op in forged_root["operations"]
                    if op["logical_id"] == created["logical_id"])
    adoption["op_id"] = root_op_id
    kept["predecessor"] = {"op_id": root_op_id, "remote_id": None}
    inventory[created["logical_id"]].update({
        "payload_snapshot_ref": None, "last_op_id": kept["op_id"],
    })
    return first, second, forged_root, inventory


def test_coordinated_noncanonical_op_id_hiding_real_create_rejected(tmp_path):
    first, second, forged_root, inventory = (
        _created_entitlement_rewired_to_adoption_root(
            tmp_path, 1, "forged-adoption-root"))

    with pytest.raises(ApplyContractError, match="op_id does not bind"):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(first, second, forged_root),
        )


def test_future_revision_r99_hiding_real_create_rejected(tmp_path):
    first, second, forged_root, inventory = (
        _created_entitlement_rewired_to_adoption_root(
            tmp_path, 99,
            "cs_phase3:course_entitlement_grant:course:test-race@r99"))

    with pytest.raises(ApplyContractError, match="strictly descending"):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(first, second, forged_root),
        )


@pytest.mark.parametrize("tamper", ["missing_link", "cycle"])
def test_null_snapshot_predecessor_chain_rejects_missing_links_and_cycles(
    tmp_path, tamper,
):
    first = _contract(tmp_path, inspection={"entitlements": ["course:test-race"]})
    root = next(op for op in first["operations"]
                if op["kind"] == "course_entitlement_grant")
    inventory = {root["logical_id"]: {
        "kind": root["kind"], "remote_id": None,
        "desired_digest": root["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": root["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
        last_operation_reader=_operation_reader(first),
    )
    kept = next(op for op in second["operations"]
                if op["logical_id"] == root["logical_id"])
    inventory[root["logical_id"]]["last_op_id"] = kept["op_id"]
    reader_contracts = [copy.deepcopy(first), copy.deepcopy(second)]
    if tamper == "missing_link":
        reader_contracts = [reader_contracts[1]]
        match = "could not resolve durable positional predecessor"
    else:
        next(op for op in reader_contracts[0]["operations"]
             if op["op_id"] == root["op_id"])["predecessor"] = {
            "op_id": kept["op_id"], "remote_id": None,
        }
        match = "contains a cycle"

    with pytest.raises(ApplyContractError, match=match):
        _contract(
            tmp_path, generation_revision=3,
            inspection={"entitlements": ["course:test-race"]},
            effective_remote_inventory=inventory,
            last_operation_reader=_operation_reader(*reader_contracts),
        )


def test_created_entitlement_snapshot_supports_subsequent_keep(tmp_path):
    first = _contract(tmp_path)
    created = next(op for op in first["operations"]
                   if op["kind"] == "course_entitlement_grant")
    inventory = {created["logical_id"]: {
        "kind": created["kind"], "remote_id": None,
        "desired_digest": created["expected_digest"],
        "payload_snapshot_ref": "snapshots/entitlement-r1.json",
        "last_op_id": created["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        inspection={"entitlements": ["course:test-race"]},
        effective_remote_inventory=inventory,
    )
    kept = next(op for op in second["operations"]
                if op["kind"] == "course_entitlement_grant")
    assert kept["disposition"] == "keep"
    assert kept["predecessor"] == {"op_id": created["op_id"], "remote_id": None}


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


@pytest.mark.parametrize("tamper", ["prior_filename", "prior_parent", "prior_digest"])
def test_attachment_update_validates_prior_identity_and_inventory_digest(tmp_path, tamper):
    first = _contract(tmp_path)
    attachment = next(op for op in first["operations"]
                      if op["kind"] == "attachment_upsert")
    old_payload = copy.deepcopy(attachment["payload"])
    old_payload["sha256"] = "0" * 64
    inventory = {attachment["logical_id"]: {
        "kind": attachment["kind"], "remote_id": "attachment-1",
        "desired_digest": digest_payload(old_payload),
        "payload_snapshot_ref": "snapshots/attachment-r1.json",
        "last_op_id": attachment["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        effective_remote_inventory=inventory,
        payload_snapshot_reader=lambda _: old_payload,
    )
    updated = next(op for op in second["operations"]
                   if op["kind"] == "attachment_upsert")
    assert updated["disposition"] == "update"
    assert updated["prior_payload"] == old_payload

    tampered = copy.deepcopy(second)
    prior = next(op for op in tampered["operations"]
                 if op["kind"] == "attachment_upsert")["prior_payload"]
    if tamper == "prior_filename":
        prior["filename"] = "wrong.html"
    elif tamper == "prior_parent":
        prior["parent_logical_id"] = "cs_phase3:workout_upsert:2099-01-01#1"
    else:
        prior["sha256"] = "f" * 64
    with pytest.raises(ApplyContractError, match="attachment"):
        validate_contract(tampered, effective_remote_inventory=inventory)


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


def test_dated_inventory_requires_remote_id_and_snapshot_even_for_keep(tmp_path):
    first = _contract(tmp_path)
    workout = next(op for op in first["operations"] if op["kind"] == "workout_upsert")
    base = {
        "kind": workout["kind"], "remote_id": "w-1",
        "desired_digest": workout["expected_digest"],
        "payload_snapshot_ref": "snapshots/w-1.json",
        "last_op_id": workout["op_id"],
    }
    for field in ("remote_id", "payload_snapshot_ref"):
        record = copy.deepcopy(base)
        record[field] = None
        with pytest.raises(ApplyContractError, match="dated effective inventory"):
            _contract(
                tmp_path, generation_revision=2,
                effective_remote_inventory={workout["logical_id"]: record},
                payload_snapshot_reader=lambda _: workout["payload"],
            )


def test_positional_inventory_rejects_remote_id_and_adopted_keep_can_update(tmp_path):
    name = "lthr"
    old_payload = {"metric": "lthr", "after_value": 170, "unit": "bpm"}
    first = _contract(
        tmp_path,
        singleton_desires={name: {"kind": "threshold_update", "payload": old_payload}},
        inspection={"singletons": {name: old_payload}},
    )
    kept = next(op for op in first["operations"] if op["kind"] == "threshold_update")
    adopted = {
        "kind": kept["kind"], "remote_id": None,
        "desired_digest": kept["expected_digest"],
        "payload_snapshot_ref": None, "last_op_id": kept["op_id"],
    }
    invalid = copy.deepcopy(adopted)
    invalid["remote_id"] = "not-positional"
    with pytest.raises(ApplyContractError, match="positional effective inventory"):
        _contract(
            tmp_path, generation_revision=2,
            singleton_desires={name: {"kind": "threshold_update", "payload": old_payload}},
            inspection={"singletons": {name: old_payload}},
            effective_remote_inventory={kept["logical_id"]: invalid},
        )

    new_payload = {"metric": "lthr", "after_value": 174, "unit": "bpm"}
    changed = _contract(
        tmp_path, generation_revision=2,
        singleton_desires={name: {"kind": "threshold_update", "payload": new_payload}},
        inspection={"singletons": {name: old_payload}},
        effective_remote_inventory={kept["logical_id"]: adopted},
        last_operation_reader=_operation_reader(first),
    )
    updated = next(op for op in changed["operations"]
                   if op["kind"] == "threshold_update")
    assert updated["disposition"] == "update"
    assert updated["before_image"] == old_payload
    assert updated["predecessor"] == {"op_id": kept["op_id"], "remote_id": None}


def test_written_singleton_snapshot_branch_supports_keep_then_update(tmp_path):
    name = "lthr"
    before = {"metric": "lthr", "after_value": 165, "unit": "bpm"}
    desired = {"metric": "lthr", "after_value": 171, "unit": "bpm"}
    first = _contract(
        tmp_path,
        singleton_desires={name: {"kind": "threshold_update", "payload": desired}},
        inspection={"singletons": {name: before}},
    )
    written = next(op for op in first["operations"] if op["kind"] == "threshold_update")
    assert written["disposition"] == "update"
    inventory = {written["logical_id"]: {
        "kind": written["kind"], "remote_id": None,
        "desired_digest": written["expected_digest"],
        "payload_snapshot_ref": "snapshots/lthr-r1.json",
        "last_op_id": written["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        singleton_desires={name: {"kind": "threshold_update", "payload": desired}},
        inspection={"singletons": {name: desired}},
        effective_remote_inventory=inventory,
    )
    kept = next(op for op in second["operations"] if op["kind"] == "threshold_update")
    assert kept["disposition"] == "keep"

    changed = {"metric": "lthr", "after_value": 176, "unit": "bpm"}
    inventory[written["logical_id"]]["last_op_id"] = kept["op_id"]
    third = _contract(
        tmp_path, generation_revision=3,
        singleton_desires={name: {"kind": "threshold_update", "payload": changed}},
        inspection={"singletons": {name: desired}},
        effective_remote_inventory=inventory,
    )
    updated = next(op for op in third["operations"] if op["kind"] == "threshold_update")
    assert updated["disposition"] == "update"
    assert updated["before_image"] == desired


def test_dated_snapshot_branch_supports_keep_then_update(tmp_path):
    first = _contract(tmp_path)
    workout = next(op for op in first["operations"] if op["kind"] == "workout_upsert")
    inventory = {workout["logical_id"]: {
        "kind": workout["kind"], "remote_id": "w-1",
        "desired_digest": workout["expected_digest"],
        "payload_snapshot_ref": "snapshots/w-r1.json",
        "last_op_id": workout["op_id"],
    }}
    second = _contract(
        tmp_path, generation_revision=2,
        effective_remote_inventory=inventory,
    )
    kept = next(op for op in second["operations"] if op["kind"] == "workout_upsert")
    assert kept["disposition"] == "keep"

    changed_ir = _ir()
    changed_ir["weeks"][0]["sessions"][0]["title"] = "Changed LTHR Field Test"
    inventory[workout["logical_id"]]["last_op_id"] = kept["op_id"]
    third = build_contract(
        changed_ir, order_id="cs_phase3", tp_athlete_id="fake-42",
        generation_revision=3,
        canonical_model={"model_version": "canonical_training_model/v1"},
        review_items=[], guide_sources={}, athlete_dir=tmp_path,
        effective_remote_inventory=inventory,
        payload_snapshot_reader=lambda _: workout["payload"],
    )
    updated = next(op for op in third["operations"] if op["kind"] == "workout_upsert")
    assert updated["disposition"] == "update"
    assert updated["prior_payload"] == workout["payload"]


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
    """Exact legacy creates match D0; unsupported supersession stays explicit."""
    (tmp_path / "guide.html").write_text("guide")
    first_ir = _ir()
    template = copy.deepcopy(first_ir["weeks"][0]["sessions"][0])
    second_session = {**copy.deepcopy(template), "date": "2026-08-15",
                      "title": "Kept Session"}
    third_session = {**copy.deepcopy(template), "date": "2026-08-16",
                     "title": "Deleted Session"}
    first_ir["weeks"][0]["sessions"].extend([second_session, third_session])
    first_legacy = build_manifest_from_plan_ir(first_ir, tmp_path)
    first_contract = build_contract(
        first_ir, order_id="cs_phase3", tp_athlete_id="fake-42",
        generation_revision=1,
        canonical_model={"model_version": "canonical_training_model/v1"},
        review_items=[], guide_sources={}, athlete_dir=tmp_path)

    old_remote, new_remote = FakeRemoteModel(), FakeRemoteModel()
    old_remote.apply_legacy_requests(legacy_apply_requests("fake-42", first_legacy))
    new_remote.apply_contract(first_contract)
    first_differences = classify_migration_differences(old_remote, new_remote)
    assert {item["disposition"] for item in first_differences.values()} == {
        INTENTIONAL_D0_DIFFERENCES["workout_external_marker"],
        INTENTIONAL_D0_DIFFERENCES["workout_sport_type"],
        INTENTIONAL_D0_DIFFERENCES["workout_segments"],
        INTENTIONAL_D0_DIFFERENCES["mental_task_upsert"],
    }

    raw_workout = next(
        record for record in old_remote.raw_snapshot().values()
        if record["kind"] == "workout_upsert")
    assert set(raw_workout["payload"]) == {
        "external_id", "title", "date", "duration", "sportType", "segments"}
    assert "description" not in raw_workout["payload"]
    assert "structure" not in raw_workout["payload"]

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
        payload_snapshot_reader=snapshots.__getitem__)
    dispositions = {operation["disposition"] for operation in second_contract["operations"]}
    assert dispositions == {"create", "update", "delete", "keep"}

    old_remote.apply_legacy_requests(legacy_apply_requests("fake-42", second_legacy))
    new_remote.apply_contract(second_contract)
    differences = classify_migration_differences(old_remote, new_remote)
    assert differences
    dispositions = {item["disposition"] for item in differences.values()}
    assert dispositions == {
        INTENTIONAL_D0_DIFFERENCES["update"],
        INTENTIONAL_D0_DIFFERENCES["delete"],
        INTENTIONAL_D0_DIFFERENCES["mental_task_upsert"],
        INTENTIONAL_D0_DIFFERENCES["workout_external_marker"],
        INTENTIONAL_D0_DIFFERENCES["workout_sport_type"],
        INTENTIONAL_D0_DIFFERENCES["workout_segments"],
    }


@pytest.mark.parametrize(("field", "tampered", "classified_as"), [
    ("external_id", "tampered-marker", "workout_external_marker"),
    ("title", "Tampered title", None),
    ("date", "2099-01-01", None),
    ("duration", 999, None),
    ("sportType", 99, "workout_sport_type"),
    ("segments", [{"tampered": True}], "workout_segments"),
])
def test_each_legacy_workout_request_field_is_compared(
    tmp_path, field, tampered, classified_as,
):
    (tmp_path / "guide.html").write_text("guide")
    legacy = build_manifest_from_plan_ir(_ir(), tmp_path)
    contract = _contract(tmp_path)
    old_remote, new_remote = FakeRemoteModel(), FakeRemoteModel()
    old_remote.apply_legacy_requests(legacy_apply_requests("fake-42", legacy))
    new_remote.apply_contract(contract)
    workout_key = next(key for key, record in old_remote.state.items()
                       if record["kind"] == "workout_upsert")
    old_remote.state[workout_key]["payload"][field] = copy.deepcopy(tampered)

    if classified_as is None:
        with pytest.raises(ParityError, match="unclassified shared remote-field delta"):
            classify_migration_differences(old_remote, new_remote)
        return
    differences = classify_migration_differences(old_remote, new_remote)
    delta = differences[f"{workout_key}:{field}"]
    assert delta["disposition"] == INTENTIONAL_D0_DIFFERENCES[classified_as]
    assert delta["legacy"] == tampered


def test_module_has_no_execution_or_network_surface():
    source = __import__("apply_contract").__file__
    text = open(source, encoding="utf-8").read()
    assert "requests" not in text and "selenium" not in text
    assert "def apply(" not in text and "def execute" not in text
