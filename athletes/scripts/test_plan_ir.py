"""PlanIR v0 aggregation tests."""

import json
from pathlib import Path

import pytest
import yaml

import plan_ir
from plan_ir import PlanIR, build_plan_ir


PRESCRIPTION = {
    "race_target_g_per_hour": 72,
    "race_range_g_per_hour": [65, 79],
    "total_g": 360,
    "training_tiers": {
        "quality": {"target_g_per_hour": 62, "range_g_per_hour": [55, 69]},
        "long_ride": {"target_g_per_hour": 67, "range_g_per_hour": [60, 72]},
        "race_sim": {"target_g_per_hour": 72, "range_g_per_hour": [65, 79]},
    },
    "hydration": {"target_ml_per_hour": 600},
    "assumptions": [],
    "inputs": {"duration_hours": 5.0, "weight_kg": 70.0},
    "policy_version": "test-policy",
}


def _write_zwo(path: Path, name: str, blocks: str) -> None:
    path.write_text(
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        "<workout_file>\n"
        f"  <name>{name}</name>\n"
        "  <description>fixture</description>\n"
        f"  <workout>\n{blocks}\n  </workout>\n"
        "</workout_file>\n"
    )


@pytest.fixture
def fixture_athlete(tmp_path, monkeypatch):
    athletes_dir = tmp_path / "athletes"
    athlete_dir = athletes_dir / "fixture-athlete"
    workouts = athlete_dir / "workouts"
    workouts.mkdir(parents=True)
    monkeypatch.setattr(plan_ir, "ATHLETES_DIR", athletes_dir)

    profile = {
        "name": "Fixture Athlete",
        "sex": "female",
        "weight_kg": 70.0,
        "fitness_markers": {"ftp_watts": 250, "resting_hr": 48, "w_kg": 3.57},
        "target_race": {
            "name": "Fixture Gravel",
            "date": "2026-09-13",
            "distance_miles": 75,
            "elevation_ft": 5100,
            "goal_type": "compete",
            "source": "https://example.test/race",
            "verified_at": "2026-07-14",
            "event_year": 2026,
            "course_variant": "standard",
        },
    }
    plan_dates = {
        "race_date": "2026-09-13",
        "weeks": [{
            "week": 1,
            "phase": "taper",
            "days": [
                {"date": "2026-09-11", "workout_prefix": "W01_Fri_Sep11", "is_race_day": False},
                {"date": "2026-09-12", "workout_prefix": "W01_Sat_Sep12", "is_race_day": False},
                {"date": "2026-09-13", "workout_prefix": "W01_Sun_Sep13", "is_race_day": True},
            ],
        }],
    }
    (athlete_dir / "profile.yaml").write_text(yaml.safe_dump(profile))
    (athlete_dir / "fueling.yaml").write_text(yaml.safe_dump({"race": {"duration_hours": 5.0}, "prescription": PRESCRIPTION}))
    (athlete_dir / "plan_dates.yaml").write_text(yaml.safe_dump(plan_dates))
    (athlete_dir / "weekly_structure.yaml").write_text(yaml.safe_dump({"days": {}}))
    _write_zwo(
        workouts / "W01_Fri_Sep11_Intervals.zwo",
        "W01_Fri_Sep11_Intervals",
        '    <Warmup Duration="600" PowerLow="0.45" PowerHigh="0.65"/>\n'
        '    <SteadyState Duration="900" Power="0.70"/>\n'
        '    <IntervalsT Repeat="3" OnDuration="120" OnPower="1.10" OffDuration="120" OffPower="0.50"/>\n'
        '    <Cooldown Duration="300" PowerLow="0.55" PowerHigh="0.40"/>',
    )
    _write_zwo(
        workouts / "W01_Sun_Sep13_RACE_DAY_Fixture_Gravel.zwo",
        "W01_Sun_Sep13_RACE_DAY_Fixture_Gravel",
        '    <FreeRide Duration="18000"/>',
    )
    return athlete_dir


def test_build_plan_ir_aggregates_existing_artifacts(fixture_athlete):
    ir = build_plan_ir("fixture-athlete")

    assert (fixture_athlete / "plan_ir.json").exists()
    assert ir.race_snapshot.name == "Fixture Gravel"
    assert ir.race_snapshot.distance_miles == 75
    assert ir.race_snapshot.elevation_feet == 5100
    assert ir.race_snapshot.source == "https://example.test/race"
    assert ir.fueling.race_target_g_per_hour == PRESCRIPTION["race_target_g_per_hour"]

    sessions = {session.date: session for session in ir.weeks[0].sessions}
    structured = sessions["2026-09-11"]
    assert structured.source_file == "W01_Fri_Sep11_Intervals.zwo"
    assert structured.segments
    intervals = [segment for segment in structured.segments if segment.kind == "intervals"]
    assert len(intervals) == 1
    assert intervals[0].repeat == 3
    assert intervals[0].seconds == 720
    assert sessions["2026-09-12"].origin == "rest"
    assert sessions["2026-09-13"].origin == "event"


def test_plan_ir_json_round_trip(fixture_athlete):
    original = build_plan_ir("fixture-athlete")
    restored = PlanIR.from_dict(json.loads(json.dumps(original.to_dict())))

    assert restored == original


def test_missing_optional_artifact_warns_and_returns_partial_object(fixture_athlete):
    (fixture_athlete / "weekly_structure.yaml").unlink()
    (fixture_athlete / "fueling.yaml").unlink()

    with pytest.warns(RuntimeWarning, match="optional artifact missing"):
        ir = build_plan_ir("fixture-athlete")

    assert ir.fueling is None
    assert ir.weeks


def test_plan_ir_projects_blocked_review_status(fixture_athlete):
    """PlanIR must project the LIVE fulfillment status. intake_to_plan sets its
    final RACE_STALE/quality blockers after generate_athlete_package's own
    build_plan_ir, then re-runs build_plan_ir so plan_ir.json follows the gate;
    without that re-sync plan_ir reports stale GENERATED and G5 flags a
    disagreement with fulfillment_status.json."""
    import json
    (fixture_athlete / "fulfillment_status.json").write_text(json.dumps({
        "status": "BLOCKED_REVIEW",
        "blocking_issues": [{"id": "RACE_STALE", "severity": "CRITICAL",
                             "source": "race_provenance", "message": "no source url"}],
    }))
    ir = build_plan_ir("fixture-athlete")
    assert ir.fulfillment.status == "BLOCKED_REVIEW"


def test_plan_ir_write_is_atomic_on_failure(fixture_athlete, monkeypatch):
    """A write failure must leave an already-valid plan_ir.json intact and leave
    no temp file behind (build_plan_ir runs several times per package)."""
    import os
    import plan_ir
    good = fixture_athlete / "plan_ir.json"
    good.write_text('{"sentinel": true}\n')

    def _boom(*args, **kwargs):
        raise OSError("simulated disk full")

    monkeypatch.setattr(plan_ir.os, "replace", _boom)
    build_plan_ir("fixture-athlete")  # swallows OSError -> RuntimeWarning, non-fatal

    assert good.read_text() == '{"sentinel": true}\n'  # untouched
    assert not any(f.startswith(".plan_ir.") for f in os.listdir(fixture_athlete))
