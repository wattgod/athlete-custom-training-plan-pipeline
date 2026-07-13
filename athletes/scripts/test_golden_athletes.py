#!/usr/bin/env python3
"""
Golden integration tests — 5 representative athletes.

Every archetype × discipline × plan-length combination below must produce a
plan that passes ALL critical compliance rules plus variety and structure
thresholds. These are the "would a coach ship this?" tests: if one fails,
the generator is producing plans we wouldn't hand to a paying athlete.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from block_chain import build_plan_from_calendar, derive_week_descriptors
from block_compliance import validate_plan, format_compliance_report
from calculate_plan_dates import calculate_plan_dates


def make_descriptors(total_weeks: int) -> list:
    """Build descriptors from the REAL calendar generator.

    The race date is computed relative to today so these tests never go
    stale, and the descriptors come from calculate_plan_dates →
    derive_week_descriptors — the exact production path. A private replica
    here would let calendar/builder drift slip through (the root cause of
    the June 2026 plan-quality incident).
    """
    # Race lands on the Saturday at least total_weeks weeks out
    race = date.today() + timedelta(weeks=total_weeks)
    race += timedelta(days=(5 - race.weekday()) % 7)  # next Saturday
    plan_dates = calculate_plan_dates(race.isoformat(), plan_weeks=total_weeks)
    return derive_week_descriptors(plan_dates)


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


class TestVolumeFloors:
    """B9/B10: load weeks hit their periodized floor; peak is never below build."""

    def test_peak_not_below_build(self, golden_plans):
        # B9: the peak floor lived under a bare 'peak' key, but CALENDAR_PHASE_MAP
        # renames peak->race_prep, so it was dead and peak fell to the 0.72
        # else-branch — BELOW build's 0.82. A GOAT athlete's peak ran ~74% (under
        # build ~85%), inverting periodization. Now peak >= build.
        plan, spec = golden_plans['goat_mtb_16wk']
        tgt = spec['hours'] * 60
        def avg(ph):
            loads = [w['total_duration'] for w in plan['weeks']
                     if w.get('phase') == ph and w.get('week_type') == 'load']
            return sum(loads) / len(loads) if loads else 0
        build_avg, peak_avg = avg('build'), avg('race_prep')
        assert build_avg > 0 and peak_avg > 0
        assert peak_avg >= build_avg, f"peak {peak_avg/tgt:.0%} < build {build_avg/tgt:.0%}"
        assert peak_avg / tgt >= 0.80, f"peak only {peak_avg/tgt:.0%} of target"

    def test_base_load_weeks_past_rampin_meet_floor(self, golden_plans):
        # B10: base load weeks past the ramp-in window (global plan_week>4, matching
        # R19's exemption) must be grown to the base floor, not left silently under
        # it by the old phase-local block_number exemption.
        plan, spec = golden_plans['goat_mtb_16wk']
        tgt = spec['hours'] * 60
        for w in plan['weeks']:
            if (w.get('phase') == 'base' and w.get('week_type') == 'load'
                    and w.get('plan_week', 0) > 4):
                assert w['total_duration'] / tgt >= 0.62, \
                    f"base W{w['plan_week']} at {w['total_duration']/tgt:.0%} < 0.62 floor"


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


class TestRenderCoverage:
    """Every selectable workout name must render under every methodology.

    The Nate generator's methodology avoid-lists used to veto planner
    selections into None (MAF_LT1 × VO2max), silently dropping those days
    to legacy templates. The mapper now falls back to POLARIZED rendering;
    this test pins the invariant.
    """

    def test_all_names_render_under_all_methodologies(self):
        from workout_mapper import render_workout, get_mapped_types
        from generate_athlete_package import METHODOLOGY_MAP
        failures = []
        for m in sorted(set(METHODOLOGY_MAP.values())):
            for n in get_mapped_types():
                if render_workout(n, level=3, methodology=m) is None:
                    failures.append((m, n))
        assert not failures, f"Render failures: {failures}"

    def test_rendered_durations_match_library(self):
        """Every emittable workout must render at a plausible duration.

        The 'NP/IF Target' archetype had no render handler and shipped a
        10-MINUTE long ride for entire base blocks — not-None alone is
        not enough; the minutes must agree with the workout library.
        """
        import re
        import yaml
        from pathlib import Path
        from workout_mapper import WORKOUT_MAP, render_workout
        from generate_athlete_package import METHODOLOGY_MAP
        from workout_library import WorkoutLibrary

        lib = WorkoutLibrary()
        sel = yaml.safe_load(
            (Path(__file__).parent.parent / 'config' / 'workout_selection.yaml').read_text())
        names = set()

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                names.add(o)

        walk(sel)
        emittable = sorted(n for n in names if n in WORKOUT_MAP)
        assert len(emittable) >= 25, "selection surface shrank unexpectedly"

        failures = []
        methodologies = sorted(set(METHODOLOGY_MAP.values()))
        for name in emittable:
            for level in (1, 3, 6):  # ends + middle of the ladder
                try:
                    expect = lib.get_duration(name, level)
                except Exception:
                    expect = 0
                for m in methodologies:
                    xml = render_workout(name, level=level, methodology=m)
                    if xml is None:
                        continue  # legitimate veto — upstream falls back
                    mins = sum(int(d) for d in re.findall(r'Duration="(\d+)"', xml)) / 60
                    if name not in ('Rest Day', 'Openers') and mins < 15:
                        failures.append(f"{name} L{level} {m}: {mins:.0f}min")
                    elif expect and abs(mins - expect) > max(0.5 * expect, 45):
                        failures.append(
                            f"{name} L{level} {m}: {mins:.0f}min vs library {expect}min")
        assert not failures, f"{len(failures)} duration violations: {failures[:8]}"


class TestGoldenDayCaps:
    """Per-day duration caps must hold in the plan dict."""

    def test_capped_athlete_no_day_exceeds_cap(self):
        caps = {'Mon': 60, 'Tue': 75, 'Wed': 60, 'Thu': 75, 'Fri': 60,
                'Sat': 300, 'Sun': 0}
        plan = build_plan_from_calendar(
            week_descriptors=make_descriptors(12),
            archetype='specialist', off_days=['Sun'], long_ride_day='Sat',
            hours_per_week=8, discipline='gravel', day_caps=caps,
        )
        violations = []
        for w in plan['weeks']:
            for d in w['days']:
                if d.get('role') == 'off':
                    continue
                cap = caps.get(d['day'], 0)
                if cap and d.get('duration', 0) > cap:
                    violations.append(
                        f"W{w['plan_week']} {d['day']}: {d['duration']} > {cap}")
        assert not violations, f"Day cap violations: {violations}"


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
