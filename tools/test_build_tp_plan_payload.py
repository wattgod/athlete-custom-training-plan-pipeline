"""Tests for tools/build_tp_plan_payload.py.

Fixture athlete dir: a small synthetic tp_manifest.json + fulfillment_manifest.json
+ plan_dates.yaml mirroring the real shapes in athletes/<id>/ (see
athletes/steve-wagner/ for the reference build these fixtures are modeled on).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import build_tp_plan_payload as btpp
from tools.tp_polyline import polyline_from_structure

PLAN_DAY_ONE = "2026-08-31"

# golden_sessions() always trips exactly one FAIL (AE-3.11 banned-name on
# "FatMax Ride", 2026-09-04) -- clearing it via --allow-known-fails is how
# tests exercise the "gate passed, plan/notes payload written" path without
# also asserting the lint content itself (that's TestLintWiring's job).
KNOWN_FAILS_CLEAR_FATMAX = {("2026-09-04", "AE-3.11/AE-6.3", "FatMax Ride")}

NONZERO_STRUCTURE = {
    "importedFromZwo": True,
    "polyline": [[0, 0], [1, 0]],
    "primaryIntensityMetric": "percentOfFtp",
    "primaryIntensityTargetOrRange": "target",
    "primaryLengthMetric": "duration",
    "structure": [
        {
            "begin": 0, "end": 900,
            "length": {"unit": "repetition", "value": 1},
            "steps": [{
                "intensityClass": "active",
                "length": {"unit": "second", "value": 900},
                "name": "Steady State", "notes": "",
                "targets": [{"minValue": 65}],
            }],
            "type": "step",
        },
    ],
}

# AE-8.4d fixture: every block's first step carries the flat zero-power
# target ({"minValue": 0}, no maxValue) -- the exact shape the ratified rule
# forbids from shipping as a step graph.
ZERO_POWER_STRUCTURE = {
    "importedFromZwo": True,
    "polyline": [[0, 0], [1, 0]],
    "primaryIntensityMetric": "percentOfFtp",
    "primaryIntensityTargetOrRange": "target",
    "primaryLengthMetric": "duration",
    "structure": [
        {
            "begin": 0, "end": 60,
            "length": {"unit": "repetition", "value": 1},
            "steps": [{
                "intensityClass": "active",
                "length": {"unit": "second", "value": 60},
                "name": "Recruitment", "notes": "",
                "targets": [{"minValue": 0}],
            }],
            "type": "step",
        },
        {
            "begin": 60, "end": 120,
            "length": {"unit": "repetition", "value": 1},
            "steps": [{
                "intensityClass": "active",
                "length": {"unit": "second", "value": 60},
                "name": "Recruitment", "notes": "",
                "targets": [{"minValue": 0}],
            }],
            "type": "step",
        },
    ],
}


def _session(*, date, title, workout_type_value_id=2, description="body",
             total_time_planned=1.0, tss_planned=50.0, structure=None,
             pre_activity_comment=None):
    return {
        "date": date,
        "title": title,
        "display_name": title,
        "filename_stem": None,
        "description": description,
        "tp_kind": "bike" if workout_type_value_id == 2 else (
            "day_off" if workout_type_value_id == 7 else "strength"),
        "workout_type_value_id": workout_type_value_id,
        "tss_planned": tss_planned,
        "total_time_planned": total_time_planned,
        "structure": structure,
        "series_id": None, "series_index": None, "series_total": None,
        "order_on_day": 0, "strength_template": None, "archetype_id": None,
        "race": None, "control_basis": "ftp", "control_metric": "power",
        "library_item_id": None, "library_rpe_text": None,
        "pre_activity_comment": pre_activity_comment,
        "target_summary": "",
    }


def golden_sessions():
    return [
        # W00 -- before plan-day-one, plain session -> excluded
        _session(date="2026-08-25", title="Pre-Plan Easy",
                  total_time_planned=0.667, tss_planned=20),
        # Day 1 -- in window, real structure, no comment
        _session(date="2026-08-31", title="Z2 Ride",
                  total_time_planned=1.5, tss_planned=60,
                  structure=NONZERO_STRUCTURE),
        # in window, carries a pre-activity comment
        _session(date="2026-09-01", title="FTP Test",
                  total_time_planned=1.0, tss_planned=71.3,
                  pre_activity_comment="Feels great? Extend the duration, never add power."),
        # in window, AE-8.4d zero-power structure that must be suppressed
        _session(date="2026-09-02", title="Muscle Recruitment Progressions - Trainer",
                  total_time_planned=0.7, tss_planned=10,
                  structure=ZERO_POWER_STRUCTURE),
        # in window, day off
        _session(date="2026-09-03", title="Rest Day", workout_type_value_id=7,
                  description="Off the bike.", total_time_planned=0.0, tss_planned=0.0),
        # in window, deliberately trips ae_lint's banned-name FAIL (AE-3.11)
        _session(date="2026-09-04", title="FatMax Ride",
                  total_time_planned=1.5, tss_planned=55),
    ]


def golden_notes():
    return [
        {
            "date": "2026-08-25",
            "external_id": "note:fixture:weekly:2026-08-25",
            "logical_key": "weekly-briefing-2026-08-25",
            "text": "As a reminder, do your workout comments like this...",
            "title": btpp.COMMENT_PROTOCOL_TITLE,
        },
        {
            "date": "2026-08-25",
            "external_id": "note:fixture:weekly:2026-08-25:2",
            "logical_key": "weekly-briefing-2026-08-25-2",
            "text": "Week 0. The plan starts Monday.",
            "title": "Week 0: Pre-Plan",
        },
        {
            "date": "2026-08-31",
            "external_id": "note:fixture:weekly:2026-08-31",
            "logical_key": "weekly-briefing-2026-08-31",
            "text": "Week 1 of 6. Testing week.",
            "title": "Week 1: Testing",
        },
    ]


def golden_tp_manifest():
    return {
        "version": 1,
        "plan_title": "Fixture Athlete · Fixture Race · 6wk [CUSTOM]",
        "athlete": "Fixture Athlete",
        "race": {"name": "Fixture Race", "date": "2026-10-10", "priority": "A"},
        "expected": {"bike": 4, "day_off": 1, "strength": 0, "race": 0,
                     "total": len(golden_sessions())},
        "sessions": golden_sessions(),
    }


def golden_fulfillment_manifest():
    return {
        "schema_version": 1,
        "athlete_id": "fixture-athlete",
        "attachments": [],
        "calendar_dates": sorted({s["date"] for s in golden_sessions()}),
        "course_entitlement": {},
        "mental_training_tasks": [],
        "native_notes": golden_notes(),
        "verification_expectations": {},
        "workouts": golden_sessions(),
    }


@pytest.fixture
def athlete_dir(tmp_path):
    d = tmp_path / "fixture-athlete"
    d.mkdir()
    (d / "tp_manifest.json").write_text(json.dumps(golden_tp_manifest()), encoding="utf-8")
    (d / "fulfillment_manifest.json").write_text(
        json.dumps(golden_fulfillment_manifest()), encoding="utf-8")
    (d / "plan_dates.yaml").write_text(
        f"race_date: '2026-10-10'\nweek1_monday: '{PLAN_DAY_ONE}'\n", encoding="utf-8")
    return d


# --------------------------------------------------------------------- unit

class TestSuppressZeroPower:
    def test_all_zero_power_suppressed_to_none(self):
        assert btpp.suppress_zero_power(ZERO_POWER_STRUCTURE) is None

    def test_real_targets_pass_through_unchanged(self):
        assert btpp.suppress_zero_power(NONZERO_STRUCTURE) == NONZERO_STRUCTURE

    def test_none_structure_passes_through(self):
        assert btpp.suppress_zero_power(None) is None

    def test_mixed_zero_and_real_targets_not_suppressed(self):
        mixed = {
            "structure": [
                ZERO_POWER_STRUCTURE["structure"][0],
                NONZERO_STRUCTURE["structure"][0],
            ]
        }
        assert btpp.suppress_zero_power(mixed) == mixed

    def test_zero_power_first_step_with_honest_later_step_in_same_block_not_suppressed(self):
        # A single BLOCK whose first step is zero-power (e.g. a warmup
        # recruitment step) but a LATER step in that same block is honest
        # work. The old implementation only inspected steps[0] per block
        # and would wrongly suppress this; every step must be examined.
        block_with_ramp_then_work = {
            "structure": [
                {
                    "begin": 0, "end": 960,
                    "length": {"unit": "repetition", "value": 1},
                    "steps": [
                        {
                            "intensityClass": "active",
                            "length": {"unit": "second", "value": 60},
                            "name": "Recruitment", "notes": "",
                            "targets": [{"minValue": 0}],
                        },
                        {
                            "intensityClass": "active",
                            "length": {"unit": "second", "value": 900},
                            "name": "Steady State", "notes": "",
                            "targets": [{"minValue": 65}],
                        },
                    ],
                    "type": "step",
                },
            ],
        }
        assert btpp.suppress_zero_power(block_with_ramp_then_work) == block_with_ramp_then_work


class TestPolylineRecomputation:
    def test_upstream_polyline_is_never_trusted(self):
        # NONZERO_STRUCTURE's own polyline ([[0,0],[1,0]]) is a placeholder
        # that does NOT match what its steps compute to -- the emitted entry
        # must carry the recomputed value, not the upstream one.
        assert NONZERO_STRUCTURE["polyline"] != polyline_from_structure(NONZERO_STRUCTURE)
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        z2 = next(e for e in entries if e["title"] == "Z2 Ride")
        assert z2["structure"]["polyline"] == polyline_from_structure(NONZERO_STRUCTURE)
        assert z2["structure"]["polyline"] != NONZERO_STRUCTURE["polyline"]

    def test_null_structure_passes_through_without_polyline_key(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        rest = next(e for e in entries if e["title"] == "Rest Day")
        assert rest["structure"] is None

    def test_ae84d_suppressed_structure_never_gets_a_polyline(self):
        # A structure suppressed to None by AE-8.4d must stay None -- it
        # must not come back with a computed polyline bolted on.
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        recruitment = next(
            e for e in entries if e["title"] == "Muscle Recruitment Progressions - Trainer")
        assert recruitment["structure"] is None


class TestBuildPlanPayload:
    def test_w00_session_excluded(self):
        entries, excluded = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        assert all(e["workoutDay"][:10] >= PLAN_DAY_ONE for e in entries)
        assert {x["title"] for x in excluded} == {"Pre-Plan Easy"}

    def test_entry_shape_matches_tp_container_contract(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        z2 = next(e for e in entries if e["title"] == "Z2 Ride")
        # NONZERO_STRUCTURE ships a placeholder polyline; the emitted entry
        # must carry the recomputed one instead (see TestPolylineRecomputation).
        expected_structure = {
            **NONZERO_STRUCTURE,
            "polyline": polyline_from_structure(NONZERO_STRUCTURE),
        }
        assert z2 == {
            "title": "Z2 Ride",
            "workoutTypeValueId": 2,
            "workoutDay": "2026-08-31T00:00:00",
            "description": "body",
            "totalTimePlanned": 1.5,
            "tssPlanned": 60.0,
            "structure": expected_structure,
        }
        # no comment on this session -> key must be absent, not null
        assert "coachComments" not in z2

    def test_coach_comments_passthrough_only_when_present(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        ftp_test = next(e for e in entries if e["title"] == "FTP Test")
        assert ftp_test["coachComments"] == (
            "Feels great? Extend the duration, never add power.")

    def test_ae84d_zero_power_structure_suppressed_in_payload(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        recruitment = next(
            e for e in entries if e["title"] == "Muscle Recruitment Progressions - Trainer")
        assert recruitment["structure"] is None

    def test_day_off_entry_has_null_structure(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        rest = next(e for e in entries if e["title"] == "Rest Day")
        assert rest["structure"] is None
        assert rest["workoutTypeValueId"] == 7

    # ------------------------------------------------------ same-day order
    def test_same_day_strength_sorts_before_bike(self):
        # order_on_day contract (generate_athlete_package.py's TP
        # projection post-pass): 0 = strength first. Manifest order here is
        # deliberately bike-then-strength to prove the sort, not the
        # manifest's own order, decides the sequence.
        bike = _session(date="2026-09-15", title="Descending VO2 Pyramid")
        bike["order_on_day"] = 1
        strength = _session(date="2026-09-15", title="Cycling-Specific",
                             workout_type_value_id=5)
        strength["order_on_day"] = 0
        entries, _ = btpp.build_plan_payload([bike, strength], PLAN_DAY_ONE)
        assert [e["title"] for e in entries] == ["Cycling-Specific", "Descending VO2 Pyramid"]

    def test_same_day_same_order_on_day_keeps_manifest_order(self):
        first = _session(date="2026-09-15", title="First in manifest")
        second = _session(date="2026-09-15", title="Second in manifest")
        entries, _ = btpp.build_plan_payload([first, second], PLAN_DAY_ONE)
        assert [e["title"] for e in entries] == ["First in manifest", "Second in manifest"]

    def test_cross_day_order_unaffected_by_order_on_day(self):
        later_low_order = _session(date="2026-09-02", title="Later day")
        later_low_order["order_on_day"] = 0
        earlier_high_order = _session(date="2026-09-01", title="Earlier day")
        earlier_high_order["order_on_day"] = 5
        entries, _ = btpp.build_plan_payload(
            [later_low_order, earlier_high_order], PLAN_DAY_ONE)
        assert [e["title"] for e in entries] == ["Earlier day", "Later day"]


class TestBuildNotesPayload:
    def test_protocol_note_redated_and_included(self):
        entries, excluded, redated = btpp.build_notes_payload(golden_notes(), PLAN_DAY_ONE)
        protocol = next(e for e in entries if e["title"] == btpp.COMMENT_PROTOCOL_TITLE)
        assert protocol["noteDate"] == PLAN_DAY_ONE
        assert redated == [{
            "title": btpp.COMMENT_PROTOCOL_TITLE,
            "original_date": "2026-08-25",
            "redated_to": PLAN_DAY_ONE,
        }]

    def test_other_w00_note_excluded_not_redated(self):
        entries, excluded, redated = btpp.build_notes_payload(golden_notes(), PLAN_DAY_ONE)
        assert {e["title"] for e in entries} == {
            btpp.COMMENT_PROTOCOL_TITLE, "Week 1: Testing"}
        assert excluded == [{"date": "2026-08-25", "title": "Week 0: Pre-Plan"}]

    def test_in_window_note_passthrough(self):
        entries, _, _ = btpp.build_notes_payload(golden_notes(), PLAN_DAY_ONE)
        week1 = next(e for e in entries if e["title"] == "Week 1: Testing")
        assert week1 == {
            "title": "Week 1: Testing",
            "noteDate": "2026-08-31",
            "description": "Week 1 of 6. Testing week.",
        }


class TestDefaultPlanDayOne:
    def test_reads_week1_monday_from_plan_dates_yaml(self, athlete_dir):
        assert btpp.default_plan_day_one(athlete_dir) == PLAN_DAY_ONE

    def test_missing_plan_dates_yaml_raises(self, tmp_path):
        with pytest.raises(btpp.PlanPayloadError):
            btpp.default_plan_day_one(tmp_path)


# ---------------------------------------------------------------- lint wiring

class TestLintWiring:
    def test_known_fail_surfaces_in_findings(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        report = btpp.run_lint(entries, "2026-10-10")
        assert report["fail"] >= 1
        assert any(f["rule"].startswith("AE-3.11") for f in report["findings"])
        assert report["unresolved_fails"] == [
            f for f in report["findings"] if f["severity"] == "FAIL"]

    def test_allow_known_fails_clears_unresolved(self):
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        report = btpp.run_lint(entries, "2026-10-10")
        fail = next(f for f in report["findings"] if f["severity"] == "FAIL")
        known = {(fail["day"], fail["rule"], fail["title"])}
        resolved = btpp.run_lint(entries, "2026-10-10", known_fails=known)
        assert resolved["unresolved_fails"] == []
        assert resolved["fail"] == report["fail"]  # still counted, just allow-listed


# ------------------------------------------------------------------- build()

class TestBuild:
    def test_writes_all_four_artifacts(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        report = btpp.build(athlete_dir, out_dir, known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        for name in ("plan_payload.json", "notes_payload.json",
                      "exclusions.json", "lint.json"):
            assert (out_dir / name).exists()
        assert report["plan_day_one"] == PLAN_DAY_ONE

    def test_plan_payload_excludes_w00(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        btpp.build(athlete_dir, out_dir, known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        payload = json.loads((out_dir / "plan_payload.json").read_text())
        assert all(e["workoutDay"][:10] >= PLAN_DAY_ONE for e in payload)
        assert len(payload) == len(golden_sessions()) - 1

    def test_notes_payload_includes_redated_protocol_note(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        btpp.build(athlete_dir, out_dir, known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        notes = json.loads((out_dir / "notes_payload.json").read_text())
        protocol = next(n for n in notes if n["title"] == btpp.COMMENT_PROTOCOL_TITLE)
        assert protocol["noteDate"] == PLAN_DAY_ONE
        assert len(notes) == 2  # protocol note + Week 1 (Week 0 excluded)

    def test_exclusions_file_shape(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        # exclusions.json is written regardless of the lint gate -- exercise
        # that with the DEFAULT (unresolved-FAIL) path, no known_fails.
        btpp.build(athlete_dir, out_dir)
        exclusions = json.loads((out_dir / "exclusions.json").read_text())
        assert exclusions["plan_day_one"] == PLAN_DAY_ONE
        assert exclusions["excluded_sessions"] == [
            {"date": "2026-08-25", "title": "Pre-Plan Easy"}]
        assert exclusions["excluded_notes"] == [
            {"date": "2026-08-25", "title": "Week 0: Pre-Plan"}]
        assert exclusions["redated_notes"][0]["title"] == btpp.COMMENT_PROTOCOL_TITLE

    def test_explicit_plan_day_one_overrides_yaml(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        report = btpp.build(athlete_dir, out_dir, plan_day_one="2026-09-01",
                             known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        assert report["plan_day_one"] == "2026-09-01"
        payload = json.loads((out_dir / "plan_payload.json").read_text())
        assert all(e["workoutDay"][:10] >= "2026-09-01" for e in payload)

    def test_missing_tp_manifest_raises(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        (d / "fulfillment_manifest.json").write_text("{}", encoding="utf-8")
        with pytest.raises(btpp.PlanPayloadError):
            btpp.build(d, tmp_path / "out")

    # ---------------------------------------------------- gate ordering
    def test_unresolved_fail_writes_lint_and_exclusions_but_not_payloads(
            self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        report = btpp.build(athlete_dir, out_dir)  # no known_fails -> gate blocked
        assert report["unresolved_fails"]
        assert (out_dir / "lint.json").exists()
        assert (out_dir / "exclusions.json").exists()
        assert not (out_dir / "plan_payload.json").exists()
        assert not (out_dir / "notes_payload.json").exists()

    def test_gate_blocked_deletes_stale_payloads_from_a_prior_clean_run(
            self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        # First run: gate clean -> both payloads written.
        btpp.build(athlete_dir, out_dir, known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        assert (out_dir / "plan_payload.json").exists()
        assert (out_dir / "notes_payload.json").exists()
        # Second run into the SAME out_dir, gate now blocked -> the stale
        # payloads from the clean run must not survive.
        btpp.build(athlete_dir, out_dir)
        assert not (out_dir / "plan_payload.json").exists()
        assert not (out_dir / "notes_payload.json").exists()

    # -------------------------------------------------------- empty plan
    def test_zero_sessions_after_w00_filter_raises_and_writes_no_payload(
            self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        with pytest.raises(btpp.PlanPayloadError, match="zero sessions"):
            # Every golden session predates this plan_day_one.
            btpp.build(athlete_dir, out_dir, plan_day_one="2099-01-01",
                       known_fails=KNOWN_FAILS_CLEAR_FATMAX)
        assert not (out_dir / "plan_payload.json").exists()

    # --------------------------------------------------- date validation
    def test_malformed_plan_day_one_raises(self, athlete_dir, tmp_path):
        with pytest.raises(btpp.PlanPayloadError, match="malformed date"):
            btpp.build(athlete_dir, tmp_path / "out", plan_day_one="08-31-2026")

    def test_malformed_session_date_raises_naming_the_session(self, tmp_path):
        sessions = [_session(date="2026-13-40", title="Bad Date Ride")]
        with pytest.raises(btpp.PlanPayloadError, match="Bad Date Ride"):
            btpp.build_plan_payload(sessions, PLAN_DAY_ONE)

    def test_malformed_note_date_raises_naming_the_note(self):
        notes = [{"date": "not-a-date", "title": "Broken Note", "text": "x"}]
        with pytest.raises(btpp.PlanPayloadError, match="Broken Note"):
            btpp.build_notes_payload(notes, PLAN_DAY_ONE)

    # ------------------------------------------------------- duplicates
    def test_duplicate_note_title_same_date_raises(self):
        notes = [
            {"date": "2026-09-01", "title": "Week 1: Testing", "text": "a"},
            {"date": "2026-09-01", "title": "Week 1: Testing", "text": "b"},
        ]
        with pytest.raises(btpp.PlanPayloadError, match="duplicate"):
            btpp.build_notes_payload(notes, PLAN_DAY_ONE)


# ---------------------------------------------------------------------- CLI

class TestCLI:
    def test_main_exits_nonzero_on_unresolved_fail(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        rc = btpp.main([
            "--athlete-dir", str(athlete_dir),
            "--out-dir", str(out_dir),
        ])
        assert rc == 1

    def test_main_exits_zero_with_allow_known_fails(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        entries, _ = btpp.build_plan_payload(golden_sessions(), PLAN_DAY_ONE)
        report = btpp.run_lint(entries, "2026-10-10")
        fail = next(f for f in report["findings"] if f["severity"] == "FAIL")
        known_path = tmp_path / "known_fails.json"
        known_path.write_text(json.dumps([
            {"day": fail["day"], "rule": fail["rule"], "title": fail["title"]}
        ]), encoding="utf-8")

        rc = btpp.main([
            "--athlete-dir", str(athlete_dir),
            "--out-dir", str(out_dir),
            "--allow-known-fails", str(known_path),
        ])
        assert rc == 0

    def test_main_exits_2_on_missing_manifest(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        rc = btpp.main(["--athlete-dir", str(d), "--out-dir", str(tmp_path / "out")])
        assert rc == 2

    def test_cli_subprocess_smoke(self, athlete_dir, tmp_path):
        out_dir = tmp_path / "out"
        known_path = tmp_path / "known_fails.json"
        known_path.write_text(json.dumps([
            {"day": "2026-09-04", "rule": "AE-3.11/AE-6.3", "title": "FatMax Ride"}
        ]), encoding="utf-8")
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(repo_root / "tools" / "build_tp_plan_payload.py"),
             "--athlete-dir", str(athlete_dir),
             "--out-dir", str(out_dir),
             "--allow-known-fails", str(known_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert (out_dir / "plan_payload.json").exists()
