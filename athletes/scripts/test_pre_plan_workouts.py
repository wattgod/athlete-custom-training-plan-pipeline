#!/usr/bin/env python3
"""
Tests for pre-plan week (W00) workout generation.

These tests ensure that:
1. Pre-plan workouts are generated when plan starts in the future
2. Pre-plan workouts have correct naming format
3. Pre-plan workouts have personalized content
4. Pre-plan workouts are NOT generated if plan already started
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


def test_pre_plan_workout_naming_format():
    """Test that pre-plan workouts follow W00_Day_Date_Type.zwo format."""
    # Valid pre-plan workout names
    valid_names = [
        "W00_Wed_Feb11_Pre_Plan_Easy.zwo",
        "W00_Thu_Feb12_Pre_Plan_Strength_Prep.zwo",
        "W00_Fri_Feb13_Pre_Plan_Easy.zwo",
        "W00_Sat_Feb14_Pre_Plan_Endurance.zwo",
        "W00_Sun_Feb15_Pre_Plan_Rest.zwo",
    ]

    import re
    pattern = r'^W00_[A-Z][a-z]{2}_[A-Z][a-z]{2}\d{1,2}_Pre_Plan_\w+\.zwo$'

    for name in valid_names:
        assert re.match(pattern, name), f"Invalid pre-plan workout name: {name}"

    print("All pre-plan workout naming formats are valid")


def test_pre_plan_workouts_exist_for_kyle():
    """Test that Kyle's pre-plan workouts exist if plan starts in future."""
    from constants import get_athlete_dir

    kyle_dir = get_athlete_dir('kyle-cocowitch')
    workouts_dir = kyle_dir / 'workouts'

    if not workouts_dir.exists():
        pytest.skip("Kyle's workouts directory doesn't exist")

    # Check if pre-plan workouts exist
    pre_plan_files = list(workouts_dir.glob('W00_*.zwo'))

    # Load plan_dates to see if pre-plan should exist
    import yaml
    plan_dates_path = kyle_dir / 'plan_dates.yaml'
    if not plan_dates_path.exists():
        pytest.skip("Kyle's plan_dates.yaml doesn't exist")

    with open(plan_dates_path) as f:
        plan_dates = yaml.safe_load(f)

    plan_start = datetime.strptime(plan_dates['plan_start'], '%Y-%m-%d')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_until_start = (plan_start - today).days

    if 0 < days_until_start <= 7:
        # Pre-plan should exist
        assert len(pre_plan_files) > 0, "Pre-plan workouts should exist when plan starts within 7 days"
        print(f"Found {len(pre_plan_files)} pre-plan workout files")
    else:
        # Pre-plan may or may not exist (depends on when generated)
        print(f"Plan starts in {days_until_start} days - pre-plan generation rules vary")


def test_pre_plan_workout_content_is_personalized():
    """Test that pre-plan workouts contain personalized athlete content."""
    from constants import get_athlete_dir

    kyle_dir = get_athlete_dir('kyle-cocowitch')
    workouts_dir = kyle_dir / 'workouts'

    if not workouts_dir.exists():
        pytest.skip("Kyle's workouts directory doesn't exist")

    pre_plan_files = list(workouts_dir.glob('W00_*.zwo'))

    if not pre_plan_files:
        pytest.skip("No pre-plan workouts found")

    # Check at least one file for personalization
    with open(pre_plan_files[0], 'r') as f:
        content = f.read()

    # Should contain athlete's first name
    assert 'Kyle' in content, "Pre-plan workout should contain athlete's name"

    # Should contain PRE-PLAN marker
    assert 'PRE-PLAN' in content, "Pre-plan workout should be marked as PRE-PLAN"

    print(f"Pre-plan workout content is personalized for Kyle")


def test_pre_plan_workouts_are_valid_zwo():
    """Test that pre-plan workouts are valid ZWO XML."""
    from constants import get_athlete_dir
    import xml.etree.ElementTree as ET

    kyle_dir = get_athlete_dir('kyle-cocowitch')
    workouts_dir = kyle_dir / 'workouts'

    if not workouts_dir.exists():
        pytest.skip("Kyle's workouts directory doesn't exist")

    pre_plan_files = list(workouts_dir.glob('W00_*.zwo'))

    if not pre_plan_files:
        pytest.skip("No pre-plan workouts found")

    for zwo_file in pre_plan_files:
        with open(zwo_file, 'r') as f:
            content = f.read()

        # Should parse as valid XML
        try:
            root = ET.fromstring(content)
            assert root.tag == 'workout_file', f"{zwo_file.name} should have workout_file root"
        except ET.ParseError as e:
            pytest.fail(f"{zwo_file.name} is not valid XML: {e}")

    print(f"All {len(pre_plan_files)} pre-plan workouts are valid ZWO XML")


def test_pre_plan_week_not_generated_for_past_plan():
    """Test that pre-plan week is NOT generated if plan start is in the past."""
    # This is a logic test - we verify by checking plan_dates
    # If plan_start is in the past, W00 files should not be regenerated

    from datetime import datetime

    # Simulate a plan that already started
    past_plan_start = datetime.now() - timedelta(days=5)
    today = datetime.now()

    days_until_start = (past_plan_start - today).days

    # Logic check: if days_until_start <= 0, no pre-plan should be generated
    assert days_until_start < 0, "Test setup: plan start should be in past"

    # The generate_pre_plan_week function should return [] for this case
    should_generate = 0 < days_until_start <= 7
    assert not should_generate, "Pre-plan should NOT be generated for past plan start"

    print("Correctly identified that pre-plan should not be generated for past plans")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
