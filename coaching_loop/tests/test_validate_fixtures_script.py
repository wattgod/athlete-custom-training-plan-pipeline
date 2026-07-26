"""CL-T0a deliverable: a validation script real captures get dropped
through, using the same schema as the synthetic fixtures. Exercised here
without any subprocess/network -- straight function calls, no TP access."""

from __future__ import annotations

import json

from coaching_loop.fixtures.loader import (
    EXCLUDED_FIXTURE_ATHLETE_ID,
    SYNTHETIC_ATHLETE_ID,
    SYNTHETIC_DIR,
)
from coaching_loop.validate_fixtures import main, validate_file


def test_synthetic_pilot_fixture_passes():
    path = SYNTHETIC_DIR / f"tp_snapshot_{SYNTHETIC_ATHLETE_ID}.json"
    assert validate_file(path) == []


def test_excluded_athlete_fixture_fails_with_exclusion_reason():
    path = SYNTHETIC_DIR / f"tp_snapshot_{EXCLUDED_FIXTURE_ATHLETE_ID}.json"
    problems = validate_file(path)
    assert problems
    assert any("code-excluded" in p for p in problems)


def test_malformed_json_reported_not_raised(tmp_path):
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    problems = validate_file(bad_file)
    assert problems
    assert "could not read/parse JSON" in problems[0]


def test_schema_violation_reported_with_field_path(tmp_path):
    instance = {
        "schema_version": "tp-fixture-v1",
        "athlete_id": SYNTHETIC_ATHLETE_ID,
        "fetched_at": "2026-08-01T13:00:00Z",
        "source": "synthetic",
        "calendar": {"week_start": "2026-07-27", "athlete_tz": "America/Denver", "days": []},
        "workouts": [],
        "comments": [],
    }
    bad_file = tmp_path / "bad_fixture.json"
    bad_file.write_text(json.dumps(instance), encoding="utf-8")
    problems = validate_file(bad_file)
    assert problems  # calendar.days must have 7 entries


def test_main_exits_zero_on_all_pass():
    path = SYNTHETIC_DIR / f"tp_snapshot_{SYNTHETIC_ATHLETE_ID}.json"
    assert main([str(path)]) == 0


def test_main_exits_nonzero_on_any_fail():
    passing = SYNTHETIC_DIR / f"tp_snapshot_{SYNTHETIC_ATHLETE_ID}.json"
    failing = SYNTHETIC_DIR / f"tp_snapshot_{EXCLUDED_FIXTURE_ATHLETE_ID}.json"
    assert main([str(passing), str(failing)]) == 1


def test_main_can_validate_a_whole_directory():
    assert main([str(SYNTHETIC_DIR)]) == 1  # the excluded-athlete fixture lives there on purpose
