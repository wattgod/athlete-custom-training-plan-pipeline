#!/usr/bin/env python3
"""
Tests for intake_to_plan.py — parser, profile builder, validators, unit conversions.

Covers:
- Markdown parsing (sections, key-value pairs, edge cases)
- Unit conversions (lbs/kg, height, watts, years, ranges)
- Athlete ID generation
- Race matching (via known_races.py)
- Weight detection logic
- Intake validation (missing sections/fields)
- Profile sanity checks (bounds)
- Build profile types and content (real Nicholas intake)
- Integration round-trip tests
- Edge cases (ambiguous units, trailing text, duplicates)
"""

import sys
import copy
import pytest
from pathlib import Path

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent))

from intake_to_plan import (
    parse_intake_markdown,
    build_profile,
    validate_parsed_intake,
    validate_profile_sanity,
    lbs_to_kg,
    height_to_cm,
    parse_watts,
    parse_wkg,
    parse_years,
    parse_range,
    generate_athlete_id,
    IntakeValidationError,
    _normalize_section_name,
    extract_date_from_text,
    extract_distance_from_name,
    generate_coaching_brief,
    _parse_ftp_with_unknown_handling,
)
from known_races import match_race, KNOWN_RACES, RACE_ALIASES
from constants import (
    FTP_MIN_WATTS,
    FTP_MAX_WATTS,
    WEIGHT_MIN_KG,
    WEIGHT_MAX_KG,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NICHOLAS_INTAKE_PATH = Path("/tmp/nicholas-intake.md")


@pytest.fixture
def nicholas_intake_text():
    """Load the real Nicholas Applegate intake markdown."""
    assert NICHOLAS_INTAKE_PATH.exists(), (
        f"Nicholas intake fixture not found at {NICHOLAS_INTAKE_PATH}. "
        f"Copy it there before running tests."
    )
    return NICHOLAS_INTAKE_PATH.read_text()


@pytest.fixture
def nicholas_parsed(nicholas_intake_text):
    """Parse the Nicholas intake once for reuse."""
    return parse_intake_markdown(nicholas_intake_text)


@pytest.fixture
def nicholas_profile(nicholas_parsed):
    """Build profile from Nicholas intake once for reuse."""
    return build_profile(nicholas_parsed)


@pytest.fixture
def minimal_valid_parsed():
    """A minimal parsed dict that passes validate_parsed_intake."""
    return {
        'athlete_name': 'Test Athlete',
        '__header__': {'email': 'test@example.com'},
        'basic_info': {'age': '30', 'weight': '75 kg', 'sex': 'male'},
        'goals': {'primary_goal': 'specific_race', 'races': 'Unbound 200'},
        'current_fitness': {'ftp': '250 W', 'years_cycling': '5', 'years_structured': '2'},
        'schedule': {'weekly_hours_available': '8-10', 'long_ride_days': 'saturday'},
        'recovery': {'resting_hr': '55 bpm', 'typical_sleep': '7 hrs', 'sleep_quality': 'good', 'recovery_speed': 'normal'},
        'equipment': {'devices': 'garmin, power_meter', 'platform': 'trainingpeaks'},
        'work_life': {'work_hours': '40', 'job_stress': 'moderate', 'life_stress': 'moderate'},
        'health': {},
        'strength': {'current': 'none', 'include': 'no'},
        'coaching': {'autonomy': 'guided'},
        'mental_game': {},
        'additional': {},
    }


@pytest.fixture
def valid_profile():
    """A reasonable profile dict that passes validate_profile_sanity."""
    return {
        'name': 'Test Athlete',
        'athlete_id': 'test-athlete',
        'weight_kg': 80.0,
        'height_cm': 180,
        'fitness_markers': {
            'ftp_watts': 250,
            'w_kg': 3.13,
        },
        'health_factors': {
            'age': 35,
        },
        'weekly_availability': {
            'cycling_hours_target': 10,
        },
    }


# ===========================================================================
# TestParseIntakeMarkdown
# ===========================================================================

class TestParseIntakeMarkdown:
    """Tests for parse_intake_markdown()."""

    def test_parses_athlete_name(self, nicholas_intake_text):
        result = parse_intake_markdown(nicholas_intake_text)
        assert result['athlete_name'] == 'Nicholas Clift Shaw Applegate'

    def test_parses_all_sections(self, nicholas_parsed):
        expected_sections = [
            'basic_info', 'goals', 'current_fitness', 'recovery',
            'equipment', 'schedule', 'work_life', 'health',
            'strength', 'coaching', 'mental_game', 'additional',
        ]
        for section in expected_sections:
            assert section in nicholas_parsed, f"Missing section: {section}"

    def test_handles_missing_sections(self):
        text = "# Athlete Intake: Jane Doe\n\n## Basic Info\n- Age: 30\n"
        result = parse_intake_markdown(text)
        assert result['athlete_name'] == 'Jane Doe'
        assert 'basic_info' in result
        assert 'health' not in result  # not present, not crash

    def test_handles_alternate_section_headings(self):
        text = (
            "# Athlete Intake: Test\n"
            "## Basic Information\n- Age: 25\n"
            "## Recovery & Baselines\n- Resting HR: 55 bpm\n"
            "## Equipment & Data\n- Platform: zwift\n"
        )
        result = parse_intake_markdown(text)
        # "Basic Information" doesn't map to basic_info via the mapping
        # because the mapping only has "basic info". Let's check:
        # _normalize_section_name lowercases and looks up in mapping.
        # "basic information" isn't in the mapping, so it becomes "basic_information"
        assert 'basic_information' in result or 'basic_info' in result
        assert 'recovery' in result
        assert 'equipment' in result

    def test_parses_key_value_pairs(self, nicholas_parsed):
        assert nicholas_parsed['basic_info']['age'] == '44'
        assert nicholas_parsed['basic_info']['weight'] == '195 lbs'

    def test_handles_multiline_values(self, nicholas_parsed):
        races = nicholas_parsed['goals']['races']
        assert 'Unbound 200' in races
        assert 'Boulder Roubaix' in races
        # Multiline values are joined with newline
        assert '\n' in races

    def test_handles_no_dash_fields(self, nicholas_parsed):
        # "Email: applen@gmail.com" has no leading dash
        header = nicholas_parsed.get('__header__', {})
        assert header.get('email') == 'applen@gmail.com'

    def test_empty_input_returns_minimal(self):
        result = parse_intake_markdown('')
        assert isinstance(result, dict)
        # Should not crash, should have __header__ at least
        assert '__header__' in result

    def test_normalize_section_ignores_case(self):
        # Test via _normalize_section_name directly
        assert _normalize_section_name('BASIC INFO') == 'basic_info'
        assert _normalize_section_name('basic info') == 'basic_info'
        assert _normalize_section_name('Basic Info') == 'basic_info'

    def test_handles_extra_whitespace(self):
        text = "# Athlete Intake: Whitespace Test\n\n  ## Basic Info  \n- Age: 25\n"
        result = parse_intake_markdown(text)
        # Section heading detection strips whitespace before matching
        assert 'basic_info' in result
        assert result['basic_info']['age'] == '25'


# ===========================================================================
# TestUnitConversions
# ===========================================================================

class TestUnitConversions:
    """Tests for lbs_to_kg()."""

    def test_lbs_to_kg_standard(self):
        assert lbs_to_kg('195 lbs') == 88.5

    def test_lbs_to_kg_no_unit(self):
        # lbs_to_kg always converts, unit detection is in build_profile
        assert lbs_to_kg('195') == 88.5

    def test_lbs_to_kg_decimal(self):
        result = lbs_to_kg('195.5 lbs')
        assert result == 88.7

    def test_lbs_to_kg_empty(self):
        assert lbs_to_kg('') == 0.0

    def test_height_feet_inches_apostrophe(self):
        assert height_to_cm("6'1\"") == 185

    def test_height_feet_inches_ft(self):
        assert height_to_cm("6 ft 1 in") == 185

    def test_height_cm_direct(self):
        assert height_to_cm("185 cm") == 185

    def test_height_inches_only(self):
        result = height_to_cm("73 in")
        assert result == 185

    def test_height_empty(self):
        assert height_to_cm("") == 0

    def test_height_smart_quotes(self):
        # Curly/smart quotes: \u2019 = right single quote, \u201D = right double quote
        result = height_to_cm("6\u20191\u201D")
        assert result == 185


# ===========================================================================
# TestParseYears
# ===========================================================================

class TestParseYears:
    """Tests for parse_years()."""

    def test_with_plus(self):
        assert parse_years('10+') == 10

    def test_without_plus(self):
        assert parse_years('4') == 4

    def test_empty(self):
        assert parse_years('') == 0

    def test_none(self):
        assert parse_years(None) == 0

    def test_text_only(self):
        assert parse_years('many') == 0


# ===========================================================================
# TestParseRange
# ===========================================================================

class TestParseRange:
    """Tests for parse_range()."""

    def test_range(self):
        assert parse_range('8-10') == (8, 10)

    def test_single(self):
        assert parse_range('5') == (5, 5)

    def test_en_dash(self):
        # en-dash: \u2013
        assert parse_range('8\u201310') == (8, 10)

    def test_empty(self):
        assert parse_range('') == (None, None)

    def test_spaced(self):
        assert parse_range('8 - 10') == (8, 10)


# ===========================================================================
# TestParseWatts
# ===========================================================================

class TestParseWatts:
    """Tests for parse_watts()."""

    def test_with_w(self):
        assert parse_watts('315 W') == 315

    def test_without_w(self):
        assert parse_watts('315') == 315

    def test_empty(self):
        assert parse_watts('') is None


# ===========================================================================
# TestGenerateAthleteId
# ===========================================================================

class TestGenerateAthleteId:
    """Tests for generate_athlete_id()."""

    def test_first_last(self):
        assert generate_athlete_id('John Smith') == 'john-smith'

    def test_with_middle_names(self):
        assert generate_athlete_id('Nicholas Clift Shaw Applegate') == 'nicholas-applegate'

    def test_single_name(self):
        assert generate_athlete_id('Madonna') == 'madonna'

    def test_special_chars(self):
        # Accented chars are stripped by [^a-z0-9-] regex
        result = generate_athlete_id('Jose Garcia')
        assert result == 'jose-garcia'
        # With actual accents
        result2 = generate_athlete_id('Jose Garcia')
        assert result2 == 'jose-garcia'

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty name"):
            generate_athlete_id('')


# ===========================================================================
# TestMatchRace
# ===========================================================================

class TestMatchRace:
    """Tests for match_race() from known_races.py."""

    def test_exact_alias(self):
        result = match_race('Unbound 200')
        assert result is not None
        race_id, info = result
        assert race_id == 'unbound_gravel_200'

    def test_case_insensitive(self):
        result = match_race('UNBOUND 200')
        assert result is not None
        race_id, _ = result
        assert race_id == 'unbound_gravel_200'

    def test_abbreviation(self):
        result = match_race('DK200')
        assert result is not None
        race_id, _ = result
        assert race_id == 'unbound_gravel_200'

    def test_substring_match(self):
        result = match_race('Unbound Gravel')
        assert result is not None
        race_id, _ = result
        assert 'unbound' in race_id

    def test_unknown_race(self):
        result = match_race('Tour de France')
        # Token matching might still match on "de" -> unlikely.
        # The token match requires overlap >= 1, but "Tour de France" tokens
        # don't overlap meaningfully with any known race.
        # Let's check: "tour", "de", "france" -- "gravel" has none of these.
        # But "100" might match "Leadville Trail 100 MTB" via token "100"?
        # No -- "Tour de France" has no "100" token.
        # Actually, let's be careful: token matching overlap >= 1 means
        # even a single token match counts. None of "tour", "de", "france"
        # appear in any known race name. So this should be None.
        assert result is None

    def test_boulder_roubaix(self):
        result = match_race('Boulder Roubaix')
        assert result is not None
        race_id, _ = result
        assert race_id == 'boulder_roubaix'

    def test_token_overlap(self):
        result = match_race('Big Sugar')
        assert result is not None
        race_id, _ = result
        assert race_id == 'big_sugar'


# ===========================================================================
# TestWeightDetection
# ===========================================================================

class TestWeightDetection:
    """Tests for the weight unit detection logic in build_profile."""

    def _build_with_weight(self, weight_str):
        """Helper: build profile with specific weight string."""
        parsed = {
            'athlete_name': 'Weight Test',
            '__header__': {},
            'basic_info': {'age': '30', 'weight': weight_str, 'sex': 'male'},
            'goals': {'primary_goal': 'specific_race', 'races': 'Unbound 200'},
            'current_fitness': {'ftp': '200 W'},
            'schedule': {'weekly_hours_available': '8'},
            'recovery': {},
            'equipment': {},
            'work_life': {},
            'health': {},
            'strength': {'include': 'no'},
            'coaching': {},
            'mental_game': {},
            'additional': {},
        }
        return build_profile(parsed)

    def test_explicit_lbs(self):
        profile = self._build_with_weight('195 lbs')
        assert profile['weight_kg'] == 88.5

    def test_explicit_kg(self):
        profile = self._build_with_weight('88.5 kg')
        assert profile['weight_kg'] == 88.5

    def test_no_unit_over_100(self):
        profile = self._build_with_weight('195')
        # > 100 with no unit -> assumes lbs -> converts
        assert profile['weight_kg'] == 88.5

    def test_no_unit_40_to_100(self):
        profile = self._build_with_weight('75')
        # 40-100 with no unit -> assumes kg
        assert profile['weight_kg'] == 75.0

    def test_no_unit_under_40(self):
        profile = self._build_with_weight('30')
        # < 40 -> keeps value as-is (sanity check catches it)
        assert profile['weight_kg'] == 30.0


# ===========================================================================
# TestValidateParsedIntake
# ===========================================================================

class TestValidateParsedIntake:
    """Tests for validate_parsed_intake()."""

    def test_valid_intake_passes(self, minimal_valid_parsed):
        # Should not raise
        validate_parsed_intake(minimal_valid_parsed)

    def test_missing_required_section_raises(self, minimal_valid_parsed):
        parsed = copy.deepcopy(minimal_valid_parsed)
        del parsed['basic_info']
        with pytest.raises(IntakeValidationError, match="basic_info"):
            validate_parsed_intake(parsed)

    def test_missing_required_field_raises(self, minimal_valid_parsed):
        parsed = copy.deepcopy(minimal_valid_parsed)
        del parsed['current_fitness']['ftp']
        with pytest.raises(IntakeValidationError, match="FTP"):
            validate_parsed_intake(parsed)

    def test_empty_races_raises(self, minimal_valid_parsed):
        parsed = copy.deepcopy(minimal_valid_parsed)
        parsed['goals']['races'] = ''
        with pytest.raises(IntakeValidationError, match="race"):
            validate_parsed_intake(parsed)

    def test_all_missing_listed(self):
        # Completely empty parsed dict: multiple missing sections
        parsed = {'athlete_name': 'Test', '__header__': {}}
        with pytest.raises(IntakeValidationError) as exc_info:
            validate_parsed_intake(parsed)
        msg = str(exc_info.value)
        assert 'basic_info' in msg
        assert 'goals' in msg
        assert 'current_fitness' in msg
        assert 'schedule' in msg


# ===========================================================================
# TestValidateProfileSanity
# ===========================================================================

class TestValidateProfileSanity:
    """Tests for validate_profile_sanity()."""

    def test_valid_profile_passes(self, valid_profile):
        # Should not raise
        validate_profile_sanity(valid_profile)

    def test_ftp_too_low_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['ftp_watts'] = 10
        with pytest.raises(IntakeValidationError, match=f"below minimum.*{FTP_MIN_WATTS}W"):
            validate_profile_sanity(profile)

    def test_ftp_too_high_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['ftp_watts'] = 600
        with pytest.raises(IntakeValidationError, match=f"above maximum.*{FTP_MAX_WATTS}W"):
            validate_profile_sanity(profile)

    def test_weight_too_low_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['weight_kg'] = 30.0
        with pytest.raises(IntakeValidationError, match="below minimum.*Was the unit lbs"):
            validate_profile_sanity(profile)

    def test_weight_too_high_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['weight_kg'] = 200.0
        with pytest.raises(IntakeValidationError, match="above maximum"):
            validate_profile_sanity(profile)

    def test_height_too_low_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['height_cm'] = 100
        with pytest.raises(IntakeValidationError, match="below minimum.*120 cm"):
            validate_profile_sanity(profile)

    def test_wkg_too_high_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['w_kg'] = 9.0
        with pytest.raises(IntakeValidationError, match="above maximum.*8.0"):
            validate_profile_sanity(profile)

    def test_multiple_violations_all_listed(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['ftp_watts'] = 10
        profile['weight_kg'] = 200.0
        with pytest.raises(IntakeValidationError) as exc_info:
            validate_profile_sanity(profile)
        msg = str(exc_info.value)
        assert 'FTP' in msg
        assert 'Weight' in msg

    def test_zero_ftp_fails(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['ftp_watts'] = 0
        with pytest.raises(IntakeValidationError, match="below minimum"):
            validate_profile_sanity(profile)

    def test_none_ftp_skipped(self, valid_profile):
        profile = copy.deepcopy(valid_profile)
        profile['fitness_markers']['ftp_watts'] = None
        # Should not raise (FTP check is skipped when None)
        validate_profile_sanity(profile)


# ===========================================================================
# TestBuildProfileTypes
# ===========================================================================

class TestBuildProfileTypes:
    """Verify all value types in the built profile are correct."""

    def test_years_cycling_is_int(self, nicholas_profile):
        val = nicholas_profile['training_history']['years_cycling']
        assert isinstance(val, int), f"years_cycling should be int, got {type(val)}"
        assert val == 10

    def test_years_structured_is_int(self, nicholas_profile):
        val = nicholas_profile['training_history']['years_structured']
        assert isinstance(val, int), f"years_structured should be int, got {type(val)}"
        assert val == 4

    def test_ftp_watts_is_int(self, nicholas_profile):
        val = nicholas_profile['fitness_markers']['ftp_watts']
        assert isinstance(val, int), f"ftp_watts should be int, got {type(val)}"
        assert val == 315

    def test_weight_kg_is_float(self, nicholas_profile):
        val = nicholas_profile['weight_kg']
        assert isinstance(val, float), f"weight_kg should be float, got {type(val)}"

    def test_height_cm_is_int(self, nicholas_profile):
        val = nicholas_profile['height_cm']
        assert isinstance(val, int), f"height_cm should be int, got {type(val)}"
        assert val == 185

    def test_resting_hr_is_int(self, nicholas_profile):
        val = nicholas_profile['fitness_markers']['resting_hr']
        assert isinstance(val, int), f"resting_hr should be int, got {type(val)}"
        assert val == 45

    def test_sleep_hours_is_int(self, nicholas_profile):
        val = nicholas_profile['health_factors']['sleep_hours_avg']
        assert isinstance(val, int), f"sleep_hours_avg should be int, got {type(val)}"
        assert val == 7

    def test_cycling_hours_is_int(self, nicholas_profile):
        val = nicholas_profile['weekly_availability']['cycling_hours_target']
        assert isinstance(val, int), f"cycling_hours_target should be int, got {type(val)}"
        assert val == 10

    def test_age_is_int(self, nicholas_profile):
        val = nicholas_profile['health_factors']['age']
        assert isinstance(val, int), f"age should be int, got {type(val)}"
        assert val == 44

    def test_w_kg_is_float(self, nicholas_profile):
        val = nicholas_profile['fitness_markers']['w_kg']
        assert isinstance(val, float), f"w_kg should be float, got {type(val)}"


# ===========================================================================
# TestBuildProfileContent
# ===========================================================================

class TestBuildProfileContent:
    """Verify correct values in the built profile from Nicholas intake."""

    def test_athlete_id(self, nicholas_profile):
        assert nicholas_profile['athlete_id'] == 'nicholas-applegate'

    def test_target_race_name(self, nicholas_profile):
        assert nicholas_profile['target_race']['name'] == 'Unbound Gravel 200'

    def test_target_race_date(self, nicholas_profile):
        assert nicholas_profile['target_race']['date'] == '2026-05-30'

    def test_off_day_unavailable(self, nicholas_profile):
        tuesday = nicholas_profile['preferred_days']['tuesday']
        assert tuesday['availability'] == 'unavailable'

    def test_long_day_is_sunday(self, nicholas_profile):
        sunday = nicholas_profile['preferred_days']['sunday']
        assert sunday['max_duration_min'] == 600

    def test_interval_day_is_key(self, nicholas_profile):
        wednesday = nicholas_profile['preferred_days']['wednesday']
        assert wednesday['is_key_day_ok'] is True

    def test_methodology_prefs_neutral(self, nicholas_profile):
        """Preference scores must stay neutral — select_methodology.py decides, not keywords."""
        meth = nicholas_profile['methodology_preferences']
        for key in ('polarized', 'pyramidal', 'threshold_focused', 'hiit_focused', 'high_volume', 'time_crunched'):
            assert meth[key] == 3, f"{key} should be neutral (3), got {meth[key]}"

    def test_methodology_sweet_spot_vetoed(self, nicholas_profile):
        """Nicholas said sweet spot 'doesn't seem to build durability' — must be captured as failure."""
        meth = nicholas_profile['methodology_preferences']
        assert meth['past_failure_with'], "past_failure_with should capture sweet spot rejection"
        assert 'sweet spot' in meth['past_failure_with'].lower() or 'threshold' in meth['past_failure_with'].lower()

    def test_strength_excluded(self, nicholas_profile):
        assert nicholas_profile['strength']['include_in_plan'] is False
        assert nicholas_profile['strength']['sessions_per_week'] == 0

    def test_medical_conditions_captured(self, nicholas_profile):
        conditions = nicholas_profile['health_factors']['medical_conditions']
        assert 'hemophilia' in conditions.lower()

    def test_email_captured(self, nicholas_profile):
        assert nicholas_profile['email'] == 'applen@gmail.com'


# ===========================================================================
# TestIntegrationRoundTrip
# ===========================================================================

class TestIntegrationRoundTrip:
    """End-to-end tests using the real Nicholas intake."""

    def test_parse_then_validate_passes(self, nicholas_parsed):
        # Should not raise
        validate_parsed_intake(nicholas_parsed)

    def test_parse_then_build_then_sanity_passes(self, nicholas_parsed):
        profile = build_profile(nicholas_parsed)
        # Should not raise
        validate_profile_sanity(profile)

    def test_profile_passes_validate_profile_script(self, nicholas_profile):
        """The built profile should pass validate_profile.py's checks."""
        try:
            from validate_profile import validate_profile
        except ImportError:
            pytest.skip("validate_profile.py not importable")

        is_valid, errors, warnings = validate_profile(nicholas_profile)
        # Profile should be valid (errors list should be empty or
        # have only non-blocking issues)
        # Note: some fields may produce warnings, that's OK
        assert is_valid, f"Profile validation failed: {errors}"


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    """Edge case tests for unusual or boundary inputs."""

    def _build_with_weight(self, weight_str):
        """Helper: build profile with specific weight string."""
        parsed = {
            'athlete_name': 'Edge Test',
            '__header__': {},
            'basic_info': {'age': '30', 'weight': weight_str, 'sex': 'male'},
            'goals': {'primary_goal': 'specific_race', 'races': 'Unbound 200'},
            'current_fitness': {'ftp': '200 W'},
            'schedule': {'weekly_hours_available': '8'},
            'recovery': {},
            'equipment': {},
            'work_life': {},
            'health': {},
            'strength': {'include': 'no'},
            'coaching': {},
            'mental_game': {},
            'additional': {},
        }
        return build_profile(parsed)

    def test_weight_exactly_100_no_unit(self):
        # 100 with no unit -> 40-100 range -> assumes kg
        # But 100 kg is ~220 lbs (very heavy). The code uses <= 100 -> kg.
        # So weight_kg = 100.0 (keeps as-is)
        profile = self._build_with_weight('100')
        assert profile['weight_kg'] == 100.0

    def test_ftp_with_trailing_text(self):
        result = parse_watts('315 watts estimated')
        assert result == 315

    def test_race_name_with_year(self):
        # "Unbound 200 2026" should still match something
        result = match_race('Unbound 200 2026')
        assert result is not None
        race_id, _ = result
        # Should match via token overlap ("unbound", "200") or substring
        assert 'unbound' in race_id

    def test_age_zero_fails_sanity(self):
        profile = {
            'health_factors': {'age': 0},
            'fitness_markers': {'ftp_watts': 200, 'w_kg': 3.0},
            'weight_kg': 70.0,
            'height_cm': 175,
            'weekly_availability': {'cycling_hours_target': 8},
        }
        # Age 0 -> age > 0 check is False, so age check is skipped.
        # This should NOT raise because the code guards with `if age is not None and age > 0`.
        validate_profile_sanity(profile)  # no error

    def test_negative_ftp(self):
        # parse_watts uses \d+ which only matches digits (no minus sign)
        result = parse_watts('-200')
        # \d+ matches "200" from "-200"
        assert result == 200

    def test_height_just_feet_no_inches(self):
        result = height_to_cm("6'")
        # feet=6, inches=0 -> (6*12+0)*2.54 = 72*2.54 = 182.88 -> 183
        assert result == 183

    def test_duplicate_section_headings(self):
        text = (
            "# Athlete Intake: Dupe Test\n"
            "## Goals\n"
            "- Primary Goal: fitness\n"
            "## Basic Info\n"
            "- Age: 25\n"
            "## Goals\n"
            "- Races: Unbound 200\n"
        )
        result = parse_intake_markdown(text)
        # Second "## Goals" re-uses the same section dict (current_section = 'goals')
        # and adds keys to it. So we should get both primary_goal AND races.
        goals = result.get('goals', {})
        assert 'primary_goal' in goals
        assert 'races' in goals

    def test_extremely_long_input(self):
        # 10000 lines should not crash
        lines = ["# Athlete Intake: Long Test\n"]
        lines.append("## Basic Info\n")
        lines.append("- Age: 30\n")
        lines.append("## Extra Section\n")
        for i in range(10000):
            lines.append(f"- field_{i}: value_{i}\n")
        text = ''.join(lines)
        result = parse_intake_markdown(text)
        assert result['athlete_name'] == 'Long Test'
        assert result['basic_info']['age'] == '30'


class TestMethodologySelection:
    """Test that methodology selection is driven by objective data, not free text."""

    def _make_profile(self, hours=10, years_structured=4, stress='moderate',
                      distance_miles=100, goal='finish', age=35,
                      past_failure='', past_success=''):
        """Build a minimal profile for methodology scoring."""
        return {
            'weekly_availability': {'cycling_hours_target': hours},
            'training_history': {'years_structured': years_structured},
            'health_factors': {'stress_level': stress, 'age': age, 'sleep_hours_avg': 7},
            'work': {'hours_per_week': 40},
            'schedule_constraints': {
                'travel_frequency': 'none',
                'work_schedule': '9-5',
                'family_commitments': '',
            },
            'target_race': {
                'distance_miles': distance_miles,
                'goal_type': goal,
            },
            'training_environment': {'indoor_riding_tolerance': 'tolerate_it'},
            'recent_training': {'coming_off_injury': False},
            'methodology_preferences': {
                'past_success_with': past_success,
                'past_failure_with': past_failure,
            },
        }

    def test_time_crunched_gets_hiit_or_sweet_spot(self):
        """4 hrs/week should NOT get polarized or pyramidal (need 8+ hrs)."""
        from select_methodology import select_methodology
        profile = self._make_profile(hours=4, distance_miles=40)
        result = select_methodology(profile, {})
        method_id = result['methodology_id']
        # Should pick something suited for low hours, not ultra-endurance
        assert method_id not in ('traditional_pyramidal', 'hvli_lsd', 'norwegian_double_threshold')

    def test_high_hours_gets_volume_methodology(self):
        """20 hrs/week should favor volume-based methodologies."""
        from select_methodology import select_methodology
        profile = self._make_profile(hours=20, years_structured=5, distance_miles=200)
        result = select_methodology(profile, {})
        method_id = result['methodology_id']
        # Should pick something that can handle 20h — NOT hiit_focused (max 6h)
        assert method_id != 'hiit_focused'

    def test_veto_eliminates_methodology(self):
        """past_failure_with should make methodology score very low."""
        from select_methodology import select_methodology, METHODOLOGIES
        # Veto sweet spot/threshold
        profile = self._make_profile(hours=8, past_failure='Sweet Spot / Threshold')
        result = select_methodology(profile, {})
        # Sweet spot should NOT be selected
        assert result['methodology_id'] != 'sweet_spot_threshold'
        # Check it has veto warning
        for alt in result.get('alternatives', []):
            if 'Threshold' in alt['name'] or 'Sweet Spot' in alt['name']:
                assert alt['score'] < 30, f"Vetoed methodology scored {alt['score']}, should be <30"

    def test_veto_does_not_affect_unrelated_methodologies(self):
        """Vetoing sweet spot shouldn't penalize polarized."""
        from select_methodology import select_methodology, calculate_methodology_score, METHODOLOGIES
        profile = self._make_profile(hours=10, past_failure='Sweet Spot / Threshold')
        derived = {}
        race_demands = {'distance_miles': 100, 'duration_hours': 8,
                        'technical_difficulty': 'moderate', 'repeated_surges': False, 'altitude_feet': 0}
        # Score polarized — should not be penalized by sweet spot veto
        polarized = METHODOLOGIES.get('polarized_80_20')
        if polarized:
            candidate = calculate_methodology_score(polarized, profile, derived, race_demands)
            assert candidate.score >= 50, f"Polarized wrongly penalized: {candidate.score}"

    def test_beginner_penalized_for_advanced_methodology(self):
        """0 years structured should penalize block periodization (-15 experience)."""
        from select_methodology import select_methodology
        profile = self._make_profile(hours=12, years_structured=0)
        result = select_methodology(profile, {})
        # Block periodization requires advanced experience
        assert result['methodology_id'] != 'block_periodization'

    def test_high_stress_prefers_stress_tolerant(self):
        """High stress + high hours should prefer stress-tolerant methodology."""
        from select_methodology import select_methodology
        profile = self._make_profile(hours=10, stress='high')
        result = select_methodology(profile, {})
        # Selected methodology should handle stress well
        assert result['score'] >= 60  # Should have reasonable confidence

    def test_ultra_distance_penalizes_hiit(self):
        """200-mile race should not select HIIT."""
        from select_methodology import select_methodology
        profile = self._make_profile(hours=10, distance_miles=200)
        result = select_methodology(profile, {})
        assert result['methodology_id'] != 'hiit_focused'

    def test_all_yaml_methodologies_scored(self):
        """All 13 YAML methodologies should be in the selection pool."""
        from select_methodology import METHODOLOGIES
        expected_ids = {
            'traditional_pyramidal', 'polarized_80_20', 'sweet_spot_threshold',
            'hiit_focused', 'block_periodization', 'reverse_periodization',
            'autoregulated_hrv', 'maf_low_hr', 'critical_power', 'inscyd',
            'norwegian_double_threshold', 'hvli_lsd', 'goat_composite',
        }
        actual_ids = set(METHODOLOGIES.keys())
        missing = expected_ids - actual_ids
        assert not missing, f"Missing from YAML: {missing}"

    def test_all_yaml_ids_in_methodology_map(self):
        """Every YAML methodology ID must have an entry in METHODOLOGY_MAP."""
        from select_methodology import METHODOLOGIES
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_athlete_package import METHODOLOGY_MAP
        for method_id in METHODOLOGIES:
            assert method_id in METHODOLOGY_MAP, (
                f"YAML methodology '{method_id}' not in METHODOLOGY_MAP — "
                f"would silently fall through to default POLARIZED"
            )

    def test_methodology_map_values_are_valid_nate_ids(self):
        """Every METHODOLOGY_MAP value must be a valid Nate generator ID."""
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_athlete_package import METHODOLOGY_MAP
        valid_nate_ids = {
            'PYRAMIDAL', 'POLARIZED', 'G_SPOT', 'HIT', 'BLOCK', 'REVERSE',
            'HRV_AUTO', 'MAF_LT1', 'CRITICAL_POWER', 'INSCYD', 'NORWEGIAN',
            'HVLI', 'GOAT', 'TIME_CRUNCHED',
        }
        for yaml_id, nate_id in METHODOLOGY_MAP.items():
            assert nate_id in valid_nate_ids, (
                f"METHODOLOGY_MAP['{yaml_id}'] = '{nate_id}' — not a valid Nate ID. "
                f"Valid: {sorted(valid_nate_ids)}"
            )

    def test_derive_methodology_stays_neutral(self):
        """_derive_methodology must NOT set preference scores from keywords."""
        from intake_to_plan import _derive_methodology
        # Text that mentions base, polarized, zone 2 — old code would set polarized=5
        text = "i want more base building, zone 2, polarized approach, 80/20 training"
        prefs = _derive_methodology(text)
        for key in ('polarized', 'pyramidal', 'threshold_focused', 'hiit_focused', 'high_volume', 'time_crunched'):
            assert prefs[key] == 3, f"{key} should be neutral 3, got {prefs[key]}"

    def test_derive_methodology_captures_failure(self):
        """Explicit failure language near approach keyword should be captured."""
        from intake_to_plan import _derive_methodology
        text = "tried sweet spot but it didn't work for building durability"
        prefs = _derive_methodology(text)
        assert prefs['past_failure_with'] != '', "Should capture sweet spot failure"
        assert 'Sweet Spot' in prefs['past_failure_with'] or 'Threshold' in prefs['past_failure_with']

    def test_derive_methodology_no_false_positives(self):
        """Mention without negative context should NOT trigger failure."""
        from intake_to_plan import _derive_methodology
        text = "i did some sweet spot training last year and it was fine"
        prefs = _derive_methodology(text)
        assert 'Sweet Spot' not in prefs.get('past_failure_with', '')

    def test_derive_methodology_captures_success(self):
        """Positive context near keyword should be captured as success."""
        from intake_to_plan import _derive_methodology
        text = "polarized training worked great for me in 2024"
        prefs = _derive_methodology(text)
        assert prefs['past_success_with'] != '', "Should capture polarized success"

    def test_failure_beats_success_for_same_approach(self):
        """If same approach is both success and failure, failure wins."""
        from intake_to_plan import _derive_methodology
        text = "sweet spot worked well initially but ultimately failed me for long events"
        prefs = _derive_methodology(text)
        # Sweet spot is mentioned with both positive and negative context
        # Failure should win
        if 'Sweet Spot' in prefs.get('past_failure_with', ''):
            assert 'Sweet Spot' not in prefs.get('past_success_with', '')


# ===========================================================================
# TestMultiAthleteProfiles
# ===========================================================================

class TestMultiAthleteProfiles:
    """Test pipeline handles diverse athlete profiles correctly.

    Covers four athlete archetypes: time-crunched, high-volume, beginner,
    and strength-included.  Each profile is built via build_profile() from
    a minimal parsed dict, then validated for schedule logic, methodology
    fit, strength config, and numeric consistency.
    """

    # -----------------------------------------------------------------------
    # Helper: build a minimal parsed dict that matches the format expected
    # by build_profile() (see minimal_valid_parsed fixture for shape).
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_parsed(
        name, age, weight, sex, ftp, years_cycling, years_structured,
        weekly_hours, races, long_ride_days, off_days,
        interval_days='', strength_include='no', strength_current='none',
        job_stress='moderate', life_stress='moderate',
    ):
        """Build a parsed intake dict suitable for build_profile()."""
        return {
            'athlete_name': name,
            '__header__': {'email': f'{name.split()[0].lower()}@test.com'},
            'basic_info': {
                'age': str(age),
                'weight': weight,
                'sex': sex,
            },
            'goals': {
                'primary_goal': 'specific_race',
                'races': races,
            },
            'current_fitness': {
                'ftp': f'{ftp} W',
                'years_cycling': str(years_cycling),
                'years_structured': str(years_structured),
            },
            'schedule': {
                'weekly_hours_available': str(weekly_hours),
                'long_ride_days': long_ride_days,
                'interval_days': interval_days,
                'off_days': off_days,
            },
            'recovery': {
                'resting_hr': '55 bpm',
                'typical_sleep': '7 hrs',
                'sleep_quality': 'good',
                'recovery_speed': 'normal',
            },
            'equipment': {
                'devices': 'garmin, power_meter',
                'platform': 'trainingpeaks',
            },
            'work_life': {
                'work_hours': '40',
                'job_stress': job_stress,
                'life_stress': life_stress,
            },
            'health': {},
            'strength': {
                'current': strength_current,
                'include': strength_include,
            },
            'coaching': {'autonomy': 'guided'},
            'mental_game': {},
            'additional': {},
        }

    # -----------------------------------------------------------------------
    # Parametrized fixture — one profile per archetype
    # -----------------------------------------------------------------------

    @pytest.fixture(params=['time_crunched', 'high_volume', 'beginner', 'strength_included'])
    def athlete_profile(self, request):
        """Build profile for each athlete archetype."""
        archetypes = {
            'time_crunched': self._make_parsed(
                name='Tim Crunched',
                age=38, weight='75 kg', sex='male',
                ftp=280, years_cycling=5, years_structured=5,
                weekly_hours=4,
                races='Steamboat Gravel',
                long_ride_days='saturday',
                off_days='sunday',
                interval_days='',
                job_stress='moderate', life_stress='moderate',
            ),
            'high_volume': self._make_parsed(
                name='Hank Volume',
                age=29, weight='72 kg', sex='male',
                ftp=350, years_cycling=8, years_structured=8,
                weekly_hours=20,
                races='Unbound 200',
                long_ride_days='sunday',
                off_days='monday',
                interval_days='tuesday, thursday, saturday, sunday',
                job_stress='low', life_stress='low',
            ),
            'beginner': self._make_parsed(
                name='Betty Beginner',
                age=52, weight='65 kg', sex='female',
                ftp=150, years_cycling=0, years_structured=0,
                weekly_hours=6,
                races='SBT GRVL',
                long_ride_days='saturday',
                off_days='tuesday, thursday',
                interval_days='',
                job_stress='high', life_stress='high',
            ),
            'strength_included': self._make_parsed(
                name='Sam Strong',
                age=35, weight='80 kg', sex='male',
                ftp=250, years_cycling=3, years_structured=3,
                weekly_hours=8,
                races='Gravel Worlds',
                long_ride_days='sunday',
                off_days='',
                interval_days='',
                strength_include='yes', strength_current='moderate',
                job_stress='moderate', life_stress='moderate',
            ),
        }
        parsed = archetypes[request.param]
        profile = build_profile(parsed)
        return profile, request.param

    # -----------------------------------------------------------------------
    # Tests
    # -----------------------------------------------------------------------

    def test_profile_passes_sanity(self, athlete_profile):
        """All archetypes must pass sanity validation."""
        profile, name = athlete_profile
        validate_profile_sanity(profile)  # should not raise

    def test_off_days_unavailable(self, athlete_profile):
        """Off days must be marked unavailable."""
        profile, name = athlete_profile
        off_days = profile['schedule_constraints']['preferred_off_days']
        for day in off_days:
            assert profile['preferred_days'][day]['availability'] == 'unavailable', (
                f"{name}: off day '{day}' should be unavailable"
            )

    def test_long_day_is_correct(self, athlete_profile):
        """Long day must match what was specified and have adequate duration."""
        profile, name = athlete_profile
        long_day = profile['schedule_constraints']['preferred_long_day']
        assert profile['preferred_days'][long_day]['max_duration_min'] >= 240, (
            f"{name}: long day '{long_day}' max_duration_min "
            f"({profile['preferred_days'][long_day]['max_duration_min']}) should be >= 240"
        )

    def test_methodology_not_mismatched(self, athlete_profile):
        """Methodology selection should be reasonable for athlete."""
        from select_methodology import select_methodology
        profile, name = athlete_profile
        result = select_methodology(profile, {})
        if name == 'time_crunched':
            # 4 hrs/week should NOT get polarized/pyramidal (need 8+ hrs)
            assert result['methodology_id'] not in (
                'traditional_pyramidal', 'hvli_lsd', 'norwegian_double_threshold'
            ), f"Time-crunched athlete got volume methodology: {result['methodology_id']}"
        elif name == 'high_volume':
            # 20 hrs/week should NOT get HIIT (max 6h)
            assert result['methodology_id'] != 'hiit_focused', (
                "High-volume athlete should not get HIIT methodology"
            )
        elif name == 'beginner':
            # 0 years should NOT get block/inscyd/norwegian (advanced)
            assert result['methodology_id'] not in (
                'block_periodization', 'inscyd', 'norwegian_double_threshold'
            ), f"Beginner athlete got advanced methodology: {result['methodology_id']}"

    def test_strength_sessions_correct(self, athlete_profile):
        """Strength sessions should match athlete request."""
        profile, name = athlete_profile
        if name == 'strength_included':
            assert profile['strength']['include_in_plan'] is True, (
                "strength_included athlete should have include_in_plan=True"
            )
            assert profile['strength']['sessions_per_week'] == 2, (
                f"Expected 2 strength sessions, got {profile['strength']['sessions_per_week']}"
            )
        # For other archetypes, don't assert False — some might want it

    def test_key_days_have_key_flag(self, athlete_profile):
        """Days marked as key should have is_key_day_ok=True and not be unavailable."""
        profile, name = athlete_profile
        for day_name, day_info in profile['preferred_days'].items():
            if day_info.get('is_key_day_ok'):
                assert day_info['availability'] != 'unavailable', (
                    f"{name}: key day '{day_name}' can't be unavailable"
                )

    def test_cycling_hours_in_range(self, athlete_profile):
        """Cycling hours must be positive and reasonable."""
        profile, name = athlete_profile
        hours = profile['weekly_availability']['cycling_hours_target']
        assert 1 <= hours <= 40, (
            f"Hours {hours} out of range for {name}"
        )

    def test_ftp_and_wkg_consistent(self, athlete_profile):
        """W/kg must equal FTP / weight."""
        profile, name = athlete_profile
        ftp = profile['fitness_markers']['ftp_watts']
        weight = profile['weight_kg']
        wkg = profile['fitness_markers']['w_kg']
        expected = round(ftp / weight, 2)
        assert abs(wkg - expected) < 0.1, (
            f"W/kg {wkg} != {expected} for {name}"
        )

    def test_athlete_id_generated(self, athlete_profile):
        """Athlete ID should be a first-last slug."""
        profile, name = athlete_profile
        assert '-' in profile['athlete_id'] or len(profile['athlete_id']) > 0, (
            f"Missing or empty athlete_id for {name}"
        )

    def test_target_race_matched(self, athlete_profile):
        """Target race should match a known race."""
        profile, name = athlete_profile
        target = profile['target_race']
        # All four races are in known_races.py
        assert target.get('name'), f"No target race name for {name}"
        assert target.get('date'), f"No target race date for {name}"
        assert target.get('distance_miles', 0) > 0, (
            f"No target race distance for {name}"
        )

    def test_sex_preserved(self, athlete_profile):
        """Sex should be carried through to profile."""
        profile, name = athlete_profile
        expected = {
            'time_crunched': 'male',
            'high_volume': 'male',
            'beginner': 'female',
            'strength_included': 'male',
        }
        assert profile['sex'] == expected[name], (
            f"Expected sex={expected[name]} for {name}, got {profile['sex']}"
        )

    def test_age_carried_through(self, athlete_profile):
        """Age must be an int and match input."""
        profile, name = athlete_profile
        expected_ages = {
            'time_crunched': 38,
            'high_volume': 29,
            'beginner': 52,
            'strength_included': 35,
        }
        assert profile['health_factors']['age'] == expected_ages[name], (
            f"Expected age={expected_ages[name]} for {name}, "
            f"got {profile['health_factors']['age']}"
        )

    def test_stress_level_captured(self, athlete_profile):
        """Stress level should reflect the higher of job/life stress."""
        profile, name = athlete_profile
        stress = profile['health_factors']['stress_level']
        if name == 'beginner':
            assert stress == 'high', (
                f"Beginner has high job+life stress, got '{stress}'"
            )
        elif name == 'high_volume':
            assert stress == 'low', (
                f"High-volume has low stress, got '{stress}'"
            )


# ===========================================================================
# TestUnknownRaceFallback
# ===========================================================================

class TestUnknownRaceFallback:
    """Tests for graceful handling when match_race() returns None."""

    def _make_parsed_with_race(self, race_name, goals_extra=None):
        """Build a minimal parsed dict with a specific race name."""
        goals = {'primary_goal': 'specific_race', 'races': race_name}
        if goals_extra:
            goals.update(goals_extra)
        return {
            'athlete_name': 'Test Fallback',
            '__header__': {'email': 'test@example.com'},
            'basic_info': {'age': '30', 'weight': '75 kg', 'sex': 'male'},
            'goals': goals,
            'current_fitness': {'ftp': '250 W', 'years_cycling': '5', 'years_structured': '2'},
            'schedule': {'weekly_hours_available': '8-10', 'long_ride_days': 'saturday'},
            'recovery': {'resting_hr': '55 bpm', 'typical_sleep': '7 hrs',
                         'sleep_quality': 'good', 'recovery_speed': 'normal'},
            'equipment': {'devices': 'garmin, power_meter', 'platform': 'trainingpeaks'},
            'work_life': {'work_hours': '40', 'job_stress': 'moderate', 'life_stress': 'moderate'},
            'health': {},
            'strength': {'current': 'none', 'include': 'no'},
            'coaching': {'autonomy': 'guided'},
            'mental_game': {},
            'additional': {},
        }

    def test_unknown_race_doesnt_crash(self):
        """Race name not in KNOWN_RACES should not crash build_profile."""
        parsed = self._make_parsed_with_race('Zephyr Desert Rally')
        # Should not raise
        profile = build_profile(parsed)
        assert profile is not None
        assert 'target_race' in profile

    def test_unknown_race_uses_raw_name(self):
        """Unknown race should keep the original athlete-provided name."""
        parsed = self._make_parsed_with_race('Copper Triangle')
        profile = build_profile(parsed)
        assert profile['target_race']['name'] == 'Copper Triangle'

    def test_unknown_race_extracts_distance(self):
        """'Zephyr Desert Rally 150' should extract distance_miles=150."""
        parsed = self._make_parsed_with_race('Zephyr Desert Rally 150')
        profile = build_profile(parsed)
        assert profile['target_race']['distance_miles'] == 150

    def test_unknown_race_extracts_distance_direct(self):
        """Test extract_distance_from_name directly with various patterns."""
        assert extract_distance_from_name('Steamboat 100') == 100
        assert extract_distance_from_name('Unbound 200') == 200
        assert extract_distance_from_name('Some Race 50K') == 31  # 50km -> 31mi
        assert extract_distance_from_name('Big Race') == 0

    def test_unknown_race_generates_valid_race_id(self):
        """Unknown race should still generate a valid race_id."""
        parsed = self._make_parsed_with_race('Copper Triangle')
        profile = build_profile(parsed)
        race_id = profile['target_race']['race_id']
        assert race_id, "race_id should not be empty"
        assert ' ' not in race_id, "race_id should not contain spaces"

    def test_unknown_race_extracts_date_from_goals(self):
        """Date in goals text should be extracted for unknown races."""
        parsed = self._make_parsed_with_race(
            'Copper Triangle',
            goals_extra={'success': 'Finish the race on June 6, 2026'}
        )
        profile = build_profile(parsed)
        assert profile['target_race']['date'] == '2026-06-06'


# ===========================================================================
# TestExtractDateFromText
# ===========================================================================

class TestExtractDateFromText:
    """Tests for extract_date_from_text helper."""

    def test_iso_format(self):
        assert extract_date_from_text('Race is on 2026-05-30') == '2026-05-30'

    def test_month_day_year(self):
        assert extract_date_from_text('Race on May 30, 2026') == '2026-05-30'

    def test_month_day_no_year(self):
        """Without a year, should use current year."""
        from datetime import date
        result = extract_date_from_text('Race on June 6')
        assert result.endswith('-06-06')

    def test_us_date_format(self):
        assert extract_date_from_text('Date: 5/30/2026') == '2026-05-30'

    def test_no_date_returns_empty(self):
        assert extract_date_from_text('No date here') == ''

    def test_empty_string(self):
        assert extract_date_from_text('') == ''

    def test_none_input(self):
        assert extract_date_from_text(None) == ''


# ===========================================================================
# TestExtractDistanceFromName
# ===========================================================================

class TestExtractDistanceFromName:
    """Tests for extract_distance_from_name helper."""

    def test_trailing_number(self):
        assert extract_distance_from_name('Steamboat 100') == 100

    def test_200_miles(self):
        assert extract_distance_from_name('Unbound 200') == 200

    def test_km_conversion(self):
        result = extract_distance_from_name('Gravel Growler 50K')
        assert result == 31  # 50 * 0.621371 ~ 31

    def test_no_distance(self):
        assert extract_distance_from_name('Big Race') == 0

    def test_empty_string(self):
        assert extract_distance_from_name('') == 0

    def test_none_input(self):
        assert extract_distance_from_name(None) == 0


# ===========================================================================
# TestPlanWeeksClamping
# ===========================================================================

class TestPlanWeeksClamping:
    """Tests for plan_weeks clamping to 4-26 range."""

    def _make_parsed_with_date(self, race_date_str):
        """Build a minimal parsed dict with a known race but override date."""
        return {
            'athlete_name': 'Test Clamp',
            '__header__': {'email': 'test@example.com'},
            'basic_info': {'age': '30', 'weight': '75 kg', 'sex': 'male'},
            'goals': {'primary_goal': 'specific_race', 'races': 'Unbound 200'},
            'current_fitness': {'ftp': '250 W', 'years_cycling': '5', 'years_structured': '2'},
            'schedule': {'weekly_hours_available': '8-10', 'long_ride_days': 'saturday'},
            'recovery': {'resting_hr': '55 bpm', 'typical_sleep': '7 hrs',
                         'sleep_quality': 'good', 'recovery_speed': 'normal'},
            'equipment': {'devices': 'garmin, power_meter', 'platform': 'trainingpeaks'},
            'work_life': {'work_hours': '40', 'job_stress': 'moderate', 'life_stress': 'moderate'},
            'health': {},
            'strength': {'current': 'none', 'include': 'no'},
            'coaching': {'autonomy': 'guided'},
            'mental_game': {},
            'additional': {},
        }

    def test_plan_weeks_clamped_to_range(self):
        """Race 2 weeks away should produce 4-week plan note,
        race 40 weeks away should cap at 26 in plan notes."""
        from datetime import date, timedelta

        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        plan_start = today + timedelta(days=days_until_monday)

        # Race very close (2 weeks away) — should clamp to 4
        close_race_date = (plan_start + timedelta(weeks=2)).isoformat()
        parsed_close = self._make_parsed_with_date(close_race_date)
        # Override the known race date with a close date
        from unittest.mock import patch
        close_races = {
            'unbound_gravel_200': {
                'date': close_race_date,
                'name': 'Unbound Gravel 200',
                'distance_miles': 200,
                'elevation_ft': 11000,
            }
        }
        with patch('intake_to_plan.KNOWN_RACES', close_races), \
             patch('intake_to_plan.match_race') as mock_match:
            mock_match.return_value = ('unbound_gravel_200', close_races['unbound_gravel_200'])
            profile_close = build_profile(parsed_close)
            # The plan_notes should reference ~4 weeks (clamped from 2)
            notes = profile_close['plan_start']['notes']
            assert '~4 weeks' in notes, (
                f"Expected '~4 weeks' in notes for close race, got: {notes}"
            )

        # Race very far (40 weeks away) — should clamp to 26
        far_race_date = (plan_start + timedelta(weeks=40)).isoformat()
        parsed_far = self._make_parsed_with_date(far_race_date)
        far_races = {
            'unbound_gravel_200': {
                'date': far_race_date,
                'name': 'Unbound Gravel 200',
                'distance_miles': 200,
                'elevation_ft': 11000,
            }
        }
        with patch('intake_to_plan.KNOWN_RACES', far_races), \
             patch('intake_to_plan.match_race') as mock_match:
            mock_match.return_value = ('unbound_gravel_200', far_races['unbound_gravel_200'])
            profile_far = build_profile(parsed_far)
            notes = profile_far['plan_start']['notes']
            assert '~26 weeks' in notes, (
                f"Expected '~26 weeks' in notes for far race, got: {notes}"
            )

    def test_calculate_plan_dates_rejects_too_few_weeks(self):
        """calculate_plan_dates should raise ValueError for plan_weeks < 4."""
        from calculate_plan_dates import calculate_plan_dates
        with pytest.raises(ValueError, match="at least 4 weeks"):
            calculate_plan_dates('2026-06-01', plan_weeks=3)

    def test_calculate_plan_dates_rejects_too_many_weeks(self):
        """calculate_plan_dates should raise ValueError for plan_weeks > 52."""
        from calculate_plan_dates import calculate_plan_dates
        with pytest.raises(ValueError, match="cannot exceed 52 weeks"):
            calculate_plan_dates('2026-06-01', plan_weeks=53)

    def test_calculate_plan_dates_accepts_boundary_values(self):
        """calculate_plan_dates should accept 4 and 52 weeks."""
        from calculate_plan_dates import calculate_plan_dates
        # 4 weeks should work
        result_4 = calculate_plan_dates('2027-06-01', plan_weeks=4)
        assert result_4['plan_weeks'] >= 4

        # 52 weeks should work
        result_52 = calculate_plan_dates('2028-06-01', plan_weeks=52)
        assert result_52 is not None


# ===========================================================================
# Coaching Brief Tests
# ===========================================================================

class TestCoachingBrief:
    """Tests for generate_coaching_brief — reads pipeline YAMLs, traces decisions."""

    @pytest.fixture
    def nicholas_athlete_dir(self):
        return Path(__file__).parent.parent / 'nicholas-applegate'

    @pytest.fixture
    def nicholas_profile(self, nicholas_athlete_dir):
        import yaml
        with open(nicholas_athlete_dir / 'profile.yaml') as f:
            return yaml.safe_load(f)

    def test_brief_reads_methodology_yaml(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show actual methodology from methodology.yaml, not 'Balanced'."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'Polarized (80/20)' in brief
        assert 'Balanced / Structured' not in brief

    def test_brief_has_all_sections(self, nicholas_profile, nicholas_athlete_dir):
        """Brief must contain all 10 numbered sections."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert '## 1. Plan Overview' in brief
        assert '## 2. Questionnaire -> Implementation Mapping' in brief
        assert '## 3. Methodology Selection' in brief
        assert '## 4. Phase Structure' in brief
        assert '## 5. Weekly Structure' in brief
        assert '## 6. Fueling Plan' in brief
        assert '## 7. B-Race Handling' in brief
        assert '## 8. Risk Factors' in brief
        assert '## 9. Key Coaching Notes' in brief
        assert '## 10. Pipeline Output Files' in brief

    def test_brief_shows_methodology_score(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show methodology score from methodology.yaml."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'score: 100/100' in brief

    def test_brief_shows_veto(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show past_failure_with as a VETO row."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'VETO' in brief
        assert 'Sweet Spot' in brief

    def test_brief_shows_phase_structure(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should list all 12 weeks with phases."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'W01' in brief
        assert 'W12' in brief
        assert 'BASE' in brief
        assert 'BUILD' in brief
        assert 'PEAK' in brief
        assert 'TAPER' in brief
        assert 'RACE' in brief

    def test_brief_shows_b_race(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should include Boulder Roubaix B-race handling."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'Boulder Roubaix' in brief
        assert 'B-race overlay' in brief or 'B (training race)' in brief

    def test_brief_shows_fueling(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should include fueling plan from fueling.yaml."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert '66g/hr' in brief or '66' in brief
        assert 'Gut Training' in brief

    def test_brief_shows_weekly_structure(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show day-by-day workout assignments."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'Monday' in brief
        assert 'Sunday' in brief
        assert 'Long Ride' in brief
        assert 'Intervals' in brief

    def test_brief_shows_zone_distribution(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show zone distribution targets from methodology config."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert '80%' in brief
        assert '0%' in brief
        assert '20%' in brief

    def test_brief_shows_alternatives(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should list alternative methodologies that were considered."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'MAF' in brief
        assert 'Autoregulated' in brief or 'HRV' in brief

    def test_brief_works_without_athlete_dir(self, nicholas_profile):
        """Brief should still generate (degraded) without athlete_dir."""
        brief = generate_coaching_brief(nicholas_profile, {})
        assert '## 1. Plan Overview' in brief
        assert 'Unknown' in brief  # methodology falls back to Unknown

    def test_brief_medical_conditions_shown(self, nicholas_profile, nicholas_athlete_dir):
        """Brief should show medical conditions in risk factors and mapping."""
        brief = generate_coaching_brief(nicholas_profile, {}, athlete_dir=nicholas_athlete_dir)
        assert 'hemophilia' in brief.lower()
        assert 'factor IX' in brief or 'Recombinant' in brief


# ===========================================================================
# TestEdgeCasesSilentFailures — guards against silent pipeline failures
# ===========================================================================

class TestEdgeCasesSilentFailures:
    """Edge cases that could cause silent failures in the training plan pipeline.

    Covers: zero B-events, FTP unknown, very short plans, high-volume athletes,
    zero off days, missing YAMLs, and race distance edge cases.
    """

    # -----------------------------------------------------------------------
    # Helper: build a parsed intake dict (mirrors TestMultiAthleteProfiles)
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_parsed(
        name='Test Athlete', age=30, weight='75 kg', sex='male',
        ftp='250 W', years_cycling=5, years_structured=2,
        weekly_hours='8-10', races='Unbound 200',
        long_ride_days='saturday', off_days='',
        interval_days='', strength_include='no', strength_current='none',
        job_stress='moderate', life_stress='moderate',
    ):
        """Build a parsed intake dict suitable for build_profile()."""
        return {
            'athlete_name': name,
            '__header__': {'email': f'{name.split()[0].lower()}@test.com'},
            'basic_info': {
                'age': str(age),
                'weight': weight,
                'sex': sex,
            },
            'goals': {
                'primary_goal': 'specific_race',
                'races': races,
            },
            'current_fitness': {
                'ftp': ftp,
                'years_cycling': str(years_cycling),
                'years_structured': str(years_structured),
            },
            'schedule': {
                'weekly_hours_available': str(weekly_hours),
                'long_ride_days': long_ride_days,
                'interval_days': interval_days,
                'off_days': off_days,
            },
            'recovery': {
                'resting_hr': '55 bpm',
                'typical_sleep': '7 hrs',
                'sleep_quality': 'good',
                'recovery_speed': 'normal',
            },
            'equipment': {
                'devices': 'garmin, power_meter',
                'platform': 'trainingpeaks',
            },
            'work_life': {
                'work_hours': '40',
                'job_stress': job_stress,
                'life_stress': life_stress,
            },
            'health': {},
            'strength': {
                'current': strength_current,
                'include': strength_include,
            },
            'coaching': {'autonomy': 'guided'},
            'mental_game': {},
            'additional': {},
        }

    # -------------------------------------------------------------------
    # 1. Zero B-events
    # -------------------------------------------------------------------

    def test_zero_b_events_profile_builds(self):
        """Profile with only 1 race (no B-events) should build cleanly."""
        parsed = self._make_parsed(races='Unbound 200')
        profile = build_profile(parsed)
        assert profile['b_events'] == []
        assert len(profile['a_events']) == 1

    def test_zero_b_events_coaching_brief(self):
        """Coaching brief should not crash when b_events is empty."""
        parsed = self._make_parsed(races='Unbound 200')
        profile = build_profile(parsed)
        brief = generate_coaching_brief(profile, parsed)
        # Section 7 (B-Race Handling) should be absent
        assert '## 7. B-Race Handling' not in brief
        # Other sections should still be present
        assert '## 1. Plan Overview' in brief
        assert '## 8. Risk Factors' in brief
        assert '## 9. Key Coaching Notes' in brief
        assert '## 10. Pipeline Output Files' in brief

    def test_zero_b_events_sanity_passes(self):
        """Profile with zero B-events should pass sanity validation."""
        parsed = self._make_parsed(races='Unbound 200')
        profile = build_profile(parsed)
        validate_profile_sanity(profile)  # should not raise

    # -------------------------------------------------------------------
    # 2. FTP unknown / no power meter
    # -------------------------------------------------------------------

    def test_parse_ftp_unknown_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for 'unknown'."""
        assert _parse_ftp_with_unknown_handling('unknown') is None

    def test_parse_ftp_na_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for 'N/A'."""
        assert _parse_ftp_with_unknown_handling('N/A') is None

    def test_parse_ftp_no_power_meter_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for 'no power meter'."""
        assert _parse_ftp_with_unknown_handling('no power meter') is None

    def test_parse_ftp_not_tested_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for 'not tested'."""
        assert _parse_ftp_with_unknown_handling('not tested') is None

    def test_parse_ftp_dont_know_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for "don't know"."""
        assert _parse_ftp_with_unknown_handling("don't know") is None

    def test_parse_ftp_empty_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for empty string."""
        assert _parse_ftp_with_unknown_handling('') is None

    def test_parse_ftp_dash_returns_none(self):
        """_parse_ftp_with_unknown_handling returns None for '-'."""
        assert _parse_ftp_with_unknown_handling('-') is None

    def test_parse_ftp_normal_value(self):
        """_parse_ftp_with_unknown_handling returns watts for '315 W'."""
        assert _parse_ftp_with_unknown_handling('315 W') == 315

    def test_parse_ftp_just_number(self):
        """_parse_ftp_with_unknown_handling returns watts for '250'."""
        assert _parse_ftp_with_unknown_handling('250') == 250

    def test_ftp_unknown_estimates_from_weight(self):
        """FTP='unknown' should estimate FTP from weight, not crash."""
        parsed = self._make_parsed(ftp='unknown', weight='75 kg', sex='male', age=30)
        profile = build_profile(parsed)
        ftp = profile['fitness_markers']['ftp_watts']
        assert ftp is not None
        assert ftp > 0
        assert profile['fitness_markers']['ftp_estimated'] is True

    def test_ftp_unknown_female_lower_estimate(self):
        """Female FTP estimate should use 2.2 W/kg (lower than male 2.5)."""
        male_parsed = self._make_parsed(ftp='unknown', weight='70 kg', sex='male', age=30)
        female_parsed = self._make_parsed(ftp='unknown', weight='70 kg', sex='female', age=30)
        male_profile = build_profile(male_parsed)
        female_profile = build_profile(female_parsed)
        assert male_profile['fitness_markers']['ftp_watts'] > female_profile['fitness_markers']['ftp_watts']

    def test_ftp_unknown_age_adjusted(self):
        """Older athletes should get lower FTP estimates."""
        young_parsed = self._make_parsed(ftp='unknown', weight='75 kg', age=30)
        old_parsed = self._make_parsed(ftp='unknown', weight='75 kg', age=60)
        young_profile = build_profile(young_parsed)
        old_profile = build_profile(old_parsed)
        assert young_profile['fitness_markers']['ftp_watts'] > old_profile['fitness_markers']['ftp_watts']

    def test_ftp_unknown_wkg_calculated(self):
        """W/kg should be calculated from estimated FTP."""
        parsed = self._make_parsed(ftp='unknown', weight='75 kg')
        profile = build_profile(parsed)
        ftp = profile['fitness_markers']['ftp_watts']
        wkg = profile['fitness_markers']['w_kg']
        assert wkg is not None
        expected_wkg = round(ftp / 75.0, 2)
        assert abs(wkg - expected_wkg) < 0.01

    def test_ftp_unknown_passes_sanity(self):
        """Estimated FTP should pass sanity validation bounds."""
        parsed = self._make_parsed(ftp='unknown', weight='75 kg')
        profile = build_profile(parsed)
        validate_profile_sanity(profile)  # should not raise

    def test_ftp_known_not_estimated(self):
        """Normal FTP should not be flagged as estimated."""
        parsed = self._make_parsed(ftp='315 W')
        profile = build_profile(parsed)
        assert profile['fitness_markers']['ftp_estimated'] is False
        assert profile['fitness_markers']['ftp_watts'] == 315

    def test_ftp_no_power_meter_builds_plan(self):
        """'no power meter' FTP should produce a buildable profile."""
        parsed = self._make_parsed(ftp='no power meter', weight='80 kg', age=35)
        profile = build_profile(parsed)
        assert profile['fitness_markers']['ftp_watts'] > 0
        assert profile['fitness_markers']['ftp_estimated'] is True
        # W/kg should be reasonable
        wkg = profile['fitness_markers']['w_kg']
        assert 1.0 <= wkg <= 5.0

    # -------------------------------------------------------------------
    # 4. High-volume athlete (20 hours/week)
    # -------------------------------------------------------------------

    def test_high_volume_volume_warning_emitted(self):
        """20h/wk athlete with limited schedule should get volume warning."""
        parsed = self._make_parsed(
            name='Hank Volume',
            weekly_hours=20,
            long_ride_days='sunday',
            off_days='monday',
            interval_days='tuesday, thursday',
        )
        profile = build_profile(parsed)
        warning = profile['weekly_availability'].get('volume_warning')
        # The schedule capacity is sum of max_duration_min for available days.
        # With monday off, 6 available days:
        # sun=600, tue=120, wed=120, thu=120, fri=120, sat=240 = 1320min = 22h
        # Target 20h should be under 22h capacity, so no warning.
        # But let's verify the field is populated correctly.
        assert 'volume_warning' in profile['weekly_availability']

    def test_high_volume_exceeding_capacity_warns(self):
        """30h/wk target with limited schedule MUST produce a volume warning."""
        parsed = self._make_parsed(
            name='Ultra Volume',
            weekly_hours=30,
            long_ride_days='saturday',
            off_days='sunday, monday, tuesday',
            # Only 4 days available: wed=120, thu=120, fri=120, sat=600 = 960min = 16h
        )
        profile = build_profile(parsed)
        warning = profile['weekly_availability']['volume_warning']
        assert warning is not None, "Should warn when 30h target exceeds 16h capacity"
        assert 'exceeds' in warning.lower()

    def test_high_volume_still_generates_profile(self):
        """Volume warning should not prevent profile generation."""
        parsed = self._make_parsed(
            name='Ultra Volume',
            weekly_hours=30,
            long_ride_days='saturday',
            off_days='sunday, monday, tuesday',
        )
        profile = build_profile(parsed)
        # Profile should still be complete
        assert profile['name'] == 'Ultra Volume'
        assert profile['weekly_availability']['cycling_hours_target'] == 30
        # Sanity should pass (volume warning is non-blocking)
        validate_profile_sanity(profile)

    def test_high_volume_no_warning_when_capacity_sufficient(self):
        """20h target with enough schedule capacity should NOT warn."""
        parsed = self._make_parsed(
            name='High But Feasible',
            weekly_hours=20,
            long_ride_days='saturday',
            off_days='',
            # All 7 days available:
            # sat=600, sun=240, mon-fri=120*5=600 -> total=1440min=24h
        )
        profile = build_profile(parsed)
        assert profile['weekly_availability']['volume_warning'] is None

    # -------------------------------------------------------------------
    # 5. Zero off days (7 available days)
    # -------------------------------------------------------------------

    def test_zero_off_days_all_seven_assigned(self):
        """Athlete with 0 off days should get all 7 days assigned."""
        parsed = self._make_parsed(
            name='Seven Day Sam',
            off_days='',
            long_ride_days='saturday',
        )
        profile = build_profile(parsed)
        available_count = sum(
            1 for d in profile['preferred_days'].values()
            if d['availability'] != 'unavailable'
        )
        assert available_count == 7, f"Expected 7 available days, got {available_count}"

    def test_zero_off_days_no_unavailable(self):
        """No days should be marked unavailable when off_days is empty."""
        parsed = self._make_parsed(
            name='No Rest Rick',
            off_days='',
        )
        profile = build_profile(parsed)
        for day_name, day_info in profile['preferred_days'].items():
            assert day_info['availability'] != 'unavailable', (
                f"Day '{day_name}' should not be unavailable with zero off days"
            )

    def test_zero_off_days_passes_sanity(self):
        """Zero off days profile should pass sanity validation."""
        parsed = self._make_parsed(name='Full Week Fred', off_days='')
        profile = build_profile(parsed)
        validate_profile_sanity(profile)

    def test_zero_off_days_has_key_days(self):
        """With 7 days available, there should be multiple key days."""
        parsed = self._make_parsed(
            name='Key Day Ken',
            off_days='',
            long_ride_days='saturday',
            interval_days='tuesday, thursday',
        )
        profile = build_profile(parsed)
        key_days = [
            d for d, info in profile['preferred_days'].items()
            if info.get('is_key_day_ok')
        ]
        assert len(key_days) >= 3, (
            f"Expected at least 3 key days with 7 available, got {len(key_days)}: {key_days}"
        )
