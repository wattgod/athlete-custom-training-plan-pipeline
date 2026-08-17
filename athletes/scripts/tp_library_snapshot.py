#!/usr/bin/env python3
"""Build and reconcile the normalized index of the coach's curated TP libraries.

C1 of SPEC v2 (docs/SPEC_LIBRARY_SELECTION.md): the pipeline stops synthesizing
its own archetypes for standard training sessions and instead SELECTS from the
coach's 24 "GG |" bike libraries in TrainingPeaks. This module is the read-only
snapshot step: it turns the raw browser-exported dump into a normalized,
selectable item index that C3 (the selector, not built here) will query.

Input: the raw dump (a JSON object of {library_key: {libraryId, items: [...]}},
pulled from the coach's browser session -- no TP credentials belong in this
repo; refreshing the dump is a manual browser-session job). Output: a gzip'd
JSON index at ``athletes/config/tp_library_index.json.gz``.

Name parsing is RIGHT-ANCHORED, not a naive dash-split: 73% of names have
exactly 4 " - "-separated segments, but ~4% are unparseable and several real
shapes (5-dash names, category+modifier names with no internal dash, bare
names like "Just Ride") break a naive split. See ``parse_item_name``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_RAW_PATH = Path(
    "/Users/mattirowe/Downloads/guillermo-romero-delivery/gg_tp_library_full.json"
)
DEFAULT_INDEX_PATH = Path(__file__).parent.parent / "config" / "tp_library_index.json.gz"

# workoutTypeId 2 == Bike in this TP account's taxonomy (verified against the
# real dump: 1,593 of 1,631 items carry it; the remaining 38 are run/MTB/other
# non-bike types 0, 8, 10, 13 and are excluded outright).
BIKE_WORKOUT_TYPE_ID = 2

# Cadence targets live on structure steps as a second target entry with this
# unit (a second target alongside the power target on the same step).
CADENCE_TARGET_UNIT = "roundOrStridePerMinute"

# Leading category words observed across the real dump's item names, longest
# phrase first so "Sweet Spot"/"Race Sim"/"Group Ride" match before any
# shorter prefix could. This is a GLOBAL vocabulary (not scoped per
# library_key): several libraries file items under another library's category
# word (e.g. "Threshold"-named items appear inside sweet_spot_intervals), so a
# strict per-library vocabulary would under-strip. Judgment call -- flagged in
# the executor report.
CATEGORY_VOCAB = (
    "Sweet Spot",
    "Race Sim",
    "Group Ride",
    "VO2max",
    "Torque",
    "Endurance",
    "Threshold",
    "Durability",
    "Specialty",
    "Anaerobic",
    "Tempo",
    "Sprint",
    "Recovery",
)

# Right-anchored token patterns, applied in order: RPE, then duration, then
# level/ref. Each is optional; whatever token isn't present simply isn't
# stripped, and parsing stops early (the remaining text -- possibly the whole
# original name -- becomes name_base). Verified 100% of names that have an
# RPE suffix also have a duration suffix immediately before it (1,508/1,508
# in the real dump), so these two never appear independently.
_RPE_RE = re.compile(r"\s*-?\s*RPE\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*\Z")
_DURATION_RE = re.compile(r"\s*-\s*(\d+)\s*m(?:in)?\s*\Z")
_LEVEL_RE = re.compile(r"\s*-\s*(ref|[1-6])\s*\Z")

# Dimension-cue keyword classes (D6). Deliberately coarse coach-level
# heuristics, not NLP -- "climb"/"descend" are filed under terrain_surface
# since climbing is a terrain feature in these descriptions. Judgment call --
# flagged in the executor report.
_DIMENSION_PATTERNS: dict[str, re.Pattern[str]] = {
    "cadence_rpm": re.compile(r"\bcadence\b|\brpm\b", re.IGNORECASE),
    "position_posture": re.compile(r"\bposition\b|\bhoods?\b|\bdrops\b|\baero\b", re.IGNORECASE),
    "terrain_surface": re.compile(
        r"\bterrain\b|\bgravel\b|\bdirt\b|\bpavement\b|\bsurface\b|\bclimb(?:ing|s)?\b|\bdescend(?:ing|s)?\b",
        re.IGNORECASE,
    ),
    "drill_technique": re.compile(r"\bdrills?\b|\btechnique\b|\bskills?\b|\bcorner(?:ing|s)?\b", re.IGNORECASE),
    "standing_seated": re.compile(r"\bstand(?:ing|s)?\b|\bseated\b", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------

def _strip_leading_category(remainder: str) -> str:
    """Strip a leading category word/phrase from a right-stripped remainder.

    Two shapes appear in the real data: the category is its own leading
    " - "-separated segment ("Torque - Stutter Step" -> "Stutter Step"), or
    the category word is glued to a modifier with no dash ("Endurance with
    Surges" -> "with Surges"). Both are handled; if neither matches, the
    remainder passes through unchanged (this is what makes bare names like
    "Just Ride" fall back to name_base = full name).
    """
    first_segment = remainder.split(" - ", 1)[0]
    if first_segment in CATEGORY_VOCAB:
        rest = remainder[len(first_segment):]
        return rest.lstrip(" -")
    for category in CATEGORY_VOCAB:
        if remainder.startswith(category + " "):
            return remainder[len(category):].lstrip(" -")
    return remainder


def parse_item_name(name: str) -> dict[str, Any]:
    """Right-anchor-parse a raw TP item name into name_base/explicit_level/rpe_text.

    From the right: strip an optional RPE token, then an optional NNmin/NNm
    token, then an optional bare 'ref' or digit 1-6 (captured as
    explicit_level -- only 1-6 counts; other digits, e.g. an hour-count like
    "- 7 -" in "Endurance - (MxHr) - 7 - 180min", are NOT a level token and
    stay embedded in name_base). Then strip a leading category word. The
    remainder -- which may itself contain dashes -- is name_base. Names with
    none of these tokens (~5% of the real dump) fall back to name_base = the
    full original name and stay selectable as singletons.
    """
    remainder = name
    rpe_text = None
    match = _RPE_RE.search(remainder)
    if match:
        rpe_text = match.group(1) if match.group(2) is None else f"{match.group(1)}-{match.group(2)}"
        remainder = remainder[: match.start()]

    match = _DURATION_RE.search(remainder)
    if match:
        remainder = remainder[: match.start()]

    explicit_level = None
    match = _LEVEL_RE.search(remainder)
    if match:
        token = match.group(1)
        if token != "ref":
            explicit_level = int(token)
        remainder = remainder[: match.start()]

    name_base = _strip_leading_category(remainder)
    return {"name_base": name_base, "explicit_level": explicit_level, "rpe_text": rpe_text}


# ---------------------------------------------------------------------------
# Dimension scoring (D6)
# ---------------------------------------------------------------------------

def classify_dimension_cues(description: str | None) -> set[str]:
    """Return the distinct dimension-cue classes present in a description."""
    if not description:
        return set()
    return {name for name, pattern in _DIMENSION_PATTERNS.items() if pattern.search(description)}


def has_cadence_targets(structure: Mapping[str, Any] | None) -> bool:
    """Return True if any structure step carries a roundOrStridePerMinute target."""
    if not structure:
        return False
    for element in structure.get("structure", []) or []:
        for step in element.get("steps", []) or []:
            for target in step.get("targets", []) or []:
                if target.get("unit") == CADENCE_TARGET_UNIT:
                    return True
    return False


def compute_dimension_score(description: str | None, structure: Mapping[str, Any] | None) -> int:
    """Count of distinct description dimension-cue classes, plus 1 if the
    structure carries a cadence target (D6). Max possible score is 6."""
    return len(classify_dimension_cues(description)) + (1 if has_cadence_targets(structure) else 0)


# ---------------------------------------------------------------------------
# IF computation
# ---------------------------------------------------------------------------

def compute_if_planned(tss: float | None, hours: float | None, existing: float | None) -> float | None:
    """Return the item's IF, computed from TSS/hours when the dump omits it.

    Standard relationship TSS = 100 * hours * IF^2, verified against the real
    dump's 1,410 items that carry both tssPlanned and ifPlanned (mean abs
    error 0.0004). Returns None when TSS or hours aren't available to compute
    from (67 real items have neither -- unstructured "coach's discretion"
    briefs).
    """
    if existing is not None:
        return existing
    if tss is None or not hours:
        return None
    return (tss / (100 * hours)) ** 0.5


# ---------------------------------------------------------------------------
# Item selection + exclusion
# ---------------------------------------------------------------------------

def _is_bike(item: Mapping[str, Any]) -> bool:
    return item.get("workoutTypeId") == BIKE_WORKOUT_TYPE_ID


def _has_usable_structure(item: Mapping[str, Any]) -> bool:
    structure = item.get("structure")
    return bool(structure and structure.get("structure"))


def load_raw_dump(path: Path) -> dict[str, Any]:
    """Read and validate the documented {library_key: {libraryId, items}} dump format."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read raw TP library dump {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Raw TP library dump JSON must be an object of {library_key: {...}}")
    return document


def _normalize_extra_exclusions(extra_exclusions: Any) -> dict[int, str]:
    """Normalize the extra_exclusions hook into {item_id: reason}.

    Accepts a mapping already in that shape, or an iterable of ints / of
    {"item_id": ..., "reason": ...} objects (the JSON sidecar shape loaded by
    --extra-exclusions on the CLI).
    """
    if extra_exclusions is None:
        return {}
    if isinstance(extra_exclusions, Mapping):
        return {int(item_id): str(reason) for item_id, reason in extra_exclusions.items()}
    normalized: dict[int, str] = {}
    for entry in extra_exclusions:
        if isinstance(entry, Mapping):
            normalized[int(entry["item_id"])] = str(entry.get("reason", "extra_exclusion"))
        else:
            normalized[int(entry)] = "extra_exclusion"
    return normalized


def build_items(
    raw: Mapping[str, Any], extra_exclusions: Any = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Turn the raw dump into (selectable items, exclusions report).

    Exclusion order: non-bike (workoutTypeId != 2), then structureless bike
    (bike but no usable ``structure.structure``), then the extra_exclusions
    hook (a documented escape valve for C2 round-trip failures discovered
    downstream -- this module never re-parses to apply them, it simply drops
    matching item_ids and logs why).
    """
    extra_exclusion_reasons = _normalize_extra_exclusions(extra_exclusions)

    items: list[dict[str, Any]] = []
    excluded_non_bike: list[dict[str, Any]] = []
    excluded_structureless: list[dict[str, Any]] = []
    excluded_extra: list[dict[str, Any]] = []

    for library_key, library in raw.items():
        for raw_item in library.get("items", []):
            item_id = raw_item.get("exerciseLibraryItemId")
            name_raw = raw_item.get("itemName", "")

            if not _is_bike(raw_item):
                excluded_non_bike.append({"item_id": item_id, "library_key": library_key, "name_raw": name_raw})
                continue
            if not _has_usable_structure(raw_item):
                excluded_structureless.append(
                    {"item_id": item_id, "library_key": library_key, "name_raw": name_raw}
                )
                continue
            if item_id in extra_exclusion_reasons:
                excluded_extra.append(
                    {
                        "item_id": item_id,
                        "library_key": library_key,
                        "name_raw": name_raw,
                        "reason": extra_exclusion_reasons[item_id],
                    }
                )
                continue

            parsed = parse_item_name(name_raw)
            hours = raw_item.get("totalTimePlanned")
            tss = raw_item.get("tssPlanned")
            structure = raw_item.get("structure")
            description = raw_item.get("description")

            items.append(
                {
                    "item_id": item_id,
                    "library_key": library_key,
                    "name_raw": name_raw,
                    "name_base": parsed["name_base"],
                    "explicit_level": parsed["explicit_level"],
                    "duration_min": round(hours * 60) if hours else None,
                    "tss": tss,
                    "if_planned": compute_if_planned(tss, hours, raw_item.get("ifPlanned")),
                    "rpe_text": parsed["rpe_text"],
                    "dimension_score": compute_dimension_score(description, structure),
                    "has_cadence_targets": has_cadence_targets(structure),
                    "structure": structure,
                    "description": description,
                    "workout_type_id": raw_item.get("workoutTypeId"),
                }
            )

    exclusions = {
        "non_bike": {"count": len(excluded_non_bike), "items": excluded_non_bike},
        "structureless_bike": {"count": len(excluded_structureless), "items": excluded_structureless},
        "extra": {"count": len(excluded_extra), "items": excluded_extra},
    }
    return items, exclusions


# ---------------------------------------------------------------------------
# Family grouping (D8)
# ---------------------------------------------------------------------------

def _family_key(item: Mapping[str, Any]) -> str:
    return f"{item['library_key']}||{item['name_base']}"


def build_family_index(items: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group selectable items into families by (library_key, name_base) and
    build each family's ladder (D8): rung = explicit_level when every member
    that's ranked carries one, else rank by if_planned ascending. Members
    lacking a usable rung key (no explicit_level in an explicit-level family,
    or no if_planned in an IF-ranked family) are still listed but excluded
    from the ladder.
    """
    members: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        members.setdefault(_family_key(item), []).append(item)

    families: dict[str, dict[str, Any]] = {}
    for key, family_members in members.items():
        library_key = family_members[0]["library_key"]
        name_base = family_members[0]["name_base"]
        has_any_explicit_level = any(m["explicit_level"] is not None for m in family_members)

        ladder: list[dict[str, Any]] = []
        if has_any_explicit_level:
            rung_basis = "explicit_level"
            ranked = sorted(
                (m for m in family_members if m["explicit_level"] is not None),
                key=lambda m: m["explicit_level"],
            )
            for member in ranked:
                ladder.append(
                    {
                        "rung": member["explicit_level"],
                        "item_id": member["item_id"],
                        "explicit_level": member["explicit_level"],
                        "if_planned": member["if_planned"],
                    }
                )
        else:
            rung_basis = "if_rank"
            ranked = sorted(
                (m for m in family_members if m["if_planned"] is not None),
                key=lambda m: m["if_planned"],
            )
            for rung, member in enumerate(ranked, start=1):
                ladder.append(
                    {
                        "rung": rung,
                        "item_id": member["item_id"],
                        "explicit_level": member["explicit_level"],
                        "if_planned": member["if_planned"],
                    }
                )

        families[key] = {
            "library_key": library_key,
            "name_base": name_base,
            "members": [m["item_id"] for m in family_members],
            "ladder": ladder,
            "rung_basis": rung_basis,
        }
    return families


def family_stats(families: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    family_count = len(families)
    sizes = [len(family["members"]) for family in families.values()]
    singleton_count = sum(1 for size in sizes if size == 1)
    return {
        "family_count": family_count,
        "singleton_count": singleton_count,
        "singleton_share": (singleton_count / family_count) if family_count else 0.0,
        "max_family_size": max(sizes) if sizes else 0,
    }


# ---------------------------------------------------------------------------
# Index build / write / reconcile
# ---------------------------------------------------------------------------

def build_index(raw_path: Path, extra_exclusions: Any = None) -> dict[str, Any]:
    """Build the full normalized index document from a raw dump path."""
    raw = load_raw_dump(raw_path)
    items, exclusions = build_items(raw, extra_exclusions=extra_exclusions)
    families = build_family_index(items)

    per_library_counts: dict[str, int] = {}
    for item in items:
        per_library_counts[item["library_key"]] = per_library_counts.get(item["library_key"], 0) + 1

    explicit_level_count = sum(1 for item in items if item["explicit_level"] is not None)
    dimension_scores = [item["dimension_score"] for item in items]

    return {
        "source_path": str(raw_path),
        "counts": {
            "selectable": len(items),
            "per_library": per_library_counts,
            "explicit_level_coverage": (explicit_level_count / len(items)) if items else 0.0,
            "dimension_score_distribution": {
                "min": min(dimension_scores) if dimension_scores else 0,
                "median": statistics.median(dimension_scores) if dimension_scores else 0,
                "max": max(dimension_scores) if dimension_scores else 0,
            },
        },
        "exclusions": exclusions,
        "family_stats": family_stats(families),
        "families": families,
        "items": items,
    }


def write_index(index: Mapping[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(index, indent=2, sort_keys=True).encode("utf-8")
    with gzip.open(out_path, "wb") as handle:
        handle.write(payload)


def read_index(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def reconcile(raw_path: Path, index_path: Path, extra_exclusions: Any = None) -> dict[str, Any]:
    """Compare a fresh raw dump against a previously built index and report drift.

    Mirrors the build_run_tp_library reconcile pattern: rebuild the expected
    document from the fresh source, diff it against the on-disk index by
    item_id, and report added/removed/changed items so a refreshed browser
    dump can be reviewed before it's committed.
    """
    fresh = build_index(raw_path, extra_exclusions=extra_exclusions)
    existing = read_index(index_path)

    fresh_by_id = {item["item_id"]: item for item in fresh["items"]}
    existing_by_id = {item["item_id"]: item for item in existing["items"]}

    added = sorted(set(fresh_by_id) - set(existing_by_id))
    removed = sorted(set(existing_by_id) - set(fresh_by_id))

    changed: list[dict[str, Any]] = []
    tracked_fields = (
        "name_base",
        "explicit_level",
        "duration_min",
        "tss",
        "if_planned",
        "dimension_score",
        "has_cadence_targets",
    )
    for item_id in sorted(set(fresh_by_id) & set(existing_by_id)):
        fresh_item, existing_item = fresh_by_id[item_id], existing_by_id[item_id]
        diffs = {
            field: {"old": existing_item.get(field), "new": fresh_item.get(field)}
            for field in tracked_fields
            if existing_item.get(field) != fresh_item.get(field)
        }
        if diffs:
            changed.append({"item_id": item_id, "fields": diffs})

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "family_count_old": existing["family_stats"]["family_count"],
        "family_count_new": fresh["family_stats"]["family_count"],
    }


# ---------------------------------------------------------------------------
# Downstream loader API (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _load_index_cached(path_str: str) -> dict[str, Any]:
    return read_index(Path(path_str))


def load_index(path: Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    """Return the built index (items + families), cached per resolved path.

    Downstream code (C3, the selector) should use this rather than reading
    the gzip file directly. Returns the same dict shape written by
    ``build_index``/``write_index``: ``items`` (list) and ``families`` (dict
    keyed "library_key||name_base").
    """
    return _load_index_cached(str(Path(path).resolve()))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_extra_exclusions_file(path: Path | None) -> Any:
    if path is None:
        return None
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return document


def _print_summary(index: Mapping[str, Any]) -> None:
    counts = index["counts"]
    stats = index["family_stats"]
    print(f"selectable items: {counts['selectable']}")
    print("per-library counts:")
    for library_key, count in sorted(counts["per_library"].items()):
        print(f"  {library_key}: {count}")
    print(f"excluded non-bike: {index['exclusions']['non_bike']['count']}")
    print(f"excluded structureless bike: {index['exclusions']['structureless_bike']['count']}")
    print(f"excluded extra: {index['exclusions']['extra']['count']}")
    print(f"families: {stats['family_count']}")
    print(f"singleton share: {stats['singleton_share']:.1%}")
    print(f"explicit-level coverage: {counts['explicit_level_coverage']:.1%}")
    dist = counts["dimension_score_distribution"]
    print(f"dimension_score min/median/max: {dist['min']}/{dist['median']}/{dist['max']}")


def _print_reconcile_report(report: Mapping[str, Any]) -> None:
    for section in ("added", "removed", "changed"):
        print(f"{section}:")
        entries = report[section]
        if not entries:
            print("  none")
            continue
        for entry in entries:
            print(f"  {json.dumps(entry, sort_keys=True)}" if isinstance(entry, dict) else f"  {entry}")
    print(f"family_count: {report['family_count_old']} -> {report['family_count_new']}")


def main(argv: list[str] | None = None) -> int:
    """Build (default) or reconcile (--reconcile) the TP library snapshot index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "raw_path",
        nargs="?",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help=f"path to the raw TP library dump (default: {DEFAULT_RAW_PATH})",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_INDEX_PATH, help="index path: write target, or reconcile target"
    )
    parser.add_argument(
        "--extra-exclusions",
        type=Path,
        default=None,
        help="JSON sidecar: a list of item_ids, or of {item_id, reason} objects, to exclude "
        "(e.g. C2 structure round-trip failures discovered downstream)",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="compare a fresh raw dump against the existing index at --out and print drift",
    )
    args = parser.parse_args(argv)

    extra_exclusions = _load_extra_exclusions_file(args.extra_exclusions)

    if args.reconcile:
        report = reconcile(args.raw_path, args.out, extra_exclusions=extra_exclusions)
        _print_reconcile_report(report)
        return 1 if (report["added"] or report["removed"] or report["changed"]) else 0

    index = build_index(args.raw_path, extra_exclusions=extra_exclusions)
    write_index(index, args.out)
    _print_summary(index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
