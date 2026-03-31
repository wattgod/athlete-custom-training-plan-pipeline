#!/usr/bin/env python3
"""
Tests for block-builder compliance rules adopted into the training plan pipeline.

Rules tested:
- Recovery week insertion (3:1 mesocycle pattern)
- Training age constraints (intensity caps, level caps)
- Masters athlete constraints (48hr gap, intensity cap)
- Back-to-back intensity ban (cross-week aware)
- Weekly hour budget enforcement
- VO2max 14-day gap check
- Per-workout fuel tags
- Strength + interval separation
- Series coherence within mesocycles

Created: Mar 2026
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from constants import (
    INTENSITY_WORKOUT_TYPES,
    EASY_WORKOUT_TYPES,
    RECOVERY_WEEK_VOLUME_FACTOR,
    RECOVERY_WEEK_MIN_PLAN_WEEKS,
    MASTERS_AGE_THRESHOLD,
    TRAINING_AGE_CONSTRAINTS,
    MASTERS_MAX_INTENSITY_PER_WEEK,
    WEEKLY_HOUR_BUDGET_TOLERANCE,
    VO2MAX_GAP_MAX_DAYS,
    FUEL_TAGS,
    RACE_SIM_WORKOUT_TYPES,
    DEFAULT_MESO_PATTERN,
)
from calculate_plan_dates import calculate_plan_dates, parse_meso_pattern


# ============================================================
# Step 0: Constants validation
# ============================================================

class TestComplianceConstants:
    def test_intensity_types_not_in_easy_types(self):
        """No overlap between intensity and easy workout types."""
        overlap = set(INTENSITY_WORKOUT_TYPES) & set(EASY_WORKOUT_TYPES)
        assert not overlap, f"Overlap: {overlap}"

    def test_fuel_tag_keys(self):
        """All three fuel tag categories present."""
        assert 'intensity' in FUEL_TAGS
        assert 'endurance' in FUEL_TAGS
        assert 'race_sim' in FUEL_TAGS

    def test_recovery_volume_range(self):
        """Recovery volume factor is between 0 and 1."""
        low, high = RECOVERY_WEEK_VOLUME_FACTOR
        assert 0 < low < high <= 1.0

    def test_training_age_constraints_ordered(self):
        """Higher training age thresholds allow more intensity."""
        prev_max_int = 0
        for threshold in sorted(TRAINING_AGE_CONSTRAINTS.keys()):
            max_int, max_lvl = TRAINING_AGE_CONSTRAINTS[threshold]
            assert max_int >= prev_max_int
            prev_max_int = max_int

    def test_openers_not_intensity(self):
        """Openers should NOT be in INTENSITY_WORKOUT_TYPES (allowed in recovery weeks)."""
        assert 'Openers' not in INTENSITY_WORKOUT_TYPES

    def test_default_meso_pattern_parseable(self):
        """Default meso pattern can be parsed."""
        load, recovery = parse_meso_pattern(DEFAULT_MESO_PATTERN)
        assert load >= 1
        assert recovery >= 1


# ============================================================
# Step 1: Recovery week marking
# ============================================================

class TestRecoveryWeeks:
    def test_12_week_plan_has_recovery_weeks(self):
        """3:1 pattern in a 12-week plan: weeks 4, 8 are recovery."""
        # Use a far-future date to avoid past-date issues
        result = calculate_plan_dates('2027-06-01', plan_weeks=12, meso_pattern='3:1')
        weeks = result['weeks']
        recovery_weeks = [w['week'] for w in weeks if w.get('is_recovery_week')]
        assert 4 in recovery_weeks, f"Week 4 should be recovery. Got: {recovery_weeks}"
        assert 8 in recovery_weeks, f"Week 8 should be recovery. Got: {recovery_weeks}"

    def test_short_plan_skips_recovery(self):
        """Plans < 6 weeks have no recovery weeks."""
        result = calculate_plan_dates('2027-06-01', plan_weeks=5, meso_pattern='3:1')
        weeks = result['weeks']
        recovery_weeks = [w['week'] for w in weeks if w.get('is_recovery_week')]
        assert len(recovery_weeks) == 0

    def test_taper_race_never_recovery(self):
        """Taper and race weeks are never marked as recovery."""
        result = calculate_plan_dates('2027-06-01', plan_weeks=12, meso_pattern='3:1')
        weeks = result['weeks']
        for w in weeks:
            if w['phase'] in ('taper', 'race'):
                assert not w.get('is_recovery_week'), \
                    f"Week {w['week']} ({w['phase']}) should not be recovery"

    def test_2_1_pattern(self):
        """2:1 pattern marks every 3rd week as recovery."""
        result = calculate_plan_dates('2027-06-01', plan_weeks=12, meso_pattern='2:1')
        weeks = result['weeks']
        recovery_weeks = [w['week'] for w in weeks
                          if w.get('is_recovery_week') and w['phase'] not in ('taper', 'race')]
        assert 3 in recovery_weeks, f"Week 3 should be recovery. Got: {recovery_weeks}"
        assert 6 in recovery_weeks, f"Week 6 should be recovery. Got: {recovery_weeks}"

    def test_b_race_overrides_recovery(self):
        """B-race on a recovery week clears the recovery flag."""
        # Calculate which week 4 Monday falls on, then place B-race there
        result = calculate_plan_dates('2027-06-01', plan_weeks=12, meso_pattern='3:1')
        week_4 = result['weeks'][3]
        b_race_date = week_4['days'][3]['date']  # Thursday of week 4

        result2 = calculate_plan_dates(
            '2027-06-01', plan_weeks=12, meso_pattern='3:1',
            b_events=[{'name': 'Local Race', 'date': b_race_date}]
        )
        week_4_with_b = result2['weeks'][3]
        assert not week_4_with_b.get('is_recovery_week'), \
            "Recovery week should be cleared when B-race is present"

    def test_all_weeks_have_recovery_flag(self):
        """Every week has the is_recovery_week field."""
        result = calculate_plan_dates('2027-06-01', plan_weeks=12, meso_pattern='3:1')
        for w in result['weeks']:
            assert 'is_recovery_week' in w, f"Week {w['week']} missing is_recovery_week"


class TestParsePatterns:
    def test_3_1(self):
        assert parse_meso_pattern('3:1') == (3, 1)

    def test_2_1(self):
        assert parse_meso_pattern('2:1') == (2, 1)

    def test_4_1(self):
        assert parse_meso_pattern('4:1') == (4, 1)

    def test_invalid_falls_back(self):
        assert parse_meso_pattern('invalid') == (3, 1)

    def test_empty_falls_back(self):
        assert parse_meso_pattern('') == (3, 1)


# ============================================================
# Step 3: Training age constraints
# ============================================================

class TestTrainingAgeConstraints:
    def test_beginner_caps(self):
        """years_structured=0: max 1 intensity, max level 2."""
        max_int, max_lvl = TRAINING_AGE_CONSTRAINTS[0]
        assert max_int == 1
        assert max_lvl == 2

    def test_novice_caps(self):
        """years_structured=1: max 2 intensity, max level 3."""
        max_int, max_lvl = TRAINING_AGE_CONSTRAINTS[1]
        assert max_int == 2
        assert max_lvl == 3

    def test_masters_threshold(self):
        """Masters threshold is 50."""
        assert MASTERS_AGE_THRESHOLD == 50

    def test_masters_intensity_cap(self):
        """Masters athletes: max 2 intensity per week."""
        assert MASTERS_MAX_INTENSITY_PER_WEEK == 2


# ============================================================
# Step 5: Weekly hour budget
# ============================================================

class TestWeeklyHourBudget:
    def test_budget_tolerance(self):
        """Budget tolerance is 110%."""
        assert WEEKLY_HOUR_BUDGET_TOLERANCE == 1.10

    def test_budget_calculation(self):
        """8 hr target → max 528 min (8 * 60 * 1.10)."""
        target_hours = 8
        max_min = target_hours * 60 * WEEKLY_HOUR_BUDGET_TOLERANCE
        assert max_min == 528.0


# ============================================================
# Step 6: VO2max gap check
# ============================================================

class TestVO2maxGapConstants:
    def test_gap_max_days(self):
        """VO2max gap maximum is 16 days."""
        assert VO2MAX_GAP_MAX_DAYS == 16


# ============================================================
# Step 7: Fuel tags
# ============================================================

class TestFuelTags:
    def test_intensity_fuel_tag_content(self):
        """Intensity fuel tag mentions carbs/hr."""
        assert 'carbs/hr' in FUEL_TAGS['intensity']
        assert '60-90g' in FUEL_TAGS['intensity']

    def test_endurance_fuel_tag_content(self):
        """Endurance fuel tag is moderate."""
        assert 'carbs/hr' in FUEL_TAGS['endurance']
        assert '30-60g' in FUEL_TAGS['endurance']

    def test_race_sim_fuel_tag_content(self):
        """Race sim fuel tag practices race-day fueling."""
        assert 'carbs/hr' in FUEL_TAGS['race_sim']
        assert '80-100g' in FUEL_TAGS['race_sim']

    def test_race_sim_types(self):
        """Race_Sim and Gravel_Specific get practice fuel."""
        assert 'Race_Sim' in RACE_SIM_WORKOUT_TYPES
        assert 'Gravel_Specific' in RACE_SIM_WORKOUT_TYPES


# ============================================================
# Integration: fuel tag helper
# ============================================================

class TestFuelTagHelper:
    def test_vo2max_gets_high_fuel(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('VO2max')
        assert 'HIGH FUEL' in tag

    def test_endurance_gets_moderate_fuel(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('Endurance')
        assert 'MODERATE FUEL' in tag

    def test_race_sim_gets_practice_fuel(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('Race_Sim')
        assert 'PRACTICE FUEL' in tag

    def test_long_ride_gets_moderate_fuel(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('Long_Ride')
        assert 'MODERATE FUEL' in tag

    def test_recovery_gets_no_tag(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('Recovery')
        assert tag == ''

    def test_rest_gets_no_tag(self):
        from generate_athlete_package import _get_fuel_tag_for_type
        tag = _get_fuel_tag_for_type('Rest')
        assert tag == ''


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
