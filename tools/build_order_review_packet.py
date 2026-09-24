#!/usr/bin/env python3
"""Read-only, order-specific coach review packet for a sealed TP package.

This reports evidence and release blockers; it never grants approval or writes
an athlete calendar, hosted guide, order state, or TrainingPeaks plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "webhook") not in sys.path:
    sys.path.insert(0, str(ROOT / "webhook"))

from tools import build_sealed_tp_plan_package as sealed
from webhook.fulfillment_state import approval_matches_release, load


class PacketError(ValueError):
    pass


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"missing or malformed review input: {path.name}") from exc


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _norm(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def _guide_checks(plan, guide_html):
    parser = _Text()
    parser.feed(guide_html)
    text = _norm(" ".join(parser.parts))
    facts = []
    athlete = plan.get("athlete") or {}
    if athlete.get("name"):
        facts.append(("athlete_name", athlete["name"]))
    for index, event in enumerate(plan.get("events") or []):
        if event.get("name"):
            facts.append((f"event_{index}_name", event["name"]))
    return [{"fact": key, "value": value, "present": _norm(value) in text}
            for key, value in facts]


def _spot_checks(plan):
    weeks = [week for week in plan.get("weeks", []) if isinstance(week, dict)
             and week.get("number", 0) >= 1]
    if not weeks:
        return []
    weeks.sort(key=lambda week: week["number"])
    chosen = [("week_one", weeks[0]), ("middle", weeks[len(weeks) // 2])]
    events = plan.get("events") or []
    race_dates = {event.get("date") for event in events if event.get("priority") == "A"}
    race = next((week for week in weeks if any(
        item.get("date") in race_dates for item in week.get("sessions", []))), weeks[-1])
    chosen.append(("race_week", race))
    return [{"spot": spot, "week": week["number"],
             "sessions": [{"date": item.get("date"), "title": item.get("title")}
                          for item in week.get("sessions", [])]}
            for spot, week in chosen]


def build(order_id: str, state_path: Path, revision_dir: Path,
          package_dir: Path, *, draft_journal: Path | None = None) -> dict:
    state_path, revision_dir, package_dir = map(
        lambda path: Path(path).resolve(), (state_path, revision_dir, package_dir))
    # Rebuilding invokes the canonical state, exact revision, and sealed-byte
    # verifier. Scratch output is disposed and cannot become release authority.
    with tempfile.TemporaryDirectory(prefix="coach-review-packet-") as scratch:
        receipt = sealed.build(order_id, state_path, revision_dir, Path(scratch))
        names = ["coverage_receipt.json", "exclusions.json", "lint.json"]
        if receipt["ready_for_review"]:
            names += ["plan_payload.json", "notes_payload.json"]
        for name in names:
            if _read(package_dir / name) != _read(Path(scratch) / name):
                raise PacketError(f"package {name} differs from current sealed source")
    state = load(state_path)
    if (state.get("generation_revision") != receipt["generation_revision"]
            or state.get("model_seal") != receipt["model_seal"]
            or state.get("release_manifest_digest") != receipt["release_manifest_digest"]):
        raise PacketError("order revision changed during packet build")
    artifacts = revision_dir / "artifacts"
    plan = _read(artifacts / "plan_ir.json")
    model = _read(artifacts / "canonical_training_model.json")
    guide = artifacts / "training_guide.html"
    pdf = artifacts / "training_guide.pdf"
    checks = _guide_checks(plan, guide.read_text(encoding="utf-8"))
    blockers = []
    if not (artifacts / "plan_preview.html").is_file():
        blockers.append("exact plan preview is missing")
    if not pdf.is_file():
        blockers.append("customer PDF guide is missing")
    elif not pdf.read_bytes().startswith(b"%PDF-"):
        blockers.append("customer PDF guide is malformed")
    if not checks:
        blockers.append("guide has no comparable athlete or event facts")
    blockers.extend(f"guide/plan drift: {check['fact']}" for check in checks
                    if not check["present"])
    if (plan.get("athlete") or {}).get("id") != state["athlete_id"] or (
            model.get("athlete") or {}).get("id") != state["athlete_id"]:
        blockers.append("athlete identity differs across sealed sources")
    identity = state.get("identity_resolution") or {}
    binding = state.get("platform_identity") or {}
    if (identity.get("outcome") != "bound" or not binding.get("tp_athlete_id")
            or binding.get("order_id") != order_id):
        blockers.append("exact order-scoped TP athlete identity is unresolved")
    if not receipt["ready_for_review"]:
        blockers.append("sealed TP package is not ready for review")
    w00 = [entry for kind in ("sessions", "notes") for entry in receipt[kind]
           if entry.get("action") == "manual_W00_placement"]
    if w00:
        blockers.append("W00 manual placement has no recorded disposition")
    if state.get("blocking_issues"):
        blockers.append("canonical order has unresolved quality blockers")
    journal = _read(Path(draft_journal)) if draft_journal else None
    if journal is not None and not isinstance(journal, dict):
        raise PacketError("malformed draft journal")
    journal_binding = (journal or {}).get("binding") or {}
    folder_proof = (journal or {}).get("folder_proof") or {}
    package_digests = ({name: _json_digest(_read(package_dir / name)) for name in
                        ("coverage_receipt.json", "plan_payload.json", "notes_payload.json")}
                       if receipt["ready_for_review"] else None)
    draft_verified = bool(journal and journal.get("status") == "verified"
                          and journal.get("plan_id")
                          and folder_proof.get("verified") is True
                          and folder_proof.get("plan_id") == journal.get("plan_id")
                          and folder_proof.get("folder") == journal_binding.get("expected_folder")
                          and folder_proof.get("evidence")
                          and journal_binding.get("order_id") == order_id
                          and journal_binding.get("generation_revision")
                          == receipt["generation_revision"]
                          and journal_binding.get("model_seal") == receipt["model_seal"]
                          and journal_binding.get("release_manifest_digest")
                          == receipt["release_manifest_digest"]
                          and journal_binding.get("package_digests") == package_digests)
    if not draft_verified:
        blockers.append("TP library DRAFT has no matching verified readback")
    approval = state.get("approval") or {}
    approval_current = approval_matches_release(state)
    if not approval_current:
        blockers.append("current revision has no valid existing approval")
    package_binding = approval.get("tp_package_binding") or {}
    package_bound = bool(
        approval_current
        and package_binding.get("coverage_receipt_sha256")
        == _sha(package_dir / "coverage_receipt.json")
        and package_binding.get("customer_guide") == receipt["customer_guide"]
    )
    if not package_bound:
        blockers.append("existing approval lacks matching payload receipt and guide digest binding")
    return {
        "order_id": order_id, "generation_revision": receipt["generation_revision"],
        "athlete_id": state["athlete_id"], "status": state["status"],
        "model_seal": receipt["model_seal"],
        "release_manifest_digest": receipt["release_manifest_digest"],
        "payload_receipt_sha256": _sha(package_dir / "coverage_receipt.json"),
        "approval": {"current": approval_current, "revision": approval.get("revision"),
                     "model_seal": approval.get("model_seal"),
                     "release_manifest_digest": approval.get("release_manifest_digest"),
                     "package_bound": package_bound},
        "artifacts": {"plan_ir": str(artifacts / "plan_ir.json"),
                      "plan_payload": str(package_dir / "plan_payload.json")
                      if receipt["ready_for_review"] else None,
                      "notes_payload": str(package_dir / "notes_payload.json")
                      if receipt["ready_for_review"] else None,
                      "plan_preview": str(artifacts / "plan_preview.html")
                      if (artifacts / "plan_preview.html").is_file() else None,
                      "guide_html": {"path": str(guide), "sha256": _sha(guide)},
                      "guide_pdf": {"path": str(pdf), "sha256": _sha(pdf)}
                      if pdf.is_file() else None},
        "guide_fact_checks": checks,
        "assumption_provenance": {"plan_ir": plan.get("provenance") or {},
                                  "model_derived_values": model.get("derived_values") or [],
                                  "fueling": (plan.get("fueling") or {}).get("assumptions") or []},
        "quality_blockers": state.get("blocking_issues") or [],
        "w00_manual_dispositions_needed": w00,
        "coverage": receipt["counts"], "tp_ready_for_review": receipt["ready_for_review"],
        "tp_draft": {"verified": draft_verified, "journal": str(draft_journal)
                     if draft_journal else None},
        "spot_checks": _spot_checks(plan), "release_ready": not blockers,
        "release_blockers": blockers,
        "note": "Library DRAFT is not athlete-calendar application or delivery confirmation.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for arg in ("order-id", "state-path", "revision-dir", "package-dir"):
        parser.add_argument("--" + arg, required=True,
                            type=Path if arg != "order-id" else str)
    parser.add_argument("--draft-journal", type=Path)
    args = parser.parse_args(argv)
    try:
        packet = build(args.order_id, args.state_path, args.revision_dir,
                       args.package_dir, draft_journal=args.draft_journal)
    except (PacketError, sealed.SealedPackageError, OSError, ValueError) as exc:
        print(f"build_order_review_packet: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(packet, sort_keys=True, indent=2))
    return 0 if packet["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
