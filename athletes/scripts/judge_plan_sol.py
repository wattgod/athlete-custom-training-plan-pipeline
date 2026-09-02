#!/usr/bin/env python3
"""Synthetic-only GPT-5.6 Sol shadow judge through Vercel AI Gateway.

This evaluator is deliberately isolated from paid-athlete fulfillment. It will
only read an ``avatar-*`` package whose profile email ends in
``@synthetic.local``. Its verdict is advisory: it does not change the plan,
quality history, backlog, delivery artifacts, or any production gate.

Env: AI_GATEWAY_API_KEY (fail-soft when absent).
"""

import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import requests
import yaml

from judge_plan import JUDGE_SCHEMA, JUDGE_SYSTEM, _guide_plain_text, _plan_facts


MODEL = "openai/gpt-5.6-sol"
GATEWAY_RESPONSES_URL = "https://ai-gateway.vercel.sh/v1/responses"
MAX_GUIDE_CHARS = 120_000
MAX_OUTPUT_TOKENS = 4_000

# Vercel AI Gateway promotional rate verified 2026-08-26. These constants are
# only a conservative preflight estimate; the response's billed token counts
# are retained in every verdict for reconciliation against the dashboard.
INPUT_USD_PER_MILLION = 2.0
OUTPUT_USD_PER_MILLION = 10.0
DEFAULT_REQUEST_BUDGET_USD = 1.0


class SyntheticOnlyError(ValueError):
    """Raised before networking when an artifact is not a synthetic avatar."""


def _strict_schema() -> dict:
    schema = deepcopy(JUDGE_SCHEMA)
    schema["additionalProperties"] = False
    schema["properties"]["problems"]["items"]["additionalProperties"] = False
    return schema


def _assert_synthetic_avatar(athlete_dir: Path) -> dict:
    profile_path = athlete_dir / "profile.yaml"
    try:
        profile = yaml.safe_load(profile_path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SyntheticOnlyError(f"synthetic profile unavailable: {exc}") from exc

    email = str(profile.get("email") or "").strip().lower()
    if not athlete_dir.name.startswith("avatar-") or not email.endswith(
        "@synthetic.local"
    ):
        raise SyntheticOnlyError(
            "Sol shadow judge accepts only avatar-* profiles at @synthetic.local"
        )
    return profile


def _estimated_max_cost_usd(prompt_chars: int) -> float:
    # Three chars/token intentionally overestimates normal English and JSON.
    input_tokens = (prompt_chars + 2) // 3
    return round(
        input_tokens / 1_000_000 * INPUT_USD_PER_MILLION
        + MAX_OUTPUT_TOKENS / 1_000_000 * OUTPUT_USD_PER_MILLION,
        4,
    )


def _extract_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output") or []:
        for part in item.get("content") or []:
            text = part.get("text")
            if isinstance(text, str):
                return text
    raise ValueError("Gateway response contained no output text")


def _actual_cost_usd(payload: dict) -> float | None:
    usage = payload.get("usage") or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return round(
        input_tokens / 1_000_000 * INPUT_USD_PER_MILLION
        + output_tokens / 1_000_000 * OUTPUT_USD_PER_MILLION,
        6,
    )


def judge(
    athlete_dir: Path,
    delivery_dir: Path,
    meta: dict | None = None,
    request_budget_usd: float = DEFAULT_REQUEST_BUDGET_USD,
) -> dict:
    """Return a Sol verdict for one synthetic avatar without mutating artifacts."""
    try:
        _assert_synthetic_avatar(athlete_dir)
    except SyntheticOnlyError as exc:
        return {"status": "blocked", "reason": str(exc)}

    api_key = os.environ.get("AI_GATEWAY_API_KEY", "").strip()
    if not api_key:
        return {"status": "skipped", "reason": "AI_GATEWAY_API_KEY not set"}

    facts = _plan_facts(athlete_dir, delivery_dir, meta or {})
    guide = _guide_plain_text(athlete_dir)[:MAX_GUIDE_CHARS]
    user = (
        "Plan facts (JSON):\n"
        + json.dumps(facts, indent=2, default=str)
        + "\n\nTraining guide text:\n\"\"\"\n"
        + guide
        + "\n\"\"\"\n\nJudge this plan. Return only the structured verdict."
    )
    estimated_max = _estimated_max_cost_usd(len(JUDGE_SYSTEM) + len(user))
    if estimated_max > request_budget_usd:
        return {
            "status": "blocked",
            "reason": (
                f"estimated request ceiling ${estimated_max:.4f} exceeds "
                f"${request_budget_usd:.2f} request budget"
            ),
        }

    request_payload = {
        "model": MODEL,
        "input": [
            {"type": "message", "role": "system", "content": JUDGE_SYSTEM},
            {"type": "message", "role": "user", "content": user},
        ],
        "reasoning": {"effort": "high"},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "coach_verdict",
                "strict": True,
                "schema": _strict_schema(),
            }
        },
    }

    try:
        response = requests.post(
            GATEWAY_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_payload,
            timeout=180,
        )
        response.raise_for_status()
        raw = response.json()
        verdict = json.loads(_extract_output_text(raw))
        verdict["status"] = "judged"
        verdict["judge"] = "sol-shadow"
        verdict["model"] = MODEL
        verdict["facts"] = facts
        verdict["usage"] = raw.get("usage") or {}
        verdict["estimated_max_cost_usd"] = estimated_max
        verdict["actual_cost_usd"] = _actual_cost_usd(raw)
        return verdict
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "error", "reason": str(exc)[:240], "model": MODEL}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: judge_plan_sol.py <synthetic-athlete-dir> <delivery-dir>")
        sys.exit(1)
    result = judge(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("status") in {"judged", "skipped"} else 1)
