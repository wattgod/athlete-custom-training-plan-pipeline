#!/usr/bin/env python3
"""
Regression tests for plan date calculations.

All race dates are computed RELATIVE TO TODAY (a Sunday ~45 weeks out).
The original suite hardcoded June 2026 dates; once the calendar caught up,
calculate_plan_dates clamped the plans ("race too soon") and six tests
failed on date drift instead of real regressions. Never hardcode dates here.

Run with: python3 test_plan_dates.py
"""

import sys
from datetime import datetime, timedelta
from calculate_plan_dates import calculate_plan_dates, validate_plan_dates, PlanDateValidationError


def _next_sunday(weeks_out: int = 45) -> datetime:
    """A Sunday far enough out that no plan length gets clamped."""
    d = datetime.now() + timedelta(weeks=weeks_out)
    return d + timedelta(days=(6 - d.weekday()) % 7)


RACE_DT = _next_sunday()
RACE_DATE = RACE_DT.strftime('%Y-%m-%d')


def _iso(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d')


def test_basic_calculation():
    """Test basic plan date calculation."""
    print("\n📋 Test: Basic Calculation")

    plan_weeks = 12
    result = calculate_plan_dates(RACE_DATE, plan_weeks)

    # Assertions
    assert result['race_date'] == RACE_DATE, f"Race date mismatch: {result['race_date']}"
    assert result['race_weekday'] == 'Sunday', f"Race weekday wrong: {result['race_weekday']}"
    assert result['plan_weeks'] == 12, f"Plan weeks wrong: {result['plan_weeks']}"
    assert len(result['weeks']) == 12, f"Weeks list wrong length: {len(result['weeks'])}"

    # Race week must contain race date
    race_week = result['weeks'][-1]
    assert race_week['is_race_week'] == True, "Final week must be race week"
    race_week_monday = datetime.strptime(race_week['monday'], '%Y-%m-%d')
    race_week_sunday = datetime.strptime(race_week['sunday'], '%Y-%m-%d')
    race_dt = datetime.strptime(RACE_DATE, '%Y-%m-%d')
    assert race_week_monday <= race_dt <= race_week_sunday, "Race date not in race week"

    print("  ✓ PASSED")


def test_race_on_different_weekdays():
    """Test races on different days of the week."""
    print("\n📋 Test: Race on Different Weekdays")

    test_cases = [
        (_iso(RACE_DT), "Sunday"),
        (_iso(RACE_DT - timedelta(days=1)), "Saturday"),
        (_iso(RACE_DT - timedelta(days=6)), "Monday"),
        (_iso(RACE_DT - timedelta(days=4)), "Wednesday"),
    ]

    for race_date, expected_day in test_cases:
        result = calculate_plan_dates(race_date, 12)

        assert result['race_weekday'] == expected_day, \
            f"Weekday wrong for {race_date}: expected {expected_day}, got {result['race_weekday']}"

        # Race must be in final week
        race_week = result['weeks'][-1]
        race_dt = datetime.strptime(race_date, '%Y-%m-%d')
        race_week_monday = datetime.strptime(race_week['monday'], '%Y-%m-%d')
        race_week_sunday = datetime.strptime(race_week['sunday'], '%Y-%m-%d')

        assert race_week_monday <= race_dt <= race_week_sunday, \
            f"Race {race_date} not in race week {race_week['monday']}-{race_week['sunday']}"

        print(f"  ✓ {expected_day} race ({race_date}) - race week correct")

    print("  ✓ PASSED")


def test_week_continuity():
    """Test that weeks are continuous with no gaps."""
    print("\n📋 Test: Week Continuity")

    result = calculate_plan_dates(RACE_DATE, 19)

    for i in range(1, len(result['weeks'])):
        prev_week = result['weeks'][i-1]
        curr_week = result['weeks'][i]

        prev_sunday = datetime.strptime(prev_week['sunday'], '%Y-%m-%d')
        curr_monday = datetime.strptime(curr_week['monday'], '%Y-%m-%d')

        gap = (curr_monday - prev_sunday).days
        assert gap == 1, f"Gap between W{i} and W{i+1}: {gap} days (should be 1)"

    print(f"  ✓ All {len(result['weeks'])} weeks are continuous")
    print("  ✓ PASSED")


def test_week_numbering():
    """Test that week numbers are sequential starting at 1."""
    print("\n📋 Test: Week Numbering")

    result = calculate_plan_dates(RACE_DATE, 19)

    for i, week in enumerate(result['weeks']):
        expected_num = i + 1
        assert week['week'] == expected_num, \
            f"Week number wrong at index {i}: expected {expected_num}, got {week['week']}"

    print(f"  ✓ Week numbers 1-{len(result['weeks'])} sequential")
    print("  ✓ PASSED")


def test_workout_naming_format():
    """Test workout naming includes date."""
    print("\n📋 Test: Workout Naming Format")

    result = calculate_plan_dates(RACE_DATE, 12)

    # Check first week has day info
    week1 = result['weeks'][0]
    assert 'days' in week1, "Week should have days array"
    assert len(week1['days']) == 7, "Week should have 7 days"

    monday = week1['days'][0]
    assert 'workout_prefix' in monday, "Day should have workout_prefix"
    assert monday['day'] == 'Mon', f"First day should be Mon, got {monday['day']}"

    # Prefix should be W01_Mon_{Month}{Day}
    prefix = monday['workout_prefix']
    assert prefix.startswith('W01_Mon_'), f"Prefix format wrong: {prefix}"
    assert len(prefix) > 10, f"Prefix too short: {prefix}"

    print(f"  ✓ Workout prefix format: {prefix}")
    print("  ✓ PASSED")


def test_validation_catches_errors():
    """Test that validation catches bad data."""
    print("\n📋 Test: Validation Catches Errors")

    # Create valid plan first
    valid = calculate_plan_dates(RACE_DATE, 12)
    errors = validate_plan_dates(valid, RACE_DATE)
    critical_errors = [e for e in errors if e.startswith("CRITICAL")]
    assert len(critical_errors) == 0, f"Valid plan has errors: {critical_errors}"
    print("  ✓ Valid plan passes validation")

    # Test: Race date outside race week (shift the final week past the race)
    bad_plan = calculate_plan_dates(RACE_DATE, 12)
    bad_plan['weeks'][-1]['monday'] = _iso(RACE_DT + timedelta(days=3))
    bad_plan['weeks'][-1]['sunday'] = _iso(RACE_DT + timedelta(days=9))
    errors = validate_plan_dates(bad_plan, RACE_DATE)
    assert any("Race date" in e for e in errors), "Should catch race date outside race week"
    print("  ✓ Catches race date outside race week")

    # Test: Week number mismatch
    bad_plan2 = calculate_plan_dates(RACE_DATE, 12)
    bad_plan2['weeks'][5]['week'] = 99
    errors = validate_plan_dates(bad_plan2, RACE_DATE)
    assert any("Week number" in e for e in errors), "Should catch week number mismatch"
    print("  ✓ Catches week number mismatch")

    # Test: plan_weeks doesn't match weeks list
    bad_plan3 = calculate_plan_dates(RACE_DATE, 12)
    bad_plan3['plan_weeks'] = 99
    errors = validate_plan_dates(bad_plan3, RACE_DATE)
    assert any("plan_weeks" in e for e in errors), "Should catch plan_weeks mismatch"
    print("  ✓ Catches plan_weeks mismatch")

    print("  ✓ PASSED")


def test_phase_progression():
    """Test that phases progress correctly."""
    print("\n📋 Test: Phase Progression")

    result = calculate_plan_dates(RACE_DATE, 20)

    phases_seen = []
    for week in result['weeks']:
        if not phases_seen or phases_seen[-1] != week['phase']:
            phases_seen.append(week['phase'])

    # Should see: base -> build -> peak -> taper -> race
    assert phases_seen[0] == 'base', f"Should start with base, got {phases_seen[0]}"
    assert phases_seen[-1] == 'race', f"Should end with race, got {phases_seen[-1]}"
    assert result['weeks'][-1]['phase'] == 'race', "Final week must be race phase"

    print(f"  ✓ Phase progression: {' -> '.join(phases_seen)}")
    print("  ✓ PASSED")


def test_short_plans():
    """Test minimum plan length."""
    print("\n📋 Test: Short Plans")

    # 6-week minimum
    result = calculate_plan_dates(RACE_DATE, 6)
    assert result['plan_weeks'] == 6, f"Should allow 6 weeks, got {result['plan_weeks']}"
    assert len(result['weeks']) == 6, f"Should have 6 weeks"
    print("  ✓ 6-week plan works")

    # Even shorter should still work but warn
    result2 = calculate_plan_dates(RACE_DATE, 4)
    errors = validate_plan_dates(result2, RACE_DATE)
    warnings = [e for e in errors if e.startswith("WARNING")]
    # Note: 4 weeks is below recommended minimum
    print(f"  ✓ Short plan gets warning: {len(warnings)} warnings")
    print("  ✓ PASSED")


def test_real_athlete_shape():
    """A 19-week plan ending on a Sunday race (the Benjy Duke shape)."""
    print("\n📋 Test: Real Athlete Shape (19wk Sunday race)")

    result = calculate_plan_dates(RACE_DATE, 19)

    # Verify key dates
    assert result['race_date'] == RACE_DATE
    assert result['race_weekday'] == "Sunday"

    # Race week is the Monday before through the race Sunday
    race_week = result['weeks'][-1]
    assert race_week['monday'] == _iso(RACE_DT - timedelta(days=6)), \
        f"Race week Monday wrong: {race_week['monday']}"
    assert race_week['sunday'] == RACE_DATE, \
        f"Race week Sunday wrong: {race_week['sunday']}"

    # Validate
    errors = validate_plan_dates(result, RACE_DATE)
    critical = [e for e in errors if e.startswith("CRITICAL")]
    assert len(critical) == 0, f"Plan has critical errors: {critical}"

    print(f"  ✓ Race week: {race_week['monday']} - {race_week['sunday']}")
    print("  ✓ PASSED")


def test_known_race_dates():
    """Weekday derivation sanity check against fixed calendar facts."""
    print("\n📋 Test: Known Race Dates 2026")

    # Known races - source: official websites (weekday math only; these
    # may be past dates, which is fine for weekday derivation)
    known_races = {
        'SBT GRVL': ('2026-06-28', 'Sunday'),        # sbtgrvl.com
        'Unbound 200': ('2026-05-30', 'Saturday'),   # unboundgravel.com
    }

    for race_name, (date, expected_day) in known_races.items():
        result = calculate_plan_dates(date, 12)
        assert result['race_weekday'] == expected_day, \
            f"{race_name} should be {expected_day}, got {result['race_weekday']}"
        print(f"  ✓ {race_name}: {date} ({expected_day})")

    print("  ✓ PASSED")


def test_is_race_day_flag():
    """Test that is_race_day flag is set correctly."""
    print("\n📋 Test: is_race_day Flag")

    result = calculate_plan_dates(RACE_DATE, 12)

    # Find the race week
    race_week = result['weeks'][-1]
    assert race_week['is_race_week'] == True

    # Check is_race_day is only true for actual race day
    race_day_count = 0
    for day in race_week['days']:
        if day['is_race_day']:
            race_day_count += 1
            assert day['date'] == RACE_DATE, \
                f"Wrong day marked as race day: {day['date']} (expected {RACE_DATE})"

    assert race_day_count == 1, f"Expected 1 race day, found {race_day_count}"

    print(f"  ✓ Race day flag set correctly for {RACE_DATE}")
    print("  ✓ PASSED")


def test_heavy_training_end_constraint():
    """Test that heavy_training_end constraint affects phase calculation."""
    print("\n📋 Test: Heavy Training End Constraint")

    # Constraint lands on the Monday 4 weeks before race week — weeks from
    # there to taper must become maintenance instead of build/peak.
    constraint_monday = RACE_DT - timedelta(days=27)   # a Monday
    prev_monday = constraint_monday - timedelta(days=7)
    heavy_training_end = _iso(constraint_monday)

    result_with_constraint = calculate_plan_dates(
        RACE_DATE, 19, None, heavy_training_end)

    # Find the week starting on the constraint Monday
    constraint_week = None
    for week in result_with_constraint['weeks']:
        if week['monday'] == _iso(constraint_monday):
            constraint_week = week
            break

    assert constraint_week is not None, "Constraint-start week not found"
    assert constraint_week['phase'] == 'maintenance', \
        f"Week at constraint should be maintenance, got {constraint_week['phase']}"

    # Check that earlier weeks are still build/peak
    may_week = None
    for week in result_with_constraint['weeks']:
        if week['monday'] == _iso(prev_monday):
            may_week = week
            break

    assert may_week is not None, "Week before constraint not found"
    assert may_week['phase'] in ('build', 'peak'), \
        f"Week before constraint should be build/peak, got {may_week['phase']}"

    # Verify final weeks are still taper/race
    race_week = result_with_constraint['weeks'][-1]
    assert race_week['phase'] == 'race', f"Race week should be race, got {race_week['phase']}"

    print("  ✓ PASSED")
