"""Golden and contract tests for RUN-LIB descriptions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_archetypes import RUN_ARCHETYPES  # noqa: E402
from run_renderer import get_run_hydration, get_run_nutrition, render_run_description  # noqa: E402


GOLDEN_DIR = Path(__file__).parent / "tests" / "goldens" / "run_descriptions"
HEADERS = [
    "WARM-UP:", "MAIN SET:", "COOL-DOWN:", "PROGRESSION:", "PURPOSE:",
    "EXECUTION:", "NUTRITION:", "HYDRATION:", "RPE:",
]


def _golden_level(workout):
    return 3 if "levels" in workout else 1


def test_all_rendered_descriptions_match_committed_goldens():
    for archetype_id, workout in RUN_ARCHETYPES.items():
        actual = render_run_description(archetype_id, _golden_level(workout))
        # Text fixtures conventionally end in a newline; descriptions (and, in
        # particular, race briefs) deliberately do not gain one at render time.
        expected = (GOLDEN_DIR / f"{archetype_id}.txt").read_text(encoding="utf-8").rstrip("\n")
        assert actual == expected


def test_leveled_descriptions_have_all_sections_in_contract_order():
    for archetype_id, workout in RUN_ARCHETYPES.items():
        if "levels" not in workout:
            continue
        rendered = render_run_description(archetype_id, 3)
        positions = [rendered.index(header) for header in HEADERS]
        assert positions == sorted(positions)


def test_no_bpm_is_rendered_without_an_athlete():
    rendered = render_run_description("run.endurance_z2.bread_and_butter", 3)
    assert "BPM" not in rendered
    assert "70-83% LTHR" in rendered


def test_bpm_is_rendered_from_shipped_hr_data_only_when_lthr_is_available():
    rendered = render_run_description(
        "run.endurance_z2.bread_and_butter", 3, athlete={"lthr": 170}
    )
    assert "119-141 BPM (70-83% LTHR)." in rendered


def test_nutrition_tier_boundaries():
    assert get_run_nutrition("none", 59) == "None needed at this duration."
    assert get_run_nutrition("optional", 60).startswith("Optional:")
    assert get_run_nutrition("z2_long", 90).startswith("40-60g/hr")
    assert get_run_nutrition("dress_rehearsal", 90).startswith("Dress rehearsal:")
    assert "sodium" in get_run_nutrition("z2_long", 121).lower()


def test_hill_medicine_rpe_calls_uphill_reps_running_not_power_hiking():
    rendered = render_run_description("run.hills_reps.hill_medicine", 3)
    rpe_section = rendered.split("RPE:\n", 1)[1]
    assert "running" in rpe_section
    assert "power-hiking" not in rpe_section
    assert "1-2/10 running" not in rpe_section
    assert "walking" in rpe_section or "recovery" in rpe_section


def test_long_runs_and_dress_rehearsals_get_hourly_hydration_below_two_hours():
    assert "500-750ml/hr" in get_run_hydration("long_run", 75, "optional")
    assert "sodium beyond 2 hours" in get_run_hydration("race_pace", 90, "dress_rehearsal")


def test_category_dispatch_is_independent_of_display_name():
    archetype_id = "run.hills_powerhike.hike_the_damn_hill"
    workout = RUN_ARCHETYPES[archetype_id]
    original = workout["display_name"]
    before = render_run_description(archetype_id, 3)
    try:
        workout["display_name"] = "A Completely Renamed Workout"
        assert render_run_description(archetype_id, 3) == before
    finally:
        workout["display_name"] = original
