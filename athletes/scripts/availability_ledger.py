"""G4 recurring-session availability ledger.

One day can contain several immutable athlete/event sessions plus the residual
capacity available to prescription.  This module is deliberately data-only so
both intake and the block builder can use the same accounting.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List

VALID_ORIGINS = {'prescribed', 'athlete_fixed', 'event', 'rest'}
HARD_INTENSITIES = {'hard', 'threshold', 'vo2', 'anaerobic', 'race'}


class AvailabilityLedgerError(ValueError):
    pass


def normalize_sessions(sessions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for raw in sessions or []:
        origin = raw.get('origin', 'athlete_fixed')
        if origin not in VALID_ORIGINS:
            raise AvailabilityLedgerError(f'unknown session origin: {origin}')
        day = str(raw.get('day', '')).title()[:3]
        if not day:
            raise AvailabilityLedgerError('session day is required')
        duration = int(raw.get('duration_min', raw.get('duration', 0)) or 0)
        if duration < 0:
            raise AvailabilityLedgerError('session duration cannot be negative')
        result.append({'day': day, 'slot': raw.get('slot', 'am'), 'duration_min': duration,
                       'intensity': str(raw.get('intensity', 'easy')).lower(),
                       'origin': origin, 'locked': bool(raw.get('locked', origin != 'prescribed')),
                       'title': raw.get('title', '')})
    return result


def build_ledger(sessions: Iterable[Dict[str, Any]], day_caps: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    ledger = {str(day).title()[:3]: {'cap_min': int(cap or 0), 'sessions': [],
                                     'fixed_min': 0, 'residual_min': int(cap or 0),
                                     'hard': False}
              for day, cap in (day_caps or {}).items()}
    for session in normalize_sessions(sessions):
        day = session['day']
        entry = ledger.setdefault(day, {'cap_min': 0, 'sessions': [], 'fixed_min': 0,
                                        'residual_min': 0, 'hard': False})
        entry['sessions'].append(session)
        if session['locked']:
            entry['fixed_min'] += session['duration_min']
        entry['hard'] = entry['hard'] or session['intensity'] in HARD_INTENSITIES
    for day, entry in ledger.items():
        entry['residual_min'] = entry['cap_min'] - entry['fixed_min']
        if entry['residual_min'] < 0:
            raise AvailabilityLedgerError(f'{day} fixed sessions exceed daily cap by {-entry["residual_min"]} min')
    return ledger


def weekly_load_minutes(ledger: Dict[str, Dict[str, Any]], prescribed: Iterable[Dict[str, Any]] = ()) -> int:
    fixed = sum(entry['fixed_min'] for entry in ledger.values())
    planned = sum(int(item.get('duration_min', item.get('duration', 0)) or 0) for item in prescribed)
    return fixed + planned


def hard_days(ledger: Dict[str, Dict[str, Any]], prescribed: Iterable[Dict[str, Any]] = ()) -> set[str]:
    days = {day for day, entry in ledger.items() if entry['hard']}
    days.update(str(item.get('day', '')).title()[:3] for item in prescribed
                if str(item.get('intensity', '')).lower() in HARD_INTENSITIES)
    return days


def contradiction_issues(structured: Iterable[Dict[str, Any]], free_text: str) -> List[Dict[str, str]]:
    """Catch the high-risk claim that a locked commute is an off/rest day."""
    text = (free_text or '').lower()
    issues = []
    for session in normalize_sessions(structured):
        if not session['locked']:
            continue
        day = session['day'].lower()
        if any(f'{day} {word}' in text for word in ('off', 'rest', 'unavailable')):
            issues.append({'id': 'AVAILABILITY_CONTRADICTION', 'source': 'availability_ledger',
                           'severity': 'CRITICAL',
                           'message': f"{session['day']} is described as unavailable but has locked {session['title'] or 'session'}"})
    return issues
