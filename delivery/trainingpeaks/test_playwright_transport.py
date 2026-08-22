import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PAYLOAD_PATH = ROOT / "tools" / "tp_phase5_browser_payload.js"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD_PATH.read_bytes()).hexdigest()

from delivery.trainingpeaks.phase5_service import Phase5ReadbackMismatch
from delivery.trainingpeaks.playwright_transport import (
    RECEIPT_TYPE,
    PlaywrightTransport,
    PlaywrightTransportConfig,
    PlaywrightTransportError,
    compile_playwright_request,
)


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _contract():
    create_payload = {
        "date": "2026-10-05", "title": "Phase 5 RPE canary",
        "description": "Transport fixture", "tp_workout_type": 2,
        "total_seconds": 1800, "tss_planned": 20,
        "structure": {"primaryIntensityMetric": "rpe", "structure": []},
    }
    return {
        "contract_version": "apply_contract/v1",
        "order_id": "canary_cheesehead",
        "tp_athlete_id": "1522591",
        "generation_revision": 1,
        "model_seal": "a" * 64,
        "operations": [
            {
                "op_id": "canary_cheesehead:workout_upsert:protected@r1",
                "logical_id": "canary_cheesehead:workout_upsert:protected",
                "kind": "workout_upsert", "disposition": "keep",
                "expected_digest": "1" * 64,
            },
            {
                "op_id": "canary_cheesehead:workout_upsert:2026-10-05#1@r1",
                "logical_id": "canary_cheesehead:workout_upsert:2026-10-05#1",
                "kind": "workout_upsert", "disposition": "create",
                "payload": create_payload, "expected_digest": _digest(create_payload),
                "remote_marker": "canary_cheesehead:workout_upsert:2026-10-05#1",
                "rollback": {"strategy": "delete_by_remote_id"},
            },
        ],
    }


@dataclass
class _Grant:
    claims: dict


class _Context:
    def __init__(self, contract):
        self.contract = contract
        self.grant = _Grant({
            "action": "apply", "order_id": contract["order_id"],
            "grant_id": "grant_0000000000000001",
            "request_digest": _digest(contract),
        })
        self.intents = []
        self.receipts = []

    @property
    def prior_receipts(self):
        return []

    def persist_intent(self, operation):
        self.intents.append(operation["op_id"])

    def record_receipt(self, operation, **receipt):
        self.receipts.append({"op_id": operation["op_id"], **receipt})


def _valid_receipt(request):
    operations = []
    for operation in request["operations"]:
        keep = operation["disposition"] == "keep"
        operations.append({
            "op_id": operation["op_id"],
            "status": "kept" if keep else "landed",
            "remote_id": "existing-protected" if keep else "created-canary",
            "observed_digest": operation["expected_digest"],
            "reconciled_after_error": False,
        })
    return {
        "receipt_type": RECEIPT_TYPE,
        "contract_digest": request["contract_digest"],
        "action": request["action"], "dry_run": False,
        "tp_athlete_id": request["tp_athlete_id"],
        "script_sha256": request["script_sha256"],
        "started_at": "2026-08-22T00:00:00Z",
        "finished_at": "2026-08-22T00:00:01Z",
        "readback_verified": True, "rollback_verified": False,
        "failure": None,
        "operations": operations,
    }


def test_compile_request_is_exact_and_credential_free():
    contract = _contract()
    request = compile_playwright_request(
        contract, action="apply", dry_run=True, script_sha256=PAYLOAD_SHA)
    assert request["contract_digest"] == _digest(contract)
    assert request["operations"] == contract["operations"]
    assert request["dry_run"] is True
    encoded = json.dumps(request).lower()
    assert "cookie" not in encoded
    assert "authorization" not in encoded
    assert "grant_id" not in encoded


def test_transport_journals_intent_before_runner_and_ingests_exact_receipt(tmp_path):
    context = _Context(_contract())
    observed = {}

    def runner(argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        assert context.intents == [context.contract["operations"][1]["op_id"]]
        request_path = Path(argv[argv.index("--request") + 1])
        receipt_path = Path(argv[argv.index("--receipt") + 1])
        assert request_path.stat().st_mode & 0o777 == 0o600
        request = json.loads(request_path.read_text())
        receipt_path.write_text(json.dumps(_valid_receipt(request)))
        return subprocess.CompletedProcess(argv, 0)

    config = PlaywrightTransportConfig.create(
        ["reviewed-playwright-runner", "--profile", "coach"],
        tmp_path / "staging", PAYLOAD_PATH)
    result = PlaywrightTransport(config, process_runner=runner)(context)

    assert result == {"readback_verified": True}
    assert [item["status"] for item in context.receipts] == ["kept", "landed"]
    assert observed["argv"][:3] == (
        "reviewed-playwright-runner", "--profile", "coach")
    assert observed["kwargs"]["stdout"] is subprocess.DEVNULL
    assert observed["kwargs"]["stderr"] is subprocess.DEVNULL
    assert not list((tmp_path / "staging").rglob("*.json"))


def test_receipt_binding_or_operation_drift_fails_without_forwarding_receipts(tmp_path):
    context = _Context(_contract())

    def runner(argv, **_kwargs):
        request_path = Path(argv[argv.index("--request") + 1])
        receipt_path = Path(argv[argv.index("--receipt") + 1])
        request = json.loads(request_path.read_text())
        receipt = _valid_receipt(request)
        receipt["operations"][1]["observed_digest"] = "f" * 64
        receipt_path.write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(argv, 0)

    config = PlaywrightTransportConfig.create(
        ["reviewed-playwright-runner"], tmp_path / "staging", PAYLOAD_PATH)
    with pytest.raises(Phase5ReadbackMismatch, match="write readback"):
        PlaywrightTransport(config, process_runner=runner)(context)
    assert context.receipts == []
    assert not list((tmp_path / "staging").rglob("*.json"))


def test_runner_failure_is_redacted_and_keeps_remote_state_ambiguous(tmp_path):
    context = _Context(_contract())

    def runner(argv, **_kwargs):
        return subprocess.CompletedProcess(
            argv, 17, stdout="private athlete payload", stderr="session cookie")

    config = PlaywrightTransportConfig.create(
        ["reviewed-playwright-runner"], tmp_path / "staging", PAYLOAD_PATH)
    with pytest.raises(PlaywrightTransportError) as error:
        PlaywrightTransport(config, process_runner=runner)(context)
    assert str(error.value) == "Playwright runner failed with exit code 17"
    assert context.intents
    assert context.receipts == []


def test_receipt_rejects_dry_run_as_live_evidence(tmp_path):
    context = _Context(_contract())

    def runner(argv, **_kwargs):
        request_path = Path(argv[argv.index("--request") + 1])
        receipt_path = Path(argv[argv.index("--receipt") + 1])
        receipt = _valid_receipt(json.loads(request_path.read_text()))
        receipt["dry_run"] = True
        receipt_path.write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(argv, 0)

    config = PlaywrightTransportConfig.create(
        ["reviewed-playwright-runner"], tmp_path / "staging", PAYLOAD_PATH)
    with pytest.raises(PlaywrightTransportError, match="non-dry-run"):
        PlaywrightTransport(config, process_runner=runner)(context)


def test_receipt_is_bound_to_the_server_selected_browser_payload(tmp_path):
    context = _Context(_contract())

    def runner(argv, **_kwargs):
        request_path = Path(argv[argv.index("--request") + 1])
        receipt_path = Path(argv[argv.index("--receipt") + 1])
        receipt = _valid_receipt(json.loads(request_path.read_text()))
        receipt["script_sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(argv, 0)

    config = PlaywrightTransportConfig.create(
        ["reviewed-playwright-runner"], tmp_path / "staging", PAYLOAD_PATH)
    with pytest.raises(PlaywrightTransportError, match="script digest mismatch"):
        PlaywrightTransport(config, process_runner=runner)(context)


def test_browser_payload_fake_remote_round_trip():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the browser payload harness")
    completed = subprocess.run(
        [node, str(ROOT / "tools" / "test_tp_phase5_browser_payload.mjs")],
        check=False, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "tp_phase5_browser_payload: ok"


def test_canonical_cli_fails_redacted_when_server_secrets_are_unavailable(
    tmp_path, monkeypatch, capsys,
):
    from tools.tp_phase5_execute import main

    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(_contract()))
    state_path = tmp_path / "state.json"
    state_path.write_text("{}")
    capability_path = tmp_path / "capability.txt"
    capability_path.write_text("private-capability-value")
    capability_path.chmod(0o600)
    monkeypatch.delenv("GG_WORKER_CAPABILITY_SECRET", raising=False)
    monkeypatch.delenv("GG_TP_EXECUTION_GRANT_SECRET", raising=False)

    result = main([
        "--contract", str(contract_path), "--state", str(state_path),
        "--capability-file", str(capability_path),
        "--record-root", str(tmp_path / "records"),
        "--staging-root", str(tmp_path / "staging"),
    ])
    captured = capsys.readouterr()
    assert result == 1
    assert json.loads(captured.err) == {
        "status": "failed", "error_type": "ValueError"}
    assert "private-capability-value" not in captured.err
