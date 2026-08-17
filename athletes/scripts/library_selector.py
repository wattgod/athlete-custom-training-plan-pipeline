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
    """series_key when present, else a stable identity for the slot itself.

    R3(c) fix wave: the non-series identity is extended with
    (plan_week, day) -- without it, two different weeks sharing the same
    (canonical_name, role, phase, week_in_block) tuple (e.g. week_in_block
    resets every block) would rotate to the identical index and draw the
    identical item, which is exactly the variety bug this fix wave closes.
    """
    series_key = slot.get("series_key")
    if series_key:
        return series_key
    return (
        slot.get("canonical_name"),
        slot.get("role"),
        slot.get("phase"),
        slot.get("week_in_block"),
        slot.get("plan_week"),
        slot.get("day"),
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
    items: Sequence[Mapping[str, Any]], library_keys: Sequence[str], budget_min: float, day_cap_min: Optional[float],
    *, slot: Optional[Mapping[str, Any]] = None,
) -> list[Mapping[str, Any]]:
    """``slot`` is optional and keyword-only so existing positional callers
    (including the realism sweep and unit tests) are unaffected; passing it
    applies the R2 role/week-type intensity ceiling (see
    ``_passes_role_ceiling``) on top of the duration-fit filter."""
    if not library_keys:
        return []
    lo, hi = _duration_bounds(budget_min, day_cap_min)
    key_set = set(library_keys)
    pool = [
        item
        for item in items
        if item["library_key"] in key_set
        and item.get("duration_min") is not None
        and lo <= item["duration_min"] <= hi
    ]
    if slot is not None:
        pool = [item for item in pool if _passes_role_ceiling(item, slot)]
    return pool


# ---------------------------------------------------------------------------
# R2 fix wave: role/week-type intensity ceilings.
#
# Easy-role (filler) slots were drawing sprint-loaded items -- "Z2 + Sprints"
# 6x30s @200% FTP, RPE8-9 -- into what the week briefing calls an easy
# endurance day, twice in a RECOVERY week. Intensity-role and long_ride slots
# are unaffected (a hard durability long ride in build/peak is the house
# signature, per SPEC_LIBRARY_SELECTION.md T21).
# ---------------------------------------------------------------------------

_FILLER_IF_CEILING = 0.78
_FILLER_IF_CEILING_RECOVERY = 0.70
_FILLER_POWER_CEILING_PCT = 115.0
_FILLER_POWER_CEILING_PCT_RECOVERY = 110.0


def _filler_ceilings(slot: Mapping[str, Any]) -> Optional[tuple[float, float]]:
    """(if_ceiling, power_ceiling_pct) for an easy-context slot.

    Fillers are ceilinged everywhere (tighter in recovery weeks). The
    long-ride slot is ceilinged ONLY in recovery weeks: a deload Sunday
    once resolved to a 5x30s @125% blended session at IF 0.746 — the
    hardest ride of its own recovery week — because long_ride carried no
    ceiling anywhere. Build/peak long rides stay unceilinged: hard
    durability long rides are the house signature there."""
    role = slot.get("role")
    week_type = slot.get("week_type")
    if role == "long_ride":
        if week_type == "recovery":
            return (_FILLER_IF_CEILING_RECOVERY, _FILLER_POWER_CEILING_PCT_RECOVERY)
        return None
    if role != "filler":
        return None
    if week_type == "recovery":
        return (_FILLER_IF_CEILING_RECOVERY, _FILLER_POWER_CEILING_PCT_RECOVERY)
    return (_FILLER_IF_CEILING, _FILLER_POWER_CEILING_PCT)


def _max_power_target_pct(structure: Any) -> float:
    """Highest %FTP POWER target anywhere in a TP structure (0.0 if none).

    Cadence targets (unit ``roundOrStridePerMinute``) and non-%FTP labeled
    targets (Power Zone / RPE, per tp_structure_to_zwo._classify_leaf) are
    not power and never count against the ceiling -- drills and spin-ups
    with a cadence prescription are fine on an easy day."""
    highest = 0.0
    blocks = structure.get("structure") if isinstance(structure, dict) else structure
    for block in (blocks or []):
        for leaf in (block.get("steps") or []):
            for target in (leaf.get("targets") or []):
                if target.get("unit") == "roundOrStridePerMinute" or "label" in target:
                    continue
                value = target.get("maxValue", target.get("minValue"))
                if value is not None:
                    highest = max(highest, float(value))
    return highest


# Hard-work-volume budget for ceilinged slots: IF ceilings cannot catch
# BACK-LOADED intensity (an hour of Z2 dilutes 4x3min @110% down to IF
# 0.68 — 12 minutes of genuine VO2 work that once landed on a deload
# Sunday). Total seconds at >=92% FTP is the honest measure: recovery
# slots allow only opener-class touches; regular fillers a little more.
_HARD_WORK_PCT_FLOOR = 92.0
_HARD_WORK_SECONDS_RECOVERY = 150
_HARD_WORK_SECONDS_FILLER = 360


def _hard_work_seconds(structure: Any) -> float:
    total = 0.0
    if not isinstance(structure, Mapping):
        return total
    for step in structure.get("structure") or []:
        reps = ((step.get("length") or {}).get("value") or 1)
        for sub in step.get("steps") or []:
            target = next((t for t in sub.get("targets") or []
                           if t.get("unit") != "roundOrStridePerMinute"), None)
            if not target:
                continue
            pct = target.get("maxValue") or target.get("minValue") or 0
            if pct >= _HARD_WORK_PCT_FLOOR:
                total += reps * ((sub.get("length") or {}).get("value") or 0)
    return total


def _passes_role_ceiling(item: Mapping[str, Any], slot: Mapping[str, Any]) -> bool:
    ceilings = _filler_ceilings(slot)
    if ceilings is None:
        return True
    if_ceiling, power_ceiling_pct = ceilings
    if_planned = item.get("if_planned")
    if if_planned is not None and if_planned > if_ceiling:
        return False
    if _max_power_target_pct(item.get("structure")) > power_ceiling_pct:
        return False
    budget = (_HARD_WORK_SECONDS_RECOVERY if slot.get("week_type") == "recovery"
              else _HARD_WORK_SECONDS_FILLER)
    return _hard_work_seconds(item.get("structure")) <= budget


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

# R3 fix wave: within-plan used-item memory. 24 placements once drew only
# 16 items ("with Surges" x4, "Z2 + Sprints" x3 with zero progression and
# two same-week duplicates) -- different FRESH (non-series) picks across the
# plan kept converging on the same top-ranked item for a given
# duration/level band. A series is exempt (D8's monotone progression
# already guarantees distinct items week to week); this cap only ever
# constrains the first pick of a new series/slot.
_PLAN_WIDE_REUSE_CAP = 2


def _filter_used_items(
    pool: Sequence[Mapping[str, Any]], slot: Mapping[str, Any], used_items: Mapping[Any, Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """R3(a)/(b): both the same-week duplicate ban (b) and the plan-wide
    reuse cap (a) are hard exclusions with no softening -- a small pool
    (e.g. Cadence Work's ~7-item torque_starts_cadence library) once fell
    back to unlimited reuse of its only duration-qualified candidate 5x
    plan-wide when the cap was allowed to soften; a real library miss
    belongs in D9's loud fallback report, not a silent 3rd-plus repeat.
    "An item may repeat in the same plan only as part of a progressing
    series" -- a continuing series is exempt (see select()), never this
    fresh-pick path."""
    plan_week = slot.get("plan_week")
    same_week_free = [
        item for item in pool
        if plan_week not in used_items.get(item["item_id"], {}).get("weeks", ())
    ]
    return [
        item for item in same_week_free
        if used_items.get(item["item_id"], {}).get("count", 0) < _PLAN_WIDE_REUSE_CAP
    ]


def _record_used_item(used_items: dict[Any, dict[str, Any]], item_id: Any, plan_week: Any) -> None:
    entry = used_items.setdefault(item_id, {"count": 0, "weeks": set()})
    entry["count"] += 1
    if plan_week is not None:
        entry["weeks"].add(plan_week)


def select(
    slot: Mapping[str, Any],
    series_state: Optional[dict[str, Any]] = None,
    index: Optional[Mapping[str, Any]] = None,
    used_items: Optional[dict[Any, dict[str, Any]]] = None,
) -> Optional[dict[str, Any]]:
    """Resolve a canonical slot to a curated TP library item, or None (D9).

    ``series_state`` is the caller's dict, threaded through across a plan's
    calls (D8). It is mutated in place to record/advance per-series state;
    pass a fresh {} (or None, treated as a scratch dict) for a non-series
    slot or a slot's first call. Never raises for "no fit" -- returns None.

    ``used_items`` (R3) is the caller's dict, threaded the same way as
    ``series_state``, tracking {item_id: {"count": int, "weeks": set}}
    across the whole plan. It constrains only FRESH (non-continuation)
    picks -- a continuing series is exempt (D8) but still records into it so
    a later fresh pick elsewhere in the plan won't collide with it.
    """
    index = index if index is not None else load_index()
    items = index["items"]

    canonical_name = slot["canonical_name"]
    if canonical_name in SYNTHETIC_ONLY:
        return None

    library_keys = resolve_library_keys(slot)
    budget_min = float(slot.get("budget_min") or 0)
    day_cap_min = slot.get("day_cap_min")

    pool = _qualifying_pool(items, library_keys, budget_min, day_cap_min, slot=slot)
    if not pool:
        return None

    series_key = slot.get("series_key")
    if series_state is not None and series_key and series_key in series_state:
        resolution = _select_series_continuation(slot, series_state, index, pool)
        if resolution is not None:
            if used_items is not None:
                _record_used_item(used_items, resolution["item_id"], slot.get("plan_week"))
            return resolution
        # Series continuation had nothing to progress to (e.g. ladder top,
        # or no qualifying candidate) -- loud fallback, per D9.
        return None

    candidate_pool = pool
    if used_items is not None:
        candidate_pool = _filter_used_items(pool, slot, used_items)
        if not candidate_pool:
            return None

    level = int(slot.get("level") or 1)
    leveled_pool = _apply_level(candidate_pool, level)
    ranked = _rank(leveled_pool)
    if not ranked:
        return None

    idx = _rotate_index(len(ranked), slot.get("athlete_seed"), _slot_identity(slot))
    chosen = ranked[idx]

    if used_items is not None:
        _record_used_item(used_items, chosen["item_id"], slot.get("plan_week"))
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
        # R2: still honors the role/week-type ceiling -- duration drift is
        # an acceptable coherence trade, a recovery-week sprint item is not.
        all_in_library = [
            item for item in index["items"]
            if item["library_key"] == library_key and _passes_role_ceiling(item, slot)
        ]
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

    pool = _qualifying_pool(items, library_keys, budget_min, day_cap_min, slot=slot)
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
