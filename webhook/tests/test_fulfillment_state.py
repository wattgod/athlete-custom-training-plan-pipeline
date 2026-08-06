"""Focused J1 state-machine tests (kept independent of Flask fixtures)."""

import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fulfillment_state import (APPLIED, APPROVED, BLOCKED_REVIEW, CONFIRMED,
                               GENERATED, FulfillmentStateError, bind_legacy_order,
                               confirm_after_send, finalize_transitional_release,
                               load, merge_generation_blockers,
                               migrate_v1_to_quarantine, transition,
                               verify_release_manifest, write_generation)


def _issue(rule_id="R05"):
    return {'id': rule_id, 'source': 'block_compliance', 'severity': 'CRITICAL',
            'message': 'Intensity count: W8 has one hard session'}


def _seal(path, tmp_path):
    root = tmp_path / 'artifacts'
    root.mkdir(exist_ok=True)
    (root / 'guide.html').write_text('sealed guide')
    state = load(path)
    return finalize_transitional_release(
        path, root, expected_revision=state['generation_revision'])


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
        transition(path, APPROVED, 'coach@example.test', waiver={'rule_ids': ['R05'], 'reason': 'no'})
    state = transition(path, APPROVED, 'coach@example.test', waiver={
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
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    transition(path, APPROVED, 'coach@example.test')
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    calls = []
    assert confirm_after_send(path, lambda: calls.append(True) or True)[0] == 'confirmed'
    assert calls == [True]
    assert load(path)['status'] == CONFIRMED


def test_confirm_email_failure_leaves_applied(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    transition(path, APPROVED, 'coach@example.test')
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    with pytest.raises(RuntimeError):
        confirm_after_send(path, lambda: False)
    assert load(path)['status'] == APPLIED


def test_confirmed_retry_is_idempotent(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    transition(path, APPROVED, 'coach@example.test')
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    confirm_after_send(path, lambda: True)
    assert confirm_after_send(path, lambda: pytest.fail('must not send'))[0] == 'idempotent'


def test_concurrent_confirm_sends_once(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    transition(path, APPROVED, 'coach@example.test')
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    calls, results = [], []
    threads = [threading.Thread(target=lambda: results.append(confirm_after_send(
        path, lambda: calls.append(True) or True)[0])) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert calls == [True]
    assert sorted(results) == ['confirmed', 'idempotent']


def test_missing_or_malformed_state_fails_closed(tmp_path):
    with pytest.raises(FulfillmentStateError):
        confirm_after_send(tmp_path / 'absent.json', lambda: True)
    path = tmp_path / 'bad.json'
    path.write_text('{bad')
    with pytest.raises(FulfillmentStateError):
        load(path)


def test_regeneration_invalidates_prior_approval_and_application(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'heather_gray')
    _seal(path, tmp_path)
    transition(path, APPROVED, 'coach@example.test')
    transition(path, APPLIED, 'coach@example.test', platform='trainingpeaks', evidence='TP 123')
    state = write_generation(path, 'heather_gray')
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
        transition(path, APPROVED, 'coach', waiver={
            'rule_ids': ['FTP_ESTIMATED'], 'reason': 'accept'})
    assert state['blocking_issues'][0]['waivable'] is False


def test_seal_detects_same_revision_mutation(tmp_path):
    path = tmp_path / 'status.json'
    write_generation(path, 'athlete-m', order_id='cs_seal')
    state = _seal(path, tmp_path)
    root = tmp_path / 'artifacts'
    verify_release_manifest(state, root)
    (root / 'guide.html').write_text('mutated')
    with pytest.raises(FulfillmentStateError, match='sealed artifact mismatch'):
        verify_release_manifest(path, root)


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
