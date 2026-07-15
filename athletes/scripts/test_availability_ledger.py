import pytest
from availability_ledger import (AvailabilityLedgerError, build_ledger,
                                 contradiction_issues, hard_days,
                                 materialize_fixed_sessions, weekly_load_minutes)
from block_compliance import r01_no_back_to_back_intensity, r05_intensity_count


def test_two_commute_legs_reserve_capacity_and_count_fixed_hard_day():
    ledger = build_ledger([
        {'day': 'monday', 'slot': 'am', 'duration_min': 35, 'intensity': 'easy', 'origin': 'athlete_fixed', 'locked': True},
        {'day': 'monday', 'slot': 'pm', 'duration_min': 35, 'intensity': 'easy', 'origin': 'athlete_fixed', 'locked': True},
        {'day': 'thursday', 'slot': 'am', 'duration_min': 75, 'intensity': 'hard', 'origin': 'athlete_fixed', 'locked': True},
    ], {'Mon': 120, 'Thu': 120, 'Fri': 60})
    assert ledger['Mon']['residual_min'] == 50
    assert weekly_load_minutes(ledger, [{'duration_min': 650}]) == 795
    assert hard_days(ledger) == {'Thu'}


def test_impossible_daily_caps_fail_before_generation():
    with pytest.raises(AvailabilityLedgerError, match='exceed daily cap'):
        build_ledger([{'day': 'fri', 'duration_min': 90, 'origin': 'athlete_fixed', 'locked': True}], {'Fri': 60})


def test_heather_ledger_materializes_two_commutes_and_total_load_for_compliance():
    """Golden G4 shape: external load is part of the same weekly truth."""
    sessions = [
        *[{'day': day, 'slot': slot, 'duration_min': 35, 'intensity': 'easy',
           'origin': 'athlete_fixed', 'locked': True, 'title': 'Commute'}
          for day in ('Mon', 'Tue', 'Wed') for slot in ('am', 'pm')],
        {'day': 'Thu', 'slot': 'pm', 'duration_min': 75, 'intensity': 'threshold',
         'origin': 'athlete_fixed', 'locked': True, 'title': 'Thursday group ride'},
    ]
    ledger = build_ledger(sessions, {day: 180 for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')})
    # 11h10 prescribed + 4h45 fixed = 15h55 would be overfilled; the builder
    # receives residual capacity/target.  This golden total is 12h50.
    plan = {'weeks': [{'plan_week': 2, 'week_type': 'load', 'phase': 'build',
                       'total_duration': 485, 'total_tss': 410,
                       'days': [
                           {'day': 'Mon', 'role': 'off', 'name': 'Rest Day'},
                           {'day': 'Tue', 'role': 'intensity', 'name': 'VO2max'},
                           {'day': 'Wed', 'role': 'filler', 'name': 'Endurance'},
                           {'day': 'Thu', 'role': 'off', 'name': 'Rest Day'},
                           {'day': 'Fri', 'role': 'off', 'name': 'Rest Day'},
                       ]}]}
    materialize_fixed_sessions(plan, ledger)
    week = plan['weeks'][0]
    assert 12 * 60 <= week['total_duration'] <= 14 * 60
    assert len(next(d for d in week['days'] if d['day'] == 'Mon')['sessions']) == 2
    assert len(next(d for d in week['days'] if d['day'] == 'Tue')['sessions']) == 2
    assert len(next(d for d in week['days'] if d['day'] == 'Wed')['sessions']) == 2
    assert r05_intensity_count([week], max_per_week=2)[0]
    assert r01_no_back_to_back_intensity([week])[0]
    assert next(d for d in week['days'] if d['day'] == 'Thu')['role'] == 'off'
    assert next(d for d in week['days'] if d['day'] == 'Fri')['role'] == 'off'


def test_structured_and_free_text_availability_contradiction_is_critical():
    issues = contradiction_issues(
        [{'day': 'Thursday', 'duration_min': 75, 'origin': 'athlete_fixed',
          'locked': True, 'title': 'group ride'}],
        'Thursday unavailable due to work.',
    )
    assert issues and issues[0]['id'] == 'AVAILABILITY_CONTRADICTION'
    assert issues[0]['severity'] == 'CRITICAL'
