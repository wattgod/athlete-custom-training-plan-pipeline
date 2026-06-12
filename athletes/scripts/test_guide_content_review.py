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
    _section_race_profile,
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
        assert "20-minute test" in html  # the protocol (how, not when) stays


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


class TestRaceProfileHonesty:
    def _render(self, race_data):
        return _section_race_profile(
            "Test Race", 100, "", "", "compete", "Intermediate", 21,
            "<svg>radar</svg>", race_data, derived={}, date_xref={})

    def test_no_intel_hides_radar_and_empty_rows(self):
        html = self._render({})
        assert "<svg>radar</svg>" not in html          # radar needs real data
        assert "database intel on this race" in html   # honest note instead
        assert ">Location</strong></td><td></td>" not in html
        assert ">Climate" not in html

    def test_with_intel_shows_radar(self):
        html = self._render({"race_characteristics": {"terrain": "gravel"}})
        assert "<svg>radar</svg>" in html
        assert "database intel" not in html
