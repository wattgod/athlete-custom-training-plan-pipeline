"""A3.0 E1 parity fixtures: the only nine pre-existing blockers."""

from __future__ import annotations

import copy
import hashlib
import itertools
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from block_compliance import INTENSITY_TYPES, VO2MAX_TYPES, validate_plan
from earned_selection_rules import (PRE_EXISTING, build_legacy_projection,
                                    execute_rules, legacy_verdicts)
from earned_selection import VERSION_VECTOR, canonical_digest
from workout_quality_report import build_report
sys.path.insert(0, str(REPO_ROOT / "webhook"))
from fulfillment_state import write_generation


def _day(day, name="Endurance", role="filler", duration=60, sessions=None):
    return {"day": day, "name": name, "role": role, "duration": duration,
            "workout": {"duration": duration}, "sessions": sessions or []}


def _week(number=1, *, phase="base", week_type="load", tss=300,
          duration=500, days=None):
    return {"plan_week": number, "phase": phase, "week_type": week_type,
            "total_tss": tss, "total_duration": duration,
            "days": days or [
                _day("Mon", "VO2max 30/30", "intensity"),
                _day("Tue"), _day("Wed", "Threshold Steady", "intensity"),
                _day("Sat", "Endurance", "long_ride", 120),
            ]}


def _assert_parity(plan, *, target_hours=9.0, off_days=(), max_intensity=3):
    projection = build_legacy_projection(
        plan, target_hours=target_hours, off_days=off_days,
        max_intensity=max_intensity)
    adapter = legacy_verdicts(projection)
    production = validate_plan(
        plan, target_hours=target_hours, off_days=list(off_days),
        max_intensity=max_intensity)
    assert set(adapter) == PRE_EXISTING
    assert adapter == {rule_id: production["rules"][rule_id]["passed"]
                       for rule_id in sorted(PRE_EXISTING)}
    assert all(projection == copy.deepcopy(projection) for _ in range(1))


def test_named_a30_equivalence_goldens():
    # R01 resets at the week boundary.
    cross_week = {"weeks": [
        _week(1, days=[_day("Sun", "Threshold Steady", "intensity")]),
        _week(2, days=[_day("Mon", "VO2max 30/30", "intensity")]),
    ]}
    _assert_parity(cross_week)
    assert legacy_verdicts(build_legacy_projection(
        cross_week, target_hours=9, off_days=[], max_intensity=3))["R01"] is True

    # R02 race-week type is excluded from applicability but not the separate
    # raw-name stimulus scan (the asymmetric production-true counterexample).
    r02c = {"weeks": [_week(i, days=[_day("Sat", role="long_ride", duration=90)])
                      for i in range(1, 5)] + [
        _week(5, week_type="race", days=[
            _day("Tue", "VO2max 30/30", "intensity"),
            _day("Sat", role="long_ride", duration=90)])]}
    _assert_parity(r02c)
    assert legacy_verdicts(build_legacy_projection(
        r02c, target_hours=9, off_days=[], max_intensity=3))["R02"] is True

    # R03 retains the E1 30% floor: 100/250 = 40% is production PASS.
    r03 = {"weeks": [_week(1, tss=250),
                     _week(2, week_type="recovery", tss=100,
                           days=[_day("Sat", role="off")])]}
    _assert_parity(r03)
    assert legacy_verdicts(build_legacy_projection(
        r03, target_hours=9, off_days=[], max_intensity=3))["R03"] is True

    for hours, duration, expected in [
            (6.5, 59, False), (6.5, 60, True),
            (7.0, 89, False), (7.0, 90, True)]:
        plan = {"weeks": [_week(days=[
            _day("Tue", "VO2max 30/30", "intensity"),
            _day("Thu", "Threshold Steady", "intensity"),
            _day("Sat", role="long_ride", duration=duration)])]}
        _assert_parity(plan, target_hours=hours)
        assert legacy_verdicts(build_legacy_projection(
            plan, target_hours=hours, off_days=[], max_intensity=3))["R06"] is expected

    race_off_day = {"weeks": [_week(days=[_day("Sun", "Race", "race", 120)])]}
    _assert_parity(race_off_day, off_days=["Sun"])
    assert legacy_verdicts(build_legacy_projection(
        race_off_day, target_hours=9, off_days=["Sun"], max_intensity=3))["R20"] is True


def test_generated_a30_branch_boundary_corpus_is_exactly_equivalent():
    cases = []
    week_types = ["load", "testing", "recovery", "taper", "race", "medium", "uber_load"]
    phases = ["base", "racing", "taper"]
    hard_tokens = [None, "", "easy", "hard", "ThReShOlD", "vo2",
                   "anaerobic", "race"]
    names = [None, "unknown", "Openers", next(iter(INTENSITY_TYPES)),
             *sorted(VO2MAX_TYPES)]
    roles = [None, "filler", "intensity"]
    for week_type, phase, token in itertools.product(week_types, phases, hard_tokens):
        sessions = [] if token is None else [{"intensity": token}]
        cases.append(({"weeks": [_week(
            phase=phase, week_type=week_type,
            days=[_day("Tue", "Endurance", "filler", sessions=sessions),
                  _day("Sat", role="long_ride", duration=90)])]}, 9, [], 3))
    for name, role in itertools.product(names, roles):
        cases.append(({"weeks": [_week(days=[
            _day("Tue", name, role), _day("Wed"),
            _day("Thu", "Threshold Steady", "intensity"),
            _day("Sat", role="long_ride", duration=90)])]}, 9, [], 3))
    for race_position in (None, 0, 1, 2):
        days = [_day("Tue", "VO2max 30/30", "intensity"),
                _day("Thu", "Threshold Steady", "intensity"),
                _day("Sat", role="long_ride", duration=90)]
        if race_position is not None:
            days.insert(race_position, _day("Race", "Race", "race", 120))
        cases.append(({"weeks": [_week(days=days)]}, 9, [], 3))
    for hours in (0, 5.999, 6, 6.999, 7):
        for long_duration in (0, 59, 60, 89, 90):
            for weekly_duration in (0, hours * .65 * 60,
                                    hours * 1.1 * 60, hours * 1.1 * 60 + .01):
                cases.append(({"weeks": [_week(
                    duration=weekly_duration, days=[
                        _day("Tue", "VO2max 30/30", "intensity"),
                        _day("Thu", "Threshold Steady", "intensity"),
                        _day("Sat", role="long_ride", duration=long_duration)])]},
                              hours, [], 3))
    for violations, off_role, max_intensity in itertools.product(
            (None, [], ["series"]), ("off", "race", "filler"), (1, 2, 3)):
        plan = {"weeks": [_week(days=[
            _day("Mon", "VO2max 30/30", "intensity"),
            _day("Wed", "Threshold Steady", "intensity"),
            _day("Fri", "Endurance", off_role),
            _day("Sat", role="long_ride", duration=90)])]}
        if violations is not None:
            plan["all_violations"] = violations
        cases.append((plan, 9, ["Fri"], max_intensity))

    for plan, hours, off_days, maximum in cases:
        _assert_parity(plan, target_hours=hours, off_days=off_days,
                       max_intensity=maximum)
    assert len(cases) >= 300


def test_all_nine_report_blockers_are_the_exact_fulfillment_authority(tmp_path):
    bad_days = [
        _day("Mon", "Threshold Steady", "intensity", sessions=[{"intensity": "hard"}]),
        _day("Tue", "Threshold Steady", "intensity", sessions=[{"intensity": "hard"}]),
        _day("Fri", "Endurance", "filler", 60),
    ]
    plan = {"all_violations": ["series"], "weeks": [
        _week(1, tss=300, duration=1200, days=bad_days),
        _week(2, tss=300, duration=1200, days=bad_days),
        _week(3, week_type="recovery", tss=250, duration=1200, days=bad_days),
        _week(4, tss=300, duration=1200, days=bad_days),
        _week(5, tss=300, duration=1200, days=bad_days),
    ]}
    projection = build_legacy_projection(
        plan, target_hours=1, off_days=["Fri"], max_intensity=1)
    assert {rule for rule, passed in legacy_verdicts(projection).items() if not passed} == PRE_EXISTING
    manifest = {"schema_version": "certification_manifest/v1",
                "version_vector": dict(VERSION_VECTOR),
                "promotion_artifacts": [], "rows": []}
    pin = {"snapshot_path": "certification_manifest.json",
           "snapshot_digest": canonical_digest(manifest),
           "manifest_version": "certification_manifest/v1",
           "version_vector": dict(VERSION_VECTOR), "promotion_digests": []}
    candidate = {"generation_revision": 1, "generated_at": "2026-08-13T00:00:00Z",
                 "manifest_pin": pin, "legacy_compliance_projection": projection,
                 "sessions": [], "weeks": [], "guide_inputs": [],
                 "config_digests": {
                     "rollout": hashlib.sha256(
                         (Path(__file__).resolve().parents[1] / "config" /
                          "earned_selection_rollout.yaml").read_bytes()).hexdigest()
                 }}
    report, findings, blockers = build_report(
        candidate, "0" * 64, manifest, b"<html></html>")
    routed = [row for row in report["gate_summary"]["rubric"]
              if row["routed_to_blocking_issues"]]
    assert {row["rule_id"] for row in routed} == PRE_EXISTING
    state = write_generation(
        tmp_path / "state.json", "athlete-rules", blockers,
        order_id="order-rules", quality_findings=findings)
    by_id = {item["id"]: item for item in state["blocking_issues"]}
    assert len(by_id) == len(routed) == 9
    for row in routed:
        issue = by_id[row["output_code"]]
        assert issue["source"] == "earned_selection_rules"
        assert issue["review_value"]["rule_id"] == row["rule_id"]
        assert issue["review_value"]["result"] == row["result"] == "FAIL"
        assert issue["review_value"]["subject_ids"] == row["subject_ids"]


def test_r07_and_r25_are_bound_to_each_paid_weeks_monday_note():
    projection = build_legacy_projection(
        {"weeks": []}, target_hours=0, off_days=[], max_intensity=0)
    candidate = {"legacy_compliance_projection": projection, "sessions": [],
                 "weeks": [{"week": 1, "is_paid": True,
                             "block_note_template_id": "recovery"},
                            {"week": 2, "is_paid": True,
                             "block_note_template_id": "load"}]}
    present = """
      <div data-plan-week="1" data-weekday="monday"
           data-block-note-template="recovery">Don't be afraid to shorten workouts</div>
      <div data-plan-week="2" data-weekday="monday"
           data-block-note-template="load">Prioritize sleep (8+ hours)</div>
    """
    rows = {row["rule_id"]: row for row in execute_rules(
        candidate, guide_html=present, stage="POST_GUIDE")}
    assert rows["R07"]["result"] == "PASS"
    assert rows["R25"]["result"] == "FAIL"
    assert rows["R25"]["subject_ids"] == ["2"]

    both_marked = present.replace(
        "Prioritize sleep (8+ hours)",
        "If anything feels wrong (sharp pain, illness), STOP immediately")
    rows = {row["rule_id"]: row for row in execute_rules(
        candidate, guide_html=both_marked, stage="POST_GUIDE")}
    assert rows["R07"]["result"] == rows["R25"]["result"] == "PASS"

    duplicate = both_marked + (
        '<div data-plan-week="1" data-weekday="monday" '
        'data-block-note-template="recovery">duplicate</div>')
    rows = {row["rule_id"]: row for row in execute_rules(
        candidate, guide_html=duplicate, stage="POST_GUIDE")}
    assert rows["R07"]["result"] == "FAIL"

    unavailable = {row["rule_id"]: row for row in execute_rules(
        candidate, guide_html=None, stage="POST_GUIDE")}
    assert unavailable["R07"]["result"] == "UNAVAILABLE"
    assert unavailable["R25"]["result"] == "UNAVAILABLE"
