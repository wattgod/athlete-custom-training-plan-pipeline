"""CTL/ATL/TSB trajectory model for planned bike load only."""

from dataclasses import dataclass
from datetime import date
from numbers import Number
from typing import Any, Dict, List, Optional, Sequence

from plan_load_schedule import default_meso_pattern

TAU_CTL = 42
TAU_ATL_DEFAULT = 7
ESTIMATED_TSS_PER_HOUR = 55


@dataclass(frozen=True)
class PMCState:
    ctl: float
    atl: float

    @property
    def tsb(self) -> float:
        return self.ctl - self.atl


def step(
    state: PMCState,
    tss: float,
    tau_ctl: float = TAU_CTL,
    tau_atl: float = TAU_ATL_DEFAULT,
) -> PMCState:
    """Advance CTL and ATL by one day of training stress."""
    if tau_ctl <= 0 or tau_atl <= 0:
        raise ValueError("PMC time constants must be positive")
    return PMCState(
        ctl=state.ctl + (float(tss) - state.ctl) / tau_ctl,
        atl=state.atl + (float(tss) - state.atl) / tau_atl,
    )


def simulate(
    daily_tss: Sequence[float],
    start_ctl: float,
    start_atl: Optional[float] = None,
    tau_ctl: float = TAU_CTL,
    tau_atl: float = TAU_ATL_DEFAULT,
) -> List[PMCState]:
    """Return end-of-day PMC states for a sequence of daily TSS values."""
    state = PMCState(float(start_ctl), float(start_ctl if start_atl is None else start_atl))
    states = []
    for tss in daily_tss:
        state = step(state, tss, tau_ctl=tau_ctl, tau_atl=tau_atl)
        states.append(state)
    return states


def _number(value: Any) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _hours_from_profile(profile: dict) -> tuple[float, str, bool]:
    history = (profile or {}).get("training_history", {}) or {}
    sources = (
        (history, ("current_weekly_hours", "weekly_hours", "hours"),
         "training_history"),
        (profile or {}, ("weekly_hours", "hours"), "profile"),
    )
    for source, keys, source_name in sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                try:
                    hours = float(value)
                    if hours > 0:
                        return hours, f"{source_name}.{key}", False
                except (TypeError, ValueError):
                    pass
    availability = (profile or {}).get("weekly_availability", {}) or {}
    for key in ("cycling_hours_target", "total_hours_available"):
        value = availability.get(key)
        if value not in (None, ""):
            try:
                hours = float(value)
                if hours > 0:
                    return hours, f"weekly_availability.{key}", True
            except (TypeError, ValueError):
                pass
    return 0.0, "unknown", False


def _plan_load_density(plan: Optional[dict]) -> Optional[float]:
    total_tss = 0.0
    total_hours = 0.0
    for week in (plan or {}).get("weeks", []):
        if week.get("week_type") != "load":
            continue
        for day in week.get("days", []):
            duration = float(day.get("duration") or 0)
            if duration > 0:
                total_tss += float(day.get("tss") or 0)
                total_hours += duration / 60
    if total_hours <= 0:
        return None
    return total_tss / total_hours


def _cycle_factor(
    meso_pattern: Optional[str],
    athlete_age: Optional[int],
) -> tuple[float, str]:
    pattern = meso_pattern or default_meso_pattern(athlete_age)
    try:
        load_weeks = int(str(pattern).split(':', 1)[0])
    except (TypeError, ValueError):
        pattern = default_meso_pattern(athlete_age)
        load_weeks = int(pattern.split(':', 1)[0])
    factor = (load_weeks + 0.65) / (load_weeks + 1)
    return factor, pattern


def estimate_start_ctl(
    profile: dict,
    plan: Optional[dict] = None,
    meso_pattern: Optional[str] = None,
    athlete_age: Optional[int] = None,
) -> dict:
    """Estimate the athlete's starting CTL and preserve its provenance."""
    markers = (profile or {}).get("fitness_markers", {}) or {}
    if _number(markers.get("ctl")):
        value = float(markers["ctl"])
        return {
            "ctl": value,
            "value_class": "measured",
            "basis": "fitness_markers.ctl",
            "inputs": {"ctl": value},
        }

    hours, hours_source, hours_fallback = _hours_from_profile(profile or {})
    tss_per_hour = _plan_load_density(plan)
    cycle_factor, effective_meso_pattern = _cycle_factor(
        meso_pattern or (plan or {}).get("meso_pattern"),
        athlete_age if athlete_age is not None else (profile or {}).get("age"),
    )
    if tss_per_hour is None:
        tss_per_hour = ESTIMATED_TSS_PER_HOUR
        basis = (
            "training_history weekly hours at default 55 TSS/hour ÷ 7 "
            "× cycle factor"
        )
        source = "default"
    else:
        basis = (
            "training_history weekly hours at this plan's load-week "
            f"dose density ({tss_per_hour:.1f} TSS/h) ÷ 7 × cycle factor"
        )
        source = "plan_load_weeks"
    if hours_fallback:
        basis += " (current hours not reported; assumed at plan target)"
    value = hours * tss_per_hour / 7 * cycle_factor
    return {
        "ctl": value,
        "value_class": "inferred",
        "basis": basis,
        "inputs": {
            "current_weekly_hours": hours,
            "hours_source": hours_source,
            "tss_per_hour": tss_per_hour,
            "source": source,
            "cycle_factor": cycle_factor,
            "meso_pattern": effective_meso_pattern,
        },
    }


def _day_tss(day: dict) -> float:
    prescribed_tss = float(day.get("tss") or 0)
    if any(day.get(flag) for flag in (
        "sessions_included",
        "nested_sessions_included",
        "sessions_tss_included",
        "nested_load_included",
        "fixed_tss_included",
    )):
        return prescribed_tss
    return prescribed_tss + sum(
        float(session.get("tss") or 0)
        for session in day.get("sessions", [])
    )


def plan_daily_tss(
    plan: dict,
    plan_dates: dict,
    daily_override: Optional[List[dict]] = None,
) -> List[dict]:
    """Join block-builder day load to the authoritative calendar dates."""
    override_by_date = {
        entry.get("date"): float(entry.get("tss") or 0)
        for entry in (daily_override or [])
        if entry.get("date")
    }
    plan_by_week = {
        week.get("plan_week", week.get("week")): week
        for week in (plan or {}).get("weeks", [])
    }
    entries = []
    for calendar_week in (plan_dates or {}).get("weeks", []):
        plan_week = calendar_week.get("week", calendar_week.get("plan_week"))
        block_week = plan_by_week.get(plan_week, {})
        days_by_name = {
            day.get("day"): day for day in block_week.get("days", [])
        }
        week_type = block_week.get("week_type") or calendar_week.get("week_type")
        if not week_type:
            if calendar_week.get("is_recovery_week"):
                week_type = "recovery"
            elif calendar_week.get("phase") == "taper":
                week_type = "taper"
            elif calendar_week.get("is_race_week") or calendar_week.get("phase") == "race":
                week_type = "race"
            else:
                week_type = "load"
        for calendar_day in calendar_week.get("days", []):
            block_day = days_by_name.get(calendar_day.get("day"), {})
            entries.append({
                "date": calendar_day.get("date"),
                "plan_week": plan_week,
                "week_type": week_type,
                "tss": (
                    override_by_date[calendar_day.get("date")]
                    if calendar_day.get("date") in override_by_date
                    else _day_tss(block_day)
                ),
            })
    return entries


def _week_start_state(
    days: List[dict],
    plan_week: Any,
    start_ctl: float,
) -> float:
    prior = [day["ctl"] for day in days if day["plan_week"] < plan_week]
    return prior[-1] if prior else float(start_ctl)


def build_trajectory(
    plan: dict,
    plan_dates: dict,
    start_ctl: float,
    *,
    tau_atl: float = TAU_ATL_DEFAULT,
    b_race_dates: Sequence[str] = (),
    build_ctl: Optional[float] = None,
    daily_override: Optional[List[dict]] = None,
) -> dict:
    """Build a JSON-serialisable daily and weekly PMC trajectory."""
    daily = plan_daily_tss(plan, plan_dates, daily_override=daily_override)
    states = simulate(
        [entry["tss"] for entry in daily],
        start_ctl=start_ctl,
        tau_atl=tau_atl,
    )
    days = []
    for entry, state in zip(daily, states):
        days.append({
            **entry,
            "ctl": state.ctl,
            "atl": state.atl,
            "tsb": state.tsb,
        })

    weekly = []
    for plan_week in dict.fromkeys(day["plan_week"] for day in days):
        week_days = [day for day in days if day["plan_week"] == plan_week]
        if not week_days:
            continue
        start = _week_start_state(days, plan_week, start_ctl)
        end = week_days[-1]
        weekly.append({
            "plan_week": plan_week,
            "week_type": week_days[0]["week_type"],
            "start_ctl": start,
            "end_ctl": end["ctl"],
            "end_atl": end["atl"],
            "end_tsb": end["tsb"],
            "min_tsb": min(day["tsb"] for day in week_days),
            "ctl_delta": end["ctl"] - start,
        })

    taper_week = next(
        (week for week in weekly if week["week_type"] == "taper"),
        None,
    )
    if taper_week is None:
        taper_week = next(
            (week for week in weekly if week["week_type"] == "race"),
            None,
        )
    taper_start_ctl = (
        taper_week["start_ctl"] if taper_week is not None else float(start_ctl)
    )

    race_calendar_day = next(
        (
            calendar_day
            for calendar_week in (plan_dates or {}).get("weeks", [])
            for calendar_day in calendar_week.get("days", [])
            if calendar_day.get("is_race_day")
        ),
        None,
    )
    day_by_date = {day["date"]: day for day in days}

    def state_before(target_date: str) -> PMCState:
        target = date.fromisoformat(target_date)
        prior = [
            day for day in days
            if day.get("date") and date.fromisoformat(day["date"]) < target
        ]
        if not prior:
            return PMCState(float(start_ctl), float(start_ctl))
        day = prior[-1]
        return PMCState(day["ctl"], day["atl"])

    race_day = None
    if race_calendar_day and race_calendar_day.get("date") in day_by_date:
        race_date = race_calendar_day["date"]
        state = state_before(race_date)
        race_day = {
            "date": race_date,
            "ctl": state.ctl,
            "atl": state.atl,
            "tsb": state.tsb,
        }

    b_races = []
    requested_b_dates = set(b_race_dates or ())
    for day in days:
        if day["date"] not in requested_b_dates:
            continue
        state = state_before(day["date"])
        b_races.append({"date": day["date"], "tsb": state.tsb})

    recovery_weeks = [
        (index, week)
        for index, week in enumerate(weekly)
        if week["week_type"] == "recovery"
    ]
    monthly_ramps = []
    previous_recovery_ctl = float(start_ctl)
    previous_recovery_date = days[0]["date"] if days else None
    for _, recovery_week in recovery_weeks:
        week_days = [
            day for day in days
            if day["plan_week"] == recovery_week["plan_week"]
        ]
        if not week_days:
            continue
        to_date = week_days[-1]["date"]
        days_between = max(
            1,
            (date.fromisoformat(to_date)
             - date.fromisoformat(previous_recovery_date)).days,
        )
        monthly_ramps.append({
            "from_date": previous_recovery_date,
            "to_date": to_date,
            "ctl_delta_per_28d": (
                (recovery_week["end_ctl"] - previous_recovery_ctl)
                * 28 / days_between
            ),
        })
        previous_recovery_ctl = recovery_week["end_ctl"]
        previous_recovery_date = to_date

    return {
        "start_ctl": float(start_ctl),
        "build_ctl": float(start_ctl if build_ctl is None else build_ctl),
        "tau_ctl": TAU_CTL,
        "tau_atl": tau_atl,
        "days": days,
        "weeks": weekly,
        "taper_start_ctl": taper_start_ctl,
        "peak_ctl": max((day["ctl"] for day in days), default=float(start_ctl)),
        "race_day": race_day,
        "b_races": b_races,
        "monthly_ramps": monthly_ramps,
    }
