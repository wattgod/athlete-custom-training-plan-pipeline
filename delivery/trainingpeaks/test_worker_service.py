import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from delivery.trainingpeaks.worker_service import (
    MUTATION_CAPABILITY_TYPE,
    PROBE_CAPABILITY_TYPE,
    CapabilityCodec,
    CannedProbeTransport,
    ProbeExecutionStore,
    ReadOnlyWorkerService,
    WorkerAuthorizationError,
    WorkerMutationRefused,
    exchange_mutation_capability_phase4,
    mutation_exchange_predicate,
)


NOW = 1_800_000_000
AUDIENCE = "gg-trainingpeaks-worker"
KEYS = {"phase4-k1": "phase4-worker-signing-secret-00001"}


def _codec():
    return CapabilityCodec(KEYS, audience=AUDIENCE)


def _probe_claims(action="probe", **overrides):
    claims = {
        "order_id": "order_phase4_worker",
        "subject": {"kind": "identity_query", "email": "fixture@example.invalid"},
        "action": action,
        "audience": AUDIENCE,
        "iat": NOW - 1,
        "exp": NOW + 300,
        "jti": "probe-jti-00000000000001",
    }
    claims.update(overrides)
    return claims


def _mutation_claims(action="apply", **overrides):
    claims = {
        "order_id": "order_phase4_worker",
        "tp_athlete_id": "fixture-athlete-m",
        "generation_revision": 4,
        "model_seal": "a" * 64,
        "action": action,
        "audience": AUDIENCE,
        "iat": NOW - 1,
        "exp": NOW + 120,
        "jti": "mutation-jti-0000000001",
    }
    claims.update(overrides)
    return claims


def test_probe_capability_executes_canned_transport_and_replay_returns_recorded_result(tmp_path):
    fixture = json.loads((ROOT / "tests/fixtures/athlete_m/worker_probes.json").read_text())
    transport = CannedProbeTransport(fixture)
    service = ReadOnlyWorkerService(
        _codec(), ProbeExecutionStore(tmp_path / "jti"), transport)
    token = _codec().issue(_probe_claims(), kid="phase4-k1")

    first = service.probe_athlete(
        {"email": "fixture@example.invalid"}, token, now=NOW)
    second = service.probe_athlete(
        {"email": "fixture@example.invalid"}, token, now=NOW)

    assert first == second == {
        "outcome": "bound", "tp_athlete_id": "fixture-athlete-m",
        "candidates": [],
    }
    assert transport.calls == [("probe", {"email": "fixture@example.invalid"})]
    record = json.loads(next((tmp_path / "jti/order_phase4_worker").glob("*.json")).read_text())
    assert record["status"] == "succeeded"
    assert record["order_id"] == "order_phase4_worker"


def test_inspect_capability_is_bound_to_tp_id_and_returns_exact_fixture(tmp_path):
    fixture = json.loads((ROOT / "tests/fixtures/athlete_m/worker_probes.json").read_text())
    transport = CannedProbeTransport(fixture)
    service = ReadOnlyWorkerService(_codec(), ProbeExecutionStore(tmp_path), transport)
    claims = _probe_claims(
        action="inspect",
        subject={"kind": "identity_query", "tp_athlete_id": "fixture-athlete-m"},
        jti="inspect-jti-0000000000001",
    )
    token = _codec().issue(claims, kid="phase4-k1")
    result = service.inspect_account("fixture-athlete-m", token, now=NOW)
    assert {key: result[key] for key in fixture} == fixture
    assert result["tp_athlete_id"] == "fixture-athlete-m"
    with pytest.raises(WorkerAuthorizationError, match="subject"):
        service.inspect_account("different-athlete", token, now=NOW)


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda claims: claims.update(audience="wrong"), "audience"),
        (lambda claims: claims.update(exp=NOW), "currently valid"),
        (lambda claims: claims.update(iat=NOW + 1), "currently valid"),
        (lambda claims: claims.update(extra=True), "shape"),
        (lambda claims: claims["subject"].update(tp_athlete_id="also"), "exactly one"),
    ],
)
def test_probe_capability_validation_fails_closed(mutator, message):
    claims = _probe_claims()
    mutator(claims)
    token = _codec().issue(claims, kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match=message):
        _codec().verify(token, now=NOW)


def test_tampered_signature_and_unknown_kid_fail_closed():
    token = _codec().issue(_probe_claims(), kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match="signature"):
        _codec().verify(token[:-1] + ("A" if token[-1] != "A" else "B"), now=NOW)
    other = CapabilityCodec(
        {"other-kid": "other-worker-signing-secret-0000001"}, audience=AUDIENCE)
    unknown = other.issue(_probe_claims(), kid="other-kid")
    with pytest.raises(WorkerAuthorizationError, match="unknown"):
        _codec().verify(unknown, now=NOW)


def test_same_jti_with_different_request_is_rejected(tmp_path):
    transport = CannedProbeTransport({"account_found": True, "coached": True})
    service = ReadOnlyWorkerService(_codec(), ProbeExecutionStore(tmp_path), transport)
    token = _codec().issue(_probe_claims(), kid="phase4-k1")
    service.probe_athlete({"email": "fixture@example.invalid"}, token, now=NOW)
    with pytest.raises(WorkerAuthorizationError, match="subject"):
        service.probe_athlete({"email": "other@example.invalid"}, token, now=NOW)


def test_mutation_capability_type_and_action_specific_predicates_are_offline_only():
    codec = _codec()
    token = codec.issue(_mutation_claims(), kid="phase4-k1")
    verified = codec.verify(token, now=NOW)
    assert verified.capability_type == MUTATION_CAPABILITY_TYPE
    state = {
        "order_id": "order_phase4_worker", "generation_revision": 4,
        "model_seal": "a" * 64, "status": "APPROVED",
        "platform_identity": {"tp_athlete_id": "fixture-athlete-m"},
        "cancel_requested": False,
    }
    assert mutation_exchange_predicate(verified, state) == (True, "apply-initial")
    assert mutation_exchange_predicate(
        verified, {**state, "status": "APPLYING"},
        attempt={
            "jti": verified.claims["jti"], "request_digest": "request-digest",
            "status": "running",
        }, request_digest="request-digest",
    ) == (True, "apply-resume")
    assert mutation_exchange_predicate(
        verified, {**state, "status": "APPLYING"},
        attempt={
            "jti": verified.claims["jti"], "request_digest": "different",
            "status": "running",
        }, request_digest="request-digest",
    )[0] is False

    verify_cap = codec.verify(
        codec.issue(_mutation_claims(action="verify", jti="verify-jti-00000000000001"),
                    kid="phase4-k1"), now=NOW)
    assert mutation_exchange_predicate(verify_cap, {**state, "status": "APPLIED"}) == (
        True, "verify")
    rollback_cap = codec.verify(
        codec.issue(_mutation_claims(action="rollback", jti="rollback-jti-0000000001"),
                    kid="phase4-k1"), now=NOW)
    assert mutation_exchange_predicate(
        rollback_cap, {**state, "status": "CANCELLED", "compensation_pending": True},
        operator_authorized=True,
    ) == (True, "rollback")
    assert mutation_exchange_predicate(
        rollback_cap, {**state, "status": "APPLIED"},
        operator_authorized=False,
    )[0] is False


def test_probe_tokens_can_never_validate_as_mutations():
    token = _codec().issue(_probe_claims(), kid="phase4-k1")
    verified = _codec().verify(token, now=NOW)
    assert verified.capability_type == PROBE_CAPABILITY_TYPE
    assert mutation_exchange_predicate(verified, {})[0] is False


def test_all_mutation_entrypoints_and_grant_issuance_refuse_before_transport(tmp_path):
    transport = CannedProbeTransport({"account_found": True, "coached": True})
    service = ReadOnlyWorkerService(_codec(), ProbeExecutionStore(tmp_path), transport)
    for operation in (service.apply, service.verify, service.rollback):
        with pytest.raises(WorkerMutationRefused, match="REFUSED"):
            operation({"would": "write"})
    with pytest.raises(WorkerMutationRefused, match="zero remote writes"):
        exchange_mutation_capability_phase4()
    assert transport.calls == []
