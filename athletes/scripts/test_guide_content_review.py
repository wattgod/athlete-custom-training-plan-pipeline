"""Guards for the June 2026 coach content review of the training guide.

Matti reviewed the delivered guide and ordered structural changes. These
tests pin every decision so the content cannot regress:
  1. Non-Negotiables section removed (pointless)
  2-3. Weekly structure + phase progression generalized; week-by-week
       reference removed — THE SCHEDULE LIVES IN THE TRAINING PLAN
  4. Equipment list sanity (no helmet-on-trainer)
  6. Race week has no day-by-day schedule
  7. Gravel skills must agree with the Dirt Craft course
  8. Training zones carry no scheduling prescriptions
  9. Race profile renders only data we actually have
"""

import re

import pytest

from training_guide_builder import (
    REQUIRED_SECTIONS,
    _section_race_week,
    _section_training_zones,
    _section_weekly_structure,
    _section_phase_progression,
    _section_equipment_checklist,
    _section_gravel_skills,
    _build_section_titles,
)


SCHEDULE_DAY_ROW = re.compile(r"<t[dh][^>]*>\s*(?:<strong>)?(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day")


class TestRemovedSections:
    def test_non_negotiables_gone(self):
        assert "non-negotiables" not in REQUIRED_SECTIONS
        titles = [t for _, t in _build_section_titles({}, {})]
        assert "Non-Negotiables" not in titles

    def test_week_by_week_gone(self):
        assert "week-by-week overview" not in REQUIRED_SECTIONS
        titles = [t for _, t in _build_section_titles({}, {})]
        assert "Week-by-Week Overview" not in titles

    def test_toc_numbering_is_sequential(self):
        ids = [sid for sid, _ in _build_section_titles({}, {})]
        assert ids == [f"section-{i+1}" for i in range(len(ids))]


class TestNoScheduleDuplication:
    """The plan calendar is the only schedule. The guide explains, never schedules."""

    def test_weekly_structure_has_no_day_table(self):
        html = _section_weekly_structure({"days": {"monday": {"session": "rest"}}}, "Compete", "10-12")
        assert not SCHEDULE_DAY_ROW.search(html)
        assert "training calendar" in html or "Your plan places them" in html

    def test_race_week_has_no_schedule_table(self):
        html = _section_race_week({}, "compete", "Test Race", {"race_date": "2026-11-14"})
        assert not SCHEDULE_DAY_ROW.search(html)
        assert "Day -1" not in html and "Day -6" not in html
        assert "Pre-Race Checklist" in html  # the advice stays

    def test_phase_progression_has_no_week_numbers(self):
        html = _section_phase_progression(21, "compete")
        assert not re.search(r"WEEKS \d", html)
        assert not re.search(r"Weeks \d+-\d+", html)
        assert "RECOVERY WEEKS" in html  # principle stays, cadence claim doesn't
        assert not re.search(r"Every \d", html)

    def test_zones_have_no_scheduling_prescriptions(self):
        html = _section_training_zones(275, "compete")
        assert "Retest every" not in html
        assert "80% of your training should be" not in html
        assert "80/20 rule" not in html
        assert "20-minute protocol" in html  # the protocol (how, not when) stays
        assert "plan schedules retests" not in html
        assert "plan includes FTP tests" not in html
        assert "plan opens with an FTP test" not in html


class TestEquipmentSanity:
    def test_no_helmet_on_trainer(self):
        html = _section_equipment_checklist({}, {})
        assert "even on trainer" not in html
        assert "every outdoor ride" in html

    def test_repair_kit_scoped_to_outdoor(self):
        html = _section_equipment_checklist({}, {})
        assert "Repair kit (outdoor rides)" in html


class TestDirtCraftAlignment:
    """Technique numbers must agree with the Dirt Craft course."""

    def test_cornering_inside_hand_unweighted(self):
        html = _section_gravel_skills({})
        # Dirt Craft L06: outside foot 60-70% of the work, inside hand
        # almost nothing. The old copy said press through the inside hand.
        assert "inside hand should feel almost empty" in html
        assert "Press weight through outside pedal and inside hand" not in html

    def test_braking_distribution_matches_dirt_craft(self):
        html = _section_gravel_skills({})
        # Dirt Craft L05: hardpack ~70/30, loose gravel 65/35, mud ~50/50
        assert "65/35 on loose gravel" in html
        assert "50/50 on loose)" not in html


class TestAltitudeIsNotClimbing:
    """elevation_feet is total CLIMBING — it once made the guide claim
    Unbound 'takes place at 11,000 feet' (Emporia, KS: ~1,100 ft)."""

    def test_climbing_does_not_trigger_altitude(self):
        from training_guide_builder import _conditional_triggers
        race_data = {"elevation_feet": 11000, "race_metadata": {}}
        assert _conditional_triggers({}, race_data)["altitude"] is False

    def test_real_altitude_triggers(self):
        from training_guide_builder import _conditional_triggers
        race_data = {"race_metadata": {"start_elevation_feet": 6500}}
        assert _conditional_triggers({}, race_data)["altitude"] is True

    def test_section_refuses_without_altitude_data(self):
        from training_guide_builder import _section_altitude_training
        html = _section_altitude_training({"elevation_feet": 11000}, "Test Race", 11000)
        assert html == ""

    def test_section_never_uses_climbing_number(self):
        from training_guide_builder import _section_altitude_training
        race_data = {"race_metadata": {"start_elevation_feet": 6000,
                                       "avg_elevation_feet": 7000},
                     "elevation_feet": 11000}
        html = _section_altitude_training(race_data, "Test Race", 11000)
        # dynamic claims use real altitude, never the climbing total
        assert "around 11000" not in html and "At 11000" not in html
        assert "around 6000" in html
        assert "At 7000 feet" in html


class TestGuideTextBugs:
    """Fixes for judge-found content bugs."""

    def test_zone_watts_are_contiguous(self):
        import re
        from training_guide_builder import _section_training_zones
        html = _section_training_zones(235, "compete")
        watts = [(int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)W", html)]
        assert len(watts) >= 5
        gaps = [(watts[i][1], watts[i + 1][0]) for i in range(len(watts) - 1)
                if watts[i + 1][0] - watts[i][1] != 1]
        assert not gaps, f"zone watt gaps/overlaps: {gaps}"

    def test_ftp_protocol_has_one_maximal_test(self):
        from training_guide_builder import _section_training_zones
        html = _section_training_zones(235, "compete")
        assert "ALL OUT" not in html  # the old two-all-out wording is gone
        assert "20-MINUTE TIME TRIAL" in html
        assert "not the test" in html  # the opener is explicitly not maximal

    def test_long_ride_duration_never_degenerate(self):
        from training_guide_builder import _section_weekly_structure
        # a tiny budget collapses lo==hi; must not render "1.5-1.5 hours"
        sched = {"days": {"saturday": {"session": "long_ride"},
                          "sunday": {"session": "rest"}}}
        html = _section_weekly_structure(sched, "Finisher", "4")
        assert "1.5-1.5" not in html
        import re
        # lookbehind so we don't false-match "4-4" inside a valid "2.4-4 hours"
        assert not re.search(r"(?<![\d.])(\d+(?:\.\d+)?)-\1 hours", html)


class TestMethodologyMatchesSelection:
    """The guide must display the ACTUALLY-SELECTED methodology, never a
    tier default (the judge's top recurring finding: MAF/Sweet-Spot
    athletes told they're on 'Traditional Pyramidal')."""

    def test_display_built_from_selection(self):
        from training_guide_builder import _methodology_display
        d = _methodology_display({
            "selected_methodology": "MAF / Low-HR (LT1)",
            "configuration": {"intensity_distribution": {"z1_z2": 0.95, "z3": 0.0, "z4_z5": 0.05},
                              "progression_style": "build_aerobic_base"},
        })
        assert d["name"] == "MAF / Low-HR (LT1)"
        assert "95% easy" in d["description"]
        assert "Traditional Pyramidal" not in d["description"]

    def test_empty_methodology_yields_no_override(self):
        from training_guide_builder import _methodology_display
        assert _methodology_display({}) == {}


class TestBrandByDiscipline:
    """A road athlete must not get a GRAVEL GOD footer or gravel-cornering
    drills; gravel/mtb keep Gravel God. (Roadie Labs branding.)"""

    def test_road_gets_road_skills_not_gravel(self):
        from training_guide_builder import _section_skills
        road = _section_skills({}, "road")
        assert "Road Skills" in road
        assert "HOLDING A WHEEL" in road  # pack craft
        assert "loose gravel" not in road.lower()

    def test_gravel_gets_gravel_skills(self):
        from training_guide_builder import _section_skills
        assert "Gravel Skills" in _section_skills({}, "gravel")

    def test_brand_logo_by_discipline(self):
        from training_guide_builder import _brand
        assert _brand("road")["logo"] == "ROADIE LABS"
        assert _brand("gravel")["logo"] == "GRAVEL GOD"
        assert _brand("mtb")["logo"] == "GRAVEL GOD"
        assert _brand(None)["logo"] == "GRAVEL GOD"  # safe default


class TestDateVerificationWired:
    """The date-verification card was hardcoded empty (broken cross-repo
    import), so every guide said 'not in database'. It must verify real
    races against the snapshot now."""

    def test_real_race_verifies(self):
        from training_guide_builder import _cross_reference_race_date
        # any real dated race in the snapshot
        from real_races import buildable_races
        races = buildable_races(min_weeks=0, max_weeks=520)
        if not races:
            import pytest
            pytest.skip("snapshot empty")
        race = races[0]
        x = _cross_reference_race_date(race["name"], race["date"])
        assert x.get("matched") is True
        assert x.get("date_match") is True

    def test_unknown_race_not_in_db(self):
        from training_guide_builder import _cross_reference_race_date
        x = _cross_reference_race_date("Totally Fictional Race 99000", "2026-09-26")
        assert x.get("matched") is False


class TestLongRideSlotIsAlwaysEndurance:
    """The long-ride slot must never be a short quality session. A
    time_crunched athlete once got 'Race Simulation' (75-80min) as the
    weekly long ride — shorter than its own fillers, on an athlete with a
    wide-open long-ride day. Long ride = endurance, every phase, every
    archetype."""

    ENDURANCE_FAMILY = {
        "Endurance", "Endurance with Surges", "Endurance Blocks",
        "NP/IF Target", "Long Z2", "Terrain Simulation Z2",
        "Long Endurance", "Z2 Endurance",
    }

    def test_no_long_ride_slot_is_a_quality_session(self):
        import yaml
        from pathlib import Path
        cfg = yaml.safe_load(
            (Path(__file__).parent.parent / "config" / "workout_selection.yaml").read_text())
        phases = cfg.get("phases", cfg)
        offenders = []
        for phase, pdata in phases.items():
            if not isinstance(pdata, dict):
                continue
            lr = pdata.get("slots", {}).get("long_ride")
            if not lr:
                continue
            picks = {"default": lr.get("default")}
            for arch, ov in (lr.get("overrides") or {}).items():
                picks[arch] = ov.get("name") if isinstance(ov, dict) else ov
            for who, name in picks.items():
                if name and name not in self.ENDURANCE_FAMILY:
                    offenders.append(f"{phase}.{who} = {name}")
        assert not offenders, (
            "long-ride slots must be endurance-family: " + "; ".join(offenders))


class TestRaceProfileRemoved:
    """Race Profile section removed entirely per coach review (Jun 2026);
    only the race-date verification card survives, inside section 1."""

    def test_race_profile_not_in_titles(self):
        titles = [t for _, t in _build_section_titles({}, {})]
        assert "Race Profile" not in titles
        assert "race profile" not in REQUIRED_SECTIONS

    def test_date_verification_card_lives_in_brief(self):
        from training_guide_builder import _section_training_plan_brief
        html = _section_training_plan_brief(
            "Jess", "Test Race", 100, "compete", "Compete", "Intermediate",
            21, {"fitness": {}, "demographics": {}, "schedule": {}},
            {"race_date": "2099-11-14"}, {"days": {}}, {},
            date_xref={})
        assert "RACE DATE VERIFICATION" in html
        assert "Triple-check" in html

    def test_brief_has_no_prescriptive_methodology_tables(self):
        from training_guide_builder import _section_training_plan_brief
        html = _section_training_plan_brief(
            "Jess", "Test Race", 100, "compete", "Compete", "Intermediate",
            21, {"fitness": {}, "demographics": {}, "schedule": {}},
            {}, {"days": {}}, {})
        assert "Key Workouts in This Plan" not in html
        assert "Intensity Distribution" not in html
        assert "% of Training" not in html
