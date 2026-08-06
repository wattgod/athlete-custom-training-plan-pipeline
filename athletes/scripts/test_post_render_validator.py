"""Phase 1 transitional post-render blocker contracts."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from post_render_validator import INPUT_VERSION, validate_transitional_input


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
    return {
        'input_version': INPUT_VERSION,
        'plan_ir': {
            'plan_ir_version': '0.1',
            'race_snapshot': {'date': '2026-09-19'},
            'weeks': weeks,
        },
        'tp_manifest': {'version': 1, 'sessions': copy.deepcopy(sessions)},
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
    issues, _ = validate_transitional_input(document)
    assert 'THIN_RACE_WEEK' in {item['id'] for item in issues}


def test_duplicate_same_metric_field_test_fires_once():
    document = _document()
    document['plan_ir']['weeks'][1]['sessions'].append(
        _session('2026-08-12', 'Second HR Field Test'))
    document['tp_manifest']['sessions'].append(
        _session('2026-08-12', 'Second HR Field Test'))
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
    issues, _ = validate_transitional_input(document)
    assert 'SCHEDULE_CONTRADICTION' in {item['id'] for item in issues}


def test_missing_race_and_carb_contradiction_are_independent():
    document = _document()
    document['plan_ir']['weeks'][-1]['sessions'][-1]['tp_kind'] = 'bike'
    document['plan_ir']['weeks'][-1]['sessions'][-1]['type'] = 'workout'
    document['tp_manifest']['sessions'][-1]['tp_kind'] = 'bike'
    document['context']['guide_html'] = '<div data-canonical-carb-target="70">70</div>'
    issues, _ = validate_transitional_input(document)
    ids = {item['id'] for item in issues}
    assert {'NO_RACE_DAY_WORKOUT', 'CARB_TARGET_CONTRADICTION'} <= ids
