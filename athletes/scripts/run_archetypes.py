#!/usr/bin/env python3
"""Registry and validation helpers for the standalone run workout library."""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml


LIBRARY_PATH = Path(__file__).resolve().parents[1] / "config" / "run_workout_library.yaml"
LEVEL_KEYS = {"1", "2", "3", "4", "5", "6"}
RPE_TO_IF = {
    (1, 2): 0.55,
    (2, 3): 0.62,
    (3, 4): 0.70,
    (4, 5): 0.78,
    (5, 6): 0.83,
    (6, 7): 0.88,
    (7, 8): 0.93,
    (8, 9): 1.00,
    (9, 10): 1.05,
}
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


def _expanded_segments(segments: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Unroll nested repeat blocks into leaf segments."""
    expanded = []
    for segment in segments:
        if segment.get("type") == "repeat":
            count = segment.get("count", 0)
            children = segment.get("of", [])
            if isinstance(count, int) and count >= 0 and isinstance(children, list):
                for _ in range(count):
                    expanded.extend(_expanded_segments(children))
            continue
        expanded.append(segment)
    return expanded


def calculate_tss(segments: Iterable[Mapping[str, Any]]) -> float:
    """Calculate rTSS from normalized, seconds-based leaf or repeat segments."""
    total = 0.0
    for segment in _expanded_segments(segments):
        rpe = tuple(segment.get("rpe", ()))
        intensity_factor = RPE_TO_IF.get(rpe)
        duration = segment.get("duration")
        if intensity_factor is None or not isinstance(duration, (int, float)):
            continue
        total += (duration / 3600) * intensity_factor ** 2 * 100
    return total


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
        if display_name in seen_names:
            violations.append(f"Duplicate display name: {display_name}")
        if isinstance(display_name, str):
            seen_names.add(display_name)

        match = _ID_PATTERN.fullmatch(archetype_id)
        if match is None or match.group(1) != workout.get("category"):
            violations.append(f"{archetype_id}: ID must match run.<category>.<slug>")
        if workout.get("sport") != "run":
            violations.append(f"{archetype_id}: sport must be 'run'")

        levels = workout.get("levels")
        if levels is None:
            if not workout.get("structure_exempt"):
                violations.append(f"{archetype_id}: unleveled item must be structure_exempt")
            continue
        if not isinstance(levels, Mapping) or set(map(str, levels)) != LEVEL_KEYS:
            violations.append(f"{archetype_id}: leveled item must contain exactly levels 1-6")
            continue

        for level_key, level in levels.items():
            if not isinstance(level, Mapping):
                violations.append(f"{archetype_id} L{level_key}: level must be a mapping")
                continue
            segments = level.get("segments", [])
            if not isinstance(segments, list):
                violations.append(f"{archetype_id} L{level_key}: segments must be a list")
                continue
            leaves = _expanded_segments(segments)
            for segment in leaves:
                if tuple(segment.get("rpe", ())) not in RPE_TO_IF:
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
            calculated_tss = calculate_tss(segments)
            if not isinstance(stored_tss, (int, float)) or abs(stored_tss - calculated_tss) > calculated_tss * 0.15:
                violations.append(f"{archetype_id} L{level_key}: tss is outside ±15% of formula")

            if workout.get("category") == "long_run" and actual_duration and actual_duration > 195 * 60:
                violations.append(f"{archetype_id} L{level_key}: long run exceeds 195 minutes")

    return violations
