"""Regression tests for ae_lint (docs/ALGORITHM_EVIDENCE.md enforcement CLI).

Fixtures mirror the real defect classes found in the 2026-08-23 athlete audit:
the Stars-In-Your-Eyes 180s hard leaf, the Openers-v1.1 300s threshold step,
percentOfMaxHr endurance structures, bare Day Off cards, and cadence-critical
sessions without a programmed cadence target. The plan-level gates
(AE-1.14, AE-2.10) mirror the two same-day 2026-08-26 build failures: Jesse
Couch's v1 modeled 72 -> low-40s CTL by his A-race, and Kendall Aubertot's
load weeks anchored to a stale plan number instead of her demonstrated dose.
"""
import json
from datetime import date, timedelta

from ae_lint import (lint_demonstrated_dose, lint_ctl_trajectory, lint_race_day_tsb,
                     lint_taper_shape, lint_workout, main)


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


def test_test_titled_sessions_exempt_from_ws_structure():
    # Coach ruling 2026-08-24: assessments are legitimately RPE-structured
    # (authored ground truth) -- an RPE-metric bike structure titled as a
    # test/assessment must not FAIL the %FTP-structuring check the way a
    # genuinely mistagged endurance ride does (test_maxhr_bike_structure_
    # fails above).
    ftp_test = {"title": "FTP Test", "workoutTypeValueId": 2,
                "workoutDay": "2026-08-21", "totalTimePlanned": 1.0,
                "structure": _structure([_step(1200, 8, 10)], metric="rpe")}
    anaerobic_test = {"title": "Anaerobic Test", "workoutTypeValueId": 2,
                       "workoutDay": "2026-08-21", "totalTimePlanned": 1.0,
                       "structure": _structure([_step(60, 9, 10)], metric="rpe")}
    the_assessment = {"title": "Specialty - The Assessment - Functional Threshold",
                       "workoutTypeValueId": 2, "workoutDay": "2026-08-21",
                       "totalTimePlanned": 1.0,
                       "structure": _structure([_step(1200, 8, 10)], metric="rpe")}
    for w in (ftp_test, anaerobic_test, the_assessment):
        assert not any(f["rule"] == "WS-structure" for f in lint_workout(w, None)), w["title"]
    # A non-test RPE-metric bike structure is still caught -- the exemption
    # is title-scoped, not a blanket RPE carve-out.
    not_a_test = {"title": "Endurance - RPE ride", "workoutTypeValueId": 2,
                  "workoutDay": "2026-08-21", "totalTimePlanned": 1.0,
                  "structure": _structure([_step(3600, 5, 6)], metric="rpe")}
    assert ("FAIL", "WS-structure") in _rules(lint_workout(not_a_test, None))


# ---------------------------------------------------------- AE-1.14 CTL gate
def _daily_workouts(start, num_days, tss_per_day):
    """A workout on every day from `start` for `num_days` days, each
    carrying `tss_per_day` planned TSS (constant, or a callable of the
    zero-based day index)."""
    out = []
    for i in range(num_days):
        d = start + timedelta(days=i)
        tss = tss_per_day(i) if callable(tss_per_day) else tss_per_day
        out.append({"title": "Endurance", "workoutTypeValueId": 2,
                    "workoutDay": d.isoformat(), "totalTimePlanned": 1.0,
                    "tssPlanned": tss})
    return out


def test_ctl_gate_catches_jesse_shaped_drop():
    # Jesse's v1: modeled 72 -> low-40s at the A-race. Low, steady daily TSS
    # (43/day, well under the 72 CTL floor) over ~13 weeks drops CTL sharply.
    start = date(2026, 9, 1)
    race = date(2026, 12, 1)
    workouts = _daily_workouts(start, (race - start).days + 1, 43.0)
    findings = lint_ctl_trajectory(workouts, race, current_ctl=72.0)
    assert len(findings) == 1
    f = findings[0]
    assert f["rule"] == "AE-1.14"
    assert f["severity"] == "FAIL"
    assert f["day"] == race.isoformat()


def test_ctl_gate_passes_a_holding_payload():
    # Daily TSS held at the athlete's current CTL is the equilibrium load --
    # CTL doesn't move, so the gate must stay silent.
    start = date(2026, 9, 1)
    race = date(2026, 9, 21)
    workouts = _daily_workouts(start, (race - start).days + 1, 60.0)
    assert lint_ctl_trajectory(workouts, race, current_ctl=60.0) == []


def test_ctl_gate_silent_without_current_ctl_or_race():
    start = date(2026, 9, 1)
    race = date(2026, 12, 1)
    workouts = _daily_workouts(start, (race - start).days + 1, 20.0)
    assert lint_ctl_trajectory(workouts, race, current_ctl=None) == []
    assert lint_ctl_trajectory(workouts, None, current_ctl=72.0) == []


# ------------------------------------------------------ AE-2.10 dose gate
def _weekly_workouts(monday, weekly_tss):
    """One workout per week, each week's total planned TSS lumped onto its
    Monday -- the plan-level gate only cares about the weekly sum."""
    out = []
    for i, tss in enumerate(weekly_tss):
        d = monday + timedelta(weeks=i)
        out.append({"title": "Load Week" if tss >= 0 else "Recovery",
                    "workoutTypeValueId": 2, "workoutDay": d.isoformat(),
                    "totalTimePlanned": 1.0, "tssPlanned": tss})
    return out


def test_dose_gate_catches_kendall_shaped_underdose():
    # Kendall's build anchored load weeks to a stale plan number instead of
    # her demonstrated 800 TSS/week dose. Weeks: 650, 620 (load -- top
    # half), 280, 260 (recovery -- bottom half). 620 < 0.8*800=640 fails;
    # both recovery weeks < 0.5*800=400 warn (AE-1.9c).
    monday = date(2026, 8, 3)
    workouts = _weekly_workouts(monday, [650, 620, 280, 260])
    findings = lint_demonstrated_dose(workouts, demonstrated_load=800.0)
    rules = {(f["severity"], f["rule"]) for f in findings}
    assert ("FAIL", "AE-2.10") in rules
    assert ("WARN", "AE-1.9c") in rules
    fail_msgs = [f["msg"] for f in findings if f["rule"] == "AE-2.10"]
    assert any("620" in m for m in fail_msgs)


def test_dose_gate_passes_a_correctly_dosed_plan():
    # Load weeks at/above 80% of the 500 TSS/week demonstrated dose,
    # recovery weeks at/above 50% -- nothing should fire.
    monday = date(2026, 8, 3)
    workouts = _weekly_workouts(monday, [520, 480, 300, 280])
    assert lint_demonstrated_dose(workouts, demonstrated_load=500.0) == []


def test_dose_gate_silent_without_demonstrated_load():
    monday = date(2026, 8, 3)
    workouts = _weekly_workouts(monday, [650, 620, 280, 260])
    assert lint_demonstrated_dose(workouts, demonstrated_load=None) == []


# ------------------------------------------- both plan-level gates via CLI
def test_plan_gates_silent_in_cli_without_flags(tmp_path, capsys):
    # Same under-dosed, CTL-collapsing payload as above -- without
    # --current-ctl/--race-date or --demonstrated-load, neither AE-1.14 nor
    # AE-2.10 may appear, and the exit code must not reflect them.
    monday = date(2026, 8, 3)
    workouts = _weekly_workouts(monday, [650, 620, 280, 260])
    payload = {"workouts": workouts}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload))

    exit_code = main(["--json", str(path)])
    out = json.loads(capsys.readouterr().out)
    rules = {f["rule"] for f in out["findings"]}
    assert "AE-1.14" not in rules
    assert "AE-2.10" not in rules
    assert "AE-1.9c" not in rules
    assert exit_code == 0


# ---------------------------------------------------------- AE-1.16 TSB gate
def _tsb_workouts(day, tss=0.0):
    """A single workout on `day` -- just enough to seed `_daily_tss` with a
    real earliest-day so lint_race_day_tsb's CTL/ATL walk has something to
    walk from. Missing days between it and race default to 0 TSS anyway."""
    return [{"title": "Taper", "workoutTypeValueId": 2, "workoutDay": day.isoformat(),
             "totalTimePlanned": 1.0, "tssPlanned": tss}]


TSB_RACE = date(2026, 9, 21)


def test_tsb_gate_target_band_passes_clean():
    # S=80, seeded ATL=CTL, 2 zero-TSS taper days -> TSB ~= 17.5 (target
    # sub-band [15,25]) -- verified: 80 * ((41/42)^2 - (6/7)^2) = 17.46.
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=2))
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0, current_atl=80.0)
    assert findings == []


def test_tsb_gate_over_tapered_fails():
    # 5 zero-TSS taper days -> TSB ~= 33.9, above the +25 ceiling.
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=5))
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0, current_atl=80.0)
    assert ("FAIL", "AE-1.16") in _rules(findings)
    assert "outside" in findings[0]["msg"]


def test_tsb_gate_buried_fails():
    # No taper at all (CTL==ATL going into race) -> TSB == 0, below +5.
    workouts = _tsb_workouts(TSB_RACE)
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0, current_atl=80.0)
    assert ("FAIL", "AE-1.16") in _rules(findings)


def test_tsb_gate_in_band_under_target_warns():
    # 1 zero-TSS taper day -> TSB ~= 9.5: inside [5,25] but under the
    # [15,25] target sub-band.
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=1))
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0, current_atl=80.0)
    assert ("WARN", "AE-1.16") in _rules(findings)
    assert "under target" in findings[0]["msg"]


def test_tsb_gate_coach_override_downgrades_fail_to_warn():
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=5))
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0, current_atl=80.0,
                                  coach_override="athlete requested extra sharpening")
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == "WARN"
    assert f["rule"] == "AE-1.16"
    assert "athlete requested extra sharpening" in f["msg"]


def test_tsb_gate_assumed_atl_is_logged():
    # No --current-atl given -> assumed ATL=CTL at plan start, logged in msg.
    workouts = _tsb_workouts(TSB_RACE)
    findings = lint_race_day_tsb(workouts, TSB_RACE, current_ctl=80.0)
    assert ("FAIL", "AE-1.16") in _rules(findings)
    assert "ASSUMPTION" in findings[0]["msg"]


def test_tsb_gate_silent_without_flags():
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=5))
    assert lint_race_day_tsb(workouts, None, current_ctl=80.0) == []
    assert lint_race_day_tsb(workouts, TSB_RACE, current_ctl=None) == []


def test_tsb_gate_silent_in_cli_without_flags(tmp_path, capsys):
    workouts = _tsb_workouts(TSB_RACE - timedelta(days=5))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"workouts": workouts}))
    exit_code = main(["--json", str(path)])
    out = json.loads(capsys.readouterr().out)
    rules = {f["rule"] for f in out["findings"]}
    assert "AE-1.16" not in rules
    assert exit_code == 0


# ------------------------------------------------- AE-1.17/1.18 taper shape
def _taper_workout(day, tss=0.0, hard_seconds=0.0):
    w = {"title": "Taper Session", "workoutTypeValueId": 2, "workoutDay": day.isoformat(),
         "totalTimePlanned": 1.0, "tssPlanned": tss}
    if hard_seconds:
        w["structure"] = _structure([_step(hard_seconds, 93, 93)])
    return w


TAPER_RACE = date(2026, 9, 21)          # race day; window = 2026-09-07 .. 2026-09-20


def test_taper_shape_compliant_passes():
    workouts = [
        _taper_workout(date(2026, 9, 3), tss=100, hard_seconds=1000),   # pre-taper week
        _taper_workout(date(2026, 9, 10), tss=300, hard_seconds=750),   # window week 1
        _taper_workout(date(2026, 9, 14), tss=20),
        _taper_workout(date(2026, 9, 15), tss=20),
        _taper_workout(date(2026, 9, 16), tss=20),
        _taper_workout(date(2026, 9, 17), tss=20, hard_seconds=720),    # window week 2
        _taper_workout(date(2026, 9, 18), tss=25),
        _taper_workout(date(2026, 9, 19), tss=25),
        _taper_workout(date(2026, 9, 20), tss=25),                      # openers-shaped tail
    ]
    assert lint_taper_shape(workouts, TAPER_RACE) == []


def test_taper_shape_intensity_cut_fails():
    workouts = [
        _taper_workout(date(2026, 9, 3), tss=100, hard_seconds=1000),   # pre-taper week
        _taper_workout(date(2026, 9, 10), tss=300, hard_seconds=100),   # week1: 10% retention
        _taper_workout(date(2026, 9, 17), tss=250, hard_seconds=80),    # week2: decaying, low intensity
    ]
    findings = lint_taper_shape(workouts, TAPER_RACE)
    fails = [f for f in findings if f["severity"] == "FAIL" and f["rule"] == "AE-1.17"]
    assert len(fails) == 2
    assert not any(f["severity"] == "WARN" for f in findings)


def test_taper_shape_volume_increase_warns():
    workouts = [
        _taper_workout(date(2026, 9, 10), tss=300),   # window week 1
        _taper_workout(date(2026, 9, 14), tss=90),
        _taper_workout(date(2026, 9, 15), tss=90),
        _taper_workout(date(2026, 9, 16), tss=90),
        _taper_workout(date(2026, 9, 17), tss=90),
        _taper_workout(date(2026, 9, 18), tss=150),
        _taper_workout(date(2026, 9, 19), tss=150),
        _taper_workout(date(2026, 9, 20), tss=150),   # final 3d bump too large to qualify
    ]
    findings = lint_taper_shape(workouts, TAPER_RACE)
    assert ("WARN", "AE-1.17") in _rules(findings)
    assert not any(f["severity"] == "FAIL" for f in findings)


def test_taper_shape_ctl_loss_fails():
    # Single zero-TSS workout seeds the earliest day at taper-start+1, so
    # CTL-at-taper-start == current_ctl exactly (no walk before the
    # window); 14 zero-TSS days across the window then drop CTL to ~71% of
    # that -- well past the 10% cap.
    workouts = [_taper_workout(date(2026, 9, 8))]
    findings = lint_taper_shape(workouts, TAPER_RACE, current_ctl=100.0)
    assert ("FAIL", "AE-1.18") in _rules(findings)


def test_taper_shape_sub_300_pre_taper_skip():
    workouts = [
        _taper_workout(date(2026, 9, 3), tss=100, hard_seconds=200),    # below 300s floor
        _taper_workout(date(2026, 9, 10), tss=300, hard_seconds=10),
        _taper_workout(date(2026, 9, 17), tss=250, hard_seconds=5),
    ]
    assert not any(f["rule"] == "AE-1.17" for f in lint_taper_shape(workouts, TAPER_RACE))


def test_taper_shape_silent_without_race_date():
    workouts = [_taper_workout(date(2026, 9, 10), tss=300, hard_seconds=10)]
    assert lint_taper_shape(workouts, None) == []
    assert lint_taper_shape(workouts, None, current_ctl=100.0) == []
