#!/usr/bin/env python3
"""ae-lint — score TrainingPeaks workouts/calendars against the ratified
Algorithm Evidence rules (docs/ALGORITHM_EVIDENCE.md).

Self-contained on purpose: no pipeline imports, stdlib only, so it runs from
any repo or none. Every finding cites its AE rule ID. Severity FAIL means the
ratified standard is violated outright; WARN means it needs a human look.

Input formats (auto-detected per file):
  - TP calendar readback JSON: {"workouts": [...]} or a bare list of workouts
  - a single TP workout dict (has "structure" or "workoutDay"/"title")
  - TP notes_payload.json: a bare list of {title, noteDate, description}
    dicts, or {"notes": [...]} -- feeds the AE-9.11 voice gate only

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
ATL_TAU_DAYS = 7                                       # AE-1.20: default ATL time constant (fixed, categorical-only)
TSB_RACE_MIN, TSB_RACE_MAX = 5.0, 25.0                 # AE-1.16: race-day TSB band
TSB_RACE_TARGET_MIN = 15.0                             # AE-1.16: target sub-band floor (target is [15,25])
TAPER_SHAPE_WINDOW_DAYS = 14                           # AE-1.17/1.18: fixed taper-shape window (race-14..race-1)
TAPER_OPENER_BUMP_MAX = 0.30                           # AE-1.17: default openers bump ceiling, final 3 days only
TAPER_INTENSITY_RETENTION = 0.70                       # AE-1.17: X=70 ratified by Matti 2026-08-26
TAPER_INTENSITY_FLOOR_SECONDS = 300                    # AE-1.17: pre-taper week under this = nothing to retain, skip
CTL_TAPER_RETENTION_FRACTION = 0.90                    # AE-1.18: race-day CTL >= 90% of CTL at taper start
MIN_LEN_FOR_VOICE_CHECK = 60                           # AE-9.11: floor below which a card is a legitimately
# short mechanical card (interval list, rest-day one-liner) with no voice to
# check -- not tuned to the doc's "~200 chars" prose since the real pinned
# examples (Motoren's real notes, 65-86 chars; Forest's pre-fix leak, 188
# chars) are all under 200. Tuned 2026-08-29 against those exact strings.

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

# AE-9.11 -- first-person coach voice. (a) internal-leak markers: coach-only
# metadata that must never render athlete-facing (Forest Hietpas Week-1 note,
# 2026-08-29). Documented as a growing list -- add a marker + label pair
# here, never inline. (b) second/first-person pronoun regexes for the
# impersonal-construction check, below.
INTERNAL_LEAK_MARKERS: list[tuple[str, re.Pattern]] = [
    ("AE rule citation", re.compile(r"\bAE-\d")),
    ("coach-confirmed citation", re.compile(r"coach-confirmed", re.I)),
    ("%FTP engine-structure jargon",
     re.compile(r"\bstructure\b(?:(?!\.).){0,30}\brun[s]?\b(?:(?!\.).){0,10}%\s?FTP", re.I)),
    ("re-anchored jargon", re.compile(r"re-anchored", re.I)),
    ("no-A-race internal shorthand", re.compile(r"\bno\s+A-race\b", re.I)),
    ("week_type field name", re.compile(r"\bweek_type\b")),
    ("coached_block field name", re.compile(r"\bcoached_block\b")),
    ("profile.yaml path", re.compile(r"profile\.yaml")),
    ("archetype jargon", re.compile(r"\barchetype\b", re.I)),
    ("library_key field name", re.compile(r"\blibrary_key\b")),
    ("RUN-LIB jargon", re.compile(r"\bRUN-LIB\b")),
    ("Motoren engine name", re.compile(r"\bMotoren\b")),
    # Quoted coach speech about the athlete (e.g. `"300 is about right"`)
    # is folded into this marker rather than standing alone: a bare
    # quoted-string regex fired on ordinary quoted titles ("Recovery
    # Week", "Start Line") and on AE-9.4's verbatim workout-comment
    # template ("e.g., ... or \"Felt sluggish to start\"") across nearly
    # every athlete in the 2026-08-29 sweep -- false positives, not leaks.
    # The real defect shape is a quoted remark sitting inside a
    # coach-confirmed provenance parenthetical, which this catches without
    # the noise.
    ("parenthetical ISO-date citation",
     re.compile(r"\([^()]{0,60}\d{4}-\d{2}-\d{2}[^()]{0,60}\)")),
    ("quoted coach speech in a provenance citation",
     re.compile(r'\(\s*coach-confirmed\b[^()]*"[A-Za-z0-9][^"]{2,60}"[^()]*\)', re.I)),
]
SECOND_PERSON_RE = re.compile(r"\byou\b|\byour\b", re.I)
FIRST_PERSON_RE = re.compile(r"\bi'm\b|\bi've\b|\bi'll\b|\bi\b|\bmy\b|\bme\b", re.I)

# AE-9.11 narrowing (Matti ruling 2026-08-29: "The rule is over broad.").
# A numbered/bulleted instruction line is tactical race or workout direction
# -- "Sit in and don't pull for free", "Fuel at your long-ride rate". There is
# no coaching judgment in it to attribute, so there is no natural place for
# the coach's "I", and demanding one produces worse copy. The voice rule
# exists for NARRATIVE copy -- the prose that frames the week and explains
# what the coach wants ("I've built more work into this week than you're used
# to"). So the impersonal-construction check now runs on prose lines only.
# Trigger case: Eric Quiat's Mad Gravel race-day brief, which Matti edited by
# hand into exactly the shape he wanted and which the rule then flagged.
LIST_ITEM_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+")


def _prose_only(text: str) -> str:
    """Drop numbered/bulleted instruction lines, keeping narrative prose."""
    return "\n".join(
        line for line in text.splitlines() if not LIST_ITEM_RE.match(line))


# RPE -> (%FTP low, %FTP high). MIRRORS tp_structure_to_zwo._RPE_TO_PCT_FTP
# verbatim -- ae_lint stays import-free of the pipeline by design, so the
# table is duplicated rather than imported; keep the two in sync. Without
# this decode every RPE-metric structure reads as ZERO hard seconds, which
# silently disabled the AE-1.12 caps and the AE-1.17 taper-intensity gate
# for every RPE-authored plan (live defect found 2026-08-29).
RPE_TO_PCT_FTP = {
    1: (40.0, 50.0), 2: (50.0, 60.0), 3: (50.0, 60.0), 4: (60.0, 70.0),
    5: (60.0, 70.0), 6: (76.0, 90.0), 7: (76.0, 90.0), 8: (95.0, 110.0),
    9: (95.0, 110.0), 10: (115.0, 130.0),
}
RPE_METRICS = ("rpe", "perceivedexertion", "percentofmaxhr_rpe")


# ---------------------------------------------------------------- structure
def _steps(structure: Mapping[str, Any] | None) -> Iterator[dict]:
    """Yield flattened executable steps {seconds, lo, hi, cadence} from a TP
    structure dict. Repetitions are expanded. Percent targets only; cadence
    targets surface as cadence=True on the step. Uses max(maxValue,minValue)
    for the hard edge — mirrors library_selector's excursion counting."""
    if not structure:
        return
    metric = str(structure.get("primaryIntensityMetric") or "").lower()
    is_rpe = metric in RPE_METRICS
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
                    if is_rpe:
                        # decode RPE points -> %FTP band before any comparison
                        lo_pct = RPE_TO_PCT_FTP.get(int(round(mn)), (0.0, 0.0))[0]
                        hi_pct = RPE_TO_PCT_FTP.get(int(round(max(mn, mx))),
                                                    (0.0, 0.0))[1]
                        mn, mx = lo_pct, hi_pct
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


def _voice_findings(day: str, title: str, text: str) -> list[dict]:
    """Shared AE-9.11 checks for one athlete-facing text blob (a workout
    description or a calendar/plan note). Leak markers are searched over
    title+text combined (a leak can hide in either); the impersonal-
    construction check runs on `text` alone -- titles are too short to
    carry the "gives instruction" signal."""
    findings: list[dict] = []
    combined = f"{title}\n{text}" if title else text
    for label, pattern in INTERNAL_LEAK_MARKERS:
        m = pattern.search(combined)
        if m:
            findings.append({"day": day, "title": title or "(untitled)",
                             "severity": "FAIL", "rule": "AE-9.11",
                             "msg": f"coach-internal leak ({label}): {m.group(0)!r}"})
    # The first-person marker may live anywhere in the card, but the
    # second-person address that DEMANDS one only counts if it appears in
    # narrative prose -- see _prose_only and the AE-9.11 narrowing note.
    prose = _prose_only(text)
    if len(text) >= MIN_LEN_FOR_VOICE_CHECK:
        if SECOND_PERSON_RE.search(prose) and not FIRST_PERSON_RE.search(text):
            findings.append({"day": day, "title": title or "(untitled)",
                             "severity": "WARN", "rule": "AE-9.11",
                             "msg": "second-person instruction with no first-person coach voice (impersonal construction)"})
    return findings


def lint_voice(workouts: list[dict], notes: list[dict] | None = None) -> list[dict]:
    """AE-9.11 -- first-person coach voice. On by DEFAULT, no flag: this is
    an always-on quality gate, not opt-in. Two checks over every
    athlete-facing title/description in `workouts` and `notes` (TP calendar
    notes -- weekly/mid-week story notes, self-review templates, etc.):
      (a) internal-leak markers (INTERNAL_LEAK_MARKERS) -- coach-internal
          metadata (rule IDs, config field names, engine jargon, FTP
          provenance, quoted coach speech) bleeding into athlete-facing
          copy. FAIL.
      (b) impersonal construction -- NARRATIVE text (>=
          MIN_LEN_FOR_VOICE_CHECK chars) using second-person address
          ("you"/"your") with no first-person coach marker ("I", "I'm",
          "I've", "I'll", "my", "me"). WARN. Two exemptions, both
          deliberate: short mechanical cards fall under the length floor,
          and numbered/bulleted instruction lines are stripped before the
          second-person search (see _prose_only). The first-person marker
          still counts wherever it appears in the card -- only the
          second-person address that DEMANDS one is restricted to prose.
    Source: Matti ruling 2026-08-29 ("you have to write it in first
    person" / "in the future that needs to be a gate."), Forest Hietpas
    block review. NARROWED by Matti ruling 2026-08-29 ("The rule is over
    broad.") after it flagged Eric Quiat's Mad Gravel race-day brief --
    a tactical card of facts plus numbered race instructions that Matti
    had just hand-edited into the exact shape he wanted. Tactical
    direction carries no coaching judgment to attribute, so it has no
    natural place for "I"; forcing one produces worse copy. The voice
    rule is for prose that frames the block and says what the coach
    wants.
    """
    findings: list[dict] = []
    for w in workouts:
        title = (w.get("title") or "").strip()
        text = w.get("description") or ""
        day = (w.get("workoutDay") or "")[:10]
        findings.extend(_voice_findings(day, title, text))
    for n in notes or []:
        title = (n.get("title") or "").strip()
        text = n.get("description") or ""
        day = (n.get("noteDate") or "")[:10]
        findings.extend(_voice_findings(day, title, text))
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


def _weekly_hard_seconds(workouts: list[dict]) -> dict[date, float]:
    """Sum of AE-1.12 hard-seconds (_hard_seconds total, >=92% FTP) per
    calendar week -- mirrors _weekly_totals but for hard-seconds instead of
    TSS. Used by the AE-1.17 taper intensity-retention check."""
    totals: dict[date, float] = {}
    for w in workouts:
        d = _workout_day(w)
        if d is None:
            continue
        structure = w.get("structure") if isinstance(w.get("structure"), Mapping) else None
        if not structure:
            continue
        hard, _ = _hard_seconds(structure)
        wk = _week_start(d)
        totals[wk] = totals.get(wk, 0.0) + hard
    return totals


def _model_ctl_atl(daily: dict[date, float], seed_day: date, seed_ctl: float,
                    seed_atl: float, through_day: date) -> tuple[float, float]:
    """Walk the CTL(tau=42)/ATL(tau=7) recurrence day-by-day from `seed_day`
    (exclusive) through `through_day` (inclusive), starting from
    seed_ctl/seed_atl. Missing days = 0 TSS. Returns (ctl, atl) at
    `through_day` -- the seed pair unchanged if through_day <= seed_day.
    Shared by lint_race_day_tsb (AE-1.16) and lint_taper_shape's CTL-
    retention check (AE-1.18)."""
    ctl, atl = seed_ctl, seed_atl
    d = seed_day
    while d < through_day:
        d += timedelta(days=1)
        tss = daily.get(d, 0.0)
        ctl += (tss - ctl) / CTL_TAU_DAYS
        atl += (tss - atl) / ATL_TAU_DAYS
    return ctl, atl


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


def lint_race_day_tsb(workouts: list[dict], race: date | None,
                       current_ctl: float | None, current_atl: float | None = None,
                       coach_override: str | None = None) -> list[dict]:
    """AE-1.16 -- race-day TSB gate. TSB(race) = CTL(race-1) - ATL(race-1)
    (Coggan: yesterday's values), modeled by walking the CTL(tau=42)/
    ATL(tau=7) recurrence day-by-day from `current_ctl`/`current_atl`
    through the day before race day. FAIL if TSB(race) falls outside
    [TSB_RACE_MIN, TSB_RACE_MAX]; WARN if it's inside that band but under
    the target sub-band floor (TSB_RACE_TARGET_MIN). `--coach-override`
    downgrades a FAIL to WARN, logging the reason. If `current_atl` isn't
    supplied, ATL is assumed equal to CTL at plan start (TSB=0 baseline) --
    an explicit, logged ASSUMPTION, never a silent default. Silent (returns
    []) unless both `race` and `current_ctl` are supplied."""
    if race is None or current_ctl is None:
        return []
    assumed_atl = current_atl is None
    seed_atl = current_ctl if assumed_atl else current_atl
    daily = _daily_tss(workouts)
    days = list(daily.keys())
    if not days:
        return []
    start = min(min(days), race) - timedelta(days=1)
    tsb_day = race - timedelta(days=1)
    if tsb_day < start:
        return []
    if tsb_day == start:
        ctl_y, atl_y = current_ctl, seed_atl
    else:
        ctl_y, atl_y = _model_ctl_atl(daily, start, current_ctl, seed_atl, tsb_day)
    tsb = ctl_y - atl_y

    if tsb < TSB_RACE_MIN or tsb > TSB_RACE_MAX:
        severity = "FAIL"
    elif tsb < TSB_RACE_TARGET_MIN:
        severity = "WARN"
    else:
        return []

    assumption_note = (f" [ASSUMPTION: no --current-atl given, seeded ATL=CTL="
                        f"{current_ctl:.1f} at plan start]" if assumed_atl else "")
    band = f"[{TSB_RACE_MIN:.0f}, {TSB_RACE_MAX:.0f}]"
    if severity == "FAIL" and coach_override:
        severity = "WARN"
        msg = (f"modeled race-day TSB {tsb:.1f} outside {band} -- "
               f"coach override: {coach_override}{assumption_note}")
    elif severity == "FAIL":
        msg = f"modeled race-day TSB {tsb:.1f} outside {band}{assumption_note}"
    else:
        target = f"[{TSB_RACE_TARGET_MIN:.0f}, {TSB_RACE_MAX:.0f}]"
        msg = (f"modeled race-day TSB {tsb:.1f} inside {band} but under "
               f"target sub-band {target}{assumption_note}")

    return [{"day": race.isoformat(), "title": "(race-day TSB)",
             "severity": severity, "rule": "AE-1.16", "msg": msg}]


def _race_weeks(workouts: list[dict]) -> set:
    """Weeks (Monday-anchored date) containing a race-day-shaped card: no
    structure but tssPlanned >= 100, or a title starting with RACE/EVENT.
    Such weeks carry real intensity invisibly (race cards have TSS but no
    step structure), so AE-1.17's intensity-retention check exempts them."""
    weeks = set()
    for w in workouts:
        day = _workout_day(w)
        if day is None:
            continue
        title = str(w.get("title") or "")
        structured = bool(w.get("structure"))
        tss = w.get("tssPlanned") or 0
        if (not structured and tss >= 100) or re.match(r"\s*(RACE|EVENT)\b", title):
            weeks.add(_week_start(day))
    return weeks


def lint_taper_shape(workouts: list[dict], race: date | None,
                      current_ctl: float | None = None) -> list[dict]:
    """AE-1.17/1.18 -- taper shape gates. Taper window is fixed at the
    TAPER_SHAPE_WINDOW_DAYS calendar days immediately before race day
    (race-14 .. race-1 inclusive) -- a documented fixed-constant
    simplification of AE-1.17's duration-scaled 8-21d window (matches this
    file's existing fixed-constant style, see TAPER_WINDOW_DAYS for
    AE-1.12). Three checks, all silent unless `race` is supplied; the third
    additionally needs `current_ctl`:
      (a) volume decay -- weekly TSS inside the window (via _weekly_totals)
          must not increase week over week, except a single final-week
          increase that's explained entirely by an AE-1.17 opener in the
          window's last 3 days (<=TAPER_OPENER_BUMP_MAX over the
          immediately-prior 3-day load). WARN, rule AE-1.17.
      (b) intensity retention -- weekly hard-seconds (AE-1.12 >=92%FTP
          seconds, via _weekly_hard_seconds) inside the window must stay
          >= TAPER_INTENSITY_RETENTION of the last pre-taper week's
          hard-seconds (Matti ruling 2026-08-26). Silently skipped if that
          pre-taper week had < TAPER_INTENSITY_FLOOR_SECONDS hard-seconds
          (nothing to retain). FAIL, rule AE-1.17.
      (c) CTL retention -- race-day modeled CTL must stay >=
          CTL_TAPER_RETENTION_FRACTION of CTL at taper start (AE-1.18,
          joins AE-1.14). FAIL, rule AE-1.18.
    """
    if race is None:
        return []
    findings: list[dict] = []
    window_start = race - timedelta(days=TAPER_SHAPE_WINDOW_DAYS)
    window_end = race - timedelta(days=1)
    daily = _daily_tss(workouts)

    # (a) volume decay --------------------------------------------------
    totals = _weekly_totals(workouts)
    window_weeks = sorted(wk for wk in totals
                           if wk <= window_end and wk + timedelta(days=6) >= window_start)
    for i in range(1, len(window_weeks)):
        prev_wk, wk = window_weeks[i - 1], window_weeks[i]
        prev_total, total = totals[prev_wk], totals[wk]
        if total <= prev_total:
            continue
        bump_ok = False
        if i == len(window_weeks) - 1:
            final3 = sum(daily.get(window_end - timedelta(days=n), 0.0) for n in range(3))
            prior3 = sum(daily.get(window_end - timedelta(days=n), 0.0) for n in range(3, 6))
            if prior3 > 0 and final3 <= prior3 * (1 + TAPER_OPENER_BUMP_MAX):
                bump_ok = True
        if not bump_ok:
            findings.append({"day": wk.isoformat(), "title": "(taper shape)",
                             "severity": "WARN", "rule": "AE-1.17",
                             "msg": f"taper week {total:.0f} TSS increases over prior week "
                                    f"{prev_total:.0f} TSS without a compliant final-3-day "
                                    f"opener bump (cap +{TAPER_OPENER_BUMP_MAX:.0%})"})

    # (b) intensity retention ---------------------------------------------
    weekly_hard = _weekly_hard_seconds(workouts)
    race_wks = _race_weeks(workouts)
    pre_taper_week = _week_start(window_start) - timedelta(weeks=1)
    pre_taper_hard = weekly_hard.get(pre_taper_week, 0.0)
    if pre_taper_hard >= TAPER_INTENSITY_FLOOR_SECONDS:
        for wk in window_weeks:
            if wk in race_wks:
                continue  # race cards carry intensity without structure
            taper_hard = weekly_hard.get(wk, 0.0)
            if taper_hard < TAPER_INTENSITY_RETENTION * pre_taper_hard:
                findings.append({"day": wk.isoformat(), "title": "(taper intensity)",
                                 "severity": "FAIL", "rule": "AE-1.17",
                                 "msg": f"taper week hard-seconds {taper_hard:.0f}s under "
                                        f"{TAPER_INTENSITY_RETENTION:.0%} of pre-taper week "
                                        f"{pre_taper_hard:.0f}s"})

    # (c) CTL retention --------------------------------------------------
    if current_ctl is not None:
        days = list(daily.keys())
        if days:
            seed_day = min(min(days), race) - timedelta(days=1)
            ctl_taper_start, _ = _model_ctl_atl(daily, seed_day, current_ctl,
                                                  current_ctl, window_start)
            ctl_race, _ = _model_ctl_atl(daily, window_start, ctl_taper_start,
                                          ctl_taper_start, race)
            if ctl_race < CTL_TAPER_RETENTION_FRACTION * ctl_taper_start:
                drop_pct = ((1 - ctl_race / ctl_taper_start) * 100
                            if ctl_taper_start else 0.0)
                cap_pct = 100 - CTL_TAPER_RETENTION_FRACTION * 100
                findings.append({"day": race.isoformat(), "title": "(taper CTL retention)",
                                 "severity": "FAIL", "rule": "AE-1.18",
                                 "msg": f"race-day modeled CTL {ctl_race:.1f} is "
                                        f"{drop_pct:.0f}% below taper-start CTL "
                                        f"{ctl_taper_start:.1f} (cap {cap_pct:.0f}%)"})
    return findings


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
    # Break/off weeks (near-zero planned TSS, AE-1.13) are excluded from the
    # load/recovery classification pool -- zeros drag the median down and
    # misclassify real recovery weeks as load weeks (live misfire: Kendall v2
    # recovery week 348 TSS classified load because two 0-TSS break weeks
    # halved the median). They are also exempt from the AE-1.9c WARN.
    active = {wk: t for wk, t in totals.items()
              if t >= 0.10 * max(totals.values())}
    if len(active) < 2:
        return []
    median = statistics.median(active.values())
    findings: list[dict] = []
    for wk in sorted(active):
        total = active[wk]
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
def _is_note(item: Mapping[str, Any]) -> bool:
    """TP calendar-note items carry noteDate and never workoutDay/structure
    -- distinguishes a notes_payload.json entry from a workout entry when
    both can appear as bare-list JSON."""
    return "noteDate" in item and "workoutDay" not in item and "structure" not in item


def _workouts(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [w for w in payload if isinstance(w, dict) and not _is_note(w)]
    if isinstance(payload, dict):
        for key in ("workouts", "items", "Workouts", "w"):
            if isinstance(payload.get(key), list):
                return [w for w in payload[key] if isinstance(w, dict) and not _is_note(w)]
        if "title" in payload or "structure" in payload or "workoutDay" in payload:
            return [payload]
    return []


def _notes(payload: Any) -> list[dict]:
    """TP calendar-note payloads (notes_payload.json): a bare list of
    {title, noteDate, description} dicts, or {"notes": [...]}."""
    items: list = payload if isinstance(payload, list) else []
    if not items and isinstance(payload, dict):
        for key in ("notes", "Notes"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
    return [n for n in items if isinstance(n, dict) and _is_note(n)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--ftp", type=float, default=None, help="reserved (structure targets are %%FTP already)")
    parser.add_argument("--race-date", type=str, default=None, help="YYYY-MM-DD — enables AE-1.12 taper/race-week caps + AE-1.14 CTL gate")
    parser.add_argument("--current-ctl", type=float, default=None, help="athlete's current CTL — enables the AE-1.14 CTL trajectory gate, AE-1.16 TSB gate, and AE-1.18 taper CTL-retention check (requires --race-date)")
    parser.add_argument("--current-atl", type=float, default=None, help="athlete's current ATL — feeds the AE-1.16 TSB gate (default: ATL=CTL at plan start, a logged assumption)")
    parser.add_argument("--coach-override", type=str, default=None, help="reason string — downgrades an AE-1.16 race-day TSB FAIL to WARN")
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
        notes = _notes(payload)
        total_workouts += len(workouts)
        all_workouts.extend(workouts)
        for w in workouts:
            for finding in lint_workout(w, race):
                finding["file"] = str(path)
                all_findings.append(finding)
        for finding in lint_voice(workouts, notes):  # AE-9.11 -- always on, no flag
            finding["file"] = str(path)
            all_findings.append(finding)

    # Plan-level gates (span the whole payload, not a single workout) —
    # both silent unless their inputs are supplied.
    plan_file = str(args.files[0]) if len(args.files) == 1 else "(plan)"
    for finding in lint_ctl_trajectory(all_workouts, race, args.current_ctl):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_race_day_tsb(all_workouts, race, args.current_ctl,
                                      args.current_atl, args.coach_override):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_taper_shape(all_workouts, race, args.current_ctl):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_demonstrated_dose(all_workouts, args.demonstrated_load):
        finding["file"] = plan_file
        all_findings.append(finding)

    # Plan-level gates (span the whole payload, not a single workout) —
    # both silent unless their inputs are supplied.
    plan_file = str(args.files[0]) if len(args.files) == 1 else "(plan)"
    for finding in lint_ctl_trajectory(all_workouts, race, args.current_ctl):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_race_day_tsb(all_workouts, race, args.current_ctl,
                                      args.current_atl, args.coach_override):
        finding["file"] = plan_file
        all_findings.append(finding)
    for finding in lint_taper_shape(all_workouts, race, args.current_ctl):
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
