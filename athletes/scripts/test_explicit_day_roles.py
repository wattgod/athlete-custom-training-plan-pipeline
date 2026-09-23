"""Opt-in placement switches (profile schedule_constraints):
explicit_interval_days -> _build_day_template honors stated interval days,
even next to the long ride; strength_on_interval_days -> place_strength_days
stacks strength onto the intensity days instead of avoiding them (AE-8.4).
Both default OFF: with no switch the defaults are byte-identical."""
from block_builder import _build_day_template


def test_friday_long_ride_keeps_two_spaced_quality_days():
    # Greedily taking Tuesday stranded the schedule at one intensity day:
    # Wednesday touches Tuesday and Thursday touches the Friday long ride.
    roles = _build_day_template(['Sun'], 'Fri', 2)
    assert [day for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
            if roles[day] == 'intensity'] == ['Mon', 'Wed']
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
    days = place_strength_days(_avail, 2, preferred_days=['Tue', 'Fri'], avoid_days=set())
    assert days == ['Tue', 'Fri']


def test_strength_stacking_still_respects_hard_blocks():
    days = place_strength_days(_avail, 2, blocked_days={'Tue'}, preferred_days=['Tue', 'Fri'], avoid_days=set())
    assert 'Tue' not in days and 'Fri' in days and len(days) == 2


def test_preferred_days_never_land_on_unavailable_day():
    # Review 2026-09-19 finding 4: the strength_only fallback used to place
    # strength on an unavailable day when it was the only intensity day.
    days = place_strength_days(lambda d: d not in {'Sun', 'Wed', 'Tue'}, 1, preferred_days=['Tue'], avoid_days=set())
    assert days and 'Tue' not in days


def test_unmapped_day_strings_are_ignored():
    roles = _build_day_template(['Sun'], 'Sat', 2, preferred_intensity_days=['Tues', 'TUE', 'Fri'])
    assert roles['Fri'] == 'intensity'


def test_explicit_days_around_a_simulation_do_not_rearm_the_runway():
    from block_chain import protect_post_simulation_recovery
    from block_compliance import r01_no_back_to_back_intensity as r01
    roles = _build_day_template(['Sun'], 'Wed', 2, preferred_intensity_days=['Tue', 'Thu'])
    from block_builder import DAY_ORDER
    days = [{'day': d, 'role': roles[d], 'name': {'intensity': 'VO2max', 'long_ride': 'Endurance', 'filler': 'Endurance', 'off': 'Rest'}[roles[d]],
             'level': 1, 'duration': 60, 'tss': 50} for d in DAY_ORDER]
    days[2].update(is_simulation=True, duration=240, act_simulation={'dress_rehearsal': True})  # Wed
    plan = {'weeks': [{'plan_week': 1, 'week_type': 'load', 'phase': 'build', 'days': days}]}
    protect_post_simulation_recovery(plan, ['Tue', 'Thu'])
    got = {d['day']: d['role'] for d in plan['weeks'][0]['days']}
    assert got['Tue'] != 'intensity' and got['Thu'] != 'intensity'
    ok, _ = r01(plan['weeks'])
    assert ok
    # Round-2 finding: the displaced session must not be dropped -- the
    # week still needs its sharp day (R05), relocated to a safe filler.
    from block_compliance import r05_intensity_count as r05
    ok5, msg = r05(plan['weeks'])
    assert ok5, msg
    assert [d['day'] for d in plan['weeks'][0]['days'] if d['role'] == 'intensity'] in (['Fri'], ['Mon'])


def test_explicit_sunday_and_monday_do_not_both_become_intensity():
    # Devin (PR #263): the template repeats weekly, so Sun -> next Mon is back-to-back.
    roles = _build_day_template(['Wed'], 'Sat', 2, preferred_intensity_days=['Mon', 'Sun'])
    hard = [d for d, r in roles.items() if r == 'intensity']
    assert not ({'Mon', 'Sun'} <= set(hard))


def test_invalid_exclusion_regex_is_skipped_not_fatal(capsys):
    from library_selector import profile_excluded_item_ids
    index = {"items": [{"item_id": 1, "name_base": "Float Sets", "structure": {"structure": [1]}}]}
    assert profile_excluded_item_ids(index, ['[', '^Float']) == frozenset({1})
    assert "not a valid regex" in capsys.readouterr().out
