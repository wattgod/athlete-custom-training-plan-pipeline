#!/usr/bin/env python3
"""C3 of SPEC v2 (docs/SPEC_LIBRARY_SELECTION.md): the selector.

Queries the C1 normalized index (``tp_library_snapshot.load_index``) to
resolve a canonical block-builder slot -- {canonical_name, level, budget_min,
day_cap_min, role, phase, series_key, week_in_block, athlete_seed,
race_demands} -- to a curated TrainingPeaks library item.

This module does NOT call C2 (``tp_structure_to_zwo``); that converter is
internal-only (D4) and consumed downstream by C4 integration, not by the
selector itself.

Determinism: no ``random`` module anywhere in this file. All "random-feeling"
behavior (variety across athletes, series rotation) is hashlib-seeded on
caller-supplied identity so two calls with identical inputs are byte-identical.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Optional, Sequence

from tp_library_snapshot import load_index


# ---------------------------------------------------------------------------
# Routing table: canonical bike type (athletes/config/workout_library.yaml
# key) -> tuple of TP library_keys queried for that type. Built EXACTLY from
# the SPEC_LIBRARY_SELECTION.md C3 routing-table prose -- see the executor
# report for the judgment calls made where that prose was ambiguous.
# ---------------------------------------------------------------------------

# VO2max 30/30 + Thirty-Fifteens -> vo2_3030_micro
_VO2_3030_TYPES = ("VO2max 30/30", "Thirty-Fifteens")

# VO2max 40/20 + VO2max Steady Intervals + VO2max Extended -> vo2_classic, vo2_blends
_VO2_CLASSIC_TYPES = ("VO2max 40/20", "VO2max Steady Intervals", "VO2max Extended")

# Threshold Accumulation/Progressive/Steady/Touch -> threshold_intervals,
# threshold_sustained; "over-under class" -> threshold_floats_ou.
# JUDGMENT CALL: the spec names no canonical type called "over-under" (that
# name belongs to the OLDER nate_workout_generator archetype system, not this
# workout_library.yaml vocabulary). The only canonical types that plausibly
# constitute an "over-under class" are these same four Threshold types, so
# threshold_floats_ou is added as a third candidate library for all four
# rather than left permanently unrouted. Flagged for coach review.
_THRESHOLD_TYPES = (
    "Threshold Accumulation",
    "Threshold Progressive",
    "Threshold Steady",
    "Threshold Touch",
)

# Tempo* -> tempo
_TEMPO_TYPES = ("Tempo", "Tempo with Accelerations", "Tempo with Sprints")

# Endurance + focus variants (budget-split at query time, see
# _endurance_library_keys). JUDGMENT CALL: "focus variants" is read as the
# other 4 canonical types sharing workout_library.yaml's `category:
# endurance` -- Endurance Blocks, Endurance with Surges, Taper Burst
# Endurance, NP/IF Target -- alongside Endurance itself. Flagged for coach
# review.
_ENDURANCE_TYPES = (
    "Endurance",
    "Endurance Blocks",
    "Endurance with Surges",
    "Taper Burst Endurance",
    "NP/IF Target",
)

_ENDURANCE_BUDGET_SPLIT_MIN = 150  # minutes


def _base_routing_table() -> dict[str, tuple[str, ...]]:
    table: dict[str, tuple[str, ...]] = {}
    for name in _VO2_3030_TYPES:
        table[name] = ("vo2_3030_micro",)
    for name in _VO2_CLASSIC_TYPES:
        table[name] = ("vo2_classic", "vo2_blends")
    for name in _THRESHOLD_TYPES:
        table[name] = ("threshold_intervals", "threshold_sustained", "threshold_floats_ou")
    table["G-Spot"] = ("sweet_spot_gspot",)
    for name in _TEMPO_TYPES:
        table[name] = ("tempo",)
    table["SFR"] = ("torque_sfr",)
    table["Stomps"] = ("torque_stomps",)
    table["Cadence Work"] = ("torque_starts_cadence",)
    table["Microbursts"] = ("sprint_attacks",)
    for name in _ENDURANCE_TYPES:
        table[name] = ("endurance_z2_short", "endurance_z2_long", "endurance_with_work")
    # "Stars In Your Eyes" (category: anaerobic in workout_library.yaml) is
    # the natural home for the otherwise-unrouted anaerobic_capacity library;
    # sprint_attacks joins it under race_demands per T22 (see
    # _apply_race_demands_extras). JUDGMENT CALL, flagged for coach review.
    table["Stars In Your Eyes"] = ("anaerobic_capacity",)
    return table


ROUTING_TABLE: dict[str, tuple[str, ...]] = _base_routing_table()

# D5: composed/synthetic-only canonical types (race sims, tests, openers,
# rest days). The remaining types below the D5 line are canonical bike types
# with NO explicit routing in the spec's C3 prose and NOT named in D5 either
# -- they are out of the stated Phase 1 scope ("intensity slots, long rides,
# endurance fillers"). JUDGMENT CALL: declared synthetic-only rather than
# silently unrouted, to satisfy routing totality; flagged for coach review.
SYNTHETIC_ONLY: frozenset[str] = frozenset(
    {
        # D5 explicit
        "Race Simulation",
        "FTP Test",
        "Anaerobic Test",
        "Openers",
        "Rest Day",
        # Out of Phase 1 scope -- not named in the C3 routing prose or D5
        "VO2 Bookend",
        "Mixed Climbing",
        "Mixed Climbing Variations",
        "Mixed Intervals",
        "Buffer Workout",
        "Blended 30/30 and SFR",
        "Blended VO2max and G Spot",
        "Blended Endurance, Threshold, and Sprints",
    }
)

# Durability long-ride alternatives (T21): build/peak long-ride slots on an
# Endurance-family canonical type also draw these two libraries.
_DURABILITY_ALTERNATIVE_LIBRARIES = ("durability_long_sims", "durability_tired_intervals")
_LONG_RIDE_PHASES = ("build", "peak")

# T22: anaerobic_capacity + sprint_attacks join the rotation for the
# anaerobic-flavored canonical type when the slot's race_demands flags it.
_RACE_DEMANDS_EXTRA_LIBRARIES = ("anaerobic_capacity", "sprint_attacks")


def _is_long_ride_role(role: Optional[str]) -> bool:
    return bool(role) and "long" in role.lower()


def _endurance_library_keys(budget_min: float) -> tuple[str, ...]:
    if budget_min < _ENDURANCE_BUDGET_SPLIT_MIN:
        return ("endurance_z2_short", "endurance_with_work")
    return ("endurance_z2_long", "endurance_with_work")


def resolve_library_keys(slot: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the ordered, de-duplicated tuple of library_keys routed for a slot.

    Applies the static ROUTING_TABLE plus the three dynamic routing rules:
    Endurance budget split, T21 durability long-ride alternatives, and T22
    race-demands-gated anaerobic extras. Raises KeyError for a canonical_name
    that isn't in ROUTING_TABLE and isn't SYNTHETIC_ONLY -- that should never
    happen given the routing-totality test, so a KeyError here is a real bug.
    """
    canonical_name = slot["canonical_name"]
    if canonical_name in SYNTHETIC_ONLY:
        return ()
    if canonical_name not in ROUTING_TABLE:
        raise KeyError(f"canonical bike type {canonical_name!r} has no C3 routing and is not SYNTHETIC_ONLY")

    if canonical_name in _ENDURANCE_TYPES:
        keys = list(_endurance_library_keys(float(slot.get("budget_min") or 0)))
        phase = slot.get("phase")
        if _is_long_ride_role(slot.get("role")) and phase in _LONG_RIDE_PHASES:
            keys.extend(_DURABILITY_ALTERNATIVE_LIBRARIES)
    else:
        keys = list(ROUTING_TABLE[canonical_name])

    if canonical_name == "Stars In Your Eyes" and slot.get("race_demands"):
        keys.extend(_RACE_DEMANDS_EXTRA_LIBRARIES)

    # de-dup, preserve first-seen order
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return tuple(ordered)


# ---------------------------------------------------------------------------
# Deterministic hashing (no `random`)
# ---------------------------------------------------------------------------

def _seed_int(*parts: Any) -> int:
    """Deterministic non-negative integer from arbitrary hashable-ish parts."""
    joined = "\x1f".join("" if p is None else str(p) for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return int(digest, 16)


def _slot_identity(slot: Mapping[str, Any]) -> Any:
    """series_key when present, else a stable identity for the slot itself."""
    series_key = slot.get("series_key")
    if series_key:
        return series_key
    return (
        slot.get("canonical_name"),
        slot.get("role"),
        slot.get("phase"),
        slot.get("week_in_block"),
    )


def _rotate_index(pool_len: int, *seed_parts: Any) -> int:
    """Deterministic index into [0, pool_len) that spans the TOP HALF only.

    D7: rotation must span the top half of the RANKED pool (rank 0 = most
    dimension-rich) so different athletes draw different, equally-good
    workouts, while dimension-poor items at the tail stay unlikely.
    """
    if pool_len <= 1:
        return 0
    top_half = max(1, (pool_len + 1) // 2)
    return _seed_int(*seed_parts) % top_half


# ---------------------------------------------------------------------------
# Duration fit + level filtering
# ---------------------------------------------------------------------------

def _duration_bounds(budget_min: float, day_cap_min: Optional[float]) -> tuple[float, float]:
    lo = 0.85 * budget_min
    hi = 1.15 * budget_min
    if day_cap_min is not None:
        hi = min(hi, day_cap_min)
    return lo, hi


def _qualifying_pool(
    items: Sequence[Mapping[str, Any]], library_keys: Sequence[str], budget_min: float, day_cap_min: Optional[float]
) -> list[Mapping[str, Any]]:
    if not library_keys:
        return []
    lo, hi = _duration_bounds(budget_min, day_cap_min)
    key_set = set(library_keys)
    return [
        item
        for item in items
        if item["library_key"] in key_set
        and item.get("duration_min") is not None
        and lo <= item["duration_min"] <= hi
    ]


def _percentile(sorted_vals: Sequence[float], pct: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (pct / 100) * (len(sorted_vals) - 1)
    lo_idx = int(k)
    hi_idx = min(lo_idx + 1, len(sorted_vals) - 1)
    if lo_idx == hi_idx:
        return sorted_vals[lo_idx]
    frac = k - lo_idx
    return sorted_vals[lo_idx] + (sorted_vals[hi_idx] - sorted_vals[lo_idx]) * frac


# Level 1..6 -> center percentile 10..90 (p10, p26, p42, p58, p74, p90),
# generous +/-20pt half-width so the band leaves multiple candidates.
_IF_BAND_HALF_WIDTH_PCT = 20.0


def _if_band(level: int) -> tuple[float, float]:
    center = 10.0 + (level - 1) * 16.0
    lo = max(0.0, center - _IF_BAND_HALF_WIDTH_PCT)
    hi = min(100.0, center + _IF_BAND_HALF_WIDTH_PCT)
    return lo, hi


def _apply_level(pool: list[Mapping[str, Any]], level: int) -> list[Mapping[str, Any]]:
    """Apply D6/C3 level mapping. Soft preference, never hard-empties the pool.

    Mode A (>=50% of pool carries explicit_level): prefer exact
    explicit_level match, then +/-1 tolerance, else fall back to the full
    duration-qualified pool (the spec says "filter/prefer", read as a
    preference rather than a hard veto -- consistent with D7's "many good
    fits" ruling).
    Mode B (else): IF-percentile band around the level, generous width;
    falls back to the full pool if the band is empty (band sizing should
    never legitimately empty it).
    """
    if not pool:
        return pool

    with_level = [item for item in pool if item.get("explicit_level") is not None]
    if with_level and len(with_level) / len(pool) >= 0.5:
        exact = [item for item in pool if item.get("explicit_level") == level]
        if exact:
            return exact
        tolerant = [
            item
            for item in pool
            if item.get("explicit_level") is not None and abs(item["explicit_level"] - level) <= 1
        ]
        return tolerant or pool

    with_if = sorted(item["if_planned"] for item in pool if item.get("if_planned") is not None)
    if not with_if:
        return pool
    lo_pct, hi_pct = _if_band(level)
    lo_val = _percentile(with_if, lo_pct)
    hi_val = _percentile(with_if, hi_pct)
    banded = [item for item in pool if item.get("if_planned") is not None and lo_val <= item["if_planned"] <= hi_val]
    return banded or pool


def _rank(pool: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Dimension-rich outranks flat (D6); item_id breaks ties deterministically."""
    return sorted(
        pool,
        key=lambda item: (-item["dimension_score"], -(item.get("if_planned") or 0.0), item["item_id"]),
    )


def _to_resolution(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "item_id": item["item_id"],
        "name_base": item["name_base"],
        "library_key": item["library_key"],
        "duration_min": item["duration_min"],
        "tss": item["tss"],
        "if_planned": item["if_planned"],
        "structure": item["structure"],
        "description": item["description"],
        "dimension_score": item["dimension_score"],
    }


def _family_key(item: Mapping[str, Any]) -> str:
    return f"{item['library_key']}||{item['name_base']}"


# ---------------------------------------------------------------------------
# select()
# ---------------------------------------------------------------------------

def select(
    slot: Mapping[str, Any],
    series_state: Optional[dict[str, Any]] = None,
    index: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Resolve a canonical slot to a curated TP library item, or None (D9).

    ``series_state`` is the caller's dict, threaded through across a plan's
    calls (D8). It is mutated in place to record/advance per-series state;
    pass a fresh {} (or None, treated as a scratch dict) for a non-series
    slot or a slot's first call. Never raises for "no fit" -- returns None.
    """
    index = index if index is not None else load_index()
    items = index["items"]

    canonical_name = slot["canonical_name"]
    if canonical_name in SYNTHETIC_ONLY:
        return None

    library_keys = resolve_library_keys(slot)
    budget_min = float(slot.get("budget_min") or 0)
    day_cap_min = slot.get("day_cap_min")

    pool = _qualifying_pool(items, library_keys, budget_min, day_cap_min)
    if not pool:
        return None

    series_key = slot.get("series_key")
    if series_state is not None and series_key and series_key in series_state:
        resolution = _select_series_continuation(slot, series_state, index, pool)
        if resolution is not None:
            return resolution
        # Series continuation had nothing to progress to (e.g. ladder top,
        # or no qualifying candidate) -- loud fallback, per D9.
        return None

    level = int(slot.get("level") or 1)
    leveled_pool = _apply_level(pool, level)
    ranked = _rank(leveled_pool)
    if not ranked:
        return None

    idx = _rotate_index(len(ranked), slot.get("athlete_seed"), _slot_identity(slot))
    chosen = ranked[idx]

    if series_state is not None and series_key:
        _record_series_state(series_state, series_key, chosen, index)

    return _to_resolution(chosen)


def _select_series_continuation(
    slot: Mapping[str, Any],
    series_state: dict[str, Any],
    index: Mapping[str, Any],
    pool: Sequence[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    state = series_state[slot["series_key"]]
    qualifying_ids = {item["item_id"] for item in pool}

    if not state.get("singleton") and state.get("family_key") in index["families"]:
        family = index["families"][state["family_key"]]
        current_rung = state.get("rung")
        ladder = sorted(family["ladder"], key=lambda entry: entry["rung"])
        if current_rung is not None:
            candidates = [entry for entry in ladder if entry["rung"] > current_rung]
        else:
            candidates = list(ladder)
        # Prefer the next rung that's still duration-qualified for this
        # slot; if none qualify, fall back to the next rung regardless
        # (the family ladder itself is the strongest series-coherence
        # signal -- D8 -- so honor it even if duration drifted slightly).
        in_pool = [entry for entry in candidates if entry["item_id"] in qualifying_ids]
        next_entry = (in_pool or candidates)
        if next_entry:
            chosen_id = next_entry[0]["item_id"]
            chosen_item = _find_item(index, chosen_id)
            if chosen_item is not None:
                _record_series_state(series_state, slot["series_key"], chosen_item, index)
                return _to_resolution(chosen_item)
        # Ladder exhausted (top rung already reached) -- degrade to
        # singleton-style same-library nearest-higher-IF continuation.

    return _select_singleton_continuation(slot, series_state, index, pool)


def _select_singleton_continuation(
    slot: Mapping[str, Any],
    series_state: dict[str, Any],
    index: Mapping[str, Any],
    pool: Sequence[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    state = series_state[slot["series_key"]]
    library_key = state["library_key"]
    last_if = state.get("if_planned")

    same_library = [item for item in pool if item["library_key"] == library_key]
    if last_if is not None:
        higher = [item for item in same_library if item.get("if_planned") is not None and item["if_planned"] > last_if]
    else:
        higher = [item for item in same_library if item.get("if_planned") is not None]

    if not higher:
        # No strictly-higher-IF candidate within the duration-qualified
        # pool for this slot -- try the same library ignoring duration fit
        # (series coherence over strict duration precision) before giving up.
        all_in_library = [item for item in index["items"] if item["library_key"] == library_key]
        if last_if is not None:
            higher = [
                item for item in all_in_library if item.get("if_planned") is not None and item["if_planned"] > last_if
            ]
        else:
            higher = [item for item in all_in_library if item.get("if_planned") is not None]
        if not higher:
            return None

    # Nearest strictly-higher IF (D8 monotone-increasing).
    higher.sort(key=lambda item: (item["if_planned"], item["item_id"]))
    chosen_item = higher[0]
    _record_series_state(series_state, slot["series_key"], chosen_item, index)
    return _to_resolution(chosen_item)


def _record_series_state(
    series_state: dict[str, Any], series_key: str, item: Mapping[str, Any], index: Mapping[str, Any]
) -> None:
    family_key = _family_key(item)
    family = index["families"].get(family_key)
    singleton = bool(family) and len(family["members"]) == 1
    rung = None
    if family:
        for rung_entry in family["ladder"]:
            if rung_entry["item_id"] == item["item_id"]:
                rung = rung_entry["rung"]
                break
    series_state[series_key] = {
        "family_key": family_key,
        "library_key": item["library_key"],
        "item_id": item["item_id"],
        "rung": rung,
        "if_planned": item.get("if_planned"),
        "singleton": singleton,
    }


def _find_item(index: Mapping[str, Any], item_id: Any) -> Optional[Mapping[str, Any]]:
    for item in index["items"]:
        if item["item_id"] == item_id:
            return item
    return None


# ---------------------------------------------------------------------------
# refit()
# ---------------------------------------------------------------------------

def refit(
    slot: Mapping[str, Any],
    series_state: Optional[dict[str, Any]] = None,
    index: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Trim-step resolution: same routing/series constraints, next-shorter fit.

    ``slot['budget_min']`` should already be the caller's reduced (trimmed)
    budget. Honors an active series' locked family/library (same coherence
    rule as ``select``'s continuation path) so trimming doesn't jump the
    athlete to an unrelated workout mid-series. Returns None (never raises)
    when nothing qualifies -- D9's loud fallback.
    """
    index = index if index is not None else load_index()
    items = index["items"]

    canonical_name = slot["canonical_name"]
    if canonical_name in SYNTHETIC_ONLY:
        return None

    library_keys = resolve_library_keys(slot)
    budget_min = float(slot.get("budget_min") or 0)
    day_cap_min = slot.get("day_cap_min")

    pool = _qualifying_pool(items, library_keys, budget_min, day_cap_min)
    if not pool:
        return None

    series_key = slot.get("series_key")
    if series_state is not None and series_key and series_key in series_state:
        state = series_state[series_key]
        constrained = [item for item in pool if item["library_key"] == state.get("library_key")]
        if not state.get("singleton") and state.get("family_key"):
            family_constrained = [item for item in constrained if _family_key(item) == state["family_key"]]
            if family_constrained:
                constrained = family_constrained
        if constrained:
            pool = constrained

    # "Next-shorter qualifying candidate": largest duration_min that still
    # fits the (already-trimmed) budget window, i.e. the closest fit from
    # below; dimension_score desc then item_id break ties deterministically.
    pool_sorted = sorted(
        pool,
        key=lambda item: (-item["duration_min"], -item["dimension_score"], item["item_id"]),
    )
    chosen = pool_sorted[0]

    if series_state is not None and series_key:
        _record_series_state(series_state, series_key, chosen, index)

    return _to_resolution(chosen)
