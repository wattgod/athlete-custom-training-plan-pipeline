"""Vendored copy of webhook/preview_contract.py for integration testing.

PROVENANCE: fetched via
    git show origin/codex/public-plan-preview-20260825:webhook/preview_contract.py
at commit ec84cdb30d181bea7fe28fca156c7aad70fae9d3 (branch
codex/public-plan-preview-20260825, forked from e785ccb). Byte-identical to
that revision. Not maintained here -- re-vendor from that branch if the
consumer contract changes; this copy exists only so
test_motoren_preview.py can exercise motoren_preview.generate_preview_source
against the REAL allowlist projection + fail-closed quality gate without a
cross-branch git dependency at test time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


REQUEST_SCHEMA_VERSION = "training-plan-preview-request/v1"
RESPONSE_SCHEMA_VERSION = "training-plan-preview/v1"

BRANDS = {"gravel_god", "roadie_labs", "xc_ski_labs"}
EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced"}
DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SESSION_KINDS = {"bike", "ski", "strength", "race", "rest", "note"}
FUEL_TAGS = {"high", "moderate", "practice", "none"}

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+:-]{0,95}$")
_INTERNAL_TEXT_RE = re.compile(
    r"(?:library_item_id|source_file|compliance|internal[_ -]?only|"
    r"engine_shared_secret|railway_git_commit_sha)",
    re.IGNORECASE,
)

_VOICE_FILES = (
    "athletes/scripts/story_notes.py",
    "athletes/scripts/delivery_notes.py",
    "athletes/scripts/apply_contract.py",
    "athletes/scripts/test_voice_contract.py",
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


def normalize_request(payload: Mapping[str, Any]) -> Dict[str, Any]:
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


def project_response(
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
