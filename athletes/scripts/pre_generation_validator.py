#!/usr/bin/env python3
"""
Pre-generation validation for athlete data.

Validates ALL input files BEFORE generation starts to fail fast
and provide actionable error messages.
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from constants import (
    REQUIRED_PROFILE_FIELDS,
    FTP_MIN_WATTS, FTP_MAX_WATTS,
    WEIGHT_MIN_KG, WEIGHT_MAX_KG,
    PLAN_WEEKS_MIN, PLAN_WEEKS_MAX,
    AVAILABILITY_TYPES,
    DAY_FULL_TO_ABBREV,
)


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def merge(self, other: 'ValidationResult'):
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


def load_yaml_safe(path: Path) -> Tuple[Optional[dict], Optional[str]]:
    """Load YAML file safely. Returns (data, error_message)."""
    if not path.exists():
        return None, f"File not found: {path}"

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if data is None:
            return None, f"File is empty: {path}"
        return data, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML in {path}: {e}"
    except Exception as e:
        return None, f"Error reading {path}: {e}"


def get_nested(data: dict, key_path: str) -> Tuple[any, bool]:
    """Get nested value using dot notation. Returns (value, exists)."""
    keys = key_path.split('.')
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None, False

    return value, True


def validate_profile(profile: dict) -> ValidationResult:
    """Validate profile.yaml structure and values."""
    result = ValidationResult(is_valid=True)

    # Check required fields
    for field_path in REQUIRED_PROFILE_FIELDS:
        value, exists = get_nested(profile, field_path)
        if not exists:
            result.add_error(f"Missing required field: {field_path}")
        elif value is None or (isinstance(value, str) and not value.strip()):
            result.add_error(f"Required field is empty: {field_path}")

    # Validate athlete_id format
    athlete_id = profile.get('athlete_id', '')
    if athlete_id:
        import re
        if not re.match(r'^[a-z0-9-]+$', athlete_id):
            result.add_error(f"Invalid athlete_id format: '{athlete_id}' (use lowercase, numbers, hyphens)")

    # Validate race date
    race_date_str = profile.get('target_race', {}).get('date', '')
    if race_date_str:
        try:
            race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
            days_until = (race_date - datetime.now()).days
            if days_until < -7:
                result.add_error(f"Race date is {abs(days_until)} days in the past")
            elif days_until < 14:
                result.add_warning(f"Race is only {days_until} days away - plan may be too short")
        except ValueError:
            result.add_error(f"Invalid date format: '{race_date_str}' (use YYYY-MM-DD)")

    # Validate FTP if present
    ftp = profile.get('fitness_markers', {}).get('ftp_watts')
    if ftp is not None:
        if not isinstance(ftp, (int, float)):
            result.add_error(f"FTP must be a number, got: {type(ftp).__name__}")
        elif ftp < FTP_MIN_WATTS or ftp > FTP_MAX_WATTS:
            result.add_error(f"FTP {ftp}W outside valid range ({FTP_MIN_WATTS}-{FTP_MAX_WATTS})")

    # Validate weight if present
    weight = profile.get('fitness_markers', {}).get('weight_kg')
    if weight is not None:
        if not isinstance(weight, (int, float)):
            result.add_error(f"Weight must be a number, got: {type(weight).__name__}")
        elif weight < WEIGHT_MIN_KG or weight > WEIGHT_MAX_KG:
            result.add_error(f"Weight {weight}kg outside valid range ({WEIGHT_MIN_KG}-{WEIGHT_MAX_KG})")

    # Validate preferred_days
    preferred_days = profile.get('preferred_days', {})
    if not preferred_days:
        result.add_warning("No preferred_days defined - will use default schedule")
    else:
        key_day_count = 0
        for day_name, prefs in preferred_days.items():
            if day_name.lower() not in DAY_FULL_TO_ABBREV:
                result.add_error(f"Invalid day name in preferred_days: '{day_name}'")
                continue

            if isinstance(prefs, dict):
                avail = prefs.get('availability')
                if avail and avail not in AVAILABILITY_TYPES:
                    result.add_error(f"Invalid availability for {day_name}: '{avail}'")

                if prefs.get('is_key_day_ok'):
                    key_day_count += 1

                max_dur = prefs.get('max_duration_min')
                if max_dur is not None and (not isinstance(max_dur, (int, float)) or max_dur < 0):
                    result.add_error(f"Invalid max_duration_min for {day_name}: {max_dur}")

        if key_day_count == 0:
            result.add_warning("No days marked as is_key_day_ok=true - key workouts may not be scheduled")

    return result


def validate_derived(derived: dict, profile: dict) -> ValidationResult:
    """Validate derived.yaml and consistency with profile."""
    result = ValidationResult(is_valid=True)

    # Check required fields
    if 'plan_weeks' not in derived:
        result.add_error("derived.yaml missing plan_weeks")
    else:
        plan_weeks = derived['plan_weeks']
        if not isinstance(plan_weeks, int):
            result.add_error(f"plan_weeks must be integer, got: {type(plan_weeks).__name__}")
        elif plan_weeks < PLAN_WEEKS_MIN or plan_weeks > PLAN_WEEKS_MAX:
            result.add_error(f"plan_weeks {plan_weeks} outside valid range ({PLAN_WEEKS_MIN}-{PLAN_WEEKS_MAX})")

    # Check race date consistency
    profile_race_date = profile.get('target_race', {}).get('date')
    derived_race_date = derived.get('race_date')
    if profile_race_date and derived_race_date and profile_race_date != derived_race_date:
        result.add_error(f"Race date mismatch: profile={profile_race_date}, derived={derived_race_date}")

    return result


def validate_plan_dates(plan_dates: dict, derived: dict) -> ValidationResult:
    """Validate plan_dates.yaml structure."""
    result = ValidationResult(is_valid=True)

    if 'weeks' not in plan_dates:
        result.add_error("plan_dates.yaml missing weeks array")
        return result

    weeks = plan_dates.get('weeks', [])
    plan_weeks = plan_dates.get('plan_weeks', 0)

    if len(weeks) == 0:
        result.add_error("plan_dates.yaml has empty weeks array")
        return result

    if len(weeks) != plan_weeks:
        result.add_error(f"weeks array length ({len(weeks)}) != plan_weeks ({plan_weeks})")

    # Check weeks have required structure
    for i, week in enumerate(weeks):
        week_num = i + 1
        if 'week' not in week:
            result.add_error(f"Week {week_num} missing 'week' field")
        if 'phase' not in week:
            result.add_error(f"Week {week_num} missing 'phase' field")
        if 'days' not in week:
            result.add_error(f"Week {week_num} missing 'days' array")
        elif not week.get('days'):
            result.add_error(f"Week {week_num} has empty 'days' array")

    # Check last week is race week
    if weeks:
        last_week = weeks[-1]
        if not last_week.get('is_race_week'):
            result.add_warning("Final week not marked as race week")

    return result


def validate_methodology(methodology: dict) -> ValidationResult:
    """Validate methodology.yaml."""
    result = ValidationResult(is_valid=True)

    if 'selected_methodology' not in methodology:
        result.add_error("methodology.yaml missing selected_methodology")

    return result


def validate_fueling(fueling: dict, profile: dict) -> ValidationResult:
    """Validate fueling.yaml and consistency with profile."""
    result = ValidationResult(is_valid=True)

    # Check distance consistency
    fueling_distance = fueling.get('race', {}).get('distance_miles')
    profile_distance = profile.get('target_race', {}).get('distance_miles')

    if fueling_distance and profile_distance:
        if abs(fueling_distance - profile_distance) > 1:
            result.add_warning(
                f"Fueling distance ({fueling_distance}mi) differs from profile ({profile_distance}mi)"
            )

    return result


def validate_athlete_data(athlete_dir: Path) -> ValidationResult:
    """
    Validate all athlete data files BEFORE generation.

    Returns ValidationResult with is_valid=True only if ALL validations pass.
    """
    result = ValidationResult(is_valid=True)

    # Load all files
    profile, err = load_yaml_safe(athlete_dir / 'profile.yaml')
    if err:
        result.add_error(err)
        return result  # Can't continue without profile

    derived, err = load_yaml_safe(athlete_dir / 'derived.yaml')
    if err:
        result.add_error(err)

    plan_dates, err = load_yaml_safe(athlete_dir / 'plan_dates.yaml')
    if err:
        result.add_error(err)

    methodology, err = load_yaml_safe(athlete_dir / 'methodology.yaml')
    if err:
        result.add_error(err)

    fueling, err = load_yaml_safe(athlete_dir / 'fueling.yaml')
    if err:
        result.add_error(err)

    # If any required files failed to load, return early
    if not result.is_valid:
        return result

    # Validate each file
    result.merge(validate_profile(profile))
    result.merge(validate_derived(derived, profile))
    result.merge(validate_plan_dates(plan_dates, derived))
    result.merge(validate_methodology(methodology))
    result.merge(validate_fueling(fueling, profile))

    return result


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 pre_generation_validator.py <athlete_id>")
        sys.exit(1)

    athlete_id = sys.argv[1]
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id

    if not athlete_dir.exists():
        print(f"Athlete directory not found: {athlete_dir}")
        sys.exit(1)

    print(f"Validating {athlete_id}...")
    result = validate_athlete_data(athlete_dir)

    if result.errors:
        print("\n❌ ERRORS:")
        for err in result.errors:
            print(f"   {err}")

    if result.warnings:
        print("\n⚠️  WARNINGS:")
        for warn in result.warnings:
            print(f"   {warn}")

    if result.is_valid:
        print("\n✅ Validation passed" + (" (with warnings)" if result.warnings else ""))
        sys.exit(0)
    else:
        print("\n❌ Validation failed - fix errors before generating")
        sys.exit(1)
