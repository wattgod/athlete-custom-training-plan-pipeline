"""I1 platform-neutral fulfillment manifest serialized from PlanIR.

This module deliberately has no HTTP imports.  Delivery adapters consume this
file; generating it is safe for package creation and tests.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict

from delivery_notes import render_coached_weekly_notes


MANIFEST_VERSION = 1
SPORT_TYPES = {'cycling': 1, 'road': 1, 'gravel': 1, 'mtb': 8, 'mountain_bike': 8}


def _sport_type(session: Dict[str, Any]) -> int:
    return SPORT_TYPES.get(str(session.get('sport', 'cycling')).lower(), 1)


def build_manifest_from_plan_ir(ir: Dict[str, Any], athlete_dir: Path | str) -> dict:
    """Project a parsed PlanIR dictionary to an adapter-neutral manifest."""
    athlete_dir = Path(athlete_dir)
    workouts, notes = [], []
    per_date = {}
    for week in ir.get('weeks', []):
        for sequence, session in enumerate(week.get('sessions', []), 1):
            # A platform operation gets a stable identity; title alone is not
            # stable because plans legitimately repeat Endurance every week.
            external_id = f"{ir['athlete']['id']}:w{week.get('number')}:{sequence}:{session.get('date') or 'undated'}"
            date_key = str(session.get('date') or 'undated')
            per_date[date_key] = per_date.get(date_key, 0) + 1
            logical_key = f"{date_key}#{per_date[date_key]}"
            item = {
                'external_id': external_id,
                'logical_key': logical_key,
                'plan_week': week.get('number'), 'date': session.get('date'),
                'title': session.get('title', 'Untitled session'),
                'workout_type': _sport_type(session), 'sport': session.get('sport', 'cycling'),
                'session_type': session.get('type', 'workout'), 'origin': session.get('origin', 'prescribed'),
                'duration_s': int(session.get('duration_s', 0) or 0),
                'segments': session.get('segments', []), 'source_file': session.get('source_file'),
                # Complete remote field set used by the legacy/D0 parity gate.
                'description': session.get('description'),
                # AE-9.2 (2026-08-24 TP review): TP's preActivityComments
                # field -- populated for key sessions only (see
                # pre_activity_comments.py / plan_ir._annotate_delivery_context).
                'pre_activity_comment': session.get('pre_activity_comment'),
                'tp_workout_type': session.get('workout_type_value_id'),
                'total_seconds': int(session.get('duration_s', 0) or 0),
                'tss_planned': session.get('tss_planned'),
                'structure': session.get('structure'),
            }
            workouts.append(item)

    # AE-9.3/AE-9.4 (2026-08-24 TP review, round-2 addendum): the fixed
    # self-review and comment-protocol notes are dated deliberately onto a
    # date another note already claims (the self-review lands on a week's
    # own Sunday, which can coincide with a midweek note's date on a short
    # week; the Day-1 protocol note always shares its date with that week's
    # Monday note). Sequence-number the key only when a date is genuinely
    # shared, so the single-note-per-date case keeps its original id shape.
    per_note_date: Dict[str, int] = {}
    for note in render_coached_weekly_notes(ir):
        note_date = str(note['date'])
        per_note_date[note_date] = per_note_date.get(note_date, 0) + 1
        sequence = per_note_date[note_date]
        suffix = '' if sequence == 1 else f":{sequence}"
        notes.append({
            'external_id': f"note:{ir['athlete']['id']}:weekly:{note_date}{suffix}",
            'date': note_date,
            'logical_key': f"weekly-briefing-{note_date}{suffix.replace(':', '-')}",
            'title': note['title'],
            'text': note['body'],
        })

    attachments = [dict(attachment) for attachment in (ir.get('attachments') or [])]
    if not any(a.get('kind') == 'guide' for a in attachments):
        guide = 'training_guide.pdf' if (athlete_dir / 'training_guide.pdf').exists() else 'training_guide.html'
        attachments.append({'id': 'guide', 'external_id': 'attachment:guide', 'path': guide, 'kind': 'guide'})
    for attachment in attachments:
        attachment.setdefault('external_id', f"attachment:{attachment.get('id') or attachment.get('path')}")
        raw_path = str(attachment.get('path') or 'training_guide.html')
        file_path = athlete_dir / raw_path
        file_bytes = file_path.read_bytes() if file_path.is_file() else b''
        parent_key = workouts[0]['logical_key'] if workouts else 'undated#1'
        attachment.update({
            'parent_logical_key': parent_key,
            'filename': Path(raw_path).name,
            'sha256': hashlib.sha256(file_bytes).hexdigest(),
            'bytes_ref': raw_path,
            'logical_key': f"{parent_key}:{Path(raw_path).name}",
        })
    target = ir.get('race_snapshot') or {}
    tasks = [note for note in (ir.get('notes') or [])
             if note.get('kind') in ('mental_training', 'mental_task')]
    tasks = [{**task,
              'logical_key': str(task.get('id') or f"mental-task-{index}"),
              'body': str(task.get('body') or task.get('text') or '')}
             for index, task in enumerate(tasks, 1)]
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
    product_id = str(entitlement.get('product_id') or entitlement.get('external_id')
                     or entitlement.get('race') or 'course')
    entitlement['product_id'] = product_id
    entitlement['logical_key'] = product_id
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
