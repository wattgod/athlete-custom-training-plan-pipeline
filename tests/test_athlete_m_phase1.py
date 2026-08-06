"""Deterministic Phase 1 replay gate for the synthetic athlete-m contract."""

import json
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))

import intake_to_plan
from fulfillment_state import APPROVED, FulfillmentStateError, transition, write_generation
from post_render_validator import INPUT_VERSION, validate_transitional_input

FIXTURE = ROOT / "tests" / "fixtures" / "athlete_m"


def _load(name):
    return json.loads((FIXTURE / name).read_text())


def _race_info(snapshot):
    return {
        **snapshot,
        "source_urls": [],
        "source_type": "fixture",
        "event_year": 2026,
        "course_variant": None,
    }


@pytest.fixture(autouse=True)
def _isolate_webhook_module():
    yield
    sys.modules.pop("app", None)


def _replay_profile(monkeypatch, webhook_app):
    intake = _load("intake.json")
    clock = _load("clock.json")
    race = _load("race_snapshot.json")
    monkeypatch.setattr(
        intake_to_plan, "lookup_by_slug",
        lambda slug: (f"gravel:{slug}", _race_info(race)),
    )
    markdown = webhook_app._questionnaire_to_markdown(
        intake,
        fulfillment={
            "order_id": "test_athlete_m",
            "delivery_platform": "trainingpeaks",
            "order_created_at": clock["order_created_at"],
            "generation_at": clock["generation_at"],
            "weeks_purchased": 7,
            "athlete_timezone": clock["athlete_timezone"],
        },
    )
    assert "- Devices: power meter, hr strap" in markdown
    return intake_to_plan.build_profile(
        intake_to_plan.parse_intake_markdown(markdown))


def _rendered_replay(profile):
    plan_dates = _load("expected/plan_dates.json")
    weeks = []
    sessions = []
    for week in plan_dates["weeks"]:
        rendered = []
        for source in week["sessions"]:
            session = {
                **source,
                "display_name": source["title"],
                "duration_s": 3600,
                "total_time_planned": 1.0,
                "structure": None,
            }
            rendered.append(session)
            sessions.append(dict(session))
        weeks.append({
            "number": week["week"], "phase": week["phase"],
            "sessions": rendered,
        })
    labels = ["W00"] + [f"W{week}" for week in range(1, 7)]
    fueling = {
        "prescription": {"race_target_g_per_hour": 60},
        "gut_training": {"weekly_progression": [
            {"week_label": label} for label in labels
        ]},
    }
    document = {
        "input_version": INPUT_VERSION,
        "plan_ir": {
            "plan_ir_version": "0.1",
            "race_snapshot": {"date": plan_dates["race_date"]},
            "weeks": weeks,
        },
        "tp_manifest": {"version": 1, "sessions": sessions},
        "context": {
            "profile": profile,
            "fueling": fueling,
            "guide_html": '<div data-canonical-carb-target="60">60g/hr</div>',
            **_load("clock.json"),
            "weeks_purchased": 7,
        },
    }
    return document, fueling


def _intake_issues(profile):
    return [
        {"id": "COURSE_UNRESOLVED", "source": "intake", "severity": "CRITICAL",
         "message": profile["target_race"]["course_unresolved_reason"]},
        {"id": "FTP_ESTIMATED", "source": "intake", "severity": "CRITICAL",
         "message": "FTP was estimated; regenerate from a truthful control basis."},
        {"id": "RACE_STALE", "source": "intake", "severity": "CRITICAL",
         "message": profile["target_race"]["race_provenance_issue"]},
        {"id": "WEEKS_MISMATCH", "source": "intake", "severity": "CRITICAL",
         "message": "Generated 6 paid weeks but the order purchased 7; W00 excluded."},
    ]


def test_athlete_m_phase1_golden(monkeypatch, tmp_path):
    import app as webhook_app
    expected = _load("expected/phase1.json")
    profile = _replay_profile(monkeypatch, webhook_app)
    document, fueling = _rendered_replay(profile)
    validator_issues, confirmations = validate_transitional_input(document)
    issues = sorted(_intake_issues(profile) + validator_issues,
                    key=lambda item: item["id"])

    assert profile["devices"]["devices"] == expected["profile_devices"]
    assert [i["id"] for i in issues] == [i["id"] for i in expected["blockers"]]
    assert [c["id"] for c in confirmations] == expected["required_confirmations"]
    assert not set(expected["absent_blockers"]) & {i["id"] for i in issues}
    labels = [item["week_label"] for item in fueling["gut_training"]["weekly_progression"]]
    assert labels == expected["fueling_week_labels"]

    source = tmp_path / "generated" / "athlete-m"
    workouts = source / "workouts"
    workouts.mkdir(parents=True)
    (workouts / "W01_HR_Field_Test.zwo").write_text("<workout_file/>")
    (source / "profile.yaml").write_text(yaml.safe_dump(profile))
    (source / "fueling.yaml").write_text(yaml.safe_dump(fueling))
    (source / "plan_ir.json").write_text(json.dumps(document["plan_ir"]))
    (source / "tp_manifest.json").write_text(json.dumps(document["tp_manifest"]))
    (source / "training_guide.html").write_text(document["context"]["guide_html"])
    (source / "plan_preview.html").write_text("<h1>Review only</h1>")
    (source / "coaching_brief.md").write_text("# Synthetic review")
    (source / "plan_summary.yaml").write_text("plan_weeks: 6\n")
    state = write_generation(
        source / "fulfillment_status.json", "athlete-m", issues,
        order_id="test_athlete_m", delivery_platform="trainingpeaks",
        required_confirmations=confirmations,
    )

    data_dir = tmp_path / "data"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(data_dir / "deliveries"))
    monkeypatch.setattr(webhook_app, "JOBS_DIR", str(data_dir / "jobs"))
    monkeypatch.setattr(webhook_app, "CRON_SECRET", "fixture-secret")
    monkeypatch.setenv("CRON_SECRET", "fixture-secret")
    monkeypatch.setenv("DOWNLOAD_TOKEN_SECRET", "fixture-token-secret")

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
