"""Executable workout segments and their human-readable projection.

The ZWO blocks are the source of truth.  This small adapter exists so every
renderer can derive its MAIN SET wording from the same executable segments.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


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
    prefix). Returns ``None`` for anything render_main_set doesn't cover."""
    kind = segment['kind']
    if kind == 'intervals':
        return (f"{segment['repeat']}x{_mins(segment['on_seconds'])} @ {round(segment['on_power'] * 100)}% FTP, "
                f"{_mins(segment['off_seconds'])} recovery @ {round(segment['off_power'] * 100)}% FTP")
    if kind == 'steady':
        return f"{_mins(segment['seconds'])} @ {round(segment['power'] * 100)}% FTP"
    if kind == 'free_ride':
        return f"{_mins(segment['seconds'])} free ride"
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


def replace_main_set(description: str, segments: Iterable[Dict[str, Any]]) -> str:
    rendered = 'MAIN SET:\n' + render_main_set(segments)
    pattern = r'MAIN SET:\n.*?(?=\n\n(?:COOL-DOWN|PROGRESSION|PURPOSE|EXECUTION|RPE|NUTRITION|HYDRATION):|\Z)'
    if re.search(pattern, description, flags=re.S):
        return re.sub(pattern, rendered, description, flags=re.S)
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
