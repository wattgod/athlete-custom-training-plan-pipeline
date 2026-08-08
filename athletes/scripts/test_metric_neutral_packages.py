"""Production-package regressions for every non-power control basis."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "athlete_m"
sys.path.insert(0, str(ROOT / "webhook"))

WATTS = re.compile(r"\b\d+(?:\.\d+)?\s*(?:W|watts?)\b", re.I)
FTP_TARGET = re.compile(r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%\s*FTP\b", re.I)

CASES = [
    ("lthr", "hr", "170", "190", "LTHR Field Test", "lthr", "lthr_field_test"),
    ("hrmax", "hr", "", "190", "HRmax Field Test", "hrmax", "hrmax_field_test"),
    ("rpe", "rpe", "", "", "RPE Field Test", "rpe", "rpe_field_test"),
]


@pytest.fixture(autouse=True)
def _fresh_webhook_module():
    yield
    sys.modules.pop("app", None)


def _assert_metric_neutral(label: str, text: str) -> None:
    assert not WATTS.search(text), f"watts leaked from {label}"
    assert not FTP_TARGET.search(text), f"%FTP leaked from {label}"


def _scan_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            suffix = Path(member.filename).suffix.lower()
            if suffix in {".html", ".md", ".json", ".yaml", ".yml", ".txt", ".zwo"}:
                _assert_metric_neutral(
                    f"{path.name}:{member.filename}",
                    archive.read(member).decode("utf-8", errors="replace"),
                )
            elif suffix == ".pdf" and shutil.which("pdftotext"):
                extracted = subprocess.run(
                    ["pdftotext", "-", "-"], input=archive.read(member),
                    capture_output=True, check=True,
                ).stdout.decode("utf-8", errors="replace")
                _assert_metric_neutral(f"{path.name}:{member.filename}", extracted)


@pytest.mark.parametrize(
    "case_id,metric,lthr,hrmax,field_test,basis,reanchor_test", CASES,
    ids=[case[0] for case in CASES],
)
def test_nonpower_paid_order_every_artifact_is_metric_neutral(
    monkeypatch, tmp_path, case_id, metric, lthr, hrmax, field_test, basis,
    reanchor_test,
):
    """The real webhook runner, package builder, seal, and both bundles agree."""
    import app as webhook_app

    intake = json.loads((FIXTURE / "intake.json").read_text())
    clock = json.loads((FIXTURE / "clock.json").read_text())
    intake.update({
        "name": f"Metric Neutral {case_id}",
        "email": f"metric-{case_id}@example.invalid",
        "powerOrHr": metric,
        "ftp": "",
        "hr_threshold": lthr,
        "hr_max": hrmax,
        "generation_clock": clock["generation_at"],
    })
    order_id = f"test_metric_neutral_{case_id}"
    data_dir = tmp_path / "data"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data_dir / "deliveries"))
    monkeypatch.setattr(webhook_app, "JOBS_DIR", str(data_dir / "jobs"))
    monkeypatch.setattr(
        webhook_app, "SCRIPTS_DIR", str(ROOT / "athletes" / "scripts"))
    monkeypatch.setenv("GG_FIXED_NOW", clock["generation_at"])
    monkeypatch.setenv(
        "GG_RACE_SNAPSHOT_FIXTURE", str(FIXTURE / "race_snapshot.json"))
    monkeypatch.setenv("CRON_SECRET", "fixture-secret")
    monkeypatch.setenv("DOWNLOAD_TOKEN_SECRET", "fixture-token-secret")

    result = webhook_app.run_pipeline(
        case_id, deliver=True, intake_data=intake,
        order_data={
            "order_id": order_id,
            "delivery_platform": "trainingpeaks",
            "order_created_at": clock["order_created_at"],
            "weeks_purchased": 7,
        },
    )
    assert result["success"], result.get("stderr") or result.get("stdout")
    source = Path(result["artifact_dir"])
    persisted = webhook_app.persist_deliverables(
        order_id, case_id, source_dir=source,
        delivery_platform="trainingpeaks",
    )
    revision = Path(persisted["revision_dir"])
    artifacts = revision / "artifacts"

    # These are the named athlete/review surfaces in the Phase 3 contract.
    for filename in (
        "training_guide.html", "plan_preview.html", "coaching_brief.md",
        "plan_summary.yaml",
    ):
        _assert_metric_neutral(filename, (artifacts / filename).read_text())
    _assert_metric_neutral(
        "release_manifest.json", (revision / "release_manifest.json").read_text())
    _scan_zip(Path(persisted["review_zip"]))
    _scan_zip(Path(persisted["customer_zip"]))

    canonical = json.loads((artifacts / "canonical_training_model.json").read_text())
    summary = yaml.safe_load((artifacts / "plan_summary.yaml").read_text())
    week_one_tests = [
        session for session in canonical["sessions"]
        if session.get("week") == 1 and "field test" in session["title"].lower()
    ]
    assert [session["title"] for session in week_one_tests] == [field_test]
    assert "RE-ANCHOR" in week_one_tests[0]["description"]
    assert canonical["athlete"]["control_basis"] == basis
    assert canonical["athlete"]["reanchor"] == {
        "required": True, "week": 1, "test": reanchor_test,
        "action": "Update the measured anchor after the Week 1 field test.",
    }
    assert summary["control"]["week_1_field_test"] == field_test
    assert summary["control"]["reanchor"] == canonical["athlete"]["reanchor"]
    assert not list((artifacts / "workouts").glob("*.zwo"))
