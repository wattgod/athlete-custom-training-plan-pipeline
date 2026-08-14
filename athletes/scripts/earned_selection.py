"""Earned Selection E1 scoring, registry, and certification primitives.

E1 is deliberately audit-only: observations are complete, while every
hypothesis gate has effective verdict ``NOT_ENFORCED``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import yaml


SCORER_VERSION = "earned_selection_scorer/v1"
VERSION_VECTOR = {
    "purpose_registry_version": "purpose_registry/v1",
    "gate_registry_version": "quality_gates/v1",
    "scorer_version": SCORER_VERSION,
    "rule_registry_version": "rule_registry/v1",
}
VERDICTS = {"PASS", "FAIL", "NOT_APPLICABLE", "UNAVAILABLE"}
EFFECTIVE_VERDICTS = VERDICTS | {"NOT_ENFORCED"}
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "athletes" / "config"


class EarnedSelectionError(ValueError):
    """A closed E1 artifact, trace, or registry is invalid."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _nonnegative_integer(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _neutral(value: Any, target_type: str) -> Optional[float]:
    number = _finite(value)
    if number is None or number < 0:
        return None
    if target_type == "power_pct_ftp":
        return number
    if target_type in {"pct_lthr", "pct_hrmax", "rpe"}:
        from canonical_training_model import normalize_target_effort
        return normalize_target_effort(target_type, number)
    return None


def prescribed_trace(segments: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Expand the normative §1.2 total 1 Hz prescribed trace."""
    if not isinstance(segments, Sequence) or isinstance(segments, (str, bytes)):
        return {"status": "UNAVAILABLE", "reason": "INVALID_SEGMENTS"}
    trace: list[float] = []
    free_seconds = 0
    has_free = False
    for segment in segments:
        if not isinstance(segment, Mapping):
            return {"status": "UNAVAILABLE", "reason": "INVALID_SEGMENT"}
        seconds = _nonnegative_integer(segment.get("seconds"))
        if seconds is None:
            return {"status": "UNAVAILABLE", "reason": "INVALID_DURATION"}
        kind = str(segment.get("kind") or "").lower()
        target = segment.get("target")
        if not isinstance(target, Mapping):
            return {"status": "UNAVAILABLE", "reason": "INVALID_TARGET"}
        target_type = str(target.get("type") or "")
        if kind in {"free", "freeride", "free_ride"} or target_type == "free":
            if target_type != "free":
                return {"status": "UNAVAILABLE", "reason": "INVALID_FREE_TARGET"}
            has_free = True
            free_seconds += seconds
            continue
        if kind == "intervals":
            repeat = _nonnegative_integer(segment.get("repeat"))
            on_seconds = _nonnegative_integer(segment.get("on_seconds"))
            off_seconds = _nonnegative_integer(segment.get("off_seconds"))
            on = _neutral(target.get("on"), target_type)
            off = _neutral(target.get("off"), target_type)
            if (repeat is None or repeat < 1 or on_seconds is None
                    or off_seconds is None or on is None or off is None
                    or seconds != repeat * (on_seconds + off_seconds)):
                return {"status": "UNAVAILABLE", "reason": "INVALID_INTERVAL"}
            for _ in range(repeat):
                trace.extend([on] * on_seconds)
                trace.extend([off] * off_seconds)
            continue
        if kind in {"ramp", "warmup", "cooldown"}:
            low = _neutral(target.get("low"), target_type)
            high = _neutral(target.get("high"), target_type)
            if low is None or high is None:
                return {"status": "UNAVAILABLE", "reason": "INVALID_RAMP"}
            denominator = max(1, seconds - 1)
            trace.extend(low + (high - low) * index / denominator
                         for index in range(seconds))
            continue
        if kind in {"steady", "steady_state"}:
            value = _neutral(target.get("value"), target_type)
            if value is None:
                return {"status": "UNAVAILABLE", "reason": "INVALID_STEADY"}
            trace.extend([value] * seconds)
            continue
        return {"status": "UNAVAILABLE", "reason": "UNKNOWN_SEGMENT_KIND"}
    return {
        "status": "OK",
        "trace": trace,
        "trace_seconds": len(trace),
        "free_seconds": free_seconds,
        "has_free_segments": has_free,
    }


def wbal_nadir_kj(trace: Sequence[float], *, ftp: float = 250.0,
                  wprime_j: float = 20_000.0) -> float:
    cp = ftp / 0.96
    balance = wprime_j
    nadir = wprime_j
    for ratio in trace:
        watts = ratio * ftp
        if watts > cp:
            balance -= watts - cp
        else:
            tau = 546.0 * math.exp(-0.01 * (cp - watts)) + 316.0
            balance += (wprime_j - balance) * (1.0 - math.exp(-1.0 / tau))
        nadir = min(nadir, balance)
    return nadir / 1000.0


def score_design_dose(
    segments: Sequence[Mapping[str, Any]], *,
    main_set_segment_ids: Iterable[str] = (),
) -> Dict[str, Any]:
    expanded = prescribed_trace(segments)
    if expanded.get("status") == "UNAVAILABLE":
        return {
            "status": "UNAVAILABLE", "reason": expanded.get("reason"),
            "trace_seconds": 0, "free_seconds": 0,
            "has_free_segments": False, "design_if": None,
            "design_tss": None, "design_kj": None,
            "t_at_vo2max_seconds": None, "wbal_nadir_kj": None,
        }
    trace = expanded.pop("trace")
    if not trace:
        return {
            "status": "NOT_APPLICABLE", "reason": "EMPTY_PRESCRIBED_TRACE",
            "trace_seconds": 0, "free_seconds": expanded["free_seconds"],
            "has_free_segments": True, "design_if": None,
            "design_tss": None, "design_kj": None,
            "t_at_vo2max_seconds": None, "wbal_nadir_kj": None,
        }
    design_if = (sum(value ** 4 for value in trace) / len(trace)) ** 0.25
    ids = set(main_set_segment_ids)
    main_segments = [segment for segment in segments if segment.get("id") in ids]
    main_trace = prescribed_trace(main_segments) if ids else {"trace": []}
    main_values = main_trace.get("trace", [])
    return {
        "status": "APPLICABLE", "reason": None,
        "trace_seconds": len(trace), "free_seconds": expanded["free_seconds"],
        "has_free_segments": expanded["has_free_segments"],
        "design_if": design_if,
        "design_tss": (len(trace) / 3600.0) * design_if ** 2 * 100.0,
        "design_kj": sum(value * 250.0 / 1000.0 for value in trace),
        "t_at_vo2max_seconds": sum(value >= 1.06 for value in main_values),
        "wbal_nadir_kj": wbal_nadir_kj(trace),
    }


@lru_cache(maxsize=1)
def purpose_rows() -> Dict[str, Dict[str, Any]]:
    try:
        payload = yaml.safe_load(
            (CONFIG_DIR / "purpose_registry.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EarnedSelectionError("purpose registry is unavailable") from exc
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if payload.get("schema_version") != "purpose_registry/v1" or not isinstance(rows, list):
        raise EarnedSelectionError("invalid purpose registry")
    by_id = {row.get("row_id"): row for row in rows if isinstance(row, dict)}
    if len(rows) != 600 or len(by_id) != 600 or None in by_id:
        raise EarnedSelectionError("purpose registry must cover exactly 600 rows")
    return by_id


@lru_cache(maxsize=1)
def quality_gates() -> Dict[str, Any]:
    try:
        payload = yaml.safe_load(
            (CONFIG_DIR / "quality_gates.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EarnedSelectionError("quality gate registry is unavailable") from exc
    if payload.get("schema_version") != "quality_gates/v1":
        raise EarnedSelectionError("invalid quality gate registry")
    gates = payload.get("gates")
    if not isinstance(gates, list) or len(gates) != 6:
        raise EarnedSelectionError("quality gate registry is incomplete")
    if any(gate.get("status") not in {"hypothesis", "calibrated"} for gate in gates):
        raise EarnedSelectionError("invalid quality gate authority status")
    return payload


def _gate_record(gate: Mapping[str, Any], observed: str,
                 measurement: Mapping[str, Any], criterion: Mapping[str, Any]) -> Dict[str, Any]:
    if observed not in VERDICTS:
        raise EarnedSelectionError("invalid observed verdict")
    status = gate["status"]
    return {
        "gate_id": gate["gate_id"], "gate_version": gate["gate_version"],
        "authority_status": status, "observed_verdict": observed,
        "effective_verdict": "NOT_ENFORCED" if status == "hypothesis" else observed,
        "measurement": dict(measurement), "criterion": dict(criterion),
    }


def evaluate_purpose_gate(*, archetype_id: Optional[str], purpose: Mapping[str, Any],
                          is_assessment: bool, dose: Mapping[str, Any],
                          final_session: bool = False) -> list[Dict[str, Any]]:
    """Evaluate exactly one of the first four Appendix 6 gates."""
    gates = quality_gates()["gates"][:4]
    purpose_class = purpose.get("class")
    selected: list[Mapping[str, Any]] = []
    for gate in gates:
        applicability = gate["applicability"]
        ids = applicability.get("archetype_ids")
        include = applicability.get("include_purpose_classes")
        if ids is not None and archetype_id not in ids:
            continue
        if archetype_id in (applicability.get("exclude_archetype_ids") or []):
            continue
        if include is not None and purpose_class not in include:
            continue
        if applicability.get("exclude_is_assessment") and is_assessment:
            continue
        selected.append(gate)
    if len(selected) != 1:
        raise EarnedSelectionError(
            "purpose gate applicability is not total and exclusive for "
            f"{archetype_id!r}/{purpose_class!r}: "
            f"{[gate.get('gate_id') for gate in selected]}"
        )
    gate = selected[0]
    metric = gate["metric"]
    threshold = gate["threshold"]
    if metric == "t_at_vo2max_seconds":
        value = dose.get(metric)
        observed = ("UNAVAILABLE" if value is None else "PASS"
                    if threshold["minimum"] <= value <= threshold["maximum"] else "FAIL")
        measurement = {metric: value}
    elif metric == "wbal_nadir_kj":
        value = dose.get(metric)
        observed = ("UNAVAILABLE" if value is None else "PASS"
                    if threshold["minimum"] <= value <= threshold["maximum"] else "FAIL")
        measurement = {metric: value}
    elif metric == "prescribed_dose_record":
        fields = ("trace_seconds", "design_if", "design_tss", "design_kj")
        observed = "PASS" if all(dose.get(field) is not None for field in fields) else "UNAVAILABLE"
        measurement = {field: dose.get(field) for field in fields}
    else:
        observed = "PASS" if purpose_class in {"assessment", "free"} else "FAIL"
        measurement = {"dose_status": dose.get("status"), "purpose_class": purpose_class}
    return [_gate_record(gate, observed, measurement, threshold)]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_manifest_pin(pin: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    expected = {
        "snapshot_path": "certification_manifest.json",
        "snapshot_digest": canonical_digest(manifest),
        "manifest_version": manifest.get("schema_version"),
        "version_vector": manifest.get("version_vector"),
        "promotion_digests": [item["digest"] for item in manifest.get("promotion_artifacts", [])],
    }
    if dict(pin) != expected:
        raise EarnedSelectionError("manifest pin does not match snapshot")
