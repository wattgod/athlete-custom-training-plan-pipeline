"""G4 recurring-session availability ledger.

One day can contain several immutable athlete/event sessions plus the residual
capacity available to prescription.  This module is deliberately data-only so
both intake and the block builder can use the same accounting.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

VALID_ORIGINS = {'prescribed', 'athlete_fixed', 'event', 'rest'}
HARD_INTENSITIES = {'hard', 'threshold', 'vo2', 'anaerobic', 'race'}
_DAY_ORDER = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


class AvailabilityLedgerError(ValueError):
    pass


def normalize_sessions(sessions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for raw in sessions or []:
        origin = raw.get('origin', 'athlete_fixed')
        if origin not in VALID_ORIGINS:
            raise AvailabilityLedgerError(f'unknown session origin: {origin}')
        day = str(raw.get('day', '')).title()[:3]
        if day not in _DAY_ORDER:
            raise AvailabilityLedgerError('session day is required')
        duration = int(raw.get('duration_min', raw.get('duration', 0)) or 0)
        if duration < 0:
            raise AvailabilityLedgerError('session duration cannot be negative')
        slot = str(raw.get('slot', 'am')).lower()
        if slot not in {'am', 'midday', 'pm', 'evening', 'any'}:
            raise AvailabilityLedgerError(f'unknown session slot: {slot}')
        result.append({'day': day, 'slot': slot, 'duration_min': duration,
                       'intensity': str(raw.get('intensity', 'easy')).lower(),
                       'origin': origin, 'locked': bool(raw.get('locked', origin != 'prescribed')),
                       'title': raw.get('title', ''), 'tss': raw.get('tss')})
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


def fixed_session_tss(session: Dict[str, Any]) -> int:
    """Conservative load estimate where the athlete did not supply TSS.

    The ledger must include fixed external work in recovery-ratio checks.  An
    explicit TSS always wins; otherwise use a stable intensity-based estimate
    that is intentionally visible in the PlanIR provenance.
    """
    if session.get('tss') not in (None, ''):
        return int(session['tss'])
    factor = 0.9 if session.get('intensity') in HARD_INTENSITIES else 0.45
    return round(int(session.get('duration_min', 0)) * factor)


def materialize_fixed_sessions(plan: Dict[str, Any], ledger: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Attach immutable sessions to every generated week.

    ``days`` remains one prescribed calendar row per day for the renderer, but
    its ``sessions`` list makes the multi-session day explicit to compliance
    and PlanIR projections.  Week totals are *total* athlete load.
    """
    for week in plan.get('weeks', []):
        by_day = {day.get('day'): day for day in week.get('days', [])}
        fixed_minutes = fixed_tss = 0
        for day, entry in ledger.items():
            fixed = [s for s in entry.get('sessions', []) if s.get('locked')]
            if not fixed:
                continue
            row = by_day.get(day)
            if row is None:
                row = {'day': day, 'name': 'Rest Day', 'role': 'off', 'duration': 0, 'tss': 0}
                week.setdefault('days', []).append(row)
            row.setdefault('sessions', [])
            for session in fixed:
                item = {**session, 'tss': fixed_session_tss(session)}
                row['sessions'].append(item)
                fixed_minutes += item['duration_min']
                fixed_tss += item['tss']
        week['prescribed_duration'] = week.get('total_duration', 0)
        week['prescribed_tss'] = week.get('total_tss', 0)
        week['fixed_duration'] = fixed_minutes
        week['fixed_tss'] = fixed_tss
        week['total_duration'] = week['prescribed_duration'] + fixed_minutes
        week['total_tss'] = week['prescribed_tss'] + fixed_tss
    return plan


def contradiction_issues(structured: Iterable[Dict[str, Any]], free_text: str) -> List[Dict[str, str]]:
    """Catch the high-risk claim that a locked commute is an off/rest day."""
    text = (free_text or '').lower()
    issues = []
    for session in normalize_sessions(structured):
        if not session['locked']:
            continue
        day = session['day'].lower()
        full_day = {'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday',
                    'thu': 'thursday', 'fri': 'friday', 'sat': 'saturday',
                    'sun': 'sunday'}[day]
        if any(f'{label} {word}' in text
               for label in (day, full_day)
               for word in ('off', 'rest', 'unavailable')):
            issues.append({'id': 'AVAILABILITY_CONTRADICTION', 'source': 'availability_ledger',
                           'severity': 'CRITICAL',
                           'message': f"{session['day']} is described as unavailable but has locked {session['title'] or 'session'}"})
    return issues
