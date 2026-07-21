"""Tests for the RUN-LIB v1 data model and registry."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_archetypes import (  # noqa: E402
    RPE_TO_IF,
    RUN_ARCHETYPES,
    calculate_tss,
    catalog,
    get_run_level,
    validate_library,
)


def test_library_loads_with_expected_archetypes():
    assert len(catalog()) == 15
    assert sum("levels" in item for item in RUN_ARCHETYPES.values()) == 13
    assert sum("levels" not in item for item in RUN_ARCHETYPES.values()) == 2
    assert sum(len(item.get("levels", {})) or 1 for item in RUN_ARCHETYPES.values()) == 80


def test_shipped_library_validates_cleanly():
    assert validate_library() == []


def test_level_key_normalization_accepts_int_or_string():
    assert get_run_level("run.endurance_z2.bread_and_butter", 3) == get_run_level(
        "run.endurance_z2.bread_and_butter", "3"
    )
    assert get_run_level("run.endurance_z2.bread_and_butter", 3)["duration"] == 3600


def test_tss_formula_for_every_leveled_item():
    for workout in RUN_ARCHETYPES.values():
        for level in workout.get("levels", {}).values():
            calculated = calculate_tss(level["segments"])
            assert level["tss"] == round(calculated)


def _bad_library():
    return copy.deepcopy(RUN_ARCHETYPES)


def test_validator_catches_id_category_mismatch():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["category"] = "long_run"
    assert any("ID must match" in issue for issue in validate_library(bad))


def test_validator_catches_malformed_id():
    bad = _bad_library()
    workout = bad.pop("run.endurance_z2.bread_and_butter")
    bad["run.endurance_z2.not-valid"] = workout
    assert any("ID must match" in issue for issue in validate_library(bad))


def test_validator_catches_non_run_sport():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["sport"] = "bike"
    assert any("sport must be 'run'" in issue for issue in validate_library(bad))


def test_validator_catches_missing_level():
    bad = _bad_library()
    del bad["run.endurance_z2.bread_and_butter"]["levels"]["6"]
    assert any("exactly levels 1-6" in issue for issue in validate_library(bad))


def test_validator_catches_invalid_rpe_band():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["levels"]["1"]["segments"][0]["rpe"] = [3, 5]
    assert any("invalid RPE band" in issue for issue in validate_library(bad))


def test_validator_catches_duration_mismatch():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["levels"]["1"]["duration"] += 60
    assert any("duration does not equal" in issue for issue in validate_library(bad))


def test_validator_catches_tss_mismatch():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["levels"]["1"]["tss"] = 999
    assert any("tss is outside" in issue for issue in validate_library(bad))


def test_validator_catches_duplicate_ids_and_display_names():
    duplicate = copy.deepcopy(RUN_ARCHETYPES["run.endurance_z2.bread_and_butter"])
    pairs = list(RUN_ARCHETYPES.items()) + [
        ("run.endurance_z2.bread_and_butter", duplicate),
    ]
    violations = validate_library(pairs)
    assert any("Duplicate ID" in issue for issue in violations)
    assert any("Duplicate display name" in issue for issue in violations)


def test_validator_catches_long_run_cap():
    bad = _bad_library()
    level = bad["run.long_run.time_on_feet"]["levels"]["6"]
    level["duration"] = 196 * 60
    assert any("long run exceeds 195" in issue for issue in validate_library(bad))


def test_rpe_lookup_is_complete_for_authored_segments():
    for workout in RUN_ARCHETYPES.values():
        for level in workout.get("levels", {}).values():
            assert all(
                tuple(segment["rpe"]) in RPE_TO_IF
                for segment in _leaf_segments(level["segments"])
            )


def _leaf_segments(segments):
    result = []
    for segment in segments:
        if segment["type"] == "repeat":
            result.extend(_leaf_segments(segment["of"]))
        else:
            result.append(segment)
    return result
