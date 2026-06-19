"""Methodology selection must be safe and deliverable.

The avatar judge flagged a 61-year-old masters returner on 6h/week assigned
HIIT-Focused (50% hard) — both medically aggressive and undeliverable by
the compliance-bound builder (which always runs ~70-85% easy). These guards
pin the fix.
"""

from select_methodology import select_methodology


def _profile(age, hours, years=4):
    return {
        "health_factors": {"age": age},
        "age": age,
        "weekly_availability": {"cycling_hours_target": hours},
        "training_history": {"years_structured": years},
        "fitness_markers": {"ftp_watts": 200, "sex": "male"},
        "target_race": {"name": "Test Gravel 100", "distance_miles": 100,
                        "goal_type": "finish", "discipline": "gravel"},
    }


def _selected(profile):
    res = select_methodology(profile, {"plan_weeks": 16}, None)
    # select_methodology returns a dict; the chosen name lives under a few keys
    return (res.get("selected_methodology") or res.get("name")
            or res.get("configuration", {}).get("methodology") or "")


def test_masters_does_not_get_hiit():
    name = _selected(_profile(age=61, hours=6))
    assert "HIIT" not in name, f"masters athlete got {name}"


def test_masters_not_given_high_hard_load():
    # the judge's flag was a 50%-HARD plan for a 61yo; the hard fraction
    # (z4_z5), not the tempo fraction, is the medical-safety bound
    res = select_methodology(_profile(age=61, hours=6), {"plan_weeks": 16}, None)
    dist = res.get("configuration", {}).get("intensity_distribution", {})
    assert isinstance(dist, dict) and "z1_z2" in dist
    assert dist.get("z4_z5", 0) < 0.30, f"masters got {dist}"
    # and not the undeliverable near-all-easy extreme either
    assert dist["z1_z2"] < 0.90, dist


def test_distribution_always_dict_for_any_athlete():
    # adaptive-distribution methodologies must be normalized, not crash
    for age, hours in [(30, 12), (55, 7), (45, 5), (62, 9)]:
        res = select_methodology(_profile(age, hours), {"plan_weeks": 16}, None)
        dist = res.get("configuration", {}).get("intensity_distribution")
        assert isinstance(dist, dict) and "z1_z2" in dist, (age, hours, dist)
