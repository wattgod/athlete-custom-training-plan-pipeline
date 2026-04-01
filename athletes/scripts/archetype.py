#!/usr/bin/env python3
"""
Athlete Archetype Determination

Maps athlete profile data to one of 5 training archetypes that drive
workout selection, TSS guardrails, and intensity limits.

Source: block-builder SKILL.md Step 1
"""

from typing import Dict, Any, Tuple


# Archetype thresholds by weekly cycling hours
ARCHETYPE_THRESHOLDS = [
    (8,  'time_crunched'),  # <8 hrs/week
    (12, 'specialist'),     # 8-12 hrs/week
    (15, 'volume'),         # 12-15 hrs/week
    (99, 'goat'),           # 15-20+ hrs/week
]

# Phase thresholds by weeks to A-race
PHASE_THRESHOLDS = [
    (4,  'racing'),         # <4 weeks
    (8,  'race_prep'),      # 4-8 weeks
    (12, 'build'),          # 8-12 weeks
    (16, 'build'),          # 12-16 weeks (late base / early build)
    (99, 'base'),           # >16 weeks
]

# Training age constraints
TRAINING_AGE_CONSTRAINTS = {
    0: {'max_intensity_per_week': 1, 'max_level': 2, 'label': 'beginner'},
    1: {'max_intensity_per_week': 2, 'max_level': 3, 'label': 'novice'},
    2: {'max_intensity_per_week': 3, 'max_level': 5, 'label': 'intermediate'},
    3: {'max_intensity_per_week': 3, 'max_level': 6, 'label': 'experienced'},
}

# Masters constraints
MASTERS_AGE = 50
MASTERS_MAX_INTENSITY = 2
MASTERS_MIN_RECOVERY_HOURS = 48


def determine_archetype(hours_per_week: float) -> str:
    """Map weekly cycling hours to athlete archetype.

    Args:
        hours_per_week: Available cycling hours per week (from questionnaire)

    Returns:
        Archetype string: 'time_crunched', 'specialist', 'volume', or 'goat'
    """
    for threshold, archetype in ARCHETYPE_THRESHOLDS:
        if hours_per_week < threshold:
            return archetype
    return 'goat'


def determine_phase(weeks_to_race: int) -> str:
    """Map weeks until A-race to training phase.

    Args:
        weeks_to_race: Number of weeks until the primary A-race

    Returns:
        Phase string: 'base', 'build', 'race_prep', or 'racing'
    """
    for threshold, phase in PHASE_THRESHOLDS:
        if weeks_to_race <= threshold:
            return phase
    return 'base'


def get_training_age_constraints(years_structured: int) -> Dict[str, Any]:
    """Get intensity and level constraints for training age.

    Args:
        years_structured: Years of structured training (from questionnaire)

    Returns:
        Dict with max_intensity_per_week, max_level, label
    """
    # Clamp to known thresholds
    clamped = min(years_structured, max(TRAINING_AGE_CONSTRAINTS.keys()))
    for age_threshold in sorted(TRAINING_AGE_CONSTRAINTS.keys(), reverse=True):
        if clamped >= age_threshold:
            return TRAINING_AGE_CONSTRAINTS[age_threshold]
    return TRAINING_AGE_CONSTRAINTS[0]


def get_athlete_constraints(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Derive all training constraints from an athlete profile.

    Args:
        profile: Full athlete profile dict (from profile.yaml)

    Returns:
        Dict with archetype, phase, constraints, and overrides
    """
    # Extract profile fields
    hours = profile.get('weekly_availability', {}).get('cycling_hours_target', 8)
    age = profile.get('health_factors', {}).get('age', 30)
    years_structured = profile.get('training_history', {}).get('years_structured', 0)

    # Calculate weeks to race
    from datetime import date, datetime
    race_date_str = profile.get('target_race', {}).get('date', '')
    if race_date_str:
        race_date = datetime.strptime(race_date_str, '%Y-%m-%d').date()
        weeks_to_race = max(0, (race_date - date.today()).days // 7)
    else:
        weeks_to_race = 16  # Default to base if no race

    archetype = determine_archetype(hours)
    phase = determine_phase(weeks_to_race)
    training_age = get_training_age_constraints(years_structured)

    # Masters override
    is_masters = age >= MASTERS_AGE
    max_intensity = min(
        training_age['max_intensity_per_week'],
        MASTERS_MAX_INTENSITY if is_masters else 99
    )

    return {
        'archetype': archetype,
        'phase': phase,
        'weeks_to_race': weeks_to_race,
        'hours_per_week': hours,
        'is_masters': is_masters,
        'age': age,
        'years_structured': years_structured,
        'training_age_label': training_age['label'],
        'max_intensity_per_week': max_intensity,
        'max_level': training_age['max_level'],
    }
