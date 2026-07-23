#!/usr/bin/env python3
"""Deterministic RUN-LIB R5 dual-sport weekly-template selector."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

import yaml

from run_archetypes import RUN_ARCHETYPES, get_run_level


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "dual_sport_week.yaml"
DAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DAY_OFFSET = {day: offset for offset, day in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))}
BIKE_DAY_NOTE = "bike day — existing GG bike libraries"
BIKE_OPENERS_NOTE = "bike openers — existing GG bike libraries"


@dataclass(frozen=True)
class Session:
    """A stable calendar-session record consumed by R6 and renderers."""

    day: str
    archetype_id: str | None
    level: int | None
    optional: bool
    gated: bool
    note: str | None


@dataclass(frozen=True)
class WeekPlan:
    """Typed RUN-LIB placement consumed directly by the compliance gate."""

    sessions: dict[str, Session]
    week_start: date
    week_type: Literal["load", "recovery", "race", "taper"]
    template_required_hours: float
    races: list[Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation without dataclass internals."""
        result = asdict(self)
        result["week_start"] = self.week_start.isoformat()
        return result


def _load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("dual_sport_week.yaml must contain a mapping")
    return config


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD") from exc


def _clamp_level(value: Any, minimum: int, maximum: int) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        level = minimum
    return max(minimum, min(maximum, level))


def _category_ids(category: str) -> list[str]:
    return [
        archetype_id
        for archetype_id, archetype in RUN_ARCHETYPES.items()
        if archetype.get("category") == category and archetype.get("levels")
    ]


def _deterministic_id(categories: Sequence[str], week_number: int) -> str:
    """Rotate authored IDs by ISO week, with no random process-global state."""
    choices = [archetype_id for category in categories for archetype_id in _category_ids(category)]
    if not choices:
        raise ValueError(f"No leveled run archetypes for categories {list(categories)!r}")
    return choices[(week_number - 1) % len(choices)]


def _duration_minutes(archetype_id: str, level: int) -> int:
    level_data = get_run_level(archetype_id, level)
    if level_data is None:
        raise ValueError(f"Unknown run workout level: {archetype_id} L{level}")
    return int(level_data["duration"] // 60)


def _level_at_or_below_duration(archetype_id: str, requested_level: int, maximum_minutes: int) -> int:
    """Keep the requested progression level unless its library duration is too long."""
    for level in range(requested_level, 0, -1):
        if _duration_minutes(archetype_id, level) <= maximum_minutes:
            return level
    return 1


def _race_sessions(races: Sequence[Mapping[str, Any]], week_start: date) -> tuple[dict[str, Mapping[str, Any]], list[date]]:
    """Return same-week race overlays plus every valid race date."""
    by_day: dict[str, Mapping[str, Any]] = {}
    all_dates: list[date] = []
    for race in races:
        if not isinstance(race, Mapping):
            raise ValueError("Each race must be a mapping")
        race_date = _parse_date(race.get("date"), "race.date")
        if race.get("priority") not in {"A", "B", "C"}:
            raise ValueError("race.priority must be A, B, or C")
        if race.get("sport") not in {"bike", "run"}:
            raise ValueError("race.sport must be bike or run")
        offset = (race_date - week_start).days
        if not 0 <= offset <= 6:
            raise ValueError("descriptor races must fall within week_start through Sunday")
        day = tuple(DAY_OFFSET)[offset]
        if day in by_day:
            raise ValueError(f"Only one race may occupy {day}")
        by_day[day] = race
        all_dates.append(race_date)
    return by_day, all_dates


def _race_session(day: str, race: Mapping[str, Any]) -> Session:
    if race["sport"] == "bike":
        return Session(day, None, None, False, False, "bike race — existing GG bike libraries")
    priority = race["priority"]
    archetype_id = "run.race_day.a_race_brief" if priority == "A" else "run.race_day.b_race_brief"
    return Session(day, archetype_id, None, False, False, f"{priority}-priority run race")


def _post_race_required(session_date: date, all_race_dates: Sequence[date], scheduled_run_dates: Sequence[date], protected_days: int) -> bool:
    """Whether a session is protected or the first run after a race."""
    for race_date in all_race_dates:
        if session_date <= race_date:
            continue
        if session_date <= race_date + timedelta(days=protected_days):
            return True
        if not any(race_date < other_date < session_date for other_date in scheduled_run_dates):
            return True
    return False


def _week_type(week: Mapping[str, Any], phase: str, has_race: bool) -> Literal["load", "recovery", "race", "taper"]:
    """Resolve the descriptor's explicit type without making race overlays phases."""
    value = week.get("week_type")
    if value is None:
        value = "race" if has_race or phase == "race" else "taper" if phase == "taper" else "load"
    if value not in {"load", "recovery", "race", "taper"}:
        raise ValueError("week_type must be one of load, recovery, race, taper")
    return value


def _run_dates(plan: WeekPlan) -> list[date]:
    """Return ordinary placed run dates; race briefs do not satisfy recovery gates."""
    dates: list[date] = []
    for day, session in plan.sessions.items():
        if not isinstance(session.archetype_id, str) or session.archetype_id.startswith("run.race_day."):
            continue
        if day in DAY_OFFSET:
            dates.append(plan.week_start + timedelta(days=DAY_OFFSET[day]))
    return dates


def _required_hours(sessions: Mapping[str, Session]) -> float:
    """Calculate the authored mandatory run volume for R-C4's real metadata."""
    total = 0.0
    for session in sessions.values():
        if session.optional or session.archetype_id is None or session.level is None:
            continue
        total += _duration_minutes(session.archetype_id, session.level) / 60
    return total


def _easy_session(
    day: str,
    categories: Sequence[str],
    level: int,
    week_number: int,
    *,
    optional: bool,
    maximum_minutes: int | None,
    gated: bool,
    note_prefix: str | None = None,
    gate_note: str | None = None,
) -> Session:
    archetype_id = _deterministic_id(categories, week_number)
    if maximum_minutes is not None and _duration_minutes(archetype_id, 1) > maximum_minutes:
        eligible_ids = [
            candidate
            for category in categories
            for candidate in _category_ids(category)
            if _duration_minutes(candidate, 1) <= maximum_minutes
        ]
        if not eligible_ids:
            raise ValueError(f"No easy run fits the {maximum_minutes}-minute cap")
        archetype_id = eligible_ids[(week_number - 1) % len(eligible_ids)]
    selected_level = _level_at_or_below_duration(archetype_id, level, maximum_minutes) if maximum_minutes is not None else level
    display_name = RUN_ARCHETYPES[archetype_id]["display_name"]
    notes = [f"{note_prefix} {display_name}" if note_prefix else None, gate_note if gated else None]
    note = " ".join(part for part in notes if part) or None
    return Session(day, archetype_id, selected_level, optional, gated, note)


def select_week(
    week: Mapping[str, Any],
    prior_week_races: Sequence[Mapping[str, Any]] | None = None,
    prior_long_run_level: int | None = None,
    *,
    prior_week_plan: WeekPlan | None = None,
) -> WeekPlan:
    """Select a deterministic R5 week from its calendar descriptor.

    Race and taper are distinct accepted phases but both select openers. Race
    overlays preserve the descriptor's phase. ``prior_week_plan`` is for the
    dispatcher only, so a prior week's already-gated first run is not gated a
    second time across the Monday boundary.
    """
    config = _load_config()
    phase = week.get("phase")
    phase_mapping = config["tuesday_phase_mapping"]
    if phase not in phase_mapping:
        raise ValueError(f"phase must be one of {sorted(phase_mapping)}")
    week_start = _parse_date(week.get("week_start"), "week_start")
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    races_value = week.get("races", [])
    if not isinstance(races_value, Sequence) or isinstance(races_value, (str, bytes)):
        raise ValueError("races must be a sequence")
    if prior_week_races is not None and (not isinstance(prior_week_races, Sequence) or isinstance(prior_week_races, (str, bytes))):
        raise ValueError("prior_week_races must be a sequence")

    progression = config["progression"]
    minimum, maximum = progression["minimum_level"], progression["maximum_level"]
    quality_level = _clamp_level(week.get("quality_level"), minimum, maximum)
    long_run_level = _clamp_level(week.get("long_run_level"), minimum, maximum)
    if prior_long_run_level is not None:
        long_run_level = min(long_run_level, _clamp_level(prior_long_run_level, minimum, maximum) + progression["max_long_run_level_increase"])

    current_races = list(races_value)
    prior_races = list(prior_week_races or [])
    overlays, current_race_dates = _race_sessions(current_races, week_start)
    _, prior_race_dates = _race_sessions(prior_races, week_start - timedelta(days=7))
    all_race_dates = current_race_dates + prior_race_dates
    iso_week = week_start.isocalendar().week
    post_race = config["post_race"]
    gate_note = post_race["stairs_gate_note"]
    week_type = _week_type(week, str(phase), bool(current_races))
    week_type_config = config["week_types"][week_type]

    sessions: dict[str, Session] = {
        "Mon": Session("Mon", None, None, False, False, "rest day"),
        "Thu": Session("Thu", None, None, False, False, "athlete-owned day"),
        "Fri": Session("Fri", None, None, False, False, BIKE_DAY_NOTE),
        "Sun": Session("Sun", None, None, False, False, "athlete-owned day"),
    }
    # A Sunday shakeout consumes the single optional-session budget for every
    # race week. All other race weeks may retain Wednesday as their one option.
    sunday_shakeout = "Sun" in overlays and "Sat" not in overlays
    candidate_run_days = {
        "Tue",
        "Sat",
    }
    if not sunday_shakeout:
        candidate_run_days.add("Wed")
    candidate_run_days -= set(overlays)
    scheduled_run_dates = [week_start + timedelta(days=DAY_OFFSET[day]) for day in candidate_run_days]
    if prior_week_plan is not None:
        scheduled_run_dates.extend(_run_dates(prior_week_plan))

    def gated(day: str) -> bool:
        return _post_race_required(
            week_start + timedelta(days=DAY_OFFSET[day]),
            all_race_dates,
            scheduled_run_dates,
            post_race["protected_calendar_days"],
        )

    if "Tue" not in overlays:
        tue_gated = gated("Tue")
        sessions["Tue"] = (
            _easy_session("Tue", post_race["preferred_tuesday_categories"], quality_level, iso_week, optional=False, maximum_minutes=None, gated=True, gate_note=gate_note)
            if tue_gated else Session("Tue", _deterministic_id(phase_mapping[phase], iso_week), quality_level, False, False, None)
        )
    if "Wed" not in overlays and not sunday_shakeout:
        wed_cap = min(config["slots"]["wednesday"]["max_duration_minutes"], week_type_config["monday_equivalent_min"])
        sessions["Wed"] = _easy_session("Wed", config["slots"]["wednesday"]["categories"], quality_level, iso_week, optional=True, maximum_minutes=wed_cap, gated=gated("Wed"), note_prefix=config["slots"]["wednesday"]["title_prefix"], gate_note=gate_note)
    elif sunday_shakeout and "Wed" not in overlays:
        sessions["Wed"] = Session("Wed", None, None, False, False, "optional run suppressed: race-week optional budget")
    if "Sat" not in overlays:
        if sunday_shakeout:
            sessions["Sat"] = _easy_session("Sat", ["recovery_easy"], quality_level, iso_week, optional=True, maximum_minutes=40, gated=gated("Sat"), note_prefix="OPTIONAL:", gate_note=gate_note)
        elif gated("Sat"):
            sessions["Sat"] = _easy_session("Sat", post_race["first_run_categories"], long_run_level, iso_week, optional=False, maximum_minutes=None, gated=True, gate_note=gate_note)
        else:
            sessions["Sat"] = Session("Sat", _deterministic_id(["long_run"], iso_week), long_run_level, False, False, None)

    for day, race in overlays.items():
        sessions[day] = _race_session(day, race)
    if {"Sat", "Sun"} & set(overlays) and "Fri" not in overlays:
        sessions["Fri"] = Session("Fri", None, None, False, False, BIKE_OPENERS_NOTE)

    ordered_sessions = {day: sessions[day] for day in DAY_ORDER}
    template_hours = week.get("template_required_hours")
    if not isinstance(template_hours, (int, float)) or isinstance(template_hours, bool) or template_hours < 0:
        template_hours = _required_hours(ordered_sessions)
    return WeekPlan(ordered_sessions, week_start, week_type, float(template_hours), current_races)
