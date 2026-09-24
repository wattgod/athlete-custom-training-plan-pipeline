#!/usr/bin/env python3
"""Build an offline TP review package from one sealed paid-order revision.

No provider or fulfillment-state writes occur. Output is disposable scratch data;
the canonical order state and its release manifest remain the authority.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "webhook") not in sys.path:
    sys.path.insert(0, str(ROOT / "webhook"))

from tools import build_tp_plan_payload as payload
from webhook.fulfillment_state import FulfillmentStateError, load, verify_release_manifest


class SealedPackageError(ValueError):
    """The requested order/revision cannot produce a trustworthy package."""


OUTPUT_NAMES = ("plan_payload.json", "notes_payload.json", "exclusions.json",
                "lint.json", "coverage_receipt.json")


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SealedPackageError(f"invalid or missing sealed source: {path.name}") from exc
    if not isinstance(value, dict):
        raise SealedPackageError(f"sealed source must be an object: {path.name}")
    return value


def _inventory_keys(items: list, name: str) -> list[tuple[str, str]]:
    keys = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            raise SealedPackageError(f"malformed {name} session inventory")
        value = item.get("date")
        if not isinstance(value, str):
            raise SealedPackageError(f"malformed {name} session date")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise SealedPackageError(f"malformed {name} session date") from exc
        keys.append((value, item["title"]))
    return keys


def _day_one(plan_ir: dict, tp_manifest: dict) -> str:
    weeks = plan_ir.get("weeks")
    first = [week for week in weeks if isinstance(week, dict) and
             week.get("number") == 1] if isinstance(weeks, list) else []
    if len(first) != 1 or not isinstance(first[0].get("sessions"), list):
        raise SealedPackageError("ambiguous plan day one: expected exactly one PlanIR Week 1")
    dates = [item.get("date") for item in first[0]["sessions"]]
    if not dates or any(not isinstance(value, str) for value in dates):
        raise SealedPackageError("ambiguous plan day one: Week 1 has no dated sessions")
    try:
        start = min(date.fromisoformat(value) for value in dates)
    except ValueError as exc:
        raise SealedPackageError("ambiguous plan day one: malformed Week 1 date") from exc
    if start.weekday() != 0 or any(date.fromisoformat(value) >= start + timedelta(days=7)
                                   for value in dates):
        raise SealedPackageError("ambiguous plan day one: Week 1 does not start on Monday")
    tp_dates = [item.get("date") for item in tp_manifest.get("sessions", [])]
    if start.isoformat() not in tp_dates:
        raise SealedPackageError("ambiguous plan day one: TP manifest has no Day 1 session")
    return start.isoformat()


def _coverage(source: list, entries: list, excluded: list, redated: list,
              day_one: str, *, kind: str) -> list[dict]:
    """Bind each source occurrence to one disposition, including duplicate titles."""
    result = []
    in_window = [i for i, item in enumerate(source) if item.get("date") >= day_one]
    if kind == "session":
        in_window.sort(key=lambda i: (source[i].get("date"),
                                      source[i].get("order_on_day") or 0))
    indices = {source_index: output_index for output_index, source_index in
               enumerate(in_window)}
    excluded_count = 0
    redated_count = 0
    note_output_index = 0
    for index, item in enumerate(source):
        disposition = "included"
        action = None
        output_index = indices.get(index)
        if item.get("date") < day_one:
            if kind == "note" and item.get("title") == payload.COMMENT_PROTOCOL_TITLE:
                disposition = "redated"
                action = "comment_protocol_to_plan_day_one"
                output_index = note_output_index
                redated_count += 1
            else:
                disposition = "excluded"
                action = "manual_W00_placement"
                excluded_count += 1
        if kind == "note" and disposition != "excluded":
            output_index = note_output_index
            note_output_index += 1
        result.append({"source_index": index, "date": item.get("date"),
                       "title": item.get("title"), "disposition": disposition,
                       "output_index": output_index, "action": action})
    included_count = sum(item["output_index"] is not None for item in result)
    if (included_count != len(entries) or excluded_count != len(excluded)
            or redated_count != len(redated)):
        raise SealedPackageError(f"{kind} coverage does not reconcile")
    return result


def build(order_id: str, state_path: Path, revision_dir: Path, out_dir: Path) -> dict:
    state_path, revision_dir, out_dir = (Path(p).resolve() for p in
                                         (state_path, revision_dir, out_dir))
    order_root = state_path.parent
    if order_root in out_dir.parents or out_dir == order_root:
        raise SealedPackageError("output directory must be outside the order source tree")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_NAMES:
        (out_dir / name).unlink(missing_ok=True)

    if state_path.name != "fulfillment_status.json" or order_root.name != order_id:
        raise SealedPackageError("canonical order-state path and order ID do not match")
    state = load(state_path)
    revision = state["generation_revision"]
    if state["order_id"] != order_id:
        raise SealedPackageError("order ID does not match canonical state")
    if revision_dir != order_root / "revisions" / f"r{revision}":
        raise SealedPackageError("stale or foreign revision directory")
    if Path(state.get("release_manifest") or "").resolve() != revision_dir / "release_manifest.json":
        raise SealedPackageError("release manifest is not bound to requested revision")
    manifest = verify_release_manifest(state, revision_dir)

    artifact_dir = revision_dir / "artifacts"
    sealed_records = {record["path"]: record for record in manifest["artifacts"]}
    for name in ("tp_manifest.json", "fulfillment_manifest.json", "plan_ir.json",
                 "canonical_training_model.json", "training_guide.html"):
        if f"artifacts/{name}" not in sealed_records or not (artifact_dir / name).is_file():
            raise SealedPackageError(f"missing sealed source artifact: {name}")
    html_guide_path = "artifacts/training_guide.html"
    pdf_guide_path = "artifacts/training_guide.pdf"
    if (artifact_dir / "training_guide.pdf").is_file() and pdf_guide_path not in sealed_records:
        raise SealedPackageError("customer PDF guide is not in the sealed release")
    guide_artifacts = {html_guide_path: sealed_records[html_guide_path]["sha256"]}
    if pdf_guide_path in sealed_records:
        guide_artifacts[pdf_guide_path] = sealed_records[pdf_guide_path]["sha256"]
    customer_guide_path = pdf_guide_path if pdf_guide_path in guide_artifacts else html_guide_path
    tp = _json(artifact_dir / "tp_manifest.json")
    fulfillment = _json(artifact_dir / "fulfillment_manifest.json")
    plan_ir = _json(artifact_dir / "plan_ir.json")
    if fulfillment.get("athlete_id") != state["athlete_id"] or (
            plan_ir.get("athlete") or {}).get("id") != state["athlete_id"]:
        raise SealedPackageError("sealed source athlete identity mismatch")
    sessions = tp.get("sessions")
    notes = fulfillment.get("native_notes")
    if not isinstance(sessions, list) or not isinstance(notes, list):
        raise SealedPackageError("missing source sessions or native notes")
    if any(not isinstance(item, dict) for item in sessions + notes):
        raise SealedPackageError("malformed source session or note")
    if not isinstance(plan_ir.get("weeks"), list) or any(
            not isinstance(week, dict) or not isinstance(week.get("sessions"), list)
            for week in plan_ir["weeks"]):
        raise SealedPackageError("malformed PlanIR week inventory")
    all_plan_sessions = [item for week in plan_ir["weeks"] for item in week["sessions"]]
    plan_keys = _inventory_keys(all_plan_sessions, "PlanIR")
    tp_keys = _inventory_keys(sessions, "TP")
    day_one = _day_one(plan_ir, tp)
    source_workouts = fulfillment.get("workouts")
    if not isinstance(source_workouts, list):
        raise SealedPackageError("malformed fulfillment session inventory")
    if Counter(_inventory_keys(source_workouts, "fulfillment")) != Counter(tp_keys):
        raise SealedPackageError("TP and fulfillment session inventories disagree")
    if Counter(key for key in plan_keys if key[0] >= day_one) != Counter(
            key for key in tp_keys if key[0] >= day_one):
        raise SealedPackageError("PlanIR and TP session inventories disagree")
    workouts, excluded_sessions = payload.build_plan_payload(sessions, day_one)
    if not workouts:
        raise SealedPackageError("no in-window sessions")
    note_entries, excluded_notes, redated_notes = payload.build_notes_payload(notes, day_one)
    lint = payload.run_lint(workouts, (tp.get("race") or {}).get("date"))
    lint["plan_day_one"] = day_one
    blocked = bool(state.get("blocking_issues"))
    ready = (state.get("status") in {"GENERATED", "APPROVED"}
             and not blocked and not lint["unresolved_fails"])
    receipt = {
        "order_id": order_id, "generation_revision": revision,
        "athlete_id": state["athlete_id"], "model_seal": state["model_seal"],
        "release_manifest_digest": state["release_manifest_digest"],
        "guide_sha256": guide_artifacts[customer_guide_path],
        "guide_artifacts": guide_artifacts,
        "customer_guide": {"path": customer_guide_path,
                           "sha256": guide_artifacts[customer_guide_path]},
        "plan_day_one": day_one, "ready_for_review": ready,
        "blocking_issue_ids": [issue["id"] for issue in state.get("blocking_issues", [])],
        "sessions": _coverage(sessions, workouts, excluded_sessions, [], day_one,
                              kind="session"),
        "notes": _coverage(notes, note_entries, excluded_notes, redated_notes, day_one,
                           kind="note"),
        "counts": {"source_sessions": len(sessions), "included_sessions": len(workouts),
                   "excluded_sessions": len(excluded_sessions), "source_notes": len(notes),
                   "included_notes": len(note_entries), "excluded_notes": len(excluded_notes),
                   "redated_notes": len(redated_notes)},
    }
    latest = load(state_path)
    if (latest["generation_revision"] != revision or latest.get("model_seal") != state["model_seal"]
            or latest.get("release_manifest_digest") != state["release_manifest_digest"]):
        raise SealedPackageError("order revision changed during package build")
    verify_release_manifest(latest, revision_dir)
    try:
        payload._write_json_atomic(out_dir / "exclusions.json", {
            "plan_day_one": day_one, "excluded_sessions": excluded_sessions,
            "excluded_notes": excluded_notes, "redated_notes": redated_notes})
        payload._write_json_atomic(out_dir / "lint.json", lint)
        if ready:
            payload._write_json_atomic(out_dir / "plan_payload.json", workouts)
            payload._write_json_atomic(out_dir / "notes_payload.json", note_entries)
        payload._write_json_atomic(out_dir / "coverage_receipt.json", receipt)
    except OSError:
        for name in OUTPUT_NAMES:
            (out_dir / name).unlink(missing_ok=True)
        raise
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--state-path", required=True, type=Path)
    parser.add_argument("--revision-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = build(args.order_id, args.state_path, args.revision_dir, args.out_dir)
    except (SealedPackageError, FulfillmentStateError, payload.PlanPayloadError) as exc:
        print(f"build_sealed_tp_plan_package: {exc}", file=sys.stderr)
        return 2
    return 0 if receipt["ready_for_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
