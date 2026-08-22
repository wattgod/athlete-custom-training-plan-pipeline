import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webhook"))

from delivery.trainingpeaks.phase5_service import (
    CanaryPolicy,
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
from tools.tp_phase5_execute import build_parser


NOW = 1_800_000_000
AUDIENCE = "gg-trainingpeaks-worker"
CAPABILITY_KEYS = {"cap-k1": "phase5-capability-signing-secret-0001"}
GRANT_KEYS = {"grant-k1": "phase5-execution-grant-secret-00001"}
TP_ID = "fixture-phase5-athlete"
ORDER_ID = "order_phase5_fixture"


def _digest(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _approved_state(tmp_path, *, order_id=ORDER_ID):
    state_path = tmp_path / "fulfillment_status.json"
    state = write_generation(
        state_path, "fixture-athlete", order_id=order_id,
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
    order_id = state["order_id"]
    revision = state["generation_revision"]
    prior_note = {
        "date": "2026-08-31", "title": "Legacy note", "body": "Protected prior note",
    }
    create_workout = {
        "date": "2026-09-01", "title": "Fixture create",
        "description": "Fixture only", "tp_workout_type": 1,
        "total_seconds": 3600, "tss_planned": 50, "structure": None,
    }
    return {
        "contract_version": "apply_contract/v1",
        "order_id": state["order_id"],
        "tp_athlete_id": TP_ID,
        "generation_revision": state["generation_revision"],
        "model_seal": state["model_seal"],
        "operations": [
            {
                "op_id": f"{order_id}:calendar_note_upsert:legacy-note@r{revision}",
                "logical_id": f"{order_id}:calendar_note_upsert:legacy-note",
                "kind": "calendar_note_upsert", "disposition": "delete",
                "payload": None, "expected_digest": None,
                "prior_payload": prior_note, "before_image": None,
                "remote_marker": f"{order_id}:calendar_note_upsert:legacy-note",
                "predecessor": {"op_id": "prior-note-op", "remote_id": "note-1"},
                "rollback": {"strategy": "recreate_from_prior_payload"},
            },
            {
                "op_id": f"{order_id}:workout_upsert:2026-09-01#1@r{revision}",
                "logical_id": f"{order_id}:workout_upsert:2026-09-01#1",
                "kind": "workout_upsert", "disposition": "create",
                "payload": create_workout, "expected_digest": _digest(create_workout),
                "prior_payload": None, "before_image": None,
                "remote_marker": f"{order_id}:workout_upsert:2026-09-01#1",
                "predecessor": None,
                "rollback": {"strategy": "delete_by_remote_id"},
            },
            {
                "op_id": f"{order_id}:workout_upsert:2026-09-02#1@r{revision}",
                "logical_id": f"{order_id}:workout_upsert:2026-09-02#1",
                "kind": "workout_upsert", "disposition": "keep",
                "payload": None, "expected_digest": "1" * 64,
                "prior_payload": None, "before_image": None,
                "remote_marker": f"{order_id}:workout_upsert:2026-09-02#1",
                "predecessor": {"op_id": "prior-workout-op", "remote_id": "workout-1"},
                "rollback": {"strategy": "none"},
            },
        ],
        "compat": {"min_reader": "apply_contract/v1"},
    }


def _service(tmp_path):
    capability_codec = CapabilityCodec(CAPABILITY_KEYS, audience=AUDIENCE)
    grant_codec = ExecutionGrantCodec(GRANT_KEYS, audience="gg-tp-phase5-executor")
    return Phase5MutationService(
        capability_codec, grant_codec, tmp_path / "worker", grant_kid="grant-k1",
        live_writes_enabled=True)


def _capability(service, state, contract, **overrides):
    action = overrides.pop("action", "trainingpeaks.apply")
    if action in {"apply", "verify", "rollback"}:
        action = f"trainingpeaks.{action}"
    claims = {
        "order_id": state["order_id"], "tp_athlete_id": TP_ID,
        "generation_revision": state["generation_revision"],
        "model_seal": state["model_seal"],
        "contract_digest": _digest(contract),
        "approval_digest": _digest(state["approval"]),
        "release_manifest_digest": state["release_manifest_digest"],
        "authorization_id": f"phase5-authorization-{action.rsplit('.', 1)[-1]}-000001",
        "actor": "coach:fixture", "scope": "trainingpeaks:athlete-calendar",
        "action": action,
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


def _operation(contract, disposition):
    return next(
        item for item in contract["operations"]
        if item["disposition"] == disposition
    )


def _workout_update(state, *, date="2026-08-30"):
    order_id = state["order_id"]
    revision = state["generation_revision"]
    prior = {
        "date": date, "title": "Fixture prior", "description": "Before",
        "tp_workout_type": 1, "total_seconds": 2700, "tss_planned": 35,
        "structure": None,
    }
    payload = {
        "date": date, "title": "Fixture update", "description": "After",
        "tp_workout_type": 1, "total_seconds": 3300, "tss_planned": 45,
        "structure": None,
    }
    logical_id = f"{order_id}:workout_upsert:{date}#1"
    return {
        "op_id": f"{logical_id}@r{revision}", "logical_id": logical_id,
        "kind": "workout_upsert", "disposition": "update",
        "payload": payload, "expected_digest": _digest(payload),
        "prior_payload": prior, "before_image": None,
        "remote_marker": logical_id,
        "predecessor": {"op_id": "prior-update-op", "remote_id": "updated-1"},
        "rollback": {"strategy": "restore_prior_payload"},
    }


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
        context.persist_intent(operation)
        context.record_receipt(
            operation, status="absent", remote_id="deleted-1",
            observed_digest=None)
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


@pytest.mark.parametrize(
    "mutation",
    [
        "single_field", "reorder", "add", "delete", "payload",
        "prior_payload", "before_image", "rollback_strategy",
    ],
)
def test_signed_authorization_refuses_any_contract_substitution_before_applying(
    tmp_path, mutation,
):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    capability = _capability(service, state, contract)
    substituted = copy.deepcopy(contract)

    if mutation == "single_field":
        _operation(substituted, "keep")["expected_digest"] = "a" * 64
    elif mutation == "reorder":
        substituted["operations"].reverse()
    elif mutation == "add":
        added = copy.deepcopy(_operation(substituted, "keep"))
        added["logical_id"] = added["logical_id"].replace("2026-09-02", "2026-09-03")
        added["op_id"] = added["op_id"].replace("2026-09-02", "2026-09-03")
        added["remote_marker"] = added["logical_id"]
        substituted["operations"].append(added)
    elif mutation == "delete":
        substituted["operations"].pop()
    elif mutation == "payload":
        operation = _operation(substituted, "create")
        operation["payload"]["title"] = "Substituted workout"
        operation["expected_digest"] = _digest(operation["payload"])
    elif mutation == "prior_payload":
        _operation(substituted, "delete")["prior_payload"]["body"] = "Substituted"
    elif mutation == "before_image":
        _operation(substituted, "create")["before_image"] = {"changed": True}
    elif mutation == "rollback_strategy":
        _operation(substituted, "create")["rollback"]["strategy"] = "none"

    with pytest.raises(Phase5AuthorizationError):
        service.exchange(capability, substituted, state_path, now=NOW)
    assert load(state_path)["status"] == APPROVED
    assert load(state_path)["application_attempt"] is None


def test_authorization_action_and_approval_snapshot_are_exact(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)

    verify_only = _capability(
        service, state, contract, action="verify",
        jti="phase5-verify-action-000001",
    )
    with pytest.raises(Phase5AuthorizationError, match="verify status"):
        service.exchange(verify_only, contract, state_path, now=NOW)

    stale_approval = _capability(
        service, state, contract, approval_digest="f" * 64,
        jti="phase5-stale-approval-00001",
    )
    with pytest.raises(Phase5AuthorizationError, match="approval snapshot is stale"):
        service.exchange(stale_approval, contract, state_path, now=NOW)

    stale_release = _capability(
        service, state, contract, release_manifest_digest="e" * 64,
        jti="phase5-stale-release-000001",
    )
    with pytest.raises(Phase5AuthorizationError, match="release manifest is stale"):
        service.exchange(stale_release, contract, state_path, now=NOW)
    assert load(state_path)["status"] == APPROVED


def test_execution_grant_retains_redacted_authorization_bindings(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    claims = service.grant_codec.verify(grant, now=NOW).claims
    assert claims["request_digest"] == _digest(contract)
    assert claims["approval_digest"] == _digest(state["approval"])
    assert claims["release_manifest_digest"] == state["release_manifest_digest"]
    assert claims["authorization_id"] == "phase5-authorization-apply-000001"
    assert claims["actor"] == "coach:fixture"
    assert claims["scope"] == "trainingpeaks:athlete-calendar"


def test_canonical_entrypoint_has_no_boolean_rollback_authorization():
    argv = [
        "--contract", "contract.json", "--state", "state.json",
        "--capability-file", "capability.txt", "--record-root", "records",
        "--staging-root", "staging", "--operator-authorized",
    ]
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)


def test_cancellation_revokes_epoch_and_marks_partial_writes_for_compensation(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def interrupted(context):
        deleted, operation = context.contract["operations"][:2]
        context.persist_intent(deleted)
        context.record_receipt(
            deleted, status="absent", remote_id="deleted-1",
            observed_digest=None)
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
        context.persist_intent(operation)
        context.record_receipt(
            operation, status="absent", remote_id="deleted-1",
            observed_digest=None)
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


def test_capability_replay_is_refused_and_original_grant_remains_valid(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    capability = _capability(service, state, contract)
    first_grant = service.exchange(capability, contract, state_path, now=NOW)
    replay = _capability(
        service, state, contract, jti="phase5-mutation-jti-replay02",
        iat=NOW, exp=NOW + 120,
    )
    with pytest.raises(Phase5AuthorizationError, match="already exchanged"):
        service.exchange(replay, contract, state_path, now=NOW + 1)
    receipt = service.execute(
        first_grant, contract, state_path, _successful_executor, now=NOW + 2)
    assert receipt["status"] == "applied"


def test_controlled_rollback_compensates_created_resource_and_clears_pending(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    contract["operations"] = [
        _operation(contract, "create"),
        _operation(contract, "keep"),
    ]
    service = _service(tmp_path)
    apply_grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def apply_executor(context):
        create, keep = context.contract["operations"]
        context.persist_intent(create)
        context.record_receipt(
            create, status="landed", remote_id="created-1",
            observed_digest=create["expected_digest"])
        context.record_receipt(
            keep, status="kept", remote_id="existing-1",
            observed_digest=keep["expected_digest"])
        return {"readback_verified": True}

    service.execute(apply_grant, contract, state_path, apply_executor, now=NOW + 1)
    cancelled = request_application_cancellation(
        state_path, actor="fixture-coach", reason="exercise compensation")
    assert cancelled["compensation_pending"] is True

    rollback_capability = _capability(
        service, state, contract, action="rollback",
        jti="phase5-rollback-jti-000001", iat=NOW + 1, exp=NOW + 120)
    rollback_grant = service.exchange(
        rollback_capability, contract, state_path, now=NOW + 2)

    def rollback_executor(context):
        assert context.prior_receipts == [
            {
                "op_id": contract["operations"][0]["op_id"],
                "logical_id": contract["operations"][0]["logical_id"],
                "kind": "workout_upsert", "disposition": "create",
                "status": "landed", "remote_id": "created-1",
                "observed_digest": contract["operations"][0]["expected_digest"],
                "reconciled_after_error": False,
            },
        ]
        create = context.contract["operations"][0]
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


def test_disabled_global_writes_require_an_explicit_canary_lane(tmp_path):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    service.live_writes_enabled = False
    with pytest.raises(Phase5AuthorizationError, match="no canary lane"):
        service.exchange(
            _capability(service, state, contract), contract, state_path, now=NOW)


def test_canary_lane_allows_only_exact_target_bounded_contract(tmp_path):
    state_path, state = _approved_state(tmp_path, order_id="canary_cheesehead")
    contract = _contract(state)
    service = _service(tmp_path)
    service.live_writes_enabled = False
    service.canary_policy = CanaryPolicy(
        allowed_tp_athlete_ids=frozenset({TP_ID}))
    capability = _capability(
        service, state, contract, order_id="canary_cheesehead")
    grant = service.exchange(capability, contract, state_path, now=NOW)
    assert service.grant_codec.verify(grant, now=NOW).claims["tp_athlete_id"] == TP_ID

    other_policy = CanaryPolicy(
        allowed_tp_athlete_ids=frozenset({"different-fixture"}))
    service.canary_policy = other_policy
    with pytest.raises(Phase5AuthorizationError, match="not allowlisted"):
        service.exchange(capability, contract, state_path, now=NOW + 1)


def test_partial_apply_freezes_landed_only_targets_and_rollback_resumes_in_reverse(
    tmp_path,
):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    legacy_delete, create, keep = contract["operations"]
    update = _workout_update(state)
    # Normative order is dated update/delete first, then dated create/keep.
    contract["operations"] = [update, legacy_delete, create, keep]
    service = _service(tmp_path)
    apply_grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def partial_apply(context):
        context.persist_intent(update)
        context.record_receipt(
            update, status="landed", remote_id="updated-1",
            observed_digest=update["expected_digest"])
        context.persist_intent(legacy_delete)
        context.record_receipt(
            legacy_delete, status="absent", remote_id="deleted-note-1",
            observed_digest=None)
        context.persist_intent(create)
        context.record_receipt(
            create, status="landed", remote_id="created-1",
            observed_digest=create["expected_digest"])
        context.record_failure(
            op_id=keep["op_id"], code="HTTP_ERROR",
            at="2026-08-22T01:02:03Z", receipt_digest="f" * 64)
        raise Phase5Interrupted("strict partial receipt")

    with pytest.raises(Phase5Interrupted):
        service.execute(apply_grant, contract, state_path, partial_apply, now=NOW + 1)
    applying = load(state_path)
    assert applying["status"] == APPLYING
    assert [item["op_id"] for item in applying["application_attempt"]["landed"]] == [
        operation["op_id"] for operation in contract["operations"][:3]
    ]
    assert applying["application_attempt"]["failure"] == {
        "op_id": keep["op_id"], "code": "HTTP_ERROR",
        "at": "2026-08-22T01:02:03Z", "receipt_digest": "f" * 64,
    }

    cancelled = request_application_cancellation(
        state_path, actor="fixture-coach", reason="compensate partial apply")
    assert cancelled["compensation_pending"] is True
    assert [item["op_id"] for item in
            cancelled["application_attempt"]["compensation_targets"]] == [
        update["op_id"], legacy_delete["op_id"], create["op_id"]]

    rollback_grant = service.exchange(
        _capability(
            service, state, contract, action="rollback",
            jti="phase5-rollback-resume-jti", iat=NOW + 1, exp=NOW + 120),
        contract, state_path, now=NOW + 2)

    def rollback_crash(context):
        assert [item["op_id"] for item in context.prior_receipts] == [
            update["op_id"], legacy_delete["op_id"], create["op_id"]]
        assert context.rollback_receipts == []
        context.persist_intent(create)
        context.record_receipt(
            create, status="absent", remote_id="created-1",
            observed_digest=None)
        context.record_failure(
            op_id=legacy_delete["op_id"], code="HTTP_ERROR",
            at="2026-08-22T01:03:03Z", receipt_digest="e" * 64)
        raise Phase5Interrupted("rollback process death")

    with pytest.raises(Phase5Interrupted):
        service.execute(
            rollback_grant, contract, state_path, rollback_crash, now=NOW + 3)
    partial = load(state_path)
    assert partial["compensation_pending"] is True
    assert [item["op_id"] for item in
            partial["application_attempt"]["compensation_receipts"]] == [
        create["op_id"]]

    def rollback_resume(context):
        assert [item["op_id"] for item in context.rollback_receipts] == [
            create["op_id"]]
        context.persist_intent(legacy_delete)
        context.record_receipt(
            legacy_delete, status="restored", remote_id="recreated-note-9",
            observed_digest=_digest(legacy_delete["prior_payload"]),
            reconciled_after_error=True)
        context.persist_intent(update)
        context.record_receipt(
            update, status="restored", remote_id="updated-1",
            observed_digest=_digest(update["prior_payload"]))
        return {"rollback_verified": True}

    receipt = service.execute(
        rollback_grant, contract, state_path, rollback_resume, now=NOW + 4)
    assert receipt["status"] == "rolled_back"
    assert [item["op_id"] for item in receipt["receipts"]] == [
        create["op_id"], legacy_delete["op_id"], update["op_id"]]
    final = load(state_path)
    assert final["compensation_pending"] is False
    assert final["status"] == "CANCELLED"


def test_state_first_receipt_checkpoint_recovers_when_record_write_dies(
    tmp_path, monkeypatch,
):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    service = _service(tmp_path)
    grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)
    original_write = service._write_json
    injected = {"done": False}

    def fail_once(path, value):
        if (not injected["done"] and value.get("record_type")
                and value.get("receipts")):
            injected["done"] = True
            raise OSError("simulated process death between state and record")
        return original_write(path, value)

    monkeypatch.setattr(service, "_write_json", fail_once)

    def first(context):
        deleted = context.contract["operations"][0]
        context.persist_intent(deleted)
        context.record_receipt(
            deleted, status="absent", remote_id="deleted-1",
            observed_digest=None)
        raise AssertionError("checkpoint crash should interrupt before this line")

    with pytest.raises(OSError, match="simulated process death"):
        service.execute(grant, contract, state_path, first, now=NOW + 1)
    checkpointed = load(state_path)
    assert checkpointed["status"] == APPLYING
    assert [item["op_id"] for item in
            checkpointed["application_attempt"]["landed"]] == [
        contract["operations"][0]["op_id"]]

    observed = []

    def resume(context):
        observed.extend(context.prior_receipts)
        return _successful_executor(context)

    receipt = service.execute(grant, contract, state_path, resume, now=NOW + 2)
    assert receipt["status"] == "applied"
    assert [item["op_id"] for item in observed] == [
        contract["operations"][0]["op_id"]]


@pytest.mark.parametrize("crash_after", [0, 1, 2, 3])
def test_rollback_crash_retry_is_safe_at_every_prefix_boundary(
    tmp_path, crash_after,
):
    state_path, state = _approved_state(tmp_path)
    contract = _contract(state)
    delete, create, keep = contract["operations"]
    update = _workout_update(state)
    contract["operations"] = [update, delete, create, keep]
    service = _service(tmp_path)
    apply_grant = service.exchange(
        _capability(service, state, contract), contract, state_path, now=NOW)

    def apply_all(context):
        for operation, status, remote_id in [
            (update, "landed", "updated-1"),
            (delete, "absent", "deleted-note-1"),
            (create, "landed", "created-1"),
        ]:
            context.persist_intent(operation)
            context.record_receipt(
                operation, status=status, remote_id=remote_id,
                observed_digest=(operation["expected_digest"]
                                 if status == "landed" else None))
        context.record_receipt(
            keep, status="kept", remote_id="protected-1",
            observed_digest=keep["expected_digest"])
        return {"readback_verified": True}

    service.execute(apply_grant, contract, state_path, apply_all, now=NOW + 1)
    request_application_cancellation(
        state_path, actor="fixture-coach", reason="rollback boundary test")
    rollback_grant = service.exchange(
        _capability(
            service, state, contract, action="rollback",
            jti=f"phase5-rollback-boundary-{crash_after}",
            iat=NOW + 1, exp=NOW + 120),
        contract, state_path, now=NOW + 2)
    expected = [create, delete, update]

    def compensate(operation, context):
        context.persist_intent(operation)
        if operation is delete:
            context.record_receipt(
                operation, status="restored", remote_id="recreated-9",
                observed_digest=_digest(delete["prior_payload"]))
        elif operation is update:
            context.record_receipt(
                operation, status="restored", remote_id="updated-1",
                observed_digest=_digest(update["prior_payload"]))
        else:
            context.record_receipt(
                operation, status="absent", remote_id="created-1",
                observed_digest=None, reconciled_after_error=True)

    def crash(context):
        for operation in expected[:crash_after]:
            compensate(operation, context)
        raise Phase5Interrupted("rollback boundary crash")

    with pytest.raises(Phase5Interrupted):
        service.execute(rollback_grant, contract, state_path, crash, now=NOW + 3)
    partial = load(state_path)
    assert partial["compensation_pending"] is True
    assert [item["op_id"] for item in
            partial["application_attempt"]["compensation_receipts"]] == [
        item["op_id"] for item in expected[:crash_after]]

    def resume(context):
        assert [item["op_id"] for item in context.rollback_receipts] == [
            item["op_id"] for item in expected[:crash_after]]
        for operation in expected[crash_after:]:
            compensate(operation, context)
        return {"rollback_verified": True}

    receipt = service.execute(
        rollback_grant, contract, state_path, resume, now=NOW + 4)
    assert [item["op_id"] for item in receipt["receipts"]] == [
        item["op_id"] for item in expected]
    assert load(state_path)["compensation_pending"] is False
