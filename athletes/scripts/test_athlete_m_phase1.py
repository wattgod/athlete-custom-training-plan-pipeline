"""Deterministic Phase 1 replay gate for the synthetic athlete-m contract."""

import json
import sys
import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))

from fulfillment_state import APPROVED, FulfillmentStateError, transition

FIXTURE = ROOT / "tests" / "fixtures" / "athlete_m"


def _load(name):
    return json.loads((FIXTURE / name).read_text())


def _plan_dates_golden(plan_dates):
    """Stable, lossless-enough calendar projection from production output."""
    return {
        "race_date": plan_dates["race_date"],
        "plan_weeks": plan_dates["plan_weeks"],
        "plan_start": plan_dates["plan_start"],
        "plan_end": plan_dates["plan_end"],
        "weeks": [
            {
                "week": week["week"],
                "phase": week["phase"],
                "start_date": week["days"][0]["date"],
                "end_date": week["days"][-1]["date"],
                "dates": [day["date"] for day in week["days"]],
                "race_days": [
                    day["date"] for day in week["days"]
                    if day.get("is_race_day")
                ],
            }
            for week in plan_dates["weeks"]
        ],
    }


@pytest.fixture(autouse=True)
def _isolate_webhook_module():
    yield
    sys.modules.pop("app", None)


def test_athlete_m_phase1_golden(monkeypatch, tmp_path):
    import app as webhook_app
    expected = _load("expected/phase1.json")
    intake = _load("intake.json")
    clock = _load("clock.json")
    intake["generation_clock"] = clock["generation_at"]

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
        "athlete-m", deliver=True, intake_data=intake,
        order_data={
            "order_id": "test_athlete_m",
            "delivery_platform": "trainingpeaks",
            "order_created_at": clock["order_created_at"],
            "weeks_purchased": 7,
        },
    )
    assert result["success"], result.get("stderr") or result.get("stdout")
    source = Path(result["artifact_dir"])
    profile = yaml.safe_load((source / "profile.yaml").read_text())
    fueling = yaml.safe_load((source / "fueling.yaml").read_text())
    plan_dates = yaml.safe_load((source / "plan_dates.yaml").read_text())
    plan_ir = json.loads((source / "plan_ir.json").read_text())
    state = webhook_app.load_fulfillment_state(
        source / "fulfillment_status.json")
    issues = state["blocking_issues"]
    confirmations = state["required_confirmations"]

    assert profile["devices"]["devices"] == expected["profile_devices"]
    assert profile["target_race"]["distance_miles"] == 75
    assert _plan_dates_golden(plan_dates) == _load("expected/plan_dates.json")
    sessions = [
        (week["number"], session)
        for week in plan_ir["weeks"] for session in week["sessions"]
    ]
    field_tests = [
        (week, session) for week, session in sessions
        if "field test" in session["title"].lower()
    ]
    assert [(week, session["title"]) for week, session in field_tests] == [
        (1, "HR Field Test")]
    race_week_counted = [
        session for week, session in sessions
        if week == 6 and session["tp_kind"] in {"bike", "race"}
    ]
    assert len(race_week_counted) >= 3
    assert any(
        session["date"] == "2026-09-19" and session["tp_kind"] == "race"
        for _, session in sessions
    )
    assert any(
        "vo2" in session["title"].lower()
        and date.fromisoformat(session["date"]).weekday() == 6
        for _, session in sessions
    )
    assert [i["id"] for i in issues] == [i["id"] for i in expected["blockers"]]
    assert [c["id"] for c in confirmations] == expected["required_confirmations"]
    assert not set(expected["absent_blockers"]) & {i["id"] for i in issues}
    labels = [item["week_label"] for item in fueling["gut_training"]["weekly_progression"]]
    assert labels == expected["fueling_week_labels"]

    monkeypatch.setattr(webhook_app, "CRON_SECRET", "fixture-secret")

    persisted = webhook_app.persist_deliverables(
        "test_athlete_m", "athlete-m", source_dir=source,
        delivery_platform="trainingpeaks",
    )
    state = persisted["state"]
    assert state["status"] == expected["status"]
    assert [{"id": i["id"], "waivable": i["waivable"]}
            for i in state["blocking_issues"]] == expected["blockers"]

    with zipfile.ZipFile(persisted["review_zip"]) as archive:
        assert not any(name.lower().endswith(".zwo") for name in archive.namelist())

    details = {
        "pipeline_success": True, "name": "Athlete M",
        "order_id": "test_athlete_m", "fulfillment_state": "available",
        "fulfillment_status": state["status"],
        "blocking_issues": state["blocking_issues"],
        "download_token": webhook_app._generate_download_token(
            "test_athlete_m", "review_bundle"),
    }
    _, email_text, email_html = webhook_app._build_training_plan_email(details)
    email = email_text + email_html
    for blocker in expected["blockers"]:
        assert blocker["id"] in email
    assert "non-waivable" in email and "waivable with reason" in email
    assert "import steps" not in email.lower()
    assert "/api/confirm/" not in email

    webhook_app.mark_order_processed("test_athlete_m", "athlete-m")
    customer_token = webhook_app._generate_download_token(
        "test_athlete_m", "customer_bundle")
    client = webhook_app.app.test_client()
    response = client.get(
        "/api/download/test_athlete_m",
        query_string={"artifact": "customer_bundle", "token": customer_token},
    )
    assert response.status_code == 409
    assert response.get_json() == {"error": "plan not released"}
    status = client.get("/api/order-status/test_athlete_m")
    assert status.status_code == 200
    assert status.get_json()["status"] == "processing"
    confirmed = client.post(
        "/api/confirm/test_athlete_m", headers={"X-Cron-Secret": "fixture-secret"})
    assert confirmed.status_code == 409

    with pytest.raises(FulfillmentStateError, match="non-waivable"):
        transition(
            Path(persisted["delivery_dir"]) / "fulfillment_status.json",
            APPROVED, "coach@example.invalid",
            waiver={"rule_ids": [item["id"] for item in issues],
                    "reason": "fixture must remain blocked"},
        )


def test_order_scoped_jobs_do_not_suppress_repeat_customer(monkeypatch, tmp_path):
    import app as webhook_app
    monkeypatch.setattr(webhook_app, "JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("SYNC_PIPELINE", "")
    monkeypatch.setattr(webhook_app, "_start_job_thread", lambda *args, **kwargs: None)
    first, _ = webhook_app._spawn_plan_job({
        "athlete_id": "same_slug", "order_id": "test_repeat_1", "profile": {},
    })
    second, _ = webhook_app._spawn_plan_job({
        "athlete_id": "same_slug", "order_id": "test_repeat_2", "profile": {},
    })
    assert first["order_id"] != second["order_id"]
    assert webhook_app._read_job("test_repeat_1")["status"] == "queued"
    assert webhook_app._read_job("test_repeat_2")["status"] == "queued"
    assert webhook_app._read_job("same_slug") is None


def test_lazy_v1_migration_lists_candidates_without_inference(monkeypatch, tmp_path):
    import app as webhook_app
    data_dir = tmp_path / "data"
    legacy = data_dir / "deliveries" / "repeat_rider" / "fulfillment_status.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({
        "schema_version": 1, "athlete_id": "repeat_rider",
        "generation_revision": 1, "status": "APPROVED",
        "blocking_issues": [], "approval": {"coach": "legacy"},
        "waiver": None, "application": None, "confirmation": None,
        "history": [], "updated_at": "2026-08-01T00:00:00Z",
    }))
    (data_dir / ".processed_orders.json").write_text(json.dumps({
        "test_candidate_1": {"athlete_id": "repeat_rider"},
        "test_candidate_2": {"athlete_id": "repeat_rider"},
    }))
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data_dir / "deliveries"))
    order_id = webhook_app._resolve_order_id("repeat_rider")
    assert order_id.startswith("legacy_")
    migrated = webhook_app.load_fulfillment_state(
        Path(webhook_app.DELIVERIES_DIR) / "orders" / order_id
        / "fulfillment_status.json")
    assert migrated["legacy"] is True
    assert migrated["legacy_binding"] is None
    assert migrated["legacy_candidates"] == ["test_candidate_1", "test_candidate_2"]
    assert migrated["blocking_issues"][0]["id"] == "STATE_UNAVAILABLE"
    assert json.loads(legacy.read_text())["schema_version"] == "tombstone/v1"
    monkeypatch.setenv("CRON_SECRET", "bind-secret")
    response = webhook_app.app.test_client().post(
        f"/api/fulfillment/{order_id}/bind-legacy",
        headers={"X-Cron-Secret": "bind-secret"},
        json={"ledger_order_id": "test_candidate_2",
              "coach": "coach@example.invalid"},
    )
    assert response.status_code == 200
    assert response.get_json()["legacy_binding"]["ledger_order_id"] == "test_candidate_2"


def test_pipeline_generation_roots_are_order_isolated(monkeypatch, tmp_path):
    import app as webhook_app
    roots = []

    def fake_run(*args, **kwargs):
        root = Path(kwargs["env"]["GG_ATHLETES_BASE_DIR"])
        roots.append(root)
        generated = root / "same-slug"
        generated.mkdir(parents=True)
        (generated / "fulfillment_status.json").write_text("{}")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(webhook_app, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(webhook_app, "SCRIPTS_DIR", str(ROOT / "athletes" / "scripts"))
    monkeypatch.setattr(webhook_app.subprocess, "run", fake_run)
    intake = {"name": "Same Slug", "email": "synthetic@example.invalid"}
    for order_id in ("test_concurrent_1", "test_concurrent_2"):
        result = webhook_app.run_pipeline(
            "same_slug", intake_data=intake,
            order_data={"order_id": order_id, "delivery_platform": "manual"},
        )
        assert result["success"] is True
        assert order_id in result["artifact_dir"]
    assert roots[0] != roots[1]
