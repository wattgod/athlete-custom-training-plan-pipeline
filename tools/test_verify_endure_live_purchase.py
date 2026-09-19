import hashlib
import stat

import pytest
import requests

from tools.verify_endure_live_purchase import (
    ENDURE_URL,
    PIPELINE_URL,
    ProductionTransport,
    VerificationFailure,
    _write_receipt,
    validate_pipeline_receipt,
    validate_stripe_receipt,
    verify_live_purchase,
)

ORDER_ID = "cs_live_verified123"
EMAIL = "pilot@example.com"
EMAIL_DIGEST = hashlib.sha256(EMAIL.encode()).hexdigest()
PIPELINE_SHA = "1" * 40
ENDURE_SHA = "2" * 40
RELEASE = {
    "generation_revision": 2,
    "release_manifest_digest": "a" * 64,
    "model_seal": "b" * 64,
}
STAGE = {
    "order_id": ORDER_ID,
    "athlete_id": "athlete-1",
    "plan_id": "plan-1",
    "block_id": "block-1",
    "invitation_id": "invite-1",
    "invite_url": f"{ENDURE_URL}/invite/token",
    "linked_account": True,
    "invitation_accepted": False,
    "recipient_email_sha256": EMAIL_DIGEST,
    "release": RELEASE,
    "status": "ready_for_review",
}
CALENDAR = {"status": "verified", "expectedCount": 7, "actualCount": 7}


def _health(**delivery_overrides):
    return {
        "status": "ok",
        "deployment_sha": PIPELINE_SHA,
        "endure_delivery": {
            "enabled": True,
            "default_target": "trainingpeaks",
            **delivery_overrides,
        },
    }


def _stripe(**overrides):
    receipt = {
        "id": ORDER_ID,
        "livemode": True,
        "mode": "payment",
        "status": "complete",
        "payment_status": "paid",
        "amount_total": 14900,
        "currency": "usd",
        "client_reference_id": "intake-1",
        "customer_details": {"email": EMAIL},
        "metadata": {
            "intake_id": "intake-1",
            "brand": "gravelgod",
            "product_type": "training_plan",
            "tier": "custom",
            "delivery_target": "endure",
        },
    }
    receipt.update(overrides)
    return receipt


def _pipeline(**overrides):
    state = {
        "order_id": ORDER_ID,
        "delivery_platform": "endure",
        "status": "CONFIRMED",
        "seal_verified": True,
        "release_authorized": True,
        "generation_revision": 2,
        "release_manifest_digest": "a" * 64,
        "model_seal": "b" * 64,
        "endure_stage": STAGE,
        "endure_confirmation_attempt": {
            "status": "accepted",
            "recipient_email_sha256": EMAIL_DIGEST,
            "calendar_verification": CALENDAR,
        },
        "confirmation": {
            "provider": "resend",
            "recipient_email_sha256": EMAIL_DIGEST,
            "endure_stage": STAGE,
            "calendar_verification": CALENDAR,
        },
    }
    state.update(overrides)
    return state


def _readiness(**overrides):
    body = {
        **STAGE,
        "status": "ready_for_athlete",
        "calendar_verification": CALENDAR,
    }
    body.update(overrides)
    return body


class FakeTransport:
    def __init__(
        self, *, health=None, version=None, stripe=None, pipeline=None, readiness=None
    ):
        self.health = health or _health()
        self.version = version or {"sha": ENDURE_SHA, "env": "production"}
        self.stripe = stripe or _stripe()
        self.pipeline = pipeline or _pipeline()
        self.readiness = readiness or _readiness()
        self.operations = []

    def get_json(self, label, url, *, headers=None, params=None):
        self.operations.append(("GET", label, url))
        return {
            "pipeline_health": self.health,
            "endure_version": self.version,
            "pipeline_status": self.pipeline,
            "endure_readiness": self.readiness,
        }[label]

    def stripe_session(self, order_id, secret_key):
        self.operations.append(("STRIPE_RETRIEVE", order_id, secret_key))
        return self.stripe


def _verify(transport=None, **overrides):
    args = {
        "order_id": ORDER_ID,
        "stripe_secret": "rk_live_secret-value",
        "cron_secret": "cron-secret-value",
        "delivery_secret": "delivery-secret-value",
        "expected_pipeline_sha": PIPELINE_SHA,
        "expected_endure_sha": ENDURE_SHA,
        "transport": transport or FakeTransport(),
    }
    args.update(overrides)
    return verify_live_purchase(**args)


def test_exact_three_way_binding_emits_redacted_single_order_receipt():
    transport = FakeTransport()
    receipt = _verify(transport)
    encoded = str(receipt)
    assert receipt["schema"] == "endure_live_purchase_receipt/v1"
    assert receipt["rollout_authorized"] is False
    assert receipt["calendar_count"] == 7
    for raw in (
        ORDER_ID,
        EMAIL,
        "athlete-1",
        "plan-1",
        "block-1",
        "invite-1",
        "token",
        "cron-secret-value",
        "delivery-secret-value",
        "rk_live_secret-value",
    ):
        assert raw not in encoded
    assert [operation[0] for operation in transport.operations] == [
        "GET",
        "GET",
        "STRIPE_RETRIEVE",
        "GET",
        "GET",
    ]
    assert transport.operations[0][2] == f"{PIPELINE_URL}/health"


def test_receipt_file_is_private_and_contains_no_raw_identity(tmp_path):
    receipt = _verify()
    path = tmp_path / "receipt.json"
    _write_receipt(path, receipt)
    encoded = path.read_text()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    for raw in (ORDER_ID, EMAIL, "athlete-1", "plan-1", "block-1", "invite-1"):
        assert raw not in encoded


def test_transport_redacts_provider_exception(monkeypatch):
    leaked = "sk_live_do-not-print"
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectionError(leaked)),
    )
    with pytest.raises(VerificationFailure) as caught:
        ProductionTransport().get_json("pipeline_health", f"{PIPELINE_URL}/health")
    assert caught.value.code == "pipeline_health_unavailable"
    assert leaked not in str(caught.value)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"order_id": "cs_test_123"}, "order_id_not_live_checkout"),
        ({"stripe_secret": "sk_test_secret"}, "stripe_key_not_live"),
        ({"expected_pipeline_sha": "short"}, "pipeline_sha_invalid"),
        ({"expected_endure_sha": "short"}, "endure_sha_invalid"),
    ],
)
def test_configuration_fails_closed(override, code):
    with pytest.raises(VerificationFailure, match=code):
        _verify(**override)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"livemode": False}, "stripe_not_live"),
        ({"payment_status": "unpaid"}, "stripe_not_paid"),
        ({"status": "open"}, "stripe_not_complete"),
        ({"currency": "cad"}, "stripe_currency_mismatch"),
        ({"client_reference_id": "other"}, "stripe_intake_binding_mismatch"),
    ],
)
def test_stripe_receipt_fails_closed(override, code):
    with pytest.raises(VerificationFailure, match=code):
        validate_stripe_receipt(ORDER_ID, _stripe(**override))


def test_stripe_requires_exact_endure_metadata():
    metadata = {**_stripe()["metadata"], "delivery_target": "trainingpeaks"}
    with pytest.raises(VerificationFailure, match="stripe_delivery_target_mismatch"):
        validate_stripe_receipt(ORDER_ID, _stripe(metadata=metadata))


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"status": "APPROVED"}, "pipeline_not_confirmed"),
        ({"release_authorized": False}, "pipeline_release_unauthorized"),
        ({"seal_verified": False}, "pipeline_seal_unverified"),
    ],
)
def test_pipeline_receipt_rejects_partial_authority(override, code):
    with pytest.raises(VerificationFailure, match=code):
        validate_pipeline_receipt(
            ORDER_ID, _pipeline(**override), recipient_email_sha256=EMAIL_DIGEST
        )


def test_pipeline_binds_stripe_buyer_to_endure_recipient():
    other = hashlib.sha256(b"other@example.com").hexdigest()
    with pytest.raises(VerificationFailure, match="pipeline_recipient_mismatch"):
        validate_pipeline_receipt(ORDER_ID, _pipeline(), recipient_email_sha256=other)


def test_pipeline_requires_exact_confirmed_stage():
    confirmation = {
        **_pipeline()["confirmation"],
        "endure_stage": {**STAGE, "plan_id": "another-plan"},
    }
    with pytest.raises(
        VerificationFailure, match="pipeline_confirmation_stage_mismatch"
    ):
        validate_pipeline_receipt(
            ORDER_ID,
            _pipeline(confirmation=confirmation),
            recipient_email_sha256=EMAIL_DIGEST,
        )


def test_idempotent_endure_stage_status_is_valid():
    stage = {**STAGE, "status": "already_ready_for_review"}
    state = _pipeline(
        endure_stage=stage,
        confirmation={**_pipeline()["confirmation"], "endure_stage": stage},
    )
    verified_stage, count = validate_pipeline_receipt(
        ORDER_ID, state, recipient_email_sha256=EMAIL_DIGEST
    )
    assert verified_stage == stage
    assert count == 7


def test_production_default_must_remain_trainingpeaks():
    transport = FakeTransport(health=_health(default_target="endure"))
    with pytest.raises(VerificationFailure, match="pipeline_default_target_unsafe"):
        _verify(transport)


def test_unpinned_deployment_fails_before_stripe_lookup():
    transport = FakeTransport(health={**_health(), "deployment_sha": "f" * 40})
    with pytest.raises(VerificationFailure, match="pipeline_deployment_mismatch"):
        _verify(transport)
    assert [operation[0] for operation in transport.operations] == ["GET"]


def test_unpinned_endure_deployment_fails_before_stripe_lookup():
    transport = FakeTransport(version={"sha": "f" * 40, "env": "production"})
    with pytest.raises(VerificationFailure, match="endure_deployment_mismatch"):
        _verify(transport)
    assert [operation[0] for operation in transport.operations] == ["GET", "GET"]


def test_already_consented_linked_account_is_a_valid_delivery_path():
    stage = {
        **STAGE,
        "invitation_accepted": True,
        "invitation_id": None,
        "invite_url": None,
    }
    state = _pipeline(
        endure_stage=stage,
        confirmation={**_pipeline()["confirmation"], "endure_stage": stage},
    )
    verified_stage, count = validate_pipeline_receipt(
        ORDER_ID, state, recipient_email_sha256=EMAIL_DIGEST
    )
    assert verified_stage == stage
    assert count == 7


def test_accepted_invitation_cannot_retain_live_capability():
    stage = {**STAGE, "invitation_accepted": True}
    with pytest.raises(
        VerificationFailure,
        match="pipeline_accepted_invitation_retains_capability",
    ):
        validate_pipeline_receipt(
            ORDER_ID,
            _pipeline(endure_stage=stage),
            recipient_email_sha256=EMAIL_DIGEST,
        )


def test_live_calendar_must_match_confirmed_calendar_count():
    transport = FakeTransport(
        readiness=_readiness(
            calendar_verification={
                "status": "verified",
                "expectedCount": 8,
                "actualCount": 8,
            }
        )
    )
    with pytest.raises(VerificationFailure, match="cross_system_calendar_mismatch"):
        _verify(transport)


def test_endure_readiness_identity_mismatch_fails_closed():
    transport = FakeTransport(readiness=_readiness(plan_id="another-plan"))
    with pytest.raises(VerificationFailure, match="endure_readback_mismatch"):
        _verify(transport)
