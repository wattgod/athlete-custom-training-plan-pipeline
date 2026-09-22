from block_chain import build_plan_from_calendar
from block_compliance import r15_level_progression, validate_plan


def _descriptors(count=4):
    return [
        {'plan_week': week, 'phase': 'base', 'week_type': 'load'}
        for week in range(1, count + 1)
    ]


def _intensity_levels(plan):
    return [
        [day['level'] for day in week['days'] if day.get('role') == 'intensity']
        for week in plan['weeks']
    ]


def test_hours_ramp_uses_volume_as_the_only_progression_lever():
    plan = build_plan_from_calendar(
        week_descriptors=_descriptors(),
        archetype='specialist',
        hours_per_week=8,
        hours_schedule={1: 6, 2: 7, 3: 8, 4: 8},
        off_days=['Sun'],
        max_intensity=2,
    )

    assert _intensity_levels(plan) == [[1, 1], [1, 1], [1, 1], [2, 2]]
    assert [
        week['progression_lever'] for week in plan['weeks']
    ] == [None, 'volume', 'volume', 'intensity']


def test_without_hours_schedule_preserves_plus_one_level_ladder():
    plan = build_plan_from_calendar(
        week_descriptors=_descriptors(),
        archetype='specialist',
        hours_per_week=8,
        off_days=['Sun'],
        max_intensity=2,
    )

    assert _intensity_levels(plan) == [[1, 1], [2, 2], [3, 3], [4, 4]]
    assert [
        week['progression_lever'] for week in plan['weeks']
    ] == [None, 'intensity', 'intensity', 'intensity']


def _compliance_plan(levels):
    return {
        'weeks': [
            {
                'plan_week': index,
                'week_type': 'load',
                'block_number': 1,
                'days': [
                    {
                        'day': day,
                        'role': 'intensity',
                        'level': level,
                        'name': 'VO2max 30/30',
                    }
                    for day, level in zip(('Tue', 'Thu'), week_levels)
                ],
            }
            for index, week_levels in enumerate(levels, start=1)
        ]
    }


def test_r15_accepts_one_lever_levels_and_is_advisory():
    plan = _compliance_plan([[3, 3], [3, 4]])

    passed, message = r15_level_progression(plan)
    result = validate_plan(plan)

    assert passed
    assert message == 'Level progression follows AE-4.1'
    assert result['rules']['R15']['severity'] == 'WARNING'
    assert result['rules']['R15']['passed'] is True


def test_r15_rejects_a_level_decrease():
    passed, message = r15_level_progression(
        _compliance_plan([[3, 4], [2, 4]]))

    assert not passed
    assert 'level delta -1' in message
