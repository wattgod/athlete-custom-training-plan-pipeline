#!/usr/bin/env python3
"""Compute the TrainingPeaks calendar-tile power-profile polyline.

THIN WRAPPER around ``athletes/scripts/tp_polyline.py::compute_polyline`` --
the vendored SINGLE SOURCE OF TRUTH for TP's calendar-tile polyline (itself
reverse-engineered from Matti's working OG TrainingPeaks workouts, and
vendored byte-identically into gravel-god-training-plans/tools/tp_polyline.py
too). This module does NOT reimplement the polyline math -- it delegates.

TP PEAK-NORMALIZES y: ``y = intensity / workout's own peak intensity``, NOT
a flat ``intensity / 100``. Confirmed 2026-08-26 against four live TP-native
ZWO-imported cards on athlete 33194 with max targets of 58/60/64/65% FTP --
every one carries polyline maxY == 1.0. A flat ``/100`` rule only agreed
with athletes/scripts/tp_polyline.py on an earlier reference case because
that case's own peak happened to be exactly 100.

The underlying module already unrolls repetition blocks (``length.unit ==
"repetition"`` -> N cycles on the time axis) -- see its own
``athletes/scripts/test_tp_polyline.py`` / ``tp_polyline_golden.json``, which
this module's tests also draw on. It does NOT collapse adjacent equal-y
step boundaries into a single point (redundant identical-coordinate points
are intentionally part of its golden-pinned output, e.g. the
``vo2_intervals_unrolled`` case) -- so this wrapper does not add any such
collapsing either; doing so would silently diverge from the single source
of truth's own verified contract.

This module adds only what the underlying module cannot know on its own:
  - RPE-metric skip: a structure with ``primaryIntensityMetric`` in
    {"rpe", "perceivedExertion"} returns ``[]`` -- there is no
    live-verified RPE polyline convention (see
    ``athletes/scripts/tests/fixtures/tp_run_structure_fixture.json``, a
    live-accepted TP run payload whose own stored polyline is ``[]`` for
    an RPE structure).
  - Degenerate-input guards: a missing/falsy ``structure_obj`` or an empty
    ``structure`` (blocks) list returns ``[]`` rather than delegating (the
    underlying module's own ``compute_polyline([])`` returns
    ``[[0, 0], [1, 0]]`` -- a flat line -- which is correct for a REAL
    zero-duration structure but not useful as this wrapper's signal for
    "there was nothing here to begin with").

Pure function: no I/O, no network. See tp_polyline.js for the faithful JS
port used by browser repair scripts.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parents[1]
_ATHLETES_SCRIPTS = _ROOT / "athletes" / "scripts"
if str(_ATHLETES_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_ATHLETES_SCRIPTS))

from tp_polyline import compute_polyline  # noqa: E402  -- single source of truth

_RPE_METRICS = {"rpe", "perceivedExertion"}


def polyline_from_structure(structure_obj: Mapping[str, Any] | None) -> list[list[float]]:
    """Compute the calendar-tile polyline for one TP ``structure`` object
    (the ``{"structure": [...blocks...], "primaryIntensityMetric": ...}``
    shape carried on a session / plan-payload entry's ``structure`` field).

    Delegates the actual peak-normalized computation to
    ``athletes/scripts/tp_polyline.py::compute_polyline`` -- see module
    docstring. Returns ``[]`` for a missing/falsy structure, an
    RPE-metric structure, or an empty blocks list.
    """
    if not structure_obj:
        return []

    metric = structure_obj.get("primaryIntensityMetric")
    if metric in _RPE_METRICS:
        return []

    blocks = structure_obj.get("structure") or []
    if not blocks:
        return []

    return compute_polyline(blocks)
