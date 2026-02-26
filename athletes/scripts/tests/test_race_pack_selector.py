#!/usr/bin/env python3
"""Tests for race_pack_selector.py (Sprint 3).

40+ tests covering:
- Workout pack selection: size, category balance, max-3 rule
- ZWO rendering: intervals, segments, single_effort, tired_vo2, pyramid
- ZWO format: single quotes in declaration, self-closing tags, indent
- File generation and XML validity

Run with: pytest tests/test_race_pack_selector.py -v
"""

import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# Add script path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from race_pack_selector import (
    select_workout_pack,
    generate_race_pack_zwos,
    _render_zwo,
    _find_archetype,
    _xml_escape,
    _slugify,
)
from race_category_scorer import calculate_category_scores, DEMAND_DIMENSIONS
from new_archetypes import NEW_ARCHETYPES


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def balanced_scores():
    """Category scores from balanced demands."""
    demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
    return calculate_category_scores(demands)


@pytest.fixture
def durability_heavy_scores():
    """Category scores from durability-heavy demands (Unbound-like)."""
    demands = {
        'durability': 9, 'climbing': 4, 'vo2_power': 6, 'threshold': 5,
        'technical': 5, 'heat_resilience': 8, 'altitude': 2, 'race_specificity': 7,
    }
    return calculate_category_scores(demands)


@pytest.fixture
def tmp_output_dir():
    """Temporary output directory for ZWO files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# TEST SELECT WORKOUT PACK
# =============================================================================

class TestSelectWorkoutPack:
    """Test workout pack selection logic."""

    def test_returns_list(self, balanced_scores):
        """Must return a list."""
        pack = select_workout_pack(balanced_scores)
        assert isinstance(pack, list)

    def test_default_pack_size_10(self, balanced_scores):
        """Default pack size is 10."""
        pack = select_workout_pack(balanced_scores)
        assert len(pack) <= 10

    def test_custom_pack_size(self, balanced_scores):
        """Custom pack_size is respected."""
        for size in [5, 8, 12]:
            pack = select_workout_pack(balanced_scores, pack_size=size)
            assert len(pack) <= size

    def test_pack_size_1(self, balanced_scores):
        """Pack size 1 returns a single workout."""
        pack = select_workout_pack(balanced_scores, pack_size=1)
        assert len(pack) == 1

    def test_empty_scores_returns_empty(self):
        """Empty category scores return empty pack."""
        pack = select_workout_pack({})
        assert pack == []

    def test_pack_items_have_required_keys(self, balanced_scores):
        """Each pack item must have category, archetype_name, relevance_score, level."""
        pack = select_workout_pack(balanced_scores, pack_size=5)
        for item in pack:
            assert 'category' in item
            assert 'archetype_name' in item
            assert 'relevance_score' in item
            assert 'level' in item

    def test_max_3_per_category(self, balanced_scores):
        """No category should have more than 3 archetypes in the pack."""
        pack = select_workout_pack(balanced_scores, pack_size=15)
        from collections import Counter
        counts = Counter(item['category'] for item in pack)
        for cat, count in counts.items():
            assert count <= 3, f"Category {cat} has {count} archetypes, max is 3"

    def test_top_categories_represented(self, durability_heavy_scores):
        """Top-scoring categories should appear in the pack."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=10)
        pack_cats = {item['category'] for item in pack}
        # Top category should be in pack
        top_cat = list(durability_heavy_scores.keys())[0]
        assert top_cat in pack_cats, f"Top category {top_cat} not in pack"

    def test_top_3_get_2_archetypes_each(self, durability_heavy_scores):
        """Top 3 categories with score >= 50 should get 2 archetypes each."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=10)
        from collections import Counter
        counts = Counter(item['category'] for item in pack)
        # Get top 3 categories with score >= 50
        top3 = [(c, s) for c, s in durability_heavy_scores.items() if s >= 50][:3]
        for cat, score in top3:
            if cat in NEW_ARCHETYPES and len(NEW_ARCHETYPES[cat]) >= 2:
                assert counts.get(cat, 0) >= 2, (
                    f"Top category {cat} (score={score}) should have >= 2 archetypes, got {counts.get(cat, 0)}"
                )

    def test_sorted_by_relevance_descending(self, balanced_scores):
        """Pack should be sorted by relevance_score descending."""
        pack = select_workout_pack(balanced_scores, pack_size=10)
        scores = [item['relevance_score'] for item in pack]
        assert scores == sorted(scores, reverse=True)

    def test_archetype_names_are_real(self, balanced_scores):
        """Every archetype_name in the pack must exist in NEW_ARCHETYPES."""
        pack = select_workout_pack(balanced_scores, pack_size=10)
        for item in pack:
            cat = item['category']
            name = item['archetype_name']
            found = _find_archetype(cat, name)
            assert found is not None, f"Archetype '{name}' not found in category '{cat}'"

    def test_all_scores_non_negative(self, balanced_scores):
        """All relevance scores must be non-negative."""
        pack = select_workout_pack(balanced_scores, pack_size=10)
        for item in pack:
            assert item['relevance_score'] >= 0

    def test_categories_with_no_archetypes_skipped(self):
        """Categories that don't exist in NEW_ARCHETYPES are skipped."""
        fake_scores = {'NonExistentCategory': 100, 'VO2max': 80}
        pack = select_workout_pack(fake_scores, pack_size=5)
        cats = {item['category'] for item in pack}
        assert 'NonExistentCategory' not in cats
        assert 'VO2max' in cats

    def test_pack_size_larger_than_available(self):
        """Pack size larger than available archetypes returns what's available."""
        # Single category with score
        scores = {'Recovery': 100}  # Recovery has 2 archetypes
        pack = select_workout_pack(scores, pack_size=50)
        assert len(pack) <= 3  # max 3 from any category


class TestSelectWorkoutPackLargeSize:
    """Test pack selection with large pack sizes."""

    def test_pack_size_20(self, balanced_scores):
        """Pack of 20 should have diverse categories."""
        pack = select_workout_pack(balanced_scores, pack_size=20)
        cats = {item['category'] for item in pack}
        assert len(cats) >= 5, f"Expected 5+ categories in pack of 20, got {len(cats)}"

    def test_no_duplicate_workouts(self, balanced_scores):
        """No exact duplicate (same category + archetype_name) in a pack."""
        pack = select_workout_pack(balanced_scores, pack_size=20)
        seen = set()
        for item in pack:
            key = (item['category'], item['archetype_name'])
            assert key not in seen, f"Duplicate workout: {key}"
            seen.add(key)


# =============================================================================
# TEST ZWO RENDERING
# =============================================================================

class TestRenderZwo:
    """Test ZWO XML rendering for various archetype formats."""

    def test_intervals_format(self):
        """Archetype with intervals key renders IntervalsT."""
        archetype = {
            'name': 'Test Intervals',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'intervals': (5, 180),
                    'on_power': 1.15,
                    'off_power': 0.55,
                    'duration': 180,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-intervals')
        assert 'IntervalsT' in xml
        assert 'Repeat="5"' in xml
        assert 'OnDuration="180"' in xml
        assert 'OnPower="1.15"' in xml

    def test_single_effort_format(self):
        """Archetype with single_effort renders SteadyState."""
        archetype = {
            'name': 'Test Single',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'single_effort': True,
                    'duration': 1200,
                    'power': 0.96,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-single')
        assert 'SteadyState Duration="1200" Power="0.96"' in xml

    def test_tired_vo2_format(self):
        """Archetype with tired_vo2 renders base + intervals."""
        archetype = {
            'name': 'Test Tired',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'tired_vo2': True,
                    'base_duration': 7200,
                    'base_power': 0.70,
                    'intervals': (3, 240),
                    'on_power': 1.15,
                    'off_power': 0.55,
                    'off_duration': 210,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-tired')
        assert 'SteadyState Duration="7200" Power="0.70"' in xml
        assert 'IntervalsT' in xml
        assert 'Repeat="3"' in xml

    def test_segments_format(self):
        """Archetype with segments renders each segment type."""
        archetype = {
            'name': 'Test Segments',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'segments': [
                        {'type': 'steady', 'duration': 600, 'power': 0.88},
                        {'type': 'intervals', 'repeats': 4, 'on_duration': 180, 'on_power': 0.97, 'off_duration': 180, 'off_power': 0.55},
                    ],
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-segments')
        assert 'SteadyState Duration="600" Power="0.88"' in xml
        assert 'IntervalsT Repeat="4"' in xml

    def test_pyramid_format(self):
        """Archetype with pyramid renders descending efforts."""
        archetype = {
            'name': 'Test Pyramid',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'pyramid': True,
                    'sets': 2,
                    'efforts': [
                        {'duration': 240, 'power': 1.12},
                        {'duration': 180, 'power': 1.15},
                        {'duration': 120, 'power': 1.18},
                    ],
                    'recovery_duration': 180,
                    'set_recovery': 300,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-pyramid')
        assert 'Power="1.12"' in xml
        assert 'Power="1.15"' in xml
        assert 'Power="1.18"' in xml
        # Set recovery
        assert 'Duration="300"' in xml

    def test_loaded_recovery_format(self):
        """Archetype with loaded_recovery renders VO2 + tempo recovery."""
        archetype = {
            'name': 'Test Loaded',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'loaded_recovery': True,
                    'intervals': (4, 300),
                    'on_power': 1.18,
                    'loaded_power': 0.87,
                    'loaded_duration': 150,
                    'off_power': 0.50,
                    'off_duration': 150,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-loaded')
        assert 'Power="1.18"' in xml
        assert 'Power="0.87"' in xml

    def test_double_day_format(self):
        """Archetype with double_day renders AM + PM."""
        archetype = {
            'name': 'Test Double',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'double_day': True,
                    'am_duration': 7200,
                    'am_power': 0.70,
                    'pm_intervals': (3, 720),
                    'pm_on_power': 1.00,
                    'pm_off_power': 0.55,
                    'pm_off_duration': 240,
                }
            }
        }
        xml = _render_zwo(archetype, 3, 200, 'test-double')
        assert 'Duration="7200"' in xml
        # Transition marker
        assert 'Duration="1800"' in xml
        assert 'IntervalsT' in xml

    def test_fallback_level(self):
        """Requesting unavailable level falls back to level 3."""
        archetype = {
            'name': 'Test Fallback',
            'levels': {
                '3': {
                    'structure': 'Test',
                    'intervals': (4, 180),
                    'on_power': 1.10,
                    'off_power': 0.55,
                }
            }
        }
        xml = _render_zwo(archetype, 6, 200, 'test-fallback')
        assert 'Repeat="4"' in xml  # got level 3 data


class TestZwoFormat:
    """Test ZWO XML formatting requirements."""

    def _get_sample_zwo(self):
        """Generate a sample ZWO for format testing."""
        archetype = {
            'name': 'Format Test',
            'levels': {
                '3': {
                    'structure': 'Test workout for format validation',
                    'intervals': (5, 180),
                    'on_power': 1.15,
                    'off_power': 0.55,
                }
            }
        }
        return _render_zwo(archetype, 3, 200, 'format-test')

    def test_single_quotes_in_xml_declaration(self):
        """XML declaration must use single quotes."""
        xml = self._get_sample_zwo()
        assert xml.startswith("<?xml version='1.0' encoding='UTF-8'?>")

    def test_self_closing_warmup(self):
        """Warmup element must be self-closing (end with />)."""
        xml = self._get_sample_zwo()
        assert '<Warmup' in xml
        # Find warmup line and check it ends with />
        for line in xml.split('\n'):
            if '<Warmup' in line:
                assert line.strip().endswith('/>'), f"Warmup not self-closing: {line}"

    def test_self_closing_cooldown(self):
        """Cooldown element must be self-closing."""
        xml = self._get_sample_zwo()
        for line in xml.split('\n'):
            if '<Cooldown' in line:
                assert line.strip().endswith('/>'), f"Cooldown not self-closing: {line}"

    def test_self_closing_steady_state(self):
        """SteadyState elements must be self-closing."""
        archetype = {
            'name': 'SS Test',
            'levels': {'3': {'structure': 'Test', 'single_effort': True, 'duration': 1200, 'power': 0.96}}
        }
        xml = _render_zwo(archetype, 3, 200, 'ss-test')
        for line in xml.split('\n'):
            if '<SteadyState' in line:
                assert line.strip().endswith('/>'), f"SteadyState not self-closing: {line}"

    def test_self_closing_intervals(self):
        """IntervalsT elements must be self-closing."""
        xml = self._get_sample_zwo()
        for line in xml.split('\n'):
            if '<IntervalsT' in line:
                assert line.strip().endswith('/>'), f"IntervalsT not self-closing: {line}"

    def test_2_space_indent_metadata(self):
        """Metadata elements use 2-space indent."""
        xml = self._get_sample_zwo()
        lines = xml.split('\n')
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('<name>') or stripped.startswith('<author>'):
                indent = len(line) - len(stripped)
                assert indent == 2, f"Metadata indent should be 2, got {indent}: {line}"

    def test_4_space_indent_workout_blocks(self):
        """Workout blocks use 4-space indent."""
        xml = self._get_sample_zwo()
        lines = xml.split('\n')
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('<Warmup') or stripped.startswith('<IntervalsT') or stripped.startswith('<Cooldown'):
                indent = len(line) - len(stripped)
                assert indent == 4, f"Workout block indent should be 4, got {indent}: {line}"

    def test_warmup_duration_600(self):
        """Warmup should be 600 seconds (10 minutes)."""
        xml = self._get_sample_zwo()
        assert 'Duration="600"' in xml.split('Warmup')[1].split('/')[0]

    def test_warmup_power_range(self):
        """Warmup should go from 45% to 65% FTP."""
        xml = self._get_sample_zwo()
        warmup_line = [l for l in xml.split('\n') if 'Warmup' in l and 'PowerLow' in l][0]
        assert 'PowerLow="0.45"' in warmup_line
        assert 'PowerHigh="0.65"' in warmup_line

    def test_cooldown_duration_300(self):
        """Cooldown should be 300 seconds (5 minutes)."""
        xml = self._get_sample_zwo()
        cooldown_line = [l for l in xml.split('\n') if 'Cooldown' in l and 'Duration' in l][0]
        assert 'Duration="300"' in cooldown_line

    def test_cooldown_power_range(self):
        """Cooldown should go from 60% to 45% FTP."""
        xml = self._get_sample_zwo()
        cooldown_line = [l for l in xml.split('\n') if 'Cooldown' in l and 'PowerLow' in l][0]
        assert 'PowerLow="0.60"' in cooldown_line
        assert 'PowerHigh="0.45"' in cooldown_line

    def test_parseable_xml(self):
        """Generated ZWO must be parseable XML (after fixing single-quote declaration)."""
        xml = self._get_sample_zwo()
        # ET.fromstring requires double quotes in declaration or no declaration
        xml_fixed = xml.replace("<?xml version='1.0' encoding='UTF-8'?>", '')
        try:
            root = ET.fromstring(xml_fixed)
        except ET.ParseError as e:
            pytest.fail(f"Generated ZWO is not valid XML: {e}")
        assert root.tag == 'workout_file'

    def test_has_workout_element(self):
        """ZWO must have a <workout> element."""
        xml = self._get_sample_zwo()
        assert '<workout>' in xml
        assert '</workout>' in xml

    def test_has_name_element(self):
        """ZWO must have a <name> element."""
        xml = self._get_sample_zwo()
        assert '<name>' in xml

    def test_sport_type_is_bike(self):
        """sportType must be 'bike'."""
        xml = self._get_sample_zwo()
        assert '<sportType>bike</sportType>' in xml


# =============================================================================
# TEST ZWO FILE GENERATION
# =============================================================================

class TestGenerateRacePackZwos:
    """Test ZWO file generation."""

    def test_creates_files(self, durability_heavy_scores, tmp_output_dir):
        """ZWO files are created on disk."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=5)
        paths = generate_race_pack_zwos(pack, tmp_output_dir, ftp=250, level=3)
        assert len(paths) >= 1
        for p in paths:
            assert p.exists()
            assert p.suffix == '.zwo'

    def test_file_content_is_xml(self, durability_heavy_scores, tmp_output_dir):
        """Generated files contain valid XML."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=3)
        paths = generate_race_pack_zwos(pack, tmp_output_dir, ftp=250, level=3)
        for p in paths:
            content = p.read_text()
            assert content.startswith("<?xml version='1.0'")

    def test_creates_output_directory(self, durability_heavy_scores, tmp_output_dir):
        """Output directory is created if it doesn't exist."""
        nested = tmp_output_dir / 'deep' / 'nested'
        pack = select_workout_pack(durability_heavy_scores, pack_size=2)
        paths = generate_race_pack_zwos(pack, nested, ftp=200, level=3)
        assert nested.exists()

    def test_filenames_are_numbered(self, durability_heavy_scores, tmp_output_dir):
        """ZWO filenames start with a 2-digit number."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=5)
        paths = generate_race_pack_zwos(pack, tmp_output_dir, ftp=200, level=3)
        for p in paths:
            assert p.name[:2].isdigit(), f"Filename should start with 2-digit number: {p.name}"

    def test_level_propagated(self, durability_heavy_scores, tmp_output_dir):
        """Level is propagated to pack items."""
        pack = select_workout_pack(durability_heavy_scores, pack_size=3)
        generate_race_pack_zwos(pack, tmp_output_dir, ftp=200, level=5)
        for item in pack:
            assert item['level'] == 5

    def test_empty_pack_returns_empty(self, tmp_output_dir):
        """Empty pack returns empty list."""
        paths = generate_race_pack_zwos([], tmp_output_dir, ftp=200, level=3)
        assert paths == []


# =============================================================================
# TEST UTILITY FUNCTIONS
# =============================================================================

class TestUtilities:
    """Test utility functions."""

    def test_xml_escape_ampersand(self):
        assert _xml_escape('a & b') == 'a &amp; b'

    def test_xml_escape_lt_gt(self):
        assert _xml_escape('a < b > c') == 'a &lt; b &gt; c'

    def test_xml_escape_quotes(self):
        assert _xml_escape('say "hello"') == 'say &quot;hello&quot;'

    def test_xml_escape_apostrophe(self):
        assert _xml_escape("it's") == "it&apos;s"

    def test_xml_escape_empty(self):
        assert _xml_escape('') == ''

    def test_xml_escape_none(self):
        assert _xml_escape(None) == ''

    def test_slugify_basic(self):
        assert _slugify('5x3 VO2 Classic') == '5x3-vo2-classic'

    def test_slugify_special_chars(self):
        assert _slugify("W' Depletion") == 'w-depletion'

    def test_slugify_spaces(self):
        assert _slugify('Attack Repeats') == 'attack-repeats'

    def test_find_archetype_exists(self):
        """Find an archetype that exists."""
        arch = _find_archetype('VO2max', '5x3 VO2 Classic')
        assert arch is not None
        assert arch['name'] == '5x3 VO2 Classic'

    def test_find_archetype_missing(self):
        """Missing archetype returns None."""
        arch = _find_archetype('VO2max', 'NonExistent Workout')
        assert arch is None

    def test_find_archetype_wrong_category(self):
        """Archetype in wrong category returns None."""
        arch = _find_archetype('Recovery', '5x3 VO2 Classic')
        assert arch is None


# =============================================================================
# TEST REAL ARCHETYPES
# =============================================================================

class TestRealArchetypeRendering:
    """Test rendering with actual archetypes from NEW_ARCHETYPES."""

    def test_render_5x3_vo2_classic(self):
        """Render a real VO2max archetype."""
        arch = _find_archetype('VO2max', '5x3 VO2 Classic')
        assert arch is not None
        xml = _render_zwo(arch, 3, 250, 'vo2-classic')
        assert 'IntervalsT' in xml
        assert 'OnPower="1.15"' in xml

    def test_render_single_sustained_threshold(self):
        """Render a real single_effort archetype."""
        arch = _find_archetype('TT_Threshold', 'Single Sustained Threshold')
        assert arch is not None
        xml = _render_zwo(arch, 3, 250, 'threshold')
        assert 'SteadyState' in xml

    def test_render_tired_vo2max(self):
        """Render a real tired_vo2 archetype."""
        arch = _find_archetype('Durability', 'Tired VO2max')
        assert arch is not None
        xml = _render_zwo(arch, 3, 250, 'tired-vo2')
        assert 'Duration="9000"' in xml  # level 3 base_duration
        assert 'IntervalsT' in xml

    def test_render_descending_pyramid(self):
        """Render a real pyramid archetype."""
        arch = _find_archetype('VO2max', 'Descending VO2 Pyramid')
        assert arch is not None
        xml = _render_zwo(arch, 3, 250, 'pyramid')
        # Level 3 has 2 sets, should have set recovery
        assert 'Duration="300"' in xml  # set_recovery

    def test_render_loaded_recovery(self):
        """Render a real loaded_recovery archetype."""
        arch = _find_archetype('VO2max', 'VO2max with Loaded Recovery')
        assert arch is not None
        xml = _render_zwo(arch, 3, 250, 'loaded')
        assert 'Power="1.18"' in xml  # level 3 on_power

    @pytest.mark.parametrize("category", list(NEW_ARCHETYPES.keys()))
    def test_every_category_first_archetype_renders(self, category):
        """Every category's first archetype should render valid XML."""
        archetypes = NEW_ARCHETYPES[category]
        if not archetypes:
            pytest.skip(f"No archetypes in {category}")
        arch = archetypes[0]
        xml = _render_zwo(arch, 3, 200, f'test-{category}')
        assert "<?xml version='1.0'" in xml
        assert '<workout_file>' in xml
        assert '</workout_file>' in xml
        assert '<Warmup' in xml
        assert '<Cooldown' in xml
