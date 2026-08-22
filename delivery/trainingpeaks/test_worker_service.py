import base64
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


def _service(root, transport):
    codec = _codec()
    return ReadOnlyWorkerService(
        codec, ProbeExecutionStore(root, codec), transport)


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


def _mutation_claims(action="trainingpeaks.apply", **overrides):
    claims = {
        "order_id": "order_phase4_worker",
        "tp_athlete_id": "fixture-athlete-m",
        "generation_revision": 4,
        "model_seal": "a" * 64,
        "contract_digest": "b" * 64,
        "approval_digest": "c" * 64,
        "release_manifest_digest": "d" * 64,
        "authorization_id": "authorization-phase5-0001",
        "actor": "coach:fixture",
        "scope": "trainingpeaks:athlete-calendar",
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
    service = _service(tmp_path / "jti", transport)
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
    assert record["record_type"] == "trainingpeaks_probe_execution/v3"
    assert record["capability_token"] == token


def test_inspect_capability_is_bound_to_tp_id_and_returns_exact_fixture(tmp_path):
    fixture = json.loads((ROOT / "tests/fixtures/athlete_m/worker_probes.json").read_text())
    transport = CannedProbeTransport(fixture)
    service = _service(tmp_path, transport)
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


def test_fresh_jti_after_terminal_probe_fetches_and_records_fresh_data(tmp_path):
    class ChangingTransport:
        def __init__(self):
            self.calls = 0

        def probe_athlete(self, _identity):
            self.calls += 1
            return {
                "outcome": "bound", "tp_athlete_id": f"athlete-{self.calls}",
                "candidates": [],
            }

        def inspect_account(self, _tp_athlete_id):
            raise AssertionError("not used")

    transport = ChangingTransport()
    service = _service(tmp_path / "jti", transport)
    first_token = _codec().issue(
        _probe_claims(jti="probe-attempt-000000000001"), kid="phase4-k1")
    second_token = _codec().issue(
        _probe_claims(jti="probe-attempt-000000000002", iat=NOW - 2),
        kid="phase4-k1")

    first = service.probe_athlete(
        {"email": "fixture@example.invalid"}, first_token, now=NOW)
    second = service.probe_athlete(
        {"email": "fixture@example.invalid"}, second_token, now=NOW)

    assert first["tp_athlete_id"] == "athlete-1"
    assert second["tp_athlete_id"] == "athlete-2"
    assert transport.calls == 2
    assert len(list((tmp_path / "jti/order_phase4_worker").glob("*.json"))) == 2


def test_verified_inspection_evidence_binds_capability_and_request_digest(tmp_path):
    fixture = json.loads((ROOT / "tests/fixtures/athlete_m/worker_probes.json").read_text())
    service = _service(tmp_path, CannedProbeTransport(fixture))
    claims = _probe_claims(
        action="inspect",
        subject={"kind": "identity_query", "tp_athlete_id": "fixture-athlete-m"},
        jti="inspect-evidence-0000000001",
    )
    evidence = service.inspect_account_evidence(
        "fixture-athlete-m", _codec().issue(claims, kid="phase4-k1"), now=NOW)
    assert evidence.order_id == claims["order_id"]
    assert evidence.capability_jti == claims["jti"]
    assert evidence.capability_kid == "phase4-k1"
    assert len(evidence.request_digest) == 64
    assert evidence.observed_at == "2027-01-15T08:00:00Z"
    assert evidence.result["lthr_bpm"] == 148


def test_run_record_refuses_unsigned_claims_before_creating_any_record(tmp_path):
    codec = _codec()
    store = ProbeExecutionStore(tmp_path, codec)
    claims = _probe_claims(
        action="inspect",
        subject={"kind": "identity_query", "tp_athlete_id": "fixture-athlete-m"},
        jti="unsigned-inspect-0000000001",
    )
    operation_called = False

    def operation():
        nonlocal operation_called
        operation_called = True
        return {"tp_athlete_id": "fixture-athlete-m", "lthr_bpm": 155}

    with pytest.raises(WorkerAuthorizationError, match="encoding"):
        store.run_record(
            claims,
            {"operation": "inspect_account", "tp_athlete_id": "fixture-athlete-m"},
            operation, now=NOW,
        )

    assert operation_called is False
    assert list(tmp_path.rglob("*.json")) == []


def test_run_record_checks_capability_action_and_expiry_itself(tmp_path):
    codec = _codec()
    store = ProbeExecutionStore(tmp_path, codec)
    request = {
        "operation": "inspect_account", "tp_athlete_id": "fixture-athlete-m",
    }
    probe_token = codec.issue(_probe_claims(), kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match="action mismatch"):
        store.run_record(probe_token, request, lambda: {}, now=NOW)

    expired_claims = _probe_claims(
        action="inspect",
        subject={"kind": "identity_query", "tp_athlete_id": "fixture-athlete-m"},
        iat=NOW - 301, exp=NOW - 1, jti="expired-inspect-0000000001",
    )
    expired_token = codec.issue(expired_claims, kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match="currently valid"):
        store.run_record(expired_token, request, lambda: {}, now=NOW)

    assert list(tmp_path.rglob("*.json")) == []


def test_probe_store_rejects_symlinked_order_directory_before_transport(tmp_path):
    codec = _codec()
    root = tmp_path / "records"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "order_phase4_worker").symlink_to(outside, target_is_directory=True)
    store = ProbeExecutionStore(root, codec)
    claims = _probe_claims(
        action="inspect",
        subject={"kind": "identity_query", "tp_athlete_id": "fixture-athlete-m"},
        jti="symlink-inspect-0000000001",
    )
    token = codec.issue(claims, kid="phase4-k1")
    operation_called = False

    def operation():
        nonlocal operation_called
        operation_called = True
        return {"tp_athlete_id": "fixture-athlete-m", "lthr_bpm": 155}

    with pytest.raises(WorkerAuthorizationError, match="directory is unsafe"):
        store.run_record(
            token,
            {"operation": "inspect_account", "tp_athlete_id": "fixture-athlete-m"},
            operation, now=NOW,
        )

    assert operation_called is False
    assert list(outside.iterdir()) == []


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


@pytest.mark.parametrize(
    "claims, message",
    [
        (_probe_claims(exp=NOW + 901), "lifetime"),
        (_probe_claims(jti="short"), "jti"),
        (_probe_claims(iat=True), "iat"),
        (_probe_claims(exp=True), "exp"),
        (_mutation_claims(extra=True), "shape"),
    ],
)
def test_capability_edge_shapes_fail_closed(claims, message):
    token = _codec().issue(claims, kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match=message):
        _codec().verify(token, now=NOW)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"action": "apply"}, "action"),
        ({"contract_digest": "short"}, "contract_digest"),
        ({"approval_digest": "short"}, "approval_digest"),
        ({"release_manifest_digest": "short"}, "release_manifest_digest"),
        ({"authorization_id": "short"}, "authorization_id"),
        ({"actor": "coach@example.invalid"}, "actor"),
        ({"scope": "trainingpeaks:anything"}, "scope"),
    ],
)
def test_mutation_authorization_claims_are_closed_and_typed(overrides, message):
    token = _codec().issue(_mutation_claims(**overrides), kid="phase4-k1")
    with pytest.raises(WorkerAuthorizationError, match=message):
        _codec().verify(token, now=NOW)


def test_malformed_header_and_wrong_expected_action_fail_closed():
    token = _codec().issue(_probe_claims(), kid="phase4-k1")
    _header, payload, signature = token.split(".")
    malformed = base64.urlsafe_b64encode(json.dumps({
        "alg": "HS256", "kid": "phase4-k1", "typ": "GG-WORKER-CAP",
        "extra": True,
    }).encode()).rstrip(b"=").decode()
    with pytest.raises(WorkerAuthorizationError, match="header"):
        _codec().verify(f"{malformed}.{payload}.{signature}", now=NOW)
    with pytest.raises(WorkerAuthorizationError, match="action mismatch"):
        _codec().verify(token, now=NOW, expected_action="inspect")


def test_same_jti_with_different_request_is_rejected(tmp_path):
    transport = CannedProbeTransport({"account_found": True, "coached": True})
    service = _service(tmp_path, transport)
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
    assert mutation_exchange_predicate(
        verified, state, request_digest="b" * 64,
    ) == (True, "apply-initial")
    assert mutation_exchange_predicate(
        verified, {**state, "status": "APPLYING"},
        attempt={
            "jti": verified.claims["jti"], "request_digest": "b" * 64,
            "status": "running",
        }, request_digest="b" * 64,
    ) == (True, "apply-resume")
    assert mutation_exchange_predicate(
        verified, {**state, "status": "APPLYING"},
        attempt={
            "jti": verified.claims["jti"], "request_digest": "different",
            "status": "running",
        }, request_digest="b" * 64,
    )[0] is False

    verify_cap = codec.verify(
        codec.issue(_mutation_claims(
            action="trainingpeaks.verify", jti="verify-jti-00000000000001"),
                    kid="phase4-k1"), now=NOW)
    assert mutation_exchange_predicate(
        verify_cap, {**state, "status": "APPLIED"}, request_digest="b" * 64,
    ) == (
        True, "verify")
    rollback_cap = codec.verify(
        codec.issue(_mutation_claims(
            action="trainingpeaks.rollback", jti="rollback-jti-0000000001"),
                    kid="phase4-k1"), now=NOW)
    assert mutation_exchange_predicate(
        rollback_cap, {**state, "status": "CANCELLED", "compensation_pending": True},
        request_digest="b" * 64,
    ) == (True, "rollback")
    assert mutation_exchange_predicate(
        rollback_cap, {**state, "status": "APPLIED"},
        request_digest="b" * 64,
    ) == (True, "rollback")


def test_probe_tokens_can_never_validate_as_mutations():
    token = _codec().issue(_probe_claims(), kid="phase4-k1")
    verified = _codec().verify(token, now=NOW)
    assert verified.capability_type == PROBE_CAPABILITY_TYPE
    assert mutation_exchange_predicate(verified, {})[0] is False


def test_all_mutation_entrypoints_and_grant_issuance_refuse_before_transport(tmp_path):
    transport = CannedProbeTransport({"account_found": True, "coached": True})
    service = _service(tmp_path, transport)
    for operation in (service.apply, service.verify, service.rollback):
        with pytest.raises(WorkerMutationRefused, match="REFUSED"):
            operation({"would": "write"})
    with pytest.raises(WorkerMutationRefused, match="zero remote writes"):
        exchange_mutation_capability_phase4()
    assert transport.calls == []
