"""Platform-neutral fulfillment manifest serialized from PlanIR."""
from __future__ import annotations
import json
from pathlib import Path


def build_fulfillment_manifest(athlete_dir: Path | str) -> dict:
    athlete_dir = Path(athlete_dir)
    ir = json.loads((athlete_dir / 'plan_ir.json').read_text())
    workouts, notes = [], []
    for week in ir.get('weeks', []):
        for session in week.get('sessions', []):
            item = {'plan_week': week['number'], 'date': session.get('date'),
                    'title': session['title'], 'type': session['type'], 'sport': session['sport'],
                    'duration_s': session['duration_s'], 'segments': session.get('segments', []),
                    'source_file': session.get('source_file')}
            workouts.append(item)
            notes.append({'date': item['date'], 'title': item['title'],
                          'text': f"{item['title']} — Week {item['plan_week']}"})
    target = ir.get('race_snapshot') or {}
    manifest = {'schema_version': 1, 'athlete_id': ir['athlete']['id'], 'workouts': workouts,
                'calendar_dates': [x.get('date') for x in workouts if x.get('date')],
                'native_notes': notes, 'attachments': [
                    {'path': 'training_guide.pdf' if (athlete_dir / 'training_guide.pdf').exists() else 'training_guide.html', 'kind': 'guide'}],
                'mental_training_tasks': ir.get('notes', []),
                'course_entitlement': {'race': target.get('name'), 'race_date': target.get('date')},
                'verification_expectations': {'workout_count': len(workouts), 'read_back': True}}
    (athlete_dir / 'fulfillment_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest
