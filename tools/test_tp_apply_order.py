"""Tests for tp_apply_order.py (D5).

Covers manifest validation, apply_job.json emission (golden fixture from a
synthetic manifest), receipt validation, and approval-gate refusal paths.
Deliberately no browser/network tests — tp_apply_driver.js executes in a
real TP browser tab and is out of pytest's reach; --server paths here are
exercised with a monkeypatched network layer only.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import tp_apply_order as tao


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _session(*, date, title, tp_kind, order_on_day=0, workout_type_value_id=2,
             strength_template=None, display_name=None, description="", structure=None,
             tss_planned=50, total_time_planned=1.0, race=None):
    return {
        "date": date,
        "title": title,
        "display_name": display_name or title,
        "filename_stem": f"W01_{title.replace(' ', '_')}",
        "description": description,
        "tp_kind": tp_kind,
        "workout_type_value_id": workout_type_value_id,
        "tss_planned": tss_planned,
        "total_time_planned": total_time_planned,
        "structure": structure,
        "series_id": None,
        "series_index": None,
        "series_total": None,
        "order_on_day": order_on_day,
        "strength_template": strength_template,
        "archetype_id": None,
        "race": race,
    }


def golden_manifest() -> dict:
    """A synthetic tp_manifest.json mirroring plan_ir.py:project_tp_manifest's
    real output shape: version, plan_title, athlete, race, expected, sessions."""
    sessions = [
        _session(date="2026-08-03", title="Endurance Ride", tp_kind="bike"),
        _session(date="2026-08-04", title="Rest Day", tp_kind="day_off", workout_type_value_id=7),
        _session(date="2026-08-05", title="Foundation (A)", tp_kind="strength",
                 order_on_day=0, workout_type_value_id=9, strength_template="foundation_a",
                 tss_planned=19, total_time_planned=0.75),
        _session(date="2026-08-05", title="Intervals", tp_kind="bike", order_on_day=1),
        _session(date="2026-08-06", title="Example Downtown Criterium", tp_kind="race",
                 race={"priority": "A"}, tss_planned=120, total_time_planned=3.0),
    ]
    return {
        "version": 1,
        "plan_title": "Example Client · Example Downtown Criterium · 10wk [CUSTOM]",
        "athlete": "Example Client",
        "race": {"name": "Example Downtown Criterium", "date": "2026-08-06", "priority": "A"},
        "expected": {"bike": 2, "strength": 1, "day_off": 1, "race": 1, "total": 5},
        "sessions": sessions,
    }


@pytest.fixture
def package_dir(tmp_path):
    d = tmp_path / "pkg"
    d.mkdir()
    (d / tao.MANIFEST_FILENAME).write_text(json.dumps(golden_manifest()), encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Manifest validation
# ---------------------------------------------------------------------------

class TestValidateManifest:
    def test_golden_manifest_is_valid(self):
        tao.validate_manifest(golden_manifest())  # must not raise

    def test_missing_required_key_rejected(self):
        manifest = golden_manifest()
        del manifest["expected"]
        with pytest.raises(tao.ApplyOrderError, match="missing required key"):
            tao.validate_manifest(manifest)

    def test_expected_total_mismatch_rejected(self):
        manifest = golden_manifest()
        manifest["expected"]["total"] = 999
        with pytest.raises(tao.ApplyOrderError, match="expected.total"):
            tao.validate_manifest(manifest)

    def test_session_tally_mismatch_rejected(self):
        manifest = golden_manifest()
        # Keep total consistent so the total-sum check passes and the
        # per-kind tally check (which compares against actual sessions) is
        # the one that catches this.
        manifest["expected"]["bike"] = 1
        manifest["expected"]["day_off"] = 2
        with pytest.raises(tao.ApplyOrderError, match="session tally"):
            tao.validate_manifest(manifest)

    def test_unknown_tp_kind_rejected(self):
        manifest = golden_manifest()
        manifest["sessions"][0]["tp_kind"] = "bogus"
        with pytest.raises(tao.ApplyOrderError, match="tp_kind"):
            tao.validate_manifest(manifest)

    def test_strength_without_template_rejected(self):
        manifest = golden_manifest()
        for session in manifest["sessions"]:
            if session["tp_kind"] == "strength":
                session["strength_template"] = None
        with pytest.raises(tao.ApplyOrderError, match="strength_template"):
            tao.validate_manifest(manifest)

    def test_strength_with_bike_type_id_rejected(self):
        manifest = golden_manifest()
        for session in manifest["sessions"]:
            if session["tp_kind"] == "strength":
                session["workout_type_value_id"] = 2
        with pytest.raises(tao.ApplyOrderError, match="bike workoutTypeValueId"):
            tao.validate_manifest(manifest)

    def test_empty_sessions_rejected(self):
        manifest = golden_manifest()
        manifest["sessions"] = []
        with pytest.raises(tao.ApplyOrderError, match="non-empty list"):
            tao.validate_manifest(manifest)


# ---------------------------------------------------------------------------
# Package / manifest loading
# ---------------------------------------------------------------------------

class TestLoadManifest:
    def test_loads_from_directory(self, package_dir):
        manifest = tao.load_manifest(package_dir)
        assert manifest["plan_title"].endswith("[CUSTOM]")

    def test_missing_manifest_raises(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(tao.ApplyOrderError, match="not found"):
            tao.load_manifest(empty)

    def test_resolve_package_dir_extracts_zip(self, tmp_path):
        zip_path = tmp_path / "example-athlete-full-package.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("example-athlete/" + tao.MANIFEST_FILENAME, json.dumps(golden_manifest()))
            zf.writestr("example-athlete/training_guide.html", "<html></html>")

        extracted = tao.resolve_package_dir(zip_path)
        manifest = tao.load_manifest(extracted)  # discovered via rglob under the nested folder
        assert manifest["expected"]["total"] == 5

    def test_resolve_package_dir_missing_path_raises(self, tmp_path):
        with pytest.raises(tao.ApplyOrderError, match="not found"):
            tao.resolve_package_dir(tmp_path / "does-not-exist")


# ---------------------------------------------------------------------------
# apply_job.json emission
# ---------------------------------------------------------------------------

class TestBuildApplyJob:
    def test_requires_athlete_tp_id(self):
        with pytest.raises(tao.ApplyOrderError, match="athlete_tp_id"):
            tao.build_apply_job(golden_manifest(), athlete_tp_id="", target_date=None, start_type=1)

    def test_golden_job_without_strength_module(self):
        """Pinned golden fixture: module absent -> strength jobs carry
        {pending_module: true}, per spec's degrade-gracefully instruction."""
        job = tao.build_apply_job(golden_manifest(), athlete_tp_id="2000302",
                                  target_date=None, start_type=1, strength_module=None)

        assert job["plan_title"] == "Example Client · Example Downtown Criterium · 10wk [CUSTOM]"
        assert job["athlete_tp_id"] == "2000302"
        assert job["duplicate_guard"] == {"title": job["plan_title"]}
        assert job["strength_module_pending"] is True
        assert job["custom_exercises"] == []

        # bike/day_off/race sessions land in workouts[]; strength does not.
        assert len(job["workouts"]) == 4
        assert {w["title"] for w in job["workouts"]} == {
            "Endurance Ride", "Rest Day", "Intervals", "Example Downtown Criterium",
        }
        assert all("strength_template" not in w for w in job["workouts"])

        assert len(job["strength"]) == 1
        strength = job["strength"][0]
        assert strength == {
            "date": "2026-08-05", "order_on_day": 0, "title": "Foundation (A)",
            "template_key": "foundation_a", "pending_module": True, "doc": None,
        }

        assert job["apply"] == {"targetDate": None, "startType": 1, "enabled": False}
        assert job["verify"] == {
            "expected": {"bike": 2, "strength": 1, "day_off": 1, "race": 1, "total": 5},
            "date_range": {"start": "2026-08-03", "end": "2026-08-06"},
        }
        assert job["rollback"] == {"snapshot_range": {"start": "2026-08-03", "end": "2026-08-06"}}

    def test_target_date_enables_apply_stage(self):
        job = tao.build_apply_job(golden_manifest(), athlete_tp_id="2000302",
                                  target_date="2027-06-28", start_type=3, strength_module=None)
        assert job["apply"] == {"targetDate": "2027-06-28", "startType": 3, "enabled": True}

    def test_strength_module_present_builds_docs(self):
        calls = []

        class FakeStrengthModule:
            @staticmethod
            def build_strength_doc(template_key, *, calendar_id, prescribed_date, doc_id, uuid_factory):
                calls.append((template_key, calendar_id, prescribed_date, doc_id))
                return {"title": template_key, "blocks": [], "prescribedDate": prescribed_date, "id": uuid_factory()}

            @staticmethod
            def custom_exercises_needed():
                return [{"key": "dead_bug", "title": "Dead Bug"}]

        job = tao.build_apply_job(golden_manifest(), athlete_tp_id="2000302", target_date=None,
                                  start_type=1, strength_module=FakeStrengthModule(),
                                  uuid_factory=lambda: "fixed-uuid")

        assert "strength_module_pending" not in job
        assert job["custom_exercises"] == [{"key": "dead_bug", "title": "Dead Bug"}]
        assert calls == [("foundation_a", None, "2026-08-05", None)]
        strength = job["strength"][0]
        assert strength["doc"] == {"title": "foundation_a", "blocks": [],
                                   "prescribedDate": "2026-08-05", "id": "fixed-uuid"}
        assert "pending_module" not in strength

    def test_total_time_planned_passes_through_unrounded_and_stays_whole_minutes(self):
        """Regression guard for the "4:09:44" ragged-duration bug: PlanIR
        (plan_ir.py::_round_time_planned_hours) is the single place
        total_time_planned is computed -- tp_apply_order._workout_entry must
        be a pure passthrough (session.get("total_time_planned"), no
        re-derivation) so a whole-minute value entering the apply-job body
        stays whole-minute, byte-for-byte. 4.1333h == 248min exactly (the
        value a real "Endurance with Surges" session projects to)."""
        manifest = golden_manifest()
        manifest["sessions"][0]["total_time_planned"] = 4.1333
        job = tao.build_apply_job(manifest, athlete_tp_id="2000302",
                                  target_date=None, start_type=1, strength_module=None)
        entry = next(w for w in job["workouts"] if w["title"] == "Endurance Ride")
        assert entry["totalTimePlanned"] == 4.1333, (
            "totalTimePlanned was re-derived instead of passed through unchanged")
        reconstructed_sec = round(entry["totalTimePlanned"] * 3600)
        assert reconstructed_sec % 60 == 0, (
            f"totalTimePlanned {entry['totalTimePlanned']} is not a whole number of minutes "
            f"({reconstructed_sec}s)")


# ---------------------------------------------------------------------------
# Receipt validation
# ---------------------------------------------------------------------------

def _ok_receipt(**overrides):
    receipt = {
        "finishedAt": "2026-08-10T00:00:00Z",
        "failures": [],
        "planId": 661259,
        "planPersonId": 2000302,
        "verified": {"bike_and_race": 3, "strength": 1, "day_off": 1, "total": 5},
    }
    receipt.update(overrides)
    return receipt


class TestValidateReceipt:
    def test_valid_receipt_has_no_problems(self):
        problems = tao.validate_receipt(_ok_receipt(), golden_manifest(), apply_enabled=False)
        assert problems == []

    def test_not_a_dict(self):
        assert tao.validate_receipt([], golden_manifest(), apply_enabled=False) == \
            ["receipt must be a JSON object"]

    def test_missing_finished_at(self):
        problems = tao.validate_receipt(_ok_receipt(finishedAt=None), golden_manifest(), apply_enabled=False)
        assert any("finishedAt" in p for p in problems)

    def test_nonempty_failures_flagged(self):
        problems = tao.validate_receipt(
            _ok_receipt(failures=[{"stage": "workouts", "message": "boom"}]),
            golden_manifest(), apply_enabled=False)
        assert any("failure" in p for p in problems)

    def test_missing_plan_ids_flagged(self):
        problems = tao.validate_receipt(_ok_receipt(planId=None, planPersonId=None),
                                        golden_manifest(), apply_enabled=False)
        assert any("planId" in p for p in problems)
        assert any("planPersonId" in p for p in problems)

    def test_verified_count_mismatch_flagged(self):
        problems = tao.validate_receipt(
            _ok_receipt(verified={"bike_and_race": 2, "strength": 1, "day_off": 1, "total": 4}),
            golden_manifest(), apply_enabled=False)
        assert any("verified.bike_and_race" in p for p in problems)
        assert any("verified.total" in p for p in problems)

    def test_apply_enabled_requires_applied_and_athlete_verified(self):
        problems = tao.validate_receipt(_ok_receipt(), golden_manifest(), apply_enabled=True)
        assert any("applied.status" in p for p in problems)
        assert any("athleteVerified" in p for p in problems)

    def test_apply_enabled_passes_with_full_evidence(self):
        receipt = _ok_receipt(
            applied={"appliedPlanId": 10828759, "status": "ok"},
            athleteVerified={"bike_and_race": 3, "strength": 1, "day_off": 1, "total": 5},
        )
        problems = tao.validate_receipt(receipt, golden_manifest(), apply_enabled=True)
        assert problems == []


# ---------------------------------------------------------------------------
# Approval-gate refusal paths
# ---------------------------------------------------------------------------

class TestApprovalGate:
    def test_server_approved_passes(self, monkeypatch):
        monkeypatch.setattr(tao, "fetch_fulfillment_status",
                            lambda server, token, athlete_id: {"status": "APPROVED"})
        status = tao.check_approval_gate(server="https://example.railway.app", token="secret",
                                         athlete_id="example_client", skip_approval_check=False)
        assert status["status"] == "APPROVED"

    def test_server_not_approved_refused(self, monkeypatch):
        monkeypatch.setattr(tao, "fetch_fulfillment_status",
                            lambda server, token, athlete_id: {"status": "GENERATED"})
        with pytest.raises(tao.ApprovalGateError, match="not APPROVED"):
            tao.check_approval_gate(server="https://example.railway.app", token="secret",
                                    athlete_id="example_client", skip_approval_check=False)

    def test_server_without_token_refused(self):
        with pytest.raises(tao.ApplyOrderError, match="token"):
            tao.check_approval_gate(server="https://example.railway.app", token="",
                                    athlete_id="example_client", skip_approval_check=False)

    def test_no_server_no_skip_refused(self):
        with pytest.raises(tao.ApprovalGateError, match="local/dev mode"):
            tao.check_approval_gate(server=None, token=None, athlete_id="example_client",
                                    skip_approval_check=False)

    def test_no_server_with_skip_proceeds(self, capsys):
        result = tao.check_approval_gate(server=None, token=None, athlete_id="example_client",
                                         skip_approval_check=True)
        assert result is None
        assert "WARNING" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# CLI end-to-end (no network — job mode + local receipt validation only)
# ---------------------------------------------------------------------------

class TestMainJobMode:
    def test_writes_apply_job_with_skip_approval_check(self, package_dir, capsys):
        rc = tao.main(["example_client", "--package", str(package_dir),
                      "--athlete-tp-id", "2000302", "--skip-approval-check"])
        assert rc == 0
        job_path = package_dir / "apply_job.json"
        assert job_path.exists()
        job = json.loads(job_path.read_text())
        assert job["athlete_tp_id"] == "2000302"
        assert "OPERATOR RUNBOOK" in capsys.readouterr().out

    def test_missing_athlete_tp_id_errors(self, package_dir):
        rc = tao.main(["example_client", "--package", str(package_dir), "--skip-approval-check"])
        assert rc == 1

    def test_no_server_no_skip_exits_3(self, package_dir):
        rc = tao.main(["example_client", "--package", str(package_dir), "--athlete-tp-id", "2000302"])
        assert rc == 3

    def test_server_not_approved_exits_3(self, package_dir, monkeypatch):
        monkeypatch.setattr(tao, "fetch_fulfillment_status",
                            lambda server, token, athlete_id: {"status": "BLOCKED_REVIEW"})
        monkeypatch.setenv("CRON_SECRET", "secret")
        rc = tao.main(["example_client", "--package", str(package_dir), "--athlete-tp-id", "2000302",
                      "--server", "https://example.railway.app"])
        assert rc == 3


class TestMainReceiptMode:
    def _write_receipt(self, tmp_path, **overrides):
        receipt = _ok_receipt(**overrides)
        path = tmp_path / "receipt.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path

    def test_valid_receipt_exits_0(self, package_dir, tmp_path, capsys):
        receipt_path = self._write_receipt(tmp_path)
        rc = tao.main(["example_client", "--package", str(package_dir), "--receipt", str(receipt_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "receipt OK" in out
        assert "plan_registry.py register" in out
        assert "plan_registry.py check" in out

    def test_invalid_receipt_exits_1(self, package_dir, tmp_path):
        receipt_path = self._write_receipt(tmp_path, finishedAt=None)
        rc = tao.main(["example_client", "--package", str(package_dir), "--receipt", str(receipt_path)])
        assert rc == 1

    def test_receipt_mode_posts_applied_transition_with_server(self, package_dir, tmp_path, monkeypatch):
        receipt_path = self._write_receipt(tmp_path)
        posted = {}

        def fake_post(server, token, athlete_id, coach, evidence):
            posted.update(server=server, token=token, athlete_id=athlete_id, coach=coach, evidence=evidence)
            return {"status": "APPLIED"}

        monkeypatch.setattr(tao, "post_applied_transition", fake_post)
        monkeypatch.setenv("CRON_SECRET", "secret-token")
        rc = tao.main(["example_client", "--package", str(package_dir), "--receipt", str(receipt_path),
                      "--server", "https://example.railway.app", "--coach", "coach_lee"])
        assert rc == 0
        assert posted["athlete_id"] == "example_client"
        assert posted["token"] == "secret-token"
        assert posted["coach"] == "coach_lee"
        assert posted["evidence"]["planId"] == 661259
