"""Contract tests for RUN-LIB's TrainingPeaks structure export."""

from __future__ import annotations

import copy
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from run_archetypes import RUN_ARCHETYPES, get_run_level  # noqa: E402
from run_structure_export import (  # noqa: E402
    export_tp_structure,
    export_tp_workout,
    validate_tp_structure,
)


FIXTURE_PATH = Path(__file__).parent / "tests" / "fixtures" / "tp_run_structure_fixture.json"
LEVELED_ARCHETYPES = [
    archetype_id for archetype_id, workout in RUN_ARCHETYPES.items() if "levels" in workout
]


def _total_seconds(structure: dict) -> float:
    return structure["structure"][-1]["end"]


def test_live_fixture_round_trips_through_the_same_shape_validator():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    validate_tp_structure(fixture["structure"])


@pytest.mark.parametrize("archetype_id", LEVELED_ARCHETYPES)
@pytest.mark.parametrize("level", [1, 6])
def test_leveled_exports_validate_and_preserve_duration_and_flat_repeats(archetype_id, level):
    structure = export_tp_structure(archetype_id, level)
    level_data = get_run_level(archetype_id, level)

    validate_tp_structure(structure)
    assert _total_seconds(structure) == level_data["duration"]
    assert all(element["type"] == "step" for element in structure["structure"])
    assert all("repeat" not in element for element in structure["structure"])


@pytest.mark.parametrize("archetype_id", LEVELED_ARCHETYPES)
@pytest.mark.parametrize("level", [1, 6])
def test_leveled_workout_payload_uses_library_duration_and_tss(archetype_id, level):
    payload = export_tp_workout(archetype_id, level, date(2026, 7, 21))
    level_data = get_run_level(archetype_id, level)

    assert payload["workoutTypeValueId"] == 3
    assert payload["workoutDay"] == "2026-07-21T00:00:00"
    assert abs(payload["totalTimePlanned"] - level_data["duration"] / 3600) < 1e-6
    assert payload["tssPlanned"] == level_data["tss"]
    validate_tp_structure(payload["structure"])


@pytest.mark.parametrize("archetype_id", ["run.race_day.a_race_brief", "run.race_day.b_race_brief"])
def test_race_brief_payload_omits_structure(archetype_id):
    payload = export_tp_workout(archetype_id, 1, "2026-07-21")

    assert payload["workoutTypeValueId"] == 3
    assert "structure" not in payload


def test_structure_export_is_deterministic():
    first = export_tp_structure("run.hills_powerhike.hike_the_damn_hill", 6)
    second = export_tp_structure("run.hills_powerhike.hike_the_damn_hill", 6)
    assert first == second


def test_intensity_classes_distinguish_warmup_cooldown_and_stride_recoveries():
    structure = export_tp_structure("run.strides.quick_feet", 1)
    steps = [element["steps"][0] for element in structure["structure"]]

    assert steps[0]["intensityClass"] == "warmUp"
    assert steps[-1]["intensityClass"] == "coolDown"
    assert all(
        step["intensityClass"] == "rest"
        for step in steps
        if step["name"] == "Easy jog"
    )


def test_fixture_validator_rejects_non_integer_rpe_targets():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    invalid = copy.deepcopy(fixture["structure"])
    invalid["structure"][0]["steps"][0]["targets"][0]["minValue"] = 2.5

    with pytest.raises(ValueError, match="integer RPE"):
        validate_tp_structure(invalid)
