import json
from pathlib import Path

import yaml

import judge_plan_sol
from daily_avatar_run import _render_report


def _avatar(tmp_path: Path, email="avatar-1@synthetic.local"):
    athlete = tmp_path / "avatar-test"
    delivery = tmp_path / "delivery"
    athlete.mkdir()
    delivery.mkdir()
    (athlete / "profile.yaml").write_text(yaml.safe_dump({"email": email}))
    (athlete / "training_guide.html").write_text("<h1>Guide</h1><p>Specific plan.</p>")
    return athlete, delivery


def test_blocks_non_synthetic_before_network(tmp_path, monkeypatch):
    athlete, delivery = _avatar(tmp_path, email="real@example.com")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "secret")

    def unexpected(*args, **kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr(judge_plan_sol.requests, "post", unexpected)
    result = judge_plan_sol.judge(athlete, delivery)

    assert result["status"] == "blocked"
    assert "synthetic.local" in result["reason"]


def test_fail_soft_without_gateway_key(tmp_path, monkeypatch):
    athlete, delivery = _avatar(tmp_path)
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)

    result = judge_plan_sol.judge(athlete, delivery)

    assert result == {"status": "skipped", "reason": "AI_GATEWAY_API_KEY not set"}


def test_sends_bounded_structured_request_and_records_cost(tmp_path, monkeypatch):
    athlete, delivery = _avatar(tmp_path)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "secret")
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "score": 8,
                                        "would_send": True,
                                        "summary": "Coherent.",
                                        "strengths": ["Specific"],
                                        "problems": [],
                                    }
                                ),
                            }
                        ]
                    }
                ],
                "usage": {"input_tokens": 1000, "output_tokens": 200},
            }

    def post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(judge_plan_sol.requests, "post", post)
    result = judge_plan_sol.judge(athlete, delivery, {"persona": "test"})

    assert result["status"] == "judged"
    assert result["judge"] == "sol-shadow"
    assert result["actual_cost_usd"] == 0.004
    assert captured["url"].endswith("/v1/responses")
    assert captured["timeout"] == 180
    payload = captured["json"]
    assert payload["model"] == judge_plan_sol.MODEL
    assert payload["reasoning"] == {"effort": "high"}
    assert payload["store"] is False
    assert payload["max_output_tokens"] == judge_plan_sol.MAX_OUTPUT_TOKENS
    assert payload["text"]["format"]["strict"] is True
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_request_budget_blocks_before_network(tmp_path, monkeypatch):
    athlete, delivery = _avatar(tmp_path)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "secret")

    def unexpected(*args, **kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr(judge_plan_sol.requests, "post", unexpected)
    result = judge_plan_sol.judge(
        athlete, delivery, request_budget_usd=0.000001
    )

    assert result["status"] == "blocked"
    assert "request budget" in result["reason"]


def test_report_identifies_sol_and_request_cost():
    report = _render_report(
        "pilot",
        [
            {
                "index": 0,
                "persona": "test",
                "discipline": "gravel",
                "race": {},
                "contract_ok": True,
                "verdict": {
                    "status": "judged",
                    "judge": "sol-shadow",
                    "model": judge_plan_sol.MODEL,
                    "score": 8,
                    "would_send": True,
                    "summary": "Coherent.",
                    "problems": [],
                    "actual_cost_usd": 0.0421,
                },
            }
        ],
    )

    assert "Sol shadow" in report
    assert judge_plan_sol.MODEL in report
    assert "$0.0421" in report
