"""rTSS contract tests for RUN-LIB's canonical estimation formula."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from run_archetypes import RUN_ARCHETYPES  # noqa: E402
from run_tss import RPE_IF_TABLE, band_for, estimate_tss  # noqa: E402


def test_rpe_if_table_is_complete_and_contiguous():
    bands = [band for band, _ in RPE_IF_TABLE]

    assert RPE_IF_TABLE == (
        ((1, 2), 0.55), ((2, 3), 0.62), ((3, 4), 0.70),
        ((4, 5), 0.78), ((5, 6), 0.83), ((6, 7), 0.88),
        ((7, 8), 0.93), ((8, 9), 1.00), ((9, 10), 1.05),
    )
    assert bands[0][0] == 1
    assert bands[-1][1] == 10
    assert all(lower < upper for lower, upper in bands)
    # The spec's adjacent inclusive endpoint pairs touch but do not duplicate
    # a table row: 1-2, 2-3, ..., 9-10.
    assert all(current[1] == following[0] for current, following in zip(bands, bands[1:]))


def test_known_sixty_minute_rpe_three_to_four_value():
    assert estimate_tss([{"type": "steady", "duration": 60 * 60, "rpe": [3, 4]}]) == 49


def test_repeat_blocks_are_expanded_before_estimation():
    segments = [
        {
            "type": "repeat",
            "count": 3,
            "of": [
                {"type": "steady", "duration": 10 * 60, "rpe": [3, 4]},
                {"type": "hike", "duration": 5 * 60, "rpe": [4, 5]},
            ],
        }
    ]

    assert estimate_tss(segments) == 40


def test_mixed_band_workout_sums_each_segment():
    segments = [
        {"type": "steady", "duration": 30 * 60, "rpe": [3, 4]},
        {"type": "tempo", "duration": 30 * 60, "rpe": [6, 7]},
    ]

    assert estimate_tss(segments) == 63


def test_non_table_rpe_pair_raises():
    with pytest.raises(ValueError, match="table row"):
        band_for([3, 5])
    with pytest.raises(ValueError, match="table row"):
        estimate_tss([{"type": "steady", "duration": 60 * 60, "rpe": [3, 5]}])


def test_shipped_leveled_tss_values_match_estimator():
    race_brief_ids = {
        archetype_id
        for archetype_id, workout in RUN_ARCHETYPES.items()
        if workout.get("structure_exempt")
    }
    assert race_brief_ids == {"run.race_day.a_race_brief", "run.race_day.b_race_brief"}
    assert all("levels" not in RUN_ARCHETYPES[archetype_id] for archetype_id in race_brief_ids)

    levels = [
        level
        for workout in RUN_ARCHETYPES.values()
        for level in workout.get("levels", {}).values()
    ]
    estimates = [estimate_tss(level["segments"]) for level in levels]

    assert all(
        abs(level["tss"] - estimate) <= estimate * 0.15
        for level, estimate in zip(levels, estimates)
    )
    exact_matches = sum(level["tss"] == estimate for level, estimate in zip(levels, estimates))
    print(f"rTSS exact matches: {exact_matches}/{len(levels)}")
    assert exact_matches / len(levels) >= 0.80, (
        f"rTSS exact matches: {exact_matches}/{len(levels)}"
    )
