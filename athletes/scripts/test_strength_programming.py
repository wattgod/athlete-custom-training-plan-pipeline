"""T15 regression coverage for scheduled, equipment-aware strength work."""

import datetime
import re

import calculate_plan_dates as cpd
from generate_athlete_package import (
    generate_zwo_files,
    strength_equipment_tier,
    strength_sessions_for_week,
)
from workout_library import WorkoutLibrary


def _full_gym_profile():
    return {
        'name': 'Strength Fixture',
        'target_race': {'name': 'Strength Fixture Race', 'date': '2026-03-21',
                        'distance_miles': 60, 'discipline': 'gravel'},
        'fitness_markers': {'ftp_watts': 250, 'weight_kg': 75},
        'weekly_availability': {'cycling_hours_target': 6},
        'schedule_constraints': {'preferred_long_day': 'saturday',
                                 'preferred_off_days': ['monday']},
        'preferred_days': {
            'monday': {'availability': 'rest'},
            'tuesday': {'availability': 'available', 'is_key_day_ok': True,
                        'max_duration_min': 90},
            'wednesday': {'availability': 'available', 'is_key_day_ok': False,
                          'max_duration_min': 75},
            'thursday': {'availability': 'available', 'is_key_day_ok': True,
                         'max_duration_min': 90},
            'friday': {'availability': 'available', 'is_key_day_ok': False,
                       'max_duration_min': 75},
            'saturday': {'availability': 'available', 'is_key_day_ok': True,
                         'max_duration_min': 240},
            'sunday': {'availability': 'available', 'is_key_day_ok': True,
                       'max_duration_min': 150},
        },
        'strength': {'sessions_per_week': 2},
        'strength_equipment': ['full-gym'],
        'health_factors': {'age': 52},
    }


def _eight_week_dates(monkeypatch):
    class FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1)

    monkeypatch.setattr(cpd, 'datetime', FrozenDatetime)
    return cpd.calculate_plan_dates('2026-03-21', plan_weeks=8)


def _strength_files_by_week(files):
    by_week = {}
    for path in files:
        match = re.match(r'W(\d+)_', path.name)
        if match and '_Strength_' in path.name and '_RACE_DAY_' not in path.name:
            by_week.setdefault(int(match.group(1)), []).append(path)
    return by_week


def test_strength_frequency_reduction_rule():
    assert strength_sessions_for_week(2, 'base') == 2
    assert strength_sessions_for_week(2, 'build') == 2
    assert strength_sessions_for_week(2, 'build', is_recovery_week=True) == 1
    assert strength_sessions_for_week(2, 'taper') == 1
    assert strength_sessions_for_week(2, 'race') == 0


def test_equipment_tier_reads_both_intake_locations():
    assert strength_equipment_tier({'strength_equipment': ['full-gym']}) == 'full-gym'
    assert strength_equipment_tier(
        {'strength_preferences': {'equipment_tier': 'none'}}) == 'none'
    assert strength_equipment_tier({'strength_equipment': ['home-basic']}) == 'home-basic'


def test_full_gym_two_per_load_week_and_reduced_calendar_weeks(tmp_path, monkeypatch):
    dates = _eight_week_dates(monkeypatch)
    athlete_dir = tmp_path / 'strength-fixture'
    (athlete_dir / 'workouts').mkdir(parents=True)
    files = generate_zwo_files(
        athlete_dir, dates,
        {'methodology_id': 'polarized_80_20',
         'configuration': {'intensity_distribution': {'z2': .80, 'z4': .15, 'z5': .05}}},
        {'plan_weeks': 8, 'ability_level': 'Intermediate'}, _full_gym_profile())

    by_week = _strength_files_by_week(files)
    # Weeks 1-3 are base load, W5 is build load, W4 recovery, W7 taper,
    # and W8 race in this frozen calendar.
    assert {week: len(by_week.get(week, [])) for week in (1, 2, 3, 5)} == {
        1: 2, 2: 2, 3: 2, 5: 2}
    assert len(by_week.get(4, [])) == 1
    assert len(by_week.get(7, [])) == 1
    assert not by_week.get(8)
    assert all('_Sat_' not in path.name and '_Mon_' not in path.name
               for paths in by_week.values() for path in paths)

    full_session = by_week[5][0].read_text()
    assert '<name>Max Strength A - 45min</name>' in full_session
    assert 'Back Squat - 4x6 @ RPE7' in full_session
    assert 'Romanian Deadlift - 3x8 @ RPE7' in full_session
    assert 'leave at least 3 reps in reserve' in full_session  # masters 50+
    assert 'Jump Squat' not in full_session
    assert 'Single Leg Hop' not in full_session
    exercise_lines = re.findall(r'^- .+ - \d+x.+@ .+$', full_session, re.M)
    assert len(exercise_lines) == 4


def test_home_basic_library_remains_the_existing_rotation():
    # T15 adds tiers; it must not alter a home-basic athlete's established
    # dumbbell/bodyweight selection or its title/content.
    assert WorkoutLibrary.get_strength_workout(1, 1, equipment_tier='home-basic') == \
        WorkoutLibrary.STRENGTH_WORKOUTS[0]
    assert WorkoutLibrary.get_strength_workout(2, 2, equipment_tier='home-basic') == \
        WorkoutLibrary.STRENGTH_WORKOUTS[4]
