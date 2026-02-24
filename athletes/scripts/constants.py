#!/usr/bin/env python3
"""
Single source of truth for constants used across the pipeline.

All shared constants should be defined here to avoid duplication.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional


# === ATHLETE PATH UTILITIES ===
# Use these instead of constructing paths manually throughout the codebase

# Get the absolute path to the athletes directory (scripts/../)
ATHLETES_BASE_DIR: Path = Path(__file__).parent.parent.resolve()


def get_athlete_dir(athlete_id: str) -> Path:
    """Get the base directory for an athlete."""
    return ATHLETES_BASE_DIR / athlete_id


def get_athlete_file(athlete_id: str, filename: str) -> Path:
    """Get path to a file in athlete's directory (e.g., profile.yaml, derived.yaml)."""
    return get_athlete_dir(athlete_id) / filename


def get_athlete_plans_dir(athlete_id: str) -> Path:
    """Get the plans directory for an athlete."""
    return get_athlete_dir(athlete_id) / "plans"


def get_athlete_current_plan_dir(athlete_id: str) -> Path:
    """Get the current plan directory for an athlete."""
    return get_athlete_plans_dir(athlete_id) / "current"


def get_athlete_plan_dir(athlete_id: str, year: int, race_id: str) -> Path:
    """Get a specific plan directory for an athlete."""
    return get_athlete_plans_dir(athlete_id) / f"{year}-{race_id}"


def load_athlete_yaml(athlete_id: str, filename: str) -> Optional[Dict]:
    """
    Load a YAML file from an athlete's directory.

    Returns None if file doesn't exist. Raises on parse error.
    """
    import yaml
    path = get_athlete_file(athlete_id, filename)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return yaml.safe_load(f)


# === DAY MAPPINGS ===
# Use these everywhere instead of defining locally

DAY_FULL_TO_ABBREV: Dict[str, str] = {
    'monday': 'Mon',
    'tuesday': 'Tue',
    'wednesday': 'Wed',
    'thursday': 'Thu',
    'friday': 'Fri',
    'saturday': 'Sat',
    'sunday': 'Sun',
}

DAY_ABBREV_TO_FULL: Dict[str, str] = {v: k for k, v in DAY_FULL_TO_ABBREV.items()}

# Ordered lists of days
DAY_ORDER: List[str] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
DAY_ORDER_FULL: List[str] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
DAY_ORDER_DISPLAY: List[str] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

WEEKDAYS: List[str] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
WEEKDAYS_FULL: List[str] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
WEEKEND: List[str] = ['Sat', 'Sun']
WEEKEND_FULL: List[str] = ['saturday', 'sunday']


# === WORKOUT TYPES ===

KEY_WORKOUT_TYPES: List[str] = [
    'FTP_Test',
    'Intervals',
    'VO2max',
    'Race_Sim',
    'Tempo',
]

LONG_RIDE_TYPES: List[str] = ['Long_Ride']

EASY_WORKOUT_TYPES: List[str] = ['Recovery', 'Easy', 'Shakeout', 'Endurance']

STRENGTH_WORKOUT_TYPES: List[str] = ['Strength']


# === WORKOUT DURATIONS (minutes) ===
# Approximate durations by workout type for validation

WORKOUT_DURATIONS: Dict[str, int] = {
    'Recovery': 30,
    'Easy': 30,
    'Shakeout': 20,
    'Endurance': 60,
    'Tempo': 60,
    'Intervals': 75,
    'VO2max': 60,
    'Race_Sim': 75,
    'FTP_Test': 62,
    'Long_Ride': 120,
    'Openers': 45,
    'Strength': 30,
}


# === FTP TEST ===

FTP_TEST_DURATION_MIN: int = 62  # Based on standard protocol


# === TRAINING PHASES ===

TRAINING_PHASES: List[str] = [
    'base',
    'build',
    'peak',
    'maintenance',
    'taper',
    'race',
]

# Phases where strength training is included
STRENGTH_PHASES: List[str] = ['base', 'build', 'peak', 'maintenance']


# === VALIDATION BOUNDS ===

FTP_MIN_WATTS: int = 50
FTP_MAX_WATTS: int = 500

WEIGHT_MIN_KG: float = 40.0
WEIGHT_MAX_KG: float = 150.0

PLAN_WEEKS_MIN: int = 4
PLAN_WEEKS_MAX: int = 52

AGE_MIN: int = 16
AGE_MAX: int = 100

# === TIER THRESHOLDS ===
# Weekly cycling hours that determine tier classification
TIER_HOURS_AYAHUASCA_MAX: int = 5   # <= 5 hours/week
TIER_HOURS_FINISHER_MAX: int = 10   # <= 10 hours/week
TIER_HOURS_COMPETE_MAX: int = 16    # <= 16 hours/week
# > 16 hours/week = podium tier


# === RATE LIMITING ===
RATE_LIMIT_MAX_PER_DAY: int = 5     # Maximum submissions per email per day
RATE_LIMIT_CLEANUP_DAYS: int = 7    # Days before old rate limit entries are cleaned up

# === WORKOUT PERCENTAGES ===
# Used for calculating warmup duration, intensity distributions, etc.
WARMUP_DURATION_PERCENT: float = 0.10  # 10% of workout for warmup
COOLDOWN_DURATION_MIN: int = 5  # Minimum 5 minutes cooldown


# === AVAILABILITY TYPES ===

AVAILABILITY_TYPES: List[str] = ['available', 'limited', 'unavailable', 'rest']


# === FILE PATTERNS ===

ZWO_FILENAME_PATTERN: str = r'W(\d+)_(\w{3})_\w+\d+_(.+)\.zwo'


# === PROFILE REQUIRED FIELDS ===

REQUIRED_PROFILE_FIELDS: List[str] = [
    'name',
    'athlete_id',
    'target_race.name',
    'target_race.date',
    'target_race.distance_miles',
]

RECOMMENDED_PROFILE_FIELDS: List[str] = [
    'preferred_days',
    'fitness_markers.ftp_watts',
    'fitness_markers.weight_kg',
    'weekly_availability.cycling_hours_target',
    'schedule_constraints.preferred_long_day',
]
