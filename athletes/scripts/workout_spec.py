"""Executable workout segments and their human-readable projection.

The ZWO blocks are the source of truth.  This small adapter exists so every
renderer can derive its MAIN SET wording from the same executable segments.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from delivery_render import zone_rpe_annotation


def normalize_zwo_blocks(blocks: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(f'<workout>{blocks}</workout>')
    segments: List[Dict[str, Any]] = []
    for node in root:
        attrs = node.attrib
        kind = node.tag
        if kind == 'IntervalsT':
            segments.append({'kind': 'intervals', 'repeat': int(attrs.get('Repeat', 1)),
                             'on_seconds': int(float(attrs.get('OnDuration', 0))),
                             'on_power': float(attrs.get('OnPower', 0)),
                             'off_seconds': int(float(attrs.get('OffDuration', 0))),
                             'off_power': float(attrs.get('OffPower', 0))})
        elif kind in ('SteadyState', 'FreeRide'):
            segments.append({'kind': 'steady' if kind == 'SteadyState' else 'free_ride',
                             'seconds': int(float(attrs.get('Duration', 0))),
                             'power': float(attrs['Power']) if 'Power' in attrs else None})
        else:
            segments.append({'kind': kind.lower(), 'seconds': int(float(attrs.get('Duration', 0))),
                             'power_low': float(attrs.get('PowerLow', 0)),
                             'power_high': float(attrs.get('PowerHigh', 0))})
    return segments


def _mins(seconds: int) -> str:
    """Whole minutes render as ``Nmin``; anything else renders as ``M:SS``.

    Never emit a decimal-minute token (e.g. ``7.41667min``) -- descriptions
    must be coach-readable and machine-parseable at whole-second precision.
    """
    if seconds % 60 == 0:
        return f'{seconds // 60}min'
    return f'{seconds // 60}:{seconds % 60:02d}'


def _line_for_segment(segment: Dict[str, Any]) -> Optional[str]:
    """Render a single executable segment as training-work prose (no bullet
    prefix). Returns ``None`` for anything render_main_set doesn't cover.

    AE-3.12 (2026-08-24 TP review): every %FTP target carries its RPE decode
    right beside it ("80% FTP (Z3, RPE 6-7)") -- best practice for executing
    a session that is built as %FTP but felt as effort. zone_rpe_annotation
    is the shared canon (delivery_render.py) also used for session-level
    title RPE, so a step's decode never disagrees with the card's own RPE.
    """
    kind = segment['kind']
    if kind == 'intervals':
        on_pct = round(segment['on_power'] * 100)
        off_pct = round(segment['off_power'] * 100)
        return (f"{segment['repeat']}x{_mins(segment['on_seconds'])} @ {on_pct}% FTP {zone_rpe_annotation(on_pct)}, "
                f"{_mins(segment['off_seconds'])} recovery @ {off_pct}% FTP {zone_rpe_annotation(off_pct)}")
    if kind == 'steady':
        pct = round(segment['power'] * 100)
        return f"{_mins(segment['seconds'])} @ {pct}% FTP {zone_rpe_annotation(pct)}"
    if kind == 'free_ride':
        # Target-free blocks in emitted workouts are max-effort test segments
        # (sprints, capacity efforts). "Free ride" reads as no-effort-required
        # and risks the athlete soft-pedaling exactly where the test needs
        # everything; say what the block is for. No %FTP target exists to
        # decode, but the effort is unambiguously maximal -- RPE 10.
        return f"{_mins(segment['seconds'])} all-out (no target — empty the tank) (RPE 10)"
    return None


def _find_best_repeat_run(lines: List[str]) -> Optional[Tuple[int, int, int, int]]:
    """Find the contiguous run ``[start, start+covered)`` that is a
    period-``p`` block (``p``>=1) repeated ``m``>=2 times back-to-back,
    ANYWHERE in ``lines`` -- a non-repeating lead-in and/or tail need not
    participate. Only full periods count toward ``m``; a final partial
    repeat is left out of the run (and so stays expanded) rather than
    forcing an inexact "K x" count.

    Among all qualifying runs, prefers the one covering the most lines
    (the biggest wall-reduction); ties broken by earliest start, then by
    the smallest (tightest) period. Returns ``None`` if no run repeats.
    """
    n = len(lines)
    best = None  # (covered, start, period, repeats)
    for start in range(n):
        max_p = (n - start) // 2
        for p in range(1, max_p + 1):
            m = 1
            while (start + (m + 1) * p <= n
                   and lines[start + m * p:start + (m + 1) * p] == lines[start:start + p]):
                m += 1
            if m < 2:
                continue
            covered = m * p
            candidate = (covered, start, p, m)
            if best is None or (candidate[0], -candidate[1], -candidate[2]) > (best[0], -best[1], -best[2]):
                best = candidate
    return best


def _collapse_repeated_lines(lines: List[str]) -> List[str]:
    """Collapse every contiguous repeat run in ``lines`` -- a period-``p``
    block repeated ``m``>=2 times -- into a single ``m x (unit)`` line,
    leaving any non-repeating lead-in/tail bullets (and a trailing partial
    repeat) exactly as they were.

    General, period-K, run-anywhere-in-the-list version of the reference
    gravel-god-training-plans/engine/collapse_description.py::collapse_description
    period-detection ("Shape A": a p-line block repeated K times). The
    reference only detects a period spanning an ENTIRE bullet section; this
    extends that to find the run wherever it sits (e.g. a workout that
    opens with a one-line lead-in before a repeating interval group, or
    that has a mid-set recovery break splitting two separate repeat
    groups), recursing on whatever's left before/after each collapsed run
    so multiple independent repeat groups in one list all collapse. A list
    with no repeating run (or a single segment) is returned unchanged.
    """
    best = _find_best_repeat_run(lines)
    if best is None:
        return lines
    covered, start, p, m = best
    unit = lines[start:start + p]
    unit_text = ' + '.join(unit) if len(unit) > 1 else unit[0]
    collapsed = f"{m} x ({unit_text})" if len(unit) > 1 else f"{m}x {unit_text}"
    pre = _collapse_repeated_lines(lines[:start])
    post = _collapse_repeated_lines(lines[start + covered:])
    return pre + [collapsed] + post


def render_main_set(segments: Iterable[Dict[str, Any]]) -> str:
    """Render only training work, never infer reps/duration from prose.

    Consecutive segments that form a repeated unit (e.g. 15x[steady + surge])
    collapse into one ``K x (unit)`` line instead of unrolling every rep as
    its own bullet -- see _collapse_repeated_lines.
    """
    lines = [line for line in (_line_for_segment(segment) for segment in segments)
              if line is not None]
    lines = _collapse_repeated_lines(lines)
    return '\n'.join(f'- {line}' for line in lines) or '- Recovery / rest as scheduled'


_DIMENSION_LABELS = ('cadence', 'position', 'drill')


def _is_dimension_line(line: str) -> bool:
    """True for an authored '-Cadence: ...' / '- Position: ...' bullet.

    Two conventions coexist in this codebase: the Nate generator emits
    ``-Cadence: ...`` (no space after the dash); the block-mapper's
    focus-variant endurance renderer emits ``- Position: ...`` /
    ``- Cadence: ...`` (a space after the dash). The old no-space-only check
    silently dropped every space-formatted cadence line and never
    recognized Position at all -- so a focus-variant card's title promised
    "Position Focus" / "Cadence Focus" while the rendered description
    carried neither instruction.
    """
    stripped = line.strip()
    if not stripped.startswith('-'):
        return False
    rest = stripped[1:].lstrip().lower()
    return any(rest.startswith(f'{label}:') for label in _DIMENSION_LABELS)


def replace_main_set(description: str, segments: Iterable[Dict[str, Any]]) -> str:
    rendered = 'MAIN SET:\n' + render_main_set(segments)
    pattern = r'MAIN SET:\n.*?(?=\n\n(?:COOL-DOWN|PROGRESSION|PURPOSE|EXECUTION|RPE|NUTRITION|HYDRATION):|\Z)'
    match = re.search(pattern, description, flags=re.S)
    if match:
        # MAIN SET prose is replaced from executable ZWO blocks, but cadence
        # and position are dimensions of execution rather than power
        # segments.  Retain their authored lines so the projection cannot
        # silently strip an rpm/position prescription (notably Cadence_Work
        # sessions and focus-variant endurance rides).
        dimension_lines = [line for line in match.group(0).splitlines()
                           if _is_dimension_line(line)]
        if dimension_lines:
            rendered += '\n' + '\n'.join(dimension_lines)
        return description[:match.start()] + rendered + description[match.end():]
    return rendered + '\n\n' + description


def calendar_safe_description(description: str, plan_week: Optional[int] = None,
                              session_date: Optional[str] = None,
                              event_date: Optional[str] = None) -> str:
    """Prevent stale hard-coded calendar claims in otherwise reusable prose."""
    if plan_week:
        description = re.sub(r'Week\s+\d+(?:/\d+)?(?=\s+(?:FTP|retest|test))',
                             f'Week {plan_week}', description, flags=re.I)
    if 'day before race' in description.lower():
        is_pre_race = False
        try:
            is_pre_race = date.fromisoformat(session_date) == date.fromisoformat(event_date) - timedelta(days=1)
        except (TypeError, ValueError):
            pass
        if not is_pre_race:
            description = re.sub('day before race', 'pre-event activation', description, flags=re.I)
    return description


def rewrite_zwo_description(xml_text: str, *, plan_week: Optional[int] = None,
                            session_date: Optional[str] = None,
                            event_date: Optional[str] = None) -> str:
    """Project final (including scaled) XML segments back into description."""
    root = ET.fromstring(xml_text)
    workout = root.find('workout')
    desc = root.find('description')
    if workout is None or desc is None:
        return xml_text
    blocks = ''.join(ET.tostring(child, encoding='unicode') for child in workout)
    desc.text = calendar_safe_description(
        replace_main_set(desc.text or '', normalize_zwo_blocks(blocks)),
        plan_week, session_date, event_date)
    return "<?xml version='1.0' encoding='UTF-8'?>\n" + ET.tostring(root, encoding='unicode')
