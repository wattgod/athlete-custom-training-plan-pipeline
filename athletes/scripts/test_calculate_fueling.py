import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from calculate_fueling import estimate_race_duration, generate_fueling_context
from fueling_policy import build_fueling_prescription, tolerated_intake_from_profile
from known_races import UNMATCHED_RACE_MPH, estimate_unmatched_race_duration_hours


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


def test_race_total_carbs_round_full_product_not_accumulated_parts():
    """Regression: the race-card total-carbs figure said '521g' for a
    56g/hr x 9.3333h race, when the correct full-product rounding is
    round(56 x 9.3333) = 523g. The bug was double-rounding -- duration got
    pre-rounded to 1 decimal (9.3) before being multiplied by the hourly
    rate, instead of rounding the full precision product exactly once."""
    prescription = build_fueling_prescription(
        duration_hours=9.3333, weight_kg=80, ftp_watts=150, goal_type="finish",
    )
    assert prescription.race_target_g_per_hour == 56
    assert prescription.total_g == 523
    assert prescription.total_g == round(prescription.race_target_g_per_hour * 9.3333)


def test_estimate_race_duration_no_longer_pre_rounds_to_one_decimal():
    """Regression: estimate_race_duration() used to round its own return
    value to 1 decimal, which then double-rounded every downstream
    multiplication (total carbs, calories) against an already-truncated
    duration. It must now hand back full precision; display sites format
    with .1f themselves."""
    from calculate_fueling import estimate_race_duration
    duration = estimate_race_duration(100, "finish", 6200, "gravel")
    # The specific, previously-buggy live case: 100mi/6200ft gravel finish
    # no longer collapses to an exact-tenth value at the source.
    assert abs(duration - round(duration, 1)) > 1e-9


def test_heather_scale_podium_is_not_flat_90g_per_hour():
    fueling = generate_fueling_context(_profile(61, 230))
    prescription = fueling["prescription"]
    assert 60 <= prescription["race_target_g_per_hour"] <= 75
    assert prescription["race_target_g_per_hour"] != 90
    assert prescription["race_target_g_per_hour"] in range(
        prescription["race_range_g_per_hour"][0], prescription["race_range_g_per_hour"][1] + 1)
    # Full-precision duration (not the display-rounded 5.6h) is what the
    # total-carbs figure is actually computed from -- see
    # test_race_total_carbs_round_full_product_not_accumulated_parts.
    assert abs(prescription["total_g"]
               - prescription["race_target_g_per_hour"] * fueling["race"]["duration_hours"]) <= 1
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


def test_coach_locked_race_fueling_range_is_canonical():
    profile = _profile(80, 230, "finish")
    profile["nutrition"] = {
        "training_fuel": "65 g/h",
        "race_fueling_range_g_per_hour": [60, 70],
    }
    prescription = generate_fueling_context(profile)["prescription"]
    assert prescription["race_target_g_per_hour"] == 65
    assert prescription["race_range_g_per_hour"] == [60, 70]
    assert prescription["inputs"]["prescribed_range_g_per_hour"] == [60, 70]


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


def test_unmatched_race_duration_uses_flat_terrain_estimate_not_goal_speed_table():
    """sol programming review 2026-08-24, major 10: an UNMATCHED race (no
    course-database match) has no verified terrain to trust the
    discipline+goal speed table against -- it modeled Steve Wagner's real
    71mi unmatched gravel event at 5.92h ('6.0 hours' on the race card)
    against the intake's own ~4.7-5h expectation. generate_fueling_context
    must use the flat 15mph unmatched estimator for a generic_profile race,
    not estimate_race_duration's gravel/finish=12mph table."""
    profile = {
        "fitness_markers": {"weight_kg": 80, "ftp_watts": 261, "sex": "male"},
        "target_race": {"distance_miles": 71, "goal_type": "finish",
                        "elevation_ft": 0, "generic_profile": True},
    }
    fueling = generate_fueling_context(profile)
    expected = estimate_unmatched_race_duration_hours(71)
    assert fueling["race"]["duration_hours"] == expected
    assert 4.5 <= fueling["race"]["duration_hours"] <= 5.0
    # Confirms this genuinely differs from (is not accidentally equal to)
    # the discipline/goal-type table it replaces for unmatched races.
    assert fueling["race"]["duration_hours"] != estimate_race_duration(
        71, "finish", 0, "gravel")


def test_matched_race_duration_still_uses_discipline_goal_speed_table():
    """A matched (real course-database) race keeps the richer
    discipline+goal+elevation model -- only UNMATCHED races fall back to
    the flat estimator."""
    profile = {
        "fitness_markers": {"weight_kg": 80, "ftp_watts": 261, "sex": "male"},
        "target_race": {"distance_miles": 71, "goal_type": "finish",
                        "elevation_ft": 0, "race_id": "some_known_race"},
    }
    fueling = generate_fueling_context(profile)
    assert fueling["race"]["duration_hours"] == estimate_race_duration(
        71, "finish", 0, "gravel")


def test_unmatched_race_duration_estimator_matches_the_race_card_mph_constant():
    assert estimate_unmatched_race_duration_hours(71) == 71 / UNMATCHED_RACE_MPH
