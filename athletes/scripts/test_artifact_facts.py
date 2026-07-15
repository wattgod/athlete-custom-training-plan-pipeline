import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fueling_policy import build_fueling_prescription, render_workout_fueling
from generate_athlete_package import _get_fuel_tag_for_type
from training_guide_builder import _build_nutrition_section


def test_personalized_fuel_artifacts_project_the_serialized_prescription():
    prescription = build_fueling_prescription(
        duration_hours=5.6, weight_kg=61, ftp_watts=230, goal_type="podium", sex="female"
    ).to_dict()
    fueling = {"prescription": prescription, "carbohydrates": {"hourly_target": 999, "total_grams": 999}}
    assert f"{prescription['training_tiers']['quality']['target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Threshold", fueling)
    assert f"{prescription['training_tiers']['long_ride']['target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Endurance", fueling)
    assert f"{prescription['race_target_g_per_hour']}g carbs/hr" in _get_fuel_tag_for_type("Race_Sim", fueling)
    guide = _build_nutrition_section(fueling, {})
    assert f">{prescription['race_target_g_per_hour']}g/hr<" in guide
    assert f">{prescription['total_g']}g<" in guide
    assert "90g/hr" not in guide
