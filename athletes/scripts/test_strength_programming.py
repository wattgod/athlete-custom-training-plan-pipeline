"""T15 regression coverage for scheduled, equipment-aware strength work."""

import datetime
import json
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

    # FIX 2 (Aug 17 2026 adversarial grade): the label ("Max Strength A/B")
    # and the exercise content family must derive from the SAME phase-wide
    # ordinal. W4's single recovery-week session consumes phase-wide
    # ordinal 0 in the 'build' phase, so W5's first (chronologically
    # earliest) session is ordinal 1 -- "B", deadlift-family -- and its
    # second session is ordinal 2 -- "A", squat-family. Content now matches
    # title in both cases; previously the ZWO's own <name> always said "A"
    # for a week's first session regardless of this carried-over parity.
    full_session = by_week[5][0].read_text()
    assert '<name>Max Strength B - 45min</name>' in full_session
    assert 'Trap Bar Deadlift - 4x5 @ RPE7' in full_session
    assert 'Bulgarian Split Squat - 3x6 each @ RPE7' in full_session
    assert 'leave at least 3 reps in reserve' in full_session  # masters 50+
    assert 'Jump Squat' not in full_session
    assert 'Single Leg Hop' not in full_session
    exercise_lines = re.findall(r'^- .+ - \d+x.+@ .+$', full_session, re.M)
    assert len(exercise_lines) == 4

    second_session = by_week[5][1].read_text()
    assert '<name>Max Strength A - 45min</name>' in second_session
    assert 'Back Squat - 4x6 @ RPE7' in second_session
    assert 'Romanian Deadlift - 3x8 @ RPE7' in second_session


def test_strength_title_letter_matches_exercise_family_across_2_1_2_weeks(tmp_path, monkeypatch):
    # FIX 2 (Aug 17 2026 adversarial grade) regression: force 3 consecutive
    # weeks in the SAME phase with a load/recovery/load (2/1/2)
    # strength-session pattern -- the shape that surfaces the desync,
    # since a recovery week's single session shifts the phase-wide parity
    # for every session placed after it within that phase. Assert every
    # emitted card's delivered title letter (naming_manifest's
    # strength_template, which is what the athlete's calendar shows)
    # matches its own baked-in exercise family.
    dates = _eight_week_dates(monkeypatch)
    for i in range(3):
        dates['weeks'][i]['phase'] = 'build'
    dates['weeks'][0]['is_recovery_week'] = False
    dates['weeks'][1]['is_recovery_week'] = True
    dates['weeks'][2]['is_recovery_week'] = False

    athlete_dir = tmp_path / 'strength-fixture-212'
    (athlete_dir / 'workouts').mkdir(parents=True)
    generate_zwo_files(
        athlete_dir, dates,
        {'methodology_id': 'polarized_80_20',
         'configuration': {'intensity_distribution': {'z2': .80, 'z4': .15, 'z5': .05}}},
        {'plan_weeks': 8, 'ability_level': 'Intermediate'}, _full_gym_profile())

    workouts_dir = athlete_dir / 'workouts'
    manifest = json.loads((workouts_dir / 'naming_manifest.json').read_text())
    strength_recs = {
        stem: rec for stem, rec in manifest.items()
        if rec.get('tp_kind') == 'strength' and rec.get('week_num') in (1, 2, 3)
    }
    assert len(strength_recs) == 5  # 2 + 1 + 2

    for stem, rec in strength_recs.items():
        content = (workouts_dir / f"{stem}.zwo").read_text()
        label = rec['strength_template']  # e.g. 'max_strength_a'
        letter = label.rsplit('_', 1)[-1]
        has_squat_family = 'Back Squat' in content
        has_deadlift_family = 'Trap Bar Deadlift' in content
        assert has_squat_family != has_deadlift_family, f"{stem}: ambiguous family"
        assert (letter == 'a') == has_squat_family, (
            f"{stem}: title says {label!r} but content is "
            f"{'squat' if has_squat_family else 'deadlift'}-family")


def test_home_basic_library_remains_the_existing_rotation():
    # T15 adds tiers; it must not alter a home-basic athlete's established
    # dumbbell/bodyweight selection or its title/content.
    assert WorkoutLibrary.get_strength_workout(1, 1, equipment_tier='home-basic') == \
        WorkoutLibrary.STRENGTH_WORKOUTS[0]
    assert WorkoutLibrary.get_strength_workout(2, 2, equipment_tier='home-basic') == \
        WorkoutLibrary.STRENGTH_WORKOUTS[4]
