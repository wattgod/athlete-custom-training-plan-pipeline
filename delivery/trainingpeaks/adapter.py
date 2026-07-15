"""Resumable, idempotent adapter for TrainingPeaks calendar endpoints."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
import requests


class TrainingPeaksReadbackMismatch(RuntimeError): pass


class TrainingPeaksAdapter:
    api_version = 'tp-undocumented-v1'
    def __init__(self, base_url: str, token: str, op_log: Path | str, *, dry_run=False):
        self.base_url, self.token, self.op_log, self.dry_run = base_url.rstrip('/'), token, Path(op_log), dry_run
        self.op_log.parent.mkdir(parents=True, exist_ok=True)
        self.done = set(json.loads(self.op_log.read_text()).get('done', [])) if self.op_log.exists() else set()
    def _save(self): self.op_log.write_text(json.dumps({'version': self.api_version, 'done': sorted(self.done)}, indent=2))
    def _request(self, method, path, payload):
        if self.dry_run: return {'dry_run': True}
        response = requests.request(method, self.base_url + path, json=payload,
            headers={'Authorization': f'Bearer {self.token}', 'Idempotency-Key': payload['external_id']}, timeout=15)
        response.raise_for_status(); return response.json() if response.content else {}
    def apply(self, athlete_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        for workout in manifest.get('workouts', []):
            key = f"workout:{workout.get('date')}:{workout['title']}"
            if key in self.done: continue
            payload = {'external_id': key, 'title': workout['title'], 'date': workout.get('date'),
                       'duration': workout.get('duration_s'), 'sportType': 8 if workout.get('sport') == 'mtb' else 1,
                       'segments': workout.get('segments', [])}
            self._request('POST', f'/fitness/v6/athletes/{athlete_id}/workouts', payload); self.done.add(key); self._save()
        for note in manifest.get('native_notes', []):
            key = f"note:{note.get('date')}:{note['title']}"
            if key in self.done: continue
            self._request('POST', f'/fitness/v1/athletes/{athlete_id}/calendarNote', {'external_id': key, **note}); self.done.add(key); self._save()
        return {'status': 'applied', 'operations': len(self.done)}
    def verify(self, athlete_id: str, manifest: Dict[str, Any]) -> None:
        if self.dry_run: return
        response = requests.get(self.base_url + f'/fitness/v6/athletes/{athlete_id}/workouts', headers={'Authorization': f'Bearer {self.token}'}, timeout=15)
        response.raise_for_status(); actual = response.json()
        titles = {item.get('title') for item in actual}
        missing = [item['title'] for item in manifest.get('workouts', []) if item['title'] not in titles]
        if missing: raise TrainingPeaksReadbackMismatch(f'read-back missing workouts: {missing}')
