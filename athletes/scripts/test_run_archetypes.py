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


def test_validator_requires_nonempty_display_name_and_complete_brief_data():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["display_name"] = ""
    brief = bad["run.race_day.a_race_brief"]
    brief["description_brief"] = ""
    brief["tss"] = 0
    violations = validate_library(bad)
    assert any("display_name must be non-empty" in issue for issue in violations)
    assert any("non-empty description_brief" in issue for issue in violations)
    assert any("positive tss" in issue for issue in violations)


def test_validator_collects_unknown_type_and_malformed_repeat_errors():
    bad = _bad_library()
    level = bad["run.endurance_z2.bread_and_butter"]["levels"]["1"]
    level["segments"][0]["type"] = "teleport"
    level["segments"].append({"type": "repeat", "count": "three"})
    violations = validate_library(bad)
    assert any("unknown segment type" in issue for issue in violations)
    assert any("malformed repeat" in issue for issue in violations)


def test_validator_rejects_duplicate_and_mixed_axis_adjacent_levels():
    bad = _bad_library()
    levels = bad["run.strides.quick_feet"]["levels"]
    levels["2"] = copy.deepcopy(levels["1"])
    violations = validate_library(bad)
    assert any("adjacent levels must differ" in issue for issue in violations)

    bad = _bad_library()
    level = bad["run.strides.quick_feet"]["levels"]["2"]
    level["duration"] += 180
    level["segments"][1]["count"] += 1
    violations = validate_library(bad)
    assert any("change both duration and density" in issue for issue in violations)


def test_validator_catches_changed_work_interval_length_with_changed_duration():
    """Regression: 3x7min -> 3x8min must not evade the single-axis check."""
    bad = _bad_library()
    levels = bad["run.race_pace.loop_one_rehearsal"]["levels"]
    levels["3"] = copy.deepcopy(levels["2"])
    levels["3"]["duration"] += 5 * 60
    levels["3"]["segments"][1]["of"][0]["duration"] = 8 * 60
    assert any("change both duration and density" in issue for issue in validate_library(bad))


def test_validator_requires_fueling_tier_and_duration_consistency():
    bad = _bad_library()
    del bad["run.endurance_z2.bread_and_butter"]["levels"]["1"]["fueling_tier"]
    bad["run.endurance_z2.bread_and_butter"]["levels"]["6"]["fueling_tier"] = "optional"
    violations = validate_library(bad)
    assert any("missing fueling_tier" in issue for issue in violations)
    assert any("90 minutes or longer" in issue for issue in violations)


def test_validator_catches_long_run_cap():
    bad = _bad_library()
    level = bad["run.long_run.time_on_feet"]["levels"]["6"]
    level["duration"] = 196 * 60
    assert any("long run exceeds 195" in issue for issue in validate_library(bad))


def test_validator_requires_coherent_structure_exempt_definitions():
    bad = _bad_library()
    bad["run.endurance_z2.bread_and_butter"]["structure_exempt"] = True
    bad["run.race_day.a_race_brief"]["category"] = "recovery_easy"
    del bad["run.race_day.b_race_brief"]["structure_exempt"]
    violations = validate_library(bad)
    assert any("leveled item cannot be structure_exempt" in issue for issue in violations)
    assert any("unleveled item must use category race_day" in issue for issue in violations)
    assert any("unleveled item must be structure_exempt" in issue for issue in violations)


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
