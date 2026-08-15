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
from generate_athlete_package import _apply_delivery_fuel_ladder
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


def test_fuel_banner_respects_weekly_gut_ceiling():
    """A base-phase long ride must not tag above the week's gut-training ceiling
    (the plan teaches a week-by-week progression); later weeks are unclamped."""
    prescription = build_fueling_prescription(
        duration_hours=6.8, weight_kg=75, ftp_watts=285, goal_type="podium", sex="male"
    ).to_dict()
    fueling = {"prescription": prescription, "gut_training": {"weekly_progression": [
        {"week": 1, "phase_name": "base", "target_range": [40, 50]},
        {"week": 2, "phase_name": "base", "target_range": [40, 50]},
        {"week": 10, "phase_name": "peak", "target_range": [60, 80]},
    ]}}
    long_ride = prescription["training_tiers"]["long_ride"]["target_g_per_hour"]  # e.g. 62
    # Week 1 (base, ceiling 50): a long ride is clamped down to 50.
    wk1 = _get_fuel_tag_for_type("Endurance", fueling, duration_min=180, week_num=1)
    assert "50g carbs/hr" in wk1 and f"{long_ride}g" not in wk1
    # Week 3 (peak, ceiling 80 >= tier): unclamped, tier value stands.
    wk3 = _get_fuel_tag_for_type("Endurance", fueling, duration_min=180, week_num=3)
    assert f"{long_ride}g carbs/hr" in wk3


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


def _authored_zwo(name, minutes, description=""):
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <name>{name}</name>
  <description>{description}</description>
  <workout>
    <SteadyState Duration=\"{minutes * 60}\" Power=\"0.65\" />
  </workout>
</workout_file>"""


def _race_zwo(name, hours):
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <name>{name}</name>
  <description>RACE DAY\n\nPRE-RACE CHECKLIST:</description>
  <workout>
    <FreeRide Duration=\"{round(hours * 3600)}\" />
  </workout>
</workout_file>"""


def _delivery_calendar(race_hours=9.3):
    stale_tag = "[HIGH FUEL: Target 46g carbs/hr. Practice this prescription.]\n\n"
    documents = {
        "W01_Sat": _authored_zwo("Long Ride 1", 120, stale_tag),
        "W02_Sat": _authored_zwo("Long Ride 2", 180, stale_tag),
        # No author-time tag: calendar reconciliation must still tag every
        # >=90 minute ride that appears in the delivery ladder.
        "W03_Sat": _authored_zwo("Final Rehearsal", 246),
        "W04_Sat": _authored_zwo("Taper Ride", 100, stale_tag),
        "W05_Sat": _race_zwo("Race Day", race_hours),
    }
    manifest = {
        "W01_Sat": {"date": "2026-08-01", "week_num": 1, "tp_kind": "bike"},
        "W02_Sat": {"date": "2026-08-08", "week_num": 2, "tp_kind": "bike"},
        "W03_Sat": {"date": "2026-08-15", "week_num": 3, "tp_kind": "bike"},
        "W04_Sat": {"date": "2026-08-22", "week_num": 4, "tp_kind": "bike"},
        "W05_Sat": {"date": "2026-08-29", "week_num": 5, "tp_kind": "race",
                     "race": {"priority": "A"}},
    }
    dates = {
        "race_date": "2026-08-29",
        "weeks": [
            {"week": 1, "phase": "base"}, {"week": 2, "phase": "build"},
            {"week": 3, "phase": "peak"}, {"week": 4, "phase": "taper"},
            {"week": 5, "phase": "race"},
        ],
    }
    return documents, manifest, dates


def test_authored_fuel_tags_match_delivery_ladder_and_final_rehearsal_hits_race_rate():
    documents, manifest, dates = _delivery_calendar()
    fueling = {"race": {"duration_hours": 9.3},
               "prescription": {"race_target_g_per_hour": 70}}
    ladder = _apply_delivery_fuel_ladder(documents, manifest, dates, fueling)

    ride_dates = ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22"]
    ride_stems = ["W01_Sat", "W02_Sat", "W03_Sat", "W04_Sat"]
    rates = []
    for date, stem in zip(ride_dates, ride_stems):
        rate = ladder[date]
        rates.append(rate)
        assert f"Target {rate}g carbs/hr" in documents[stem]
    assert rates[:3] == sorted(rates[:3])
    assert rates[2] == 70  # final pre-taper long ride = race prescription
    assert rates[3] < 70   # taper deliberately steps back
    assert ladder["2026-08-29"] == 70


def test_race_day_ceiling_note_uses_longest_training_ride_and_threshold():
    documents, manifest, dates = _delivery_calendar(race_hours=9.3)
    _apply_delivery_fuel_ladder(
        documents, manifest, dates,
        {"race": {"duration_hours": 9.3}, "prescription": {"race_target_g_per_hour": 70}},
    )
    ceiling = documents["W05_Sat"]
    assert "RACE-DAY CEILING:" in ceiling
    assert "Final Rehearsal (4.1 hours)" in ceiling
    assert "expected to take 9.3 hours" in ceiling
    assert "First third conservative, fuel on the timer" in ceiling
    assert "coverable in pieces" in ceiling

    documents, manifest, dates = _delivery_calendar(race_hours=6.0)
    _apply_delivery_fuel_ladder(
        documents, manifest, dates,
        {"race": {"duration_hours": 6.0}, "prescription": {"race_target_g_per_hour": 70}},
    )
    assert "RACE-DAY CEILING:" not in documents["W05_Sat"]
