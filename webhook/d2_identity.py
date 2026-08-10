"""D2 identity resolution, inspection findings, and state-changing commands."""

from __future__ import annotations

import copy
import re
from datetime import date, datetime, timezone
from typing import Any, Mapping

from delivery.trainingpeaks.worker_service import (
    ProbeExecutionStore,
    VerifiedInspectionEvidence,
    WorkerAuthorizationError,
)

from fulfillment_state import (
    BLOCKED_REVIEW,
    GENERATED,
    FulfillmentStateError,
    _atomic_write,
    _history,
    _refresh_review_catalog,
    _validate_confirmation,
    _validate_derived_value,
    _validate_issue,
    locked_state,
    now_iso,
)


IDENTITY_OUTCOMES = {
    "bound", "multiple-candidates", "not-coached", "not-found", "unresolved",
}
RESOLUTION_CHOICES = {
    "use-tp-value", "update-from-intake", "manually-corrected", "cannot-resolve",
}
THRESHOLD_ITEM_ID = "D2_THRESHOLD_LTHR_STALE_MISMATCH"
DEMOGRAPHIC_ITEM_ID = "D2_DEMOGRAPHIC_AGE_MISMATCH"
DORMANCY_ITEM_ID = "D2_ACCOUNT_DORMANCY"
D2_REGENERATION_RULE = "D2_REGENERATION_REQUIRED"


def _automated(state: Mapping[str, Any]) -> bool:
    return state.get("delivery_platform") in {"trainingpeaks", "endure"}


def _safe_int(value: Any, *, field: str, allow_none: bool = True) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise FulfillmentStateError(f"D2 {field} must be an integer")
    return value


def _iso_date(value: Any, *, field: str, allow_none: bool = True) -> str | None:
    if value in {None, ""} and allow_none:
        return None
    if not isinstance(value, str):
        raise FulfillmentStateError(f"D2 {field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise FulfillmentStateError(f"D2 {field} must be an ISO date") from exc


def _set_defaults(state: dict[str, Any]) -> None:
    state.setdefault("d2_active", False)
    state.setdefault("platform_identity", None)
    state.setdefault("identity_resolution", {
        "outcome": "unresolved", "candidates": [], "at": None,
    })
    state.setdefault("account_inspection", None)
    state.setdefault("d2_resolutions", {})
    state.setdefault("d2_pending_requirements", {})
    state.setdefault("d2_apply_operations", {})
    state.setdefault("canonical_input_overrides", {})
    state.setdefault("d2_context", {})
    state.setdefault("regeneration_request", None)


def validate_d2_state(state: dict[str, Any]) -> None:
    """Validate the optional D2 extension embedded in schema-v2 state."""
    _set_defaults(state)
    if not isinstance(state.get("d2_active"), bool):
        raise FulfillmentStateError("d2_active must be boolean")
    identity = state["identity_resolution"]
    if not isinstance(identity, dict) or identity.get("outcome") not in IDENTITY_OUTCOMES:
        raise FulfillmentStateError("invalid D2 identity outcome")
    if not isinstance(identity.get("candidates", []), list):
        raise FulfillmentStateError("D2 candidates must be a list")
    if any(
        not isinstance(candidate, dict)
        or not str(candidate.get("tp_athlete_id") or "").strip()
        for candidate in identity.get("candidates", [])
    ):
        raise FulfillmentStateError("D2 candidate identities are invalid")
    binding = state.get("platform_identity")
    if binding is not None and (
        not isinstance(binding, dict)
        or not str(binding.get("tp_athlete_id") or "").strip()
        or binding.get("order_id") != state.get("order_id")
    ):
        raise FulfillmentStateError("invalid order-scoped platform identity")
    for key in (
        "d2_resolutions", "d2_pending_requirements", "d2_apply_operations",
        "canonical_input_overrides", "d2_context",
    ):
        if not isinstance(state.get(key), dict):
            raise FulfillmentStateError(f"{key} must be an object")
    inspection = state.get("account_inspection")
    if inspection is not None:
        required = {
            "account_found", "coached", "tp_athlete_id", "age", "ftp_watts",
            "ftp_date", "lthr_bpm", "lthr_date", "expires_at",
            "workouts_since_threshold", "observed_at", "capability_jti",
        }
        if not isinstance(inspection, dict) or set(inspection) != required:
            raise FulfillmentStateError("D2 account inspection shape is invalid")
        if any(not isinstance(inspection.get(key), bool)
               for key in ("account_found", "coached")):
            raise FulfillmentStateError("D2 account inspection flags are invalid")
    for item_id, resolution in state["d2_resolutions"].items():
        if (not str(item_id).strip() or not isinstance(resolution, dict)
                or resolution.get("choice") not in RESOLUTION_CHOICES
                or not str(resolution.get("actor") or "").strip()
                or not str(resolution.get("at") or "").strip()):
            raise FulfillmentStateError("D2 resolution record is invalid")
        evidence = resolution.get("readback_evidence")
        if evidence is not None:
            required = {
                "record_type", "order_id", "tp_athlete_id", "capability_jti",
                "capability_kid", "request_digest", "observed_at", "metric",
                "field", "value", "unit",
            }
            metric_fields = {
                "lthr": ("lthr_bpm", "bpm"),
                "ftp": ("ftp_watts", "W"),
                "age": ("age", "years"),
            }
            metric = evidence.get("metric") if isinstance(evidence, dict) else None
            expected_field_unit = metric_fields.get(metric)
            try:
                observed = datetime.fromisoformat(
                    str(evidence.get("observed_at") or "").replace("Z", "+00:00")
                ) if isinstance(evidence, dict) else None
            except ValueError:
                observed = None
            if (not isinstance(evidence, dict) or set(evidence) != required
                    or evidence.get("record_type") != "d2_worker_readback/v1"
                    or evidence.get("order_id") != state.get("order_id")
                    or not str(evidence.get("tp_athlete_id") or "").strip()
                    or not str(evidence.get("capability_kid") or "").strip()
                    or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", str(
                        evidence.get("capability_jti") or ""))
                    or not re.fullmatch(r"[0-9a-f]{64}", str(
                        evidence.get("request_digest") or ""))
                    or observed is None or observed.tzinfo is None
                    or expected_field_unit != (
                        evidence.get("field"), evidence.get("unit"))
                    or isinstance(evidence.get("value"), bool)
                    or not isinstance(evidence.get("value"), int)
                    or resolution.get("choice") != "manually-corrected"):
                raise FulfillmentStateError("D2 worker readback evidence is invalid")
            derived_id = f"D2_MANUAL_READBACK_{metric.upper()}"
            derived_matches = [
                item for item in state.get("derived_values", [])
                if item.get("id") == derived_id
            ]
            expected_inputs = {
                "capability_jti": evidence["capability_jti"],
                "capability_kid": evidence["capability_kid"],
                "request_digest": evidence["request_digest"],
                "tp_athlete_id": evidence["tp_athlete_id"],
            }
            if (len(derived_matches) != 1
                    or derived_matches[0].get("field") != f"d2.manual_readback.{metric}"
                    or derived_matches[0].get("class") != "externally_observed"
                    or derived_matches[0].get("sensitivity") != "sensitive"
                    or derived_matches[0].get("at") != evidence["observed_at"]
                    or derived_matches[0].get("value") != evidence["value"]
                    or derived_matches[0].get("inputs") != expected_inputs):
                raise FulfillmentStateError(
                    "D2 worker readback evidence is not registry-consistent")
    for item_id, requirement in state["d2_pending_requirements"].items():
        if (not str(item_id).strip() or not isinstance(requirement, dict)
                or requirement.get("kind") != "worker-readback"
                or not str(requirement.get("metric") or "").strip()
                or "expected_value" not in requirement):
            raise FulfillmentStateError("D2 pending requirement is invalid")
    for logical_key, operation in state["d2_apply_operations"].items():
        if (not str(logical_key).strip() or not isinstance(operation, dict)
                or set(operation) != {"kind", "payload"}
                or operation.get("kind") not in {"threshold_update", "zone_update"}
                or not isinstance(operation.get("payload"), dict)):
            raise FulfillmentStateError("D2 apply operation is invalid")
    if set(state["canonical_input_overrides"]) - {"hr_threshold", "ftp", "age", "weight"}:
        raise FulfillmentStateError("D2 canonical input override is invalid")
    regeneration = state.get("regeneration_request")
    if regeneration is not None and (
        not isinstance(regeneration, dict)
        or set(regeneration) != {"reason", "requested_at", "prior_revision"}
        or not str(regeneration.get("reason") or "").strip()
        or not str(regeneration.get("requested_at") or "").strip()
        or isinstance(regeneration.get("prior_revision"), bool)
        or not isinstance(regeneration.get("prior_revision"), int)
        or regeneration["prior_revision"] < 1
    ):
        raise FulfillmentStateError("D2 regeneration request is invalid")


def _replace_source(state: dict[str, Any], collection: str, values: list[dict[str, Any]]) -> None:
    state[collection] = sorted(
        [item for item in state.get(collection, []) if item.get("source") != "d2"]
        + values,
        key=lambda item: item["id"],
    )


def _d2_issue(rule_id: str, message: str, value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_issue({
        "id": rule_id,
        "source": "d2",
        "severity": "CRITICAL",
        "message": message,
        "review_value": dict(value),
        "basis": "D2 worker identity/account inspection",
        "sensitivity": "internal",
    })


def _begin_regeneration(state: dict[str, Any], *, reason: str) -> None:
    """Revoke a sealed revision before a D2 command changes reviewed truth."""
    if not state.get("model_seal") and not state.get("release_manifest"):
        return
    prior_revision = state["generation_revision"]
    state["generation_revision"] = prior_revision + 1
    state["status"] = BLOCKED_REVIEW
    state["approval"] = None
    state["waiver"] = None
    state["application"] = None
    state["confirmation"] = None
    state["model_seal"] = None
    state["release_manifest_digest"] = None
    state["release_manifest"] = None
    state["release_artifact_count"] = None
    state["seal_version"] = None
    state["regeneration_request"] = {
        "reason": reason, "requested_at": now_iso(),
        "prior_revision": prior_revision,
    }
    existing = [
        issue for issue in state.get("blocking_issues", [])
        if issue.get("id") != D2_REGENERATION_RULE
    ]
    existing.append(_d2_issue(
        D2_REGENERATION_RULE,
        "A D2 command changed sealed inputs; regeneration must finish before review.",
        {"regeneration_required": True, "reason": reason},
    ))
    state["blocking_issues"] = sorted(existing, key=lambda item: item["id"])
    _history(
        state, "D2_REGENERATION_REQUESTED", reason=reason,
        prior_revision=prior_revision,
    )


def record_identity_result(
    path, expected_revision: int, result: Mapping[str, Any], *,
    capability_jti: str, actor: str = "worker",
) -> dict[str, Any]:
    """Persist one probe outcome and an order-scoped binding when unambiguous."""
    if not isinstance(result, Mapping) or result.get("outcome") not in IDENTITY_OUTCOMES:
        raise FulfillmentStateError("worker identity result has an invalid outcome")
    outcome = str(result["outcome"])
    candidates = copy.deepcopy(result.get("candidates") or [])
    if not isinstance(candidates, list) or any(not isinstance(item, dict) for item in candidates):
        raise FulfillmentStateError("worker identity candidates are invalid")
    tp_id = str(result.get("tp_athlete_id") or "").strip()
    if outcome == "bound" and not tp_id:
        raise FulfillmentStateError("bound identity requires tp_athlete_id")
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        validate_d2_state(state)
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        _begin_regeneration(state, reason="platform identity changed")
        state["d2_active"] = True
        state["identity_resolution"] = {
            "outcome": outcome,
            "candidates": candidates,
            "at": now_iso(),
            "capability_jti": str(capability_jti),
            "actor": str(actor),
        }
        state["platform_identity"] = (
            {
                "platform": "trainingpeaks", "tp_athlete_id": tp_id,
                "order_id": state["order_id"], "bound_at": now_iso(),
                "binding_evidence": {"capability_jti": str(capability_jti)},
            }
            if outcome == "bound" else None
        )
        d2_issues = []
        if _automated(state) and outcome != "bound":
            rule = (
                "ATHLETE_UNLINKED" if outcome == "not-coached" else
                "ATHLETE_NO_ACCOUNT" if outcome == "not-found" else
                "ATHLETE_IDENTITY_UNRESOLVED"
            )
            d2_issues.append(_d2_issue(
                rule,
                "Automated delivery requires a confirmed platform account binding.",
                {"identity_outcome": outcome, "candidate_count": len(candidates)},
            ))
        preserved = [
            issue for issue in state["blocking_issues"]
            if issue.get("source") != "d2" or issue.get("id") == D2_REGENERATION_RULE
        ]
        state["blocking_issues"] = sorted(preserved + d2_issues, key=lambda item: item["id"])
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _refresh_review_catalog(state)
        _history(
            state, "D2_IDENTITY_RECORDED", outcome=outcome,
            capability_jti=str(capability_jti), actor=str(actor),
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def select_identity_candidate(
    path, expected_revision: int, tp_athlete_id: str, *, actor: str,
) -> dict[str, Any]:
    """Coach command selecting exactly one candidate from the probed set."""
    selected = str(tp_athlete_id or "").strip()
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        validate_d2_state(state)
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if state["identity_resolution"].get("outcome") != "multiple-candidates":
            raise FulfillmentStateError("identity selection requires multiple candidates")
        candidates = state["identity_resolution"].get("candidates") or []
        matches = [item for item in candidates if item.get("tp_athlete_id") == selected]
        if len(matches) != 1:
            raise FulfillmentStateError("selected identity is not an exact candidate")
        _begin_regeneration(state, reason="coach selected platform identity")
        state["d2_active"] = True
        state["identity_resolution"].update({
            "outcome": "bound", "selected_at": now_iso(), "selected_by": str(actor),
        })
        state["platform_identity"] = {
            "platform": "trainingpeaks", "tp_athlete_id": selected,
            "order_id": state["order_id"], "bound_at": now_iso(),
            "binding_evidence": {"actor": str(actor), "selection": "candidate"},
        }
        state["blocking_issues"] = [
            issue for issue in state["blocking_issues"]
            if issue.get("id") != "ATHLETE_IDENTITY_UNRESOLVED"
        ]
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _refresh_review_catalog(state)
        _history(state, "D2_IDENTITY_SELECTED", actor=str(actor))
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def _derived(
    record_id: str, field: str, value: Any, *, basis: str,
    inputs: Mapping[str, Any], at: str, revision: int,
) -> dict[str, Any]:
    return _validate_derived_value({
        "id": record_id,
        "field": field,
        "class": "externally_observed",
        "basis": basis,
        "inputs": dict(inputs),
        "sensitivity": "sensitive",
        "at": at,
        "value": value,
        "revision": revision,
    })


def record_account_inspection(
    path, expected_revision: int, inspection: Mapping[str, Any], *,
    intake_age: int | None, intake_thresholds: Mapping[str, Any],
    control_metric: str, canonical_control_value: int | None,
    capability_jti: str, observed_at: str | None = None,
) -> dict[str, Any]:
    """Persist sensitive inspection facts and materialize typed D2 findings."""
    if not isinstance(inspection, Mapping):
        raise FulfillmentStateError("worker inspection must be an object")
    required_bool = {"account_found", "coached"}
    if any(not isinstance(inspection.get(key), bool) for key in required_bool):
        raise FulfillmentStateError("worker inspection account flags are invalid")
    account_age = _safe_int(inspection.get("age"), field="age")
    ftp = _safe_int(inspection.get("ftp_watts"), field="ftp_watts")
    lthr = _safe_int(inspection.get("lthr_bpm"), field="lthr_bpm")
    workouts = _safe_int(
        inspection.get("workouts_since_threshold"),
        field="workouts_since_threshold", allow_none=False,
    )
    ftp_date = _iso_date(inspection.get("ftp_date"), field="ftp_date")
    lthr_date = _iso_date(inspection.get("lthr_date"), field="lthr_date")
    expires = _iso_date(inspection.get("expires_at"), field="expires_at")
    at = observed_at or now_iso()
    try:
        observed_date = datetime.fromisoformat(at.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise FulfillmentStateError("inspection observed_at is invalid") from exc
    normalized = {
        "account_found": inspection["account_found"],
        "coached": inspection["coached"],
        "tp_athlete_id": str(inspection.get("tp_athlete_id") or ""),
        "age": account_age,
        "ftp_watts": ftp,
        "ftp_date": ftp_date,
        "lthr_bpm": lthr,
        "lthr_date": lthr_date,
        "expires_at": expires,
        "workouts_since_threshold": workouts,
        "observed_at": at,
        "capability_jti": str(capability_jti),
    }
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        validate_d2_state(state)
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        binding = state.get("platform_identity") or {}
        if _automated(state) and not binding.get("tp_athlete_id"):
            raise FulfillmentStateError("account inspection requires a bound identity")
        if (normalized["tp_athlete_id"]
                and normalized["tp_athlete_id"] != binding.get("tp_athlete_id")):
            raise FulfillmentStateError("inspection identity does not match binding")
        _begin_regeneration(state, reason="account inspection changed reviewed facts")
        state["d2_active"] = True
        revision = state["generation_revision"]
        state["account_inspection"] = normalized
        state["d2_context"] = {
            "control_metric": str(control_metric),
            "canonical_control_value": canonical_control_value,
            "intake_age": intake_age,
            "intake_thresholds": copy.deepcopy(dict(intake_thresholds)),
        }
        d2_derived = [
            _derived("D2_ACCOUNT_AGE", "d2.account.age", account_age,
                     basis="TrainingPeaks account inspection", inputs={"capability_jti": capability_jti}, at=at, revision=revision),
            _derived("D2_ACCOUNT_FTP", "d2.account.ftp_watts", ftp,
                     basis="TrainingPeaks threshold inspection", inputs={"threshold_date": ftp_date}, at=at, revision=revision),
            _derived("D2_ACCOUNT_LTHR", "d2.account.lthr_bpm", lthr,
                     basis="TrainingPeaks threshold inspection", inputs={"threshold_date": lthr_date}, at=at, revision=revision),
            _derived("D2_ACCOUNT_EXPIRY", "d2.account.expires_at", expires,
                     basis="TrainingPeaks account inspection", inputs={"capability_jti": capability_jti}, at=at, revision=revision),
            _derived("D2_ACCOUNT_WORKOUT_COUNT", "d2.account.workouts_since_threshold", workouts,
                     basis="TrainingPeaks account inspection", inputs={"threshold_date": lthr_date}, at=at, revision=revision),
        ]
        state["derived_values"] = sorted(
            [item for item in state["derived_values"] if not item["id"].startswith("D2_")]
            + d2_derived,
            key=lambda item: item["id"],
        )

        required: list[dict[str, Any]] = []
        soft: list[dict[str, Any]] = []
        if control_metric == "hr" and lthr is not None:
            threshold_age_days = (
                (observed_date - date.fromisoformat(lthr_date)).days if lthr_date else None
            )
            if canonical_control_value != lthr or (threshold_age_days or 0) > 180:
                required.append(_validate_confirmation({
                    "id": THRESHOLD_ITEM_ID,
                    "source": "d2",
                    "message": "TrainingPeaks LTHR is stale or differs from the plan's HR anchor.",
                    "review_value": {
                        "metric": "lthr", "control_metric": "hr",
                        "account_value": lthr, "plan_value": canonical_control_value,
                        "unit": "bpm", "account_value_date": lthr_date,
                        "stale": bool((threshold_age_days or 0) > 180),
                    },
                    "display_unit": "bpm",
                    "basis": "sealed plan control metric compared with account inspection",
                    "sensitivity": "sensitive",
                    "resolution_choices": sorted(RESOLUTION_CHOICES),
                }))
        if account_age is not None and intake_age is not None and account_age != intake_age:
            required.append(_validate_confirmation({
                "id": DEMOGRAPHIC_ITEM_ID,
                "source": "d2",
                "message": "TrainingPeaks account age differs from the intake age.",
                "review_value": {
                    "field": "age", "account_value": account_age,
                    "intake_value": intake_age,
                },
                "display_unit": "years",
                "basis": "account inspection compared with athlete intake",
                "sensitivity": "sensitive",
                "resolution_choices": [
                    "cannot-resolve", "manually-corrected", "use-tp-value",
                ],
            }))
        dormant = workouts == 0 and bool(expires and date.fromisoformat(expires) < observed_date)
        if dormant:
            soft.append(_validate_confirmation({
                "id": DORMANCY_ITEM_ID,
                "source": "d2",
                "message": "The inspected TrainingPeaks account appears dormant.",
                "review_value": {
                    "expires_at": expires, "workouts_since_threshold": workouts,
                    "dormant": True,
                },
                "basis": "account expiry and workout history inspection",
                "sensitivity": "sensitive",
            }))
        _replace_source(state, "required_confirmations", required)
        if control_metric == "hr" and lthr is not None:
            # The inspected LTHR mismatch is the more specific D2 decision.
            # Keeping the transitional no-anchor confirmation as well would
            # ask the coach to resolve the same anchor twice.
            state["required_confirmations"] = [
                item for item in state["required_confirmations"]
                if item.get("id") != "POWER_BASIS_NONE_CONFIRM"
            ]
        _replace_source(state, "soft_confirmations", soft)
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _refresh_review_catalog(state)
        _history(
            state, "D2_ACCOUNT_INSPECTED", capability_jti=str(capability_jti),
            required_item_ids=[item["id"] for item in required],
            soft_item_ids=[item["id"] for item in soft],
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def _source_confirmation(state: Mapping[str, Any], item_id: str) -> dict[str, Any]:
    matches = [
        item for item in state.get("required_confirmations", [])
        if item.get("source") == "d2" and item.get("id") == item_id
    ]
    if len(matches) != 1:
        raise FulfillmentStateError("D2 resolution item is not current")
    return copy.deepcopy(matches[0])


def _mark_resolution_on_source(state: dict[str, Any], item_id: str, choice: str) -> None:
    for item in state["required_confirmations"]:
        if item.get("source") == "d2" and item.get("id") == item_id:
            item["resolved_resolution"] = choice


def _clear_resolution_on_source(state: dict[str, Any], item_id: str) -> None:
    for item in state["required_confirmations"]:
        if item.get("source") == "d2" and item.get("id") == item_id:
            item.pop("resolved_resolution", None)


def _retract_resolution_effects(
    state: dict[str, Any], item_id: str, metric: str,
) -> None:
    """Remove every effect owned by the item's previous resolution."""
    previous = (state.get("d2_resolutions") or {}).get(item_id) or {}
    input_field = {
        "lthr": "hr_threshold", "ftp": "ftp", "age": "age", "weight": "weight",
    }.get(metric)
    if input_field:
        state["canonical_input_overrides"].pop(input_field, None)
    state["d2_apply_operations"].pop(metric, None)
    state["d2_pending_requirements"].pop(item_id, None)
    state["derived_values"] = [
        item for item in state.get("derived_values", [])
        if item.get("id") != f"D2_MANUAL_READBACK_{metric.upper()}"
    ]
    if previous.get("choice") == "use-tp-value" and metric == "lthr":
        restored = previous.get(
            "plan_value_before_resolution",
            (state.get("d2_context", {}).get("intake_thresholds") or {}).get(metric),
        )
        state["d2_context"]["canonical_control_value"] = restored
        for confirmation in state["required_confirmations"]:
            if confirmation.get("id") == item_id:
                confirmation.setdefault("review_value", {})["plan_value"] = restored
    state["blocking_issues"] = [
        issue for issue in state["blocking_issues"]
        if not (
            issue.get("id") == "D2_CANNOT_RESOLVE"
            and (issue.get("review_value") or {}).get("item_id") == item_id
        )
    ]
    state["d2_resolutions"].pop(item_id, None)
    _clear_resolution_on_source(state, item_id)


def resolve_d2_item(
    path, expected_revision: int, item_id: str, choice: str, *, actor: str,
) -> dict[str, Any]:
    """Execute one D2 resolution command; never treats a selector as page-only data."""
    choice = str(choice or "").strip()
    if choice not in RESOLUTION_CHOICES:
        raise FulfillmentStateError("unknown D2 resolution command")
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        validate_d2_state(state)
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        item = _source_confirmation(state, str(item_id))
        if choice not in item.get("resolution_choices", []):
            raise FulfillmentStateError("resolution is not allowed for this D2 item")
        value = item.get("review_value") or {}
        metric = str(value.get("metric") or value.get("field") or "")
        account_value = value.get("account_value")
        context = state["d2_context"]
        previous_choice = (state["d2_resolutions"].get(str(item_id)) or {}).get("choice")

        input_field = {
            "lthr": "hr_threshold", "ftp": "ftp", "age": "age", "weight": "weight",
        }.get(metric)
        intake_value = (context.get("intake_thresholds") or {}).get(metric)
        if choice == "use-tp-value" and (not input_field or account_value is None):
            raise FulfillmentStateError("inspected value cannot become a canonical input")
        if choice == "update-from-intake":
            if metric not in {"lthr", "ftp"}:
                raise FulfillmentStateError(
                    "only threshold/zone findings can emit apply operations")
            if intake_value is None:
                raise FulfillmentStateError(
                    "update-from-intake requires an intake threshold value")
        previous_resolution = state["d2_resolutions"].get(str(item_id)) or {}
        manual_expected = (
            previous_resolution.get(
                "plan_value_before_resolution",
                context.get("canonical_control_value"),
            ) if metric == "lthr"
            else (context.get("intake_age") if metric == "age" else None)
        )
        if choice == "manually-corrected" and manual_expected is None:
            raise FulfillmentStateError(
                "manual correction requires a canonical expected value")

        # Only choices which add/remove plan or apply-contract content revoke
        # the seal. Manual readback and cannot-resolve alter review evidence,
        # not the sealed release bytes.
        if choice in {"use-tp-value", "update-from-intake"} or previous_choice in {
            "use-tp-value", "update-from-intake",
        }:
            _begin_regeneration(
                state, reason=f"D2 resolution {choice} for {item_id}")
        _retract_resolution_effects(state, str(item_id), metric)

        if choice == "use-tp-value":
            plan_value_before = context.get("canonical_control_value")
            state["canonical_input_overrides"][input_field] = account_value
            if metric == "lthr":
                context["canonical_control_value"] = account_value
                for confirmation in state["required_confirmations"]:
                    if confirmation.get("id") == item_id:
                        confirmation.setdefault("review_value", {})[
                            "plan_value"] = account_value
            state["d2_resolutions"][item_id] = {
                "choice": choice, "actor": str(actor), "at": now_iso(),
                "inspected_value": account_value,
                "plan_value_before_resolution": plan_value_before,
                "effect": "canonical-input-override-and-regeneration",
            }
            _mark_resolution_on_source(state, item_id, choice)
        elif choice == "update-from-intake":
            unit = "bpm" if metric == "lthr" else "W"
            state["d2_apply_operations"][metric] = {
                "kind": "threshold_update",
                "payload": {"metric": metric, "after_value": intake_value, "unit": unit},
            }
            state["d2_resolutions"][item_id] = {
                "choice": choice, "actor": str(actor), "at": now_iso(),
                "inspected_before_image": {
                    "metric": metric, "value": account_value, "unit": unit,
                },
                "sealed_plan_value": context.get("canonical_control_value"),
                "intake_value": intake_value,
                "effect": "apply-contract-threshold-update-plan-unchanged",
            }
            _mark_resolution_on_source(state, item_id, choice)
        elif choice == "manually-corrected":
            state["d2_pending_requirements"][item_id] = {
                "kind": "worker-readback", "metric": metric,
                "expected_value": manual_expected, "requested_by": str(actor),
                "requested_at": now_iso(),
            }
            state["d2_resolutions"][item_id] = {
                "choice": choice, "actor": str(actor), "at": now_iso(),
                "effect": "pending-worker-readback",
            }
            # Deliberately not marked resolved until record_manual_readback.
        else:
            state["d2_resolutions"][item_id] = {
                "choice": choice, "actor": str(actor), "at": now_iso(),
                "effect": "non-waivable-block",
            }
            _mark_resolution_on_source(state, item_id, choice)
            state["blocking_issues"] = sorted(
                [issue for issue in state["blocking_issues"]
                 if issue.get("id") != "D2_CANNOT_RESOLVE"]
                + [_d2_issue(
                    "D2_CANNOT_RESOLVE",
                    "A required account inconsistency could not be resolved.",
                    {"item_id": item_id, "resolution": choice},
                )],
                key=lambda issue: issue["id"],
            )
        state["status"] = BLOCKED_REVIEW if state["blocking_issues"] else GENERATED
        _refresh_review_catalog(state)
        _history(
            state, "D2_RESOLUTION_COMMAND", item_id=str(item_id), choice=choice,
            actor=str(actor),
        )
        _atomic_write(state_path, state)
        return copy.deepcopy(state)


def record_manual_readback(
    path, expected_revision: int, item_id: str,
    evidence: VerifiedInspectionEvidence,
) -> dict[str, Any]:
    """Persist readback against the server-selected store under both locks."""
    if not isinstance(evidence, VerifiedInspectionEvidence):
        raise FulfillmentStateError(
            "manual correction requires verified worker inspection evidence")
    replay_store = ProbeExecutionStore.authoritative()
    with locked_state(path) as (state_path, state):
        if state is None:
            raise FulfillmentStateError("missing or malformed fulfillment state")
        validate_d2_state(state)
        if state["generation_revision"] != expected_revision:
            raise FulfillmentStateError("generation revision mismatch")
        if not state.get("model_seal") or not state.get("release_manifest"):
            raise FulfillmentStateError("manual correction readback requires a sealed review")
        pending = state["d2_pending_requirements"].get(str(item_id))
        if not isinstance(pending, dict) or pending.get("kind") != "worker-readback":
            raise FulfillmentStateError("manual correction has no pending readback")
        try:
            with replay_store.locked_inspection_evidence(evidence) as evidence_guard:
                metric = pending["metric"]
                field = {
                    "lthr": "lthr_bpm", "ftp": "ftp_watts", "age": "age",
                }.get(metric)
                binding = state.get("platform_identity") or {}
                if (evidence.order_id != state.get("order_id")
                        or evidence.tp_athlete_id != binding.get("tp_athlete_id")):
                    raise FulfillmentStateError(
                        "worker readback evidence does not match this order binding")
                inspection = evidence.result
                if (inspection.get("tp_athlete_id")
                        not in {None, "", evidence.tp_athlete_id}
                        or not field
                        or inspection.get(field) != pending["expected_value"]):
                    raise FulfillmentStateError(
                        "worker readback does not confirm corrected value")
                unit = (
                    "bpm" if metric == "lthr"
                    else ("W" if metric == "ftp" else "years"))
                record = {
                    "record_type": "d2_worker_readback/v1",
                    "order_id": evidence.order_id,
                    "tp_athlete_id": evidence.tp_athlete_id,
                    "capability_jti": evidence.capability_jti,
                    "capability_kid": evidence.capability_kid,
                    "request_digest": evidence.request_digest,
                    "observed_at": evidence.observed_at,
                    "metric": metric,
                    "field": field,
                    "value": inspection[field],
                    "unit": unit,
                }
                state["d2_resolutions"][str(item_id)].update({
                    "effect": "worker-readback-confirmed",
                    "readback_evidence": record,
                })
                del state["d2_pending_requirements"][str(item_id)]
                derived_id = f"D2_MANUAL_READBACK_{metric.upper()}"
                state["derived_values"] = sorted(
                    [item for item in state["derived_values"]
                     if item.get("id") != derived_id]
                    + [_derived(
                        derived_id, f"d2.manual_readback.{metric}",
                        inspection[field],
                        basis=(
                            "TrainingPeaks worker readback after "
                            "coach-reported correction"),
                        inputs={
                            "capability_jti": evidence.capability_jti,
                            "capability_kid": evidence.capability_kid,
                            "request_digest": evidence.request_digest,
                            "tp_athlete_id": evidence.tp_athlete_id,
                        },
                        at=evidence.observed_at,
                        revision=state["generation_revision"],
                    )],
                    key=lambda item: item["id"],
                )
                _mark_resolution_on_source(
                    state, str(item_id), "manually-corrected")
                _refresh_review_catalog(state)
                _history(
                    state, "D2_MANUAL_READBACK_CONFIRMED",
                    item_id=str(item_id),
                    capability_jti=evidence.capability_jti,
                )
                # Close the old verify/commit gap: re-read under the still-held
                # execution-record lock immediately before the state replace.
                evidence_guard.reverify()
                _atomic_write(state_path, state)
                return copy.deepcopy(state)
        except WorkerAuthorizationError as exc:
            raise FulfillmentStateError(
                f"manual correction evidence origin is unverified: {exc}") from exc


def d2_contract_inputs(state: Mapping[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Return the bound identity, singleton desires, and inspected before-images."""
    binding = state.get("platform_identity") or {}
    tp_id = str(binding.get("tp_athlete_id") or "")
    inspection = state.get("account_inspection") or {}
    singletons: dict[str, Any] = {}
    if inspection.get("lthr_bpm") is not None:
        singletons["lthr"] = {
            "metric": "lthr", "value": inspection["lthr_bpm"], "unit": "bpm",
            "observed_at": inspection.get("observed_at"),
        }
    if inspection.get("ftp_watts") is not None:
        singletons["ftp"] = {
            "metric": "ftp", "value": inspection["ftp_watts"], "unit": "W",
            "observed_at": inspection.get("observed_at"),
        }
    return tp_id, copy.deepcopy(state.get("d2_apply_operations") or {}), {
        "singletons": singletons,
    }


def validate_d2_approval(state: Mapping[str, Any]) -> None:
    """Server-side approval legality for identity and account consistency."""
    if _automated(state):
        binding = state.get("platform_identity") or {}
        if (not str(binding.get("tp_athlete_id") or "").strip()
                or binding.get("order_id") != state.get("order_id")):
            raise FulfillmentStateError("approval requires a bound platform identity")
    if not state.get("d2_active"):
        return
    if state.get("regeneration_request"):
        raise FulfillmentStateError("D2 regeneration is pending")
    if state.get("d2_pending_requirements"):
        raise FulfillmentStateError("D2 worker readback is still required")
    expected_overrides: dict[str, Any] = {}
    expected_operations: dict[str, Any] = {}
    for item in state.get("required_confirmations", []):
        if item.get("source") != "d2":
            continue
        choice = item.get("resolved_resolution")
        if choice not in item.get("resolution_choices", []):
            raise FulfillmentStateError(f"D2 review item is unresolved: {item['id']}")
        if choice == "cannot-resolve":
            raise FulfillmentStateError(f"D2 review item cannot be resolved: {item['id']}")
        value = item.get("review_value") or {}
        metric = str(value.get("metric") or value.get("field") or "")
        resolution = (state.get("d2_resolutions") or {}).get(item["id"]) or {}
        if resolution.get("choice") != choice:
            raise FulfillmentStateError(
                f"D2 resolution record is inconsistent: {item['id']}")
        if choice == "use-tp-value":
            input_field = {
                "lthr": "hr_threshold", "ftp": "ftp", "age": "age", "weight": "weight",
            }.get(metric)
            if not input_field or resolution.get("inspected_value") != value.get("account_value"):
                raise FulfillmentStateError("adopted account value provenance is inconsistent")
            expected_overrides[input_field] = value.get("account_value")
        elif choice == "update-from-intake":
            intake_value = ((state.get("d2_context") or {}).get(
                "intake_thresholds") or {}).get(metric)
            unit = "bpm" if metric == "lthr" else "W"
            expected_operations[metric] = {
                "kind": "threshold_update",
                "payload": {
                    "metric": metric, "after_value": intake_value, "unit": unit,
                },
            }
            if resolution.get("inspected_before_image") != {
                "metric": metric, "value": value.get("account_value"), "unit": unit,
            }:
                raise FulfillmentStateError("threshold before-image is inconsistent")
        elif choice == "manually-corrected":
            readback = resolution.get("readback_evidence") or {}
            expected = (
                (state.get("d2_context") or {}).get("canonical_control_value")
                if metric == "lthr" else
                (state.get("d2_context") or {}).get("intake_age")
                if metric == "age" else None
            )
            if (readback.get("record_type") != "d2_worker_readback/v1"
                    or readback.get("value") != expected
                    or readback.get("order_id") != state.get("order_id")):
                raise FulfillmentStateError("manual correction lacks consistent readback")
    if state.get("canonical_input_overrides") != expected_overrides:
        raise FulfillmentStateError("D2 canonical input effects are inconsistent")
    if state.get("d2_apply_operations") != expected_operations:
        raise FulfillmentStateError("D2 apply-contract effects are inconsistent")
    context = state.get("d2_context") or {}
    inspection = state.get("account_inspection") or {}
    control = context.get("control_metric")
    if control == "hr":
        plan_value = context.get("canonical_control_value")
        account_value = inspection.get("lthr_bpm")
        threshold = next((
            item for item in state.get("required_confirmations", [])
            if item.get("id") == THRESHOLD_ITEM_ID
        ), None)
        if threshold:
            choice = threshold.get("resolved_resolution")
            if choice == "use-tp-value" and plan_value != account_value:
                raise FulfillmentStateError("sealed HR anchor does not match adopted account LTHR")
            if choice == "update-from-intake":
                intake_value = (context.get("intake_thresholds") or {}).get("lthr")
                resolution = (state.get("d2_resolutions") or {}).get(
                    THRESHOLD_ITEM_ID, {})
                if (plan_value != intake_value
                        or resolution.get("sealed_plan_value") != plan_value
                        or resolution.get("intake_value") != intake_value):
                    raise FulfillmentStateError(
                        "sealed HR anchor does not match the intake update target")
            if choice == "manually-corrected":
                evidence = (state.get("d2_resolutions") or {}).get(
                    THRESHOLD_ITEM_ID, {}).get("readback_evidence")
                if not evidence or evidence.get("value") != plan_value:
                    raise FulfillmentStateError("manual correction lacks consistent readback")
