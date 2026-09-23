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
    # Monday note. AE-9.3/AE-9.4 (round-2 addendum) add two more: the Day-1
    # comment-protocol note (shares Jan 12 with the Monday note) and the
    # week's Sunday self-review note, which this short two-day fixture
    # lands on its own last dated day, Jan 16, alongside the midweek note --
    # both same-date pairs are what fulfillment_manifest's collision-safe
    # keying (":2" suffix) exists to support.
    assert len(manifest['native_notes']) == 4
    assert manifest['native_notes'][0]['logical_key'] == 'weekly-briefing-2026-01-12'
    assert manifest['native_notes'][0]['title'] == 'How To Comment On Workouts'
    assert manifest['native_notes'][1]['logical_key'] == 'weekly-briefing-2026-01-12-2'
    assert 'Week 2 ·' not in manifest['native_notes'][1]['text']
    assert manifest['native_notes'][2]['logical_key'] == 'weekly-briefing-2026-01-16'
    assert manifest['native_notes'][3]['logical_key'] == 'weekly-briefing-2026-01-16-2'
    assert manifest['native_notes'][3]['title'] == 'Week Self Review - 3 Qs'
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


def test_gravelgod_plan_includes_four_gravel_grit_notes(tmp_path):
    ir = {
        'athlete': {'id': 'grit-rider', 'name': 'Grit Rider'},
        'brand': 'gravelgod',
        'race_snapshot': {'name': 'Mid South', 'date': '2027-03-13'},
        'weeks': [
            {'number': week, 'phase': 'build', 'sessions': [
                {'date': f'2027-0{month}-{day:02d}', 'title': 'Endurance',
                 'sport': 'cycling', 'duration_s': 3600}
            ]}
            for week, month, day in [(1, 1, 4), (2, 1, 11), (3, 1, 18)]
        ],
    }
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir))
    notes = build_fulfillment_manifest(tmp_path)['native_notes']
    grit = [note for note in notes if note['title'].startswith('GRAVEL GRIT ')]
    assert len(grit) == 4
    assert len({note['date'] for note in grit}) == 4
    assert min(note['date'] for note in grit) >= '2027-01-04'
    assert all(len(note['text'].split()) <= 100 for note in grit)


def test_matched_a_events_add_distinct_pre_race_intel_notes(tmp_path):
    ir = {
        'athlete': {'id': 'johnny', 'name': 'Johnny'},
        'brand': 'gravelgod',
        'race_snapshot': {'name': 'Unbound Gravel 100', 'date': '2027-06-05'},
        'events': [
            {'name': 'Mid South', 'date': '2027-03-13', 'priority': 'A', 'race_id': 'mid_south'},
            {'name': 'Unbound Gravel 100', 'date': '2027-06-05', 'priority': 'A', 'race_id': 'unbound_gravel_100'},
        ],
        'weeks': [{'number': 1, 'phase': 'build', 'sessions': [
            {'date': '2027-02-22', 'title': 'Endurance', 'sport': 'cycling', 'duration_s': 3600}
        ]}],
    }
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir))
    notes = build_fulfillment_manifest(tmp_path)['native_notes']
    race = [note for note in notes if note['title'].startswith('RACE INTEL')]
    assert len(race) == 2
    assert {note['date'] for note in race} == {'2027-02-27', '2027-05-22'}
    assert 'sticky' in race[0]['text'].lower()
    assert 'flint' in race[1]['text'].lower()
