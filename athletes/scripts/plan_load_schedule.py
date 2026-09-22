"""Plan-hour scheduling primitives for age-aware, capped load progression."""

from typing import Dict, Optional


def default_meso_pattern(athlete_age: Optional[int]) -> str:
    """Return the AE-1.21 recovery cycle for an athlete's age."""
    try:
        age = float(athlete_age)
    except (TypeError, ValueError):
        age = None
    return '2:1' if age is not None and age >= 40 else '3:1'


def _week_type(week: dict) -> str:
    explicit = week.get('week_type')
    if explicit in ('load', 'testing', 'recovery', 'taper', 'race'):
        return explicit
    if week.get('is_race_week') or week.get('phase') == 'race':
        return 'race'
    if week.get('phase') == 'taper':
        return 'taper'
    if week.get('is_recovery_week'):
        return 'recovery'
    return 'load'


def build_hours_schedule(
    plan_dates: dict,
    *,
    current_hours: float,
    target_hours: float,
    tss_per_hour: float = 55.0,
    max_ctl_per_week: float = 8.0,
) -> Dict[int, float]:
    """Build capped load-week hour targets from the calendar's week sequence."""
    target = max(0.0, float(target_hours or 0))
    current = float(current_hours or 0)
    if target <= 0:
        last_load_hours = 0.0
    elif current <= 0:
        last_load_hours = target
    else:
        last_load_hours = min(target, max(0.60 * target, current))

    if tss_per_hour and float(tss_per_hour) > 0:
        weekly_increment = float(max_ctl_per_week) * 7 / float(tss_per_hour)
    else:
        weekly_increment = 0.0

    schedule: Dict[int, float] = {}
    seen_load = False
    for week in (plan_dates or {}).get('weeks', []):
        plan_week = int(week.get('week', week.get('plan_week')))
        week_type = _week_type(week)
        if week_type in ('load', 'testing'):
            if seen_load:
                last_load_hours = min(
                    target, max(last_load_hours, last_load_hours + weekly_increment)
                )
            seen_load = True
        schedule[plan_week] = last_load_hours
    return schedule
