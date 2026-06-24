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


class TestFuelingDurationByDiscipline:
    """Race-duration estimate must reflect discipline — a road event is far
    faster than gravel. (Judge caught an 8h estimate for a 96mi road race.)"""

    def test_road_faster_than_gravel_than_mtb(self):
        from calculate_fueling import estimate_race_duration
        road = estimate_race_duration(96, "finish", 4000, "road")
        gravel = estimate_race_duration(96, "finish", 4000, "gravel")
        mtb = estimate_race_duration(96, "finish", 4000, "mtb")
        assert road < gravel < mtb
        assert road < 7.5  # 96mi road should not read as an 8h+ slog

    def test_default_discipline_is_gravel(self):
        from calculate_fueling import estimate_race_duration
        assert (estimate_race_duration(100, "finish", 0)
                == estimate_race_duration(100, "finish", 0, "gravel"))

    def test_zero_or_missing_distance_never_yields_zero_duration(self):
        # judge caught a 0.0h race in the plan JSON → race-day fueling anchored
        # to a zero-length event. A present-but-zero/None/garbage distance must
        # fall back to a sane non-zero duration.
        from calculate_fueling import estimate_race_duration, generate_fueling_context
        for d in (0, None, "", -5, "abc"):
            assert estimate_race_duration(d, "finish", 0, "gravel") > 0, d
        prof = {"target_race": {"name": "X", "distance_miles": 0, "goal_type": "finish"},
                "fitness_markers": {"weight_kg": 70}, "sex": "male"}
        dur = generate_fueling_context(prof).get("race", {}).get("duration_hours")
        assert dur and dur > 0, dur


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

    def test_workout_execution_is_discipline_neutral(self):
        # the judge flagged a gravel cadence cue and an indoor "6+ hours"
        # string leaking into road/mtb plans — the execution chapter must
        # be discipline-neutral
        from training_guide_builder import _section_workout_execution
        html = _section_workout_execution("Competitor", 250)
        low = html.lower()
        assert "gravel racing requires" not in low
        assert "6+ hours" not in html
        assert "grind up climbs and spin on flats" not in low

    def test_long_ride_peak_capped_by_race_duration(self):
        # the judge flagged a 6.8h long ride for a ~3.8h race — a weekly-hours
        # budget artifact that contradicts the fueling section. The peak must
        # not wildly exceed race duration.
        import re
        from training_guide_builder import _section_weekly_structure
        sched = {"days": {"saturday": {"session": "long_ride"},
                          "sunday": {"session": "rest"},
                          "tuesday": {"session": "intervals"},
                          "thursday": {"session": "intervals"}}}
        html = _section_weekly_structure(sched, "Finisher", "11", 3.8)
        hi = max(float(b) for _, b in re.findall(r"([\d.]+)-([\d.]+) hours", html))
        assert hi <= 3.8 * 1.2, f"long-ride peak {hi}h exceeds race-duration cap"

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
            "selected_methodology": "Polarized (80/20)",
            "configuration": {"intensity_distribution": {"z1_z2": 0.80, "z3": 0.0, "z4_z5": 0.20},
                              "emphasis": "a hard/easy split",
                              "progression_style": "increase_hard_work"},
        })
        assert d["name"] == "Polarized (80/20)"
        # honest VOLUME framing ("roughly N% easy"), not a precise split
        assert "80%" in d["description"] and "easy" in d["description"].lower()

    def test_empty_methodology_yields_no_override(self):
        from training_guide_builder import _methodology_display
        assert _methodology_display({}) == {}


class TestDistributionHonesty:
    """The displayed intensity distribution must not contradict the plan. A
    literal '0% tempo' for Polarized contradicts the Build-phase tempo the
    plan prescribes (judge flag)."""

    def test_display_never_claims_a_precise_tempo_or_hard_split(self):
        # The plan is compliance-bound to mostly-easy riding, so the guide must
        # NOT promise an exact "X% tempo / Y% hard" it can't deliver. It states
        # volume honestly ("roughly N% easy") and describes the emphasis.
        from training_guide_builder import _methodology_display
        import re
        for z1, z3, z45, emph in [(0.80, 0.0, 0.20, "a hard/easy split"),
                                  (0.65, 0.25, 0.10, "the productive zone")]:
            d = _methodology_display({
                "selected_methodology": "M",
                "configuration": {"intensity_distribution":
                                  {"z1_z2": z1, "z3": z3, "z4_z5": z45},
                                  "emphasis": emph}})
            desc = d["description"]
            assert "0% tempo" not in desc
            # no precise "NN% tempo" or "NN% hard" claim
            assert not re.search(r"\d+%\s*(tempo|hard)", desc.lower()), desc
            assert emph in desc                       # leads with the emphasis
            assert "roughly" in desc.lower()          # honest volume framing


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

    def test_mtb_gets_mtb_skills_not_gravel_or_road(self):
        from training_guide_builder import _section_skills
        mtb = _section_skills({}, "mtb")
        assert "Mountain Bike Skills" in mtb
        assert "rock garden" in mtb.lower() or "switchback" in mtb.lower()
        # not the road pack-craft chapter, not gravel-only cornering framing
        assert "HOLDING A WHEEL" not in mtb
        assert "Gravel Skills" not in mtb

    def test_brand_logo_by_discipline(self):
        from training_guide_builder import _brand
        assert _brand("road")["logo"] == "ROADIE LABS"
        assert _brand("gravel")["logo"] == "GRAVEL GOD"
        assert _brand("mtb")["logo"] == "GRAVEL GOD"
        assert _brand(None)["logo"] == "GRAVEL GOD"  # safe default


class TestRaceDataResolution:
    """The guide must load the race file that MATCHES the named race, never
    an unrelated one via fuzzy substring/first-token matching. The judge
    caught 'Niseko, Hokkaido, Japan' rendered on a Greek gran fondo."""

    def _race_dir(self):
        from pathlib import Path
        d = Path.home() / 'Documents' / 'GravelGod' / 'gravel-race-automation' / 'race-data'
        return d

    def test_loutraki_loads_greece_not_japan(self):
        import pytest
        from training_guide_builder import _resolve_race_data
        d = self._race_dir()
        if not d.exists():
            pytest.skip("race-data dir not present")
        rd, loc = _resolve_race_data("UCI Gran Fondo Loutraki", [d])
        # the VENUE fields must be the Greek race, not Japan. (The file's
        # prose legitimately mentions the Niseko worlds as a qualification
        # target — that's history, not the venue, so we only check location.)
        venue = " ".join(str(x).lower() for x in [
            loc,
            (rd.get('race', {}).get('vitals', {}) or {}).get('location'),
            rd.get('location'),
            (rd.get('race_metadata') or {}).get('location'),
        ] if x)
        assert "loutraki" in venue or "greece" in venue
        assert "niseko" not in venue and "hokkaido" not in venue and "japan" not in venue

    def test_no_first_token_or_substring_cross_match(self):
        # a race whose name shares a leading token with an unrelated file
        # must not silently load that file
        import pytest
        from training_guide_builder import _resolve_race_data
        d = self._race_dir()
        if not d.exists():
            pytest.skip("race-data dir not present")
        # gibberish race that matches nothing → empty, never a wrong file
        rd, loc = _resolve_race_data("Zzzx Nonexistent Fondo 9999", [d])
        assert rd == {}

    def test_verified_location_overlaid_when_file_missing(self):
        # even when no JSON file exists, a matched race still yields its
        # verified location (so the venue is correct, never blank-or-wrong)
        from training_guide_builder import _resolve_race_data
        from pathlib import Path
        # point at an empty dir to force the file-miss path
        rd, loc = _resolve_race_data("Maratona dles Dolomites", [Path("/tmp/nonexistent-race-dir")])
        assert rd == {}
        # location comes from the matcher, not a file
        assert loc and "Italy" in loc


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


class TestHeartRateZones:
    """An HR-tested athlete must get real bpm zones off their LTHR — not just
    % columns, and not the mislabeled '% HRmax' (the values are % of LTHR)."""

    def test_lthr_drives_bpm_bands_and_relabel(self):
        from training_guide_builder import _section_training_zones
        html = _section_training_zones(155, "finisher", lthr=170, max_hr=184)
        assert '% LTHR' in html and '% HRmax' not in html   # relabel
        assert 'HR (bpm)' in html                            # real bpm column
        assert 'threshold HR (LTHR): 170' in html            # the anchor
        assert '184 bpm' in html                             # measured HRmax
        # Zone 4 (~95-105% LTHR) must bracket 170 bpm
        import re
        bands = [(int(a), int(b)) for a, b in re.findall(r'(\d{2,3})-(\d{2,3}) bpm', html)]
        assert any(lo <= 170 <= hi for lo, hi in bands), bands

    def test_no_hr_data_keeps_percent_only(self):
        from training_guide_builder import _section_training_zones
        html = _section_training_zones(200, "finisher")  # no lthr
        assert 'HR (bpm)' not in html        # no bpm column without a tested LTHR

    def test_build_profile_captures_hr_markers(self):
        import intake_to_plan as itp
        md = """## Basic Info
- Name: HR Rider
- Email: h@e.com
- Age: 31
- Weight: 150 lbs

## Goals
- Primary Goal: specific_race
- Races:
  Big Sugar Gravel (2026-10-17, 100 miles, priority A)

## Current Fitness
- FTP: 155
- HR Max: 184
- HR Threshold: 170

## Schedule
- Weekly Hours Available: 6
"""
        prof = itp.build_profile(itp.parse_intake_markdown(md))
        fm = prof['fitness_markers']
        assert fm.get('max_hr') == 184 and fm.get('lthr') == 170
