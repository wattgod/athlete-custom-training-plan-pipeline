"""Focused J1 state-machine tests (kept independent of Flask fixtures)."""

import json
import os
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fulfillment_state import (APPLIED, APPROVED, BLOCKED_REVIEW, CANCELLED,
                               CONFIRMED, GENERATED, FulfillmentStateError,
                               bind_legacy_order,
                               approval_matches_release,
                               confirm_after_send, confirm_endure_after_send,
                               finalize_transitional_release,
                               load, merge_generation_blockers,
                               migrate_v1_to_quarantine, transition,
                               open_verified_release_artifact,
                               record_endure_stage_receipt,
                               reconcile_endure_confirmation,
                               record_seal_mismatch,
                               verify_release_manifest, write_generation)
from d2_identity import record_identity_result


ENDURE_PAYLOAD_DIGEST = 'd' * 64


def _issue(rule_id="R05"):
    return {'id': rule_id, 'source': 'block_compliance', 'severity': 'CRITICAL',
            'message': 'Intensity count: W8 has one hard session'}


def _seal(path, tmp_path):
    root = tmp_path / 'artifacts'
    root.mkdir(exist_ok=True)
    (root / 'guide.html').write_text('sealed guide')
    state = load(path)
    if (state['delivery_platform'] in {'trainingpeaks', 'endure'}
            and not state.get('platform_identity')):
        state = record_identity_result(
            path, state['generation_revision'], {
                'outcome': 'bound', 'tp_athlete_id': 'fixture-state-athlete',
                'candidates': [],
            }, capability_jti='fixture-state-binding-jti')
    return finalize_transitional_release(
        path, root, expected_revision=state['generation_revision'])


def _decisions(state, *extra_ids):
    ids = [
        item['item_id'] for item in state['review_items']
        if item['type'] in {'required_confirmation', 'verified_fact'}
    ] + list(extra_ids)
    return [
        {'item_id': item_id, 'revision': state['generation_revision'],
         'disposition': 'confirmed'}
        for item_id in ids
    ]


def _approve(path, coach='coach@example.test', **kwargs):
    state = load(path)
    return transition(
        path, APPROVED, coach,
        expected_revision=state['generation_revision'],
        expected_catalog_digest=state['review_catalog_digest'],
        review_decisions=_decisions(state),
        **kwargs,
    )


def test_r05_failure_writes_blocked_review_with_rule_id(tmp_path):
    state = write_generation(tmp_path / 'fulfillment_status.json', 'heather_gray', [_issue()])
    assert state['status'] == BLOCKED_REVIEW
    assert state['blocking_issues'][0]['id'] == 'R05'


def test_clean_generation_writes_generated(tmp_path):
    assert write_generation(tmp_path / 'status.json', 'heather_gray')['status'] == GENERATED


def test_blocked_approval_requires_complete_waiver(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', [_issue('R05'), _issue('R01')])
    _seal(path, tmp_path)
    with pytest.raises(FulfillmentStateError):
        _approve(path, waiver={'rule_ids': ['R05'], 'reason': 'no'})
    state = _approve(path, waiver={
        'rule_ids': ['R01', 'R05'], 'reason': 'Reviewed and accepted the exception.'})
    assert state['status'] == APPROVED


def test_apply_requires_approved(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    with pytest.raises(FulfillmentStateError):
        transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')


def test_confirm_applied_sends_once_and_marks_confirmed(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    calls = []
    assert confirm_after_send(path, lambda: calls.append(True) or True)[0] == 'confirmed'
    assert calls == [True]
    assert load(path)['status'] == CONFIRMED


def test_confirm_email_failure_leaves_applied(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    with pytest.raises(RuntimeError):
        confirm_after_send(path, lambda: False)
    assert load(path)['status'] == APPLIED


def test_confirmed_retry_is_idempotent(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    confirm_after_send(path, lambda: True)
    assert confirm_after_send(path, lambda: pytest.fail('must not send'))[0] == 'idempotent'


def test_concurrent_confirm_sends_once(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    calls, results = [], []
    threads = [threading.Thread(target=lambda: results.append(confirm_after_send(
        path, lambda: calls.append(True) or True)[0])) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert calls == [True]
    assert sorted(results) == ['confirmed', 'idempotent']


def _endure_stage(state):
    return {
        'ok': True,
        'order_id': state['order_id'],
        'athlete_id': 'endure-athlete-1',
        'plan_id': 'endure-plan-1',
        'block_id': 'endure-block-1',
        'invitation_id': 'endure-invite-1',
        'invite_url': 'https://endurelabs.app/invite/live-token',
        'linked_account': False,
        'invitation_accepted': False,
        'review_url': (
            'https://endurelabs.app/coach/athletes/endure-athlete-1/plan'
            '?planId=endure-plan-1&blockId=endure-block-1'),
        'recipient_email_sha256': 'c' * 64,
        'release': {
            'generation_revision': state['generation_revision'],
            'release_manifest_digest': state['release_manifest_digest'],
            'model_seal': state['model_seal'],
        },
        'status': 'ready_for_review',
    }


def _endure_readiness(stage):
    return {
        **stage,
        'status': 'ready_for_athlete',
        'calendar_verification': {
            'status': 'verified', 'expectedCount': 6, 'actualCount': 6,
        },
    }


def _approved_endure(path, tmp_path):
    write_generation(
        path, 'endure-athlete', order_id='cs_endure_1',
        delivery_platform='endure')
    state = _seal(path, tmp_path)
    return _approve(path)


def test_endure_stage_binds_exact_approved_release_and_is_idempotent(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    prepared = _endure_stage(approved)
    action, state = record_endure_stage_receipt(path, prepared)
    assert action == 'staged'
    assert state['status'] == APPROVED
    assert state['endure_stage']['block_id'] == 'endure-block-1'
    retry = {**prepared, 'status': 'already_ready_for_review'}
    assert record_endure_stage_receipt(path, retry)[0] == 'idempotent'


def test_endure_stage_rejects_stale_release_without_mutating_state(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    prepared = _endure_stage(approved)
    prepared['release'] = {**prepared['release'], 'generation_revision': 99}
    with pytest.raises(FulfillmentStateError, match='approved release'):
        record_endure_stage_receipt(path, prepared)
    assert load(path)['endure_stage'] is None


def test_endure_stage_rejects_accepted_but_unlinked_identity(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    prepared = {
        **_endure_stage(approved),
        'invitation_id': None,
        'invite_url': None,
        'linked_account': False,
        'invitation_accepted': True,
    }
    with pytest.raises(FulfillmentStateError, match='not linked'):
        record_endure_stage_receipt(path, prepared)
    assert load(path)['endure_stage'] is None


def test_endure_confirm_sends_once_directly_from_approved(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    calls, results = [], []
    threads = [threading.Thread(target=lambda: results.append(
        confirm_endure_after_send(
            path, readiness, lambda: calls.append(True) or True,
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)[0])) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert calls == [True]
    assert sorted(results) == ['confirmed', 'idempotent']
    confirmed = load(path)
    assert confirmed['status'] == CONFIRMED
    assert confirmed['confirmation']['endure_stage']['block_id'] == 'endure-block-1'
    assert confirmed['endure_confirmation_attempt']['status'] == 'accepted'
    assert confirmed['endure_confirmation_attempt']['attempt_number'] == 1


def test_endure_confirm_failure_or_mismatch_never_marks_confirmed(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    readiness['block_id'] = 'wrong-block'
    with pytest.raises(FulfillmentStateError, match='block_id'):
        confirm_endure_after_send(
            path, readiness, lambda: pytest.fail('must not send'),
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    readiness['block_id'] = 'endure-block-1'
    with pytest.raises(RuntimeError, match='email failed'):
        confirm_endure_after_send(
            path, readiness, lambda: False,
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    failed = load(path)
    assert failed['status'] == APPROVED
    assert failed['endure_confirmation_attempt']['status'] == 'unknown'


def test_endure_confirm_retries_same_key_after_lease_inside_provider_window(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    key = 'endure/cs_endure_1/r1'
    with pytest.raises(RuntimeError, match='email failed'):
        confirm_endure_after_send(path, readiness, lambda: False,
                                  idempotency_key=key,
                                  payload_digest=ENDURE_PAYLOAD_DIGEST)
    raw = json.loads(path.read_text())
    raw['endure_confirmation_attempt']['lease_expires_at'] = (
        raw['endure_confirmation_attempt']['started_at'])
    path.write_text(json.dumps(raw))
    action, confirmed = confirm_endure_after_send(
        path, readiness, lambda: True, idempotency_key=key,
        payload_digest=ENDURE_PAYLOAD_DIGEST)
    assert action == 'confirmed'
    assert confirmed['endure_confirmation_attempt']['status'] == 'accepted'
    assert confirmed['endure_confirmation_attempt']['attempt_number'] == 2


def test_endure_confirm_refuses_retry_while_prior_attempt_lease_is_live(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True

    class SimulatedCrash(RuntimeError):
        pass

    with pytest.raises(SimulatedCrash):
        confirm_endure_after_send(
            path, readiness,
            lambda: (_ for _ in ()).throw(SimulatedCrash('lost worker')),
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    with pytest.raises(FulfillmentStateError, match='already in progress'):
        confirm_endure_after_send(
            path, readiness, lambda: pytest.fail('must not resend'),
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)


def test_endure_confirm_fails_closed_after_provider_idempotency_window(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    key = 'endure/cs_endure_1/r1'
    with pytest.raises(RuntimeError, match='email failed'):
        confirm_endure_after_send(path, readiness, lambda: False,
                                  idempotency_key=key,
                                  payload_digest=ENDURE_PAYLOAD_DIGEST)
    raw = json.loads(path.read_text())
    raw['endure_confirmation_attempt'].update({
        'started_at': '2000-01-01T00:00:00Z',
        'lease_expires_at': '2000-01-01T00:02:00Z',
        'last_result_at': '2000-01-01T00:02:00Z',
    })
    path.write_text(json.dumps(raw))
    with pytest.raises(FulfillmentStateError, match='reconcile Resend'):
        confirm_endure_after_send(
            path, readiness, lambda: pytest.fail('must not resend'),
            idempotency_key=key,
            payload_digest=ENDURE_PAYLOAD_DIGEST)


def test_endure_confirm_rejects_changed_payload_before_retry_io(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    key = 'endure/cs_endure_1/r1'
    with pytest.raises(RuntimeError, match='email failed'):
        confirm_endure_after_send(
            path, readiness, lambda: False, idempotency_key=key,
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    raw = json.loads(path.read_text())
    raw['endure_confirmation_attempt']['lease_expires_at'] = (
        raw['endure_confirmation_attempt']['started_at'])
    path.write_text(json.dumps(raw))
    with pytest.raises(FulfillmentStateError, match='changed the provider payload'):
        confirm_endure_after_send(
            path, readiness, lambda: pytest.fail('must not resend'),
            idempotency_key=key, payload_digest='e' * 64)


def test_endure_email_reconcile_delivered_requires_and_records_provider_id(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    key = 'endure/cs_endure_1/r1'
    with pytest.raises(RuntimeError):
        confirm_endure_after_send(
            path, readiness, lambda: False, idempotency_key=key,
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    with pytest.raises(FulfillmentStateError, match='provider message id'):
        reconcile_endure_confirmation(
            path, outcome='delivered', operator='matti', evidence='Resend log',
            expected_idempotency_key=key,
            expected_payload_digest=ENDURE_PAYLOAD_DIGEST)

    action, confirmed = reconcile_endure_confirmation(
        path, outcome='delivered', operator='matti',
        evidence='Verified in Resend delivery log',
        expected_idempotency_key=key,
        expected_payload_digest=ENDURE_PAYLOAD_DIGEST,
        provider_message_id='resend-message-123')
    assert action == 'confirmed_from_provider_evidence'
    assert confirmed['status'] == CONFIRMED
    assert confirmed['endure_confirmation_attempt']['status'] == 'accepted'
    assert confirmed['confirmation']['provider_message_id'] == 'resend-message-123'
    assert confirmed['confirmation']['calendar_verification'] == (
        readiness['calendar_verification'])


def test_endure_email_reconcile_not_sent_clears_exact_attempt_for_new_send(tmp_path):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    key = 'endure/cs_endure_1/r1'
    with pytest.raises(RuntimeError):
        confirm_endure_after_send(
            path, readiness, lambda: False, idempotency_key=key,
            payload_digest=ENDURE_PAYLOAD_DIGEST)

    action, cleared = reconcile_endure_confirmation(
        path, outcome='not_sent', operator='matti',
        evidence='Resend search returned no message for the exact key',
        expected_idempotency_key=key,
        expected_payload_digest=ENDURE_PAYLOAD_DIGEST)
    assert action == 'cleared_for_new_attempt'
    assert cleared['status'] == APPROVED
    assert cleared['endure_confirmation_attempt'] is None

    action, confirmed = confirm_endure_after_send(
        path, readiness, lambda: True,
        idempotency_key='endure/cs_endure_1/r1/reconciled-2',
        payload_digest='e' * 64)
    assert action == 'confirmed'
    assert confirmed['endure_confirmation_attempt']['attempt_number'] == 1


@pytest.mark.parametrize(
    ('key', 'digest', 'message'),
    [
        ('wrong-key', ENDURE_PAYLOAD_DIGEST, 'idempotency key is stale'),
        ('endure/cs_endure_1/r1', 'e' * 64, 'payload digest is stale'),
    ],
)
def test_endure_email_reconcile_rejects_stale_attempt_identity_without_mutation(
        tmp_path, key, digest, message):
    path = tmp_path / 'status.json'
    approved = _approved_endure(path, tmp_path)
    _, staged = record_endure_stage_receipt(path, _endure_stage(approved))
    readiness = _endure_readiness(staged['endure_stage'])
    readiness['ok'] = True
    with pytest.raises(RuntimeError):
        confirm_endure_after_send(
            path, readiness, lambda: False,
            idempotency_key='endure/cs_endure_1/r1',
            payload_digest=ENDURE_PAYLOAD_DIGEST)
    before = path.read_text()
    with pytest.raises(FulfillmentStateError, match=message):
        reconcile_endure_confirmation(
            path, outcome='not_sent', operator='matti', evidence='provider log',
            expected_idempotency_key=key, expected_payload_digest=digest)
    assert path.read_text() == before


def test_endure_email_reconcile_requires_an_existing_attempt(tmp_path):
    path = tmp_path / 'status.json'
    _approved_endure(path, tmp_path)
    with pytest.raises(FulfillmentStateError, match='durable send attempt'):
        reconcile_endure_confirmation(
            path, outcome='not_sent', operator='matti', evidence='provider log',
            expected_idempotency_key='endure/cs_endure_1/r1',
            expected_payload_digest=ENDURE_PAYLOAD_DIGEST)


def test_missing_or_malformed_state_fails_closed(tmp_path):
    with pytest.raises(FulfillmentStateError):
        confirm_after_send(tmp_path / 'absent.json', lambda: True)
    path = tmp_path / 'bad.json'
    path.write_text('{bad')
    with pytest.raises(FulfillmentStateError):
        load(path)


def test_regeneration_invalidates_prior_approval_and_application(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    state = write_generation(path, 'heather_gray', delivery_platform='trainingpeaks')
    assert state['generation_revision'] == 2
    assert state['status'] == GENERATED
    assert state['approval'] is None and state['application'] is None


def test_order_identity_is_immutable_across_regeneration(tmp_path):
    path = tmp_path / 'status.json'
    first = write_generation(
        path, 'athlete-m', order_id='cs_order_1',
        delivery_platform='trainingpeaks')
    assert first['schema_version'] == 2
    assert first['order_id'] == 'cs_order_1'
    second = write_generation(
        path, 'athlete-m', order_id='cs_order_1',
        delivery_platform='trainingpeaks')
    assert second['generation_revision'] == 2
    with pytest.raises(FulfillmentStateError, match='order_id is immutable'):
        write_generation(
            path, 'athlete-m', order_id='cs_order_2',
            delivery_platform='trainingpeaks')


def test_namespaced_merge_preserves_and_clears_other_sources(tmp_path):
    path = tmp_path / 'status.json'
    state = write_generation(
        path, 'athlete-m', [_issue('RACE_STALE')], order_id='cs_merge')
    state = merge_generation_blockers(
        path, state['generation_revision'], 'post_render',
        [_issue('THIN_RACE_WEEK')])
    assert [i['id'] for i in state['blocking_issues']] == [
        'RACE_STALE', 'THIN_RACE_WEEK']
    state = merge_generation_blockers(
        path, state['generation_revision'], 'post_render', [])
    assert [i['id'] for i in state['blocking_issues']] == ['RACE_STALE']


def test_merge_rejects_stale_revision(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_stale')
    with pytest.raises(FulfillmentStateError, match='revision mismatch'):
        merge_generation_blockers(path, 99, 'post_render', [])


def test_nonwaivable_blocker_rejects_complete_waiver(tmp_path):
    path = tmp_path / 'status.json'
    state = write_generation(
        path, 'athlete-m', [_issue('FTP_ESTIMATED')], order_id='cs_ftp')
    _seal(path, tmp_path)
    with pytest.raises(FulfillmentStateError, match='non-waivable'):
        _approve(path, 'coach', waiver={
            'rule_ids': ['FTP_ESTIMATED'], 'reason': 'accept'})
    assert state['blocking_issues'][0]['waivable'] is False


def test_review_catalog_and_approval_snapshot_store_typed_values(tmp_path):
    path = tmp_path / 'status.json'
    state = write_generation(
        path, 'athlete-m', order_id='cs_snapshot',
        required_confirmations=[{
            'id': 'SCHEDULE_MISMATCH_CONFIRM', 'source': 'post_render',
            'message': 'Sunday intensity needs confirmation.',
            'review_value': {
                'day': 'sunday', 'role': 'long_ride_only', 'count': 1,
            },
            'basis': 'generated schedule versus athlete availability',
            'sensitivity': 'personal',
        }],
        soft_confirmations=[{
            'id': 'COSMETIC_NOTE', 'source': 'fixture',
            'message': 'Optional copy observation.', 'review_value': True,
        }],
    )
    state = _seal(path, tmp_path)
    catalog = {item['item_id']: item for item in state['review_items']}
    assert catalog['SCHEDULE_MISMATCH_CONFIRM']['value'] == {
        'day': 'sunday', 'role': 'long_ride_only', 'count': 1,
    }
    assert catalog['SCHEDULE_MISMATCH_CONFIRM']['value_type'] == 'object'
    assert catalog['COSMETIC_NOTE']['value_type'] == 'boolean'
    assert catalog['FACT_RELEASE_SEAL']['value']['model_seal'] == state['model_seal']

    approved = transition(
        path, APPROVED, 'review-link-credential', expected_revision=1,
        expected_catalog_digest=state['review_catalog_digest'],
        review_decisions=_decisions(state),
        credential='review-link:kid:jti-issued-to',
    )
    assert approval_matches_release(approved)
    snapshots = {item['item_id']: item
                 for item in approved['approval']['confirmations']}
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['value'] == catalog[
        'SCHEDULE_MISMATCH_CONFIRM']['value']
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['disposition'] == 'confirmed'
    assert snapshots['COSMETIC_NOTE']['disposition'] == 'unconfirmed'
    assert approved['approval']['credential'] == 'review-link:kid:jti-issued-to'


def test_approval_auto_confirms_verified_facts_without_per_item_decisions(tmp_path):
    path = tmp_path / 'status.json'
    state = write_generation(
        path, 'athlete-m', order_id='cs_auto_facts',
        required_confirmations=[{
            'id': 'SCHEDULE_MISMATCH_CONFIRM', 'source': 'post_render',
            'message': 'Sunday intensity needs confirmation.',
        }],
    )
    state = _seal(path, tmp_path)
    required_only = [
        decision for decision in _decisions(state)
        if decision['item_id'] == 'SCHEDULE_MISMATCH_CONFIRM'
    ]
    approved = transition(
        path, APPROVED, 'review-link-credential', expected_revision=1,
        expected_catalog_digest=state['review_catalog_digest'],
        review_decisions=required_only,
        credential='review-link:kid:jti-issued-to',
    )
    snapshots = {item['item_id']: item
                 for item in approved['approval']['confirmations']}
    assert snapshots['SCHEDULE_MISMATCH_CONFIRM']['disposition'] == 'confirmed'
    fact_ids = [
        item['item_id'] for item in state['review_items']
        if item['type'] == 'verified_fact'
    ]
    assert fact_ids
    for item_id in fact_ids:
        assert snapshots[item_id]['disposition'] == 'confirmed'


@pytest.mark.parametrize('decisions, message', [
    ([{'item_id': 'UNKNOWN', 'revision': 1, 'disposition': 'confirmed'}],
     'unknown review item'),
    ([{'item_id': 'REQUIRED', 'revision': 2, 'disposition': 'confirmed'}],
     'revision mismatch'),
])
def test_approval_snapshot_rejects_unknown_or_wrong_revision_items(
    tmp_path, decisions, message,
):
    path = tmp_path / 'status.json'
    state = write_generation(
        path, 'athlete-m', order_id='cs_bad_snapshot',
        required_confirmations=[{
            'id': 'REQUIRED', 'source': 'fixture', 'message': 'Confirm me.',
        }])
    state = _seal(path, tmp_path)
    decisions.extend(
        item for item in _decisions(state)
        if item['item_id'].startswith('FACT_')
    )
    with pytest.raises(FulfillmentStateError, match=message):
        transition(
            path, APPROVED, 'operator', expected_revision=1,
            expected_catalog_digest=state['review_catalog_digest'],
            review_decisions=decisions, credential='operator-secret')


def test_incomplete_legacy_approval_snapshot_grants_no_release_authority(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_old_approval')
    state = _seal(path, tmp_path)
    state = _approve(path, 'operator')
    raw = json.loads(path.read_text())
    raw['approval'].pop('confirmations')
    path.write_text(json.dumps(raw))
    incomplete = load(path)
    assert incomplete['status'] == APPROVED
    assert approval_matches_release(incomplete) is False
    with pytest.raises(FulfillmentStateError, match='complete seal-bound'):
        transition(
            path, APPLIED, 'operator', platform='manual',
            evidence='must not accept incomplete approval')


def test_seal_detects_same_revision_mutation(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_seal')
    state = _seal(path, tmp_path)
    root = tmp_path / 'artifacts'
    verify_release_manifest(state, root)
    (root / 'guide.html').write_text('mutated')
    with pytest.raises(FulfillmentStateError, match='sealed artifact mismatch'):
        verify_release_manifest(path, root)


def test_approval_after_sealed_byte_mutation_fails_and_materializes_blocker(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_seal_approval')
    _seal(path, tmp_path)
    (tmp_path / 'artifacts' / 'guide.html').write_text('mutated after seal')

    with pytest.raises(FulfillmentStateError, match='approval refused'):
        _approve(path)

    state = load(path)
    assert state['status'] == BLOCKED_REVIEW
    assert state['generation_revision'] == 2
    assert state['model_seal'] is None
    mismatch = next(i for i in state['blocking_issues']
                    if i['id'] == 'SEAL_MISMATCH')
    assert mismatch['waivable'] is False
    assert state['approval'] is None


def test_application_reverifies_seal_and_materializes_mismatch(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(
        path, 'athlete-m', order_id='cs_apply_seal',
        delivery_platform='trainingpeaks')
    _seal(path, tmp_path)
    _approve(path)
    (tmp_path / 'artifacts' / 'guide.html').write_text('mutated after approval')

    with pytest.raises(FulfillmentStateError, match='application refused'):
        transition(
            path, APPLIED, 'coach@example.test',
            platform='trainingpeaks', evidence='TP 123')

    state = load(path)
    assert state['status'] == BLOCKED_REVIEW
    assert state['generation_revision'] == 2
    assert state['model_seal'] is None
    mismatch = next(
        issue for issue in state['blocking_issues']
        if issue['id'] == 'SEAL_MISMATCH')
    assert mismatch['waivable'] is False
    assert state['application'] is None


def test_seal_mismatch_preserves_all_prior_decision_evidence(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(
        path, 'athlete-m', order_id='cs_full_provenance',
        delivery_platform='trainingpeaks',
        blocking_issues=[{
            'id': 'R05', 'source': 'fixture', 'severity': 'CRITICAL',
            'message': 'Coach must review an intensity exception.',
            'review_value': {'week': 8, 'hard_sessions': 1},
            'basis': 'rendered workout inventory', 'sensitivity': 'internal',
        }],
        required_confirmations=[{
            'id': 'FTP_TARGET_CONFIRM', 'source': 'fixture',
            'message': 'Confirm the displayed FTP target.',
            'review_value': {'ftp_watts': 287, 'display': '287 W'},
            'basis': 'coach-reviewed athlete threshold test',
            'sensitivity': 'personal',
        }],
    )
    _seal(path, tmp_path)
    current = load(path)
    approved = transition(
        path, APPROVED, 'coach@example.test',
        waiver={
            'rule_ids': ['R05'],
            'reason': 'Reviewed week 8 and accepted the exception.',
        },
        expected_revision=current['generation_revision'],
        expected_catalog_digest=current['review_catalog_digest'],
        review_decisions=_decisions(current),
        credential='review-link:coach-v2:jti-provenance',
    )
    transition(
        path, APPLIED, 'coach@example.test', platform='trainingpeaks',
        evidence='TP receipt 12345')
    confirm_after_send(
        path, lambda: True,
        metadata={'message_id': 'gmail-message-123', 'recipient': 'athlete@test.invalid'},
    )
    prior = load(path)

    superseded = record_seal_mismatch(path, 'sealed artifact mismatch: guide.html')
    assert superseded['status'] == BLOCKED_REVIEW
    assert superseded['generation_revision'] == 2
    assert superseded['approval'] is None
    assert superseded['waiver'] is None
    assert superseded['application'] is None
    assert superseded['confirmation'] is None
    assert approval_matches_release(superseded) is False
    archived = superseded['superseded_approvals'][0]
    assert archived['authoritative'] is False
    assert archived['approval'] == prior['approval'] == approved['approval']
    assert archived['waiver'] == prior['waiver']
    assert archived['application'] == prior['application']
    assert archived['confirmation'] == prior['confirmation']
    assert archived['model_seal'] == prior['model_seal']
    assert archived['release_manifest_digest'] == prior['release_manifest_digest']
    assert archived['approval']['credential'] == 'review-link:coach-v2:jti-provenance'
    assert archived['waiver']['reason'] == (
        'Reviewed week 8 and accepted the exception.')
    snapshots = {
        item['item_id']: item for item in archived['approval']['confirmations']
    }
    assert snapshots['FTP_TARGET_CONFIRM']['value']['ftp_watts'] == 287
    assert snapshots['FTP_TARGET_CONFIRM']['disposition'] == 'confirmed'
    assert snapshots['R05']['value'] == {'week': 8, 'hard_sessions': 1}
    assert snapshots['R05']['disposition'] == 'resolved:waived'

    regenerated = write_generation(
        path, 'athlete-m', order_id='cs_full_provenance',
        delivery_platform='trainingpeaks')
    assert regenerated['generation_revision'] == 3
    assert regenerated['superseded_approvals'] == superseded[
        'superseded_approvals']


def test_phase1_endure_application_is_disabled_but_manual_attestation_is_allowed(
    tmp_path,
):
    endure_path = tmp_path / 'endure.json'
    write_generation(
        endure_path, 'athlete-m', order_id='cs_endure',
        delivery_platform='endure')
    _seal(endure_path, tmp_path)
    _approve(endure_path)
    with pytest.raises(FulfillmentStateError, match='D4/R9 condition 11'):
        transition(
            endure_path, APPLIED, 'coach@example.test',
            platform='endure', evidence='x')
    assert load(endure_path)['status'] == APPROVED

    manual_root = tmp_path / 'manual-artifacts'
    manual_root.mkdir()
    (manual_root / 'guide.html').write_text('manual sealed guide')
    manual_path = tmp_path / 'manual.json'
    write_generation(
        manual_path, 'athlete-m', order_id='cs_manual',
        delivery_platform='manual')
    state = load(manual_path)
    finalize_transitional_release(
        manual_path, manual_root,
        expected_revision=state['generation_revision'])
    _approve(manual_path)
    applied = transition(
        manual_path, APPLIED, 'coach@example.test',
        platform='manual', evidence='coach-attested inventory')
    assert applied['status'] == APPLIED
    assert applied['application']['platform'] == 'manual'


def test_download_handle_is_the_verified_descriptor_not_a_reopen(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_handle')
    _seal(path, tmp_path)
    _approve(path)
    artifact = tmp_path / 'artifacts' / 'guide.html'

    handle = open_verified_release_artifact(
        path, tmp_path / 'artifacts', 'guide.html')
    replacement = tmp_path / 'replacement.html'
    replacement.write_text('unsealed replacement')
    os.replace(replacement, artifact)
    try:
        assert handle.read() == b'sealed guide'
    finally:
        handle.close()


def test_schema_accepts_only_journaled_phase5_transitional_statuses(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_future_status')
    raw = json.loads(path.read_text())
    raw['status'] = CANCELLED
    path.write_text(json.dumps(raw))
    assert load(path)['status'] == CANCELLED
    raw['status'] = 'APPLYING'
    path.write_text(json.dumps(raw))
    with pytest.raises(FulfillmentStateError, match='malformed'):
        load(path)
    raw['application_attempt'] = {
        'jti': 'phase5-fixture-jti', 'action': 'apply',
        'request_digest': 'a' * 64, 'status': 'running',
        'execution_epoch': 0, 'fencing_token': 1,
        'lease': {'athlete_key_digest': 'b' * 64,
                  'expires_at': '2026-08-22T01:00:00Z'},
        'landed': [], 'intents': [], 'receipt_ref': '/fixture/receipt.json',
    }
    raw['execution_fence'] = 1
    path.write_text(json.dumps(raw))
    assert load(path)['status'] == 'APPLYING'
    raw['status'] = 'APPLIED_ATTESTED'
    path.write_text(json.dumps(raw))
    assert load(path)['status'] == 'APPLIED_ATTESTED'


def test_preapply_cancellation_is_durable_and_audit_ready(tmp_path):
    path = tmp_path / 'cancel.json'
    write_generation(path, 'daily-drill', order_id='drill-20260812')
    cancelled = transition(
        path, CANCELLED, 'daily-drill-cleanup',
        credential='operator-secret', metadata={'reason': 'daily cleanup'})
    assert cancelled['status'] == CANCELLED
    assert cancelled['cancel_requested'] is True
    assert cancelled['execution_epoch'] == 1
    assert cancelled['cancellation']['worker_stop_acknowledged'] is True
    assert cancelled['cancellation']['reason'] == 'daily cleanup'


def test_cancellation_refuses_to_hide_application_evidence(tmp_path):
    path = tmp_path / 'applied.json'
    write_generation(
        path, 'daily-drill', order_id='drill-20260812',
        delivery_platform='manual')
    _seal(path, tmp_path)
    _approve(path)
    transition(
        path, APPLIED, 'coach@example.test', platform='manual',
        evidence='coach-attested inventory')
    with pytest.raises(FulfillmentStateError, match='compensation workflow'):
        transition(path, CANCELLED, 'daily-drill-cleanup')
    assert load(path)['status'] == APPLIED


def test_v1_migration_quarantines_and_tombstones(tmp_path):
    old = tmp_path / 'athlete' / 'fulfillment_status.json'
    old.parent.mkdir()
    original = {
        'schema_version': 1, 'athlete_id': 'athlete-m',
        'generation_revision': 2, 'status': 'APPROVED',
        'blocking_issues': [], 'approval': {'coach': 'old'},
        'waiver': None, 'application': None, 'confirmation': None,
        'history': [], 'updated_at': '2026-08-01T00:00:00Z',
    }
    old.write_text(json.dumps(original))
    destination, state = migrate_v1_to_quarantine(
        old, tmp_path / 'orders', ledger_candidates=['cs_candidate'])
    assert destination.exists()
    assert state['legacy'] is True
    assert state['legacy_original_evidence'] == original
    assert json.loads(old.read_text())['schema_version'] == 'tombstone/v1'
    with pytest.raises(FulfillmentStateError, match='quarantined'):
        transition(destination, APPROVED, 'coach')
    bound = bind_legacy_order(destination, 'cs_candidate', 'coach')
    assert bound['legacy_binding']['ledger_order_id'] == 'cs_candidate'
    with pytest.raises(FulfillmentStateError, match='must be regenerated'):
        transition(destination, APPLIED, 'coach', platform='trainingpeaks',
                   evidence='legacy evidence')
    with pytest.raises(FulfillmentStateError, match='must be regenerated'):
        confirm_after_send(destination, lambda: pytest.fail('must not send'))
