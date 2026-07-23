#!/usr/bin/env python3
"""Build and reconcile the generic TrainingPeaks RUN-LIB exercise folder.

This module deliberately has no TrainingPeaks client: coaches post its output
through their logged-in browser tooling.  The payload is therefore safe to
generate locally and can be reconciled against a browser-exported folder dump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from run_archetypes import RUN_ARCHETYPES
from run_renderer import render_run_description
from run_structure_export import export_tp_structure


FOLDER_NAME = "GG Run | Workouts"
WORKOUT_TYPE_VALUE_ID = 3
_RECONCILE_FIELDS = (
    "workoutTypeValueId",
    "totalTimePlanned",
    "tssPlanned",
    "descriptionSha1",
    "structureDigest",
)


def _category_name(category_id: str) -> str:
    """Turn a stable category ID into the human-facing library title segment."""
    return category_id.replace("_", " ").title()


def _leaf_segments(segments: Iterable[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    """Yield segment leaves in authored order, expanding repeat blocks."""
    for segment in segments:
        if segment.get("type") == "repeat":
            yield from _leaf_segments(segment.get("of", []))
        else:
            yield segment


def _rpe_band(level_data: Mapping[str, Any]) -> str:
    """Return the session's highest active RPE band for its TP library name.

    Warm-up, cooldown, and authored rest steps are intentionally excluded.  A
    workout title should describe its meaningful work rather than its recovery
    bookends; if a workout has only recovery steps, its highest available band
    remains the truthful title band.
    """
    leaves = list(_leaf_segments(level_data["segments"]))
    active = [
        segment
        for segment in leaves
        if segment.get("type") not in {"warmup", "cooldown"}
        and segment.get("intensity_class") != "rest"
    ]
    candidates = active or leaves
    try:
        low, high = max(
            (segment["rpe"] for segment in candidates),
            key=lambda band: (band[1], band[0]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("A library level needs at least one valid RPE segment") from exc
    return f"{low}-{high}"


def _leveled_item_name(archetype: Mapping[str, Any], level: str, level_data: Mapping[str, Any]) -> str:
    """Return the versioned generic exercise-library name for one level."""
    duration_min = int(level_data["duration"] / 60)
    return (
        f"Run {_category_name(str(archetype['category']))} - "
        f"{archetype['display_name']} - {level} - {duration_min}min - RPE{_rpe_band(level_data)}"
    )


def _brief_item_name(archetype: Mapping[str, Any]) -> str:
    """Return the stable, unlevelled exercise-library name for a race brief."""
    return f"Run Race Day - {archetype['display_name']} - brief"


def generate_library_payload() -> dict[str, Any]:
    """Return all 80 browser-ready TP exercise-library item POST bodies.

    Leveled workouts include their normalized TP structure and duration in
    hours. Race briefs are deliberately description-only generic items: their
    athlete-specific placement duration is unknown at library-build time.
    """
    items: list[dict[str, Any]] = []
    for archetype_id, archetype in RUN_ARCHETYPES.items():
        if archetype.get("structure_exempt"):
            items.append({
                "itemName": _brief_item_name(archetype),
                "workoutTypeValueId": WORKOUT_TYPE_VALUE_ID,
                "tssPlanned": archetype["tss"],
                "description": render_run_description(archetype_id, None),
            })
            continue

        for level, level_data in archetype["levels"].items():
            items.append({
                "itemName": _leveled_item_name(archetype, level, level_data),
                "workoutTypeValueId": WORKOUT_TYPE_VALUE_ID,
                "totalTimePlanned": level_data["duration"] / 3600,
                "tssPlanned": level_data["tss"],
                "description": render_run_description(archetype_id, int(level)),
                "structure": export_tp_structure(archetype_id, level),
            })

    return {"folder_name": FOLDER_NAME, "items": items}


def _sha1(value: Any) -> str | None:
    return hashlib.sha1(value.encode("utf-8")).hexdigest() if isinstance(value, str) else None


def _structure_digest(structure: Any) -> dict[str, Any] | None:
    """Fingerprint TP steps by their count and the fields that affect execution."""
    if not isinstance(structure, Mapping):
        return None
    elements = structure.get("structure")
    if not isinstance(elements, list):
        return None
    steps: list[list[Any]] = []
    for element in elements:
        if not isinstance(element, Mapping):
            return None
        element_steps = element.get("steps")
        if not isinstance(element_steps, list) or len(element_steps) != 1 or not isinstance(element_steps[0], Mapping):
            return None
        step = element_steps[0]
        length = step.get("length")
        targets = step.get("targets")
        if not isinstance(length, Mapping) or not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], Mapping):
            return None
        target = targets[0]
        steps.append([length.get("value"), target.get("minValue"), target.get("maxValue"), step.get("intensityClass")])
    encoded = json.dumps(steps, separators=(",", ":"), ensure_ascii=True)
    return {"elementCount": len(steps), "sha1": hashlib.sha1(encoded.encode("utf-8")).hexdigest()}


def _reconciliation_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a full TP item into the fields that prove a faithful library dump."""
    return {
        "itemName": item.get("itemName"),
        "workoutTypeValueId": item.get("workoutTypeValueId"),
        "totalTimePlanned": item.get("totalTimePlanned"),
        "tssPlanned": item.get("tssPlanned"),
        "descriptionSha1": _sha1(item.get("description")),
        "structureDigest": _structure_digest(item.get("structure")),
    }


def expected_reconciliation_items() -> list[dict[str, Any]]:
    """Return expected reconciliation fingerprints, keyed by stable item name."""
    return [_reconciliation_item(item) for item in generate_library_payload()["items"]]


def _values_match(expected: Any, actual: Any) -> bool:
    """Compare numeric dump values without false mismatches from JSON floats."""
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and abs(float(expected) - float(actual)) < 1e-9
        )
    return expected == actual


def reconcile_library_dump(dump_items: Iterable[Mapping[str, Any]]) -> dict[str, list[Any]]:
    """Compare a TP folder dump to the expected 80 generic library items.

    ``dump_items`` must be full TP item objects containing ``itemName``,
    ``workoutTypeValueId``, ``totalTimePlanned``, ``tssPlanned``,
    ``description``, and (for leveled workouts) ``structure``. The returned
    report always contains ``missing``, ``extra``, and ``mismatched`` lists.
    """
    expected_by_name = {item["itemName"]: item for item in expected_reconciliation_items()}
    actual_by_name: dict[str, Mapping[str, Any]] = {}
    extra: list[str] = []

    for item in dump_items:
        if not isinstance(item, Mapping):
            raise ValueError("TP folder dump items must be objects")
        item_name = item.get("itemName")
        if not isinstance(item_name, str) or not item_name:
            raise ValueError("Each TP folder dump item requires a non-empty itemName")
        if item_name not in expected_by_name or item_name in actual_by_name:
            extra.append(item_name)
            continue
        actual_by_name[item_name] = _reconciliation_item(item)

    missing = sorted(set(expected_by_name) - set(actual_by_name))
    mismatched: list[dict[str, Any]] = []
    for item_name in sorted(set(expected_by_name) & set(actual_by_name)):
        expected, actual = expected_by_name[item_name], actual_by_name[item_name]
        fields = {
            field: {"expected": expected[field], "actual": actual.get(field)}
            for field in _RECONCILE_FIELDS
            if not _values_match(expected[field], actual.get(field))
        }
        if fields:
            mismatched.append({"itemName": item_name, "fields": fields})

    return {"missing": missing, "extra": sorted(extra), "mismatched": mismatched}


def _load_dump(path: Path) -> list[Mapping[str, Any]]:
    """Read and validate the documented JSON list dump format."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read JSON dump {path}: {exc}") from exc
    if not isinstance(document, list):
        raise ValueError("TP folder dump JSON must be a list of item objects")
    return document


def _print_report(report: Mapping[str, list[Any]]) -> None:
    """Print a stable, readable reconciliation report for the coach."""
    for section in ("missing", "extra", "mismatched"):
        print(f"{section}:")
        entries = report[section]
        if not entries:
            print("  none")
            continue
        for entry in entries:
            print(f"  {json.dumps(entry, sort_keys=True)}" if isinstance(entry, dict) else f"  {entry}")


def main(argv: list[str] | None = None) -> int:
    """Write a payload or reconcile a folder dump; return a shell exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--out", type=Path, help="write the browser-ready library payload JSON")
    actions.add_argument(
        "--reconcile",
        type=Path,
        metavar="DUMP_JSON",
        help=(
            "compare a JSON list of full TP items: itemName, workoutTypeValueId, "
            "totalTimePlanned, tssPlanned, description, and structure for leveled items"
        ),
    )
    args = parser.parse_args(argv)

    if args.out is not None:
        args.out.write_text(json.dumps(generate_library_payload(), indent=2) + "\n", encoding="utf-8")
        return 0

    try:
        report = reconcile_library_dump(_load_dump(args.reconcile))
    except ValueError as exc:
        parser.error(str(exc))
    _print_report(report)
    return 1 if any(report.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
