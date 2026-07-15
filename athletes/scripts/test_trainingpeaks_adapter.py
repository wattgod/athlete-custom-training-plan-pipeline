"""I2 contract tests against an in-process fake TP server, never live TP."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'webhook'))

from delivery.trainingpeaks import TrainingPeaksAdapter, TrainingPeaksReadbackMismatch
from fulfillment_state import APPROVED, load, transition, write_generation


class FakeTP:
    def __init__(self, *, fail_once_path=None, mismatch=False):
        self.items = {'workouts': [], 'calendarNote': [], 'attachments': [], 'entitlements': []}
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


def test_first_apply_creates_and_second_apply_is_idempotent(tmp_path, manifest):
    fake = FakeTP()
    try:
        adapter = TrainingPeaksAdapter(fake.url, 'test', tmp_path / 'ops.json')
        assert adapter.apply('7', manifest)['created'] == 4
        adapter.verify('7', manifest)
        before = len([c for c in fake.calls if c[0] == 'POST'])
        assert TrainingPeaksAdapter(fake.url, 'test', tmp_path / 'ops.json').apply('7', manifest)['created'] == 0
        assert len([c for c in fake.calls if c[0] == 'POST']) == before
        assert fake.items['workouts'][0]['sportType'] == 8
    finally:
        fake.close()


def test_partial_failure_resumes_from_checkpoint(tmp_path, manifest):
    fake = FakeTP(fail_once_path='calendarNote')
    try:
        adapter = TrainingPeaksAdapter(fake.url, 'test', tmp_path / 'ops.json')
        with pytest.raises(Exception):
            adapter.apply('7', manifest)
        assert len(fake.items['workouts']) == 1
        resumed = TrainingPeaksAdapter(fake.url, 'test', tmp_path / 'ops.json')
        assert resumed.apply('7', manifest)['created'] == 3
        resumed.verify('7', manifest)
        assert len(fake.items['workouts']) == len(fake.items['calendarNote']) == 1
    finally:
        fake.close()


def test_readback_mismatch_never_marks_j1_applied(tmp_path, manifest):
    fake = FakeTP(mismatch=True)
    state_path = tmp_path / 'fulfillment_status.json'
    write_generation(state_path, 'heather')
    transition(state_path, APPROVED, 'coach@example.test')
    try:
        adapter = TrainingPeaksAdapter(fake.url, 'test', tmp_path / 'ops.json')
        with pytest.raises(TrainingPeaksReadbackMismatch):
            adapter.apply_and_mark_applied('7', manifest, state_path, 'coach@example.test')
        assert load(state_path)['status'] == APPROVED
    finally:
        fake.close()
