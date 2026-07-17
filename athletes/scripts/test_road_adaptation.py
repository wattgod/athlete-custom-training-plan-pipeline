#!/usr/bin/env python3
"""Roadie Labs regression coverage for brand, guide, duration, and ZWO output."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from brand_config import get_brand_config, workout_author
from calculate_fueling import generate_fueling_context
from config_loader import get_config
from nate_workout_generator import generate_nate_zwo
import training_guide_builder as guide_builder
from training_guide_builder import _brand, _build_full_guide, _estimate_race_hours
from workout_mapper import render_workout
from workout_selector import select_workouts_for_week


def _road_profile(sex="male"):
    return {
        "name": "Road Test",
        "brand": "roadielabs",
        "discipline": "road",
        "fitness": {"ftp_watts": 250},
        "fitness_markers": {
            "ftp_watts": 250,
            "weight_kg": 65 if sex == "female" else 75,
            "sex": sex,
        },
        "schedule": {
            "weekly_hours": "8",
            "off_days": ["Monday"],
            "long_ride_days": ["Saturday"],
            "interval_days": ["Tuesday"],
        },
        "demographics": {"age": 35, "sex": sex, "weight_lbs": 145},
        "strength": {"include_in_plan": False},
        "target_race": {
            "name": "Gran Fondo Maryland",
            "goal_type": "finish",
            "distance_miles": 100,
            "elevation_feet": 3000,
        },
        "health": {},
        "training_history": {},
        "equipment": {},
    }


def _road_guide(sex="male"):
    derived = {
        "weekly_hours": "8",
        "race_distance_miles": 100,
        "elevation_feet": 3000,
        "race_date": "2027-09-12",
        "plan_start_date": "2027-06-21",
    }
    race_data = {
        "race_metadata": {"elevation_feet": 3000, "location": "Maryland"},
        "elevation_feet": 3000,
        "race_characteristics": {},
        "workout_modifications": {},
        "non_negotiables": {},
        "race_specific": {},
    }
    return _build_full_guide(
        "Road Test", "Gran Fondo Maryland", 100, "finisher",
        "intermediate", 12, _road_profile(sex), derived, {},
        {"template": {}}, race_data,
    )


@pytest.mark.parametrize("sex", ["male", "female"])
def test_road_guide_is_branded_and_has_zero_gravel_leaks(sex):
    guide = _road_guide(sex)
    assert "ROADIE LABS" in guide
    assert "Road Skills" in guide
    assert "gravel" not in guide.lower()
    assert "GRAVEL GOD" not in guide


def test_gravelgod_mtb_retains_off_road_tagline():
    brand = _brand("mtb", {"brand": "gravelgod", "discipline": "mtb"})
    assert brand["tagline"] == "Custom training plans for off-road racing"


def test_guide_and_fueling_share_exact_road_duration():
    profile = _road_profile()
    fueling_hours = generate_fueling_context(profile)["race"]["duration_hours"]
    guide_hours = _estimate_race_hours(
        100, 3000, "finisher", "road", "finish")
    assert guide_hours == fueling_hours
    assert guide_hours < _estimate_race_hours(
        100, 3000, "finisher", "gravel", "finish")


def test_guide_uses_profile_elevation_when_race_repo_data_is_absent(monkeypatch):
    calls = []
    real_estimator = guide_builder.estimate_race_duration

    def capture(distance, goal, elevation, discipline):
        calls.append((distance, goal, elevation, discipline))
        return real_estimator(distance, goal, elevation, discipline)

    monkeypatch.setattr(guide_builder, "estimate_race_duration", capture)
    profile = _road_profile()
    derived = {
        "weekly_hours": "8", "race_distance_miles": 100,
        "elevation_feet": 3000, "race_date": "2027-09-12",
        "plan_start_date": "2027-06-21",
    }
    _build_full_guide(
        "Road Test", "Gran Fondo Maryland", 100, "finisher",
        "intermediate", 12, profile, derived, {}, {"template": {}}, {},
    )
    assert calls
    assert all(call[2] == 3000 for call in calls)
    assert all(call[3] == "road" for call in calls)


def test_brand_guide_path_overrides_are_preserved(monkeypatch):
    # Config intentionally rejects arbitrary /tmp paths. These need not exist;
    # they only verify the resolved override within the allowed repo boundary.
    repo_root = Path(__file__).resolve().parents[2]
    gravel_dir = repo_root / "work" / "test-gravel-guides"
    roadie_dir = repo_root / "work" / "test-roadie-guides"
    monkeypatch.setenv("GG_GUIDES_DIR", str(gravel_dir))
    monkeypatch.setenv("ROADIE_GUIDES_DIR", str(roadie_dir))
    config = get_config()
    assert config.get_guides_dir("gravelgod") == gravel_dir.resolve()
    assert config.get_guides_dir("roadielabs") == roadie_dir.resolve()


def test_all_shared_zwo_emitters_accept_roadie_author():
    author = workout_author(_road_profile())
    assert author == get_brand_config("roadielabs")["workout_author"]

    direct = generate_nate_zwo(
        "durability", level=3, methodology="POLARIZED", variation=3,
        author=author, discipline="road")
    mapped = render_workout(
        "VO2 Bookend", level=3, author=author, discipline="road")
    for zwo in (direct, mapped):
        assert zwo is not None
        assert f"<author>{author}</author>" in zwo
        assert "Gravel God" not in zwo
        assert "gravel" not in zwo.lower()


@pytest.mark.parametrize("name,level", [
    ("VO2 Bookend", 1),
    ("Mixed Intervals", 6),
    ("NP/IF Target", 4),
])
def test_reachable_road_rotations_have_no_gravel_copy(name, level):
    zwo = render_workout(
        name, level=level, author="Roadie Labs Training", discipline="road")
    assert zwo is not None
    assert "gravel" not in zwo.lower()


def test_every_reachable_road_rotation_is_brand_clean_at_every_level():
    names = set()
    for phase in ("base", "build", "race_prep", "racing"):
        for archetype in ("time_crunched", "specialist", "volume", "goat"):
            for block in range(1, 7):
                selected = select_workouts_for_week(
                    phase, archetype, "load", 1, 3,
                    block_number=block, discipline="road")
                names.update(w["name"] for w in selected if w.get("name"))

    assert names, "road selection matrix produced no reachable workouts"
    for name in sorted(names):
        for level in range(1, 7):
            zwo = render_workout(
                name, level=level, author="Roadie Labs Training",
                discipline="road")
            assert zwo is not None, f"failed to render {name} L{level}"
            assert "gravel" not in zwo.lower(), f"road leak in {name} L{level}"
            assert "Gravel God" not in zwo, f"brand leak in {name} L{level}"
