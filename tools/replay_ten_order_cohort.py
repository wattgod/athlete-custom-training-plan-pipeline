#!/usr/bin/env python3
"""Offline, order-private replay of ten varied synthetic Motoren custom plans.

This measures generation and sealed TP-package readiness. It makes no provider
requests and does not measure coach review, publication, or confirmation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from datetime import date
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "athletes" / "scripts"
for location in (ROOT, SCRIPTS, ROOT / "webhook"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

FIXED_DAY = "2026-08-06"  # Matches the committed order-acceptance generation clock.
FIXED_CLOCK = "2026-08-06T15:00:00Z"


def _race(name: str, weeks_min: int, weeks_max: int) -> dict:
    from real_races import buildable_races
    candidates = buildable_races("gravel", weeks_min, weeks_max, today=FIXED_DAY)
    matches = [item for item in candidates if item["name"] == name]
    if len(matches) != 1:
        raise RuntimeError(f"committed race missing or ambiguous: {name}")
    return matches[0]


def cohort() -> list[dict]:
    """Fixed synthetic variety; all event facts come from the committed race DB."""
    from synthesize_athlete import synthesize

    short = _race("Fools Gold Gravel Grinder", 5, 7)
    middle = _race("Big Sugar", 10, 12)
    long = _race("Walburg Dirty 30", 17, 22)
    personas = [
        ("short_runway", "time_crunched_parent", short),
        ("long_runway", "veteran_podium_chaser", long),
        ("unknown_ftp_blank", "masters_returner", middle),
        ("hr_rpe", "ambitious_first_timer", middle),
        ("full_gym", "veteran_podium_chaser", middle),
        ("no_strength", "weekend_warrior", middle),
        ("joint_a_races", "veteran_podium_chaser", middle),
        ("repeat_buyer_first", "time_crunched_parent", middle),
        ("repeat_buyer_second", "time_crunched_parent", long),
        ("tight_schedule", "time_crunched_parent", short),
    ]
    cases = []
    for index, (label, persona, race) in enumerate(personas):
        intake = synthesize("motoren-cohort-20260806", index, today=FIXED_DAY,
                            persona_key=persona, race=race)
        intake.pop("_meta", None)
        intake["generation_clock"] = FIXED_CLOCK
        if label == "unknown_ftp_blank":
            intake["ftp"] = ""
        elif label == "hr_rpe":
            intake["ftp"] = ""
            intake["power_or_hr"] = "heart rate/RPE"
            intake["trainer_access"] = "none"
        elif label == "full_gym":
            intake.update(strength_want="yes", strength_equipment="full gym")
        elif label == "no_strength":
            intake.update(strength_want="no", strength_current="none",
                          strength_equipment="minimal")
        elif label == "joint_a_races":
            second = _race("Spirit World 100", 13, 15)
            intake["races"].append({"name": second["name"], "date": second["date"],
                                     "distance": f"{round(float(second['distance_mi']))} miles",
                                     "priority": "A", "goal": "Compete"})
        elif label == "tight_schedule":
            intake.update(hours_per_week="5", off_days=["Monday", "Wednesday", "Friday"],
                          interval_days=["Tuesday", "Thursday"], long_ride_days=["Saturday"])
        if label == "repeat_buyer_second":
            intake["name"] = cases[7]["intake"]["name"]
            intake["email"] = cases[7]["intake"]["email"]
        cases.append({"label": label, "order_id": f"cohort-{index + 1:02d}",
                      "intake": intake})
    return cases


def _peak_kib() -> int:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return int(usage / 1024) if sys.platform == "darwin" else int(usage)


def run_one(case: dict, root: Path, *, inject_seal_edit: bool = False) -> dict:
    """Use the webhook's real generator and revision persistence under a private root."""
    os.environ["DATA_DIR"] = str(root)
    os.environ["GG_PDF_DISABLE"] = "1"  # Local smoke: PDF remains an explicit gap.
    os.environ.pop("RESEND_API_KEY", None)
    os.environ.pop("SMTP_HOST", None)
    import app as webhook_app
    webhook_app.SCRIPTS_DIR = str(SCRIPTS)
    from tools import build_sealed_tp_plan_package as sealed
    from webhook.fulfillment_state import load, verify_release_manifest

    started = time.monotonic()
    order_id = case["order_id"]
    intake = case["intake"]
    report = {"case": case["label"], "order_ref": hashlib.sha256(order_id.encode()).hexdigest()[:12],
              "status": "generation_failed", "artifact_sealed": False,
              "ready_for_review": False, "guide_tp_match": False,
              "blocked_issue_ids": [], "exception": None}
    try:
        generation = webhook_app.run_pipeline(
            order_id, deliver=True, intake_data=intake,
            order_data={"order_id": order_id, "delivery_platform": "manual"})
        source_name = generation.get("artifact_dir")
        source = Path(source_name) if source_name else None
        if not generation.get("success") or source is None or not source.is_dir():
            report["exception"] = "generation_failed_or_source_missing"
            return report
        persisted = webhook_app.persist_deliverables(
            order_id, source_dir=source, delivery_platform="manual")
        state_path = root / "deliveries" / "orders" / order_id / "fulfillment_status.json"
        revision_dir = Path(persisted["revision_dir"])
        state = load(state_path)
        verify_release_manifest(state, revision_dir)
        report["artifact_sealed"] = True
        report["status"] = state["status"]
        report["blocked_issue_ids"] = sorted(issue["id"] for issue in state["blocking_issues"])
        report["generation_revision"] = state["generation_revision"]
        if inject_seal_edit:
            with (revision_dir / "artifacts" / "training_guide.html").open("a") as handle:
                handle.write("\nsynthetic tamper injection\n")
        package_root = root / "tp-packages" / order_id
        try:
            receipt = sealed.build(order_id, state_path, revision_dir, package_root)
        except Exception as exc:
            report["exception"] = type(exc).__name__
            if not inject_seal_edit:
                return report
            report["seal_edit_rejected"] = True
            # A corrupted sealed revision is never reused. Rebuild the same
            # synthetic order through production generation, yielding r2.
            repaired = webhook_app.run_pipeline(
                order_id, deliver=True, intake_data=intake,
                order_data={"order_id": order_id, "delivery_platform": "manual"})
            repaired_source = repaired.get("artifact_dir")
            if not repaired.get("success") or not repaired_source:
                report["repair_error"] = "regeneration_failed"
                return report
            new_persisted = webhook_app.persist_deliverables(
                order_id, source_dir=Path(repaired_source), delivery_platform="manual")
            revision_dir = Path(new_persisted["revision_dir"])
            state = load(state_path)
            verify_release_manifest(state, revision_dir)
            receipt = sealed.build(order_id, state_path, revision_dir, package_root)
            report["generation_revision"] = state["generation_revision"]
            report["repair_new_revision"] = report["generation_revision"] > 1
            report["exception"] = None
        report["ready_for_review"] = receipt["ready_for_review"]
        report["counts"] = receipt["counts"]
        report["unaccounted_items"] = (
            receipt["counts"]["source_sessions"] != receipt["counts"]["included_sessions"]
            + receipt["counts"]["excluded_sessions"] or
            receipt["counts"]["source_notes"] != receipt["counts"]["included_notes"]
            + receipt["counts"]["excluded_notes"])
        tp = json.loads((revision_dir / "artifacts" / "tp_manifest.json").read_text())
        guide = unescape((revision_dir / "artifacts" / "training_guide.html").read_text())
        race = tp.get("race") or {}
        report["guide_tp_match"] = (
            bool(race.get("name")) and race["name"].casefold() in guide.casefold()
            and bool(race.get("date")) and race["date"] in guide)
        report["source_session_count"] = len(tp.get("sessions") or [])
        return report
    except Exception as exc:
        report["exception"] = type(exc).__name__
        return report
    finally:
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        report["peak_generator_child_rss_kib"] = _peak_kib()


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_all(root: Path, *, limit: int = 10, seal_edit_case: int | None = None) -> dict:
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("rehearsal output root must be empty to prevent stale evidence")
    root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    rows = []
    for index, case in enumerate(cohort()[:limit]):
        replay_wait_seconds = round(time.monotonic() - started, 3)
        case_file = root / f"case-{index + 1:02d}.json"
        _write(case_file, case)
        command = [sys.executable, str(Path(__file__).resolve()), "--run-one", str(case_file),
                   "--out-root", str(root)]
        if seal_edit_case == index + 1:
            command.append("--inject-seal-edit")
        proc = subprocess.run(command, capture_output=True, text=True, timeout=900,
                              env={**os.environ, "GG_PDF_DISABLE": "1"})
        try:
            row = json.loads(proc.stdout)
        except json.JSONDecodeError:
            row = {"case": case["label"], "status": "harness_failed",
                   "exception": "child_no_json_result", "ready_for_review": False}
        row["child_exit_code"] = proc.returncode
        row["sequential_replay_wait_seconds"] = replay_wait_seconds
        rows.append(row)
        summary = {
            "sealed": sum(item.get("artifact_sealed") is True for item in rows),
            "ready_for_review": sum(item.get("ready_for_review") is True for item in rows),
            "blocked_review": sum(item.get("status") == "BLOCKED_REVIEW" for item in rows),
            "guide_tp_match": sum(item.get("guide_tp_match") is True for item in rows),
            "unaccounted_items": sum(item.get("unaccounted_items") is True for item in rows),
            "exceptions": sum(item.get("exception") is not None for item in rows),
            "max_generator_child_rss_kib": max(
                (item.get("peak_generator_child_rss_kib") or 0 for item in rows), default=0),
        }
        _write(root / "report.json", {
            "artifact_type": "motoren_ten_order_offline_replay/v1",
            "scope": "offline_generator_seal_tp_package_only",
            "fixed_generation_clock": FIXED_CLOCK,
            "cases_run": len(rows), "cases_planned": 10,
            "elapsed_wall_seconds": round(time.monotonic() - started, 3),
            "summary": summary,
            "results": rows,
            "not_measured": ["live_TP_readback", "coach_minutes", "athlete_calendar",
                             "confirmed_delivery", "three_day_soak", "PDF_disabled"],
        })
    return json.loads((root / "report.json").read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--run-one", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--inject-seal-edit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--seal-edit-case", type=int)
    args = parser.parse_args(argv)
    if args.run_one:
        row = run_one(json.loads(args.run_one.read_text()), args.out_root,
                      inject_seal_edit=args.inject_seal_edit)
        print(json.dumps(row, sort_keys=True))
        return 0 if row["artifact_sealed"] else 1
    if not 1 <= args.limit <= 10 or (args.seal_edit_case and
                                      not 1 <= args.seal_edit_case <= args.limit):
        parser.error("limit must be 1-10 and seal-edit-case must be inside the limit")
    result = run_all(args.out_root, limit=args.limit, seal_edit_case=args.seal_edit_case)
    print(json.dumps({key: value for key, value in result.items() if key != "results"},
                     sort_keys=True))
    return 0 if all(row.get("artifact_sealed") for row in result["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
