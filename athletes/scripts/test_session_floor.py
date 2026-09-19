"""AE-2.7 amendment (Matti, 2026-09-17): 60-minute session floor.

"An hour should be a minimum, with the average for a 9-5, ~10 h/wk rider
being ~1.5 h on a weekday." 35/40/45-minute cards ship only when the athlete
explicitly asked for short sessions. Under-floor sessions grow to the weekday
target instead of being shipped as stubs; race-week openers and days whose
availability cap is itself under the floor are exempt.
"""
import block_builder as bb
import library_selector as ls


def _week():
    return [
        {'day': 'Mon', 'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'rest'},
        {'day': 'Tue', 'name': 'Cadence Work', 'level': 1, 'tss': 24, 'duration': 35, 'role': 'filler'},
        {'day': 'Wed', 'name': 'Endurance', 'level': 1, 'tss': 55, 'duration': 70, 'role': 'filler'},
        {'day': 'Thu', 'name': 'Microbursts', 'level': 1, 'tss': 24, 'duration': 32, 'role': 'intensity'},
        {'day': 'Fri', 'name': 'OFF', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'off'},
        {'day': 'Sat', 'name': 'Endurance', 'level': 4, 'tss': 128, 'duration': 180, 'role': 'long_ride'},
        {'day': 'Sun', 'name': 'Endurance', 'level': 1, 'tss': 55, 'duration': 70, 'role': 'filler'},
    ]


def test_weekday_target_is_about_ninety_minutes_for_a_ten_hour_rider():
    # 600 min - 180 long ride, over 4 other rides = 105
    assert bb.weekday_target_minutes(_week(), 10, 60) == 105


def test_under_floor_sessions_grow_to_the_weekday_target_and_add_z2_tss():
    days = _week()
    grown = bb.apply_session_floor(days, hours_per_week=10, day_caps=None)
    assert sorted(grown) == ['Cadence Work', 'Microbursts']
    tue = next(d for d in days if d['day'] == 'Tue')
    thu = next(d for d in days if d['day'] == 'Thu')
    assert tue['duration'] == 105 and thu['duration'] == 105
    assert tue['floor_extended_min'] == 70
    assert tue['tss'] == 24 + round(70 * bb._Z2_TSS_PER_MIN)
    # sessions already over the floor are untouched
    assert next(d for d in days if d['day'] == 'Wed')['duration'] == 70


def test_athlete_stated_short_cap_is_the_explicit_request():
    days = _week()
    bb.apply_session_floor(days, hours_per_week=10, day_caps={'Tue': 45})
    tue = next(d for d in days if d['day'] == 'Tue')
    assert tue['duration'] == 35 and 'floor_extended_min' not in tue


def test_cap_above_floor_bounds_the_growth():
    days = _week()
    bb.apply_session_floor(days, hours_per_week=10, day_caps={'Thu': 75})
    assert next(d for d in days if d['day'] == 'Thu')['duration'] == 75


def test_race_week_openers_are_exempt_but_the_easy_day_is_not():
    days = [
        {'day': 'Wed', 'name': 'Endurance', 'level': 1, 'tss': 39, 'duration': 50, 'role': 'filler'},
        {'day': 'Fri', 'name': 'Openers', 'level': 2, 'tss': 26, 'duration': 40, 'role': 'intensity'},
        {'day': 'Sat', 'name': 'RACE_DAY', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'race'},
    ]
    bb.apply_session_floor(days, hours_per_week=0, week_type='race', grow_to_weekday_target=False)
    assert days[1]['duration'] == 40
    assert days[0]['duration'] == 60


def test_opt_in_floor_is_forty_five():
    days = _week()
    bb.apply_session_floor(days, hours_per_week=10, floor_min=bb.SESSION_FLOOR_MIN_OPT_IN,
                           grow_to_weekday_target=False)
    assert next(d for d in days if d['day'] == 'Tue')['duration'] == 45


def test_library_window_never_reaches_under_the_floor():
    lo, hi = ls._duration_bounds(60, None, 'Cadence Work', session_floor_min=60)
    assert lo == 60 and hi >= 60
    lo_old, _ = ls._duration_bounds(60, None, 'Cadence Work')
    assert lo_old < 60  # the pre-ruling window (0.70 x budget) reached to 42 min
