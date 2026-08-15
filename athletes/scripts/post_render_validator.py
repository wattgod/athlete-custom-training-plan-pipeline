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
    r"\b(vo2(?:max)?|maximal|threshold|over.?under|anaerobic|sprint|g.?spot|microburst)\b",
    re.I,
)
LONG_RIDE_TITLE = re.compile(r"\b(long ride|durability|long endurance)\b", re.I)
TP_KINDS = ("bike", "strength", "day_off", "race")
TP_SESSION_FIELDS = (
    "date", "title", "display_name", "filename_stem", "description",
    "tp_kind", "workout_type_value_id", "tss_planned",
    "total_time_planned", "structure", "series_id", "series_index",
    "series_total", "order_on_day", "strength_template", "archetype_id",
    "race",
)


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


def _issue(
    rule_id: str, message: str, *, review_value: Any = None,
    basis: str = "post-render PlanIR and TP manifest validation",
    display_unit: str | None = None,
) -> Dict[str, Any]:
    item = {
        "id": rule_id,
        "source": "post_render",
        "severity": "CRITICAL",
        "message": message,
        "review_value": message if review_value is None else review_value,
        "basis": basis,
        "sensitivity": "internal",
    }
    if display_unit:
        item["display_unit"] = display_unit
    return item


def _confirmation(
    item_id: str, message: str, *, review_value: Any = None,
    basis: str = "generated schedule compared with athlete availability",
) -> Dict[str, Any]:
    return {
        "id": item_id,
        "source": "post_render",
        "message": message,
        "review_value": message if review_value is None else review_value,
        "basis": basis,
        "sensitivity": "personal",
    }


def _sessions(plan_ir: Dict[str, Any]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    for week in plan_ir.get("weeks") or []:
        number = int(week.get("number", 0))
        for session in week.get("sessions") or []:
            yield number, session


def _validate_manifest_projection(
    plan_ir: Dict[str, Any], manifest: Dict[str, Any],
) -> None:
    """Prove the executable manifest is the semantic PlanIR projection."""
    manifest_sessions = manifest.get("sessions")
    plan_sessions = [session for _, session in _sessions(plan_ir)]
    if not isinstance(manifest_sessions, list) or not manifest_sessions:
        raise PostRenderValidationError("tp_manifest.sessions must be non-empty")
    if len(manifest_sessions) != len(plan_sessions):
        raise PostRenderValidationError("PlanIR/tp_manifest session count mismatch")
    plan_weeks = max(
        (int(week.get("number", 0)) for week in plan_ir.get("weeks") or []
         if int(week.get("number", 0)) > 0),
        default=0,
    )
    athlete_name = str((plan_ir.get("athlete") or {}).get("name") or "Athlete")
    race_snapshot = plan_ir.get("race_snapshot") or {}
    race_name = str(race_snapshot.get("name") or "Race")
    expected_top_level = {
        "plan_title": f"{athlete_name} · {race_name} · {plan_weeks}wk [CUSTOM]",
        "athlete": athlete_name,
        "race": {
            "name": race_snapshot.get("name"),
            "date": race_snapshot.get("date"),
            "priority": "A",
        },
    }
    for field, expected_value in expected_top_level.items():
        if manifest.get(field) != expected_value:
            raise PostRenderValidationError(
                f"tp_manifest.{field} does not match PlanIR projection")

    counts = {kind: 0 for kind in TP_KINDS}
    for index, (source, projected) in enumerate(
        zip(plan_sessions, manifest_sessions)
    ):
        if not isinstance(projected, dict):
            raise PostRenderValidationError(
                f"tp_manifest.sessions[{index}] must be an object")
        expected = {field: source.get(field) for field in TP_SESSION_FIELDS}
        actual = {field: projected.get(field) for field in TP_SESSION_FIELDS}
        if actual != expected:
            differing = sorted(
                field for field in TP_SESSION_FIELDS
                if actual[field] != expected[field]
            )
            raise PostRenderValidationError(
                f"tp_manifest semantic drift at session {index}: "
                + ", ".join(differing)
            )
        kind = projected.get("tp_kind")
        if kind not in counts:
            raise PostRenderValidationError(
                f"tp_manifest.sessions[{index}] has unknown tp_kind")
        counts[kind] += 1

    expected_counts = manifest.get("expected")
    canonical_counts = {**counts, "total": sum(counts.values())}
    if expected_counts != canonical_counts:
        raise PostRenderValidationError(
            "tp_manifest.expected does not match projected session kinds")


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
    for metric, pattern in FIELD_TEST_PATTERNS.items():
        if pattern.search(title):
            return metric
    # Transitional authored shape still labels every field-test source ZWO as
    # ftp_test; the canonical title is authoritative for HR/RPE projections.
    if str(session.get("type") or "") == "ftp_test":
        return "power"
    return None


try:
    from block_compliance import INTENSITY_TYPES as _CANONICAL_INTENSITY_TYPES
    _CANONICAL_INTENSITY = re.compile(
        r"\b(?:" + "|".join(
            re.escape(name) for name in sorted(_CANONICAL_INTENSITY_TYPES)
        ) + r")\b",
        re.I,
    )
except ImportError:  # degrade to the regex + structure fallback below
    _CANONICAL_INTENSITY = None
OPENERS_TITLE = re.compile(r"\bopeners?\b", re.I)


def _is_intensity(session: Dict[str, Any]) -> bool:
    if session.get("tp_kind") != "bike" or _field_test_metric(session):
        return False
    title = str(session.get("title") or session.get("display_name") or "")
    # Openers are explicitly NOT intensity (constants.INTENSITY_WORKOUT_TYPES
    # note) — a taper opener with 30s @ 110% must not generate a
    # systematically-false schedule-mismatch confirmation.
    if OPENERS_TITLE.search(title):
        return False
    # Canonical workout identity first: RPE-controlled sessions carry NO
    # structure (project_tp_structure returns None), so names like Tempo,
    # Cadence Work, SFR, Mixed Intervals would otherwise slip through and
    # repeat the partial-disclosure failure for RPE athletes.
    haystack = " ".join(
        str(session.get(field) or "")
        for field in ("title", "display_name", "archetype_id")
    )
    if _CANONICAL_INTENSITY is not None and _CANONICAL_INTENSITY.search(
            haystack.replace("_", " ")):
        return True
    if INTENSITY_TITLE.search(title):
        return True
    # Documented fallback: any structured step targeting >= 85% FTP.
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
        # An athlete who named explicit interval days gets told about EVERY
        # intensity session outside them, not only the ones that collided
        # with a long-ride day. On a real order (intervals: wednesday) the
        # generator trained Tue/Thu/Fri and this item disclosed only the two
        # Saturdays — the coach confirmed on partial information.
        if (interval_days and weekday not in interval_days
                and weekday not in long_days and _is_intensity(session)):
            mismatch.append(
                f"intensity on {weekday} ({session_day.isoformat()}) "
                "outside stated interval days")
    blockers = []
    confirmations = []
    if contradiction:
        blockers.append(_issue(
            "SCHEDULE_CONTRADICTION",
            "Explicit off-day constraints were violated: " + "; ".join(contradiction),
            review_value={
                "off_days": sorted(off_days),
                "scheduled_conflicts": contradiction,
            },
        ))
    if mismatch:
        confirmations.append(_confirmation(
            "SCHEDULE_MISMATCH_CONFIRM",
            "Generated roles differ from stated availability roles: "
            + "; ".join(mismatch),
            review_value={
                "long_ride_days": sorted(long_days),
                "interval_days": sorted(interval_days),
                "generated_mismatches": mismatch,
            },
        ))
    return blockers, confirmations


def _day_cap_findings(
    plan_ir: Dict[str, Any], profile: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Flag calendar days whose combined sessions exceed the athlete's
    stated per-day duration cap (profile.preferred_days.*.max_duration_min).

    On a real order a 30-minute strength session stacked on a 120-minute
    interval ride produced a 150-minute Thursday against a 120-minute cap
    and nothing surfaced it. Race day and day-off entries are exempt; a
    missing or non-positive cap means the day is not cap-checked — EXCEPT
    when preferred_days marks the day unavailable. An unavailable day not
    covered by availability_roles.off_days (the two fields are duplicated
    by intake and can drift) would otherwise be completely silent, so it is
    treated as a zero cap here; when off_days DOES cover the weekday,
    SCHEDULE_CONTRADICTION owns it and this rule stays quiet.
    """
    preferred_days = profile.get("preferred_days") or {}
    role_off_days = set(
        (profile.get("availability_roles") or {}).get("off_days") or [])
    totals: Dict[date, Dict[str, Any]] = {}
    for _, session in _sessions(plan_ir):
        session_day = _session_date(session)
        if not session_day:
            continue
        if session.get("tp_kind") in ("race", "day_off"):
            continue
        seconds = int(session.get("duration_s") or 0)
        if not seconds:
            seconds = int(float(session.get("total_time_planned") or 0) * 3600)
        entry = totals.setdefault(
            session_day, {"minutes": 0.0, "titles": []})
        entry["minutes"] += seconds / 60.0
        entry["titles"].append(str(session.get("title") or ""))
    violations = []
    for session_day in sorted(totals):
        weekday = session_day.strftime("%A").lower()
        day_prefs = preferred_days.get(weekday) or {}
        try:
            cap = int(day_prefs.get("max_duration_min") or 0)
        except (TypeError, ValueError):
            cap = 0
        unavailable = (
            str(day_prefs.get("availability") or "").lower() == "unavailable"
            and weekday not in role_off_days
        )
        if unavailable:
            cap = 0
        total_min = int(round(totals[session_day]["minutes"]))
        if (cap > 0 and total_min > cap) or (unavailable and total_min > 0):
            violations.append({
                "date": session_day.isoformat(),
                "weekday": weekday,
                "total_min": total_min,
                "cap_min": cap,
                "unavailable_day": unavailable,
                "sessions": totals[session_day]["titles"],
            })
    if not violations:
        return []
    detail = "; ".join(
        (f"{item['date']} ({item['weekday']}) {item['total_min']}min "
         "scheduled on a stated-unavailable day")
        if item["unavailable_day"] else
        (f"{item['date']} ({item['weekday']}) {item['total_min']}min > "
         f"{item['cap_min']}min cap")
        for item in violations)
    return [_confirmation(
        "DAY_DURATION_OVER_CAP",
        "Scheduled day totals exceed the athlete's stated daily caps: " + detail,
        review_value={"violations": violations},
        basis="generated day totals compared with stated per-day duration caps",
    )]


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
    _validate_manifest_projection(plan_ir, manifest)

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
            "NO_RACE_DAY_WORKOUT", "Race date has no race-day entry.",
            review_value={"race_date": race_date_raw, "race_day_entries": 0}))
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
                review_value={
                    "race_week": race_week,
                    "counted_entries": counted,
                    "minimum_entries": 3,
                    "counted_kinds": sorted(COUNTED_RACE_WEEK_KINDS),
                },
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
            "DUPLICATE_FIELD_TEST", "Duplicate same-metric field tests: " + detail,
            review_value=[
                {"week": week, "metric": metric, "count": count}
                for week, metric, count in duplicates
            ]))

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
            review_value={
                "session_dates": predates_generation,
                "generation_date": generation_date.isoformat() if generation_date else None,
                "athlete_timezone": timezone_name,
            },
        ))
    if predates_order:
        issues.append(_issue(
            "SESSION_PREDATES_ORDER",
            "Sessions precede the local order date: " + ", ".join(predates_order),
            review_value={
                "session_dates": predates_order,
                "order_date": order_date.isoformat() if order_date else None,
                "athlete_timezone": timezone_name,
            },
        ))

    profile = context.get("profile") or {}
    schedule_issues, schedule_confirmations = _schedule_findings(plan_ir, profile)
    issues.extend(schedule_issues)
    confirmations.extend(schedule_confirmations)
    confirmations.extend(_day_cap_findings(plan_ir, profile))

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
            review_value={"fueling_labels": labels, "plan_labels": expected_labels},
        ))

    guide = str(context.get("guide_html") or "")
    target = (fueling.get("prescription") or {}).get("race_target_g_per_hour")
    rendered_targets = [int(value) for value in re.findall(
        r'data-canonical-carb-target="(\d+)"', guide)]
    if target and rendered_targets != [int(target)]:
        issues.append(_issue(
            "CARB_TARGET_CONTRADICTION",
            f"Guide canonical carb targets {rendered_targets} do not equal fueling target {target}.",
            review_value={
                "guide_targets_g_per_hour": rendered_targets,
                "fueling_target_g_per_hour": int(target),
            },
            display_unit="g/h",
        ))

    target_race = profile.get("target_race") or {}
    race_metadata = target_race.get("race_metadata") or {}
    try:
        altitude = max(
            float(race_metadata.get("start_elevation_feet") or 0),
            float(race_metadata.get("avg_elevation_feet") or 0),
        )
        qualifies_altitude = altitude > 5000
    except (TypeError, ValueError):
        qualifies_altitude = False
    if qualifies_altitude and "Altitude Training" not in guide:
        issues.append(_issue(
            "ALTITUDE_SECTION_MISSING",
            "Frozen race snapshot qualifies for altitude guidance but the guide lacks it.",
            review_value={
                "qualifying_elevation_feet": altitude,
                "altitude_section_present": False,
            },
            display_unit="ft",
        ))

    return (
        sorted({item["id"]: item for item in issues}.values(), key=lambda item: item["id"]),
        sorted(
            {item["id"]: item for item in confirmations}.values(),
            key=lambda item: item["id"],
        ),
    )
