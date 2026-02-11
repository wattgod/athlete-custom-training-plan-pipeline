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
        # Base phase: Build aerobic foundation, introduce tempo
        'key_cardio': ('Endurance', 'Zone 2 aerobic development', 60, 0.65),
        'long_ride': ('Long_Ride', 'Long Zone 2 endurance', 120, 0.60),
        'easy': ('Recovery', 'Easy spin or rest', 30, 0.50),
        'moderate': ('Endurance', 'Zone 2 steady state', 45, 0.62),
        'tempo': ('Tempo', 'Tempo: 2x10min @ 85% FTP', 50, 0.72),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'build': {
        # Build phase: Threshold work, introduce VO2max
        'key_cardio': ('Threshold', 'Threshold intervals: 3x10min @ 95-100% FTP', 60, 0.78),
        'long_ride': ('Long_Ride', 'Long ride with race-pace efforts', 150, 0.65),
        'easy': ('Recovery', 'Easy spin', 45, 0.55),
        'moderate': ('Sweet_Spot', 'Sweet spot: 3x12min @ 88% FTP', 55, 0.75),
        'tempo': ('Tempo', 'Tempo intervals: 2x15min @ 85% FTP', 50, 0.72),
        'vo2max': ('VO2max', 'VO2max: 4x3min @ 110-115% FTP', 50, 0.80),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'peak': {
        # Peak phase: VO2max emphasis, anaerobic power, race specificity
        'key_cardio': ('VO2max', 'VO2max intervals: 5x3min @ 115% FTP', 55, 0.82),
        'long_ride': ('Long_Ride', 'Long ride with race-pace blocks', 180, 0.65),
        'easy': ('Recovery', 'Easy spin', 40, 0.55),
        'moderate': ('Threshold', 'Threshold: 2x15min @ 95-100% FTP', 50, 0.78),
        'tempo': ('Sweet_Spot', 'Sweet spot: 3x10min @ 88% FTP', 50, 0.75),
        'vo2max': ('VO2max', 'VO2max: 5x3min @ 115-120% FTP', 50, 0.82),
        'anaerobic': ('Anaerobic', 'Anaerobic capacity: 8x30sec @ 150% FTP', 45, 0.70),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'taper': {
        # Taper: Maintain intensity, reduce volume, openers
        'key_cardio': ('Openers', 'Short openers: 4x30sec @ 130% FTP', 40, 0.62),
        'long_ride': ('Shakeout', 'Pre-race shakeout ride', 30, 0.55),
        'easy': ('Easy', 'Easy spin', 30, 0.55),
        'moderate': ('Easy', 'Easy spin with leg openers', 35, 0.58),
        'tempo': ('Easy', 'Easy spin', 30, 0.55),
        'vo2max': ('Openers', 'VO2 openers: 3x2min @ 110% FTP', 40, 0.65),
        'anaerobic': ('Sprints', 'Sprint openers: 4x15sec all-out', 35, 0.55),
        'strength': ('Strength', 'Light strength maintenance', 30, 0.0),
    },
    'maintenance': {
        # Maintenance: Keep fitness, reduced load
        'key_cardio': ('Tempo', 'Light tempo: 20min @ 80% FTP', 45, 0.65),
        'long_ride': ('Endurance', 'Longer endurance ride', 90, 0.60),
        'easy': ('Recovery', 'Optional easy spin', 30, 0.50),
        'moderate': ('Endurance', 'Zone 2 maintenance', 50, 0.62),
        'tempo': ('Tempo', 'Tempo: 2x12min @ 85% FTP', 45, 0.70),
        'vo2max': ('Threshold', 'Threshold touch: 2x8min @ 95% FTP', 45, 0.72),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'race': {
        # Race week: Minimal volume, maintain sharpness
        'key_cardio': ('Openers', 'Race week openers', 30, 0.60),
        'long_ride': ('RACE_DAY', 'RACE DAY - Execute your plan!', 0, 0),
        'easy': ('Easy', 'Easy spin', 30, 0.50),
        'moderate': ('Easy', 'Easy spin', 30, 0.50),
        'tempo': ('Easy', 'Easy spin', 25, 0.50),
        'vo2max': ('Openers', 'Brief openers', 25, 0.55),
        'anaerobic': ('Sprints', 'Neuromuscular activation: 3x10sec', 25, 0.50),
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
