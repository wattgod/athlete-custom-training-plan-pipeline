"""Contract test for the TP calendar-tile polyline (tp_polyline.compute_polyline).

The polyline algorithm is duplicated across two separate repos/deploys (this
one and gravel-god-training-plans/tools/build_tp_bodies.py::compute_polyline)
because there is no shared package between them. `tp_polyline_golden.json`
holds structure->polyline vectors generated FROM the canonical reference
implementation; these tests pin this repo's copy to that exact output, so any
drift from the reference is caught here (a blank/wrong polyline = a blank or
wrong calendar tile).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from tp_polyline import compute_polyline

_GOLDEN = json.loads((Path(__file__).parent / "tp_polyline_golden.json").read_text())


def _norm(polyline):
    # JSON round-trips ints/floats as-is; normalise to lists for comparison.
    return [list(p) for p in polyline]


def test_matches_reference_golden_vectors():
    """Every golden case reproduces the reference polyline exactly."""
    for name, structure in _GOLDEN["inputs"].items():
        expected = _norm(_GOLDEN["expected"][name])
        got = _norm(compute_polyline(structure))
        assert got == expected, f"polyline drift on {name}:\n  got  {got}\n  want {expected}"


def test_every_case_opens_and_closes_flat():
    for name, structure in _GOLDEN["inputs"].items():
        poly = compute_polyline(structure)
        assert list(poly[0]) == [0, 0], f"{name} must open at [0,0]"
        assert list(poly[-1]) == [1, 0], f"{name} must close at [1,0]"
        assert len(poly) >= 3, f"{name} polyline too short: {poly}"


def test_empty_structure_is_flat_line():
    assert compute_polyline([]) == [[0, 0], [1, 0]]


def test_peak_normalizes_to_one():
    # Hardest step's y == 1.0 (intensity / peak).
    structure = _GOLDEN["inputs"]["vo2_intervals_unrolled"]
    ys = [p[1] for p in compute_polyline(structure)]
    assert max(ys) == 1.0, "peak step must normalise to y=1.0"


def test_integral_points_are_json_integers_without_changing_fractional_points():
    structure = [{
        "length": {"value": 1, "unit": "repetition"},
        "steps": [
            {
                "length": {"value": 1, "unit": "second"},
                "targets": [{"minValue": 50}],
            },
            {
                "length": {"value": 2, "unit": "second"},
                "targets": [{"minValue": 100}],
            },
        ],
    }]

    polyline = compute_polyline(structure)

    assert polyline == [
        [0, 0], [0, 0.5], [0.333, 0.5],
        [0.333, 1], [1, 1], [1, 0],
    ]
    assert all(
        type(value) is int
        for point in polyline
        for value in point
        if value in (0, 1)
    )
    assert all(
        type(value) is float
        for point in polyline
        for value in point
        if value not in (0, 1)
    )
    encoded = json.dumps(polyline, separators=(",", ":"))
    assert "0.0" not in encoded
    assert "1.0" not in encoded


def test_x_values_are_clamped_and_monotonic_for_rounding_heavy_structure():
    structure = _GOLDEN["inputs"]["vo2_intervals_unrolled"]
    xs = [point[0] for point in compute_polyline(structure)]
    assert all(0 <= x <= 1 for x in xs)
    assert xs == sorted(xs)


@pytest.mark.parametrize("durations", [
    [1] * 3, [1] * 7, [17, 19, 23, 29, 31], [1, 999, 1, 999, 1],
])
def test_duration_fraction_property(durations):
    structure = [{
        "length": {"value": 1, "unit": "repetition"},
        "steps": [{
            "length": {"value": duration, "unit": "second"},
            "targets": [{"minValue": 50 + index}],
        }],
    } for index, duration in enumerate(durations)]
    xs = [point[0] for point in compute_polyline(structure)]
    assert xs == sorted(xs)
    assert min(xs) == 0 and max(xs) == 1
