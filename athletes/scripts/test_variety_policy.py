"""Variety policy (Matti, 2026-09-18; spec docs/specs/2026-09-18-variety-and-
weekly-dynamic-plans.md part A): block spread, progression-first series
starts, series length caps, easy-day library rotation, and the variety
report. Synthetic indexes via test_library_selector's builders."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import library_selector as ls  # noqa: E402
from test_library_selector import make_index, make_item  # noqa: E402


def _slot(**over):
    base = {
        "canonical_name": "VO2max 40/20", "level": 2, "budget_min": 60, "role": "intensity",
        "phase": "build", "week_type": "load", "series_key": (1, "Tue", "VO2max 40/20"),
        "week_in_block": 1, "plan_week": 1, "day": "Tue", "athlete_seed": "ath",
        "block_id": 1, "session_floor_min": 60,
    }
    base.update(over)
    return base


def _vo2_pool():
    # family "Deep" opens a 3-rung ladder over the floor; "Shallow" has a
    # 2nd rung under the floor (not floor-qualified); "Solo" is a singleton.
    return [
        make_item(1, "vo2_classic", "Deep", explicit_level=1, duration_min=60, if_planned=0.80, dimension_score=1),
        make_item(2, "vo2_classic", "Deep", explicit_level=2, duration_min=65, if_planned=0.83, dimension_score=1),
        make_item(3, "vo2_classic", "Deep", explicit_level=3, duration_min=70, if_planned=0.86, dimension_score=1),
        make_item(4, "vo2_classic", "Shallow", explicit_level=1, duration_min=60, if_planned=0.80, dimension_score=3),
        make_item(5, "vo2_classic", "Shallow", explicit_level=2, duration_min=45, if_planned=0.84, dimension_score=3),
        make_item(6, "vo2_classic", "Solo", explicit_level=2, duration_min=60, if_planned=0.81, dimension_score=3),
    ]


def test_ladder_depth_counts_only_floor_qualified_rungs():
    idx = make_index(_vo2_pool())
    deep = next(i for i in idx["items"] if i["item_id"] == 1)
    shallow = next(i for i in idx["items"] if i["item_id"] == 4)
    solo = next(i for i in idx["items"] if i["item_id"] == 6)
    assert ls._ladder_depth_above_floor(deep, idx, 60) == 2
    assert ls._ladder_depth_above_floor(shallow, idx, 60) == 0
    assert ls._ladder_depth_above_floor(solo, idx, 60) == 0
    assert ls._ladder_depth_above_floor(deep, idx, 60, cap_min=65) == 1


def test_intensity_series_start_prefers_the_deep_ladder_over_richer_singletons():
    idx = make_index(_vo2_pool())
    series, used = {}, {}
    first = ls.select(_slot(level=1), series_state=series, index=idx, used_items=used)
    assert first["name_base"] == "Deep"
    # and the series then climbs its own ladder
    second = ls.select(_slot(level=2, plan_week=2), series_state=series, index=idx, used_items=used)
    assert (second["name_base"], second["item_id"]) == ("Deep", 2)


def test_series_closes_after_three_rungs_and_restarts_on_a_different_family():
    pool = _vo2_pool() + [
        make_item(7, "vo2_classic", "Deep", explicit_level=4, duration_min=75, if_planned=0.88, dimension_score=1),
        make_item(8, "vo2_classic", "Other", explicit_level=1, duration_min=60, if_planned=0.80, dimension_score=0),
        make_item(9, "vo2_classic", "Other", explicit_level=2, duration_min=62, if_planned=0.83, dimension_score=0),
    ]
    idx = make_index(pool)
    series, used = {}, {}
    names = []
    for week in (1, 2, 3, 4):
        res = ls.select(_slot(level=min(week, 3), plan_week=week), series_state=series, index=idx, used_items=used)
        names.append(res["name_base"])
    assert names[:3] == ["Deep", "Deep", "Deep"]
    assert names[3] != "Deep"
    assert series[(1, "Tue", "VO2max 40/20")]["placed"] == 1


def test_filler_pair_closes_after_two_rungs():
    pool = [
        make_item(1, "endurance_with_work", "Sprints", explicit_level=1, duration_min=60, if_planned=0.65, dimension_score=2),
        make_item(2, "endurance_with_work", "Sprints", explicit_level=2, duration_min=65, if_planned=0.67, dimension_score=2),
        make_item(3, "endurance_with_work", "Sprints", explicit_level=3, duration_min=70, if_planned=0.69, dimension_score=2),
        make_item(4, "skills", "Drills", explicit_level=1, duration_min=60, if_planned=0.60, dimension_score=1),
        make_item(5, "skills", "Drills", explicit_level=2, duration_min=62, if_planned=0.62, dimension_score=1),
    ]
    idx = make_index(pool)
    series, used = {}, {}
    names = []
    for week in (1, 2, 3):
        res = ls.select(_slot(canonical_name="Endurance", role="filler", level=1, plan_week=week,
                              series_key=(1, "Wed", "Endurance"), filler_ordinal=None),
                        series_state=series, index=idx, used_items=used)
        names.append(res["name_base"])
    assert names[0] == names[1]
    assert names[2] != names[0]


def test_no_item_twice_in_a_block_but_allowed_in_a_later_block():
    pool = [make_item(1, "vo2_classic", "Only", duration_min=60, if_planned=0.8)]
    idx = make_index(pool)
    used = {}
    a = ls.select(_slot(series_key=None, plan_week=1, day="Tue"), index=idx, used_items=used)
    b = ls.select(_slot(series_key=None, plan_week=2, day="Thu"), index=idx, used_items=used)
    c = ls.select(_slot(series_key=None, plan_week=5, day="Tue", block_id=2), index=idx, used_items=used)
    assert a is not None and b is None and c is not None


def test_family_already_on_the_week_is_avoided_when_an_alternative_exists():
    pool = [
        make_item(1, "vo2_classic", "Fam", explicit_level=1, duration_min=60, if_planned=0.80, dimension_score=5),
        make_item(2, "vo2_classic", "Fam", explicit_level=2, duration_min=62, if_planned=0.82, dimension_score=5),
        make_item(3, "vo2_classic", "Alt", explicit_level=1, duration_min=60, if_planned=0.80, dimension_score=0),
    ]
    idx = make_index(pool)
    used = {}
    first = ls.select(_slot(series_key=None, day="Tue", level=1), index=idx, used_items=used)
    second = ls.select(_slot(series_key=None, day="Thu", level=2), index=idx, used_items=used)
    assert first["name_base"] == "Fam" and second["name_base"] == "Alt"
    # soft: with no other family the pool stands rather than failing
    only_fam = make_index(pool[:2])
    used2 = {}
    ls.select(_slot(series_key=None, day="Tue", level=1), index=only_fam, used_items=used2)
    assert ls.select(_slot(series_key=None, day="Thu", level=2), index=only_fam, used_items=used2) is not None


def test_endurance_fillers_rotate_libraries_across_the_week():
    pool = [
        make_item(1, "endurance_with_work", "Sprints", duration_min=60, if_planned=0.65, dimension_score=2),
        make_item(2, "skills", "Drills", duration_min=60, if_planned=0.60, dimension_score=2),
        make_item(3, "endurance_z2_short", "Steady", duration_min=60, if_planned=0.62, dimension_score=2),
    ]
    idx = make_index(pool)
    keys = []
    for ordinal, day in enumerate(("Mon", "Wed", "Fri")):
        res = ls.select(_slot(canonical_name="Endurance", role="filler", level=1, series_key=None,
                              day=day, filler_ordinal=ordinal, plan_week=1, block_id=None),
                        index=idx, used_items={})
        keys.append(res["library_key"])
    assert len(set(keys)) == 3


def test_variety_report_counts_spread_series_and_pool_use():
    idx = make_index(_vo2_pool())
    plan = {"weeks": [
        {"plan_week": 1, "days": [{"day": "Tue", "role": "intensity",
                                   "library_resolution": {"item_id": 1, "name_base": "Deep", "library_key": "vo2_classic"}}]},
        {"plan_week": 2, "days": [{"day": "Tue", "role": "intensity",
                                   "library_resolution": {"item_id": 2, "name_base": "Deep", "library_key": "vo2_classic"}},
                                  {"day": "Thu", "role": "intensity",
                                   "library_resolution": {"item_id": 2, "name_base": "Deep", "library_key": "vo2_classic"}}]},
    ]}
    series = {(1, "Tue", "VO2max 40/20"): {"family_key": "vo2_classic||Deep", "placed": 2}}
    rep = ls.variety_report(plan, idx, series)
    assert rep["sessions_resolved"] == 3 and rep["distinct_items"] == 2 and rep["distinct_families"] == 1
    assert rep["series"][0]["rungs"] == 2 and rep["series_sessions"] == 2
    assert rep["repeated_items"][0]["item_id"] == 2
    assert rep["same_week_family_repeats"] == ["vo2_classic||Deep@2"]
    assert rep["pool_utilisation"]["vo2_classic"] == {"used": 2, "pool": 6}


def test_a_family_is_freshly_started_at_most_twice_per_plan():
    pool = [
        make_item(1, "torque_starts_cadence", "Ladder", explicit_level=1, duration_min=60, if_planned=0.66, dimension_score=5),
        make_item(2, "torque_starts_cadence", "Spin-Ups", explicit_level=1, duration_min=60, if_planned=0.64, dimension_score=0),
    ]
    idx = make_index(pool)
    used = {}
    names = []
    for block, week in ((1, 1), (2, 4), (3, 7), (4, 10)):
        res = ls.select(_slot(canonical_name="Cadence Work", role="filler", level=1, series_key=None,
                              plan_week=week, block_id=block, day="Fri"), index=idx, used_items=used)
        names.append(res["name_base"] if res else None)
    assert names[:2] == ["Ladder", "Ladder"]
    assert names[2] == "Spin-Ups"
    # item 1 is at its plan-wide reuse cap and Spin-Ups is under the block
    # spread only once -- the 4th draw takes the family still under cap
    assert names[3] == "Spin-Ups"


def test_fresh_pick_avoids_a_family_already_placed_in_the_block():
    pool = [
        make_item(1, "torque_starts_cadence", "Ladder", explicit_level=1, duration_min=60, if_planned=0.66, dimension_score=5),
        make_item(2, "torque_starts_cadence", "Ladder", explicit_level=2, duration_min=62, if_planned=0.68, dimension_score=5),
        make_item(3, "torque_starts_cadence", "Spin-Ups", explicit_level=1, duration_min=60, if_planned=0.64, dimension_score=0),
    ]
    idx = make_index(pool)
    series, used = {}, {}
    fri = dict(canonical_name="Cadence Work", role="filler", series_key=(1, "Fri", "Cadence Work"), day="Fri")
    a = ls.select(_slot(plan_week=1, level=1, **fri), series_state=series, index=idx, used_items=used)
    b = ls.select(_slot(plan_week=2, level=2, **fri), series_state=series, index=idx, used_items=used)
    assert (a["name_base"], b["name_base"]) == ("Ladder", "Ladder")  # the pair progresses
    c = ls.select(_slot(plan_week=3, series_key=None, canonical_name="Cadence Work", role="filler", level=1, day="Wed"),
                  index=idx, used_items=used)
    assert c["name_base"] == "Spin-Ups"  # a fresh start in the same block takes another family


def test_filler_block_repeat_is_preferred_over_no_candidate_but_intensity_stays_hard():
    pool = [make_item(1, "endurance_with_work", "Only", duration_min=60, if_planned=0.65)]
    idx = make_index(pool)
    used = {}
    a = ls.select(_slot(canonical_name="Endurance", role="filler", series_key=None, plan_week=1, day="Tue"),
                  index=idx, used_items=used)
    b = ls.select(_slot(canonical_name="Endurance", role="filler", series_key=None, plan_week=2, day="Thu"),
                  index=idx, used_items=used)
    assert a is not None and b is not None  # a repeated easy hour beats a synthetic one
    hard = [make_item(2, "vo2_classic", "Solo", duration_min=60, if_planned=0.82)]
    idx2 = make_index(hard); used2 = {}
    assert ls.select(_slot(series_key=None, plan_week=1, day="Tue"), index=idx2, used_items=used2) is not None
    assert ls.select(_slot(series_key=None, plan_week=2, day="Thu"), index=idx2, used_items=used2) is None


def test_variety_report_counts_series_closed_by_the_rung_cap():
    idx = make_index(_vo2_pool())
    series = {ls._CLOSED_SERIES_KEY: [{"series_key": (1, "Tue", "X"), "family_key": "vo2_classic||Deep", "placed": 3}],
              (1, "Thu", "Y"): {"family_key": "vo2_classic||Solo", "placed": 1}}
    rep = ls.variety_report({"weeks": []}, idx, series)
    assert rep["series_sessions"] == 3 and rep["series"][0]["rungs"] == 3
