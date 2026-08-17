#!/usr/bin/env python3
"""TP structure -> ZWO converter (C2, INTERNAL ONLY).

Per docs/SPEC_LIBRARY_SELECTION.md D4, the athlete-facing library card is
verbatim-curated (original TP structure/description placed as-is); this
converter never reaches the athlete. It exists to feed the internal preview
renderer, TSS calculation, and plan_ir with an executable ZWO representation
of a curated TP item, so C1 (index build) can validate a candidate item is
representable before it enters the selectable pool.

Input shape (as found on a dump item's ``structure`` field):
    {"structure": [block, block, ...]}
where each ``block`` is either
    {"type": "step"|"repetition"|"rampUp"|"rampDown",
     "length": {"value": N, "unit": "repetition"},
     "steps": [leaf, ...]}
and each ``leaf`` is
    {"name": str, "length": {"value": seconds, "unit": "second"},
     "targets": [{"minValue": N[, "maxValue": M][, "unit": "roundOrStridePerMinute"]}, ...],
     "intensityClass": "warmUp"|"active"|"rest"|"coolDown",
     "openDuration": bool}

The declared block-level ``type`` string is NOT used to pick the ZWO element
-- verified against the real dump (gg_tp_library_full.json, 1,463
workoutTypeId==2 items with structure), "step" blocks can carry 2-4
sequential leaves and "repetition" blocks can have a repeat count of 1 (no
real repetition). What matters is only the block's repeat count and leaf
count:
    - repeat >= 2 and exactly 2 leaves  -> IntervalsT (on/off)
    - anything else                     -> unroll: emit each leaf, repeated
                                            `repeat` times, as its own element
This also transparently handles rampUp/rampDown blocks (a top-level type not
mentioned in the spec but present in the real corpus, ~146 occurrences):
their leaves carry intensityClass "active" with a distinct target per leg,
so the generic unroll renders them as a staircase of SteadyState elements
that reproduces the source exactly.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPT_DIR = str(Path(__file__).parent.resolve())
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from workout_spec import normalize_zwo_blocks  # noqa: E402

# Power-target comparison tolerance for the round-trip contract, in
# percentage-of-FTP points (i.e. 1.0 == 1 %FTP).
_ROUND_TRIP_TOLERANCE_PCT = 1.0


# =============================================================================
# Structure walking helpers
# =============================================================================

def _extract_blocks(structure: Any) -> List[Dict[str, Any]]:
    """Accept either the raw ``{"structure": [...]}`` wrapper or a bare list."""
    if isinstance(structure, dict):
        blocks = structure.get('structure')
    else:
        blocks = structure
    return list(blocks) if blocks else []


def _block_repeat(block: Dict[str, Any]) -> int:
    length = block.get('length') or {}
    if length.get('unit') != 'repetition':
        return 1
    try:
        value = int(length.get('value', 1))
    except (TypeError, ValueError):
        return 1
    return value if value >= 1 else 1


def _leaf_seconds(leaf: Dict[str, Any]) -> int:
    length = leaf.get('length') or {}
    try:
        return int(length.get('value', 0))
    except (TypeError, ValueError):
        return 0


def _classify_leaf(leaf: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    """Split a leaf's targets into (power_target, cadence_target, has_unsupported_label).

    A leaf carries at most one power-ish target and at most one cadence
    target (verified against the real dump -- no leaf ever has more than 2
    targets). A target that carries a ``label`` key (observed twice in the
    real corpus: "Power Zone" 1-6 and "Rating of Perceived Exertion" 1-10)
    is not a %FTP value and must never be divided by 100 as if it were one.
    """
    power_target = None
    cadence_target = None
    has_unsupported_label = False
    for target in (leaf.get('targets') or []):
        if target.get('unit') == 'roundOrStridePerMinute':
            cadence_target = target
        elif 'label' in target:
            has_unsupported_label = True
        elif power_target is None:
            power_target = target
    return power_target, cadence_target, has_unsupported_label


def _power_fraction(target: Dict[str, Any]) -> float:
    """Min-only targets (~50% of the corpus) render at Power = minValue/100.
    Both bounds present -> midpoint."""
    min_value = target.get('minValue')
    max_value = target.get('maxValue')
    if max_value is not None:
        return (float(min_value) + float(max_value)) / 2.0 / 100.0
    return float(min_value) / 100.0


def _cadence_range(target: Dict[str, Any]) -> Tuple[int, int]:
    min_value = target.get('minValue')
    max_value = target.get('maxValue')
    if max_value is None:
        max_value = min_value
    return int(round(float(min_value))), int(round(float(max_value)))


def _ramp_bounds(target: Dict[str, Any], rising: bool) -> Tuple[float, float]:
    """Judgment call: TP's target dict never encodes ramp direction (minValue
    <= maxValue always, even on coolDown legs -- verified against the real
    dump). Warmup ramps low->high (builds); Cooldown ramps high->low (eases
    off). A min-only target collapses to a flat PowerLow==PowerHigh so the
    round-trip stays exact rather than inventing a spread the source never
    specified."""
    min_value = target.get('minValue')
    max_value = target.get('maxValue')
    if max_value is None:
        max_value = min_value
    low, high = float(min_value) / 100.0, float(max_value) / 100.0
    return (low, high) if rising else (high, low)


# =============================================================================
# ZWO element emitters (4-space indent, matches nate_workout_generator.py /
# workout_mapper.py conventions)
# =============================================================================

def _cadence_attr(cadence: Optional[Tuple[int, int]]) -> str:
    if not cadence:
        return ''
    return f' CadenceLow="{cadence[0]}" CadenceHigh="{cadence[1]}"'


def _steady_xml(seconds: int, power: float, cadence: Optional[Tuple[int, int]] = None) -> str:
    return f'    <SteadyState Duration="{seconds}" Power="{power:.2f}"{_cadence_attr(cadence)}/>\n'


def _free_ride_xml(seconds: int) -> str:
    return f'    <FreeRide Duration="{seconds}"/>\n'


def _ramp_xml(tag: str, seconds: int, power_low: float, power_high: float,
              cadence: Optional[Tuple[int, int]] = None) -> str:
    return (f'    <{tag} Duration="{seconds}" PowerLow="{power_low:.2f}" '
            f'PowerHigh="{power_high:.2f}"{_cadence_attr(cadence)}/>\n')


def _intervals_xml(repeat: int, on_seconds: int, on_power: float, off_seconds: int,
                    off_power: float, cadence: Optional[Tuple[int, int]] = None) -> str:
    return (f'    <IntervalsT Repeat="{repeat}" OnDuration="{on_seconds}" '
            f'OnPower="{on_power:.2f}"{_cadence_attr(cadence)} '
            f'OffDuration="{off_seconds}" OffPower="{off_power:.2f}"/>\n')


# =============================================================================
# Leaf -> element mapping
# =============================================================================

def _map_single_leaf(leaf: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, float]], int, Optional[str]]:
    """Map one leaf to (xml, expected_power_check_or_None, dropped_cadence, note)."""
    seconds = _leaf_seconds(leaf)
    intensity_class = leaf.get('intensityClass')
    power_target, cadence_target, has_unsupported_label = _classify_leaf(leaf)

    if power_target is None:
        # Target-free (never observed in the real dump, but part of the
        # contract) or a Power-Zone/RPE-labeled target we cannot express as
        # %FTP without inventing a number -- both render as FreeRide.
        note = None
        if has_unsupported_label:
            note = f'leaf carries a non-%FTP labeled target ({seconds}s) -- rendered as FreeRide'
        return _free_ride_xml(seconds), None, 0, note

    if intensity_class == 'warmUp':
        power_low, power_high = _ramp_bounds(power_target, rising=True)
        cadence = _cadence_range(cadence_target) if cadence_target else None
        xml = _ramp_xml('Warmup', seconds, power_low, power_high, cadence)
        return xml, {'power_low_pct': power_low * 100, 'power_high_pct': power_high * 100}, 0, None

    if intensity_class == 'coolDown':
        power_low, power_high = _ramp_bounds(power_target, rising=False)
        cadence = _cadence_range(cadence_target) if cadence_target else None
        xml = _ramp_xml('Cooldown', seconds, power_low, power_high, cadence)
        return xml, {'power_low_pct': power_low * 100, 'power_high_pct': power_high * 100}, 0, None

    # 'active' / 'rest' (or missing intensityClass, defensively) with a real
    # %FTP target -> SteadyState.
    #
    # Judgment call: openDuration is TP's "athlete may extend/shorten this
    # step" UI flag, not a target-absence flag -- in the real dump, 100% of
    # openDuration leaves (497/497) carry a genuine %FTP target, some spanning
    # a full hour of race-sim work. Rendering those as target-free FreeRide
    # would silently discard the exact TSS-bearing data C2 exists to
    # preserve for the internal preview/TSS pipeline (D4). So openDuration is
    # NOT treated as an independent trigger for FreeRide here; FreeRide is
    # reserved for leaves with no usable %FTP target at all (see above).
    power = _power_fraction(power_target)
    cadence = _cadence_range(cadence_target) if cadence_target else None
    xml = _steady_xml(seconds, power, cadence)
    return xml, {'power_pct': power * 100}, 0, None


def _build(structure: Any) -> Tuple[List[str], List[Optional[Dict[str, float]]], int, List[str]]:
    """Walk every top-level block and return (xml_parts, expected_checks, dropped_cadence, notes).

    ``xml_parts`` and ``expected_checks`` are parallel lists: xml_parts[i] is
    the ZWO element text, expected_checks[i] is either None (no power check,
    e.g. FreeRide) or a dict of expected %FTP values used by
    ``verify_round_trip``.
    """
    xml_parts: List[str] = []
    expected: List[Optional[Dict[str, float]]] = []
    dropped_cadence = 0
    notes: List[str] = []

    for block in _extract_blocks(structure):
        repeat = _block_repeat(block)
        leaves = block.get('steps') or []

        if repeat >= 2 and len(leaves) == 2:
            on_leaf, off_leaf = leaves
            on_power_t, on_cadence_t, on_bad = _classify_leaf(on_leaf)
            off_power_t, off_cadence_t, off_bad = _classify_leaf(off_leaf)
            on_ic = on_leaf.get('intensityClass')
            off_ic = off_leaf.get('intensityClass')
            fits_intervals = (
                on_power_t is not None and off_power_t is not None
                and not on_bad and not off_bad
                and on_ic not in ('warmUp', 'coolDown')
                and off_ic not in ('warmUp', 'coolDown')
            )
            if fits_intervals:
                on_seconds = _leaf_seconds(on_leaf)
                off_seconds = _leaf_seconds(off_leaf)
                on_power = _power_fraction(on_power_t)
                off_power = _power_fraction(off_power_t)
                cadence = _cadence_range(on_cadence_t) if on_cadence_t else None
                if off_cadence_t:
                    dropped_cadence += 1
                    notes.append(
                        "IntervalsT off-leg cadence target dropped (element type "
                        "only carries one cadence spec, for the on-interval)")
                xml_parts.append(_intervals_xml(repeat, on_seconds, on_power, off_seconds, off_power, cadence))
                expected.append({'on_power_pct': on_power * 100, 'off_power_pct': off_power * 100})
                continue
            # Falls through to the generic unroll below (e.g. one leg has no
            # usable %FTP target) rather than emitting a broken IntervalsT.

        # Repetition steps whose sub-step pattern doesn't fit IntervalsT (not
        # exactly 2 leaves, or repeat == 1) UNROLL: emit every leaf, repeated
        # `repeat` times, never truncated.
        for _ in range(repeat):
            for leaf in leaves:
                xml, exp, dropped, note = _map_single_leaf(leaf)
                xml_parts.append(xml)
                expected.append(exp)
                dropped_cadence += dropped
                if note:
                    notes.append(note)

    return xml_parts, expected, dropped_cadence, notes


def _source_total_seconds(structure: Any) -> int:
    """Total duration computed straight off the raw TP structure (repeat *
    sum-of-leaf-seconds per block), independent of any emitted XML."""
    total = 0
    for block in _extract_blocks(structure):
        repeat = _block_repeat(block)
        leaves = block.get('steps') or []
        total += repeat * sum(_leaf_seconds(leaf) for leaf in leaves)
    return total


# =============================================================================
# Public API
# =============================================================================

def convert_structure(structure: Any) -> Dict[str, Any]:
    """Convert a TP structure dict/list into ZWO ``<workout>`` inner blocks.

    Returns {'blocks_xml': str, 'dropped_cadence': int, 'notes': list[str]}.
    ``blocks_xml`` is the joined, newline-terminated element text (no
    surrounding ``<workout>`` tags) -- feed it through
    ``workout_spec.normalize_zwo_blocks`` or wrap it with
    ``render_full_zwo`` for a complete file.
    """
    xml_parts, _expected, dropped_cadence, notes = _build(structure)
    return {
        'blocks_xml': ''.join(xml_parts),
        'dropped_cadence': dropped_cadence,
        'notes': notes,
    }


def render_full_zwo(blocks_xml: str, *, author: str = 'Gravel God Training',
                     name: str = 'Workout', description: str = '',
                     sport_type: str = 'bike') -> str:
    """Convenience full-ZWO wrapper around C2's blocks_xml output, matching
    nate_workout_generator.ZWO_TEMPLATE's structure/escaping convention."""
    name_escaped = html.escape(name or 'Workout', quote=False)
    desc_escaped = html.escape(description or '', quote=False)
    author_escaped = html.escape(author or 'Gravel God Training', quote=False)
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        "<workout_file>\n"
        f"  <author>{author_escaped}</author>\n"
        f"  <name>{name_escaped}</name>\n"
        f"  <description>{desc_escaped}</description>\n"
        f"  <sportType>{sport_type}</sportType>\n"
        "  <workout>\n"
        f"{blocks_xml}"
        "  </workout>\n"
        "</workout_file>"
    )


# R5 fix wave (SPEC_LIBRARY_SELECTION.md): hard-day detection for
# SEQUENCING/adjacency guidance, checked against a resolved session's raw
# structure directly (not the converted ZWO -- min-only sprint targets
# rendering as flat blocks is exactly the R1 problem this sidesteps).
_HARD_EFFORT_POWER_PCT = 120.0
_HARD_EFFORT_MIN_SECONDS = 60


def structure_has_hard_effort(structure: Any, power_pct: float = _HARD_EFFORT_POWER_PCT,
                               min_seconds: int = _HARD_EFFORT_MIN_SECONDS) -> bool:
    """True when any single leaf carries a POWER target (cadence/label
    targets excluded, matching ``_classify_leaf``) at or above ``power_pct``
    %FTP sustained for at least ``min_seconds``.

    Per-leaf, not repeat-multiplied: a repeated short interval (e.g. 6x30s
    @200%) is a different training stimulus than one continuous >=60s push,
    and per-rep duration is what R1 flagged as inflating NP when flattened
    -- it must not also inflate hard-day detection here.
    """
    for block in _extract_blocks(structure):
        for leaf in (block.get('steps') or []):
            power_target, _cadence_target, _bad = _classify_leaf(leaf)
            if power_target is None:
                continue
            if _leaf_seconds(leaf) < min_seconds:
                continue
            value = power_target.get('maxValue', power_target.get('minValue'))
            if value is not None and float(value) >= power_pct:
                return True
    return False


def verify_round_trip(structure: Any) -> Tuple[bool, Dict[str, Any]]:
    """Round-trip contract: parse C2's own output back through
    workout_spec.normalize_zwo_blocks and check (a) total seconds match the
    source structure EXACTLY and (b) every power target is within 1 %FTP of
    the source (FreeRide-mapped leaves carry no target by design and are
    skipped, per the openDuration/target-free judgment call above).

    Returns (ok, detail) where detail always carries enough to diagnose a
    failure: source/rendered totals, any power mismatches, dropped cadence
    count, and notes from the conversion itself.
    """
    xml_parts, expected, dropped_cadence, notes = _build(structure)
    blocks_xml = ''.join(xml_parts)
    source_total = _source_total_seconds(structure)

    detail: Dict[str, Any] = {
        'source_total_seconds': source_total,
        'rendered_total_seconds': None,
        'dropped_cadence': dropped_cadence,
        'notes': notes,
        'power_mismatches': [],
        'segment_count_mismatch': False,
        'duration_mismatch': False,
    }

    if not blocks_xml.strip():
        detail['rendered_total_seconds'] = 0
        ok = source_total == 0
        return ok, detail

    try:
        segments = normalize_zwo_blocks(blocks_xml)
    except Exception as exc:  # defensive: malformed emission is a hard failure
        detail['parse_error'] = str(exc)
        return False, detail

    rendered_total = 0
    for seg in segments:
        if seg['kind'] == 'intervals':
            rendered_total += seg['repeat'] * (seg['on_seconds'] + seg['off_seconds'])
        else:
            rendered_total += seg.get('seconds', 0)
    detail['rendered_total_seconds'] = rendered_total

    if len(segments) != len(expected):
        detail['segment_count_mismatch'] = True
        return False, detail

    detail['duration_mismatch'] = source_total != rendered_total

    for index, (seg, exp) in enumerate(zip(segments, expected)):
        if exp is None:
            continue  # FreeRide: no target to check by design
        if seg['kind'] == 'intervals':
            on_diff = abs(seg['on_power'] * 100 - exp['on_power_pct'])
            off_diff = abs(seg['off_power'] * 100 - exp['off_power_pct'])
            if on_diff > _ROUND_TRIP_TOLERANCE_PCT or off_diff > _ROUND_TRIP_TOLERANCE_PCT:
                detail['power_mismatches'].append(
                    {'index': index, 'kind': seg['kind'], 'on_diff': on_diff, 'off_diff': off_diff})
        elif seg['kind'] == 'steady':
            diff = abs(seg['power'] * 100 - exp['power_pct'])
            if diff > _ROUND_TRIP_TOLERANCE_PCT:
                detail['power_mismatches'].append({'index': index, 'kind': seg['kind'], 'diff': diff})
        else:  # warmup / cooldown ramps
            lo_diff = abs(seg.get('power_low', 0) * 100 - exp['power_low_pct'])
            hi_diff = abs(seg.get('power_high', 0) * 100 - exp['power_high_pct'])
            if lo_diff > _ROUND_TRIP_TOLERANCE_PCT or hi_diff > _ROUND_TRIP_TOLERANCE_PCT:
                detail['power_mismatches'].append(
                    {'index': index, 'kind': seg['kind'], 'lo_diff': lo_diff, 'hi_diff': hi_diff})

    ok = not detail['duration_mismatch'] and not detail['power_mismatches']
    return ok, detail
