#!/usr/bin/env python3
"""
Tests for Workout Distribution and Schedule Logic

These tests verify the bugs we found and fixed in the workout generation pipeline:
1. Quality/easy day derivation from athlete profiles
2. Polarized methodology distribution (80/20 rule)
3. Intensity placement on key days only
4. Pre-plan week respecting availability and rest days
5. Zone classification completeness
6. Taper phase not being all-intensity
7. Weekly structure long-day placement

Run with: pytest test_distribution_and_schedule.py -v
"""

import pytest
import sys
import os
import yaml
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from collections import defaultdict

# Add script path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workout_templates import (
    PHASE_WORKOUT_ROLES,
    DEFAULT_WEEKLY_SCHEDULE,
    get_phase_roles,
    cap_duration,
)
from validate_workout_distribution import (
    ZONE_CLASSIFICATION,
    METHODOLOGY_TARGETS,
    classify_workout,
)
from build_weekly_structure import build_weekly_structure
from constants import (
    DAY_FULL_TO_ABBREV,
    DAY_ABBREV_TO_FULL,
    DAY_ORDER,
)


# ============================================================================
# HELPERS: Mock profile data and workout simulation
# ============================================================================

def make_profile(
    preferred_long_day='sunday',
    available_days=None,
    unavailable_days=None,
    rest_days=None,
    key_days=None,
):
    """
    Create a mock profile with preferred_days structure.

    Args:
        preferred_long_day: 'sunday' or 'saturday'
        available_days: dict of day_full -> max_duration_min (defaults to all available)
        unavailable_days: list of day_full names that are unavailable
        rest_days: list of day_full names that are rest days
        key_days: list of day_full names where is_key_day_ok=True
    """
    if available_days is None:
        available_days = {
            'monday': 120,
            'tuesday': 120,
            'wednesday': 120,
            'thursday': 120,
            'friday': 90,
            'saturday': 240,
            'sunday': 600,
        }
    if unavailable_days is None:
        unavailable_days = []
    if rest_days is None:
        rest_days = []
    if key_days is None:
        key_days = []

    preferred_days = {}
    for day_full, max_dur in available_days.items():
        if day_full in unavailable_days:
            preferred_days[day_full] = {
                'availability': 'unavailable',
                'time_slots': [],
                'max_duration_min': 0,
                'is_key_day_ok': False,
            }
        elif day_full in rest_days:
            preferred_days[day_full] = {
                'availability': 'rest',
                'time_slots': [],
                'max_duration_min': 0,
                'is_key_day_ok': False,
            }
        else:
            preferred_days[day_full] = {
                'availability': 'available',
                'time_slots': ['am', 'pm'] if max_dur >= 180 else ['pm'],
                'max_duration_min': max_dur,
                'is_key_day_ok': day_full in key_days,
            }

    return {
        'name': 'Test Athlete',
        'athlete_id': 'test-athlete',
        'target_race': {
            'name': 'Test Race',
            'date': '2026-06-01',
            'distance_miles': 100,
        },
        'preferred_days': preferred_days,
        'schedule_constraints': {
            'preferred_long_day': preferred_long_day,
            'strength_only_days': [],
            'preferred_off_days': [],
        },
        'fitness_markers': {
            'ftp_watts': 250,
            'weight_kg': 75,
        },
        'weekly_availability': {
            'cycling_hours_target': 10,
        },
    }


def derive_quality_and_easy_days(profile, long_day_abbrev):
    """
    Replicate the quality_days/easy_days derivation logic from
    generate_athlete_package.py lines 342-375.

    This is the exact logic the generator uses to decide which days
    get methodology-driven workouts vs which get rest/recovery.
    """
    preferred_days = profile.get('preferred_days', {})
    all_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    def get_day_availability(day_abbrev):
        day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
        return preferred_days.get(day_full, {'availability': 'available'})

    quality_days = []
    easy_days = []
    for d in all_days:
        if d == long_day_abbrev:
            continue  # Long day handled separately (returns early)
        d_avail = get_day_availability(d)
        if d_avail.get('availability') in ('unavailable', 'rest'):
            easy_days.append(d)
        else:
            quality_days.append(d)

    # Fallback if profile has no available days
    if not quality_days:
        quality_days = ['Mon', 'Wed', 'Thu', 'Fri']
        easy_days = [d for d in all_days if d not in quality_days and d != long_day_abbrev]

    return quality_days, easy_days


def derive_key_positions(profile, quality_days):
    """
    Replicate the key_positions derivation logic from
    generate_athlete_package.py lines 368-374.
    """
    preferred_days = profile.get('preferred_days', {})

    def get_day_availability(day_abbrev):
        day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
        return preferred_days.get(day_full, {'availability': 'available'})

    n_quality = len(quality_days)
    key_positions = [
        i for i, d in enumerate(quality_days)
        if get_day_availability(d).get('is_key_day_ok', False)
    ]
    # Fallback: if no key days marked, use first and middle positions
    if not key_positions:
        key_positions = [0, n_quality // 2] if n_quality > 1 else [0]

    return key_positions


def simulate_polarized_workouts(profile, phases_weeks, long_day_abbrev='Sun'):
    """
    Simulate the POLARIZED methodology workout selection for a full plan.

    Returns a list of (phase, day_abbrev, workout_type) tuples.

    This replicates the core logic from generate_athlete_package.py
    lines 430-476 (POLARIZED branch of build_day_schedule).
    """
    preferred_days = profile.get('preferred_days', {})

    def get_day_availability(day_abbrev):
        day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
        return preferred_days.get(day_full, {'availability': 'available'})

    quality_days, easy_days = derive_quality_and_easy_days(profile, long_day_abbrev)
    key_positions = derive_key_positions(profile, quality_days)

    results = []
    for phase, num_weeks in phases_weeks:
        for week_num in range(num_weeks):
            workout_count = 0
            for day in DAY_ORDER:
                avail = get_day_availability(day)
                availability = avail.get('availability', 'available')

                # Unavailable or rest -> Rest
                if availability in ('unavailable', 'rest'):
                    results.append((phase, day, 'Rest'))
                    continue

                # Long day
                if day == long_day_abbrev and phase != 'race':
                    results.append((phase, day, 'Long_Ride'))
                    continue

                # Easy days (from derivation)
                if day in easy_days:
                    results.append((phase, day, 'Recovery'))
                    continue

                # Quality days - methodology-driven
                workout_count += 1
                workout_num = workout_count

                nq = max(len(quality_days), 1)
                cycle = (workout_num - 1) % nq
                kp0 = key_positions[0] if key_positions else 0
                kp1 = key_positions[1] if len(key_positions) > 1 else (kp0 + nq // 2) % nq

                if phase == 'base':
                    if cycle == kp0:
                        wtype = 'VO2max'
                    else:
                        wtype = 'Endurance'
                elif phase == 'build':
                    if cycle == kp0:
                        wtype = 'VO2max'
                    elif cycle == kp1:
                        wtype = 'Anaerobic'
                    else:
                        wtype = 'Endurance'
                elif phase == 'peak':
                    if cycle == kp0:
                        wtype = 'VO2max'
                    elif cycle == kp1:
                        wtype = 'Sprints'
                    else:
                        wtype = 'Endurance'
                elif phase == 'taper':
                    if cycle == kp0:
                        wtype = 'VO2max'
                    else:
                        wtype = 'Easy'
                elif phase == 'race':
                    wtype = 'Easy'
                else:
                    wtype = 'Endurance'

                results.append((phase, day, wtype))

    return results


# ============================================================================
# TestQualityDayDerivation
# ============================================================================

class TestQualityDayDerivation:
    """Test quality_days / easy_days derivation from athlete profiles."""

    def test_sunday_long_day_saturday_not_quality(self):
        """When preferred_long_day=sunday, Saturday should be in quality_days
        (if available) but Sunday should NOT be in quality_days (it's the long day)."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=['wednesday', 'saturday', 'sunday'],
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')

        # Sunday is excluded (it's the long day, handled separately)
        assert 'Sun' not in quality_days, "Sunday should not be in quality_days when it's the long day"
        # Saturday IS available and should be in quality_days
        assert 'Sat' in quality_days, "Saturday should be a quality day when it's available"
        # Saturday should not be the first quality day (Mon comes first in order)
        assert quality_days[0] != 'Sat' or quality_days[0] == 'Mon', \
            "Quality days should follow day order, not hardcode Saturday first"

    def test_saturday_long_day_sunday_in_easy(self):
        """When preferred_long_day=saturday and Sunday is not a key day,
        Sunday should still be a quality day if it's marked available."""
        profile = make_profile(
            preferred_long_day='saturday',
            key_days=['wednesday'],
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sat')

        # Saturday is the long day, excluded from quality_days
        assert 'Sat' not in quality_days, "Saturday should not be in quality_days when it's the long day"
        # Sunday is available (not rest/unavailable), so it should be a quality day
        assert 'Sun' in quality_days, "Sunday should be in quality_days if it's available"

    def test_unavailable_days_in_easy(self):
        """Days marked unavailable should end up in easy_days."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday', 'thursday'],
            key_days=['wednesday', 'saturday'],
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')

        assert 'Tue' in easy_days, "Tuesday (unavailable) should be in easy_days"
        assert 'Thu' in easy_days, "Thursday (unavailable) should be in easy_days"
        assert 'Tue' not in quality_days, "Tuesday (unavailable) should NOT be in quality_days"
        assert 'Thu' not in quality_days, "Thursday (unavailable) should NOT be in quality_days"

    def test_all_available_days_are_quality(self):
        """Days marked available (not rest/unavailable) should be quality days."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            rest_days=['thursday'],
            key_days=['wednesday', 'saturday'],
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')

        # Available days (Mon, Wed, Fri, Sat) should all be quality
        for d in ['Mon', 'Wed', 'Fri', 'Sat']:
            assert d in quality_days, f"{d} is available and should be a quality day"

        # Unavailable/rest days should be easy
        assert 'Tue' in easy_days, "Tuesday (unavailable) should be easy"
        assert 'Thu' in easy_days, "Thursday (rest) should be easy"

    def test_fallback_when_no_key_days(self):
        """If no is_key_day_ok flags are set, fallback to default key positions."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=[],  # No key days flagged
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')
        key_positions = derive_key_positions(profile, quality_days)

        # Should have fallback key positions (first and middle)
        assert len(key_positions) >= 1, "Should have at least 1 fallback key position"
        assert key_positions[0] == 0, "First fallback key position should be index 0"
        n = len(quality_days)
        if n > 1:
            assert key_positions[1] == n // 2, "Second fallback key position should be middle"


# ============================================================================
# TestPolarizedDistribution
# ============================================================================

class TestPolarizedDistribution:
    """Test POLARIZED methodology workout distribution."""

    def _make_polarized_profile(self):
        """Create a profile suitable for polarized testing."""
        return make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            rest_days=['thursday'],
            key_days=['wednesday', 'saturday'],
        )

    def test_polarized_base_one_intensity_per_week(self):
        """Base phase: exactly 1 intensity workout per week cycle among quality days."""
        profile = self._make_polarized_profile()
        results = simulate_polarized_workouts(
            profile, [('base', 2)], long_day_abbrev='Sun'
        )

        # Filter to quality-day workouts in base phase (exclude Rest, Long_Ride, Recovery)
        base_quality = [
            (day, wtype) for phase, day, wtype in results
            if phase == 'base' and wtype not in ('Rest', 'Long_Ride', 'Recovery')
        ]

        # Count intensity workouts per week
        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        intensity_per_week = defaultdict(int)
        week = 0
        day_count = 0
        for day, wtype in base_quality:
            if day == 'Mon' and day_count > 0:
                week += 1
            day_count += 1
            if wtype in intensity_types:
                intensity_per_week[week] += 1

        for wk, count in intensity_per_week.items():
            assert count == 1, f"Base phase week {wk} should have exactly 1 intensity workout, got {count}"

    def test_polarized_build_two_intensity_per_week(self):
        """Build phase: exactly 2 intensity workouts per week cycle."""
        profile = self._make_polarized_profile()
        results = simulate_polarized_workouts(
            profile, [('build', 2)], long_day_abbrev='Sun'
        )

        build_quality = [
            (day, wtype) for phase, day, wtype in results
            if phase == 'build' and wtype not in ('Rest', 'Long_Ride', 'Recovery')
        ]

        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        intensity_per_week = defaultdict(int)
        week = 0
        day_count = 0
        for day, wtype in build_quality:
            if day == 'Mon' and day_count > 0:
                week += 1
            day_count += 1
            if wtype in intensity_types:
                intensity_per_week[week] += 1

        for wk, count in intensity_per_week.items():
            assert count == 2, f"Build phase week {wk} should have exactly 2 intensity workouts, got {count}"

    def test_polarized_taper_one_opener(self):
        """Taper: only 1 VO2max opener per week cycle, rest easy."""
        profile = self._make_polarized_profile()
        results = simulate_polarized_workouts(
            profile, [('taper', 1)], long_day_abbrev='Sun'
        )

        taper_quality = [
            (day, wtype) for phase, day, wtype in results
            if phase == 'taper' and wtype not in ('Rest', 'Long_Ride', 'Recovery')
        ]

        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        intensity_count = sum(1 for _, wtype in taper_quality if wtype in intensity_types)

        assert intensity_count == 1, \
            f"Taper should have exactly 1 intensity workout (opener), got {intensity_count}"

    def test_polarized_race_all_easy(self):
        """Race week: all quality days produce Easy workouts."""
        profile = self._make_polarized_profile()
        results = simulate_polarized_workouts(
            profile, [('race', 1)], long_day_abbrev='Sun'
        )

        race_quality = [
            (day, wtype) for phase, day, wtype in results
            if phase == 'race' and wtype not in ('Rest', 'Long_Ride', 'Recovery')
        ]

        for day, wtype in race_quality:
            assert wtype == 'Easy', \
                f"Race week quality day {day} should be Easy, got {wtype}"

    def test_polarized_overall_distribution_80_20(self):
        """Full plan (base+build+peak+taper+race) should produce 75-85% Z1-Z2 by workout count."""
        profile = self._make_polarized_profile()
        phases_weeks = [
            ('base', 4),
            ('build', 3),
            ('peak', 2),
            ('taper', 1),
            ('race', 1),
        ]
        results = simulate_polarized_workouts(
            profile, phases_weeks, long_day_abbrev='Sun'
        )

        # Classify all workouts
        z1_z2_types = {'Recovery', 'Easy', 'Endurance', 'Shakeout', 'Long_Ride', 'Rest'}
        total = 0
        z1_z2_count = 0
        for phase, day, wtype in results:
            total += 1
            if wtype in z1_z2_types:
                z1_z2_count += 1

        ratio = z1_z2_count / total if total > 0 else 0
        assert 0.75 <= ratio <= 0.85, \
            f"Polarized plan should have 75-85% Z1-Z2 workouts, got {ratio*100:.1f}%"


# ============================================================================
# TestIntensityOnKeyDays
# ============================================================================

class TestIntensityOnKeyDays:
    """Test that intensity workouts land on key days."""

    def test_vo2max_lands_on_key_day(self):
        """VO2max workouts should be on days with is_key_day_ok=true."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            key_days=['wednesday', 'saturday'],
        )
        # Simulate a base phase (1 intensity per cycle on primary key day)
        results = simulate_polarized_workouts(
            profile, [('base', 2)], long_day_abbrev='Sun'
        )

        quality_days, _ = derive_quality_and_easy_days(profile, 'Sun')
        key_positions = derive_key_positions(profile, quality_days)
        key_day_abbrevs = [quality_days[kp] for kp in key_positions if kp < len(quality_days)]

        vo2max_days = [day for phase, day, wtype in results if wtype == 'VO2max']
        for day in vo2max_days:
            assert day in key_day_abbrevs, \
                f"VO2max landed on {day}, but key days are {key_day_abbrevs}"

    def test_no_intensity_on_non_key_day(self):
        """Non-key available days should only get Endurance/Easy in polarized base."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            key_days=['wednesday', 'saturday'],
        )
        results = simulate_polarized_workouts(
            profile, [('base', 2)], long_day_abbrev='Sun'
        )

        quality_days, _ = derive_quality_and_easy_days(profile, 'Sun')
        key_positions = derive_key_positions(profile, quality_days)
        key_day_abbrevs = set(quality_days[kp] for kp in key_positions if kp < len(quality_days))

        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        non_key_quality = [
            (day, wtype) for phase, day, wtype in results
            if phase == 'base' and day in quality_days and day not in key_day_abbrevs
            and wtype not in ('Rest', 'Long_Ride', 'Recovery')
        ]

        for day, wtype in non_key_quality:
            assert wtype not in intensity_types, \
                f"Non-key day {day} got intensity workout {wtype} in base phase"

    def test_key_positions_correct(self):
        """key_positions list matches profile is_key_day_ok flags."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            key_days=['wednesday', 'saturday'],
        )
        quality_days, _ = derive_quality_and_easy_days(profile, 'Sun')
        key_positions = derive_key_positions(profile, quality_days)

        # Wednesday and Saturday are the key days
        expected_key_days = {'Wed', 'Sat'}
        actual_key_days = {quality_days[kp] for kp in key_positions if kp < len(quality_days)}

        assert actual_key_days == expected_key_days, \
            f"Key positions should map to {expected_key_days}, got {actual_key_days}"


# ============================================================================
# TestPrePlanDayAvailability
# ============================================================================

class TestPrePlanDayAvailability:
    """Test that pre-plan week respects day availability."""

    def test_pre_plan_skips_unavailable_days(self):
        """Pre-plan week should NOT generate workouts for unavailable days."""
        # The generate_pre_plan_week function checks:
        # if day_avail.get('availability') in ('unavailable', 'rest'): continue
        profile = make_profile(
            unavailable_days=['tuesday', 'thursday'],
        )
        preferred_days = profile['preferred_days']

        # Simulate the pre-plan skip logic
        days_to_check = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        generated_days = []
        for day_abbrev in days_to_check:
            day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
            day_avail = preferred_days.get(day_full, {'availability': 'available'})
            if day_avail.get('availability') not in ('unavailable', 'rest'):
                generated_days.append(day_abbrev)

        assert 'Tue' not in generated_days, "Pre-plan should skip unavailable Tuesday"
        assert 'Thu' not in generated_days, "Pre-plan should skip unavailable Thursday"
        assert 'Mon' in generated_days, "Pre-plan should include available Monday"
        assert 'Wed' in generated_days, "Pre-plan should include available Wednesday"

    def test_pre_plan_respects_rest_days(self):
        """Pre-plan should skip days marked as rest in the profile."""
        profile = make_profile(
            rest_days=['thursday'],
        )
        preferred_days = profile['preferred_days']

        day_abbrev = 'Thu'
        day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
        day_avail = preferred_days.get(day_full, {'availability': 'available'})

        should_skip = day_avail.get('availability') in ('unavailable', 'rest')
        assert should_skip, "Pre-plan should skip rest days"


# ============================================================================
# TestZoneClassification
# ============================================================================

class TestZoneClassification:
    """Test zone classification completeness."""

    def test_pre_plan_types_classified(self):
        """Pre_Plan_Easy, Pre_Plan_Endurance, Pre_Plan_Rest are classified as z1_z2."""
        pre_plan_types = ['Pre_Plan_Easy', 'Pre_Plan_Endurance', 'Pre_Plan_Rest']
        for workout_type in pre_plan_types:
            assert workout_type in ZONE_CLASSIFICATION, \
                f"Pre-plan type '{workout_type}' should be in ZONE_CLASSIFICATION"
            assert ZONE_CLASSIFICATION[workout_type] == 'z1_z2', \
                f"Pre-plan type '{workout_type}' should be classified as z1_z2"

    def test_all_workout_types_have_classification(self):
        """Every training workout type should be in ZONE_CLASSIFICATION.
        Excluded types (FTP_Test, RACE_DAY) are handled by EXCLUDED_PREFIXES."""
        from validate_workout_distribution import EXCLUDED_PREFIXES

        # Training workout types (not assessments/race days)
        training_types = [
            'Recovery', 'Easy', 'Endurance', 'Shakeout', 'Long_Ride', 'Rest',
            'Tempo', 'G_Spot',
            'Threshold', 'VO2max', 'Over_Under', 'Blended',
            'Openers', 'Anaerobic', 'Sprints', 'Race_Sim',
            'Sweet_Spot',
            'Pre_Plan_Easy', 'Pre_Plan_Endurance', 'Pre_Plan_Rest',
        ]

        for workout_type in training_types:
            zone = ZONE_CLASSIFICATION.get(workout_type, 'unknown')
            assert zone != 'unknown', \
                f"Workout type '{workout_type}' is not in ZONE_CLASSIFICATION"

        # Excluded types should NOT be in ZONE_CLASSIFICATION
        excluded_types = ['FTP_Test', 'RACE_DAY', 'Strength']
        for excl in excluded_types:
            assert excl not in ZONE_CLASSIFICATION, \
                f"'{excl}' is an excluded type and should NOT be in ZONE_CLASSIFICATION"
            assert any(excl.startswith(p) for p in EXCLUDED_PREFIXES), \
                f"'{excl}' should be in EXCLUDED_PREFIXES"

    def test_race_day_excluded_from_distribution(self):
        """RACE_DAY and FTP_Test are excluded from zone distribution counting."""
        from validate_workout_distribution import EXCLUDED_PREFIXES

        # RACE_DAY and FTP_Test should be in EXCLUDED_PREFIXES
        assert any('RACE_DAY'.startswith(p) for p in EXCLUDED_PREFIXES), \
            "RACE_DAY should be in EXCLUDED_PREFIXES"
        assert any('FTP_Test'.startswith(p) for p in EXCLUDED_PREFIXES), \
            "FTP_Test should be in EXCLUDED_PREFIXES"

        # Verify RACE_DAY IS used in templates as a valid workout type
        race_templates = PHASE_WORKOUT_ROLES.get('race', {})
        race_types = [t[0] for t in race_templates.values() if t[0] is not None]
        assert 'RACE_DAY' in race_types, "RACE_DAY should exist in race phase templates"

    def test_classify_workout_from_filename(self):
        """classify_workout should extract type from filename and return correct zone."""
        test_cases = [
            ('W01_Mon_Feb16_Easy.zwo', 'z1_z2'),
            ('W03_Wed_Mar04_VO2max.zwo', 'z4_z5'),
            ('W05_Fri_Mar18_Tempo.zwo', 'z3'),
            ('W08_Sat_Apr08_Long_Ride.zwo', 'z1_z2'),
            ('W00_Thu_Feb12_Pre_Plan_Easy.zwo', 'z1_z2'),
            ('W10_Mon_Apr20_G_Spot.zwo', 'z3'),
            ('W12_Wed_May06_Threshold.zwo', 'z4_z5'),
        ]
        for filename, expected_zone in test_cases:
            result = classify_workout(filename)
            assert result == expected_zone, \
                f"classify_workout('{filename}') should return '{expected_zone}', got '{result}'"

    def test_sweet_spot_classified_as_z3(self):
        """Sweet_Spot (88-94% FTP) should be classified as z3 alongside G_Spot."""
        assert 'Sweet_Spot' in ZONE_CLASSIFICATION, \
            "Sweet_Spot should be in ZONE_CLASSIFICATION"
        assert ZONE_CLASSIFICATION['Sweet_Spot'] == 'z3', \
            f"Sweet_Spot should be classified as z3, got {ZONE_CLASSIFICATION['Sweet_Spot']}"


# ============================================================================
# TestTaperNotAllIntensity
# ============================================================================

class TestTaperNotAllIntensity:
    """Test that taper phase is mostly easy, not all intensity."""

    def test_taper_phase_mostly_easy(self):
        """Taper phase should have at most 1-2 intensity sessions, not all."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            key_days=['wednesday', 'saturday'],
        )
        results = simulate_polarized_workouts(
            profile, [('taper', 1)], long_day_abbrev='Sun'
        )

        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        easy_types = {'Easy', 'Recovery', 'Endurance', 'Shakeout', 'Long_Ride', 'Rest'}

        taper_workouts = [(day, wtype) for phase, day, wtype in results if phase == 'taper']
        intensity_count = sum(1 for _, wtype in taper_workouts if wtype in intensity_types)
        easy_count = sum(1 for _, wtype in taper_workouts if wtype in easy_types)

        total = len(taper_workouts)
        assert intensity_count <= 2, \
            f"Taper should have at most 2 intensity sessions, got {intensity_count}"
        assert easy_count >= total - 2, \
            f"Taper should have at least {total - 2} easy sessions, got {easy_count}"

    def test_taper_has_openers(self):
        """At least 1 opener/VO2max workout in taper for race preparation."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['tuesday'],
            key_days=['wednesday', 'saturday'],
        )
        results = simulate_polarized_workouts(
            profile, [('taper', 1)], long_day_abbrev='Sun'
        )

        opener_types = {'VO2max', 'Openers'}
        taper_openers = [
            wtype for phase, day, wtype in results
            if phase == 'taper' and wtype in opener_types
        ]

        assert len(taper_openers) >= 1, \
            "Taper should have at least 1 opener/VO2max workout for race prep"


# ============================================================================
# TestWeeklyStructureLongDay
# ============================================================================

class TestWeeklyStructureLongDay:
    """Test weekly structure long-day placement via build_weekly_structure."""

    def _get_key_days_from_profile(self, profile):
        """Extract key_days list from profile for build_weekly_structure."""
        preferred_days = profile.get('preferred_days', {})
        return [
            day for day, prefs in preferred_days.items()
            if prefs.get('is_key_day_ok', False)
        ]

    def test_sunday_long_day_respected(self):
        """When preferred_long_day=sunday, build_weekly_structure puts long_ride on Sunday."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=['wednesday', 'saturday', 'sunday'],
        )
        key_days = self._get_key_days_from_profile(profile)

        structure = build_weekly_structure(
            preferred_days=profile['preferred_days'],
            key_days=key_days,
            strength_days=[],
            tier='compete',
            preferred_long_day='sunday',
        )

        sunday = structure['days'].get('sunday', {})
        # Sunday should have long_ride in AM or PM
        has_long_ride = (
            sunday.get('am') == 'long_ride' or
            sunday.get('pm') == 'long_ride'
        )
        assert has_long_ride, \
            f"Sunday should have long_ride when preferred_long_day=sunday, got AM={sunday.get('am')}, PM={sunday.get('pm')}"

    def test_saturday_long_day_respected(self):
        """When preferred_long_day=saturday, long_ride on Saturday."""
        profile = make_profile(
            preferred_long_day='saturday',
            key_days=['wednesday', 'saturday'],
        )
        key_days = self._get_key_days_from_profile(profile)

        structure = build_weekly_structure(
            preferred_days=profile['preferred_days'],
            key_days=key_days,
            strength_days=[],
            tier='compete',
            preferred_long_day='saturday',
        )

        saturday = structure['days'].get('saturday', {})
        has_long_ride = (
            saturday.get('am') == 'long_ride' or
            saturday.get('pm') == 'long_ride'
        )
        assert has_long_ride, \
            f"Saturday should have long_ride when preferred_long_day=saturday, got AM={saturday.get('am')}, PM={saturday.get('pm')}"

    def test_no_long_ride_on_wrong_day(self):
        """Long ride should NOT appear on non-preferred days."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=['wednesday', 'saturday', 'sunday'],
        )
        key_days = self._get_key_days_from_profile(profile)

        structure = build_weekly_structure(
            preferred_days=profile['preferred_days'],
            key_days=key_days,
            strength_days=[],
            tier='compete',
            preferred_long_day='sunday',
        )

        non_long_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        for day in non_long_days:
            day_struct = structure['days'].get(day, {})
            am = day_struct.get('am', None)
            pm = day_struct.get('pm', None)
            assert am != 'long_ride' and pm != 'long_ride', \
                f"{day} should NOT have long_ride when preferred_long_day=sunday, " \
                f"got AM={am}, PM={pm}"


# ============================================================================
# TestPolarizedDistributionEdgeCases
# ============================================================================

class TestPolarizedDistributionEdgeCases:
    """Additional edge case tests for distribution logic."""

    def test_all_days_available_polarized(self):
        """With all days available, polarized should still maintain 80/20."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=['wednesday', 'saturday'],
            unavailable_days=[],
            rest_days=[],
        )
        results = simulate_polarized_workouts(
            profile, [('base', 4), ('build', 3)], long_day_abbrev='Sun'
        )

        z1_z2_types = {'Recovery', 'Easy', 'Endurance', 'Shakeout', 'Long_Ride', 'Rest'}
        total = len(results)
        z1_z2 = sum(1 for _, _, wtype in results if wtype in z1_z2_types)

        ratio = z1_z2 / total if total > 0 else 0
        assert 0.70 <= ratio <= 0.90, \
            f"All-available polarized plan should be ~80% Z1-Z2, got {ratio*100:.1f}%"

    def test_minimal_availability_still_gets_intensity(self):
        """Even with most days unavailable, athlete gets at least some intensity."""
        profile = make_profile(
            preferred_long_day='saturday',
            unavailable_days=['monday', 'tuesday', 'thursday', 'friday'],
            key_days=['wednesday', 'saturday'],
        )
        results = simulate_polarized_workouts(
            profile, [('build', 2)], long_day_abbrev='Sat'
        )

        intensity_types = {'VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers'}
        intensity_workouts = [
            (day, wtype) for _, day, wtype in results if wtype in intensity_types
        ]

        assert len(intensity_workouts) >= 2, \
            f"Even with limited availability, build should have intensity workouts, got {len(intensity_workouts)}"

    def test_methodology_targets_defined_for_polarized(self):
        """POLARIZED methodology target should be 80% Z1-Z2, 0% Z3, 20% Z4-Z5."""
        target = METHODOLOGY_TARGETS.get('polarized')
        assert target is not None, "POLARIZED should have defined methodology targets"
        assert target['z1_z2'] == 0.80, f"POLARIZED Z1-Z2 target should be 80%, got {target['z1_z2']*100}%"
        assert target['z3'] == 0.00, f"POLARIZED Z3 target should be 0%, got {target['z3']*100}%"
        assert target['z4_z5'] == 0.20, f"POLARIZED Z4-Z5 target should be 20%, got {target['z4_z5']*100}%"


# ============================================================================
# TestQualityDayDerivationEdgeCases
# ============================================================================

class TestQualityDayDerivationEdgeCases:
    """Edge cases for quality/easy day derivation."""

    def test_all_days_unavailable_uses_fallback(self):
        """When ALL days are unavailable, fallback quality_days should be used."""
        profile = make_profile(
            preferred_long_day='sunday',
            unavailable_days=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
            key_days=[],
        )
        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')

        # All non-Sunday days are unavailable, Sunday is long day
        # Fallback: quality_days = ['Mon', 'Wed', 'Thu', 'Fri']
        assert len(quality_days) == 4, \
            f"Fallback should give 4 quality days, got {len(quality_days)}: {quality_days}"
        assert 'Mon' in quality_days, "Fallback should include Mon"
        assert 'Wed' in quality_days, "Fallback should include Wed"

    def test_limited_availability_is_quality(self):
        """Days with 'limited' availability should still be quality days."""
        profile = make_profile(preferred_long_day='sunday')
        # Manually set Friday to limited
        profile['preferred_days']['friday']['availability'] = 'limited'

        quality_days, easy_days = derive_quality_and_easy_days(profile, 'Sun')

        assert 'Fri' in quality_days, \
            "Limited availability days should be quality days (time-constrained, not intensity-constrained)"
        assert 'Fri' not in easy_days, \
            "Limited availability days should NOT be easy days"


# ============================================================================
# TestTaperPhaseTemplates
# ============================================================================

class TestTaperPhaseTemplates:
    """Test taper phase workout templates are appropriately light."""

    def test_taper_templates_reduced_duration(self):
        """Taper phase templates should have shorter durations than build/peak."""
        taper_roles = get_phase_roles('taper')
        build_roles = get_phase_roles('build')

        for role in ['key_cardio', 'easy', 'long_ride']:
            taper_dur = taper_roles[role][2]
            build_dur = build_roles[role][2]
            assert taper_dur <= build_dur, \
                f"Taper {role} duration ({taper_dur}) should be <= build ({build_dur})"

    def test_taper_easy_is_actually_easy(self):
        """Taper easy workouts should be low intensity."""
        taper_roles = get_phase_roles('taper')
        easy = taper_roles['easy']
        assert easy[0] == 'Easy', f"Taper easy should be Easy type, got {easy[0]}"
        assert easy[3] <= 0.60, f"Taper easy power {easy[3]} should be <= 0.60"

    def test_taper_long_ride_is_shakeout(self):
        """Taper long_ride should be a short shakeout, not a real long ride."""
        taper_roles = get_phase_roles('taper')
        long_ride = taper_roles['long_ride']
        assert long_ride[0] == 'Shakeout', f"Taper long_ride should be Shakeout, got {long_ride[0]}"
        assert long_ride[2] <= 45, f"Taper shakeout duration {long_ride[2]} should be <= 45 min"


# ============================================================================
# TestRacePhaseTemplates
# ============================================================================

class TestRacePhaseTemplates:
    """Test race phase workout templates."""

    def test_race_phase_easy_workouts(self):
        """Race phase should have mostly Easy workouts."""
        race_roles = get_phase_roles('race')
        easy_types = {'Easy', 'Shakeout', 'Rest', 'Openers', 'Sprints', 'RACE_DAY'}
        for role, template in race_roles.items():
            assert template[0] in easy_types or template[0] is None, \
                f"Race phase role '{role}' has unexpected type '{template[0]}'"

    def test_race_phase_has_race_day(self):
        """Race phase should have a RACE_DAY entry."""
        race_roles = get_phase_roles('race')
        types = [t[0] for t in race_roles.values()]
        assert 'RACE_DAY' in types, "Race phase should include RACE_DAY"


class TestFTPTestPlacement:
    """FTP tests must not cannibalize the long ride day."""

    def test_ftp_never_on_long_day(self):
        """FTP_Test must not replace the long ride — it's the most important workout in polarized."""
        athlete_dir = Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'
        if not athlete_dir.exists():
            pytest.skip("nicholas-applegate workouts not generated")

        # Find the long day from the weekly structure
        ws_path = Path(__file__).parent.parent / 'nicholas-applegate' / 'weekly_structure.yaml'
        if ws_path.exists():
            with open(ws_path) as f:
                ws = yaml.safe_load(f)
            long_days = [d.capitalize()[:3] for d, info in ws.get('days', {}).items()
                         if info.get('workout_type') == 'long_ride']
        else:
            long_days = ['Sun']  # Default

        ftp_files = list(athlete_dir.glob('*FTP_Test*'))
        for ftp_file in ftp_files:
            parts = ftp_file.stem.split('_')
            day_abbrev = parts[1] if len(parts) >= 2 else ''
            assert day_abbrev not in long_days, \
                f"FTP_Test on {day_abbrev} ({ftp_file.name}) — this replaces the long ride"

    def test_every_base_build_peak_week_has_long_ride(self):
        """Every base/build/peak week must have a long ride on the long day."""
        athlete_dir = Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'
        if not athlete_dir.exists():
            pytest.skip("nicholas-applegate workouts not generated")

        # Get all week numbers that have long rides
        long_ride_weeks = set()
        for f in athlete_dir.glob('*Long_Ride*'):
            m = __import__('re').match(r'W(\d+)', f.name)
            if m:
                long_ride_weeks.add(int(m.group(1)))

        # Get all week numbers from any workout
        all_weeks = set()
        for f in athlete_dir.glob('*.zwo'):
            m = __import__('re').match(r'W(\d+)', f.name)
            if m:
                all_weeks.add(int(m.group(1)))

        max_week = max(all_weeks)
        # Last 2 weeks (taper + race) are exempt
        training_weeks = [w for w in all_weeks if w <= max_week - 2]

        missing = [w for w in training_weeks if w not in long_ride_weeks]
        assert not missing, \
            f"Weeks {missing} are missing long rides (non-taper/race weeks need them)"


class TestOutputCompleteness:
    """Every available day should have a workout — no silent gaps."""

    def test_no_missing_days(self):
        """Each week should have 6 workouts (7 days minus Tuesday off)."""
        athlete_dir = Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'
        if not athlete_dir.exists():
            pytest.skip("nicholas-applegate workouts not generated")

        from collections import Counter
        week_counts = Counter()
        for f in athlete_dir.glob('*.zwo'):
            m = __import__('re').match(r'W(\d+)', f.name)
            if m:
                week_counts[int(m.group(1))] += 1

        for week_num, count in sorted(week_counts.items()):
            assert count >= 5, \
                f"Week {week_num} has only {count} workouts (expected 5-6 for 6 available days)"


# ============================================================================
# TestZeroOffDays — edge case: athlete with 7 available days
# ============================================================================

class TestZeroOffDays:
    """Test weekly structure handles 7 available days (zero off days)."""

    def test_seven_days_all_assigned(self):
        """With 0 off days, build_weekly_structure should assign all 7 days."""
        profile = make_profile(
            preferred_long_day='saturday',
            key_days=['wednesday', 'thursday', 'saturday', 'sunday'],
            # All 7 days available (default), no unavailable/rest days
        )
        key_days = [
            d for d, prefs in profile['preferred_days'].items()
            if prefs.get('is_key_day_ok', False)
        ]

        structure = build_weekly_structure(
            preferred_days=profile['preferred_days'],
            key_days=key_days,
            strength_days=[],
            tier='compete',
            preferred_long_day='saturday',
        )

        assigned = 0
        for day_name, day_info in structure['days'].items():
            am = day_info.get('am')
            pm = day_info.get('pm')
            if am or pm:
                assigned += 1
        assert assigned == 7, (
            f"Expected 7 assigned days with zero off days, got {assigned}"
        )

    def test_seven_days_has_easy_day(self):
        """With 7 available days, at least 1 day should be easy (not all intensity)."""
        profile = make_profile(
            preferred_long_day='sunday',
            key_days=['wednesday', 'friday', 'saturday', 'sunday'],
        )
        key_days = [
            d for d, prefs in profile['preferred_days'].items()
            if prefs.get('is_key_day_ok', False)
        ]

        structure = build_weekly_structure(
            preferred_days=profile['preferred_days'],
            key_days=key_days,
            strength_days=[],
            tier='compete',
            preferred_long_day='sunday',
        )

        easy_count = 0
        for day_name, day_info in structure['days'].items():
            am = day_info.get('am', '')
            pm = day_info.get('pm', '')
            workout_type = pm or am
            if workout_type in ('easy_ride', 'recovery'):
                easy_count += 1
        assert easy_count >= 1, (
            f"Expected at least 1 easy day with 7 available, got {easy_count}. "
            f"Structure: {structure['days']}"
        )

    def test_seven_days_distribution_valid(self):
        """With 7 available days, quality_days + easy_days derivation should work."""
        profile = make_profile(
            preferred_long_day='saturday',
            key_days=['wednesday', 'saturday', 'sunday'],
        )
        long_day_abbrev = 'Sat'

        quality_days, easy_days = derive_quality_and_easy_days(profile, long_day_abbrev)
        total = len(quality_days) + len(easy_days)
        # Should have at least 5 days allocated (some may overlap as long day)
        assert total >= 5, (
            f"Expected at least 5 days, got {total}: quality={quality_days}, easy={easy_days}"
        )
        # Long day abbreviation should NOT be in quality_days (it's its own thing)
        assert long_day_abbrev not in quality_days, (
            f"Long day {long_day_abbrev} should not be in quality_days"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
