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
from run_renderer import render_run_description  # noqa: E402
from run_structure_export import (  # noqa: E402
    _build_structure,
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


def test_live_fixture_and_export_are_independently_internally_consistent():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    validate_tp_structure(fixture["structure"])
    exported = export_tp_workout("run.race_pace.loop_one_rehearsal", 3, "2026-07-21")
    exported_structure = exported["structure"]
    exported_segments = get_run_level("run.race_pace.loop_one_rehearsal", 3)["segments"]

    assert set(fixture) - {"_comment"} == set(exported) - {"workoutDay", "description"}
    assert set(fixture["structure"]) == set(exported["structure"])
    assert len(fixture["structure"]["structure"]) == 8
    assert all(
        element["begin"] < element["end"]
        and (index == 0 or element["begin"] == fixture["structure"]["structure"][index - 1]["end"])
        for index, element in enumerate(fixture["structure"]["structure"])
    )
    assert len(exported_structure["structure"]) == len(_unrolled_segments(exported_segments))
    assert sum(
        element["steps"][0]["length"]["value"] for element in exported_structure["structure"]
    ) == get_run_level("run.race_pace.loop_one_rehearsal", 3)["duration"]


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
    payload = export_tp_workout(archetype_id, workout_day="2026-07-21", planned_hours=6.5)

    assert payload["workoutTypeValueId"] == 3
    assert "structure" not in payload
    assert payload["totalTimePlanned"] == 6.5
    assert payload["tssPlanned"] == RUN_ARCHETYPES[archetype_id]["tss"]
    assert payload["description"] == render_run_description(archetype_id, None)


def test_race_brief_requires_positive_planned_hours():
    with pytest.raises(ValueError, match="planned_hours"):
        export_tp_workout("run.race_day.a_race_brief", workout_day="2026-07-21")
    with pytest.raises(ValueError, match="planned_hours"):
        export_tp_workout("run.race_day.a_race_brief", workout_day="2026-07-21", planned_hours=0)


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


def test_label_text_cannot_turn_an_unclassified_segment_into_rest():
    structure = _build_structure(
        [{"type": "steady", "duration": 60, "rpe": [2, 3], "label": "easy jog"}],
        60,
    )
    assert structure["structure"][0]["steps"][0]["intensityClass"] == "active"


def test_fixture_validator_rejects_non_integer_rpe_targets():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    invalid = copy.deepcopy(fixture["structure"])
    invalid["structure"][0]["steps"][0]["targets"][0]["minValue"] = 2.5

    with pytest.raises(ValueError, match="integer RPE"):
        validate_tp_structure(invalid)


def _unrolled_segments(segments):
    result = []
    for segment in segments:
        if segment["type"] == "repeat":
            for _ in range(segment["count"]):
                result.extend(_unrolled_segments(segment["of"]))
        else:
            result.append(segment)
    return result
