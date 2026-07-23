"""R6 tests for the standalone RUN-LIB compliance gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from dual_sport_selector import Session, WeekPlan, select_week  # noqa: E402
import run_compliance  # noqa: E402


@dataclass(frozen=True)
class CalendarWeek:
    """R5 WeekPlan plus dispatch-owned calendar/template metadata."""

    sessions: dict[str, Session]
    week_start: date
    plan_week: int
    week_type: str = "load"
    template_run_hours: float | None = None


def selected_week(start: str, number: int, **overrides) -> CalendarWeek:
    descriptor = {
        "phase": "base",
        "week_start": start,
        "races": [],
        "long_run_level": 3,
        "quality_level": 3,
    }
    descriptor.update(overrides.pop("descriptor", {}))
    plan: WeekPlan = select_week(descriptor)
    return CalendarWeek(
        sessions=overrides.pop("sessions", dict(plan.sessions)),
        week_start=date.fromisoformat(start),
        plan_week=number,
        template_run_hours=overrides.pop("template_run_hours", None),
        **overrides,
    )


def rules(violations: list[str]) -> set[str]:
    return {violation.split(":", 1)[0].split()[-1] for violation in violations}


def test_compliant_multi_week_plan_passes():
    weeks = [
        selected_week("2026-07-06", 1, descriptor={"long_run_level": 2}),
        selected_week("2026-07-13", 2, descriptor={"long_run_level": 3}),
    ]
    assert run_compliance.validate_run_plan(weeks, []) == []


def test_rc1_race_adjacency_across_week_boundaries_is_rejected():
    race_week = selected_week("2026-07-06", 1, week_type="race", sessions={})
    # An ordinary selector week has intensity on Tuesday and is deliberately
    # ungated.  Sunday 7/12 -> Tuesday 7/14 spans WeekPlan boundaries.
    next_week = selected_week("2026-07-13", 2)
    violations = run_compliance.validate_run_plan(
        [race_week, next_week], [{"date": "2026-07-12", "sport": "bike"}],
    )
    assert rules(violations) == {"R-C1"}
    assert any(violation.startswith("W2 R-C1") for violation in violations)


def test_rc2_requires_a_long_run_in_each_non_race_load_week():
    week = selected_week("2026-07-20", 1, template_run_hours=1.0)
    sessions = dict(week.sessions)
    sessions["Sat"] = Session("Sat", None, None, False, False, "rest")
    week = CalendarWeek(**{**week.__dict__, "sessions": sessions})
    violations = run_compliance.validate_run_plan([week], [])
    assert rules(violations) == {"R-C2"}
    assert any("W1 R-C2" in violation for violation in violations)


def test_rc3_requires_actionable_nutrition_for_every_ninety_minute_run(monkeypatch):
    week = selected_week("2026-07-20", 1, template_run_hours=2.8)
    real_renderer = run_compliance.render_run_description

    def renderer_with_bad_long_run(*args, **kwargs):
        rendered = real_renderer(*args, **kwargs)
        if args[0] == week.sessions["Sat"].archetype_id:
            before, _, after = rendered.partition("NUTRITION:\n")
            nutrition, _, remainder = after.partition("\n\nHYDRATION:")
            return f"{before}NUTRITION:\n-None needed at this duration.\n\nHYDRATION:{remainder}"
        return rendered

    monkeypatch.setattr(run_compliance, "render_run_description", renderer_with_bad_long_run)
    violations = run_compliance.validate_run_plan([week], [])
    assert rules(violations) == {"R-C3"}
    assert any("W1 R-C3" in violation for violation in violations)


def test_rc4_rejects_required_hours_below_the_template_floor():
    week = selected_week("2026-07-20", 1, template_run_hours=2.8)
    sessions = dict(week.sessions)
    sessions["Tue"] = Session("Tue", "run.recovery_easy.shakeout", 1, False, False, None)
    week = CalendarWeek(**{**week.__dict__, "sessions": sessions})
    violations = run_compliance.validate_run_plan([week], [])
    assert rules(violations) == {"R-C4"}
    assert any("W1 R-C4" in violation for violation in violations)


def test_rc5_rejects_intensity_inside_an_optional_run():
    week = selected_week("2026-07-20", 1, template_run_hours=3.1)
    sessions = dict(week.sessions)
    sessions["Wed"] = Session("Wed", "run.hills_powerhike.hike_the_damn_hill", 3, True, False, "OPTIONAL: bad")
    week = CalendarWeek(**{**week.__dict__, "sessions": sessions})
    violations = run_compliance.validate_run_plan([week], [])
    assert rules(violations) == {"R-C5"}
    assert any("W1 R-C5" in violation for violation in violations)


def test_rc6_rejects_a_long_run_level_jump_greater_than_one():
    first = selected_week("2026-07-06", 1, descriptor={"long_run_level": 2}, template_run_hours=2.5)
    second = selected_week("2026-07-13", 2, descriptor={"long_run_level": 4}, template_run_hours=3.0)
    violations = run_compliance.validate_run_plan([first, second], [])
    assert rules(violations) == {"R-C6"}
    assert any("W2 R-C6" in violation for violation in violations)


def test_optional_run_paradox_dropping_or_completing_optional_does_not_break_rc4():
    complete = selected_week("2026-07-20", 1, template_run_hours=2.8)
    dropped_sessions = dict(complete.sessions)
    dropped_sessions["Wed"] = Session("Wed", None, None, False, False, "optional skipped")
    dropped = CalendarWeek(**{**complete.__dict__, "sessions": dropped_sessions})

    assert "R-C4" not in rules(run_compliance.validate_run_plan([dropped], []))
    assert "R-C4" not in rules(run_compliance.validate_run_plan([complete], []))
