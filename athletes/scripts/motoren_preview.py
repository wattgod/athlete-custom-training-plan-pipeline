#!/usr/bin/env python3
"""Motoren's canonical in-memory public-preview interface.

This is the ``generate_preview_source`` provider the marketing sites'
public-plan-preview boundary calls (see ``docs/PUBLIC_PLAN_PREVIEW_CONTRACT.md``
on ``codex/public-plan-preview-20260825`` -- ``webhook/preview_contract.py``'s
``project_response`` is the allowlist projection that consumes this module's
output; ``webhook/preview_service.py``'s ``build_public_preview`` is the
``provider`` boundary this function fills).

WHY THIS EXISTS: the public sites must never call the real block-builder
engine directly, carry an engine secret, or receive raw PlanIR/library data.
This module runs the REAL in-memory engine -- archetype selection, the
calendar-driven block builder, the real Nate ZWO renderer, the real
canonical/TP structure projector, real fueling policy, and the real
story-notes voice pipeline -- for a synthetic athlete built from the public
request, then hands back a small, engine-agnostic ``source`` dict (matching
``preview_contract.project_response``'s allowlist input) that never leaks
library ids, file paths, or PlanIR internals. No TrainingPeaks access, no
network, no disk writes.

Determinism: the synthetic athlete, the representative week's calendar dates,
and the race date are all derived from a fixed reference epoch and a digest
of the normalized request -- never from wall-clock time -- so the same
request always produces byte-identical output (until ``engine_version`` or
``voice_version`` changes).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Flat layout -- all pipeline modules live in athletes/scripts/ (see
# workout_mapper.py's identical sys.path guard). This module can be imported
# from a different cwd (tests, a future webhook adapter), so make the
# sibling modules importable regardless of caller cwd.
_SCRIPT_DIR = str(Path(__file__).parent.resolve())
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from archetype import determine_archetype, derive_discipline, get_training_age_constraints
from block_builder import build_calendar_week, DAY_ORDER
from block_chain import build_plan_from_calendar, derive_week_descriptors
from calculate_plan_dates import calculate_plan_dates
from race_category_scorer import calculate_category_scores
from road_racing import (
    ROAD_PROFILE_VERSION, normalize_event_format, resolve_event_format,
)
from workout_mapper import render_workout
from zwo_parser import parse_zwo_structure_text
from canonical_training_model import determine_control, _canonical_segment, project_tp_structure
from fueling_policy import build_fueling_prescription, render_workout_fueling
from generate_athlete_package import classify_fuel_tier, _get_fuel_tag_for_type, place_strength_days
from generate_athlete_package import race_day_tss_from_emitted_minutes
from workout_library import WorkoutLibrary
from story_notes import (
    render_story_notes, render_preview_workout_copy,
    render_preview_strength_copy, render_preview_race_copy,
    SELF_REVIEW_BODY, COMMENT_PROTOCOL_BODY,
)


class MotorenPreviewError(Exception):
    """Raised for any failure building a public plan preview.

    A single exception class, always a safe/generic message -- never the
    underlying exception's raw text (which can carry file paths or internal
    names). The original exception is chained via ``from`` for local
    debugging; callers must not surface it to the browser.
    """


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VOICE_SOURCE_FILES = (
    "athletes/config/voice_rules.yaml",
    "athletes/scripts/story_notes.py",
    "athletes/scripts/delivery_notes.py",
    "athletes/scripts/apply_contract.py",
    "athletes/scripts/voice_lint.py",
)


def _git_short_sha() -> str:
    # Railway's production image intentionally has no .git directory. Its
    # deployment metadata is the authoritative revision in that environment.
    configured = (
        os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GIT_SHA")
        or ""
    ).strip().lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", configured):
        return configured[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT), capture_output=True, text=True,
            check=True, timeout=10,
        )
        sha = result.stdout.strip()
        if sha and re.fullmatch(r"[0-9a-f]{4,40}", sha):
            return sha
    except Exception:
        pass
    return "unknown"


def _voice_digest() -> str:
    digest = hashlib.sha256()
    try:
        for relative in _VOICE_SOURCE_FILES:
            path = _REPO_ROOT / relative
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return "unknown"
    return digest.hexdigest()[:12]


# Computed once, at import time, per spec.
ENGINE_VERSION = f"motoren/{_git_short_sha()}+ae-2026-08-23"
VOICE_VERSION = f"voice/{_voice_digest()}"


def engine_version() -> str:
    return ENGINE_VERSION


def voice_version() -> str:
    return VOICE_VERSION


# ---------------------------------------------------------------------------
# Deterministic synthetic athlete
# ---------------------------------------------------------------------------

# A fixed Monday -- never wall-clock. Used both as the representative week's
# calendar (so story_notes can compute weekdays / the self-review date) and
# as the base for the synthetic race date.
_REFERENCE_MONDAY = date(2026, 1, 5)

# A representative BUILD load week -- not "week 1 of 1" (render_story_notes
# derives its own "of N" from the weeks actually passed in, so a
# single-week synthetic PlanIR reads as "Week 6 of 6"; that keeps the
# generic phase-line path (see _position_line) instead of the week-0/
# pre-plan special case a degenerate week=1/total=1 would trigger).
_WEEK_NUMBER = 6

_EXPERIENCE_TO_YEARS_STRUCTURED = {"beginner": 0, "intermediate": 2, "advanced": 3}
_EXPERIENCE_TO_BASE_LEVEL = {"beginner": 1, "intermediate": 2, "advanced": 3}
_EXPERIENCE_TO_FTP_BASE = {"beginner": 160, "intermediate": 215, "advanced": 270}
_EXPERIENCE_TO_GOAL_TYPE = {"beginner": "finish", "intermediate": "compete", "advanced": "podium"}

# The request carries no race duration; a mid-length gravel/road race is a
# reasonable, honest default for the fueling model (build_fueling_prescription
# needs *a* duration -- there is no per-race duration anywhere in the request
# to draw a real one from). Flagged in the module's own docstring/report, not
# silently presented as request-derived.
_ASSUMED_RACE_DURATION_HOURS = 6.0


def _request_digest(normalized_request: Mapping[str, Any]) -> int:
    wire = json.dumps(normalized_request, sort_keys=True, separators=(",", ":"))
    return int(hashlib.sha256(wire.encode("utf-8")).hexdigest()[:8], 16)


def _synthetic_race_date() -> date:
    """~12 weeks from the fixed reference Monday, landed on a Saturday."""
    target = _REFERENCE_MONDAY + timedelta(weeks=12)
    target += timedelta(days=(5 - target.weekday()) % 7)
    return target


def _synthetic_athlete(request: Mapping[str, Any], seed: int) -> Dict[str, Any]:
    experience = request["rider"]["experience_level"]
    years_structured = _EXPERIENCE_TO_YEARS_STRUCTURED.get(experience, 0)
    ftp_base = _EXPERIENCE_TO_FTP_BASE.get(experience, 200)
    ftp_watts = ftp_base + (seed % 41) - 20
    weight_kg = 70 + (seed % 21) - 10
    return {
        "training_history": {"years_structured": years_structured},
        "fitness_markers": {
            "ftp_watts": ftp_watts, "weight_kg": weight_kg,
            "power_basis": "measured", "requested_metric": "power",
        },
        "target_race": {
            "name": request["race"]["name"],
            "date": _synthetic_race_date().isoformat(),
            "goal_type": _EXPERIENCE_TO_GOAL_TYPE.get(experience, "finish"),
        },
        "discipline": request["race"]["discipline"],
    }


def _resolve_discipline(request: Mapping[str, Any]) -> str:
    raw = str(request["race"].get("discipline") or "").strip().lower()
    profile = {
        "discipline": raw if raw in ("gravel", "road", "mtb") else None,
        "target_race": {"name": request["race"]["name"]},
    }
    return derive_discipline(profile)


def _resolve_road_event_format(
    request: Mapping[str, Any], discipline: str,
) -> Optional[str]:
    """Resolve the canonical road profile without guessing across sports."""
    race = request["race"]
    explicit = race.get("event_format")
    if discipline != "road":
        if explicit is not None:
            raise MotorenPreviewError(
                "road event format cannot be applied to this discipline")
        return None
    if explicit is not None and normalize_event_format(explicit) is None:
        raise MotorenPreviewError("road event format is not supported")
    resolution = resolve_event_format({
        "target_race": {
            "name": race["name"],
            **({"event_format": explicit} if explicit is not None else {}),
        },
    })
    return str(resolution["event_format"])


# ---------------------------------------------------------------------------
# Day-budget allocation (keeps the emitted week's total minutes inside the
# public quality gate's tolerance -- the real engine's load-week budget
# formula (hours x 1.10, floor-grown besides) deliberately overshoots stated
# hours; the preview must not).
# ---------------------------------------------------------------------------

def _capitalized_days(day_keys: List[str]) -> List[str]:
    return [d.capitalize() for d in day_keys]


def _pick_long_ride_day(preferred_caps: List[str]) -> str:
    for candidate in ("Sat", "Sun", "Fri", "Thu", "Wed", "Tue", "Mon"):
        if candidate in preferred_caps:
            return candidate
    return preferred_caps[0]


def _allocate_day_caps(preferred_caps: List[str], long_ride_day: str,
                       bike_budget_minutes: int) -> Dict[str, int]:
    bike_budget_minutes = max(60, int(bike_budget_minutes))
    if len(preferred_caps) == 1:
        return {preferred_caps[0]: bike_budget_minutes}
    long_ride_cap = max(30, round(bike_budget_minutes * 0.4))
    long_ride_cap = min(long_ride_cap, bike_budget_minutes - 30)
    other_days = [d for d in preferred_caps if d != long_ride_day]
    remaining = bike_budget_minutes - long_ride_cap
    per_other = max(20, remaining // len(other_days))
    caps = {long_ride_day: long_ride_cap}
    used = 0
    for i, day in enumerate(other_days):
        cap = per_other
        if i == len(other_days) - 1:
            cap = max(20, remaining - used)
        caps[day] = cap
        used += cap
    return caps


# ---------------------------------------------------------------------------
# Purpose text -- reuses generate_athlete_package.WORKOUT_DESCRIPTIONS (real,
# shipped athlete-facing copy) via keyword routing. No purpose-text generator
# exists elsewhere in the pipeline for the block-builder's own workout names,
# so this routing table is new; the copy itself is not.
# ---------------------------------------------------------------------------

def _purpose_key(name: str) -> str:
    low = name.lower()
    if "ftp test" in low:
        return "FTP_Test"
    if "opener" in low:
        return "Openers"
    if "vo2" in low or "thirty-fifteen" in low or "ronnestad" in low:
        return "VO2max"
    if "threshold" in low:
        return "Threshold"
    if "g-spot" in low or "g spot" in low or "sweet spot" in low:
        return "G_Spot"
    if "over-under" in low or "over under" in low:
        return "Over_Under"
    if "blended" in low or "mixed" in low or "kitchen sink" in low or "sfr" in low:
        return "Blended"
    if "tempo" in low:
        return "Tempo"
    if "sprint" in low:
        return "Sprints"
    if "anaerobic" in low:
        return "Anaerobic"
    if "cadence" in low:
        return "Tempo"
    return "Endurance"


_INTENSITY_LABELS = {
    "FTP_Test": "FTP Test", "Openers": "Openers", "VO2max": "VO2max",
    "Threshold": "Threshold", "G_Spot": "Sweet Spot", "Over_Under": "Over-Under",
    "Blended": "Blended", "Tempo": "Tempo", "Sprints": "Sprints",
    "Anaerobic": "Anaerobic", "Long_Ride": "Endurance", "Endurance": "Endurance",
}


def _intensity_label(name: str, role: str) -> str:
    key = "Long_Ride" if role == "long_ride" and _purpose_key(name) == "Endurance" else _purpose_key(name)
    return _INTENSITY_LABELS.get(key, "Endurance")


# ---------------------------------------------------------------------------
# Structure sanitization: TP-native project_tp_structure() output -> the
# allowlisted {primary_length_metric, primary_intensity_metric, polyline,
# steps:[{type,length_seconds,label,intensity_target_min,intensity_target_max,
# cadence_rpm}]} shape preview_contract.project_response's _step()/_session()
# actually read.
# ---------------------------------------------------------------------------

_INTENSITY_CLASS_TO_TYPE = {
    "warmUp": "warmup", "coolDown": "cooldown", "active": "interval", "rest": "recovery",
}
_CADENCE_UNIT = "roundOrStridePerMinute"


def _sanitize_step(block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    leaf = (block.get("steps") or [{}])[0]
    seconds = int((leaf.get("length") or {}).get("value") or 0)
    if seconds < 1:
        return None
    intensity_class = str(leaf.get("intensityClass") or "active")
    step: Dict[str, Any] = {
        "type": _INTENSITY_CLASS_TO_TYPE.get(intensity_class, "interval"),
        "length_seconds": seconds,
    }
    label = str(leaf.get("name") or "").strip()
    if label:
        step["label"] = label[:80]
    targets = leaf.get("targets") or []
    primary = targets[0] if targets else {}
    if primary.get("minValue") is not None:
        step["intensity_target_min"] = round(
            max(0.0, min(2.0, float(primary["minValue"]) / 100.0)), 4)
    if primary.get("maxValue") is not None:
        step["intensity_target_max"] = round(
            max(0.0, min(2.0, float(primary["maxValue"]) / 100.0)), 4)
    for extra in targets[1:]:
        if extra.get("unit") == _CADENCE_UNIT:
            if extra.get("maxValue") is not None and extra.get("minValue") is not None:
                cadence = round((float(extra["minValue"]) + float(extra["maxValue"])) / 2)
            else:
                cadence = extra.get("minValue", extra.get("maxValue"))
            if cadence is not None:
                step["cadence_rpm"] = max(30, min(200, int(round(cadence))))
            break
    return step


def _sanitize_structure(tp_structure: Dict[str, Any]) -> Dict[str, Any]:
    steps = [s for s in (_sanitize_step(b) for b in tp_structure.get("structure") or []) if s]
    polyline = [
        [round(float(x), 5), round(float(y), 5)]
        for x, y in (tp_structure.get("polyline") or [])
    ]
    return {
        "primary_length_metric": str(tp_structure.get("primaryLengthMetric") or "duration"),
        "primary_intensity_metric": str(tp_structure.get("primaryIntensityMetric") or "percentOfFtp"),
        "polyline": polyline,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# Session builders
# ---------------------------------------------------------------------------

def _build_bike_session(
    *, name: str, level: int, role: str, duration_min: int, tss: int,
    discipline: str, methodology: str, control: Dict[str, Any],
    fueling_input: Dict[str, Any], race_name: str, weekday: date,
    used_titles: set,
) -> Dict[str, Any]:
    zwo = render_workout(
        name=name, level=level, methodology=methodology, discipline=discipline,
        display_name=name, week_type="load", phase="build",
    )
    if not zwo:
        raise MotorenPreviewError("engine could not render a selected session")
    try:
        parsed = parse_zwo_structure_text(zwo, source_name=name)
        canonical_segments = [_canonical_segment(seg, control) for seg in parsed["segments"]]
        session_for_projection = {
            "tp_kind": "bike", "segments": canonical_segments, "title": parsed["name"],
        }
        tp_structure = project_tp_structure(session_for_projection, control)
    except Exception as exc:  # pragma: no cover - defensive, engine internals
        raise MotorenPreviewError("engine failed to project a session structure") from exc
    if not tp_structure or not tp_structure.get("structure"):
        raise MotorenPreviewError("engine produced no structured content for a session")

    title = str(parsed.get("name") or name).strip() or name
    base_title = title
    suffix_idx = 1
    while title.casefold() in used_titles:
        suffix_idx += 1
        title = f"{base_title} — {weekday.strftime('%A')}" if suffix_idx == 2 else f"{base_title} ({suffix_idx})"
    used_titles.add(title.casefold())

    tier = classify_fuel_tier(name)
    fuel_text = _get_fuel_tag_for_type(
        name, fueling=fueling_input, duration_min=duration_min, week_num=None)
    if tier == "exempt":
        fuel_tag = "none"
    elif tier == "race_sim":
        fuel_tag = "high"
    elif tier == "quality":
        fuel_tag = "high" if duration_min >= 90 else "moderate"
    else:
        fuel_tag = "practice" if duration_min >= 90 else "none"
    if not fuel_text:
        fuel_text = "Water and normal fueling; no in-ride carbohydrate target needed."

    session_voice_input = {
        "archetype_id": name, "title": title, "duration_s": duration_min * 60,
        "is_field_test": False, "is_simulation": False, "is_dress_rehearsal": False,
    }
    try:
        copy = render_preview_workout_copy(
            session_voice_input, description=str(parsed.get("description") or ""),
            day=weekday.strftime("%A"), race_name=race_name,
        )
    except ValueError as exc:
        raise MotorenPreviewError(
            "engine workout copy failed the coaching voice contract") from exc

    return {
        "kind": "bike",
        "title": title[:120],
        "purpose": copy["purpose"],
        "duration_minutes": int(duration_min),
        "tss": int(round(tss)),
        "intensity_label": _intensity_label(name, role),
        "fuel_tag": fuel_tag,
        "fueling_guidance": fuel_text[:240],
        "coach_note": copy["coach_note"],
        "structure": _sanitize_structure(tp_structure),
    }


def _build_strength_session(
    *, week_num: int, phase: str, race_name: str, weekday: date, used_titles: set,
    equipment_tier: str = "full-gym", is_recovery_week: bool = False,
) -> Dict[str, Any]:
    program = WorkoutLibrary.get_strength_workout(
        week_num=week_num, session_num=1, equipment_tier=equipment_tier,
        phase=phase, is_recovery_week=is_recovery_week, is_masters=False,
    )
    raw_name = str(program.get("name") or "Strength")
    title = re.sub(r"\s*-\s*\d+min\s*$", "", raw_name).strip() or raw_name
    base_title = title
    suffix_idx = 1
    while title.casefold() in used_titles:
        suffix_idx += 1
        title = f"{base_title} ({suffix_idx})"
    used_titles.add(title.casefold())

    exercises: List[Dict[str, Any]] = []
    # Rest is not part of workout_library.py's prescription strings -- a
    # reasonable, honestly-derived default by position (heavier compound
    # lifts first, lighter accessory work last), not pipeline-sourced.
    rest_by_index = [150, 120, 90, 60]
    for idx, (exercise_name, prescription) in enumerate(program.get("exercises") or []):
        match = re.match(r"^\s*(\d+)\s*x\s*([^\s@]+(?:\s+each)?)", str(prescription))
        sets = int(match.group(1)) if match else 3
        reps = match.group(2) if match else "8"
        if "@" in prescription:
            cue = prescription.split("@", 1)[1].strip()
        else:
            cue = str(prescription).strip()
        rest_seconds = rest_by_index[idx] if idx < len(rest_by_index) else rest_by_index[-1]
        exercises.append({
            "name": str(exercise_name)[:80],
            "sets": max(1, min(12, sets)),
            "reps": str(reps)[:24],
            "rest_seconds": rest_seconds,
            "cue": (cue or "Controlled tempo; stop short of grinding reps.")[:180],
        })
    duration_min = int(program.get("duration_min") or 45)
    focus = str(program.get("focus") or "Cycling-specific strength")

    try:
        copy = render_preview_strength_copy(
            title=title, focus=focus, day=weekday.strftime("%A"),
            race_name=race_name,
        )
    except ValueError as exc:
        raise MotorenPreviewError(
            "engine strength copy failed the coaching voice contract") from exc

    return {
        "kind": "strength",
        "title": title[:120],
        "purpose": copy["purpose"],
        "duration_minutes": duration_min,
        "tss": max(1, round(duration_min * 0.7)),
        "intensity_label": "Strength",
        "fuel_tag": "moderate",
        "fueling_guidance": copy["fueling_guidance"],
        "coach_note": copy["coach_note"],
        "strength": {"focus": focus[:120], "exercises": exercises},
    }


# ---------------------------------------------------------------------------
# Week-level notes (real story_notes voice pipeline, in-memory PlanIR-shaped
# dict -- story_notes._get() accepts plain dicts, no dataclass needed).
# ---------------------------------------------------------------------------

def _week_coach_note(
    sessions: List[Dict[str, Any]], race_name: str, *,
    week_num: int = _WEEK_NUMBER, phase: str = "build", week_type: str = "load",
    total_weeks: Optional[int] = None,
) -> str:
    story_phase = "peak" if phase == "race_prep" else phase
    if total_weeks is None:
        # V1 fixture compatibility: the original one-week preview hands the
        # voice renderer only its representative week.
        weeks = [{
            "number": week_num, "phase": story_phase,
            "week_type": week_type, "sessions": sessions,
        }]
    else:
        total_weeks = max(week_num, int(total_weeks))
        dated_sessions = [
            date.fromisoformat(str(session["date"])) for session in sessions
            if session.get("date")
        ]
        current_start = min(dated_sessions) if dated_sessions else _REFERENCE_MONDAY
        weeks = [
            {
                "number": number,
                "phase": story_phase,
                "week_type": week_type if number == week_num else "load",
                "sessions": sessions if number == week_num else [{
                    "date": (current_start + timedelta(
                        days=(number - week_num) * 7)).isoformat(),
                    "tp_kind": "note",
                    "title": "Plan week",
                    "duration_s": 0,
                }],
            }
            for number in range(1, total_weeks + 1)
        ]
    plan_ir = {
        "athlete": {"id": "preview"},
        "events": [{"name": race_name, "priority": "A", "date": None}],
        "race_snapshot": {"name": race_name, "date": None},
        "coached_block": {},
        "weeks": weeks,
    }
    try:
        notes = render_story_notes(plan_ir)
    except Exception as exc:  # pragma: no cover - defensive
        raise MotorenPreviewError("engine failed to render week notes") from exc
    target_title = f"Week {week_num}: {story_phase.replace('_', ' ').title()}"
    for note in notes:
        if note["title"] == target_title:
            return note["body"][:700]
    # Fall back to the first non-protocol/self-review note if the title
    # ever drifts (label derivation lives in story_notes, not here).
    for note in notes:
        if note["title"] not in ("How To Comment On Workouts", "Week Self Review - 3 Qs"):
            return note["body"][:700]
    raise MotorenPreviewError("engine produced no week note")


# ---------------------------------------------------------------------------
# Leak check
# ---------------------------------------------------------------------------

_LEAK_LIBRARY_ID = re.compile(r"\b\d{7,8}\b.{0,20}library|library.{0,20}\b\d{7,8}\b", re.I)
_LEAK_PATTERNS = [
    _LEAK_LIBRARY_ID,
    re.compile(r"\.py\b"),
    re.compile(r"/athletes/"),
    re.compile(r"plan[_]?ir", re.I),
    re.compile(r"library_item_id", re.I),
    re.compile(r"source_file", re.I),
    re.compile(r"compliance", re.I),
    re.compile(r"internal[_ -]?only", re.I),
]


def _assert_no_leak(source: Dict[str, Any]) -> None:
    wire = json.dumps(source, sort_keys=True, ensure_ascii=False)
    for pattern in _LEAK_PATTERNS:
        if pattern.search(wire):
            raise MotorenPreviewError("engine output failed the internal-token leak check")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def generate_preview_source(normalized_request: Mapping[str, Any]) -> Dict[str, Any]:
    """Run Motoren in-memory and return the requested public-preview source.

    V1 remains byte-stable for existing consumers. V2 builds one canonical
    calendar-backed plan, then selects its sample weeks from that same plan so
    calendar cards and the load curve cannot disagree.

    Deterministic: the same normalized request always produces byte-identical
    output for a given ``ENGINE_VERSION``/``VOICE_VERSION``. Raises
    ``MotorenPreviewError`` on any failure; never returns a partial result.
    """
    try:
        if normalized_request.get("schema_version") == "training-plan-preview-request/v2":
            return _generate_preview_source_v2(normalized_request)
        return _generate_preview_source(normalized_request)
    except MotorenPreviewError:
        raise
    except Exception as exc:
        raise MotorenPreviewError("unable to build a preview for this request") from exc


def _generate_preview_source(normalized_request: Mapping[str, Any]) -> Dict[str, Any]:
    request = normalized_request
    rider = request["rider"]
    race = request["race"]
    experience = rider["experience_level"]
    hours_per_week = int(rider["hours_per_week"])
    preferred_days = list(rider["preferred_days"])
    if len(preferred_days) < 3:
        raise MotorenPreviewError("at least three preferred days are required")

    seed = _request_digest(request)
    athlete = _synthetic_athlete(request, seed)
    discipline = _resolve_discipline(request)

    archetype_name = determine_archetype(hours_per_week)
    training_age = get_training_age_constraints(
        athlete["training_history"]["years_structured"])
    max_level = training_age["max_level"]
    # Reserve at least one day for the long ride and, when there are enough
    # preferred days, one for filler/endurance volume -- block_builder's
    # grow-to-floor pass only grows long_ride/filler days (never intensity
    # days, which are pinned to their level-based duration ladder), so an
    # athlete with few preferred days and many stated hours needs headroom
    # on a growable day or the week under-fills the quality gate's 60%
    # credible-use floor regardless of day_caps.
    max_intensity = min(
        training_age["max_intensity_per_week"], max(1, len(preferred_days) - 2))
    base_level = min(_EXPERIENCE_TO_BASE_LEVEL.get(experience, 2), max_level)

    category_weights = calculate_category_scores(dict(race["demands"]))

    preferred_caps = _capitalized_days(preferred_days)
    off_days = [d for d in DAY_ORDER if d not in preferred_caps]
    long_ride_day = _pick_long_ride_day(preferred_caps)

    control = determine_control(athlete)
    ftp_watts = athlete["fitness_markers"]["ftp_watts"]
    weight_kg = athlete["fitness_markers"]["weight_kg"]
    goal_type = athlete["target_race"]["goal_type"]
    prescription = build_fueling_prescription(
        duration_hours=_ASSUMED_RACE_DURATION_HOURS, weight_kg=weight_kg,
        ftp_watts=ftp_watts, goal_type=goal_type).to_dict()
    fueling_input = {"prescription": prescription}

    strength_program = WorkoutLibrary.get_strength_workout(
        week_num=_WEEK_NUMBER, session_num=1, equipment_tier="full-gym",
        phase="build", is_recovery_week=False, is_masters=False)
    strength_duration = int(strength_program.get("duration_min") or 45)

    avail_minutes = hours_per_week * 60
    bike_budget = avail_minutes - strength_duration
    day_caps = _allocate_day_caps(preferred_caps, long_ride_day, bike_budget)

    week = build_calendar_week(
        week_type="load", phase="build", archetype=archetype_name,
        block_number=2, week_in_block=1, base_level=base_level,
        max_level=max_level, max_intensity=max_intensity,
        off_days=off_days, long_ride_day=long_ride_day,
        hours_per_week=hours_per_week, discipline=discipline,
        methodology="polarized_80_20", category_weights=category_weights,
        day_caps=day_caps,
    )

    intensity_days = {
        d["day"] for d in week["days"] if d.get("role") == "intensity"}
    strength_days = place_strength_days(
        lambda d: d in preferred_caps, requested_sessions=1,
        blocked_days={long_ride_day} | set(off_days), avoid_days=intensity_days)

    used_titles: set = set()
    days_by_key: Dict[str, List[Dict[str, Any]]] = {k: [] for k in _DAY_KEYS}
    story_sessions: List[Dict[str, Any]] = []

    for offset, day_dict in enumerate(week["days"]):
        day_abbrev = day_dict["day"]  # 'Mon'..'Sun'
        day_key = _DAY_KEYS[offset]
        weekday_date = _REFERENCE_MONDAY + timedelta(days=offset)
        role = day_dict.get("role")
        if role == "off":
            continue
        name = day_dict["name"]
        session = _build_bike_session(
            name=name, level=int(day_dict.get("level") or 1), role=role,
            duration_min=int(day_dict.get("duration") or 0),
            tss=int(day_dict.get("tss") or 0), discipline=discipline,
            methodology="POLARIZED", control=control,
            fueling_input=fueling_input, race_name=race["name"],
            weekday=weekday_date, used_titles=used_titles,
        )
        days_by_key[day_key].append(session)
        story_sessions.append({
            "date": weekday_date.isoformat(), "tp_kind": "bike",
            "title": session["title"], "archetype_id": name,
            "duration_s": session["duration_minutes"] * 60,
            "is_field_test": False, "is_simulation": False,
            "is_dress_rehearsal": False,
        })

    for offset, day_abbrev in enumerate(DAY_ORDER):
        if day_abbrev not in strength_days:
            continue
        day_key = _DAY_KEYS[offset]
        weekday_date = _REFERENCE_MONDAY + timedelta(days=offset)
        strength_session = _build_strength_session(
            week_num=_WEEK_NUMBER, phase="build", race_name=race["name"],
            weekday=weekday_date, used_titles=used_titles,
        )
        days_by_key[day_key].append(strength_session)
        story_sessions.append({
            "date": weekday_date.isoformat(), "tp_kind": "strength",
            "title": strength_session["title"], "archetype_id": None,
            "duration_s": strength_session["duration_minutes"] * 60,
            "is_field_test": False, "is_simulation": False,
            "is_dress_rehearsal": False,
        })

    days = [{"day": key, "sessions": days_by_key[key]} for key in _DAY_KEYS]

    active_sessions = [s for day in days for s in day["sessions"]]
    if not active_sessions:
        raise MotorenPreviewError("engine produced an empty preview week")
    total_minutes = sum(s["duration_minutes"] for s in active_sessions)
    total_tss = sum(s["tss"] for s in active_sessions)

    story_sessions.sort(key=lambda s: s["date"])
    week_coach_note = _week_coach_note(story_sessions, race["name"])

    source = {
        "week": {
            "phase": "build",
            "type": "load",
            "target_minutes": int(total_minutes),
            "target_tss": int(total_tss),
            "coach_note": week_coach_note,
            "weekly_self_review": SELF_REVIEW_BODY,
            "comment_protocol": COMMENT_PROTOCOL_BODY,
            "days": days,
        },
    }
    _assert_no_leak(source)
    return source


# ---------------------------------------------------------------------------
# V2: one canonical full-plan source for both calendar weeks and load curve.
# ---------------------------------------------------------------------------

_V2_SCHEMA = "training-plan-preview-request/v2"


def _v2_athlete(request: Mapping[str, Any], seed: int) -> Dict[str, Any]:
    athlete = _synthetic_athlete(request, seed)
    rider = request["rider"]
    race = request["race"]
    athlete["target_race"]["date"] = race["date"]
    athlete["target_race"]["goal_type"] = rider["goal_type"]
    control_method = rider["control_method"]
    fitness = athlete["fitness_markers"]
    fitness["requested_metric"] = control_method
    if control_method == "power":
        fitness["ftp_watts"] = rider["ftp_watts"]
        fitness["power_basis"] = "measured"
    else:
        fitness["ftp_watts"] = None
        fitness["power_basis"] = "none"
    if rider.get("lthr_bpm") is not None:
        fitness["lthr"] = rider["lthr_bpm"]
    if rider.get("max_hr_bpm") is not None:
        fitness["max_hr"] = rider["max_hr_bpm"]
    return athlete


def _v2_strength_days(
    week: Mapping[str, Any], preferred_caps: List[str], off_days: List[str],
    long_ride_day: str,
) -> set:
    if week.get("week_type") == "race":
        return set()
    intensity_days = {
        day["day"] for day in week["days"] if day.get("role") == "intensity"
    }
    return set(place_strength_days(
        lambda day: day in preferred_caps,
        requested_sessions=1,
        blocked_days={long_ride_day} | set(off_days),
        avoid_days=intensity_days,
    ))


def _v2_strength_metrics(
    *, week_num: int, phase: str, week_type: str, equipment_tier: str,
) -> Tuple[int, int]:
    if week_type == "race":
        return 0, 0
    program = WorkoutLibrary.get_strength_workout(
        week_num=week_num, session_num=1, equipment_tier=equipment_tier,
        phase=phase, is_recovery_week=week_type == "recovery",
        is_masters=False,
    )
    minutes = int(program.get("duration_min") or 45)
    return minutes, max(1, round(minutes * 0.7))


def _build_race_session(
    *, race_name: str, duration_minutes: int, fueling_input: Mapping[str, Any],
) -> Dict[str, Any]:
    prescription = dict(fueling_input.get("prescription") or {})
    race_target = prescription.get("race_target_g_per_hour")
    if race_target is None:
        race_target = prescription.get("target_g_per_hour")
    fueling = (
        f"Begin in the first 20 minutes. Target {int(round(race_target))}g "
        "carbohydrate per hour and use the bottles and foods rehearsed in training."
        if isinstance(race_target, (int, float))
        else "Begin in the first 20 minutes and execute the fueling plan rehearsed in training."
    )
    try:
        copy = render_preview_race_copy(race_name)
    except ValueError as exc:
        raise MotorenPreviewError(
            "engine race copy failed the coaching voice contract") from exc
    return {
        "kind": "race",
        "title": f"Race Day — {race_name}"[:120],
        "purpose": copy["purpose"],
        "duration_minutes": duration_minutes,
        "tss": race_day_tss_from_emitted_minutes(duration_minutes),
        "intensity_label": "Race",
        "fuel_tag": "high",
        "fueling_guidance": fueling[:240],
        "coach_note": copy["coach_note"],
        # AE-8.4d: race-day FreeRide cards intentionally have no fake power graph.
        "structure": None,
        "_engine_overlay": True,
    }


def _v2_week_summary(
    week: Mapping[str, Any], calendar_week: Mapping[str, Any], *,
    preferred_caps: List[str], off_days: List[str], long_ride_day: str,
    equipment_tier: str, race_duration_minutes: int,
) -> Dict[str, Any]:
    week_num = int(week["plan_week"])
    phase = str(week["phase"])
    week_type = str(week["week_type"])
    race_days = {
        str(day["day"])[:3].title() for day in calendar_week["days"]
        if day.get("is_race_day")
    }
    minutes = 0
    tss = 0
    session_count = 0
    longest = 0
    for day in week["days"]:
        if day.get("role") == "off" or day["day"] in race_days:
            continue
        duration = int(day.get("duration") or 0)
        if duration <= 0:
            continue
        day_tss = int(day.get("tss") or 0)
        minutes += duration
        tss += day_tss
        session_count += 1
        longest = max(longest, duration)
    strength_days = _v2_strength_days(
        week, preferred_caps, off_days, long_ride_day)
    if strength_days:
        strength_minutes, strength_tss = _v2_strength_metrics(
            week_num=week_num, phase=phase, week_type=week_type,
            equipment_tier=equipment_tier,
        )
        minutes += strength_minutes
        tss += strength_tss
        session_count += 1
        longest = max(longest, strength_minutes)
    if race_days:
        race_tss = race_day_tss_from_emitted_minutes(race_duration_minutes)
        minutes += race_duration_minutes
        tss += race_tss
        session_count += 1
        longest = max(longest, race_duration_minutes)
    return {
        "week_number": week_num,
        "phase": phase,
        "type": week_type,
        "start_date": calendar_week["days"][0]["date"],
        "end_date": calendar_week["days"][-1]["date"],
        "target_minutes": minutes,
        "target_tss": tss,
        "session_count": session_count,
        "longest_session_minutes": longest,
    }


def _v2_sample_numbers(
        volume: Sequence[Mapping[str, Any]], requested: Optional[int] = None,
) -> List[int]:
    first = next(
        item["week_number"] for item in volume
        if item["type"] == "load")
    specific_candidates = [
        item for item in volume
        if item["phase"] in {"build", "peak", "race_prep"}
        and item["type"] == "load"
    ]
    specific = max(
        specific_candidates or list(volume),
        key=lambda item: (item["target_tss"], item["week_number"]),
    )["week_number"]
    race = next(
        (item["week_number"] for item in reversed(volume)
         if item["type"] == "race"),
        volume[-1]["week_number"],
    )
    ordered = [first, specific]
    if requested is not None:
        ordered.append(int(requested))
    ordered.append(race)
    return list(dict.fromkeys(ordered))


def _v2_render_week(
    week: Mapping[str, Any], calendar_week: Mapping[str, Any], *,
    request: Mapping[str, Any], discipline: str, control: Mapping[str, Any],
    fueling_input: Mapping[str, Any], preferred_caps: List[str],
    off_days: List[str], long_ride_day: str,
    race_duration_minutes: int,
    total_weeks: int,
) -> Dict[str, Any]:
    race = request["race"]
    rider = request["rider"]
    week_num = int(week["plan_week"])
    phase = str(week["phase"])
    week_type = str(week["week_type"])
    date_by_abbrev = {
        str(day["day"])[:3].title(): date.fromisoformat(day["date"])
        for day in calendar_week["days"]
    }
    race_days = {
        str(day["day"])[:3].title() for day in calendar_week["days"]
        if day.get("is_race_day")
    }
    used_titles: set = set()
    days_by_key: Dict[str, List[Dict[str, Any]]] = {key: [] for key in _DAY_KEYS}
    story_sessions: List[Dict[str, Any]] = []
    for offset, day_dict in enumerate(week["days"]):
        day_abbrev = day_dict["day"]
        day_key = _DAY_KEYS[offset]
        weekday_date = date_by_abbrev[day_abbrev]
        if day_abbrev in race_days:
            session = _build_race_session(
                race_name=race["name"], duration_minutes=race_duration_minutes,
                fueling_input=fueling_input,
            )
            days_by_key[day_key].append(session)
            story_sessions.append({
                "date": weekday_date.isoformat(), "tp_kind": "race",
                "title": session["title"], "archetype_id": None,
                "duration_s": session["duration_minutes"] * 60,
                "is_field_test": False, "is_simulation": False,
                "is_dress_rehearsal": False,
            })
            continue
        if day_dict.get("role") == "off":
            continue
        duration = int(day_dict.get("duration") or 0)
        if duration <= 0:
            continue
        name = day_dict["name"]
        session = _build_bike_session(
            name=name, level=int(day_dict.get("level") or 1),
            role=day_dict.get("role"), duration_min=duration,
            tss=int(day_dict.get("tss") or 0), discipline=discipline,
            methodology="POLARIZED", control=control,
            fueling_input=fueling_input, race_name=race["name"],
            weekday=weekday_date, used_titles=used_titles,
        )
        session["_library_backed"] = True
        days_by_key[day_key].append(session)
        story_sessions.append({
            "date": weekday_date.isoformat(), "tp_kind": "bike",
            "title": session["title"], "archetype_id": name,
            "duration_s": session["duration_minutes"] * 60,
            "is_field_test": False, "is_simulation": False,
            "is_dress_rehearsal": False,
        })
    strength_days = _v2_strength_days(
        week, preferred_caps, off_days, long_ride_day)
    for offset, day_abbrev in enumerate(DAY_ORDER):
        if day_abbrev not in strength_days or day_abbrev in race_days:
            continue
        day_key = _DAY_KEYS[offset]
        weekday_date = date_by_abbrev[day_abbrev]
        session = _build_strength_session(
            week_num=week_num, phase=phase, race_name=race["name"],
            weekday=weekday_date, used_titles=used_titles,
            equipment_tier=rider["strength_equipment"],
            is_recovery_week=week_type == "recovery",
        )
        session["_library_backed"] = True
        days_by_key[day_key].append(session)
        story_sessions.append({
            "date": weekday_date.isoformat(), "tp_kind": "strength",
            "title": session["title"], "archetype_id": None,
            "duration_s": session["duration_minutes"] * 60,
            "is_field_test": False, "is_simulation": False,
            "is_dress_rehearsal": False,
        })
    days = [
        {
            "day": key,
            "date": calendar_week["days"][index]["date"],
            "sessions": days_by_key[key],
        }
        for index, key in enumerate(_DAY_KEYS)
    ]
    active = [session for day in days for session in day["sessions"]]
    total_minutes = sum(session["duration_minutes"] for session in active)
    total_tss = sum(session["tss"] for session in active)
    story_sessions.sort(key=lambda item: item["date"])
    coach_note = _week_coach_note(
        story_sessions, race["name"], week_num=week_num,
        phase=phase, week_type=week_type, total_weeks=total_weeks,
    )
    return {
        "week_number": week_num,
        "phase": phase,
        "type": week_type,
        "start_date": calendar_week["days"][0]["date"],
        "end_date": calendar_week["days"][-1]["date"],
        "target_minutes": total_minutes,
        "target_tss": total_tss,
        "coach_note": coach_note,
        "weekly_self_review": SELF_REVIEW_BODY,
        "comment_protocol": COMMENT_PROTOCOL_BODY,
        "days": days,
    }


def _generate_preview_source_v2(request: Mapping[str, Any]) -> Dict[str, Any]:
    if request.get("schema_version") != _V2_SCHEMA:
        raise MotorenPreviewError("unsupported preview schema")
    rider = request["rider"]
    race = request["race"]
    hours_per_week = int(rider["hours_per_week"])
    preferred_days = list(rider["preferred_days"])
    preferred_caps = _capitalized_days(preferred_days)
    off_days = [day for day in DAY_ORDER if day not in preferred_caps]
    long_ride_day = _pick_long_ride_day(preferred_caps)
    seed = _request_digest(request)
    athlete = _v2_athlete(request, seed)
    discipline = _resolve_discipline(request)
    event_format = _resolve_road_event_format(request, discipline)
    if event_format:
        athlete["target_race"]["event_format"] = event_format
    training_age = get_training_age_constraints(
        athlete["training_history"]["years_structured"])
    max_level = training_age["max_level"]
    max_intensity = min(
        training_age["max_intensity_per_week"],
        max(1, len(preferred_days) - 2),
    )
    base_level = min(
        _EXPERIENCE_TO_BASE_LEVEL.get(rider["experience_level"], 2),
        max_level,
    )
    control = determine_control(athlete)
    ftp_watts = athlete["fitness_markers"].get("ftp_watts") or 200
    weight_kg = athlete["fitness_markers"]["weight_kg"]
    expected_hours = float(race["expected_duration_hours"])
    prescription = build_fueling_prescription(
        duration_hours=expected_hours, weight_kg=weight_kg,
        ftp_watts=ftp_watts, goal_type=rider["goal_type"],
    ).to_dict()
    fueling_input = {"prescription": prescription}
    plan_dates = calculate_plan_dates(
        race["date"], plan_weeks=int(request["plan_weeks"]),
        clamp_past_start=False,
    )
    descriptors = derive_week_descriptors(plan_dates)
    day_caps = {
        day.capitalize(): int(minutes)
        for day, minutes in rider.get("day_caps_minutes", {}).items()
    } or None
    plan = build_plan_from_calendar(
        week_descriptors=descriptors,
        archetype=determine_archetype(hours_per_week),
        max_level=max_level, max_intensity=max_intensity,
        off_days=off_days, long_ride_day=long_ride_day,
        starting_level=base_level, hours_per_week=hours_per_week,
        discipline=discipline, day_caps=day_caps,
        methodology="polarized_80_20",
        category_weights=calculate_category_scores(dict(race["demands"])),
        training_age=training_age["label"],
        event_format=event_format,
    )
    if len(plan["weeks"]) != len(plan_dates["weeks"]):
        raise MotorenPreviewError("engine plan calendar did not align")
    race_duration_minutes = int(round(expected_hours * 60))
    volume = [
        _v2_week_summary(
            week, calendar_week, preferred_caps=preferred_caps,
            off_days=off_days, long_ride_day=long_ride_day,
            equipment_tier=rider["strength_equipment"],
            race_duration_minutes=race_duration_minutes,
        )
        for week, calendar_week in zip(plan["weeks"], plan_dates["weeks"])
    ]
    sample_numbers = _v2_sample_numbers(
        volume, requested=request.get("sample_week_number"))
    sample_weeks = [
        _v2_render_week(
            plan["weeks"][number - 1], plan_dates["weeks"][number - 1],
            request=request, discipline=discipline, control=control,
            fueling_input=fueling_input, preferred_caps=preferred_caps,
            off_days=off_days, long_ride_day=long_ride_day,
            race_duration_minutes=race_duration_minutes,
            total_weeks=len(volume),
        )
        for number in sample_numbers
    ]
    by_number = {item["week_number"]: item for item in volume}
    for sample in sample_weeks:
        summary = by_number[sample["week_number"]]
        if (sample["target_minutes"] != summary["target_minutes"]
                or sample["target_tss"] != summary["target_tss"]):
            raise MotorenPreviewError(
                "engine sample week did not match planned volume")
    source = {
        "plan": {
            "total_weeks": len(volume),
            "race_date": race["date"],
            "sample_week_numbers": sample_numbers,
            **({"profile_version": ROAD_PROFILE_VERSION}
               if event_format else {}),
        },
        "planned_volume": volume,
        "sample_weeks": sample_weeks,
    }
    _assert_no_leak(source)
    return source
