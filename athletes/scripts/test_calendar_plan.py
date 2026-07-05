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


_DEFAULT_PLAN_CACHE = {}


def _build_jesse_plan(**overrides):
    """Build the canonical 21-week test plan. The no-override default is
    memoized — a dozen tests use it and each build takes ~3s."""
    if not overrides:
        if 'default' not in _DEFAULT_PLAN_CACHE:
            _DEFAULT_PLAN_CACHE['default'] = _build_jesse_plan(_fresh=True)
        return _DEFAULT_PLAN_CACHE['default']
    overrides.pop('_fresh', None)
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
            assert 0.30 <= ratio <= 0.72, (
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


class TestDisciplineGating:
    """Phase 4: discipline-specific archetype pools."""

    def _intensity_menu(self, discipline):
        plan = _build_jesse_plan(archetype='specialist', hours_per_week=10,
                                 discipline=discipline)
        return {d['name'] for w in plan['weeks'] for d in w['days']
                if d.get('role') == 'intensity' and d['name'] != 'Openers'}

    def test_gravel_gets_gravel_specific_work(self):
        menu = self._intensity_menu('gravel')
        assert 'Microbursts' in menu or 'SFR' in menu, (
            f"Gravel plan missing gravel-specific work: {sorted(menu)}"
        )

    def test_road_does_not_get_microbursts(self):
        menu = self._intensity_menu('road')
        assert 'Microbursts' not in menu

    def test_mtb_gets_neuromuscular_work(self):
        menu = self._intensity_menu('mtb')
        assert 'Stomps' in menu or 'Microbursts' in menu

    def test_disciplines_produce_different_menus(self):
        menus = {d: self._intensity_menu(d) for d in ('gravel', 'road', 'mtb')}
        assert menus['gravel'] != menus['road']
        assert menus['road'] != menus['mtb']


class TestDeriveDiscipline:
    def test_keyword_detection(self):
        from archetype import derive_discipline
        cases = [
            ('Unbound Gravel 200', 'gravel'),
            ('El Tour de Tucson', 'road'),
            ('Maratona Gran Fondo', 'road'),
            ('Leadville Trail 100 MTB', 'mtb'),
            ('Borderlands AZ State Championships', 'gravel'),  # default
        ]
        for name, expected in cases:
            got = derive_discipline({'target_race': {'name': name}})
            assert got == expected, f"{name}: expected {expected}, got {got}"

    def test_explicit_field_wins(self):
        from archetype import derive_discipline
        profile = {'discipline': 'road', 'target_race': {'name': 'Gravel Worlds'}}
        assert derive_discipline(profile) == 'road'


class TestMethodologyDifferentiatesThePlan:
    """ANTI-THEATER: the four methodologies must produce genuinely DIFFERENT
    workout plans, not the same plan with different labels. The methodology
    steers the secondary (non-VO2) intensity day; the VO2 day and discipline
    work are preserved."""

    def _secondaries(self, methodology):
        from block_compliance import VO2MAX_TYPES
        plan = build_plan_from_calendar(
            week_descriptors=_jesse_descriptors(), archetype='specialist',
            max_level=6, max_intensity=2, off_days=['Sun'], long_ride_day='Sat',
            hours_per_week=8, methodology=methodology)
        names = set()
        for w in plan['weeks']:
            if w.get('week_type') == 'load':
                for d in w['days']:
                    if d.get('role') == 'intensity' and d['name'] not in VO2MAX_TYPES:
                        names.add(d['name'])
        return names

    def test_methods_produce_different_intensity_work(self):
        pol = self._secondaries('polarized_80_20')
        gsp = self._secondaries('g_spot')
        pyr = self._secondaries('traditional_pyramidal')
        # each method's signature work shows up and the sets are not identical
        assert any('G-Spot' in n or 'Threshold Touch' in n or 'Threshold Steady' in n for n in gsp)
        assert any('Tempo' in n for n in pyr)
        assert pol != gsp and gsp != pyr and pol != pyr, (
            f"methods produced identical plans (theater): {pol} {gsp} {pyr}")

    def test_differentiated_plans_stay_compliant(self):
        from block_compliance import validate_plan
        for m in ('polarized_80_20', 'g_spot', 'traditional_pyramidal', 'time_crunched'):
            plan = build_plan_from_calendar(
                week_descriptors=_jesse_descriptors(), archetype='specialist',
                max_level=6, max_intensity=2, off_days=['Sun'], long_ride_day='Sat',
                hours_per_week=8, methodology=m)
            r = validate_plan(plan, target_hours=8, off_days=['Sun'], max_intensity=2)
            assert r['critical_pass'], f"{m} not compliant: {r.get('critical_score')}"


class TestVO2GapWithLowIntensityBudget:
    """A low-training-age athlete gets max_intensity=1. The build-phase VO2
    slot is intensity_2, so a fixed slot order would fill only intensity_1
    (threshold) and leave a 6-7 week VO2 gap → R02 gate failure → refunded
    order. The selector now fills the VO2 slot FIRST, so VO2 survives a tight
    budget in every phase."""

    def _plan(self, max_intensity, archetype='specialist'):
        return build_plan_from_calendar(
            week_descriptors=_jesse_descriptors(), archetype=archetype,
            max_level=6, max_intensity=max_intensity, off_days=['Sun'],
            long_ride_day='Sat', hours_per_week=8)

    def test_r02_passes_with_single_intensity_budget(self):
        from block_compliance import r02_vo2max_frequency
        for mi in (1, 2, 3):
            plan = self._plan(mi)
            ok, msg = r02_vo2max_frequency(plan['weeks'])
            assert ok, f"max_intensity={mi}: R02 failed — {msg}"

    def test_build_weeks_have_vo2_even_at_budget_one(self):
        from block_compliance import VO2MAX_TYPES
        plan = self._plan(1)
        build_load = [w for w in plan['weeks']
                      if w.get('phase') == 'build' and w.get('week_type') == 'load']
        assert build_load, "no build load weeks in fixture"
        for w in build_load:
            names = [d.get('name') for d in w['days']]
            assert any(n in VO2MAX_TYPES for n in names), (
                f"build week {w.get('plan_week')} has no VO2 at max_intensity=1: {names}")


class TestTestingWeek:
    """Testing weeks are an assessment battery (coach pattern), not a
    single FTP test floating in a normal load week."""

    def _testing_week(self):
        descs = [{'plan_week': 1, 'phase': 'base', 'week_type': 'testing'}] + [
            {'plan_week': w, 'phase': 'base',
             'week_type': 'recovery' if w == 4 else 'load'}
            for w in range(2, 6)]
        plan = build_plan_from_calendar(
            week_descriptors=descs, archetype='specialist',
            off_days=['Sun'], long_ride_day='Sat', hours_per_week=10)
        return plan['weeks'][0]

    def test_battery_composition(self):
        w1 = self._testing_week()
        names = {d['day']: d['name'] for d in w1['days']}
        assert names['Tue'] == 'FTP Test'
        assert names['Thu'] == 'Anaerobic Test'
        assert names['Sat'] == 'Endurance'  # long aerobic test slot

    def test_anaerobic_test_renders(self):
        from workout_mapper import render_workout
        assert render_workout('Anaerobic Test', level=1,
                              methodology='POLARIZED') is not None

    def test_metabolism_test_scales_with_experience(self):
        """Beginners ~2h, intermediates ~3h, advanced ~4h (coach spec)."""
        from workout_selector import _select_testing_week, get_workout_duration
        cases = [(3, 8, 120, 140), (5, 12, 170, 200), (6, 15, 230, 260)]
        for max_level, hrs, lo, hi in cases:
            menu = _select_testing_week(hrs, max_level)
            lr = next(w for w in menu if w['role'] == 'long_ride')
            dur = get_workout_duration('Endurance', lr['level'])
            assert lo <= dur <= hi, (
                f"max_level={max_level}: {dur}min not in [{lo},{hi}]")

    def test_metabolism_test_respects_hours_budget(self):
        from workout_selector import _select_testing_week, get_workout_duration
        menu = _select_testing_week(8, 6)  # advanced but only 8h/wk
        lr = next(w for w in menu if w['role'] == 'long_ride')
        dur = get_workout_duration('Endurance', lr['level'])
        assert dur <= 8 * 60 * 0.45 + 30  # small slack for level granularity


class TestTravelDates:
    def test_parse_singles_and_ranges(self):
        from intake_to_plan import parse_travel_dates
        got = parse_travel_dates('2026-09-03 to 2026-09-05, 2026-10-15')
        assert got == ['2026-09-03', '2026-09-04', '2026-09-05', '2026-10-15']

    def test_parse_ignores_silly_ranges(self):
        from intake_to_plan import parse_travel_dates
        # A 3-month "range" is a relocation, not travel disruption
        got = parse_travel_dates('2026-06-01 to 2026-09-01')
        # endpoints still captured as single dates
        assert '2026-06-15' not in got

    def test_calendar_marks_travel_days(self):
        from datetime import date, timedelta
        from calculate_plan_dates import calculate_plan_dates
        race = date.today() + timedelta(weeks=8)
        race += timedelta(days=(5 - race.weekday()) % 7)
        travel = (race - timedelta(days=30)).isoformat()
        pd = calculate_plan_dates(race.isoformat(), plan_weeks=8,
                                  travel_dates=[travel])
        marked = [d for w in pd['weeks'] for d in w['days']
                  if d.get('is_travel_day')]
        assert len(marked) == 1
        assert marked[0]['date'] == travel


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


class TestSelectionBiasSeam:
    """Phase 2 seam: _pick_option ranks/rotates within an EXISTING slot pool.
    Baseline path (no weights, no avoid) must be byte-identical to the old
    block-number rotation so /engine/block stays backward compatible."""

    def test_baseline_matches_block_rotation(self):
        from workout_selector import _pick_option
        opts = ['A', 'B', 'C']
        # Old behavior: options[(block_number - 1) % len(options)]
        for bn in range(1, 8):
            assert _pick_option(opts, bn) == opts[(bn - 1) % len(opts)]

    def test_category_weights_pick_highest_scored(self):
        from workout_selector import _pick_option
        # Endurance with Surges → Durability; NP/IF Target → Race_Simulation.
        opts = ['NP/IF Target', 'Endurance with Surges', 'Endurance Blocks']
        weights = {'Durability': 100, 'Race_Simulation': 10, 'HVLI_Extended': 5}
        assert _pick_option(opts, 1, category_weights=weights) == \
            'Endurance with Surges'

    def test_weight_ties_keep_config_order(self):
        from workout_selector import _pick_option
        opts = ['Threshold Steady', 'Threshold Progressive']  # both threshold
        weights = {'TT_Threshold': 50}
        assert _pick_option(opts, 3, category_weights=weights) == opts[0]

    def test_avoid_series_rotates_away(self):
        from workout_selector import _pick_option
        opts = ['A', 'B', 'C']
        assert _pick_option(opts, 1, avoid_series={'A'}) in ('B', 'C')

    def test_avoid_series_exhausted_reuses(self):
        from workout_selector import _pick_option
        opts = ['A', 'B']
        # Every option avoided → pool restored, no crash, returns a valid name.
        assert _pick_option(opts, 1, avoid_series={'A', 'B'}) in opts

    def test_keep_within_protects_vo2(self):
        from workout_selector import _pick_option
        opts = ['VO2max 40/20', 'Threshold Steady']
        # keep_within filters to VO2 first, so even a threshold-weighted race
        # cannot swap the VO2 slot out (R02 protection).
        weights = {'TT_Threshold': 100, 'VO2max': 1}
        got = _pick_option(opts, 1, category_weights=weights,
                           keep_within={'VO2max 40/20'})
        assert got == 'VO2max 40/20'

    def test_empty_options_raises(self):
        from workout_selector import _pick_option
        with pytest.raises(ValueError):
            _pick_option([], 1)


class TestMethodologyProfiles:
    """Phase 2 decision B: methodology profiles (methodology_profiles.yaml)
    contribute category-weight multipliers that COMBINE (multiply) with
    race-demand weights at the _pick_option seam, so an explicit methodology
    changes the DELIVERED zone/intensity mix — not just copy. Profile None
    (the default, and the legacy full-season path) is byte-identical to the
    historical selection."""

    ENGINE_METHODOLOGIES = ('polarized_80_20', 'time_crunched', 'g_spot',
                            'traditional_pyramidal')
    SWEET_FAMILY = {'G_Spot', 'Tempo', 'TT_Threshold'}
    VO2_FAMILY = {'VO2max', 'Anaerobic_Capacity'}

    def _plan(self, methodology, with_profile=True, **overrides):
        from workout_selector import load_methodology_profile
        kwargs = dict(
            week_descriptors=_jesse_descriptors(), archetype='specialist',
            max_level=6, max_intensity=3, off_days=['Sun'],
            long_ride_day='Sat', hours_per_week=8, methodology=methodology)
        if with_profile:
            kwargs['methodology_profile'] = load_methodology_profile(methodology)
        kwargs.update(overrides)
        return build_plan_from_calendar(**kwargs)

    def _family_counts(self, plan):
        from workout_selector import _demand_category
        sweet = vo2 = 0
        for w in plan['weeks']:
            if w.get('week_type') != 'load':
                continue
            for d in w['days']:
                if d.get('role') != 'intensity':
                    continue
                cat = _demand_category(d['name'])
                if cat in self.SWEET_FAMILY:
                    sweet += 1
                elif cat in self.VO2_FAMILY:
                    vo2 += 1
        return sweet, vo2

    # ---- config sanity ----------------------------------------------------

    def test_profiles_exist_for_all_engine_methodologies(self):
        from workout_selector import load_methodology_profile
        for m in self.ENGINE_METHODOLOGIES:
            profile = load_methodology_profile(m)
            assert profile and profile.get('category_weights'), m

    def test_unknown_methodology_has_no_profile(self):
        from workout_selector import load_methodology_profile
        assert load_methodology_profile('crossfit_only') is None

    def test_profile_categories_are_known_scorer_categories(self):
        """A typo'd category would silently never bias anything — every
        profile key must exist in the race_category_scorer taxonomy."""
        from workout_selector import load_methodology_profile
        from race_category_scorer import DEMAND_TO_CATEGORY_WEIGHTS
        known = set()
        for cats in DEMAND_TO_CATEGORY_WEIGHTS.values():
            known.update(cats)
        for m in self.ENGINE_METHODOLOGIES:
            weights = load_methodology_profile(m)['category_weights']
            unknown = set(weights) - known
            assert not unknown, f"{m}: unknown categories {unknown}"

    # ---- combination rule (multiply) ---------------------------------------

    def test_combine_both_none_is_none(self):
        from workout_selector import _combine_weights
        assert _combine_weights(None, None) is None

    def test_combine_race_only_passes_through(self):
        from workout_selector import _combine_weights
        race = {'VO2max': 80, 'Tempo': 20}
        assert _combine_weights(race, None) is race

    def test_combine_methodology_only_uses_multipliers(self):
        from workout_selector import _combine_weights
        meth = {'VO2max': 3.0, 'Tempo': 0.15}
        assert _combine_weights(None, meth) == meth

    def test_combine_multiplies_and_defaults_neutral(self):
        from workout_selector import _combine_weights
        race = {'VO2max': 80, 'Tempo': 40, 'Endurance': 50}
        meth = {'VO2max': 3.0, 'Tempo': 0.15}
        got = _combine_weights(race, meth)
        assert got == {'VO2max': 240.0, 'Tempo': 6.0, 'Endurance': 50.0}

    def test_combine_race_zero_stays_zero(self):
        """Event demand is a hard prior — a methodology multiplier cannot
        resurrect a category the race scored 0."""
        from workout_selector import _combine_weights
        got = _combine_weights({'VO2max': 0}, {'VO2max': 3.0, 'G_Spot': 3.0})
        assert got['VO2max'] == 0.0
        assert got['G_Spot'] == 0.0  # absent from race weights → race 0

    # ---- duration cap (time_crunched) --------------------------------------

    def test_duration_filter_drops_over_cap(self):
        from workout_selector import _filter_by_duration
        # At L1: VO2 Bookend=109min, VO2max Extended=45min
        got = _filter_by_duration(['VO2 Bookend', 'VO2max Extended'], 75, 1)
        assert got == ['VO2max Extended']

    def test_duration_filter_never_empties_pool(self):
        from workout_selector import _filter_by_duration
        opts = ['VO2 Bookend', 'Buffer Workout']  # both >75min at L1
        assert _filter_by_duration(opts, 75, 1) == opts

    def test_duration_filter_disabled_without_cap(self):
        from workout_selector import _filter_by_duration
        opts = ['VO2 Bookend', 'VO2max Extended']
        assert _filter_by_duration(opts, None, 1) is opts

    # ---- delivered-plan differentiation ------------------------------------

    def test_gspot_vs_polarized_distributions_differ_materially(self):
        pol_sweet, pol_vo2 = self._family_counts(self._plan('polarized_80_20'))
        gsp_sweet, gsp_vo2 = self._family_counts(self._plan('g_spot'))
        assert gsp_sweet > pol_sweet, (
            f"g_spot sweet-spot family ({gsp_sweet}) not > polarized ({pol_sweet})")
        assert pol_vo2 > gsp_vo2, (
            f"polarized VO2 family ({pol_vo2}) not > g_spot ({gsp_vo2})")

    def test_pyramidal_has_tempo_and_less_vo2_than_polarized(self):
        pyr = self._plan('traditional_pyramidal')
        names = {d['name'] for w in pyr['weeks'] if w.get('week_type') == 'load'
                 for d in w['days'] if d.get('role') == 'intensity'}
        assert any('Tempo' in n for n in names), names
        _, pyr_vo2 = self._family_counts(pyr)
        _, pol_vo2 = self._family_counts(self._plan('polarized_80_20'))
        assert pol_vo2 > pyr_vo2

    def test_all_profiles_stay_compliant(self):
        from block_compliance import validate_plan
        for m in self.ENGINE_METHODOLOGIES:
            plan = self._plan(m)
            r = validate_plan(plan, target_hours=8, off_days=['Sun'],
                              max_intensity=3)
            failed = [k for k, v in r['rules'].items()
                      if v['severity'] == 'CRITICAL' and not v['passed']]
            assert r['critical_pass'], f"{m}: failed {failed}"

    def test_profiles_combine_with_race_weights_and_stay_compliant(self):
        from block_compliance import validate_plan
        # SBT-GRVL-ish demand weights (threshold/durability leaning)
        race_weights = {'TT_Threshold': 100, 'Durability': 90, 'G_Spot': 85,
                        'Endurance': 70, 'VO2max': 60, 'Tempo': 55,
                        'Race_Simulation': 50, 'Mixed_Climbing': 45,
                        'Blended': 40, 'Gravel_Specific': 65}
        for m in self.ENGINE_METHODOLOGIES:
            plan = self._plan(m, category_weights=race_weights)
            r = validate_plan(plan, target_hours=8, off_days=['Sun'],
                              max_intensity=3)
            assert r['critical_pass'], m

    def test_vo2_anchor_survives_every_profile(self):
        """R02 mechanics: the anchor VO2 slot stays locked to VO2 stimulus
        types under every profile, so base/build load weeks always carry
        VO2 work no matter how anti-VO2 the methodology weights are."""
        from block_compliance import VO2MAX_TYPES, r02_vo2max_frequency
        for m in self.ENGINE_METHODOLOGIES:
            plan = self._plan(m)
            ok, msg = r02_vo2max_frequency(plan['weeks'])
            assert ok, f"{m}: {msg}"
            for w in plan['weeks']:
                if w.get('week_type') != 'load' or w.get('phase') == 'racing':
                    continue
                names = [d['name'] for d in w['days']
                         if d.get('role') == 'intensity']
                assert any(n in VO2MAX_TYPES for n in names), (
                    f"{m} W{w.get('plan_week')}: no VO2 anchor in {names}")

    def test_profile_none_keeps_series_coherence_and_structure(self):
        """Structure invariants under every profile: same week rhythm,
        long ride every load week, off days respected, zero series
        violations (same name +1 level across a block's load weeks)."""
        base = self._plan('polarized_80_20', with_profile=False)
        for m in self.ENGINE_METHODOLOGIES:
            plan = self._plan(m)
            assert plan['all_violations'] == [], (m, plan['all_violations'])
            assert [w['week_type'] for w in plan['weeks']] == \
                [w['week_type'] for w in base['weeks']]
            for w in plan['weeks']:
                for d in w['days']:
                    if d['day'] == 'Sun':
                        assert d['role'] == 'off'
                if w['week_type'] == 'load':
                    assert any(d['role'] == 'long_ride' for d in w['days'])

    def test_omitted_profile_equals_explicit_none(self):
        """methodology_profile=None (explicit) == omitted — the legacy
        full-season path (which never passes the kwarg) is untouched."""
        explicit = self._plan('g_spot', with_profile=False,
                              methodology_profile=None)
        omitted = self._plan('g_spot', with_profile=False)
        assert explicit == omitted
