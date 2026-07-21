"""Golden and contract tests for RUN-LIB descriptions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_archetypes import RUN_ARCHETYPES  # noqa: E402
from run_renderer import get_run_nutrition, render_run_description  # noqa: E402


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
    assert "BPM" not in render_run_description("run.tempo_steady.steady_finish", 3)


def test_bpm_is_rendered_only_when_an_athlete_lthr_and_hr_segment_are_present():
    archetype_id = "run.tempo_steady.steady_finish"
    level = RUN_ARCHETYPES[archetype_id]["levels"]["3"]
    segment = next(segment for segment in level["segments"] if segment["type"] == "tempo")
    original = segment.get("hr_pct_lthr")
    try:
        segment["hr_pct_lthr"] = [85, 90]
        assert "BPM" not in render_run_description(archetype_id, 3)
        rendered = render_run_description(archetype_id, 3, athlete={"lthr": 170})
        assert "145-153 BPM (85-90% LTHR)." in rendered
    finally:
        if original is None:
            segment.pop("hr_pct_lthr", None)
        else:
            segment["hr_pct_lthr"] = original


def test_nutrition_tier_boundaries():
    assert get_run_nutrition("endurance_z2", 59) == "None needed at this duration."
    assert get_run_nutrition("endurance_z2", 60).startswith("Optional:")
    assert get_run_nutrition("endurance_z2", 90).startswith("Optional:")
    assert get_run_nutrition("endurance_z2", 91).startswith("40-60g/hr")
    assert "sodium" in get_run_nutrition("endurance_z2", 121).lower()


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
