#!/usr/bin/env python3
"""ae-lint — score TrainingPeaks workouts/calendars against the ratified
Algorithm Evidence rules (docs/ALGORITHM_EVIDENCE.md).

Self-contained on purpose: no pipeline imports, stdlib only, so it runs from
any repo or none. Every finding cites its AE rule ID. Severity FAIL means the
ratified standard is violated outright; WARN means it needs a human look.

Input formats (auto-detected per file):
  - TP calendar readback JSON: {"workouts": [...]} or a bare list of workouts
  - a single TP workout dict (has "structure" or "workoutDay"/"title")

Usage:
  ae_lint.py [--ftp WATTS] [--race-date YYYY-MM-DD] [--json] FILE [FILE...]

Exit codes: 0 clean, 1 findings with FAIL severity, 2 usage/parse error.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping

# ---------------------------------------------------------------- thresholds
# All numbers come from docs/ALGORITHM_EVIDENCE.md — cite the AE ID, never
# restate a number without one.
ENDURANCE_IF_LO, ENDURANCE_IF_HI = 0.60, 0.70          # ratified band (AE-2.8 pair)
ENDURANCE_TSS_PER_HR = 50.0                            # AE-2.8
SESSION_FLOOR_SECONDS = 45 * 60                        # AE-2.7
TAPER_MAX_HARD_REP_SECONDS = 120                       # AE-1.12
TAPER_HARD_WORK_SECONDS = 900                          # AE-1.12
TAPER_WINDOW_DAYS = 10                                 # AE-1.12: hard caps bind once rest
# begins; last major workout sits >=10d out, so a race sim at 11-14d out is
# legitimate and must not FAIL here.
HARD_PCT = 92.0                                        # >=92% FTP = "hard" (AE-1.12)
VO2_PCT = 106.0                                        # T@VO2max proxy (AE-3.1)
VO2_FAIL_LO, VO2_WARN_LO = 5 * 60, 8 * 60              # AE-3.1 FAIL<5m WARN 5-8m
VO2_PASS_HI, VO2_FAIL_HI = 14 * 60, 18 * 60            # AE-3.1 WARN 14-18m FAIL>18m
CADENCE_UNIT = "roundorstrideperminute"                # AE-3.7 / tp-cadence-encoding
CTL_TAU_DAYS = 42                                      # AE-1.14: standard CTL time constant
CTL_FAIL_FRACTION = 0.90                               # AE-1.14: >10% below current CTL = FAIL
LOAD_WEEK_FAIL_FRACTION = 0.80                         # AE-2.10: load week under 80% of demonstrated load = FAIL
RECOVERY_WEEK_WARN_FRACTION = 0.50                     # AE-1.9c: recovery week under 50% of demonstrated load = WARN

BANNED_NAME_RE = re.compile(r"fatmax|fat\s*max|fartlek|fasted", re.I)
ENDURANCE_NAME_RE = re.compile(r"endurance|(?<!an)aerobic|\bz2\b|zone\s*2|base\s+miles", re.I)
VO2_NAME_RE = re.compile(r"vo2|30/30|30-30|40/20|ronnestad|billat|hard\s*start", re.I)
CADENCE_CRITICAL_RE = re.compile(r"torque|sfr|cadence|spin[- ]?up|high[- ]?rpm|low[- ]?rpm", re.I)
# Coach ruling 2026-08-24 (AE assessment RPE exemption): assessments are
# legitimately RPE-structured -- authored ground truth, a test guided by RPE
# is the correct open-effort form. Self-contained duplicate of
# tp_structure_to_zwo.is_assessment_item's name convention (this file takes
# no pipeline imports by design) plus the house field-test naming ("FTP
# Test"/"Anaerobic Test"/"Field Test") -- test-titled sessions generally are
# exempt from the S1 percentOfFtp check below, not just the two pinned items.
TEST_TITLE_RE = re.compile(r"\bthe assessment\b|\b(?:anaerobic|ftp|field)\b.*\btest\b", re.I)
FLOOR_EXEMPT_RE = re.compile(
    r"recovery|opener|tune[- ]?up|rest\s*day|day\s*off|easy\s*spin|pre[- ]?ride"
    r"|strength|mobility|pre[- ]?plan|activation", re.I)
BIKE_TYPE_IDS = {2}           # TP workoutTypeValueId: 2 = bike
DAY_OFF_TYPE_IDS = {7}        # 7 = Day Off / rest


# ---------------------------------------------------------------- structure
def _steps(structure: Mapping[str, Any] | None) -> Iterator[dict]:
    """Yield flattened executable steps {seconds, lo, hi, cadence} from a TP
    structure dict. Repetitions are expanded. Percent targets only; cadence
    targets surface as cadence=True on the step. Uses max(maxValue,minValue)
    for the hard edge — mirrors library_selector's excursion counting."""
    if not structure:
        return
    for element in structure.get("structure") or []:
        reps = 1
        if (element.get("type") or "").lower() == "repetition":
            reps = int((element.get("length") or {}).get("value") or 1)
        steps = element.get("steps") or []
        for _ in range(max(reps, 1)):
            for step in steps:
                length = step.get("length") or {}
                if (length.get("unit") or "").lower() not in ("second", "seconds"):
                    continue
                seconds = float(length.get("value") or 0)
                lo = hi = 0.0
                cadence = False
                for target in step.get("targets") or []:
                    unit = (target.get("unit") or "").lower()
                    if unit == CADENCE_UNIT:
                        cadence = True
                        continue
                    mn = float(target.get("minValue") or 0)
                    mx = float(target.get("maxValue") or 0)
                    lo, hi = mn, max(mn, mx)
                yield {"seconds": seconds, "lo": lo, "hi": hi, "cadence": cadence}


def _hard_seconds(structure) -> tuple[float, float]:
    """(total seconds with any >=92% excursion, longest single such rep)."""
    total = longest = 0.0
    for step in _steps(structure):
        if step["hi"] >= HARD_PCT:
            total += step["seconds"]
            longest = max(longest, step["seconds"])
    return total, longest


def _vo2_seconds(structure) -> float:
    return sum(s["seconds"] for s in _steps(structure) if s["hi"] >= VO2_PCT)


def _has_cadence_target(structure) -> bool:
    return any(s["cadence"] for s in _steps(structure))


# ---------------------------------------------------------------- checks
def lint_workout(w: Mapping[str, Any], race: date | None) -> list[dict]:
    findings: list[dict] = []
    title = (w.get("title") or "").strip()
    desc = w.get("description") or ""
    type_id = w.get("workoutTypeValueId")
    structure = w.get("structure") if isinstance(w.get("structure"), Mapping) else None
    day = (w.get("workoutDay") or "")[:10]
    hours = float(w.get("totalTimePlanned") or 0)
    tss = float(w.get("tssPlanned") or 0)
    if_planned = float(w.get("ifPlanned") or 0)

    def add(severity, rule, msg):
        findings.append({"day": day, "title": title or "(untitled)",
                         "severity": severity, "rule": rule, "msg": msg})

    # N1 — banned names (AE-3.11, AE-6.3)
    if BANNED_NAME_RE.search(title) or BANNED_NAME_RE.search(desc[:400]):
        add("FAIL", "AE-3.11/AE-6.3", "banned concept (FatMax/fartlek/fasted) in name or copy")

    # Rest days — must carry an active-recovery body (ratified rest-day rule)
    if type_id in DAY_OFF_TYPE_IDS:
        if structure is None and len(desc.strip()) < 40:
            add("WARN", "WS-restday", "bare Day Off — no active-recovery/mobility card")
        return findings  # nothing below applies to rest days

    is_endurance = bool(ENDURANCE_NAME_RE.search(title))
    floor_exempt = bool(FLOOR_EXEMPT_RE.search(title))

    # S1 — %FTP structuring for bike workouts (ratified standard #8).
    # Test-titled sessions (assessments) are exempt (see TEST_TITLE_RE
    # above) -- an RPE-structured field test is the authored, correct form,
    # not a metric violation.
    metric = (structure or {}).get("primaryIntensityMetric") or ""
    if (structure and type_id in BIKE_TYPE_IDS and metric and metric != "percentOfFtp"
            and not TEST_TITLE_RE.search(title)):
        add("FAIL", "WS-structure", f"bike structure metric is {metric}, not percentOfFtp")

    # E1/E2 — endurance band + load rate (AE-2.8 + ratified IF band)
    if is_endurance and hours > 0:
        if if_planned and not (ENDURANCE_IF_LO <= if_planned <= ENDURANCE_IF_HI):
            add("WARN", "AE-2.8", f"endurance IF {if_planned:.2f} outside {ENDURANCE_IF_LO:.2f}-{ENDURANCE_IF_HI:.2f}")
        if tss and tss / hours > ENDURANCE_TSS_PER_HR:
            add("WARN", "AE-2.8", f"endurance {tss / hours:.1f} TSS/hr exceeds {ENDURANCE_TSS_PER_HR:.0f}")

    # F1 — session floor (AE-2.7). Strength (TP type 9) is exempt pending the
    # open AE-8.4 ruling; non-bike types are out of this floor's scope.
    if (hours and hours * 3600 < SESSION_FLOOR_SECONDS and not floor_exempt
            and type_id in BIKE_TYPE_IDS):
        add("WARN", "AE-2.7", f"{hours * 60:.0f} min session under the 45-min floor (no exemption matched)")

    # T1 — taper/race-week hard caps (AE-1.12), needs --race-date
    if race and day:
        try:
            delta = (race - datetime.strptime(day, "%Y-%m-%d").date()).days
        except ValueError:
            delta = None
        if delta is not None and 0 <= delta <= TAPER_WINDOW_DAYS and structure:
            total, longest = _hard_seconds(structure)
            if longest > TAPER_MAX_HARD_REP_SECONDS:
                add("FAIL", "AE-1.12", f"race-{delta}d: single >={HARD_PCT:.0f}% rep of {longest:.0f}s (cap {TAPER_MAX_HARD_REP_SECONDS}s)")
            if total > TAPER_HARD_WORK_SECONDS:
                add("FAIL", "AE-1.12", f"race-{delta}d: {total:.0f}s total >={HARD_PCT:.0f}% work (cap {TAPER_HARD_WORK_SECONDS}s)")

    # V1 — T@VO2max proxy gate (AE-3.1)
    if structure and VO2_NAME_RE.search(title):
        vo2 = _vo2_seconds(structure)
        if vo2 < VO2_FAIL_LO or vo2 > VO2_FAIL_HI:
            add("FAIL", "AE-3.1", f"T@VO2max proxy {vo2 / 60:.1f} min (PASS 8-14, FAIL <5 or >18)")
        elif vo2 < VO2_WARN_LO or vo2 > VO2_PASS_HI:
            add("WARN", "AE-3.1", f"T@VO2max proxy {vo2 / 60:.1f} min (PASS band 8-14)")

    # C1 — cadence-critical sessions carry a programmed cadence target (AE-3.7)
    if structure and CADENCE_CRITICAL_RE.search(title) and not _has_cadence_target(structure):
        add("WARN", "AE-3.7", "cadence-critical name but no programmed cadence target in structure")

    return findings


# ---------------------------------------------------------------- plan-level gates
def _workout_day(w: Mapping[str, Any]) -> date | None:
    try:
        return datetime.strptime((w.get("workoutDay") or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _daily_tss(workouts: list[dict]) -> dict[date, float]:
    daily: dict[date, float] = {}
    for w in workouts:
        d = _workout_day(w)
        if d is None:
            continue
        daily[d] = daily.get(d, 0.0) + float(w.get("tssPlanned") or 0)
    return daily


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weekly_totals(workouts: list[dict]) -> dict[date, float]:
    totals: dict[date, float] = {}
    for w in workouts:
        d = _workout_day(w)
        if d is None:
            continue
        wk = _week_start(d)
        totals[wk] = totals.get(wk, 0.0) + float(w.get("tssPlanned") or 0)
    return totals


def lint_ctl_trajectory(workouts: list[dict], race: date | None,
                         current_ctl: float | None) -> list[dict]:
    """AE-1.14 — CTL trajectory gate. Models the standard 42-day
    time-constant CTL path (missing days = 0 TSS) from the plan's earliest
    workout day through race day, starting from `current_ctl`. FAIL if the
    modeled CTL at race day is more than CTL_FAIL_FRACTION below current
    CTL; WARN if it's below current CTL at all. Silent (returns []) unless
    both `race` and `current_ctl` are supplied."""
    if race is None or current_ctl is None:
        return []
    daily = _daily_tss(workouts)
    days = list(daily.keys())
    if not days:
        return []
    start = min(min(days), race) - timedelta(days=1)
    if race <= start:
        return []
    ctl = current_ctl
    d = start
    while d < race:
        d += timedelta(days=1)
        ctl += (daily.get(d, 0.0) - ctl) / CTL_TAU_DAYS

    if ctl < current_ctl * CTL_FAIL_FRACTION:
        severity = "FAIL"
    elif ctl < current_ctl:
        severity = "WARN"
    else:
        return []
    drop_pct = (1 - ctl / current_ctl) * 100 if current_ctl else 0.0
    return [{"day": race.isoformat(), "title": "(plan CTL trajectory)",
             "severity": severity, "rule": "AE-1.14",
             "msg": f"modeled CTL at race day {ctl:.1f}, down {drop_pct:.0f}% from "
                    f"current CTL {current_ctl:.1f}"}]


def lint_demonstrated_dose(workouts: list[dict],
                            demonstrated_load: float | None) -> list[dict]:
    """AE-2.10 (+ AE-1.9c sharpen) — demonstrated-dose gate. No explicit
    phase tags exist in a TP payload, so weeks are classified by a simple
    top-half/bottom-half split of the plan's own weekly planned-TSS
    distribution: top half (>= median) stands in for intended load weeks,
    bottom half for recovery weeks. Load weeks under LOAD_WEEK_FAIL_FRACTION
    of the demonstrated weekly load FAIL; recovery weeks under
    RECOVERY_WEEK_WARN_FRACTION WARN (AE-1.9c). Silent (returns []) unless
    `demonstrated_load` is supplied or there are fewer than 2 weeks of data."""
    if not demonstrated_load:
        return []
    totals = _weekly_totals(workouts)
    if len(totals) < 2:
        return []
    median = statistics.median(totals.values())
    findings: list[dict] = []
    for wk in sorted(totals):
        total = totals[wk]
        if total >= median:
            if total < LOAD_WEEK_FAIL_FRACTION * demonstrated_load:
                findings.append({"day": wk.isoformat(), "title": "(load week)",
                                 "severity": "FAIL", "rule": "AE-2.10",
                                 "msg": f"{total:.0f} TSS under-dosed vs demonstrated "
                                        f"load {demonstrated_load:.0f} "
                                        f"(< {LOAD_WEEK_FAIL_FRACTION:.0%})"})
        else:
            if total < RECOVERY_WEEK_WARN_FRACTION * demonstrated_load:
                findings.append({"day": wk.isoformat(), "title": "(recovery week)",
                                 "severity": "WARN", "rule": "AE-1.9c",
                                 "msg": f"{total:.0f} TSS under "
                                        f"{RECOVERY_WEEK_WARN_FRACTION:.0%} of demonstrated "
                                        f"load {demonstrated_load:.0f}"})
    return findings


# ---------------------------------------------------------------- io
def _workouts(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [w for w in payload if isinstance(w, dict)]
    if isinstance(payload, dict):
        for key in ("workouts", "items", "Workouts", "w"):
            if isinstance(payload.get(key), list):
                return [w for w in payload[key] if isinstance(w, dict)]
        if "title" in payload or "structure" in payload or "workoutDay" in payload:
            return [payload]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--ftp", type=float, default=None, help="reserved (structure targets are %%FTP already)")
    parser.add_argument("--race-date", type=str, default=None, help="YYYY-MM-DD — enables AE-1.12 taper/race-week caps + AE-1.14 CTL gate")
    parser.add_argument("--current-ctl", type=float, default=None, help="athlete's current CTL — enables the AE-1.14 CTL trajectory gate (requires --race-date)")
    parser.add_argument("--demonstrated-load", type=float, default=None, help="athlete's demonstrated weekly load-week TSS — enables the AE-2.10 dose gate")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    race = None
    if args.race_date:
        try:
            race = datetime.strptime(args.race_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ae-lint: bad --race-date {args.race_date!r}", file=sys.stderr)
            return 2

    all_findings: list[dict] = []
    all_workouts: list[dict] = []
    total_workouts = 0
    for path in args.files:
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ae-lint: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        workouts = _workouts(payload)
        total_workouts += len(workouts)
        all_workouts.extend(workouts)
        for w in workouts:
            for finding in lint_workout(w, race):
                finding["file"] = str(path)
                all_findings.append(finding)

    # Plan-level gates (span the whole payload, not a single workout) —
    # both silent unless their inputs are supplied.
    plan_file = str(args.files[0]) if len(args.files) == 1 else "(plan)"
    for finding in lint_ctl_trajectory(all_workouts, race, args.current_ctl):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_demonstrated_dose(all_workouts, args.demonstrated_load):
        finding["file"] = plan_file
        all_findings.append(finding)

    all_findings.sort(key=lambda f: (f["day"], f["severity"] != "FAIL"))
    fails = sum(1 for f in all_findings if f["severity"] == "FAIL")
    warns = len(all_findings) - fails

    if args.json:
        print(json.dumps({"workouts": total_workouts, "fail": fails,
                          "warn": warns, "findings": all_findings}, indent=2))
    else:
        for f in all_findings:
            print(f"{f['severity']:4} {f['day'] or '----------'}  {f['rule']:14} {f['title'][:44]:44} {f['msg']}")
        print(f"\nae-lint: {total_workouts} workouts — {fails} FAIL, {warns} WARN"
              f" (rules: docs/ALGORITHM_EVIDENCE.md)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
