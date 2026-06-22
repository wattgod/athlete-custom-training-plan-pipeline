#!/usr/bin/env python3
"""
Coverage sweep — build a plan for the main personas against EACH race.

The daily avatar judge samples a few random athletes for DEPTH (LLM quality
scoring). This sweep is the BREADTH complement: it drives the main personas
through the full production pipeline against every buildable race in the
1,184-race database and runs the deterministic, send-worthy contract on each
result. No LLM cost.

It answers the question the business actually rides on: "can we deliver a
coach-grade plan for every race we sell, for every kind of athlete who buys?"
— and clusters the structural failures (gate blocks, missing sections, 0.0h
fueling, preview FAILs) by failure type, persona, and discipline so the
worst-offending races and the most common breakages rise to the top.

Usage:
    python3 coverage_sweep.py --sample 30                 # stratified sample (fast)
    python3 coverage_sweep.py --full                      # every buildable race
    python3 coverage_sweep.py --sample 50 --personas weekend_warrior,masters_returner
    python3 coverage_sweep.py --workers 6 --out coverage.md
    python3 coverage_sweep.py --trend                     # print pass-rate history

Each (persona × race) cell is one real pipeline build. Default runs ALL five
personas against the sampled races. Synthetic athlete dirs are created under
athletes/ with the `avatarcov` prefix and cleaned up after each build (only
the exact dirs this run created are removed).
"""

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HISTORY = SCRIPTS_DIR.parent / "config" / "coverage_history.json"
REPORT = SCRIPTS_DIR.parent / "config" / "coverage_report.md"

PERSONA_KEYS = [
    "time_crunched_parent",
    "masters_returner",
    "ambitious_first_timer",
    "veteran_podium_chaser",
    "weekend_warrior",
]

# Distance bands for stratified sampling, so a sample spans short/mid/long
# events rather than clustering on one distance.
_BANDS = [(0, 50), (50, 80), (80, 120), (120, 9999)]


def _band(mi):
    try:
        mi = float(mi)
    except (TypeError, ValueError):
        return _BANDS[0]
    for lo, hi in _BANDS:
        if lo <= mi < hi:
            return (lo, hi)
    return _BANDS[-1]


def _stratified_sample(races, n, seed):
    """Pick n races spread across (discipline, distance-band) strata so the
    sample is representative, not clustered. Deterministic via seed."""
    import random
    rng = random.Random(f"coverage::{seed}")
    strata = defaultdict(list)
    for e in races:
        strata[(e.get("discipline"), _band(e.get("distance_mi")))].append(e)
    for v in strata.values():
        rng.shuffle(v)
    keys = list(strata.keys())
    keys.sort(key=lambda k: (str(k[0]), k[1]))
    out, i = [], 0
    # round-robin across strata until we have n (or exhaust)
    while len(out) < n and any(strata[k] for k in keys):
        k = keys[i % len(keys)]
        if strata[k]:
            out.append(strata[k].pop())
        i += 1
    return out


def _gate_reason(proc):
    """Pull a concise reason out of a non-zero pipeline run so gate blocks
    cluster by root cause (the failing CRITICAL rule / exception) rather than
    all collapsing into one 'gate blocked' bucket."""
    import re
    blob = (proc.stderr or "") + "\n" + (proc.stdout or "")
    # the compliance gate prints "[FAIL] R19 [CRITICAL]: Hours out of range:..."
    m = re.search(r"\[FAIL\]\s*(R\d+)\s*\[CRITICAL\]:\s*([^:\n]+)", blob)
    if m:
        return f"gate: {m.group(1)} {m.group(2).strip()[:60]}"
    m = re.search(r"(\w*Error): (.+)", blob)
    if m:
        return f"gate: {m.group(1)}: {m.group(2)[:70]}"
    return "pipeline exited non-zero (gate blocked)"


def _build_one(persona_key, race, idx, base_day):
    """One real pipeline build for (persona × race). Returns a result record.
    Cleans up the synthetic athlete + delivery dirs it created."""
    from synthesize_athlete import synthesize
    from daily_avatar_run import _run_pipeline, _contract

    rec = {
        "persona": persona_key,
        "race": race.get("name"),
        "discipline": race.get("discipline"),
        "distance_mi": race.get("distance_mi"),
        "ok": False,
        "failures": [],
    }
    delivery_base = Path(os.environ.get("GG_COVERAGE_DIR")
                         or (Path.home() / ".gg-coverage-runs"))
    droot = delivery_base / f"cov-{idx}"
    created = []
    try:
        droot.mkdir(parents=True, exist_ok=True)
        intake = synthesize(seed="covsweep", index=idx, today=base_day,
                            persona_key=persona_key, race=race)
        proc, athlete_id = _run_pipeline(intake, droot)
        if proc.returncode != 0:
            rec["failures"] = [_gate_reason(proc)]
            rec["tail"] = ((proc.stderr or "") + (proc.stdout or ""))[-500:]
            return rec
        athlete_dir = SCRIPTS_DIR.parent / athlete_id
        created.append(athlete_dir)
        delivery_dir = droot / f"{athlete_id}-training-plan"
        ok, failures = _contract(athlete_dir, delivery_dir)
        rec["ok"] = ok
        rec["failures"] = failures
        return rec
    except Exception as e:  # a crash is itself a coverage failure to record
        rec["failures"] = [f"build crashed: {type(e).__name__}: {e}"]
        return rec
    finally:
        # remove ONLY the exact synthetic dirs this build created
        for d in created + [droot]:
            try:
                if d.exists() and ("cov-" in d.name or "covsweep" in d.name.lower()):
                    shutil.rmtree(d)
            except Exception:
                pass


def _normalize_failure(f):
    """Collapse a failure string to a clustering key (drop race-specific
    detail so 'preview FAIL: Off Days' buckets across races)."""
    f = f.split(":")[0].strip().lower() if ":" in f else f.strip().lower()
    return f[:60]


def run(personas, races, workers, seed):
    base_day = date.today().isoformat()
    jobs = [(p, race) for race in races for p in personas]
    results = []
    print(f"coverage: {len(personas)} personas × {len(races)} races "
          f"= {len(jobs)} builds, {workers} workers")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_build_one, p, race, i, base_day): (p, race)
                for i, (p, race) in enumerate(jobs)}
        done = 0
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % 10 == 0 or done == len(jobs):
                ok = sum(1 for r in results if r["ok"])
                print(f"  {done}/{len(jobs)}  pass={ok}/{done} "
                      f"({100*ok//max(done,1)}%)")
    return _aggregate(results, seed)


def _aggregate(results, seed):
    n = len(results)
    ok = sum(1 for r in results if r["ok"])
    by_failure = defaultdict(int)
    by_persona = defaultdict(lambda: [0, 0])      # [pass, total]
    by_discipline = defaultdict(lambda: [0, 0])
    failing_races = defaultdict(list)
    for r in results:
        by_persona[r["persona"]][1] += 1
        by_discipline[r["discipline"]][1] += 1
        if r["ok"]:
            by_persona[r["persona"]][0] += 1
            by_discipline[r["discipline"]][0] += 1
        else:
            for f in (r["failures"] or ["unknown"]):
                by_failure[_normalize_failure(f)] += 1
            failing_races[r["race"]].append(f"{r['persona']}: "
                                            f"{'; '.join(r['failures'][:2])}")
    metrics = {
        "date": seed,
        "n": n,
        "pass": ok,
        "pass_rate": round(ok / n, 3) if n else 0,
        "by_failure": dict(sorted(by_failure.items(), key=lambda kv: -kv[1])),
        "by_persona": {k: round(v[0] / v[1], 3) if v[1] else 0
                       for k, v in by_persona.items()},
        "by_discipline": {str(k): round(v[0] / v[1], 3) if v[1] else 0
                          for k, v in by_discipline.items()},
        "worst_races": sorted(failing_races.items(),
                              key=lambda kv: -len(kv[1]))[:25],
    }
    _write_report(metrics)
    _append_history(metrics)
    _print_summary(metrics)
    return metrics


def _write_report(m):
    lines = [f"# Coverage sweep — {m['date']}", ""]
    lines.append(f"**{m['pass']}/{m['n']} builds send-worthy "
                 f"({int(m['pass_rate']*100)}%)** across the main personas × "
                 f"the race database.")
    lines.append("")
    lines.append("Breadth complement to the daily depth judge: every cell is a "
                 "real pipeline build checked against the deterministic "
                 "send-worthy contract (no LLM).")
    lines.append("")
    lines.append("## Pass rate by persona")
    for k, v in sorted(m["by_persona"].items(), key=lambda kv: kv[1]):
        lines.append(f"- {k}: {int(v*100)}%")
    lines.append("")
    lines.append("## Pass rate by discipline")
    for k, v in sorted(m["by_discipline"].items(), key=lambda kv: kv[1]):
        lines.append(f"- {k}: {int(v*100)}%")
    lines.append("")
    if m["by_failure"]:
        lines.append("## Failures by type (frequency)")
        for k, c in m["by_failure"].items():
            lines.append(f"- ×{c}  {k}")
        lines.append("")
    if m["worst_races"]:
        lines.append("## Worst-offending races (fix top-down)")
        for name, fails in m["worst_races"]:
            lines.append(f"### {name} — {len(fails)} persona(s) failed")
            for f in fails[:5]:
                lines.append(f"- {f}")
            lines.append("")
    REPORT.write_text("\n".join(lines))


def _append_history(m):
    hist = []
    if HISTORY.exists():
        try:
            hist = json.loads(HISTORY.read_text())
        except Exception:
            hist = []
    hist.append({k: m[k] for k in ("date", "n", "pass", "pass_rate",
                                   "by_persona", "by_discipline")})
    HISTORY.write_text(json.dumps(hist, indent=1))


def _print_summary(m):
    print(f"\n=== Coverage {m['date']} ===")
    print(f"send-worthy: {m['pass']}/{m['n']} ({int(m['pass_rate']*100)}%)")
    if m["by_failure"]:
        print("top failure types:")
        for k, c in list(m["by_failure"].items())[:6]:
            print(f"  ×{c}  {k}")
    print(f"report: {REPORT}")


def _trend():
    if not HISTORY.exists():
        print("no coverage history yet")
        return
    hist = json.loads(HISTORY.read_text())
    print("date          builds  pass%")
    for h in hist:
        print(f"{h['date']:>12}  {h['n']:>6}  {int(h['pass_rate']*100):>4}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=30,
                    help="stratified race sample size (ignored with --full)")
    ap.add_argument("--full", action="store_true", help="every buildable race")
    ap.add_argument("--personas", default=",".join(PERSONA_KEYS),
                    help="comma-separated persona keys")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", default=date.today().isoformat())
    ap.add_argument("--trend", action="store_true")
    args = ap.parse_args()

    if args.trend:
        _trend()
        return

    from real_races import buildable_races
    races = buildable_races(today=date.today().isoformat())
    if not races:
        print("no buildable races in snapshot")
        sys.exit(1)
    if not args.full:
        races = _stratified_sample(races, args.sample, args.seed)

    personas = [p for p in args.personas.split(",") if p in PERSONA_KEYS]
    if not personas:
        print("no valid personas")
        sys.exit(1)

    run(personas, races, args.workers, args.seed)


if __name__ == "__main__":
    main()
