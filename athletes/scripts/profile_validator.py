#!/usr/bin/env python3
"""
Profile validator for athlete YAML files.

Validates that profile.yaml contains all required fields with valid values.
"""

import re
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ValidationError:
    """Represents a validation error."""
    def __init__(self, level: str, field: str, message: str):
        self.level = level  # CRITICAL, ERROR, WARNING
        self.field = field
        self.message = message

    def __str__(self):
        return f"[{self.level}] {self.field}: {self.message}"


class ProfileValidator:
    """Validates athlete profile.yaml files."""

    # Required fields (dot notation for nested)
    REQUIRED_FIELDS = [
        'name',
        'athlete_id',
        'target_race.name',
        'target_race.date',
        'target_race.distance_miles',
    ]

    # Optional but recommended fields
    RECOMMENDED_FIELDS = [
        'preferred_days',
        'fitness_markers.ftp_watts',
        'fitness_markers.weight_kg',
        'weekly_availability.cycling_hours_target',
        'schedule_constraints.preferred_long_day',
    ]

    # Value constraints
    CONSTRAINTS = {
        'fitness_markers.ftp_watts': {'min': 50, 'max': 500, 'type': int},
        'fitness_markers.weight_kg': {'min': 40, 'max': 150, 'type': (int, float)},
        'target_race.distance_miles': {'min': 10, 'max': 500, 'type': (int, float)},
        'weekly_availability.cycling_hours_target': {'min': 1, 'max': 40, 'type': (int, float)},
        'age': {'min': 16, 'max': 100, 'type': int},
    }

    # Valid enum values
    ENUMS = {
        'preferred_days.*.availability': ['available', 'limited', 'unavailable', 'rest'],
        'schedule_constraints.work_schedule': ['full_time', 'part_time', 'flexible', 'none'],
        'recent_training.current_phase': ['off_season', 'base', 'build', 'peak', 'race', 'recovery'],
    }

    def __init__(self, profile: Dict):
        self.profile = profile
        self.errors: List[ValidationError] = []

    def _get_nested(self, key_path: str) -> Tuple[Any, bool]:
        """Get nested value using dot notation. Returns (value, exists)."""
        keys = key_path.split('.')
        value = self.profile

        for key in keys:
            if key == '*':
                # Wildcard - return the parent dict for iteration
                return value, True
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None, False

        return value, True

    def validate_required_fields(self):
        """Check all required fields are present."""
        for field in self.REQUIRED_FIELDS:
            value, exists = self._get_nested(field)
            if not exists:
                self.errors.append(ValidationError(
                    "CRITICAL", field, "Required field missing"
                ))
            elif value is None or (isinstance(value, str) and not value.strip()):
                self.errors.append(ValidationError(
                    "CRITICAL", field, "Required field is empty"
                ))

    def validate_recommended_fields(self):
        """Warn about missing recommended fields."""
        for field in self.RECOMMENDED_FIELDS:
            value, exists = self._get_nested(field)
            if not exists or value is None:
                self.errors.append(ValidationError(
                    "WARNING", field, "Recommended field missing"
                ))

    def validate_constraints(self):
        """Validate field value constraints."""
        for field, constraints in self.CONSTRAINTS.items():
            value, exists = self._get_nested(field)
            if not exists or value is None:
                continue

            # Type check
            expected_type = constraints.get('type')
            if expected_type and not isinstance(value, expected_type):
                self.errors.append(ValidationError(
                    "ERROR", field, f"Expected {expected_type}, got {type(value).__name__}"
                ))
                continue

            # Range check
            min_val = constraints.get('min')
            max_val = constraints.get('max')

            if min_val is not None and value < min_val:
                self.errors.append(ValidationError(
                    "ERROR", field, f"Value {value} below minimum {min_val}"
                ))
            if max_val is not None and value > max_val:
                self.errors.append(ValidationError(
                    "ERROR", field, f"Value {value} above maximum {max_val}"
                ))

    def validate_date_format(self):
        """Validate date fields are in correct format."""
        date_fields = [
            'target_race.date',
            'plan_start.preferred_start',
            'plan_start.end_heavy_training',
            'fitness_markers.ftp_date',
        ]

        for field in date_fields:
            value, exists = self._get_nested(field)
            if not exists or value is None:
                continue

            if isinstance(value, str):
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    self.errors.append(ValidationError(
                        "ERROR", field, f"Invalid date format '{value}', expected YYYY-MM-DD"
                    ))

    def validate_race_date_future(self):
        """Validate race date is in the future (or very recent past)."""
        race_date_str, exists = self._get_nested('target_race.date')
        if not exists or not race_date_str:
            return

        try:
            race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
            today = datetime.now()

            # Allow up to 7 days in the past (for post-race analysis)
            if race_date < today:
                days_past = (today - race_date).days
                if days_past > 7:
                    self.errors.append(ValidationError(
                        "CRITICAL", 'target_race.date',
                        f"Race date is {days_past} days in the past"
                    ))
        except ValueError:
            pass  # Already caught by date format validation

    def validate_preferred_days(self):
        """Validate preferred_days structure."""
        preferred_days, exists = self._get_nested('preferred_days')
        if not exists or not preferred_days:
            return

        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        valid_availability = ['available', 'limited', 'unavailable', 'rest']

        # Check at least one key day exists
        has_key_day = False
        for day, prefs in preferred_days.items():
            if day.lower() not in valid_days:
                self.errors.append(ValidationError(
                    "ERROR", f'preferred_days.{day}', f"Invalid day name"
                ))
                continue

            if isinstance(prefs, dict):
                availability = prefs.get('availability')
                if availability and availability not in valid_availability:
                    self.errors.append(ValidationError(
                        "ERROR", f'preferred_days.{day}.availability',
                        f"Invalid availability '{availability}'"
                    ))

                if prefs.get('is_key_day_ok'):
                    has_key_day = True

                max_duration = prefs.get('max_duration_min')
                if max_duration is not None:
                    if not isinstance(max_duration, (int, float)) or max_duration < 0:
                        self.errors.append(ValidationError(
                            "ERROR", f'preferred_days.{day}.max_duration_min',
                            f"Invalid duration: {max_duration}"
                        ))

        if not has_key_day:
            self.errors.append(ValidationError(
                "WARNING", 'preferred_days',
                "No days marked as is_key_day_ok=true - key workouts may not be scheduled"
            ))

    def validate_athlete_id(self):
        """Validate athlete_id format."""
        athlete_id, exists = self._get_nested('athlete_id')
        if not exists or not athlete_id:
            return

        # Should be lowercase, hyphenated
        if not re.match(r'^[a-z0-9-]+$', athlete_id):
            self.errors.append(ValidationError(
                "ERROR", 'athlete_id',
                f"Invalid format '{athlete_id}' - use lowercase letters, numbers, hyphens only"
            ))

    def validate_email(self):
        """Validate email format if present."""
        email, exists = self._get_nested('email')
        if not exists or not email:
            return

        # Basic email regex
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.errors.append(ValidationError(
                "WARNING", 'email', f"Invalid email format: {email}"
            ))

    def validate(self) -> List[ValidationError]:
        """Run all validations and return errors."""
        self.errors = []

        self.validate_required_fields()
        self.validate_recommended_fields()
        self.validate_constraints()
        self.validate_date_format()
        self.validate_race_date_future()
        self.validate_preferred_days()
        self.validate_athlete_id()
        self.validate_email()

        return self.errors


def validate_profile(profile_path: Path) -> Tuple[bool, List[ValidationError]]:
    """
    Validate a profile.yaml file.

    Returns (is_valid, errors) tuple.
    is_valid is True if no CRITICAL or ERROR level issues.
    """
    if not profile_path.exists():
        return False, [ValidationError("CRITICAL", "file", f"Profile not found: {profile_path}")]

    try:
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [ValidationError("CRITICAL", "file", f"Invalid YAML: {e}")]

    if not profile:
        return False, [ValidationError("CRITICAL", "file", "Profile is empty")]

    validator = ProfileValidator(profile)
    errors = validator.validate()

    # Check for blocking errors
    critical_or_error = [e for e in errors if e.level in ('CRITICAL', 'ERROR')]
    is_valid = len(critical_or_error) == 0

    return is_valid, errors


def validate_profile_interactive(profile_path: Path) -> bool:
    """Validate and print results interactively."""
    print(f"\n{'=' * 60}")
    print(f"VALIDATING: {profile_path.name}")
    print('=' * 60)

    is_valid, errors = validate_profile(profile_path)

    # Group by level
    critical = [e for e in errors if e.level == "CRITICAL"]
    error_level = [e for e in errors if e.level == "ERROR"]
    warnings = [e for e in errors if e.level == "WARNING"]

    if critical:
        print("\n🚨 CRITICAL:")
        for e in critical:
            print(f"   {e.field}: {e.message}")

    if error_level:
        print("\n❌ ERRORS:")
        for e in error_level:
            print(f"   {e.field}: {e.message}")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for e in warnings:
            print(f"   {e.field}: {e.message}")

    print("\n" + "-" * 40)
    print(f"Critical: {len(critical)}, Errors: {len(error_level)}, Warnings: {len(warnings)}")

    if is_valid:
        if warnings:
            print("✅ VALID (with warnings)")
        else:
            print("✅ VALID")
    else:
        print("❌ INVALID - fix critical/error issues")

    return is_valid


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 profile_validator.py <profile.yaml>")
        print("       python3 profile_validator.py --all")
        sys.exit(1)

    if sys.argv[1] == '--all':
        # Validate all profiles
        athletes_dir = Path(__file__).parent.parent
        all_valid = True

        for athlete_dir in sorted(athletes_dir.iterdir()):
            profile_path = athlete_dir / 'profile.yaml'
            if profile_path.exists():
                if not validate_profile_interactive(profile_path):
                    all_valid = False

        sys.exit(0 if all_valid else 1)
    else:
        profile_path = Path(sys.argv[1])
        if not profile_path.is_absolute():
            # Try relative to athletes dir
            athletes_dir = Path(__file__).parent.parent
            if (athletes_dir / profile_path / 'profile.yaml').exists():
                profile_path = athletes_dir / profile_path / 'profile.yaml'
            elif (athletes_dir / profile_path).exists():
                profile_path = athletes_dir / profile_path

        # If it's a directory, look for profile.yaml inside
        if profile_path.is_dir():
            profile_path = profile_path / 'profile.yaml'

        is_valid = validate_profile_interactive(profile_path)
        sys.exit(0 if is_valid else 1)
