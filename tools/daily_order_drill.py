#!/usr/bin/env python3
"""Send and verify the daily real-path synthetic WooCommerce order drill."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests


EXPECTED_STATUS = "BLOCKED_REVIEW"
EXPECTED_BLOCKERS = ("RACE_UNMATCHED",)
TERMINAL_STATUSES = {"CANCELLED", "CONFIRMED"}


class DrillError(RuntimeError):
    """A safe, operator-facing drill configuration or assertion failure."""


@dataclass(frozen=True)
class DrillConfig:
    webhook_url: str
    webhook_secret: str
    customer_email: str
    cron_secret: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def order_id_for(day: date) -> str:
    return f"drill-{day:%Y%m%d}"


def derive_drill_email(base_email: str) -> str:
    """Return a stable plus-address without exposing it in artifacts."""
    value = str(base_email or "").strip().lower()
    if value.count("@") != 1 or any(char.isspace() for char in value):
        raise DrillError("DRILL_CUSTOMER_EMAIL must be a valid email address")
    local, domain = value.rsplit("@", 1)
    local = local.split("+", 1)[0]
    if not local or "." not in domain:
        raise DrillError("DRILL_CUSTOMER_EMAIL must be a valid email address")
    return f"{local}+drill@{domain}"


def build_payload(day: date, customer_email: str) -> dict[str, Any]:
    """Build the literal Woo order JSON used for one UTC calendar day."""
    race_day = day + timedelta(days=140)
    return {
        "id": order_id_for(day),
        "status": "processing",
        "date_created_gmt": f"{day.isoformat()}T00:00:00Z",
        "currency": "USD",
        "billing": {
            "first_name": "Daily",
            "last_name": "Drill",
            "email": derive_drill_email(customer_email),
            "country": "US",
        },
        "line_items": [{
            "name": "Custom Training Plan - Race Ready",
            "sku": "training-race-ready",
            "quantity": 1,
        }],
        "meta_data": [
            {"key": "intake_complete", "value": True},
            {"key": "delivery_platform", "value": "manual"},
            {"key": "brand", "value": "gravelgod"},
            {"key": "sex", "value": "Female"},
            {"key": "age", "value": 39},
            {"key": "weight_kg", "value": 68.0},
            {"key": "ftp_watts", "value": 225},
            {"key": "power_or_hr", "value": "power"},
            {"key": "devices", "value": "power meter, hr strap"},
            {"key": "years_cycling", "value": "6"},
            {"key": "prior_plan_experience", "value": "3"},
            {"key": "race_name", "value": "Daily Drill Gravel Challenge"},
            {"key": "race_date", "value": race_day.isoformat()},
            {"key": "race_distance_miles", "value": 100},
            {"key": "race_elevation_ft", "value": 6500},
            {"key": "race_terrain", "value": "gravel"},
            {"key": "course_facts_mode", "value": "athlete_facts_only"},
            {"key": "cycling_hours", "value": 9},
            {"key": "strength_hours", "value": 2},
            {"key": "preferred_long_day", "value": "saturday"},
            {"key": "long_ride_days", "value": ["saturday"]},
            {"key": "interval_days", "value": ["tuesday", "thursday"]},
            {"key": "off_days", "value": ["monday"]},
            {"key": "trainer_access", "value": "smart trainer"},
            {"key": "strength_current", "value": "2x/week"},
            {"key": "strength_want", "value": "yes"},
            {"key": "strength_equipment", "value": "full gym"},
            {"key": "experience_level", "value": "intermediate"},
            {"key": "race_goal", "value": "finish"},
            {"key": "sleep_quality", "value": "good"},
            {"key": "stress_level", "value": "moderate"},
            {"key": "injuries", "value": "None"},
            {"key": "athlete_timezone", "value": "America/Denver"},
            {"key": "notes", "value": "Synthetic daily fulfilment drill; no real athlete."},
        ],
    }


def encode_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(
        str(secret).encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _api_base(webhook_url: str) -> str:
    parsed = urlsplit(str(webhook_url or "").strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise DrillError("DRILL_WEBHOOK_URL must be an HTTP(S) endpoint without credentials")
    path = parsed.path.rstrip("/")
    suffix = "/webhook/woocommerce"
    if not path.endswith(suffix):
        raise DrillError("DRILL_WEBHOOK_URL must end with /webhook/woocommerce")
    base_path = path[:-len(suffix)]
    return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", "")).rstrip("/")


def _response_json(response: Any) -> dict[str, Any]:
    getter = getattr(response, "json", None)
    if callable(getter):
        value = getter()
    elif hasattr(response, "get_json"):
        value = response.get_json()
    else:
        value = getter
    if not isinstance(value, dict):
        raise DrillError("production endpoint returned a non-object JSON response")
    return value


def _assertion(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _operator_headers(config: DrillConfig) -> dict[str, str]:
    return {"X-Cron-Secret": config.cron_secret}


def cleanup_previous_order(
    config: DrillConfig, day: date, *, transport: Any,
) -> list[dict[str, Any]]:
    """Cancel yesterday's non-terminal pre-apply drill through operator auth."""
    assertions: list[dict[str, Any]] = []
    previous_id = order_id_for(day - timedelta(days=1))
    base = _api_base(config.webhook_url)
    status_response = transport.get(
        f"{base}/api/order-status/{previous_id}",
        headers=_operator_headers(config), timeout=20)
    if status_response.status_code == 404:
        assertions.append(_assertion(
            "previous_order_cleanup", True,
            "previous drill order is absent; no cancellation was required"))
        return assertions
    if status_response.status_code != 200:
        raise DrillError("previous drill status lookup failed")
    status_data = _response_json(status_response)
    prior_status = status_data.get("fulfillment_status")
    if prior_status in TERMINAL_STATUSES:
        assertions.append(_assertion(
            "previous_order_cleanup", True,
            "previous drill order was already terminal"))
        return assertions
    if not prior_status:
        raise DrillError("previous drill has no authoritative fulfillment state")

    cancel_response = transport.post(
        f"{base}/api/fulfillment/{previous_id}/transition",
        json={
            "to": "CANCELLED",
            "coach": "daily-drill-cleanup",
            "reason": "automatic cleanup of the previous UTC day's synthetic drill",
        },
        headers=_operator_headers(config), timeout=20)
    if cancel_response.status_code != 200:
        raise DrillError("authenticated previous-drill cancellation failed")
    cancel_data = _response_json(cancel_response)
    if cancel_data.get("status") != "CANCELLED":
        raise DrillError("authenticated cancellation did not reach CANCELLED")
    assertions.append(_assertion(
        "previous_order_cancelled",
        True,
        "authenticated cancellation reached CANCELLED"))

    verify_response = transport.get(
        f"{base}/api/order-status/{previous_id}",
        headers=_operator_headers(config), timeout=20)
    verified = (
        verify_response.status_code == 200
        and _response_json(verify_response).get("fulfillment_status") == "CANCELLED"
    )
    if not verified:
        raise DrillError("authoritative status did not persist cancellation")
    assertions.append(_assertion(
        "previous_order_cancellation_verified", True,
        "authoritative order status persisted CANCELLED"))
    return assertions


def send_and_verify_order(
    config: DrillConfig, day: date, *, transport: Any,
    timeout_seconds: int, poll_interval_seconds: float,
    sleep=time.sleep, monotonic=time.monotonic,
) -> list[dict[str, Any]]:
    """Submit today's signed order and prove the human gate remains closed."""
    assertions: list[dict[str, Any]] = []
    payload = build_payload(day, config.customer_email)
    payload_bytes = encode_payload(payload)
    order_id = order_id_for(day)
    base = _api_base(config.webhook_url)
    webhook_response = transport.post(
        config.webhook_url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Signature": sign_payload(
                payload_bytes, config.webhook_secret),
        },
        timeout=30,
    )
    webhook_data = _response_json(webhook_response)
    accepted = (
        webhook_response.status_code == 200
        and webhook_data.get("status") in {"accepted", "success", "duplicate"}
    )
    assertions.append(_assertion(
        "signed_woocommerce_order_accepted", accepted,
        "production WooCommerce intake accepted the signed synthetic order"))
    if not accepted:
        return assertions

    deadline = monotonic() + timeout_seconds
    status_data: dict[str, Any] = {}
    while monotonic() <= deadline:
        response = transport.get(
            f"{base}/api/order-status/{order_id}",
            headers=_operator_headers(config), timeout=20)
        if response.status_code == 200:
            status_data = _response_json(response)
            if status_data.get("job_status") == "failed":
                break
            if status_data.get("generation_complete"):
                break
        sleep(poll_interval_seconds)

    generation_complete = bool(status_data.get("generation_complete"))
    assertions.append(_assertion(
        "generation_completed", generation_complete,
        "the durable generation job completed within the bounded timeout"))
    if not generation_complete:
        return assertions

    actual_status = status_data.get("fulfillment_status")
    actual_blockers = tuple(sorted(status_data.get("blocker_ids") or []))
    assertions.extend([
        _assertion(
            "expected_fulfillment_state", actual_status == EXPECTED_STATUS,
            f"fulfillment state is exactly {EXPECTED_STATUS}"),
        _assertion(
            "expected_blocker_set", actual_blockers == EXPECTED_BLOCKERS,
            "blocker ids exactly match the synthetic unknown-race contract"),
        _assertion(
            "review_bundle_exists",
            status_data.get("review_bundle_exists") is True,
            "the sealed coach review bundle exists for this revision"),
        _assertion(
            "customer_download_not_ready",
            status_data.get("download_ready") is False,
            "customer order status does not advertise a pre-approval download"),
    ])

    download_response = transport.get(
        f"{base}/api/download/{order_id}?artifact=customer_bundle",
        headers=_operator_headers(config), timeout=20)
    assertions.append(_assertion(
        "customer_download_refused_preapproval",
        download_response.status_code == 409,
        "authenticated customer-bundle check returned the required 409"))
    return assertions


def config_from_env(environ: Mapping[str, str]) -> DrillConfig:
    values = {
        key: str(environ.get(key) or "").strip()
        for key in (
            "DRILL_WEBHOOK_URL", "DRILL_WEBHOOK_SECRET",
            "DRILL_CUSTOMER_EMAIL", "DRILL_CRON_SECRET",
        )
    }
    missing = sorted(key for key, value in values.items() if not value)
    if missing:
        raise DrillError("missing required drill configuration: " + ", ".join(missing))
    _api_base(values["DRILL_WEBHOOK_URL"])
    derive_drill_email(values["DRILL_CUSTOMER_EMAIL"])
    return DrillConfig(
        webhook_url=values["DRILL_WEBHOOK_URL"],
        webhook_secret=values["DRILL_WEBHOOK_SECRET"],
        customer_email=values["DRILL_CUSTOMER_EMAIL"],
        cron_secret=values["DRILL_CRON_SECRET"],
    )


def _scrub(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, dict):
        return {str(key): _scrub(child, secrets) for key, child in value.items()}
    if isinstance(value, list):
        return [_scrub(child, secrets) for child in value]
    if isinstance(value, str):
        scrubbed = value
        for secret in secrets:
            if secret:
                scrubbed = scrubbed.replace(secret, "[REDACTED]")
        return scrubbed
    return value


def build_artifact(
    *, day: date, assertions: list[dict[str, Any]], now: datetime,
    secrets: set[str],
) -> dict[str, Any]:
    safe_assertions = _scrub(assertions, secrets)
    passed = sum(item.get("passed") is True for item in safe_assertions)
    return {
        "artifact_type": "daily_order_drill/v1",
        "generated_at": _timestamp(now),
        "drill_date": day.isoformat(),
        "order_ref": hashlib.sha256(order_id_for(day).encode()).hexdigest()[:12],
        "summary": {
            "assertions": len(safe_assertions),
            "passed": passed,
            "failed": len(safe_assertions) - passed,
        },
        "assertions": safe_assertions,
    }


def write_artifact(path: Path, artifact: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cleanup", action="store_true",
        help="cancel yesterday's non-terminal drill before sending today's order")
    parser.add_argument("--date", type=date.fromisoformat, help="UTC drill date")
    parser.add_argument("--timeout", type=int, default=720)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout < 1 or args.poll_interval <= 0:
        build_parser().error("timeout and poll interval must be positive")
    now = _utc_now()
    day = args.date or now.date()
    out = args.out or Path("reports") / "daily-drill" / f"{order_id_for(day)}.json"
    assertions: list[dict[str, Any]] = []
    configured_values = {
        str(os.environ.get(key) or "")
        for key in (
            "DRILL_WEBHOOK_URL", "DRILL_WEBHOOK_SECRET",
            "DRILL_CUSTOMER_EMAIL", "DRILL_CRON_SECRET",
        )
        if os.environ.get(key)
    }
    try:
        config = config_from_env(os.environ)
        configured_values.update({
            derive_drill_email(config.customer_email),
            _api_base(config.webhook_url),
        })
        if args.cleanup:
            assertions.extend(cleanup_previous_order(
                config, day, transport=requests))
        assertions.extend(send_and_verify_order(
            config, day, transport=requests,
            timeout_seconds=args.timeout,
            poll_interval_seconds=args.poll_interval,
        ))
    except (DrillError, requests.RequestException) as exc:
        safe_error = _scrub(str(exc), configured_values)
        assertions.append(_assertion("drill_execution", False, safe_error))

    artifact = build_artifact(
        day=day, assertions=assertions, now=now, secrets=configured_values)
    write_artifact(out, artifact)
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 1 if artifact["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
