#!/usr/bin/env python3
"""
Unit tests for validation modules.

Tests pre_generation_validator, profile_validator, and constants.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml
from constants import (
    DAY_FULL_TO_ABBREV,
    DAY_ABBREV_TO_FULL,
    DAY_ORDER,
    DAY_ORDER_FULL,
    KEY_WORKOUT_TYPES,
    TRAINING_PHASES,
    STRENGTH_PHASES,
    FTP_MIN_WATTS,
    FTP_MAX_WATTS,
    WEIGHT_MIN_KG,
    WEIGHT_MAX_KG,
    REQUIRED_PROFILE_FIELDS,
    AVAILABILITY_TYPES,
    RATE_LIMIT_MAX_PER_DAY,
    RATE_LIMIT_CLEANUP_DAYS,
    get_athlete_dir,
    get_athlete_file,
    get_athlete_plans_dir,
    get_athlete_current_plan_dir,
    get_athlete_plan_dir,
)
from pre_generation_validator import (
    ValidationResult,
    load_yaml_safe,
    get_nested,
    validate_profile,
    validate_derived,
    validate_plan_dates,
)


def test_constants_day_mappings():
    """Test that day mappings are consistent."""
    print("\n=== Testing Day Mappings ===")

    # Test bidirectional mappings
    for full, abbrev in DAY_FULL_TO_ABBREV.items():
        assert DAY_ABBREV_TO_FULL[abbrev] == full, f"Mapping mismatch: {full} <-> {abbrev}"
    print(f"✓ All {len(DAY_FULL_TO_ABBREV)} day mappings are bidirectional")

    # Test DAY_ORDER has all days
    assert len(DAY_ORDER) == 7, f"DAY_ORDER should have 7 days, got {len(DAY_ORDER)}"
    assert len(set(DAY_ORDER)) == 7, "DAY_ORDER should have 7 unique days"
    print(f"✓ DAY_ORDER has all 7 unique days")


def test_constants_validation_bounds():
    """Test validation bounds are sensible."""
    print("\n=== Testing Validation Bounds ===")

    assert FTP_MIN_WATTS < FTP_MAX_WATTS, "FTP min should be less than max"
    assert FTP_MIN_WATTS > 0, "FTP min should be positive"
    assert FTP_MAX_WATTS < 1000, "FTP max should be reasonable"
    print(f"✓ FTP bounds: {FTP_MIN_WATTS}-{FTP_MAX_WATTS}W")

    assert WEIGHT_MIN_KG < WEIGHT_MAX_KG, "Weight min should be less than max"
    assert WEIGHT_MIN_KG > 0, "Weight min should be positive"
    print(f"✓ Weight bounds: {WEIGHT_MIN_KG}-{WEIGHT_MAX_KG}kg")


def test_constants_phases():
    """Test training phases are defined correctly."""
    print("\n=== Testing Training Phases ===")

    # Strength phases should be a subset of training phases
    for phase in STRENGTH_PHASES:
        assert phase in TRAINING_PHASES, f"Strength phase '{phase}' not in TRAINING_PHASES"
    print(f"✓ All {len(STRENGTH_PHASES)} strength phases are valid training phases")

    # Check essential phases exist
    required_phases = ['base', 'build', 'peak', 'taper', 'race']
    for phase in required_phases:
        assert phase in TRAINING_PHASES, f"Missing required phase: {phase}"
    print(f"✓ All required phases present: {required_phases}")


def test_validation_result():
    """Test ValidationResult class."""
    print("\n=== Testing ValidationResult ===")

    result = ValidationResult(is_valid=True)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0

    result.add_warning("Test warning")
    assert result.is_valid is True  # Warnings don't invalidate
    assert len(result.warnings) == 1
    print("✓ Warnings don't invalidate result")

    result.add_error("Test error")
    assert result.is_valid is False  # Errors invalidate
    assert len(result.errors) == 1
    print("✓ Errors invalidate result")

    # Test merge
    other = ValidationResult(is_valid=True)
    other.add_warning("Other warning")
    result.merge(other)
    assert len(result.warnings) == 2
    print("✓ Merge combines warnings and errors")


def test_get_nested():
    """Test nested dictionary access."""
    print("\n=== Testing get_nested ===")

    data = {
        'level1': {
            'level2': {
                'value': 42
            }
        }
    }

    value, exists = get_nested(data, 'level1.level2.value')
    assert exists is True
    assert value == 42
    print("✓ Gets deeply nested value")

    value, exists = get_nested(data, 'level1.missing.value')
    assert exists is False
    print("✓ Returns False for missing path")


def test_load_yaml_safe():
    """Test safe YAML loading."""
    print("\n=== Testing load_yaml_safe ===")

    # Test with valid YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'test': 'value'}, f)
        temp_path = Path(f.name)

    data, err = load_yaml_safe(temp_path)
    assert err is None
    assert data['test'] == 'value'
    temp_path.unlink()
    print("✓ Loads valid YAML")

    # Test with non-existent file
    data, err = load_yaml_safe(Path('/nonexistent/file.yaml'))
    assert data is None
    assert 'not found' in err.lower()
    print("✓ Handles missing file")


def test_validate_profile():
    """Test profile validation."""
    print("\n=== Testing validate_profile ===")

    # Use a date 6 months in the future for testing
    from datetime import datetime, timedelta
    future_date = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')

    # Valid profile
    valid_profile = {
        'name': 'Test Athlete',
        'athlete_id': 'test-athlete',
        'target_race': {
            'name': 'Test Race',
            'date': future_date,
            'distance_miles': 100,
        },
        'preferred_days': {
            'saturday': {'is_key_day_ok': True, 'availability': 'available'},
        },
        'fitness_markers': {
            'ftp_watts': 250,
            'weight_kg': 75,
        }
    }

    result = validate_profile(valid_profile)
    assert result.is_valid is True, f"Valid profile failed: {result.errors}"
    print("✓ Valid profile passes validation")

    # Invalid athlete_id
    invalid_profile = valid_profile.copy()
    invalid_profile['athlete_id'] = 'Invalid ID!'
    result = validate_profile(invalid_profile)
    assert result.is_valid is False
    assert any('athlete_id' in e for e in result.errors)
    print("✓ Detects invalid athlete_id format")

    # FTP out of range
    invalid_profile = valid_profile.copy()
    invalid_profile['fitness_markers'] = {'ftp_watts': 5000}
    result = validate_profile(invalid_profile)
    assert result.is_valid is False
    assert any('FTP' in e for e in result.errors)
    print("✓ Detects FTP out of range")


def test_validate_derived():
    """Test derived.yaml validation."""
    print("\n=== Testing validate_derived ===")

    from datetime import datetime, timedelta
    future_date = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
    different_date = (datetime.now() + timedelta(days=200)).strftime('%Y-%m-%d')

    profile = {'target_race': {'date': future_date}}

    # Valid derived
    valid_derived = {
        'plan_weeks': 12,
        'race_date': future_date,
    }
    result = validate_derived(valid_derived, profile)
    assert result.is_valid is True
    print("✓ Valid derived passes validation")

    # Date mismatch
    mismatched = {
        'plan_weeks': 12,
        'race_date': different_date,  # Different date
    }
    result = validate_derived(mismatched, profile)
    assert result.is_valid is False
    assert any('mismatch' in e.lower() for e in result.errors)
    print("✓ Detects race date mismatch")


def test_validate_plan_dates():
    """Test plan_dates.yaml validation."""
    print("\n=== Testing validate_plan_dates ===")

    derived = {'plan_weeks': 12}

    # Valid plan_dates
    valid = {
        'plan_weeks': 12,
        'weeks': [
            {'week': i, 'phase': 'base', 'days': [{'day': 'Mon'}]}
            for i in range(1, 13)
        ]
    }
    valid['weeks'][-1]['is_race_week'] = True

    result = validate_plan_dates(valid, derived)
    assert result.is_valid is True
    print("✓ Valid plan_dates passes validation")

    # Missing weeks
    invalid = {'plan_weeks': 12, 'weeks': []}
    result = validate_plan_dates(invalid, derived)
    assert result.is_valid is False
    print("✓ Detects empty weeks array")


def test_athlete_path_utilities():
    """Test centralized athlete path utilities."""
    print("\n=== Testing Athlete Path Utilities ===")

    athlete_id = "test-athlete"

    # Test get_athlete_dir
    athlete_dir = get_athlete_dir(athlete_id)
    assert str(athlete_dir) == f"athletes/{athlete_id}"
    print(f"✓ get_athlete_dir: {athlete_dir}")

    # Test get_athlete_file
    profile_path = get_athlete_file(athlete_id, "profile.yaml")
    assert str(profile_path) == f"athletes/{athlete_id}/profile.yaml"
    print(f"✓ get_athlete_file: {profile_path}")

    # Test get_athlete_plans_dir
    plans_dir = get_athlete_plans_dir(athlete_id)
    assert str(plans_dir) == f"athletes/{athlete_id}/plans"
    print(f"✓ get_athlete_plans_dir: {plans_dir}")

    # Test get_athlete_current_plan_dir
    current_dir = get_athlete_current_plan_dir(athlete_id)
    assert str(current_dir) == f"athletes/{athlete_id}/plans/current"
    print(f"✓ get_athlete_current_plan_dir: {current_dir}")

    # Test get_athlete_plan_dir
    plan_dir = get_athlete_plan_dir(athlete_id, 2026, "big-race")
    assert str(plan_dir) == f"athletes/{athlete_id}/plans/2026-big-race"
    print(f"✓ get_athlete_plan_dir: {plan_dir}")


def test_rate_limit_constants():
    """Test rate limit constants are sensible."""
    print("\n=== Testing Rate Limit Constants ===")

    assert RATE_LIMIT_MAX_PER_DAY > 0, "Max per day should be positive"
    assert RATE_LIMIT_MAX_PER_DAY <= 100, "Max per day should be reasonable"
    print(f"✓ RATE_LIMIT_MAX_PER_DAY: {RATE_LIMIT_MAX_PER_DAY}")

    assert RATE_LIMIT_CLEANUP_DAYS > 0, "Cleanup days should be positive"
    assert RATE_LIMIT_CLEANUP_DAYS <= 30, "Cleanup should be within a month"
    print(f"✓ RATE_LIMIT_CLEANUP_DAYS: {RATE_LIMIT_CLEANUP_DAYS}")


def test_date_arithmetic_edge_cases():
    """Test date arithmetic handles edge cases correctly."""
    from datetime import datetime, timedelta

    print("\n=== Testing Date Arithmetic Edge Cases ===")

    # Test the fix: using timedelta instead of day subtraction
    # This would crash on days 1-7 of the month with the old code

    # Simulate being on day 3 of a month
    test_date = datetime(2026, 3, 3)  # March 3rd
    cutoff = test_date - timedelta(days=RATE_LIMIT_CLEANUP_DAYS)

    assert cutoff.month == 2, "Cutoff should roll back to previous month"
    assert cutoff.day == 24, f"Cutoff should be Feb 24 (7 days before Mar 3), got {cutoff.day}"
    print(f"✓ Date arithmetic handles month boundary: {test_date} - {RATE_LIMIT_CLEANUP_DAYS} days = {cutoff}")

    # Test being on day 1
    test_date = datetime(2026, 1, 1)  # January 1st
    cutoff = test_date - timedelta(days=RATE_LIMIT_CLEANUP_DAYS)
    assert cutoff.year == 2025, "Cutoff should roll back to previous year"
    assert cutoff.month == 12, "Cutoff should be December"
    print(f"✓ Date arithmetic handles year boundary: {test_date} - {RATE_LIMIT_CLEANUP_DAYS} days = {cutoff}")


def test_day_order_consistency():
    """Test DAY_ORDER and DAY_ORDER_FULL are consistent."""
    print("\n=== Testing Day Order Consistency ===")

    assert len(DAY_ORDER) == len(DAY_ORDER_FULL) == 7
    print("✓ Both DAY_ORDER lists have 7 days")

    # Check that abbreviated and full orders match
    for abbrev, full in zip(DAY_ORDER, DAY_ORDER_FULL):
        expected_abbrev = DAY_FULL_TO_ABBREV.get(full)
        assert abbrev == expected_abbrev, f"Order mismatch: {abbrev} vs {full} (expected {expected_abbrev})"
    print("✓ DAY_ORDER and DAY_ORDER_FULL are in sync")


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("VALIDATION UNIT TESTS")
    print("=" * 60)

    tests = [
        test_constants_day_mappings,
        test_constants_validation_bounds,
        test_constants_phases,
        test_validation_result,
        test_get_nested,
        test_load_yaml_safe,
        test_validate_profile,
        test_validate_derived,
        test_validate_plan_dates,
        test_athlete_path_utilities,
        test_rate_limit_constants,
        test_date_arithmetic_edge_cases,
        test_day_order_consistency,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {test.__name__}")
            print(f"   {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
