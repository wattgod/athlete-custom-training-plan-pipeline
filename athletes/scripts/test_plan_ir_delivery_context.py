"""Delivery-context enrichment coverage for PlanIR."""

from pathlib import Path

import pytest
import yaml

import plan_ir
from plan_ir import build_plan_ir, training_age_class


def _write_zwo(path: Path, name: str, description: str, duration_s: int) -> None:
    path.write_text(
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        "<workout_file>\n"
        f"  <name>{name}</name>\n"
        f"  <description>{description}</description>\n"
        f"  <workout><FreeRide Duration=\"{duration_s}\"/></workout>\n"
        "</workout_file>\n"
    )


@pytest.fixture
def delivery_context_athlete(tmp_path, monkeypatch):
    athletes_dir = tmp_path / "athletes"
    athlete_dir = athletes_dir / "delivery-context-athlete"
    workouts = athlete_dir / "workouts"
    workouts.mkdir(parents=True)
    monkeypatch.setattr(plan_ir, "ATHLETES_DIR", athletes_dir)

    profile = {
        "name": "Delivery Context Athlete",
        "training_history": {"years_cycling": "10+", "years_structured": "0-2"},
        "target_race": {
            "name": "High Country Gravel",
            "date": "2027-09-19",
            "race_metadata": {"start_elevation_feet": 8100},
        },
        "a_events": [{"name": "High Country Gravel", "date": "2027-09-19", "priority": "A"}],
        "b_events": [{"name": "Prep Race", "date": "2027-08-22", "priority": "B"}],
        "c_events": [],
    }
    plan_dates = {
        "weeks": [
            {"week": 1, "phase": "base", "days": [
                {"date": "2027-08-30", "workout_prefix": "W01_Sun_Aug30"},
            ]},
            {"week": 2, "phase": "build", "days": [
                {"date": "2027-09-06", "workout_prefix": "W02_Sun_Sep6"},
            ]},
            {"week": 3, "phase": "taper", "days": [
                {"date": "2027-09-13", "workout_prefix": "W03_Sun_Sep13"},
            ]},
        ],
    }
    (athlete_dir / "profile.yaml").write_text(yaml.safe_dump(profile))
    (athlete_dir / "fueling.yaml").write_text("{}\n")
    (athlete_dir / "plan_dates.yaml").write_text(yaml.safe_dump(plan_dates))
    (athlete_dir / "weekly_structure.yaml").write_text(yaml.safe_dump({"days": {}}))
    _write_zwo(
        workouts / "W01_Sun_Aug30_Long_Endurance.zwo",
        "W01_Sun_Aug30_Long_Endurance",
        "PROGRESSION:\n-Level 2/6: Foundation",
        4 * 60 * 60 + 30 * 60,
    )
    _write_zwo(
        workouts / "W02_Sun_Sep6_Long_Endurance.zwo",
        "W02_Sun_Sep6_Long_Endurance",
        "Long aerobic ride",
        4 * 60 * 60 + 30 * 60,
    )
    _write_zwo(
        workouts / "W03_Sun_Sep13_LTHR_Test.zwo",
        "W03_Sun_Sep13_LTHR_Test",
        "Assessment protocol",
        30 * 60,
    )
    return athlete_dir


def test_level_parsing_from_progression_description(delivery_context_athlete):
    ir = build_plan_ir("delivery-context-athlete", prefer_canonical=False)
    assert ir.weeks[0].sessions[0].level == 2
    assert ir.weeks[1].sessions[0].level is None


def test_week_type_and_simulation_dress_rehearsal(delivery_context_athlete):
    ir = build_plan_ir("delivery-context-athlete", prefer_canonical=False)

    assert [week.week_type for week in ir.weeks] == ["load", "load", "taper"]
    first, second = (ir.weeks[0].sessions[0], ir.weeks[1].sessions[0])
    assert first.is_simulation and second.is_simulation
    assert not first.is_dress_rehearsal
    assert second.is_dress_rehearsal
    assert ir.weeks[2].sessions[0].is_field_test


@pytest.mark.parametrize(("history", "expected"), [
    ({"years_cycling": "10+"}, "experienced"),
    ({"years_cycling": "0-2"}, "developing"),
    ({"years_structured": "3"}, "experienced"),
    ({"years_cycling": ""}, None),
])
def test_training_age_class_normalizes_years(history, expected):
    assert training_age_class({"training_history": history}) == expected


def test_race_metadata_and_event_ledger_passthrough(delivery_context_athlete):
    ir = build_plan_ir("delivery-context-athlete", prefer_canonical=False)
    assert ir.race_snapshot.race_metadata == {"start_elevation_feet": 8100}
    assert ir.brand == "gravelgod"
    assert ir.events == [
        {"name": "High Country Gravel", "date": "2027-09-19", "priority": "A"},
        {"name": "Prep Race", "date": "2027-08-22", "priority": "B"},
    ]


def test_race_metadata_is_none_when_absent(delivery_context_athlete):
    profile_path = delivery_context_athlete / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text())
    del profile["target_race"]["race_metadata"]
    profile_path.write_text(yaml.safe_dump(profile))

    ir = build_plan_ir("delivery-context-athlete", prefer_canonical=False)
    assert ir.race_snapshot.race_metadata is None
