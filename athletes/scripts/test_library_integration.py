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

    def test_non_endurance_filler_out_of_scope(self):
        assert not _library_selection_in_scope(
            {'role': 'filler', 'name': 'Cadence Work'})

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
                            lambda slot, series_state=None, index=None: dict(resolution))
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
                            lambda slot, series_state=None, index=None: dict(resolution))
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
                            lambda slot, series_state=None, index=None: dict(resolution))
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
                            lambda slot, series_state=None, index=None: None)
        plan = _synthetic_bb_plan()
        fallbacks = resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

        in_scope_days = {'Tue', 'Sat'}  # VO2max 40/20 (intensity), Endurance (long_ride)
        fallback_days = {fb['day'] for fb in fallbacks}
        assert fallback_days == in_scope_days
        for day in plan['weeks'][0]['days']:
            assert 'library_resolution' not in day

    def test_exceptions_propagate(self, monkeypatch):
        def _boom(slot, series_state=None, index=None):
            raise RuntimeError('selector exploded')
        monkeypatch.setattr(library_selector, 'select', _boom)
        plan = _synthetic_bb_plan()

        with pytest.raises(RuntimeError, match='selector exploded'):
            resolve_library_selections(plan, day_caps={}, athlete_seed='t', index={})

    def test_excluded_calendar_slots_skip_resolution(self, monkeypatch):
        calls = []

        def _record(slot, series_state=None, index=None):
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


def _force_select_intensity_and_filler_only(slot, series_state=None, index=None):
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
            force_select=lambda slot, series_state=None, index=None: _fake_resolution(),
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

    from post_render_validator import build_validator_input, validate_transitional_input
    document = build_validator_input(athlete_dir)
    issues, confirmations = validate_transitional_input(document)
    print(f"post_render_validator issues: {issues}")
    assert issues == [], f"post_render_validator found {len(issues)} issue(s): {issues}"
