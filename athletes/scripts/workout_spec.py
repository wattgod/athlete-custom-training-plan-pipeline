"""Executable workout segments and their human-readable projection.

The ZWO blocks are the source of truth.  This small adapter exists so every
renderer can derive its MAIN SET wording from the same executable segments.
"""
from __future__ import annotations

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


def render_main_set(segments: Iterable[Dict[str, Any]]) -> str:
    """Render only training work, never infer reps/duration from prose."""
    lines = []
    for segment in segments:
        if segment['kind'] in ('warmup', 'cooldown', 'ramp'):
            continue
        if segment['kind'] == 'intervals':
            lines.append(f"- {segment['repeat']}x{_mins(segment['on_seconds'])} @ {round(segment['on_power'] * 100)}% FTP, "
                         f"{_mins(segment['off_seconds'])} recovery @ {round(segment['off_power'] * 100)}% FTP")
        elif segment['kind'] == 'steady':
            lines.append(f"- {_mins(segment['seconds'])} @ {round(segment['power'] * 100)}% FTP")
        elif segment['kind'] == 'free_ride':
            lines.append(f"- {_mins(segment['seconds'])} free ride")
    return '\n'.join(lines) or '- Recovery / rest as scheduled'


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
