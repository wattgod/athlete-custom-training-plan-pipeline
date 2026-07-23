"""Contract tests for the sanctioned RUN-LIB dual-sport dispatch gate."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from dual_sport_dispatch import RunComplianceError, plan_dual_sport_block  # noqa: E402
from dual_sport_selector import Session, select_week  # noqa: E402


def descriptor(start: date, phase: str, races=None):
    return {
        "phase": phase,
        "week_start": start.isoformat(),
        "races": [] if races is None else races,
        "long_run_level": 3,
        "quality_level": 3,
    }


def race_for(start: date, placement: str):
    if placement == "none":
        return []
    offsets = {"sat": 5, "sun": 6, "wed": 2}
    if placement == "sat_sun":
        return [
            {"date": (start + timedelta(days=5)).isoformat(), "priority": "B", "sport": "bike"},
            {"date": (start + timedelta(days=6)).isoformat(), "priority": "A", "sport": "run"},
        ]
    priority, sport = {"sat": ("B", "bike"), "sun": ("A", "bike"), "wed": ("C", "run")}[placement]
    return [{"date": (start + timedelta(days=offsets[placement])).isoformat(), "priority": priority, "sport": sport}]


@pytest.mark.parametrize("phase", ["base", "build", "peak", "race", "taper"])
@pytest.mark.parametrize("placement", ["none", "sat", "sun", "wed", "sat_sun"])
def test_selector_output_always_passes_dispatch_gate(phase, placement):
    start = date(2026, 7, 6)
    descriptors = [
        descriptor(start, phase, race_for(start, placement)),
        descriptor(start + timedelta(days=7), phase),
        descriptor(start + timedelta(days=14), phase),
    ]
    assert len(plan_dual_sport_block(descriptors)) == 3


def test_dispatch_threads_long_run_progression_without_caller_state():
    start = date(2026, 7, 6)
    plans = plan_dual_sport_block([
        descriptor(start, "base"),
        {**descriptor(start + timedelta(days=7), "base"), "long_run_level": 6},
    ])
    assert plans[1].sessions["Sat"].level == plans[0].sessions["Sat"].level + 1


def test_dispatch_raises_all_gate_violations(monkeypatch):
    start = date(2026, 7, 6)
    original = select_week

    def invalid_week(*args, **kwargs):
        plan = original(*args, **kwargs)
        sessions = dict(plan.sessions)
        sessions["Wed"] = Session("Wed", "run.hills_powerhike.hike_the_damn_hill", 3, True, False, "bad optional")
        return plan.__class__(sessions, plan.week_start, plan.week_type, plan.template_required_hours, plan.races)

    monkeypatch.setattr("dual_sport_dispatch.select_week", invalid_week)
    with pytest.raises(RunComplianceError, match="R-C5"):
        plan_dual_sport_block([descriptor(start, "base")])
