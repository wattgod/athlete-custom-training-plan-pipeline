import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from calculate_fueling import generate_fueling_context
from fueling_policy import build_fueling_prescription, tolerated_intake_from_profile


def _profile(weight, ftp, goal="podium"):
    return {
        "fitness_markers": {"weight_kg": weight, "ftp_watts": ftp, "sex": "female"},
        "target_race": {"distance_miles": 90, "goal_type": goal},
    }


def test_race_elevation_from_target_race_extends_duration_and_energy():
    """Elevation must come from the profile's target_race (the __main__ path
    passes no race_data). Anchoring it to 0 ft understated race duration/energy."""
    flat = dict(_profile(75, 285))
    flat["target_race"] = {"distance_miles": 100, "goal_type": "podium", "elevation_ft": 0}
    climby = dict(_profile(75, 285))
    climby["target_race"] = {"distance_miles": 100, "goal_type": "podium", "elevation_ft": 6200}
    f0 = generate_fueling_context(flat)
    f6 = generate_fueling_context(climby)
    # Elevation is actually read from target_race (not silently 0)...
    assert f6["race"]["elevation_feet"] == 6200
    # ...so the climb-aware race is longer and needs more total carbs/energy.
    assert f6["race"]["duration_hours"] > f0["race"]["duration_hours"]
    assert f6["prescription"]["total_g"] > f0["prescription"]["total_g"]
    assert f6["prescription"]["race_target_g_per_hour"] == f0["prescription"]["race_target_g_per_hour"]


def test_heather_scale_podium_is_not_flat_90g_per_hour():
    fueling = generate_fueling_context(_profile(61, 230))
    prescription = fueling["prescription"]
    assert 60 <= prescription["race_target_g_per_hour"] <= 75
    assert prescription["race_target_g_per_hour"] != 90
    assert prescription["race_target_g_per_hour"] in range(
        prescription["race_range_g_per_hour"][0], prescription["race_range_g_per_hour"][1] + 1)
    assert abs(prescription["total_g"] - prescription["race_target_g_per_hour"] * 5.6) <= 1
    assert any("tolerance was not captured" in item for item in prescription["assumptions"])


def test_heavier_higher_absolute_work_resolves_higher_and_goal_cannot_jump_to_90():
    heather = generate_fueling_context(_profile(61, 230, "finish"))["prescription"]
    heavy = generate_fueling_context(_profile(80, 310, "podium"))["prescription"]
    podium_only = generate_fueling_context(_profile(61, 230, "podium"))["prescription"]
    assert heavy["race_target_g_per_hour"] > heather["race_target_g_per_hour"]
    assert podium_only["race_target_g_per_hour"] < 90
    assert podium_only["race_target_g_per_hour"] - heather["race_target_g_per_hour"] <= 6


def test_explicit_profile_tolerance_reaches_policy_and_ambiguous_servings_do_not():
    assert tolerated_intake_from_profile({"nutrition": {"training_fuel": "55g/hr"}}) == 55
    assert tolerated_intake_from_profile({"nutrition": {"training_fuel": "2 gels per hour"}}) is None
    profile = _profile(80, 450)
    profile["nutrition"] = {"training_fuel": "50 grams per hour"}
    prescription = generate_fueling_context(profile)["prescription"]
    assert prescription["inputs"]["tolerated_g_per_hour"] == 50
    assert prescription["race_target_g_per_hour"] <= 60


def test_low_tolerance_never_produces_target_outside_range():
    prescription = build_fueling_prescription(
        duration_hours=6, weight_kg=70, ftp_watts=300, goal_type="compete",
        tolerated_g_per_hour=20,
    ).to_dict()
    low, high = prescription["race_range_g_per_hour"]
    assert low <= prescription["race_target_g_per_hour"] <= high


def test_missing_tolerance_caps_large_untrained_athlete():
    prescription = build_fueling_prescription(
        duration_hours=4, weight_kg=100, ftp_watts=600, goal_type="podium",
    ).to_dict()
    assert prescription["race_target_g_per_hour"] <= 80


def test_duration_guard_scales_carbs_down_for_ultra_events():
    """Hourly carbs must step DOWN for very long events, never up (fat oxidation
    rises, GI risk climbs). Sub-8h races are uncapped by duration."""
    kw = dict(weight_kg=80, ftp_watts=320, goal_type="podium", tolerated_g_per_hour=90)
    short = build_fueling_prescription(duration_hours=5.0, **kw)
    ultra16 = build_fueling_prescription(duration_hours=16.0, **kw)
    ultra19 = build_fueling_prescription(duration_hours=19.0, **kw)
    ultra = ultra16
    assert ultra16.race_target_g_per_hour < short.race_target_g_per_hour
    assert ultra16.race_target_g_per_hour <= 60          # 12-16h band
    assert ultra19.race_target_g_per_hour <= 50          # >16h band
    assert ultra19.race_target_g_per_hour <= ultra16.race_target_g_per_hour
    # a normal 4-8h gravel race is NOT reduced by the duration cap
    band = build_fueling_prescription(duration_hours=6.0, **kw)
    assert band.race_target_g_per_hour == short.race_target_g_per_hour
    assert any("scales DOWN" in a for a in ultra.assumptions)
    # target stays inside its range after the cap
    assert ultra.race_range_g_per_hour[0] <= ultra.race_target_g_per_hour <= ultra.race_range_g_per_hour[1]
