"""Public-safe contract for the marketing training-plan simulator.

This module is deliberately separate from ``engine_adapter``.  The Endure
block contract is frozen, while the athlete-plan engine and its canonical
TrainingPeaks projection are still evolving.  The three public sites consume
only the allowlisted ``training-plan-preview/v1`` shape defined here; a thin
server-side adapter can map the finalized engine interface into ``source``
without exposing library IDs, source paths, secrets, or compliance internals.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


REQUEST_SCHEMA_VERSION_V1 = "training-plan-preview-request/v1"
REQUEST_SCHEMA_VERSION_V2 = "training-plan-preview-request/v2"
RESPONSE_SCHEMA_VERSION_V1 = "training-plan-preview/v1"
RESPONSE_SCHEMA_VERSION_V2 = "training-plan-preview/v2"
# Backwards-compatible aliases for existing v1 consumers.
REQUEST_SCHEMA_VERSION = REQUEST_SCHEMA_VERSION_V1
RESPONSE_SCHEMA_VERSION = RESPONSE_SCHEMA_VERSION_V1

BRANDS = {"gravel_god", "roadie_labs", "xc_ski_labs"}
EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced"}
DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SESSION_KINDS = {"bike", "ski", "strength", "race", "rest", "note"}
FUEL_TAGS = {"high", "moderate", "practice", "none"}
GOAL_TYPES = {"finish", "compete", "podium"}
CONTROL_METHODS = {"power", "hr", "rpe"}
STRENGTH_EQUIPMENT = {"none", "home-basic", "full-gym"}
ROAD_EVENT_FORMATS = {
    "generic_road", "criterium", "hill_climb", "time_trial",
    "stage_race", "fondo",
}
ROAD_PROFILE_VERSION = "road/v1"

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,95}$")
_INTERNAL_TEXT_RE = re.compile(
    r"(?:library_item_id|source_file|compliance|internal[_ -]?only|"
    r"engine_shared_secret|railway_git_commit_sha)",
    re.IGNORECASE,
)

_VOICE_FILES = (
    "athletes/config/voice_rules.yaml",
    "athletes/scripts/story_notes.py",
    "athletes/scripts/delivery_notes.py",
    "athletes/scripts/apply_contract.py",
    "athletes/scripts/voice_lint.py",
)


class PreviewContractError(ValueError):
    """Raised when public request or canonical preview input is invalid."""


def _text(value: Any, field: str, *, maximum: int, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise PreviewContractError(f"{field} must be a string")
    value = " ".join(value.split()).strip()
    if required and not value:
        raise PreviewContractError(f"{field} is required")
    if len(value) > maximum:
        raise PreviewContractError(f"{field} must be at most {maximum} characters")
    if _INTERNAL_TEXT_RE.search(value):
        raise PreviewContractError(f"{field} contains an internal token")
    return value


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreviewContractError(f"{field} must be a number")
    if int(value) != value:
        raise PreviewContractError(f"{field} must be a whole number")
    result = int(value)
    if not minimum <= result <= maximum:
        raise PreviewContractError(
            f"{field} must be between {minimum} and {maximum}")
    return result


def _normalize_request_v1(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and normalize the browser request used as a cache key."""
    if not isinstance(payload, Mapping):
        raise PreviewContractError("body must be an object")
    if payload.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise PreviewContractError(
            f"schema_version must be {REQUEST_SCHEMA_VERSION}")

    brand = payload.get("brand")
    if brand not in BRANDS:
        raise PreviewContractError("brand is not supported")

    race = payload.get("race")
    if not isinstance(race, Mapping):
        raise PreviewContractError("race must be an object")
    slug = _text(race.get("slug"), "race.slug", maximum=100)
    if not _SLUG_RE.fullmatch(slug):
        raise PreviewContractError("race.slug is invalid")
    name = _text(race.get("name"), "race.name", maximum=160)
    discipline = _text(
        race.get("discipline"), "race.discipline", maximum=40)

    raw_demands = race.get("demands")
    if not isinstance(raw_demands, Mapping) or not raw_demands:
        raise PreviewContractError("race.demands must be a non-empty object")
    demands: Dict[str, int] = {}
    for raw_key, raw_value in sorted(raw_demands.items()):
        key = _text(raw_key, "race.demands key", maximum=40)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise PreviewContractError(f"race.demands.{key} has an invalid key")
        demands[key] = _integer(raw_value, f"race.demands.{key}", 0, 10)

    rider = payload.get("rider")
    if not isinstance(rider, Mapping):
        raise PreviewContractError("rider must be an object")
    hours = _integer(rider.get("hours_per_week"), "rider.hours_per_week", 4, 18)
    experience = rider.get("experience_level")
    if experience not in EXPERIENCE_LEVELS:
        raise PreviewContractError("rider.experience_level is not supported")
    raw_days = rider.get("preferred_days")
    if not isinstance(raw_days, Sequence) or isinstance(raw_days, (str, bytes)):
        raise PreviewContractError("rider.preferred_days must be an array")
    days = []
    for day in raw_days:
        if day not in DAY_KEYS:
            raise PreviewContractError(f"unsupported preferred day: {day}")
        if day not in days:
            days.append(day)
    days.sort(key=DAY_KEYS.index)
    if len(days) < 3:
        raise PreviewContractError("select at least three preferred days")

    preset_id = payload.get("preset_id")
    if preset_id is not None:
        preset_id = _text(preset_id, "preset_id", maximum=40)

    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "brand": brand,
        "race": {
            "slug": slug,
            "name": name,
            "discipline": discipline,
            "demands": demands,
        },
        "rider": {
            "hours_per_week": hours,
            "preferred_days": days,
            "experience_level": experience,
        },
        **({"preset_id": preset_id} if preset_id else {}),
    }


def _iso_date(value: Any, field: str) -> str:
    value = _text(value, field, maximum=40)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PreviewContractError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise PreviewContractError(f"{field} must be an ISO date")
    return value


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreviewContractError(f"{field} must be a number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise PreviewContractError(
            f"{field} must be between {minimum:g} and {maximum:g}")
    return round(result, 2)


def _normalize_request_v2(payload: Mapping[str, Any]) -> Dict[str, Any]:
    base_payload = dict(payload)
    base_payload["schema_version"] = REQUEST_SCHEMA_VERSION_V1
    base = _normalize_request_v1(base_payload)
    race = payload.get("race")
    rider = payload.get("rider")
    assert isinstance(race, Mapping) and isinstance(rider, Mapping)

    race_date = _iso_date(race.get("date"), "race.date")
    expected_duration = _number(
        race.get("expected_duration_hours"),
        "race.expected_duration_hours", 1, 30)
    raw_event_format = race.get("event_format")
    event_format = None
    if raw_event_format is not None:
        if base["race"]["discipline"] != "road":
            raise PreviewContractError(
                "race.event_format is only valid for road previews")
        event_format = _text(
            raw_event_format, "race.event_format", maximum=40)
        if event_format not in ROAD_EVENT_FORMATS:
            raise PreviewContractError(
                "race.event_format is not supported")
    plan_weeks = _integer(payload.get("plan_weeks"), "plan_weeks", 4, 26)
    sample_week_number = payload.get("sample_week_number")
    if sample_week_number is not None:
        sample_week_number = _integer(
            sample_week_number, "sample_week_number", 1, plan_weeks)

    goal_type = rider.get("goal_type")
    if goal_type not in GOAL_TYPES:
        raise PreviewContractError("rider.goal_type is not supported")
    control_method = rider.get("control_method")
    if control_method not in CONTROL_METHODS:
        raise PreviewContractError("rider.control_method is not supported")
    equipment = rider.get("strength_equipment")
    if equipment not in STRENGTH_EQUIPMENT:
        raise PreviewContractError("rider.strength_equipment is not supported")

    markers: Dict[str, int] = {}
    if control_method == "power":
        markers["ftp_watts"] = _integer(
            rider.get("ftp_watts"), "rider.ftp_watts", 50, 500)
    elif rider.get("ftp_watts") is not None:
        markers["ftp_watts"] = _integer(
            rider.get("ftp_watts"), "rider.ftp_watts", 50, 500)
    if control_method == "hr":
        markers["lthr_bpm"] = _integer(
            rider.get("lthr_bpm"), "rider.lthr_bpm", 80, 220)
        markers["max_hr_bpm"] = _integer(
            rider.get("max_hr_bpm"), "rider.max_hr_bpm", 100, 230)
        if markers["max_hr_bpm"] <= markers["lthr_bpm"]:
            raise PreviewContractError(
                "rider.max_hr_bpm must be greater than rider.lthr_bpm")
    else:
        for key, lower, upper in (
            ("lthr_bpm", 80, 220), ("max_hr_bpm", 100, 230)):
            if rider.get(key) is not None:
                markers[key] = _integer(
                    rider.get(key), f"rider.{key}", lower, upper)

    raw_caps = rider.get("day_caps_minutes", {})
    if not isinstance(raw_caps, Mapping):
        raise PreviewContractError("rider.day_caps_minutes must be an object")
    day_caps: Dict[str, int] = {}
    preferred = set(base["rider"]["preferred_days"])
    for raw_day, raw_minutes in raw_caps.items():
        if raw_day not in DAY_KEYS or raw_day not in preferred:
            raise PreviewContractError(
                "rider.day_caps_minutes keys must be preferred days")
        day_caps[raw_day] = _integer(
            raw_minutes, f"rider.day_caps_minutes.{raw_day}", 30, 600)

    return {
        **base,
        "schema_version": REQUEST_SCHEMA_VERSION_V2,
        "plan_weeks": plan_weeks,
        **({"sample_week_number": sample_week_number}
           if sample_week_number is not None else {}),
        "race": {
            **base["race"],
            "date": race_date,
            "expected_duration_hours": expected_duration,
            **({"event_format": event_format} if event_format else {}),
        },
        "rider": {
            **base["rider"],
            "goal_type": goal_type,
            "control_method": control_method,
            "strength_equipment": equipment,
            **markers,
            **({"day_caps_minutes": dict(sorted(
                day_caps.items(), key=lambda item: DAY_KEYS.index(item[0])))
               } if day_caps else {}),
        },
    }


def normalize_request(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and normalize either supported browser request version."""
    if not isinstance(payload, Mapping):
        raise PreviewContractError("body must be an object")
    schema = payload.get("schema_version")
    if schema == REQUEST_SCHEMA_VERSION_V1:
        return _normalize_request_v1(payload)
    if schema == REQUEST_SCHEMA_VERSION_V2:
        return _normalize_request_v2(payload)
    raise PreviewContractError(
        "schema_version must be a supported training-plan-preview request")


def request_cache_key(request_payload: Mapping[str, Any]) -> str:
    normalized = normalize_request(request_payload)
    wire = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def resolve_voice_version(repo_root: Path | None = None) -> str:
    """Version the checked-in athlete-facing voice without a stale manual bump."""
    configured = os.environ.get("COACHING_VOICE_VERSION", "").strip()
    if configured:
        if not _VERSION_RE.fullmatch(configured):
            raise PreviewContractError("COACHING_VOICE_VERSION is invalid")
        return configured

    root = repo_root or Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for relative in _VOICE_FILES:
        path = root / relative
        if not path.is_file():
            raise PreviewContractError(f"voice contract source missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"github-voice-{digest.hexdigest()[:12]}"


def _version(value: Any, field: str) -> str:
    value = _text(value, field, maximum=96)
    if not _VERSION_RE.fullmatch(value):
        raise PreviewContractError(f"{field} is invalid")
    return value


def _polyline(value: Any, field: str) -> List[List[float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PreviewContractError(f"{field} must be an array")
    points: List[List[float]] = []
    for index, point in enumerate(value):
        if (not isinstance(point, Sequence) or isinstance(point, (str, bytes))
                or len(point) != 2):
            raise PreviewContractError(f"{field}[{index}] must be [x, y]")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise PreviewContractError(f"{field}[{index}] must be numeric")
        if not 0 <= float(x) <= 1 or not 0 <= float(y) <= 2:
            raise PreviewContractError(f"{field}[{index}] is out of range")
        points.append([round(float(x), 5), round(float(y), 5)])
    if len(points) > 240:
        raise PreviewContractError(f"{field} has too many points")
    return points


def _step(step: Mapping[str, Any], field: str) -> Dict[str, Any]:
    if not isinstance(step, Mapping):
        raise PreviewContractError(f"{field} must be an object")
    kind = _text(step.get("type"), f"{field}.type", maximum=30)
    seconds = _integer(step.get("length_seconds"), f"{field}.length_seconds", 1, 86400)
    result: Dict[str, Any] = {"type": kind, "length_seconds": seconds}
    label = step.get("label")
    if label is not None:
        result["label"] = _text(
            label, f"{field}.label", maximum=80, required=False)
    for key in ("intensity_target_min", "intensity_target_max"):
        value = step.get(key)
        if value is not None:
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 2:
                raise PreviewContractError(f"{field}.{key} is out of range")
            result[key] = round(float(value), 4)
    cadence = step.get("cadence_rpm")
    if cadence is not None:
        result["cadence_rpm"] = _integer(cadence, f"{field}.cadence_rpm", 30, 200)
    return result


def _strength_exercise(exercise: Mapping[str, Any], field: str) -> Dict[str, Any]:
    if not isinstance(exercise, Mapping):
        raise PreviewContractError(f"{field} must be an object")
    result: Dict[str, Any] = {
        "name": _text(exercise.get("name"), f"{field}.name", maximum=80),
        "sets": _integer(exercise.get("sets"), f"{field}.sets", 1, 12),
        "reps": _text(exercise.get("reps"), f"{field}.reps", maximum=24),
        "cue": _text(
            exercise.get("cue"), f"{field}.cue", maximum=180),
    }
    rest_seconds = exercise.get("rest_seconds")
    if rest_seconds is not None:
        result["rest_seconds"] = _integer(
            rest_seconds, f"{field}.rest_seconds", 0, 600)
    return result


def _session(session: Mapping[str, Any], field: str) -> Dict[str, Any]:
    if not isinstance(session, Mapping):
        raise PreviewContractError(f"{field} must be an object")
    kind = session.get("kind")
    if kind not in SESSION_KINDS:
        raise PreviewContractError(f"{field}.kind is not supported")
    result: Dict[str, Any] = {
        "kind": kind,
        "title": _text(session.get("title"), f"{field}.title", maximum=120),
        "purpose": _text(
            session.get("purpose", ""), f"{field}.purpose", maximum=260,
            required=kind not in {"rest", "note"}),
        "duration_minutes": _integer(
            session.get("duration_minutes", 0), f"{field}.duration_minutes", 0, 1440),
        "tss": _integer(session.get("tss", 0), f"{field}.tss", 0, 1000),
        "intensity_label": _text(
            session.get("intensity_label", ""), f"{field}.intensity_label",
            maximum=40, required=False),
        "fuel_tag": session.get("fuel_tag", "none"),
        "fueling_guidance": _text(
            session.get("fueling_guidance", ""), f"{field}.fueling_guidance",
            maximum=240, required=False),
        "coach_note": _text(
            session.get("coach_note", ""), f"{field}.coach_note",
            maximum=420, required=kind not in {"rest", "note"}),
    }
    if result["fuel_tag"] not in FUEL_TAGS:
        raise PreviewContractError(f"{field}.fuel_tag is not supported")

    structure = session.get("structure")
    if structure is not None:
        if not isinstance(structure, Mapping):
            raise PreviewContractError(f"{field}.structure must be an object")
        raw_steps = structure.get("steps", [])
        if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
            raise PreviewContractError(f"{field}.structure.steps must be an array")
        if len(raw_steps) > 80:
            raise PreviewContractError(f"{field}.structure has too many steps")
        result["structure"] = {
            "primary_length_metric": _text(
                structure.get("primary_length_metric", "duration"),
                f"{field}.structure.primary_length_metric", maximum=30),
            "primary_intensity_metric": _text(
                structure.get("primary_intensity_metric", "percentOfFtp"),
                f"{field}.structure.primary_intensity_metric", maximum=30),
            "polyline": _polyline(
                structure.get("polyline", []), f"{field}.structure.polyline"),
            "steps": [
                _step(item, f"{field}.structure.steps[{index}]")
                for index, item in enumerate(raw_steps)
            ],
        }
    strength = session.get("strength")
    if kind == "strength":
        if not isinstance(strength, Mapping):
            raise PreviewContractError(f"{field}.strength must be an object")
        raw_exercises = strength.get("exercises")
        if (not isinstance(raw_exercises, Sequence)
                or isinstance(raw_exercises, (str, bytes))):
            raise PreviewContractError(
                f"{field}.strength.exercises must be an array")
        if not 3 <= len(raw_exercises) <= 12:
            raise PreviewContractError(
                f"{field}.strength.exercises must contain 3–12 exercises")
        result["strength"] = {
            "focus": _text(
                strength.get("focus"), f"{field}.strength.focus", maximum=120),
            "exercises": [
                _strength_exercise(
                    item, f"{field}.strength.exercises[{index}]")
                for index, item in enumerate(raw_exercises)
            ],
        }
    elif strength is not None:
        raise PreviewContractError(
            f"{field}.strength is only valid for strength sessions")
    return result


def _validate_preview_quality(
        request_data: Mapping[str, Any], week: Mapping[str, Any],
        days: Sequence[Mapping[str, Any]]) -> None:
    """Reject thin marketplace teasers before they reach a consumer site."""
    active = []
    discipline_sessions = []
    used_days = set()
    preferred_days = set(request_data["rider"]["preferred_days"])
    for day in days:
        for session in day["sessions"]:
            if session["kind"] in {"rest", "note"}:
                continue
            active.append(session)
            used_days.add(day["day"])
            if session["kind"] in {"bike", "ski", "race"}:
                discipline_sessions.append(session)

    strength_sessions = [
        session for session in active if session["kind"] == "strength"]
    if not strength_sessions:
        raise PreviewContractError(
            "preview week must contain a complete strength session")
    if len(active) < 3:
        raise PreviewContractError(
            "preview week must contain at least three active sessions")
    if len(discipline_sessions) < 2:
        raise PreviewContractError(
            "preview week must contain at least two discipline sessions")
    if not used_days.issubset(preferred_days):
        raise PreviewContractError(
            "preview sessions must stay on the rider's preferred days")
    if len(used_days) < min(3, len(preferred_days)):
        raise PreviewContractError(
            "preview week must use at least three preferred days")

    titles = [session["title"].casefold() for session in active]
    if len(titles) != len(set(titles)):
        raise PreviewContractError("preview workout titles must be distinct")
    for session in discipline_sessions:
        structure = session.get("structure")
        if not structure or not structure["steps"] or not structure["polyline"]:
            raise PreviewContractError(
                "each discipline workout needs structured steps and a polyline")
        if not session["fueling_guidance"]:
            raise PreviewContractError(
                "each discipline workout needs fueling guidance")

    total_minutes = sum(session["duration_minutes"] for session in active)
    target_minutes = _integer(
        week.get("target_minutes"), "source.week.target_minutes", 0, 10800)
    if abs(total_minutes - target_minutes) > 15:
        raise PreviewContractError(
            "preview target minutes must match its scheduled sessions")
    available_minutes = request_data["rider"]["hours_per_week"] * 60
    if not int(available_minutes * 0.6) <= target_minutes <= available_minutes + 15:
        raise PreviewContractError(
            "preview duration must credibly use the rider's available hours")


def _project_response_v1(
        request_payload: Mapping[str, Any], source: Mapping[str, Any], *,
        engine_version: str, voice_version: str | None = None) -> Dict[str, Any]:
    """Allowlist a finalized canonical week into the public response.

    ``source`` is intentionally small and engine-agnostic: ``week`` contains
    seven day objects in calendar order, and each day contains zero or more
    canonical sessions.  Private fields on ``source`` are ignored, never
    serialized.  The adapter for the finalized Claude interface is therefore
    the only code that needs to understand engine internals.
    """
    request_data = normalize_request(request_payload)
    if not isinstance(source, Mapping):
        raise PreviewContractError("source must be an object")
    week = source.get("week")
    if not isinstance(week, Mapping):
        raise PreviewContractError("source.week must be an object")
    raw_days = week.get("days")
    if not isinstance(raw_days, Sequence) or isinstance(raw_days, (str, bytes)):
        raise PreviewContractError("source.week.days must be an array")
    if len(raw_days) != 7:
        raise PreviewContractError("source.week.days must contain seven days")

    days: List[Dict[str, Any]] = []
    for index, day in enumerate(raw_days):
        field = f"source.week.days[{index}]"
        if not isinstance(day, Mapping):
            raise PreviewContractError(f"{field} must be an object")
        if day.get("day") != DAY_KEYS[index]:
            raise PreviewContractError(f"{field}.day must be {DAY_KEYS[index]}")
        sessions = day.get("sessions", [])
        if not isinstance(sessions, Sequence) or isinstance(sessions, (str, bytes)):
            raise PreviewContractError(f"{field}.sessions must be an array")
        if len(sessions) > 3:
            raise PreviewContractError(f"{field}.sessions has too many entries")
        days.append({
            "day": DAY_KEYS[index],
            "sessions": [
                _session(item, f"{field}.sessions[{session_index}]")
                for session_index, item in enumerate(sessions)
            ],
        })

    _validate_preview_quality(request_data, week, days)

    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "engine_version": _version(engine_version, "engine_version"),
        "voice_version": _version(
            voice_version or resolve_voice_version(), "voice_version"),
        "preview_id": request_cache_key(request_data)[:20],
        "cache_ttl_seconds": 900,
        "race": request_data["race"],
        "rider": request_data["rider"],
        "week": {
            "phase": _text(week.get("phase"), "source.week.phase", maximum=30),
            "type": _text(week.get("type"), "source.week.type", maximum=30),
            "target_minutes": _integer(
                week.get("target_minutes"), "source.week.target_minutes", 0, 10800),
            "target_tss": _integer(
                week.get("target_tss"), "source.week.target_tss", 0, 5000),
            "coach_note": _text(
                week.get("coach_note"), "source.week.coach_note", maximum=700),
            "weekly_self_review": _text(
                week.get("weekly_self_review"), "source.week.weekly_self_review",
                maximum=700),
            "comment_protocol": _text(
                week.get("comment_protocol"), "source.week.comment_protocol",
                maximum=700),
            "days": days,
        },
    }
    # Defense in depth: the final serialized response must not contain common
    # internal identifiers, even if an allowlisted field was populated badly.
    wire = json.dumps(response, sort_keys=True)
    if _INTERNAL_TEXT_RE.search(wire):
        raise PreviewContractError("public response contains an internal token")
    return response


def _v2_source_session(
        session: Mapping[str, Any], field: str) -> Dict[str, Any]:
    """Project a session only when Motoren proves its public provenance."""
    if not isinstance(session, Mapping):
        raise PreviewContractError(f"{field} must be an object")
    kind = session.get("kind")
    if kind in {"bike", "ski", "strength"}:
        if session.get("_library_backed") is not True:
            raise PreviewContractError(
                f"{field} must be backed by the coach workout library")
    elif kind == "race":
        if session.get("_engine_overlay") is not True:
            raise PreviewContractError(
                f"{field} must be an engine-generated race overlay")
        if session.get("structure") is not None:
            raise PreviewContractError(
                f"{field} race sessions cannot contain synthetic structure")
    return _session(session, field)


def _v2_days(
        raw_days: Any, field: str) -> List[Dict[str, Any]]:
    if not isinstance(raw_days, Sequence) or isinstance(raw_days, (str, bytes)):
        raise PreviewContractError(f"{field} must be an array")
    if len(raw_days) != 7:
        raise PreviewContractError(f"{field} must contain seven days")
    result: List[Dict[str, Any]] = []
    previous_date: date | None = None
    for index, raw_day in enumerate(raw_days):
        day_field = f"{field}[{index}]"
        if not isinstance(raw_day, Mapping):
            raise PreviewContractError(f"{day_field} must be an object")
        if raw_day.get("day") != DAY_KEYS[index]:
            raise PreviewContractError(
                f"{day_field}.day must be {DAY_KEYS[index]}")
        day_date = _iso_date(raw_day.get("date"), f"{day_field}.date")
        parsed_date = date.fromisoformat(day_date)
        if previous_date is not None and (parsed_date - previous_date).days != 1:
            raise PreviewContractError(f"{field} dates must be consecutive")
        previous_date = parsed_date
        sessions = raw_day.get("sessions", [])
        if not isinstance(sessions, Sequence) or isinstance(sessions, (str, bytes)):
            raise PreviewContractError(f"{day_field}.sessions must be an array")
        if len(sessions) > 3:
            raise PreviewContractError(f"{day_field}.sessions has too many entries")
        result.append({
            "day": DAY_KEYS[index],
            "date": day_date,
            "sessions": [
                _v2_source_session(item, f"{day_field}.sessions[{session_index}]")
                for session_index, item in enumerate(sessions)
            ],
        })
    return result


def _v2_volume_item(item: Mapping[str, Any], field: str) -> Dict[str, Any]:
    if not isinstance(item, Mapping):
        raise PreviewContractError(f"{field} must be an object")
    start_date = _iso_date(item.get("start_date"), f"{field}.start_date")
    end_date = _iso_date(item.get("end_date"), f"{field}.end_date")
    if (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days != 6:
        raise PreviewContractError(f"{field} must span seven days")
    return {
        "week_number": _integer(
            item.get("week_number"), f"{field}.week_number", 1, 26),
        "phase": _text(item.get("phase"), f"{field}.phase", maximum=30),
        "type": _text(item.get("type"), f"{field}.type", maximum=30),
        "start_date": start_date,
        "end_date": end_date,
        "target_minutes": _integer(
            item.get("target_minutes"), f"{field}.target_minutes", 0, 18000),
        "target_tss": _integer(
            item.get("target_tss"), f"{field}.target_tss", 0, 10000),
        "session_count": _integer(
            item.get("session_count"), f"{field}.session_count", 1, 30),
        "longest_session_minutes": _integer(
            item.get("longest_session_minutes"),
            f"{field}.longest_session_minutes", 0, 1800),
    }


def _validate_v2_week_quality(
        request_data: Mapping[str, Any], week: Mapping[str, Any],
        days: Sequence[Mapping[str, Any]]) -> None:
    active = [
        (day, session) for day in days for session in day["sessions"]
        if session["kind"] not in {"rest", "note"}
    ]
    if not active:
        raise PreviewContractError("sample week must contain active sessions")
    total_minutes = sum(session["duration_minutes"] for _, session in active)
    total_tss = sum(session["tss"] for _, session in active)
    if total_minutes != week["target_minutes"] or total_tss != week["target_tss"]:
        raise PreviewContractError(
            "sample week totals must exactly match its scheduled sessions")
    if week["type"] != "race":
        strength = [session for _, session in active if session["kind"] == "strength"]
        discipline = [
            session for _, session in active if session["kind"] in {"bike", "ski"}
        ]
        if not strength:
            raise PreviewContractError(
                "non-race sample weeks need a complete strength session")
        if len(discipline) < 2:
            raise PreviewContractError(
                "non-race sample weeks need at least two discipline sessions")
        used_days = {day["day"] for day, _ in active}
        if not used_days.issubset(set(request_data["rider"]["preferred_days"])):
            raise PreviewContractError(
                "sample sessions must stay on the rider's preferred days")
    for _, session in active:
        if session["kind"] in {"bike", "ski"}:
            structure = session.get("structure")
            if not structure or not structure["steps"] or not structure["polyline"]:
                raise PreviewContractError(
                    "each discipline workout needs real structured steps")
        if session["kind"] in {"bike", "ski", "race"} and not session["fueling_guidance"]:
            raise PreviewContractError(
                "each endurance session needs fueling guidance")
    titles = [session["title"].casefold() for _, session in active]
    if len(titles) != len(set(titles)):
        raise PreviewContractError("sample workout titles must be distinct")


def _project_response_v2(
        request_payload: Mapping[str, Any], source: Mapping[str, Any], *,
        engine_version: str, voice_version: str | None = None) -> Dict[str, Any]:
    request_data = normalize_request(request_payload)
    if request_data["schema_version"] != REQUEST_SCHEMA_VERSION_V2:
        raise PreviewContractError("v2 projection requires a v2 request")
    if not isinstance(source, Mapping):
        raise PreviewContractError("source must be an object")
    raw_plan = source.get("plan")
    if not isinstance(raw_plan, Mapping):
        raise PreviewContractError("source.plan must be an object")
    total_weeks = _integer(raw_plan.get("total_weeks"), "source.plan.total_weeks", 4, 26)
    if total_weeks != request_data["plan_weeks"]:
        raise PreviewContractError("source plan length must match the request")
    race_date = _iso_date(raw_plan.get("race_date"), "source.plan.race_date")
    if race_date != request_data["race"]["date"]:
        raise PreviewContractError("source race date must match the request")
    profile_version = None
    if raw_plan.get("profile_version") is not None:
        profile_version = _version(
            raw_plan.get("profile_version"), "source.plan.profile_version")
    if request_data["race"].get("event_format"):
        if profile_version != ROAD_PROFILE_VERSION:
            raise PreviewContractError(
                "road preview source profile version is not supported")
    raw_sample_numbers = raw_plan.get("sample_week_numbers")
    if (not isinstance(raw_sample_numbers, Sequence)
            or isinstance(raw_sample_numbers, (str, bytes))):
        raise PreviewContractError("source.plan.sample_week_numbers must be an array")
    sample_numbers = [
        _integer(number, f"source.plan.sample_week_numbers[{index}]", 1, total_weeks)
        for index, number in enumerate(raw_sample_numbers)
    ]
    if not 2 <= len(sample_numbers) <= 4 or len(sample_numbers) != len(set(sample_numbers)):
        raise PreviewContractError("source plan must identify 2–4 distinct sample weeks")

    raw_volume = source.get("planned_volume")
    if not isinstance(raw_volume, Sequence) or isinstance(raw_volume, (str, bytes)):
        raise PreviewContractError("source.planned_volume must be an array")
    if len(raw_volume) != total_weeks:
        raise PreviewContractError("source.planned_volume must cover the full plan")
    volume = [
        _v2_volume_item(item, f"source.planned_volume[{index}]")
        for index, item in enumerate(raw_volume)
    ]
    if [item["week_number"] for item in volume] != list(range(1, total_weeks + 1)):
        raise PreviewContractError("planned volume week numbers must be sequential")
    for previous, current in zip(volume, volume[1:]):
        if (date.fromisoformat(current["start_date"])
                - date.fromisoformat(previous["start_date"])).days != 7:
            raise PreviewContractError("planned volume dates must be consecutive")

    raw_samples = source.get("sample_weeks")
    if not isinstance(raw_samples, Sequence) or isinstance(raw_samples, (str, bytes)):
        raise PreviewContractError("source.sample_weeks must be an array")
    if len(raw_samples) != len(sample_numbers):
        raise PreviewContractError("source.sample_weeks must match selected samples")
    by_number = {item["week_number"]: item for item in volume}
    samples: List[Dict[str, Any]] = []
    for index, raw_week in enumerate(raw_samples):
        field = f"source.sample_weeks[{index}]"
        if not isinstance(raw_week, Mapping):
            raise PreviewContractError(f"{field} must be an object")
        number = _integer(raw_week.get("week_number"), f"{field}.week_number", 1, total_weeks)
        if number != sample_numbers[index]:
            raise PreviewContractError("sample week order must match the plan")
        days = _v2_days(raw_week.get("days"), f"{field}.days")
        week = {
            "week_number": number,
            "phase": _text(raw_week.get("phase"), f"{field}.phase", maximum=30),
            "type": _text(raw_week.get("type"), f"{field}.type", maximum=30),
            "start_date": _iso_date(raw_week.get("start_date"), f"{field}.start_date"),
            "end_date": _iso_date(raw_week.get("end_date"), f"{field}.end_date"),
            "target_minutes": _integer(raw_week.get("target_minutes"), f"{field}.target_minutes", 0, 18000),
            "target_tss": _integer(raw_week.get("target_tss"), f"{field}.target_tss", 0, 10000),
            "coach_note": _text(raw_week.get("coach_note"), f"{field}.coach_note", maximum=700),
            "weekly_self_review": _text(raw_week.get("weekly_self_review"), f"{field}.weekly_self_review", maximum=1000),
            "comment_protocol": _text(raw_week.get("comment_protocol"), f"{field}.comment_protocol", maximum=1000),
            "days": days,
        }
        summary = by_number[number]
        for key in ("phase", "type", "start_date", "end_date", "target_minutes", "target_tss"):
            if week[key] != summary[key]:
                raise PreviewContractError(
                    f"sample week {number} must exactly match planned volume")
        if days[0]["date"] != week["start_date"] or days[-1]["date"] != week["end_date"]:
            raise PreviewContractError("sample week dates must match its day dates")
        _validate_v2_week_quality(request_data, week, days)
        samples.append(week)

    race_summary = next((item for item in volume if item["type"] == "race"), None)
    race_sample = next((item for item in samples if item["type"] == "race"), None)
    if race_summary is None or race_sample is None:
        raise PreviewContractError("full-plan preview must include its race week")
    race_sessions = [
        session for day in race_sample["days"] for session in day["sessions"]
        if session["kind"] == "race"
    ]
    if len(race_sessions) != 1:
        raise PreviewContractError("race week must contain exactly one race session")
    race_session = race_sessions[0]
    if (race_session["duration_minutes"] <= 0
            or race_summary["target_minutes"] < race_session["duration_minutes"]
            or race_summary["target_tss"] < race_session["tss"]):
        raise PreviewContractError("race workload must be present in the volume curve")

    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION_V2,
        "engine_version": _version(engine_version, "engine_version"),
        "voice_version": _version(
            voice_version or resolve_voice_version(), "voice_version"),
        "preview_id": request_cache_key(request_data)[:20],
        "cache_ttl_seconds": 900,
        "race": request_data["race"],
        "rider": request_data["rider"],
        "plan": {
            "total_weeks": total_weeks,
            "race_date": race_date,
            "sample_week_numbers": sample_numbers,
            **({"profile_version": profile_version}
               if profile_version else {}),
        },
        "planned_volume": volume,
        "sample_weeks": samples,
    }
    wire = json.dumps(response, sort_keys=True)
    if _INTERNAL_TEXT_RE.search(wire):
        raise PreviewContractError("public response contains an internal token")
    return response


def project_response(
        request_payload: Mapping[str, Any], source: Mapping[str, Any], *,
        engine_version: str, voice_version: str | None = None) -> Dict[str, Any]:
    """Project v1 or v2 Motoren source through a strict public allowlist."""
    schema = request_payload.get("schema_version") if isinstance(request_payload, Mapping) else None
    if schema == REQUEST_SCHEMA_VERSION_V2:
        return _project_response_v2(
            request_payload, source, engine_version=engine_version,
            voice_version=voice_version)
    return _project_response_v1(
        request_payload, source, engine_version=engine_version,
        voice_version=voice_version)
