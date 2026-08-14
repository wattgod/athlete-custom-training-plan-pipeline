"""Tests for derive_classifications.calculate_plan_weeks paid-weeks policy."""

from derive_classifications import calculate_plan_weeks


def test_calculate_plan_weeks_honors_weeks_purchased(monkeypatch):
    monkeypatch.setenv('GG_FIXED_NOW', '2026-08-06T15:00:00Z')
    profile = {
        'fulfillment': {'weeks_purchased': 7},
        'target_race': {'date': '2026-09-19'},
        'plan_start': {'preferred_start': 'next_monday'},
    }
    assert calculate_plan_weeks(profile) == 7


def test_calculate_plan_weeks_honors_one_purchased_week(monkeypatch):
    monkeypatch.setenv('GG_FIXED_NOW', '2026-08-06T15:00:00Z')
    profile = {
        'fulfillment': {'weeks_purchased': 1},
        'target_race': {'date': '2026-12-19'},
    }
    assert calculate_plan_weeks(profile) == 1


def test_calculate_plan_weeks_caps_purchased_at_52(monkeypatch):
    monkeypatch.setenv('GG_FIXED_NOW', '2026-08-06T15:00:00Z')
    profile = {
        'fulfillment': {'weeks_purchased': 60},
        'target_race': {'date': '2028-08-06'},
    }
    assert calculate_plan_weeks(profile) == 52


def test_calculate_plan_weeks_no_purchase_uses_calendar_not_8_24(monkeypatch):
    monkeypatch.setenv('GG_FIXED_NOW', '2026-08-06T15:00:00Z')
    far = {
        'target_race': {'date': '2027-03-06'},
        'plan_start': {'preferred_start': 'next_monday'},
    }
    near = {
        'target_race': {'date': '2026-08-22'},
        'plan_start': {'preferred_start': 'next_monday'},
    }
    far_weeks = calculate_plan_weeks(far)
    near_weeks = calculate_plan_weeks(near)
    assert far_weeks > 24
    assert far_weeks <= 52
    assert 1 <= near_weeks < 8
