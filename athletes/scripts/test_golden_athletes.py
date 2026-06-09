#!/usr/bin/env python3
"""
Golden integration tests — 5 representative athletes.

Every archetype × discipline × plan-length combination below must produce a
plan that passes ALL critical compliance rules plus variety and structure
thresholds. These are the "would a coach ship this?" tests: if one fails,
the generator is producing plans we wouldn't hand to a paying athlete.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from block_chain import build_plan_from_calendar
from block_compliance import validate_plan, format_compliance_report


def make_descriptors(total_weeks: int) -> list:
    """Replicate calculate_plan_dates' standard week typing.

    Race week last; taper the week before (plans >= 8wk); recovery every
    4th week (skipping taper/race); phases base → build → peak by plan
    fraction (base 50%, build 25%, peak the rest).
    """
    descriptors = []
    base_end = max(1, round(total_weeks * 0.50))
    build_end = max(base_end + 1, round(total_weeks * 0.75))

    for w in range(1, total_weeks + 1):
        if w == total_weeks:
            phase, wtype = 'race', 'race'
        elif total_weeks >= 8 and w == total_weeks - 1:
            phase, wtype = 'taper', 'taper'
        else:
            if w <= base_end:
                phase = 'base'
            elif w <= build_end:
                phase = 'build'
            else:
                phase = 'peak'
            wtype = 'recovery' if (w % 4 == 0) else 'load'
        descriptors.append({'plan_week': w, 'phase': phase, 'week_type': wtype})
    return descriptors


GOLDEN_ATHLETES = {
    'time_crunched_road_8wk': dict(
        total_weeks=8, archetype='time_crunched', hours=6,
        off_days=['Mon'], discipline='road', max_level=6, max_intensity=2,
        min_unique_names=6,
    ),
    'specialist_gravel_12wk': dict(
        total_weeks=12, archetype='specialist', hours=10,
        off_days=['Fri'], discipline='gravel', max_level=6, max_intensity=3,
        min_unique_names=9,
    ),
    'volume_gravel_21wk_masters': dict(
        total_weeks=21, archetype='volume', hours=12,
        off_days=['Sun'], discipline='gravel', max_level=6, max_intensity=2,
        min_unique_names=10,
    ),
    'goat_mtb_16wk': dict(
        total_weeks=16, archetype='goat', hours=16,
        off_days=['Mon'], discipline='mtb', max_level=6, max_intensity=3,
        min_unique_names=10,
    ),
    'beginner_road_26wk': dict(
        total_weeks=26, archetype='specialist', hours=9,
        off_days=['Mon'], discipline='road', max_level=3, max_intensity=2,
        min_unique_names=8,
    ),
}


def _build(spec):
    return build_plan_from_calendar(
        week_descriptors=make_descriptors(spec['total_weeks']),
        archetype=spec['archetype'],
        max_level=spec['max_level'],
        max_intensity=spec['max_intensity'],
        off_days=spec['off_days'],
        long_ride_day='Sat',
        starting_level=1,
        hours_per_week=spec['hours'],
        discipline=spec['discipline'],
    )


@pytest.fixture(scope='module')
def golden_plans():
    return {name: (_build(spec), spec) for name, spec in GOLDEN_ATHLETES.items()}


class TestGoldenCompliance:
    """Every golden athlete passes ALL critical compliance rules."""

    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_critical_compliance(self, golden_plans, name):
        plan, spec = golden_plans[name]
        result = validate_plan(
            plan,
            target_hours=spec['hours'],
            off_days=spec['off_days'],
            max_intensity=spec['max_intensity'],
        )
        assert result['critical_pass'], (
            f"{name} failed compliance:\n{format_compliance_report(result)}"
        )


class TestGoldenStructure:
    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_every_load_week_has_long_ride(self, golden_plans, name):
        plan, spec = golden_plans[name]
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            sat = next(d for d in w['days'] if d['day'] == 'Sat')
            assert sat['name'] not in ('OFF', 'Rest Day'), (
                f"{name} W{w['plan_week']}: Saturday is {sat['name']}"
            )

    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_off_days_always_off(self, golden_plans, name):
        plan, spec = golden_plans[name]
        for w in plan['weeks']:
            for d in w['days']:
                if d['day'] in spec['off_days']:
                    assert d['role'] == 'off', (
                        f"{name} W{w['plan_week']} {d['day']}: {d['name']}"
                    )

    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_race_week_light(self, golden_plans, name):
        plan, spec = golden_plans[name]
        race_weeks = [w for w in plan['weeks'] if w['week_type'] == 'race']
        assert race_weeks, f"{name}: no race week"
        for w in race_weeks:
            total = sum(d['duration'] for d in w['days'])
            assert total <= 300, f"{name} race week too heavy: {total}min"

    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_weekly_hours_within_budget(self, golden_plans, name):
        plan, spec = golden_plans[name]
        tolerance = 1.15 if spec['hours'] < 6 else 1.10
        max_min = spec['hours'] * 60 * tolerance
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            total = sum(d['duration'] for d in w['days'])
            assert total <= max_min, (
                f"{name} W{w['plan_week']}: {total}min > {max_min:.0f}min budget"
            )


class TestGoldenVariety:
    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_unique_workout_names(self, golden_plans, name):
        plan, spec = golden_plans[name]
        names = {d['name'] for w in plan['weeks'] for d in w['days']
                 if d['name'] not in ('OFF', 'Rest Day')}
        assert len(names) >= spec['min_unique_names'], (
            f"{name}: only {len(names)} unique names "
            f"(need {spec['min_unique_names']}): {sorted(names)}"
        )

    @pytest.mark.parametrize('name', list(GOLDEN_ATHLETES))
    def test_no_phase_with_single_intensity_name(self, golden_plans, name):
        """Within any phase spanning 2+ blocks, intensity must vary."""
        plan, spec = golden_plans[name]
        by_phase = {}
        for w in plan['weeks']:
            if w['week_type'] != 'load':
                continue
            by_phase.setdefault(w['phase'], []).append(w)
        for phase, weeks in by_phase.items():
            blocks = {w.get('block_number') for w in weeks}
            if len(blocks) < 2:
                continue
            int_names = {d['name'] for w in weeks for d in w['days']
                         if d.get('role') == 'intensity'}
            assert len(int_names) >= 2, (
                f"{name} {phase}: single intensity workout "
                f"across {len(blocks)} blocks: {int_names}"
            )
