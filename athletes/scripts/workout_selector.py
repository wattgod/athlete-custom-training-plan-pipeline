#!/usr/bin/env python3
"""
Workout Selector — Phase × Archetype → Specific Workout Names + Levels

Implements the block-builder's workout selection matrix (workout-selection.md).
Given a phase, archetype, and week position, returns the exact workout name
and level for each day slot.

Source: block-builder SKILL.md Steps 4-6, references/workout-selection.md
"""

import yaml
import functools
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# Load workout selection config
_CONFIG_DIR = Path(__file__).parent.parent / 'config'

# What makes the four methods produce DIFFERENT plans (not just labels): the VO2
# day stays for compliance, but the second hard day reflects the method's
# signature. A POOL per method (rotated by block) keeps block-to-block variety;
# discipline-specific work is left untouched so gravel/mtb still feel distinct.
# Every name is renderable and survives that method's render-time veto.
_METHODOLOGY_SECONDARY = {
    'polarized_80_20':       ['Threshold Progressive', 'Threshold Accumulation', 'VO2max 40/20'],
    'time_crunched':         ['Threshold Progressive', 'Threshold Touch', 'VO2max 40/20'],
    'g_spot':                ['G-Spot', 'Threshold Touch', 'Threshold Steady'],
    'traditional_pyramidal': ['Tempo with Accelerations', 'Tempo with Sprints', 'Threshold Steady'],
}
# Discipline-specific intensity work — never overwritten, so a gravel/mtb plan
# keeps its signature work alongside the methodology emphasis.
_DISCIPLINE_INTENSITY = {
    'Microbursts', 'Mixed Climbing', 'Mixed Climbing Variations', 'Stomps',
}


@functools.lru_cache(maxsize=None)
def _load_config(filename: str) -> dict:
    """Load a YAML config, cached for the process lifetime.

    The configs are static package data; without the cache, every
    get_workout_tss/get_workout_duration lookup re-parsed the YAML
    (~700ms per generated block — the /engine/block endpoint needs <500ms).
    Callers must NOT mutate the returned dict (all current callers copy
    before modifying).
    """
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
    block_number: int = 1,
    discipline: str = 'gravel',
    methodology: str = 'polarized_80_20',
) -> List[Dict[str, Any]]:
    """Select workouts for a single week.

    Args:
        phase: Training phase ('base', 'build', 'race_prep', 'racing')
        archetype: Athlete archetype ('time_crunched', 'specialist', 'volume', 'goat')
        week_type: 'load', 'recovery', 'taper', or 'race'
        week_in_block: Position within block (1=first load week, ...)
        base_level: Starting level for this block (1-6)
        max_level: Maximum level allowed (from training age constraints)
        max_intensity: Maximum intensity sessions per week
        block_number: 1-based block sequence number. Drives rotation through
            intensity/long-ride alternatives so adjacent blocks never repeat
            the same workout names, and the filler level ladder.

    Returns:
        List of workout dicts: [{'slot': str, 'name': str, 'level': int, 'role': str}]
        Filler dicts may carry a 'pool' key (list of names) that the week
        builder cycles across filler days for day-to-day variety.
    """
    config = _load_selection_config()

    # Recovery week: strict rules
    if week_type == 'recovery':
        return _select_recovery_week(config, hours_per_week)

    # Taper week: openers + short rides only
    if week_type == 'taper':
        return _select_taper_week(hours_per_week)

    # Testing week: assessment battery instead of training intensity
    if week_type == 'testing':
        return _select_testing_week(hours_per_week, max_level)

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

    # Intensity slots — VO2max FIRST when the budget is tight. The build-phase
    # VO2 slot is intensity_2, but a low-training-age athlete (max_intensity=1)
    # would fill only intensity_1 (threshold) and never get VO2 → a 6-7 week
    # VO2 gap → R02 gate failure → refunded order. Prioritising the VO2 slot
    # guarantees VO2 is the workout that's KEPT, not the one dropped, in every
    # phase. (Stable: non-VO2 slots keep their relative order.)
    try:
        from block_compliance import VO2MAX_TYPES as _VO2
    except Exception:
        _VO2 = set()

    def _is_vo2_slot(sn):
        s = slots.get(sn) or {}
        nm = _get_slot_workout(s, archetype) or s.get('default', '')
        return nm in _VO2

    intensity_slots = sorted(['intensity_1', 'intensity_2', 'intensity_3'],
                             key=lambda sn: 0 if _is_vo2_slot(sn) else 1)

    # Intensity slots
    for slot_name in intensity_slots:
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
        # block_number advances per mesocycle, so adjacent blocks pull
        # different names from the alternatives list while series
        # coherence (same name within a block) is preserved.
        # Discipline overlays widen the pool (gravel → Microbursts /
        # Mixed Climbing, road → threshold variants, mtb → sprints).
        # Extras are inserted at the FRONT of the alternatives so the
        # second block in a phase already hits discipline-specific work.
        alternatives = list(slot.get('alternatives', []))
        discipline_overlay = (config.get('disciplines', {})
                              .get(discipline, {})
                              .get(phase, {})
                              .get(slot_name, {}))
        for pos, extra in enumerate(discipline_overlay.get('extra_alternatives', [])):
            if extra != name and extra not in alternatives:
                alternatives.insert(pos, extra)
        if alternatives:
            all_options = [name] + alternatives
            name = all_options[(block_number - 1) % len(all_options)]

        workouts.append({
            'slot': slot_name,
            'name': name,
            'level': level,
            'role': 'intensity',
        })
        intensity_count += 1

    # ── Methodology emphasis: the plan now GENUINELY differs by method ──────
    # The block-builder picks compliant slots; the selected methodology then
    # steers the SECONDARY (non-VO2) intensity day toward its signature work —
    # a G Spot plan rides G-Spot/over-unders, a Pyramidal plan rides tempo
    # progressions, a Polarized / Time-Crunched plan stays hard threshold. The
    # VO2 stimulus is preserved (R02), and series coherence holds because the
    # same emphasis name repeats across the block. This also ALIGNS the choice
    # with the render-time methodology veto (POLARIZED vetoes G-Spot, etc.), so
    # the workout survives instead of silently falling back to a generic one.
    pool = _METHODOLOGY_SECONDARY.get(methodology)
    if pool:
        from block_compliance import VO2MAX_TYPES
        pick = pool[(block_number - 1) % len(pool)]  # rotate by block → variety
        for w in workouts:
            if (w['role'] == 'intensity'
                    and w['name'] not in VO2MAX_TYPES
                    and w['name'] not in _DISCIPLINE_INTENSITY):
                w['name'] = pick
                break

    # Long ride — level must fit within weekly hour budget
    long_slot = slots.get('long_ride', {})
    long_name = _get_slot_workout(long_slot, archetype)
    # Rotate long-ride variants across blocks (only when no archetype
    # override pinned a specific ride).
    long_alternatives = long_slot.get('alternatives', [])
    if long_name and long_alternatives and archetype not in long_slot.get('overrides', {}):
        long_options = [long_name] + long_alternatives
        long_name = long_options[(block_number - 1) % len(long_options)]
    if long_name:
        long_level_range = _get_level_range(long_slot, archetype)
        long_level = min(max(level, long_level_range[0]), long_level_range[1])
        long_level = min(long_level, max_level)

        # Budget check: long ride ≤45% of weekly hours. Coach reality check
        # (Matti's manual plans): 4-5h Saturdays on 10-12h weeks = 42-50%.
        # 40% forced a 12h athlete's long ride down to 4h39 — under-long for
        # a 100mi gravel A-race.
        max_long_min = hours_per_week * 60 * 0.45
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
    # Level ladder: fillers progress +1 every 2 blocks within their range,
    # so base-phase volume builds across the plan instead of pinning at L1.
    # base_level rises once per block across the WHOLE plan (block_number is
    # phase-local and resets, so it can't drive a global ladder).
    filler_level = min(
        filler_level_range[0] + (base_level - 1) // 2,
        filler_level_range[1],
        max_level,
    )
    # Week 1 ramp-in: the very first week of the plan eases the athlete in
    # one filler level below normal (a coach starts a new athlete ~80% of
    # steady-state volume, not at full load with an FTP test on top).
    if block_number == 1 and week_in_block == 1:
        filler_level = max(1, filler_level - 1)

    filler_entry = {
        'slot': 'filler',
        'name': filler_name or 'Endurance',
        'level': filler_level,
        'role': 'filler',
    }
    # Day-to-day variety: pool of low-strain variants the week builder
    # cycles across filler days (e.g. Endurance / Cadence Work).
    filler_pool = filler_slot.get('pool')
    if filler_pool:
        filler_entry['pool'] = list(filler_pool)
    workouts.append(filler_entry)

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


def _select_recovery_week(config: dict, hours_per_week: float = 10) -> List[Dict[str, Any]]:
    """Recovery week: Endurance L1-L2, one Openers, and a SHORT long ride.

    The long ride never disappears — a recovery week keeps the weekend
    rhythm with a reduced-duration Z2 ride (~50-60% of a load-week long
    ride). Without this slot, the long-ride day was silently left empty.
    """
    recovery_config = config.get('recovery_week', {})
    max_level = recovery_config.get('max_endurance_level', 2)

    # Short long ride: Endurance L2 (~100min) for everyone. L3 (130min)
    # matched the early-base LOAD long ride — a recovery weekend identical
    # to a load weekend isn't recovery.
    long_level = min(2, max(max_level, 2))

    return [
        {'slot': 'openers', 'name': 'Openers', 'level': 1, 'role': 'intensity'},
        {'slot': 'long_ride', 'name': 'Endurance', 'level': long_level, 'role': 'long_ride'},
        {'slot': 'filler', 'name': 'Endurance', 'level': 1, 'role': 'filler'},
    ]


def _select_taper_week(hours_per_week: float = 10) -> List[Dict[str, Any]]:
    """Taper week: 1-2 openers, short Z2 rides, reduced long ride.

    ~60% volume of a load week, intensity limited to openers, and a
    final medium ride on the long-ride day for equipment/fueling rehearsal.
    """
    return [
        {'slot': 'openers', 'name': 'Openers', 'level': 2, 'role': 'intensity'},
        {'slot': 'openers_2', 'name': 'Openers', 'level': 1, 'role': 'intensity'},
        {'slot': 'long_ride', 'name': 'Endurance', 'level': 2, 'role': 'long_ride'},
        {'slot': 'filler', 'name': 'Endurance', 'level': 1, 'role': 'filler'},
    ]


def _select_testing_week(hours_per_week: float = 10, max_level: int = 6) -> List[Dict[str, Any]]:
    """Testing week: a battery of assessments, not a single FTP test.

    Coach pattern (Matti's manual plans): FTP test Tue, anaerobic
    assessment Thu, long aerobic/metabolism test Sat. The Tue FTP slot is
    rendered by the legacy FTP injection (the renderer defers that day);
    the name here keeps the plan dict honest for compliance/preview.

    The Saturday aerobic/metabolism test scales with experience
    (training-age max_level as proxy): beginners ~2h (Endurance L3),
    intermediates ~3h (L5), advanced ~4h (L6) — clamped to the long-ride
    hours budget (45% of weekly hours).
    """
    if max_level <= 3:
        long_level = 3   # ~130min — beginner
    elif max_level <= 5:
        long_level = 5   # ~190min — intermediate
    else:
        long_level = 6   # ~250min — advanced
    max_long_min = hours_per_week * 60 * 0.45
    while long_level > 2 and get_workout_duration('Endurance', long_level) > max_long_min:
        long_level -= 1
    return [
        {'slot': 'intensity_1', 'name': 'FTP Test', 'level': 1, 'role': 'intensity'},
        {'slot': 'intensity_2', 'name': 'Anaerobic Test', 'level': 1, 'role': 'intensity'},
        {'slot': 'long_ride', 'name': 'Endurance', 'level': long_level, 'role': 'long_ride'},
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
