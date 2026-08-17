#!/usr/bin/env python3
"""Tests for webhook/consultations.py — the consultation record store.

Run with: pytest webhook/tests/test_consultations.py -v
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import consultations


@pytest.fixture
def deliveries_dir(tmp_path):
    return tmp_path / 'deliveries'


def _write_new(deliveries_dir, order_id='cs_test_123', **overrides):
    record = consultations.new_record(
        order_id=order_id, brand='gravelgod', athlete_name='Jesse Couch',
        athlete_email='jesse@example.com', hours=1, amount_cents=15000,
    )
    record.update(overrides)
    consultations.write_record(deliveries_dir, record)
    return record


class TestSafeOrderId:
    def test_accepts_valid_ids(self):
        assert consultations.safe_order_id('cs_test_ABC123-_') == 'cs_test_ABC123-_'

    @pytest.mark.parametrize('bad', ['', '../etc/passwd', 'has space', 'a/b', None])
    def test_rejects_unsafe_ids(self, bad):
        with pytest.raises(consultations.ConsultationError):
            consultations.safe_order_id(bad)

    def test_underscore_alias_matches(self):
        """app.py call sites use the leading-underscore alias."""
        assert consultations._safe_order_id is consultations.safe_order_id


class TestRecordShape:
    def test_new_record_has_spec_shape(self):
        record = consultations.new_record(
            order_id='cs_abc', brand='gravelgod', athlete_name='A',
            athlete_email='a@b.com')
        assert record['order_id'] == 'cs_abc'
        assert record['status'] == 'open'
        assert record['welcome_sent_at'] is None
        assert record['athlete']['tp_matched_at'] is None
        assert record['products']['consult']['amount'] == 15000
        assert record['products']['plan_addon']['purchased'] is False
        assert record['intake']['intake_id'] is None
        assert record['call_at'] is None
        assert record['analysis']['attempts'] == 0
        assert record['closed_reason'] is None
        assert record['timeline'][0]['event'] == 'paid'
        assert record['nudges_sent'] == []

    def test_plan_addon_purchased_at_checkout(self):
        record = consultations.new_record(
            order_id='cs_addon', brand='gravelgod', plan_addon=True)
        assert record['products']['plan_addon']['purchased'] is True
        assert record['products']['plan_addon']['purchased_at'] is not None


class TestWriteReadUpdate:
    def test_write_then_read_round_trips(self, deliveries_dir):
        record = _write_new(deliveries_dir)
        loaded = consultations.read_record(deliveries_dir, 'cs_test_123')
        assert loaded == record

    def test_read_missing_returns_none(self, deliveries_dir):
        assert consultations.read_record(deliveries_dir, 'cs_missing') is None

    def test_read_invalid_order_id_returns_none(self, deliveries_dir):
        assert consultations.read_record(deliveries_dir, '../etc/passwd') is None

    def test_write_is_atomic_no_partial_file(self, deliveries_dir):
        _write_new(deliveries_dir)
        path = consultations.record_path(deliveries_dir, 'cs_test_123')
        assert path.exists()
        # No leftover temp files.
        leftovers = [p for p in path.parent.iterdir() if p.name.startswith('.')]
        assert leftovers == []

    def test_update_record_mutates_and_persists(self, deliveries_dir):
        _write_new(deliveries_dir)

        def _mutate(r):
            r['status'] = 'analysis_running'

        updated = consultations.update_record(deliveries_dir, 'cs_test_123', _mutate)
        assert updated['status'] == 'analysis_running'
        reloaded = consultations.read_record(deliveries_dir, 'cs_test_123')
        assert reloaded['status'] == 'analysis_running'

    def test_update_missing_record_raises(self, deliveries_dir):
        with pytest.raises(consultations.ConsultationError):
            consultations.update_record(deliveries_dir, 'cs_nope', lambda r: None)

    def test_never_deletes_closed_terminal(self, deliveries_dir):
        _write_new(deliveries_dir)
        consultations.update_record(
            deliveries_dir, 'cs_test_123',
            lambda r: (r.update(status='closed', closed_reason='delivered')))
        assert consultations.read_record(deliveries_dir, 'cs_test_123')['status'] == 'closed'
        # File still exists — closed is terminal, never deleted.
        assert consultations.record_path(deliveries_dir, 'cs_test_123').exists()


class TestTimeline:
    def test_append_timeline_appends(self, deliveries_dir):
        record = _write_new(deliveries_dir)
        consultations.append_timeline(record, 'welcome_sent', 'ok')
        assert record['timeline'][-1]['event'] == 'welcome_sent'
        assert record['timeline'][-1]['detail'] == 'ok'
        assert 'at' in record['timeline'][-1]

    def test_append_unknown_event_raises(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        with pytest.raises(consultations.ConsultationError):
            consultations.append_timeline(record, 'not_a_real_event')

    def test_every_event_appends_one_entry(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        start_len = len(record['timeline'])
        for event in sorted(consultations.TIMELINE_EVENTS):
            consultations.append_timeline(record, event)
        assert len(record['timeline']) == start_len + len(consultations.TIMELINE_EVENTS)


class TestListRecords:
    def test_lists_all_written_records_sorted(self, deliveries_dir):
        _write_new(deliveries_dir, order_id='cs_b')
        _write_new(deliveries_dir, order_id='cs_a')
        records = consultations.list_records(deliveries_dir)
        assert [r['order_id'] for r in records] == ['cs_a', 'cs_b']

    def test_empty_dir_returns_empty_list(self, deliveries_dir):
        assert consultations.list_records(deliveries_dir) == []

    def test_skips_unreadable_files(self, deliveries_dir):
        _write_new(deliveries_dir, order_id='cs_ok')
        root = consultations.consultations_root(deliveries_dir)
        (root / 'cs_bad.json').write_text('{not json')
        records = consultations.list_records(deliveries_dir)
        assert [r['order_id'] for r in records] == ['cs_ok']


class TestReadiness:
    def test_not_ready_without_tp_match(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        assert consultations.is_ready_for_analysis(record) is False

    def test_ready_once_tp_matched(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        record['athlete']['tp_matched_at'] = consultations.now_iso()
        assert consultations.is_ready_for_analysis(record) is True

    def test_readiness_does_not_require_intake(self):
        """Spec §1: intake optional but preferred — TP link alone is enough."""
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        record['athlete']['tp_matched_at'] = consultations.now_iso()
        assert record['intake']['intake_id'] is None
        assert consultations.is_ready_for_analysis(record) is True


class TestGiveUpRule:
    def test_no_give_up_before_30_days(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        now = datetime.now(timezone.utc)
        assert consultations.should_give_up(record, now=now + timedelta(days=29)) is False

    def test_gives_up_after_30_days_no_tp_link(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        now = datetime.now(timezone.utc)
        assert consultations.should_give_up(record, now=now + timedelta(days=31)) is True

    def test_never_gives_up_once_tp_linked(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        record['athlete']['tp_matched_at'] = consultations.now_iso()
        now = datetime.now(timezone.utc)
        assert consultations.should_give_up(record, now=now + timedelta(days=60)) is False

    def test_closed_records_never_give_up(self):
        record = consultations.new_record(order_id='cs_x', brand='gravelgod')
        record['status'] = 'closed'
        now = datetime.now(timezone.utc)
        assert consultations.should_give_up(record, now=now + timedelta(days=60)) is False
