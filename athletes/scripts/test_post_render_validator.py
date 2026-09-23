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
        # A Day Off card is never blank (voice contract); fixtures carry a body.
        'description': 'Off the bike, not off the plan.' if kind == 'day_off' else None,
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
            {**_session('2026-09-17', 'Openers'), 'role': 'opener'},
            {**_session('2026-09-18', 'Race Sharpener'), 'role': 'activation'},
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


def test_every_dated_a_event_must_render_as_an_a_race_day():
    document = _document()
    early_event = {'name': 'Early Gravel 100', 'date': '2026-08-29',
                   'priority': 'A'}
    final_event = {'name': 'Three Course Race', 'date': '2026-09-19',
                   'priority': 'A'}
    document['context']['profile']['a_events'] = [early_event, final_event]
    document['plan_ir']['events'] = [early_event, final_event]
    document['plan_ir']['weeks'][-1]['sessions'][-1]['race'] = {'priority': 'A'}
    document['tp_manifest']['sessions'][-1]['race'] = {'priority': 'A'}
    rest = _session('2026-08-29', 'Rest Day', 'day_off', 'rest', 0)
    document['plan_ir']['weeks'].insert(2, {
        'number': 3, 'phase': 'race', 'sessions': [rest]})
    document['tp_manifest']['sessions'].insert(3, copy.deepcopy(rest))
    document['tp_manifest']['expected']['day_off'] += 1
    document['tp_manifest']['expected']['total'] += 1

    issues, _ = validate_transitional_input(document)

    assert any(item['id'] == 'A_EVENT_RACE_DAY_MISSING'
               and item['review_value']['missing_dates'] == ['2026-08-29']
               for item in issues)


def test_targetless_coached_block_needs_no_fake_race_day():
    document = _document()
    sessions = [
        _session('2026-08-24', 'Rest Day', 'day_off', 'rest', 0),
        _session('2026-08-25', 'Endurance'),
    ]
    document['plan_ir']['race_snapshot'] = {
        'name': None, 'date': None, 'distance_miles': None}
    document['plan_ir']['weeks'] = [{
        'number': 1, 'phase': 'build', 'sessions': sessions}]
    document['tp_manifest'].update({
        'plan_title': 'Athlete M · Coached Block · 1wk [CUSTOM]',
        'race': {'name': None, 'date': None, 'priority': None},
        'expected': {
            'bike': 1, 'strength': 0, 'day_off': 1, 'race': 0, 'total': 2},
        'sessions': copy.deepcopy(sessions),
    })
    issues, _ = validate_transitional_input(document)
    assert 'NO_RACE_DAY_WORKOUT' not in {item['id'] for item in issues}


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


def test_race_week_without_openers_requires_review():
    document = _document()
    document['plan_ir']['weeks'][-1]['sessions'] = [
        {**_session('2026-09-16', 'Race Sharpener'), 'role': 'activation'},
        _session('2026-09-18', 'Easy Endurance'),
        _session('2026-09-19', 'Race Day', 'race', 'race', 5),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert 'RACE_WEEK_OPENER_MISSING' in {item['id'] for item in issues}


def test_race_week_without_sharpener_requires_review():
    document = _document()
    document['plan_ir']['weeks'][-1]['sessions'] = [
        {**_session('2026-09-17', 'Openers'), 'role': 'opener'},
        _session('2026-09-18', 'Easy Endurance'),
        _session('2026-09-19', 'Race Day', 'race', 'race', 5),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert 'RACE_WEEK_SHARPENER_MISSING' in {item['id'] for item in issues}


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


def test_assigned_filler_skill_and_long_ride_roles_do_not_invent_interval_conflicts():
    # A generated calendar may contain cadence bursts and race-specific
    # surges without assigning another interval day. The schedule check must
    # use the generator's assigned role when one is present.
    document = _document()
    document['context']['profile']['availability_roles'] = {
        'long_ride_days': ['friday'],
        'interval_days': ['monday', 'wednesday'],
        'off_days': ['saturday'],
    }
    document['plan_ir']['weeks'][1]['sessions'].extend([
        {**_session('2026-08-11', 'High Cadence Intervals'), 'role': 'skill'},
        {**_session('2026-08-13', 'Cadence Work'), 'role': 'filler'},
        {**_session('2026-08-14', 'Race Simulation — Act 1'), 'role': 'long_ride'},
    ])
    _mirror_to_manifest(document)

    _, confirmations = validate_transitional_input(document)

    entries = [entry for item in confirmations
               if item['id'] == 'SCHEDULE_MISMATCH_CONFIRM'
               for entry in item['review_value']['generated_mismatches']]
    assert not any('2026-08-11' in entry or '2026-08-13' in entry
                   or '2026-08-14' in entry for entry in entries)


def test_assigned_intensity_role_outside_interval_days_still_requires_confirmation():
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        {**_session('2026-08-11', 'Custom Hard Set'), 'role': 'intensity'})
    _mirror_to_manifest(document)

    _, confirmations = validate_transitional_input(document)

    item = next(c for c in confirmations if c['id'] == 'SCHEDULE_MISMATCH_CONFIRM')
    assert any('2026-08-11' in entry for entry in
               item['review_value']['generated_mismatches'])


def test_race_activation_is_not_endurance_for_tss_rate_gate():
    document = _document()
    session = {**_session('2026-09-15', 'Stars In Your Eyes'),
               'role': 'activation', 'tss_planned': 63.0,
               'total_time_planned': 1.0333}
    document['plan_ir']['weeks'][-1]['sessions'].append(session)
    _mirror_to_manifest(document)

    issues, _ = validate_transitional_input(document)

    assert 'ENDURANCE_TSS_RATE_HIGH' not in {item['id'] for item in issues}


def test_each_a_race_taper_fail_reaches_canonical_readiness():
    # The ordinary generated status once said zero CRITICAL while an
    # independent ae-lint pass found two MidSouth taper FAILs.
    document = _document()
    document['context']['profile']['a_events'] = [
        {'name': 'Early Gravel', 'date': '2026-08-29', 'priority': 'A'},
        {'name': 'Three Course Race', 'date': '2026-09-19', 'priority': 'A'},
    ]

    def hard_session(day, seconds):
        return {**_session(day, 'Controlled Hard Touch'), 'role': 'intensity',
                'tss_planned': 60.0,
                'structure': {'primaryIntensityMetric': 'percentOfFtp',
                              'structure': [{'type': 'step',
                                             'length': {'value': 1, 'unit': 'repetition'},
                                             'steps': [{'length': {'value': seconds, 'unit': 'second'},
                                                        'targets': [{'minValue': 93, 'maxValue': 93}]}]}]}}

    # Early race window: Aug 15-28; Aug 8-14 is the 1000s baseline.
    document['plan_ir']['weeks'][1]['sessions'].extend([
        hard_session('2026-08-08', 1000),
        hard_session('2026-08-15', 100),
        hard_session('2026-08-22', 80),
    ])
    _mirror_to_manifest(document)

    issues, _ = validate_transitional_input(document)

    taper = [issue for issue in issues if issue['id'] == 'AE_TAPER_LINT_FAIL_20260829']
    assert len(taper) == 1
    assert {item['rule'] for item in taper[0]['review_value']['findings']} == {'AE-1.17'}
    assert not any(issue['id'] == 'AE_TAPER_LINT_FAIL_20260919' for issue in issues)


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


def test_cadence_target_is_not_read_as_intensity():
    """An RPE 6 step with a 95 rpm cadence target is RPE 6, not RPE 95
    (sol review Aug 23 2026: the two-target form created a false
    RPE_DESCRIPTION_STRUCTURE_MISMATCH blocker)."""
    from post_render_validator import _structure_max_target
    session = {"structure": {"primaryIntensityMetric": "rpe", "structure": [{"steps": [{
        "targets": [{"minValue": 6, "maxValue": 6},
                    {"minValue": 95, "unit": "roundOrStridePerMinute"}]}]}]}}
    assert _structure_max_target(session) == 6


def _step(seconds, min_pct=None, max_pct=None, intensity_class='active'):
    if max_pct is not None:
        targets = [{'minValue': min_pct, 'maxValue': max_pct}]
    elif min_pct is not None:
        targets = [{'minValue': min_pct}]
    else:
        targets = []
    return {'length': {'value': seconds, 'unit': 'second'},
            'targets': targets, 'intensityClass': intensity_class}


def _bike_session(day, title, steps, session_type='workout'):
    session = _session(day, title, session_type=session_type)
    session['structure'] = {'structure': [{'steps': [step]} for step in steps]}
    return session


def test_hard_minutes_below_floor_warns_on_a_load_week():
    """AE-2.1 (sol programming review 2026-08-24, blocker 4): a load week
    delivering under 90 structured minutes at >=92% FTP surfaces a
    WARNING (real case: W3's 26.7 hard minutes, the pilot plan's only
    true build/load week)."""
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'load'
    document['plan_ir']['weeks'][1]['sessions'] = [
        _bike_session('2026-08-11', 'Threshold Intervals', [
            _step(1800, 95, 100),  # 30 min hard
            _step(3600, 60, 65),  # 60 min easy -- not hard
        ]),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(issue for issue in issues
                if issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR')
                and issue['review_value']['week'] == 1)
    assert item['id'] == 'HARD_MINUTES_BELOW_FLOOR_W01'
    assert item['severity'] == 'WARNING'
    assert item['review_value']['hard_minutes'] == 30.0


def test_hard_minutes_expands_repetition_blocks():
    """A TP `repetition` block lists its steps ONCE and states the rep count
    in length.value. Counting those steps a single time read a 6x3min set as
    one 3-minute rep -- a 6x undercount on any repetition-shaped structure.

    Motoren's own projector emits fully-unrolled `step` blocks, so no
    generated plan's numbers moved when this was fixed; the exposure is the
    TP-curated library path, where readback structures DO carry repetition
    blocks (ae_lint._steps expands them for exactly this reason).
    """
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'load'
    session = _session('2026-08-11', 'Ronnestad 30-15')
    session['structure'] = {'structure': [{
        'type': 'repetition',
        'length': {'value': 6, 'unit': 'repetition'},
        'steps': [_step(180, 108, 112), _step(180, 50, 55, 'rest')],
    }]}
    document['plan_ir']['weeks'][1]['sessions'] = [session]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(issue for issue in issues
                if issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR')
                and issue['review_value']['week'] == 1)
    # 6 reps x 180s = 18.0 min, not the 3.0 min a single pass would report.
    assert item['review_value']['hard_minutes'] == 18.0


def test_short_taper_endurance_is_still_reviewed_without_an_exempt_role():
    document = _document()
    session = _session('2026-09-15', 'Endurance', hours=0.5)
    document['plan_ir']['weeks'].append({
        'number': 5, 'phase': 'taper', 'week_type': 'taper',
        'sessions': [session],
    })
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert 'SHORT_SESSION_BELOW_FLOOR' in {issue['id'] for issue in issues}


def test_explicit_activation_role_exempts_an_intentionally_short_taper_touch():
    document = _document()
    session = _session('2026-09-15', 'Sharpener', hours=0.5)
    session['role'] = 'activation'
    document['plan_ir']['weeks'].append({
        'number': 5, 'phase': 'taper', 'week_type': 'taper',
        'sessions': [session],
    })
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert 'SHORT_SESSION_BELOW_FLOOR' not in {issue['id'] for issue in issues}


def test_hard_minutes_at_or_above_floor_does_not_warn():
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'load'
    document['plan_ir']['weeks'][1]['sessions'] = [
        _bike_session('2026-08-11', 'Threshold Intervals', [
            _step(5700, 95, 100),  # 95 min hard
        ]),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert not [issue for issue in issues
                if issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR')
                and issue['review_value']['week'] == 1]


def test_hard_minutes_counts_an_open_field_test_effort():
    """A field-test session's open/FreeRide main effort (AE-8.4d: honest
    zero-target structure, never a fake numeric anchor) still counts
    toward the floor -- AE-2.1: 'testing weeks count test efforts toward
    the floor'. Between-rep recovery at a real sub-92% target does not."""
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'load'
    document['plan_ir']['weeks'][1]['sessions'] = [
        _bike_session('2026-08-11', 'FTP Test', [
            _step(600, 45, 70, intensity_class='warmUp'),  # warmup: excluded
            _step(1200, 0, 0),  # open 20min test effort: counted (1200s)
            _step(300, 50, 50),  # easy recovery: excluded
        ]),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    item = next(issue for issue in issues
                if issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR')
                and issue['review_value']['week'] == 1)
    assert item['review_value']['hard_minutes'] == 20.0


def test_testing_week_floor_waits_for_generated_assessment_dose_metadata():
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'testing'
    document['plan_ir']['weeks'][1]['sessions'] = [
        _session('2026-08-11', 'FTP Test'),
        _session('2026-08-13', 'Anaerobic Test'),
    ]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert not any(
        item['id'].startswith('HARD_MINUTES_BELOW_FLOOR')
        for item in issues
    )


def test_rendered_vo2_dose_above_ae_3_1_ceiling_blocks_delivery():
    document = _document()
    session = _bike_session('2026-08-11', 'Descending VO2 Pyramid', [
        _step(1260, 114, 114),  # 21 minutes at >=106% FTP
    ])
    session['archetype_id'] = 'VO2max Extended'
    session['structure']['primaryIntensityMetric'] = 'percentOfFtp'
    document['plan_ir']['weeks'][1]['sessions'] = [session]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    finding = next(item for item in issues
                   if item['id'].startswith('VO2_DOSE_OUT_OF_RANGE'))
    assert finding['severity'] == 'CRITICAL'
    assert finding['review_value']['vo2_minutes'] == 21.0


def test_rendered_vo2_dose_inside_ae_3_1_ceiling_passes():
    document = _document()
    session = _bike_session('2026-08-11', 'Ronnestad 40-20', [
        _step(1020, 120, 120),  # 17 minutes: warning band, not a failure
    ])
    session['archetype_id'] = 'VO2max 40/20'
    session['structure']['primaryIntensityMetric'] = 'percentOfFtp'
    document['plan_ir']['weeks'][1]['sessions'] = [session]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert not any(item['id'].startswith('VO2_DOSE_OUT_OF_RANGE')
                   for item in issues)


def test_rendered_rpe_vo2_does_not_use_ftp_proxy_dose():
    document = _document()
    session = _bike_session('2026-08-11', 'VO2max 30-30 (Billat)', [
        _step(900, 9, 10),
    ])
    session['archetype_id'] = 'VO2max 30/30'
    session['structure']['primaryIntensityMetric'] = 'rpe'
    document['plan_ir']['weeks'][1]['sessions'] = [session]
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    assert not any(item['id'].startswith('VO2_DOSE_OUT_OF_RANGE')
                   for item in issues)


def test_hard_minutes_floor_exempt_for_recovery_taper_race_and_pre_plan():
    """Every week in the base fixture has zero structured hard minutes
    (sessions carry no structure) -- without the exemption every week_type
    would warn. recovery/taper/race are exempt by week_type; a load-typed
    'pre_plan' (W00) bridge week is exempt by phase (it is not a
    structured training week at all)."""
    document = _document()
    document['plan_ir']['weeks'][0]['phase'] = 'pre_plan'
    document['plan_ir']['weeks'][0]['week_type'] = 'load'
    document['plan_ir']['weeks'][1]['week_type'] = 'recovery'
    document['plan_ir']['weeks'].append({
        'number': 5, 'phase': 'taper', 'week_type': 'taper', 'sessions': []})
    issues, _ = validate_transitional_input(document)
    assert not any(issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR') for issue in issues)


def test_hard_minutes_below_floor_reports_every_offending_week_distinctly():
    """validate_transitional_input's final step dedupes issues by a plain
    "id" key ({item["id"]: item for item in issues}) -- a bare
    "HARD_MINUTES_BELOW_FLOOR" id would silently collapse every offending
    week down to just the last one processed. Real case: Steve Wagner's
    W1 (38.5 min), W2 (27.0 min), and W3 (24.0 min) all failed the floor;
    a shared id would have reported only W3 to the coach. Each week's
    finding must survive as its own distinct, per-week id."""
    document = _document()
    document['plan_ir']['weeks'][1]['week_type'] = 'load'
    document['plan_ir']['weeks'][1]['sessions'] = [
        _bike_session('2026-08-11', 'Threshold Intervals', [
            _step(1800, 95, 100),  # 30 min hard
        ]),
    ]
    document['plan_ir']['weeks'].append({
        'number': 2, 'phase': 'base', 'week_type': 'load', 'sessions': [
            _bike_session('2026-08-18', 'Threshold Intervals', [
                _step(600, 95, 100),  # 10 min hard
            ]),
        ]})
    _mirror_to_manifest(document)
    issues, _ = validate_transitional_input(document)
    matches = {issue['id']: issue for issue in issues
               if issue['id'].startswith('HARD_MINUTES_BELOW_FLOOR')}
    assert set(matches) == {'HARD_MINUTES_BELOW_FLOOR_W01', 'HARD_MINUTES_BELOW_FLOOR_W02'}
    assert matches['HARD_MINUTES_BELOW_FLOOR_W01']['review_value']['hard_minutes'] == 30.0
    assert matches['HARD_MINUTES_BELOW_FLOOR_W02']['review_value']['hard_minutes'] == 10.0


def test_locked_run_sessions_project_as_tp_run_not_bike():
    """A dual-sport athlete declares a fixed run with `sport: run` on a
    recurring session. Both compilers (canonical_training_model and plan_ir)
    used to hardcode sport='cycling'/tp_kind='bike'/type=2 for every locked
    session, so a runner-cyclist's declared runs silently became bike cards
    and the block came out bike-only. TP workoutTypeId 3 = run.
    """
    import plan_ir as P
    assert P.TP_WORKOUT_TYPE_VALUE_ID['run'] == 3
    assert P._default_tp_kind('run') == 'run'
    # A bike recurring session must be untouched by the run branch.
    assert P._default_tp_kind('endurance') == 'bike'

    import apply_contract as A
    assert 3 in A.SUPPORTED_TP_WORKOUT_TYPES, (
        "delivery contract must accept run (3) or dual-sport plans cannot ship")
    assert 3 in A.LEGACY_PRIOR_TP_WORKOUT_TYPES


def test_optional_days_prefixes_only_prescribed_work():
    """schedule_constraints.optional_days marks a whole weekday's PRESCRIBED
    work optional without deleting it. The athlete's own locked blocks, rest
    days and strength are never touched -- those are his commitments, not the
    coach's prescription. Uses the existing "OPTIONAL:" convention from
    dual_sport_week.yaml.
    """
    import canonical_training_model as C
    src = __import__('inspect').getsource(C)
    assert 'optional_days' in src
    assert 'OPTIONAL: ' in src
    # The guard must exclude the athlete's own fixed blocks and non-bike kinds.
    assert '"athlete_fixed"' in src and '("day_off", "strength")' in src
    # `date` must be imported at module scope -- it is used inside the
    # session loop, and a local-only datetime import raises NameError there
    # (which fails the whole canonical build, not just the prefix).
    assert 'from datetime import date\n' in src
