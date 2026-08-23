"""TrainingPeaks-native cadence target for structured-workout steps.

Vendored byte-identical in
  athlete-custom-training-plan-pipeline/athletes/scripts/tp_cadence.py
  gravel-god-training-plans/tools/tp_cadence.py
(no shared package between the repos -- same arrangement as tp_polyline.py).
Each repo's test_tp_cadence.py pins this file to the shared golden vectors,
so drift between the two copies fails a test rather than a workout.

WHY THIS EXISTS
TP's structured-workout schema has no step-level cadence field. Cadence is a
SECOND element of a step's `targets` array, after the primary intensity
target, carrying unit "roundOrStridePerMinute". Proven from provider
readback of the 2026-07-18 library export (2,080 such targets across 425
items, e.g. library item 14356264 "RLP Rising Cadence 15"):

    "targets": [{"minValue": 84},
                {"minValue": 75, "maxValue": 90, "unit": "roundOrStridePerMinute"}]

Until Aug 2026 every cadence target in TP got there through TP's own ZWO
importer (which reads Cadence= / CadenceLow= / CadenceHigh=). Any path that
builds TP JSON directly -- canonical_training_model.project_tp_structure,
build_tp_bodies.py -- bypasses that importer and silently dropped cadence.
This helper is the one place both paths get it from.

ZWO ATTRIBUTE MAPPING (Zwift workout XML)
  CadenceLow + CadenceHigh -> range target          (work steps)
  Cadence                  -> single target         (work steps)
  CadenceResting           -> single target         (IntervalsT recovery step)
A single target is emitted as {"minValue": N, "unit": ...} -- the form TP
returned for the pipeline-generated item W01_Fri_Jul31_Cadence_Work.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

CADENCE_UNIT = "roundOrStridePerMinute"
CADENCE_MIN_RPM = 30
CADENCE_MAX_RPM = 200

WORK = "work"
REST = "rest"


class CadenceError(ValueError):
    """A ZWO cadence attribute that cannot be a real prescription."""


def _rpm(value: Any, attribute: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        rpm = int(round(float(value)))
    except (TypeError, ValueError):
        raise CadenceError(f"{attribute}={value!r} is not numeric") from None
    if not CADENCE_MIN_RPM <= rpm <= CADENCE_MAX_RPM:
        raise CadenceError(
            f"{attribute}={rpm} is outside {CADENCE_MIN_RPM}-{CADENCE_MAX_RPM} rpm")
    return rpm


def cadence_target(attributes: Optional[Mapping[str, Any]],
                   phase: str = WORK) -> Optional[Dict[str, Any]]:
    """TP cadence target for one step, or None when the ZWO element carries
    no cadence for that phase. `attributes` is the ZWO element's attribute
    mapping (or the canonical model's `zwo.extra_attributes`). `phase` is
    WORK for every step except the recovery step of an IntervalsT, which
    is REST and reads CadenceResting only."""
    if phase not in (WORK, REST):
        raise ValueError(f"unknown cadence phase {phase!r}")
    attrs = attributes or {}
    if phase == REST:
        rpm = _rpm(attrs.get("CadenceResting"), "CadenceResting")
        return {"minValue": rpm, "unit": CADENCE_UNIT} if rpm is not None else None
    low = _rpm(attrs.get("CadenceLow"), "CadenceLow")
    high = _rpm(attrs.get("CadenceHigh"), "CadenceHigh")
    single = _rpm(attrs.get("Cadence"), "Cadence")
    if low is not None and high is not None:
        lo, hi = sorted((low, high))
        if hi > lo:
            return {"minValue": lo, "maxValue": hi, "unit": CADENCE_UNIT}
        return {"minValue": lo, "unit": CADENCE_UNIT}
    rpm = single if single is not None else (high if high is not None else low)
    return {"minValue": rpm, "unit": CADENCE_UNIT} if rpm is not None else None


def with_cadence(targets: List[Dict[str, Any]],
                 attributes: Optional[Mapping[str, Any]],
                 phase: str = WORK) -> List[Dict[str, Any]]:
    """Return `targets` with the step's cadence target appended (never
    inserted before the primary intensity target -- TP and
    compute_polyline both read targets[0] as the intensity)."""
    result = list(targets)
    cadence = cadence_target(attributes, phase)
    if cadence is not None:
        result.append(cadence)
    return result


def has_cadence_target(targets: Optional[List[Dict[str, Any]]]) -> bool:
    return any(isinstance(t, dict) and t.get("unit") == CADENCE_UNIT
               for t in (targets or []))
