#!/usr/bin/env python3
"""
LLM coach-judge — scores a generated plan the way a head coach would.

The deterministic acceptance contract (test_order_acceptance.py) catches
STRUCTURAL failures: missing sections, bad PDF, volume off, facts that
don't match. This judge catches the SUBJECTIVE layer a contract can't:
is the methodology sensible for THIS athlete? does the guide read well?
is anything incoherent a real coach would catch (e.g. a road athlete
handed a gravel-cornering chapter)? would you actually send it?

It reads the same deliverables a customer gets, hands them to Claude with
a coaching rubric, and returns a structured verdict.

Env: ANTHROPIC_API_KEY (fail-soft — returns a 'skipped' verdict if absent).
"""

import json
import os
import re
import sys
from html import unescape
from pathlib import Path

import yaml

MODEL = "claude-sonnet-4-6"
SCRIPTS_DIR = Path(__file__).resolve().parent


def _guide_plain_text(athlete_dir: Path) -> str:
    html = (athlete_dir / "training_guide.html").read_text()
    text = unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", "", html, flags=re.S)))
    return re.sub(r"\s+", " ", text).strip()


def _plan_facts(athlete_dir: Path, delivery_dir: Path, meta: dict) -> dict:
    """Compact, judge-relevant facts about the plan + who it's for."""
    facts = {"persona": meta.get("persona"), "persona_label": meta.get("persona_label"),
             "discipline": meta.get("discipline"), "weeks_out": meta.get("weeks_out"),
             "ftp_known": meta.get("ftp_known")}
    try:
        from generate_plan_preview import build_preview_data
        data = build_preview_data(athlete_dir)
        facts["preview_checks"] = {c["name"]: c["status"] for c in data["checks"]}
    except Exception as e:
        facts["preview_checks"] = f"(unavailable: {e})"
    try:
        prof = yaml.safe_load((athlete_dir / "profile.yaml").read_text())
        facts["athlete"] = {
            "sex": prof.get("sex"),
            "age": prof.get("health_factors", {}).get("age") or prof.get("age"),
            "ftp": prof.get("fitness_markers", {}).get("ftp_watts"),
            "hours_target": prof.get("weekly_availability", {}).get("cycling_hours_target"),
        }
        facts["race"] = (prof.get("a_events") or [{}])[0]
    except Exception:
        pass
    try:
        meth = yaml.safe_load((athlete_dir / "methodology.yaml").read_text())
        facts["methodology"] = meth.get("selected_methodology") or meth.get("name")
    except Exception:
        pass
    try:
        fuel = yaml.safe_load((delivery_dir / "fueling.yaml").read_text())
        facts["fueling"] = {"hourly_carbs": fuel.get("carbohydrates", {}).get("hourly_target"),
                            "duration_h": fuel.get("race", {}).get("duration_hours")}
    except Exception:
        pass
    return facts


JUDGE_SYSTEM = """You are the head coach at a cycling coaching business doing \
final QA on an automatically generated training plan before it is emailed to \
a paying customer. You are exacting but fair. You care about: (1) is the plan \
COHERENT for this specific athlete — methodology, volume, and content all fit \
their hours, experience, age, and event; (2) is anything WRONG or embarrassing \
— claims that contradict the athlete's data, content for the wrong discipline \
(e.g. gravel cornering drills for a road racer), nonsensical numbers; (3) does \
the guide READ like something a real coach wrote. You are NOT re-checking \
formatting or PDF validity — a separate automated gate covers that. \
You only judge whether this is a plan you'd put your name on."""

JUDGE_SCHEMA = {
    "type": "object",
    "required": ["score", "would_send", "summary", "strengths", "problems"],
    "properties": {
        "score": {"type": "integer", "minimum": 1, "maximum": 10,
                  "description": "1=do not send, 10=flawless, send as-is"},
        "would_send": {"type": "boolean"},
        "summary": {"type": "string", "description": "one sentence verdict"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "problems": {"type": "array", "items": {
            "type": "object", "required": ["severity", "issue"],
            "properties": {
                "severity": {"type": "string", "enum": ["critical", "major", "minor"]},
                "issue": {"type": "string"},
            }}},
    },
}


def judge(athlete_dir: Path, delivery_dir: Path, meta: dict = None) -> dict:
    meta = meta or {}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "ANTHROPIC_API_KEY not set"}

    facts = _plan_facts(athlete_dir, delivery_dir, meta)
    guide = _guide_plain_text(athlete_dir)
    # keep the guide excerpt bounded — the judge needs the gist, not 50k chars
    guide_excerpt = guide[:14000]

    user = (
        "Plan facts (JSON):\n" + json.dumps(facts, indent=2, default=str) +
        "\n\nTraining guide text (truncated):\n\"\"\"\n" + guide_excerpt + "\n\"\"\"\n\n"
        "Judge this plan. Return ONLY the structured verdict."
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL, max_tokens=1200, system=JUDGE_SYSTEM,
            tools=[{"name": "verdict", "description": "Record the coaching verdict.",
                    "input_schema": JUDGE_SCHEMA}],
            tool_choice={"type": "tool", "name": "verdict"},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                verdict = dict(block.input)
                verdict["status"] = "judged"
                verdict["facts"] = facts
                return verdict
        return {"status": "error", "reason": "no verdict returned"}
    except Exception as e:
        return {"status": "error", "reason": str(e)[:200]}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: judge_plan.py <athlete_dir> <delivery_dir>")
        sys.exit(1)
    v = judge(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(v, indent=2, default=str))
