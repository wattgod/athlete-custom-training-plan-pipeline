"""Order-bound, offline Dynamic Plan packaging regression tests."""
import hashlib
import json
from pathlib import Path

import pytest

from tools import build_sealed_tp_plan_package as sealed
from tools import build_tp_plan_payload as standalone
from tools.test_build_tp_plan_payload import (PLAN_DAY_ONE, golden_fulfillment_manifest,
                                              golden_notes, golden_sessions,
                                              golden_tp_manifest)
from webhook.fulfillment_state import (finalize_transitional_release,
                                       transition, write_generation)


def _write(path: Path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _order(tmp_path, order_id="paid-order-1", blockers=None, *, clean=False,
           ambiguous=False, malformed_workout=False, malformed_plan_date=False,
           pdf=False):
    root = tmp_path / "orders" / order_id
    root.mkdir(parents=True)
    state_path = root / "fulfillment_status.json"
    state = write_generation(state_path, "fixture-athlete", blockers or [],
                             order_id=order_id)
    revision = root / "revisions" / f"r{state['generation_revision']}"
    artifacts = revision / "artifacts"
    artifacts.mkdir(parents=True)
    tp = golden_tp_manifest()
    if clean:
        tp["sessions"][-1]["title"] = "Endurance Ride"
    _write(artifacts / "tp_manifest.json", tp)
    fulfillment = golden_fulfillment_manifest()
    if clean:
        fulfillment["workouts"][-1]["title"] = "Endurance Ride"
    if malformed_workout:
        fulfillment["workouts"][0] = None
    _write(artifacts / "fulfillment_manifest.json", fulfillment)
    plan_ir = {
        "athlete": {"id": "fixture-athlete"},
        "weeks": ([] if ambiguous else [
            {"number": 0, "sessions": [{"date": "2026-08-25",
                                          "title": "Pre-Plan Easy"}]},
            {"number": 1, "sessions": [
            {"date": session["date"], "title": session["title"]}
            for session in tp["sessions"]
            if session["date"] >= PLAN_DAY_ONE]}]),
    }
    if malformed_plan_date:
        plan_ir["weeks"][0]["sessions"][0]["date"] = None
    _write(artifacts / "plan_ir.json", plan_ir)
    _write(artifacts / "canonical_training_model.json", {"athlete_id": "fixture-athlete"})
    (artifacts / "training_guide.html").write_text("sealed guide", encoding="utf-8")
    if pdf:
        (artifacts / "training_guide.pdf").write_bytes(b"%PDF-1.4\nfixture guide\n")
    finalize_transitional_release(state_path, revision,
                                  expected_revision=state["generation_revision"])
    return state_path, revision, artifacts


def _build(tmp_path, order_id="paid-order-1", blockers=None, **kwargs):
    state_path, revision, artifacts = _order(tmp_path, order_id, blockers, **kwargs)
    out = tmp_path / "scratch" / order_id
    return state_path, revision, artifacts, out


def test_sealed_package_coverage_and_payload_reconciliation(tmp_path):
    state, revision, artifacts, out = _build(tmp_path)
    out.mkdir(parents=True)
    (out / "plan_payload.json").write_text("stale")
    (out / "coverage_receipt.json").write_text('{"ready_for_review": true}')
    receipt = sealed.build("paid-order-1", state, revision, out)
    assert receipt["ready_for_review"] is False  # unresolved AE-3.11 FAIL
    assert not (out / "plan_payload.json").exists()
    assert json.loads((out / "coverage_receipt.json").read_text())["ready_for_review"] is False
    assert receipt["counts"] == {
        "source_sessions": 6, "included_sessions": 5, "excluded_sessions": 1,
        "source_notes": 3, "included_notes": 2, "excluded_notes": 1,
        "redated_notes": 1,
    }
    assert [item["disposition"] for item in receipt["sessions"]] == [
        "excluded", "included", "included", "included", "included", "included"]
    assert [item["disposition"] for item in receipt["notes"]] == [
        "redated", "excluded", "included"]
    assert receipt["sessions"][0]["action"] == "manual_W00_placement"
    assert receipt["notes"][0]["action"] == "comment_protocol_to_plan_day_one"
    assert receipt["guide_sha256"] == hashlib.sha256(b"sealed guide").hexdigest()
    assert receipt["customer_guide"] == {
        "path": "artifacts/training_guide.html",
        "sha256": hashlib.sha256(b"sealed guide").hexdigest(),
    }
    assert receipt["model_seal"]
    assert receipt["release_manifest_digest"]


def test_ready_payload_is_deterministic_and_reconciles(tmp_path):
    state, revision, artifacts, out = _build(tmp_path, clean=True)
    receipt = sealed.build("paid-order-1", state, revision, out)
    assert receipt["ready_for_review"] is True
    plan = json.loads((out / "plan_payload.json").read_text())
    notes = json.loads((out / "notes_payload.json").read_text())
    source = json.loads((artifacts / "tp_manifest.json").read_text())["sessions"]
    for item in receipt["sessions"]:
        if item["disposition"] != "included":
            continue
        projected = plan[item["output_index"]]
        original = source[item["source_index"]]
        assert projected["workoutDay"] == original["date"] + "T00:00:00"
        assert projected["totalTimePlanned"] == original["total_time_planned"]
        assert projected["tssPlanned"] == original["tss_planned"]
        assert projected["description"] == original["description"]
        assert projected["structure"] == standalone._apply_computed_polyline(
            standalone.suppress_zero_power(original["structure"]))
        assert projected.get("coachComments") == original["pre_activity_comment"]
    assert notes[0]["noteDate"] == PLAN_DAY_ONE
    assert notes[0]["description"] == golden_notes()[0]["text"]
    before = {name: (out / name).read_bytes() for name in sealed.OUTPUT_NAMES}
    sealed.build("paid-order-1", state, revision, out)
    assert before == {name: (out / name).read_bytes() for name in sealed.OUTPUT_NAMES}


def test_pdf_customer_guide_and_html_renderer_source_are_both_seal_bound(tmp_path):
    state, revision, _, out = _build(tmp_path, clean=True, pdf=True)
    receipt = sealed.build("paid-order-1", state, revision, out)
    html_digest = hashlib.sha256(b"sealed guide").hexdigest()
    pdf_digest = hashlib.sha256(b"%PDF-1.4\nfixture guide\n").hexdigest()
    assert receipt["ready_for_review"] is True
    assert receipt["guide_artifacts"] == {
        "artifacts/training_guide.html": html_digest,
        "artifacts/training_guide.pdf": pdf_digest,
    }
    assert receipt["customer_guide"] == {
        "path": "artifacts/training_guide.pdf", "sha256": pdf_digest,
    }
    assert receipt["guide_sha256"] == pdf_digest


@pytest.mark.parametrize("target", ["training_guide.html", "canonical_training_model.json"])
def test_edited_sealed_artifact_rejected_and_stale_ready_removed(tmp_path, target):
    state, revision, artifacts, out = _build(tmp_path)
    out.mkdir(parents=True)
    (out / "plan_payload.json").write_text("stale")
    (out / "coverage_receipt.json").write_text('{"ready_for_review": true}')
    (artifacts / target).write_text("edited")
    with pytest.raises(Exception, match="sealed artifact mismatch"):
        sealed.build("paid-order-1", state, revision, out)
    assert not (out / "plan_payload.json").exists()
    assert not (out / "coverage_receipt.json").exists()


def test_stale_revision_and_mismatched_order_rejected(tmp_path):
    state, revision, _, out = _build(tmp_path)
    with pytest.raises(sealed.SealedPackageError, match="stale"):
        sealed.build("paid-order-1", state, revision.parent / "r2", out)
    with pytest.raises(sealed.SealedPackageError, match="order"):
        sealed.build("paid-order-2", state, revision, out)


def test_missing_source_and_ambiguous_day_one_rejected(tmp_path):
    state, revision, artifacts, out = _build(tmp_path)
    (artifacts / "plan_ir.json").unlink()
    with pytest.raises(Exception, match="sealed artifact unavailable"):
        sealed.build("paid-order-1", state, revision, out)
    assert not (out / "coverage_receipt.json").exists()
    state2, revision2, _, out2 = _build(tmp_path / "other", ambiguous=True)
    with pytest.raises(sealed.SealedPackageError, match="ambiguous plan day one"):
        sealed.build("paid-order-1", state2, revision2, out2)


def test_same_athlete_orders_have_distinct_receipts(tmp_path):
    first = _build(tmp_path, "paid-order-1")
    second = _build(tmp_path, "paid-order-2")
    r1 = sealed.build("paid-order-1", first[0], first[1], first[3])
    r2 = sealed.build("paid-order-2", second[0], second[1], second[3])
    assert r1["athlete_id"] == r2["athlete_id"]
    assert r1["order_id"] != r2["order_id"]


def test_blocked_source_never_gets_ready_payload(tmp_path):
    blocker = {"id": "ENDURANCE_TSS_RATE_LOW", "source": "post_render",
               "severity": "CRITICAL", "message": "A named non-waivable quality defect"}
    state, revision, _, out = _build(tmp_path, blockers=[blocker], clean=True)
    receipt = sealed.build("paid-order-1", state, revision, out)
    assert receipt["ready_for_review"] is False
    assert receipt["blocking_issue_ids"] == ["ENDURANCE_TSS_RATE_LOW"]
    assert not (out / "plan_payload.json").exists()


def test_cancelled_order_never_gets_ready_payload(tmp_path):
    state, revision, _, out = _build(tmp_path, clean=True)
    transition(state, "CANCELLED", "Coach", metadata={"reason": "refunded"})
    receipt = sealed.build("paid-order-1", state, revision, out)
    assert receipt["ready_for_review"] is False
    assert not (out / "plan_payload.json").exists()


def test_output_inside_order_rejected(tmp_path):
    state, revision, _, _ = _build(tmp_path)
    with pytest.raises(sealed.SealedPackageError, match="outside"):
        sealed.build("paid-order-1", state, revision, revision / "artifacts" / "derived")


@pytest.mark.parametrize("malformation,message", [
    ("malformed_workout", "malformed fulfillment session inventory"),
    ("malformed_plan_date", "malformed PlanIR session date"),
])
def test_malformed_sealed_inventory_has_named_error_and_clears_stale_ready(
        tmp_path, malformation, message):
    state, revision, _, out = _build(tmp_path, clean=True, **{malformation: True})
    out.mkdir(parents=True)
    (out / "coverage_receipt.json").write_text('{"ready_for_review": true}')
    (out / "plan_payload.json").write_text("stale")
    with pytest.raises(sealed.SealedPackageError, match=message):
        sealed.build("paid-order-1", state, revision, out)
    assert not (out / "coverage_receipt.json").exists()
    assert not (out / "plan_payload.json").exists()
