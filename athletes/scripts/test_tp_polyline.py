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
