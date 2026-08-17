#!/usr/bin/env python3
"""
Block Chain — chains 3-week blocks across full plan duration.

Two entry points:

1. build_plan_from_calendar() — PREFERRED. Consumes week descriptors derived
   from plan_dates.yaml so the calendar (phases, recovery weeks, taper, race
   week, B-race overlays) is the single source of truth. The block-builder
   only decides WHAT workouts fill each week, never WHICH weeks are which.

2. chain_blocks() — legacy. Divides total plan weeks into its own 3-week
   Load/Load/Recovery cycle. Kept for backward compatibility; its week typing
   can disagree with plan_dates (recovery on different weeks, final block
   mis-phased), which produced broken plans. Do not use for new code.

Source: block-builder SKILL.md, adapted for continuous plan generation
"""

from typing import Dict, List, Any, Optional
from archetype import determine_phase
from block_builder import build_block, build_calendar_week
from series_tracker import SeriesTracker

# plan_dates phase → block-builder phase
CALENDAR_PHASE_MAP = {
    'base': 'base',
    'build': 'build',
    'peak': 'race_prep',
    'maintenance': 'base',  # steady aerobic upkeep between blocks
    'taper': 'taper',
    'race': 'race',
}


def _sync_week_totals(week: Dict[str, Any]) -> None:
    week['total_tss'] = sum(day.get('tss', 0) for day in week.get('days', []))
    week['total_duration'] = sum(day.get('duration', 0) for day in week.get('days', []))


def _raise_recovery_tss_floor(
    week: Dict[str, Any], preceding_load_average: float,
    day_caps: Optional[Dict[str, int]],
) -> None:
    """Bring a recovery week into the 50-65% house band with easy volume.

    Recovery weeks may use only Endurance L1/L2, Rest Day, and Openers.  The
    previous trim-only implementation could leave them at 41% of the actual
    preceding load.  Restore easy endurance first; never add intensity.
    """
    from workout_selector import get_workout_duration, get_workout_tss

    # Internal band is tighter than the R03 gate (50-65%): filling to the
    # exact gate edge left emitted plans at 66% after rounding drift, which
    # flags NEEDS_REVIEW on a boundary composition. Land mid-band.
    floor = preceding_load_average * 0.52
    ceiling = preceding_load_average * 0.63
    _sync_week_totals(week)

    # The initial recovery template can be above the ceiling for a
    # time-crunched athlete.  Remove only easy volume (never Openers) until
    # it is inside the same house band we enforce below.
    while week['total_tss'] > ceiling:
        candidates = []
        for day in week.get('days', []):
            if day.get('name') != 'Endurance':
                continue
            if day.get('level', 1) > 1:
                next_name, next_level = 'Endurance', day['level'] - 1
            elif day.get('role') == 'filler':
                next_name, next_level = 'Rest Day', 1
            else:
                continue
            next_duration = (get_workout_duration(next_name, next_level)
                             if next_name == 'Endurance' else 0)
            next_tss = (get_workout_tss(next_name, next_level)
                        if next_name == 'Endurance' else 0)
            reduction = day.get('tss', 0) - next_tss
            if reduction > 0 and week['total_tss'] - reduction >= floor:
                candidates.append((reduction, day, next_name, next_level,
                                   next_duration, next_tss))
        if not candidates:
            break
        excess = week['total_tss'] - ceiling
        sufficient = [item for item in candidates if item[0] >= excess]
        chosen = min(sufficient or candidates,
                     key=lambda item: item[0] if sufficient else -item[0])
        _, day, name, level, duration, tss = chosen
        day.update(name=name, level=level, duration=duration, tss=tss,
                   role='filler' if name == 'Rest Day' else day.get('role', 'filler'))
        _sync_week_totals(week)

    while week['total_tss'] < floor:
        candidates = []
        for day in week.get('days', []):
            name, level = day.get('name'), day.get('level', 1)
            if name == 'Rest Day':
                next_name, next_level = 'Endurance', 1
            elif name == 'Endurance' and level < 2:
                next_name, next_level = 'Endurance', level + 1
            else:
                continue
            next_duration = get_workout_duration(next_name, next_level)
            next_tss = get_workout_tss(next_name, next_level)
            cap = (day_caps or {}).get(day.get('day'), 0)
            if cap and next_duration > cap:
                continue
            delta = next_tss - day.get('tss', 0)
            if delta > 0 and week['total_tss'] + delta <= ceiling:
                candidates.append((delta, day, next_name, next_level,
                                   next_duration, next_tss))
        if not candidates:
            break
        # Prefer the smallest sufficient addition; if none is sufficient,
        # grow steadily with the largest available easy-volume increment.
        remaining = floor - week['total_tss']
        sufficient = [item for item in candidates if item[0] >= remaining]
        chosen = min(sufficient or candidates,
                     key=lambda item: item[0] if sufficient else -item[0])
        _, day, name, level, duration, tss = chosen
        day.update(name=name, level=level, duration=duration, tss=tss,
                   role='long_ride' if day.get('role') == 'long_ride' else 'filler')
        _sync_week_totals(week)


def protect_post_simulation_recovery(
    plan: Dict[str, Any], preferred_interval_days: Optional[List[str]] = None,
) -> set[tuple[int, str]]:
    """Make the calendar day after a long/dress simulation an easy bike day.

    A displaced sharpener is moved to a stated interval weekday in the same
    week when one is safe and available.  The returned ``(plan_week, day)``
    pairs are also blocked from strength placement by the package renderer.
    """
    from workout_selector import get_workout_duration, get_workout_tss

    preferred_interval_days = preferred_interval_days or ['Tue', 'Thu']
    flattened = [(week, day) for week in plan.get('weeks', [])
                 for day in week.get('days', [])]
    protected = set()
    changed_weeks = set()
    for index, (week, day) in enumerate(flattened[:-1]):
        simulation = day.get('act_simulation') or {}
        is_dress = bool(simulation.get('dress_rehearsal')
                        or day.get('is_dress_rehearsal'))
        is_long_sim = bool(simulation or day.get('is_simulation')) and day.get('duration', 0) >= 180
        if not (is_dress or is_long_sim):
            continue
        day['is_simulation'] = True
        day['is_dress_rehearsal'] = is_dress
        # A hard simulation also needs a clean runway.  This catches a
        # Sunday interval → Monday simulation across a week boundary.
        if index:
            previous_week, previous_day = flattened[index - 1]
            if previous_day.get('role') == 'intensity':
                previous_day.update(name='Endurance', level=1,
                                    duration=get_workout_duration('Endurance', 1),
                                    tss=get_workout_tss('Endurance', 1),
                                    role='filler', pre_sim_recovery=True)
                changed_weeks.add(id(previous_week))
        next_week, next_day = flattened[index + 1]
        protected.add((next_week.get('plan_week'), next_day.get('day')))
        next_day['post_sim_recovery'] = True

        displaced = dict(next_day) if next_day.get('role') == 'intensity' else None
        next_day.update(name='Endurance', level=1,
                        duration=get_workout_duration('Endurance', 1),
                        tss=get_workout_tss('Endurance', 1), role='filler')
        changed_weeks.add(id(next_week))

        # In the usual Sunday-simulation → taper-week shape this carries the
        # sharp stimulus from Monday to Thursday, the athlete's interval day.
        # Do not manufacture another hard workout when there was none.
        if displaced:
            for candidate in next_week.get('days', []):
                if (candidate.get('day') not in preferred_interval_days
                        or candidate.get('role') in ('off', 'long_ride', 'race')
                        or candidate.get('post_sim_recovery')):
                    continue
                candidate.update(
                    name=displaced['name'], level=displaced.get('level', 1),
                    duration=displaced.get('duration', 0),
                    tss=displaced.get('tss', 0), role='intensity')
                changed_weeks.add(id(next_week))
                break
    for week in plan.get('weeks', []):
        if id(week) in changed_weeks:
            _sync_week_totals(week)
    return protected


def derive_week_descriptors(plan_dates: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive calendar week descriptors from a plan_dates dict.

    THE single place that maps plan_dates week typing to block-builder
    week types. Production (generate_athlete_package) and tests must both
    use this — a private replica in either place reintroduces the
    calendar/builder drift that broke plans in June 2026.
    """
    descriptors = []
    for w in plan_dates.get('weeks', []):
        phase = w.get('phase', 'base')
        if w.get('is_race_week') or phase == 'race':
            week_type = 'race'
        elif phase == 'taper':
            week_type = 'taper'
        elif w.get('is_recovery_week'):
            week_type = 'recovery'
        else:
            week_type = 'load'
        # The block builder owns the shape around an A-race, but the calendar
        # remains the source of truth for *which day* is race day.  Keeping
        # that weekday here lets it put openers on day -1 without taking over
        # the renderer's race-day overlay.
        race_day = next(
            (d.get('day_abbrev') or d.get('day', '')[:3].title()
             for d in w.get('days', []) if d.get('is_race_day')),
            None,
        )
        descriptors.append({
            'plan_week': w['week'],
            'phase': phase,
            'week_type': week_type,
            'race_day': race_day,
        })
    return descriptors


def build_plan_from_calendar(
    week_descriptors: List[Dict[str, Any]],
    archetype: str,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    starting_level: int = 1,
    hours_per_week: float = 10,
    discipline: str = 'gravel',
    day_caps: Dict[str, int] = None,
    methodology: str = 'polarized_80_20',
    phase_block_start: int = 1,
    category_weights: Dict[str, float] = None,
    avoid_series: set = None,
    methodology_profile: Dict[str, Any] = None,
    fixed_minutes: int = 0,
    event_format: str = None,
    training_age: Optional[str] = None,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a full plan from calendar week descriptors (plan_dates truth).

    Args:
        week_descriptors: One dict per week, in order:
            {'plan_week': int (1-based),
             'phase': str  (plan_dates phase: base/build/peak/taper/race),
             'week_type': str ('load' | 'recovery' | 'taper' | 'race')}
        archetype: Athlete archetype ('time_crunched'|'specialist'|'volume'|'goat')
        max_level: Maximum workout level (training age constraint)
        max_intensity: Max intensity sessions per load week
        off_days: Preferred off days (day abbreviations, e.g. ['Sun'])
        long_ride_day: Preferred long ride day abbreviation
        starting_level: Level for the first load block
        hours_per_week: Weekly cycling hour target
        phase_block_start: 1-based rotation seed for the FIRST phase's
            workout-variety rotation. Standalone blocks (Endure /engine/block)
            pass the athlete's progression here so consecutive externally
            chained blocks pull different alternatives instead of repeating
            block 1's selections. Full-season plans keep the default (1).
        category_weights: Optional race-demand category scores biasing which
            names fill intensity/long-ride slots (see workout_selector).
        avoid_series: Optional set of series names the previous externally
            chained block used (/engine/block previous.seriesUsed) — slots
            prefer alternatives outside this set. Both default None →
            selection byte-identical to historical behavior.
        methodology_profile: Optional methodology profile
            (workout_selector.load_methodology_profile) whose category
            multipliers combine with category_weights and whose duration cap
            filters intensity pools. None (default, and the legacy
            full-season path) → selection unchanged.
        fixed_minutes: Immutable recurring load present in every week. The
            prescribed budget is reduced from *each week type's total target*,
            so recovery ratios operate on prescribed + external load.
        training_age: ``experienced`` or ``developing`` from the shared
            profile classifier.  It sets only the initial series entry level;
            all normal block progression and day-level adjustments remain in
            place.

    Returns:
        Plan dict shaped like chain_blocks() output: {'weeks': [...], ...}
    """
    if off_days is None:
        off_days = ['Mon']

    # A short plan cannot progress an experienced athlete from an introductory
    # L1 series to meaningful work before race day.  Set the series BASE once
    # at the calendar seam; selector progression still adds +1 per load week,
    # and the existing ramp-in/trim/cap logic can still down-level individual
    # emitted sessions.
    from workout_selector import series_entry_level

    tracker = SeriesTracker()
    tracker.start_block()

    all_weeks = []
    block_number = 1
    block_base_level = max(
        starting_level,
        series_entry_level(len(week_descriptors), training_age),
    )
    week_in_block = 1
    violations = []
    # Phase-local block index: rotation through workout alternatives uses
    # this (not the absolute block number) so the 2nd block of EVERY phase
    # reaches the first alternative. Absolute numbering skipped options when
    # a phase started at a high block number.
    phase_block_index = max(1, phase_block_start)
    prev_phase = None
    cadence_skill_level = 0

    for desc in week_descriptors:
        plan_week = desc['plan_week']
        bb_phase = CALENDAR_PHASE_MAP.get(desc.get('phase', 'base'), 'base')
        week_type = desc.get('week_type', 'load')

        if prev_phase is not None and bb_phase != prev_phase:
            # Phase transition closes the running block: workouts change
            # system (base VO2 → build threshold), so the series tracker
            # must not demand name coherence across the boundary.
            violations.extend(tracker.validate_block())
            tracker.end_block()
            tracker.start_block()
            block_number += 1
            phase_block_index = 1
            week_in_block = 1
        prev_phase = bb_phase

        if week_type == 'load':
            wk_intensity = max_intensity
        elif week_type == 'testing':
            wk_intensity = 2  # assessment battery (e.g. FTP + a second test)
        elif week_type == 'taper':
            wk_intensity = 2  # Thirty-Fifteens + cadence; taper is not recovery
        else:  # recovery, race
            wk_intensity = 1

        # build_calendar_week owns the multipliers below.  Reverse that
        # multiplier to give it a prescribed budget whose final total (after
        # G4 materializes fixed sessions) is the calendar's TOTAL target.
        target_multiplier = {
            'load': 1.10 if hours_per_week >= 6 else 1.15,
            'testing': 1.10 if hours_per_week >= 6 else 1.15,
            'recovery': 0.80, 'taper': 0.70, 'race': 0.60,
        }.get(week_type, 1.0)
        prescribed_hours = max(0.0, hours_per_week - fixed_minutes / (60 * target_multiplier))

        week = build_calendar_week(
            week_type=week_type,
            phase=bb_phase,
            archetype=archetype,
            block_number=phase_block_index,
            week_in_block=week_in_block,
            base_level=block_base_level,
            max_level=max_level,
            max_intensity=wk_intensity,
            off_days=off_days,
            long_ride_day=long_ride_day,
            hours_per_week=prescribed_hours,
            series_tracker=tracker,
            discipline=discipline,
            day_caps=day_caps,
            methodology=methodology,
            category_weights=category_weights,
            avoid_series=avoid_series,
            methodology_profile=methodology_profile,
            event_format=event_format,
            race_day=desc.get('race_day'),
            athlete_age=athlete_age,
            stress_level=stress_level,
        )
        week['plan_week'] = plan_week
        week['block_number'] = block_number

        # Cadence Work is a learned skill, unlike a phase-specific interval
        # series.  A new phase must not reissue its Level-1 introductory
        # copy after the athlete has already progressed through the pattern.
        for day in week.get('days', []):
            if day.get('name') != 'Cadence Work':
                continue
            level = max(day.get('level', 1), cadence_skill_level)
            if level != day.get('level', 1):
                from workout_selector import get_workout_duration, get_workout_tss
                day['level'] = level
                day['duration'] = get_workout_duration('Cadence Work', level)
                day['tss'] = get_workout_tss('Cadence Work', level)
            cadence_skill_level = max(cadence_skill_level, day['level'])

        if week_type == 'recovery':
            previous_loads = []
            for previous in reversed(all_weeks):
                if previous.get('week_type') != 'load':
                    break
                previous_loads.append(previous.get('total_tss', 0))
            if previous_loads:
                _raise_recovery_tss_floor(
                    week, sum(previous_loads) / len(previous_loads), day_caps)

        # Skill-floor corrections happen after the weekly builder's budget
        # pass.  Keep a raised cadence level from leaking a few extra minutes
        # over the athlete's calendar allowance by proportionally trimming
        # the longest remaining bike session (the renderer applies this cap).
        weekly_multiplier = {
            'load': 1.10 if hours_per_week >= 6 else 1.15,
            'testing': 1.10 if hours_per_week >= 6 else 1.15,
            'recovery': 0.80, 'taper': 0.70, 'race': 0.60,
        }.get(week_type)
        if weekly_multiplier is not None:
            budget = int(hours_per_week * 60 * weekly_multiplier)
            overflow = sum(d.get('duration', 0) for d in week.get('days', [])) - budget
            if overflow > 0:
                candidates = [d for d in week.get('days', [])
                              if d.get('duration', 0) > 0 and d.get('name') != 'Rest Day']
                if candidates:
                    longest = max(candidates, key=lambda d: d['duration'])
                    old_duration = longest['duration']
                    longest['duration'] = max(1, old_duration - overflow)
                    longest['tss'] = round(longest['tss'] * longest['duration'] / old_duration)
        _sync_week_totals(week)
        all_weeks.append(week)

        # Block bookkeeping: a recovery/taper/race week closes the block.
        # Level progression within a block comes from week_in_block
        # (workout selection adds week_in_block - 1 to base_level).
        if week_type == 'testing':
            # Standalone assessment block: the battery is one-off tests, not
            # a training series — close it so the series tracker never pairs
            # 'FTP Test' with the next block's intervals. No level bump
            # (tests aren't training load).
            violations.extend(tracker.validate_block())
            tracker.end_block()
            tracker.start_block()
            block_number += 1
            phase_block_index += 1
            week_in_block = 1
        elif week_type == 'load':
            tracker.advance_week()
            week_in_block += 1
        else:
            violations.extend(tracker.validate_block())
            tracker.end_block()
            tracker.start_block()
            block_number += 1
            phase_block_index += 1
            week_in_block = 1
            # Next block starts one level up, capped by training age.
            block_base_level = min(block_base_level + 1, max_level)

    return {
        'total_weeks': len(week_descriptors),
        'archetype': archetype,
        'num_blocks': block_number,
        'weeks': all_weeks,
        'all_violations': violations,
    }


def chain_blocks(
    total_weeks: int,
    archetype: str,
    weeks_to_race: int,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    starting_level: int = 1,
    hours_per_week: float = 10,
) -> Dict[str, Any]:
    """Build a complete training plan by chaining 3-week blocks.

    Args:
        total_weeks: Total plan duration in weeks
        archetype: Athlete archetype
        weeks_to_race: Weeks until A-race at plan start
        max_level: Maximum workout level (training age constraint)
        max_intensity: Max intensity per week
        off_days: Preferred off days
        long_ride_day: Preferred long ride day
        starting_level: Level to start first block at
        hours_per_week: Athlete's weekly cycling hours target

    Returns:
        Plan dict with all blocks and weeks
    """
    if off_days is None:
        off_days = ['Mon']

    tracker = SeriesTracker()
    blocks = []
    current_level = starting_level
    weeks_consumed = 0

    # Divide weeks into 3-week blocks
    num_full_blocks = total_weeks // 3
    remainder_weeks = total_weeks % 3

    for block_idx in range(num_full_blocks):
        # Determine phase for this block based on weeks remaining to race
        weeks_remaining = weeks_to_race - weeks_consumed
        phase = determine_phase(weeks_remaining)

        # Last block before race may be taper/race
        is_race_block = (block_idx == num_full_blocks - 1 and remainder_weeks == 0)

        block = build_block(
            phase=phase,
            archetype=archetype,
            block_number=block_idx + 1,
            base_level=current_level,
            max_level=max_level,
            max_intensity=max_intensity,
            off_days=off_days,
            long_ride_day=long_ride_day,
            hours_per_week=hours_per_week,
            series_tracker=tracker,
        )
        blocks.append(block)
        weeks_consumed += 3

        # Level progression: next block starts where the last load week ended
        # The series tracker holds the actual last level used per slot
        last_used = max(
            (tracker._active_series.get(slot, {}).get('last_level', current_level)
             for slot in tracker._active_series),
            default=current_level
        )
        current_level = min(last_used, max_level)

    # Handle remainder weeks (1-2 weeks before race)
    if remainder_weeks > 0:
        weeks_remaining = weeks_to_race - weeks_consumed
        phase = determine_phase(weeks_remaining)

        remainder_block = _build_remainder(
            weeks=remainder_weeks,
            phase=phase,
            archetype=archetype,
            block_number=len(blocks) + 1,
            base_level=current_level,
            max_level=max_level,
            off_days=off_days,
            long_ride_day=long_ride_day,
            tracker=tracker,
            hours_per_week=hours_per_week,
        )
        blocks.append(remainder_block)

    # Flatten to week list
    all_weeks = []
    plan_week = 1
    for block in blocks:
        for week in block.get('weeks', []):
            week['plan_week'] = plan_week
            all_weeks.append(week)
            plan_week += 1

    return {
        'total_weeks': total_weeks,
        'archetype': archetype,
        'num_blocks': len(blocks),
        'blocks': blocks,
        'weeks': all_weeks,
        'all_violations': [v for b in blocks for v in b.get('series_violations', [])],
    }


def _build_remainder(
    weeks: int,
    phase: str,
    archetype: str,
    block_number: int,
    base_level: int,
    max_level: int,
    off_days: List[str],
    long_ride_day: str,
    tracker: SeriesTracker,
    hours_per_week: float = 10,
) -> Dict[str, Any]:
    """Build a partial block for remainder weeks (1-2 weeks, typically taper/race).

    If 2 weeks: Load + Race Week
    If 1 week: Race Week only
    """
    from block_builder import _build_day_template, _build_week

    day_roles = _build_day_template(off_days, long_ride_day, 2)

    tracker.start_block()
    block_weeks = []

    if weeks == 2:
        # Week 1: Taper (reduced load)
        w1 = _build_week(
            week_num=1,
            week_type='load',
            phase='racing',  # Taper regardless of original phase
            archetype=archetype,
            day_roles=day_roles,
            base_level=base_level,
            max_level=max_level,
            max_intensity=1,  # Taper: minimal intensity
            series_tracker=tracker,
            week_in_block=1,
        )
        block_weeks.append(w1)
        tracker.advance_week()

    # Final week: Race week
    w_race = _build_week(
        week_num=len(block_weeks) + 1,
        week_type='race',
        phase='racing',
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=1,
        series_tracker=tracker,
        week_in_block=len(block_weeks) + 1,
        hours_per_week=hours_per_week,
    )
    block_weeks.append(w_race)

    tracker.end_block()

    return {
        'block_number': block_number,
        'phase': phase,
        'archetype': archetype,
        'base_level': base_level,
        'weeks': block_weeks,
        'series_violations': tracker.validate_block(),
        'is_remainder': True,
    }
