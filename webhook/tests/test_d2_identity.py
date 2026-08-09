import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(ROOT / "athletes/scripts"))

from apply_contract import build_contract
from delivery.trainingpeaks.worker_service import (
    CapabilityCodec,
    CannedProbeTransport,
    ProbeExecutionStore,
    ReadOnlyWorkerService,
)
from d2_identity import (
    DEMOGRAPHIC_ITEM_ID,
    DORMANCY_ITEM_ID,
    THRESHOLD_ITEM_ID,
    d2_contract_inputs,
    record_account_inspection,
    record_identity_result,
    record_manual_readback,
    resolve_d2_item,
    select_identity_candidate,
)
from fulfillment_state import (
    APPLIED,
    APPROVED,
    FulfillmentStateError,
    finalize_transitional_release,
    load,
    transition,
    write_generation,
)


FIXTURE = ROOT / "tests/fixtures/athlete_m"
OBSERVED_AT = "2026-08-06T15:00:00Z"


def _seed(
    tmp_path, order_id="phase4-d2", *, control_value=None, intake_lthr=None,
    intake_age=45,
):
    path = tmp_path / f"{order_id}.json"
    state = write_generation(
        path, "athlete-m", order_id=order_id,
        delivery_platform="trainingpeaks",
        required_confirmations=[{
            "id": "SCHEDULE_MISMATCH_CONFIRM", "source": "post_render",
            "message": "Schedule mismatch fixture.",
            "review_value": {"mismatch": True},
            "basis": "generated schedule", "sensitivity": "personal",
        }],
    )
    state = record_identity_result(
        path, state["generation_revision"], {
            "outcome": "bound", "tp_athlete_id": "fixture-athlete-m",
            "candidates": [],
        }, capability_jti="probe-jti-00000000000001")
    fixture = json.loads((FIXTURE / "worker_probes.json").read_text())
    fixture["tp_athlete_id"] = "fixture-athlete-m"
    state = record_account_inspection(
        path, state["generation_revision"], fixture,
        intake_age=intake_age, intake_thresholds={"lthr": intake_lthr},
        control_metric="hr", canonical_control_value=control_value,
        capability_jti="inspect-jti-0000000000001",
        observed_at=OBSERVED_AT,
    )
    return path, state


def _seal(path, tmp_path):
    state = load(path)
    root = tmp_path / f"seal-r{state['generation_revision']}"
    root.mkdir()
    (root / "review.txt").write_text("sealed phase4 review")
    return finalize_transitional_release(
        path, root, expected_revision=state["generation_revision"])


def _approval_decisions(state):
    result = []
    for item in state["review_items"]:
        if item["type"] not in {"required_confirmation", "verified_fact"}:
            continue
        disposition = (
            f"resolved:{item['resolved_resolution']}"
            if item.get("resolved_resolution") else "confirmed"
        )
        result.append({
            "item_id": item["item_id"],
            "revision": state["generation_revision"],
            "disposition": disposition,
        })
    return result


def _worker_evidence(tmp_path, state, *, lthr, jti):
    fixture = json.loads((FIXTURE / "worker_probes.json").read_text())
    fixture["lthr_bpm"] = lthr
    fixture["tp_athlete_id"] = "fixture-athlete-m"
    now = 1_800_000_000
    audience = "gg-trainingpeaks-worker"
    kid = "phase4-test"
    codec = CapabilityCodec(
        {kid: "phase4-readback-test-signing-secret-0001"}, audience=audience)
    worker = ReadOnlyWorkerService(
        codec, ProbeExecutionStore(tmp_path / f"replay-{jti}"),
        CannedProbeTransport(fixture),
    )
    claims = {
        "order_id": state["order_id"],
        "subject": {
            "kind": "identity_query", "tp_athlete_id": "fixture-athlete-m",
        },
        "action": "inspect", "audience": audience,
        "iat": now - 1, "exp": now + 300, "jti": jti,
    }
    return worker.inspect_account_evidence(
        "fixture-athlete-m", codec.issue(claims, kid=kid), now=now)


def _regenerate_and_seal_if_needed(path, tmp_path, state):
    if state.get("regeneration_request"):
        state = write_generation(
            path, state["athlete_id"], order_id=state["order_id"],
            delivery_platform=state["delivery_platform"],
        )
    if not state.get("model_seal"):
        state = _seal(path, tmp_path)
    return state


def test_athlete_m_inspection_materializes_exact_phase4_findings_and_sensitive_provenance(tmp_path):
    path, state = _seed(tmp_path)
    assert state["identity_resolution"]["outcome"] == "bound"
    assert state["platform_identity"]["tp_athlete_id"] == "fixture-athlete-m"
    assert state["platform_identity"]["order_id"] == state["order_id"]
    assert [item["id"] for item in state["required_confirmations"]] == [
        DEMOGRAPHIC_ITEM_ID, THRESHOLD_ITEM_ID, "SCHEDULE_MISMATCH_CONFIRM",
    ]
    threshold = next(
        item for item in state["required_confirmations"]
        if item["id"] == THRESHOLD_ITEM_ID)
    assert threshold["review_value"] == {
        "metric": "lthr", "control_metric": "hr", "account_value": 148,
        "plan_value": None, "unit": "bpm", "account_value_date": "2019-05-01",
        "stale": True,
    }
    age = next(item for item in state["required_confirmations"]
               if item["id"] == DEMOGRAPHIC_ITEM_ID)
    assert age["review_value"] == {
        "field": "age", "account_value": 19, "intake_value": 45,
    }
    assert [item["id"] for item in state["soft_confirmations"]] == [DORMANCY_ITEM_ID]
    derived = {item["id"]: item for item in state["derived_values"]}
    assert {"D2_ACCOUNT_AGE", "D2_ACCOUNT_FTP", "D2_ACCOUNT_LTHR"} <= set(derived)
    assert all(item["class"] == "externally_observed" for key, item in derived.items()
               if key.startswith("D2_"))
    assert all(item["sensitivity"] == "sensitive" for key, item in derived.items()
               if key.startswith("D2_"))
    assert load(path)["account_inspection"]["ftp_watts"] == 197


def test_approval_rejects_unresolved_d2_items_even_with_all_generic_confirmations(tmp_path):
    path, _ = _seed(tmp_path)
    state = _seal(path, tmp_path)
    with pytest.raises(FulfillmentStateError, match="D2 review item is unresolved"):
        transition(
            path, APPROVED, "coach",
            expected_revision=state["generation_revision"],
            expected_catalog_digest=state["review_catalog_digest"],
            review_decisions=_approval_decisions(state),
        )


def test_use_tp_value_writes_canonical_override_and_starts_new_revision(tmp_path):
    path, _ = _seed(tmp_path)
    sealed = _seal(path, tmp_path)
    resolved = resolve_d2_item(
        path, sealed["generation_revision"], THRESHOLD_ITEM_ID,
        "use-tp-value", actor="review-link:k1:jti")
    assert resolved["generation_revision"] == sealed["generation_revision"] + 1
    assert resolved["canonical_input_overrides"]["hr_threshold"] == 148
    assert resolved["d2_context"]["canonical_control_value"] == 148
    assert resolved["regeneration_request"]["reason"].startswith("D2 resolution")
    assert resolved["model_seal"] is None and resolved["approval"] is None
    assert next(item for item in resolved["required_confirmations"]
                if item["id"] == THRESHOLD_ITEM_ID)["resolved_resolution"] == "use-tp-value"

    regenerated = write_generation(
        path, "athlete-m", order_id=resolved["order_id"],
        delivery_platform="trainingpeaks")
    assert regenerated["generation_revision"] == resolved["generation_revision"] + 1
    assert regenerated["regeneration_request"] is None
    assert regenerated["canonical_input_overrides"]["hr_threshold"] == 148
    carried = next(item for item in regenerated["required_confirmations"]
                   if item["id"] == THRESHOLD_ITEM_ID)
    assert carried["resolved_resolution"] == "use-tp-value"
    assert carried["review_value"]["plan_value"] == 148


def test_update_from_intake_emits_d0_threshold_update_with_before_image_and_keeps_plan_anchor(tmp_path):
    path, state = _seed(tmp_path, control_value=160, intake_lthr=160)
    resolved = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        "update-from-intake", actor="coach")
    tp_id, desires, inspection = d2_contract_inputs(resolved)
    assert tp_id == "fixture-athlete-m"
    assert desires["lthr"] == {
        "kind": "threshold_update",
        "payload": {"metric": "lthr", "after_value": 160, "unit": "bpm"},
    }
    assert resolved["d2_context"]["canonical_control_value"] == 160
    contract = build_contract(
        {"weeks": [{"number": 1, "sessions": [{
            "date": "2026-08-10", "title": "Fixture ride",
            "description": "Fixture", "workout_type_value_id": 1,
            "duration_s": 3600, "tss_planned": 40, "structure": None,
            "type": "workout",
        }]}]}, order_id=resolved["order_id"], tp_athlete_id=tp_id,
        generation_revision=resolved["generation_revision"],
        canonical_model={"model_version": "fixture"},
        review_items=resolved["review_items"], guide_sources={},
        singleton_desires=desires, inspection=inspection,
    )
    operation = next(op for op in contract["operations"]
                     if op["kind"] == "threshold_update")
    assert operation["disposition"] == "update"
    assert operation["payload"]["after_value"] == 160
    assert operation["before_image"]["value"] == 148
    assert operation["rollback"] == {"strategy": "restore_before_image"}


def test_update_from_intake_refuses_when_intake_has_no_threshold(tmp_path):
    path, state = _seed(tmp_path)
    with pytest.raises(FulfillmentStateError, match="requires an intake threshold"):
        resolve_d2_item(
            path, state["generation_revision"], THRESHOLD_ITEM_ID,
            "update-from-intake", actor="coach")


def test_approval_is_legal_when_threshold_update_resolution_matches_sealed_plan(tmp_path):
    path = tmp_path / "approved-update.json"
    state = write_generation(
        path, "athlete-m", order_id="approved-update",
        delivery_platform="trainingpeaks")
    state = record_identity_result(
        path, state["generation_revision"], {
            "outcome": "bound", "tp_athlete_id": "fixture-athlete-m",
            "candidates": [],
        }, capability_jti="approve-probe-jti-0000001")
    fixture = json.loads((FIXTURE / "worker_probes.json").read_text())
    fixture["tp_athlete_id"] = "fixture-athlete-m"
    state = record_account_inspection(
        path, state["generation_revision"], fixture,
        intake_age=19, intake_thresholds={"lthr": 160},
        control_metric="hr", canonical_control_value=160,
        capability_jti="approve-inspect-jti-00001", observed_at=OBSERVED_AT)
    state = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        "update-from-intake", actor="coach")
    state = _seal(path, tmp_path)
    approved = transition(
        path, APPROVED, "coach",
        expected_revision=state["generation_revision"],
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=_approval_decisions(state),
    )
    assert approved["status"] == APPROVED
    snapshot = next(item for item in approved["approval"]["confirmations"]
                    if item["item_id"] == THRESHOLD_ITEM_ID)
    assert snapshot["disposition"] == "resolved:update-from-intake"
    assert approved["d2_apply_operations"]["lthr"]["payload"]["after_value"] == 160


def test_manually_corrected_sealed_review_requires_exact_verified_worker_readback(tmp_path):
    path, state = _seed(
        tmp_path, control_value=155, intake_lthr=155, intake_age=19)
    state = _seal(path, tmp_path)
    original_seal = state["model_seal"]
    pending = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        "manually-corrected", actor="coach")
    assert pending["d2_pending_requirements"][THRESHOLD_ITEM_ID]["expected_value"] == 155
    assert pending["model_seal"] == original_seal
    assert pending["regeneration_request"] is None
    assert "resolved_resolution" not in next(
        item for item in pending["required_confirmations"]
        if item["id"] == THRESHOLD_ITEM_ID)
    with pytest.raises(FulfillmentStateError, match="readback is still required"):
        transition(
            path, APPROVED, "coach",
            expected_revision=pending["generation_revision"],
            expected_catalog_digest=pending["review_catalog_digest"],
            review_decisions=_approval_decisions(pending),
        )
    with pytest.raises(FulfillmentStateError, match="verified worker"):
        record_manual_readback(
            path, pending["generation_revision"], THRESHOLD_ITEM_ID,
            {"lthr_bpm": 155},
        )
    with pytest.raises(FulfillmentStateError, match="does not confirm"):
        record_manual_readback(
            path, pending["generation_revision"], THRESHOLD_ITEM_ID,
            _worker_evidence(
                tmp_path, pending, lthr=154,
                jti="readback-jti-00000000001"),
        )
    confirmed = record_manual_readback(
        path, pending["generation_revision"], THRESHOLD_ITEM_ID,
        _worker_evidence(
            tmp_path, pending, lthr=155,
            jti="readback-jti-00000000002"),
    )
    assert THRESHOLD_ITEM_ID not in confirmed["d2_pending_requirements"]
    evidence = confirmed["d2_resolutions"][THRESHOLD_ITEM_ID]["readback_evidence"]
    assert evidence["record_type"] == "d2_worker_readback/v1"
    assert evidence["value"] == 155
    assert evidence["capability_jti"] == "readback-jti-00000000002"
    assert evidence["request_digest"]
    assert evidence["observed_at"] == "2027-01-15T08:00:00Z"
    assert confirmed["model_seal"] == original_seal
    derived = next(item for item in confirmed["derived_values"]
                   if item["id"] == "D2_MANUAL_READBACK_LTHR")
    assert derived["value"] == 155
    assert derived["class"] == "externally_observed"
    assert derived["inputs"]["capability_jti"] == evidence["capability_jti"]

    approved = transition(
        path, APPROVED, "coach",
        expected_revision=confirmed["generation_revision"],
        expected_catalog_digest=confirmed["review_catalog_digest"],
        review_decisions=_approval_decisions(confirmed),
    )
    assert approved["status"] == APPROVED


def test_cannot_resolve_creates_nonwaivable_blocker(tmp_path):
    path, state = _seed(tmp_path)
    blocked = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        "cannot-resolve", actor="coach")
    issue = next(item for item in blocked["blocking_issues"]
                 if item["id"] == "D2_CANNOT_RESOLVE")
    assert issue["waivable"] is False
    assert blocked["d2_resolutions"][THRESHOLD_ITEM_ID]["effect"] == "non-waivable-block"


def test_identity_outcomes_and_candidate_binding_are_order_scoped(tmp_path):
    for outcome, rule in (
        ("not-coached", "ATHLETE_UNLINKED"),
        ("not-found", "ATHLETE_NO_ACCOUNT"),
        ("unresolved", "ATHLETE_IDENTITY_UNRESOLVED"),
    ):
        path = tmp_path / f"{outcome}.json"
        state = write_generation(
            path, "athlete-m", order_id=f"order-{outcome}",
            delivery_platform="trainingpeaks")
        state = record_identity_result(
            path, state["generation_revision"],
            {"outcome": outcome, "candidates": []},
            capability_jti=f"{outcome}-jti-00000000001")
        assert [item["id"] for item in state["blocking_issues"]] == [rule]
        assert state["blocking_issues"][0]["waivable"] is False

    path = tmp_path / "multiple.json"
    state = write_generation(
        path, "athlete-m", order_id="order-multiple",
        delivery_platform="trainingpeaks")
    state = record_identity_result(
        path, state["generation_revision"], {
            "outcome": "multiple-candidates", "candidates": [
                {"tp_athlete_id": "candidate-a", "label": "Candidate A"},
                {"tp_athlete_id": "candidate-b", "label": "Candidate B"},
            ],
        }, capability_jti="multiple-jti-00000000001")
    with pytest.raises(FulfillmentStateError, match="exact candidate"):
        select_identity_candidate(
            path, state["generation_revision"], "candidate-c", actor="coach")
    bound = select_identity_candidate(
        path, state["generation_revision"], "candidate-b", actor="coach")
    assert bound["identity_resolution"]["outcome"] == "bound"
    assert bound["platform_identity"] == {
        "platform": "trainingpeaks", "tp_athlete_id": "candidate-b",
        "order_id": "order-multiple", "bound_at": bound["platform_identity"]["bound_at"],
        "binding_evidence": {"actor": "coach", "selection": "candidate"},
    }


def test_manual_delivery_does_not_block_on_missing_platform_account(tmp_path):
    path = tmp_path / "manual.json"
    state = write_generation(
        path, "athlete-m", order_id="manual-order", delivery_platform="manual")
    state = record_identity_result(
        path, state["generation_revision"],
        {"outcome": "not-found", "candidates": []},
        capability_jti="manual-probe-jti-0000001")
    assert state["blocking_issues"] == []


@pytest.mark.parametrize("platform", ["trainingpeaks", "endure"])
def test_automated_approval_requires_order_scoped_platform_identity(tmp_path, platform):
    path = tmp_path / f"{platform}-missing-identity.json"
    state = write_generation(
        path, "athlete-m", order_id=f"order-{platform}",
        delivery_platform=platform)
    state = _seal(path, tmp_path)
    with pytest.raises(FulfillmentStateError, match="bound platform identity"):
        transition(
            path, APPROVED, "coach",
            expected_revision=state["generation_revision"],
            expected_catalog_digest=state["review_catalog_digest"],
            review_decisions=_approval_decisions(state),
        )


@pytest.mark.parametrize("platform", ["trainingpeaks", "endure"])
def test_automated_approval_accepts_valid_binding(tmp_path, platform):
    path = tmp_path / f"{platform}-bound.json"
    state = write_generation(
        path, "athlete-m", order_id=f"bound-{platform}",
        delivery_platform=platform)
    state = record_identity_result(
        path, state["generation_revision"], {
            "outcome": "bound", "tp_athlete_id": f"athlete-{platform}",
            "candidates": [],
        }, capability_jti=f"binding-{platform}-jti-000001")
    state = _seal(path, tmp_path)
    approved = transition(
        path, APPROVED, "coach",
        expected_revision=state["generation_revision"],
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=_approval_decisions(state),
    )
    assert approved["status"] == APPROVED


def test_wrong_order_platform_binding_is_rejected_fail_closed(tmp_path):
    path = tmp_path / "wrong-order-binding.json"
    state = write_generation(
        path, "athlete-m", order_id="right-order",
        delivery_platform="trainingpeaks")
    raw = json.loads(path.read_text())
    raw["platform_identity"] = {
        "platform": "trainingpeaks", "tp_athlete_id": "athlete-wrong-order",
        "order_id": "different-order", "bound_at": OBSERVED_AT,
        "binding_evidence": {"capability_jti": "wrong-order-jti-0000001"},
    }
    path.write_text(json.dumps(raw))
    with pytest.raises(FulfillmentStateError, match="malformed"):
        load(path)


def test_manual_approval_needs_no_binding_but_applied_needs_matching_evidence(tmp_path):
    path = tmp_path / "manual-approval-direction.json"
    state = write_generation(
        path, "athlete-m", order_id="manual-direction",
        delivery_platform="manual")
    state = _seal(path, tmp_path)
    approved = transition(
        path, APPROVED, "coach",
        expected_revision=state["generation_revision"],
        expected_catalog_digest=state["review_catalog_digest"],
        review_decisions=_approval_decisions(state),
    )
    assert approved["platform_identity"] is None
    with pytest.raises(FulfillmentStateError, match="nonempty evidence"):
        transition(path, APPLIED, "coach", platform="manual", evidence="")
    applied = transition(
        path, APPLIED, "coach", platform="manual",
        evidence="coach attested exact sealed package delivery")
    assert applied["status"] == APPLIED


@pytest.mark.parametrize(
    "first_choice,second_choice",
    [
        (first, second)
        for first in sorted({
            "use-tp-value", "update-from-intake", "manually-corrected",
            "cannot-resolve",
        })
        for second in sorted({
            "use-tp-value", "update-from-intake", "manually-corrected",
            "cannot-resolve",
        })
        if first != second
    ],
)
def test_threshold_resolution_switch_retracts_all_prior_effects_and_validates_terminal_state(
    tmp_path, first_choice, second_choice,
):
    path, state = _seed(
        tmp_path, order_id=f"switch-{first_choice}-to-{second_choice}",
        control_value=160, intake_lthr=160, intake_age=19)
    state = _seal(path, tmp_path)
    state = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        first_choice, actor="coach:first")
    state = _regenerate_and_seal_if_needed(path, tmp_path, state)
    if first_choice == "manually-corrected":
        state = record_manual_readback(
            path, state["generation_revision"], THRESHOLD_ITEM_ID,
            _worker_evidence(
                tmp_path, state, lthr=160,
                jti="first-readback-jti-00000001"),
        )
    state = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        second_choice, actor="coach:second")
    state = _regenerate_and_seal_if_needed(path, tmp_path, state)

    assert state["canonical_input_overrides"] == (
        {"hr_threshold": 148} if second_choice == "use-tp-value" else {})
    assert state["d2_apply_operations"] == (
        {"lthr": {
            "kind": "threshold_update",
            "payload": {"metric": "lthr", "after_value": 160, "unit": "bpm"},
        }} if second_choice == "update-from-intake" else {})
    assert set(state["d2_pending_requirements"]) == (
        {THRESHOLD_ITEM_ID} if second_choice == "manually-corrected" else set())
    resolution = state["d2_resolutions"][THRESHOLD_ITEM_ID]
    assert resolution["choice"] == second_choice
    assert "readback_evidence" not in resolution
    assert "D2_MANUAL_READBACK_LTHR" not in {
        item["id"] for item in state["derived_values"]}
    assert ("D2_CANNOT_RESOLVE" in {
        issue["id"] for issue in state["blocking_issues"]
    }) is (second_choice == "cannot-resolve")

    if second_choice == "manually-corrected":
        state = record_manual_readback(
            path, state["generation_revision"], THRESHOLD_ITEM_ID,
            _worker_evidence(
                tmp_path, state, lthr=160,
                jti="switch-readback-jti-0000001"),
        )
    if second_choice == "cannot-resolve":
        with pytest.raises(FulfillmentStateError, match="cannot be resolved"):
            transition(
                path, APPROVED, "coach",
                expected_revision=state["generation_revision"],
                expected_catalog_digest=state["review_catalog_digest"],
                review_decisions=_approval_decisions(state),
            )
    else:
        approved = transition(
            path, APPROVED, "coach",
            expected_revision=state["generation_revision"],
            expected_catalog_digest=state["review_catalog_digest"],
            review_decisions=_approval_decisions(state),
        )
        assert approved["status"] == APPROVED


def test_approval_rejects_tampered_current_resolution_effects(tmp_path):
    path, state = _seed(
        tmp_path, order_id="tampered-terminal-effects",
        control_value=160, intake_lthr=160, intake_age=19)
    state = resolve_d2_item(
        path, state["generation_revision"], THRESHOLD_ITEM_ID,
        "update-from-intake", actor="coach")
    state = _regenerate_and_seal_if_needed(path, tmp_path, state)
    raw = json.loads(path.read_text())
    raw["d2_apply_operations"]["lthr"]["payload"].update({
        "metric": "ftp", "after_value": 197, "unit": "W",
    })
    path.write_text(json.dumps(raw))
    tampered = load(path)
    with pytest.raises(FulfillmentStateError, match="apply-contract effects"):
        transition(
            path, APPROVED, "coach",
            expected_revision=tampered["generation_revision"],
            expected_catalog_digest=tampered["review_catalog_digest"],
            review_decisions=_approval_decisions(tampered),
        )
