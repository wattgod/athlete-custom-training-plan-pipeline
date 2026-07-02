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
        descriptors.append({
            'plan_week': w['week'],
            'phase': phase,
            'week_type': week_type,
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

    Returns:
        Plan dict shaped like chain_blocks() output: {'weeks': [...], ...}
    """
    if off_days is None:
        off_days = ['Mon']

    tracker = SeriesTracker()
    tracker.start_block()

    all_weeks = []
    block_number = 1
    block_base_level = starting_level
    week_in_block = 1
    violations = []
    # Phase-local block index: rotation through workout alternatives uses
    # this (not the absolute block number) so the 2nd block of EVERY phase
    # reaches the first alternative. Absolute numbering skipped options when
    # a phase started at a high block number.
    phase_block_index = max(1, phase_block_start)
    prev_phase = None

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
        elif week_type in ('taper', 'testing'):
            wk_intensity = 2  # openers / assessment battery
        else:  # recovery, race
            wk_intensity = 1

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
            hours_per_week=hours_per_week,
            series_tracker=tracker,
            discipline=discipline,
            day_caps=day_caps,
            methodology=methodology,
        )
        week['plan_week'] = plan_week
        week['block_number'] = block_number
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
