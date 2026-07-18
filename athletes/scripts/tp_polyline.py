#!/usr/bin/env python3
"""TrainingPeaks structured-workout calendar-tile polyline.

SINGLE SOURCE OF TRUTH for the power-profile polyline TrainingPeaks draws on
its calendar tile (`structure["polyline"]`). The tile renders from this
polyline, NOT from the structure steps -- an empty polyline is a blank tile
(a trust-killer that shipped once; see docs/TP_API_REVERSE_ENGINEERING.md).

Reverse-engineered point-for-point from Matti's working OG TrainingPeaks
workouts. This module is intentionally standalone (stdlib only) so it can be
vendored byte-identically into any repo that builds TP structures. The
CANONICAL SIBLING is `gravel-god-training-plans/tools/build_tp_bodies.py::
compute_polyline` (the masters/marketplace pipeline) -- keep the algorithm in
lockstep; `tests/`... the golden-fixture test in this repo
(test_tp_polyline.py) pins the exact output so drift is caught here.
"""
from typing import Any, Dict, List


def compute_polyline(structure: List[Dict[str, Any]]) -> List[List[float]]:
    """Compute the TP calendar-tile power-profile polyline from a `structure`
    array (the same list that goes in body["structure"]["structure"]).

    The calendar tile draws its mini power-profile graph from this polyline,
    NOT from the structure steps (those drive the popup builder's graph). An
    empty polyline => a blank tile. Ported point-for-point from the reference
    build (gravel-god-training-plans/tools/build_tp_bodies.py::compute_polyline),
    itself reverse-engineered from Matti's working OG TrainingPeaks workouts:
    per step a vertical rise then a horizontal hold (x = fraction of total
    duration, y = fraction of peak intensity), bookended by [0,0] and [1,0].
    Each step's duration fraction is rounded to 3 decimals BEFORE accumulating
    into the running cumulative fraction (matching the source data exactly, so
    rounding drift can push the last cumulative point slightly past 1 before
    the explicit closing [1,0]).
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
    polyline: List[List[float]] = [[0, 0]]
    if total > 0:
        cum = 0.0
        for dur, intensity in zip(durations, intensities):
            y = round(intensity / peak, 3)
            t_begin = round(cum, 3)
            cum = round(cum + round(dur / total, 3), 3)
            polyline.append([t_begin, y])
            polyline.append([cum, y])
    polyline.append([1, 0])
    return polyline
