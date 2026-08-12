import json
from pathlib import Path

from tools import canary_probe


SECRET = "fixture-worker-capability-secret-0000000001"


def _env(tmp_path, **overrides):
    values = {
        "TP_CANARY_EMAIL": "fixture-canary@example.invalid",
        "TP_CANARY_LABEL": "cheesehead",
        "GG_WORKER_CAPABILITY_SECRET": SECRET,
        "GG_WORKER_REPLAY_DIR": str(tmp_path / "replay"),
    }
    values.update(overrides)
    return values


def test_fixture_mode_runs_end_to_end_and_records_green_artifact(tmp_path):
    out = tmp_path / "canary.json"
    assert canary_probe.main(
        ["--transport", "fixture", "--out", str(out)],
        environ=_env(tmp_path),
    ) == 0

    artifact = json.loads(out.read_text())
    assert artifact["status"] == "passed"
    assert all(item["passed"] for item in artifact["assertions"])
    records = list((tmp_path / "replay").rglob("*.json"))
    assert len(records) == 2
    assert {json.loads(path.read_text())["status"] for path in records} == {"succeeded"}


def test_live_mode_fails_closed_with_phase4_gate_message(tmp_path):
    out = tmp_path / "live.json"
    assert canary_probe.main(
        ["--transport", "live", "--out", str(out)],
        environ=_env(tmp_path),
    ) == 1
    artifact = json.loads(out.read_text())
    assert artifact["status"] == "failed"
    assert artifact["assertions"][0]["detail"] == canary_probe.LIVE_PENDING_ERROR
    assert not (tmp_path / "replay").exists()


def test_artifact_never_contains_seeded_sensitive_value(tmp_path):
    sensitive = "seeded-sensitive-account-value"
    fixture = json.loads(canary_probe.FIXTURE_PATH.read_text())
    fixture["probe_athlete"] = {
        "outcome": "bound", "tp_athlete_id": sensitive, "candidates": [],
    }
    fixture["inspect_account"] = {
        **fixture, "tp_athlete_id": sensitive, "private_note": sensitive,
    }
    fixture_path = tmp_path / "sensitive-fixture.json"
    fixture_path.write_text(json.dumps(fixture))
    out = tmp_path / "redacted.json"
    assert canary_probe.main(
        ["--fixture", str(fixture_path), "--out", str(out)],
        environ=_env(tmp_path, TP_CANARY_ATHLETE_ID=sensitive, TP_CANARY_EMAIL=""),
    ) == 0
    assert sensitive not in out.read_text()


def test_mutilated_fixture_response_exits_nonzero(tmp_path):
    fixture = json.loads(canary_probe.FIXTURE_PATH.read_text())
    fixture.pop("lthr_bpm")
    fixture_path = tmp_path / "mutilated.json"
    fixture_path.write_text(json.dumps(fixture))
    out = tmp_path / "failed.json"
    assert canary_probe.main(
        ["--fixture", str(fixture_path), "--out", str(out)],
        environ=_env(tmp_path),
    ) == 1
    artifact = json.loads(out.read_text())
    assert artifact["status"] == "failed"
    assert any(
        item["name"] == "hr_lthr_threshold_structure" and not item["passed"]
        for item in artifact["assertions"]
    )


def test_runner_has_no_apply_adapter_or_mutation_calls():
    source = Path(canary_probe.__file__).read_text()
    assert "trainingpeaks.adapter" not in source
    assert all(token not in source for token in (".apply(", ".verify(", ".rollback("))
