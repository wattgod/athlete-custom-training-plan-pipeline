#!/usr/bin/env python3
"""Run the Phase 4 read-only TrainingPeaks canary boundary.

Fixture mode is an offline self-test of the production capability, replay-record,
worker-service, and validation plumbing. Live mode deliberately fails closed until
the browser/session transport is implemented and the Phase 4 live gate is opened.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from delivery.trainingpeaks.worker_service import (  # noqa: E402
    CannedProbeTransport,
    SERVER_PROBE_AUDIENCE,
    SERVER_PROBE_KID,
    authoritative_probe_execution_root,
    build_server_read_only_worker,
)
from webhook.fulfillment_state import external_state_projection  # noqa: E402


FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "athlete_m" / "worker_probes.json"
LIVE_PENDING_ERROR = "live transport not implemented — Phase 4 live gate pending"
IDENTITY_OUTCOMES = {
    "bound", "multiple-candidates", "not-coached", "not-found", "unresolved",
}
INSPECTION_FIELDS = {
    "account_found", "coached", "tp_athlete_id", "age", "ftp_watts",
    "ftp_date", "lthr_bpm", "lthr_date", "expires_at",
    "workouts_since_threshold",
}


class CanaryError(RuntimeError):
    """A safe operator-facing canary configuration or execution error."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_out(now: datetime) -> Path:
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "reports" / "canary" / f"{stamp}.json"


def _identity_from_env(environ: Mapping[str, str]) -> dict[str, str]:
    email = str(environ.get("TP_CANARY_EMAIL") or "").strip()
    athlete_id = str(environ.get("TP_CANARY_ATHLETE_ID") or "").strip()
    if athlete_id:
        return {"tp_athlete_id": athlete_id}
    if email:
        return {"email": email}
    raise CanaryError(
        "TP_CANARY_EMAIL or TP_CANARY_ATHLETE_ID is required for the canary identity"
    )


def _transport_for(
    name: str, fixture_path: Path, identity: Mapping[str, str],
) -> CannedProbeTransport:
    if name == "live":
        # PHASE 4 LIVE TRANSPORT INTEGRATION POINT: replace only this refusal
        # with the read-only browser/session transport once that implementation
        # has passed its separately witnessed live gate.
        raise CanaryError(LIVE_PENDING_ERROR)
    fixture_tp_id = identity.get("tp_athlete_id") or "fixture-athlete-m"
    return CannedProbeTransport.from_path(
        fixture_path, tp_athlete_id=str(fixture_tp_id))


def _assertion(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _is_optional_int(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def _valid_identity_shape(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    outcome = result.get("outcome")
    candidates = result.get("candidates")
    if outcome not in IDENTITY_OUTCOMES or not isinstance(candidates, list):
        return False
    return outcome != "bound" or bool(str(result.get("tp_athlete_id") or "").strip())


def _valid_inspection_shape(result: Any) -> bool:
    if not isinstance(result, dict) or not INSPECTION_FIELDS.issubset(result):
        return False
    if any(not isinstance(result.get(key), bool) for key in ("account_found", "coached")):
        return False
    if not str(result.get("tp_athlete_id") or "").strip():
        return False
    if not all(_is_optional_int(result.get(key)) for key in ("age", "ftp_watts", "lthr_bpm")):
        return False
    if (not isinstance(result.get("workouts_since_threshold"), int)
            or isinstance(result.get("workouts_since_threshold"), bool)):
        return False
    return all(
        result.get(key) is None or isinstance(result.get(key), str)
        for key in ("ftp_date", "lthr_date", "expires_at")
    )


def _valid_hr_lthr_structure(result: Any) -> bool:
    return bool(
        isinstance(result, dict)
        and {"ftp_watts", "ftp_date", "lthr_bpm", "lthr_date"}.issubset(result)
        and _is_optional_int(result.get("ftp_watts"))
        and _is_optional_int(result.get("lthr_bpm"))
        and (result.get("ftp_date") is None or isinstance(result.get("ftp_date"), str))
        and (result.get("lthr_date") is None or isinstance(result.get("lthr_date"), str))
    )


def _durable_record_actions(order_id: str) -> tuple[set[str], bool]:
    order_root = authoritative_probe_execution_root() / order_id
    actions: set[str] = set()
    valid = True
    records = sorted(order_root.glob("*.json")) if order_root.is_dir() else []
    for path in records:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            valid = False
            continue
        action = (record.get("capability_context") or {}).get("action")
        if record.get("status") != "succeeded" or action not in {"probe", "inspect"}:
            valid = False
        if isinstance(action, str):
            actions.add(action)
    return actions, valid and len(records) == 2


def _scrub_secret_values(value: Any, secrets: set[str]) -> Any:
    """Remove configured identity values before the shared external projection."""
    if isinstance(value, dict):
        return {key: _scrub_secret_values(child, secrets) for key, child in value.items()}
    if isinstance(value, list):
        return [_scrub_secret_values(child, secrets) for child in value]
    if isinstance(value, str):
        scrubbed = value
        for secret in secrets:
            if secret:
                scrubbed = scrubbed.replace(secret, "[REDACTED]")
        return scrubbed
    return value


def _write_artifact(path: Path, artifact: Mapping[str, Any], secrets: set[str]) -> None:
    projected = external_state_projection(_scrub_secret_values(dict(artifact), secrets))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(projected, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def run_canary(
    *, transport_name: str, fixture_path: Path, environ: Mapping[str, str],
    now: datetime,
) -> dict[str, Any]:
    """Execute one zero-write canary and return artifact-safe assertion metadata."""
    assertions: list[dict[str, Any]] = []
    identity = _identity_from_env(environ)
    transport = _transport_for(transport_name, fixture_path, identity)
    codec, worker = build_server_read_only_worker(transport)

    now_epoch = int(now.timestamp())
    order_id = "canary_" + uuid.uuid4().hex
    probe_jti = "probe-" + uuid.uuid4().hex
    locator, locator_value = next(iter(identity.items()))
    probe_claims = {
        "order_id": order_id,
        "subject": {"kind": "identity_query", locator: locator_value},
        "action": "probe", "audience": SERVER_PROBE_AUDIENCE,
        "iat": now_epoch - 1, "exp": now_epoch + 300, "jti": probe_jti,
    }
    probe_token = codec.issue(probe_claims, kid=SERVER_PROBE_KID)
    identity_result = worker.probe_athlete(identity, probe_token, now=now_epoch)
    assertions.append(_assertion(
        "identity_response_shape", _valid_identity_shape(identity_result),
        "probe response has a supported D2 identity outcome and candidate shape",
    ))
    assertions.append(_assertion(
        "identity_outcome_present",
        isinstance(identity_result, dict) and identity_result.get("outcome") in IDENTITY_OUTCOMES,
        "probe response contains a recognized identity outcome",
    ))

    inspection: dict[str, Any] = {}
    bound_tp_id = str(identity_result.get("tp_athlete_id") or "")
    if identity_result.get("outcome") == "bound" and bound_tp_id:
        inspect_jti = "inspect-" + uuid.uuid4().hex
        inspect_claims = {
            "order_id": order_id,
            "subject": {"kind": "identity_query", "tp_athlete_id": bound_tp_id},
            "action": "inspect", "audience": SERVER_PROBE_AUDIENCE,
            "iat": now_epoch - 1, "exp": now_epoch + 300, "jti": inspect_jti,
        }
        inspect_token = codec.issue(inspect_claims, kid=SERVER_PROBE_KID)
        inspection = worker.inspect_account(bound_tp_id, inspect_token, now=now_epoch)

    assertions.append(_assertion(
        "inspection_response_shape", _valid_inspection_shape(inspection),
        "inspection contains every typed field consumed by the D2 review surface",
    ))
    assertions.append(_assertion(
        "hr_lthr_threshold_structure", _valid_hr_lthr_structure(inspection),
        "inspection exposes nullable FTP plus HR/LTHR value-and-date fields",
    ))

    actions, records_valid = _durable_record_actions(order_id)
    assertions.append(_assertion(
        "durable_succeeded_probe_records",
        records_valid and actions == {"probe", "inspect"},
        "the authoritative replay root contains succeeded probe and inspect records",
    ))
    expected_calls = ["probe", "inspect"]
    actual_calls = [str(call[0]) for call in transport.calls]
    assertions.append(_assertion(
        "read_only_boundary", actual_calls == expected_calls,
        "transport received only probe and inspect operations; no mutation path is imported",
    ))

    passed = all(item["passed"] for item in assertions)
    return {
        "artifact_type": "trainingpeaks_canary_probe/v1",
        "generated_at": _timestamp(now),
        "label": str(environ.get("TP_CANARY_LABEL") or "cheesehead"),
        "transport": transport_name,
        "status": "passed" if passed else "failed",
        "assertions": assertions,
    }


def _failed_artifact(
    *, now: datetime, transport_name: str, label: str, message: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "trainingpeaks_canary_probe/v1",
        "generated_at": _timestamp(now),
        "label": label,
        "transport": transport_name,
        "status": "failed",
        "assertions": [
            _assertion("canary_execution", False, message),
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--out", type=Path, help="JSON artifact path")
    return parser


def main(argv: list[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if environ is None else environ
    now = _utc_now()
    out = args.out or _default_out(now)
    secrets = {
        str(env.get("TP_CANARY_EMAIL") or ""),
        str(env.get("TP_CANARY_ATHLETE_ID") or ""),
        str(env.get("GG_WORKER_CAPABILITY_SECRET") or ""),
    }
    try:
        # The alternate mapping keeps the CLI unit-testable while preserving
        # the production constructor's environment-only trust configuration.
        if environ is None:
            artifact = run_canary(
                transport_name=args.transport, fixture_path=args.fixture,
                environ=env, now=now,
            )
        else:
            with patch.dict(os.environ, dict(env), clear=False):
                artifact = run_canary(
                    transport_name=args.transport, fixture_path=args.fixture,
                    environ=env, now=now,
                )
    except Exception as exc:  # The CLI must always leave a safe failure artifact.
        safe_message = (
            str(exc) if isinstance(exc, CanaryError)
            else f"canary execution failed closed ({type(exc).__name__})"
        )
        artifact = _failed_artifact(
            now=now, transport_name=args.transport,
            label=str(env.get("TP_CANARY_LABEL") or "cheesehead"),
            message=safe_message,
        )
    _write_artifact(out, artifact, secrets)
    print(f"Canary {artifact['status']}: {out}")
    if artifact["status"] != "passed":
        failed = next(
            (item for item in artifact["assertions"] if not item["passed"]),
            artifact["assertions"][0],
        )
        print(failed["detail"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
