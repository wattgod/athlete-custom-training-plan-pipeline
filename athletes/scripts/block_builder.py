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
    methodology: str = 'polarized_80_20',
    category_weights: Dict[str, float] = None,
    avoid_series: set = None,
    methodology_profile: Dict[str, Any] = None,
    event_format: str = None,
    race_day: Optional[str] = None,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one week whose type and phase come from the calendar (plan_dates).

    Unlike build_block(), this does not impose a Load/Load/Recovery rhythm —
    the caller (build_plan_from_calendar) supplies week_type per week from
    plan_dates.yaml, the single source of scheduling truth.

    category_weights / avoid_series / methodology_profile (all optional,
    default None → behavior unchanged) bias WHICH names fill the
    intensity/long-ride slots — see workout_selector.select_workouts_for_week.
    """
    if off_days is None:
        off_days = ['Mon']
    if series_tracker is None:
        series_tracker = SeriesTracker()
        series_tracker.start_block()

    day_roles = _build_day_template(off_days, long_ride_day, max_intensity, week_type=week_type)

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
        methodology=methodology,
        category_weights=category_weights,
        avoid_series=avoid_series,
        methodology_profile=methodology_profile,
        event_format=event_format,
        race_day=race_day,
        athlete_age=athlete_age,
        stress_level=stress_level,
    )
    week['block_number'] = block_number
    return week


def _build_day_template(
    off_days: List[str],
    long_ride_day: str,
    max_intensity: int,
    week_type: Optional[str] = None,
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

    # Step 3: Place intensity days.
    # Preference order matches coach practice: Tue/Thu are the canonical
    # quality days (fresh after Monday, buffered from the weekend long ride).
    PREFERRED_INTENSITY_ORDER = ['Tue', 'Thu', 'Mon', 'Wed', 'Fri', 'Sat', 'Sun']
    available = [d for d in PREFERRED_INTENSITY_ORDER if d not in roles]

    if week_type == 'testing':
        # Testing weeks are an assessment battery, not two interchangeable
        # quality days: the coach's design intent (workout_selector's
        # _select_testing_week docstring) is FTP earlier in the week,
        # anaerobic later, because the anaerobic test's %FTP targets depend
        # on a fresh FTP number. The generic preference-order pick below
        # ("Tue/Thu are canonical") is chronologically blind -- on a
        # Tue-off schedule it picked Thu then wrapped back to Monday, which
        # a downstream chronological zip then read as FTP-Monday /
        # Anaerobic-Thursday, ahead of the very FTP test meant to set its
        # zones. Pick the earliest viable day for FTP, then the earliest
        # LATER viable day (>= 2 days after when one exists) for anaerobic.
        # This intentionally does NOT apply the long-ride adjacency
        # exclusion used below -- a short anaerobic assessment the day
        # before the long ride is coach-acceptable; wrapping it earlier
        # than the FTP test it depends on is not.
        if available:
            ftp_day = available[0]
            ftp_idx = DAY_ORDER.index(ftp_day)
            later = sorted(
                (d for d in available
                 if d != ftp_day and DAY_ORDER.index(d) > ftp_idx),
                key=lambda d: DAY_ORDER.index(d),
            )
            gapped = [d for d in later if DAY_ORDER.index(d) - ftp_idx >= 2]
            anaerobic_day = (gapped or later or [None])[0]
            intensity_days = [ftp_day] + ([anaerobic_day] if anaerobic_day else [])
            intensity_days = intensity_days[:max(1, max_intensity)]
            for d in intensity_days:
                roles[d] = 'intensity'
    else:
        # Place intensity on available non-consecutive days. Must not be
        # adjacent to other intensity days OR to the long ride day.
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
    methodology: str = 'polarized_80_20',
    category_weights: Dict[str, float] = None,
    avoid_series: set = None,
    methodology_profile: Dict[str, Any] = None,
    event_format: str = None,
    race_day: Optional[str] = None,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a single week with day-by-day workout assignments."""

    # Race day itself still defers to the legacy A-race overlay at render
    # time.  The block builder only supplies the deliberate house shape
    # around it: sharpener, easy endurance, day-before openers, and explicit
    # rest on every other available day.
    if week_type == 'race':
        return _build_race_week(
            week_num=week_num,
            phase=phase,
            off_days=[d for d, role in day_roles.items() if role == 'off'],
            race_day=race_day,
            day_caps=day_caps,
            athlete_age=athlete_age,
            stress_level=stress_level,
        )

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
        methodology=methodology,
        category_weights=category_weights,
        avoid_series=avoid_series,
        methodology_profile=methodology_profile,
        event_format=event_format,
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
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'filler'}
            elif week_type == 'race' and filler_count == 1:
                # One easy ride mid-week
                workout = {'name': 'Endurance', 'level': 1, 'tss': 55, 'duration': 50, 'role': 'filler'}
            elif week_type == 'recovery' and filler_count > 0 and filler_count % 3 == 0:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'filler'}
            else:
                w = filler_workout or {'name': 'Endurance', 'level': 1}
                f_name = w['name']
                f_level = w['level']
                # Cycle the filler pool across filler days for variety.
                # Shift the cycle by week so the same weekday doesn't get the
                # same variant every single week.
                pool = w.get('pool')
                if pool and week_type in ('load', 'testing', 'taper'):
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
                if f_name == 'Cadence Work' and week_type == 'load':
                    # Cadence is a skill series, not disposable filler: keep
                    # its familiar session but progress one level per load
                    # week (longer work blocks / higher-rpm holds) just like
                    # the named intensity series.
                    f_level = min(f_level + max(0, week_in_block - 1), max_level)
                # The generic Endurance Blocks renderer snaps its component
                # segments to whole minutes and can render one minute longer
                # than its catalog duration.  Do not put that variant exactly
                # on a stated cap; choose the standard Endurance member of the
                # same existing filler pool so the emitted file stays within
                # the athlete's availability, not merely the planner card.
                cap = (day_caps or {}).get(day, 0)
                if (f_name == 'Endurance Blocks' and cap
                        and get_workout_duration(f_name, f_level) >= cap):
                    f_name, f_level = 'Endurance', 1
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
    if week_type in ('load', 'testing'):
        tolerance = 1.15 if hours_per_week < 6 else 1.10
        max_minutes = hours_per_week * 60 * tolerance
    elif week_type == 'recovery':
        # Preserve enough low-intensity volume to meet the 50-65% recovery
        # TSS floor against the preceding load block.  The old 0.55 cap,
        # combined with Rest-Day pseudo-TSS, emitted closer to 40%.
        max_minutes = hours_per_week * 60 * 0.80
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
                        'tss': 0, 'duration': 0, 'role': 'filler',
                    }
                    total_duration -= removed_dur
                    total_tss -= removed_tss

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

        # A library can leave a small remainder after every eligible session
        # is at L1 (for example, 397 min against a 396-min budget).  The
        # emitted renderer already supports duration scaling, so trim the
        # longest remaining ride rather than shipping an over-budget week.
        total_duration = sum(d.get('duration', 0) for d in days)
        if total_duration > max_minutes:
            candidates = [d for d in days if d.get('duration', 0) > 0
                          and d.get('name') != 'Rest Day']
            if candidates:
                longest = max(candidates, key=lambda d: d['duration'])
                old_duration = longest['duration']
                new_duration = max(1, old_duration - (total_duration - max_minutes))
                longest['duration'] = new_duration
                longest['tss'] = round(longest['tss'] * new_duration / old_duration)

    # Grow-to-floor: the trim above only shrinks. Without growth, LOAD
    # weeks for high-volume athletes filled at ~50% of stated hours (a
    # 16h GOAT got 8.2h base weeks). Level UP until the week reaches the
    # floor — long ride first (cheapest quality volume), then fillers —
    # respecting per-day caps and the level ceiling.
    # The first base block is the deliberate ramp-in — no floor there.
    if (max_minutes is not None and week_type == 'load'
            and not (phase == 'base' and block_number <= 1)):
        # Phase-aware floor preserves periodized PROGRESSION: base ramps
        # (lower floor, rising per block) while build/peak fill near target.
        # A flat 0.80 floor made W1 as big as W19.
        if phase == 'base':
            floor_pct = min(0.62 + 0.05 * max(block_number - 1, 0), 0.75)
        elif phase == 'build':
            floor_pct = 0.82
        elif phase == 'peak':
            floor_pct = 0.86
        else:
            floor_pct = 0.72
        floor_minutes = hours_per_week * 60 * floor_pct
        total_duration = sum(d.get('duration', 0) for d in days)
        guard = 0
        while total_duration < floor_minutes and guard < 40:
            guard += 1
            candidates = [d for d in days
                          if d.get('role') in ('long_ride', 'filler')
                          and d.get('name') != 'Rest Day'
                          and d.get('level', 1) < max_level]
            # long ride grows before fillers
            candidates.sort(key=lambda d: (d.get('role') != 'long_ride',
                                           d.get('duration', 0)))
            grew = False
            for d in candidates:
                new_level = d['level'] + 1
                new_dur = get_workout_duration(d['name'], new_level)
                new_tss = get_workout_tss(d['name'], new_level)
                if new_dur <= d.get('duration', 0):
                    continue
                cap = (day_caps or {}).get(d['day'], 0)
                if cap and new_dur > cap:
                    continue
                delta = new_dur - d['duration']
                if total_duration + delta > max_minutes:
                    continue
                # don't overshoot the floor by more than 8% — overshoot in
                # base weeks flattened the base->peak volume progression
                if total_duration + delta > floor_minutes * 1.08:
                    continue
                total_duration += (new_dur - d['duration'])
                total_tss += (new_tss - d.get('tss', 0))
                d['level'] = new_level
                d['duration'] = new_dur
                d['tss'] = new_tss
                grew = True
                break
            if not grew:
                break

    # The grow-to-floor pass can land on a floating-point budget boundary
    # (e.g. 396.00000000000006) and reintroduce a one-minute overage. Keep
    # the emitted calendar within the integer-minute availability contract.
    if max_minutes is not None:
        total_duration = sum(d.get('duration', 0) for d in days)
        integer_budget = int(max_minutes)
        if total_duration > integer_budget:
            candidates = [d for d in days if d.get('duration', 0) > 0
                          and d.get('name') != 'Rest Day']
            if candidates:
                longest = max(candidates, key=lambda d: d['duration'])
                old_duration = longest['duration']
                new_duration = max(1, old_duration - (total_duration - integer_budget))
                longest['duration'] = new_duration
                longest['tss'] = round(longest['tss'] * new_duration / old_duration)

    return {
        'week_num': week_num,
        'week_type': week_type,
        'phase': phase,
        'total_tss': total_tss,
        'total_duration': sum(d.get('duration', 0) for d in days),
        'days': days,
    }


def _build_race_week(
    week_num: int,
    phase: str,
    off_days: List[str],
    race_day: Optional[str],
    day_caps: Optional[Dict[str, int]],
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the coach-approved race-week microcycle.

    The race is represented as a zero-load placeholder because the existing
    rendering overlay owns the actual race-day plan.  That keeps the planner
    and renderer responsibilities separate while making every surrounding
    rest day explicit in the calendar model.
    """
    race_day = race_day if race_day in DAY_ORDER else 'Sat'
    race_index = DAY_ORDER.index(race_day)
    opener_day = DAY_ORDER[(race_index - 1) % len(DAY_ORDER)]

    def _session(name, level, role, duration=None, tss=None):
        duration = get_workout_duration(name, level) if duration is None else duration
        tss = get_workout_tss(name, level) if tss is None else tss
        return {'name': name, 'level': level, 'tss': tss, 'duration': duration, 'role': role}

    # The sharpener is selected as a race-week slot first, then calibrated
    # against the actual rendered ZWO dose.  This avoids relying on a stale
    # library estimate or a single hand-tuned archetype level.
    from workout_mapper import calibrate_race_week_sharpener
    sharpener_dose = calibrate_race_week_sharpener(
        requested_level=2, athlete_age=athlete_age, stress_level=stress_level)

    # Quality-day preference is intentionally the same as the normal week
    # template.  Do not place the sharpener adjacent to day-before openers.
    sharpener_day = next(
        (day for day in ('Tue', 'Thu', 'Mon', 'Wed', 'Fri', 'Sat', 'Sun')
         if day not in off_days and day not in (race_day, opener_day)
         and DAY_ORDER.index(day) < race_index
         and abs(DAY_ORDER.index(day) - DAY_ORDER.index(opener_day)) > 1),
        None,
    )
    easy_day = next(
        (day for day in ('Wed', 'Thu', 'Tue', 'Mon', 'Fri', 'Sat', 'Sun')
         if day not in off_days and day not in (race_day, opener_day, sharpener_day)
         and DAY_ORDER.index(day) < race_index),
        None,
    )

    days = []
    for day in DAY_ORDER:
        if day == race_day:
            workout = {'name': 'RACE_DAY', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'race'}
        elif day in off_days:
            workout = {'name': 'OFF', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'off'}
        elif day == opener_day:
            workout = _session('Openers', 2, 'intensity')
        elif day == sharpener_day:
            workout = _session(
                'Stars In Your Eyes', sharpener_dose['level'], 'intensity',
                duration=round(sharpener_dose['duration_min']),
                tss=sharpener_dose['tss'],
            )
        elif day == easy_day:
            # Keep this deliberate middle-of-week ride in the 45-60min house
            # range rather than emitting a normal 70min Endurance L1.
            workout = _session('Endurance', 1, 'filler', duration=50, tss=39)
        else:
            workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'rest'}

        if day_caps and workout['role'] not in ('off', 'race') and workout['duration'] > 0:
            workout = _fit_workout_to_cap(workout, day_caps.get(day, 0))
        days.append({'day': day, **workout})

    return {
        'week_num': week_num,
        'week_type': 'race',
        'phase': phase,
        'total_tss': sum(d['tss'] for d in days),
        'total_duration': sum(d['duration'] for d in days),
        'days': days,
    }
