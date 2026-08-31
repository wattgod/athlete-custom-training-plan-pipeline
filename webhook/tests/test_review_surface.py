"""Production-route regression tests for the Phase 2 coach review page."""

import html
import hashlib
import hmac
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('FLASK_ENV', 'test')
os.environ.setdefault('STRIPE_SECRET_KEY', '')

import app as webhook_app
from fulfillment_state import (APPROVED, BLOCKED_REVIEW, GENERATED,
                               approval_matches_release,
                               finalize_transitional_release, load,
                               merge_generation_blockers,
                               review_catalog_digest,
                               set_generation_blockers, write_generation)
from download_tokens import (DownloadTokenError, MAX_REVIEW_BUNDLE_TTL_SECONDS,
                             verify_download_token)
from review_auth import verify_review_token
from d2_identity import (THRESHOLD_ITEM_ID, record_account_inspection,
                         record_identity_result, resolve_d2_item)
from endure_approval_bridge import request_message


ATHLETE_M = (Path(__file__).resolve().parents[2] / 'tests' / 'fixtures'
             / 'athlete_m')


@pytest.fixture
def review_client(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data))
    monkeypatch.setattr(webhook_app, 'DELIVERIES_DIR', str(data / 'deliveries'))
    monkeypatch.setenv('DOWNLOAD_TOKEN_SECRET', 'phase2-page-test-secret')
    monkeypatch.delenv('DOWNLOAD_TOKEN_KEYS', raising=False)
    monkeypatch.delenv('REVIEW_TOKEN_KEYS', raising=False)
    monkeypatch.delenv('REVIEW_TOKEN_SECRET', raising=False)
    webhook_app.app.config['TESTING'] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client()


def _issue(rule_id, *, value=None):
    return {
        'id': rule_id, 'source': 'fixture', 'severity': 'CRITICAL',
        'message': f'{rule_id} fixture finding',
        'review_value': value if value is not None else {'rule': rule_id},
        'basis': 'de-identified Phase 2 route fixture',
        'sensitivity': 'internal',
    }


def _confirmation(item_id='SCHEDULE_MISMATCH_CONFIRM', *, value=None):
    return {
        'id': item_id, 'source': 'fixture',
        'message': f'{item_id} fixture confirmation',
        'review_value': value if value is not None else {'item': item_id},
        'basis': 'athlete availability compared with generated schedule',
        'sensitivity': 'personal',
    }


def _seed_order(
    order_id, *, athlete_id='athlete-m', blockers=None, confirmations=None,
):
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, athlete_id, blockers or [], order_id=order_id,
        delivery_platform='trainingpeaks',
        required_confirmations=confirmations or [],
    )
    state = record_identity_result(
        state_path, state['generation_revision'], {
            'outcome': 'bound',
            'tp_athlete_id': f'fixture-{order_id}',
            'candidates': [],
        }, capability_jti=f'binding-{order_id}-jti')
    revision = (webhook_app._order_dir(order_id) / 'revisions'
                / f"r{state['generation_revision']}")
    revision.mkdir(parents=True)
    (revision / 'reviewed-values.txt').write_text('sealed review source')
    review_zip = revision / f'{order_id}-review-bundle.zip'
    with zipfile.ZipFile(review_zip, 'w') as archive:
        archive.writestr('plan_preview.txt', 'non-executable review preview')
    state = finalize_transitional_release(
        state_path, revision, expected_revision=state['generation_revision'])
    webhook_app._record_order_lookup(order_id, athlete_id)
    return state, state_path, revision


def _login(client, order_id, *, expected_secret='athlete-m'):
    token = webhook_app._generate_review_token(
        order_id, 'coach@example.invalid')
    # GET is scanner-safe and leaks no state before the fragment exchange.
    shell = client.get(f'/review/{order_id}')
    assert shell.status_code == 200
    assert expected_secret not in shell.get_data(as_text=True)
    assert shell.headers['Cache-Control'].startswith('no-store')
    assert shell.headers['Referrer-Policy'] == 'no-referrer'

    opened = client.post(
        f'/review/{order_id}/session', data={'token': token})
    assert opened.status_code == 303
    assert opened.headers['Location'] == f'/review/{order_id}'
    assert 'HttpOnly' in opened.headers['Set-Cookie']
    assert 'SameSite=Strict' in opened.headers['Set-Cookie']

    page = client.get(f'/review/{order_id}')
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', body)
    assert csrf, body
    return body, html.unescape(csrf.group(1))


def _confirmed_ids(state):
    return [
        item['item_id'] for item in state['review_items']
        if item['type'] in {'required_confirmation', 'verified_fact'}
    ]


def _approval_form(state, csrf, *, confirm_ids=None, waived_ids=None, reason=''):
    return {
        'csrf_token': csrf,
        'generation_revision': str(state['generation_revision']),
        'review_catalog_digest': state['review_catalog_digest'],
        'confirm_item': (_confirmed_ids(state) if confirm_ids is None else confirm_ids),
        'waive_item': waived_ids or [],
        'waiver_reason': reason,
    }


def _rewrite_catalog_item(state_path, collection, item_id, *, message, value):
    """Simulate an old/compromised same-revision writer bypassing mutators."""
    raw = json.loads(state_path.read_text())
    source = next(item for item in raw[collection] if item['id'] == item_id)
    source['message'] = message
    source['review_value'] = value
    rendered = next(
        item for item in raw['review_items'] if item['item_id'] == item_id)
    rendered['message'] = message
    rendered['value'] = value
    rendered['value_type'] = (
        'object' if isinstance(value, dict) else 'string'
    )
    raw['review_catalog_digest'] = review_catalog_digest(raw['review_items'])
    state_path.write_text(json.dumps(raw))


def test_d2_identity_panel_and_resolution_selector_execute_state_command(
    review_client, tmp_path, monkeypatch,
):
    order_id = 'test_phase4_d2_surface'
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, 'athlete-m', order_id=order_id,
        delivery_platform='trainingpeaks')
    state = record_identity_result(
        state_path, state['generation_revision'], {
            'outcome': 'bound', 'tp_athlete_id': 'fixture-athlete-m',
            'candidates': [],
        }, capability_jti='surface-probe-jti-00000001')
    probes = json.loads((ATHLETE_M / 'worker_probes.json').read_text())
    probes['tp_athlete_id'] = 'fixture-athlete-m'
    state = record_account_inspection(
        state_path, state['generation_revision'], probes,
        intake_age=45, intake_thresholds={'lthr': None},
        control_metric='hr', canonical_control_value=None,
        capability_jti='surface-inspect-jti-000001',
        observed_at='2026-08-06T15:00:00Z')
    revision = (webhook_app._order_dir(order_id) / 'revisions'
                / f"r{state['generation_revision']}")
    revision.mkdir(parents=True)
    (revision / 'reviewed-values.txt').write_text('sealed d2 review source')
    with zipfile.ZipFile(revision / f'{order_id}-review-bundle.zip', 'w') as archive:
        archive.writestr('plan_preview.txt', 'phase4 d2 preview')
    state = finalize_transitional_release(
        state_path, revision, expected_revision=state['generation_revision'])
    webhook_app._record_order_lookup(order_id, 'athlete-m')

    body, csrf = _login(review_client, order_id)
    assert '<h2>TrainingPeaks delivery</h2>' in body
    assert '<dd>bound</dd>' in body
    assert 'fixture-athlete-m' in body
    assert THRESHOLD_ITEM_ID in body
    assert 'Resolution command' in body
    assert 'use-tp-value' in body
    assert f'/review/{order_id}/d2/resolve' in body

    monkeypatch.setattr(
        webhook_app, '_queue_d2_regeneration', lambda *_args, **_kwargs: None)
    response = review_client.post(
        f'/review/{order_id}/d2/resolve', data={
            'csrf_token': csrf,
            'generation_revision': str(state['generation_revision']),
            'resolution_item': THRESHOLD_ITEM_ID,
            f'resolution_choice:{THRESHOLD_ITEM_ID}': 'use-tp-value',
        })
    assert response.status_code == 303
    changed = load(state_path)
    assert changed['generation_revision'] == state['generation_revision'] + 1
    assert changed['canonical_input_overrides']['hr_threshold'] == 148
    assert changed['regeneration_request']


def test_d2_regeneration_queue_applies_canonical_overrides_and_installs_intent_first(
    tmp_path, monkeypatch,
):
    data = tmp_path / 'data'
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(data))
    monkeypatch.setattr(webhook_app, '_read_job', lambda _order_id: {
        'order_id': 'queue-d2', 'athlete_id': 'athlete-m',
        'intake_id': 'intake-d2',
        'order_data': {'order_id': 'queue-d2', 'athlete_id': 'athlete-m'},
    })
    monkeypatch.setattr(webhook_app, 'load_intake', lambda _intake_id: {
        'age': 45, 'hr_threshold': '', 'race_name': 'Fixture Race',
    })
    spawned = []
    monkeypatch.setattr(
        webhook_app, '_spawn_plan_job',
        lambda order_data, **kwargs: spawned.append((order_data, kwargs)))
    state = {
        'order_id': 'queue-d2', 'athlete_id': 'athlete-m',
        'generation_revision': 2,
        'canonical_input_overrides': {'hr_threshold': 148},
        'regeneration_request': {'prior_revision': 1, 'reason': 'use TP LTHR'},
    }
    webhook_app._queue_d2_regeneration('queue-d2', state)
    installed = json.loads((
        data / 'order-work' / 'queue-d2' / 'athletes' / 'athlete-m'
        / 'fulfillment_status.json').read_text())
    assert installed == state
    assert spawned[0][1]['intake_data']['hr_threshold'] == 148
    assert spawned[0][1]['intake_data']['age'] == 45
    assert spawned[0][0]['order_id'] == 'queue-d2'


def test_approval_route_rejects_client_resolution_mismatch_and_snapshots_command(
    review_client,
):
    order_id = 'test_phase4_authoritative_resolution_snapshot'
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, 'athlete-m', order_id=order_id,
        delivery_platform='trainingpeaks')
    state = record_identity_result(
        state_path, state['generation_revision'], {
            'outcome': 'bound', 'tp_athlete_id': 'fixture-athlete-m',
            'candidates': [],
        }, capability_jti='approval-route-probe-jti-001')
    probes = json.loads((ATHLETE_M / 'worker_probes.json').read_text())
    probes['tp_athlete_id'] = 'fixture-athlete-m'
    state = record_account_inspection(
        state_path, state['generation_revision'], probes,
        intake_age=19, intake_thresholds={'lthr': 160},
        control_metric='hr', canonical_control_value=160,
        capability_jti='approval-route-inspect-jti-01',
        observed_at='2026-08-06T15:00:00Z')
    state = resolve_d2_item(
        state_path, state['generation_revision'], THRESHOLD_ITEM_ID,
        'update-from-intake', actor='review-link:test')
    state = write_generation(
        state_path, state['athlete_id'], order_id=state['order_id'],
        delivery_platform=state['delivery_platform'])
    revision = (webhook_app._order_dir(order_id) / 'revisions'
                / f"r{state['generation_revision']}")
    revision.mkdir(parents=True)
    (revision / 'reviewed-values.txt').write_text(
        'sealed authoritative D2 resolution')
    state = finalize_transitional_release(
        state_path, revision, expected_revision=state['generation_revision'])
    webhook_app._record_order_lookup(order_id, 'athlete-m')

    _body, csrf = _login(review_client, order_id)
    confirm_ids = [
        item_id for item_id in _confirmed_ids(state)
        if item_id != THRESHOLD_ITEM_ID
    ]
    mismatched_form = _approval_form(
        state, csrf, confirm_ids=confirm_ids)
    mismatched_form['resolved_item'] = [
        f'{THRESHOLD_ITEM_ID}::use-tp-value']
    rejected = review_client.post(
        f'/review/{order_id}/approve', data=mismatched_form)
    assert rejected.status_code == 409
    assert ('does not match the authoritative command'
            in rejected.get_data(as_text=True))
    assert load(state_path)['approval'] is None

    honest_form = _approval_form(state, csrf, confirm_ids=confirm_ids)
    honest_form['resolved_item'] = [
        f'{THRESHOLD_ITEM_ID}::update-from-intake']
    approved = review_client.post(
        f'/review/{order_id}/approve', data=honest_form)
    assert approved.status_code == 303
    persisted = load(state_path)
    snapshot = next(
        item for item in persisted['approval']['confirmations']
        if item['item_id'] == THRESHOLD_ITEM_ID)
    authoritative_choice = persisted['d2_resolutions'][THRESHOLD_ITEM_ID]['choice']
    assert authoritative_choice == 'update-from-intake'
    assert snapshot['disposition'] == f'resolved:{authoritative_choice}'
    assert snapshot['resolved_resolution'] == authoritative_choice
    assert persisted['d2_apply_operations']['lthr']['payload'] == {
        'metric': 'lthr', 'after_value': 160, 'unit': 'bpm',
    }


def test_manual_correction_route_uses_verified_worker_readback_and_then_approves(
    review_client, tmp_path, monkeypatch,
):
    order_id = 'test_phase4_manual_readback_surface'
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, 'athlete-m', order_id=order_id,
        delivery_platform='trainingpeaks')
    state = record_identity_result(
        state_path, state['generation_revision'], {
            'outcome': 'bound', 'tp_athlete_id': 'fixture-athlete-m',
            'candidates': [],
        }, capability_jti='surface-manual-probe-jti-001')
    probes = json.loads((ATHLETE_M / 'worker_probes.json').read_text())
    probes['tp_athlete_id'] = 'fixture-athlete-m'
    state = record_account_inspection(
        state_path, state['generation_revision'], probes,
        intake_age=19, intake_thresholds={'lthr': 155},
        control_metric='hr', canonical_control_value=155,
        capability_jti='surface-manual-inspect-jti-01',
        observed_at='2026-08-06T15:00:00Z')
    revision = (webhook_app._order_dir(order_id) / 'revisions'
                / f"r{state['generation_revision']}")
    revision.mkdir(parents=True)
    (revision / 'reviewed-values.txt').write_text('sealed manual correction review')
    state = finalize_transitional_release(
        state_path, revision, expected_revision=state['generation_revision'])
    webhook_app._record_order_lookup(order_id, 'athlete-m')

    worker_fixture = tmp_path / 'manual-worker-probes.json'
    wrong = {**probes, 'lthr_bpm': 154}
    worker_fixture.write_text(json.dumps(wrong))
    monkeypatch.setenv('GG_WORKER_PROBES_FIXTURE', str(worker_fixture))
    monkeypatch.setenv(
        'GG_WORKER_CAPABILITY_SECRET',
        'phase4-surface-worker-capability-secret-0001')
    monkeypatch.setenv('GG_WORKER_REPLAY_DIR', str(tmp_path / 'worker-replay'))

    _body, csrf = _login(review_client, order_id)
    selected = review_client.post(
        f'/review/{order_id}/d2/resolve', data={
            'csrf_token': csrf,
            'generation_revision': str(state['generation_revision']),
            'resolution_item': THRESHOLD_ITEM_ID,
            f'resolution_choice:{THRESHOLD_ITEM_ID}': 'manually-corrected',
        })
    assert selected.status_code == 303
    pending = load(state_path)
    assert pending['model_seal'] == state['model_seal']
    page = review_client.get(f'/review/{order_id}').get_data(as_text=True)
    assert 'Run worker readback' in page
    assert f'/review/{order_id}/d2/readback' in page

    bad_csrf = review_client.post(
        f'/review/{order_id}/d2/readback', data={
            'csrf_token': 'wrong',
            'generation_revision': str(pending['generation_revision']),
            'readback_item': THRESHOLD_ITEM_ID,
        })
    assert bad_csrf.status_code == 403
    wrong_readback = review_client.post(
        f'/review/{order_id}/d2/readback', data={
            'csrf_token': csrf,
            'generation_revision': str(pending['generation_revision']),
            'readback_item': THRESHOLD_ITEM_ID,
        })
    assert wrong_readback.status_code == 409
    assert THRESHOLD_ITEM_ID in load(state_path)['d2_pending_requirements']

    worker_fixture.write_text(json.dumps({**probes, 'lthr_bpm': 155}))
    exact_readback = review_client.post(
        f'/review/{order_id}/d2/readback', data={
            'csrf_token': csrf,
            'generation_revision': str(pending['generation_revision']),
            'readback_item': THRESHOLD_ITEM_ID,
        })
    assert exact_readback.status_code == 303
    confirmed = load(state_path)
    evidence = confirmed['d2_resolutions'][THRESHOLD_ITEM_ID]['readback_evidence']
    assert evidence['record_type'] == 'd2_worker_readback/v1'
    assert evidence['order_id'] == order_id
    assert evidence['tp_athlete_id'] == 'fixture-athlete-m'
    assert evidence['capability_jti'].startswith('manual-inspect-')
    assert len(evidence['request_digest']) == 64

    confirm_ids = [
        item_id for item_id in _confirmed_ids(confirmed)
        if item_id != THRESHOLD_ITEM_ID
    ]
    approval_form = _approval_form(
        confirmed, csrf, confirm_ids=confirm_ids)
    approval_form['resolved_item'] = [
        f'{THRESHOLD_ITEM_ID}::manually-corrected']
    approved = review_client.post(
        f'/review/{order_id}/approve', data=approval_form)
    assert approved.status_code == 303
    assert load(state_path)['status'] == APPROVED


def test_athlete_m_login_to_approved_persists_complete_seal_bound_snapshot(
    review_client,
):
    """The de-identified athlete-m values traverse the complete page flow."""
    intake = json.loads((ATHLETE_M / 'intake.json').read_text())
    blockers = [_issue('WEEKS_MISMATCH', value={
        'generated_paid_weeks': 6,
        'purchased_weeks': intake['computed_weeks'],
        'lead_in_excluded': True,
    })]
    confirmations = [_confirmation(value={
        'long_ride_days': intake['long_ride_days'],
        'interval_days': intake['interval_days'],
        'generated_mismatches': ['intensity on sunday (2026-08-09)'],
    })]
    state, state_path, _ = _seed_order(
        'test_athlete_m_phase2', blockers=blockers,
        confirmations=confirmations)
    body, csrf = _login(review_client, state['order_id'])
    assert 'WEEKS_MISMATCH' in body
    assert 'SCHEDULE_MISMATCH_CONFIRM' in body
    assert 'waivable with reason' in body

    approved = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf, waived_ids=['WEEKS_MISMATCH'],
            reason='Coach verified the paid entitlement and accepts six paid weeks.',
        ),
    )
    assert approved.status_code == 303

    persisted = load(state_path)
    assert persisted['status'] == APPROVED
    assert approval_matches_release(persisted)
    approval = persisted['approval']
    assert approval['model_seal'] == persisted['model_seal']
    assert approval['release_manifest_digest'] == persisted['release_manifest_digest']
    assert approval['revision'] == persisted['generation_revision']
    assert approval['review_catalog_digest'] == persisted['review_catalog_digest']
    assert approval['credential'].startswith('review-link:')
    snapshots = {item['item_id']: item for item in approval['confirmations']}
    assert set(snapshots) == {item['item_id'] for item in persisted['review_items']}
    assert snapshots['WEEKS_MISMATCH']['value']['purchased_weeks'] == 7
    assert snapshots['WEEKS_MISMATCH']['disposition'] == 'resolved:waived'
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['value'][
        'generated_mismatches'] == ['intensity on sunday (2026-08-09)']
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['disposition'] == 'confirmed'
    assert all(item['revision'] == 1 for item in snapshots.values())
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['message'] == (
        'SCHEDULE_MISMATCH_CONFIRM fixture confirmation')

    approved_page = review_client.get(f"/review/{state['order_id']}")
    assert approved_page.status_code == 200
    approved_body = approved_page.get_data(as_text=True)
    assert 'This decision is bound to revision 1' in approved_body
    assert 'resolved:waived' in approved_body
    assert 'Disposition' in approved_body


def test_sealed_catalog_mutators_require_new_generation_revision(review_client):
    state, state_path, _ = _seed_order(
        'test_sealed_catalog_immutable', blockers=[_issue('RACE_STALE')])
    with pytest.raises(ValueError, match='write_generation'):
        merge_generation_blockers(
            state_path, state['generation_revision'], 'fixture',
            [_issue('RACE_STALE', value={'changed': True})])
    with pytest.raises(ValueError, match='write_generation'):
        set_generation_blockers(state_path, [_issue('RACE_STALE')])


def test_page_rejects_confirmation_value_drift_after_render(review_client):
    state, state_path, _ = _seed_order(
        'test_confirmation_catalog_drift',
        confirmations=[_confirmation(value={'target': 40})])
    _, csrf = _login(review_client, state['order_id'])
    _rewrite_catalog_item(
        state_path, 'required_confirmations', 'SCHEDULE_MISMATCH_CONFIRM',
        message='Changed after render.', value={'target': 120})

    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf),
    )
    assert response.status_code == 409
    assert 'review catalog changed' in response.get_data(as_text=True)
    assert load(state_path)['approval'] is None


def test_page_rejects_blocker_message_and_value_drift_after_render(review_client):
    state, state_path, _ = _seed_order(
        'test_blocker_catalog_drift',
        blockers=[_issue('RACE_STALE', value={'course': 'old'})])
    _, csrf = _login(review_client, state['order_id'])
    _rewrite_catalog_item(
        state_path, 'blocking_issues', 'RACE_STALE',
        message='Different blocker message.', value={'course': 'new'})

    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf, waived_ids=['RACE_STALE'], reason='Saw old value.'),
    )
    assert response.status_code == 409
    assert 'review catalog changed' in response.get_data(as_text=True)
    assert load(state_path)['approval'] is None


def test_review_page_download_uses_same_session_post_and_is_no_store(
    review_client,
):
    state, _, _ = _seed_order('test_review_download')
    unauthorized = review_client.get(
        f"/api/download/{state['order_id']}?artifact=review_bundle")
    assert unauthorized.status_code == 401

    body, csrf = _login(review_client, state['order_id'])
    assert '?artifact=review_bundle' not in body
    assert f'/review/{state["order_id"]}/bundle' in body
    downloaded = review_client.post(
        f'/review/{state["order_id"]}/bundle', data={'csrf_token': csrf})
    assert downloaded.status_code == 200
    assert downloaded.mimetype == 'application/zip'
    assert downloaded.headers['Cache-Control'].startswith('no-store')
    assert downloaded.headers['Pragma'] == 'no-cache'


@pytest.mark.parametrize('corruption', [
    'missing_entry', 'changed_value', 'changed_type',
    'seal_field_mismatch', 'old_snapshot_version',
])
def test_page_never_reports_non_authoritative_approval_as_approved(
    review_client, corruption,
):
    state, state_path, _ = _seed_order(f'test_invalid_approval_{corruption}')
    _, csrf = _login(review_client, state['order_id'])
    approved = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf),
    )
    assert approved.status_code == 303

    raw = json.loads(state_path.read_text())
    snapshot = raw['approval']['confirmations'][0]
    if corruption == 'missing_entry':
        raw['approval']['confirmations'].pop()
    elif corruption == 'changed_value':
        snapshot['value'] = {'changed': True}
    elif corruption == 'changed_type':
        snapshot['value_type'] = 'string'
    elif corruption == 'seal_field_mismatch':
        raw['approval']['model_seal'] = 'different-seal'
    elif corruption == 'old_snapshot_version':
        raw['approval']['snapshot_version'] = 'approval_snapshot/v1'
    state_path.write_text(json.dumps(raw))

    page = review_client.get(f"/review/{state['order_id']}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'Approval not authoritative — regenerate/re-approve.' in body
    assert '<strong>Approved.</strong>' not in body
    assert '<h2>Application</h2>' not in body
    assert 'Download sealed review bundle' not in body


def test_page_approval_rejects_missing_required_confirmation(review_client):
    state, state_path, _ = _seed_order(
        'test_missing_confirmation', confirmations=[_confirmation()])
    _, csrf = _login(review_client, state['order_id'])
    fact_ids = [
        item['item_id'] for item in state['review_items']
        if item['type'] == 'verified_fact'
    ]
    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf, confirm_ids=fact_ids),
    )
    assert response.status_code == 409
    assert 'required confirmation is unresolved' in response.get_data(as_text=True)
    assert load(state_path)['status'] == GENERATED


def test_review_page_shows_trainingpeaks_steps_when_d2_is_inactive(review_client):
    order_id = 'test_tp_delivery_steps'
    state_path = webhook_app._fulfillment_status_path(order_id)
    state = write_generation(
        state_path, 'athlete-m', [], order_id=order_id,
        delivery_platform='trainingpeaks')
    revision = (webhook_app._order_dir(order_id) / 'revisions'
                / f"r{state['generation_revision']}")
    revision.mkdir(parents=True)
    (revision / 'reviewed-values.txt').write_text('sealed review source')
    with zipfile.ZipFile(revision / f'{order_id}-review-bundle.zip', 'w') as archive:
        archive.writestr('plan_preview.txt', 'non-executable review preview')
    finalize_transitional_release(
        state_path, revision, expected_revision=state['generation_revision'])
    webhook_app._record_order_lookup(order_id, 'athlete-m')
    body, _ = _login(review_client, order_id)
    assert 'TrainingPeaks delivery' in body
    assert 'Automated calendar apply is not live' in body
    assert 'full package download' in body
    assert 'not the review bundle' in body


def test_review_page_does_not_require_per_fact_checkboxes(review_client):
    state, _, _ = _seed_order('test_fact_display_only')
    body, _ = _login(review_client, state['order_id'])
    assert 'I reviewed this sealed fact' not in body
    assert 'do not need individual checkboxes' in body
    assert 'sealed facts</summary>' in body
    fact_ids = [
        item['item_id'] for item in state['review_items']
        if item['type'] == 'verified_fact'
    ]
    assert fact_ids
    for item_id in fact_ids:
        assert item_id in body


def test_page_approval_records_verified_facts_without_checkboxes(review_client):
    state, state_path, _ = _seed_order(
        'test_auto_confirm_facts', confirmations=[_confirmation()])
    _, csrf = _login(review_client, state['order_id'])
    required_ids = [
        item['item_id'] for item in state['review_items']
        if item['type'] == 'required_confirmation'
    ]
    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf, confirm_ids=required_ids),
    )
    assert response.status_code == 303
    persisted = load(state_path)
    assert persisted['status'] == APPROVED
    snapshots = {item['item_id']: item for item in persisted['approval']['confirmations']}
    for item in persisted['review_items']:
        if item['type'] == 'verified_fact':
            assert snapshots[item['item_id']]['disposition'] == 'confirmed'


def test_page_approval_rejects_waiver_that_does_not_cover_all_blockers(review_client):
    state, state_path, _ = _seed_order(
        'test_partial_waiver', blockers=[_issue('RACE_STALE'), _issue('WEEKS_MISMATCH')])
    _, csrf = _login(review_client, state['order_id'])
    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf, waived_ids=['RACE_STALE'], reason='Reviewed one only.'),
    )
    assert response.status_code == 409
    assert 'cover every blocking issue exactly' in response.get_data(as_text=True)
    assert load(state_path)['status'] == BLOCKED_REVIEW


def test_page_approval_rejects_nonwaivable_blocker_even_when_submitted(review_client):
    state, state_path, _ = _seed_order(
        'test_nonwaivable_page', blockers=[_issue('FTP_ESTIMATED')])
    body, csrf = _login(review_client, state['order_id'])
    assert 'non-waivable' in body
    assert 'Supply a measured FTP and regenerate' in body
    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf, waived_ids=['FTP_ESTIMATED'], reason='Cannot override policy.'),
    )
    assert response.status_code == 409
    assert 'non-waivable blockers require regeneration' in response.get_data(as_text=True)
    assert load(state_path)['status'] == BLOCKED_REVIEW


def test_page_approval_rejects_stale_revision_session(review_client):
    state, state_path, _ = _seed_order('test_stale_page')
    _, csrf = _login(review_client, state['order_id'])
    regenerated = write_generation(
        state_path, state['athlete_id'], order_id=state['order_id'],
        delivery_platform='trainingpeaks')
    assert regenerated['generation_revision'] == 2

    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf),
    )
    assert response.status_code == 409
    assert 'session unavailable or superseded' in response.get_data(as_text=True)
    assert load(state_path)['status'] == GENERATED


def test_page_approval_rejects_seal_mismatch_and_materializes_policy_blocker(
    review_client,
):
    state, state_path, revision = _seed_order('test_page_seal_mismatch')
    _, csrf = _login(review_client, state['order_id'])
    (revision / 'reviewed-values.txt').write_text('mutated after review')

    response = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, csrf),
    )
    assert response.status_code == 409
    persisted = load(state_path)
    assert persisted['status'] == BLOCKED_REVIEW
    mismatch = next(item for item in persisted['blocking_issues']
                    if item['id'] == 'SEAL_MISMATCH')
    assert mismatch['waivable'] is False
    assert persisted['approval'] is None


def test_seal_mismatch_archives_full_approval_and_renders_history_only(
    review_client,
):
    blocker_value = {'paid_weeks': 7, 'generated_weeks': 6}
    confirmation_value = {
        'ftp_watts': 287,
        'basis': 'coach-reviewed threshold test',
    }
    waiver_reason = 'Coach accepted the six-week build after reviewing entitlement.'
    state, state_path, revision = _seed_order(
        'test_page_approval_provenance',
        blockers=[_issue('WEEKS_MISMATCH', value=blocker_value)],
        confirmations=[_confirmation('FTP_TARGET_CONFIRM', value=confirmation_value)],
    )
    _, csrf = _login(review_client, state['order_id'])
    approved = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf, waived_ids=['WEEKS_MISMATCH'], reason=waiver_reason,
        ),
    )
    assert approved.status_code == 303
    prior = load(state_path)
    assert approval_matches_release(prior)

    review_zip = revision / f"{state['order_id']}-review-bundle.zip"
    review_zip.write_bytes(b'post-approval seal mutation')
    refused = review_client.post(
        f"/review/{state['order_id']}/bundle", data={'csrf_token': csrf})
    assert refused.status_code == 409

    superseded = load(state_path)
    assert superseded['generation_revision'] == 2
    assert superseded['status'] == BLOCKED_REVIEW
    assert superseded['approval'] is None
    assert superseded['waiver'] is None
    assert approval_matches_release(superseded) is False
    assert len(superseded['superseded_approvals']) == 1
    archived = superseded['superseded_approvals'][0]
    assert archived['authoritative'] is False
    assert archived['reason'] == 'release seal mismatch'
    assert archived['superseded_at']
    assert archived['generation_revision'] == 1
    assert archived['approval'] == prior['approval']
    assert archived['waiver'] == prior['waiver']
    assert archived['model_seal'] == prior['model_seal']
    assert archived['release_manifest_digest'] == prior['release_manifest_digest']
    snapshots = {
        item['item_id']: item for item in archived['approval']['confirmations']
    }
    assert snapshots['WEEKS_MISMATCH']['value'] == blocker_value
    assert snapshots['WEEKS_MISMATCH']['disposition'] == 'resolved:waived'
    assert snapshots['FTP_TARGET_CONFIRM']['value'] == confirmation_value
    assert snapshots['FTP_TARGET_CONFIRM']['disposition'] == 'confirmed'
    assert archived['waiver']['reason'] == waiver_reason
    assert archived['approval']['credential'].startswith('review-link:')
    assert archived['approval']['review_catalog_digest'] == prior[
        'review_catalog_digest']

    history_body, _ = _login(review_client, state['order_id'])
    assert 'Superseded approval history' in history_body
    assert 'Historical evidence only.' in history_body
    assert 'Superseded decision — non-authoritative' in history_body
    assert waiver_reason in history_body
    assert '287' in history_body
    assert archived['approval']['credential'] in history_body
    assert '<strong>Approved.</strong>' not in history_body
    assert 'This decision is bound to revision' not in history_body
    assert '<h2>Application</h2>' not in history_body


def test_page_approval_rejects_unknown_item_wrong_csrf_and_escapes_values(review_client):
    malicious = _confirmation(
        'ESCAPE_CONFIRM', value='</pre><script>alert(1)</script>')
    malicious['message'] = '<img src=x onerror=alert(2)>'
    state, state_path, _ = _seed_order(
        'test_review_xss', confirmations=[malicious])
    body, csrf = _login(review_client, state['order_id'])
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in body
    assert '&lt;img src=x onerror=alert(2)&gt;' in body
    assert '</pre><script>alert(1)</script>' not in body

    bad_csrf = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(state, 'wrong-token'),
    )
    assert bad_csrf.status_code == 403

    unknown = review_client.post(
        f"/review/{state['order_id']}/approve",
        data=_approval_form(
            state, csrf,
            confirm_ids=_confirmed_ids(state) + ['UNKNOWN_ITEM']),
    )
    assert unknown.status_code == 409
    assert 'unknown review item id' in unknown.get_data(as_text=True)
    assert load(state_path)['approval'] is None


def test_generation_email_points_to_fragment_login_not_a_bundle_alias():
    _, text, rendered = webhook_app._build_phase1_generation_email({
        'name': 'Athlete M', 'order_id': 'test_email_review',
        'fulfillment_status': 'GENERATED', 'blocking_issues': [],
        'download_token': 'download-token', 'review_token': 'review-token',
    })
    content = text + rendered
    assert '/review/test_email_review#token=review-token' in content
    assert '/review/test_email_review?token=' not in content
    assert '/api/download/test_email_review?artifact=review_bundle' not in content


def test_unauthenticated_review_get_does_not_migrate_legacy_state(
    review_client,
):
    legacy = (Path(webhook_app.DELIVERIES_DIR) / 'legacy_rider'
              / 'fulfillment_status.json')
    legacy.parent.mkdir(parents=True)
    original = {
        'schema_version': 1, 'athlete_id': 'legacy_rider',
        'generation_revision': 1, 'status': 'APPROVED',
        'blocking_issues': [], 'approval': {'coach': 'legacy'},
        'waiver': None, 'application': None, 'confirmation': None,
        'history': [], 'updated_at': '2026-08-01T00:00:00Z',
    }
    legacy.write_text(json.dumps(original))

    response = review_client.get('/review/legacy_rider')
    assert response.status_code == 200
    assert 'Opening your secure review session' in response.get_data(as_text=True)
    assert json.loads(legacy.read_text()) == original
    orders = Path(webhook_app.DELIVERIES_DIR) / 'orders'
    assert not orders.exists() or list(orders.iterdir()) == []


def test_generic_operator_endpoint_cannot_approve(
    review_client, monkeypatch,
):
    monkeypatch.setenv('CRON_SECRET', 'operator-test-secret')
    state, state_path, _ = _seed_order('test_operator_snapshot')
    endpoint = f"/api/fulfillment/{state['order_id']}/transition"
    refused = review_client.post(
        endpoint,
        json={
            'to': APPROVED,
            'coach': 'untrusted-name',
            'generation_revision': state['generation_revision'],
            'review_catalog_digest': state['review_catalog_digest'],
            'confirmations': [
                {
                    'item_id': item_id,
                    'revision': state['generation_revision'],
                    'disposition': 'confirmed',
                }
                for item_id in _confirmed_ids(state)
            ],
        },
        headers={'X-Cron-Secret': 'operator-test-secret'},
    )
    assert refused.status_code == 409
    assert 'narrow Endure approval bridge' in refused.get_json()['error']
    persisted = load(state_path)
    assert persisted['approval'] is None


def _endure_headers(method, path, body, *, timestamp=None):
    timestamp = int(time.time()) if timestamp is None else timestamp
    message, _, _ = request_message(method, path, timestamp, body)
    signature = hmac.new(
        b'endure-approval-test-secret-that-is-long-enough',
        message,
        hashlib.sha256,
    ).hexdigest()
    return {
        'X-Endure-Key-Id': 'endure-test-key',
        'X-Endure-Timestamp': str(timestamp),
        'X-Endure-Signature': signature,
    }


def test_endure_bridge_reads_and_approves_exact_sealed_catalog(
    review_client, monkeypatch,
):
    monkeypatch.setenv(
        'ENDURE_APPROVAL_SECRET',
        'endure-approval-test-secret-that-is-long-enough',
    )
    monkeypatch.setenv('ENDURE_APPROVAL_KEY_ID', 'endure-test-key')
    athlete_id = '6dfb5c7f-71e4-43d8-926a-86e13be03416'
    state, state_path, _ = _seed_order(
        'test_endure_bridge', athlete_id=athlete_id,
    )
    review_path = f"/api/fulfillment/{state['order_id']}/endure-review"
    review = review_client.get(
        review_path,
        headers=_endure_headers('GET', review_path, None),
    )
    assert review.status_code == 200
    review_body = review.get_json()
    assert review_body['schema_version'] == 'motoren_endure_review/v1'
    assert review_body['review_catalog_digest'] == state['review_catalog_digest']
    assert review_body['model_seal'] == state['model_seal']
    assert review_body['release_authorized'] is False
    assert 'operations' not in review_body

    command = {
        'command_version': 'endure_approval_command/v1',
        'request_id': '31956f0a-c567-4c16-98ef-8c6ba6c5fa47',
        'order_id': state['order_id'],
        'athlete_id': athlete_id,
        'generation_revision': state['generation_revision'],
        'review_catalog_digest': state['review_catalog_digest'],
        'model_seal': state['model_seal'],
        'release_manifest_digest': state['release_manifest_digest'],
        'approving_actor_id': '52c2787e-70fb-4c7b-bf93-334f47a34e3d',
        'approving_org_id': '25ab74b2-4b84-4fb5-bc96-104e0085b9c5',
        'approving_membership_role': 'coach',
        'confirmations': [
            {
                'item_id': item_id,
                'revision': state['generation_revision'],
                'disposition': 'confirmed',
            }
            for item_id in _confirmed_ids(state)
        ],
        'waiver': None,
    }
    approval_path = f"/api/fulfillment/{state['order_id']}/endure-approval"
    headers = _endure_headers('POST', approval_path, command)
    approved = review_client.post(approval_path, json=command, headers=headers)
    assert approved.status_code == 200
    receipt = approved.get_json()
    assert receipt['schema_version'] == 'motoren_approval_receipt/v1'
    assert receipt['status'] == APPROVED
    assert receipt['release_authorized'] is True
    assert receipt['external_writes_performed'] is False
    assert receipt['source_request_id'] == command['request_id']

    persisted = load(state_path)
    assert persisted['approval']['credential'] == (
        'endure:endure-test-key:25ab74b2-4b84-4fb5-bc96-104e0085b9c5:'
        '52c2787e-70fb-4c7b-bf93-334f47a34e3d'
    )
    assert persisted['approval']['source']['request_id'] == command['request_id']
    assert approval_matches_release(persisted)

    replay = review_client.post(approval_path, json=command, headers=headers)
    assert replay.status_code == 200
    assert replay.get_json() == receipt

    fresh_headers = _endure_headers(
        'POST', approval_path, command, timestamp=int(time.time()) + 1,
    )
    fresh_replay = review_client.post(
        approval_path, json=command, headers=fresh_headers,
    )
    assert fresh_replay.status_code == 200
    assert fresh_replay.get_json() == receipt


def test_endure_bridge_governs_revision_request_and_exact_replay(
    review_client, monkeypatch,
):
    monkeypatch.setenv(
        'ENDURE_APPROVAL_SECRET',
        'endure-approval-test-secret-that-is-long-enough',
    )
    monkeypatch.setenv('ENDURE_APPROVAL_KEY_ID', 'endure-test-key')
    athlete_id = 'd40404bb-8583-4812-bb7d-39cf2e95ea47'
    state, state_path, _ = _seed_order(
        'test_endure_revision_request', athlete_id=athlete_id,
    )
    command = {
        'command_version': 'endure_revision_request/v1',
        'request_id': '49870cb0-b8cf-4101-921b-f17865cdbac9',
        'order_id': state['order_id'],
        'athlete_id': athlete_id,
        'generation_revision': state['generation_revision'],
        'review_catalog_digest': state['review_catalog_digest'],
        'model_seal': state['model_seal'],
        'release_manifest_digest': state['release_manifest_digest'],
        'requesting_actor_id': '3dc929e1-0f68-4c39-8625-160242808e22',
        'requesting_org_id': '971883cb-173a-4cc7-a0e4-da01d9776937',
        'requesting_membership_role': 'coach',
        'decisions': [],
        'note': 'Keep completed work and move the key endurance day to Sunday.',
    }
    path = f"/api/fulfillment/{state['order_id']}/endure-revision-request"
    requested = review_client.post(
        path, json=command, headers=_endure_headers('POST', path, command),
    )
    assert requested.status_code == 200
    receipt = requested.get_json()
    assert receipt['schema_version'] == 'motoren_revision_request_receipt/v1'
    assert receipt['status'] == 'REVISION_REQUESTED'
    assert receipt['generation_revision'] == state['generation_revision']
    assert receipt['next_generation_revision'] == state['generation_revision'] + 1
    assert receipt['source_request_id'] == command['request_id']
    assert receipt['release_authorized'] is False
    assert receipt['external_writes_performed'] is False

    fresh_replay = review_client.post(
        path,
        json=command,
        headers=_endure_headers(
            'POST', path, command, timestamp=int(time.time()) + 1,
        ),
    )
    assert fresh_replay.status_code == 200
    assert fresh_replay.get_json() == receipt

    review_path = f"/api/fulfillment/{state['order_id']}/endure-review"
    readback = review_client.get(
        review_path, headers=_endure_headers('GET', review_path, None),
    )
    assert readback.status_code == 200
    assert readback.get_json()['revision_request_receipt'] == receipt
    assert load(state_path)['pending_endure_revision_request']['note'] == command['note']

    approval_command = {
        'command_version': 'endure_approval_command/v1',
        'request_id': 'e7c8a278-033a-436f-a2ba-10fb94aa2d0c',
        'order_id': state['order_id'],
        'athlete_id': athlete_id,
        'generation_revision': state['generation_revision'],
        'review_catalog_digest': state['review_catalog_digest'],
        'model_seal': state['model_seal'],
        'release_manifest_digest': state['release_manifest_digest'],
        'approving_actor_id': command['requesting_actor_id'],
        'approving_org_id': command['requesting_org_id'],
        'approving_membership_role': 'coach',
        'confirmations': [
            {
                'item_id': item_id,
                'revision': state['generation_revision'],
                'disposition': 'confirmed',
            }
            for item_id in _confirmed_ids(state)
        ],
        'waiver': None,
    }
    approval_path = f"/api/fulfillment/{state['order_id']}/endure-approval"
    refused = review_client.post(
        approval_path,
        json=approval_command,
        headers=_endure_headers('POST', approval_path, approval_command),
    )
    assert refused.status_code == 409
    assert 'must be regenerated' in refused.get_json()['error']
    assert load(state_path)['approval'] is None


def test_endure_bridge_rejects_tampered_body(review_client, monkeypatch):
    monkeypatch.setenv(
        'ENDURE_APPROVAL_SECRET',
        'endure-approval-test-secret-that-is-long-enough',
    )
    monkeypatch.setenv('ENDURE_APPROVAL_KEY_ID', 'endure-test-key')
    athlete_id = 'f080d383-7b6a-4f71-b729-1f4013b914d5'
    state, state_path, _ = _seed_order(
        'test_endure_tamper', athlete_id=athlete_id,
    )
    path = f"/api/fulfillment/{state['order_id']}/endure-approval"
    command = {
        'command_version': 'endure_approval_command/v1',
        'request_id': '50d16c1e-c9a4-49b2-a3ef-afdb0aa8291a',
        'order_id': state['order_id'],
        'athlete_id': athlete_id,
        'generation_revision': 1,
        'review_catalog_digest': state['review_catalog_digest'],
        'model_seal': state['model_seal'],
        'release_manifest_digest': state['release_manifest_digest'],
        'approving_actor_id': '65ee7c08-c799-4446-a1f0-1bd859446e16',
        'approving_org_id': '77412e7f-c691-40e8-a08d-a5d7e6807775',
        'approving_membership_role': 'coach',
        'confirmations': [],
        'waiver': None,
    }
    headers = _endure_headers('POST', path, command)
    command['approving_membership_role'] = 'admin'
    response = review_client.post(path, json=command, headers=headers)
    assert response.status_code == 401
    assert load(state_path)['approval'] is None


def test_revoking_link_after_login_ends_page_session(review_client, monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'operator-test-secret')
    state, _, _ = _seed_order('test_review_session_revoke')
    token = webhook_app._generate_review_token(
        state['order_id'], 'coach@example.invalid')
    claims = verify_review_token(
        token, order_id=state['order_id'], athlete_id=state['athlete_id'],
        generation_revision=state['generation_revision'],
        revocation_path=Path(webhook_app.DATA_DIR) / 'token_revocations.json')
    opened = review_client.post(
        f"/review/{state['order_id']}/session", data={'token': token})
    assert opened.status_code == 303

    revoked = review_client.post(
        '/api/download-tokens/revoke', json={'jti': claims['jti']},
        headers={'X-Cron-Secret': 'operator-test-secret'})
    assert revoked.status_code == 200
    shell = review_client.get(f"/review/{state['order_id']}")
    body = shell.get_data(as_text=True)
    assert 'Opening your secure review session' in body
    assert state['athlete_id'] not in body


def test_review_bundle_get_rejects_header_and_query_bearers(
    review_client, monkeypatch,
):
    monkeypatch.setenv('CRON_SECRET', 'operator-test-secret')
    state, _, _ = _seed_order('test_review_child_revoke')
    review_token = webhook_app._generate_review_token(
        state['order_id'], 'coach@example.invalid')
    parent = verify_review_token(
        review_token, order_id=state['order_id'], athlete_id=state['athlete_id'],
        generation_revision=state['generation_revision'],
        revocation_path=Path(webhook_app.DATA_DIR) / 'token_revocations.json')
    child = webhook_app._generate_download_token(
        state['order_id'], 'review_bundle', parent_review=parent)
    child_claims = verify_download_token(
        child, expected_order_id=state['order_id'],
        expected_athlete_id=state['athlete_id'], expected_revision=1,
        expected_artifact='review_bundle', expected_audience='coach',
        revocation_path=Path(webhook_app.DATA_DIR) / 'token_revocations.json')
    assert child_claims['parent_review_jti'] == parent['jti']
    assert child_claims['parent_review_kid'] == parent['kid']
    assert child_claims['exp'] - child_claims['iat'] <= MAX_REVIEW_BUNDLE_TTL_SECONDS

    url = f"/api/download/{state['order_id']}?artifact=review_bundle"
    assert review_client.get(
        url, headers={'Authorization': f'Bearer {child}'}).status_code == 401
    assert review_client.get(f'{url}&token={child}').status_code == 401
    assert review_client.get(f'{url}&%74oken={child}').status_code == 401

    revoked = review_client.post(
        '/api/download-tokens/revoke', json={'jti': parent['jti']},
        headers={'X-Cron-Secret': 'operator-test-secret'})
    assert revoked.status_code == 200
    with pytest.raises(DownloadTokenError, match='parent review credential revoked'):
        verify_download_token(
            child, expected_order_id=state['order_id'],
            expected_athlete_id=state['athlete_id'], expected_revision=1,
            expected_artifact='review_bundle', expected_audience='coach',
            revocation_path=Path(webhook_app.DATA_DIR) / 'token_revocations.json')


def test_revoking_parent_ends_same_session_bundle_fetch(review_client, monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'operator-test-secret')
    state, _, _ = _seed_order('test_session_bundle_revoke')
    token = webhook_app._generate_review_token(
        state['order_id'], 'coach@example.invalid')
    claims = verify_review_token(
        token, order_id=state['order_id'], athlete_id=state['athlete_id'],
        generation_revision=state['generation_revision'],
        revocation_path=Path(webhook_app.DATA_DIR) / 'token_revocations.json')
    assert review_client.post(
        f"/review/{state['order_id']}/session", data={'token': token}
    ).status_code == 303
    page = review_client.get(f"/review/{state['order_id']}").get_data(as_text=True)
    csrf = html.unescape(re.search(
        r'name="csrf_token" value="([^"]+)"', page).group(1))
    endpoint = f"/review/{state['order_id']}/bundle"
    assert review_client.post(
        endpoint, data={'csrf_token': csrf}).status_code == 200
    assert review_client.post(
        '/api/download-tokens/revoke', json={'jti': claims['jti']},
        headers={'X-Cron-Secret': 'operator-test-secret'}).status_code == 200
    assert review_client.post(
        endpoint, data={'csrf_token': csrf}).status_code == 401


@pytest.mark.parametrize('token_key', ['token', '%74oken', 't%6fken'])
def test_application_logging_redacts_percent_encoded_query_bearers(token_key):
    record = webhook_app.logging.LogRecord(
        'werkzeug', webhook_app.logging.INFO, __file__, 1,
        f'GET /api/download/x?artifact=review_bundle&{token_key}=secret-value HTTP/1.1',
        (), None,
    )
    assert webhook_app._bearer_query_redaction.filter(record)
    rendered = record.getMessage()
    assert 'secret-value' not in rendered
    assert '[REDACTED]' in rendered


def test_redaction_filter_is_installed_on_application_request_loggers():
    for logger_name in ('gravel-god-webhook', 'werkzeug', 'gunicorn.access'):
        assert webhook_app._bearer_query_redaction in (
            webhook_app.logging.getLogger(logger_name).filters
        )
