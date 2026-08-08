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

from delivery.trainingpeaks import (TrainingPeaksAdapter,
                                    TrainingPeaksAdapterDisabled)
from fulfillment_state import (APPROVED, finalize_transitional_release, load,
                               transition, write_generation)


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


def test_phase1_adapter_refuses_before_any_remote_write(tmp_path, manifest, monkeypatch):
    adapter = TrainingPeaksAdapter('https://tp.invalid', 'test', tmp_path / 'ops.json')
    remote_calls = []
    monkeypatch.setattr(adapter, '_request', lambda *args, **kwargs: remote_calls.append(args))

    with pytest.raises(TrainingPeaksAdapterDisabled, match='seal-bound APPROVED'):
        adapter.apply('7', manifest)

    assert remote_calls == []
