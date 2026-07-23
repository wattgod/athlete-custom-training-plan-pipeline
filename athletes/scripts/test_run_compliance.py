"""R6 tests for the standalone RUN-LIB compliance gate."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from dual_sport_selector import Session, WeekPlan, select_week  # noqa: E402
import run_compliance  # noqa: E402


def selected_week(start: str, **overrides) -> WeekPlan:
    descriptor = {
        "phase": "base",
        "week_start": start,
        "races": [],
        "long_run_level": 3,
        "quality_level": 3,
    }
    descriptor.update(overrides.pop("descriptor", {}))
    plan = select_week(descriptor)
    changes = {key: value for key, value in overrides.items() if key != "descriptor"}
    if "sessions" in changes:
        changes["sessions"] = dict(changes["sessions"])
    return replace(plan, **changes)


def rules(violations: list[str]) -> set[str]:
    return {violation.split(":", 1)[0].split()[-1] for violation in violations}


def test_compliant_multi_week_plan_passes():
    weeks = [
        selected_week("2026-07-06", descriptor={"long_run_level": 2}),
        selected_week("2026-07-13", descriptor={"long_run_level": 3}),
    ]
    assert run_compliance.validate_run_plan(weeks) == []


def test_rc1_race_adjacency_across_week_boundaries_is_rejected():
    race_week = selected_week("2026-07-06", descriptor={"races": [{"date": "2026-07-12", "priority": "B", "sport": "bike"}]})
    # An ordinary selector week has intensity on Tuesday and is deliberately
    # ungated.  Sunday 7/12 -> Tuesday 7/14 spans WeekPlan boundaries.
    next_week = selected_week("2026-07-13")
    violations = run_compliance.validate_run_plan([race_week, next_week])
    assert rules(violations) == {"R-C1"}
    assert any(violation.startswith("W2 R-C1") for violation in violations)


def test_rc2_requires_a_long_run_in_each_non_race_load_week():
    week = selected_week("2026-07-20", template_required_hours=1.0)
    sessions = dict(week.sessions)
    sessions["Sat"] = Session("Sat", None, None, False, False, "rest")
    week = replace(week, sessions=sessions)
    violations = run_compliance.validate_run_plan([week])
    assert rules(violations) == {"R-C2"}
    assert any("W1 R-C2" in violation for violation in violations)


def test_rc3_requires_actionable_nutrition_for_every_ninety_minute_run(monkeypatch):
    week = selected_week("2026-07-20", template_required_hours=2.8)
    real_renderer = run_compliance.render_run_description

    def renderer_with_bad_long_run(*args, **kwargs):
        rendered = real_renderer(*args, **kwargs)
        if args[0] == week.sessions["Sat"].archetype_id:
            before, _, after = rendered.partition("NUTRITION:\n")
            _, _, remainder = after.partition("\n\nHYDRATION:")
            return f"{before}NUTRITION:\n\nHYDRATION:{remainder}"
        return rendered

    monkeypatch.setattr(run_compliance, "render_run_description", renderer_with_bad_long_run)
    violations = run_compliance.validate_run_plan([week])
    assert rules(violations) == {"R-C3"}
    assert any("W1 R-C3" in violation for violation in violations)


def test_rc4_rejects_required_hours_below_the_template_floor():
    week = selected_week("2026-07-20", template_required_hours=2.8)
    sessions = dict(week.sessions)
    sessions["Tue"] = Session("Tue", "run.recovery_easy.shakeout", 1, False, False, None)
    week = replace(week, sessions=sessions)
    violations = run_compliance.validate_run_plan([week])
    assert rules(violations) == {"R-C4"}
    assert any("W1 R-C4" in violation for violation in violations)


def test_rc5_rejects_intensity_inside_an_optional_run():
    week = selected_week("2026-07-20", template_required_hours=3.1)
    sessions = dict(week.sessions)
    sessions["Wed"] = Session("Wed", "run.hills_powerhike.hike_the_damn_hill", 3, True, False, "OPTIONAL: bad")
    week = replace(week, sessions=sessions)
    violations = run_compliance.validate_run_plan([week])
    assert rules(violations) == {"R-C5"}
    assert any("W1 R-C5" in violation for violation in violations)


def test_rc6_rejects_a_long_run_level_jump_greater_than_one():
    first = selected_week("2026-07-06", descriptor={"long_run_level": 2})
    second = selected_week("2026-07-13", descriptor={"long_run_level": 4})
    second_sessions = dict(second.sessions)
    second_sessions["Sat"] = replace(second_sessions["Sat"], level="4")
    first_sessions = dict(first.sessions)
    first_sessions["Sat"] = replace(first_sessions["Sat"], level="2")
    violations = run_compliance.validate_run_plan([replace(first, sessions=first_sessions), replace(second, sessions=second_sessions)])
    assert rules(violations) == {"R-C6"}
    assert any("W2 R-C6" in violation for violation in violations)


def test_optional_run_paradox_dropping_or_completing_optional_does_not_break_rc4():
    complete = selected_week("2026-07-20", template_required_hours=2.8)
    dropped_sessions = dict(complete.sessions)
    dropped_sessions["Wed"] = Session("Wed", None, None, False, False, "optional skipped")
    dropped = replace(complete, sessions=dropped_sessions)

    assert "R-C4" not in rules(run_compliance.validate_run_plan([dropped]))
    assert "R-C4" not in rules(run_compliance.validate_run_plan([complete]))


def test_rc7_rejects_a_long_run_in_a_weekend_race_week():
    week = selected_week("2026-07-20", descriptor={"races": [{"date": "2026-07-25", "priority": "B", "sport": "bike"}]})
    sessions = dict(week.sessions)
    sessions["Sat"] = Session("Sat", "run.long_run.time_on_feet", 3, False, False, None)
    violations = run_compliance.validate_run_plan([replace(week, sessions=sessions)])
    assert "R-C7" in rules(violations)
