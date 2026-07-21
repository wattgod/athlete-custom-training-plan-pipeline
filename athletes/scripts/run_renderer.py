#!/usr/bin/env python3
"""Text renderer for the standalone RUN-LIB workout catalog.

This module deliberately does not share the bike renderer: bike helper dispatch
uses display-name substrings, while run workout IDs and category IDs are a public
contract.  Keep every content decision below keyed on ``category_id``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from run_archetypes import get_run_archetype, get_run_level


# Copied from nate_workout_generator.get_progression_context.  Do not import the
# bike generator here: RUN-LIB must remain independently renderable.
_PROGRESSION_CONTEXT = {
    1: "Introductory - Focus on form and learning the workout pattern",
    2: "Foundation - Building base fitness with moderate challenge",
    3: "Development - Standard training load, building consistency",
    4: "Progressive - Increased challenge, refining execution",
    5: "Advanced - High training load, pushing limits",
    6: "Peak - Maximum challenge, race-ready intensity",
}

_PURPOSES = {
    "recovery_easy": "Active recovery that restores movement quality without adding meaningful training stress.",
    "endurance_z2": "Aerobic base work that builds durable, efficient all-day running.",
    "long_run": "Time-on-feet durability and practiced run/hike pacing for long trail days.",
    "strides": "Leg-speed practice that improves coordination while keeping the overall load low.",
    "hills_powerhike": "Build efficient climbing strength and make purposeful hiking a race-ready skill.",
    "hills_reps": "Develop uphill strength and descending resilience with controlled repeatable climbs.",
    "tempo_steady": "Raise sustainable steady-running capacity and teach a controlled strong finish.",
    "race_pace": "Rehearse the sustainable all-day effort, pacing restraint, and fueling rhythm of an ultra.",
    "downhill_skills": "Build downhill skill and eccentric tolerance with deliberate, repeatable exposure.",
    "openers": "Wake up coordination and leg speed without carrying fatigue into race day.",
    "pickups": "Add a small dose of controlled speed while preserving an aerobic day.",
}

_EXECUTION = {
    "recovery_easy": "Keep the effort conversational; walk or stop if your stride does not feel smooth.",
    "endurance_z2": "Hold an effort you could sustain for hours and let hills slow you down rather than raise effort.",
    "long_run": "Practice the planned run/hike rhythm from the first climb and use the same kit you expect to race with.",
    "strides": "Accelerate smoothly, stay tall and relaxed, then stop each stride before form gets forced.",
    "hills_powerhike": "Hike hard enough that running would only be marginally faster.",
    "hills_reps": "Keep each climb strong but repeatable; walk down under control and protect the downhill legs.",
    "tempo_steady": "Start the steady work controlled and finish feeling like you could complete one more repeat.",
    "race_pace": "Use all-day effort, not watch pace, as the governor; practice fueling before you feel behind.",
    "downhill_skills": "Choose a safe line, quicken your feet, and stay within control rather than chasing speed.",
    "openers": "Make the pickups crisp, not draining; finish fresher than you started.",
    "pickups": "Run the pickups with relaxed form and return fully to easy effort between them.",
}

_DEFAULT_CADENCE = {
    "recovery_easy": "Relaxed, natural turnover; no cadence target.",
    "endurance_z2": "170-180spm on flats; let cadence shorten naturally on climbs.",
    "long_run": "Light, economical turnover; shorten the stride before steep climbs force it.",
    "strides": "Quick, relaxed turnover; stay smooth rather than reaching for speed.",
    "hills_powerhike": "170-180spm running; hike with short, strong steps.",
    "hills_reps": "Quick uphill steps; keep the descent controlled rather than braking hard.",
    "tempo_steady": "170-180spm with a compact stride at steady effort.",
    "race_pace": "Economical, compact turnover that you can sustain all day.",
    "downhill_skills": "Quick feet with a compact stride; avoid overstriding downhill.",
    "openers": "Quick and relaxed; never force turnover.",
    "pickups": "Quick, light turnover with relaxed shoulders and hands.",
}

_DEFAULT_TERRAIN = {
    "recovery_easy": "Flat, forgiving surface or treadmill.",
    "endurance_z2": "Mostly runnable rolling terrain with minimal technical footing.",
    "long_run": "Race-like trail where the planned run/hike rhythm is practical.",
    "strides": "Flat, smooth, predictable footing.",
    "hills_powerhike": "Rolling trail with sustained climbs.",
    "hills_reps": "Consistent moderate-to-steep hill with a safe walk-down.",
    "tempo_steady": "Smooth rolling route or flat path that supports even effort.",
    "race_pace": "Race-like terrain where effort, not pace, can govern the work.",
    "downhill_skills": "Runnable descent with good visibility and a safe return climb.",
    "openers": "Flat, smooth route close to home or the race venue.",
    "pickups": "Flat, smooth route with uninterrupted running room.",
}

_TYPE_LABELS = {
    "warmup": "warm-up",
    "steady": "easy run",
    "stride": "stride",
    "pickup": "pickup",
    "tempo": "steady run",
    "hike": "power-hike",
    "race": "race effort",
    "cooldown": "cool-down",
}


def get_run_purpose(category_id: str) -> str:
    """Return category-owned purpose copy without consulting a display name."""
    return _PURPOSES.get(category_id, "Build confident, sustainable running with deliberate effort control.")


def get_run_execution(category_id: str, level_data: Mapping[str, Any]) -> str:
    """Return level-specific execution when authored, otherwise category copy."""
    return str(level_data.get("execution") or _EXECUTION.get(
        category_id, "Focus on consistent effort and good form throughout."
    ))


def get_run_nutrition(category_id: str, duration_min: float) -> str:
    """Return run-specific fueling copy for a minutes-based workout duration."""
    if duration_min < 60:
        return "None needed at this duration."
    if duration_min <= 90:
        return "Optional: carry carbs if you are practicing race fueling or starting under-fueled."

    if category_id in {"long_run", "race_pace", "race_day"}:
        guidance = "Dress rehearsal: 50-60g/hr; practice race products and timing."
    else:
        guidance = "40-60g/hr for Z2 endurance."
    if duration_min > 120:
        guidance += " Include sodium, especially in heat or heavy sweat conditions."
    return guidance


def get_run_hydration(category_id: str, duration_min: float) -> str:
    """Return category- and duration-aware hydration guidance in minutes."""
    if category_id == "recovery_easy":
        return "Drink to thirst; rehydrate normally after the run."
    if duration_min > 120:
        return "500-750ml/hr to thirst; include electrolytes and sodium for heat or heavy sweat loss."
    if category_id in {"hills_powerhike", "hills_reps", "tempo_steady", "race_pace", "downhill_skills"}:
        return "500-750ml/hr to thirst; start hydrated and use electrolytes in warm conditions."
    return "Drink to thirst; carry water when conditions or access require it."


def _get_default_run_cadence(category_id: str, level: int) -> str:
    """Return a category-owned cadence fallback; level is retained for the public contract."""
    del level
    return _DEFAULT_CADENCE.get(category_id, "Relaxed, economical turnover appropriate to the terrain.")


def _get_default_terrain(category_id: str, level: int) -> str:
    """Return a category-owned terrain fallback; level is retained for the public contract."""
    del level
    return _DEFAULT_TERRAIN.get(category_id, "Safe, runnable terrain appropriate to the session.")


def _format_duration(seconds: float) -> str:
    seconds = round(seconds)
    if seconds >= 60:
        minutes = seconds / 60
        return f"{minutes:g}min"
    return f"{seconds}sec"


def _rpe_text(segment: Mapping[str, Any]) -> str:
    low, high = segment.get("rpe", ("?", "?"))
    return f"RPE {low}-{high}"


def _segment_label(segment: Mapping[str, Any]) -> str:
    return str(segment.get("label") or _TYPE_LABELS.get(segment.get("type"), "run"))


def _render_segment(segment: Mapping[str, Any]) -> str:
    return f"{_format_duration(float(segment['duration']))} {_segment_label(segment)} @ {_rpe_text(segment)}"


def _render_main_segment(segment: Mapping[str, Any]) -> str:
    if segment.get("type") != "repeat":
        return f"-{_render_segment(segment)}."
    children = " + ".join(_render_segment(child) for child in segment.get("of", []))
    return f"-{segment.get('count', 0)}x [{children}]."


def _leaf_segments(segments: Iterable[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for segment in segments:
        if segment.get("type") == "repeat":
            yield from _leaf_segments(segment.get("of", []))
        else:
            yield segment


def _as_fraction(value: Any) -> float:
    value = float(value)
    return value / 100 if value > 1 else value


def _hr_line(segment: Mapping[str, Any], lthr: Any) -> str | None:
    values = segment.get("hr_pct_lthr")
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        return None
    try:
        low, high = (_as_fraction(value) for value in values)
        lthr_value = float(lthr)
    except (TypeError, ValueError):
        return None
    label = _segment_label(segment)
    bpm_low = int(lthr_value * low + 0.5)
    bpm_high = int(lthr_value * high + 0.5)
    return f"-{label}: {bpm_low}-{bpm_high} BPM ({round(low * 100)}-{round(high * 100)}% LTHR)."


def _rpe_descriptor(segment_type: str) -> str:
    return {
        "stride": "strides",
        "pickup": "pickups",
        "tempo": "steady running",
        "hike": "power-hiking",
        "race": "race effort",
        "steady": "easy running",
    }.get(segment_type, "running")


def _render_rpe(segments: Iterable[Mapping[str, Any]]) -> str:
    bands: dict[tuple[Any, Any], list[str]] = {}
    for segment in _leaf_segments(segments):
        if segment.get("type") in {"warmup", "cooldown"}:
            continue
        rpe = tuple(segment.get("rpe", ()))
        if len(rpe) != 2:
            continue
        descriptor = _rpe_descriptor(str(segment.get("type")))
        if descriptor not in bands.setdefault(rpe, []):
            bands[rpe].append(descriptor)
    if not bands:
        return "-RPE-led: keep the effort controlled."
    return "-" + ", ".join(
        f"{low}-{high}/10 {'/'.join(descriptors)}" for (low, high), descriptors in bands.items()
    ) + "."


def render_run_description(archetype_id: str, level: int, athlete: Mapping[str, Any] | None = None) -> str:
    """Render one RUN-LIB workout as the canonical nine-section description."""
    archetype = get_run_archetype(archetype_id)
    if archetype is None:
        raise ValueError(f"Unknown run archetype: {archetype_id}")
    if archetype.get("structure_exempt"):
        return str(archetype.get("description_brief", ""))

    level_data = get_run_level(archetype_id, level)
    if level_data is None:
        raise ValueError(f"Unknown level {level!r} for run archetype: {archetype_id}")

    level_number = int(level)
    category_id = str(archetype["category"])
    segments = level_data["segments"]
    warmup_segments = [segment for segment in segments if segment.get("type") == "warmup"]
    cooldown_segments = [segment for segment in segments if segment.get("type") == "cooldown"]
    main_segments = [
        segment for segment in segments if segment.get("type") not in {"warmup", "cooldown"}
    ]
    duration_min = float(level_data["duration"]) / 60

    sections = [
        ("WARM-UP:", [f"-{_render_segment(segment)}." for segment in warmup_segments]),
        ("MAIN SET:", [*(_render_main_segment(segment) for segment in main_segments)]),
        ("COOL-DOWN:", [f"-{_render_segment(segment)}." for segment in cooldown_segments]),
        ("PROGRESSION:", [f"-Level {level_number}/6: {_PROGRESSION_CONTEXT.get(level_number, 'Progressive development')}"]),
        ("PURPOSE:", [get_run_purpose(category_id)]),
        ("EXECUTION:", [f"-{get_run_execution(category_id, level_data)}"]),
        ("NUTRITION:", [f"-{get_run_nutrition(category_id, duration_min)}"]),
        ("HYDRATION:", [f"-{get_run_hydration(category_id, duration_min)}"]),
        ("RPE:", [_render_rpe(segments)]),
    ]

    cadence = level_data.get("cadence_prescription") or _get_default_run_cadence(category_id, level_number)
    terrain = level_data.get("terrain_prescription") or _get_default_terrain(category_id, level_number)
    sections[1][1].extend((f"-Cadence: {cadence}", f"-Terrain: {terrain}"))
    if athlete and athlete.get("lthr") is not None:
        sections[1][1].extend(
            line for line in (_hr_line(segment, athlete["lthr"]) for segment in _leaf_segments(main_segments))
            if line is not None
        )

    return "\n\n".join("\n".join([header, *body]) for header, body in sections)
