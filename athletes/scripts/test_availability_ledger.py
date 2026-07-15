import pytest
from availability_ledger import AvailabilityLedgerError, build_ledger, hard_days, weekly_load_minutes


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
