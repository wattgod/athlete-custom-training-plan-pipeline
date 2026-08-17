"""Contract tests for the C1 TP library snapshot (SPEC_LIBRARY_SELECTION.md).

Parser fixtures use REAL name strings pulled from the coach's raw dump
(``gg_tp_library_full.json``) rather than invented shapes -- the spec
explicitly warns that a naive 4-dash split misparses real names. Exclusion
counts and dimension-score fixtures are asserted against the real dump so a
future dump refresh that silently changes shape gets caught here.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from tp_library_snapshot import (  # noqa: E402
    DEFAULT_RAW_PATH,
    build_family_index,
    build_index,
    build_items,
    classify_dimension_cues,
    compute_dimension_score,
    compute_if_planned,
    family_stats,
    has_cadence_targets,
    load_index,
    load_raw_dump,
    main,
    parse_item_name,
    reconcile,
    write_index,
)


REAL_DUMP_AVAILABLE = DEFAULT_RAW_PATH.exists()
requires_real_dump = pytest.mark.skipif(
    not REAL_DUMP_AVAILABLE, reason=f"real raw dump not present at {DEFAULT_RAW_PATH}"
)


# ---------------------------------------------------------------------------
# Name parser fixtures (all real strings from the dump)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name,expected_base,expected_level,expected_rpe",
    [
        # 4-dash: category is its own leading segment, digit level.
        ("Sweet Spot - Folgers Choice - 2 - 85min - RPE7-8", "Folgers Choice", 2, "7-8"),
        ("Torque - Stutter Step - 3 - 107min - RPE10", "Stutter Step", 3, "10"),
        # 5-dash with 'ref': the internal dash inside name_base must survive.
        (
            "Sweet Spot - Not Threshold - 3 Pints - ref - 109min - RPE7-8",
            "Not Threshold - 3 Pints",
            None,
            "7-8",
        ),
        # digit-rung, category glued to a "w/ ..." modifier via its own dash segment.
        ("Endurance - w/ surges - 2 - 300min - RPE3-4", "w/ surges", 2, "3-4"),
        # category word glued directly to its modifier with no internal dash.
        ("Endurance with Surges - 6 - 80min - RPE9-10", "with Surges", 6, "9-10"),
        # bare names: no RPE/duration/level tokens at all -> name_base = full name.
        ("Just Ride", "Just Ride", None, None),
        ("Commute", "Commute", None, None),
        # out-of-range digit (not 1-6) is NOT a level token -- stays in name_base.
        ("Endurance - (MxHr) - 7 - 180min - RPE1-2", "(MxHr) - 7", None, "1-2"),
    ],
)
def test_parse_item_name_real_shapes(name, expected_base, expected_level, expected_rpe):
    parsed = parse_item_name(name)
    assert parsed["name_base"] == expected_base
    assert parsed["explicit_level"] == expected_level
    assert parsed["rpe_text"] == expected_rpe


def test_parse_item_name_explicit_level_range_is_1_to_6():
    for level in range(1, 7):
        parsed = parse_item_name(f"Torque - Sample - {level} - 90min - RPE5-6")
        assert parsed["explicit_level"] == level

    # 7-9 are not valid rungs -- they stay embedded in the name.
    for out_of_range in (0, 7, 8, 16):
        parsed = parse_item_name(f"Torque - Sample - {out_of_range} - 90min - RPE5-6")
        assert parsed["explicit_level"] is None
        assert str(out_of_range) in parsed["name_base"]


def test_parse_item_name_ref_does_not_set_explicit_level():
    parsed = parse_item_name("Recovery - Cafe Ride - ref - 60min - RPE1-2")
    assert parsed["explicit_level"] is None
    assert parsed["name_base"] == "Cafe Ride"


# ---------------------------------------------------------------------------
# Dimension scoring -- hand-labeled real items (min 0 .. max 6)
# ---------------------------------------------------------------------------

def _mk_item(description, structure=None):
    return {"description": description, "structure": structure}


_CADENCE_STRUCTURE = {
    "structure": [
        {
            "steps": [
                {"targets": [{"minValue": 85}, {"minValue": 100, "unit": "roundOrStridePerMinute"}]}
            ]
        }
    ]
}
_NO_CADENCE_STRUCTURE = {"structure": [{"steps": [{"targets": [{"minValue": 85}]}]}]}

# (item_id, description, structure, expected_classes, expected_score)
# Hand-labeled against the real item text/structure pulled from the dump
# (2026-08-17). See executor report for the item_id -> library_key mapping.
DIMENSION_FIXTURES = [
    (
        14356150,
        "5min high cadence Z3 (100+ rpm) to prime efforts\nCadence: variable\nPosition: Variable\n"
        "Variable power matching terrain",
        _CADENCE_STRUCTURE,
        {"cadence_rpm", "position_posture", "terrain_surface"},
        4,
    ),
    (
        14356131,
        "Pick 3-4 climbs and ride them like this:\n1 min Z5\n1 min Z4\nZ3 to top",
        _CADENCE_STRUCTURE,
        {"terrain_surface"},
        2,
    ),
    (
        14357230,
        "3x 10min microbursts: continuous 15sec @150% FTP / 15sec easy spin, 5min recovery between sets",
        _NO_CADENCE_STRUCTURE,
        set(),
        0,
    ),
    (14355807, "Avoid big intensity, keep it fun.", None, set(), 0),
    (14356185, "Z1 - EASY spin, light on the pedals.", None, set(), 0),
    (
        14356880,
        "15' warmup then 2x10' @ 87-91% FTP, 5' easy between, 10' cooldown. RPE 6-7/10.",
        _CADENCE_STRUCTURE,
        set(),
        1,
    ),
    (
        14357237,
        "1x5min high cadence (95+) z3\n5x20sec seated stomps. Start in big gear from a standstill.",
        _NO_CADENCE_STRUCTURE,
        {"cadence_rpm", "standing_seated"},
        2,
    ),
    (
        14357448,
        "1x10m Z3 to get loose; focus on cadence (>100rpm)\n6x3m Z5, 3min Z1",
        _NO_CADENCE_STRUCTURE,
        {"cadence_rpm"},
        1,
    ),
    (
        14357057,
        "5x [15sec @200% FTP sprint / 10sec @150% FTP settle] full gas, then 20min @70% FTP steady",
        _NO_CADENCE_STRUCTURE,
        set(),
        0,
    ),
    (
        14356914,
        "#2 - 10-12 min Z3 on climb alt 1.5 min seated / 30 sec standing\n"
        "#4 - in the drops, 95+ rpm, natural technique, use climbs, high cadence, terrain allows",
        _CADENCE_STRUCTURE,
        {"cadence_rpm", "position_posture", "terrain_surface", "drill_technique", "standing_seated"},
        6,
    ),
]


@pytest.mark.parametrize("item_id,description,structure,expected_classes,expected_score", DIMENSION_FIXTURES)
def test_dimension_score_hand_labeled(item_id, description, structure, expected_classes, expected_score):
    assert classify_dimension_cues(description) == expected_classes
    assert compute_dimension_score(description, structure) == expected_score


def test_dimension_score_max_is_six():
    assert max(score for *_rest, score in [(f[3], f[4]) for f in DIMENSION_FIXTURES]) == 6


def test_has_cadence_targets():
    assert has_cadence_targets(_CADENCE_STRUCTURE) is True
    assert has_cadence_targets(_NO_CADENCE_STRUCTURE) is False
    assert has_cadence_targets(None) is False
    assert has_cadence_targets({}) is False


# ---------------------------------------------------------------------------
# IF computation
# ---------------------------------------------------------------------------

def test_compute_if_planned_prefers_existing_value():
    assert compute_if_planned(tss=200, hours=2, existing=0.5) == 0.5


def test_compute_if_planned_computes_from_tss_and_hours():
    # TSS = 100 * hours * IF^2  ->  IF = sqrt(tss / (100*hours))
    result = compute_if_planned(tss=381.5, hours=4.916666666666667, existing=None)
    assert result == pytest.approx(0.8809, abs=1e-3)


def test_compute_if_planned_none_when_uncomputable():
    assert compute_if_planned(tss=None, hours=2, existing=None) is None
    assert compute_if_planned(tss=100, hours=0, existing=None) is None
    assert compute_if_planned(tss=None, hours=None, existing=None) is None


# ---------------------------------------------------------------------------
# Family grouping + ladder monotonicity (synthetic, deterministic)
# ---------------------------------------------------------------------------

def _mk_selectable(item_id, library_key, name_base, explicit_level=None, if_planned=None):
    return {
        "item_id": item_id,
        "library_key": library_key,
        "name_raw": f"raw-{item_id}",
        "name_base": name_base,
        "explicit_level": explicit_level,
        "duration_min": 60,
        "tss": 50,
        "if_planned": if_planned,
        "rpe_text": "5-6",
        "dimension_score": 0,
        "has_cadence_targets": False,
        "structure": {"structure": [{"steps": []}]},
        "description": "",
        "workout_type_id": 2,
    }


def test_family_grouping_by_library_key_and_name_base():
    items = [
        _mk_selectable(1, "vo2_classic", "Widget", explicit_level=1),
        _mk_selectable(2, "vo2_classic", "Widget", explicit_level=2),
        _mk_selectable(3, "vo2_blends", "Widget", explicit_level=1),  # same name_base, different library
        _mk_selectable(4, "vo2_classic", "Gadget", explicit_level=1),
    ]
    families = build_family_index(items)
    assert set(families) == {"vo2_classic||Widget", "vo2_blends||Widget", "vo2_classic||Gadget"}
    assert families["vo2_classic||Widget"]["members"] == [1, 2]
    assert families["vo2_blends||Widget"]["members"] == [3]


def test_ladder_uses_explicit_level_when_present_and_is_monotone():
    items = [
        _mk_selectable(1, "torque_stomps", "Ramp", explicit_level=3, if_planned=0.9),
        _mk_selectable(2, "torque_stomps", "Ramp", explicit_level=1, if_planned=0.6),
        _mk_selectable(3, "torque_stomps", "Ramp", explicit_level=2, if_planned=0.99),  # deliberately non-IF-monotone
    ]
    families = build_family_index(items)
    ladder = families["torque_stomps||Ramp"]["ladder"]
    assert families["torque_stomps||Ramp"]["rung_basis"] == "explicit_level"
    rungs = [entry["rung"] for entry in ladder]
    assert rungs == sorted(rungs)
    assert rungs == [1, 2, 3]
    assert [entry["item_id"] for entry in ladder] == [2, 3, 1]


def test_ladder_falls_back_to_if_rank_when_no_explicit_level():
    items = [
        _mk_selectable(1, "endurance_z2_long", "Base", if_planned=0.7),
        _mk_selectable(2, "endurance_z2_long", "Base", if_planned=0.5),
        _mk_selectable(3, "endurance_z2_long", "Base", if_planned=0.6),
    ]
    families = build_family_index(items)
    family = families["endurance_z2_long||Base"]
    assert family["rung_basis"] == "if_rank"
    rungs = [entry["rung"] for entry in family["ladder"]]
    assert rungs == [1, 2, 3]
    ifs = [entry["if_planned"] for entry in family["ladder"]]
    assert ifs == sorted(ifs)
    assert [entry["item_id"] for entry in family["ladder"]] == [2, 3, 1]


def test_family_stats_singleton_share():
    items = [
        _mk_selectable(1, "a", "solo"),
        _mk_selectable(2, "b", "pair"),
        _mk_selectable(3, "b", "pair"),
    ]
    families = build_family_index(items)
    stats = family_stats(families)
    assert stats == {
        "family_count": 2,
        "singleton_count": 1,
        "singleton_share": 0.5,
        "max_family_size": 2,
    }


# ---------------------------------------------------------------------------
# Exclusion counts against the REAL dump
# ---------------------------------------------------------------------------

@requires_real_dump
def test_exclusion_counts_against_real_dump():
    raw = load_raw_dump(DEFAULT_RAW_PATH)
    items, exclusions = build_items(raw)

    total_raw = sum(len(library.get("items", [])) for library in raw.values())
    assert total_raw == 1631

    assert exclusions["non_bike"]["count"] == 38
    # Spec's own rationale cites ~130; the real dump (verified 2026-08-17)
    # actually excludes 134 structureless bike items. Asserting the real
    # count here rather than the spec's approximation, so a future dump
    # refresh that changes this is caught.
    assert exclusions["structureless_bike"]["count"] == 134
    assert exclusions["extra"]["count"] == 0

    assert len(items) == total_raw - 38 - 134
    assert len(items) == 1459


@requires_real_dump
def test_extra_exclusions_hook_drops_matching_item_ids():
    raw = load_raw_dump(DEFAULT_RAW_PATH)
    baseline_items, _ = build_items(raw)
    victim_id = baseline_items[0]["item_id"]

    items, exclusions = build_items(raw, extra_exclusions=[victim_id])

    assert exclusions["extra"]["count"] == 1
    assert exclusions["extra"]["items"][0]["item_id"] == victim_id
    assert victim_id not in {item["item_id"] for item in items}
    assert len(items) == len(baseline_items) - 1


@requires_real_dump
def test_extra_exclusions_hook_accepts_reason_objects():
    raw = load_raw_dump(DEFAULT_RAW_PATH)
    baseline_items, _ = build_items(raw)
    victim_id = baseline_items[1]["item_id"]

    _items, exclusions = build_items(
        raw, extra_exclusions=[{"item_id": victim_id, "reason": "C2 round-trip failure"}]
    )

    assert exclusions["extra"]["items"][0]["reason"] == "C2 round-trip failure"


@requires_real_dump
def test_real_dump_ladder_monotonicity_and_family_stats():
    raw = load_raw_dump(DEFAULT_RAW_PATH)
    items, _ = build_items(raw)
    families = build_family_index(items)

    for family in families.values():
        rungs = [entry["rung"] for entry in family["ladder"]]
        assert rungs == sorted(rungs), family

    stats = family_stats(families)
    assert stats["family_count"] > 0
    assert 0.0 <= stats["singleton_share"] <= 1.0


# ---------------------------------------------------------------------------
# Reconcile smoke test
# ---------------------------------------------------------------------------

def _tiny_raw_dump():
    return {
        "lib_a": {
            "libraryId": 1,
            "items": [
                {
                    "exerciseLibraryItemId": 101,
                    "itemName": "Torque - Sample - 1 - 60min - RPE5-6",
                    "workoutTypeId": 2,
                    "totalTimePlanned": 1.0,
                    "tssPlanned": 50.0,
                    "ifPlanned": 0.7071,
                    "description": "Steady cadence work.",
                    "structure": {"structure": [{"steps": [{"targets": [{"minValue": 70}]}]}]},
                },
                {
                    "exerciseLibraryItemId": 102,
                    "itemName": "Torque - Sample - 2 - 90min - RPE6-7",
                    "workoutTypeId": 2,
                    "totalTimePlanned": 1.5,
                    "tssPlanned": 90.0,
                    "ifPlanned": 0.7746,
                    "description": "Steady effort.",
                    "structure": {"structure": [{"steps": [{"targets": [{"minValue": 75}]}]}]},
                },
            ],
        }
    }


def test_reconcile_reports_no_drift_for_unchanged_dump(tmp_path):
    dump_path = tmp_path / "raw.json"
    index_path = tmp_path / "index.json.gz"
    raw = _tiny_raw_dump()
    dump_path.write_text(json.dumps(raw), encoding="utf-8")
    write_index(build_index(dump_path), index_path)

    report = reconcile(dump_path, index_path)
    assert report == {
        "added": [],
        "removed": [],
        "changed": [],
        "family_count_old": report["family_count_new"],
        "family_count_new": report["family_count_new"],
    }


def test_reconcile_detects_added_removed_and_changed(tmp_path):
    dump_path = tmp_path / "raw.json"
    index_path = tmp_path / "index.json.gz"
    raw = _tiny_raw_dump()
    dump_path.write_text(json.dumps(raw), encoding="utf-8")
    write_index(build_index(dump_path), index_path)

    mutated = copy.deepcopy(raw)
    mutated["lib_a"]["items"][0]["tssPlanned"] = 55.0  # changed
    mutated["lib_a"]["items"][0]["ifPlanned"] = None  # forces if_planned recompute -> also changes
    mutated["lib_a"]["items"].pop(1)  # removed
    mutated["lib_a"]["items"].append(
        {
            "exerciseLibraryItemId": 103,
            "itemName": "Torque - New - ref - 45min - RPE4-5",
            "workoutTypeId": 2,
            "totalTimePlanned": 0.75,
            "tssPlanned": 40.0,
            "ifPlanned": 0.73,
            "description": "New item.",
            "structure": {"structure": [{"steps": [{"targets": [{"minValue": 60}]}]}]},
        }
    )
    dump_path.write_text(json.dumps(mutated), encoding="utf-8")

    report = reconcile(dump_path, index_path)
    assert report["added"] == [103]
    assert report["removed"] == [102]
    assert [entry["item_id"] for entry in report["changed"]] == [101]
    assert "tss" in report["changed"][0]["fields"]


def test_cli_build_then_reconcile_round_trip(tmp_path, capsys):
    dump_path = tmp_path / "raw.json"
    out_path = tmp_path / "index.json.gz"
    dump_path.write_text(json.dumps(_tiny_raw_dump()), encoding="utf-8")

    assert main([str(dump_path), "--out", str(out_path)]) == 0
    assert out_path.exists()
    capsys.readouterr()

    assert main([str(dump_path), "--out", str(out_path), "--reconcile"]) == 0
    assert "added:\n  none" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Loader API
# ---------------------------------------------------------------------------

def test_load_index_returns_items_and_families_and_is_cached(tmp_path):
    dump_path = tmp_path / "raw.json"
    out_path = tmp_path / "index.json.gz"
    dump_path.write_text(json.dumps(_tiny_raw_dump()), encoding="utf-8")
    write_index(build_index(dump_path), out_path)

    loaded_a = load_index(out_path)
    loaded_b = load_index(out_path)
    assert loaded_a is loaded_b  # cached: same object identity
    assert {item["item_id"] for item in loaded_a["items"]} == {101, 102}
    assert "families" in loaded_a
