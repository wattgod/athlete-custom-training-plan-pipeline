import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webhook"))

from delivery.trainingpeaks.phase5_service import (
    ExecutionGrantCodec,
    Phase5AuthorizationError,
    Phase5Interrupted,
    Phase5MutationService,
    Phase5ReadbackMismatch,
    compile_browser_dry_run,
    request_application_cancellation,
)
from delivery.trainingpeaks.worker_service import CapabilityCodec
from d2_identity import record_identity_result
from fulfillment_state import (
    APPLIED,
    APPLYING,
    APPROVED,
    finalize_transitional_release,
    load,
    transition,
    write_generation,
)


NOW = 1_800_000_000
AUDIENCE = "gg-trainingpeaks-worker"
CAPABILITY_KEYS = {"cap-k1": "phase5-capability-signing-secret-0001"}
GRANT_KEYS = {"grant-k1": "phase5-execution-grant-secret-00001"}
TP_ID = "fixture-phase5-athlete"
ORDER_ID = "order_phase5_fixture"


def _approved_state(tmp_path):
    state_path = tmp_path / "fulfillment_status.json"
    state = write_generation(
        state_path, "fixture-athlete", order_id=ORDER_ID,
        delivery_platform="trainingpeaks",
    )
    state = record_identity_result(
        state_path, state["generation_revision"], {
            "outcome": "bound", "tp_athlete_id": TP_ID, "candidates": [],
        }, capability_jti="fixture-phase5-identity-jti",
    )
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "guide.html").write_text("fixture guide", encoding="utf-8")
    state = finalize_transitional_release(
        state_path, artifacts, expected_revision=state["generation_revision"])
    decisions = [
        {"item_id": item["item_id"], "revision": state["generation_revision"],
         "disposition": "confirmed"}
        for item in state["review_items"]
        if item["type"] in {"required_confirmation", "verified_fact"}
    ]
    state = transition(
        state_path, APPROVED, "fixture-coach",
        expected_revision=state["generation_revision"],
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=decisions,
    )
    return state_path, state


def _contract(state):
    return {
        "contract_version": "apply_contract/v1",
        "order_id": state["order_id"],
        "tp_athlete_id": TP_ID,
        "generation_revision": state["generation_revision"],
        "model_seal": state["model_seal"],
        "operations": [
            {
                "op_id": f"{ORDER_ID}:workout_upsert:keep@r1",
                "logical_id": f"{ORDER_ID}:workout_upsert:keep",
                "kind": "workout_upsert", "disposition": "keep",
                "expected_digest": "1" * 64,
            },
            {
                "op_id": f"{ORDER_ID}:workout_upsert:create@r1",
                "logical_id": f"{ORDER_ID}:workout_upsert:create",
                "kind": "workout_upsert", "disposition": "create",
                "expected_digest": "2" * 64,
            },
            {
                "op_id": f"{ORDER_ID}:calendar_note_upsert:delete@r1",
                "logical_id": f"{ORDER_ID}:calendar_note_upsert:delete",
                "kind": "calendar_note_upsert", "disposition": "delete",
                "expected_digest": None,
            },
        ],
    }


def _service(tmp_path):
    capability_codec = CapabilityCodec(CAPABILITY_KEYS, audience=AUDIENCE)
    grant_codec = ExecutionGrantCodec(GRANT_KEYS, audience="gg-tp-phase5-executor")
    return Phase5MutationService(
        capability_codec, grant_codec, tmp_path / "worker", grant_kid="grant-k1")


def _capability(service, state, contract, **overrides):
    claims = {
        "order_id": state["order_id"], "tp_athlete_id": TP_ID,
        "generation_revision": state["generation_revision"],
        "model_seal": state["model_seal"], "action": "apply",
        "audience": AUDIENCE, "iat": NOW - 1, "exp": NOW + 120,
        "jti": "phase5-mutation-jti-000001",
    }
    claims.update(overrides)
    return service.capability_codec.issue(claims, kid="cap-k1")


def _successful_executor(context):
    for operation in context.contract["operations"]:
        if operation["disposition"] == "keep":
            context.record_receipt(
                operation, status="kept", remote_id="existing-1",
                observed_digest=operation["expected_digest"])
        elif operation["disposition"] == "delete":
            context.persist_intent(operation)
            context.record_receipt(
                operation, status="absent", remote_id="deleted-1",
                observed_digest=None)
        else:
            context.persist_intent(operation)
            context.record_receipt(
                operation, status="landed", remote_id="created-1",
                observed_digest=operation["expected_digest"])
    return {"readback_verified": True}


def test_exchange_and_execute_reach_applied_only_after_exact_receipts(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    applying = load(state_path)
    assert applying["status"] == APPLYING
    assert applying["application_attempt"]["status"] == "accepted"
    assert applying["application_attempt"]["fencing_token"] == 1

    receipt = service.execute(
        grant, contract, state_path, _successful_executor, now=NOW + 1)
    assert receipt["status"] == "applied"
    assert receipt["operation_count"] == 3
    applied = load(state_path)
    assert applied["status"] == APPLIED
    assert applied["application_attempt"]["status"] == "succeeded"
    assert applied["application"]["receipt_digest"] == receipt["receipt_digest"]


def test_succeeded_grant_replays_without_running_executor_twice(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    first = service.execute(grant, contract, state_path, _successful_executor, now=NOW + 1)
    calls = []
    replay = service.execute(
        grant, contract, state_path,
        lambda _context: calls.append(True), now=NOW + 2)
    assert replay == first
    assert calls == []


def test_missing_or_mismatched_readback_leaves_order_applying(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def incomplete(context):
        operation = context.contract["operations"][0]
        context.record_receipt(
            operation, status="kept", remote_id="existing-1",
            observed_digest=operation["expected_digest"])
        return {"readback_verified": True}

    with pytest.raises(Phase5ReadbackMismatch, match="receipt count"):
        service.execute(grant, contract, state_path, incomplete, now=NOW + 1)
    assert load(state_path)["status"] == APPLYING
    assert load(state_path)["application"] is None


def test_mutating_receipt_without_durable_intent_is_refused(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def bypass(context):
        operation = context.contract["operations"][1]
        context.record_receipt(
            operation, status="landed", remote_id="created-1",
            observed_digest=operation["expected_digest"])
        return {"readback_verified": True}

    with pytest.raises(Phase5AuthorizationError, match="no durable pre-mutation intent"):
        service.execute(grant, contract, state_path, bypass, now=NOW + 1)
    assert load(state_path)["status"] == APPLYING


def test_contract_identity_drift_is_refused_before_applying(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    drifted = dict(contract)
    drifted["tp_athlete_id"] = "wrong-athlete"
    with pytest.raises(Phase5AuthorizationError, match="tp_athlete_id mismatch"):
        service.exchange(
            _capability(service, state, contract), drifted, state_path, now=NOW)
    assert load(state_path)["status"] == APPROVED


def test_cancellation_revokes_epoch_and_marks_partial_writes_for_compensation(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def interrupted(context):
        operation = context.contract["operations"][1]
        context.persist_intent(operation)
        context.record_receipt(
            operation, status="landed", remote_id="created-1",
            observed_digest=operation["expected_digest"])
        raise Phase5Interrupted("fixture kill point")

    with pytest.raises(Phase5Interrupted):
        service.execute(grant, contract, state_path, interrupted, now=NOW + 1)
    cancelled = request_application_cancellation(
        state_path, actor="fixture-coach", reason="fixture cancellation")
    assert cancelled["execution_epoch"] == 1
    assert cancelled["compensation_pending"] is True
    with pytest.raises((Phase5Interrupted, Phase5AuthorizationError)):
        service.execute(grant, contract, state_path, _successful_executor, now=NOW + 2)


def test_generated_browser_transport_dry_run_has_complete_zero_write_plan(tmp_path):
    _state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    dry_run = compile_browser_dry_run(contract)
    assert dry_run["external_writes_performed"] is False
    assert dry_run["operation_count"] == len(contract["operations"])
    assert [item["op_id"] for item in dry_run["operations"]] == [
        item["op_id"] for item in contract["operations"]]
    assert sum(item["would_mutate"] for item in dry_run["operations"]) == 2


def test_privacy_records_exclude_capability_and_grant_tokens(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    capability = _capability(service, state, contract)
    grant = service.exchange(capability, contract, state_path, now=NOW)
    service.execute(grant, contract, state_path, _successful_executor, now=NOW + 1)
    rendered = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "worker").rglob("*.json"))
    assert capability not in rendered
    assert grant not in rendered
    assert "phase5-capability-signing-secret" not in rendered
    assert "phase5-execution-grant-secret" not in rendered


def test_expired_capability_is_refused_before_state_transition(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    expired = _capability(service, state, contract, iat=NOW - 60, exp=NOW)
    with pytest.raises(Phase5AuthorizationError, match="not currently valid"):
        service.exchange(expired, contract, state_path, now=NOW)
    assert load(state_path)["status"] == APPROVED


def test_interrupted_partial_execution_resumes_without_losing_receipts(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def first_attempt(context):
        operation = context.contract["operations"][0]
        context.record_receipt(
            operation, status="kept", remote_id="existing-1",
            observed_digest=operation["expected_digest"])
        raise Phase5Interrupted("fixture process stop")

    with pytest.raises(Phase5Interrupted):
        service.execute(grant, contract, state_path, first_attempt, now=NOW + 1)

    observed_prior = []

    def resumed(context):
        observed_prior.extend(context.prior_receipts)
        return _successful_executor(context)

    receipt = service.execute(grant, contract, state_path, resumed, now=NOW + 2)
    assert receipt["status"] == "applied"
    assert [item["op_id"] for item in observed_prior] == [
        contract["operations"][0]["op_id"]]


def test_new_fence_invalidates_older_grant_for_same_resumable_attempt(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    capability = _capability(service, state, contract)
    first_grant = service.exchange(capability, contract, state_path, now=NOW)
    second_grant = service.exchange(capability, contract, state_path, now=NOW + 1)
    with pytest.raises(Phase5AuthorizationError, match="stale or fenced"):
        service.execute(
            first_grant, contract, state_path, _successful_executor, now=NOW + 2)
    receipt = service.execute(
        second_grant, contract, state_path, _successful_executor, now=NOW + 2)
    assert receipt["status"] == "applied"


def test_controlled_rollback_compensates_created_resource_and_clears_pending(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    contract["operations"] = [
        {**contract["operations"][0], "rollback": {"strategy": "none"}},
        {**contract["operations"][1],
         "rollback": {"strategy": "delete_by_remote_id"}},
    ]
    service = _service(tmp_path)
    apply_grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def apply_executor(context):
        keep, create = context.contract["operations"]
        context.record_receipt(
            keep, status="kept", remote_id="existing-1",
            observed_digest=keep["expected_digest"])
        context.persist_intent(create)
        context.record_receipt(
            create, status="landed", remote_id="created-1",
            observed_digest=create["expected_digest"])
        return {"readback_verified": True}

    service.execute(apply_grant, contract, state_path, apply_executor, now=NOW + 1)
    cancelled = request_application_cancellation(
        state_path, actor="fixture-coach", reason="exercise compensation")
    assert cancelled["compensation_pending"] is True

    rollback_capability = _capability(
        service, state, contract, action="rollback",
        jti="phase5-rollback-jti-000001", iat=NOW + 1, exp=NOW + 120)
    rollback_grant = service.exchange(
        rollback_capability, contract, state_path, now=NOW + 2,
        operator_authorized=True)

    def rollback_executor(context):
        create = context.contract["operations"][1]
        context.persist_intent(create)
        context.record_receipt(
            create, status="absent", remote_id="created-1",
            observed_digest=None)
        return {"rollback_verified": True}

    receipt = service.execute(
        rollback_grant, contract, state_path, rollback_executor, now=NOW + 3)
    assert receipt["status"] == "rolled_back"
    final = load(state_path)
    assert final["status"] == "CANCELLED"
    assert final["compensation_pending"] is False
    assert final["cancellation"]["worker_stop_acknowledged"] is True
