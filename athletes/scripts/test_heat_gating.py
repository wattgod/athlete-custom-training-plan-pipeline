#!/usr/bin/env python3
"""
Heat-gating tests (heat-gating SPEC deliverable H5).

Covers three layers:
  1. heat_classifier.py — the vendored §3-contract classifier (unit tests,
     real-fixture smoke tests that skip cleanly when the sibling race repos
     are absent).
  2. generate_athlete_package.py — cue injection obeys the classified
     register (low drops cues entirely; high/moderate/unknown keep them with
     register-specific framing) within the concentrated 2-week window.
  3. training_guide_builder.py — the standalone Heat Training section renders
     all four registers, and the Altitude/Women's cross-references point at
     it correctly.

Reference: docs/research/heat-training-gating.md (research doc),
gravel-god-training-plans/specs/heat-gating/SPEC.md (H5).

NOTE (flagged for the parent spec owner): generate_zwo_files has TWO render
paths. The block-builder path (the PRIMARY path for nearly all plans today)
never had heat-cue injection at all, before or after this change — it
`continue`s straight to file write without touching the cue code. Only days
that DEFER to the legacy template path (FTP test days, race day, B-race
opener/easy days) reach the register-gated cue injection fixed here. That
mirrors the SPEC's own line-number audit (:2329/:2386, both inside the
legacy path) — this deliverable did not expand scope to add cue injection to
the block-builder path, which would be a much larger change. Tests below
force a 4-week plan (window = weeks 1-2, and week 1 always gets an FTP test,
which is a defer-to-legacy day) to exercise the fixed code deterministically.
"""

import sys
import tempfile
from pathlib import Path
from datetime import date, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from calculate_plan_dates import calculate_plan_dates
import generate_athlete_package as gap
import heat_classifier as hc


# ---------------------------------------------------------------------------
# 1. heat_classifier.py — the §3-contract classifier
# ---------------------------------------------------------------------------

GRAVEL_REPO = Path(__file__).resolve().parent.parent.parent.parent / "gravel-race-automation" / "race-data"
ROAD_REPO = Path(__file__).resolve().parent.parent.parent.parent / "road-race-automation" / "race-data"


class TestHeatClassifierSyntheticContract:
    """Contract behavior on synthetic race dicts — independent of real data
    drifting over time."""

    def test_raam_rule_high_regardless_of_cold_mix(self):
        race = {"climate": {
            "description": "Riders face 110F desert heat and freezing 10,000ft mountain passes "
                            "in the same continuous effort.",
        }}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "high"
        assert "RAAM" in r["reason"] or "95" in r["reason"]

    def test_oetztaler_rule_dampens_to_moderate(self):
        race = {"climate": {
            "description": "Valleys warm to 30C in the afternoon, but the summit pass near "
                            "freezing wind chill stays cold all day.",
        }}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "moderate"

    def test_primary_alone_never_establishes_high(self):
        """climate.primary is a keyword supplement only (Pomerode lesson) —
        a primary/description contradiction forces unknown, not high."""
        race = {"climate": {
            "primary": "Hot",
            "description": "Typically mild, cool spring weather with rain likely.",
        }}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "unknown"
        assert "contradiction" in r["reason"]

    def test_no_usable_prose_is_unknown_never_high(self):
        r = hc.classify_race_dict({})
        assert r["heat_risk"] == "unknown"

    def test_negation_is_respected(self):
        race = {"climate": {"description": "This race is not hot; expect cool, wet conditions."}}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] != "high"

    def test_modality_downgrades_to_moderate_not_high(self):
        race = {"climate": {"description": "In a record year it can occasionally get hot, "
                                            "but conditions are usually mild."}}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] != "high"

    def test_idiom_not_counted_as_heat_evidence(self):
        race = {"climate": {"description": "The field always goes out hot from the gun, "
                                            "then settles into a cool, steady rhythm."}}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] != "high"

    def test_gravel_nested_race_weather_field(self):
        race = {
            "climate": {},
            "guide_variables": {"race_weather": "Typically 90-98F with high humidity"},
        }
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "high"

    def test_declared_avg_temp_f_numeric(self):
        race = {"climate": {"overview": "Warm, humid summer conditions.", "avg_temp_f": 75}}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "moderate"

    def test_low_register_cold_dominant(self):
        race = {"climate": {
            "description": "Cool spring conditions with rain likely.",
            "challenges": ["Spring cool", "Rain possible"],
        }}
        r = hc.classify_race_dict(race)
        assert r["heat_risk"] == "low"

    def test_manual_override_beats_classifier(self, tmp_path, monkeypatch):
        overrides = tmp_path / "heat_overrides.json"
        overrides.write_text('{"the-rift": "high"}')
        monkeypatch.setattr(hc, "_override_paths", lambda: [overrides])
        r = hc.classify_heat_risk("the-rift", discipline="gravel")
        assert r["heat_risk"] == "high"
        assert r["reason"] == "manual override"

    def test_result_shape_always_has_evidence_and_reason(self):
        r = hc.classify_race_dict({"climate": {"description": "Hot and humid, typically 90-95F"}})
        assert set(r.keys()) == {"heat_risk", "evidence", "reason"}
        assert isinstance(r["evidence"], list)
        assert isinstance(r["reason"], str) and r["reason"]


class TestHeatClassifierRealFixtures:
    """Smoke tests against real race-data profiles (H1's fixture list).
    Skips cleanly when the sibling race repos aren't present."""

    @pytest.mark.parametrize("slug,discipline,expected", [
        ("unbound-200", "gravel", "high"),
        ("race-across-america", "gravel", "high"),
        ("the-rift", "gravel", "low"),
        ("battenkill", "gravel", "low"),
        ("mid-south", "gravel", "moderate"),
        ("otztaler-radmarathon", "gravel", "moderate"),
    ])
    def test_gravel_fixtures(self, slug, discipline, expected):
        if not GRAVEL_REPO.exists():
            pytest.skip("gravel-race-automation not present (sibling repo)")
        if not (GRAVEL_REPO / f"{slug}.json").exists():
            pytest.skip(f"{slug}.json not present in gravel-race-automation")
        r = hc.classify_heat_risk(slug, discipline=discipline)
        assert r["heat_risk"] == expected, r["reason"]

    def test_helsinki_unknown(self):
        if not ROAD_REPO.exists():
            pytest.skip("road-race-automation not present (sibling repo)")
        if not (ROAD_REPO / "helsinki-gran-fondo.json").exists():
            pytest.skip("helsinki-gran-fondo.json not present in road-race-automation")
        r = hc.classify_heat_risk("helsinki-gran-fondo", discipline="road")
        assert r["heat_risk"] == "unknown"

    def test_unknown_race_id_is_unknown_not_high(self):
        r = hc.classify_heat_risk("this-race-does-not-exist-anywhere", discipline="gravel")
        assert r["heat_risk"] == "unknown"


# ---------------------------------------------------------------------------
# 2. generate_athlete_package.py — cue injection register + window
# ---------------------------------------------------------------------------

def _minimal_profile_and_dates(plan_weeks=4):
    """4-week plan: window = weeks 1-2 (total-3..total-2, clamped), and week 1
    always carries an FTP test (a defer-to-legacy day) — the only
    deterministic way to land a legacy-path day inside the cue window without
    reverse-engineering the block-builder's phase boundaries."""
    race = date.today() + timedelta(weeks=plan_weeks)
    race += timedelta(days=(5 - race.weekday()) % 7)  # next Saturday
    plan_dates = calculate_plan_dates(race.isoformat(), plan_weeks=plan_weeks)
    profile = {
        'name': 'Test Athlete', 'athlete_id': 'test-athlete',
        'target_race': {'name': 'Test Race', 'date': race.isoformat(),
                         'distance_miles': 100, 'race_id': 'test-race'},
        'preferred_days': {
            'monday': {'availability': 'rest'},
            'tuesday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 90},
            'wednesday': {'availability': 'limited', 'is_key_day_ok': False, 'max_duration_min': 45},
            'thursday': {'availability': 'rest'},
            'friday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 60},
            'saturday': {'availability': 'available', 'is_long_day': True, 'is_key_day_ok': True, 'max_duration_min': 240},
            'sunday': {'availability': 'available', 'is_key_day_ok': True, 'max_duration_min': 120},
        },
        'fitness_markers': {'ftp_watts': 250, 'weight_kg': 75},
        'weekly_availability': {'cycling_hours_target': 10},
        'schedule_constraints': {'preferred_long_day': 'saturday', 'preferred_off_days': ['monday', 'thursday']},
    }
    derived = {'tier': 'finisher', 'ability_level': 'Intermediate',
               'plan_weeks': plan_dates.get('plan_weeks', plan_weeks), 'race_date': race.isoformat()}
    methodology = {
        'selected_methodology': 'polarized', 'score': 85,
        'configuration': {'key_workouts': ['Intervals', 'Long_Ride'],
                           'intensity_distribution': {'z2': 0.80, 'z4': 0.15, 'z5': 0.05}},
    }
    return profile, plan_dates, methodology, derived


def _generate(monkeypatch, heat_risk, exclude_hard_types=True):
    """Generate a full 4-week plan's ZWO files under a forced heat_risk
    register. exclude_hard_types=False isolates the register/window wiring
    from the (separately tested, in TestHeatCueHardDayExclusion) hard-day
    exclusion — the only day the legacy cue-injection code reliably reaches
    in a block-builder-driven plan is the week-1 FTP test, which is itself
    excluded (assessment day, sol finding P2). Forcing the exclusion set
    empty here proves the register/window plumbing is wired correctly
    without conflating it with which specific days are eligible."""
    monkeypatch.setattr(gap, "classify_heat_risk",
                         lambda *a, **k: {"heat_risk": heat_risk, "evidence": [], "reason": "test"})
    if exclude_hard_types:
        pass
    else:
        monkeypatch.setattr(gap, "_HEAT_CUE_EXCLUDED_TYPES", set())
    profile, plan_dates, methodology, derived = _minimal_profile_and_dates()
    with tempfile.TemporaryDirectory() as tmp:
        athlete_dir = Path(tmp) / 'test-athlete'
        athlete_dir.mkdir()
        files = gap.generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
        bodies = {Path(f).name: Path(f).read_text() for f in files}
    return bodies


class TestCueInjectionRegisters:
    def test_low_risk_produces_zero_heat_cues(self, monkeypatch):
        bodies = _generate(monkeypatch, "low", exclude_hard_types=False)
        hits = [name for name, body in bodies.items() if "HEAT" in body]
        assert hits == [], f"'low' register must drop cues entirely, found in: {hits}"

    def test_high_risk_produces_required_framing(self, monkeypatch):
        bodies = _generate(monkeypatch, "high", exclude_hard_types=False)
        hits = [body for body in bodies.values() if "HEAT ACCLIMATION" in body]
        assert hits, "expected at least one heat cue for 'high' register"
        assert any("REQUIRED" in body for body in hits)
        assert not any("free fitness" in body.lower() for body in hits)

    def test_moderate_risk_produces_recommended_framing(self, monkeypatch):
        bodies = _generate(monkeypatch, "moderate", exclude_hard_types=False)
        hits = [body for body in bodies.values() if "HEAT ACCLIMATION" in body]
        assert hits, "expected at least one heat cue for 'moderate' register"
        assert any("RECOMMENDED" in body for body in hits)

    def test_unknown_risk_produces_conditional_framing(self, monkeypatch):
        bodies = _generate(monkeypatch, "unknown", exclude_hard_types=False)
        hits = [body for body in bodies.values() if "HEAT ACCLIMATION" in body]
        assert hits, "expected at least one heat cue for 'unknown' register"
        assert any("IF YOUR RACE RUNS HOT" in body for body in hits)

    def test_absent_field_falls_back_to_unknown_register(self, monkeypatch):
        """A malformed/absent classification result must degrade to the
        conditional 'unknown' framing, never silently to 'high'."""
        monkeypatch.setattr(gap, "classify_heat_risk", lambda *a, **k: {})
        monkeypatch.setattr(gap, "_HEAT_CUE_EXCLUDED_TYPES", set())
        profile, plan_dates, methodology, derived = _minimal_profile_and_dates()
        with tempfile.TemporaryDirectory() as tmp:
            athlete_dir = Path(tmp) / 'test-athlete'
            athlete_dir.mkdir()
            files = gap.generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
            bodies = [Path(f).read_text() for f in files]
        hits = [b for b in bodies if "HEAT ACCLIMATION" in b]
        assert hits and any("IF YOUR RACE RUNS HOT" in b for b in hits)

    def test_ftp_test_day_never_gets_a_heat_cue_in_real_plan(self, monkeypatch):
        """Regression for the sol-flagged safety contradiction: the ONE day
        the legacy cue path reliably reaches in a real (block-builder-
        driven) plan is the week-1 FTP test. It must never carry a heat
        cue — the guide's own safety line says never stack heat on a hard
        day, and FTP_Test is a max-effort assessment, not a normal session.
        This test does NOT force-empty the exclusion set — it exercises the
        real, shipped behavior end-to-end."""
        bodies = _generate(monkeypatch, "high", exclude_hard_types=True)
        ftp_bodies = [body for name, body in bodies.items() if 'FTP_Test' in name]
        assert ftp_bodies, "expected at least one FTP_Test file in a 4-week plan"
        assert not any("HEAT ACCLIMATION" in b for b in ftp_bodies)


class TestHeatCueHardDayExclusion:
    """_heat_cue_eligible: register/window can say yes, but a hard/
    intensity or assessment workout type must still veto the cue (sol P2 —
    'never stack a heat session on a hard training day')."""

    @pytest.mark.parametrize("workout_type", sorted(gap._HEAT_CUE_EXCLUDED_TYPES))
    def test_hard_and_assessment_types_never_eligible(self, workout_type):
        assert gap._heat_cue_eligible(workout_type, "high", 9, 12) is False

    @pytest.mark.parametrize("workout_type", ["Endurance", "Openers", "Recovery", "Long_Ride"])
    def test_easy_and_normal_types_eligible_when_register_and_window_allow(self, workout_type):
        assert gap._heat_cue_eligible(workout_type, "high", 9, 12) is True

    def test_low_register_vetoes_regardless_of_type(self):
        assert gap._heat_cue_eligible("Endurance", "low", 9, 12) is False

    def test_outside_window_vetoes_regardless_of_type(self):
        assert gap._heat_cue_eligible("Endurance", "high", 1, 12) is False


class TestHeatCueWindow:
    def test_window_is_total_minus_3_to_total_minus_2(self):
        assert gap._in_heat_cue_window(9, 12) is True
        assert gap._in_heat_cue_window(10, 12) is True
        assert gap._in_heat_cue_window(8, 12) is False
        assert gap._in_heat_cue_window(11, 12) is False

    def test_window_clamped_for_short_plans(self):
        # 4-week plan: window clamps to weeks 1-2, never goes to 0 or negative
        assert gap._in_heat_cue_window(1, 4) is True
        assert gap._in_heat_cue_window(2, 4) is True
        assert gap._in_heat_cue_window(3, 4) is False

    def test_cue_body_never_none_for_any_register(self):
        for register in ("high", "moderate", "low", "unknown", "garbage-value"):
            body = gap._heat_cue_body(register)
            assert body and "HEAT ACCLIMATION" in body


# ---------------------------------------------------------------------------
# 3. training_guide_builder.py — standalone Heat Training section
# ---------------------------------------------------------------------------

class TestGuideHeatSection:
    def test_all_four_registers_render_with_correct_label(self):
        from training_guide_builder import _section_heat_training
        expectations = {
            "high": "REQUIRED",
            "moderate": "RECOMMENDED",
            "low": "OPTIONAL",
            "unknown": "CHECK YOUR RACE",
        }
        for register, label in expectations.items():
            html = _section_heat_training("Test Race", register, plan_duration=12, section_num=14)
            assert f"HEAT TRAINING: {label}" in html, f"missing {label} framing for {register}"
            assert "Heat Training" in html

    def test_low_register_uses_mixed_evidence_framing_not_free_fitness(self):
        from training_guide_builder import _section_heat_training
        html = _section_heat_training("Test Race", "low", plan_duration=12, section_num=14)
        assert "mixed" in html.lower()
        assert "free fitness" not in html.lower()
        assert "5-8%" not in html  # the retired universal-benefit claim

    def test_window_text_matches_generator_window(self):
        from training_guide_builder import _section_heat_training
        html = _section_heat_training("Test Race", "high", plan_duration=12, section_num=14)
        assert "WEEKS 9-10" in html  # total-3..total-2 for a 12-week plan

    def test_altitude_crossover_mention_is_register_aware(self):
        from training_guide_builder import _section_altitude_training
        race_data = {"race_metadata": {"start_elevation_feet": 9000, "avg_elevation_feet": 9500}}
        hot_html = _section_altitude_training(race_data, "Leadville", 0, "high", section_num=15)
        cool_html = _section_altitude_training(race_data, "Leadville", 0, "low", section_num=15)
        assert "Heat Training block" in hot_html
        assert "isn't required prep" in cool_html
        # Neither register keeps the old unconditional "5-8% performance improvements" claim
        assert "5-8% performance" not in hot_html
        assert "5-8% performance" not in cool_html

    def test_altitude_section_no_full_heat_protocol_duplicate(self):
        """The full 10-14 day heat protocol data-card must live ONLY in the
        standalone Heat Training section, not duplicated inside Altitude."""
        from training_guide_builder import _section_altitude_training
        race_data = {"race_metadata": {"start_elevation_feet": 9000, "avg_elevation_feet": 9500}}
        html = _section_altitude_training(race_data, "Leadville", 0, "high", section_num=15)
        assert "10-14 DAY HEAT PROTOCOL" not in html

    def test_women_section_points_at_heat_training_not_altitude(self):
        from training_guide_builder import _section_women_specific
        profile = {"demographics": {"weight_lbs": 140}}
        html = _section_women_specific(profile, {}, "Test Race", section_num=16, discipline="gravel")
        assert "See the Heat Training section" in html
        assert "See the Altitude Training section" not in html

    def test_section_titles_include_heat_training(self):
        from training_guide_builder import _build_section_titles
        profile = {"demographics": {"sex": "male", "age": 30}}
        titles = _build_section_titles(profile, {})
        title_names = [t for _, t in titles]
        assert "Heat Training" in title_names
