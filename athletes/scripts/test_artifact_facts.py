import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from archetype_registry import get_archetype
from fueling_policy import (
    build_fueling_prescription,
    prescription_from_fueling,
    render_workout_fueling,
)
from generate_athlete_package import _get_fuel_tag_for_type
from nate_workout_generator import generate_description
from training_guide_builder import _build_nutrition_section, _section_nutrition


def test_personalized_fuel_artifacts_project_the_serialized_prescription():
    prescription = build_fueling_prescription(
        duration_hours=5.6, weight_kg=61, ftp_watts=230, goal_type="podium", sex="female"
    ).to_dict()
    fueling = {"prescription": prescription, "carbohydrates": {"hourly_target": 999, "total_grams": 999}}
    assert f"{prescription['training_tiers']['quality']['target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Threshold", fueling)
    assert f"{prescription['training_tiers']['long_ride']['target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Endurance", fueling)
    assert f"{prescription['race_target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Race_Sim", fueling)


def test_fuel_tag_gates_on_duration_and_routes_ftp_to_quality():
    """Short aerobic rides get no in-workout fuel banner (<90 min = water is
    fine); FTP tests fuel as quality efforts, not long rides."""
    prescription = build_fueling_prescription(
        duration_hours=5.6, weight_kg=61, ftp_watts=230, goal_type="podium", sex="female"
    ).to_dict()
    fueling = {"prescription": prescription}
    quality = f"{prescription['training_tiers']['quality']['target_g_per_hour']}g carbs/hr"
    long_ride = f"{prescription['training_tiers']['long_ride']['target_g_per_hour']}g carbs/hr"
    # A short endurance ride carries no banner...
    assert _get_fuel_tag_for_type("Endurance", fueling, duration_min=60) == ""
    # ...but a genuinely long one still does.
    assert long_ride in _get_fuel_tag_for_type("Endurance", fueling, duration_min=180)
    # FTP tests fuel as quality, never as a long ride.
    ftp_tag = _get_fuel_tag_for_type("FTP_Test", fueling, duration_min=60)
    assert quality in ftp_tag and long_ride not in ftp_tag
    guide = _build_nutrition_section(fueling, {})
    assert f">{prescription['race_target_g_per_hour']}g/hr<" in guide
    assert f">{prescription['total_g']}g<" in guide
    assert "90g/hr" not in guide


def test_legacy_fueling_yaml_still_renders_workout_tags():
    legacy = {
        "carbohydrates": {"hourly_target": 72, "hourly_range": [65, 79], "total_grams": 360},
        "recommendations": {"hydration": {"target_ml_per_hour": 500}},
    }
    adapted = prescription_from_fueling(legacy)
    assert adapted["race_target_g_per_hour"] == 72
    assert "62g carbs/hr" in _get_fuel_tag_for_type("Threshold", legacy)


def test_shipping_archetype_description_has_no_independent_personalized_rate():
    _, archetype = get_archetype("Gravel Race Simulation")
    description = generate_description(archetype, 3)
    assert "80-90g" not in description
    assert "personalized race prescription" in description


def test_static_guide_ranges_are_explicitly_general_guidance():
    section = _section_nutrition({}, "compete", 90, {})
    assert "General Guidance" in section
    assert "General guidance only" in section
    assert "YOUR PERSONALIZED FUELING TARGETS" not in section
