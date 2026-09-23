import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/state-audit.yml"


def _health_validator_source():
    lines = WORKFLOW.read_text().splitlines(keepends=True)
    start = next(
        index + 1
        for index, line in enumerate(lines)
        if line.strip() == "python3 - <<'PY'"
    )
    end = next(
        index
        for index, line in enumerate(lines[start:], start=start)
        if line.strip() == "PY"
    )
    return textwrap.dedent("".join(lines[start:end]))


def _run_health_validator(tmp_path, payload):
    (tmp_path / "health.json").write_text(json.dumps(payload))
    env = os.environ.copy()
    env["RUNNER_TEMP"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, "-c", _health_validator_source()],
        capture_output=True,
        env=env,
        text=True,
    )


@pytest.mark.parametrize(("present", "token_config"), [
    pytest.param(False, None, id="absent"),
    pytest.param(True, None, id="null"),
    pytest.param(True, "configured", id="scalar"),
    pytest.param(True, [], id="list"),
])
def test_health_validator_rejects_absent_or_malformed_token_config(
        tmp_path, present, token_config):
    payload = {
        "runtime_files": {"apply_contract_schema": True},
    }
    if present:
        payload["token_config"] = token_config

    result = _run_health_validator(tmp_path, payload)

    assert result.returncode == 1
    assert "token_config.review" in result.stderr
    assert "token_config.download" in result.stderr


@pytest.mark.parametrize(("token_config", "missing_path"), [
    ({"review": False, "download": True}, "token_config.review"),
    ({"review": True, "download": False}, "token_config.download"),
    ({"download": True}, "token_config.review"),
    ({"review": True}, "token_config.download"),
])
def test_health_validator_rejects_false_or_missing_token_key(
        tmp_path, token_config, missing_path):
    result = _run_health_validator(tmp_path, {
        "runtime_files": {"apply_contract_schema": True},
        "token_config": token_config,
    })

    assert result.returncode == 1
    assert missing_path in result.stderr


@pytest.mark.parametrize(("present", "runtime_files"), [
    pytest.param(False, None, id="absent"),
    pytest.param(True, None, id="null"),
    pytest.param(True, "available", id="scalar"),
    pytest.param(True, [], id="list"),
])
def test_health_validator_rejects_absent_or_malformed_runtime_metadata(
        tmp_path, present, runtime_files):
    payload = {
        "token_config": {"review": True, "download": True},
    }
    if present:
        payload["runtime_files"] = runtime_files

    result = _run_health_validator(tmp_path, payload)

    assert result.returncode == 1
    assert "runtime_files.apply_contract_schema" in result.stderr


def test_health_validator_accepts_required_schema_and_token_keys(tmp_path):
    result = _run_health_validator(tmp_path, {
        "runtime_files": {"apply_contract_schema": True},
        "token_config": {"review": True, "download": True},
    })

    assert result.returncode == 0


def test_health_step_retains_non_200_http_failure_guard():
    workflow = WORKFLOW.read_text()
    health_step = workflow.split(
        "- name: Production health must ship schema and token keys", 1)[1]
    health_step = health_step.split(
        "- name: Trigger authenticated Railway state audit", 1)[0]

    status_guard = 'if [ "$HTTP_STATUS" != "200" ]; then'
    assert status_guard in health_step
    assert health_step.index(status_guard) < health_step.index("python3 - <<'PY'")
    guard_body = health_step.split(status_guard, 1)[1].split("fi", 1)[0]
    assert "exit 1" in guard_body


def _annotation_source():
    lines = WORKFLOW.read_text().splitlines(keepends=True)
    step = next(
        index for index, line in enumerate(lines)
        if "- name: Trigger authenticated Railway state audit" in line)
    start = next(
        index + 1
        for index, line in enumerate(lines[step:], start=step)
        if line.strip() == "python3 - <<'PY'"
    )
    end = next(
        index
        for index, line in enumerate(lines[start:], start=start)
        if line.strip() == "PY"
    )
    return textwrap.dedent("".join(lines[start:end]))


def test_audit_step_annotates_stale_paid_orders(tmp_path):
    (tmp_path / "state-audit.json").write_text(json.dumps({
        "anomalies": [
            {"state_ref": "abc123abc123", "code": "PAID_ORDER_STALE",
             "severity": "CRITICAL", "status": "BLOCKED_REVIEW",
             "hours_since_payment": 26, "blocker_count": 2, "alert": "new",
             "coach_email": "sent", "detail": "paid order is still open"},
            {"state_ref": "def456def456", "code": "PAID_ORDER_STALE",
             "severity": "WARNING", "status": "APPROVED",
             "hours_since_payment": 30, "blocker_count": 0,
             "alert": "repeat_within_24h", "detail": "paid order is still open"},
        ],
        "alert_ledger": "failed",
    }))
    env = os.environ.copy()
    env["RUNNER_TEMP"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", _annotation_source()],
        capture_output=True, env=env, text=True)

    assert result.returncode == 0, result.stderr
    first, second, ledger = result.stdout.splitlines()
    assert ledger.startswith("::warning::stale-order alert ledger unavailable")
    assert first.startswith("::error::PAID_ORDER_STALE state_ref=abc123abc123 ")
    assert "hours_since_payment=26 blocker_count=2 alert=new" in first
    assert second.startswith("::warning::PAID_ORDER_STALE state_ref=def456def456 ")


def test_audit_step_still_fails_on_non_200_after_annotations():
    workflow = WORKFLOW.read_text()
    audit_step = workflow.split(
        "- name: Trigger authenticated Railway state audit", 1)[1]
    status_guard = 'if [ "$HTTP_STATUS" != "200" ]; then'
    assert audit_step.index("python3 - <<'PY'") < audit_step.index(status_guard)
    assert "exit 1" in audit_step.split(status_guard, 1)[1].split("fi", 1)[0]
