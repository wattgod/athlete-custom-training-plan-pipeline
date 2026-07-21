#!/usr/bin/env python3
"""TrainingPeaks structure and workout payload export for RUN-LIB workouts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

from run_archetypes import get_run_archetype, get_run_level
from run_renderer import render_run_description


_TP_INTENSITY_CLASSES = {"active", "warmUp", "coolDown", "rest"}
_TYPE_NAMES = {
    "warmup": "Warm up",
    "steady": "Easy run",
    "stride": "Stride",
    "pickup": "Pickup",
    "tempo": "Steady run",
    "hike": "Power-hike",
    "race": "Race effort",
    "cooldown": "Cool down",
}
_RECOVERY_LABELS = ("recover", "easy jog", "easy reset", "walk down", "walk back")


def _unroll_segments(segments: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return copied leaf segments, expanding every repeat block in order."""
    leaves: list[dict[str, Any]] = []
    for segment in segments:
        if segment.get("type") != "repeat":
            leaves.append(dict(segment))
            continue

        count = segment.get("count")
        children = segment.get("of")
        if not isinstance(count, int) or count < 0 or not isinstance(children, list):
            raise ValueError("Repeat segments require a non-negative integer count and a list of children")
        for _ in range(count):
            leaves.extend(_unroll_segments(children))
    return leaves


def _is_recovery(segment: Mapping[str, Any], previous_type: str | None) -> bool:
    """Recognize authored recovery leaves whose type remains ``steady`` in Format R."""
    if previous_type in {"stride", "pickup"} and segment.get("type") == "steady":
        return True
    label = str(segment.get("label", "")).lower()
    return any(marker in label for marker in _RECOVERY_LABELS)


def _intensity_class(segment: Mapping[str, Any], previous_type: str | None) -> str:
    segment_type = str(segment.get("type", ""))
    if segment_type == "warmup":
        return "warmUp"
    if segment_type == "cooldown":
        return "coolDown"
    if _is_recovery(segment, previous_type):
        return "rest"
    return "active"


def _segment_name(segment: Mapping[str, Any]) -> str:
    """Use an authored label when available, otherwise a stable type-owned name."""
    return str(segment.get("label") or _TYPE_NAMES.get(segment.get("type"), "Run"))


def _target(segment: Mapping[str, Any]) -> dict[str, int]:
    """Build the sole canonical RPE target; no HR or pace data reaches TP."""
    rpe = segment.get("rpe")
    if not isinstance(rpe, (list, tuple)) or len(rpe) != 2:
        raise ValueError("Every exported run segment requires an RPE [min, max] target")
    minimum, maximum = rpe
    if (
        not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or isinstance(minimum, bool)
        or isinstance(maximum, bool)
        or not 0 <= minimum <= maximum <= 10
    ):
        raise ValueError(f"Invalid RPE target: {rpe!r}")
    return {"minValue": minimum, "maxValue": maximum}


def _duration(segment: Mapping[str, Any]) -> float | int:
    value = segment.get("duration")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Invalid segment duration: {value!r}")
    return value


def _build_structure(segments: Iterable[Mapping[str, Any]], total_seconds: float | int) -> dict[str, Any]:
    """Project normalized seconds-based leaf segments into the accepted TP shape."""
    leaves = _unroll_segments(segments)
    if not leaves:
        raise ValueError("A TP run structure needs at least one segment")

    durations = [_duration(segment) for segment in leaves]
    segment_total = sum(durations)
    if abs(segment_total - total_seconds) > 1e-6:
        raise ValueError("Expanded segment duration does not match the workout duration")

    # Absorb only floating-point dust in the final value so the exported end is
    # exactly the library's authoritative duration (important for TP totals).
    durations[-1] = total_seconds - sum(durations[:-1])
    elements: list[dict[str, Any]] = []
    begin: float | int = 0
    previous_type: str | None = None
    for index, (segment, seconds) in enumerate(zip(leaves, durations)):
        end = total_seconds if index == len(leaves) - 1 else begin + seconds
        step = {
            "name": _segment_name(segment),
            "length": {"value": seconds, "unit": "second"},
            "targets": [_target(segment)],
            "intensityClass": _intensity_class(segment, previous_type),
            "openDuration": False,
        }
        elements.append({
            "type": "step",
            "length": {"value": 1, "unit": "repetition"},
            "steps": [step],
            "begin": begin,
            "end": end,
        })
        begin = end
        previous_type = str(segment.get("type", ""))

    return {
        "structure": elements,
        "primaryLengthMetric": "duration",
        "primaryIntensityMetric": "rpe",
        "primaryIntensityTargetOrRange": "range",
        "polyline": [],
    }


def export_tp_structure(archetype_id: str, level: int | str) -> dict[str, Any]:
    """Export one leveled RUN-LIB workout's TrainingPeaks structure object."""
    archetype = get_run_archetype(archetype_id)
    if archetype is None:
        raise ValueError(f"Unknown run archetype: {archetype_id}")
    if archetype.get("structure_exempt"):
        raise ValueError(f"Run race brief has no TP structure: {archetype_id}")

    level_data = get_run_level(archetype_id, level)
    if level_data is None:
        raise ValueError(f"Unknown level {level!r} for run archetype: {archetype_id}")
    return _build_structure(level_data["segments"], level_data["duration"])


def _workout_day_value(workout_day: date | datetime | str) -> str:
    """Return the date-only timestamp TrainingPeaks expects in workout payloads."""
    if isinstance(workout_day, datetime):
        day = workout_day.date()
    elif isinstance(workout_day, date):
        day = workout_day
    elif isinstance(workout_day, str):
        try:
            day = date.fromisoformat(workout_day[:10])
        except ValueError as exc:
            raise ValueError("workout_day must start with an ISO YYYY-MM-DD date") from exc
    else:
        raise TypeError("workout_day must be a date, datetime, or ISO date string")
    return f"{day.isoformat()}T00:00:00"


def _workout_title(archetype: Mapping[str, Any], level: int | str) -> str:
    """Keep generic library titles stable while race briefs remain unlevelled."""
    display_name = str(archetype["display_name"])
    return display_name if archetype.get("structure_exempt") else f"{display_name} L{level}"


def export_tp_workout(
    archetype_id: str,
    level: int | str,
    workout_day: date | datetime | str,
    athlete: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Export the complete POST body for a generic or athlete-specific run workout."""
    archetype = get_run_archetype(archetype_id)
    if archetype is None:
        raise ValueError(f"Unknown run archetype: {archetype_id}")

    structure_exempt = bool(archetype.get("structure_exempt"))
    if structure_exempt:
        total_seconds = 0
        tss = archetype.get("tss")
    else:
        level_data = get_run_level(archetype_id, level)
        if level_data is None:
            raise ValueError(f"Unknown level {level!r} for run archetype: {archetype_id}")
        total_seconds = level_data["duration"]
        tss = level_data["tss"]

    payload = {
        "workoutTypeValueId": 3,
        "workoutDay": _workout_day_value(workout_day),
        "title": _workout_title(archetype, level),
        "description": render_run_description(archetype_id, int(level), athlete),
        "totalTimePlanned": total_seconds / 3600,
        "tssPlanned": tss,
    }
    if not structure_exempt:
        payload["structure"] = export_tp_structure(archetype_id, level)
    return payload


def validate_tp_structure(obj: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` unless *obj* has the live-accepted TP structure shape."""
    if not isinstance(obj, Mapping):
        raise ValueError("TP structure must be a mapping")
    required = {
        "structure",
        "primaryLengthMetric",
        "primaryIntensityMetric",
        "primaryIntensityTargetOrRange",
        "polyline",
    }
    if set(obj) != required:
        raise ValueError("TP structure has incorrect top-level keys")
    if obj["primaryLengthMetric"] != "duration":
        raise ValueError("TP primaryLengthMetric must be duration")
    if obj["primaryIntensityMetric"] != "rpe":
        raise ValueError("TP primaryIntensityMetric must be rpe")
    if obj["primaryIntensityTargetOrRange"] != "range" or obj["polyline"] != []:
        raise ValueError("TP structure has incorrect intensity-range or polyline fields")
    if not isinstance(obj["structure"], list):
        raise ValueError("TP structure list is required")

    previous_end: float | int = 0
    for element in obj["structure"]:
        if not isinstance(element, Mapping) or set(element) != {"type", "length", "steps", "begin", "end"}:
            raise ValueError("TP structure element has incorrect keys")
        if element["type"] != "step":
            raise ValueError("TP structure elements must be flat steps")
        if element["length"] != {"value": 1, "unit": "repetition"}:
            raise ValueError("TP structure element length must be one repetition")
        begin, end = element["begin"], element["end"]
        if not isinstance(begin, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError("TP structure begin/end must be numeric")
        if abs(begin - previous_end) > 1e-6 or end <= begin:
            raise ValueError("TP structure begin/end must be cumulative and monotone")
        steps = element["steps"]
        if not isinstance(steps, list) or len(steps) != 1:
            raise ValueError("TP structure elements must contain exactly one step")
        step = steps[0]
        if not isinstance(step, Mapping) or set(step) != {
            "name", "length", "targets", "intensityClass", "openDuration"
        }:
            raise ValueError("TP step has incorrect keys")
        if not isinstance(step["name"], str) or not step["name"]:
            raise ValueError("TP step needs a name")
        length = step["length"]
        if (
            not isinstance(length, Mapping)
            or set(length) != {"value", "unit"}
            or length["unit"] != "second"
            or not isinstance(length["value"], (int, float))
            or abs((end - begin) - length["value"]) > 1e-6
        ):
            raise ValueError("TP step length must match its cumulative span in seconds")
        if step["intensityClass"] not in _TP_INTENSITY_CLASSES or step["openDuration"] is not False:
            raise ValueError("TP step intensity or openDuration is invalid")
        targets = step["targets"]
        if not isinstance(targets, list) or len(targets) != 1:
            raise ValueError("TP step needs exactly one RPE target")
        target = targets[0]
        if not isinstance(target, Mapping) or set(target) != {"minValue", "maxValue"}:
            raise ValueError("TP target has incorrect keys")
        minimum, maximum = target["minValue"], target["maxValue"]
        if (
            not isinstance(minimum, int)
            or not isinstance(maximum, int)
            or isinstance(minimum, bool)
            or isinstance(maximum, bool)
            or not 0 <= minimum <= maximum <= 10
        ):
            raise ValueError("TP target values must be ordered integer RPE values from 0 through 10")
        previous_end = end
