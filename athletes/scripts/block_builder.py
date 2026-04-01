#!/usr/bin/env python3
"""
Block Builder — constructs a single 3-week training block.

Standard block = 2 Load weeks + 1 Recovery week.
Each load week gets intensity, long ride, and filler workouts assigned
from the phase × archetype matrix. Recovery week is sacred (Endurance L1-L2 + Openers only).

Source: block-builder SKILL.md Steps 3-6
"""

from typing import Dict, List, Any, Optional
from workout_selector import (
    select_workouts_for_week,
    get_workout_tss,
    get_workout_duration,
    estimate_week_tss,
)
from series_tracker import SeriesTracker

# Day template: standard week structure
# Intensity days are non-consecutive, long ride on weekend
STANDARD_DAY_TEMPLATE = {
    # day: role
    'Mon': 'off_or_strength',
    'Tue': 'intensity',
    'Wed': 'filler',
    'Thu': 'intensity',
    'Fri': 'off_or_strength',
    'Sat': 'long_ride',
    'Sun': 'filler',
}

DAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def build_block(
    phase: str,
    archetype: str,
    block_number: int,
    base_level: int,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    available_days: int = 6,
    hours_per_week: float = 10,
    series_tracker: Optional[SeriesTracker] = None,
) -> Dict[str, Any]:
    """Build a single 3-week training block.

    Args:
        phase: Training phase ('base', 'build', 'race_prep', 'racing')
        archetype: Athlete archetype
        block_number: Block sequence number (1-indexed)
        base_level: Starting workout level for this block
        max_level: Maximum level (training age constraint)
        max_intensity: Max intensity sessions per week
        off_days: Athlete's preferred off days (e.g., ['Mon', 'Fri'])
        long_ride_day: Preferred long ride day
        available_days: Total training days per week
        series_tracker: Optional tracker for cross-block coherence

    Returns:
        Block dict with 3 weeks of day-by-day workout assignments
    """
    if off_days is None:
        off_days = ['Mon']
    if series_tracker is None:
        series_tracker = SeriesTracker()

    series_tracker.start_block()

    # Build day template from athlete preferences
    day_roles = _build_day_template(off_days, long_ride_day, max_intensity)

    weeks = []

    # Week 1: Load
    w1 = _build_week(
        week_num=1,
        week_type='load',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=1,
        hours_per_week=hours_per_week,
    )
    weeks.append(w1)

    series_tracker.advance_week()

    # Week 2: Load (+1 level)
    w2 = _build_week(
        week_num=2,
        week_type='load',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=2,
        hours_per_week=hours_per_week,
    )
    weeks.append(w2)

    series_tracker.advance_week()

    # Week 3: Recovery (sacred)
    w3 = _build_week(
        week_num=3,
        week_type='recovery',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=1,  # Recovery: max 1 (openers only)
        series_tracker=series_tracker,
        week_in_block=3,
        hours_per_week=hours_per_week,
    )
    weeks.append(w3)

    series_tracker.end_block()

    # Validate series coherence
    violations = series_tracker.validate_block()

    return {
        'block_number': block_number,
        'phase': phase,
        'archetype': archetype,
        'base_level': base_level,
        'weeks': weeks,
        'series_violations': violations,
    }


def _build_day_template(
    off_days: List[str],
    long_ride_day: str,
    max_intensity: int,
) -> Dict[str, str]:
    """Build a day-by-day role template from athlete preferences.

    Rules:
    1. Mark off days first
    2. Place long ride on preferred day
    3. Place intensity on non-consecutive days
    4. Fill remaining with filler (endurance)
    """
    roles = {}

    # Step 1: Off days
    for day in off_days:
        roles[day] = 'off'

    # Step 2: Long ride day
    roles[long_ride_day] = 'long_ride'

    # Step 3: Place intensity on available non-consecutive days
    # Must not be adjacent to other intensity days OR to the long ride day
    available = [d for d in DAY_ORDER if d not in roles]
    hard_days = [long_ride_day]  # Long ride counts as "hard" for adjacency
    intensity_days = []
    for d in available:
        if len(intensity_days) >= max_intensity:
            break
        d_idx = DAY_ORDER.index(d)
        adjacent_to_hard = any(
            abs(DAY_ORDER.index(existing) - d_idx) <= 1
            for existing in hard_days
        )
        if not adjacent_to_hard:
            intensity_days.append(d)
            hard_days.append(d)
            roles[d] = 'intensity'

    # Step 4: Fill remaining with filler
    for day in DAY_ORDER:
        if day not in roles:
            roles[day] = 'filler'

    return roles


def _build_week(
    week_num: int,
    week_type: str,
    phase: str,
    archetype: str,
    day_roles: Dict[str, str],
    base_level: int,
    max_level: int,
    max_intensity: int,
    series_tracker: SeriesTracker,
    week_in_block: int,
    hours_per_week: float = 10,
) -> Dict[str, Any]:
    """Build a single week with day-by-day workout assignments."""

    # Get workout menu for this week
    workout_menu = select_workouts_for_week(
        phase=phase,
        archetype=archetype,
        week_type=week_type,
        week_in_block=week_in_block,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        hours_per_week=hours_per_week,
    )

    # Organize menu by role
    intensity_workouts = [w for w in workout_menu if w['role'] == 'intensity']
    long_ride_workout = next((w for w in workout_menu if w['role'] == 'long_ride'), None)
    filler_workout = next((w for w in workout_menu if w['role'] == 'filler'), None)
    rest_workout = next((w for w in workout_menu if w['role'] == 'rest'), None)

    # Assign workouts to days
    days = []
    intensity_idx = 0
    total_tss = 0
    filler_count = 0  # Track filler days for recovery week rest alternation

    for day in DAY_ORDER:
        role = day_roles.get(day, 'filler')
        workout = None

        if role == 'off':
            workout = {'name': 'OFF', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'off'}

        elif role == 'intensity' and intensity_idx < len(intensity_workouts):
            w = intensity_workouts[intensity_idx]
            # Track series coherence
            slot = w.get('slot', f'intensity_{intensity_idx + 1}')
            tracked = series_tracker.assign(slot, w['name'], w['level'])
            tss = get_workout_tss(tracked['name'], tracked['level'])
            dur = get_workout_duration(tracked['name'], tracked['level'])
            workout = {
                'name': tracked['name'],
                'level': tracked['level'],
                'tss': tss,
                'duration': dur,
                'role': 'intensity',
                'series_coherent': tracked['coherent'],
            }
            intensity_idx += 1

        elif role == 'long_ride' and long_ride_workout:
            w = long_ride_workout
            tss = get_workout_tss(w['name'], w['level'])
            dur = get_workout_duration(w['name'], w['level'])
            workout = {
                'name': w['name'],
                'level': w['level'],
                'tss': tss,
                'duration': dur,
                'role': 'long_ride',
            }

        elif role == 'intensity' and week_type == 'recovery':
            # Recovery week: intensity slots that aren't openers become filler
            w = filler_workout or {'name': 'Endurance', 'level': 1}
            tss = get_workout_tss(w['name'], w['level'])
            dur = get_workout_duration(w['name'], w['level'])
            workout = {
                'name': w['name'], 'level': w['level'],
                'tss': tss, 'duration': dur, 'role': 'filler',
            }

        else:
            # Filler — recovery weeks alternate endurance with rest
            if week_type == 'recovery' and filler_count > 0 and filler_count % 3 == 0:
                # Every other filler day is rest during recovery
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 23, 'duration': 35, 'role': 'filler'}
            else:
                w = filler_workout or {'name': 'Endurance', 'level': 1}
                tss = get_workout_tss(w['name'], w['level'])
                dur = get_workout_duration(w['name'], w['level'])
                workout = {
                    'name': w['name'],
                    'level': w['level'],
                    'tss': tss,
                    'duration': dur,
                    'role': 'filler',
                }
            filler_count += 1

        total_tss += workout.get('tss', 0)
        days.append({
            'day': day,
            **workout,
        })

    # Post-assignment budget trim: if total exceeds hours_per_week × 1.10,
    # convert filler days to rest (starting from the end) until within budget
    tolerance = 1.15 if hours_per_week < 6 else 1.10
    max_minutes = hours_per_week * 60 * tolerance
    total_duration = sum(d.get('duration', 0) for d in days)
    if total_duration > max_minutes and week_type == 'load':
        for i in range(len(days) - 1, -1, -1):
            if total_duration <= max_minutes:
                break
            if days[i]['role'] == 'filler' and days[i]['name'] != 'Rest Day':
                removed_dur = days[i]['duration']
                removed_tss = days[i]['tss']
                days[i] = {
                    'day': days[i]['day'], 'name': 'Rest Day', 'level': 1,
                    'tss': 23, 'duration': 35, 'role': 'filler',
                }
                total_duration -= (removed_dur - 35)
                total_tss -= (removed_tss - 23)

    return {
        'week_num': week_num,
        'week_type': week_type,
        'phase': phase,
        'total_tss': total_tss,
        'total_duration': sum(d.get('duration', 0) for d in days),
        'days': days,
    }
