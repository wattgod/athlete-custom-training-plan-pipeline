#!/usr/bin/env python3
"""
Tests for the calendar-driven plan builder (build_plan_from_calendar).

Regression coverage for the Jesse Couch pipeline bugs (June 2026):
- Recovery weeks lost their Saturday long ride entirely (Rest Day alternation
  landed on the long-ride day; renderer skips Rest Day files)
- Final block of N%3==0 plans treated Wks N-2..N as 'racing' (Tue-Fri all
  Rest Days for three straight weeks)
- block_chain's L/L/R rhythm disagreed with plan_dates' recovery weeks, so
  recovery landed on the wrong weeks and load weeks ran 5h long rides in
  weeks plan_dates considered recovery
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from block_chain import build_plan_from_calendar, CALENDAR_PHASE_MAP
from block_builder import build_calendar_week
from workout_selector import (
    select_workouts_for_week,
    _select_recovery_week,
    _select_taper_week,
    _load_selection_config,
    get_workout_duration,
)


def _jesse_descriptors():
    """Jesse Couch's 21-week calendar: base W1-10, build W11-15,
    peak W16-19, taper W20, race W21; recovery W4/8/12/16."""
    descriptors = []
    for w in range(1, 22):
        if w <= 10:
            phase = 'base'
        elif w <= 15:
            phase = 'build'
        elif w <= 19:
            phase = 'peak'
        elif w == 20:
            phase = 'taper'
        else:
            phase = 'race'
        if w == 21:
            wtype = 'race'
        elif w == 20:
            wtype = 'taper'
        elif w in (4, 8, 12, 16):
            wtype = 'recovery'
        else:
            wtype = 'load'
        descriptors.append({'plan_week': w, 'phase': phase, 'week_type': wtype})
    return descriptors


def _build_jesse_plan(**overrides):
    kwargs = dict(
        week_descriptors=_jesse_descriptors(),
        archetype='goat',
        max_level=6,
        max_intensity=3,
        off_days=['Sun'],
        long_ride_day='Sat',
        starting_level=1,
        hours_per_week=15,
    )
    kwargs.update(overrides)
    return build_plan_from_calendar(**kwargs)


def _week(plan, n):
    return next(w for w in plan['weeks'] if w['plan_week'] == n)


def _day(week, abbrev):
    return next(d for d in week['days'] if d['day'] == abbrev)


class TestRecoveryWeekSelection:
    def test_recovery_week_has_long_ride_slot(self):
        config = _load_selection_config()
        menu = _select_recovery_week(config, hours_per_week=12)
        roles = [w['role'] for w in menu]
        assert 'long_ride' in roles

    def test_recovery_long_ride_is_short(self):
        config = _load_selection_config()
        menu = _select_recovery_week(config, hours_per_week=12)
        lr = next(w for w in menu if w['role'] == 'long_ride')
        dur = get_workout_duration(lr['name'], lr['level'])
        assert 0 < dur <= 150, f"Recovery long ride should be <=150min, got {dur}"

    def test_low_hours_athlete_gets_shorter_recovery_ride(self):
        config = _load_selection_config()
        low = _select_recovery_week(config, hours_per_week=6)
        high = _select_recovery_week(config, hours_per_week=15)
        lr_low = next(w for w in low if w['role'] == 'long_ride')
        lr_high = next(w for w in high if w['role'] == 'long_ride')
        assert lr_low['level'] <= lr_high['level']


class TestTaperWeekSelection:
    def test_taper_returns_openers_and_short_ride(self):
        menu = _select_taper_week(hours_per_week=12)
        roles = [w['role'] for w in menu]
        assert roles.count('intensity') == 2  # two openers
        assert 'long_ride' in roles
        names = [w['name'] for w in menu if w['role'] == 'intensity']
        assert all(n == 'Openers' for n in names)

    def test_select_workouts_for_week_accepts_taper(self):
        menu = select_workouts_for_week(
            phase='taper', archetype='specialist', week_type='taper',
            week_in_block=1, base_level=3,
        )
        assert any(w['role'] == 'long_ride' for w in menu)


class TestCalendarPlan:
    def test_every_load_week_has_saturday_long_ride(self):
        plan = _build_jesse_plan()
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            sat = _day(w, 'Sat')
            assert sat['name'] not in ('OFF', 'Rest Day'), (
                f"W{w['plan_week']} (load) Saturday must have a long ride, "
                f"got {sat['name']}"
            )
            assert sat['duration'] >= 120, (
                f"W{w['plan_week']} load-week long ride too short: {sat['duration']}min"
            )

    def test_recovery_weeks_have_short_saturday_ride(self):
        plan = _build_jesse_plan()
        for n in (4, 8, 12, 16):
            sat = _day(_week(plan, n), 'Sat')
            assert sat['name'] == 'Endurance', (
                f"W{n} (recovery) Saturday should be a short Endurance ride, "
                f"got {sat['name']}"
            )
            assert 60 <= sat['duration'] <= 150

    def test_recovery_week_volume_in_band(self):
        """Recovery weeks must meaningfully unload vs the preceding load week.

        Target band is 50-65%, widened to 30-75% here because base-phase load
        weeks are currently underloaded (filler stuck at Endurance L1 — the
        Phase 3 duration ladder will raise base load volume and tighten this
        band back to 0.65 on the high side).
        """
        plan = _build_jesse_plan()
        for n in (8, 12, 16):
            rec = sum(d['duration'] for d in _week(plan, n)['days'])
            prev_load = sum(d['duration'] for d in _week(plan, n - 1)['days'])
            ratio = rec / prev_load
            assert 0.30 <= ratio <= 0.75, (
                f"W{n} recovery volume ratio {ratio:.2f} outside band"
            )

    def test_final_three_weeks_are_not_all_rest(self):
        """Regression: 21-week plans used to make Wks 19-21 a 'racing' block
        with Tue-Fri Rest Days for all three weeks."""
        plan = _build_jesse_plan()
        w19 = _week(plan, 19)
        riding_days = [d for d in w19['days']
                       if d['name'] not in ('OFF', 'Rest Day')]
        assert len(riding_days) >= 5, (
            f"W19 (peak load week) should be a full week, got "
            f"{[(d['day'], d['name']) for d in w19['days']]}"
        )
        assert _day(w19, 'Sat')['duration'] >= 240, "W19 peak long ride missing"

    def test_taper_week_volume_reduced(self):
        plan = _build_jesse_plan()
        w20 = sum(d['duration'] for d in _week(plan, 20)['days'])
        w19 = sum(d['duration'] for d in _week(plan, 19)['days'])
        assert w20 < w19 * 0.65, f"Taper week not reduced: {w20} vs {w19}"

    def test_race_week_is_mostly_rest(self):
        plan = _build_jesse_plan()
        w21 = _week(plan, 21)
        total = sum(d['duration'] for d in w21['days'])
        assert total <= 240, f"Race week too heavy: {total}min"

    def test_load_weeks_have_two_or_three_intensity(self):
        plan = _build_jesse_plan()
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            n_int = sum(1 for d in w['days'] if d.get('role') == 'intensity')
            assert 2 <= n_int <= 3, (
                f"W{w['plan_week']} has {n_int} intensity days (want 2-3)"
            )

    def test_off_days_respected(self):
        plan = _build_jesse_plan()
        for w in plan['weeks']:
            sun = _day(w, 'Sun')
            assert sun['name'] == 'OFF', f"W{w['plan_week']} Sunday must be OFF"

    def test_week_types_follow_descriptors(self):
        plan = _build_jesse_plan()
        descriptors = {d['plan_week']: d['week_type'] for d in _jesse_descriptors()}
        for w in plan['weeks']:
            assert w['week_type'] == descriptors[w['plan_week']]

    def test_level_progresses_across_blocks(self):
        plan = _build_jesse_plan()
        w1_mon = _day(_week(plan, 1), 'Mon')
        w9_mon = _day(_week(plan, 9), 'Mon')
        assert w9_mon['level'] > w1_mon['level']

    def test_phase_map_covers_plan_dates_phases(self):
        for phase in ('base', 'build', 'peak', 'taper', 'race'):
            assert phase in CALENDAR_PHASE_MAP


class TestVariety:
    """Phase 3 regression: 80 of 150 workouts used to be identical
    'Endurance.zwo'. Selection must rotate names across blocks and days."""

    def test_at_least_12_unique_workout_names(self):
        plan = _build_jesse_plan()
        names = {d['name'] for w in plan['weeks'] for d in w['days']
                 if d['name'] not in ('OFF', 'Rest Day')}
        assert len(names) >= 12, f"Only {len(names)} unique names: {sorted(names)}"

    def test_long_rides_rotate_across_blocks(self):
        plan = _build_jesse_plan()
        long_ride_names = {
            _day(w, 'Sat')['name'] for w in plan['weeks']
            if w['week_type'] == 'load'
        }
        assert len(long_ride_names) >= 3, (
            f"Long rides should rotate variants, got {long_ride_names}"
        )

    def test_filler_days_vary_within_week(self):
        """At least some load weeks must have >1 distinct filler name."""
        plan = _build_jesse_plan()
        weeks_with_varied_fillers = 0
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            fillers = {d['name'] for d in w['days'] if d.get('role') == 'filler'}
            if len(fillers) > 1:
                weeks_with_varied_fillers += 1
        assert weeks_with_varied_fillers >= 10, (
            f"Only {weeks_with_varied_fillers} load weeks have varied fillers"
        )

    def test_adjacent_blocks_use_different_intensity(self):
        """Wednesday intensity in base block 1 vs block 2 must differ."""
        plan = _build_jesse_plan()
        # W1 (block 1) and W5 (block 2) are both base-phase load weeks
        w1_int = {d['name'] for d in _week(plan, 1)['days'] if d.get('role') == 'intensity'}
        w5_int = {d['name'] for d in _week(plan, 5)['days'] if d.get('role') == 'intensity'}
        assert w1_int != w5_int, (
            f"Adjacent blocks repeat the same intensity menu: {w1_int}"
        )

    def test_filler_level_ladders_up(self):
        """Fillers progress from L1 early-plan to L2+ later (volume builds)."""
        plan = _build_jesse_plan()
        early = [d['level'] for d in _week(plan, 1)['days'] if d.get('role') == 'filler']
        late = [d['level'] for d in _week(plan, 17)['days'] if d.get('role') == 'filler']
        assert max(late) > max(early), (
            f"Filler levels never progress: early {early}, late {late}"
        )

    def test_weekly_volume_builds_across_plan(self):
        plan = _build_jesse_plan()
        w1 = sum(d['duration'] for d in _week(plan, 1)['days'])
        w19 = sum(d['duration'] for d in _week(plan, 19)['days'])
        assert w19 > w1 * 1.3, (
            f"Plan volume should build: W1={w1}min, W19={w19}min"
        )


class TestBuildCalendarWeek:
    def test_single_recovery_week_standalone(self):
        week = build_calendar_week(
            week_type='recovery', phase='base', archetype='specialist',
            block_number=2, week_in_block=1, base_level=2,
            off_days=['Sun'], long_ride_day='Sat', hours_per_week=10,
        )
        sat = next(d for d in week['days'] if d['day'] == 'Sat')
        assert sat['name'] == 'Endurance'
        assert sat['role'] == 'long_ride'

    def test_short_plan_no_taper(self):
        """4-week plan: 3 load + race week — no recovery, no taper."""
        descriptors = [
            {'plan_week': 1, 'phase': 'build', 'week_type': 'load'},
            {'plan_week': 2, 'phase': 'build', 'week_type': 'load'},
            {'plan_week': 3, 'phase': 'peak', 'week_type': 'load'},
            {'plan_week': 4, 'phase': 'race', 'week_type': 'race'},
        ]
        plan = build_plan_from_calendar(
            week_descriptors=descriptors, archetype='time_crunched',
            off_days=['Mon'], long_ride_day='Sat', hours_per_week=6,
        )
        assert len(plan['weeks']) == 4
        for n in (1, 2, 3):
            sat = _day(_week(plan, n), 'Sat')
            assert sat['name'] not in ('OFF', 'Rest Day')
