"""Contract tests for tp_cadence (TP cadence target emission).

The helper is vendored byte-identical in two repos (this one and
gravel-god-training-plans/tools/tp_cadence.py) with no shared package.
`tp_cadence_golden.json` holds the shared vectors; any drift between the
copies fails here instead of silently dropping an athlete's cadence.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from tp_cadence import (CADENCE_UNIT, REST, WORK, CadenceError, cadence_target,
                        has_cadence_target, with_cadence)

_GOLDEN = json.loads((Path(__file__).parent / "tp_cadence_golden.json").read_text())


@pytest.mark.parametrize("case", _GOLDEN["cases"], ids=[c["name"] for c in _GOLDEN["cases"]])
def test_golden_vectors(case):
    assert cadence_target(case["attributes"], case["phase"]) == case["expected"]


@pytest.mark.parametrize("case", _GOLDEN["errors"], ids=[c["name"] for c in _GOLDEN["errors"]])
def test_golden_errors_fail_closed(case):
    with pytest.raises(CadenceError):
        cadence_target(case["attributes"], case["phase"])


def test_with_cadence_appends_after_primary_target():
    primary = [{"minValue": 84}]
    out = with_cadence(primary, {"CadenceLow": "75", "CadenceHigh": "90"}, WORK)
    assert out[0] == {"minValue": 84}, "intensity must stay targets[0] (polyline + TP read it there)"
    assert out[1] == {"minValue": 75, "maxValue": 90, "unit": CADENCE_UNIT}
    assert primary == [{"minValue": 84}], "input list is not mutated"


def test_with_cadence_is_identity_without_cadence():
    assert with_cadence([{"minValue": 55}], {"Duration": "600"}, REST) == [{"minValue": 55}]
    assert with_cadence([{"minValue": 55}], None) == [{"minValue": 55}]


def test_has_cadence_target():
    assert has_cadence_target([{"minValue": 84}, {"minValue": 90, "unit": CADENCE_UNIT}])
    assert not has_cadence_target([{"minValue": 84}])
    assert not has_cadence_target(None)


def test_unknown_phase_rejected():
    with pytest.raises(ValueError):
        cadence_target({"Cadence": "90"}, "warmup")
