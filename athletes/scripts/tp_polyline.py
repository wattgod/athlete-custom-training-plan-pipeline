#!/usr/bin/env python3
"""TrainingPeaks structured-workout calendar-tile polyline.

SINGLE SOURCE OF TRUTH for the power-profile polyline TrainingPeaks draws on
its calendar tile (`structure["polyline"]`). The tile renders from this
polyline, NOT from the structure steps -- an empty polyline is a blank tile
(a trust-killer that shipped once; see docs/TP_API_REVERSE_ENGINEERING.md).

Reverse-engineered point-for-point from Matti's working OG TrainingPeaks
workouts. This module is intentionally standalone (stdlib only) and is VENDORED
byte-identically into both TP-building repos:
  - gravel-god-training-plans/tools/tp_polyline.py       (masters/marketplace)
  - athlete-custom-training-plan-pipeline/.../tp_polyline.py (custom plans)
Keep the two copies identical. Each repo's golden-fixture test
(test_tp_polyline.py, tp_polyline_golden.json) pins the exact output, so a
copy that drifts fails its own suite.
"""
from typing import Any, Dict, List, Union


JsonNumber = Union[int, float]


def _json_stable_number(value: float) -> JsonNumber:
    """Use JSON integers for integral coordinates across Python and JS."""
    return int(value) if value.is_integer() else value


def compute_polyline(structure: List[Dict[str, Any]]) -> List[List[JsonNumber]]:
    """Compute the TP calendar-tile power-profile polyline from a `structure`
    array (the same list that goes in body["structure"]["structure"]).

    The calendar tile draws its mini power-profile graph from this polyline,
    NOT from the structure steps (those drive the popup builder's graph). An
    empty polyline => a blank tile. Ported point-for-point from the reference
    build (gravel-god-training-plans/tools/build_tp_bodies.py::compute_polyline),
    itself reverse-engineered from Matti's working OG TrainingPeaks workouts:
    per step a vertical rise then a horizontal hold (x = fraction of total
    duration, y = fraction of peak intensity), bookended by [0,0] and [1,0].
    Cumulative time stays unrounded until each point is emitted. Emitted x
    values are clamped to [0, 1] and monotonically nondecreasing.
    """
    flat: List[Dict[str, Any]] = []
    for block in structure:
        length = block.get("length", {})
        inner = block.get("steps", [])
        if length.get("unit") == "repetition":
            for _ in range(int(length.get("value", 1))):
                flat.extend(inner)
        else:
            flat.extend(inner)

    durations, intensities = [], []
    for step in flat:
        durations.append(step.get("length", {}).get("value", 0))
        t0 = (step.get("targets") or [{}])[0]
        maxv = t0.get("maxValue")
        intensities.append(maxv if maxv is not None else t0.get("minValue", 0))

    total = sum(durations)
    peak = max(intensities + [1])
    polyline: List[List[JsonNumber]] = [[0, 0]]
    if total > 0:
        cum = 0.0
        emitted_x = 0.0
        for dur, intensity in zip(durations, intensities):
            y = round(intensity / peak, 3)
            t_begin = max(emitted_x, min(1.0, round(cum, 3)))
            cum += dur / total
            t_end = max(t_begin, min(1.0, round(cum, 3)))
            polyline.append([
                _json_stable_number(t_begin),
                _json_stable_number(y),
            ])
            polyline.append([
                _json_stable_number(t_end),
                _json_stable_number(y),
            ])
            emitted_x = t_end
    polyline.append([1, 0])
    return polyline
