#!/usr/bin/env python3
"""Canonical rTSS estimation for normalized RUN-LIB segments.

RUN-LIB loaders convert authored minute durations to seconds before any
validation reaches this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from numbers import Real
from typing import Any


# Ordered to make the authored RPE bands auditable against the RUN-LIB spec.
RPE_IF_TABLE = (
    ((1, 2), 0.55),
    ((2, 3), 0.62),
    ((3, 4), 0.70),
    ((4, 5), 0.78),
    ((5, 6), 0.83),
    ((6, 7), 0.88),
    ((7, 8), 0.93),
    ((8, 9), 1.00),
    ((9, 10), 1.05),
)

_RPE_TO_IF = dict(RPE_IF_TABLE)


def band_for(rpe_pair: object) -> float:
    """Return the intensity factor for an exact authored RPE band.

    RUN-LIB intervals use the table's pairs verbatim; wider mixed bands are
    deliberately invalid rather than interpolated.
    """
    try:
        band = tuple(rpe_pair)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"RPE band must match a RUN-LIB table row: {rpe_pair!r}") from exc
    try:
        return _RPE_TO_IF[band]
    except KeyError as exc:
        raise ValueError(f"RPE band must match a RUN-LIB table row: {rpe_pair!r}") from exc


def _expanded_segments(segments: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Unroll nested repeat blocks into their ordered leaf segments."""
    expanded: list[Mapping[str, Any]] = []
    for segment in segments:
        if segment.get("type") != "repeat":
            expanded.append(segment)
            continue

        count = segment.get("count")
        children = segment.get("of")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Repeat segments require a non-negative integer count")
        if not isinstance(children, list):
            raise ValueError("Repeat segments require a list of child segments")
        for _ in range(count):
            expanded.extend(_expanded_segments(children))
    return expanded


def _unrounded_tss(segments: Iterable[Mapping[str, Any]]) -> float:
    """Return unrounded rTSS for normalized seconds-based segments."""
    total = 0.0
    for segment in _expanded_segments(segments):
        duration = segment.get("duration")
        if not isinstance(duration, Real) or isinstance(duration, bool):
            raise ValueError(f"Run segment duration must be numeric: {duration!r}")
        total += (duration / 3600) * band_for(segment.get("rpe")) ** 2 * 100
    return total


def estimate_tss(segments: Iterable[Mapping[str, Any]]) -> int:
    """Estimate rTSS as Σ(segment_hours × IF² × 100), rounded to an int."""
    return int(round(_unrounded_tss(segments)))
