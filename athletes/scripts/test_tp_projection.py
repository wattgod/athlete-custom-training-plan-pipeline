"""D1/D3/D5 TP-native projection regression tests (WS-B).

Covers: PlanIR.Session extensions, session-kind semantics (rest -> day_off,
strength -> id 9 + template, race -> id 2 no structure, two-a-day
order_on_day), the ZWO-segment -> TP `structure` conversion, and
tp_manifest.json emission + schema.

Reuses the proven integration-fixture recipe from test_naming_and_rounding.py
(frozen 8-week plan covering block-builder series/A-race/B-race/travel/
legacy-FTP-test/strength; a separate real-clock fixture for W00) rather than
importing its module-scoped fixtures directly -- generate_zwo_files exposes
its W00 week entry via a *function attribute*
(generate_zwo_files.last_pre_plan_week), which is last-call-wins/stateful
across the whole test process, so each fixture here captures it immediately
after its own generate_zwo_files() call instead of relying on another test
module's fixture having already done so.
"""
import datetime
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

import calculate_plan_dates as cpd
from generate_athlete_package import generate_zwo_files
from plan_ir import build_plan_ir, build_tp_manifest
import plan_ir as plan_ir_module
from test_naming_and_rounding import _base_profile


def _finish_package(athlete_dir, athlete_id, plan_dates, profile, monkeypatch):
    """Write the sidecar artifacts build_plan_ir/build_tp_manifest read, run
    both, and return (plan_ir_object, manifest_dict)."""
    monkeypatch.setattr(plan_ir_module, 'ATHLETES_DIR', athlete_dir.parent)
    (athlete_dir / 'profile.yaml').write_text(yaml.safe_dump(profile))
    (athlete_dir / 'plan_dates.yaml').write_text(yaml.safe_dump(plan_dates))
    (athlete_dir / 'fueling.yaml').write_text(yaml.safe_dump({}))
    (athlete_dir / 'weekly_structure.yaml').write_text(yaml.safe_dump({}))

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        ir = build_plan_ir(athlete_id)
        manifest = build_tp_manifest(athlete_id)
    return ir, manifest


def _build_structure_plan(tmp_path, monkeypatch):
    """Frozen 8-week plan: main block path, A-race, B-race, travel, legacy
    FTP-test day, and strength -- no W00 (real clock is far from the frozen
    calendar's plan_start). See test_naming_and_rounding._build_full_plan."""

    class _FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1)

    mp = pytest.MonkeyPatch()
    mp.setattr(cpd, 'datetime', _FrozenDatetime)
    try:
        b_events = [{'name': 'Sanity Tune-Up', 'date': '2026-03-07'}]
        plan_dates = cpd.calculate_plan_dates(
            '2026-03-21', plan_weeks=8, b_events=b_events,
            travel_dates=['2026-02-03'],
        )
    finally:
        mp.undo()

    profile = _base_profile(
        'tp-structure-athlete', 'Sanity Gravel Race', '2026-03-21',
        extra={'b_events': [{'name': 'Sanity Tune-Up', 'date': '2026-03-07', 'priority': 'B'}]},
    )
    derived = {'plan_weeks': 8, 'ability_level': 'Intermediate'}
    methodology = {'methodology_id': 'polarized_80_20',
                    'configuration': {'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}}}

    athlete_dir = tmp_path / 'tp-structure-athlete'
    (athlete_dir / 'workouts').mkdir(parents=True)
    files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    assert files, "generate_zwo_files produced no workouts"

    ir, manifest = _finish_package(athlete_dir, 'tp-structure-athlete', plan_dates, profile, monkeypatch)
    return athlete_dir, ir, manifest, files


def _build_w00_projection_plan(tmp_path, monkeypatch):
    """Real (unfrozen) calendar with plan_start forced 1-7 days out, exactly
    like test_naming_and_rounding._build_w00_plan, but also merges the
    captured W00 week entry into plan_dates and runs PlanIR/tp_manifest."""
    today = datetime.datetime.now().date()
    race_date = (today + datetime.timedelta(days=40)).isoformat()
    plan_dates = cpd.calculate_plan_dates(race_date, plan_weeks=10)
    days_out = (datetime.date.fromisoformat(plan_dates['plan_start']) - today).days
    assert 1 <= days_out <= 7, (
        "test setup drifted -- plan_start no longer lands in the W00 window "
        f"(days_out={days_out}); adjust the race_date/plan_weeks offsets above"
    )

    profile = _base_profile('tp-w00-athlete', 'W00 Projection Race', race_date)
    derived = {'plan_weeks': plan_dates.get('plan_weeks', 6), 'ability_level': 'Intermediate'}
    methodology = {'methodology_id': 'polarized_80_20',
                    'configuration': {'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}}}

    athlete_dir = tmp_path / 'tp-w00-athlete'
    (athlete_dir / 'workouts').mkdir(parents=True)
    files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    w00_files = [f for f in files if f.name.startswith('W00_')]
    assert w00_files, "test setup did not trigger the W00 pre-plan branch"

    pre_plan_week = getattr(generate_zwo_files, 'last_pre_plan_week', None)
    assert pre_plan_week, "test setup did not capture a W00 week entry"
    plan_dates.setdefault('weeks', []).insert(0, pre_plan_week)

    ir, manifest = _finish_package(athlete_dir, 'tp-w00-athlete', plan_dates, profile, monkeypatch)
    return athlete_dir, ir, manifest, files, w00_files


@pytest.fixture(scope='module')
def structure_plan(tmp_path_factory, monkeypatch_module):
    return _build_structure_plan(tmp_path_factory.mktemp('tp-structure'), monkeypatch_module)


@pytest.fixture(scope='module')
def w00_projection_plan(tmp_path_factory, monkeypatch_module):
    return _build_w00_projection_plan(tmp_path_factory.mktemp('tp-w00-projection'), monkeypatch_module)


@pytest.fixture(scope='module')
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


# ===========================================================================
# Manifest schema: exists + validates (no new deps -- plain structural check)
# ===========================================================================

_REQUIRED_TOP_KEYS = {'version', 'plan_title', 'athlete', 'race', 'expected', 'sessions'}
_REQUIRED_EXPECTED_KEYS = {'bike', 'strength', 'day_off', 'race', 'total'}
_VALID_TP_KINDS = {'bike', 'strength', 'race', 'day_off'}
_VALID_WORKOUT_TYPE_IDS = {2, 7, 9}


def _validate_tp_manifest_schema(manifest):
    assert isinstance(manifest, dict)
    missing_top = _REQUIRED_TOP_KEYS - manifest.keys()
    assert not missing_top, f"tp_manifest missing top-level keys: {missing_top}"
    assert manifest['version'] == 1
    assert isinstance(manifest['plan_title'], str) and manifest['plan_title']
    assert '[CUSTOM]' in manifest['plan_title']

    expected = manifest['expected']
    missing_expected = _REQUIRED_EXPECTED_KEYS - expected.keys()
    assert not missing_expected, f"tp_manifest.expected missing keys: {missing_expected}"
    for key in _REQUIRED_EXPECTED_KEYS:
        assert isinstance(expected[key], int), f"expected.{key} must be an int"
    assert expected['total'] == sum(expected[k] for k in ('bike', 'strength', 'day_off', 'race'))

    sessions = manifest['sessions']
    assert isinstance(sessions, list) and sessions, "tp_manifest.sessions must be a non-empty list"
    for s in sessions:
        assert s['tp_kind'] in _VALID_TP_KINDS, f"invalid tp_kind: {s['tp_kind']!r}"
        assert s['workout_type_value_id'] in _VALID_WORKOUT_TYPE_IDS, (
            f"invalid workout_type_value_id: {s['workout_type_value_id']!r}"
        )
        assert s['display_name'], f"session missing display_name: {s}"
        # filename_stem may be None only for a PlanIR-synthesized day_off
        # session (a calendar day with no rendered ZWO at all -- e.g. a
        # true off day the block-builder skips). Every bike/strength/race
        # session always comes from a real emitted ZWO in this pipeline.
        if s['tp_kind'] != 'day_off':
            assert s['filename_stem'], f"non-day_off session missing filename_stem: {s}"
    return sessions


def test_tp_manifest_exists_and_validates(structure_plan):
    _, _, manifest, _ = structure_plan
    assert manifest, "build_tp_manifest returned an empty dict"
    _validate_tp_manifest_schema(manifest)


def test_tp_manifest_written_to_disk(structure_plan):
    athlete_dir, _, _, _ = structure_plan
    manifest_path = athlete_dir / 'tp_manifest.json'
    assert manifest_path.exists(), "tp_manifest.json was not written to the athlete dir"
    import json
    on_disk = json.loads(manifest_path.read_text())
    _validate_tp_manifest_schema(on_disk)


# ===========================================================================
# Expected counts must equal the actual session-list tallies (never a
# hardcoded number -- spec sol F17).
# ===========================================================================

def test_expected_counts_equal_session_tallies(structure_plan):
    _, _, manifest, _ = structure_plan
    sessions = manifest['sessions']
    tallies = {'bike': 0, 'strength': 0, 'day_off': 0, 'race': 0}
    for s in sessions:
        tallies[s['tp_kind']] += 1
    for kind in ('bike', 'strength', 'day_off', 'race'):
        assert manifest['expected'][kind] == tallies[kind], (
            f"expected.{kind} ({manifest['expected'][kind]}) != actual tally ({tallies[kind]})"
        )
    assert manifest['expected']['total'] == len(sessions)


# ===========================================================================
# Every bike session has a structure with unrolled steps and int percent
# targets; strength/race/day_off never carry a structure.
# ===========================================================================

def test_bike_sessions_have_unrolled_structure_with_int_percent_targets(structure_plan):
    _, _, manifest, _ = structure_plan
    bike_sessions = [s for s in manifest['sessions'] if s['tp_kind'] == 'bike']
    assert bike_sessions, "no bike sessions found -- test setup lost coverage"

    saw_a_structure = False
    for s in bike_sessions:
        structure = s['structure']
        if structure is None:
            continue  # FreeRide-only sessions with no parsed segments are rare but legal
        saw_a_structure = True
        assert structure['primaryLengthMetric'] == 'duration'
        assert structure['primaryIntensityMetric'] == 'percentOfFtp'
        steps = structure['structure']
        assert steps, f"bike session {s['filename_stem']} has an empty structure"
        for block in steps:
            assert block['length'] == {'value': 1, 'unit': 'repetition'}, (
                "intervals must be unrolled -- each on/off step is its own "
                "repetition-1 block, never a repeated block"
            )
            step = block['steps'][0]
            for target in step['targets']:
                for key in ('minValue', 'maxValue'):
                    if key in target:
                        assert isinstance(target[key], int), (
                            f"non-integer percent target in {s['filename_stem']}: {target}"
                        )
    assert saw_a_structure, "no bike session produced a structure -- conversion not exercised"


def test_bike_structures_carry_a_populated_polyline(structure_plan):
    """The TP calendar tile draws its mini power-profile from structure.polyline
    (NOT the steps). An empty polyline => a blank tile -- a trust-killer that
    shipped once (all bike workouts rendered blank). Every structured bike
    workout must carry a non-empty polyline that opens at [0,0] and closes at
    [1,0]."""
    _, _, manifest, _ = structure_plan
    checked = 0
    for s in manifest['sessions']:
        if s['tp_kind'] != 'bike' or not s.get('structure'):
            continue
        poly = s['structure'].get('polyline')
        stem = s['filename_stem']
        assert poly, f"bike session {stem} has an EMPTY polyline -- blank calendar tile"
        assert len(poly) >= 3, f"{stem} polyline too short to be a real profile: {poly}"
        assert list(poly[0]) == [0, 0], f"{stem} polyline must open at [0,0], got {poly[0]}"
        assert list(poly[-1]) == [1, 0], f"{stem} polyline must close at [1,0], got {poly[-1]}"
        checked += 1
    assert checked, "no bike session with a structure -- polyline path not exercised"


def test_strength_race_day_off_never_carry_structure(structure_plan):
    _, _, manifest, _ = structure_plan
    for s in manifest['sessions']:
        if s['tp_kind'] in ('strength', 'race', 'day_off'):
            assert s['structure'] is None, (
                f"{s['tp_kind']} session {s['filename_stem']} unexpectedly has a structure"
            )


# ===========================================================================
# Strength sessions: valid template keys + A/B alternation by emitted
# ordinal, order_on_day == 0, workoutTypeValueId == 9 (never 2).
# ===========================================================================

_VALID_STRENGTH_TEMPLATES = {
    'foundation_a', 'foundation_b', 'max_strength_a', 'max_strength_b',
    'power_a', 'power_b', 'maintenance_a',
}


def test_strength_sessions_have_valid_template_and_never_type_2(structure_plan):
    _, _, manifest, _ = structure_plan
    strength_sessions = [s for s in manifest['sessions'] if s['tp_kind'] == 'strength']
    assert strength_sessions, "no strength sessions found -- test setup lost coverage"
    for s in strength_sessions:
        assert s['workout_type_value_id'] == 9
        assert s['order_on_day'] == 0, "strength must always be order_on_day 0"
        assert s['strength_template'] in _VALID_STRENGTH_TEMPLATES, (
            f"invalid/missing strength_template: {s['strength_template']!r}"
        )


def test_strength_ab_alternates_by_week(structure_plan):
    _, ir, manifest, _ = structure_plan
    by_week = {}
    for week in ir.weeks:
        for session in week.sessions:
            if session.tp_kind == 'strength':
                by_week.setdefault(week.number, []).append(session)

    saw_a_pair = False
    for week_num, sessions in by_week.items():
        if len(sessions) < 2:
            continue
        saw_a_pair = True
        sessions.sort(key=lambda s: s.date or '')
        templates = [s.strength_template for s in sessions]
        # Same family, alternating letters (A then B) by chronological/
        # emitted ordinal -- never both A or both B.
        assert templates[0].endswith('_a'), f"week {week_num}: first strength session not A: {templates}"
        assert templates[1].endswith('_b'), f"week {week_num}: second strength session not B: {templates}"
        assert templates[0][:-2] == templates[1][:-2], f"week {week_num}: A/B family mismatch: {templates}"
    assert saw_a_pair, "no week with 2 strength sessions found -- A/B alternation not exercised"


# ===========================================================================
# W00: sessions carry real dates and PlanIR matches every W00 ZWO via the
# primary calendar-day path (D1 fix; WS-A's allow_unmatched_date_prefixes
# exemption is removed in test_naming_and_rounding.py).
# ===========================================================================

def test_w00_sessions_carry_dates_and_are_projected(w00_projection_plan):
    _, ir, manifest, _, w00_files = w00_projection_plan
    w00_stems = {f.stem for f in w00_files}
    w00_sessions = [s for s in manifest['sessions'] if s['filename_stem'] in w00_stems]
    assert len(w00_sessions) == len(w00_stems), (
        f"expected {len(w00_stems)} W00 sessions in the manifest, got {len(w00_sessions)}"
    )
    for s in w00_sessions:
        assert s['date'], f"W00 session {s['filename_stem']} has no date"


def test_w00_sessions_matched_by_primary_calendar_path(w00_projection_plan):
    _, ir, manifest, _, w00_files = w00_projection_plan
    w00_stems = {f.stem for f in w00_files}
    matched_with_date = set()
    for week in ir.weeks:
        for session in week.sessions:
            if session.filename_stem in w00_stems and session.date is not None:
                matched_with_date.add(session.filename_stem)
    assert matched_with_date == w00_stems, (
        f"W00 ZWOs not matched via the primary calendar-day path: "
        f"{w00_stems - matched_with_date}"
    )


# ===========================================================================
# Rest days -> day_off / id 7; A-race -> kind race.
# ===========================================================================

def test_rest_days_are_day_off_type_7(structure_plan):
    _, _, manifest, _ = structure_plan
    rest_sessions = [s for s in manifest['sessions'] if s['title'] == 'Rest Day' or s['display_name'] == 'Rest Day']
    assert rest_sessions, "no rest-day sessions found -- test setup lost coverage"
    for s in rest_sessions:
        assert s['tp_kind'] == 'day_off'
        assert s['workout_type_value_id'] == 7


def test_a_race_day_is_kind_race(structure_plan):
    _, _, manifest, _ = structure_plan
    race_sessions = [s for s in manifest['sessions'] if s['tp_kind'] == 'race']
    assert race_sessions, "no A-race session found -- test setup lost coverage"
    for s in race_sessions:
        assert s['race'] == {'priority': 'A'}
        assert s['structure'] is None


# ===========================================================================
# Every session has display_name + filename_stem.
# ===========================================================================

def test_no_session_lacks_display_name_or_filename_stem(structure_plan, w00_projection_plan):
    for s in structure_plan[2]['sessions']:
        assert s['display_name'], f"session missing display_name: {s}"
        if s['tp_kind'] != 'day_off':
            assert s['filename_stem'], f"non-day_off session missing filename_stem: {s}"


# ===========================================================================
# Two-a-day ordering: strength always order_on_day 0; the same-day bike
# session (if any) sorts after it.
# ===========================================================================

def test_two_a_day_ordering_strength_first(structure_plan):
    _, _, manifest, _ = structure_plan
    by_date = {}
    for s in manifest['sessions']:
        by_date.setdefault(s['date'], []).append(s)

    saw_two_a_day = False
    for date, sessions in by_date.items():
        if len(sessions) < 2:
            continue
        kinds = {s['tp_kind'] for s in sessions}
        if 'strength' not in kinds:
            continue
        saw_two_a_day = True
        orders = sorted(sessions, key=lambda s: s['order_on_day'])
        assert orders[0]['tp_kind'] == 'strength', f"{date}: strength did not sort first: {sessions}"
        assert orders[0]['order_on_day'] == 0
        for idx, s in enumerate(orders):
            assert s['order_on_day'] == idx, f"{date}: order_on_day not sequential: {sessions}"
    assert saw_two_a_day, "no two-a-day (strength + bike, same date) found -- ordering not exercised"
