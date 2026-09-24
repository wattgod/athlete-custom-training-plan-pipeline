"""The existing coach approval binds the exact sealed TP review package."""

import hashlib

from tools import build_sealed_tp_plan_package as sealed
from tools import test_build_sealed_tp_plan_package as package_tests
from webhook.fulfillment_state import APPROVED, load, transition


def _tp_order(tmp_path, monkeypatch):
    original = package_tests.write_generation

    def trainingpeaks_generation(*args, **kwargs):
        kwargs["delivery_platform"] = "trainingpeaks"
        return original(*args, **kwargs)

    monkeypatch.setattr(package_tests, "write_generation", trainingpeaks_generation)
    state_path, revision_dir, _, package_dir = package_tests._build(
        tmp_path, clean=True, pdf=True)
    return state_path, revision_dir, package_dir


def _approve(path):
    state = load(path)
    decisions = [{"item_id": item["item_id"],
                  "revision": state["generation_revision"],
                  "disposition": "confirmed"}
                 for item in state["review_items"]
                 if item["type"] in {"required_confirmation", "verified_fact"}]
    return transition(path, APPROVED, "Coach", expected_revision=state["generation_revision"],
                      expected_catalog_digest=state["review_catalog_digest"],
                      review_decisions=decisions, credential="operator-secret")


def test_existing_approval_binds_exact_tp_receipt_and_customer_guide(tmp_path, monkeypatch):
    path, revision, package_dir = _tp_order(tmp_path, monkeypatch)
    receipt = sealed.build("paid-order-1", path, revision, package_dir)
    assert receipt["ready_for_review"] is True

    approved = _approve(path)
    assert approved["approval"]["tp_package_binding"] == {
        "coverage_receipt_sha256": hashlib.sha256(
            (package_dir / "coverage_receipt.json").read_bytes()).hexdigest(),
        "customer_guide": receipt["customer_guide"],
    }


def test_legacy_trainingpeaks_approval_without_card1_artifacts_still_works(tmp_path):
    from webhook.tests.test_fulfillment_state import _approve as approve_legacy
    from webhook.tests.test_fulfillment_state import _seal
    from webhook.fulfillment_state import write_generation, approval_matches_release

    path = tmp_path / "status.json"
    write_generation(path, "legacy-athlete", order_id="legacy-order",
                     delivery_platform="trainingpeaks")
    _seal(path, tmp_path)
    approved = approve_legacy(path)
    assert approval_matches_release(approved)
    assert "tp_package_binding" not in approved["approval"]
