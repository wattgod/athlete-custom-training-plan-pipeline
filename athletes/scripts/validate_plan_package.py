"""Semantic package consistency gate for PlanIR serializers (G5)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from workout_spec import _mins  # renderer's canonical minute formatter — single source
from zwo_parser import parse_zwo_structure


def _issue(artifact: str, field: str, expected: Any, actual: Any) -> Dict[str, str]:
    return {
        'id': f'PACKAGE_{artifact.upper()}_{field.upper().replace(".", "_")}',
        'source': 'validate_plan_package', 'severity': 'CRITICAL',
        'message': f'{artifact}.{field}: expected {expected!r}, found {actual!r}',
    }


def _load(path: Path, loader):
    if not path.exists():
        return None
    with path.open() as handle:
        return loader(handle) or {}


def _canon_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop None-valued keys so a PlanIR ``Segment`` (all fields present, most
    None) compares equal to a freshly parsed ZWO segment (only populated keys).
    Any real value difference — power, seconds, kind, repeat — still mismatches.
    """
    return [{k: v for k, v in (seg or {}).items() if v is not None} for seg in segments]


def _main_set_text(description: str) -> str:
    match = re.search(r'MAIN SET:\s*(.*?)(?=\n\n[A-Z -]+:|\Z)', description or '', re.S)
    return match.group(1).strip() if match else ''


def validate_plan_package(athlete_dir: Path | str) -> List[Dict[str, str]]:
    """Compare serializer facts against ``plan_ir.json``.

    Missing optional artifacts are not a mismatch here; the pre-delivery gate
    owns required-file checks.  Any artifact that *does* claim a canonical fact
    must agree with PlanIR exactly.
    """
    athlete_dir = Path(athlete_dir)
    ir = _load(athlete_dir / 'plan_ir.json', json.load)
    if not ir:
        return [_issue('plan_ir', 'document', 'valid PlanIR', 'missing or unreadable')]
    issues: List[Dict[str, str]] = []
    race = ir.get('race_snapshot') or {}
    fueling = ir.get('fueling') or {}

    state = _load(athlete_dir / 'fulfillment_status.json', json.load)
    if state and (ir.get('fulfillment') or {}).get('status') != state.get('status'):
        issues.append(_issue('fulfillment_status.json', 'status',
                             (ir.get('fulfillment') or {}).get('status'), state.get('status')))

    fueling_file = _load(athlete_dir / 'fueling.yaml', yaml.safe_load)
    if fueling_file:
        actual = fueling_file.get('prescription') or {}
        if actual != fueling:
            issues.append(_issue('fueling.yaml', 'prescription', fueling, actual))

    # Every PlanIR workout must reparse to precisely the final executable ZWO
    # structure and the description's displayed main set must reproduce it.
    for week in ir.get('weeks', []):
        for session in week.get('sessions', []):
            filename = session.get('source_file')
            if not filename:
                continue
            path = athlete_dir / 'workouts' / filename
            if not path.exists():
                issues.append(_issue('zwo', f'{filename}.file', 'present', 'missing'))
                continue
            parsed = parse_zwo_structure(path)
            if _canon_segments(parsed['segments']) != _canon_segments(session.get('segments', [])):
                issues.append(_issue('zwo', f'{filename}.segments', session.get('segments', []), parsed['segments']))
            main_set = _main_set_text(parsed.get('description', ''))
            for segment in parsed['segments']:
                if segment['kind'] == 'intervals':
                    # Reconstruct the WHOLE rendered interval line (same template and
                    # ``_mins`` formatter the description uses) and require it verbatim.
                    # Substring-per-fragment let a wrong "11.5min recovery" satisfy a
                    # required "1.5min recovery"; a full-line match closes that.
                    expected_line = (
                        f"{segment['repeat']}x{_mins(segment['on_seconds'])} @ "
                        f"{round(segment['on_power'] * 100)}% FTP, "
                        f"{_mins(segment['off_seconds'])} recovery @ "
                        f"{round(segment['off_power'] * 100)}% FTP")
                    if expected_line not in main_set:
                        issues.append(_issue('zwo', f'{filename}.main_set', expected_line, main_set))
                        break

    guide_path = athlete_dir / 'training_guide.html'
    if guide_path.exists():
        guide = guide_path.read_text(errors='replace')
        target = ((fueling.get('race') or {}).get('hourly_target')
                  or (fueling.get('race') or {}).get('target_g_per_hour'))
        # The personalized nutrition card carries "Your target". General
        # education ranges are expressly outside G5's canonical fact scope.
        found_target = re.search(r'(?:Your target|Race target)[^0-9]{0,80}(\d+(?:\.\d+)?)\s*g(?:/| per )hr', guide, re.I)
        if target is not None and found_target and float(found_target.group(1)) != float(target):
            issues.append(_issue('training_guide.html', 'fueling.race_target', target, found_target.group(1)))
        elevation = race.get('elevation_feet')
        if elevation is not None:
            # Only validate an explicit race elevation badge/claim, avoiding
            # unrelated altitude/elevation education elsewhere in the guide.
            found_elevation = re.search(r'(?:Race elevation|Elevation)[^0-9]{0,40}([\d,]+)\s*(?:ft|feet)', guide, re.I)
            if found_elevation and int(found_elevation.group(1).replace(',', '')) != int(float(elevation)):
                issues.append(_issue('training_guide.html', 'race.elevation_feet', elevation, found_elevation.group(1)))

    for week in ir.get('weeks', []):
        for session in week.get('sessions', []):
            if session.get('type') == 'ftp_test' and session.get('source_file'):
                description = parse_zwo_structure(athlete_dir / 'workouts' / session['source_file']).get('description', '')
                if f"Week {week['number']}" not in description:
                    issues.append(_issue('zwo', f"{session['source_file']}.plan_week", f"Week {week['number']}", description[:160]))

    return issues
