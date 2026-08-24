"""Regression tests for ae_lint (docs/ALGORITHM_EVIDENCE.md enforcement CLI).

Fixtures mirror the real defect classes found in the 2026-08-23 athlete audit:
the Stars-In-Your-Eyes 180s hard leaf, the Openers-v1.1 300s threshold step,
percentOfMaxHr endurance structures, bare Day Off cards, and cadence-critical
sessions without a programmed cadence target.
"""
from datetime import date

from ae_lint import lint_workout


def _structure(steps, metric="percentOfFtp"):
    return {
        "primaryIntensityMetric": metric,
        "structure": [
            {"type": "step", "length": {"value": 1, "unit": "repetition"},
             "steps": [s]} for s in steps
        ],
    }


def _step(seconds, lo, hi, cadence=None):
    targets = [{"minValue": lo, "maxValue": hi}]
    if cadence:
        targets.append({"minValue": cadence, "unit": "roundOrStridePerMinute"})
    return {"length": {"value": seconds, "unit": "second"}, "targets": targets}


RACE = date(2026, 9, 19)


def _rules(findings):
    return {(f["severity"], f["rule"]) for f in findings}


def test_taper_hard_rep_fails_inside_race_window():
    # AE-1.12: the real Sep-15 defect — 180s excursion to 95% at race-4d.
    w = {"title": "Anaerobic - Stars In Your Eyes", "workoutTypeValueId": 2,
         "workoutDay": "2026-09-15", "totalTimePlanned": 0.8,
         "structure": _structure([_step(180, 85, 95)])}
    assert ("FAIL", "AE-1.12") in _rules(lint_workout(w, RACE))


def test_race_eve_threshold_step_fails():
    # AE-1.12: the real Sep-18 defect — 300s @ 95% the day before the race.
    w = {"title": "Openers v1.1", "workoutTypeValueId": 2,
         "workoutDay": "2026-09-18", "totalTimePlanned": 0.72,
         "structure": _structure([_step(300, 95, 95)])}
    assert ("FAIL", "AE-1.12") in _rules(lint_workout(w, RACE))


def test_legit_race_sim_outside_10d_window_passes():
    # A hard race sim at race-14d is a legitimate last big session.
    w = {"title": "Race Sim - Full Dress Rehearsal", "workoutTypeValueId": 2,
         "workoutDay": "2026-09-05", "totalTimePlanned": 3.0,
         "structure": _structure([_step(600, 90, 100)])}
    assert not any(f["rule"] == "AE-1.12" for f in lint_workout(w, RACE))


def test_short_taper_rep_passes():
    w = {"title": "Sharpener 30/30s", "workoutTypeValueId": 2,
         "workoutDay": "2026-09-16", "totalTimePlanned": 0.9,
         "structure": _structure([_step(30, 110, 120)] * 10)}
    assert not any(f["rule"] == "AE-1.12" for f in lint_workout(w, RACE))


def test_maxhr_bike_structure_fails():
    # Ratified standard #8: bike structures are %FTP (the real Monika defect).
    w = {"title": "Endurance - (MxHr)", "workoutTypeValueId": 2,
         "workoutDay": "2026-08-21", "totalTimePlanned": 1.5,
         "structure": _structure([_step(3600, 60, 70)], metric="percentOfMaxHr")}
    assert ("FAIL", "WS-structure") in _rules(lint_workout(w, None))


def test_endurance_band_and_tss_rate_warn():
    w = {"title": "Endurance - Big Day", "workoutTypeValueId": 2,
         "workoutDay": "2026-08-20", "totalTimePlanned": 2.0,
         "tssPlanned": 116, "ifPlanned": 0.76,
         "structure": _structure([_step(7200, 70, 78)])}
    rules = _rules(lint_workout(w, None))
    assert ("WARN", "AE-2.8") in rules
    assert sum(1 for s, r in rules if r == "AE-2.8") == 1 or len(
        [f for f in lint_workout(w, None) if f["rule"] == "AE-2.8"]) == 2


def test_anaerobic_title_is_not_endurance():
    # "Anaerobic" must not match the endurance band via the "aerobic" substring.
    w = {"title": "Anaerobic Capacity Repeats", "workoutTypeValueId": 2,
         "workoutDay": "2026-08-20", "totalTimePlanned": 1.0,
         "tssPlanned": 80, "ifPlanned": 0.85,
         "structure": _structure([_step(60, 120, 130)])}
    assert not any(f["rule"] == "AE-2.8" for f in lint_workout(w, None))


def test_bare_day_off_warns_and_card_passes():
    bare = {"title": "Day Off", "workoutTypeValueId": 7, "workoutDay": "2026-08-24",
            "description": ""}
    card = {"title": "Day Off", "workoutTypeValueId": 7, "workoutDay": "2026-08-31",
            "description": "MOBILITY: 10min couch stretch + hip openers. Walk 20min. Sleep."}
    assert ("WARN", "WS-restday") in _rules(lint_workout(bare, None))
    assert not lint_workout(card, None)


def test_banned_names_fail():
    w = {"title": "FatMax Development L3", "workoutTypeValueId": 2,
         "workoutDay": "2026-08-25", "totalTimePlanned": 2.0}
    assert ("FAIL", "AE-3.11/AE-6.3") in _rules(lint_workout(w, None))


def test_session_floor_warns_and_exemptions_hold():
    short = {"title": "Midweek Spin Intervals", "workoutTypeValueId": 2,
             "workoutDay": "2026-08-26", "totalTimePlanned": 0.5}
    opener = {"title": "Pre-Race Openers", "workoutTypeValueId": 2,
              "workoutDay": "2026-08-26", "totalTimePlanned": 0.5}
    assert ("WARN", "AE-2.7") in _rules(lint_workout(short, None))
    assert not any(f["rule"] == "AE-2.7" for f in lint_workout(opener, None))


def test_vo2_proxy_band():
    # 6 x 3min @ 108-112 => 18min at >=106 => FAIL high edge is >18, so PASS..WARN
    good = {"title": "VO2max 5x3min", "workoutTypeValueId": 2,
            "workoutDay": "2026-08-27", "totalTimePlanned": 1.0,
            "structure": _structure([_step(180, 108, 112)] * 4)}   # 12 min => PASS
    under = {"title": "VO2max micro", "workoutTypeValueId": 2,
             "workoutDay": "2026-08-27", "totalTimePlanned": 1.0,
             "structure": _structure([_step(30, 108, 112)] * 4)}   # 2 min => FAIL
    assert not any(f["rule"] == "AE-3.1" for f in lint_workout(good, None))
    assert ("FAIL", "AE-3.1") in _rules(lint_workout(under, None))


def test_cadence_critical_needs_programmed_target():
    naked = {"title": "Cadence Work - 100-120rpm", "workoutTypeValueId": 2,
             "workoutDay": "2026-08-28", "totalTimePlanned": 0.9,
             "structure": _structure([_step(600, 60, 70)])}
    wired = {"title": "Cadence Work - 100-120rpm", "workoutTypeValueId": 2,
             "workoutDay": "2026-08-28", "totalTimePlanned": 0.9,
             "structure": _structure([_step(600, 60, 70, cadence=100)])}
    assert ("WARN", "AE-3.7") in _rules(lint_workout(naked, None))
    assert not any(f["rule"] == "AE-3.7" for f in lint_workout(wired, None))


def test_strength_sessions_exempt_from_bike_floor():
    # AE-2.7 floor is bike-scoped; TP type 9 = strength (open AE-8.4 ruling).
    w = {"title": "Foundation Strength A", "workoutTypeValueId": 9,
         "workoutDay": "2026-09-01", "totalTimePlanned": 0.5}
    assert not any(f["rule"] == "AE-2.7" for f in lint_workout(w, None))
