#!/usr/bin/env python3
"""
Daily avatar run — synthetic athletes through the real pipeline, judged.

For a small number of synthetic-but-realistic athletes:
  1. synthesize a never-identical avatar (synthesize_athlete)
  2. run the REAL pipeline (webhook markdown -> intake_to_plan -> plan + PDF)
  3. run the deterministic send-worthy contract (structural pass/fail)
  4. judge the plan with the LLM coach (subjective quality)
  5. write a markdown report

This is the production-grade extension of test_order_acceptance.py: instead
of two fixed golden orders, it fuzzes the input space daily and adds a coach's
judgment. Run it on a schedule; surface anything the contract fails or the
judge flags critical.

Usage:
    python3 daily_avatar_run.py [--count N] [--seed YYYY-MM-DD] [--out report.md]

Env:
    ANTHROPIC_API_KEY  — enables the LLM judge (else judge is skipped)
    GG_DELIVERY_DIR    — where deliverables land (default ~/Downloads)

Exit code: 0 if every avatar passed the contract and had no critical judge
problem; 1 otherwise (so CI flags it).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
WEBHOOK_DIR = REPO_ROOT / "webhook"


def _markdown(intake):
    sys.path.insert(0, str(WEBHOOK_DIR))
    from app import _questionnaire_to_markdown
    return _questionnaire_to_markdown(intake, name=intake["name"], email=intake["email"])


def _run_pipeline(intake, delivery_root):
    md = _markdown(intake)
    md_file = delivery_root / "intake.md"
    md_file.write_text(md)
    env = dict(os.environ)
    env["GG_DELIVERY_DIR"] = str(delivery_root)
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, "intake_to_plan.py", "--file", str(md_file)],
        cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True, timeout=600,
    )
    m = re.search(r"\bID:\s*(\S+)", proc.stdout)
    athlete_id = m.group(1) if m else None
    return proc, athlete_id


def _contract(athlete_dir, delivery_dir):
    """Deterministic send-worthy checks. Returns (ok, failures[])."""
    failures = []
    pdf = delivery_dir / "training_guide.pdf"
    if not (delivery_dir / "training_guide.html").exists():
        failures.append("guide HTML missing")
    if not pdf.exists():
        failures.append("PDF missing")
    else:
        from pdf_generator import validate_pdf
        ok, msg = validate_pdf(pdf)
        if not ok:
            failures.append(f"PDF invalid: {msg}")
    try:
        from validate_guide_quality import validate_guide
        passed, report = validate_guide(athlete_dir.name)
        if not passed:
            failures.append("guide quality gate failed")
    except Exception as e:
        failures.append(f"guide quality check errored: {e}")
    try:
        from generate_plan_preview import build_preview_data
        data = build_preview_data(athlete_dir)
        for c in data["checks"]:
            if c["status"] == "FAIL":
                failures.append(f"preview FAIL: {c['name']}")
    except Exception as e:
        failures.append(f"preview errored: {e}")
    return (not failures), failures


def run_avatars(count, seed, judge_plans=True):
    """Synth -> pipeline -> contract -> (judge) for `count` avatars.
    Returns the list of per-avatar result records. Shared by the daily
    report and the improvement loop."""
    from synthesize_athlete import synthesize

    delivery_base = Path(os.environ.get("GG_DELIVERY_DIR")
                         or (Path.home() / ".gg-avatar-runs"))
    delivery_base.mkdir(parents=True, exist_ok=True)

    results = []
    for i in range(count):
        intake = synthesize(seed=seed, index=i, today=date.today().isoformat())
        meta = intake.get("_meta", {})
        droot = delivery_base / f"{seed}-{i}"
        droot.mkdir(parents=True, exist_ok=True)

        proc, athlete_id = _run_pipeline(intake, droot)
        rec = {"index": i, "persona": meta.get("persona"),
               "persona_label": meta.get("persona_label"),
               "discipline": meta.get("discipline"),
               "race": intake["races"][0], "hours": intake["hours_per_week"],
               "ftp": intake["ftp"], "age": intake["age"], "sex": intake["sex"],
               "pipeline_ok": proc.returncode == 0}

        if proc.returncode != 0:
            rec["contract_ok"] = False
            rec["failures"] = ["pipeline exited non-zero (gate blocked)"]
            tail = (proc.stdout or "")[-600:]
            rec["pipeline_tail"] = tail
            results.append(rec)
            continue

        athlete_dir = SCRIPTS_DIR.parent / athlete_id
        delivery_dir = droot / f"{athlete_id}-training-plan"
        ok, failures = _contract(athlete_dir, delivery_dir)
        rec["contract_ok"] = ok
        rec["failures"] = failures

        if judge_plans:
            from judge_plan import judge
            rec["verdict"] = judge(athlete_dir, delivery_dir, meta)
        results.append(rec)

    return results


def run(count, seed, out_path):
    results = run_avatars(count, seed)
    report = _render_report(seed, results)
    if out_path:
        Path(out_path).write_text(report)
    print(report)

    # CI signal: fail if any contract failed or any critical judge problem
    bad = any(
        (not r.get("contract_ok"))
        or any(p.get("severity") == "critical"
               for p in (r.get("verdict", {}).get("problems") or []))
        for r in results
    )
    return 1 if bad else 0


def _render_report(seed, results):
    lines = [f"# Avatar run — {seed}", ""]
    n = len(results)
    passed = sum(1 for r in results if r.get("contract_ok"))
    judged = [r["verdict"]["score"] for r in results
              if r.get("verdict", {}).get("status") == "judged"]
    avg = f"{sum(judged)/len(judged):.1f}" if judged else "n/a"
    lines.append(f"**{passed}/{n} passed the contract · avg coach score {avg}/10**")
    lines.append("")
    for r in results:
        v = r.get("verdict", {})
        score = v.get("score")
        head = (f"## #{r['index']} · {r.get('persona_label') or r.get('persona')} "
                f"({r.get('discipline')})")
        lines.append(head)
        race = r.get("race", {})
        lines.append(f"- {r.get('sex')}, {r.get('age')}y · {r.get('hours')}h/wk · "
                     f"FTP {r.get('ftp')} · {race.get('name')} "
                     f"({race.get('distance')}, {race.get('date')})")
        badge = "✅" if r.get("contract_ok") else "❌"
        lines.append(f"- Contract: {badge} " +
                     ("" if r.get("contract_ok") else "— " + "; ".join(r.get("failures", []))))
        if v.get("status") == "judged":
            send = "would send" if v.get("would_send") else "WOULD NOT SEND"
            lines.append(f"- Coach: **{score}/10**, {send} — {v.get('summary', '')}")
            for p in (v.get("problems") or []):
                lines.append(f"    - _{p.get('severity')}_: {p.get('issue')}")
        elif v.get("status") == "skipped":
            lines.append(f"- Coach: skipped ({v.get('reason')})")
        elif v:
            lines.append(f"- Coach: error ({v.get('reason')})")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--seed", default=date.today().isoformat())
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    sys.exit(run(args.count, args.seed, args.out))


if __name__ == "__main__":
    main()
