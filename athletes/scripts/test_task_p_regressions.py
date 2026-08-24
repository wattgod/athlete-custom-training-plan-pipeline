"""Regression coverage for Task P: recovery after simulations and plan variety."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from block_chain import (build_plan_from_calendar,
                         protect_post_simulation_recovery,
                         pre_simulation_strength_block_days)
from block_compliance import (r01_no_back_to_back_intensity,
                              r03_recovery_tss_ceiling)
from generate_athlete_package import (race_day_tss_from_emitted_minutes,
                                      place_strength_days)
from workout_mapper import endurance_focus_title


def _day(day, name, role, duration, tss, **extra):
    return {'day': day, 'name': name, 'role': role,
            'duration': duration, 'tss': tss, **extra}


def test_r01_detects_a_hard_session_across_the_sunday_monday_seam():
    weeks = [
        {'plan_week': 1, 'days': [
            _day('Sun', 'Act Race Simulation', 'long_ride', 250, 250,
                 act_simulation={'dress_rehearsal': True}),
        ]},
        {'plan_week': 2, 'days': [
            _day('Mon', 'Thirty-Fifteens', 'intensity', 55, 70),
        ]},
    ]

    passed, message = r01_no_back_to_back_intensity(weeks)

    assert not passed
    assert 'W1 Sun→W2 Mon' in message


def test_post_simulation_day_is_easy_and_displaced_sharpener_moves_to_interval_day():
    plan = {'weeks': [
        {'plan_week': 1, 'days': [
            _day('Sun', 'Act Race Simulation', 'long_ride', 250, 250,
                 act_simulation={'dress_rehearsal': True}),
        ]},
        {'plan_week': 2, 'days': [
            _day('Mon', 'Thirty-Fifteens', 'intensity', 55, 70),
            _day('Tue', 'OFF', 'off', 0, 0),
            _day('Thu', 'Endurance', 'filler', 70, 55),
        ]},
    ]}

    protected = protect_post_simulation_recovery(plan, ['Thu'])
    monday = plan['weeks'][1]['days'][0]
    thursday = plan['weeks'][1]['days'][2]

    assert protected == {(2, 'Mon')}
    assert monday['post_sim_recovery'] is True
    assert monday['name'] == 'Endurance'
    assert monday['role'] == 'filler'
    assert thursday['name'] == 'Thirty-Fifteens'
    assert thursday['role'] == 'intensity'
    assert r01_no_back_to_back_intensity(plan['weeks'])[0]


def test_pre_simulation_strength_block_days_flags_the_day_before_dress_rehearsal():
    """Regression: verified live, loaded strength (Power B -- Bulgarians +
    trap-bar triples) landed on the Saturday immediately before a Sunday
    Act 2 dress rehearsal -- the plan's biggest day -- while Act 1 got a
    3-day strength buffer. The day before an Act-class simulation must be
    flagged for strength placement to avoid."""
    plan = {'weeks': [
        {'plan_week': 1, 'days': [
            _day('Mon', 'Threshold', 'intensity', 60, 70),
            _day('Tue', 'OFF', 'off', 0, 0),
            _day('Wed', 'Endurance', 'filler', 70, 55),
            _day('Thu', 'Thirty-Fifteens', 'intensity', 55, 70),
            _day('Fri', 'OFF', 'off', 0, 0),
            _day('Sat', 'Endurance', 'filler', 90, 60),
            _day('Sun', 'Act Race Simulation', 'long_ride', 250, 245,
                 act_simulation={'dress_rehearsal': True}, is_dress_rehearsal=True),
        ]},
    ]}

    blocked = pre_simulation_strength_block_days(plan)

    assert blocked == {(1, 'Sat')}
    # An easy bike day the day before is untouched -- only strength cares.
    assert plan['weeks'][0]['days'][5]['name'] == 'Endurance'


def test_strength_relocates_off_the_day_before_a_dress_rehearsal():
    """Regression: a week with a Sunday act-sim and Saturday strength in the
    naive layout must relocate strength to Thu or earlier once the pre-sim
    day is blocked, using place_strength_days' own candidate selection."""
    plan = {'weeks': [
        {'plan_week': 1, 'days': [
            _day('Mon', 'Threshold', 'intensity', 60, 70),
            _day('Tue', 'OFF', 'off', 0, 0),
            _day('Wed', 'Endurance', 'filler', 70, 55),
            _day('Thu', 'Thirty-Fifteens', 'intensity', 55, 70),
            _day('Fri', 'OFF', 'off', 0, 0),
            _day('Sat', 'Endurance', 'filler', 90, 60),
            _day('Sun', 'Act Race Simulation', 'long_ride', 250, 245,
                 act_simulation={'dress_rehearsal': True}, is_dress_rehearsal=True),
        ]},
    ]}
    protected_days = {day for week, day in pre_simulation_strength_block_days(plan)
                      if week == 1}
    assert protected_days == {'Sat'}

    def is_available(day):
        return day != 'Sun'  # Sunday is the long/act-sim day

    naive = place_strength_days(is_available, 1, strength_only_abbrevs=['Sat'])
    assert naive == ['Sat']  # confirms the naive layout really does land on Saturday

    relocated = place_strength_days(is_available, 1, blocked_days=protected_days,
                                    strength_only_abbrevs=['Sat'])
    assert relocated and relocated[0] != 'Sat'
    assert relocated[0] in ('Mon', 'Tue', 'Wed', 'Thu')


def test_strength_avoids_vo2_intensity_day_when_an_easy_day_is_available():
    """AE-8.4 (sol programming review 2026-08-24, major 9): the default
    coach-preferred strength pair (Tue/Thu) collides directly with the
    default intensity_1/intensity_2 slot days, stacking strength onto VO2
    days. avoid_days must sink an eligible-but-intensity day behind every
    non-intensity candidate."""
    def is_available(day):
        return day in ('Tue', 'Wed', 'Thu', 'Fri')

    placed = place_strength_days(is_available, 1, avoid_days={'Tue', 'Thu'})
    assert placed == ['Wed']


def test_strength_falls_back_to_an_avoided_day_to_keep_weekly_frequency():
    """avoid_days is a soft preference, never a hard block -- if nothing
    else can satisfy the requested session count, the avoided (intensity)
    day is still used rather than silently dropping the session."""
    def is_available(day):
        return day in ('Tue', 'Thu')

    placed = place_strength_days(is_available, 2, avoid_days={'Tue', 'Thu'})
    assert sorted(placed) == ['Thu', 'Tue']


def test_strength_never_lands_on_a_hard_blocked_test_day_even_without_avoid():
    """Test days (FTP Test / Anaerobic Test) are a hard block, not a soft
    avoid -- unlike VO2/intensity days, there is no frequency-preserving
    fallback onto them (AE-8.4's morning-primer exception does not apply
    to test days)."""
    def is_available(day):
        return day in ('Tue', 'Thu')

    placed = place_strength_days(is_available, 2, blocked_days={'Tue', 'Thu'})
    assert placed == []


def test_strength_drops_for_the_week_when_no_relocation_slot_fits():
    """Relocation is preferred, but when the pre-sim day is the only
    available day, the session must drop for that week rather than
    silently keeping the blocked placement."""
    def is_available(day):
        return day == 'Sat'  # only the blocked day is available at all

    relocated = place_strength_days(is_available, 1, blocked_days={'Sat'},
                                    strength_only_abbrevs=['Sat'])
    assert relocated == []


def test_recovery_floor_uses_preceding_load_weeks_and_stays_in_house_band():
    descriptors = [
        {'plan_week': 1, 'phase': 'base', 'week_type': 'load'},
        {'plan_week': 2, 'phase': 'base', 'week_type': 'load'},
        {'plan_week': 3, 'phase': 'base', 'week_type': 'load'},
        {'plan_week': 4, 'phase': 'base', 'week_type': 'recovery'},
    ]
    plan = build_plan_from_calendar(
        descriptors, archetype='specialist', max_intensity=2,
        off_days=['Tue'], long_ride_day='Sun', hours_per_week=10,
    )
    loads = [week['total_tss'] for week in plan['weeks'][:3]]
    recovery = plan['weeks'][3]['total_tss']
    ratio = recovery / (sum(loads) / len(loads))

    assert 0.50 <= ratio <= 0.65
    assert r03_recovery_tss_ceiling(plan['weeks'])[0]


def test_cadence_skill_never_returns_to_introductory_level_in_later_phases():
    descriptors = [
        {'plan_week': 1, 'phase': 'base', 'week_type': 'load'},
        {'plan_week': 2, 'phase': 'base', 'week_type': 'load'},
        {'plan_week': 3, 'phase': 'base', 'week_type': 'recovery'},
        {'plan_week': 4, 'phase': 'peak', 'week_type': 'load'},
        {'plan_week': 5, 'phase': 'peak', 'week_type': 'load'},
        {'plan_week': 6, 'phase': 'taper', 'week_type': 'taper'},
    ]
    plan = build_plan_from_calendar(
        descriptors, archetype='specialist', max_intensity=2,
        off_days=['Tue'], long_ride_day='Sun', hours_per_week=10,
    )
    levels = [
        (week['plan_week'], day['level'])
        for week in plan['weeks'] for day in week['days']
        if day['name'] == 'Cadence Work'
    ]

    highest = 0
    for _, level in levels:
        assert level >= highest
        highest = max(highest, level)
    assert highest >= 2


def test_load_filler_pool_rotates_existing_workout_types():
    descriptors = [
        {'plan_week': number, 'phase': 'base', 'week_type': 'load'}
        for number in range(1, 4)
    ]
    plan = build_plan_from_calendar(
        descriptors, archetype='specialist', max_intensity=2,
        off_days=['Tue'], long_ride_day='Sun', hours_per_week=10,
    )
    filler_names = [
        day['name'] for week in plan['weeks'] for day in week['days']
        if day['role'] == 'filler'
    ]

    assert {'Endurance', 'Cadence Work', 'Endurance Blocks',
            'Taper Burst Endurance'} <= set(filler_names)
    assert max(Counter(filler_names).values()) <= 3


def test_endurance_focus_titles_rotate_without_a_fourth_identical_card():
    # The generator uses a monotonic variation offset for rendered Endurance
    # fillers. Six honest focus variants keep an 18-card plan at three or
    # fewer cards per title rather than restarting the old 70min generic card.
    titles = [endurance_focus_title(offset) for offset in range(18)]

    assert len(set(titles)) == 6
    assert max(Counter(titles).values()) <= 3


def test_race_day_description_tss_uses_emitted_free_ride_duration():
    # 5.2h rounds to an emitted 310-minute FreeRide, which is 218 TSS with
    # the shared parser's IF=0.65 estimate.  The old raw-hour calculation
    # yielded 220 while PlanIR correctly held 218.
    assert race_day_tss_from_emitted_minutes(310) == 218
