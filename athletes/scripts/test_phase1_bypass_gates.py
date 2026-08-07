"""Regression tests for Phase 1's retired release/apply entry points."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))

import deliver_package
import email_delivery
from fulfillment_state import (APPROVED, BLOCKED_REVIEW,
                               FulfillmentStateError,
                               load as load_fulfillment_state, transition,
                               write_generation)
import tp_apply_order


def _persistable_source(tmp_path, *, order_id, platform='trainingpeaks'):
    source = tmp_path / f'source-{order_id}'
    (source / 'workouts').mkdir(parents=True)
    for relative, content in {
        'workouts/W01.zwo': 'sealed workout',
        'training_guide.html': 'sealed guide',
        'plan_preview.html': 'review',
        'coaching_brief.md': 'brief',
        'personal_email.md': '**Subject:** Ready\n\nSealed body',
        'plan_summary.yaml': 'plan_weeks: 1\n',
        'fueling.yaml': '{}\n',
        'plan_ir.json': '{}\n',
        'tp_manifest.json': '{}\n',
    }.items():
        (source / relative).write_text(content)
    write_generation(
        source / 'fulfillment_status.json', 'athlete-m',
        order_id=order_id, delivery_platform=platform,
    )
    return source


def test_legacy_package_delivery_refuses_before_writing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        deliver_package.config, "get_path",
        lambda key: tmp_path / key.replace("_dir", ""),
    )

    result = deliver_package.deliver_package("legacy-athlete")

    assert result["success"] is False
    assert "seal-bound APPROVED order" in result["error"]
    assert list(tmp_path.iterdir()) == []


def test_legacy_email_delivery_refuses_before_loading_athlete():
    success, message = email_delivery.send_training_package(
        "legacy-athlete", "athlete@example.invalid")

    assert success is False
    assert "seal-bound APPROVED order" in message


def test_webhook_no_intake_path_never_spawns_legacy_pipeline(monkeypatch):
    import app as webhook_app

    spawned = []
    monkeypatch.setattr(
        webhook_app.subprocess, "run",
        lambda *args, **kwargs: spawned.append((args, kwargs)),
    )

    result = webhook_app.run_pipeline(
        "legacy-athlete", deliver=True, intake_data=None,
        order_data={"order_id": "test_no_intake"},
    )

    assert result["success"] is False
    assert result["fulfillment_state"] == "unavailable"
    assert "No intake was attached" in result["stderr"]
    assert spawned == []


def test_persistence_refuses_same_revision_replacement_after_seal(
    monkeypatch, tmp_path,
):
    import app as webhook_app

    source = tmp_path / "source"
    (source / "workouts").mkdir(parents=True)
    (source / "workouts" / "W01.zwo").write_text("sealed workout")
    (source / "training_guide.html").write_text("sealed guide")
    (source / "plan_preview.html").write_text("review")
    (source / "coaching_brief.md").write_text("brief")
    (source / "plan_summary.yaml").write_text("plan_weeks: 1\n")
    (source / "fueling.yaml").write_text("{}\n")
    (source / "tp_manifest.json").write_text("{}\n")
    write_generation(
        source / "fulfillment_status.json", "athlete-m",
        order_id="test_immutable", delivery_platform="trainingpeaks",
    )
    data_dir = tmp_path / "data"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(
        webhook_app, "DELIVERIES_DIR", str(data_dir / "deliveries"))

    first = webhook_app.persist_deliverables(
        "test_immutable", "athlete-m", source_dir=source,
        delivery_platform="trainingpeaks",
    )
    sealed_workout = Path(first["revision_dir"]) / "artifacts/workouts/W01.zwo"
    assert sealed_workout.read_text() == "sealed workout"
    (source / "workouts" / "W01.zwo").write_text("same revision mutation")

    with pytest.raises(FulfillmentStateError, match="write_generation"):
        webhook_app.persist_deliverables(
            "test_immutable", "athlete-m", source_dir=source,
            delivery_platform="trainingpeaks",
        )

    assert sealed_workout.read_text() == "sealed workout"


def test_download_seal_mismatch_revokes_authority_and_persists_blocker(
    monkeypatch, tmp_path,
):
    import app as webhook_app

    source = tmp_path / "source"
    (source / "workouts").mkdir(parents=True)
    for relative, content in {
        "workouts/W01.zwo": "sealed workout",
        "training_guide.html": "sealed guide",
        "plan_preview.html": "review",
        "coaching_brief.md": "brief",
        "plan_summary.yaml": "plan_weeks: 1\n",
        "fueling.yaml": "{}\n",
        "tp_manifest.json": "{}\n",
    }.items():
        (source / relative).write_text(content)
    write_generation(
        source / "fulfillment_status.json", "athlete-m",
        order_id="test_download_mismatch", delivery_platform="trainingpeaks",
    )
    data_dir = tmp_path / "data"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(
        webhook_app, "DELIVERIES_DIR", str(data_dir / "deliveries"))
    monkeypatch.setenv("DOWNLOAD_TOKEN_SECRET", "test-token-secret")

    persisted = webhook_app.persist_deliverables(
        "test_download_mismatch", "athlete-m", source_dir=source,
        delivery_platform="trainingpeaks",
    )
    state_path = Path(persisted["delivery_dir"]) / "fulfillment_status.json"
    transition(state_path, APPROVED, "coach@example.invalid")
    token = webhook_app._generate_download_token(
        "test_download_mismatch", "customer_bundle")
    Path(persisted["customer_zip"]).write_bytes(b"post-approval mutation")

    response = webhook_app.app.test_client().get(
        "/api/download/test_download_mismatch",
        query_string={"artifact": "customer_bundle", "token": token},
    )

    assert response.status_code == 409
    state = load_fulfillment_state(state_path)
    assert state["status"] == BLOCKED_REVIEW
    mismatch = next(item for item in state["blocking_issues"]
                    if item["id"] == "SEAL_MISMATCH")
    assert mismatch["waivable"] is False


def test_live_apply_gate_revokes_emitted_job_after_regeneration(monkeypatch, tmp_path):
    """A real server-issued browser job dies if the order regenerates."""
    import app as webhook_app

    data_dir = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data_dir / 'deliveries'))
    monkeypatch.setenv('CRON_SECRET', 'ops-secret')
    source = _persistable_source(tmp_path, order_id='test_live_gate')
    persisted = webhook_app.persist_deliverables(
        'test_live_gate', 'athlete-m', source_dir=source,
        delivery_platform='trainingpeaks')
    state_path = Path(persisted['delivery_dir']) / 'fulfillment_status.json'
    transition(state_path, APPROVED, 'coach@example.invalid')

    client = webhook_app.app.test_client()
    status_response = client.get(
        '/api/fulfillment/test_live_gate/status',
        headers={'X-Cron-Secret': 'ops-secret'})
    assert status_response.status_code == 200
    status = status_response.get_json()
    job = tp_apply_order.build_apply_job(
        {'plan_title': 'Bound plan', 'sessions': [{
            'date': '2026-08-07', 'title': 'Ride', 'tp_kind': 'bike',
        }], 'expected': {
            'bike': 1, 'strength': 0, 'day_off': 0, 'race': 0, 'total': 1,
        }},
        athlete_tp_id='123', target_date='2026-08-07', start_type=1,
        binding={
            **{key: status[key] for key in (
                'order_id', 'athlete_id', 'delivery_platform',
                'generation_revision', 'model_seal',
                'release_manifest_digest', 'tp_manifest_sha256',
            )},
            'apply_gate_url': status['apply_gate_url'],
            'apply_gate_token': status['apply_gate_token'],
        },
    )
    assert job['order_id'] == 'test_live_gate'

    write_generation(
        state_path, 'athlete-m', order_id='test_live_gate',
        delivery_platform='trainingpeaks')
    revoked = client.get(
        '/api/fulfillment/test_live_gate/apply-gate',
        query_string={'token': job['gate']['token']},
        headers={'Origin': 'https://app.trainingpeaks.com'})
    assert revoked.status_code == 409
    assert 'not APPROVED' in revoked.get_json()['error']
    assert revoked.headers['Access-Control-Allow-Origin'] == 'https://app.trainingpeaks.com'


def test_live_apply_gate_materializes_post_emission_seal_mismatch(
    monkeypatch, tmp_path,
):
    import app as webhook_app

    data_dir = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data_dir / 'deliveries'))
    monkeypatch.setenv('CRON_SECRET', 'ops-secret')
    source = _persistable_source(tmp_path, order_id='test_live_gate_seal')
    persisted = webhook_app.persist_deliverables(
        'test_live_gate_seal', 'athlete-m', source_dir=source,
        delivery_platform='trainingpeaks')
    state_path = Path(persisted['delivery_dir']) / 'fulfillment_status.json'
    transition(state_path, APPROVED, 'coach@example.invalid')
    client = webhook_app.app.test_client()
    status = client.get(
        '/api/fulfillment/test_live_gate_seal/status',
        headers={'X-Cron-Secret': 'ops-secret'}).get_json()

    (Path(persisted['revision_dir']) / 'artifacts/tp_manifest.json').write_text(
        '{"post_approval":"mutation"}')
    refused = client.get(
        '/api/fulfillment/test_live_gate_seal/apply-gate',
        query_string={'token': status['apply_gate_token']},
        headers={'Origin': 'https://app.trainingpeaks.com'})

    assert refused.status_code == 409
    assert 'seal verification failed' in refused.get_json()['error']
    state = load_fulfillment_state(state_path)
    assert state['status'] == BLOCKED_REVIEW
    assert next(item for item in state['blocking_issues']
                if item['id'] == 'SEAL_MISMATCH')['waivable'] is False


def test_production_apply_gate_rejects_cross_platform_order(monkeypatch, tmp_path):
    import app as webhook_app

    data_dir = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data_dir / 'deliveries'))
    monkeypatch.setenv('CRON_SECRET', 'ops-secret')
    source = _persistable_source(
        tmp_path, order_id='test_endure_gate', platform='endure')
    persisted = webhook_app.persist_deliverables(
        'test_endure_gate', 'athlete-m', source_dir=source,
        delivery_platform='endure')
    state_path = Path(persisted['delivery_dir']) / 'fulfillment_status.json'
    transition(state_path, APPROVED, 'coach@example.invalid')

    response = webhook_app.app.test_client().get(
        '/api/fulfillment/test_endure_gate/status',
        headers={'X-Cron-Secret': 'ops-secret'})
    assert response.status_code == 200
    status = response.get_json()
    assert status['delivery_platform'] == 'endure'
    assert 'apply_gate_token' not in status
    with pytest.raises(FulfillmentStateError, match='immutable delivery_platform'):
        transition(
            state_path, 'APPLIED', 'coach@example.invalid',
            platform='trainingpeaks', evidence='must never land')


@pytest.mark.parametrize('mutated_artifact', [
    'personal_email.md', 'training_guide.html',
])
def test_confirm_route_refuses_mutated_sealed_bytes(
    monkeypatch, tmp_path, mutated_artifact,
):
    """The real customer-send route materializes SEAL_MISMATCH before send."""
    import app as webhook_app

    data_dir = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data_dir / 'deliveries'))
    monkeypatch.setenv('CRON_SECRET', 'ops-secret')
    source = _persistable_source(tmp_path, order_id='test_confirm_seal')
    persisted = webhook_app.persist_deliverables(
        'test_confirm_seal', 'athlete-m', source_dir=source,
        delivery_platform='trainingpeaks')
    state_path = Path(persisted['delivery_dir']) / 'fulfillment_status.json'
    transition(state_path, APPROVED, 'coach@example.invalid')
    transition(
        state_path, 'APPLIED', 'coach@example.invalid',
        platform='trainingpeaks', evidence='verified receipt')

    log_dir = data_dir / '.logs'
    log_dir.mkdir(parents=True)
    (log_dir / '2026-08.jsonl').write_text(json.dumps({
        'order_id': 'test_confirm_seal', 'success': True,
        'email': 'athlete@example.invalid', 'name': 'Athlete M',
    }) + '\n')
    artifact = (Path(persisted['revision_dir']) / 'artifacts'
                / mutated_artifact)
    artifact.write_bytes(b'post-approval mutation')

    with patch.object(webhook_app, '_send_email') as send:
        response = webhook_app.app.test_client().post(
            '/api/confirm/test_confirm_seal',
            headers={'X-Cron-Secret': 'ops-secret'})

    assert response.status_code == 409
    assert response.get_json()['error'] == 'Release seal verification failed'
    send.assert_not_called()
    state = load_fulfillment_state(state_path)
    assert state['status'] == BLOCKED_REVIEW
    mismatch = next(
        item for item in state['blocking_issues']
        if item['id'] == 'SEAL_MISMATCH')
    assert mismatch['waivable'] is False


def test_startup_migrates_shadowed_v1_and_quarantine_has_no_authority(
    monkeypatch, tmp_path,
):
    import app as webhook_app

    data_dir = tmp_path / "data"
    deliveries = data_dir / "deliveries"
    monkeypatch.setattr(webhook_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(webhook_app, "DELIVERIES_DIR", str(deliveries))
    monkeypatch.setenv("CRON_SECRET", "ops-secret")

    # A newer v2 lookup already exists for this repeat customer.
    current_path = deliveries / "orders/current-order/fulfillment_status.json"
    write_generation(
        current_path, "repeat-rider", order_id="current-order",
        delivery_platform="trainingpeaks",
    )
    webhook_app._record_order_lookup("current-order", "repeat-rider")

    legacy_path = deliveries / "repeat-rider/fulfillment_status.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps({
        "schema_version": 1, "athlete_id": "repeat-rider",
        "generation_revision": 1, "status": "APPLIED",
        "blocking_issues": [], "approval": {"coach": "legacy"},
        "waiver": None, "application": {"legacy": True},
        "confirmation": None, "history": [],
        "updated_at": "2026-08-01T00:00:00Z",
    }))

    stats = webhook_app.migrate_all_v1_states()
    assert stats["migrated"] == 1
    lookup = json.loads(webhook_app._order_lookup_path("repeat-rider").read_text())
    assert len(lookup["order_ids"]) == 2
    legacy_order = next(item for item in lookup["order_ids"]
                        if item != "current-order")
    assert webhook_app._resolve_order_id("repeat-rider") is None

    client = webhook_app.app.test_client()
    status = client.get(
        f"/api/fulfillment/{legacy_order}/status",
        headers={"X-Cron-Secret": "ops-secret"},
    )
    assert status.status_code == 200
    assert status.get_json()["status"] == "APPLIED"  # evidence preserved
    assert status.get_json()["legacy"] is True
    assert status.get_json()["release_authorized"] is False

    confirmation = client.post(
        f"/api/confirm/{legacy_order}",
        headers={"X-Cron-Secret": "ops-secret"},
    )
    assert confirmation.status_code == 409
    assert "quarantined" in confirmation.get_json()["error"]
