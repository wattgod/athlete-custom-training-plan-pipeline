"""Tests for tools/tp_polyline.py.

tools/tp_polyline.py is a thin wrapper around
athletes/scripts/tp_polyline.py::compute_polyline (the single source of
truth, peak-normalized -- see tp_polyline.py's module docstring for the
2026-08-26 live-evidence correction from an earlier flat /100 rule). This
file's golden cases draw on athletes/scripts/tp_polyline_golden.json --
the same vectors that pin the underlying module's own contract -- so a
regression in either copy is caught from both sides.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.tp_polyline import polyline_from_structure

ROOT = Path(__file__).resolve().parents[1]
_UNDERLYING_GOLDEN = json.loads(
    (ROOT / "athletes" / "scripts" / "tp_polyline_golden.json").read_text())


def _as_structure_obj(blocks):
    return {"primaryIntensityMetric": "percentOfFtp", "structure": blocks}


# ------------------------------------------------------------- golden case
#
# 100-peak reference (2026-08-26 known-good TP card): peak intensity in this
# structure IS 100, so flat-/100 and peak-normalization agree here -- this
# is why it "still passes" across the algorithm correction.

GOLDEN_STRUCTURE = {
    "primaryIntensityMetric": "percentOfFtp",
    "structure": [
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Warm up", "length": {"value": 1200, "unit": "second"},
                    "targets": [{"minValue": 50, "maxValue": 70}], "intensityClass": "warmUp"}]},
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Active", "length": {"value": 360, "unit": "second"},
                    "targets": [{"minValue": 100}], "intensityClass": "active"}]},
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Rest", "length": {"value": 240, "unit": "second"},
                    "targets": [{"minValue": 55}], "intensityClass": "rest"}]},
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Active", "length": {"value": 360, "unit": "second"},
                    "targets": [{"minValue": 100}], "intensityClass": "active"}]},
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Rest", "length": {"value": 240, "unit": "second"},
                    "targets": [{"minValue": 55}], "intensityClass": "rest"}]},
        {"type": "step", "length": {"value": 1, "unit": "repetition"},
         "steps": [{"name": "Cool down", "length": {"value": 600, "unit": "second"},
                    "targets": [{"minValue": 50}], "intensityClass": "coolDown"}]},
    ],
}

GOLDEN_POLYLINE = [
    [0, 0], [0, 0.7], [0.4, 0.7], [0.4, 1], [0.52, 1], [0.52, 0.55],
    [0.6, 0.55], [0.6, 1], [0.72, 1], [0.72, 0.55], [0.8, 0.55],
    [0.8, 0.5], [1, 0.5], [1, 0],
]


class TestGoldenReproduction:
    def test_100_peak_reference_reproduces_exactly(self):
        assert polyline_from_structure(GOLDEN_STRUCTURE) == GOLDEN_POLYLINE

    def test_missing_metric_defaults_to_percent_of_ftp(self):
        structure = {k: v for k, v in GOLDEN_STRUCTURE.items()
                     if k != "primaryIntensityMetric"}
        assert polyline_from_structure(structure) == GOLDEN_POLYLINE


# ---------------------------------------------------------- sub-100 peak
#
# The correction this course-change exists to fix: live evidence (four
# TP-native ZWO-imported cards on athlete 33194, max targets 58/60/64/65%
# FTP, all polyline maxY == 1.0) shows TP normalizes to the WORKOUT'S OWN
# peak, not a flat /100. warmup 50-60% (600s), steady 65% (900s),
# cooldown 50% (300s) -- peak is 65, so the steady step (the workout's
# hardest effort) must normalize to y == 1.0, not y == 0.65.

class TestSubHundredPeakNormalization:
    def test_peak_step_normalizes_to_one_not_its_raw_percent(self):
        structure = _as_structure_obj([
            {"length": {"value": 1, "unit": "repetition"},
             "steps": [{"length": {"value": 600, "unit": "second"},
                        "targets": [{"minValue": 50, "maxValue": 60}]}]},
            {"length": {"value": 1, "unit": "repetition"},
             "steps": [{"length": {"value": 900, "unit": "second"},
                        "targets": [{"minValue": 65}]}]},
            {"length": {"value": 1, "unit": "repetition"},
             "steps": [{"length": {"value": 300, "unit": "second"},
                        "targets": [{"minValue": 50}]}]},
        ])
        computed = polyline_from_structure(structure)
        assert max(p[1] for p in computed) == 1
        # 60/65, 65/65, 50/65 -- NOT 0.6, 0.65 (raw /100), NOT 0.923-style
        # miscomputation from the wrong denominator.
        assert computed == [
            [0, 0], [0, 0.923], [0.333, 0.923], [0.333, 1],
            [0.833, 1], [0.833, 0.769], [1, 0.769], [1, 0],
        ]


# ------------------------------------------- underlying-module golden cases
#
# Per the course correction: reuse athletes/scripts/tp_polyline_golden.json
# directly rather than hand-deriving fixtures -- these are the same vectors
# that pin the single source of truth's own contract, including its
# repetition-unroll case (vo2_intervals_unrolled) and its deliberately
# NON-collapsed equal-y duplicate points (both that case and ftp_test).

class TestUnderlyingGoldenVectors:
    def test_every_underlying_golden_case_reproduces_through_the_wrapper(self):
        for name, blocks in _UNDERLYING_GOLDEN["inputs"].items():
            expected = [list(p) for p in _UNDERLYING_GOLDEN["expected"][name]]
            got = polyline_from_structure(_as_structure_obj(blocks))
            assert got == expected, f"drift on {name}:\n  got  {got}\n  want {expected}"

    def test_repetition_block_unrolls_via_vo2_intervals_case(self):
        # vo2_intervals_unrolled is a single repeated work/rest block
        # (length.unit="repetition", value>1, two leaf steps) -- the
        # underlying module must unroll it to N cycles on the time axis
        # before totals/cumulatives are computed.
        blocks = _UNDERLYING_GOLDEN["inputs"]["vo2_intervals_unrolled"]
        computed = polyline_from_structure(_as_structure_obj(blocks))
        assert computed[0] == [0, 0]
        assert computed[-1] == [1, 0]
        assert max(p[1] for p in computed) == 1.0

    def test_adjacent_equal_y_boundaries_are_not_collapsed(self):
        # vo2_intervals_unrolled's own golden output carries a literal
        # duplicate point pair ([0.667, 0.4], [0.667, 0.4]) where two
        # adjacent steps share the same normalized y -- the single source
        # of truth does NOT collapse this, and neither does this wrapper.
        blocks = _UNDERLYING_GOLDEN["inputs"]["vo2_intervals_unrolled"]
        computed = polyline_from_structure(_as_structure_obj(blocks))
        assert [0.667, 0.4] in computed
        assert computed.count([0.667, 0.4]) == 2


# --------------------------------------------------------------------- RPE

class TestRpeMetric:
    def test_live_accepted_rpe_fixture_carries_no_polyline_convention(self):
        fixture_path = (ROOT / "athletes" / "scripts" / "tests" / "fixtures"
                         / "tp_run_structure_fixture.json")
        data = json.loads(fixture_path.read_text())
        structure_obj = data["structure"]
        assert structure_obj["primaryIntensityMetric"] == "rpe"
        # The live-accepted payload itself ships an empty polyline for this
        # RPE structure -- there is no established non-empty convention to
        # reverse-engineer, so this module matches that: empty.
        assert structure_obj["polyline"] == []
        assert polyline_from_structure(structure_obj) == []

    def test_perceived_exertion_metric_is_also_empty(self):
        structure = dict(GOLDEN_STRUCTURE)
        structure["primaryIntensityMetric"] = "perceivedExertion"
        assert polyline_from_structure(structure) == []


# --------------------------------------------------------------- degenerate

class TestDegenerate:
    def test_none_returns_empty(self):
        assert polyline_from_structure(None) == []

    def test_empty_dict_returns_empty(self):
        assert polyline_from_structure({}) == []

    def test_missing_structure_key_returns_empty(self):
        assert polyline_from_structure({"primaryIntensityMetric": "percentOfFtp"}) == []

    def test_empty_structure_list_returns_empty(self):
        assert polyline_from_structure(
            {"primaryIntensityMetric": "percentOfFtp", "structure": []}) == []

    def test_zero_total_duration_delegates_to_underlying_flat_line(self):
        # A non-empty blocks list whose only step has zero duration is NOT
        # short-circuited by this wrapper -- it delegates, and the single
        # source of truth's own contract for this input (see
        # athletes/scripts/test_tp_polyline.py::test_empty_structure_is_flat_line)
        # is a flat [[0,0],[1,0]] line, not [].
        structure = _as_structure_obj([
            {"length": {"value": 1, "unit": "repetition"},
             "steps": [{"length": {"value": 0, "unit": "second"},
                        "targets": [{"minValue": 50}]}]},
        ])
        assert polyline_from_structure(structure) == [[0, 0], [1, 0]]
