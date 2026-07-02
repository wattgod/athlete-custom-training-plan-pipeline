#!/usr/bin/env python3
"""
Tests for fuzzy race matching + honest unknown-race fallback.

Covers:
- match_race_scored(): exact/alias behavior unchanged, case/punctuation
  variants, conservative fuzzy matching (threshold + margin), near-misses
- The old silent unbound_gravel_200 default is DEAD in every path
  (build_profile, create_profile_from_form)
- Generic race profile (athlete's own inputs, neutral demands, no
  fabricated course data) for unmatched races
- Coach-side loudness: UNMATCHED RACE block in the coaching brief and
  pre-delivery checklist race-match section
- Athlete-facing invisibility: verbatim race name, no "unknown race" /
  "not in database" copy in the guide's verification card
"""

import sys
import copy
from pathlib import Path

import pytest

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent))

from known_races import (
    KNOWN_RACES,
    FUZZY_MATCH_THRESHOLD,
    FUZZY_MATCH_MARGIN,
    match_race,
    match_race_scored,
    fuzzy_score,
    build_generic_race_profile,
    generic_race_demands,
)
from intake_to_plan import build_profile, generate_coaching_brief
from create_profile_from_form import resolve_race_id
from pre_delivery_checklist import race_match_lines


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_parsed_with_race(race_name, goals_extra=None):
    """Minimal parsed-intake dict with a specific race name."""
    goals = {'primary_goal': 'specific_race', 'races': race_name}
    if goals_extra:
        goals.update(goals_extra)
    return {
        'athlete_name': 'Match Test',
        '__header__': {'email': 'test@example.com'},
        'basic_info': {'age': '30', 'weight': '75 kg', 'sex': 'male'},
        'goals': goals,
        'current_fitness': {'ftp': '250 W', 'years_cycling': '5',
                            'years_structured': '2'},
        'schedule': {'weekly_hours_available': '8-10',
                     'long_ride_days': 'saturday'},
        'recovery': {'resting_hr': '55 bpm', 'typical_sleep': '7 hrs',
                     'sleep_quality': 'good', 'recovery_speed': 'normal'},
        'equipment': {'devices': 'garmin, power_meter',
                      'platform': 'trainingpeaks'},
        'work_life': {'work_hours': '40', 'job_stress': 'moderate',
                      'life_stress': 'moderate'},
        'health': {},
        'strength': {'current': 'none', 'include': 'no'},
        'coaching': {'autonomy': 'guided'},
        'mental_game': {},
        'additional': {},
    }


UNKNOWN_RACE = "Joe's Backyard Fondo"


# ===========================================================================
# TestMatchRaceScored — the matcher itself
# ===========================================================================

class TestMatchRaceScored:

    def test_exact_alias_unchanged(self):
        matched, meta = match_race_scored('Unbound 200')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'
        assert meta['method'] == 'alias'
        assert meta['score'] == 1.0
        assert meta['matched_slug'] == 'unbound_gravel_200'

    def test_exact_name_unchanged(self):
        matched, meta = match_race_scored('Unbound Gravel 200')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'
        # the full name is also an alias key, which is checked first —
        # either way it is a top-confidence deterministic match
        assert meta['method'] in ('alias', 'exact')
        assert meta['score'] == 1.0

    def test_case_variant(self):
        matched, meta = match_race_scored('UNBOUND 200')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'

    def test_punctuation_variant(self):
        matched, meta = match_race_scored('Unbound Gravel 200!!')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'

    def test_the_prefix_variant(self):
        matched, meta = match_race_scored('The Unbound Gravel 200')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'

    def test_typo_fuzzy_matches(self):
        matched, meta = match_race_scored('Unbund Gravel 200')
        assert matched is not None
        assert matched[0] == 'unbound_gravel_200'
        assert meta['method'] == 'fuzzy'
        assert meta['score'] >= FUZZY_MATCH_THRESHOLD

    def test_clearly_unknown_race_unmatched(self):
        matched, meta = match_race_scored(UNKNOWN_RACE)
        assert matched is None
        assert meta['method'] == 'none'
        assert meta['matched_slug'] is None
        # near misses reported for the coach, with scores
        assert len(meta['near_misses']) >= 1
        for n in meta['near_misses']:
            assert n['score'] < FUZZY_MATCH_THRESHOLD
            assert 'slug' in n and 'name' in n

    def test_ambiguous_near_tie_is_unmatched(self):
        # "Unbound Gravel 150" doesn't exist; it scores a near-tie between
        # the real 200/100/50 editions. Conservative: UNMATCHED, coach
        # verifies — never a guess at which edition was meant.
        matched, meta = match_race_scored('Unbound Gravel 150')
        assert matched is None
        assert meta['method'] == 'none'
        # the near misses show the editions it was torn between
        slugs = {n['slug'] for n in meta['near_misses']}
        assert slugs & {'unbound_gravel_200', 'unbound_gravel_100',
                        'unbound_gravel_50'}

    def test_no_unknown_race_resolves_to_unbound(self):
        # The old-contract kill test: unknown names must NEVER fall through
        # to unbound_gravel_200 (or any other real race).
        for name in (UNKNOWN_RACE, 'Zephyr Desert Rally',
                     'Gravel Blinduro Czech', 'Tour de France',
                     'Borderlands AZ State Championships'):
            assert match_race(name) is None, name

    def test_edition_specific_substring(self):
        # Longest-name substring: "SBT GRVL 75 mile" must hit the 75, not
        # the shorter flagship "SBT GRVL".
        matched, _ = match_race_scored('SBT GRVL 75 mile')
        assert matched is not None
        assert matched[0] == 'sbt_grvl_75'

    def test_empty_name(self):
        matched, meta = match_race_scored('')
        assert matched is None
        assert meta['method'] == 'none'

    def test_match_race_wrapper_compat(self):
        # match_race() keeps its (race_id, info) | None contract
        result = match_race('Unbound 200')
        assert result == ('unbound_gravel_200',
                          KNOWN_RACES['unbound_gravel_200'])
        assert match_race(UNKNOWN_RACE) is None

    def test_fuzzy_score_bounds(self):
        assert fuzzy_score('Unbound Gravel 200', 'Unbound Gravel 200') > 0.99
        assert 0.0 <= fuzzy_score('abc', 'xyz') <= 1.0
        assert fuzzy_score('', 'Unbound Gravel 200') == 0.0


# ===========================================================================
# TestGenericRaceProfile — the honest fallback object
# ===========================================================================

class TestGenericRaceProfile:

    def test_verbatim_name_and_athlete_data(self):
        g = build_generic_race_profile(UNKNOWN_RACE, date='2026-09-12',
                                       distance_miles=60, discipline='road')
        assert g['name'] == UNKNOWN_RACE
        assert g['date'] == '2026-09-12'
        assert g['distance_miles'] == 60
        assert g['discipline'] == 'road'
        assert g['generic'] is True

    def test_no_fabricated_elevation(self):
        g = build_generic_race_profile(UNKNOWN_RACE, distance_miles=60)
        assert g['elevation_ft'] == 0

    def test_demands_shape_for_scorer(self):
        # Same interface race_category_scorer consumes: 8 dims, each 0-10.
        from race_category_scorer import (calculate_category_scores,
                                          DEMAND_DIMENSIONS)
        demands = generic_race_demands(60, 'road')
        assert set(demands.keys()) == set(DEMAND_DIMENSIONS)
        assert all(0 <= v <= 10 for v in demands.values())
        scores = calculate_category_scores(demands)
        assert scores  # scorable without errors

    def test_demands_scale_with_distance_and_discipline(self):
        short = generic_race_demands(40, 'road')
        ultra = generic_race_demands(200, 'gravel')
        assert ultra['durability'] > short['durability']
        assert ultra['technical'] > short['technical']
        mtb = generic_race_demands(100, 'mtb')
        assert mtb['technical'] > ultra['technical']


# ===========================================================================
# TestBuildProfileUnknownRace — pipeline entry (intake_to_plan)
# ===========================================================================

class TestBuildProfileUnknownRace:

    @pytest.fixture(scope='class')
    def unknown_profile(self):
        return build_profile(_make_parsed_with_race(
            f'{UNKNOWN_RACE} (2026-09-12, 60, priority A)'))

    def test_silent_unbound_default_is_dead(self, unknown_profile):
        assert unknown_profile['target_race']['race_id'] != 'unbound_gravel_200'

    def test_verbatim_race_name(self, unknown_profile):
        assert unknown_profile['target_race']['name'] == UNKNOWN_RACE

    def test_generic_profile_flagged(self, unknown_profile):
        tr = unknown_profile['target_race']
        assert tr.get('generic_profile') is True
        assert tr.get('race_match', {}).get('method') == 'none'
        assert tr['race_match'].get('near_misses') is not None

    def test_generic_demands_recorded(self, unknown_profile):
        demands = unknown_profile['target_race'].get('generic_demands')
        assert demands
        assert all(0 <= v <= 10 for v in demands.values())

    def test_discipline_derived_from_name(self, unknown_profile):
        # "Fondo" in the race name → road (derive_discipline keywords)
        assert unknown_profile['target_race'].get('generic_discipline') == 'road'

    def test_athlete_data_kept(self, unknown_profile):
        tr = unknown_profile['target_race']
        assert tr['date'] == '2026-09-12'
        assert tr['distance_miles'] == 60
        assert tr['elevation_ft'] == 0  # nothing fabricated

    def test_matched_race_records_race_match(self):
        profile = build_profile(_make_parsed_with_race(
            'Unbound Gravel 200 (2026-05-30, 200, priority A)'))
        tr = profile['target_race']
        assert tr['race_id'] == 'unbound_gravel_200'
        rm = tr.get('race_match')
        assert rm and rm['method'] in ('alias', 'exact', 'substring', 'fuzzy')
        assert rm['matched_slug'] == 'unbound_gravel_200'
        assert not tr.get('generic_profile')

    def test_fuzzy_matched_race_records_method_and_score(self):
        profile = build_profile(_make_parsed_with_race(
            'Unbund Gravel 200 (2026-05-30, 200, priority A)'))
        rm = profile['target_race'].get('race_match')
        assert rm['method'] == 'fuzzy'
        assert rm['score'] >= FUZZY_MATCH_THRESHOLD
        assert rm['matched_slug'] == 'unbound_gravel_200'


# ===========================================================================
# TestCoachingBriefFlag — loud to the coach
# ===========================================================================

class TestCoachingBriefFlag:

    def test_unmatched_race_block_present(self):
        parsed = _make_parsed_with_race(
            f'{UNKNOWN_RACE} (2026-09-12, 60, priority A)')
        profile = build_profile(parsed)
        brief = generate_coaching_brief(profile, parsed)
        assert 'UNMATCHED RACE' in brief
        assert UNKNOWN_RACE in brief          # raw name, verbatim
        # near misses with scores are listed for verification
        rm = profile['target_race']['race_match']
        for near in rm['near_misses']:
            assert near['name'] in brief
        # generic assumptions are disclosed
        assert 'generic' in brief.lower()

    def test_matched_race_has_no_flag(self):
        parsed = _make_parsed_with_race(
            'Unbound Gravel 200 (2026-05-30, 200, priority A)')
        profile = build_profile(parsed)
        brief = generate_coaching_brief(profile, parsed)
        assert 'UNMATCHED RACE' not in brief


# ===========================================================================
# TestPreDeliveryChecklistFlag
# ===========================================================================

class TestPreDeliveryChecklistFlag:

    def test_unmatched_race_item(self):
        profile = build_profile(_make_parsed_with_race(
            f'{UNKNOWN_RACE} (2026-09-12, 60, priority A)'))
        lines = '\n'.join(race_match_lines(profile))
        assert 'UNMATCHED RACE' in lines
        assert UNKNOWN_RACE in lines
        assert 'score' in lines               # near-miss scores shown
        assert 'verified race identity' in lines.lower()

    def test_matched_race_item(self):
        profile = build_profile(_make_parsed_with_race(
            'Unbound Gravel 200 (2026-05-30, 200, priority A)'))
        lines = '\n'.join(race_match_lines(profile))
        assert 'UNMATCHED' not in lines
        assert 'unbound_gravel_200' in lines

    def test_legacy_profile_without_race_match(self):
        # Old profiles (no race_match key) produce no section, no crash.
        assert race_match_lines({'target_race': {'name': 'X'}}) == []
        assert race_match_lines({}) == []


# ===========================================================================
# TestFormPathNoSilentDefault — create_profile_from_form
# ===========================================================================

class TestFormPathNoSilentDefault:

    def test_unknown_race_not_unbound(self):
        race_id, meta = resolve_race_id(UNKNOWN_RACE)
        assert race_id != 'unbound_gravel_200'
        assert race_id == 'joe_s_backyard_fondo'
        assert meta['method'] == 'none'

    def test_known_race_resolves(self):
        race_id, meta = resolve_race_id('Unbound 200')
        assert race_id == 'unbound_gravel_200'
        assert meta['method'] == 'alias'

    def test_empty_name(self):
        race_id, meta = resolve_race_id('')
        assert race_id == ''
        assert meta is None

    def test_full_form_profile_unknown_race(self):
        from create_profile_from_form import create_profile_from_form
        profile = create_profile_from_form('form-test', {
            'name': 'Form Test',
            'email': 'f@example.com',
            'race_name': UNKNOWN_RACE,
            'race_date': '2026-09-12',
            'race_distance': '60',
            'race_distance_unit': 'miles',
            'weekly_volume': '8-10',
        })
        tr = profile['target_race']
        assert tr['race_id'] != 'unbound_gravel_200'
        assert tr['name'] == UNKNOWN_RACE
        assert tr['race_match']['method'] == 'none'

    def test_full_form_profile_known_race(self):
        from create_profile_from_form import create_profile_from_form
        profile = create_profile_from_form('form-test2', {
            'name': 'Form Test Two',
            'email': 'f2@example.com',
            'race_name': 'Unbound Gravel 200',
            'race_date': '2026-05-30',
            'race_distance': '200',
            'race_distance_unit': 'miles',
            'weekly_volume': '8-10',
        })
        tr = profile['target_race']
        assert tr['race_id'] == 'unbound_gravel_200'
        assert tr['race_match']['method'] in ('alias', 'exact', 'substring')


# ===========================================================================
# TestAthleteFacingGuide — invisible to the athlete
# ===========================================================================

class TestAthleteFacingGuide:

    def test_verification_card_no_defensive_copy(self):
        from training_guide_builder import _date_verification_card
        card = _date_verification_card(
            {'race_date': '2026-09-12'},
            {'matched': False, 'date_match': None, 'date_specific': ''},
        )
        low = card.lower()
        assert 'unknown race' not in low
        assert 'not in database' not in low
        assert 'not in the database' not in low
        # still nudges the athlete to confirm the date
        assert 'official race website' in low

    def test_cross_reference_unmatched(self):
        from training_guide_builder import _cross_reference_race_date
        x = _cross_reference_race_date(UNKNOWN_RACE, '2026-09-12')
        assert x.get('matched') is False

    def test_guide_badges_use_verbatim_name(self):
        from training_guide_builder import _meta_badges
        html = _meta_badges(UNKNOWN_RACE, 60, 0, '', 12, '')
        assert UNKNOWN_RACE in html
        assert 'Unbound' not in html
        # elevation 0 is dropped, not rendered as "0 ft"
        assert '0 ft' not in html
