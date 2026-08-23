"""Phase 1 transitional post-render blocker contracts."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from post_render_validator import (INPUT_VERSION, PostRenderValidationError,
                                   validate_transitional_input)


def _session(day, title, kind='bike', session_type='workout', hours=1.0):
    return {
        'date': day, 'title': title, 'display_name': title,
        'tp_kind': kind, 'type': session_type,
        'duration_s': int(hours * 3600), 'total_time_planned': hours,
        'structure': None,
    }


def _document():
    weeks = [
        {'number': 0, 'phase': 'lead_in', 'sessions': [
            _session('2026-08-05', 'Easy Endurance'),
        ]},
        {'number': 1, 'phase': 'base', 'sessions': [
            _session('2026-08-10', 'HR Field Test'),
            _session('2026-08-16', 'VO2 Session'),
        ]},
        {'number': 6, 'phase': 'race', 'sessions': [
            _session('2026-09-17', 'Openers'),
            _session('2026-09-18', 'Easy Endurance'),
            _session('2026-09-19', 'Race Day', 'race', 'race', 5),
        ]},
    ]
    sessions = [s for week in weeks for s in week['sessions']]
    counts = {kind: sum(s['tp_kind'] == kind for s in sessions)
              for kind in ('bike', 'strength', 'day_off', 'race')}
    return {
        'input_version': INPUT_VERSION,
        'plan_ir': {
            'plan_ir_version': '0.1',
            'athlete': {'name': 'Athlete M'},
            'race_snapshot': {
                'name': 'Three Course Race', 'date': '2026-09-19'},
            'weeks': weeks,
        },
        'tp_manifest': {
            'version': 1,
            'plan_title': 'Athlete M · Three Course Race · 6wk [CUSTOM]',
            'athlete': 'Athlete M',
            'race': {'name': 'Three Course Race', 'date': '2026-09-19',
                     'priority': 'A'},
            'expected': {**counts, 'total': sum(counts.values())},
            'sessions': copy.deepcopy(sessions),
        },
        'context': {
            'order_created_at': '2026-08-04T17:00:00Z',
            'generation_at': '2026-08-06T15:00:00Z',
            'athlete_timezone': 'America/Denver',
            'weeks_purchased': 6,
            'profile': {'availability_roles': {
                'long_ride_days': ['sunday'], 'interval_days': ['wednesday'],
                'off_days': ['saturday'],
            }},
            'fueling': {'prescription': {'race_target_g_per_hour': 58},
                        'gut_training': {'weekly_progression': [
                            {'week_label': 'W00'}, {'week_label': 'W1'},
                            {'week_label': 'W6'},
                        ]}},
            'guide_html': '<div data-canonical-carb-target="58">58g/hr</div>',
        },
    }


def test_valid_fixture_discriminates_generation_from_order_date():
    issues, confirmations = validate_transitional_input(_document())
    assert [item['id'] for item in issues] == ['SESSION_PREDATES_GENERATION']
    assert [item['id'] for item in confirmations] == ['SCHEDULE_MISMATCH_CONFIRM']


def test_seven_synthesized_rest_days_plus_race_is_thin():
    document = _document()
    rest = [_session(f'2026-09-{12 + index:02d}', 'Rest Day', 'day_off', 'rest', 0)
            for index in range(7)]
    race = _session('2026-09-19', 'Race Day', 'race', 'race', 5)
    document['plan_ir']['weeks'][-1]['sessions'] = rest + [race]
    document['tp_manifest']['sessions'] = [
        s for week in document['plan_ir']['weeks'] for s in week['sessions']]
    document['tp_manifest']['expected'] = {
        'bike': 3, 'strength': 0, 'day_off': 7, 'race': 1, 'total': 11}
    issues, _ = validate_transitional_input(document)
    assert 'THIN_RACE_WEEK' in {item['id'] for item in issues}


def test_duplicate_same_metric_field_test_fires_once():
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-12', 'Second HR Field Test'))
    document['tp_manifest']['sessions'] = [
        copy.deepcopy(session)
        for week in document['plan_ir']['weeks']
        for session in week['sessions']
    ]
    document['tp_manifest']['expected']['bike'] += 1
    document['tp_manifest']['expected']['total'] += 1
    issues, _ = validate_transitional_input(document)
    assert 'DUPLICATE_FIELD_TEST' in {item['id'] for item in issues}


def test_race_day_is_exempt_from_off_day_contradiction():
    document = _document()
    issues, _ = validate_transitional_input(document)
    assert 'SCHEDULE_CONTRADICTION' not in {item['id'] for item in issues}
    document['plan_ir']['weeks'][-1]['sessions'].append(
        _session('2026-09-19', 'Saturday Tempo'))
    document['tp_manifest']['sessions'].append(
        _session('2026-09-19', 'Saturday Tempo'))
    document['tp_manifest']['expected']['bike'] += 1
    document['tp_manifest']['expected']['total'] += 1
    issues, _ = validate_transitional_input(document)
    assert 'SCHEDULE_CONTRADICTION' in {item['id'] for item in issues}


def test_missing_race_and_carb_contradiction_are_independent():
    document = _document()
    document['plan_ir']['weeks'][-1]['sessions'][-1]['tp_kind'] = 'bike'
    document['plan_ir']['weeks'][-1]['sessions'][-1]['type'] = 'workout'
    document['tp_manifest']['sessions'][-1]['tp_kind'] = 'bike'
    document['tp_manifest']['expected']['bike'] += 1
    document['tp_manifest']['expected']['race'] -= 1
    document['context']['guide_html'] = '<div data-canonical-carb-target="70">70</div>'
    issues, _ = validate_transitional_input(document)
    ids = {item['id'] for item in issues}
    assert {'NO_RACE_DAY_WORKOUT', 'CARB_TARGET_CONTRADICTION'} <= ids


def test_equal_count_manifest_semantic_drift_is_rejected():
    document = _document()
    document['tp_manifest']['sessions'][0]['title'] = 'Malicious replacement'

    with pytest.raises(PostRenderValidationError, match='semantic drift'):
        validate_transitional_input(document)


@pytest.mark.parametrize(('field_path', 'mutated'), [
    (('plan_title',), 'Injected plan title'),
    (('athlete',), 'Different Athlete'),
    (('race', 'name'), 'Different Race'),
    (('race', 'date'), '2026-09-20'),
    (('race', 'priority'), 'B'),
])
def test_every_top_level_manifest_projection_field_is_validated(
    field_path, mutated,
):
    document = _document()
    target = document['tp_manifest']
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = mutated

    with pytest.raises(PostRenderValidationError, match='PlanIR projection'):
        validate_transitional_input(document)


def test_production_shaped_altitude_snapshot_requires_guide_section():
    document = _document()
    document['context']['profile']['target_race'] = {
        'name': 'High Start Race',
        'elevation_ft': 9000,  # total gain is not the trigger
        'race_metadata': {
            'start_elevation_feet': 6200,
            'avg_elevation_feet': 7100,
        },
    }
    issues, _ = validate_transitional_input(document)
    assert 'ALTITUDE_SECTION_MISSING' in {item['id'] for item in issues}

    document['context']['guide_html'] += '<h2>Altitude Training</h2>'
    issues, _ = validate_transitional_input(document)
    assert 'ALTITUDE_SECTION_MISSING' not in {item['id'] for item in issues}


def _mirror_to_manifest(document):
    document['tp_manifest']['sessions'] = [
        copy.deepcopy(session)
        for week in document['plan_ir']['weeks']
        for session in week['sessions']
    ]
    sessions = document['tp_manifest']['sessions']
    counts = {kind: sum(s['tp_kind'] == kind for s in sessions)
              for kind in ('bike', 'strength', 'day_off', 'race')}
    document['tp_manifest']['expected'] = {
        **counts, 'total': sum(counts.values())}


def test_intensity_outside_stated_interval_days_is_disclosed():
    # Real-order shape: intervals stated Wednesday-only, generator trained
    # Tuesday — previously silent because Tuesday is not a long-ride day.
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-11', 'Threshold Over-Unders'))
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    item = next(c for c in confirmations if c['id'] == 'SCHEDULE_MISMATCH_CONFIRM')
    assert any(
        'tuesday' in entry and 'outside stated interval days' in entry
        for entry in item['review_value']['generated_mismatches'])


def test_no_interval_days_stated_means_no_outside_disclosure():
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-11', 'Threshold Over-Unders'))
    document['context']['profile']['availability_roles']['interval_days'] = []
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    entries = [
        entry for c in confirmations if c['id'] == 'SCHEDULE_MISMATCH_CONFIRM'
        for entry in c['review_value']['generated_mismatches']]
    assert not any('outside stated interval days' in entry for entry in entries)


def test_day_total_over_stated_cap_is_disclosed():
    # Real-order shape: 30min strength stacked on a 120min ride against a
    # 120min Thursday cap (2.5h scheduled into a 2h window) — was silent.
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].extend([
        _session('2026-08-13', 'Big Interval Ride', hours=2.0),
        _session('2026-08-13', 'Foundation Strength', 'strength', 'strength', 0.5),
    ])
    document['context']['profile']['preferred_days'] = {
        'thursday': {'availability': 'available', 'max_duration_min': 120},
    }
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    item = next(c for c in confirmations if c['id'] == 'DAY_DURATION_OVER_CAP')
    violation = item['review_value']['violations'][0]
    assert violation['date'] == '2026-08-13'
    assert violation['total_min'] == 150
    assert violation['cap_min'] == 120


def test_day_at_cap_race_day_and_uncapped_days_are_not_flagged():
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-13', 'Exactly At Cap', hours=2.0))
    document['context']['profile']['preferred_days'] = {
        'thursday': {'availability': 'available', 'max_duration_min': 120},
        # Race Saturday: 5h race vs 120 cap must NOT flag (race exempt).
        'saturday': {'availability': 'available', 'max_duration_min': 120},
        # Monday unavailable AND covered by the off_days role: owned by
        # SCHEDULE_CONTRADICTION, so the cap rule must stay quiet (HR Field
        # Test lands Monday in the fixture).
        'monday': {'availability': 'unavailable', 'max_duration_min': 0},
    }
    document['context']['profile']['availability_roles']['off_days'] = [
        'saturday', 'monday']
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    assert not any(c['id'] == 'DAY_DURATION_OVER_CAP' for c in confirmations)


def test_unavailable_day_not_covered_by_off_role_is_disclosed():
    # preferred_days and availability_roles are duplicated by intake and can
    # drift: unavailable Monday with off_days missing it must not be silent.
    document = _document()
    document['context']['profile']['preferred_days'] = {
        'monday': {'availability': 'unavailable', 'max_duration_min': 0},
    }
    _mirror_to_manifest(document)
    issues, confirmations = validate_transitional_input(document)
    assert 'SCHEDULE_CONTRADICTION' not in {item['id'] for item in issues}
    item = next(c for c in confirmations if c['id'] == 'DAY_DURATION_OVER_CAP')
    violation = item['review_value']['violations'][0]
    assert violation['weekday'] == 'monday'
    assert violation['unavailable_day'] is True


def test_structureless_canonical_intensity_is_disclosed_for_rpe_athletes():
    # Canonical intensity identity remains authoritative even when an older
    # transitional document lacks the now-required RPE structure.
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-11', 'Cadence Work'))
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    item = next(c for c in confirmations if c['id'] == 'SCHEDULE_MISMATCH_CONFIRM')
    assert any(
        'tuesday' in entry and 'outside stated interval days' in entry
        for entry in item['review_value']['generated_mismatches'])


def test_openers_with_hot_structure_are_not_intensity():
    # Openers carry >=85% steps but are explicitly NOT intensity — they must
    # not create a systematically-false required confirmation on taper days.
    document = _document()
    session = _session('2026-08-11', 'Openers')
    session['structure'] = {'structure': [
        {'steps': [{'targets': [{'minValue': 110}]}]}]}
    document['plan_ir']['weeks'][1]['sessions'].append(session)
    _mirror_to_manifest(document)
    _, confirmations = validate_transitional_input(document)
    entries = [
        entry for c in confirmations if c['id'] == 'SCHEDULE_MISMATCH_CONFIRM'
        for entry in c['review_value']['generated_mismatches']]
    assert not any('tuesday' in entry for entry in entries)


def _rpe_structure(maximum):
    return {
        'primaryIntensityMetric': 'rpe',
        'structure': [{
            'steps': [{
                'targets': [{'minValue': maximum, 'maxValue': maximum}],
            }],
        }],
    }


def test_rpe_description_structure_mismatch_blocks_review():
    document = _document()
    session = _session('2026-08-11', 'RPE Field Test')
    session['description'] = '20-minute field test at RPE 9/10.'
    session['structure'] = _rpe_structure(8)
    document['plan_ir']['weeks'][1]['sessions'].append(session)
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(
        issue for issue in issues
        if issue['id'] == 'RPE_DESCRIPTION_STRUCTURE_MISMATCH')
    mismatch = item['review_value']['sessions'][0]
    assert mismatch['description_max_rpe'] == 9
    assert mismatch['structure_max_rpe'] == 8


def test_matching_rpe_description_and_structure_are_accepted():
    document = _document()
    session = _session('2026-08-11', 'Hard Intervals')
    session['description'] = 'MAIN SET:\n-7x1min at RPE 9-10.'
    session['structure'] = _rpe_structure(10)
    document['plan_ir']['weeks'][1]['sessions'].append(session)
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert 'RPE_DESCRIPTION_STRUCTURE_MISMATCH' not in {
        issue['id'] for issue in issues}


def test_explicit_no_test_directive_blocks_any_rendered_field_test():
    document = _document()
    document['context']['profile'].setdefault('fitness_markers', {})[
        'field_testing_allowed'] = False
    session = _session('2026-08-11', 'RPE Field Test')
    session['description'] = '20-minute field test at RPE 9.'
    session['structure'] = _rpe_structure(9)
    document['plan_ir']['weeks'][1]['sessions'].append(session)
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(
        issue for issue in issues
        if issue['id'] == 'FIELD_TEST_SUPPRESSION_BREACH')
    assert {'date': '2026-08-11', 'title': 'RPE Field Test'} in (
        item['review_value']['sessions'])


def test_unresolved_pain_blocks_field_tests_and_max_rpe_prescriptions():
    document = _document()
    document['context']['profile']['injury_history'] = {
        'current_injuries': [{
            'area': 'back', 'description': 'Recent back pain', 'status': 'active',
        }],
    }
    max_session = _session('2026-08-11', 'Standing Starts')
    max_session['description'] = 'MAIN SET:\n-5 starts at RPE 10.'
    max_session['structure'] = _rpe_structure(10)
    document['plan_ir']['weeks'][1]['sessions'].append(max_session)
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(
        issue for issue in issues
        if issue['id'] == 'UNRESOLVED_PAIN_MAX_PRESCRIPTION')
    titles = {session['title'] for session in item['review_value']['blocked_sessions']}
    assert {'HR Field Test', 'Standing Starts'} <= titles


def test_resolved_injury_does_not_block_max_prescription():
    document = _document()
    document['context']['profile']['injury_history'] = {
        'current_injuries': [{
            'description': 'Prior back pain', 'status': 'cleared',
        }],
    }
    issues, _ = validate_transitional_input(document)
    assert 'UNRESOLVED_PAIN_MAX_PRESCRIPTION' not in {
        issue['id'] for issue in issues}


def test_athlete_visible_copy_policy_rejects_leaks_and_generated_essays():
    document = _document()
    session = document['plan_ir']['weeks'][1]['sessions'][1]
    session['title'] = 'Tempo [retained 14357240]'
    session['display_name'] = session['title']
    session['description'] = (
        'Athlete - Week 1/2 - 2 weeks to Race\nPhase: BUILD\n\n'
        'PURPOSE:\nAn internal explanation.\n\nGO GET IT, ATHLETE!')
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(
        issue for issue in issues if issue['id'] == 'ATHLETE_VISIBLE_COPY_POLICY')
    reasons = item['review_value']['violations'][0]['reasons']
    assert 'internal retained token' in reasons
    assert 'personal/week header' in reasons
    assert 'phase or purpose essay header' in reasons
    assert 'all-caps cheerleading' in reasons


def test_a_only_weekly_note_copy_policy_does_not_invent_b_event():
    document = _document()
    document['plan_ir']['events'] = [{
        'name': 'Three Course Race', 'priority': 'A', 'date': '2026-09-19',
    }]
    issues, _ = validate_transitional_input(document)
    assert 'ATHLETE_VISIBLE_COPY_POLICY' not in {issue['id'] for issue in issues}
