#!/usr/bin/env python3
"""
Block Chain — chains 3-week blocks across full plan duration.

Divides total plan weeks into sequential blocks (Load/Load/Recovery),
handling phase transitions and remainder weeks (taper/race).

Source: block-builder SKILL.md, adapted for continuous plan generation
"""

from typing import Dict, List, Any, Optional
from archetype import determine_phase
from block_builder import build_block
from series_tracker import SeriesTracker


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
