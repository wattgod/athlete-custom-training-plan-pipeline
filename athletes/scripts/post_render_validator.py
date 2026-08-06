"""Phase 1 post-render validation over PlanIR + tp_manifest.

The input envelope is explicitly versioned so the later apply-contract
validator can replace this transitional projection without pretending the two
formats are equivalent.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

INPUT_VERSION = "post_render/transitional-planir-tp-manifest/v1"
COUNTED_RACE_WEEK_KINDS = {"bike", "race"}
FIELD_TEST_PATTERNS = {
    "power": re.compile(r"\b(?:ftp|power)\b.*\btest\b|\btest\b.*\bftp\b", re.I),
    "hr": re.compile(r"\b(?:lthr|heart rate|hr)\b.*\btest\b|\btest\b.*\blthr\b", re.I),
    "rpe": re.compile(r"\brpe\b.*\btest\b|\bfield test\b", re.I),
}
INTENSITY_TITLE = re.compile(
    r"\b(vo2|maximal|threshold|over.?under|anaerobic|sprint|g.?spot|microburst)\b",
    re.I,
)
LONG_RIDE_TITLE = re.compile(r"\b(long ride|durability|long endurance)\b", re.I)


class PostRenderValidationError(ValueError):
    pass


def _read(path: Path, loader) -> Dict[str, Any]:
    try:
        with path.open() as handle:
            return loader(handle) or {}
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise PostRenderValidationError(f"cannot read {path.name}: {exc}") from exc


def build_validator_input(
    athlete_dir: Path | str,
    *,
    order_created_at: str = "",
    generation_at: str = "",
    athlete_timezone: str = "",
    weeks_purchased: int | None = None,
) -> Dict[str, Any]:
    athlete_dir = Path(athlete_dir)
    profile = _read(athlete_dir / "profile.yaml", yaml.safe_load)
    fulfillment = profile.get("fulfillment") or {}
    return {
        "input_version": INPUT_VERSION,
        "plan_ir": _read(athlete_dir / "plan_ir.json", json.load),
        "tp_manifest": _read(athlete_dir / "tp_manifest.json", json.load),
        "context": {
            "profile": profile,
            "plan_dates": _read(athlete_dir / "plan_dates.yaml", yaml.safe_load),
            "fueling": _read(athlete_dir / "fueling.yaml", yaml.safe_load),
            "guide_html": (athlete_dir / "training_guide.html").read_text(
                encoding="utf-8") if (athlete_dir / "training_guide.html").exists() else "",
            "order_created_at": order_created_at or fulfillment.get("order_created_at", ""),
            "generation_at": generation_at or fulfillment.get("generation_at", ""),
            "athlete_timezone": athlete_timezone or fulfillment.get("athlete_timezone", ""),
            "weeks_purchased": (
                weeks_purchased if weeks_purchased is not None
                else fulfillment.get("weeks_purchased")
            ),
        },
    }


def _issue(rule_id: str, message: str) -> Dict[str, str]:
    return {
        "id": rule_id,
        "source": "post_render",
        "severity": "CRITICAL",
        "message": message,
    }


def _confirmation(item_id: str, message: str) -> Dict[str, str]:
    return {"id": item_id, "source": "post_render", "message": message}


def _sessions(plan_ir: Dict[str, Any]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    for week in plan_ir.get("weeks") or []:
        number = int(week.get("number", 0))
        for session in week.get("sessions") or []:
            yield number, session


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError as exc:
        raise PostRenderValidationError(f"unknown athlete timezone: {name}") from exc


def _local_date(value: str, timezone_name: str) -> date | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PostRenderValidationError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_timezone(timezone_name))
    return parsed.astimezone(_timezone(timezone_name)).date()


def _session_date(session: Dict[str, Any]) -> date | None:
    try:
        return date.fromisoformat(str(session.get("date") or ""))
    except ValueError:
        return None


def _field_test_metric(session: Dict[str, Any]) -> str | None:
    title = str(session.get("title") or session.get("display_name") or "")
    if str(session.get("type") or "") == "ftp_test":
        return "power"
    for metric, pattern in FIELD_TEST_PATTERNS.items():
        if pattern.search(title):
            return metric
    return None


def _is_intensity(session: Dict[str, Any]) -> bool:
    if session.get("tp_kind") != "bike" or _field_test_metric(session):
        return False
    title = str(session.get("title") or session.get("display_name") or "")
    if INTENSITY_TITLE.search(title):
        return True
    structure = (session.get("structure") or {}).get("structure") or []
    for block in structure:
        for step in block.get("steps") or []:
            target = (step.get("targets") or [{}])[0]
            if max(target.get("maxValue", 0), target.get("minValue", 0)) >= 85:
                return True
    return False


def _is_long_ride(session: Dict[str, Any]) -> bool:
    if session.get("tp_kind") != "bike" or _is_intensity(session):
        return False
    title = str(session.get("title") or session.get("display_name") or "")
    seconds = int(session.get("duration_s") or 0)
    hours = float(session.get("total_time_planned") or 0)
    return bool(LONG_RIDE_TITLE.search(title) or seconds >= 3 * 3600 or hours >= 3)


def _schedule_findings(
    plan_ir: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    roles = profile.get("availability_roles") or {}
    long_days = set(roles.get("long_ride_days") or [])
    interval_days = set(roles.get("interval_days") or [])
    off_days = set(roles.get("off_days") or [])
    mismatch = []
    contradiction = []
    for _, session in _sessions(plan_ir):
        session_day = _session_date(session)
        if not session_day:
            continue
        weekday = session_day.strftime("%A").lower()
        is_race = session.get("tp_kind") == "race" or session.get("type") == "race"
        is_rest = session.get("tp_kind") == "day_off" or session.get("type") == "rest"
        if weekday in off_days and not is_race and not is_rest:
            contradiction.append(f"{session_day.isoformat()} {session.get('title')}")
        if weekday in long_days and weekday not in interval_days and _is_intensity(session):
            mismatch.append(f"intensity on {weekday} ({session_day.isoformat()})")
        if weekday in interval_days and weekday not in long_days and _is_long_ride(session):
            mismatch.append(f"long ride on {weekday} ({session_day.isoformat()})")
    blockers = []
    confirmations = []
    if contradiction:
        blockers.append(_issue(
            "SCHEDULE_CONTRADICTION",
            "Explicit off-day constraints were violated: " + "; ".join(contradiction),
        ))
    if mismatch:
        confirmations.append(_confirmation(
            "SCHEDULE_MISMATCH_CONFIRM",
            "Generated roles differ from stated availability roles: "
            + "; ".join(mismatch),
        ))
    return blockers, confirmations


def validate_transitional_input(
    document: Dict[str, Any],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    if document.get("input_version") != INPUT_VERSION:
        raise PostRenderValidationError("unsupported post-render validator input")
    plan_ir = document.get("plan_ir")
    manifest = document.get("tp_manifest")
    context = document.get("context") or {}
    if not isinstance(plan_ir, dict) or not isinstance(manifest, dict):
        raise PostRenderValidationError("PlanIR and tp_manifest are required")
    if not str(plan_ir.get("plan_ir_version") or "").startswith("0."):
        raise PostRenderValidationError("unsupported transitional PlanIR version")
    if manifest.get("version") != 1:
        raise PostRenderValidationError("unsupported tp_manifest version")

    issues: List[Dict[str, str]] = []
    confirmations: List[Dict[str, str]] = []
    race_date_raw = (plan_ir.get("race_snapshot") or {}).get("date")
    try:
        race_date = date.fromisoformat(str(race_date_raw or ""))
    except ValueError:
        race_date = None
    sessions = list(_sessions(plan_ir))
    race_entries = [
        (week, session) for week, session in sessions
        if race_date and _session_date(session) == race_date
        and (session.get("tp_kind") == "race" or session.get("type") == "race")
    ]
    if not race_entries:
        issues.append(_issue(
            "NO_RACE_DAY_WORKOUT", "Race date has no race-day entry."))
    else:
        race_week = race_entries[0][0]
        counted = sum(
            1 for week, session in sessions
            if week == race_week and session.get("tp_kind") in COUNTED_RACE_WEEK_KINDS
        )
        if counted < 3:
            issues.append(_issue(
                "THIN_RACE_WEEK",
                f"Race week W{race_week} has {counted} counted bike/race entries; minimum is 3.",
            ))

    tests: Dict[Tuple[int, str], int] = {}
    for week, session in sessions:
        metric = _field_test_metric(session)
        if metric:
            tests[(week, metric)] = tests.get((week, metric), 0) + 1
    duplicates = sorted(
        (week, metric, count) for (week, metric), count in tests.items() if count > 1
    )
    if duplicates:
        detail = ", ".join(f"W{week} {metric}={count}" for week, metric, count in duplicates)
        issues.append(_issue(
            "DUPLICATE_FIELD_TEST", "Duplicate same-metric field tests: " + detail))

    timezone_name = str(context.get("athlete_timezone") or "UTC")
    generation_date = _local_date(str(context.get("generation_at") or ""), timezone_name)
    order_date = _local_date(str(context.get("order_created_at") or ""), timezone_name)
    dated_sessions = [(session, _session_date(session)) for _, session in sessions]
    predates_generation = sorted({
        day.isoformat() for _, day in dated_sessions
        if day and generation_date and day < generation_date
    })
    predates_order = sorted({
        day.isoformat() for _, day in dated_sessions
        if day and order_date and day < order_date
    })
    if predates_generation:
        issues.append(_issue(
            "SESSION_PREDATES_GENERATION",
            "Sessions precede the local generation date: " + ", ".join(predates_generation),
        ))
    if predates_order:
        issues.append(_issue(
            "SESSION_PREDATES_ORDER",
            "Sessions precede the local order date: " + ", ".join(predates_order),
        ))

    profile = context.get("profile") or {}
    schedule_issues, schedule_confirmations = _schedule_findings(plan_ir, profile)
    issues.extend(schedule_issues)
    confirmations.extend(schedule_confirmations)

    fueling = context.get("fueling") or {}
    labels = [
        item.get("week_label")
        for item in (fueling.get("gut_training") or {}).get("weekly_progression") or []
    ]
    actual_weeks = sorted({int(week.get("number", 0))
                           for week in plan_ir.get("weeks") or []})
    expected_labels = ["W00" if week == 0 else f"W{week}" for week in actual_weeks]
    if labels != expected_labels:
        issues.append(_issue(
            "FUELING_WEEK_LABEL_MISMATCH",
            f"Fueling labels {labels} do not match plan weeks {expected_labels}.",
        ))

    guide = str(context.get("guide_html") or "")
    target = (fueling.get("prescription") or {}).get("race_target_g_per_hour")
    rendered_targets = [int(value) for value in re.findall(
        r'data-canonical-carb-target="(\d+)"', guide)]
    if target and rendered_targets != [int(target)]:
        issues.append(_issue(
            "CARB_TARGET_CONTRADICTION",
            f"Guide canonical carb targets {rendered_targets} do not equal fueling target {target}.",
        ))

    target_race = profile.get("target_race") or {}
    altitude = (
        target_race.get("start_elevation_asl_ft")
        or target_race.get("average_elevation_asl_ft")
        or 0
    )
    try:
        qualifies_altitude = float(altitude) > 5000
    except (TypeError, ValueError):
        qualifies_altitude = False
    if qualifies_altitude and "Altitude Training" not in guide:
        issues.append(_issue(
            "ALTITUDE_SECTION_MISSING",
            "Frozen race snapshot qualifies for altitude guidance but the guide lacks it.",
        ))

    # Cross-projection sanity: the validator's two named inputs must enumerate
    # the same number of sessions before any semantic result is trusted.
    if len(manifest.get("sessions") or []) != len(sessions):
        raise PostRenderValidationError("PlanIR/tp_manifest session count mismatch")
    return (
        sorted({item["id"]: item for item in issues}.values(), key=lambda item: item["id"]),
        sorted(
            {item["id"]: item for item in confirmations}.values(),
            key=lambda item: item["id"],
        ),
    )
