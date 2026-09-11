#!/usr/bin/env python3
"""Create a diagnostic receipt for one paid Gravel God to Endure handoff.

The verifier binds live Stripe payment, the production pipeline's sealed
fulfillment state, and Endure's canonical calendar readback. It issues only
provider retrievals and HTTP GETs; the GET handlers may perform their existing
fail-closed integrity reconciliation. The tool cannot stage, confirm, email,
enroll, delete, or authorize a broader rollout.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from webhook import endure_delivery  # noqa: E402

PIPELINE_URL = "https://athlete-custom-training-plan-pipeline-production.up.railway.app"
ENDURE_URL = "https://endurelabs.app"
ORDER_PATTERN = re.compile(r"^cs_live_[A-Za-z0-9]+$")
SHA1_PATTERN = re.compile(r"^[a-f0-9]{40}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
LIVE_KEY_PATTERN = re.compile(r"^(?:rk|sk)_live_")


class VerificationFailure(RuntimeError):
    """A fixed, non-sensitive failure safe to emit to operator logs."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise VerificationFailure(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        _fail(code)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        _fail(f"missing_{name.lower()}")
    return value


def _field(record: object, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _email_digest(email: object) -> str:
    normalized = str(email or "").strip().lower()
    _require(bool(normalized and "@" in normalized), "stripe_email_missing")
    return _digest(normalized)


def _valid_sha256(value: object) -> bool:
    return SHA256_PATTERN.fullmatch(str(value or "")) is not None


class ProductionTransport:
    """GET-only provider transport with redacted failure surfaces."""

    def get_json(
        self,
        label: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
        except requests.RequestException:
            _fail(f"{label}_unavailable")
        if response.status_code != 200:
            _fail(f"{label}_http_error")
        try:
            body = response.json()
        except ValueError:
            _fail(f"{label}_invalid_json")
        _require(isinstance(body, dict), f"{label}_invalid_body")
        return body

    def stripe_session(self, order_id: str, secret_key: str) -> object:
        try:
            import stripe
        except ImportError:
            _fail("stripe_sdk_unavailable")
        stripe.api_key = secret_key
        try:
            return stripe.checkout.Session.retrieve(order_id)
        except Exception:  # Stripe's exception hierarchy varies by SDK version.
            _fail("stripe_lookup_failed")


def validate_health(
    health: object,
    *,
    expected_pipeline_sha: str,
) -> None:
    _require(isinstance(health, dict), "pipeline_health_invalid")
    _require(health.get("status") == "ok", "pipeline_health_not_ok")
    _require(
        health.get("deployment_sha") == expected_pipeline_sha,
        "pipeline_deployment_mismatch",
    )
    delivery = health.get("endure_delivery")
    _require(isinstance(delivery, dict), "pipeline_delivery_health_missing")
    _require(delivery.get("enabled") is True, "pipeline_delivery_disabled")
    _require(
        delivery.get("default_target") == "trainingpeaks",
        "pipeline_default_target_unsafe",
    )


def validate_endure_version(
    version: object,
    *,
    expected_endure_sha: str,
) -> None:
    _require(isinstance(version, dict), "endure_version_invalid")
    _require(version.get("sha") == expected_endure_sha, "endure_deployment_mismatch")
    _require(version.get("env") == "production", "endure_not_production")


def validate_stripe_receipt(order_id: str, session: object) -> str:
    """Return the normalized buyer-email digest for a live paid checkout."""
    _require(_field(session, "id") == order_id, "stripe_order_mismatch")
    _require(_field(session, "livemode") is True, "stripe_not_live")
    _require(_field(session, "mode") == "payment", "stripe_mode_mismatch")
    _require(_field(session, "status") == "complete", "stripe_not_complete")
    _require(_field(session, "payment_status") == "paid", "stripe_not_paid")
    amount = _field(session, "amount_total")
    _require(
        isinstance(amount, int) and not isinstance(amount, bool) and amount > 0,
        "stripe_amount_invalid",
    )
    _require(_field(session, "currency") == "usd", "stripe_currency_mismatch")

    metadata = _field(session, "metadata")
    _require(isinstance(metadata, Mapping), "stripe_metadata_missing")
    expected = {
        "brand": "gravelgod",
        "product_type": "training_plan",
        "tier": "custom",
        "delivery_target": "endure",
    }
    for key, value in expected.items():
        _require(metadata.get(key) == value, f"stripe_{key}_mismatch")
    intake_id = str(metadata.get("intake_id") or "").strip()
    _require(bool(intake_id), "stripe_intake_id_missing")
    _require(
        _field(session, "client_reference_id") == intake_id,
        "stripe_intake_binding_mismatch",
    )

    details = _field(session, "customer_details")
    email = _field(details, "email") or _field(session, "customer_email")
    return _email_digest(email)


def validate_pipeline_receipt(
    order_id: str,
    state: object,
    *,
    recipient_email_sha256: str,
) -> tuple[dict[str, Any], int]:
    """Return source stage and calendar count after validating authority."""
    _require(isinstance(state, dict), "pipeline_status_invalid")
    _require(state.get("order_id") == order_id, "pipeline_order_mismatch")
    _require(
        state.get("delivery_platform") == "endure", "pipeline_destination_mismatch"
    )
    _require(state.get("status") == "CONFIRMED", "pipeline_not_confirmed")
    _require(state.get("seal_verified") is True, "pipeline_seal_unverified")
    _require(state.get("release_authorized") is True, "pipeline_release_unauthorized")
    revision = state.get("generation_revision")
    _require(
        isinstance(revision, int) and not isinstance(revision, bool) and revision > 0,
        "pipeline_revision_invalid",
    )
    _require(
        _valid_sha256(state.get("release_manifest_digest")),
        "pipeline_manifest_digest_invalid",
    )
    _require(_valid_sha256(state.get("model_seal")), "pipeline_model_seal_invalid")

    stage = state.get("endure_stage")
    _require(isinstance(stage, dict), "pipeline_stage_missing")
    _require(stage.get("order_id") == order_id, "pipeline_stage_order_mismatch")
    _require(
        stage.get("status") in {"ready_for_review", "already_ready_for_review"},
        "pipeline_stage_status_invalid",
    )
    _require(
        isinstance(stage.get("linked_account"), bool), "pipeline_linked_account_invalid"
    )
    invitation_accepted = stage.get("invitation_accepted")
    _require(isinstance(invitation_accepted, bool), "pipeline_invitation_state_invalid")
    for key in ("athlete_id", "plan_id", "block_id"):
        _require(
            isinstance(stage.get(key), str) and bool(stage[key].strip()),
            f"pipeline_stage_{key}_missing",
        )
    if invitation_accepted:
        _require(
            stage["linked_account"] is True, "pipeline_accepted_invitation_unlinked"
        )
        _require(
            stage.get("invitation_id") is None and stage.get("invite_url") is None,
            "pipeline_accepted_invitation_retains_capability",
        )
    else:
        _require(
            isinstance(stage.get("invitation_id"), str)
            and bool(stage["invitation_id"].strip()),
            "pipeline_stage_invitation_id_missing",
        )
        _require(
            isinstance(stage.get("invite_url"), str)
            and stage["invite_url"].startswith(f"{ENDURE_URL}/invite/"),
            "pipeline_invite_capability_invalid",
        )
    _require(
        stage.get("recipient_email_sha256") == recipient_email_sha256,
        "pipeline_recipient_mismatch",
    )

    release = stage.get("release")
    expected_release = {
        "generation_revision": revision,
        "release_manifest_digest": state.get("release_manifest_digest"),
        "model_seal": state.get("model_seal"),
    }
    _require(release == expected_release, "pipeline_stage_release_mismatch")

    confirmation = state.get("confirmation")
    _require(isinstance(confirmation, dict), "pipeline_confirmation_missing")
    _require(
        confirmation.get("provider") == "resend",
        "pipeline_confirmation_provider_mismatch",
    )
    _require(
        confirmation.get("recipient_email_sha256") == recipient_email_sha256,
        "pipeline_confirmation_recipient_mismatch",
    )
    _require(
        confirmation.get("endure_stage") == stage,
        "pipeline_confirmation_stage_mismatch",
    )
    attempt = state.get("endure_confirmation_attempt")
    _require(
        isinstance(attempt, dict) and attempt.get("status") == "accepted",
        "pipeline_email_attempt_unaccepted",
    )
    _require(
        attempt.get("recipient_email_sha256") == recipient_email_sha256,
        "pipeline_email_recipient_mismatch",
    )

    calendar = confirmation.get("calendar_verification")
    _require(
        isinstance(calendar, dict) and calendar.get("status") == "verified",
        "pipeline_calendar_unverified",
    )
    count = calendar.get("expectedCount")
    _require(
        isinstance(count, int)
        and not isinstance(count, bool)
        and count > 0
        and calendar.get("actualCount") == count,
        "pipeline_calendar_mismatch",
    )
    _require(
        attempt.get("calendar_verification") == calendar,
        "pipeline_email_calendar_mismatch",
    )
    return stage, count


def _readiness_params(order_id: str, stage: dict[str, Any]) -> dict[str, object]:
    release = stage["release"]
    invitation_accepted = stage["invitation_accepted"]
    params = {
        "order_id": order_id,
        "athlete_id": stage["athlete_id"],
        "plan_id": stage["plan_id"],
        "block_id": stage["block_id"],
        "recipient_email_sha256": stage["recipient_email_sha256"],
        "generation_revision": release["generation_revision"],
        "release_manifest_digest": release["release_manifest_digest"],
        "model_seal": release["model_seal"],
        "linked_account": "true" if stage["linked_account"] else "false",
        "invitation_accepted": "true" if invitation_accepted else "false",
    }
    if not invitation_accepted:
        params["invitation_id"] = stage["invitation_id"]
    return params


def validate_endure_readback(
    order_id: str,
    stage: dict[str, Any],
    readiness: object,
) -> int:
    error = endure_delivery._readiness_response_error(  # noqa: SLF001
        readiness, order_id, stage
    )
    _require(error is None, "endure_readback_mismatch")
    calendar = readiness["calendar_verification"]
    return calendar["expectedCount"]


def verify_live_purchase(
    *,
    order_id: str,
    stripe_secret: str,
    cron_secret: str,
    delivery_secret: str,
    expected_pipeline_sha: str,
    expected_endure_sha: str,
    transport: ProductionTransport,
) -> dict[str, Any]:
    _require(
        ORDER_PATTERN.fullmatch(order_id) is not None, "order_id_not_live_checkout"
    )
    _require(LIVE_KEY_PATTERN.match(stripe_secret) is not None, "stripe_key_not_live")
    _require(
        SHA1_PATTERN.fullmatch(expected_pipeline_sha) is not None,
        "pipeline_sha_invalid",
    )
    _require(
        SHA1_PATTERN.fullmatch(expected_endure_sha) is not None, "endure_sha_invalid"
    )

    health = transport.get_json("pipeline_health", f"{PIPELINE_URL}/health")
    validate_health(health, expected_pipeline_sha=expected_pipeline_sha)
    version = transport.get_json("endure_version", f"{ENDURE_URL}/api/version")
    validate_endure_version(version, expected_endure_sha=expected_endure_sha)
    session = transport.stripe_session(order_id, stripe_secret)
    recipient_digest = validate_stripe_receipt(order_id, session)
    state = transport.get_json(
        "pipeline_status",
        f"{PIPELINE_URL}/api/fulfillment/{order_id}/status",
        headers={"X-Cron-Secret": cron_secret},
    )
    stage, source_calendar_count = validate_pipeline_receipt(
        order_id, state, recipient_email_sha256=recipient_digest
    )
    readiness = transport.get_json(
        "endure_readiness",
        f"{ENDURE_URL}/api/delivery/purchased-plan",
        headers={"X-Delivery-Secret": delivery_secret},
        params=_readiness_params(order_id, stage),
    )
    calendar_count = validate_endure_readback(order_id, stage, readiness)
    _require(calendar_count == source_calendar_count, "cross_system_calendar_mismatch")

    return {
        "schema": "endure_live_purchase_receipt/v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "single_order_receipt_only",
        "rollout_authorized": False,
        "references": {
            "order_sha256": _digest(order_id),
            "athlete_sha256": _digest(stage["athlete_id"]),
            "plan_sha256": _digest(stage["plan_id"]),
            "block_sha256": _digest(stage["block_id"]),
        },
        "deployments": {
            "pipeline_sha": expected_pipeline_sha,
            "endure_sha": expected_endure_sha,
        },
        "source_status": state["status"],
        "release": stage["release"],
        "calendar_count": calendar_count,
        "checks": {
            "production_default_remains_trainingpeaks": True,
            "live_stripe_payment_complete": True,
            "stripe_buyer_matches_endure_recipient": True,
            "sealed_release_authorized": True,
            "resend_attempt_accepted": True,
            "endure_calendar_readback_exact": True,
        },
    }


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    parent = path.expanduser().resolve().parent
    _require(parent.is_dir(), "receipt_parent_missing")
    previous_umask = os.umask(0o077)
    temporary: Path | None = None
    try:
        handle, name = tempfile.mkstemp(prefix=".endure-receipt-", dir=parent)
        temporary = Path(name)
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(receipt, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path.expanduser().resolve())
        temporary = None
    except OSError:
        _fail("receipt_write_failed")
    finally:
        os.umask(previous_umask)
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def main() -> int:
    try:
        order_id = _required_env("ENDURE_PILOT_ORDER_ID")
        stripe_secret = _required_env("STRIPE_SECRET_KEY")
        cron_secret = _required_env("CRON_SECRET")
        delivery_secret = _required_env("ENDURE_DELIVERY_SECRET")
        expected_pipeline_sha = _required_env("EXPECTED_PIPELINE_SHA")
        expected_endure_sha = _required_env("EXPECTED_ENDURE_SHA")
        output_path = Path(_required_env("ENDURE_PILOT_RECEIPT_PATH"))
        receipt = verify_live_purchase(
            order_id=order_id,
            stripe_secret=stripe_secret,
            cron_secret=cron_secret,
            delivery_secret=delivery_secret,
            expected_pipeline_sha=expected_pipeline_sha,
            expected_endure_sha=expected_endure_sha,
            transport=ProductionTransport(),
        )
        _write_receipt(output_path, receipt)
    except VerificationFailure as exc:
        print(
            json.dumps({"ok": False, "error": exc.code}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    except Exception:
        print(
            json.dumps(
                {"ok": False, "error": "unexpected_verifier_error"}, sort_keys=True
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "receipt": "written",
                "rollout_authorized": False,
                "scope": "single_order_receipt_only",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
