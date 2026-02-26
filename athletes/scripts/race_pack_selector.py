#!/usr/bin/env python3
"""Race pack selector -- selects archetypes and generates ZWO files.

Sprint 3 of the race-to-archetype mapping system.

Given category scores from race_category_scorer, this module:
1. Selects a balanced workout pack from top-scoring categories
2. Generates ZWO (Zwift Workout) XML files for each workout

The ZWO renderer is self-contained (no dependency on nate_workout_generator)
to keep the race pack system standalone.

Usage:
    from race_pack_selector import select_workout_pack, generate_race_pack_zwos
    from race_category_scorer import calculate_category_scores

    scores = calculate_category_scores(demands)
    pack = select_workout_pack(scores, pack_size=10)
    paths = generate_race_pack_zwos(pack, output_dir=Path('./zwos'), ftp=250, level=3)
"""

import sys
from pathlib import Path
from typing import List, Optional

# Add script directory for local imports
_module_dir = Path(__file__).resolve().parent
if str(_module_dir) not in sys.path:
    sys.path.insert(0, str(_module_dir))

from new_archetypes import NEW_ARCHETYPES


# =============================================================================
# WORKOUT PACK SELECTION
# =============================================================================

def select_workout_pack(category_scores: dict, pack_size: int = 10) -> list:
    """Select a balanced workout pack from top-scoring categories.

    Selection algorithm:
      - Top 3 categories (score >= 50): 2 archetypes each (6 slots)
      - Next 2 categories (score >= 20): 1 archetype each (2 slots)
      - Fill remaining slots from next categories: 1 each
      - Max 3 from any single category
      - Each item: {category, archetype_name, relevance_score, level}

    Args:
        category_scores: Dict mapping category name -> score (0-100),
                         sorted descending (from calculate_category_scores).
        pack_size: Total number of workouts in pack (default 10).

    Returns:
        List of pack item dicts, sorted by relevance_score descending.
    """
    if not category_scores:
        return []

    sorted_cats = sorted(category_scores.items(), key=lambda x: -x[1])
    pack = []
    category_counts = {}

    def _add_from_category(cat_name: str, score: int, count: int):
        """Add up to `count` archetypes from a category."""
        if cat_name not in NEW_ARCHETYPES:
            return
        current = category_counts.get(cat_name, 0)
        available = NEW_ARCHETYPES[cat_name]
        added = 0
        idx = current  # start from where we left off
        while added < count and idx < len(available) and current + added < 3:
            arch = available[idx]
            pack.append({
                'category': cat_name,
                'archetype_name': arch['name'],
                'relevance_score': score,
                'level': 3,  # default level, overridden by caller
            })
            added += 1
            idx += 1
        category_counts[cat_name] = current + added

    # Phase 1: Top 3 categories with score >= 50 get 2 archetypes each
    top_cats = [(c, s) for c, s in sorted_cats if s >= 50][:3]
    for cat, score in top_cats:
        _add_from_category(cat, score, 2)

    # Phase 2: Next 2 categories with score >= 20 get 1 archetype each
    used = {c for c, _ in top_cats}
    mid_cats = [(c, s) for c, s in sorted_cats if s >= 20 and c not in used][:2]
    for cat, score in mid_cats:
        _add_from_category(cat, score, 1)

    # Phase 3: Fill remaining slots from next unused categories
    used.update(c for c, _ in mid_cats)
    remaining = pack_size - len(pack)
    fill_cats = [(c, s) for c, s in sorted_cats if c not in used]
    for cat, score in fill_cats:
        if remaining <= 0:
            break
        before = len(pack)
        _add_from_category(cat, score, 1)
        if len(pack) > before:
            remaining -= 1

    # Trim to pack_size
    pack = pack[:pack_size]

    # Sort by relevance score descending
    pack.sort(key=lambda x: -x['relevance_score'])

    return pack


# =============================================================================
# ZWO RENDERING (self-contained)
# =============================================================================

def _render_zwo(archetype: dict, level: int, ftp: int, workout_name: str) -> str:
    """Render a ZWO XML file from an archetype definition.

    Supports archetype formats:
      - intervals: (repeats, on_duration) + on_power, off_power
      - segments: list of segment dicts (steady, intervals, freeride, ramp)
      - single_effort: single sustained block
      - tired_vo2: base endurance + interval block
      - pyramid: descending duration efforts
      - loaded_recovery: VO2 + loaded recovery intervals
      - double_day: AM endurance + PM intervals

    Args:
        archetype: Archetype dict with 'name' and 'levels'.
        level: Level 1-6.
        ftp: Functional threshold power in watts.
        workout_name: Name for the ZWO file metadata.

    Returns:
        ZWO XML string.
    """
    level_key = str(level)
    if level_key not in archetype.get('levels', {}):
        level_key = '3'  # fallback
    level_data = archetype['levels'][level_key]

    lines = []
    lines.append("<?xml version='1.0' encoding='UTF-8'?>")
    lines.append("<workout_file>")
    lines.append(f"  <name>{_xml_escape(workout_name)}</name>")
    lines.append(f"  <author>Gravel God</author>")
    lines.append(f"  <description>{_xml_escape(level_data.get('structure', ''))}</description>")
    lines.append(f"  <sportType>bike</sportType>")
    lines.append(f"  <tags/>")
    lines.append("  <workout>")

    # Warmup: 10min, 45% -> 65% FTP
    lines.append('    <Warmup Duration="600" PowerLow="0.45" PowerHigh="0.65" />')

    # Main body
    if level_data.get('tired_vo2'):
        _render_tired_vo2(lines, level_data)
    elif level_data.get('single_effort'):
        _render_single_effort(lines, level_data)
    elif level_data.get('pyramid'):
        _render_pyramid(lines, level_data)
    elif level_data.get('loaded_recovery'):
        _render_loaded_recovery(lines, level_data)
    elif level_data.get('double_day'):
        _render_double_day(lines, level_data)
    elif level_data.get('breakaway'):
        _render_breakaway(lines, level_data)
    elif level_data.get('chaos'):
        _render_chaos(lines, level_data)
    elif level_data.get('sector_sim'):
        _render_sector_sim(lines, level_data)
    elif level_data.get('progressive_fatigue'):
        _render_progressive_fatigue(lines, level_data)
    elif level_data.get('surge_settle'):
        _render_surge_settle(lines, level_data)
    elif level_data.get('microbursts'):
        _render_microbursts(lines, level_data)
    elif level_data.get('gravel_grind'):
        _render_gravel_grind(lines, level_data)
    elif level_data.get('late_race'):
        _render_late_race(lines, level_data)
    elif 'segments' in level_data:
        _render_segments(lines, level_data)
    elif level_data.get('w_prime'):
        _render_w_prime(lines, level_data)
    elif level_data.get('criss_cross'):
        _render_criss_cross(lines, level_data)
    elif level_data.get('openers'):
        _render_openers(lines, level_data)
    elif level_data.get('terrain_sim') or level_data.get('hvli_terrain'):
        _render_terrain_sim(lines, level_data)
    elif 'intervals' in level_data and isinstance(level_data['intervals'], tuple):
        _render_intervals(lines, level_data)
    elif 'intervals' in level_data:
        # Integer intervals with on_power + duration -- render as IntervalsT
        _render_simple_repeats(lines, level_data)
    elif level_data.get('efforts') and isinstance(level_data.get('efforts'), list):
        # Generic efforts list (descending, buildup, etc.)
        _render_effort_list(lines, level_data)
    elif level_data.get('testing') or level_data.get('maf_test'):
        _render_test_protocol(lines, level_data)
    elif 'duration' in level_data and 'power' in level_data:
        # Simple steady state (recovery, LT1, HVLI, etc.)
        _render_steady_duration(lines, level_data)
    else:
        # Fallback: 20min steady at 75% FTP
        lines.append('    <SteadyState Duration="1200" Power="0.75" />')

    # Cooldown: 5min, 60% -> 45% FTP
    lines.append('    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.45" />')

    lines.append("  </workout>")
    lines.append("</workout_file>")

    return "\n".join(lines)


def _render_intervals(lines: list, level_data: dict):
    """Render standard interval block."""
    repeats, on_duration = level_data['intervals']
    on_power = level_data.get('on_power', 1.0)
    off_power = level_data.get('off_power', 0.55)
    off_duration = level_data.get('off_duration', on_duration)
    cadence = level_data.get('cadence')

    cadence_attr = f' Cadence="{cadence}"' if cadence else ''
    lines.append(
        f'    <IntervalsT Repeat="{repeats}" '
        f'OnDuration="{on_duration}" OnPower="{on_power:.2f}" '
        f'OffDuration="{off_duration}" OffPower="{off_power:.2f}"'
        f'{cadence_attr} />'
    )


def _render_segments(lines: list, level_data: dict):
    """Render segment-based workouts."""
    for seg in level_data['segments']:
        seg_type = seg.get('type', 'steady')
        if seg_type == 'steady':
            dur = seg.get('duration', 600)
            pwr = seg.get('power', 0.75)
            cadence_low = seg.get('cadence_low')
            cadence_high = seg.get('cadence_high')
            cad_attrs = ''
            if cadence_low and cadence_high:
                cad_attrs = f' CadenceLow="{cadence_low}" CadenceHigh="{cadence_high}"'
            lines.append(f'    <SteadyState Duration="{dur}" Power="{pwr:.2f}"{cad_attrs} />')
        elif seg_type == 'intervals':
            repeats = seg.get('repeats', 4)
            on_dur = seg.get('on_duration', 180)
            on_pwr = seg.get('on_power', 1.0)
            off_dur = seg.get('off_duration', 180)
            off_pwr = seg.get('off_power', 0.55)
            cadence = seg.get('cadence')
            cad_attr = f' Cadence="{cadence}"' if cadence else ''
            lines.append(
                f'    <IntervalsT Repeat="{repeats}" '
                f'OnDuration="{on_dur}" OnPower="{on_pwr:.2f}" '
                f'OffDuration="{off_dur}" OffPower="{off_pwr:.2f}"'
                f'{cad_attr} />'
            )
        elif seg_type == 'ramp':
            dur = seg.get('duration', 600)
            low = seg.get('power_low', 0.50)
            high = seg.get('power_high', 1.00)
            lines.append(f'    <Warmup Duration="{dur}" PowerLow="{low:.2f}" PowerHigh="{high:.2f}" />')
        elif seg_type == 'freeride':
            dur = seg.get('duration', 600)
            lines.append(f'    <FreeRide Duration="{dur}" />')
        else:
            # Unknown segment type -- render as SteadyState with safe defaults
            dur = seg.get('duration', 600)
            pwr = seg.get('power', 0.70)
            lines.append(f'    <SteadyState Duration="{dur}" Power="{pwr:.2f}" />')


def _render_single_effort(lines: list, level_data: dict):
    """Render single sustained effort."""
    duration = level_data.get('duration', 1200)
    power = level_data.get('power', 0.96)
    lines.append(f'    <SteadyState Duration="{duration}" Power="{power:.2f}" />')


def _render_tired_vo2(lines: list, level_data: dict):
    """Render tired VO2max: base endurance + intervals."""
    base_dur = level_data.get('base_duration', 7200)
    base_pwr = level_data.get('base_power', 0.70)
    lines.append(f'    <SteadyState Duration="{base_dur}" Power="{base_pwr:.2f}" />')

    # Then intervals
    repeats, on_dur = level_data['intervals']
    on_pwr = level_data.get('on_power', 1.10)
    off_pwr = level_data.get('off_power', 0.55)
    off_dur = level_data.get('off_duration', on_dur)
    lines.append(
        f'    <IntervalsT Repeat="{repeats}" '
        f'OnDuration="{on_dur}" OnPower="{on_pwr:.2f}" '
        f'OffDuration="{off_dur}" OffPower="{off_pwr:.2f}" />'
    )


def _render_pyramid(lines: list, level_data: dict):
    """Render pyramid efforts (descending duration, ascending intensity)."""
    efforts = level_data.get('efforts', [])
    recovery_dur = level_data.get('recovery_duration', 180)
    sets = int(level_data.get('sets', 1))
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        if s > 0:
            # Set recovery
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.50" />')
        for i, effort in enumerate(efforts):
            dur = effort.get('duration', 180)
            pwr = effort.get('power', 1.10)
            lines.append(f'    <SteadyState Duration="{dur}" Power="{pwr:.2f}" />')
            if i < len(efforts) - 1:
                lines.append(f'    <SteadyState Duration="{recovery_dur}" Power="0.50" />')


def _render_loaded_recovery(lines: list, level_data: dict):
    """Render VO2max with loaded (tempo) recovery."""
    repeats, on_dur = level_data['intervals']
    on_pwr = level_data.get('on_power', 1.15)
    loaded_pwr = level_data.get('loaded_power', 0.85)
    loaded_dur = level_data.get('loaded_duration', 120)
    off_pwr = level_data.get('off_power', 0.50)
    off_dur = level_data.get('off_duration', 180)

    for i in range(repeats):
        # VO2 effort
        lines.append(f'    <SteadyState Duration="{on_dur}" Power="{on_pwr:.2f}" />')
        # Loaded recovery
        lines.append(f'    <SteadyState Duration="{loaded_dur}" Power="{loaded_pwr:.2f}" />')
        if i < repeats - 1:
            # Full recovery between sets
            lines.append(f'    <SteadyState Duration="{off_dur}" Power="{off_pwr:.2f}" />')


def _render_double_day(lines: list, level_data: dict):
    """Render double day simulation (AM + PM in single file)."""
    am_dur = level_data.get('am_duration', 5400)
    am_pwr = level_data.get('am_power', 0.70)
    lines.append(f'    <SteadyState Duration="{am_dur}" Power="{am_pwr:.2f}" />')

    # Transition marker (30min easy)
    lines.append('    <SteadyState Duration="1800" Power="0.45" />')

    # PM intervals
    repeats, on_dur = level_data.get('pm_intervals', (3, 480))
    on_pwr = level_data.get('pm_on_power', 1.00)
    off_pwr = level_data.get('pm_off_power', 0.55)
    off_dur = level_data.get('pm_off_duration', 300)
    lines.append(
        f'    <IntervalsT Repeat="{repeats}" '
        f'OnDuration="{on_dur}" OnPower="{on_pwr:.2f}" '
        f'OffDuration="{off_dur}" OffPower="{off_pwr:.2f}" />'
    )


def _render_surge_settle(lines: list, level_data: dict):
    """Render surge-and-settle: sets of surge/settle pairs."""
    sets = level_data.get('sets', 3)
    surges_per_set = level_data.get('surges_per_set', 4)
    surge_dur = level_data.get('surge_duration', 25)
    surge_pwr = level_data.get('surge_power', 1.40)
    settle_dur = level_data.get('settle_duration', 60)
    settle_pwr = level_data.get('settle_power', 0.87)
    set_recovery = level_data.get('set_recovery', 240)

    for s in range(sets):
        for sg in range(surges_per_set):
            lines.append(f'    <SteadyState Duration="{surge_dur}" Power="{surge_pwr:.2f}" />')
            lines.append(f'    <SteadyState Duration="{settle_dur}" Power="{settle_pwr:.2f}" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_microbursts(lines: list, level_data: dict):
    """Render terrain microbursts: short bursts within endurance blocks."""
    sets = level_data.get('sets', 3)
    block_dur = level_data.get('block_duration', 600)
    burst_dur = level_data.get('burst_duration', 15)
    burst_pwr = level_data.get('burst_power', 1.50)
    burst_interval = level_data.get('burst_interval', 60)
    base_pwr = level_data.get('base_power', 0.70)
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        # Alternate between base and burst within the block
        remaining = block_dur
        while remaining > 0:
            # Burst
            b_dur = min(burst_dur, remaining)
            lines.append(f'    <SteadyState Duration="{b_dur}" Power="{burst_pwr:.2f}" />')
            remaining -= b_dur
            # Base until next burst
            base_dur = min(burst_interval - burst_dur, remaining)
            if base_dur > 0:
                lines.append(f'    <SteadyState Duration="{base_dur}" Power="{base_pwr:.2f}" />')
                remaining -= base_dur
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_gravel_grind(lines: list, level_data: dict):
    """Render gravel grind: sustained base with power spikes."""
    sets = level_data.get('sets', 3)
    block_dur = level_data.get('block_duration', 600)
    base_pwr = level_data.get('base_power', 0.82)
    spike_dur = level_data.get('spike_duration', 30)
    spike_pwr = level_data.get('spike_power', 1.30)
    num_spikes = level_data.get('num_spikes', 4)
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        # Divide block into sections with spikes
        section_dur = block_dur // (num_spikes + 1) if num_spikes > 0 else block_dur
        for sp in range(num_spikes):
            lines.append(f'    <SteadyState Duration="{section_dur}" Power="{base_pwr:.2f}" />')
            lines.append(f'    <SteadyState Duration="{spike_dur}" Power="{spike_pwr:.2f}" />')
        # Final section
        lines.append(f'    <SteadyState Duration="{section_dur}" Power="{base_pwr:.2f}" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_late_race(lines: list, level_data: dict):
    """Render late race surge: preload + efforts."""
    preload_dur = level_data.get('preload_duration', 3600)
    preload_pwr = level_data.get('preload_power', 0.72)
    efforts = level_data.get('efforts', [])
    sets = level_data.get('sets', 1)
    set_recovery = level_data.get('set_recovery', 300)

    # Preload
    lines.append(f'    <SteadyState Duration="{preload_dur}" Power="{preload_pwr:.2f}" />')

    for s in range(sets):
        for effort in efforts:
            dur = effort.get('duration', 180)
            pwr = effort.get('power', 1.10)
            lines.append(f'    <SteadyState Duration="{dur}" Power="{pwr:.2f}" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_w_prime(lines: list, level_data: dict):
    """Render W' depletion: surge/hold repeats."""
    sets = level_data.get('sets', 3)
    surge_dur = level_data.get('surge_duration', 30)
    surge_pwr = level_data.get('surge_power', 1.50)
    hold_dur = level_data.get('hold_duration', 300)
    hold_pwr = level_data.get('hold_power', 0.95)
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        lines.append(f'    <SteadyState Duration="{surge_dur}" Power="{surge_pwr:.2f}" />')
        lines.append(f'    <SteadyState Duration="{hold_dur}" Power="{hold_pwr:.2f}" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_criss_cross(lines: list, level_data: dict):
    """Render criss-cross: alternating high/low power within a block."""
    total_dur = level_data.get('total_duration', 1200)
    interval_dur = level_data.get('interval_duration', 60)
    high_pwr = level_data.get('high_power', 0.92)
    low_pwr = level_data.get('low_power', 0.87)
    sets = level_data.get('sets', 1)
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        remaining = total_dur
        toggle = True
        while remaining > 0:
            chunk = min(interval_dur, remaining)
            pwr = high_pwr if toggle else low_pwr
            lines.append(f'    <SteadyState Duration="{chunk}" Power="{pwr:.2f}" />')
            remaining -= chunk
            toggle = not toggle
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_openers(lines: list, level_data: dict):
    """Render pre-race openers: short sharp efforts."""
    efforts_raw = level_data.get('efforts', 4)
    effort_power = level_data.get('effort_power', 1.30)
    effort_recovery = level_data.get('effort_recovery', 180)
    warmup_dur = level_data.get('warmup_duration', 900)
    warmup_pwr = level_data.get('warmup_power', 0.65)

    # efforts can be int (count) or tuple (count, duration)
    if isinstance(efforts_raw, tuple):
        num_efforts, effort_dur = efforts_raw
    else:
        num_efforts = efforts_raw
        effort_dur = 30

    # Extended warmup
    lines.append(f'    <SteadyState Duration="{warmup_dur}" Power="{warmup_pwr:.2f}" />')
    # Opener efforts
    for i in range(num_efforts):
        lines.append(f'    <SteadyState Duration="{effort_dur}" Power="{effort_power:.2f}" />')
        if i < num_efforts - 1:
            lines.append(f'    <SteadyState Duration="{effort_recovery}" Power="0.55" />')


def _render_terrain_sim(lines: list, level_data: dict):
    """Render terrain simulation: alternating power within Z2."""
    total_dur = level_data.get('duration', 3600)
    high_pwr = level_data.get('high_power', 0.75)
    low_pwr = level_data.get('low_power', 0.62)
    seg_dur = level_data.get('segment_duration',
                             level_data.get('high_interval',
                             level_data.get('interval_duration', 300)))

    remaining = total_dur
    toggle = True
    while remaining > 0:
        chunk = min(seg_dur, remaining)
        pwr = high_pwr if toggle else low_pwr
        lines.append(f'    <SteadyState Duration="{chunk}" Power="{pwr:.2f}" />')
        remaining -= chunk
        toggle = not toggle


def _render_effort_list(lines: list, level_data: dict):
    """Render a generic list of efforts with recovery between."""
    efforts = level_data.get('efforts', [])
    recovery_dur = level_data.get('recovery_duration',
                                  level_data.get('effort_recovery', 180))
    set_recovery = level_data.get('set_recovery', 300)
    sets = level_data.get('sets', 1)

    for s in range(sets):
        for i, effort in enumerate(efforts):
            if isinstance(effort, dict):
                dur = effort.get('duration', 300)
                pwr = effort.get('power', 1.00)
            else:
                dur = effort
                pwr = level_data.get('on_power', 1.00)
            lines.append(f'    <SteadyState Duration="{dur}" Power="{pwr:.2f}" />')
            if i < len(efforts) - 1:
                lines.append(f'    <SteadyState Duration="{recovery_dur}" Power="0.55" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _render_test_protocol(lines: list, level_data: dict):
    """Render testing protocol as FreeRide (max effort, no target)."""
    warmup_dur = level_data.get('warmup_duration', 600)
    test_dur = level_data.get('test_duration',
                              level_data.get('test_1_duration', 1200))

    lines.append(f'    <SteadyState Duration="{warmup_dur}" Power="0.55" />')
    lines.append(f'    <FreeRide Duration="{test_dur}" />')

    # Two-part test (like CP test)
    test_2 = level_data.get('test_2_duration')
    rest = level_data.get('rest_duration', 600)
    if test_2:
        lines.append(f'    <SteadyState Duration="{rest}" Power="0.45" />')
        lines.append(f'    <FreeRide Duration="{test_2}" />')


def _render_steady_duration(lines: list, level_data: dict):
    """Render simple steady-state duration + power."""
    duration = level_data.get('duration', 3600)
    power = level_data.get('power', 0.65)
    lines.append(f'    <SteadyState Duration="{duration}" Power="{power:.2f}" />')


def _render_simple_repeats(lines: list, level_data: dict):
    """Render when intervals is a plain int (not a tuple).

    Used by formats that specify intervals as count + separate duration fields.
    """
    repeats = level_data['intervals']
    on_dur = level_data.get('effort_duration', level_data.get('duration', 300))
    on_pwr = level_data.get('on_power', 1.0)
    off_pwr = level_data.get('off_power', 0.55)
    off_dur = level_data.get('off_duration', 180)
    lines.append(
        f'    <IntervalsT Repeat="{repeats}" '
        f'OnDuration="{on_dur}" OnPower="{on_pwr:.2f}" '
        f'OffDuration="{off_dur}" OffPower="{off_pwr:.2f}" />'
    )


def _render_progressive_fatigue(lines: list, level_data: dict):
    """Render progressive fatigue: efforts with decreasing recovery."""
    repeats = level_data.get('intervals', 4)
    effort_dur = level_data.get('effort_duration', 600)
    on_pwr = level_data.get('on_power', 0.99)
    recovery_seq = level_data.get('recovery_sequence', [300, 240, 180, 120])

    for i in range(repeats):
        lines.append(f'    <SteadyState Duration="{effort_dur}" Power="{on_pwr:.2f}" />')
        if i < repeats - 1:
            rec_dur = recovery_seq[i] if i < len(recovery_seq) else 180
            lines.append(f'    <SteadyState Duration="{rec_dur}" Power="0.55" />')


def _render_breakaway(lines: list, level_data: dict):
    """Render breakaway simulation: attack + hold + recovery."""
    repeats = level_data.get('intervals', 3)
    attack_dur = level_data.get('attack_duration', 300)
    attack_pwr = level_data.get('attack_power', 1.12)
    hold_dur = level_data.get('hold_duration', 600)
    hold_pwr = level_data.get('hold_power', 0.89)
    recovery_dur = level_data.get('recovery_duration', 240)

    for i in range(repeats):
        lines.append(f'    <SteadyState Duration="{attack_dur}" Power="{attack_pwr:.2f}" />')
        lines.append(f'    <SteadyState Duration="{hold_dur}" Power="{hold_pwr:.2f}" />')
        if i < repeats - 1:
            lines.append(f'    <SteadyState Duration="{recovery_dur}" Power="0.55" />')


def _render_chaos(lines: list, level_data: dict):
    """Render variable pace chaos: blocks of alternating power.

    Since ZWO doesn't support randomized power, we render as alternating
    high/low SteadyState blocks within each chaos block.
    """
    blocks = level_data.get('blocks', 1)
    block_dur = level_data.get('block_duration', 1200)
    power_range = level_data.get('power_range', (0.80, 1.15))
    block_recovery = level_data.get('block_recovery', 300)

    low_pwr = power_range[0]
    high_pwr = power_range[1]
    mid_pwr = (low_pwr + high_pwr) / 2

    for b in range(blocks):
        # Alternate between high and low in 60-second chunks
        remaining = block_dur
        toggle = True
        while remaining > 0:
            chunk = min(60, remaining)
            pwr = high_pwr if toggle else low_pwr
            lines.append(f'    <SteadyState Duration="{chunk}" Power="{pwr:.2f}" />')
            remaining -= chunk
            toggle = not toggle
        if b < blocks - 1 and block_recovery > 0:
            lines.append(f'    <SteadyState Duration="{block_recovery}" Power="0.55" />')


def _render_sector_sim(lines: list, level_data: dict):
    """Render sector simulation: sets of sector efforts with recovery."""
    sets = level_data.get('sets', 2)
    sectors = level_data.get('sectors_per_set', 3)
    sector_dur = level_data.get('sector_duration', 300)
    sector_pwr = level_data.get('sector_power', 1.05)
    sector_rec = level_data.get('sector_recovery', 120)
    sector_rec_pwr = level_data.get('sector_recovery_power', 0.55)
    set_recovery = level_data.get('set_recovery', 300)

    for s in range(sets):
        for sec in range(sectors):
            lines.append(f'    <SteadyState Duration="{sector_dur}" Power="{sector_pwr:.2f}" />')
            if sec < sectors - 1:
                lines.append(f'    <SteadyState Duration="{sector_rec}" Power="{sector_rec_pwr:.2f}" />')
        if s < sets - 1:
            lines.append(f'    <SteadyState Duration="{set_recovery}" Power="0.55" />')


def _xml_escape(text: str) -> str:
    """Escape XML special characters."""
    if not text:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _slugify(name: str) -> str:
    """Convert archetype name to filesystem-safe slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


# =============================================================================
# ZWO GENERATION
# =============================================================================

def generate_race_pack_zwos(
    pack: list,
    output_dir: Path,
    ftp: int = 200,
    level: int = 3,
) -> list:
    """Generate ZWO files for each workout in the pack.

    Args:
        pack: List of pack items from select_workout_pack().
        output_dir: Directory to write ZWO files to.
        ftp: Functional threshold power in watts.
        level: Archetype level 1-6.

    Returns:
        List of Path objects for generated ZWO files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for i, item in enumerate(pack):
        cat = item['category']
        arch_name = item['archetype_name']

        # Find archetype in NEW_ARCHETYPES
        archetype = _find_archetype(cat, arch_name)
        if archetype is None:
            continue

        # Update level in pack item
        item['level'] = level

        # Generate ZWO
        workout_name = f"{i+1:02d}_{_slugify(arch_name)}"
        zwo_xml = _render_zwo(archetype, level, ftp, workout_name)

        # Write file
        filename = f"{workout_name}.zwo"
        filepath = output_dir / filename
        filepath.write_text(zwo_xml, encoding='utf-8')
        generated.append(filepath)

    return generated


def _find_archetype(category: str, name: str) -> Optional[dict]:
    """Find an archetype by category and name."""
    archetypes = NEW_ARCHETYPES.get(category, [])
    for arch in archetypes:
        if arch['name'] == name:
            return arch
    return None


if __name__ == '__main__':
    from race_category_scorer import calculate_category_scores

    # Demo with Unbound-200-like demands
    demands = {
        'durability': 9, 'climbing': 4, 'vo2_power': 6, 'threshold': 5,
        'technical': 5, 'heat_resilience': 8, 'altitude': 2, 'race_specificity': 7,
    }
    scores = calculate_category_scores(demands)
    pack = select_workout_pack(scores, pack_size=10)

    print("WORKOUT PACK")
    print("=" * 70)
    for item in pack:
        print(f"  [{item['relevance_score']:3d}] {item['category']:25s} | {item['archetype_name']}")

    # Generate ZWOs
    out = Path('/tmp/race-pack-demo')
    paths = generate_race_pack_zwos(pack, out, ftp=250, level=3)
    print(f"\nGenerated {len(paths)} ZWO files in {out}")
    for p in paths:
        print(f"  {p.name}")
