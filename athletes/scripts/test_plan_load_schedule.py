import pytest

from block_chain import build_plan_from_calendar
from block_compliance import r19_hours_fit
from plan_load_schedule import build_hours_schedule, default_meso_pattern


def _weeks(*types):
    weeks = []
    for number, week_type in enumerate(types, start=1):
        weeks.append({
            'week': number,
            'phase': 'base' if week_type == 'load' else week_type,
            'week_type': week_type,
            'is_recovery_week': week_type == 'recovery',
            'is_race_week': week_type == 'race',
        })
    return {'weeks': weeks}


def test_default_meso_pattern_uses_age_40_boundary():
    assert default_meso_pattern(39) == '3:1'
    assert default_meso_pattern(40) == '2:1'
    assert default_meso_pattern(None) == '3:1'


def test_schedule_clamps_first_load_week_and_caps_ramp():
    plan_dates = _weeks('load', 'load', 'load')
    schedule = build_hours_schedule(
        plan_dates,
        current_hours=4,
        target_hours=10,
        tss_per_hour=55,
    )
    increment = 8 * 7 / 55
    assert schedule[1] == pytest.approx(6)
    assert schedule[2] <= schedule[1] + increment
    assert schedule[3] <= schedule[2] + increment
    assert schedule[1] <= schedule[2] <= schedule[3]


def test_schedule_holds_at_target_and_recovery_inherits_latest_load():
    plan_dates = _weeks('load', 'load', 'recovery', 'taper', 'race', 'load')
    schedule = build_hours_schedule(
        plan_dates,
        current_hours=10,
        target_hours=10,
    )
    assert schedule[1] == schedule[2] == 10
    assert schedule[3] == schedule[4] == schedule[5] == 10
    assert schedule[6] == 10


def test_schedule_missing_current_hours_uses_target():
    schedule = build_hours_schedule(
        _weeks('load', 'recovery', 'load'),
        current_hours=0,
        target_hours=8,
    )
    assert schedule == {1: 8, 2: 8, 3: 8}


def test_scheduled_builder_records_targets_and_r19_uses_each_target():
    schedule = {1: 6.0, 2: 7.0, 3: 7.0, 4: 8.0}
    plan = build_plan_from_calendar(
        week_descriptors=[
            {'plan_week': 1, 'phase': 'base', 'week_type': 'load'},
            {'plan_week': 2, 'phase': 'base', 'week_type': 'load'},
            {'plan_week': 3, 'phase': 'base', 'week_type': 'recovery'},
            {'plan_week': 4, 'phase': 'build', 'week_type': 'load'},
        ],
        archetype='specialist',
        hours_per_week=8,
        hours_schedule=schedule,
        off_days=['Sun'],
    )
    assert [week['target_hours'] for week in plan['weeks']] == [6, 7, 7, 8]
    assert r19_hours_fit(plan['weeks'], target_hours=8)[0]
    for week in plan['weeks']:
        if week['week_type'] == 'recovery':
            continue
        target_minutes = week['target_hours'] * 60
        assert week['total_duration'] <= target_minutes * 1.10


def test_builder_records_target_hours_without_a_schedule():
    plan = build_plan_from_calendar(
        week_descriptors=[
            {'plan_week': 1, 'phase': 'base', 'week_type': 'load'},
            {'plan_week': 2, 'phase': 'base', 'week_type': 'recovery'},
        ],
        archetype='specialist',
        hours_per_week=8,
        off_days=['Sun'],
    )
    assert [week['target_hours'] for week in plan['weeks']] == [8, 8]
