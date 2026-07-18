"""Regression tests for three workout-output-quality bugs Matti flagged from
a live TP calendar screenshot, all on the "Endurance with Surges" workout
(~15 alternating SteadyState pairs: 843s @ 70% FTP + 5s @ 150% FTP):

  Bug 1 -- segment durations too precise: 843s/849s-style segments rendered
  as "14:03" instead of "14min" in both the ZWO <SteadyState Duration> and
  the projected description. Fixed by
  nate_workout_generator._snap_long_segment_seconds (rounds a segment to the
  nearest whole minute once it's >=60s; leaves anything shorter -- e.g. a
  5-10s surge -- exact) plus workout_templates.scale_zwo_to_target_duration's
  snap_to=60 lever (now opted into by generate_athlete_package.py), which
  excludes those same sub-60s segments from its proportional scale/snap so a
  surge never gets rescaled up to a full minute.

  Bug 2 -- MAIN SET description unrolls rep-by-rep: 15x[steady + surge]
  rendered as 30 separate bullets (the "shit instructions" wall) -- and,
  found on a second pass against a live-regenerated plan, "Tempo Sprints"
  shipped the same wall in a harder shape: a non-repeating lead-in bullet
  followed by a period-3 group (85% / 200% sprint / 50% recovery) repeated
  4 times, a mid-set recovery break, then the same period-3 group again.
  Fixed by workout_spec.render_main_set / _collapse_repeated_lines /
  _find_best_repeat_run, which finds ANY contiguous run anywhere in the
  bullet list that is a period-K block (K>=1) repeated M>=2 times --
  leaving a lead-in, a mid-set break, and a trailing partial repeat exactly
  as they were -- and recurses on what's left so multiple independent
  repeat groups in one description all collapse, not just the first.

  Bug 3 -- ragged total duration ("4:09:44"): plan_ir.Session.total_time_planned
  summed raw segment seconds straight to hours. Fixed by
  plan_ir._round_time_planned_hours, which rounds to the nearest whole minute
  before projecting to hours, so the delivered totalTimePlanned (manifest +
  tpapi apply-job body) is always a whole number of minutes.

These tests mirror the style of test_naming_and_rounding.py: unit tests for
the primitives, plus sweeps over a real generated plan (reusing
test_naming_and_rounding's proven full_plan/w00_plan fixtures) so a
regression anywhere in the generation path is caught, not just in the one
archetype that surfaced it.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from archetype_registry import get_archetype
from nate_workout_generator import _snap_long_segment_seconds, generate_blocks_from_archetype
from plan_ir import _round_time_planned_hours, build_plan_ir, build_tp_manifest
import plan_ir as plan_ir_module
from workout_spec import normalize_zwo_blocks, render_main_set
from workout_templates import scale_zwo_to_target_duration

from test_naming_and_rounding import full_plan, w00_plan  # noqa: F401 (fixtures)


def _max_group_repeat(lines, max_k=4):
    """Return the largest number of consecutive back-to-back repeats found
    for any group size K in 1..max_k within `lines`.

    A "wall" is any group of K bullets repeated >=3 times with nothing
    collapsing it -- this catches BOTH the period-2 shape (a steady+surge
    pair unrolled rep-by-rep) AND the period-3+ shape (a work/sprint/
    recovery group unrolled rep-by-rep, the "Tempo Sprints" regression) --
    unlike a naive "consecutive IDENTICAL bullets" check, which only
    catches K=1 and misses group-repeats of DIFFERENT lines entirely.
    Independent of render_main_set's own algorithm, so it also catches a
    regression where collapse is skipped/bypassed for some code path.
    """
    n = len(lines)
    worst = 0
    for k in range(1, max_k + 1):
        for start in range(0, max(0, n - 2 * k + 1)):
            reps = 1
            while (start + (reps + 1) * k <= n
                   and lines[start + reps * k:start + (reps + 1) * k] == lines[start:start + k]):
                reps += 1
            worst = max(worst, reps)
    return worst


# ===========================================================================
# Bug 1 (a): _snap_long_segment_seconds unit tests -- the duration-snap rule.
#
# Rule: a segment duration is only ever snapped to the nearest whole minute
# once it's already >=60s (the "long" segments a coach reads in minutes).
# Anything under 60s (a 5-10s surge, an opener) is returned byte-for-byte
# unchanged -- it must never be snapped UP to a full minute.
# ===========================================================================

class TestSnapLongSegmentSeconds:
    @pytest.mark.parametrize("raw,expected", [
        (843, 840),   # 14:03 -> 14min
        (849, 840),   # 14:09 -> 14min (nearest-minute, not nearest-multiple-of-849)
        (5, 5),       # sub-60s surge: stays exact
        (30, 30),     # sub-60s: stays exact (rule is "<60s untouched", not "<60s -> 60s")
        (60, 60),     # exactly one minute: unchanged
        (900, 900),   # already whole-minute: unchanged
    ])
    def test_duration_snap_rule(self, raw, expected):
        assert _snap_long_segment_seconds(raw) == expected


# ===========================================================================
# Bug 1 (b): scale_zwo_to_target_duration(snap_to=60) must not touch
# sub-60s segments even while proportionally shrinking a workout, and must
# land the long blocks it does touch on whole minutes.
# ===========================================================================

class TestScaleSnapExcludesShortSegments:
    def _endurance_with_surges_zwo(self):
        blocks = ''.join(
            f'<SteadyState Duration="894" Power="0.70"/><SteadyState Duration="6" Power="1.50"/>'
            for _ in range(15)
        ) + '<SteadyState Duration="894" Power="0.70"/>'
        return (
            "<?xml version='1.0' encoding='UTF-8'?><workout_file><name>x</name>"
            "<description>d</description><workout>"
            '<Warmup Duration="600" PowerLow="0.5" PowerHigh="0.7"/>'
            + blocks +
            '<Cooldown Duration="300" PowerLow="0.6" PowerHigh="0.4"/>'
            "</workout></workout_file>"
        )

    def test_surges_survive_shrink_scaling_untouched(self):
        zwo = self._endurance_with_surges_zwo()
        scaled = scale_zwo_to_target_duration(zwo, 220, 'endurance', snap_to=60)
        durations = [int(d) for d in re.findall(r'<SteadyState[^>]*Duration="(\d+)"', scaled)]
        surge_durations = [d for d in durations if d < 60]
        long_durations = [d for d in durations if d >= 60]
        assert surge_durations, "test setup lost surge segments"
        assert all(d == 6 for d in surge_durations), (
            f"a sub-60s surge was rescaled: {surge_durations}")
        assert long_durations, "test setup lost long steady segments"
        assert all(d % 60 == 0 for d in long_durations), (
            f"a long (>=60s) segment did not land on a whole minute: {long_durations}")


# ===========================================================================
# Bug 2: render_main_set collapses a repeating unit; a single non-repeated
# segment, and a true IntervalsT-derived segment, are unaffected.
# ===========================================================================

class TestRenderMainSetCollapse:
    def test_synthetic_15x_steady_surge_collapses_to_few_lines(self):
        segments = []
        for _ in range(15):
            segments.append({'kind': 'steady', 'seconds': 840, 'power': 0.70})
            segments.append({'kind': 'steady', 'seconds': 6, 'power': 1.50})
        rendered = render_main_set(segments)
        lines = rendered.strip().split('\n')
        assert len(lines) <= 3, f"surge MAIN SET should collapse to <=3 lines, got: {lines}"
        assert '70%' in rendered and '150%' in rendered
        assert re.search(r'\bx\b|x \(', rendered), f"no rep-count marker in collapsed line: {rendered!r}"

    def test_true_intervals_segment_still_collapses_to_nx_form(self):
        blocks = ('<IntervalsT Repeat="5" OnDuration="180" OnPower="1.15" '
                  'OffDuration="120" OffPower="0.55" />')
        rendered = render_main_set(normalize_zwo_blocks(blocks))
        assert rendered == '- 5x3min @ 115% FTP, 2min recovery @ 55% FTP'

    def test_single_non_repeated_segment_renders_unchanged(self):
        segments = [{'kind': 'steady', 'seconds': 1800, 'power': 0.65}]
        assert render_main_set(segments) == '- 30min @ 65% FTP'

    def test_real_endurance_with_surges_archetype_collapses(self):
        """End-to-end through the real archetype + generation path (not a
        synthetic fixture): the actual 'Endurance with Surges' L1 data,
        pushed through generate_blocks_from_archetype and back through
        render_main_set, must not unroll into a wall."""
        _, archetype = get_archetype('Endurance with Surges')
        blocks = generate_blocks_from_archetype(archetype, 1)
        rendered = render_main_set(normalize_zwo_blocks(blocks))
        lines = rendered.strip().split('\n')
        assert len(lines) <= 3, f"real archetype MAIN SET should collapse, got: {lines}"

    def test_synthetic_lead_in_plus_period_3_group_collapses_to_single_line(self):
        """The exact shape that regressed on 'Tempo Sprints': a one-line
        lead-in followed by a period-3 group (work / sprint / recovery)
        repeated N>=2 times, with NO mid-set break -- must collapse to one
        "N x (unit)" line, leaving the lead-in as its own bullet."""
        segments = [{'kind': 'steady', 'seconds': 600, 'power': 0.70}]
        for _ in range(5):
            segments.append({'kind': 'steady', 'seconds': 120, 'power': 0.85})
            segments.append({'kind': 'steady', 'seconds': 10, 'power': 2.00})
            segments.append({'kind': 'steady', 'seconds': 50, 'power': 0.50})
        rendered = render_main_set(segments)
        lines = rendered.strip().split('\n')
        assert lines[0] == '- 10min @ 70% FTP', f"lead-in should stay its own bullet, got: {lines}"
        assert len(lines) == 2, f"period-3 group should collapse to 1 line after the lead-in, got: {lines}"
        assert lines[1] == '- 5 x (2min @ 85% FTP + 0:10 @ 200% FTP + 0:50 @ 50% FTP)'

    def test_real_tempo_sprints_archetype_collapses_both_repeat_groups(self):
        """End-to-end through the real 'Tempo Sprints' archetype (the exact
        workout the coordinator flagged as still shipping a wall): a
        lead-in, a period-3 group x4, a mid-set recovery break, then the
        same period-3 group x4 again. Both repeat groups must collapse --
        no group of size K in 1..4 may repeat >=3 times uncollapsed
        anywhere in the rendered MAIN SET, regardless of the mid-set break
        splitting them into two separate runs."""
        _, archetype = get_archetype('Tempo Sprints')
        blocks = generate_blocks_from_archetype(archetype, 1)
        rendered = render_main_set(normalize_zwo_blocks(blocks))
        lines = [l[2:] for l in rendered.strip().split('\n')]  # strip "- " prefix
        assert _max_group_repeat(lines) < 3, (
            f"Tempo Sprints MAIN SET still has an uncollapsed repeat wall: {lines}")
        assert sum(1 for l in lines if 'x (' in l or re.match(r'\d+x ', l)) >= 2, (
            f"expected both period-3 repeat groups to collapse to their own "
            f"'M x (...)' line, got: {lines}")


# ===========================================================================
# Bug 3: total_time_planned always projects a whole number of minutes.
# ===========================================================================

class TestRoundTimePlannedHours:
    @pytest.mark.parametrize("duration_sec", [0, 14910, 14400, 3723, 1, 59])
    def test_rounds_to_whole_minute_of_seconds(self, duration_sec):
        hours = _round_time_planned_hours(duration_sec)
        # Reconstructing seconds from the stored (4-decimal) hours value must
        # land on an exact multiple of 60 once re-rounded to the nearest
        # second -- i.e. "a whole number of minutes", not a ragged remainder.
        reconstructed_sec = round(hours * 3600)
        assert reconstructed_sec % 60 == 0, (
            f"total_time_planned for {duration_sec}s round-trips to "
            f"{reconstructed_sec}s, not a whole number of minutes")

    def test_zero_duration_is_zero(self):
        assert _round_time_planned_hours(0) == 0.0


# ===========================================================================
# Golden-plan sweeps: build a real plan (reusing test_naming_and_rounding's
# proven fixtures) and assert no description regresses into a rep-wall, no
# segment >=60s shows a ragged seconds component, and every bike session's
# projected duration (manifest + tp_manifest.json, which tools/tp_apply_order
# passes straight through into the apply-job body's totalTimePlanned) is a
# whole number of minutes.
# ===========================================================================

_MSS_RE = re.compile(r'(\d+):(\d{2})')


def _zwo_description(path):
    m = re.search(r'<description>(.*?)</description>', path.read_text(), re.S)
    return m.group(1) if m else path.read_text()


@pytest.fixture(scope='module')
def golden_files(full_plan, w00_plan):
    _, _, _, full_files = full_plan
    _, _, _, w00_files = w00_plan
    return list(full_files) + list(w00_files)


def test_no_description_has_a_rep_by_rep_wall(golden_files):
    """No generated ZWO <description> contains an uncollapsed group of K
    bullets (K in 1..4) repeated >=3 times back-to-back -- the general
    rep-wall guard. Checking only consecutive IDENTICAL bullets (K=1) would
    catch the "Endurance with Surges" period-2 surge wall but miss
    "Tempo Sprints"-shaped period-3+ group-repeats of DIFFERENT lines."""
    offenders = []
    for f in golden_files:
        lines = [line for line in _zwo_description(f).split('\n') if line.strip().startswith('-')]
        worst = _max_group_repeat(lines)
        if worst >= 3:
            offenders.append((f.name, worst))
    assert offenders == [], (
        f"description(s) with an uncollapsed repeat wall (fname, repeat count): {offenders}")


def test_no_long_segment_renders_with_ragged_seconds(golden_files):
    """No segment >=60s renders with a non-zero seconds component ("14:03")
    anywhere in a generated description; sub-60s segments (surges) may
    legitimately show as "0:05" etc."""
    offenders = []
    for f in golden_files:
        desc = _zwo_description(f)
        for m in _MSS_RE.finditer(desc):
            if int(m.group(1)) >= 1:  # M:SS with M>=1 minute implies >=60s total
                offenders.append((f.name, m.group(0)))
    assert offenders == [], (
        f"description(s) with a ragged (non-whole-minute) >=60s segment: {offenders}")


@pytest.fixture(scope='module')
def full_plan_manifest(full_plan, monkeypatch_module):
    athlete_dir, plan_dates, profile, _ = full_plan
    monkeypatch_module.setattr(plan_ir_module, 'ATHLETES_DIR', athlete_dir.parent)
    (athlete_dir / 'profile.yaml').write_text(yaml.safe_dump(profile))
    (athlete_dir / 'plan_dates.yaml').write_text(yaml.safe_dump(plan_dates))
    (athlete_dir / 'fueling.yaml').write_text(yaml.safe_dump({}))
    (athlete_dir / 'weekly_structure.yaml').write_text(yaml.safe_dump({}))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        build_plan_ir('full-plan-athlete')
        manifest = build_tp_manifest('full-plan-athlete')
    return manifest


@pytest.fixture(scope='module')
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_manifest_total_time_planned_is_whole_minutes(full_plan_manifest):
    bike_sessions = [s for s in full_plan_manifest['sessions'] if s['tp_kind'] == 'bike']
    assert bike_sessions, "no bike sessions found -- test setup lost coverage"
    offenders = []
    for s in bike_sessions:
        ttp = s.get('total_time_planned')
        if not ttp:
            continue
        reconstructed_sec = round(ttp * 3600)
        if reconstructed_sec % 60 != 0:
            offenders.append((s.get('filename_stem'), ttp, reconstructed_sec))
    assert offenders == [], (
        f"bike session(s) with a non-whole-minute totalTimePlanned "
        f"(stem, hours, reconstructed_sec): {offenders}")
