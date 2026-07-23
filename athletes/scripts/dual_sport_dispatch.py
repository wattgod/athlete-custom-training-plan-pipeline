#!/usr/bin/env python3
"""Sanctioned RUN-LIB coached-athlete entrypoint.

``plan_dual_sport_block`` is the only sanctioned entrypoint for selecting
RUN-LIB weeks: it owns prior-week state and hard-fails the completed block at
the run-compliance gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from dual_sport_selector import WeekPlan, select_week
from run_compliance import validate_run_plan


class RunComplianceError(ValueError):
    """Raised when the completed RUN-LIB block cannot pass its safety gate."""


def plan_dual_sport_block(weeks: list[Mapping[str, Any]]) -> list[WeekPlan]:
    """Select consecutive descriptors, carry state, then hard-gate the block."""
    plans: list[WeekPlan] = []
    prior_races: Sequence[Mapping[str, Any]] = []
    prior_long_run_level: int | None = None
    prior_plan: WeekPlan | None = None

    for descriptor in weeks:
        plan = select_week(
            descriptor,
            prior_week_races=prior_races,
            prior_long_run_level=prior_long_run_level,
            prior_week_plan=prior_plan,
        )
        plans.append(plan)
        prior_races = plan.races
        saturday = plan.sessions.get("Sat")
        if saturday is not None and saturday.archetype_id and saturday.archetype_id.startswith("run.long_run."):
            prior_long_run_level = saturday.level
        prior_plan = plan

    violations = validate_run_plan(plans)
    if violations:
        raise RunComplianceError("RUN-LIB compliance failed:\n" + "\n".join(violations))
    return plans
