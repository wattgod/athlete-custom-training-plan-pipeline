#!/usr/bin/env python3
"""Registry and validation helpers for the standalone run workout library."""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from run_tss import RPE_IF_TABLE, _expanded_segments, _unrounded_tss, band_for, estimate_tss


LIBRARY_PATH = Path(__file__).resolve().parents[1] / "config" / "run_workout_library.yaml"
LEVEL_KEYS = {"1", "2", "3", "4", "5", "6"}
SEGMENT_TYPES = {
    "warmup", "steady", "stride", "pickup", "tempo", "hike", "race", "cooldown", "repeat",
}
FUELING_TIERS = {"none", "optional", "z2_long", "dress_rehearsal"}
# Backwards-compatible lookup retained for existing registry consumers.
RPE_TO_IF = dict(RPE_IF_TABLE)
_ID_PATTERN = re.compile(r"^run\.([a-z0-9]+(?:_[a-z0-9]+)*)\.([a-z0-9]+(?:_[a-z0-9]+)*)$")


class DuplicateRunArchetypeIDError(ValueError):
    """Raised when a YAML mapping contains the same workout ID twice."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that does not silently discard duplicate mapping keys."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateRunArchetypeIDError(f"Duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _normalize_segment(segment: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a YAML segment and convert minute durations to seconds."""
    normalized = copy.deepcopy(dict(segment))
    if "duration" in normalized:
        normalized["duration"] = float(normalized["duration"]) * 60
    if normalized.get("type") == "repeat":
        normalized["of"] = [_normalize_segment(child) for child in normalized.get("of", [])]
    return normalized


def _normalize_workout(workout: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a workout definition, normalizing level keys and durations."""
    normalized = copy.deepcopy(dict(workout))
    if "levels" not in normalized:
        return normalized

    normalized_levels = {}
    for level, definition in normalized["levels"].items():
        level_definition = copy.deepcopy(dict(definition))
        if "duration" in level_definition:
            level_definition["duration"] = float(level_definition["duration"]) * 60
        level_definition["segments"] = [
            _normalize_segment(segment)
            for segment in level_definition.get("segments", [])
        ]
        normalized_levels[str(level)] = level_definition
    normalized["levels"] = normalized_levels
    return normalized


def load_library(path: Path | str = LIBRARY_PATH) -> dict[str, dict[str, Any]]:
    """Load the authored YAML library into its internal seconds-based shape."""
    with Path(path).open(encoding="utf-8") as handle:
        document = yaml.load(handle, Loader=_UniqueKeyLoader)
    if not isinstance(document, Mapping) or not isinstance(document.get("run_workouts"), Mapping):
        raise ValueError("Run workout library must be a mapping with a run_workouts mapping")
    return {
        str(archetype_id): _normalize_workout(workout)
        for archetype_id, workout in document["run_workouts"].items()
    }


RUN_ARCHETYPES = load_library()


def catalog() -> list[str]:
    """Return stable run workout IDs in their authored order."""
    return list(RUN_ARCHETYPES)


def get_run_archetype(archetype_id: str) -> dict[str, Any] | None:
    """Return a run archetype by its stable ID, or ``None`` when unknown."""
    return RUN_ARCHETYPES.get(archetype_id)


def get_run_level(archetype_id: str, level: int | str) -> dict[str, Any] | None:
    """Return a normalized level definition; integer and string levels both work."""
    archetype = get_run_archetype(archetype_id)
    if archetype is None:
        return None
    return archetype.get("levels", {}).get(str(level))


def calculate_tss(segments: Iterable[Mapping[str, Any]]) -> float:
    """Calculate rTSS from normalized, seconds-based leaf or repeat segments."""
    return _unrounded_tss(segments)


def _item_pairs(library: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Accept a mapping or pairs so callers can validate duplicate IDs in memory."""
    if isinstance(library, Mapping):
        return list(library.items())
    return list(library)


def validate_library(
    library: Mapping[str, Any] | Iterable[tuple[str, Any]] | None = None,
) -> list[str]:
    """Return every schema and integrity violation in a normalized run library."""
    pairs = _item_pairs(RUN_ARCHETYPES if library is None else library)
    violations: list[str] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()

    for archetype_id, workout in pairs:
        if archetype_id in seen_ids:
            violations.append(f"Duplicate ID: {archetype_id}")
        seen_ids.add(archetype_id)

        if not isinstance(workout, Mapping):
            violations.append(f"{archetype_id}: definition must be a mapping")
            continue

        display_name = workout.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            violations.append(f"{archetype_id}: display_name must be non-empty")
        elif display_name in seen_names:
            violations.append(f"Duplicate display name: {display_name}")
        elif isinstance(display_name, str):
            seen_names.add(display_name)

        match = _ID_PATTERN.fullmatch(archetype_id)
        if match is None or match.group(1) != workout.get("category"):
            violations.append(f"{archetype_id}: ID must match run.<category>.<slug>")
        if workout.get("sport") != "run":
            violations.append(f"{archetype_id}: sport must be 'run'")

        levels = workout.get("levels")
        if "levels" in workout and workout.get("structure_exempt"):
            violations.append(f"{archetype_id}: leveled item cannot be structure_exempt")
        if levels is None:
            if not workout.get("structure_exempt"):
                violations.append(f"{archetype_id}: unleveled item must be structure_exempt")
            if workout.get("category") != "race_day":
                violations.append(f"{archetype_id}: unleveled item must use category race_day")
            if not isinstance(workout.get("description_brief"), str) or not workout["description_brief"].strip():
                violations.append(f"{archetype_id}: brief requires non-empty description_brief")
            if not isinstance(workout.get("tss"), (int, float)) or workout["tss"] <= 0:
                violations.append(f"{archetype_id}: brief requires positive tss")
            continue
        if not isinstance(levels, Mapping) or set(map(str, levels)) != LEVEL_KEYS:
            violations.append(f"{archetype_id}: leveled item must contain exactly levels 1-6")
            continue

        ordered_levels: list[Mapping[str, Any]] = []
        for level_key, level in levels.items():
            if not isinstance(level, Mapping):
                violations.append(f"{archetype_id} L{level_key}: level must be a mapping")
                continue
            ordered_levels.append(level)
            segments = level.get("segments", [])
            if not isinstance(segments, list):
                violations.append(f"{archetype_id} L{level_key}: segments must be a list")
                continue
            malformed_repeat = _validate_segment_schema(segments, archetype_id, str(level_key), violations)
            if malformed_repeat:
                continue
            try:
                leaves = _expanded_segments(segments)
            except ValueError as exc:
                violations.append(f"{archetype_id} L{level_key}: malformed repeat ({exc})")
                continue
            for segment in leaves:
                try:
                    band_for(segment.get("rpe"))
                except ValueError:
                    violations.append(f"{archetype_id} L{level_key}: invalid RPE band {segment.get('rpe')}")
                    break
            expected_duration = sum(
                segment.get("duration", 0)
                for segment in leaves
                if isinstance(segment.get("duration"), (int, float))
            )
            actual_duration = level.get("duration")
            if not isinstance(actual_duration, (int, float)) or abs(actual_duration - expected_duration) > 0.01:
                violations.append(f"{archetype_id} L{level_key}: duration does not equal expanded segments")
            stored_tss = level.get("tss")
            try:
                calculated_tss = estimate_tss(segments)
            except ValueError:
                calculated_tss = None
            if (
                not isinstance(stored_tss, (int, float))
                or calculated_tss is None
                or abs(stored_tss - calculated_tss) > calculated_tss * 0.15
            ):
                violations.append(f"{archetype_id} L{level_key}: tss is outside ±15% of formula")

            if workout.get("category") == "long_run" and actual_duration and actual_duration > 195 * 60:
                violations.append(f"{archetype_id} L{level_key}: long run exceeds 195 minutes")

            fueling_tier = level.get("fueling_tier")
            if fueling_tier not in FUELING_TIERS:
                violations.append(f"{archetype_id} L{level_key}: invalid or missing fueling_tier")
            elif isinstance(actual_duration, (int, float)):
                duration_min = actual_duration / 60
                if duration_min < 60 and fueling_tier != "none":
                    violations.append(f"{archetype_id} L{level_key}: workouts under 60 minutes require fueling_tier none")
                elif duration_min < 90 and fueling_tier != "optional":
                    violations.append(f"{archetype_id} L{level_key}: workouts 60-89 minutes require fueling_tier optional")
                elif duration_min >= 90 and fueling_tier not in {"z2_long", "dress_rehearsal"}:
                    violations.append(f"{archetype_id} L{level_key}: workouts 90 minutes or longer require long fueling")

        for index, (previous, current) in enumerate(zip(ordered_levels, ordered_levels[1:]), start=1):
            if previous == current:
                violations.append(f"{archetype_id} L{index}/L{index + 1}: adjacent levels must differ")
                continue
            previous_duration = previous.get("duration")
            current_duration = current.get("duration")
            try:
                duration_changed = abs(float(current_duration) - float(previous_duration)) > 120
                previous_work_count, previous_work_per_rep = _work_signature(previous.get("segments", []))
                current_work_count, current_work_per_rep = _work_signature(current.get("segments", []))
                work_changed = (
                    previous_work_count != current_work_count
                    or abs(previous_work_per_rep - current_work_per_rep) > 0.01
                )
            except (TypeError, ValueError):
                continue
            if duration_changed and work_changed:
                violations.append(f"{archetype_id} L{index}/L{index + 1}: adjacent levels change both duration and density")

    return violations


def _validate_segment_schema(
    segments: Iterable[Any], archetype_id: str, level_key: str, violations: list[str],
) -> bool:
    """Collect segment-type and repeat errors without letting malformed YAML abort validation."""
    malformed_repeat = False
    for segment in segments:
        if not isinstance(segment, Mapping):
            violations.append(f"{archetype_id} L{level_key}: segment must be a mapping")
            continue
        segment_type = segment.get("type")
        if segment_type not in SEGMENT_TYPES:
            violations.append(f"{archetype_id} L{level_key}: unknown segment type {segment_type!r}")
        if segment_type != "repeat":
            continue
        count, children = segment.get("count"), segment.get("of")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0 or not isinstance(children, list):
            violations.append(f"{archetype_id} L{level_key}: malformed repeat")
            malformed_repeat = True
            continue
        malformed_repeat = _validate_segment_schema(children, archetype_id, level_key, violations) or malformed_repeat
    return malformed_repeat


def _work_signature(segments: Iterable[Mapping[str, Any]]) -> tuple[int, float]:
    """Return active work-rep count and mean work duration for ladder checks.

    Explicit ``rest`` leaves are recovery padding, not work. Comparing the
    per-rep duration catches ladders that hide a work-interval change behind an
    unchanged expanded leaf count (for example, 3x7min becoming 3x8min).
    """
    work_leaves = [
        segment
        for segment in _expanded_segments(segments)
        if segment.get("type") not in {"warmup", "cooldown"}
        and segment.get("intensity_class") != "rest"
    ]
    if not work_leaves:
        return 0, 0.0
    durations = [float(segment["duration"]) for segment in work_leaves]
    return len(durations), sum(durations) / len(durations)
