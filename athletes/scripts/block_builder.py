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


def build_calendar_week(
    week_type: str,
    phase: str,
    archetype: str,
    block_number: int,
    week_in_block: int,
    base_level: int,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    hours_per_week: float = 10,
    series_tracker: Optional[SeriesTracker] = None,
    discipline: str = 'gravel',
    day_caps: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Build one week whose type and phase come from the calendar (plan_dates).

    Unlike build_block(), this does not impose a Load/Load/Recovery rhythm —
    the caller (build_plan_from_calendar) supplies week_type per week from
    plan_dates.yaml, the single source of scheduling truth.
    """
    if off_days is None:
        off_days = ['Mon']
    if series_tracker is None:
        series_tracker = SeriesTracker()
        series_tracker.start_block()

    day_roles = _build_day_template(off_days, long_ride_day, max_intensity)

    week = _build_week(
        week_num=week_in_block,
        week_type=week_type,
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=week_in_block,
        hours_per_week=hours_per_week,
        block_number=block_number,
        discipline=discipline,
        day_caps=day_caps,
    )
    week['block_number'] = block_number
    return week


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

    # Step 3: Place intensity on available non-consecutive days.
    # Must not be adjacent to other intensity days OR to the long ride day.
    # Preference order matches coach practice: Tue/Thu are the canonical
    # quality days (fresh after Monday, buffered from the weekend long ride).
    PREFERRED_INTENSITY_ORDER = ['Tue', 'Thu', 'Mon', 'Wed', 'Fri', 'Sat', 'Sun']
    available = [d for d in PREFERRED_INTENSITY_ORDER if d not in roles]
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


def _fit_workout_to_cap(workout: Dict[str, Any], cap: int) -> Dict[str, Any]:
    """Fit a workout to a per-day duration cap.

    Steps the level down until the library duration fits; as a last resort
    hard-caps the duration (the renderer scales the ZWO to match) with TSS
    scaled proportionally. Without this, athletes with '45min weekdays' got
    3-hour Wednesday workouts that only the WEEKLY budget noticed.
    """
    if not cap or cap <= 0 or workout.get('duration', 0) <= cap:
        return workout
    name = workout.get('name', '')
    level = workout.get('level', 1)
    while level > 1:
        level -= 1
        dur = get_workout_duration(name, level)
        if 0 < dur <= cap:
            workout['level'] = level
            workout['duration'] = dur
            workout['tss'] = get_workout_tss(name, level)
            return workout
    orig_dur = workout.get('duration', 0) or 1
    workout['tss'] = round(workout.get('tss', 0) * cap / orig_dur)
    workout['duration'] = cap
    return workout


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
    block_number: int = 1,
    discipline: str = 'gravel',
    day_caps: Dict[str, int] = None,
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
        block_number=block_number,
        discipline=discipline,
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
            # Race week: mostly rest. One easy ride (Wed), rest of filler = Rest Day.
            if week_type == 'race' and filler_count != 1:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 23, 'duration': 35, 'role': 'filler'}
            elif week_type == 'race' and filler_count == 1:
                # One easy ride mid-week
                workout = {'name': 'Endurance', 'level': 1, 'tss': 55, 'duration': 50, 'role': 'filler'}
            elif week_type == 'recovery' and filler_count > 0 and filler_count % 3 == 0:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 23, 'duration': 35, 'role': 'filler'}
            else:
                w = filler_workout or {'name': 'Endurance', 'level': 1}
                f_name = w['name']
                f_level = w['level']
                # Cycle the filler pool across filler days for variety.
                # Shift the cycle by week so the same weekday doesn't get the
                # same variant every single week.
                pool = w.get('pool')
                if pool and week_type == 'load':
                    f_name = pool[(filler_count + week_in_block - 1) % len(pool)]
                    if get_workout_duration(f_name, f_level) <= 0:
                        # Unknown level for this variant — clamp to a level
                        # the library defines, else fall back to Endurance.
                        for try_level in range(min(f_level, 6), 0, -1):
                            if get_workout_duration(f_name, try_level) > 0:
                                f_level = try_level
                                break
                        else:
                            f_name = 'Endurance'
                tss = get_workout_tss(f_name, f_level)
                dur = get_workout_duration(f_name, f_level)
                workout = {
                    'name': f_name,
                    'level': f_level,
                    'tss': tss,
                    'duration': dur,
                    'role': 'filler',
                }
            filler_count += 1

        # Per-day duration cap (athlete availability). Off days excluded.
        if day_caps and workout.get('role') != 'off' and workout.get('duration', 0) > 0:
            workout = _fit_workout_to_cap(workout, day_caps.get(day, 0))

        total_tss += workout.get('tss', 0)
        days.append({
            'day': day,
            **workout,
        })

    # Post-assignment budget trim: convert filler days to rest (starting
    # from the end) until within budget.
    # - Load weeks: hours x 1.10 (1.15 for very low-hour athletes)
    # - Recovery weeks: hours x 0.62 — a recovery week must actually unload.
    #   The fixed recovery template (~5h) was 80%+ of a low-hour athlete's
    #   load volume, defeating the purpose.
    if week_type == 'load':
        tolerance = 1.15 if hours_per_week < 6 else 1.10
        max_minutes = hours_per_week * 60 * tolerance
    elif week_type == 'recovery':
        # 0.55 of HOURS ≈ 50-70% of actual load volume across athletes
        # (load weeks land at 0.79-1.10 of stated hours), keeping recovery
        # inside the 50-65%-of-load coaching band.
        max_minutes = hours_per_week * 60 * 0.55
    elif week_type == 'taper':
        max_minutes = hours_per_week * 60 * 0.70
    elif week_type == 'race':
        max_minutes = hours_per_week * 60 * 0.60
    else:
        max_minutes = None

    if max_minutes is not None:
        total_duration = sum(d.get('duration', 0) for d in days)
        if total_duration > max_minutes:
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

        # Fillers exhausted but still over budget (time-crunched athletes in
        # high-level blocks): step the longest intensity/long-ride workout
        # down a level at a time until the week fits or everything is at L1.
        total_duration = sum(d.get('duration', 0) for d in days)
        while total_duration > max_minutes:
            candidates = [d for d in days
                          if d.get('role') in ('intensity', 'long_ride')
                          and d.get('level', 1) > 1]
            if not candidates:
                break
            longest = max(candidates, key=lambda d: d.get('duration', 0))
            new_level = longest['level'] - 1
            new_dur = get_workout_duration(longest['name'], new_level)
            new_tss = get_workout_tss(longest['name'], new_level)
            if new_dur <= 0:
                # Library gap — treat as unloweable, stop trying this one
                longest['level'] = 1
                continue
            total_duration -= (longest['duration'] - new_dur)
            total_tss -= (longest['tss'] - new_tss)
            longest['level'] = new_level
            longest['duration'] = new_dur
            longest['tss'] = new_tss

    return {
        'week_num': week_num,
        'week_type': week_type,
        'phase': phase,
        'total_tss': total_tss,
        'total_duration': sum(d.get('duration', 0) for d in days),
        'days': days,
    }
