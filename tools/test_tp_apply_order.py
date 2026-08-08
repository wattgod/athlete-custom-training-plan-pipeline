"""Tests for Phase 1-disabled tp_apply_order.py and its retained gate helpers."""
from __future__ import annotations

import json
import subprocess
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


def sealed_binding(**overrides) -> dict:
    value = {
        "order_id": "order-1",
        "athlete_id": "example_client",
        "delivery_platform": "trainingpeaks",
        "generation_revision": 2,
        "model_seal": "seal-2",
        "release_manifest_digest": "release-2",
        "tp_manifest_sha256": "manifest-2",
        "apply_gate_url": "https://example.railway.app/api/fulfillment/order-1/apply-gate",
        "apply_gate_token": "short-lived-token",
    }
    value.update(overrides)
    return value


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
# apply_job.json emission is hard-disabled
# ---------------------------------------------------------------------------

class TestBuildApplyJob:
    def test_direct_builder_refuses_all_inputs(self):
        with pytest.raises(
                tao.ApprovalGateError,
                match="AUTOMATED TRAININGPEAKS APPLY IS DISABLED FOR PHASE 1"):
            tao.build_apply_job(
                golden_manifest(), athlete_tp_id="2000302",
                target_date="2027-06-28", start_type=3,
                binding=sealed_binding())


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
    @staticmethod
    def _status(**overrides):
        value = {
            "status": "APPROVED", "legacy": False,
            "delivery_platform": "trainingpeaks",
            "release_authorized": True, "seal_verified": True,
            "order_id": "order-1", "athlete_id": "example_client",
            "generation_revision": 2, "model_seal": "seal-2",
            "release_manifest_digest": "release-2",
            "tp_manifest_sha256": "manifest-2",
            "apply_gate_url": "https://example.railway.app/api/fulfillment/order-1/apply-gate",
            "apply_gate_token": "short-lived-token",
            "approval": {"model_seal": "seal-2",
                         "release_manifest_digest": "release-2"},
        }
        value.update(overrides)
        return value

    @staticmethod
    def _check(**overrides):
        values = {
            "server": "https://example.railway.app", "token": "secret",
            "order_id": "order-1", "athlete_id": "example_client",
            "generation_revision": 2, "model_seal": "seal-2",
            "manifest_sha256": "manifest-2",
        }
        values.update(overrides)
        return tao.check_approval_gate(**values)

    def test_server_approved_passes(self, monkeypatch):
        monkeypatch.setattr(tao, "fetch_fulfillment_status",
                            lambda server, token, order_id: self._status())
        status = self._check()
        assert status["status"] == "APPROVED"

    def test_server_not_approved_refused(self, monkeypatch):
        monkeypatch.setattr(tao, "fetch_fulfillment_status",
                            lambda server, token, order_id: self._status(
                                status="GENERATED", release_authorized=False))
        with pytest.raises(tao.ApprovalGateError, match="not APPROVED"):
            self._check()

    def test_server_without_token_refused(self):
        with pytest.raises(tao.ApplyOrderError, match="token"):
            self._check(token="")

    def test_no_server_refused_without_bypass(self):
        with pytest.raises(tao.ApprovalGateError, match="local bypass is disabled"):
            self._check(server=None, token=None)

    @pytest.mark.parametrize("field,value", [
        ("legacy", True), ("generation_revision", 3),
        ("model_seal", "other"), ("tp_manifest_sha256", "other"),
        ("delivery_platform", "endure"),
    ])
    def test_binding_mismatch_refused(self, monkeypatch, field, value):
        monkeypatch.setattr(
            tao, "fetch_fulfillment_status",
            lambda server, token, order_id: self._status(**{field: value}),
        )
        with pytest.raises(tao.ApprovalGateError):
            self._check()


# ---------------------------------------------------------------------------
# CLI end-to-end (no network — job mode + local receipt validation only)
# ---------------------------------------------------------------------------

class TestMainJobMode:
    BINDING = ["--order-id", "order-1", "--generation-revision", "2",
               "--model-seal", "seal-2"]

    def test_missing_athlete_tp_id_still_hits_hard_disable(self, package_dir):
        rc = tao.main(["example_client", "--package", str(package_dir), *self.BINDING])
        assert rc == 3

    def test_no_server_exits_3_and_writes_no_job(self, package_dir):
        rc = tao.main(["example_client", "--package", str(package_dir),
                       "--athlete-tp-id", "2000302", *self.BINDING])
        assert rc == 3
        assert not (package_dir / "apply_job.json").exists()

    def test_approved_server_cannot_emit_job_or_runbook(
        self, package_dir, tmp_path, monkeypatch, capsys,
    ):
        def unexpected_status_call(*args, **kwargs):
            pytest.fail("disabled CLI must stop before requesting a capability")

        monkeypatch.setattr(tao, "fetch_fulfillment_status", unexpected_status_call)
        monkeypatch.setenv("CRON_SECRET", "secret")
        output_path = tmp_path / "apply_job.json"
        rc = tao.main([
            "example_client", "--package", str(package_dir),
            "--athlete-tp-id", "2000302",
            "--server", "https://example.railway.app",
            "--out", str(output_path), *self.BINDING,
        ])
        assert rc == 3
        assert not output_path.exists()
        captured = capsys.readouterr()
        assert tao.AUTOMATED_APPLY_DISABLED_MESSAGE in captured.err
        assert "OPERATOR RUNBOOK" not in captured.out + captured.err


class TestMainReceiptMode:
    BINDING = TestMainJobMode.BINDING
    def _write_receipt(self, tmp_path, **overrides):
        receipt = _ok_receipt(**overrides)
        path = tmp_path / "receipt.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path

    def test_valid_receipt_exits_0(self, package_dir, tmp_path, capsys):
        receipt_path = self._write_receipt(tmp_path)
        rc = tao.main(["example_client", "--package", str(package_dir),
                       "--receipt", str(receipt_path), *self.BINDING])
        assert rc == 3

    def test_invalid_receipt_exits_1(self, package_dir, tmp_path):
        receipt_path = self._write_receipt(tmp_path, finishedAt=None)
        rc = tao.main(["example_client", "--package", str(package_dir),
                       "--receipt", str(receipt_path), *self.BINDING])
        assert rc == 3

    def test_receipt_mode_posts_applied_transition_with_server(self, package_dir, tmp_path, monkeypatch):
        receipt_path = self._write_receipt(tmp_path)
        posted = {}

        digest = __import__('hashlib').sha256(
            (package_dir / tao.MANIFEST_FILENAME).read_bytes()).hexdigest()
        monkeypatch.setattr(tao, "fetch_fulfillment_status", lambda *args: {
            "status": "APPROVED", "legacy": False, "release_authorized": True,
            "seal_verified": True, "order_id": "order-1",
            "delivery_platform": "trainingpeaks",
            "athlete_id": "example_client", "generation_revision": 2,
            "model_seal": "seal-2", "release_manifest_digest": "release-2",
            "tp_manifest_sha256": digest,
            "apply_gate_url": "https://example.railway.app/api/fulfillment/order-1/apply-gate",
            "apply_gate_token": "short-lived-token",
            "approval": {"model_seal": "seal-2",
                         "release_manifest_digest": "release-2"},
        })

        def fake_post(server, token, order_id, coach, evidence):
            posted.update(server=server, token=token, order_id=order_id, coach=coach, evidence=evidence)
            return {"status": "APPLIED"}

        monkeypatch.setattr(tao, "post_applied_transition", fake_post)
        monkeypatch.setenv("CRON_SECRET", "secret-token")
        rc = tao.main(["example_client", "--package", str(package_dir), "--receipt", str(receipt_path),
                      "--server", "https://example.railway.app", "--coach", "coach_lee",
                      *self.BINDING])
        assert rc == 0
        assert posted["order_id"] == "order-1"
        assert posted["token"] == "secret-token"
        assert posted["coach"] == "coach_lee"
        assert posted["evidence"]["planId"] == 661259


def test_browser_driver_hard_exits_before_network_or_global_install():
    driver = Path(__file__).with_name('tp_apply_driver.js')
    script = "\n".join([
        "global.window = {};",
        "global.fetch = async function() { process.stdout.write('NETWORK'); };",
        f"require({json.dumps(str(driver))});",
        "process.stdout.write(window.applyJob ? 'INSTALLED' : 'NO_GLOBAL');",
    ])
    completed = subprocess.run(
        ['node', '-e', script], capture_output=True, text=True, timeout=10)
    assert completed.returncode != 0
    assert completed.stdout == ''
    assert tao.AUTOMATED_APPLY_DISABLED_MESSAGE in completed.stderr
