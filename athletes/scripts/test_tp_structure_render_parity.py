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
RPE_CONTROL = {"control_metric": "rpe", "control_basis": "rpe"}


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


def test_composed_session_boundaries_get_warmup_and_cooldown_intensity():
    # FIX 10 (Aug 17 2026 adversarial grade): a composed Act/midweek sim's
    # ZWO renderer emits its own warm-up/cool-down as plain <SteadyState>
    # blocks (never a literal <Warmup>/<Cooldown> ZWO tag), so after the
    # ZWO round-trip both boundary segments carry kind="steady_state" --
    # the first and last projected structure blocks read as generic
    # "active" work, identical to the hardest interval in between.
    s = project_tp_structure(_session([
        {"kind": "steady_state", "seconds": 600, "name": "Warm-up",
         "target": {"type": "power_pct_ftp", "value": 0.55}},
        {"kind": "intervals", "repeat": 2, "on_seconds": 300, "off_seconds": 180,
         "target": {"type": "power_pct_ftp", "on": 0.95, "off": 0.55}},
        {"kind": "steady_state", "seconds": 600, "name": "Cooldown",
         "target": {"type": "power_pct_ftp", "value": 0.5}},
    ]), CONTROL)
    assert s["structure"][0]["steps"][0]["intensityClass"] == "warmUp"
    assert s["structure"][-1]["steps"][0]["intensityClass"] == "coolDown"
    # The interval work in between must be untouched.
    assert s["structure"][1]["steps"][0]["intensityClass"] == "active"


def test_free_ride_boundary_is_never_mislabeled_a_cooldown():
    # A composed session's boundary is only tagged coolDown when it's a
    # real cool-down -- an all-out test/effort at the end of a session
    # must never read as a cool-down, even though it is structurally the
    # LAST block.
    s = project_tp_structure(_session([
        {"kind": "steady_state", "seconds": 600,
         "target": {"type": "power_pct_ftp", "value": 0.55}},
        {"kind": "free_ride", "seconds": 180, "name": "3min all-out test",
         "target": {"type": "free"}},
    ]), CONTROL)
    assert s["structure"][0]["steps"][0]["intensityClass"] == "warmUp"
    assert s["structure"][-1]["steps"][0]["intensityClass"] == "active"


def test_rpe_bike_projects_live_accepted_timed_structure():
    s = project_tp_structure(_session([
        {"kind": "warmup", "seconds": 600,
         "target": {"type": "rpe", "low": 2, "high": 4}},
        {"kind": "intervals", "repeat": 2, "on_seconds": 30, "off_seconds": 180,
         "target": {"type": "rpe", "on": 7, "off": 2}},
        {"kind": "cooldown", "seconds": 300,
         "target": {"type": "rpe", "low": 4, "high": 2}},
    ]), RPE_CONTROL)
    assert s["primaryIntensityMetric"] == "rpe"
    assert s["primaryIntensityTargetOrRange"] == "range"
    assert s["importedFromZwo"] is True
    assert s["polyline"][0] == [0, 0]
    assert s["polyline"][-1] == [1, 0]
    targets = [block["steps"][0]["targets"][0] for block in s["structure"]]
    assert targets == [
        {"minValue": 2, "maxValue": 4},
        {"minValue": 7, "maxValue": 7},
        {"minValue": 2, "maxValue": 2},
        {"minValue": 7, "maxValue": 7},
        {"minValue": 2, "maxValue": 2},
        {"minValue": 2, "maxValue": 4},
    ]


def test_rpe_all_out_free_ride_gets_honest_max_effort_target():
    s = project_tp_structure(_session([
        {"kind": "free_ride", "seconds": 60, "name": "1min all-out test",
         "target": {"type": "free"}},
    ]), RPE_CONTROL)
    target = s["structure"][0]["steps"][0]["targets"][0]
    assert target == {"minValue": 10, "maxValue": 10}
