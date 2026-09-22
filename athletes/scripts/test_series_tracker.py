from series_tracker import SeriesTracker


def _assignment(slot, level, expected_delta):
    return {
        'slot': slot,
        'name': 'VO2max 30/30',
        'level': level,
        'week': 0,
        'expected_delta': expected_delta,
    }


def test_default_level_delta_remains_plus_one():
    tracker = SeriesTracker()
    tracker.start_block()
    tracker.assign('intensity_1', 'VO2max 30/30', level=3)
    tracker.advance_week()
    result = tracker.assign('intensity_1', 'VO2max 30/30', level=4)

    assert result['note'] == ''
    assert tracker.validate_block() == []


def test_zero_delta_repeats_a_coherent_level():
    tracker = SeriesTracker()
    tracker.start_block()
    tracker.assign('intensity_1', 'VO2max 30/30', level=3)
    tracker.advance_week(level_delta=0)
    result = tracker.assign('intensity_1', 'VO2max 30/30', level=3)

    assert result['note'] == ''
    assert tracker.validate_block() == []


def test_in_block_jump_is_flagged_and_autocorrected():
    tracker = SeriesTracker()
    tracker.start_block()
    tracker.assign('intensity_1', 'VO2max 30/30', level=3)
    tracker.advance_week()
    result = tracker.assign('intensity_1', 'VO2max 30/30', level=5)

    assert 'expected +1' in result['note']
    assert result['level'] == 4


def test_validate_block_accepts_mixed_zero_and_one_deltas():
    tracker = SeriesTracker()
    tracker.start_block()
    tracker._current_block = [
        _assignment('intensity_1', 3, 1),
        _assignment('intensity_1', 3, 0),
        _assignment('intensity_1', 4, 1),
    ]

    assert tracker.validate_block() == []


def test_validate_block_rejects_a_decrease():
    tracker = SeriesTracker()
    tracker.start_block()
    tracker._current_block = [
        _assignment('intensity_1', 3, 1),
        _assignment('intensity_1', 4, 1),
        _assignment('intensity_1', 3, 1),
    ]

    violations = tracker.validate_block()

    assert violations
    assert 'expected +1' in violations[0]
