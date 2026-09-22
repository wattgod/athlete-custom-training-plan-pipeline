from taper_prescription import (
    pre_taper_daily_average_tss,
    taper_day_fraction,
)


def test_taper_day_fraction_decays_between_endpoints():
    assert taper_day_fraction(0, 14) == 0.70
    assert taper_day_fraction(13, 14) == 0.50
    assert taper_day_fraction(7, 14) < 0.70
    assert taper_day_fraction(7, 14) > 0.50


def test_pre_taper_daily_average_uses_last_two_load_weeks():
    weeks = [
        {'plan_week': 1, 'week_type': 'load',
         'days': [{'tss': 100}] * 7},
        {'plan_week': 2, 'week_type': 'recovery',
         'days': [{'tss': 1}] * 7},
        {'plan_week': 3, 'week_type': 'testing',
         'days': [{'tss': 200}] * 7},
        {'plan_week': 4, 'week_type': 'load',
         'days': [{'tss': 300}] * 7},
        {'plan_week': 5, 'week_type': 'taper',
         'days': []},
    ]
    assert pre_taper_daily_average_tss(weeks, 5) == 250.0
