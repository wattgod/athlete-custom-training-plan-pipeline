"""C4 integration tests (docs/SPEC_LIBRARY_SELECTION.md).

Covers:
  - the resolution pass (`generate_athlete_package.resolve_library_selections`)
    against small synthetic plan dicts (D1/D2/D9 mechanics, exception
    propagation)
  - the render branch (D3): a resolved day emits the C2-converted structure
    with the curated description preserved and fuel-tag/header prepended;
    an unresolved in-scope day still renders on the synthetic path
  - the kill switch (D10)
  - an end-to-end run of the real pipeline against the standing Sonja
    intake fixture (marked `library_e2e`; not opt-in gated -- it's part of
    this file's normal run, ~30-60s)
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import calculate_plan_dates as cpd
import library_selector
from generate_athlete_package import (_library_selection_in_scope,
                                      generate_zwo_files,
                                      resolve_library_selections)


# =============================================================================
# Fixtures shared by the resolution-pass and render sections
# =============================================================================

def _fake_resolution(item_id=990001, name_base='Curated Test Interval',
                     duration_min=20, tss=45):
    return {
        'item_id': item_id,
        'name_base': name_base,
        'library_key': 'vo2_classic',
        'duration_min': duration_min,
        'tss': tss,
        'if_planned': 82.0,
        'structure': {
            'structure': [
                {
                    'type': 'step',
                    'length': {'value': 1, 'unit': 'repetition'},
                    'steps': [{
                        'name': 'Warm Up',
                        'length': {'value': 300, 'unit': 'second'},
                        'targets': [{'minValue': 50, 'maxValue': 65}],
                        'intensityClass': 'warmUp',
                    }],
                },
                {
                    'type': 'repetition',
                    'length': {'value': 4, 'unit': 'repetition'},
                    'steps': [
                        {
                            'name': 'On',
                            'length': {'value': 180, 'unit': 'second'},
                            'targets': [{'minValue': 105}],
                            'intensityClass': 'active',
                        },
                        {
                            'name': 'Off',
                            'length': {'value': 120, 'unit': 'second'},
                            'targets': [{'minValue': 55}],
                            'intensityClass': 'rest',
                        },
                    ],
                },
            ],
        },
        'description': 'CURATED DESCRIPTION: hold cadence 95-100rpm on the on-intervals.',
        'dimension_score': 3,
    }


def _synthetic_bb_plan():
    """Minimal two-week block-builder plan dict, shaped like `_bb_plan`."""
    return {
        'weeks': [
            {
                'plan_week': 1, 'week_num': 1, 'block_number': 1, 'phase': 'base',
                'days': [
                    {'day': 'Tue', 'name': 'VO2max 40/20', 'role': 'intensity',
                     'level': 3, 'duration': 45, 'tss': 60},
                    {'day': 'Wed', 'name': 'Rest Day', 'role': 'filler',
                     'level': 1, 'duration': 0, 'tss': 0},
                    {'day': 'Sat', 'name': 'Endurance', 'role': 'long_ride',
                     'level': 3, 'duration': 180, 'tss': 120},
                    {'day': 'Sun', 'name': 'FTP Test', 'role': 'intensity',
                     'level': 1, 'duration': 60, 'tss': 70},
                ],
            },
        ],
    }


# =============================================================================
# Resolution pass unit tests (D1/D2/D9)
# =============================================================================

class TestScopePredicate:
    def test_intensity_role_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'intensity', 'name': 'VO2max 40/20'})

    def test_long_ride_role_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'long_ride', 'name': 'Endurance'})

    def test_endurance_filler_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'filler', 'name': 'Endurance'})

    # R4 fix wave: widened beyond name=='Endurance' to every canonical
    # filler whose type routes in library_selector's ROUTING_TABLE.
    def test_cadence_work_filler_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'filler', 'name': 'Cadence Work'})

    def test_endurance_blocks_filler_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'filler', 'name': 'Endurance Blocks'})

    def test_endurance_with_surges_filler_in_scope(self):
        assert _library_selection_in_scope(
            {'role': 'filler', 'name': 'Endurance with Surges'})

    # SYNTHETIC_PINNED (R4): stays out of scope even though C3 nominally
    # routes it -- a taper-specific tune-up, not a variety pool.
    def test_taper_burst_endurance_filler_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'Taper Burst Endurance'})

    def test_unrouted_filler_name_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'NP/IF Target'})

    def test_post_sim_recovery_pinned_filler_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'Endurance', 'post_sim_recovery': True})

    def test_pre_sim_recovery_pinned_filler_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'Endurance', 'pre_sim_recovery': True})

    def test_ftp_test_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'intensity', 'name': 'FTP Test'})

    def test_openers_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'intensity', 'name': 'Openers'})

    def test_rest_day_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'Rest Day'})

    def test_off_role_out_of_scope(self):
        assert not _library_selection_in_scope({'role': 'off', 'name': 'OFF'})

    def test_act_simulation_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'long_ride', 'name': 'Act Race Simulation',
             'act_simulation': {'index': 1, 'total': 3}})

    def test_strength_name_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'intensity', 'name': 'Strength'})


class TestResolveLibrarySelections:
    def test_in_scope_day_resolved_canonical_name_intact(self, monkeypatch):
        resolution = _fake_resolution()
        monkeypatch.setattr(library_selector, 'select',
                            lambda slot, series_state=None, index=None, used_items=None, lint_exclusions=None: dict(resolution))
        plan = _synthetic_bb_plan()

        fallbacks = resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        tue = plan['weeks'][0]['days'][0]
        assert tue['name'] == 'VO2max 40/20'  # D1: canonical name never overwritten
        assert tue['role'] == 'intensity'      # D1: role never overwritten
        assert tue['library_resolution']['item_id'] == resolution['item_id']
        assert tue['duration'] == resolution['duration_min']
        assert tue['tss'] == resolution['tss']

    def test_out_of_scope_days_untouched(self, monkeypatch):
        resolution = _fake_resolution()
        monkeypatch.setattr(library_selector, 'select',
                            lambda slot, series_state=None, index=None, used_items=None, lint_exclusions=None: dict(resolution))
        plan = _synthetic_bb_plan()
        resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        rest = plan['weeks'][0]['days'][1]
        ftp = plan['weeks'][0]['days'][3]
        assert 'library_resolution' not in rest
        assert rest['duration'] == 0 and rest['tss'] == 0
        assert 'library_resolution' not in ftp
        assert ftp['duration'] == 60 and ftp['tss'] == 70

    def test_week_totals_recomputed_to_sum_of_days(self, monkeypatch):
        resolution = _fake_resolution(duration_min=20, tss=45)
        monkeypatch.setattr(library_selector, 'select',
                            lambda slot, series_state=None, index=None, used_items=None, lint_exclusions=None: dict(resolution))
        plan = _synthetic_bb_plan()
        resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        week = plan['weeks'][0]
        days = week['days']
        assert week['total_duration'] == sum(d.get('duration', 0) for d in days)
        assert week['total_tss'] == sum(d.get('tss', 0) for d in days)
        # Tue (resolved to 20/45) + Wed (0/0) + Sat (unresolved -> select
        # returns the fixed resolution for every in-scope call in this
        # test, so Sat resolves too) + Sun (out of scope, untouched 60/70)
        assert week['total_duration'] == 20 + 0 + 20 + 60
        assert week['total_tss'] == 45 + 0 + 45 + 70

    def test_no_qualifying_item_produces_fallback_record(self, monkeypatch):
        monkeypatch.setattr(library_selector, 'select',
                            lambda slot, series_state=None, index=None, used_items=None, lint_exclusions=None: None)
        plan = _synthetic_bb_plan()
        fallbacks = resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        in_scope_days = {'Tue', 'Sat'}  # VO2max 40/20 (intensity), Endurance (long_ride)
        fallback_days = {fb['day'] for fb in fallbacks}
        assert fallback_days == in_scope_days
        for day in plan['weeks'][0]['days']:
            assert 'library_resolution' not in day

    def test_exceptions_propagate(self, monkeypatch):
        def _boom(slot, series_state=None, index=None, used_items=None, lint_exclusions=None):
            raise RuntimeError('selector exploded')
        monkeypatch.setattr(library_selector, 'select', _boom)
        plan = _synthetic_bb_plan()

        with pytest.raises(RuntimeError, match='selector exploded'):
            resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

    def test_excluded_calendar_slots_skip_resolution(self, monkeypatch):
        calls = []

        def _record(slot, series_state=None, index=None, used_items=None, lint_exclusions=None):
            calls.append(slot['canonical_name'])
            return _fake_resolution()
        monkeypatch.setattr(library_selector, 'select', _record)
        plan = _synthetic_bb_plan()

        resolve_library_selections(
            plan, day_caps={}, athlete_seed='t', index={},
            excluded_calendar_slots={(1, 'Tue')},
        )
        assert 'VO2max 40/20' not in calls
        assert 'Endurance' in calls  # Sat long_ride still resolved

    def test_slot_carries_week_type_plan_week_and_day(self, monkeypatch):
        """R2/R3: the selector needs week_type (intensity ceiling) and
        plan_week/day (rotation-seed extension, same-week dedup) -- verify
        the resolution pass actually plumbs them onto the slot."""
        seen_slots = []

        def _record(slot, series_state=None, index=None, used_items=None, lint_exclusions=None):
            seen_slots.append(dict(slot))
            return _fake_resolution()
        monkeypatch.setattr(library_selector, 'select', _record)
        plan = _synthetic_bb_plan()
        plan['weeks'][0]['week_type'] = 'recovery'

        resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        tue_slot = next(s for s in seen_slots if s['canonical_name'] == 'VO2max 40/20')
        assert tue_slot['week_type'] == 'recovery'
        assert tue_slot['plan_week'] == 1
        assert tue_slot['day'] == 'Tue'


# =============================================================================
# R1 (SPEC_LIBRARY_SELECTION.md regrade): authored tss/if_planned survive
# to the placed card. The internal ZWO's normalized-power recompute
# (min-only sprint targets flattened to Power blocks) massively inflates
# NP -- an authored 57.9 TSS session once placed as 103. For a
# library-resolved session, canonical_training_model must use the AUTHORED
# tss (naming_manifest.json's library_tss) instead.
# =============================================================================

class TestAuthoredTssSurvives:
    def _manifest_entry(self, library_tss=None, library_if_planned=None):
        entry = {'tp_kind': 'bike', 'display_name': 'Curated Test Interval'}
        if library_tss is not None:
            entry['library_tss'] = library_tss
            entry['library_item_id'] = 990001
            entry['library_if_planned'] = library_if_planned
        return entry

    def _minimal_zwo(self, spike_power=2.00, baseline_power=0.55):
        # Mirrors the real worst-offender item (endurance_with_work "Z2 +
        # Sprints", item 14355989: 68min, authored tss 57.9, if_planned
        # 0.715, min-only 30s@200% sprint leaves): a long easy baseline plus
        # 180s total at a min-only sprint target rendered flat. Naive
        # duration-weighted 4th-power NP inflates this to ~TSS 101 -- close
        # to the regrade's observed "57.9 authored -> 103 placed".
        return (
            "<?xml version='1.0' encoding='UTF-8'?>\n"
            "<workout_file>\n  <author>Gravel God Training</author>\n"
            "  <name>Z2 + Sprints</name>\n  <description>Test</description>\n"
            "  <sportType>bike</sportType>\n  <workout>\n"
            f"    <SteadyState Duration=\"3900\" Power=\"{baseline_power:.2f}\"/>\n"
            f"    <SteadyState Duration=\"180\" Power=\"{spike_power:.2f}\"/>\n"
            "  </workout>\n</workout_file>"
        )

    def test_library_tss_overrides_recomputed_tss(self):
        import canonical_training_model as ctm
        authored = self._manifest_entry(library_tss=57.9, library_if_planned=0.715)
        session = ctm._compiler_session(
            'W01_Tue_04-07_Z2_plus_Sprints', self._minimal_zwo(),
            date='2026-04-07', is_race_day=False,
            manifest={'W01_Tue_04-07_Z2_plus_Sprints': authored}, ftp=220,
        )
        assert session.tss == 58  # round(57.9)
        assert session.tss_planned == 57.9

    def test_recomputed_tss_would_have_diverged(self):
        """Sanity check that the fixture actually exercises R1's failure
        mode: without the override, the flat-rendered sprint block inflates
        recomputed TSS well past the authored value."""
        import canonical_training_model as ctm
        no_override = self._manifest_entry()
        session = ctm._compiler_session(
            'W01_Tue_04-07_Z2_plus_Sprints', self._minimal_zwo(),
            date='2026-04-07', is_race_day=False,
            manifest={'W01_Tue_04-07_Z2_plus_Sprints': no_override}, ftp=220,
        )
        assert session.tss > 57.9 * 1.05, (
            'fixture no longer reproduces the NP-inflation failure mode -- '
            'update it so the override test is meaningful')

    def test_no_library_tss_falls_back_to_recomputed(self):
        """A non-library-resolved session (no library_tss on the manifest
        entry) keeps the original ZWO-derived tss -- the override must be
        additive, never a behavior change for synthetic sessions."""
        import canonical_training_model as ctm
        zwo = self._minimal_zwo(spike_power=0.60, baseline_power=0.60)
        session = ctm._compiler_session(
            'W01_Tue_04-07_Endurance', zwo,
            date='2026-04-07', is_race_day=False,
            manifest={'W01_Tue_04-07_Endurance': self._manifest_entry()}, ftp=220,
        )
        from zwo_parser import parse_zwo_text
        expected = parse_zwo_text(zwo, 220, source_name='x')
        assert session.tss == int(expected['tss'])


# =============================================================================
# R5 (SPEC_LIBRARY_SELECTION.md regrade): hard-day detection from resolved
# intensity, in addition to role. A resolved long_ride day (role
# 'long_ride', never 'intensity') can carry authored IF 0.95 and needs the
# same SEQUENCING/adjacency treatment as an intensity day.
# =============================================================================

class TestHardDayDetection:
    def _hard_structure(self, seconds=300, value=125):
        return {'structure': [{
            'type': 'step', 'length': {'value': 1, 'unit': 'repetition'},
            'steps': [{'name': 'Push', 'length': {'value': seconds, 'unit': 'second'},
                      'targets': [{'minValue': value}], 'intensityClass': 'active'}],
        }]}

    def test_high_if_planned_counts_as_hard(self):
        from generate_athlete_package import _resolution_is_hard
        assert _resolution_is_hard({'if_planned': 0.95, 'structure': {'structure': []}})

    def test_moderate_if_planned_with_no_hard_target_is_not_hard(self):
        from generate_athlete_package import _resolution_is_hard
        assert not _resolution_is_hard({'if_planned': 0.70, 'structure': {'structure': []}})

    def test_long_hard_structure_target_counts_as_hard_even_at_moderate_if(self):
        from generate_athlete_package import _resolution_is_hard
        resolution = {'if_planned': 0.70, 'structure': self._hard_structure(seconds=300, value=125)}
        assert _resolution_is_hard(resolution)

    def test_short_sprint_target_does_not_count_as_hard(self):
        """R1's exact case: a 30s @200% sprint leaf is a different training
        stimulus than a sustained >=60s push -- must not trip the hard-day
        classifier on its own (that's what if_planned >= 0.85 is for)."""
        from generate_athlete_package import _resolution_is_hard
        resolution = {'if_planned': 0.60, 'structure': self._hard_structure(seconds=30, value=200)}
        assert not _resolution_is_hard(resolution)

    def test_hard_bike_dates_includes_library_is_hard_resolved(self):
        from generate_athlete_package import _compute_hard_bike_dates
        records = [
            {'tp_kind': 'bike', 'date': '2026-04-04', 'role': 'long_ride',
             'library_is_hard_resolved': True},
            {'tp_kind': 'bike', 'date': '2026-04-05', 'role': 'filler',
             'library_is_hard_resolved': False},
            {'tp_kind': 'strength', 'date': '2026-04-04', 'role': None},
        ]
        assert _compute_hard_bike_dates(records) == {'2026-04-04'}

    def test_hard_bike_dates_still_honors_role_and_is_sim(self):
        from generate_athlete_package import _compute_hard_bike_dates
        records = [
            {'tp_kind': 'bike', 'date': '2026-04-01', 'role': 'intensity'},
            {'tp_kind': 'bike', 'date': '2026-04-02', 'role': 'long_ride', 'is_sim': True},
            {'tp_kind': 'bike', 'date': '2026-04-03', 'role': 'filler'},
        ]
        assert _compute_hard_bike_dates(records) == {'2026-04-01', '2026-04-02'}


# =============================================================================
# R6 (SPEC_LIBRARY_SELECTION.md regrade): readable display names.
# name_base fragments ("with Surges", "Extended", "Blocks") shipped
# verbatim as card titles; name_base itself must never change (family
# grouping depends on it).
# =============================================================================

class TestLibraryDisplayName:
    def test_with_surges_fragment_composes_abbreviated(self):
        from generate_athlete_package import _library_display_name
        resolution = {'name_base': 'with Surges', 'library_key': 'endurance_with_work'}
        assert _library_display_name(resolution) == 'Endurance w/ Surges'
        assert resolution['name_base'] == 'with Surges'  # never mutated

    def test_extended_fragment_composes_with_category(self):
        from generate_athlete_package import _library_display_name
        resolution = {'name_base': 'Extended', 'library_key': 'vo2_classic'}
        assert _library_display_name(resolution) == 'VO2max Extended'

    def test_blocks_fragment_composes_with_category(self):
        from generate_athlete_package import _library_display_name
        resolution = {'name_base': 'Blocks', 'library_key': 'endurance_with_work'}
        assert _library_display_name(resolution) == 'Endurance Blocks'

    def test_standalone_multiword_name_base_ships_unchanged(self):
        from generate_athlete_package import _library_display_name
        resolution = {'name_base': 'Curated Test Interval', 'library_key': 'vo2_classic'}
        assert _library_display_name(resolution) == 'Curated Test Interval'

    def test_standalone_long_single_word_ships_unchanged(self):
        from generate_athlete_package import _library_display_name
        resolution = {'name_base': 'Microbursts', 'library_key': 'sprint_attacks'}
        assert _library_display_name(resolution) == 'Microbursts'


# =============================================================================
# Render tests (D3): resolved day emits converted structure with curated
# description preserved; unresolved in-scope day renders synthetic as before.
# =============================================================================

def _base_profile(athlete_id, race_name, race_date):
    return {
        'name': 'Render Test Athlete',
        'athlete_id': athlete_id,
        'target_race': {'name': race_name, 'date': race_date,
                        'distance_miles': 60, 'discipline': 'gravel'},
        'fitness_markers': {'ftp_watts': 220, 'weight_kg': 70},
        'weekly_availability': {'cycling_hours_target': 8},
        'schedule_constraints': {'preferred_long_day': 'saturday',
                                 'preferred_off_days': ['monday']},
        'preferred_days': {
            'monday': {'availability': 'rest'},
            'tuesday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 90},
            'wednesday': {'availability': 'available', 'is_key_day_ok': False, 'max_duration_min': 75},
            'thursday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 90},
            'friday': {'availability': 'available', 'is_key_day_ok': False, 'max_duration_min': 75},
            'saturday': {'availability': 'available', 'is_key_day_ok': True,
                        'is_long_day': True, 'max_duration_min': 240},
            'sunday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 150},
        },
    }


class _FrozenDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1)


def _build_small_plan(tmp_path, athlete_id, extra_env=None, force_select=None):
    mp = pytest.MonkeyPatch()
    mp.setattr(cpd, 'datetime', _FrozenDatetime)
    if force_select is not None:
        mp.setattr(library_selector, 'select', force_select)
    for key, value in (extra_env or {}).items():
        mp.setenv(key, value)
    try:
        plan_dates = cpd.calculate_plan_dates('2026-03-21', plan_weeks=4)
        profile = _base_profile(athlete_id, 'Render Test Gravel Race', '2026-03-21')
        derived = {'plan_weeks': 4, 'ability_level': 'Intermediate'}
        methodology = {'methodology_id': 'polarized_80_20',
                       'configuration': {'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}}}
        athlete_dir = tmp_path / athlete_id
        (athlete_dir / 'workouts').mkdir(parents=True)
        files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    finally:
        mp.undo()
    return athlete_dir, files


def _zwo_name(path):
    m = re.search(r'<name>(.*?)</name>', path.read_text())
    return m.group(1) if m else ''


def _zwo_description(path):
    m = re.search(r'<description>(.*?)</description>', path.read_text(), re.S)
    return m.group(1) if m else ''


def _force_select_intensity_and_filler_only(slot, series_state=None, index=None, used_items=None,
                                            lint_exclusions=None):
    """Resolve intensity/filler slots to a fixed curated item; leave
    long_ride slots unresolved so the synthetic-fallback branch (D9) is
    also exercised in the same render pass."""
    if slot['role'] == 'long_ride':
        return None
    return _fake_resolution()


class TestRenderBranch:
    def test_resolved_day_renders_converted_structure_curated_description(self, tmp_path):
        athlete_dir, files = _build_small_plan(
            tmp_path, 'render-resolved',
            force_select=_force_select_intensity_and_filler_only,
        )
        assert files, 'generate_zwo_files produced no workouts'

        curated = [f for f in files if 'CURATED DESCRIPTION' in _zwo_description(f)]
        assert curated, 'no ZWO carried the curated description -- resolution branch not exercised'

        for f in curated:
            desc = _zwo_description(f)
            name = _zwo_name(f)
            # D3: curated description preserved verbatim (not regenerated
            # by rewrite_zwo_description's MAIN SET rewrite).
            assert 'CURATED DESCRIPTION: hold cadence 95-100rpm' in desc
            # Fuel-tag/personal-header prepends still apply (D3).
            assert 'Phase:' in desc
            assert 'Week 1/4' in desc or re.search(r'Week \d/4', desc)
            # D3: curated name_base is the display name (bare or with a
            # "(n of N)" series suffix patched on afterward).
            assert re.match(r'^Curated Test Interval( \(\d+ of \d+\))?$', name), name

    def test_unresolved_in_scope_day_renders_synthetic_as_before(self, tmp_path):
        athlete_dir, files = _build_small_plan(
            tmp_path, 'render-fallback',
            force_select=_force_select_intensity_and_filler_only,
        )
        long_ride_files = [f for f in files if 'CURATED DESCRIPTION' not in _zwo_description(f)
                           and _zwo_description(f)]
        assert long_ride_files, 'expected at least one synthetic-rendered file'
        # None of the synthetic files leaked the curated description or
        # the fake item's name.
        assert not any('Curated Test Interval' == _zwo_name(f).split(' (')[0]
                       for f in long_ride_files if 'CURATED DESCRIPTION' not in _zwo_description(f))

        fallback_path = athlete_dir / 'library_fallbacks.json'
        assert fallback_path.exists(), 'D9: fallback list not written'
        fallbacks = json.loads(fallback_path.read_text())
        assert any(fb['role'] == 'long_ride' for fb in fallbacks), \
            'expected the long_ride slot(s) to be recorded as fallbacks'


# =============================================================================
# Kill switch (D10)
# =============================================================================

class TestKillSwitch:
    def test_gg_library_selection_0_yields_zero_resolutions(self, tmp_path):
        athlete_dir, files = _build_small_plan(
            tmp_path, 'kill-switch',
            extra_env={'GG_LIBRARY_SELECTION': '0'},
            force_select=lambda slot, series_state=None, index=None, used_items=None,
                                lint_exclusions=None: _fake_resolution(),
        )
        assert files, 'generate_zwo_files produced no workouts'
        curated = [f for f in files if 'CURATED DESCRIPTION' in _zwo_description(f)]
        assert curated == [], (
            'GG_LIBRARY_SELECTION=0 should disable the resolution pass entirely, '
            f'but curated content leaked into: {[f.name for f in curated]}'
        )
        assert not (athlete_dir / 'library_fallbacks.json').exists(), (
            'kill switch should skip the resolution pass entirely -- no '
            'fallback file should be written'
        )


# =============================================================================
# End-to-end: real pipeline against the standing Sonja intake fixture.
# =============================================================================

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
ATHLETES_DIR = SCRIPTS_DIR.parent
SONJA_INTAKE = Path(
    '/private/tmp/claude-501/-Users-mattirowe/'
    '5d27b4e6-9fd9-4dcf-bc65-82aa1a0c7158/scratchpad/sonja-intake.md'
)


@pytest.mark.library_e2e
@pytest.mark.skipif(not SONJA_INTAKE.exists(), reason='standing Sonja intake fixture not present')
def test_sonja_end_to_end_library_selection():
    # Clean slate: fulfillment residue anchors the pre-plan start to the
    # ORDER date, so regenerating over an old dir shifts week composition
    # (a boundary composition once flagged R03 and looked like a library
    # regression). Production dirs are always fresh; the E2E must be too.
    import shutil, time
    stale = ATHLETES_DIR / 'sonja-field'
    if stale.exists():
        shutil.move(str(stale), str(ATHLETES_DIR / f'sonja-field-e2e-prev-{int(time.time())}'))
    result = subprocess.run(
        [sys.executable, 'intake_to_plan.py', '--file', str(SONJA_INTAKE)],
        cwd=str(SCRIPTS_DIR), capture_output=True, text=True, timeout=300,
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT)},
    )
    print(result.stdout[-4000:])
    print(result.stderr[-4000:])
    assert result.returncode == 0, (
        f"pipeline exited {result.returncode}\nstdout tail:\n{result.stdout[-2000:]}\n"
        f"stderr tail:\n{result.stderr[-2000:]}"
    )

    athlete_dir = ATHLETES_DIR / 'sonja-field'
    assert athlete_dir.exists(), f"expected athlete dir {athlete_dir} to exist"

    plan_ir_path = athlete_dir / 'plan_ir.json'
    assert plan_ir_path.exists(), 'plan_ir.json missing'

    needs_review = athlete_dir / 'NEEDS_REVIEW.txt'
    assert not needs_review.exists(), (
        f"NEEDS_REVIEW.txt present:\n{needs_review.read_text() if needs_review.exists() else ''}"
    )

    manifest_path = athlete_dir / 'workouts' / 'naming_manifest.json'
    assert manifest_path.exists(), 'naming_manifest.json missing'
    manifest = json.loads(manifest_path.read_text())
    in_scope = [rec for rec in manifest.values()
               if _library_selection_in_scope(
                   {'role': rec.get('role'), 'name': rec.get('archetype_id'),
                    'act_simulation': rec.get('is_sim')})]
    resolved = [rec for rec in in_scope if rec.get('library_item_id') is not None]
    share = (len(resolved) / len(in_scope)) if in_scope else 0.0
    print(f"library-share: {len(resolved)}/{len(in_scope)} = {share:.1%}")
    assert in_scope, 'no in-scope quality/endurance sessions found in naming_manifest.json'
    assert share >= 0.60, f"library-resolved share {share:.1%} is below the 60% floor"

    fallback_path = athlete_dir / 'library_fallbacks.json'
    assert fallback_path.exists(), 'library_fallbacks.json missing'
    fallback_contents = fallback_path.read_text()
    print(f"library_fallbacks.json contents:\n{fallback_contents}")

    coaching_brief = athlete_dir / 'coaching_brief.md'
    if coaching_brief.exists():
        brief_text = coaching_brief.read_text()
        has_fallbacks = json.loads(fallback_contents or '[]')
        if has_fallbacks:
            assert 'LIBRARY FALLBACKS' in brief_text, (
                'R4: library_fallbacks.json has entries but coaching_brief.md '
                'never renders the LIBRARY FALLBACKS section')

    # R1: authored tss survives to the placed card -- resolved sessions'
    # emitted tss must be within 5% of the item's authored tss.
    tss_deltas = []
    for rec in resolved:
        library_tss = rec.get('library_tss')
        if not library_tss:
            continue
        # tss_planned isn't on the manifest itself (that's computed
        # downstream in canonical_training_model); the manifest's own
        # library_tss IS the authored value carried through, so the
        # meaningful regression check is that it made it onto the record
        # at all and canonical_training_model.tss == round(library_tss).
        tss_deltas.append((rec.get('filename_stem'), library_tss))
    print(f"resolved-session authored tss (first 10): {tss_deltas[:10]}")

    plan_ir = json.loads(plan_ir_path.read_text())
    plan_ir_by_stem = {
        s.get('filename_stem'): s
        for week in plan_ir.get('weeks', []) for s in week.get('sessions', [])
        if s.get('filename_stem')
    }
    bad_deltas = []
    for stem, library_tss in tss_deltas:
        session = plan_ir_by_stem.get(stem)
        if not session:
            continue
        placed = session.get('tss_planned')
        if placed is None:
            continue
        delta = abs(placed - library_tss) / library_tss if library_tss else 0
        if delta > 0.05:
            bad_deltas.append((stem, library_tss, placed, delta))
    print(f"placed-vs-authored tss deltas > 5%: {bad_deltas}")
    assert not bad_deltas, f"placed tss diverged >5% from authored for: {bad_deltas}"

    # R3: variety enforcement -- no same-week duplicate item, no non-series
    # item repeated more than twice plan-wide.
    from collections import Counter, defaultdict
    week_item_pairs = defaultdict(list)
    item_counts = Counter()
    for rec in resolved:
        item_id = rec['library_item_id']
        week_num = rec.get('week_num')
        week_item_pairs[(week_num, item_id)].append(rec.get('filename_stem'))
        item_counts[item_id] += 1
    same_week_dupes = {k: v for k, v in week_item_pairs.items() if len(v) > 1}
    print(f"same-week duplicate items: {same_week_dupes}")
    assert not same_week_dupes, f"R3(b): same-week duplicate item(s): {same_week_dupes}"

    over_used = {item_id: count for item_id, count in item_counts.items() if count > 2}
    print(f"distinct items used: {len(item_counts)}; item use counts: {dict(item_counts)}")
    assert not over_used, f"R3(a): item(s) repeated more than twice plan-wide: {over_used}"

    display_names = sorted({rec.get('display_name') for rec in resolved})
    print(f"display names for resolved sessions: {display_names}")

    from post_render_validator import build_validator_input, validate_transitional_input
    document = build_validator_input(athlete_dir)
    issues, confirmations = validate_transitional_input(document)
    print(f"post_render_validator issues: {issues}")
    assert issues == [], f"post_render_validator found {len(issues)} issue(s): {issues}"
