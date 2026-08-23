"""project_tp_structure must carry authored ZWO cadence into the executable TP
structure. Regression for the Aug 23 2026 six-athlete publication, where
every cadence prescription (e.g. Michael Beal's "RLP Rising Cadence 15")
reached TrainingPeaks as prose only: the canonical segment kept the cadence
in `zwo.extra_attributes` and the projector never read it.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from canonical_training_model import CanonicalModelError, project_tp_structure
from tp_cadence import CADENCE_UNIT

POWER = {"control_metric": "power", "control_basis": "ftp", "power_basis": "measured"}
RPE = {"control_metric": "rpe", "control_basis": "rpe", "power_basis": "none"}


def _seg(kind, seconds, target, **zwo_attrs):
    seg = {"kind": kind, "name": kind, "seconds": seconds, "target": target}
    if zwo_attrs:
        seg["zwo"] = {"tag": "SteadyState", "attribute_order": list(zwo_attrs),
                      "extra_attributes": dict(zwo_attrs), "children": []}
    return seg


def _rising_cadence_15():
    """Shape of TP library item 14356264 as authored in ZWO."""
    return {"title": "RLP Rising Cadence 15", "tp_kind": "bike", "segments": [
        _seg("warmup", 300, {"type": "power_pct_ftp", "low": 0.48, "high": 0.48}),
        _seg("steady_state", 300, {"type": "power_pct_ftp", "value": 0.66}),
        _seg("steady_state", 300, {"type": "power_pct_ftp", "value": 0.84}, CadenceLow="65", CadenceHigh="75"),
        _seg("steady_state", 300, {"type": "power_pct_ftp", "value": 0.84}, CadenceLow="75", CadenceHigh="90"),
        _seg("steady_state", 600, {"type": "power_pct_ftp", "value": 0.84}, CadenceLow="90", CadenceHigh="100"),
        _seg("steady_state", 600, {"type": "power_pct_ftp", "value": 0.66}),
        _seg("cooldown", 300, {"type": "power_pct_ftp", "low": 0.49, "high": 0.49}),
    ]}


def _targets(structure):
    return [blk["steps"][0]["targets"] for blk in structure["structure"]]


def test_power_structure_carries_cadence_exactly_like_the_library_item():
    structure = project_tp_structure(_rising_cadence_15(), POWER)
    assert structure["primaryIntensityMetric"] == "percentOfFtp"
    assert _targets(structure) == [
        [{"minValue": 48}],
        [{"minValue": 66}],
        [{"minValue": 84}, {"minValue": 65, "maxValue": 75, "unit": CADENCE_UNIT}],
        [{"minValue": 84}, {"minValue": 75, "maxValue": 90, "unit": CADENCE_UNIT}],
        [{"minValue": 84}, {"minValue": 90, "maxValue": 100, "unit": CADENCE_UNIT}],
        [{"minValue": 66}],
        [{"minValue": 49}],
    ]
    assert structure["polyline"], "cadence target must not disturb the tile polyline"


def test_intervals_split_work_and_resting_cadence():
    session = {"title": "Cadence HC", "tp_kind": "bike", "segments": [{
        "kind": "intervals", "name": "intervals", "repeat": 2,
        "on_seconds": 60, "off_seconds": 120,
        "target": {"type": "power_pct_ftp", "on": 0.95, "off": 0.55},
        "zwo": {"tag": "IntervalsT", "attribute_order": [], "children": [],
                "extra_attributes": {"Cadence": "110", "CadenceResting": "85"}},
    }]}
    targets = _targets(project_tp_structure(session, POWER))
    assert targets == [
        [{"minValue": 95}, {"minValue": 110, "unit": CADENCE_UNIT}],
        [{"minValue": 55}, {"minValue": 85, "unit": CADENCE_UNIT}],
    ] * 2


def test_intervals_without_resting_cadence_leave_recovery_unconstrained():
    session = {"title": "Stabs", "tp_kind": "bike", "segments": [{
        "kind": "intervals", "repeat": 1, "on_seconds": 30, "off_seconds": 120,
        "target": {"type": "power_pct_ftp", "on": 1.2, "off": 0.5},
        "zwo": {"tag": "IntervalsT", "attribute_order": [], "children": [],
                "extra_attributes": {"CadenceLow": "100", "CadenceHigh": "120"}},
    }]}
    targets = _targets(project_tp_structure(session, POWER))
    assert targets[0] == [{"minValue": 120}, {"minValue": 100, "maxValue": 120, "unit": CADENCE_UNIT}]
    assert targets[1] == [{"minValue": 50}]


def test_cadence_is_emitted_regardless_of_control_metric():
    session = {"title": "x", "tp_kind": "bike", "segments": [
        _seg("steady_state", 300, {"type": "rpe", "value": 6}, Cadence="95")]}
    structure = project_tp_structure(session, RPE)
    assert structure["primaryIntensityMetric"] == "rpe"
    assert _targets(structure) == [[{"minValue": 6, "maxValue": 6}, {"minValue": 95, "unit": CADENCE_UNIT}]]


def test_segments_without_envelope_are_unchanged():
    session = {"title": "x", "tp_kind": "bike", "segments": [
        _seg("steady_state", 300, {"type": "power_pct_ftp", "value": 0.7})]}
    assert _targets(project_tp_structure(session, POWER)) == [[{"minValue": 70}]]


def test_absurd_cadence_fails_closed_with_session_context():
    session = {"title": "Broken", "tp_kind": "bike", "segments": [
        _seg("steady_state", 300, {"type": "power_pct_ftp", "value": 0.7}, Cadence="400")]}
    with pytest.raises(CanonicalModelError, match="Broken"):
        project_tp_structure(session, POWER)
