"""Deterministic Phase 3 replay retaining every Phase 1 negative gate."""

import json
import os
import sys
import zipfile
import re
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


@pytest.fixture(autouse=True)
def _isolate_webhook_module():
    yield
    sys.modules.pop("app", None)


def test_athlete_m_phase3_golden(monkeypatch, tmp_path):
    import app as webhook_app
    expected = _load("expected/phase3.json")
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
    assert profile["fitness_markers"]["ftp_watts"] is None
    assert profile["fitness_markers"]["power_basis"] == "none"
    assert profile["fitness_markers"]["control_metric"] == "hr"
    assert profile["target_race"]["distance_miles"] == 75
    golden_path = FIXTURE / 'expected' / 'plan_dates.yaml'
    if os.environ.get('GG_UPDATE_ATHLETE_M_GOLDEN') == '1':
        golden_path.write_text((source / 'plan_dates.yaml').read_text())
    assert plan_dates == yaml.safe_load(golden_path.read_text())
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
    assert fueling["fueling_basis"]["power_used"] is False
    assert not any("watt" in key.lower() for key in fueling["prescription"]["inputs"])
    assert not any(key in {"work_rate", "kilojoules", "kj"}
                   for key in map(str.lower, fueling["prescription"]["inputs"]))
    assert not re.search(r"\b\d+(?:\.\d+)?\s*kJ\b", json.dumps(fueling), re.I)
    assert not list((source / "workouts").glob("*.zwo"))
    contract = json.loads((source / "apply_contract.json").read_text())
    assert contract["contract_version"] == "apply_contract/v1"
    assert contract["model_seal"]
    assert all(op["kind"] != "threshold_update" for op in contract["operations"])
    for path in source.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".html", ".md"}:
            text = path.read_text(errors="replace")
            assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:W|watts?)\b", text, re.I), path

    monkeypatch.setattr(webhook_app, "CRON_SECRET", "fixture-secret")

    persisted = webhook_app.persist_deliverables(
        "test_athlete_m", "athlete-m", source_dir=source,
        delivery_platform="trainingpeaks",
    )
    state = persisted["state"]
    assert state["status"] == expected["status"]
    assert [{"id": i["id"], "waivable": i["waivable"]}
            for i in state["blocking_issues"]] == expected["blockers"]
    release_manifest = json.loads(
        (Path(persisted['revision_dir']) / 'release_manifest.json').read_text())
    sealed_paths = {item['path'] for item in release_manifest['artifacts']}
    assert {
        'artifacts/plan_ir.json', 'artifacts/tp_manifest.json',
        'artifacts/canonical_training_model.json', 'artifacts/apply_contract.json',
    } <= sealed_paths
    assert release_manifest['seal_version'] == 'canonical_model_apply_contract/v1'
    assert release_manifest['model_seal'] == contract['model_seal'] == state['model_seal']

    with zipfile.ZipFile(persisted["review_zip"]) as archive:
        assert not any(name.lower().endswith(".zwo") for name in archive.namelist())

    # The real intake assembler and post-render validator values survive
    # generation, persistence, sealing, session exchange, and page rendering.
    client = webhook_app.app.test_client()
    review_token = webhook_app._generate_review_token(
        "test_athlete_m", "coach@example.invalid")
    opened = client.post(
        "/review/test_athlete_m/session", data={"token": review_token})
    assert opened.status_code == 303
    rendered_review = client.get("/review/test_athlete_m")
    assert rendered_review.status_code == 200
    review_html = rendered_review.get_data(as_text=True)
    catalog = {item['item_id']: item for item in state['review_items']}
    assert 'FTP_ESTIMATED' not in review_html
    assert 'POWER_BASIS_NONE_CONFIRM' in review_html
    assert catalog['POWER_BASIS_NONE_CONFIRM']['value']['power_basis'] == 'none'
    assert 'SCHEDULE_MISMATCH_CONFIRM' in review_html
    for mismatch in catalog['SCHEDULE_MISMATCH_CONFIRM']['value'][
            'generated_mismatches']:
        assert mismatch in review_html

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
    response = client.get(
        "/api/download/test_athlete_m",
        query_string={"artifact": "customer_bundle"},
        headers={"Authorization": f"Bearer {customer_token}"},
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
            expected_revision=state['generation_revision'],
            expected_catalog_digest=state['review_catalog_digest'],
            review_decisions=[
                {
                    'item_id': item['item_id'],
                    'revision': state['generation_revision'],
                    'disposition': 'confirmed',
                }
                for item in state['review_items']
                if item['type'] in {'required_confirmation', 'verified_fact'}
            ],
            waiver={"rule_ids": [item["id"] for item in issues],
                    "reason": "fixture must remain blocked"},
        )


def test_facts_omitted_regeneration_never_rehydrates_catalog_facts(
    monkeypatch, tmp_path,
):
    """Production intake + package + shipping guide use athlete facts only."""
    import app as webhook_app

    intake = _load('intake.json')
    clock = _load('clock.json')
    intake['generation_clock'] = clock['generation_at']
    intake['course_facts_mode'] = 'athlete_only'

    snapshot = _load('race_snapshot.json')
    snapshot.update({
        'location': 'FORBIDDEN SNAPSHOT LOCATION',
        'discipline': 'road',
        'race_metadata': {'start_elevation_feet': 9876},
    })
    snapshot_path = tmp_path / 'race_snapshot.json'
    snapshot_path.write_text(json.dumps(snapshot))

    race_data_dir = tmp_path / 'race-data'
    race_data_dir.mkdir()
    (race_data_dir / 'three-course-race.json').write_text(json.dumps({
        'race': {
            'name': 'Three Course Race',
            'vitals': {
                'distance_mi': 191,
                'elevation_ft': 12345,
                'location': 'FORBIDDEN GUIDE LOCATION',
            },
            'terrain': {'primary': 'FORBIDDEN GUIDE TERRAIN'},
            'climate': {'summary': 'FORBIDDEN GUIDE CLIMATE'},
            'race_specific': {
                'surface_hazards': ['FORBIDDEN GUIDE HAZARD'],
            },
        },
    }))

    data_dir = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data_dir / 'deliveries'))
    monkeypatch.setattr(webhook_app, 'JOBS_DIR', str(data_dir / 'jobs'))
    monkeypatch.setattr(
        webhook_app, 'SCRIPTS_DIR', str(ROOT / 'athletes' / 'scripts'))
    monkeypatch.setenv('GG_FIXED_NOW', clock['generation_at'])
    monkeypatch.setenv('GG_RACE_SNAPSHOT_FIXTURE', str(snapshot_path))
    monkeypatch.setenv('GUIDE_GRAVEL_RACE_DATA_DIR', str(race_data_dir))

    result = webhook_app.run_pipeline(
        'athlete-m-facts-omitted', deliver=True, intake_data=intake,
        order_data={
            'order_id': 'test_athlete_m_facts_omitted',
            'delivery_platform': 'trainingpeaks',
            'order_created_at': clock['order_created_at'],
            'weeks_purchased': 7,
        },
    )
    assert result['success'], result.get('stderr') or result.get('stdout')
    source = Path(result['artifact_dir'])
    profile = yaml.safe_load((source / 'profile.yaml').read_text())
    target = profile['target_race']
    assert target['course_facts_omitted'] is True
    assert target['course_facts_mode'] == 'athlete_only'
    assert target['distance_miles'] == 75
    for field in (
        'location', 'discipline', 'elevation_ft', 'race_metadata',
        'courses', 'course_variant', 'category',
    ):
        assert field not in target

    guide = (source / 'training_guide.html').read_text()
    for forbidden in (
        'FORBIDDEN SNAPSHOT LOCATION', 'FORBIDDEN GUIDE LOCATION',
        'FORBIDDEN GUIDE TERRAIN', 'FORBIDDEN GUIDE CLIMATE',
        'FORBIDDEN GUIDE HAZARD', '12345', '191 miles',
    ):
        assert forbidden not in guide


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
