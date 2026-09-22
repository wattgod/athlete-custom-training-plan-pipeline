"""Load targets for the ratified AE-1.17 taper prescription."""

from statistics import mean


TAPER_DAILY_LOAD_FRACTION = 0.70
RACE_WEEK_DAILY_LOAD_FRACTION = 0.50


def taper_day_fraction(
    day_index: int,
    taper_days: int,
    start: float = 0.70,
    end: float = 0.50,
) -> float:
    """Return an exponential decay from ``start`` to ``end``."""
    if taper_days <= 1:
        return float(end)
    index = max(0, min(int(day_index), taper_days - 1))
    progress = index / (taper_days - 1)
    return float(start * ((end / start) ** progress))


def pre_taper_daily_average_tss(
    weeks: list,
    taper_start_plan_week: int,
) -> float:
    """Mean daily TSS of the final two load/testing weeks before taper."""
    candidates = [
        week for week in weeks
        if week.get('plan_week', week.get('week_num', 0)) < taper_start_plan_week
        and week.get('week_type') in ('load', 'testing')
    ]
    candidates = candidates[-2:]
    daily_totals = [
        sum(day.get('tss', 0) for day in week.get('days', [])) / 7.0
        for week in candidates
    ]
    return mean(daily_totals) if daily_totals else 0.0
