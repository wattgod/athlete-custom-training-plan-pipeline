"""Offline review packet guards for sealed paid orders."""
import json

import pytest

from tools import build_order_review_packet as packet
from tools import build_sealed_tp_plan_package as sealed
from tools.test_build_sealed_tp_plan_package import _build
from webhook.tests.test_tp_package_approval import _approve, _tp_order


def _ready(tmp_path):
    state, revision, artifacts, out = _build(tmp_path, clean=True, pdf=True)
    sealed.build("paid-order-1", state, revision, out)
    return state, revision, artifacts, out


def test_packet_exposes_order_artifacts_and_blocks_unproven_release(tmp_path):
    state, revision, artifacts, out = _ready(tmp_path)
    result = packet.build("paid-order-1", state, revision, out)
    assert result["order_id"] == "paid-order-1"
    assert result["tp_ready_for_review"] is True
    assert result["artifacts"]["guide_pdf"]["sha256"]
    assert result["artifacts"]["guide_html"]["sha256"]
    assert result["payload_receipt_sha256"]
    assert result["coverage"]["source_sessions"] == 6
    assert [row["spot"] for row in result["spot_checks"]] == [
        "week_one", "middle", "race_week"]
    assert result["release_ready"] is False
    assert any("W00" in reason for reason in result["release_blockers"])
    assert any("payload receipt" in reason
               for reason in result["release_blockers"])


def test_packet_rejects_changed_receipt_and_sealed_guide(tmp_path):
    state, revision, artifacts, out = _ready(tmp_path)
    receipt_path = out / "coverage_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["order_id"] = "another-paid-order"
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(packet.PacketError, match="differs"):
        packet.build("paid-order-1", state, revision, out)
    sealed.build("paid-order-1", state, revision, out)
    (artifacts / "training_guide.html").write_text("changed guide")
    with pytest.raises(Exception, match="sealed artifact mismatch"):
        packet.build("paid-order-1", state, revision, out)


def test_packet_marks_missing_pdf_and_plan_preview(tmp_path):
    state, revision, artifacts, out = _build(tmp_path, clean=True)
    sealed.build("paid-order-1", state, revision, out)
    result = packet.build("paid-order-1", state, revision, out)
    assert "customer PDF guide is missing" in result["release_blockers"]
    assert "exact plan preview is missing" in result["release_blockers"]


def test_blocked_order_retains_coach_packet_without_ready_payload(tmp_path):
    blocker = {"id": "QUALITY_FAIL", "source": "fixture", "severity": "CRITICAL",
               "message": "review before release"}
    state, revision, _, out = _build(tmp_path, clean=True, blockers=[blocker])
    sealed.build("paid-order-1", state, revision, out)
    result = packet.build("paid-order-1", state, revision, out)
    assert [item["id"] for item in result["quality_blockers"]] == ["QUALITY_FAIL"]
    assert result["tp_ready_for_review"] is False
    assert result["artifacts"]["plan_payload"] is None
    assert result["release_ready"] is False


def test_guide_fact_drift_is_visible():
    plan = {"athlete": {"name": "Sample Athlete"},
            "events": [{"name": "Sample Race", "date": "2026-10-01"}]}
    checks = packet._guide_checks(plan, "<html><body>Sample Athlete rides a different race.</body></html>")
    assert checks == [{"fact": "athlete_name", "value": "Sample Athlete", "present": True},
                      {"fact": "event_0_name", "value": "Sample Race", "present": False}]


def test_foreign_draft_journal_does_not_claim_readiness(tmp_path):
    state, revision, artifacts, out = _ready(tmp_path)
    journal = tmp_path / "foreign-journal.json"
    journal.write_text(json.dumps({"status": "verified", "plan_id": 123,
                                   "folder_proof": {"verified": True},
                                   "binding": {"order_id": "another-order"}}))
    result = packet.build("paid-order-1", state, revision, out,
                          draft_journal=journal)
    assert result["tp_draft"]["verified"] is False
    assert any("DRAFT" in reason for reason in result["release_blockers"])


def test_packet_recognizes_only_matching_existing_tp_approval(tmp_path, monkeypatch):
    state, revision, out = _tp_order(tmp_path, monkeypatch)
    sealed.build("paid-order-1", state, revision, out)
    _approve(state)
    result = packet.build("paid-order-1", state, revision, out)
    assert result["approval"]["current"] is True
    assert result["approval"]["package_bound"] is True
    assert not any("payload receipt" in reason for reason in result["release_blockers"])

    raw = json.loads(state.read_text())
    raw["approval"]["tp_package_binding"]["coverage_receipt_sha256"] = "0" * 64
    state.write_text(json.dumps(raw))
    stale = packet.build("paid-order-1", state, revision, out)
    assert stale["approval"]["package_bound"] is False
    assert any("payload receipt" in reason for reason in stale["release_blockers"])
