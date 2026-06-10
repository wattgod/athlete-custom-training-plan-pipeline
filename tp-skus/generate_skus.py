#!/usr/bin/env python3
"""Generate the 27 TrainingPeaks static-plan SKUs — northstar P3.1.

For each family × duration in sku_definitions.json, composes a synthetic
design intake, runs the real plan pipeline, and collects:

  tp-skus/output/{family}-{weeks}wk/
    workouts/            the ZWO files (dated names = TP placement guide)
    BUILD_MANIFEST.md    day-by-day table for TP's plan builder (relative
                         Day 1..N), plus the marketplace listing blurb
    training_guide.html  reference while building

TP's plan builder is manual (the known bottleneck): workouts are defined by
relative day offset, so the manifest maps W01_Tue → Day 2 etc. Build each
plan ONCE in TP, then paste its URL into both brand repos'
data/tp-sku-links.json under the family + duration.

Usage:
    python3 tp-skus/generate_skus.py            # all 27
    python3 tp-skus/generate_skus.py gravel-climber-12wk
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SCRIPTS = REPO / "athletes" / "scripts"
OUTPUT = ROOT / "output"

DEFS = json.loads((ROOT / "sku_definitions.json").read_text())

DAY_OFFSET = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def race_date_for(weeks: int) -> str:
    """A Saturday exactly `weeks` weeks out (Saturday race = standard)."""
    today = date.today()
    days_to_sat = (5 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_to_sat + (weeks - 1) * 7)).isoformat()


def build_intake(family: str, weeks: int) -> str:
    f = DEFS["families"][family]
    a = DEFS["design_athlete"]
    r = f["design_race"]
    rd = race_date_for(weeks)
    sku_name = f"GG {family.replace('-', ' ').title()} {weeks}wk"
    return f"""# Athlete Intake: {sku_name}
Email: skus@gravelgodcycling.com
Submitted: {date.today().isoformat()}

## Basic Info
- Sex: {a['sex']}
- Age: {a['age']}
- Weight: {a['weight_lbs']} lbs
- Height: {a['height']}

## Goals
- Primary Goal: specific_race
- Races:
  {r['name']} ({rd}, {r['distance']}, priority A)
- Success: {r['goal']}

## Current Fitness
- FTP: {a['ftp']}
- Years Cycling: {a['years_cycling']}
- Years Structured: 1
- Longest Recent Ride: {f['longest_ride']}

## Recovery & Baselines
- Typical Sleep: {a['sleep']}
- Sleep Quality: {a['sleep']}

## Equipment
- Indoor Trainer: smart
- Devices: power meter, HR strap

## Schedule
- Weekly Hours Available: {a['weekly_hours']}
- Current Volume: {a['weekly_hours']}
- Long Ride Days: Saturday
- Interval Days: Tuesday, Thursday
- Off Days: {a['off_day']}

## Strength
- Current: {a['strength']['current']}
- Include: {a['strength']['include']}
- Equipment: {a['strength']['equipment']}

## Health
- Current Injuries: None

## Work & Life
- Life Stress: {a['stress']}

## Additional
- Other: {f['notes']} This is a template plan design athlete (not a real customer).
"""


def manifest_for(sku_id: str, family: str, weeks: int, workouts_dir: Path) -> str:
    f = DEFS["families"][family]
    rows = []
    pat = re.compile(r"W(\d{2})_(Mon|Tue|Wed|Thu|Fri|Sat|Sun)_\w+?_(.+)\.zwo")
    for w in sorted(workouts_dir.glob("*.zwo")):
        m = pat.match(w.name)
        if not m:
            continue
        week, day, label = int(m.group(1)), m.group(2), m.group(3)
        rel_day = (week - 1) * 7 + DAY_OFFSET[day] + 1
        rows.append((rel_day, week, day, label.replace("_", " "), w.name))
    rows.sort()
    table = "\n".join(
        f"| {d} | W{w:02d} {dy} | {label} | `{fn}` |"
        for d, w, dy, label, fn in rows)
    return f"""# BUILD MANIFEST — {f['name']} ({weeks} weeks)

**SKU id**: `{sku_id}` &nbsp; **Workouts**: {len(rows)}

## Marketplace listing

**Title**: {f['name']} — {weeks} Weeks
**Tagline**: {f['tagline']}

{f['notes']}

Built for 6-10 hours/week. Tuesday/Thursday intensity, Saturday long ride,
Monday off. Every workout has power AND heart-rate/RPE targets — no power
meter required. Includes strength track.

## TP Plan Builder — day-by-day

TP plans use relative day offsets (Day 1 = plan start, a Monday).
Upload the ZWOs from `workouts/`, then place each on its day:

| Day | Week/Day | Workout | File |
|---|---|---|---|
{table}

After publishing in TP, paste the plan URL into BOTH brand repos:
`data/tp-sku-links.json` → `"{family}"` → `"{weeks}"`.
"""


def generate(family: str, weeks: int) -> bool:
    sku_id = f"{family}-{weeks}wk"
    print(f"=== {sku_id}")
    intake = build_intake(family, weeks)
    proc = subprocess.run(
        [sys.executable, "intake_to_plan.py"],
        input=intake, capture_output=True, text=True,
        cwd=SCRIPTS, timeout=900,
    )
    if proc.returncode != 0:
        print(f"  FAILED rc={proc.returncode}")
        print((proc.stderr or proc.stdout)[-400:])
        return False

    # Pipeline delivers to ~/Downloads/{athlete-id}-training-plan
    m = re.search(r"Deliverables: (.+)", proc.stdout)
    if not m:
        print("  FAILED: no deliverables path in output")
        return False
    src = Path(m.group(1).strip())

    dest = OUTPUT / sku_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(src / "workouts", dest / "workouts")
    for extra in ("training_guide.html", "plan_summary.yaml"):
        if (src / extra).exists():
            shutil.copy2(src / extra, dest / extra)
    (dest / "BUILD_MANIFEST.md").write_text(
        manifest_for(sku_id, family, weeks, dest / "workouts"))
    n = len(list((dest / "workouts").glob("*.zwo")))
    print(f"  OK — {n} workouts → {dest}")
    return True


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    ok = fail = 0
    for family in DEFS["families"]:
        for weeks in DEFS["durations_weeks"]:
            sku_id = f"{family}-{weeks}wk"
            if only and sku_id != only:
                continue
            if generate(family, weeks):
                ok += 1
            else:
                fail += 1
    print(f"\nDone: {ok} SKUs generated, {fail} failed")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
