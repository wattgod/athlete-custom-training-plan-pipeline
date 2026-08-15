"""TP accepts malformed structures on POST but won't render them.

Found on a live graded delivery: apply-contract structures lacked
importedFromZwo and step notes, and free-ride steps carried EMPTY targets —
the calendar mini-chart drew a gap, the polyline skipped the step (warping
every other bar's height), and the workout-detail builder refused the
structure. These tests pin the render-safe shape (parity with the
known-good build_tp_bodies conventions).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from canonical_training_model import project_tp_structure

CONTROL = {"control_metric": "power", "control_basis": "ftp"}


def _session(segments):
    return {"tp_kind": "bike", "segments": segments}


def test_structure_carries_render_required_fields():
    s = project_tp_structure(_session([
        {"kind": "warmup", "seconds": 600,
         "target": {"type": "power_pct_ftp", "low": 0.5, "high": 0.75}},
    ]), CONTROL)
    assert s["importedFromZwo"] is True
    step = s["structure"][0]["steps"][0]
    assert step["notes"] == ""
    assert step["targets"], "steps must never carry empty targets"


def test_free_ride_steps_are_never_target_empty():
    s = project_tp_structure(_session([
        {"kind": "steady_state", "seconds": 1740,
         "target": {"type": "power_pct_ftp", "value": 0.55}},
        {"kind": "free_ride", "seconds": 180, "target": {"type": "free"}},
    ]), CONTROL)
    free = s["structure"][1]["steps"][0]
    assert free["targets"] == [{"minValue": 0}]
    # and the polyline must include the step (no gaps)
    xs = [p[0] for p in s["polyline"]]
    assert max(xs) == 1


def test_all_out_free_ride_gets_display_band_and_tops_polyline():
    s = project_tp_structure(_session([
        {"kind": "warmup", "seconds": 1200,
         "target": {"type": "power_pct_ftp", "low": 0.5, "high": 0.75}},
        {"kind": "free_ride", "seconds": 180, "name": "3min all-out test",
         "target": {"type": "free"}},
    ]), CONTROL)
    band = s["structure"][1]["steps"][0]["targets"][0]
    assert band == {"minValue": 120, "maxValue": 170}
    ys = [p[1] for p in s["polyline"]]
    assert max(ys) == 1.0
    # the warmup must NOT be the tallest block anymore
    assert s["polyline"][1][1] < 1.0
