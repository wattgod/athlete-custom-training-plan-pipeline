#!/usr/bin/env python3
"""Tests for race_intel_enhancer.py (Sprint 4).

30+ tests covering:
- Rider intel citation extraction and keyword matching
- Max 2 citations per workout
- Graceful handling of empty intel
- Coaching brief structure and content
- Text pool building from various intel sources

Run with: pytest tests/test_race_intel_enhancer.py -v
"""

import sys
from pathlib import Path

import pytest

# Add script path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from race_intel_enhancer import (
    CATEGORY_KEYWORDS,
    MAX_CITATIONS_PER_WORKOUT,
    enhance_with_rider_intel,
    generate_race_brief,
    _extract_rider_intel,
    _build_text_pool,
    _find_citations,
    _demand_bar,
    _truncate,
    _why_this_workout,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def race_data_with_intel():
    """Race data with rich rider intel."""
    return {
        'race': {
            'name': 'Test Race',
            'display_name': 'Test Race 200',
            'vitals': {
                'distance_mi': 200,
                'elevation_ft': 12000,
                'location': 'Somewhere, KS',
                'date_specific': '2026: June 6',
            },
            'gravel_god_rating': {
                'tier': 1,
                'tier_label': 'TIER 1',
                'discipline': 'gravel',
                'overall_score': 93,
            },
            'youtube_data': {
                'rider_intel': {
                    'key_challenges': [
                        {'description': 'The heat was brutal, hitting 95 degrees by mile 50'},
                        {'description': 'The elevation gain was relentless with steep climbs every 10 miles'},
                        {'description': 'Rocky technical sections destroyed tires and required careful handling'},
                    ],
                    'terrain_notes': [
                        {'text': 'Loose gravel with deep ruts on the descents'},
                        {'text': 'The long climb at mile 80 was the race selector'},
                    ],
                    'race_day_tips': [
                        {'text': 'Pace yourself for the first 50 miles or you will bonk'},
                        {'text': 'Bring extra hydration, the heat is no joke'},
                        {'text': 'Attack on the climb at mile 80 if you want to make the selection'},
                    ],
                    'additional_quotes': [
                        {
                            'text': 'The race was a survival exercise from mile 100 onwards',
                            'source_video_id': 'abc123',
                            'source_channel': 'Test Channel',
                        },
                    ],
                    'search_text': 'This race features brutal heat, relentless climbing, and technical gravel sections that test every aspect of your endurance and bike handling skills.',
                },
            },
        }
    }


@pytest.fixture
def race_data_no_intel():
    """Race data without rider intel."""
    return {
        'race': {
            'name': 'Test Race',
            'display_name': 'Test Race 100',
            'vitals': {
                'distance_mi': 100,
                'elevation_ft': 5000,
                'location': 'Nowhere, CO',
            },
            'gravel_god_rating': {
                'tier': 2,
                'tier_label': 'TIER 2',
                'discipline': 'gravel',
            },
        }
    }


@pytest.fixture
def sample_pack():
    """Sample workout pack."""
    return [
        {'category': 'Durability', 'archetype_name': 'Tired VO2max', 'relevance_score': 100, 'level': 3},
        {'category': 'VO2max', 'archetype_name': '5x3 VO2 Classic', 'relevance_score': 80, 'level': 3},
        {'category': 'Mixed_Climbing', 'archetype_name': 'Mixed Climbing', 'relevance_score': 70, 'level': 3},
        {'category': 'Gravel_Specific', 'archetype_name': 'Surge and Settle', 'relevance_score': 60, 'level': 3},
        {'category': 'Race_Simulation', 'archetype_name': 'Breakaway Simulation', 'relevance_score': 50, 'level': 3},
    ]


@pytest.fixture
def sample_demands():
    """Sample demand vector."""
    return {
        'durability': 9, 'climbing': 7, 'vo2_power': 6, 'threshold': 5,
        'technical': 5, 'heat_resilience': 8, 'altitude': 2, 'race_specificity': 7,
    }


# =============================================================================
# TEST ENHANCE WITH RIDER INTEL
# =============================================================================

class TestEnhanceWithRiderIntel:
    """Test the rider intel enhancement function."""

    def test_adds_citations_key(self, sample_pack, race_data_with_intel):
        """Each pack item gets a rider_intel_citations key."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        for item in result:
            assert 'rider_intel_citations' in item

    def test_max_2_citations_per_workout(self, sample_pack, race_data_with_intel):
        """No workout gets more than 2 citations."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        for item in result:
            assert len(item['rider_intel_citations']) <= MAX_CITATIONS_PER_WORKOUT

    def test_durability_gets_endurance_citations(self, sample_pack, race_data_with_intel):
        """Durability category should match endurance/fatigue/bonk keywords."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        durability_item = [i for i in result if i['category'] == 'Durability'][0]
        citations = durability_item['rider_intel_citations']
        assert len(citations) >= 1, "Durability should find at least one citation"

    def test_climbing_gets_elevation_citations(self, sample_pack, race_data_with_intel):
        """Mixed_Climbing category should match climb/elevation keywords."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        climbing_item = [i for i in result if i['category'] == 'Mixed_Climbing'][0]
        citations = climbing_item['rider_intel_citations']
        assert len(citations) >= 1, "Climbing should find at least one citation"

    def test_gravel_gets_technical_citations(self, sample_pack, race_data_with_intel):
        """Gravel_Specific category should match rocky/technical/gravel keywords."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        gravel_item = [i for i in result if i['category'] == 'Gravel_Specific'][0]
        citations = gravel_item['rider_intel_citations']
        assert len(citations) >= 1, "Gravel_Specific should find at least one citation"

    def test_no_intel_graceful(self, sample_pack, race_data_no_intel):
        """No rider intel: all workouts get empty citation lists."""
        result = enhance_with_rider_intel(sample_pack, race_data_no_intel)
        for item in result:
            assert item['rider_intel_citations'] == []

    def test_empty_pack_graceful(self, race_data_with_intel):
        """Empty pack returns empty list."""
        result = enhance_with_rider_intel([], race_data_with_intel)
        assert result == []

    def test_returns_same_list_mutated(self, sample_pack, race_data_with_intel):
        """Returns the same list object (mutated in place)."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        assert result is sample_pack

    def test_citations_have_required_keys(self, sample_pack, race_data_with_intel):
        """Each citation dict has text, source, matched_keyword."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        for item in result:
            for citation in item['rider_intel_citations']:
                assert 'text' in citation
                assert 'source' in citation
                assert 'matched_keyword' in citation

    def test_citation_sources_are_valid(self, sample_pack, race_data_with_intel):
        """Citation sources must be one of the known types."""
        valid_sources = {'search_text', 'race_day_tip', 'terrain_note', 'key_challenge', 'additional_quote'}
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        for item in result:
            for citation in item['rider_intel_citations']:
                assert citation['source'] in valid_sources, f"Unknown source: {citation['source']}"

    def test_prioritizes_specific_over_search_text(self, sample_pack, race_data_with_intel):
        """Specific citations (key_challenge, terrain_note) should rank above search_text."""
        result = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        for item in result:
            citations = item['rider_intel_citations']
            if len(citations) >= 2:
                # First citation should not be search_text if specific ones exist
                assert citations[0]['source'] != 'search_text', (
                    f"First citation for {item['category']} should be specific, not search_text"
                )


# =============================================================================
# TEST TEXT POOL BUILDING
# =============================================================================

class TestBuildTextPool:
    """Test text pool building from rider intel."""

    def test_builds_from_all_sources(self, race_data_with_intel):
        """Text pool includes items from all intel sources."""
        intel = _extract_rider_intel(race_data_with_intel)
        pool = _build_text_pool(intel)
        sources = {item['source'] for item in pool}
        assert 'search_text' in sources
        assert 'race_day_tip' in sources
        assert 'terrain_note' in sources
        assert 'key_challenge' in sources
        assert 'additional_quote' in sources

    def test_empty_intel(self):
        """Empty rider intel returns empty pool."""
        pool = _build_text_pool({})
        assert pool == []

    def test_count_matches_data(self, race_data_with_intel):
        """Pool count should match: 1 search_text + 3 kc + 2 tn + 3 rdt + 1 aq = 10."""
        intel = _extract_rider_intel(race_data_with_intel)
        pool = _build_text_pool(intel)
        assert len(pool) == 10

    def test_all_items_have_text_and_source(self, race_data_with_intel):
        """Every pool item has non-empty text and source."""
        intel = _extract_rider_intel(race_data_with_intel)
        pool = _build_text_pool(intel)
        for item in pool:
            assert len(item['text']) > 0
            assert len(item['source']) > 0


# =============================================================================
# TEST FIND CITATIONS
# =============================================================================

class TestFindCitations:
    """Test citation finding logic."""

    def test_matches_keyword(self):
        """Finds items matching a keyword."""
        pool = [
            {'text': 'The heat was brutal at 95 degrees', 'source': 'key_challenge'},
            {'text': 'Nice community event', 'source': 'additional_quote'},
        ]
        results = _find_citations(pool, ['heat', 'hot'])
        assert len(results) == 1
        assert results[0]['matched_keyword'] == 'heat'

    def test_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        pool = [{'text': 'The HEAT was brutal', 'source': 'key_challenge'}]
        results = _find_citations(pool, ['heat'])
        assert len(results) == 1

    def test_no_match_returns_empty(self):
        """No matching keywords returns empty list."""
        pool = [{'text': 'Beautiful scenery along the route', 'source': 'additional_quote'}]
        results = _find_citations(pool, ['heat', 'climb', 'attack'])
        assert results == []

    def test_empty_keywords_returns_empty(self):
        """Empty keyword list returns empty."""
        pool = [{'text': 'The heat was brutal', 'source': 'key_challenge'}]
        results = _find_citations(pool, [])
        assert results == []

    def test_empty_pool_returns_empty(self):
        """Empty pool returns empty."""
        results = _find_citations([], ['heat', 'climb'])
        assert results == []

    def test_deduplication(self):
        """Same text should not appear twice."""
        pool = [
            {'text': 'The heat was brutal and the climb was steep', 'source': 'key_challenge'},
        ]
        # Both 'heat' and 'climb' match, but should only produce 1 result
        results = _find_citations(pool, ['heat', 'climb'])
        assert len(results) == 1


# =============================================================================
# TEST GENERATE RACE BRIEF
# =============================================================================

class TestGenerateRaceBrief:
    """Test coaching brief generation."""

    def test_returns_string(self, race_data_with_intel, sample_pack, sample_demands):
        """Must return a string."""
        # Add empty citations to pack
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert isinstance(brief, str)

    def test_contains_race_name(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must contain the race name."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert 'Test Race 200' in brief

    def test_contains_train_for_header(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must start with # Train for {race_name}."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '# Train for Test Race 200' in brief

    def test_contains_race_profile_section(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must have ## Race Profile section."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '## Race Profile' in brief

    def test_contains_training_demands_section(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must have ## Training Demands section."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '## Training Demands' in brief

    def test_contains_demands_table(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must contain a demands table with all 8 dimensions."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '| Dimension | Score | Bar |' in brief
        assert 'Durability' in brief
        assert 'Climbing' in brief
        assert 'Vo2 Power' in brief

    def test_contains_workout_pack_section(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must have ## Your {N}-Workout Pack section."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert f'## Your {len(sample_pack)}-Workout Pack' in brief

    def test_contains_how_to_use_section(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must have ## How to Use This Pack section."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '## How to Use This Pack' in brief

    def test_contains_distance_and_elevation(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must show distance and elevation."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        assert '200 miles' in brief
        assert '12000 ft' in brief

    def test_contains_all_workout_names(self, race_data_with_intel, sample_pack, sample_demands):
        """Brief must list every workout name."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_with_intel, sample_pack, sample_demands)
        for item in sample_pack:
            assert item['archetype_name'] in brief

    def test_rider_intel_quote_in_brief(self, race_data_with_intel, sample_pack, sample_demands):
        """If pack has citations, they appear in the brief."""
        enhanced = enhance_with_rider_intel(sample_pack, race_data_with_intel)
        brief = generate_race_brief(race_data_with_intel, enhanced, sample_demands)
        assert 'Riders say' in brief

    def test_brief_with_no_intel(self, race_data_no_intel, sample_pack, sample_demands):
        """Brief still generates properly without rider intel."""
        for item in sample_pack:
            item['rider_intel_citations'] = []
        brief = generate_race_brief(race_data_no_intel, sample_pack, sample_demands)
        assert '# Train for' in brief
        assert '## How to Use This Pack' in brief


# =============================================================================
# TEST UTILITY FUNCTIONS
# =============================================================================

class TestUtilities:
    """Test utility functions."""

    def test_demand_bar_0(self):
        assert '##########' not in _demand_bar(0)
        assert '..........' in _demand_bar(0)

    def test_demand_bar_10(self):
        assert '##########' in _demand_bar(10)
        assert '..........' not in _demand_bar(10)

    def test_demand_bar_5(self):
        bar = _demand_bar(5)
        assert '#####' in bar
        assert '.....' in bar

    def test_truncate_short(self):
        assert _truncate('short', 200) == 'short'

    def test_truncate_long(self):
        text = 'a' * 300
        result = _truncate(text, 200)
        assert len(result) == 200
        assert result.endswith('...')

    def test_truncate_exact_length(self):
        text = 'a' * 200
        assert _truncate(text, 200) == text

    def test_why_this_workout_durability(self):
        demands = {'durability': 9}
        result = _why_this_workout('Durability', demands)
        assert '9/10' in result

    def test_why_this_workout_unknown_category(self):
        demands = {'durability': 5}
        result = _why_this_workout('UnknownCategory', demands)
        assert result == ''

    def test_extract_rider_intel_present(self, race_data_with_intel):
        intel = _extract_rider_intel(race_data_with_intel)
        assert intel is not None
        assert 'key_challenges' in intel

    def test_extract_rider_intel_absent(self, race_data_no_intel):
        intel = _extract_rider_intel(race_data_no_intel)
        assert intel is None

    def test_category_keywords_coverage(self):
        """At least 10 categories should have keywords."""
        assert len(CATEGORY_KEYWORDS) >= 10

    def test_all_keyword_lists_non_empty(self):
        """Every category's keyword list should have at least 1 keyword."""
        for cat, keywords in CATEGORY_KEYWORDS.items():
            assert len(keywords) >= 1, f"Category {cat} has no keywords"
