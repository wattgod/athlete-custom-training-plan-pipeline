"""Opt-in placement switches (profile schedule_constraints):
explicit_interval_days -> _build_day_template honors stated interval days,
even next to the long ride; strength_on_interval_days -> place_strength_days
stacks strength onto the intensity days instead of avoiding them (AE-8.4).
Both default OFF: with no switch the defaults are byte-identical."""
from block_builder import _build_day_template
from generate_athlete_package import place_strength_days


def test_default_template_unchanged_without_preference():
    roles = _build_day_template(['Sun'], 'Wed', 2)
    # Tue/Thu are adjacent to the Wednesday long ride -> Mon/Fri by default.
    assert [d for d, r in roles.items() if r == 'intensity'] == ['Mon', 'Fri']


def test_explicit_interval_days_allowed_next_to_long_ride():
    roles = _build_day_template(['Sun'], 'Wed', 2, preferred_intensity_days=['Tue', 'Fri'])
    assert roles['Tue'] == 'intensity' and roles['Fri'] == 'intensity'
    assert roles['Wed'] == 'long_ride' and roles['Thu'] == 'filler' and roles['Mon'] == 'filler'


def test_explicit_days_never_back_to_back():
    roles = _build_day_template(['Sun'], 'Sat', 2, preferred_intensity_days=['Tue', 'Wed'])
    hard = [d for d, r in roles.items() if r == 'intensity']
    assert 'Tue' in hard and 'Wed' not in hard and len(hard) == 2


def test_explicit_days_skip_off_and_long_days():
    roles = _build_day_template(['Mon'], 'Wed', 2, preferred_intensity_days=['Mon', 'Wed', 'Fri'])
    assert roles['Mon'] == 'off' and roles['Wed'] == 'long_ride' and roles['Fri'] == 'intensity'


def test_testing_week_ignores_preference():
    roles = _build_day_template(['Sun'], 'Sat', 2, week_type='testing', preferred_intensity_days=['Fri'])
    assert roles['Tue'] == 'intensity'  # FTP test earliest viable day, as before


def _avail(day):
    return day not in ('Sun', 'Wed')  # Sunday off, Wednesday long ride


def test_strength_default_avoids_intensity_days():
    days = place_strength_days(_avail, 2, avoid_days={'Tue', 'Fri'})
    assert not set(days) & {'Tue', 'Fri'}


def test_strength_stacked_on_intensity_days_when_requested():
    # What generate_athlete_package passes with strength_on_interval_days.
    days = place_strength_days(_avail, 2, strength_only_abbrevs=['Tue', 'Fri'], avoid_days=set())
    assert days == ['Tue', 'Fri']


def test_strength_stacking_still_respects_hard_blocks():
    days = place_strength_days(_avail, 2, blocked_days={'Tue'}, strength_only_abbrevs=['Tue', 'Fri'], avoid_days=set())
    assert 'Tue' not in days and 'Fri' in days and len(days) == 2
