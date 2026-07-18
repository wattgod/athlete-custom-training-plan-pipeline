"""D2 (filename/display-name split, progression suffixes) + D4 (rounding,
description hygiene) regression tests.

Two integration fixtures drive full `generate_zwo_files` runs and cover
every branch named in the spec that is actually reachable through the
block-builder-first architecture: main block path (incl. series suffixes),
A-race, B-race, travel day, rest/off days, the legacy generic path (FTP
test / B-race opener / B-race easy -- the only way the "LEGACY PATH:" block
is ever entered, see generate_athlete_package.py's `_defer_to_legacy`
gate), strength, and W00 pre-plan.

Some branches named in the spec's naming split (the plain 1-min "Rest"
ZWO, the direct Nate-generator legacy branch keyed on `nate_workout_types`,
and the progressive interval/endurance fallback) are dead code under the
current architecture: `_use_block_builder` is only ever True or raising
(CLAUDE.md: "There is NO legacy fallback for block-builder exceptions"),
block-builder OFF days `continue` without ever emitting a ZWO, and the
LEGACY PATH is only reached via `_defer_to_legacy`, which always resolves
`workout_type` to FTP_Test/Openers/Easy -- never Rest, and never a
`nate_workout_types` key. Those branches still got the filename/display
split (defensive correctness if the architecture ever changes), and are
covered here with direct unit tests against the underlying functions
instead of forcing unreachable integration paths.
"""
import datetime
import re
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import calculate_plan_dates as cpd
import plan_ir
from generate_athlete_package import generate_zwo_files, _display_words, GENERIC_NO_SUFFIX
from nate_workout_generator import generate_nate_zwo
from plan_ir import build_plan_ir
from workout_library import generate_progressive_interval_blocks
from workout_spec import _mins
from workout_templates import scale_zwo_to_target_duration


DECIMAL_MINUTE_RE = re.compile(r'\d+\.\d+ ?min')
DATE_PATTERN_RE = re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d|W\d\d_')


# ===========================================================================
# (c) M:SS formatting unit tests
# ===========================================================================

class TestMinsFormatting:
    def test_whole_minutes_render_as_nmin(self):
        assert _mins(60) == '1min'
        assert _mins(120) == '2min'
        assert _mins(0) == '0min'

    def test_non_whole_minutes_render_as_mss(self):
        assert _mins(445) == '7:25'   # 7min 25sec
        assert _mins(30) == '0:30'
        assert _mins(15) == '0:15'
        assert _mins(90) == '1:30'

    def test_never_emits_a_decimal_minute_token(self):
        for seconds in range(0, 3661, 7):
            assert not DECIMAL_MINUTE_RE.search(_mins(seconds)), \
                f"{seconds}s rendered a decimal-minute token: {_mins(seconds)!r}"


class TestSnapToOption(object):
    def test_default_snap_to_off_is_unchanged(self):
        zwo = (
            "<?xml version='1.0' encoding='UTF-8'?><workout_file><name>x</name>"
            "<description>d</description><workout>"
            '<Warmup Duration="600" PowerLow="0.5" PowerHigh="0.7"/>'
            '<IntervalsT Repeat="4" OnDuration="180" OnPower="1.1" OffDuration="120" OffPower="0.55"/>'
            '<Cooldown Duration="300" PowerLow="0.6" PowerHigh="0.4"/>'
            "</workout></workout_file>")
        without_flag = scale_zwo_to_target_duration(zwo, 30, 'vo2max')
        with_flag_off = scale_zwo_to_target_duration(zwo, 30, 'vo2max', snap_to=0)
        assert without_flag == with_flag_off

    def test_snap_to_60_rounds_scaled_blocks_to_whole_minutes(self):
        zwo = (
            "<?xml version='1.0' encoding='UTF-8'?><workout_file><name>x</name>"
            "<description>d</description><workout>"
            '<Warmup Duration="600" PowerLow="0.5" PowerHigh="0.7"/>'
            '<IntervalsT Repeat="4" OnDuration="180" OnPower="1.1" OffDuration="120" OffPower="0.55"/>'
            '<Cooldown Duration="300" PowerLow="0.6" PowerHigh="0.4"/>'
            "</workout></workout_file>")
        scaled = scale_zwo_to_target_duration(zwo, 75, 'vo2max', snap_to=60)
        durations = [int(d) for d in re.findall(r'Duration="(\d+)"', scaled)]
        # Warmup/Cooldown are the blocks this helper snaps; IntervalsT block
        # duration isn't a literal Duration= attribute (Repeat/On/Off), so
        # every Duration= value present here belongs to a snapped block.
        for d in durations:
            assert d % 60 == 0, f"unsnapped duration: {d}s"


# ===========================================================================
# Integration fixtures
# ===========================================================================

def _base_profile(athlete_id, race_name, race_date, extra=None):
    profile = {
        'name': 'Sanity Sample',
        'athlete_id': athlete_id,
        'target_race': {'name': race_name, 'date': race_date,
                         'distance_miles': 60, 'discipline': 'gravel'},
        'fitness_markers': {'ftp_watts': 250, 'weight_kg': 75},
        'weekly_availability': {'cycling_hours_target': 6},
        'schedule_constraints': {'preferred_long_day': 'saturday',
                                  'preferred_off_days': ['monday']},
        'preferred_days': {
            'monday': {'availability': 'rest'},
            'tuesday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 90},
            'wednesday': {'availability': 'available', 'is_key_day_ok': False, 'max_duration_min': 75},
            'thursday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 90},
            'friday': {'availability': 'available', 'is_key_day_ok': False, 'max_duration_min': 75},
            'saturday': {'availability': 'available', 'is_key_day_ok': True, 'is_long_day': True, 'max_duration_min': 240},
            'sunday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 150},
        },
    }
    if extra:
        profile.update(extra)
    return profile


def _build_full_plan(tmp_path):
    """Frozen-calendar 8-week plan covering block-builder series, A-race,
    B-race, travel, and (via FTP-test injection) the legacy generic path,
    plus strength. Recipe proven in test_zwo_format.py's
    fresh_sample_workouts fixture; extended here with travel_dates."""

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
        'ws-a-full-plan-sample', 'Sanity Gravel Race', '2026-03-21',
        extra={'b_events': [{'name': 'Sanity Tune-Up', 'date': '2026-03-07', 'priority': 'B'}]},
    )
    derived = {'plan_weeks': 8, 'ability_level': 'Intermediate'}
    methodology = {'methodology_id': 'polarized_80_20',
                    'configuration': {'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}}}

    athlete_dir = tmp_path / 'full-plan-athlete'
    (athlete_dir / 'workouts').mkdir(parents=True)
    files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    assert files, "generate_zwo_files produced no workouts"
    return athlete_dir, plan_dates, profile, files


def _build_w00_plan(tmp_path):
    """Real (unfrozen) calendar with plan_start forced 1-7 days out so the
    W00 pre-plan-week branch fires. W00's days_until_start check uses a
    *local* `datetime.now()` import inside generate_pre_plan_week, not the
    frozen calculate_plan_dates clock, so it is intentionally left
    unfrozen (documented host-local behavior) and computed relative to the
    real wall clock at test-run time: pick a race far enough out that the
    naive week-1-Monday computation lands in the past, which forces
    calculate_plan_dates's clamp-to-next-Monday, always 1-7 days out."""
    today = datetime.datetime.now().date()
    race_date = (today + datetime.timedelta(days=40)).isoformat()
    plan_dates = cpd.calculate_plan_dates(race_date, plan_weeks=10)
    days_out = (datetime.date.fromisoformat(plan_dates['plan_start']) - today).days
    assert 1 <= days_out <= 7, (
        "test setup drifted -- plan_start no longer lands in the W00 window "
        f"(days_out={days_out}); adjust the race_date/plan_weeks offsets above"
    )

    profile = _base_profile('ws-a-w00-sample', 'W00 Test Race', race_date)
    derived = {'plan_weeks': plan_dates.get('plan_weeks', 6), 'ability_level': 'Intermediate'}
    methodology = {'methodology_id': 'polarized_80_20',
                    'configuration': {'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}}}

    athlete_dir = tmp_path / 'w00-athlete'
    (athlete_dir / 'workouts').mkdir(parents=True)
    files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    w00_files = [f for f in files if f.name.startswith('W00_')]
    assert w00_files, "test setup did not trigger the W00 pre-plan branch"

    # D1 W00 fix: generate_athlete_package() merges the W00 week entry into
    # plan_dates['weeks'] (from generate_zwo_files.last_pre_plan_week) before
    # PlanIR ever runs -- replicate that merge here since this fixture calls
    # generate_zwo_files directly, not the full package function.
    pre_plan_week = getattr(generate_zwo_files, 'last_pre_plan_week', None)
    assert pre_plan_week, "test setup did not capture a W00 week entry"
    plan_dates.setdefault('weeks', []).insert(0, pre_plan_week)

    return athlete_dir, plan_dates, profile, files


@pytest.fixture(scope='module')
def full_plan(tmp_path_factory):
    return _build_full_plan(tmp_path_factory.mktemp('full-plan'))


@pytest.fixture(scope='module')
def w00_plan(tmp_path_factory):
    return _build_w00_plan(tmp_path_factory.mktemp('w00-plan'))


@pytest.fixture(scope='module')
def all_generated_files(full_plan, w00_plan):
    _, _, _, full_files = full_plan
    _, _, _, w00_files = w00_plan
    return list(full_files) + list(w00_files)


def _zwo_name(path):
    m = re.search(r'<name>(.*?)</name>', path.read_text())
    return m.group(1) if m else ''


def _zwo_description(path):
    m = re.search(r'<description>(.*?)</description>', path.read_text(), re.S)
    return m.group(1) if m else path.read_text()


# ===========================================================================
# (a) No decimal-minute token anywhere in any generated description.
# ===========================================================================

def test_no_decimal_minute_token_in_any_description(all_generated_files):
    offenders = [p.name for p in all_generated_files
                 if DECIMAL_MINUTE_RE.search(_zwo_description(p))]
    assert offenders == [], f"decimal-minute token(s) found in: {offenders}"


# ===========================================================================
# (b) No date pattern in any ZWO <name> element, across every reachable
# branch (main block/series, A-race, B-race, travel, legacy/FTP-test,
# strength, W00).
# ===========================================================================

def test_no_date_pattern_in_any_zwo_name(all_generated_files):
    offenders = {p.name: _zwo_name(p) for p in all_generated_files
                 if DATE_PATTERN_RE.search(_zwo_name(p))}
    assert offenders == {}, f"date pattern leaked into <name>: {offenders}"


def test_every_reachable_branch_is_represented(full_plan, w00_plan):
    """Guards the harness itself: a silently-skipped branch would make the
    two sweeps above pass for the wrong reason."""
    _, _, _, full_files = full_plan
    _, _, _, w00_files = w00_plan
    names = {f.name: _zwo_name(f) for f in full_files}

    assert any('RACE_DAY' in n and 'Sanity_Gravel_Race' in n for n in names), 'A-race branch not exercised'
    assert any('RACE_DAY' in n and 'Sanity_Tune-Up' in n for n in names), 'B-race branch not exercised'
    assert any('Travel_Day_Shakeout' in n for n in names), 'travel branch not exercised'
    assert any(v == 'FTP Test' for v in names.values()), 'legacy generic (FTP test) branch not exercised'
    assert any('_Strength_' in n for n in names), 'strength branch not exercised'
    assert any(re.search(r'\(\d+ of \d+\)', v) for v in names.values()), \
        'no series suffix produced -- series-suffix coverage lost'
    assert any(f.name.startswith('W00_') for f in w00_files), 'W00 branch not exercised'


# ===========================================================================
# (d) Filename stems unchanged: PlanIR still matches every ZWO by
# stem.startswith(workout_prefix).
# ===========================================================================

def _plan_ir_matches_every_zwo(athlete_dir, plan_dates, profile, athlete_id, monkeypatch,
                               allow_unmatched_date_prefixes=()):
    """Assert PlanIR's stem.startswith(workout_prefix) matching (plan_ir.py:311)
    still finds every ZWO this workstream renamed.

    allow_unmatched_date_prefixes: filename prefixes (e.g. "W00_") that are
    KNOWN to fall into plan_ir's orphan-bucket fallback for reasons entirely
    unrelated to this workstream -- W00 pre-plan days are never written into
    plan_dates['weeks'] at all (they're computed on the fly by
    generate_pre_plan_week from days_until_start, not from plan_dates), so
    there is no calendar-day workout_prefix for them to match against
    regardless of filename shape. The spec files this as a D1 PlanIR-
    projection fix ("give W00 days dates in plan_dates so PlanIR matches
    them"), explicitly out of scope for D2/D4 -- this test only asserts
    W00 ZWOs aren't silently DROPPED, not that they hit the primary
    calendar-day match path.
    """
    monkeypatch.setattr(plan_ir, 'ATHLETES_DIR', athlete_dir.parent)
    (athlete_dir / 'profile.yaml').write_text(_dump_yaml(profile))
    (athlete_dir / 'plan_dates.yaml').write_text(_dump_yaml(plan_dates))
    (athlete_dir / 'fueling.yaml').write_text(_dump_yaml({}))
    (athlete_dir / 'weekly_structure.yaml').write_text(_dump_yaml({}))

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        ir = build_plan_ir(athlete_id)

    zwo_names = {p.name for p in (athlete_dir / 'workouts').glob('*.zwo')}
    matched_names = set()
    unmatched_date = []
    for week in ir.weeks:
        for session in week.sessions:
            if not session.source_file:
                continue
            matched_names.add(session.source_file)
            if session.date is None:
                # Only reachable via the "orphan bucket" fallback
                # (plan_ir.py _build_weeks), i.e. the filename's stem did
                # NOT startswith any calendar day's workout_prefix.
                unmatched_date.append(session.source_file)

    missing = zwo_names - matched_names
    assert missing == set(), f"ZWO(s) never matched by PlanIR at all: {missing}"

    unexpected_unmatched = [
        name for name in unmatched_date
        if not name.startswith(tuple(allow_unmatched_date_prefixes))
    ]
    assert unexpected_unmatched == [], (
        f"ZWO(s) matched only via the unmatched-filename fallback, not the "
        f"calendar day's workout_prefix -- filename_stem shape changed: {unexpected_unmatched}"
    )


def _dump_yaml(data):
    import yaml
    return yaml.safe_dump(data)


def test_plan_ir_matches_every_zwo_in_full_plan(full_plan, monkeypatch):
    athlete_dir, plan_dates, profile, _ = full_plan
    _plan_ir_matches_every_zwo(athlete_dir, plan_dates, profile, 'full-plan-athlete', monkeypatch)


def test_plan_ir_matches_every_zwo_in_w00_plan(w00_plan, monkeypatch):
    """D1 fix landed (WS-B): plan_dates now carries a real week=0 W00 entry
    (see _build_w00_plan), so W00 ZWOs match PlanIR's primary
    stem.startswith(workout_prefix) path like any other calendar day -- the
    former allow_unmatched_date_prefixes=('W00_',) exemption is removed."""
    athlete_dir, plan_dates, profile, _ = w00_plan
    _plan_ir_matches_every_zwo(athlete_dir, plan_dates, profile, 'w00-athlete', monkeypatch)


# ===========================================================================
# (e) Series suffix correctness: no "(1 of 1)", no gaps.
# ===========================================================================

def test_series_suffixes_have_no_solo_or_gapped_series(full_plan):
    _, _, _, full_files = full_plan
    names = [_zwo_name(f) for f in full_files]

    suffix_re = re.compile(r'^(.*) \((\d+) of (\d+)\)$')
    by_base_and_total = {}
    for name in names:
        m = suffix_re.match(name)
        if not m:
            continue
        base, idx, total = m.group(1), int(m.group(2)), int(m.group(3))
        assert total > 1, f'"(1 of 1)"-style solo suffix should never be emitted: {name!r}'
        by_base_and_total.setdefault((base, total), set()).add(idx)

    assert by_base_and_total, 'no suffixed series found -- test setup lost series coverage'
    for (base, total), indices in by_base_and_total.items():
        assert indices == set(range(1, total + 1)), (
            f"series {base!r} has a numbering gap: got indices {sorted(indices)}, "
            f"expected 1..{total}"
        )


def test_generic_names_never_get_a_suffix(full_plan):
    _, _, _, full_files = full_plan
    names = [_zwo_name(f) for f in full_files]
    suffix_re = re.compile(r'^(.*) \(\d+ of \d+\)$')
    for name in names:
        m = suffix_re.match(name)
        if m and m.group(1) in GENERIC_NO_SUFFIX:
            pytest.fail(f"generic name {m.group(1)!r} incorrectly got a series suffix: {name!r}")


# ===========================================================================
# Dead-branch unit coverage: the plain "Rest" 1-min ZWO, the direct
# Nate-generator legacy branch, and the progressive interval/endurance
# fallback are unreachable through generate_zwo_files under the current
# block-builder-first architecture (see module docstring). Test the naming
# primitives they use directly instead.
# ===========================================================================

def test_display_words_helper_strips_underscores_and_dates_never_leak_in():
    assert _display_words('Gravel_Specific') == 'Gravel Specific'
    assert _display_words('VO2max') == 'VO2max'
    assert _display_words('Pre_Plan_Endurance') == 'Pre-Plan Endurance'
    assert not DATE_PATTERN_RE.search(_display_words('Gravel_Specific'))


def test_rest_day_display_name_constant_has_no_date():
    """Regression guard for the dead-but-present 1-min Rest ZWO branch
    (generate_athlete_package.py, "Generate Rest days as 1-min workouts")."""
    source = Path(__file__).parent.joinpath('generate_athlete_package.py').read_text()
    assert "name='Rest Day'," in source, (
        "Rest-day ZWO name literal changed or was removed -- update this "
        "guard (and verify it still has no date leak) if that was intentional"
    )


def test_nate_generator_legacy_branch_display_name_has_no_date():
    """The direct generate_nate_zwo() call in the legacy Nate-generator
    branch (workout_type in nate_workout_types) is unreachable in practice
    (see module docstring) but is still wired with display_name -- verify
    the wiring works and produces a clean <name>."""
    workout_name = 'W03_Tue_Mar10_VO2max'  # what the branch computes for the filename
    display_name = _display_words('VO2max')
    zwo = generate_nate_zwo('vo2max', level=3, methodology='POLARIZED',
                            workout_name=workout_name, display_name=display_name)
    assert zwo is not None
    name = _zwo_name_from_string(zwo)
    assert name == 'VO2max'
    assert not DATE_PATTERN_RE.search(name)
    assert workout_name not in name


def test_progressive_interval_fallback_name_has_no_date():
    """The progressive-interval fallback (generate_progressive_interval_blocks)
    supplies display_name in the branch it feeds; verify its returned name
    carries no date pattern regardless of reachability."""
    _blocks, progressive_name = generate_progressive_interval_blocks(
        phase='build', week_num=5, week_in_phase=2, duration_min=60)
    assert not DATE_PATTERN_RE.search(progressive_name)
    assert not DECIMAL_MINUTE_RE.search(progressive_name)


def _zwo_name_from_string(zwo_xml):
    m = re.search(r'<name>(.*?)</name>', zwo_xml)
    return m.group(1) if m else ''
