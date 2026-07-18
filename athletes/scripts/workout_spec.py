"""Executable workout segments and their human-readable projection.

The ZWO blocks are the source of truth.  This small adapter exists so every
renderer can derive its MAIN SET wording from the same executable segments.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional


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


def _collapse_repeated_lines(lines: List[str]) -> List[str]:
    """Collapse a run of lines that is itself K>=2 repeats of a shorter unit
    into a single ``K x (unit)`` line.

    Mirrors the period-detection ("Shape A") semantics of the reference
    gravel-god-training-plans/engine/collapse_description.py::collapse_description
    -- smallest period p such that the whole list is p repeated (a trailing
    partial repeat is allowed, same as the reference) -- but operates on
    already-rendered, already-clean segment text, so no annotation-stripping
    or ladder-detection is needed here. A single, non-repeated segment (or
    any list with no consistent period) is returned unchanged.
    """
    n = len(lines)
    for p in range(1, n // 2 + 1):
        if all(lines[i] == lines[i - p] for i in range(p, n)):
            k = math.ceil(n / p)
            unit = lines[:p]
            unit_text = ' + '.join(unit) if len(unit) > 1 else unit[0]
            if len(unit) > 1:
                return [f"{k} x ({unit_text})"]
            return [f"{k}x {unit_text}"]
    return lines


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
