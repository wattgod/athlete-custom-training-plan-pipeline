#!/usr/bin/env python3
"""
Workout Templates for Training Plan Generation.

Centralizes all workout template definitions to avoid duplication.

Two types of templates:
1. PHASE_WORKOUT_ROLES - Defines what types of workouts go in each role (key, long, easy, strength)
2. DEFAULT_WEEKLY_SCHEDULE - Default Mon-Sun schedule for athletes without custom preferences
"""

from typing import Dict, Tuple

# Workout template format: (workout_type, description, duration_min, target_power_ratio)
WorkoutTemplate = Tuple[str, str, int, float]


# ============================================================================
# PHASE WORKOUT ROLES
# ============================================================================
# Defines workout templates by ROLE (key_cardio, long_ride, easy, strength)
# Used when building custom schedules based on athlete preferences
# ============================================================================

PHASE_WORKOUT_ROLES: Dict[str, Dict[str, WorkoutTemplate]] = {
    'base': {
        'key_cardio': ('Endurance', 'Zone 2 aerobic development', 60, 0.65),
        'long_ride': ('Long_Ride', 'Long Zone 2 endurance', 120, 0.60),
        'easy': ('Recovery', 'Easy spin or rest', 30, 0.50),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'build': {
        'key_cardio': ('Intervals', 'Threshold intervals: 3x10min @ 95% FTP', 75, 0.75),
        'long_ride': ('Long_Ride', 'Long ride with race-pace efforts', 150, 0.65),
        'easy': ('Recovery', 'Easy spin', 45, 0.55),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'peak': {
        'key_cardio': ('VO2max', 'VO2max intervals: 5x3min @ 110% FTP', 60, 0.80),
        'long_ride': ('Long_Ride', 'Long ride with race-pace blocks', 180, 0.65),
        'easy': ('Recovery', 'Easy spin', 40, 0.55),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'taper': {
        'key_cardio': ('Openers', 'Short openers: 4x30sec @ 120% FTP', 45, 0.65),
        'long_ride': ('Shakeout', 'Pre-race shakeout ride', 30, 0.55),
        'easy': ('Easy', 'Easy spin', 30, 0.55),
        'strength': ('Strength', 'Light strength maintenance', 30, 0.0),
    },
    'maintenance': {
        'key_cardio': ('Tempo', 'Light tempo: 20min @ 80% FTP', 45, 0.65),
        'long_ride': ('Endurance', 'Longer endurance ride', 90, 0.60),
        'easy': ('Recovery', 'Optional easy spin', 30, 0.50),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'race': {
        'key_cardio': ('Openers', 'Race week openers', 30, 0.60),
        'long_ride': ('RACE_DAY', 'RACE DAY - Execute your plan!', 0, 0),
        'easy': ('Easy', 'Easy spin', 30, 0.50),
        'strength': ('Rest', None, 0, 0),
    },
}


# ============================================================================
# DEFAULT WEEKLY SCHEDULE
# ============================================================================
# Full week template with specific days mapped to workouts
# Used for athletes WITHOUT custom schedule preferences
# Assumes: Mon/Thu rest, Sat long ride, Sun recovery
# ============================================================================

DEFAULT_WEEKLY_SCHEDULE: Dict[str, Dict[str, WorkoutTemplate]] = {
    'base': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Endurance', 'Zone 2 steady state', 60, 0.65),
        'Wed': ('Endurance', 'Zone 2 with cadence drills', 60, 0.65),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Endurance', 'Zone 2 aerobic development', 60, 0.65),
        'Sat': ('Long_Ride', 'Long Zone 2 endurance', 120, 0.60),
        'Sun': ('Recovery', 'Easy spin or rest', 30, 0.50),
    },
    'build': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Intervals', 'Threshold intervals: 3x10min @ 95% FTP', 75, 0.75),
        'Wed': ('Endurance', 'Zone 2 recovery spin', 60, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Tempo', 'Tempo ride: 30min @ 85% FTP', 60, 0.70),
        'Sat': ('Long_Ride', 'Long ride with race-pace efforts', 150, 0.65),
        'Sun': ('Recovery', 'Easy spin', 45, 0.55),
    },
    'peak': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('VO2max', 'VO2max intervals: 5x3min @ 110% FTP', 60, 0.80),
        'Wed': ('Endurance', 'Easy spin, legs open', 45, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Race_Sim', 'Race simulation: sustained efforts', 75, 0.75),
        'Sat': ('Long_Ride', 'Long ride with race-pace blocks', 180, 0.65),
        'Sun': ('Recovery', 'Easy spin', 40, 0.55),
    },
    'taper': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Openers', 'Short openers: 4x30sec @ 120% FTP', 45, 0.65),
        'Wed': ('Easy', 'Easy spin', 30, 0.55),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Easy', 'Easy spin with a few accelerations', 45, 0.60),
        'Sat': ('Shakeout', 'Pre-race shakeout ride', 30, 0.55),
        'Sun': ('Rest', None, 0, 0),
    },
    'maintenance': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Tempo', 'Light tempo: 20min @ 80% FTP', 45, 0.65),
        'Wed': ('Easy', 'Easy endurance spin', 45, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Endurance', 'Moderate endurance ride', 60, 0.60),
        'Sat': ('Endurance', 'Longer endurance ride', 90, 0.60),
        'Sun': ('Recovery', 'Optional easy spin', 30, 0.50),
    },
    'race': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Easy', 'Easy spin', 30, 0.50),
        'Wed': ('Rest', None, 0, 0),
        'Thu': ('Openers', 'Race week openers', 30, 0.60),
        'Fri': ('Rest', None, 0, 0),
        'Sat': ('Shakeout', 'Pre-race shakeout', 20, 0.55),
        'Sun': ('RACE_DAY', 'RACE DAY - Execute your plan!', 0, 0),
    },
}


def get_phase_roles(phase: str) -> Dict[str, WorkoutTemplate]:
    """Get workout templates by role for a training phase."""
    return PHASE_WORKOUT_ROLES.get(phase, PHASE_WORKOUT_ROLES['base'])


def get_default_day_workout(phase: str, day_abbrev: str) -> WorkoutTemplate:
    """Get the default workout for a specific day and phase."""
    phase_schedule = DEFAULT_WEEKLY_SCHEDULE.get(phase, DEFAULT_WEEKLY_SCHEDULE['base'])
    return phase_schedule.get(day_abbrev, ('Rest', None, 0, 0))


def cap_duration(template: WorkoutTemplate, max_duration: int) -> WorkoutTemplate:
    """Cap a workout template's duration to a maximum."""
    if not template or template[2] == 0:
        return template
    if max_duration > 0 and max_duration < template[2]:
        return (template[0], template[1], max_duration, template[3])
    return template
