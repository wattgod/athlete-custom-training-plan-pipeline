#!/usr/bin/env python3
"""Compliance gate for real RUN-LIB ``WeekPlan`` placements (R6).

``validate_run_plan`` returns violations rather than raising.  The sanctioned
coached-athlete dispatcher raises them outside any builder ``try``/``except``.
All calendar, race, and template metadata comes from ``WeekPlan`` itself.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta
import re
from typing import Any

from dual_sport_selector import WeekPlan
from run_archetypes import get_run_archetype, get_run_level
from run_renderer import render_run_description


_DAY_OFFSETS = {day: offset for offset, day in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))}
_EASY_CATEGORIES = {"recovery_easy", "endurance_z2"}
_SECTION_HEADING = re.compile(r"^[A-Z][A-Z _-]*:\s*$", re.MULTILINE)


def _value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _week_start(week: Any) -> date | None:
    for key in ("week_start", "start_date"):
        parsed = _parse_date(_value(week, key))
        if parsed is not None:
            return parsed
    return None


def _sessions(week: Any) -> Mapping[str, Any]:
    sessions = _value(week, "sessions")
    if not isinstance(sessions, Mapping):
        raise ValueError("WeekPlan-like value must expose a day -> Session mapping as sessions")
    return sessions


def _is_run(session: Any) -> bool:
    return isinstance(_value(session, "archetype_id"), str) and get_run_archetype(_value(session, "archetype_id")) is not None


def _workout(session: Any) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    archetype_id, level = _value(session, "archetype_id"), _value(session, "level")
    archetype = get_run_archetype(archetype_id)
    if archetype is None:
        raise ValueError(f"Unknown run archetype in placement: {archetype_id!r}")
    level_data = get_run_level(archetype_id, level) if archetype.get("levels") else None
    if archetype.get("levels") and level_data is None:
        raise ValueError(f"Unknown run workout level in placement: {archetype_id!r} L{level!r}")
    return archetype, level_data


def _leaf_segments(segments: Iterable[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for segment in segments:
        if segment.get("type") == "repeat":
            yield from _leaf_segments(segment.get("of", []))
        else:
            yield segment


def _has_intensity(level_data: Mapping[str, Any] | None) -> bool:
    if level_data is None:
        return False
    for segment in _leaf_segments(level_data.get("segments", [])):
        rpe = segment.get("rpe")
        if isinstance(rpe, (list, tuple)) and len(rpe) == 2 and rpe[1] >= 5:
            return True
    return False


def _duration_hours(level_data: Mapping[str, Any] | None) -> float:
    return 0.0 if level_data is None else float(level_data["duration"]) / 3600


def _label(week: Any, index: int) -> str:
    number = _value(week, "plan_week", _value(week, "week_number", index))
    return f"W{number}"


def _violation(week: Any, index: int, rule: str, detail: str) -> str:
    return f"{_label(week, index)} {rule}: {detail}"


def _race_dates(races: Sequence[Any]) -> list[date]:
    dates: list[date] = []
    for race in races:
        parsed = _parse_date(_value(race, "date"))
        if parsed is not None:
            dates.append(parsed)
    return sorted(set(dates))


def _is_race_week(week: Any) -> bool:
    if _value(week, "week_type", "load") == "race":
        return True
    start = _week_start(week)
    if start is not None and any(start <= race_date <= start + timedelta(days=6) for race_date in _race_dates(_value(week, "races", []))):
        return True
    # R5 expresses run races as structure-exempt race-day sessions.
    return any(
        _is_run(session) and bool(_workout(session)[0].get("structure_exempt"))
        for session in _sessions(week).values()
    )


def _template_hours(week: Any) -> float:
    candidate = _value(week, "template_required_hours")
    if not isinstance(candidate, (int, float)) or isinstance(candidate, bool) or candidate < 0:
        raise ValueError("WeekPlan.template_required_hours must be a non-negative number")
    return float(candidate)


def _placed_runs(weeks: Sequence[Any]) -> list[tuple[date, int, Any, Any, Mapping[str, Any], Mapping[str, Any] | None]]:
    placed = []
    for index, week in enumerate(weeks, start=1):
        start = _week_start(week)
        if start is None:
            continue
        for day, session in _sessions(week).items():
            if not _is_run(session) or day not in _DAY_OFFSETS:
                continue
            archetype, level_data = _workout(session)
            placed.append((start + timedelta(days=_DAY_OFFSETS[day]), index, week, session, archetype, level_data))
    return sorted(placed, key=lambda item: item[0])


def _nutrition_body(rendered: str) -> str:
    """Return only NUTRITION's body, never a following heading's content."""
    match = re.search(r"^NUTRITION:\s*$", rendered, flags=re.MULTILINE)
    if match is None:
        return ""
    following = _SECTION_HEADING.search(rendered, match.end())
    return rendered[match.end():following.start() if following else len(rendered)].strip()


def _has_weekend_race(week: Any) -> bool:
    start = _week_start(week)
    if start is None:
        return False
    return any(
        race_date in {start + timedelta(days=5), start + timedelta(days=6)}
        for race_date in _race_dates(_value(week, "races", []))
    )


def _normalized_level(session: Any) -> int | None:
    level = _value(session, "level")
    if isinstance(level, bool):
        return None
    try:
        return int(level)
    except (TypeError, ValueError):
        return None


def validate_run_plan(weeks: list[WeekPlan]) -> list[str]:
    """Return all R-C1..R-C7 violations for real RUN-LIB WeekPlans."""
    if any(not isinstance(week, WeekPlan) for week in weeks):
        raise TypeError("validate_run_plan requires WeekPlan instances")
    violations: list[str] = []
    race_dates = sorted({race_date for week in weeks for race_date in _race_dates(_value(week, "races", []))})
    placed = _placed_runs(weeks)

    # R-C1: intensity must not appear in the two calendar days after any race;
    # the first placed run after every race is gated easy regardless of the gap.
    for race_date in race_dates:
        after_race = [item for item in placed if item[0] > race_date and not item[4].get("structure_exempt")]
        if after_race:
            _, index, week, first_session, first_archetype, _ = after_race[0]
            if not _value(first_session, "gated", False) or first_archetype.get("category") not in _EASY_CATEGORIES:
                violations.append(_violation(week, index, "R-C1", "first run after race must be gated recovery_easy/endurance_z2"))
        for run_date, index, week, session, _, level_data in after_race:
            if run_date <= race_date + timedelta(days=2) and _has_intensity(level_data):
                violations.append(_violation(week, index, "R-C1", "run intensity occurs within 2 calendar days after race"))

    long_runs: list[tuple[int, Any, Any]] = []
    for index, week in enumerate(weeks, start=1):
        sessions = _sessions(week)
        required_hours = 0.0
        optional_hours = 0.0
        has_long_run = False

        for session in sessions.values():
            if not _is_run(session):
                continue
            archetype, level_data = _workout(session)
            duration = _duration_hours(level_data)
            if _value(session, "optional", False):
                optional_hours += duration
                if _has_intensity(level_data):
                    violations.append(_violation(week, index, "R-C5", "optional run contains RPE >=5"))
            else:
                required_hours += duration

            if archetype.get("category") == "long_run":
                has_long_run = True
                long_runs.append((index, week, session))

            # Race briefs deliberately have a description-only renderer and
            # are overlays, not a placed RUN-LIB workout for R-C3.
            if level_data is not None and duration >= 1.5:
                rendered = render_run_description(_value(session, "archetype_id"), _value(session, "level"))
                nutrition = _nutrition_body(rendered)
                if not nutrition.strip() or "none needed" in nutrition.lower():
                    violations.append(_violation(week, index, "R-C3", "run >=90min lacks actionable NUTRITION section"))

        if _value(week, "week_type", "load") == "load" and not _is_race_week(week) and not has_long_run:
            violations.append(_violation(week, index, "R-C2", "non-race load week has no long run"))
        if _has_weekend_race(week) and has_long_run:
            violations.append(_violation(week, index, "R-C7", "Saturday/Sunday race week must not contain a long run"))

        template = _template_hours(week)
        if required_hours < template * 0.90 or required_hours > template * 1.10:
            violations.append(_violation(week, index, "R-C4", f"required run hours {required_hours:.2f} outside ±10% of {template:.2f}h template"))
        if required_hours + optional_hours > template + 0.75:
            violations.append(_violation(week, index, "R-C4", f"all run hours {required_hours + optional_hours:.2f} exceed {template + 0.75:.2f}h optional cap"))

    # R-C6: compare the actual long-run placements, even across a race week.
    for (previous_index, previous_week, previous), (index, week, current) in zip(long_runs, long_runs[1:]):
        del previous_index, previous_week
        previous_level, current_level = _normalized_level(previous), _normalized_level(current)
        if previous_level is not None and current_level is not None and current_level > previous_level + 1:
            violations.append(_violation(week, index, "R-C6", f"long-run level jumps from {previous_level} to {current_level}"))

    return violations
