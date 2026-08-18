"""Regression coverage for the v29 "design fixes" wave (coach: these are
"kind of a dumpster fire" -- five independently coach-reported defects).

1. Bookends must never exceed the main set they bracket -- synthesized easy
   templates used fixed 50->65 / 70->50 bookends regardless of the main
   set's actual intensity. A live FatMax Development delivery had its
   COOL-DOWN start at 70% FTP over a 55-65% main set, so TP's chart showed
   the cool-down as the hardest part of the ride.
2. New tp_library_snapshot lint `lint_bookend_intensity`: catches the same
   defect at the curated TP source (future-drift guard).
3. Testing-week order: two independent day-placement mechanisms (the block
   path's day-role template, and the legacy FTP-day overlay) disagreed on
   which day got the FTP test, so the Anaerobic Test could land BEFORE the
   FTP test whose zones it depends on.
4. FTP retest spacing: a mid-plan retest now requires total_weeks >= 10 AND
   a >= 5-week gap from the previous test (an 8-week plan retested at
   Week 3 -- two weeks after the Week 1 baseline).
5. "Endurance Blocks" display-name honesty: a library-resolved session
   whose PLACED structure has no real block variation (one flat SteadyState
   between two ramps) drops the word "Blocks" from its display name.
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from archetype_registry import get_archetype
from block_builder import build_calendar_week
from generate_athlete_package import _library_display_name
from nate_workout_generator import (
    enforce_steady_workout_invariants,
    generate_blocks_from_archetype,
)
from series_tracker import SeriesTracker
from tp_library_snapshot import DEFAULT_RAW_PATH, build_index, compute_bookend_intensity_flag
from workout_mapper import _render_simple_endurance, _render_taper_burst_endurance

REAL_DUMP_AVAILABLE = DEFAULT_RAW_PATH.exists()
requires_real_dump = pytest.mark.skipif(
    not REAL_DUMP_AVAILABLE, reason=f"real raw dump not present at {DEFAULT_RAW_PATH}"
)


def _leaf(seconds, intensity, minv, maxv=None):
    target = {"minValue": minv}
    if maxv is not None:
        target["maxValue"] = maxv
    return {
        "name": "x", "length": {"value": seconds, "unit": "second"},
        "targets": [target], "intensityClass": intensity, "openDuration": False,
    }


def _block(leaves, repeat=1):
    return {"type": "step", "length": {"value": repeat, "unit": "repetition"}, "steps": leaves}


# ---------------------------------------------------------------------------
# FIX 1 -- bookends must never exceed the main set
# ---------------------------------------------------------------------------

class TestBookendsNeverExceedMainSet:
    def test_easy_taper_burst_endurance_warmup_capped_at_65(self):
        """Main dominant target is 70% (edges) with 150% micro-bursts; the
        formula (min(65,main), min(70,main)) resolves to exactly 65/70 for
        any main-set peak >= 65/70, so this hard-adjacent easy ride's warmup
        must drop from its old fixed 70% peak to 65%."""
        zwo = _render_taper_burst_endurance(3)
        warmup = re.search(r'<Warmup[^/]*PowerHigh="([0-9.]+)"', zwo)
        cooldown = re.search(r'<Cooldown[^/]*PowerLow="([0-9.]+)"', zwo)
        assert float(warmup.group(1)) <= 0.65 + 1e-9
        assert float(cooldown.group(1)) <= 0.70 + 1e-9

    @pytest.mark.parametrize("level", range(1, 7))
    def test_easy_simple_endurance_bookends_never_exceed_main(self, level):
        zwo = _render_simple_endurance(level)
        warmup = re.search(r'<Warmup[^/]*PowerHigh="([0-9.]+)"', zwo)
        cooldown = re.search(r'<Cooldown[^/]*PowerLow="([0-9.]+)"', zwo)
        main_all = [float(v) for v in re.findall(r'<SteadyState[^/]*Power="([0-9.]+)"', zwo)]
        main_max = max(main_all)
        assert float(warmup.group(1)) <= main_max + 1e-9
        assert float(cooldown.group(1)) <= main_max + 1e-9
        # And the historical 65/70 ceiling is respected even when main < 65.
        assert float(warmup.group(1)) <= 0.65 + 1e-9
        assert float(cooldown.group(1)) <= 0.70 + 1e-9

    def test_hard_workout_bookends_unchanged_at_65_70(self):
        """enforce_steady_workout_invariants' formula -- min(65, main) /
        min(70, main) -- resolves back to the historical 65/70 defaults
        whenever the main set is hard (>= 76% FTP). This must never change:
        it's the "current 65/70 bookends are fine" half of the coach's own
        ruling."""
        hard_body = (
            '    <Warmup Duration="600" PowerLow="0.50" PowerHigh="0.75"/>\n'
            '    <SteadyState Duration="1200" Power="1.10"/>\n'
            '    <Cooldown Duration="600" PowerLow="0.75" PowerHigh="0.45"/>'
        )
        fixed = enforce_steady_workout_invariants(hard_body)
        warmup = re.search(r'<Warmup[^/]*PowerHigh="([0-9.]+)"', fixed)
        cooldown = re.search(r'<Cooldown[^/]*PowerLow="([0-9.]+)"', fixed)
        assert warmup.group(1) == "0.65"
        assert cooldown.group(1) == "0.70"

    def test_easy_fatmax_development_cooldown_never_starts_above_main(self):
        """Root-cause regression: the live delivered FatMax Development had
        its cool-down START at 70% FTP above its own 55-65% main set -- the
        coach's literal complaint. Structure and description must agree,
        which this render (single source of truth for both) guarantees by
        construction."""
        _, archetype = get_archetype("FatMax Development")
        for level in (1, 3, 6):
            zwo = generate_blocks_from_archetype(archetype, level)
            main = re.search(r'<SteadyState[^/]*Power="([0-9.]+)"', zwo)
            cooldown = re.search(r'<Cooldown[^/]*PowerLow="([0-9.]+)"', zwo)
            warmup = re.search(r'<Warmup[^/]*PowerHigh="([0-9.]+)"', zwo)
            assert float(cooldown.group(1)) <= float(main.group(1)) + 1e-9, (
                f"level {level}: cooldown starts above main set")
            assert float(warmup.group(1)) <= float(main.group(1)) + 1e-9, (
                f"level {level}: warmup peaks above main set")


# ---------------------------------------------------------------------------
# FIX 2 -- lint_bookend_intensity
# ---------------------------------------------------------------------------

class TestLintBookendIntensity:
    def test_synthetic_easy_item_with_broken_cooldown_flags(self):
        """70->50 cooldown ramp bracketing a 60% main set -- the exact
        FatMax-style defect."""
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 65)]),
            _block([_leaf(600, "active", 60)]),
            _block([_leaf(600, "active", 60)]),
            _block([_leaf(600, "active", 60)]),
            _block([_leaf(600, "coolDown", 50, 70)]),
        ]}
        flag = compute_bookend_intensity_flag(structure)
        assert flag is not None
        assert flag["main_max_pct"] == 60.0
        blocks = {o["block"] for o in flag["offenders"]}
        assert "cooldown" in blocks

    def test_openers_item_with_150_percent_finish_does_not_flag(self):
        """A legitimate hard-finish opener/crit-warmup: its bookends can
        legitimately run higher than the easy padding because the item's
        real content is the hard finish, not the padding."""
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 70)]),
            _block([_leaf(420, "active", 65)]),
            _block([_leaf(120, "active", 120)]),
            _block([_leaf(180, "active", 55)]),
            _block([_leaf(30, "active", 125), _leaf(120, "rest", 55)], repeat=3),
            _block([_leaf(600, "coolDown", 45, 65)]),
        ]}
        assert compute_bookend_intensity_flag(structure) is None

    def test_field_test_item_does_not_flag(self):
        """An FTP/Anaerobic Test authors its all-out effort as an
        untargeted (0%) leaf -- the heuristic only ever sees the easy
        reference-pace padding, so a structure-only read would misclassify
        this as an easy ride with broken bookends. The item's name (real
        example: "Specialty - Anaerobic Test - 3min - ref - 62min - RPE8-9")
        is a required second signal to exempt it correctly."""
        structure = {"structure": [
            _block([_leaf(1200, "warmUp", 50, 75)]),
            _block([_leaf(1740, "active", 55)]),
            _block([_leaf(180, "active", 0)]),
            _block([_leaf(600, "coolDown", 50, 75)]),
        ]}
        assert compute_bookend_intensity_flag(structure) is not None  # no name -> can't tell
        assert compute_bookend_intensity_flag(structure, "Specialty - Anaerobic Test") is None

    def test_fewer_than_three_target_bearing_blocks_skips(self):
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 65)]),
            _block([_leaf(1200, "active", 60)]),
        ]}
        assert compute_bookend_intensity_flag(structure) is None

    def test_consistent_bookends_do_not_flag(self):
        """Warmup/cooldown that top out AT the main set (not above it) --
        the corrected shape -- must never flag."""
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 65)]),
            _block([_leaf(600, "active", 65)]),
            _block([_leaf(600, "active", 65)]),
            _block([_leaf(600, "active", 65)]),
            _block([_leaf(600, "coolDown", 50, 65)]),
        ]}
        assert compute_bookend_intensity_flag(structure) is None

    @requires_real_dump
    def test_real_index_lint_runs_clean_and_flags_something(self):
        """Sanity check against the live curated library.

        NOTE (Aug 18 2026): the original bug report's "Endurance Blocks -
        1..6" and "Endurance - FatMax Development - ..." ladders were
        expected to produce >= 6 real flags. Verified directly against this
        session's raw dump: the orchestrator's parallel TP-source fix has
        ALREADY landed -- all 12 items across both families now have
        warmup/cooldown targets that exactly match (not exceed) their main
        set, so they correctly produce zero flags (this is the lint's
        future-drift guard working as designed: a corrected item unflags on
        the next snapshot). The loose real-index assertion here is a lower,
        honest bound reflecting today's data: at least one genuine
        structural defect remains flagged elsewhere in the library.
        """
        index = build_index(DEFAULT_RAW_PATH)
        flagged = [item for item in index["items"] if item.get("lint_bookend_intensity")]
        assert len(flagged) >= 1
        assert len(flagged) < 50  # precision over recall -- never a huge share


# ---------------------------------------------------------------------------
# FIX 3 -- testing-week order: FTP test first
# ---------------------------------------------------------------------------

class TestTestingWeekFtpBeforeAnaerobic:
    def test_ftp_earliest_anaerobic_later_tue_off_sun_long(self):
        """Coach scenario: Tue off, Sun long ride -> FTP Test lands
        Thursday (earliest viable day), Anaerobic Test lands Saturday
        (>= 2 days later, chronologically after FTP, never on the long
        ride day, never on an off day)."""
        tracker = SeriesTracker()
        tracker.start_block()
        week = build_calendar_week(
            week_type="testing", phase="base", archetype="Time-Crunched",
            block_number=1, week_in_block=1, base_level=1, max_level=6,
            max_intensity=2, off_days=["Tue"], long_ride_day="Sun",
            hours_per_week=8, series_tracker=tracker, discipline="gravel",
        )
        by_day = {d["day"]: d for d in week["days"]}
        assert by_day["Thu"]["name"] == "FTP Test"
        assert by_day["Sat"]["name"] == "Anaerobic Test"
        day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ftp_idx = day_order.index("Thu")
        anaerobic_idx = day_order.index("Sat")
        assert ftp_idx < anaerobic_idx
        assert anaerobic_idx - ftp_idx >= 2

    def test_ftp_never_lands_after_anaerobic_across_schedules(self):
        """FTP date < anaerobic date always, regardless of off-day/long-day
        combination (never on the long ride day; off days respected)."""
        scenarios = [
            (["Mon"], "Sat"),
            (["Sun"], "Sat"),
            (["Wed"], "Sun"),
            ([], "Sat"),
        ]
        day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for off_days, long_day in scenarios:
            tracker = SeriesTracker()
            tracker.start_block()
            week = build_calendar_week(
                week_type="testing", phase="base", archetype="Time-Crunched",
                block_number=1, week_in_block=1, base_level=1, max_level=6,
                max_intensity=2, off_days=off_days, long_ride_day=long_day,
                hours_per_week=8, series_tracker=tracker, discipline="gravel",
            )
            names_by_day = {d["day"]: d["name"] for d in week["days"]}
            ftp_days = [d for d, name in names_by_day.items() if name == "FTP Test"]
            anaerobic_days = [d for d, name in names_by_day.items() if name == "Anaerobic Test"]
            assert ftp_days, f"no FTP Test placed for off_days={off_days}, long={long_day}"
            for d in off_days:
                assert names_by_day[d] == "OFF"
            assert names_by_day[long_day] != "FTP Test"
            assert names_by_day[long_day] != "Anaerobic Test"
            if anaerobic_days:
                assert day_order.index(ftp_days[0]) < day_order.index(anaerobic_days[0]), (
                    f"FTP ({ftp_days[0]}) not before Anaerobic ({anaerobic_days[0]}) "
                    f"for off_days={off_days}, long={long_day}")


# ---------------------------------------------------------------------------
# FIX 4 -- FTP retest spacing
# ---------------------------------------------------------------------------

class TestFtpRetestSpacing:
    def _generate_ftp_dates(self, tmp_path, weeks, race_date):
        import calculate_plan_dates as cpd
        from generate_athlete_package import generate_zwo_files

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 1)

        orig_datetime = cpd.datetime
        cpd.datetime = _FrozenDatetime
        try:
            plan_dates = cpd.calculate_plan_dates(race_date, plan_weeks=weeks)
        finally:
            cpd.datetime = orig_datetime

        profile = {
            "name": f"FTP Spacing {weeks}wk", "athlete_id": f"ftp-spacing-{weeks}wk",
            "target_race": {"name": "Sanity Gravel Race", "date": race_date,
                             "distance_miles": 60, "discipline": "gravel"},
            "fitness_markers": {"ftp_watts": 250, "weight_kg": 75},
            "weekly_availability": {"cycling_hours_target": 8},
            "schedule_constraints": {"preferred_long_day": "saturday",
                                      "preferred_off_days": ["sunday"]},
        }
        derived = {"plan_weeks": weeks, "ability_level": "Intermediate"}
        methodology = {"methodology_id": "polarized_80_20",
                        "configuration": {"intensity_distribution": {"z2": 0.80, "z4": 0.15, "z5": 0.05}}}

        athlete_dir = tmp_path / f"ftp-spacing-{weeks}wk"
        (athlete_dir / "workouts").mkdir(parents=True)
        generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
        manifest = generate_zwo_files.last_naming_manifest
        ftp_recs = [rec for rec in manifest.values()
                    if "FTP_Test" in str(rec.get("filename_stem", ""))]
        dates = sorted({datetime.strptime(rec["date"], "%Y-%m-%d") for rec in ftp_recs})
        return dates

    def test_eight_week_plan_gets_exactly_one_test(self, tmp_path):
        dates = self._generate_ftp_dates(tmp_path, 8, "2026-03-21")
        assert len(dates) == 1

    def test_twelve_week_plan_tests_at_least_five_weeks_apart(self, tmp_path):
        dates = self._generate_ftp_dates(tmp_path, 12, "2026-05-16")
        assert len(dates) >= 2
        for earlier, later in zip(dates, dates[1:]):
            assert (later - earlier).days >= 35, (
                f"retest gap {(later - earlier).days} days < 5 weeks: {dates}")

    def test_sixteen_plus_week_plan_all_gaps_at_least_five_weeks(self, tmp_path):
        dates = self._generate_ftp_dates(tmp_path, 18, "2026-06-20")
        assert len(dates) >= 2
        for earlier, later in zip(dates, dates[1:]):
            assert (later - earlier).days >= 35, (
                f"retest gap {(later - earlier).days} days < 5 weeks: {dates}")


# ---------------------------------------------------------------------------
# FIX 5 -- "Endurance Blocks" display-name honesty
# ---------------------------------------------------------------------------

class TestEnduranceBlocksNameHonesty:
    def test_flat_single_block_structure_drops_blocks_word(self):
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 65)]),
            _block([_leaf(8100, "active", 65)]),
            _block([_leaf(600, "coolDown", 50, 65)]),
        ]}
        resolution = {"name_base": "Endurance Blocks", "library_key": "endurance_with_work",
                      "structure": structure}
        assert _library_display_name(resolution) == "Endurance"

    def test_real_block_variation_keeps_blocks_word(self):
        """The coach's authored 'Endurance - Blocks' items alternate real
        30-35min blocks with 10min pieces between -- multiple main-content
        elements -- and must render unchanged."""
        structure = {"structure": [
            _block([_leaf(600, "warmUp", 50, 65)]),
            _block([_leaf(1800, "active", 65)]),
            _block([_leaf(600, "active", 55)]),
            _block([_leaf(1800, "active", 65)]),
            _block([_leaf(600, "coolDown", 65, 45)]),
        ]}
        resolution = {"name_base": "Endurance - Blocks", "library_key": "endurance_with_work",
                      "structure": structure}
        assert _library_display_name(resolution) == "Endurance - Blocks"

    @requires_real_dump
    def test_real_endurance_blocks_ladder_item_renders_without_blocks_word(self):
        import json
        raw = json.loads(DEFAULT_RAW_PATH.read_text(encoding="utf-8"))
        target = None
        for library in raw.values():
            for item in library.get("items", []):
                if item.get("itemName", "").startswith("Endurance Blocks - 6"):
                    target = item
                    break
        assert target is not None, "fixture item 'Endurance Blocks - 6' not found in real dump"
        resolution = {"name_base": "Endurance Blocks", "library_key": "endurance_with_work",
                      "structure": target["structure"]}
        assert _library_display_name(resolution) == "Endurance"
