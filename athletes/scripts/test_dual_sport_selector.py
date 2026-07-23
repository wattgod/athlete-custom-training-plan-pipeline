"""R5 tests for deterministic dual-sport run-week selection."""

from __future__ import annotations

from dataclasses import asdict
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from dual_sport_selector import WeekPlan, select_week  # noqa: E402
from run_archetypes import RUN_ARCHETYPES, get_run_level  # noqa: E402


def descriptor(**overrides):
    week = {
        "phase": "base",
        "week_start": "2026-07-20",
        "races": [],
        "long_run_level": 3,
        "quality_level": 3,
    }
    week.update(overrides)
    return week


def category(session):
    return RUN_ARCHETYPES[session.archetype_id]["category"] if session.archetype_id else None


def leaf_segments(segments):
    for segment in segments:
        if segment["type"] == "repeat":
            yield from leaf_segments(segment["of"])
        else:
            yield segment


def duration_minutes(session):
    return get_run_level(session.archetype_id, session.level)["duration"] / 60


def test_selection_is_deterministic_and_explicit_template_days():
    week = descriptor()
    first, second = select_week(week), select_week(week)
    assert first == second
    assert list(first.sessions) == ["Mon", "Tue", "Wed", "Fri", "Sat", "Sun"]
    assert first.sessions["Mon"].archetype_id is None
    assert first.sessions["Fri"].archetype_id is None
    assert first.sessions["Fri"].note == "bike day — existing GG bike libraries"


@pytest.mark.parametrize(
    ("phase", "expected_categories"),
    [
        ("base", {"strides", "hills_powerhike"}),
        ("build", {"tempo_steady", "hills_reps"}),
        ("peak", {"race_pace"}),
        ("taper", {"openers"}),
    ],
)
def test_every_phase_maps_to_its_spec_categories(phase, expected_categories):
    assert category(select_week(descriptor(phase=phase)).sessions["Tue"]) in expected_categories


def test_wednesday_is_optional_capped_and_easy_against_actual_library():
    session = select_week(descriptor(quality_level=6)).sessions["Wed"]
    assert session.optional is True
    assert session.note.startswith("OPTIONAL:")
    assert duration_minutes(session) <= 40
    assert all(segment["rpe"][1] < 5 for segment in leaf_segments(get_run_level(session.archetype_id, session.level)["segments"]))


def test_saturday_bike_race_replaces_long_run_and_turns_friday_into_openers():
    plan = select_week(descriptor(races=[{"date": "2026-07-25", "priority": "B", "sport": "bike"}]))
    assert plan.sessions["Sat"].archetype_id is None
    assert "bike race" in plan.sessions["Sat"].note
    assert plan.sessions["Fri"].note == "bike openers — existing GG bike libraries"


def test_sunday_race_uses_shakeout_variant_and_race_slot():
    plan = select_week(descriptor(races=[{"date": "2026-07-26", "priority": "A", "sport": "run"}]))
    assert category(plan.sessions["Sat"]) == "recovery_easy"
    assert plan.sessions["Sat"].optional is True
    assert plan.sessions["Sun"].archetype_id == "run.race_day.a_race_brief"
    assert plan.sessions["Fri"].note == "bike openers — existing GG bike libraries"


def test_post_race_first_run_downgrades_and_gates_after_prior_saturday_race():
    plan = select_week(descriptor(), prior_week_races=[{"date": "2026-07-18", "priority": "B", "sport": "bike"}])
    assert category(plan.sessions["Tue"]) in {"endurance_z2", "recovery_easy"}
    assert plan.sessions["Tue"].gated is True
    assert "STAIRS GATE" in plan.sessions["Tue"].note


def test_sunday_race_gates_following_tuesday():
    plan = select_week(descriptor(), prior_week_races=[{"date": "2026-07-19", "priority": "C", "sport": "run"}])
    assert category(plan.sessions["Tue"]) in {"endurance_z2", "recovery_easy"}
    assert plan.sessions["Tue"].gated is True


def test_a_race_week_wednesday_is_capped_at_twenty_minutes():
    plan = select_week(descriptor(quality_level=6, races=[{"date": "2026-07-25", "priority": "A", "sport": "bike"}]))
    assert duration_minutes(plan.sessions["Wed"]) <= 20


def test_levels_clamp_and_long_run_respects_plus_one_rule():
    plan = select_week(descriptor(long_run_level=99, quality_level=-4), prior_long_run_level=2)
    assert plan.sessions["Tue"].level == 1
    assert plan.sessions["Sat"].level == 3
    assert select_week(descriptor(long_run_level=-1, quality_level=99)).sessions["Tue"].level == 6


def test_week_plan_serializes_to_json_cleanly():
    plan = select_week(descriptor())
    assert isinstance(plan, WeekPlan)
    assert json.loads(json.dumps(asdict(plan))) == json.loads(json.dumps(plan.to_dict(), sort_keys=True))
