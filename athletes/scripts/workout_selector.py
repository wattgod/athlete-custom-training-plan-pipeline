#!/usr/bin/env python3
"""
Workout Selector — Phase × Archetype → Specific Workout Names + Levels

Implements the block-builder's workout selection matrix (workout-selection.md).
Given a phase, archetype, and week position, returns the exact workout name
and level for each day slot.

Source: block-builder SKILL.md Steps 4-6, references/workout-selection.md
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# Load workout selection config
_CONFIG_DIR = Path(__file__).parent.parent / 'config'


def _load_config(filename: str) -> dict:
    with open(_CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)


def _load_selection_config():
    return _load_config('workout_selection.yaml')


def _load_tss_config():
    return _load_config('tss_guardrails.yaml')


def _load_library():
    return _load_config('workout_library.yaml')


# ============================================================
# Workout slot selection
# ============================================================

def select_workouts_for_week(
    phase: str,
    archetype: str,
    week_type: str,
    week_in_block: int,
    base_level: int,
    max_level: int = 6,
    max_intensity: int = 3,
    hours_per_week: float = 10,
) -> List[Dict[str, Any]]:
    """Select workouts for a single week.

    Args:
        phase: Training phase ('base', 'build', 'race_prep', 'racing')
        archetype: Athlete archetype ('time_crunched', 'specialist', 'volume', 'goat')
        week_type: 'load', 'recovery', or 'race'
        week_in_block: Position within 3-week block (1=first load, 2=second load, 3=recovery)
        base_level: Starting level for this block (1-6)
        max_level: Maximum level allowed (from training age constraints)
        max_intensity: Maximum intensity sessions per week

    Returns:
        List of workout dicts: [{'slot': str, 'name': str, 'level': int, 'role': str}]
    """
    config = _load_selection_config()

    # Recovery week: strict rules
    if week_type == 'recovery':
        return _select_recovery_week(config)

    # Race week
    if week_type == 'race':
        return _select_race_week()

    # Load week: use phase × archetype matrix
    phase_config = config.get('phases', {}).get(phase)
    if not phase_config:
        phase_config = config['phases']['base']  # fallback

    slots = phase_config.get('slots', {})
    level = min(base_level + (week_in_block - 1), max_level)

    workouts = []
    intensity_count = 0

    # Intensity slots
    for slot_name in ['intensity_1', 'intensity_2', 'intensity_3']:
        if intensity_count >= max_intensity:
            break

        slot = slots.get(slot_name)
        if not slot:
            continue

        # Check archetype override
        name = _get_slot_workout(slot, archetype)
        if name is None:
            continue  # Skip (e.g., time_crunched skips intensity_3)

        # Rotate through alternatives across blocks for variety.
        # base_level changes per block (1→2→3...) so different blocks
        # get different workout selections from the alternatives list.
        alternatives = slot.get('alternatives', [])
        if alternatives and base_level > 1:
            all_options = [name] + alternatives
            name = all_options[(base_level - 1) % len(all_options)]

        workouts.append({
            'slot': slot_name,
            'name': name,
            'level': level,
            'role': 'intensity',
        })
        intensity_count += 1

    # Long ride — level must fit within weekly hour budget
    long_slot = slots.get('long_ride', {})
    long_name = _get_slot_workout(long_slot, archetype)
    if long_name:
        long_level_range = _get_level_range(long_slot, archetype)
        long_level = min(max(level, long_level_range[0]), long_level_range[1])
        long_level = min(long_level, max_level)

        # Budget check: long ride should be ≤40% of weekly hours
        max_long_min = hours_per_week * 60 * 0.40
        while long_level > 1:
            dur = get_workout_duration(long_name, long_level)
            if dur <= max_long_min:
                break
            long_level -= 1

        # If even L1 is too long, fall back to regular Endurance
        dur = get_workout_duration(long_name, long_level)
        if dur > max_long_min:
            # Find highest Endurance level that fits
            long_name = 'Endurance'
            long_level = 6
            while long_level > 1:
                dur = get_workout_duration('Endurance', long_level)
                if dur <= max_long_min:
                    break
                long_level -= 1

        workouts.append({
            'slot': 'long_ride',
            'name': long_name,
            'level': long_level,
            'role': 'long_ride',
        })

    # Filler slots (endurance + rest to fill remaining days)
    filler_slot = slots.get('filler', {})
    filler_name = _get_slot_workout(filler_slot, archetype)
    filler_level_range = _get_level_range(filler_slot, archetype)
    filler_level = min(filler_level_range[0], max_level)

    workouts.append({
        'slot': 'filler',
        'name': filler_name or 'Endurance',
        'level': filler_level,
        'role': 'filler',
    })

    return workouts


def _get_slot_workout(slot: dict, archetype: str) -> Optional[str]:
    """Get workout name from a slot, checking archetype overrides."""
    if not slot:
        return None

    overrides = slot.get('overrides', {})
    if archetype in overrides:
        override = overrides[archetype]
        if override is None:
            return None  # Explicitly skipped for this archetype
        return override.get('name', slot.get('default'))

    return slot.get('default')


def _get_level_range(slot: dict, archetype: str) -> Tuple[int, int]:
    """Get level range from a slot, checking archetype overrides."""
    if not slot:
        return (1, 6)

    overrides = slot.get('overrides', {})
    if archetype in overrides:
        override = overrides[archetype]
        if override and 'level_range' in override:
            return tuple(override['level_range'])

    return tuple(slot.get('level_range', [1, 6]))


def _select_recovery_week(config: dict) -> List[Dict[str, Any]]:
    """Recovery week: ONLY Endurance L1-L2 + one Openers. Sacred."""
    recovery_config = config.get('recovery_week', {})
    max_level = recovery_config.get('max_endurance_level', 2)

    return [
        {'slot': 'openers', 'name': 'Openers', 'level': 1, 'role': 'intensity'},
        {'slot': 'filler', 'name': 'Endurance', 'level': 1, 'role': 'filler'},
    ]


def _select_race_week() -> List[Dict[str, Any]]:
    """Race week: Openers mid-week + 1 easy ride + mostly rest.

    Block-builder spec: Mon OFF, Tue Openers, Wed Easy 45-60min,
    Thu OFF, Fri OFF (travel), Sat RACE, Sun OFF.
    """
    return [
        {'slot': 'openers', 'name': 'Openers', 'level': 2, 'role': 'intensity'},
        {'slot': 'filler', 'name': 'Rest Day', 'level': 1, 'role': 'rest'},
    ]


# ============================================================
# TSS budget for a workout
# ============================================================

def get_workout_tss(name: str, level: int) -> int:
    """Look up TSS for a workout name and level from the library.

    Returns 0 if not found.
    """
    library = _load_library()
    workout = library.get('workouts', {}).get(name)
    if not workout:
        return 0
    levels = workout.get('levels', {})
    level_data = levels.get(level, levels.get(str(level)))
    if not level_data:
        return 0
    return level_data.get('tss', 0)


def get_workout_duration(name: str, level: int) -> int:
    """Look up duration (minutes) for a workout name and level.

    Returns 0 if not found.
    """
    library = _load_library()
    workout = library.get('workouts', {}).get(name)
    if not workout:
        return 0
    levels = workout.get('levels', {})
    level_data = levels.get(level, levels.get(str(level)))
    if not level_data:
        return 0
    return level_data.get('duration', 0)


def estimate_week_tss(workouts: List[Dict[str, Any]], available_days: int = 6) -> int:
    """Estimate total weekly TSS from a workout list.

    Filler workouts are replicated to fill remaining days.
    """
    total = 0
    non_filler_count = 0

    for w in workouts:
        if w['role'] != 'filler':
            total += get_workout_tss(w['name'], w['level'])
            non_filler_count += 1

    # Fill remaining days with filler workout
    filler = next((w for w in workouts if w['role'] == 'filler'), None)
    if filler:
        filler_days = max(0, available_days - non_filler_count)
        # Alternate between filler workout and rest (not all days are filler)
        filler_riding_days = max(1, filler_days - 1)  # at least 1 rest day
        total += filler_riding_days * get_workout_tss(filler['name'], filler['level'])

    return total
