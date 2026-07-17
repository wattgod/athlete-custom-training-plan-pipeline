from road_racing import (
    normalize_event_format,
    normalize_road_category,
    resolve_event_format,
    road_category_profile,
)
from block_compliance import VO2MAX_TYPES
from workout_selector import select_workouts_for_week
from workout_mapper import render_workout, resolve_display_name
from intake_to_plan import build_profile, parse_intake_markdown
from training_guide_builder import (
    _build_section_titles,
    _section_road_category_progression,
    _section_road_format_strategy,
)


def test_explicit_event_format_wins_over_name():
    result = resolve_event_format({
        "event_format": "time trial",
        "target_race": {"name": "Downtown Criterium"},
    })
    assert result == {
        "event_format": "time_trial",
        "source": "explicit",
        "needs_review": False,
    }


def test_conservative_name_inference_and_unknown_default():
    assert resolve_event_format(
        {"target_race": {"name": "City Park Crit"}}
    )["event_format"] == "criterium"
    unknown = resolve_event_format(
        {"target_race": {"name": "The Big Bicycle Day"}}
    )
    assert unknown["event_format"] == "generic_road"
    assert unknown["needs_review"] is True


def test_format_and_category_aliases():
    assert normalize_event_format("Gran Fondo") == "fondo"
    assert normalize_event_format("ITT") == "time_trial"
    assert normalize_road_category("Novice") == "cat_5"
    assert normalize_road_category("Category 2") == "cat_2"
    assert normalize_road_category("4.1 W/kg") is None


def test_category_profile_is_rules_dated_content():
    profile = road_category_profile("Cat 4")
    assert profile["next"] == "Cat 3"
    assert profile["planning_horizon_weeks"] == 12
    assert "points" in profile["current_rule_summary"].lower()


def _build_menu(event_format=None):
    return select_workouts_for_week(
        phase="build",
        archetype="specialist",
        week_type="load",
        week_in_block=1,
        base_level=3,
        max_level=5,
        max_intensity=2,
        hours_per_week=10,
        block_number=1,
        discipline="road",
        methodology="polarized_80_20",
        event_format=event_format,
    )


def test_each_format_changes_secondary_work_without_displacing_vo2():
    expected = {
        "generic_road": "Race Simulation",
        "criterium": "Microbursts",
        "hill_climb": "Mixed Climbing Variations",
        "time_trial": "Threshold Steady",
        "stage_race": "Blended Endurance, Threshold, and Sprints",
        "fondo": "Tempo with Accelerations",
    }
    for event_format, secondary in expected.items():
        menu = _build_menu(event_format)
        intensity = [w["name"] for w in menu if w["role"] == "intensity"]
        assert intensity[0] in VO2MAX_TYPES
        assert intensity[1] == secondary
        long_ride = next(w for w in menu if w["role"] == "long_ride")
        expected_long = {
            "generic_road": "Endurance with Surges",
            "criterium": "Endurance with Surges",
            "hill_climb": "Endurance Blocks",
            "time_trial": "NP/IF Target",
            "stage_race": "Endurance with Surges",
            "fondo": "Endurance with Surges",
        }[event_format]
        assert long_ride["name"] == expected_long


def test_legacy_selection_is_identical_when_format_unspecified():
    assert _build_menu() == _build_menu(None)


def test_optional_format_and_license_category_reach_profile():
    parsed = parse_intake_markdown("""# Athlete Intake: Example Athlete
Email: example@example.com

## Basic Info
- Sex: Male
- Age: 35
- Weight: 165 lbs

## Goals
- Primary Goal: specific_race
- Brand: roadielabs
- Discipline: road
- Race Format: crit
- Road Category: Cat 4
- Races:
  Example Downtown Race (2026-10-04, 40 mi, priority A)
- Success: Compete

## Current Fitness
- FTP: 250

## Schedule
- Weekly Hours Available: 10
""")
    profile = build_profile(parsed)
    assert profile["discipline"] == "road"
    assert profile["event_format"] == "criterium"
    assert profile["target_race"]["event_format_source"] == "explicit"
    assert profile["road_category"] == "cat_4"


def test_road_guide_has_format_strategy_and_full_upgrade_path():
    profile = {
        "discipline": "road",
        "event_format": "criterium",
        "road_category": "cat_4",
        "target_race": {"name": "Example Crit", "event_format": "criterium"},
    }
    strategy = _section_road_format_strategy(profile)
    category = _section_road_category_progression(profile)
    titles = [title for _, title in _build_section_titles(profile, {})]

    assert "Criterium Strategy" in strategy
    assert "6&ndash;10 seconds" in strategy
    assert "YOUR CURRENT PATH: Cat 4" in category
    assert "Novice / Cat 5" in category
    assert "Cat 1" in category
    assert "USA Cycling Policy VIII" in category
    assert "Mass-Start Upgrade Points Snapshot" in category
    assert "70+" in category
    assert "Stage-race general-classification points" in category
    assert "Road Race Strategy" in titles
    assert "Category 5 to Category 1 Pathway" in titles


def test_criterium_microbursts_render_without_gravel_language():
    display = resolve_display_name(
        "Microbursts", methodology="POLARIZED",
        variation_offset=3, discipline="road")
    zwo = render_workout(
        "Microbursts", level=3, methodology="POLARIZED",
        workout_name="Roadie_Crit_Bursts", variation_offset=3,
        author="Roadie Labs Training", discipline="road")
    assert "gravel" not in display.lower()
    assert "gravel" not in zwo.lower()
    assert "Roadie Labs Training" in zwo
