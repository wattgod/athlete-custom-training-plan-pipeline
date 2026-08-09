"""I2 contract tests against an in-process fake TP server, never live TP."""
import json
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'webhook'))

from delivery.trainingpeaks import (TrainingPeaksAdapter,
                                    TrainingPeaksAdapterDisabled)
from fulfillment_state import (APPROVED, finalize_transitional_release, load,
                               transition, write_generation)


class FakeTP:
    def __init__(self, *, fail_once_path=None, mismatch=False):
        self.items = {'workouts': [], 'calendarNote': [], 'attachments': [],
                      'mentalTasks': [], 'entitlements': []}
        self.calls = []
        self.fail_once_path, self.mismatch = fail_once_path, mismatch
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def _send(self, status, body):
                payload = json.dumps(body).encode()
                self.send_response(status); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)
            def do_POST(self):
                owner.calls.append(('POST', self.path))
                if owner.fail_once_path and self.path.endswith(owner.fail_once_path):
                    owner.fail_once_path = None; return self._send(500, {'error': 'temporary'})
                data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                bucket = next(key for key in owner.items if self.path.endswith('/' + key))
                # TP idempotency behavior represented by external ID.
                if not any(item.get('external_id') == data.get('external_id') for item in owner.items[bucket]):
                    owner.items[bucket].append(data)
                self._send(200, {'ok': True})
            def do_GET(self):
                owner.calls.append(('GET', self.path))
                bucket = next(key for key in owner.items if self.path.endswith('/' + key))
                self._send(200, [] if owner.mismatch else owner.items[bucket])
        try:
            self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        except PermissionError:
            pytest.skip('workspace sandbox forbids loopback sockets; fake-TP contract runs where sockets are allowed')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    @property
    def url(self): return f'http://127.0.0.1:{self.server.server_port}'
    def close(self): self.server.shutdown(); self.thread.join()


@pytest.fixture
def manifest():
    return {
        'workouts': [{'external_id': 'w1', 'title': 'MTB skills', 'date': '2026-01-12',
                      'duration_s': 3600, 'workout_type': 8, 'segments': []}],
        'native_notes': [{'external_id': 'n1', 'title': 'Coach note', 'date': '2026-01-12', 'text': 'Hi'}],
        'attachments': [{'external_id': 'a1', 'id': 'guide', 'path': 'guide.pdf', 'kind': 'guide'}],
        'course_entitlement': {'external_id': 'e1', 'kind': 'course', 'race': 'Nannup', 'race_date': '2026-03-01'},
    }


def test_phase1_adapter_refuses_before_any_remote_write(tmp_path, manifest, monkeypatch):
    adapter = TrainingPeaksAdapter('https://tp.invalid', 'test', tmp_path / 'ops.json')
    remote_calls = []
    monkeypatch.setattr(adapter, '_request', lambda *args, **kwargs: remote_calls.append(args))

    with pytest.raises(TrainingPeaksAdapterDisabled, match='seal-bound APPROVED'):
        adapter.apply('7', manifest)

    assert remote_calls == []


def test_legacy_request_extraction_matches_unreachable_adapter_shape(manifest):
    from delivery.trainingpeaks.adapter import legacy_apply_requests

    requests = legacy_apply_requests('7', manifest)
    workout = next(item for item in requests if item['kind'] == 'workout_upsert')
    assert workout['path'] == '/fitness/v6/athletes/7/workouts'
    assert set(workout['payload']) == {
        'external_id', 'title', 'date', 'duration', 'sportType', 'segments'}
    assert workout['payload'] == {
        'external_id': 'w1', 'title': 'MTB skills', 'date': '2026-01-12',
        'duration': 3600, 'sportType': 8, 'segments': [],
    }
    assert {item['kind'] for item in requests} == {
        'workout_upsert', 'calendar_note_upsert', 'attachment_upsert',
        'course_entitlement_grant',
    }
    assert all(item['kind'] != 'mental_task_upsert' for item in requests)


def test_phase3_contract_has_fake_server_effect_parity_with_legacy_manifest(tmp_path):
    """Socket parity gate; skipped only where the sandbox forbids loopback."""
    from apply_contract import build_contract
    from fulfillment_manifest import build_manifest_from_plan_ir
    from fake_remote_parity import LEGACY_SUPPORTED_KINDS, FakeRemoteModel
    from delivery.trainingpeaks.adapter import legacy_apply_requests

    (tmp_path / 'guide.html').write_text('guide')
    ir = {
        'athlete': {'id': 'fixture'},
        'race_snapshot': {'name': 'Fixture Race', 'date': '2026-09-01'},
        'weeks': [{'number': 1, 'sessions': [{
            'date': '2026-08-14', 'title': 'Field Session', 'description': 'HR target',
            'workout_type_value_id': 2, 'duration_s': 3600, 'tss_planned': 50,
            'structure': {'primaryIntensityMetric': 'percentOfThresholdHr', 'structure': []},
            'type': 'workout', 'sport': 'cycling', 'segments': [],
        }]}],
        'notes': [{'kind': 'mental_task', 'id': 'focus', 'date': '2026-08-14',
                   'title': 'Focus', 'text': 'Breathe'}],
        'attachments': [{'id': 'guide', 'kind': 'guide', 'path': 'guide.html'}],
        'entitlements': [{'kind': 'course', 'product_id': 'course:fixture'}],
    }
    legacy = build_manifest_from_plan_ir(ir, tmp_path)
    contract = build_contract(
        ir, order_id='cs_parity', tp_athlete_id='fake-1', generation_revision=1,
        canonical_model={'model_version': 'canonical_training_model/v1'},
        review_items=[], guide_sources={}, athlete_dir=tmp_path)
    old, new = FakeTP(), FakeTP()

    def post(server, bucket, item):
        request = urllib.request.Request(
            server.url + '/' + bucket,
            data=json.dumps(item).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.status == 200

    try:
        buckets = {'workout_upsert': 'workouts', 'calendar_note_upsert': 'calendarNote',
                   'attachment_upsert': 'attachments', 'mental_task_upsert': 'mentalTasks',
                   'course_entitlement_grant': 'entitlements'}
        legacy_model = FakeRemoteModel()
        legacy_model.apply_legacy_requests(legacy_apply_requests('fake-1', legacy))
        contract_model = FakeRemoteModel()
        contract_model.apply_contract(contract)
        legacy_state = legacy_model.normalized_snapshot(kinds=LEGACY_SUPPORTED_KINDS)
        contract_state = contract_model.normalized_snapshot(kinds=LEGACY_SUPPORTED_KINDS)
        assert legacy_state == contract_state

        for key, record in sorted(legacy_state.items()):
            post(old, buckets[record['kind']], {
                'external_id': key, **record['payload']})
        for key, record in sorted(contract_state.items()):
            post(new, buckets[record['kind']], {
                'external_id': key, **record['payload']})

        # Loopback transport compares every normalized remote field, not a
        # cardinality/selected-field subset. The socket-free model above runs
        # in restricted sandboxes; this identical state crosses HTTP in CI.
        assert old.items == new.items
    finally:
        old.close(); new.close()
