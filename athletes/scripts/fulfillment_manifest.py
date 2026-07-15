"""I1 platform-neutral fulfillment manifest serialized from PlanIR.

This module deliberately has no HTTP imports.  Delivery adapters consume this
file; generating it is safe for package creation and tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


MANIFEST_VERSION = 1
SPORT_TYPES = {'cycling': 1, 'road': 1, 'gravel': 1, 'mtb': 8, 'mountain_bike': 8}


def _sport_type(session: Dict[str, Any]) -> int:
    return SPORT_TYPES.get(str(session.get('sport', 'cycling')).lower(), 1)


def build_manifest_from_plan_ir(ir: Dict[str, Any], athlete_dir: Path | str) -> dict:
    """Project a parsed PlanIR dictionary to an adapter-neutral manifest."""
    athlete_dir = Path(athlete_dir)
    workouts, notes = [], []
    for week in ir.get('weeks', []):
        for sequence, session in enumerate(week.get('sessions', []), 1):
            # A platform operation gets a stable identity; title alone is not
            # stable because plans legitimately repeat Endurance every week.
            external_id = f"{ir['athlete']['id']}:w{week.get('number')}:{sequence}:{session.get('date') or 'undated'}"
            item = {
                'external_id': external_id,
                'plan_week': week.get('number'), 'date': session.get('date'),
                'title': session.get('title', 'Untitled session'),
                'workout_type': _sport_type(session), 'sport': session.get('sport', 'cycling'),
                'session_type': session.get('type', 'workout'), 'origin': session.get('origin', 'prescribed'),
                'duration_s': int(session.get('duration_s', 0) or 0),
                'segments': session.get('segments', []), 'source_file': session.get('source_file'),
            }
            workouts.append(item)
            notes.append({
                'external_id': f"note:{external_id}", 'date': item['date'],
                'title': item['title'],
                'text': f"Week {item['plan_week']} · {item['title']} · {item['session_type']}",
            })

    attachments = [dict(attachment) for attachment in (ir.get('attachments') or [])]
    if not any(a.get('kind') == 'guide' for a in attachments):
        guide = 'training_guide.pdf' if (athlete_dir / 'training_guide.pdf').exists() else 'training_guide.html'
        attachments.append({'id': 'guide', 'external_id': 'attachment:guide', 'path': guide, 'kind': 'guide'})
    for attachment in attachments:
        attachment.setdefault('external_id', f"attachment:{attachment.get('id') or attachment.get('path')}")
    target = ir.get('race_snapshot') or {}
    tasks = [note for note in (ir.get('notes') or [])
             if note.get('kind') in ('mental_training', 'mental_task')]
    entitlement = next((e for e in (ir.get('entitlements') or [])
                        if e.get('kind') == 'course'), None)
    if entitlement is None:
        entitlement = {
            'kind': 'course', 'external_id': f"entitlement:{target.get('name')}:{target.get('date')}",
            'race': target.get('name'), 'race_date': target.get('date'),
            'course_variant': target.get('course_variant'),
        }
    else:
        entitlement = dict(entitlement)
        entitlement.setdefault('external_id', f"entitlement:{entitlement.get('race')}:{entitlement.get('race_date')}")
    dates = sorted({workout['date'] for workout in workouts if workout.get('date')})
    return {
        'schema_version': MANIFEST_VERSION,
        'athlete_id': ir['athlete']['id'],
        'workouts': workouts,
        'calendar_dates': dates,
        'native_notes': notes,
        'attachments': attachments,
        'mental_training_tasks': tasks,
        'course_entitlement': entitlement,
        'verification_expectations': {
            'workout_count': len(workouts), 'note_count': len(notes),
            'attachment_count': len(attachments), 'read_back': True,
            'required_external_ids': [workout['external_id'] for workout in workouts],
        },
    }


def build_fulfillment_manifest(athlete_dir: Path | str) -> dict:
    athlete_dir = Path(athlete_dir)
    ir = json.loads((athlete_dir / 'plan_ir.json').read_text())
    manifest = build_manifest_from_plan_ir(ir, athlete_dir)
    (athlete_dir / 'fulfillment_manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest
