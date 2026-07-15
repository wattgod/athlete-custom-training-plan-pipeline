"""Versioned, resumable TrainingPeaks adapter for an I1 manifest.

The endpoints are undocumented and intentionally isolated here.  The adapter
uses manifest external IDs plus a durable operation log; it never appends a
second calendar object on retry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import requests


class TrainingPeaksReadbackMismatch(RuntimeError):
    pass


class TrainingPeaksAdapter:
    api_version = 'tp-undocumented-v1'

    def __init__(self, base_url: str, token: str, op_log: Path | str, *, dry_run: bool = False):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.op_log = Path(op_log)
        self.dry_run = dry_run
        self.op_log.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(self.op_log.read_text()) if self.op_log.exists() else {}
        # ``done`` is retained for the partial foundation's existing logs.
        self.done = set(data.get('done', []))
        self.operations = data.get('operations', {})

    def _save(self) -> None:
        self.op_log.write_text(json.dumps({
            'version': self.api_version, 'done': sorted(self.done),
            'operations': self.operations,
        }, indent=2, sort_keys=True) + '\n')

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
        if self.dry_run:
            return {'dry_run': True}
        headers = {'Authorization': f'Bearer {self.token}'}
        if payload and payload.get('external_id'):
            headers['Idempotency-Key'] = str(payload['external_id'])
        response = requests.request(method, self.base_url + path, json=payload,
                                    headers=headers, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}

    def _upsert(self, key: str, path: str, payload: Dict[str, Any]) -> bool:
        """Run exactly one idempotent remote operation and checkpoint it."""
        if key in self.done:
            return False
        if self.dry_run:
            return True
        response = self._request('POST', path, payload)
        self.done.add(key)
        self.operations[key] = {'path': path, 'external_id': payload['external_id'], 'response': response}
        self._save()
        return True

    @staticmethod
    def _id(prefix: str, item: Dict[str, Any], fallback: str) -> str:
        return f"{prefix}:{item.get('external_id') or fallback}"

    def apply(self, athlete_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        created = 0
        for index, workout in enumerate(manifest.get('workouts', []), 1):
            external_id = workout.get('external_id') or f"workout:{workout.get('date')}:{workout.get('title')}"
            payload = {
                'external_id': external_id, 'title': workout['title'], 'date': workout.get('date'),
                'duration': workout.get('duration_s'),
                'sportType': int(workout.get('workout_type', 8 if workout.get('sport') == 'mtb' else 1)),
                'segments': workout.get('segments', []),
            }
            created += self._upsert(self._id('workout', workout, str(index)),
                                    f'/fitness/v6/athletes/{athlete_id}/workouts', payload)
        for index, note in enumerate(manifest.get('native_notes', []), 1):
            external_id = note.get('external_id') or f"note:{note.get('date')}:{note.get('title')}"
            created += self._upsert(self._id('note', note, str(index)),
                                    f'/fitness/v1/athletes/{athlete_id}/calendarNote',
                                    {'external_id': external_id, **note})
        for index, attachment in enumerate(manifest.get('attachments', []), 1):
            external_id = attachment.get('external_id') or f"attachment:{attachment.get('id') or attachment.get('path')}"
            created += self._upsert(self._id('attachment', attachment, str(index)),
                                    f'/fitness/v1/athletes/{athlete_id}/attachments',
                                    {'external_id': external_id, **attachment})
        entitlement = manifest.get('course_entitlement')
        if entitlement:
            external_id = entitlement.get('external_id') or f"entitlement:{entitlement.get('race')}:{entitlement.get('race_date')}"
            created += self._upsert('entitlement:course',
                                    f'/fitness/v1/athletes/{athlete_id}/entitlements',
                                    {'external_id': external_id, **entitlement})
        return {'status': 'dry_run' if self.dry_run else 'applied',
                'created': created, 'operations': len(self.done)}

    def _read(self, athlete_id: str, suffix: str) -> list[Dict[str, Any]]:
        result = self._request('GET', f'/fitness/v1/athletes/{athlete_id}/{suffix}')
        # Workout readback is documented in the v6 family; other calendar
        # resources are v1.  Fake/live response bodies may be list or wrapper.
        if isinstance(result, dict):
            result = result.get('items', result.get(suffix, []))
        return result if isinstance(result, list) else []

    @staticmethod
    def _missing(expected: Iterable[Dict[str, Any]], actual: Iterable[Dict[str, Any]]) -> list[str]:
        actual_ids = {str(x.get('external_id') or x.get('externalId')) for x in actual}
        return [str(x.get('external_id') or x.get('externalId') or x.get('title'))
                for x in expected
                if str(x.get('external_id') or x.get('externalId')) not in actual_ids]

    def verify(self, athlete_id: str, manifest: Dict[str, Any]) -> None:
        if self.dry_run:
            return
        workouts = self._request('GET', f'/fitness/v6/athletes/{athlete_id}/workouts')
        if isinstance(workouts, dict):
            workouts = workouts.get('items', workouts.get('workouts', []))
        checks = [
            ('workouts', manifest.get('workouts', []), workouts if isinstance(workouts, list) else []),
            ('notes', manifest.get('native_notes', []), self._read(athlete_id, 'calendarNote')),
            ('attachments', manifest.get('attachments', []), self._read(athlete_id, 'attachments')),
            ('entitlements', [manifest['course_entitlement']] if manifest.get('course_entitlement') else [],
             self._read(athlete_id, 'entitlements')),
        ]
        mismatches = {kind: self._missing(expected, actual) for kind, expected, actual in checks if self._missing(expected, actual)}
        if mismatches:
            raise TrainingPeaksReadbackMismatch(f'read-back mismatch: {mismatches}')

    def apply_and_mark_applied(self, athlete_id: str, manifest: Dict[str, Any], state_path: Path | str, coach: str) -> Dict[str, Any]:
        """Only enter J1 APPLIED after a complete successful calendar readback."""
        result = self.apply(athlete_id, manifest)
        self.verify(athlete_id, manifest)
        if self.dry_run:
            return result
        from fulfillment_state import APPLIED, transition
        transition(state_path, APPLIED, coach, platform='trainingpeaks',
                   evidence=json.dumps({'adapter': self.api_version, 'operations': len(self.done)}),
                   metadata={'adapter': self.api_version})
        return result
