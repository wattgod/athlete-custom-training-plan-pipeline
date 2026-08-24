import json

from fulfillment_manifest import build_fulfillment_manifest


def test_heather_like_manifest_is_platform_independent(tmp_path):
    (tmp_path / 'training_guide.pdf').write_bytes(b'%PDF')
    ir = {
        'athlete': {'id': 'heather'},
        'race_snapshot': {'name': 'Nannup', 'date': '2026-03-01', 'course_variant': 'women'},
        'weeks': [{'number': 2, 'sessions': [
            {'date': '2026-01-12', 'title': 'MTB skills', 'sport': 'mtb', 'type': 'workout',
             'origin': 'prescribed', 'duration_s': 3600, 'segments': []},
            {'date': '2026-01-16', 'title': 'Friday Recovery', 'sport': 'cycling', 'type': 'recovery',
             'origin': 'prescribed', 'duration_s': 1800, 'segments': []},
        ]}],
        'notes': [{'kind': 'mental_training', 'id': 'visualization', 'text': 'Visualize Nannup climbs'}],
        'attachments': [], 'entitlements': [],
    }
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir))
    manifest = build_fulfillment_manifest(tmp_path)
    assert len(manifest['workouts']) == 2
    # AE-9.1 (2026-08-24 TP review): week 2 has no phase/week_type, which
    # story_notes defaults to "load" -- and its only non-Monday session
    # (Jan 16, Friday) earns the mid-week "feel" note alongside the Jan 12
    # Monday note.
    assert len(manifest['native_notes']) == 2
    assert manifest['native_notes'][0]['logical_key'] == 'weekly-briefing-2026-01-12'
    assert 'Week 2 ·' not in manifest['native_notes'][0]['text']
    assert manifest['workouts'][0]['workout_type'] == 8
    assert manifest['workouts'][1]['title'] == 'Friday Recovery'
    assert manifest['attachments'] == [{
        'id': 'guide', 'external_id': 'attachment:guide',
        'path': 'training_guide.pdf', 'kind': 'guide',
        'parent_logical_key': '2026-01-12#1',
        'filename': 'training_guide.pdf',
        'sha256': '315d429b7714cedb6ad04ac31240145257692630457f3c88253c5beceac76027',
        'bytes_ref': 'training_guide.pdf',
        'logical_key': '2026-01-12#1:training_guide.pdf',
    }]
    assert manifest['mental_training_tasks'][0]['id'] == 'visualization'
    assert manifest['course_entitlement']['race'] == 'Nannup'
    assert (tmp_path / 'fulfillment_manifest.json').exists()
