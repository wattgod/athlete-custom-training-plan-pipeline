#!/usr/bin/env python3
"""
Self-improving loop — measure, aggregate, rank, track convergence.

The avatar judge tells us what's wrong with individual plans. This turns
that into a CONVERGENCE engine:

  1. Run a batch of avatars (more than the daily 3, for signal)
  2. Aggregate their problems into a deduplicated, ranked backlog
     (frequency × severity) — recurring issues rise, one-off judge noise
     sinks
  3. Compute a single QUALITY SCORE for the batch and append it to
     quality_history.json
  4. Report the delta vs the last run

"Improving everything every time until we're basically not improving much"
is then objective: the quality score climbs as fixes land, then PLATEAUS,
and the critical/major counts go to zero. That plateau is the stop signal.

The fix step is human-gated (propose → review → merge): the ranked
backlog is the work queue; each fix is verified by the full test suite +
a re-run that must RAISE the score before it ships.

Usage:
    python3 improvement_loop.py [--count N] [--seed YYYY-MM-DD]
    python3 improvement_loop.py --trend          # print the score history

Env: ANTHROPIC_API_KEY (the judge), GG_DELIVERY_DIR (optional).
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HISTORY = SCRIPTS_DIR.parent / "config" / "quality_history.json"
BACKLOG = SCRIPTS_DIR.parent / "config" / "improvement_backlog.md"

SEVERITY_WEIGHT = {"critical": 5, "major": 2, "minor": 1}


def _issue_signature(text: str) -> str:
    """Normalize a free-text problem into a clustering key: lowercase,
    drop digits/punctuation/quotes, keep the salient words. Good enough to
    make 'methodology contradiction' findings collapse into one bucket."""
    t = re.sub(r"[^a-z ]", " ", (text or "").lower())
    stop = {"the", "a", "an", "is", "are", "to", "of", "for", "and", "in",
            "this", "that", "should", "be", "it", "with", "but", "not",
            "athlete", "plan", "guide", "race", "their", "you", "your"}
    words = [w for w in t.split() if w not in stop and len(w) > 2]
    # the first handful of salient words is a stable-enough signature
    return " ".join(sorted(set(words[:6])))


def aggregate(results):
    """Cluster problems across avatars. Returns ranked issue list +
    batch quality metrics."""
    buckets = defaultdict(lambda: {"count": 0, "severity": "minor",
                                   "examples": [], "where": set()})
    judged = [r for r in results if r.get("verdict", {}).get("status") == "judged"]
    scores = [r["verdict"]["score"] for r in judged]
    contract_pass = sum(1 for r in results if r.get("contract_ok"))

    weighted_load = 0
    for r in results:
        v = r.get("verdict", {})
        for p in (v.get("problems") or []):
            sig = _issue_signature(p.get("issue", ""))
            if not sig:
                continue
            b = buckets[sig]
            b["count"] += 1
            sev = p.get("severity", "minor")
            if SEVERITY_WEIGHT.get(sev, 1) > SEVERITY_WEIGHT.get(b["severity"], 1):
                b["severity"] = sev
            if len(b["examples"]) < 3:
                b["examples"].append(p.get("issue", ""))
            b["where"].add(f"{r.get('discipline')}/{r.get('persona')}")
            weighted_load += SEVERITY_WEIGHT.get(sev, 1)
        # contract failures count as load too
        if not r.get("contract_ok"):
            weighted_load += 3

    # rank by frequency × severity weight
    ranked = sorted(
        buckets.items(),
        key=lambda kv: kv[1]["count"] * SEVERITY_WEIGHT[kv[1]["severity"]],
        reverse=True,
    )
    n = len(results)
    metrics = {
        "n": n,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "contract_pass_rate": round(contract_pass / n, 2) if n else 0,
        "weighted_problem_load": round(weighted_load / n, 2) if n else 0,
        "critical_count": sum(1 for _, b in buckets.items() if b["severity"] == "critical"),
        "distinct_issues": len(buckets),
    }
    return ranked, metrics


def _load_history():
    if HISTORY.exists():
        try:
            return json.loads(HISTORY.read_text())
        except Exception:
            return []
    return []


def _quality_scalar(m):
    """One number that rises as quality improves. Avg score minus the
    normalized problem load, scaled into roughly 0..10."""
    if m["avg_score"] is None:
        return None
    return round(m["avg_score"] - 0.4 * m["weighted_problem_load"]
                 + 2.0 * (m["contract_pass_rate"] - 0.5), 2)


def write_backlog(ranked, metrics, seed):
    lines = [f"# Improvement backlog — {seed}", ""]
    q = _quality_scalar(metrics)
    lines.append(f"**Quality {q if q is not None else 'n/a'}** · "
                 f"avg coach {metrics['avg_score']}/10 · "
                 f"contract pass {int(metrics['contract_pass_rate']*100)}% · "
                 f"load {metrics['weighted_problem_load']}/plan · "
                 f"{metrics['critical_count']} critical issue types")
    lines.append("")
    lines.append("Ranked recurring issues (frequency × severity). Fix top-down; "
                 "each fix must keep tests green AND raise the quality score.")
    lines.append("")
    for i, (sig, b) in enumerate(ranked[:25], 1):
        lines.append(f"### {i}. [{b['severity']}] ×{b['count']}  "
                     f"({', '.join(sorted(b['where']))})")
        for ex in b["examples"][:1]:
            lines.append(f"> {ex}")
        lines.append("")
    BACKLOG.write_text("\n".join(lines))
    return q


def run(count, seed):
    from daily_avatar_run import run_avatars
    results = run_avatars(count, seed)
    ranked, metrics = aggregate(results)
    q = write_backlog(ranked, metrics, seed)

    history = _load_history()
    prev_q = next((h["quality"] for h in reversed(history)
                   if h.get("quality") is not None), None)
    record = {"date": seed, "quality": q, **metrics}
    history.append(record)
    HISTORY.write_text(json.dumps(history, indent=1))

    print(f"\n=== Loop {seed} ===")
    print(f"quality={q}  avg_coach={metrics['avg_score']}/10  "
          f"contract_pass={int(metrics['contract_pass_rate']*100)}%  "
          f"load={metrics['weighted_problem_load']}/plan  "
          f"critical_types={metrics['critical_count']}")
    if prev_q is not None and q is not None:
        delta = round(q - prev_q, 2)
        trend = "improving" if delta > 0.15 else ("PLATEAUED" if abs(delta) <= 0.15 else "regressed")
        print(f"delta vs last: {delta:+}  → {trend}")
    print(f"backlog: {BACKLOG}")
    print("top issues:")
    for i, (sig, b) in enumerate(ranked[:6], 1):
        print(f"  {i}. [{b['severity']}] x{b['count']}: {b['examples'][0][:90]}")
    return q


def trend():
    history = _load_history()
    if not history:
        print("no history yet")
        return
    print("date        quality  avg   pass%  load  crit")
    for h in history:
        print(f"{h['date']}   {str(h.get('quality')):>6}  "
              f"{str(h.get('avg_score')):>4}  "
              f"{int((h.get('contract_pass_rate') or 0)*100):>4}  "
              f"{str(h.get('weighted_problem_load')):>4}  "
              f"{h.get('critical_count')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--seed", default=date.today().isoformat())
    ap.add_argument("--trend", action="store_true")
    args = ap.parse_args()
    if args.trend:
        trend()
    else:
        run(args.count, args.seed)


if __name__ == "__main__":
    main()
