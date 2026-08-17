"""Contract tests for the C3 library selector (SPEC_LIBRARY_SELECTION.md).

Routing totality, fit bounds, level mapping, dimension ranking, variety, and
series/refit tests use small synthetic indexes (via ``select(..., index=...)``
overrides) for controlled edge shapes. The realism sweep runs against the
REAL index (``tp_library_snapshot.load_index()``) as the spec requires.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from tp_library_snapshot import build_family_index  # noqa: E402
from tp_library_snapshot import load_index  # noqa: E402

import library_selector as ls  # noqa: E402
from library_selector import (  # noqa: E402
    ROUTING_TABLE,
    SYNTHETIC_ONLY,
    _apply_level,
    _if_band,
    _qualifying_pool,
    _rank,
    _rotate_index,
    refit,
    resolve_library_keys,
    select,
)


WORKOUT_LIBRARY_YAML = Path(__file__).parent.parent / "config" / "workout_library.yaml"


# ---------------------------------------------------------------------------
# Synthetic index builder
# ---------------------------------------------------------------------------

def make_item(
    item_id,
    library_key="vo2_3030_micro",
    name_base="Widget",
    explicit_level=None,
    duration_min=50,
    tss=50,
    if_planned=0.8,
    dimension_score=0,
    description="",
    structure=None,
):
    return {
        "item_id": item_id,
        "library_key": library_key,
        "name_raw": name_base,
        "name_base": name_base,
        "explicit_level": explicit_level,
        "duration_min": duration_min,
        "tss": tss,
        "if_planned": if_planned,
        "rpe_text": None,
        "dimension_score": dimension_score,
        "has_cadence_targets": False,
        "structure": structure or {"structure": []},
        "description": description,
        "workout_type_id": 2,
    }


def make_index(items):
    return {"items": items, "families": build_family_index(items)}


def base_slot(**overrides):
    slot = {
        "canonical_name": "VO2max 30/30",
        "level": 3,
        "budget_min": 50,
        "day_cap_min": None,
        "role": "intensity_1",
        "phase": "build",
        "series_key": None,
        "week_in_block": 1,
        "athlete_seed": "athlete-1",
        "race_demands": None,
    }
    slot.update(overrides)
    return slot


# ---------------------------------------------------------------------------
# Routing totality
# ---------------------------------------------------------------------------

class TestRoutingTotality:
    def _canonical_names(self):
        doc = yaml.safe_load(WORKOUT_LIBRARY_YAML.read_text())
        return set(doc["workouts"].keys())

    def test_every_canonical_type_routes_or_is_synthetic_only(self):
        names = self._canonical_names()
        covered = set(ROUTING_TABLE) | SYNTHETIC_ONLY
        missing = names - covered
        assert not missing, f"canonical types with no routing and not SYNTHETIC_ONLY: {missing}"

    def test_no_overlap_between_routed_and_synthetic(self):
        overlap = set(ROUTING_TABLE) & SYNTHETIC_ONLY
        assert not overlap

    def test_routing_table_only_names_real_canonical_types(self):
        names = self._canonical_names()
        extra = set(ROUTING_TABLE) - names
        assert not extra, f"ROUTING_TABLE names types not in workout_library.yaml: {extra}"
        extra_synth = SYNTHETIC_ONLY - names
        assert not extra_synth, f"SYNTHETIC_ONLY names types not in workout_library.yaml: {extra_synth}"

    def test_routed_library_keys_are_real_library_keys(self):
        real_keys = {item["library_key"] for item in load_index()["items"]}
        for canonical_name, keys in ROUTING_TABLE.items():
            for key in keys:
                assert key in real_keys, f"{canonical_name} routes to unknown library_key {key}"


# ---------------------------------------------------------------------------
# Fit bounds
# ---------------------------------------------------------------------------

class TestFitBounds:
    def test_qualifying_pool_respects_budget_window(self):
        items = [
            make_item(1, duration_min=40),  # below 0.85*50=42.5
            make_item(2, duration_min=43),  # in window
            make_item(3, duration_min=55),  # in window (<=57.5)
            make_item(4, duration_min=60),  # above 1.15*50=57.5
        ]
        pool = _qualifying_pool(items, ("vo2_3030_micro",), budget_min=50, day_cap_min=None)
        ids = {item["item_id"] for item in pool}
        assert ids == {2, 3}

    def test_day_cap_tightens_upper_bound(self):
        items = [
            make_item(1, duration_min=55),
            make_item(2, duration_min=52),
        ]
        pool = _qualifying_pool(items, ("vo2_3030_micro",), budget_min=50, day_cap_min=53)
        ids = {item["item_id"] for item in pool}
        assert ids == {2}

    def test_select_end_to_end_respects_fit(self):
        items = [
            make_item(1, duration_min=20, dimension_score=5),  # too short, would win on dimension alone
            make_item(2, duration_min=50, dimension_score=1),
        ]
        index = make_index(items)
        result = select(base_slot(budget_min=50), series_state=None, index=index)
        assert result is not None
        assert result["item_id"] == 2


# ---------------------------------------------------------------------------
# Level mapping (both modes)
# ---------------------------------------------------------------------------

class TestLevelMapping:
    def test_explicit_level_mode_exact_match(self):
        pool = [make_item(i, explicit_level=i, duration_min=50) for i in range(1, 7)]
        result = _apply_level(pool, 4)
        assert {item["item_id"] for item in result} == {4}

    def test_explicit_level_mode_tolerance_fallback(self):
        pool = [make_item(1, explicit_level=1, duration_min=50), make_item(3, explicit_level=3, duration_min=50)]
        # level 2 has no exact match but is within +/-1 of both 1 and 3
        result = _apply_level(pool, 2)
        assert {item["item_id"] for item in result} == {1, 3}

    def test_explicit_level_mode_never_hard_empties(self):
        pool = [make_item(1, explicit_level=1, duration_min=50), make_item(2, explicit_level=1, duration_min=50)]
        # level 6 is more than 1 away from every member -> soft fallback to full pool
        result = _apply_level(pool, 6)
        assert {item["item_id"] for item in result} == {1, 2}

    def test_if_band_mode_used_when_coverage_below_half(self):
        # Only 1 of 5 items carries explicit_level -> below the 50% threshold.
        pool = [make_item(i, explicit_level=(1 if i == 1 else None), if_planned=0.5 + i * 0.05) for i in range(1, 6)]
        low = _apply_level(pool, 1)
        high = _apply_level(pool, 6)
        # Low level should skew toward lower IF values than high level.
        assert min(item["if_planned"] for item in low) <= min(item["if_planned"] for item in high)
        assert max(item["if_planned"] for item in high) >= max(item["if_planned"] for item in low)

    def test_if_band_bounds_are_generous_p10_to_p90(self):
        lo1, hi1 = _if_band(1)
        lo6, hi6 = _if_band(6)
        assert lo1 == 0.0  # p10 - 20 clipped to 0
        assert hi6 == 100.0  # p90 + 20 clipped to 100
        assert lo1 < hi1
        assert lo6 < hi6


# ---------------------------------------------------------------------------
# Dimension ranking
# ---------------------------------------------------------------------------

class TestDimensionRanking:
    def test_dimension_rich_outranks_flat_at_equal_fit(self):
        flat = make_item(1, duration_min=50, dimension_score=0, if_planned=0.8)
        rich = make_item(2, duration_min=50, dimension_score=4, if_planned=0.8)
        ranked = _rank([flat, rich])
        assert ranked[0]["item_id"] == 2

    def test_select_picks_dimension_rich_with_two_candidate_pool(self):
        # Pool size 2 -> top_half = 1 -> rotation always lands on rank 0,
        # so this deterministically proves ranking without seed ambiguity.
        items = [
            make_item(1, duration_min=50, dimension_score=0, if_planned=0.8),
            make_item(2, duration_min=50, dimension_score=4, if_planned=0.8),
        ]
        index = make_index(items)
        result = select(base_slot(), series_state=None, index=index)
        assert result["item_id"] == 2


# ---------------------------------------------------------------------------
# Variety (D7) + determinism
# ---------------------------------------------------------------------------

class TestVarietyAndDeterminism:
    def _pool_of_six(self):
        return [make_item(i, duration_min=50, dimension_score=1, if_planned=0.8) for i in range(1, 7)]

    def test_two_seeds_diverge_when_pool_at_least_three(self):
        items = self._pool_of_six()
        index = make_index(items)
        seen = set()
        for seed in range(20):
            result = select(base_slot(athlete_seed=f"athlete-{seed}"), series_state=None, index=index)
            seen.add(result["item_id"])
        assert len(seen) > 1, "expected variety across athlete seeds with pool size 6"

    def test_same_seed_regenerates_byte_identically(self):
        items = self._pool_of_six()
        index = make_index(items)
        slot = base_slot(athlete_seed="athlete-fixed")
        first = select(slot, series_state=None, index=index)
        second = select(slot, series_state=None, index=index)
        assert first == second

    def test_rotation_never_leaves_top_half(self):
        pool_len = 6
        for seed in range(50):
            idx = _rotate_index(pool_len, seed, "series-x")
            assert 0 <= idx < (pool_len + 1) // 2

    def test_rotation_stays_at_rank_zero_for_pool_of_one(self):
        assert _rotate_index(1, "any-seed", "series-x") == 0


# ---------------------------------------------------------------------------
# Series (D8): monotone across weeks, family ladder, singleton case
# ---------------------------------------------------------------------------

class TestSeries:
    def test_family_ladder_progresses_monotone_across_three_weeks(self):
        items = [
            make_item(10, library_key="torque_sfr", name_base="Big Gear Ladder", explicit_level=1,
                      duration_min=50, if_planned=0.7),
            make_item(11, library_key="torque_sfr", name_base="Big Gear Ladder", explicit_level=2,
                      duration_min=50, if_planned=0.75),
            make_item(12, library_key="torque_sfr", name_base="Big Gear Ladder", explicit_level=3,
                      duration_min=50, if_planned=0.8),
        ]
        index = make_index(items)
        series_state = {}
        slot = base_slot(canonical_name="SFR", series_key="intensity_1-block1", budget_min=50, level=1)

        r1 = select(slot, series_state=series_state, index=index)
        r2 = select(slot, series_state=series_state, index=index)
        r3 = select(slot, series_state=series_state, index=index)

        assert [r1["item_id"], r2["item_id"], r3["item_id"]] == [10, 11, 12]
        assert r1["if_planned"] < r2["if_planned"] < r3["if_planned"]

    def test_singleton_family_progresses_same_library_nearest_higher_if(self):
        items = [
            make_item(20, library_key="tempo", name_base="Alpha", duration_min=50, if_planned=0.70),
            make_item(21, library_key="tempo", name_base="Bravo", duration_min=50, if_planned=0.73),
            make_item(22, library_key="tempo", name_base="Charlie", duration_min=50, if_planned=0.78),
            make_item(23, library_key="tempo", name_base="Delta", duration_min=50, if_planned=0.90),
        ]
        index = make_index(items)
        series_key = "intensity_2-block1"
        # Pre-seed state as if week 1 already landed on the singleton "Alpha".
        series_state = {
            series_key: {
                "family_key": "tempo||Alpha",
                "library_key": "tempo",
                "item_id": 20,
                "rung": 1,
                "if_planned": 0.70,
                "singleton": True,
            }
        }
        slot = base_slot(canonical_name="Tempo", series_key=series_key, budget_min=50, level=1)

        r2 = select(slot, series_state=series_state, index=index)
        assert r2["item_id"] == 21  # nearest strictly-higher IF

        r3 = select(slot, series_state=series_state, index=index)
        assert r3["item_id"] == 22  # continues upward, nearest higher again

        assert r2["if_planned"] < r3["if_planned"]

    def test_series_returns_none_when_ladder_and_library_exhausted(self):
        items = [
            make_item(30, library_key="tempo", name_base="Alpha", duration_min=50, if_planned=0.99),
        ]
        index = make_index(items)
        series_key = "intensity_3-block1"
        series_state = {
            series_key: {
                "family_key": "tempo||Alpha",
                "library_key": "tempo",
                "item_id": 30,
                "rung": 1,
                "if_planned": 0.99,
                "singleton": True,
            }
        }
        slot = base_slot(canonical_name="Tempo", series_key=series_key, budget_min=50, level=1)
        result = select(slot, series_state=series_state, index=index)
        assert result is None


# ---------------------------------------------------------------------------
# refit()
# ---------------------------------------------------------------------------

class TestRefit:
    def test_refit_returns_shorter_candidate(self):
        items = [
            make_item(1, duration_min=50, dimension_score=1),
            make_item(2, duration_min=75, dimension_score=1),
            make_item(3, duration_min=100, dimension_score=1),
        ]
        index = make_index(items)
        original_slot = base_slot(budget_min=100)
        original = select(original_slot, series_state=None, index=index)
        assert original["duration_min"] == 100

        trimmed_slot = base_slot(budget_min=55)
        trimmed = refit(trimmed_slot, series_state=None, index=index)
        assert trimmed is not None
        assert trimmed["duration_min"] < original["duration_min"]

    def test_refit_honors_active_series_library(self):
        items = [
            make_item(1, library_key="torque_sfr", name_base="Big Gear Ladder", duration_min=50, if_planned=0.7),
            make_item(2, library_key="torque_sfr", name_base="Big Gear Ladder", duration_min=40, if_planned=0.7),
            make_item(3, library_key="vo2_3030_micro", name_base="Other", duration_min=42, if_planned=0.9),
        ]
        index = make_index(items)
        series_key = "intensity_1-block1"
        series_state = {
            series_key: {
                "family_key": "torque_sfr||Big Gear Ladder",
                "library_key": "torque_sfr",
                "item_id": 1,
                "rung": None,
                "if_planned": 0.7,
                "singleton": False,
            }
        }
        slot = base_slot(canonical_name="SFR", series_key=series_key, budget_min=45)
        result = refit(slot, series_state=series_state, index=index)
        assert result is not None
        assert result["library_key"] == "torque_sfr"


# ---------------------------------------------------------------------------
# None on impossible budget
# ---------------------------------------------------------------------------

class TestImpossibleBudget:
    def test_no_qualifying_item_returns_none(self):
        items = [make_item(1, duration_min=200)]
        index = make_index(items)
        result = select(base_slot(budget_min=5), series_state=None, index=index)
        assert result is None

    def test_synthetic_only_type_returns_none(self):
        result = select(base_slot(canonical_name="Rest Day", budget_min=35), series_state=None, index=make_index([]))
        assert result is None

    def test_unrouted_unknown_type_raises(self):
        with pytest.raises(KeyError):
            select(base_slot(canonical_name="Not A Real Type"), series_state=None, index=make_index([]))


# ---------------------------------------------------------------------------
# resolve_library_keys dynamic rules (Endurance split, T21, T22)
# ---------------------------------------------------------------------------

class TestDynamicRouting:
    def test_endurance_short_budget_routes_short_library(self):
        keys = resolve_library_keys(base_slot(canonical_name="Endurance", budget_min=100, role="filler", phase="base"))
        assert "endurance_z2_short" in keys
        assert "endurance_z2_long" not in keys
        assert "endurance_with_work" in keys

    def test_endurance_long_budget_routes_long_library(self):
        keys = resolve_library_keys(base_slot(canonical_name="Endurance", budget_min=180, role="filler", phase="base"))
        assert "endurance_z2_long" in keys
        assert "endurance_z2_short" not in keys

    def test_long_ride_in_build_phase_draws_durability_alternatives(self):
        keys = resolve_library_keys(
            base_slot(canonical_name="Endurance", budget_min=180, role="long_ride", phase="build")
        )
        assert "durability_long_sims" in keys
        assert "durability_tired_intervals" in keys

    def test_long_ride_outside_build_peak_skips_durability_alternatives(self):
        keys = resolve_library_keys(
            base_slot(canonical_name="Endurance", budget_min=180, role="long_ride", phase="base")
        )
        assert "durability_long_sims" not in keys

    def test_race_demands_flag_adds_anaerobic_extras_for_stars_in_your_eyes(self):
        keys_off = resolve_library_keys(base_slot(canonical_name="Stars In Your Eyes", race_demands=None))
        keys_on = resolve_library_keys(
            base_slot(canonical_name="Stars In Your Eyes", race_demands={"punchy_climbs"})
        )
        assert "sprint_attacks" not in keys_off
        assert "sprint_attacks" in keys_on
        assert "anaerobic_capacity" in keys_on


# ---------------------------------------------------------------------------
# Realism sweep against the REAL index
# ---------------------------------------------------------------------------

class TestRealismSweep:
    def test_realism_sweep_fallback_rate(self):
        index = load_index()
        levels = (2, 3, 4)
        budgets = (50, 70, 90, 150, 210)
        day_caps = (120, 600)

        routed_types = sorted(t for t in ROUTING_TABLE if t not in SYNTHETIC_ONLY)

        table = {}
        total_trials = 0
        total_fallbacks = 0

        for canonical_name in routed_types:
            trials = 0
            fallbacks = 0
            pool_sizes = []
            for level in levels:
                for budget in budgets:
                    for day_cap in day_caps:
                        slot = base_slot(
                            canonical_name=canonical_name,
                            level=level,
                            budget_min=budget,
                            day_cap_min=day_cap,
                            role="filler",
                            phase="build",
                            series_key=None,
                            athlete_seed="sweep",
                            race_demands=None,
                        )
                        library_keys = resolve_library_keys(slot)
                        pool = _qualifying_pool(index["items"], library_keys, budget, day_cap)
                        pool_sizes.append(len(pool))
                        result = select(slot, series_state=None, index=index)
                        trials += 1
                        if result is None:
                            fallbacks += 1

            table[canonical_name] = {
                "trials": trials,
                "fallbacks": fallbacks,
                "fallback_rate": fallbacks / trials,
                "avg_pool_size": sum(pool_sizes) / len(pool_sizes),
                "min_pool_size": min(pool_sizes),
                "max_pool_size": max(pool_sizes),
            }
            total_trials += trials
            total_fallbacks += fallbacks

        print("\nRealism sweep (levels=2-4, budgets=50/70/90/150/210, day_cap=120/600):")
        print(f"{'canonical_type':38s} {'trials':>6s} {'fallbacks':>9s} {'rate':>7s} {'avg_pool':>9s} {'min':>4s} {'max':>4s}")
        for canonical_name, stats in table.items():
            print(
                f"{canonical_name:38s} {stats['trials']:6d} {stats['fallbacks']:9d} "
                f"{stats['fallback_rate']:6.1%} {stats['avg_pool_size']:9.1f} "
                f"{stats['min_pool_size']:4d} {stats['max_pool_size']:4d}"
            )
        overall_rate = total_fallbacks / total_trials
        print(f"{'OVERALL':38s} {total_trials:6d} {total_fallbacks:9d} {overall_rate:6.1%}")

        assert overall_rate < 0.25, f"overall fallback rate {overall_rate:.1%} >= 25%"
