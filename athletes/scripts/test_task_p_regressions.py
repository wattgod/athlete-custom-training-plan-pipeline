"""Regression coverage for Task P: recovery after simulations and plan variety."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from block_chain import build_plan_from_calendar, protect_post_simulation_recovery
from block_compliance import (r01_no_back_to_back_intensity,
                              r03_recovery_tss_ceiling)
from generate_athlete_package import race_day_tss_from_emitted_minutes
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
