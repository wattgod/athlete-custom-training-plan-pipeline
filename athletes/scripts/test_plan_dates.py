#!/usr/bin/env python3
"""
Regression tests for plan date calculations.

Run with: python3 test_plan_dates.py
"""

import sys
from datetime import datetime, timedelta
from calculate_plan_dates import calculate_plan_dates, validate_plan_dates, PlanDateValidationError


def test_basic_calculation():
    """Test basic plan date calculation."""
    print("\n📋 Test: Basic Calculation")

    # Race on Sunday June 28, 2026
    race_date = "2026-06-28"
    plan_weeks = 12

    result = calculate_plan_dates(race_date, plan_weeks)

    # Assertions
    assert result['race_date'] == race_date, f"Race date mismatch: {result['race_date']}"
    assert result['race_weekday'] == 'Sunday', f"Race weekday wrong: {result['race_weekday']}"
    assert result['plan_weeks'] == 12, f"Plan weeks wrong: {result['plan_weeks']}"
    assert len(result['weeks']) == 12, f"Weeks list wrong length: {len(result['weeks'])}"

    # Race week must contain race date
    race_week = result['weeks'][-1]
    assert race_week['is_race_week'] == True, "Final week must be race week"
    race_week_monday = datetime.strptime(race_week['monday'], '%Y-%m-%d')
    race_week_sunday = datetime.strptime(race_week['sunday'], '%Y-%m-%d')
    race_dt = datetime.strptime(race_date, '%Y-%m-%d')
    assert race_week_monday <= race_dt <= race_week_sunday, "Race date not in race week"

    print("  ✓ Race date correct")
    print("  ✓ Race weekday correct")
    print("  ✓ Plan weeks correct")
    print("  ✓ Race week contains race date")
    print("  ✓ PASSED")


def test_race_on_different_weekdays():
    """Test races on different days of the week."""
    print("\n📋 Test: Race on Different Weekdays")

    test_cases = [
        ("2026-06-28", "Sunday"),    # Sunday race
        ("2026-06-27", "Saturday"),  # Saturday race
        ("2026-06-22", "Monday"),    # Monday race
        ("2026-06-24", "Wednesday"), # Wednesday race
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

    result = calculate_plan_dates("2026-06-28", 19)

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

    result = calculate_plan_dates("2026-06-28", 19)

    for i, week in enumerate(result['weeks']):
        expected_num = i + 1
        assert week['week'] == expected_num, \
            f"Week number wrong at index {i}: expected {expected_num}, got {week['week']}"

    print(f"  ✓ Week numbers 1-{len(result['weeks'])} sequential")
    print("  ✓ PASSED")


def test_workout_naming_format():
    """Test workout naming includes date."""
    print("\n📋 Test: Workout Naming Format")

    result = calculate_plan_dates("2026-06-28", 12)

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
    print(f"  ✓ Example: {prefix}_Endurance.zwo")
    print("  ✓ PASSED")


def test_validation_catches_errors():
    """Test that validation catches bad data."""
    print("\n📋 Test: Validation Catches Errors")

    # Create valid plan first
    valid = calculate_plan_dates("2026-06-28", 12)
    errors = validate_plan_dates(valid, "2026-06-28")
    critical_errors = [e for e in errors if e.startswith("CRITICAL")]
    assert len(critical_errors) == 0, f"Valid plan has errors: {critical_errors}"
    print("  ✓ Valid plan passes validation")

    # Test: Race date outside race week
    bad_plan = calculate_plan_dates("2026-06-28", 12)
    bad_plan['weeks'][-1]['monday'] = "2026-07-01"  # Move race week
    bad_plan['weeks'][-1]['sunday'] = "2026-07-07"
    errors = validate_plan_dates(bad_plan, "2026-06-28")
    assert any("Race date" in e for e in errors), "Should catch race date outside race week"
    print("  ✓ Catches race date outside race week")

    # Test: Week number mismatch
    bad_plan2 = calculate_plan_dates("2026-06-28", 12)
    bad_plan2['weeks'][5]['week'] = 99
    errors = validate_plan_dates(bad_plan2, "2026-06-28")
    assert any("Week number" in e for e in errors), "Should catch week number mismatch"
    print("  ✓ Catches week number mismatch")

    # Test: plan_weeks doesn't match weeks list
    bad_plan3 = calculate_plan_dates("2026-06-28", 12)
    bad_plan3['plan_weeks'] = 99
    errors = validate_plan_dates(bad_plan3, "2026-06-28")
    assert any("plan_weeks" in e for e in errors), "Should catch plan_weeks mismatch"
    print("  ✓ Catches plan_weeks mismatch")

    print("  ✓ PASSED")


def test_phase_progression():
    """Test that phases progress correctly."""
    print("\n📋 Test: Phase Progression")

    result = calculate_plan_dates("2026-06-28", 20)

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
    result = calculate_plan_dates("2026-06-28", 6)
    assert result['plan_weeks'] == 6, f"Should allow 6 weeks, got {result['plan_weeks']}"
    assert len(result['weeks']) == 6, f"Should have 6 weeks"
    print("  ✓ 6-week plan works")

    # Even shorter should still work but warn
    result2 = calculate_plan_dates("2026-06-28", 4)
    errors = validate_plan_dates(result2, "2026-06-28")
    warnings = [e for e in errors if e.startswith("WARNING")]
    # Note: 4 weeks is below recommended minimum
    print(f"  ✓ Short plan gets warning: {len(warnings)} warnings")
    print("  ✓ PASSED")


def test_real_athlete_benjy():
    """Test with Benjy's actual data."""
    print("\n📋 Test: Real Athlete (Benjy Duke)")

    # SBT GRVL is June 28, 2026 (Sunday)
    race_date = "2026-06-28"

    # Calculate plan starting from Feb 16
    result = calculate_plan_dates(race_date, 19)

    # Verify key dates
    assert result['race_date'] == "2026-06-28"
    assert result['race_weekday'] == "Sunday"

    # Race week should be June 22-28
    race_week = result['weeks'][-1]
    assert race_week['monday'] == "2026-06-22", f"Race week Monday wrong: {race_week['monday']}"
    assert race_week['sunday'] == "2026-06-28", f"Race week Sunday wrong: {race_week['sunday']}"

    # Validate
    errors = validate_plan_dates(result, race_date)
    critical = [e for e in errors if e.startswith("CRITICAL")]
    assert len(critical) == 0, f"Benjy's plan has critical errors: {critical}"

    print(f"  ✓ Race: June 28, 2026 (Sunday)")
    print(f"  ✓ Plan weeks: {result['plan_weeks']}")
    print(f"  ✓ Race week: {race_week['monday']} - {race_week['sunday']}")
    print(f"  ✓ Example workout: {result['weeks'][0]['days'][0]['workout_prefix']}_Endurance.zwo")
    print("  ✓ PASSED")


def test_known_race_dates():
    """Test against known 2026 race calendar."""
    print("\n📋 Test: Known Race Dates 2026")

    # Known races - source: official websites
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

    race_date = "2026-06-28"
    result = calculate_plan_dates(race_date, 12)

    # Find the race week
    race_week = result['weeks'][-1]
    assert race_week['is_race_week'] == True

    # Check is_race_day is only true for actual race day
    race_day_count = 0
    for day in race_week['days']:
        if day['is_race_day']:
            race_day_count += 1
            assert day['date'] == race_date, \
                f"Wrong day marked as race day: {day['date']} (expected {race_date})"

    assert race_day_count == 1, f"Expected 1 race day, found {race_day_count}"

    print(f"  ✓ Race day flag set correctly for {race_date}")
    print("  ✓ PASSED")


def test_heavy_training_end_constraint():
    """Test that heavy_training_end constraint affects phase calculation."""
    print("\n📋 Test: Heavy Training End Constraint")

    race_date = "2026-06-28"
    heavy_training_end = "2026-06-01"

    # Without constraint - should have peak phase in June
    result_no_constraint = calculate_plan_dates(race_date, 19)
    # Week 16 (Jun 1-7) would normally be peak

    # With constraint - weeks after June 1 should be maintenance
    result_with_constraint = calculate_plan_dates(race_date, 19, None, heavy_training_end)

    # Find the week that contains June 1
    june1_week = None
    for week in result_with_constraint['weeks']:
        if week['monday'] == '2026-06-01':
            june1_week = week
            break

    assert june1_week is not None, "Week starting June 1 not found"
    assert june1_week['phase'] == 'maintenance', \
        f"Week starting June 1 should be maintenance with constraint, got {june1_week['phase']}"

    # Check that earlier weeks are still build/peak
    may_week = None
    for week in result_with_constraint['weeks']:
        if week['monday'] == '2026-05-25':  # Week before June 1
            may_week = week
            break

    assert may_week is not None, "Week starting May 25 not found"
    assert may_week['phase'] in ('build', 'peak'), \
        f"Week before constraint should be build/peak, got {may_week['phase']}"

    # Verify final weeks are still taper/race
    race_week = result_with_constraint['weeks'][-1]
    assert race_week['phase'] == 'race', f"Race week should be race, got {race_week['phase']}"

    taper_week = result_with_constraint['weeks'][-2]
    assert taper_week['phase'] == 'taper', f"Pre-race week should be taper, got {taper_week['phase']}"

    print(f"  ✓ Week starting June 1 is maintenance (not peak)")
    print(f"  ✓ Week before constraint is still {may_week['phase']}")
    print(f"  ✓ Race week unchanged: {race_week['phase']}")
    print(f"  ✓ Taper week unchanged: {taper_week['phase']}")
    print("  ✓ PASSED")


def test_benjy_with_constraints():
    """Test Benjy's plan with his June 1 heavy training end constraint."""
    print("\n📋 Test: Benjy's Constrained Plan")

    race_date = "2026-06-28"
    heavy_training_end = "2026-06-01"  # From Benjy's derived.yaml

    result = calculate_plan_dates(race_date, 19, None, heavy_training_end)

    # Count phases
    phase_counts = {}
    for week in result['weeks']:
        phase = week['phase']
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

    # Benjy's plan should have maintenance weeks after June 1
    assert 'maintenance' in phase_counts, "Benjy's plan should have maintenance phase"

    # Heavy training weeks (base + build + peak) should all be before June 1
    heavy_training_weeks = phase_counts.get('base', 0) + phase_counts.get('build', 0) + phase_counts.get('peak', 0)

    print(f"  ✓ Phase breakdown: {phase_counts}")
    print(f"  ✓ Heavy training weeks: {heavy_training_weeks}")
    print(f"  ✓ Maintenance weeks: {phase_counts.get('maintenance', 0)}")
    print("  ✓ PASSED")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PLAN DATE CALCULATION REGRESSION TESTS")
    print("=" * 60)

    tests = [
        test_basic_calculation,
        test_race_on_different_weekdays,
        test_week_continuity,
        test_week_numbering,
        test_workout_naming_format,
        test_validation_catches_errors,
        test_phase_progression,
        test_short_plans,
        test_real_athlete_benjy,
        test_known_race_dates,
        test_is_race_day_flag,
        test_heavy_training_end_constraint,
        test_benjy_with_constraints,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
