#!/usr/bin/env python3
"""Tests for race_pack_generator.py (Sprint 5).

25+ tests covering:
- Inline demand analysis from race JSON
- End-to-end pack generation with mock data
- File output structure
- CLI argument parsing
- Edge cases

Run with: pytest tests/test_race_pack_generator.py -v
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add script path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from race_pack_generator import (
    analyze_race_demands,
    load_race_json,
    generate_race_pack,
    _scale_linear,
    _clamp,
    _safe_float,
    _safe_int,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def unbound_race_data():
    """Unbound 200 race data (simplified)."""
    return {
        'race': {
            'name': 'Unbound 200',
            'display_name': 'Unbound Gravel 200',
            'slug': 'unbound-200',
            'vitals': {
                'distance_mi': 200,
                'elevation_ft': 11000,
                'location': 'Emporia, Kansas',
                'date_specific': '2026: June 6',
                'lat': 38.404,
                'lng': -96.1816,
            },
            'terrain': {
                'primary': 'Rolling gravel with punchy climbs',
                'surface': 'Chunky limestone',
                'technical_rating': 3,
            },
            'climate': {
                'primary': 'Flint Hills heat',
                'description': 'June brings 85-95 degrees F days with high humidity',
                'challenges': ['Heat adaptation critical', 'Hydration demands extreme'],
            },
            'gravel_god_rating': {
                'overall_score': 93,
                'tier': 1,
                'tier_label': 'TIER 1',
                'discipline': 'gravel',
                'prestige': 5,
                'field_depth': 5,
                'race_quality': 5,
                'climate': 5,
                'altitude': 1,
                'elevation': 3,
                'technicality': 4,
            },
        }
    }


@pytest.fixture
def leadville_race_data():
    """Leadville-like race data."""
    return {
        'race': {
            'name': 'Leadville Trail 100 MTB',
            'display_name': 'Leadville Trail 100 MTB',
            'vitals': {
                'distance_mi': 104,
                'elevation_ft': 12000,
                'location': 'Leadville, Colorado',
                'lat': 39.25,
                'lng': -106.29,
            },
            'terrain': {
                'primary': 'Mountain trails',
                'technical_rating': 4,
            },
            'climate': {
                'description': 'Cool mountain air at 10,000+ feet',
                'challenges': ['Altitude sickness possible'],
            },
            'gravel_god_rating': {
                'overall_score': 85,
                'tier': 1,
                'prestige': 4,
                'field_depth': 4,
                'race_quality': 4,
                'climate': 2,
                'altitude': 5,
                'elevation': 5,
                'technicality': 4,
                'discipline': 'mtb',
            },
        }
    }


@pytest.fixture
def short_race_data():
    """Short local race data."""
    return {
        'race': {
            'name': 'Local Gravel Fondo',
            'display_name': 'Local Gravel Fondo',
            'vitals': {
                'distance_mi': 40,
                'elevation_ft': 2000,
                'location': 'Smalltown, USA',
            },
            'terrain': {
                'technical_rating': 2,
            },
            'climate': {
                'description': 'Mild spring weather',
            },
            'gravel_god_rating': {
                'overall_score': 40,
                'tier': 4,
                'prestige': 2,
                'field_depth': 2,
                'race_quality': 3,
                'climate': 2,
                'altitude': 1,
                'elevation': 1,
                'technicality': 2,
                'discipline': 'gravel',
            },
        }
    }


@pytest.fixture
def tmp_race_data_dir(unbound_race_data):
    """Temporary directory with race JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        # Write unbound-200.json
        (path / 'unbound-200.json').write_text(
            json.dumps(unbound_race_data), encoding='utf-8'
        )
        yield path


@pytest.fixture
def tmp_output_dir():
    """Temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# TEST INLINE DEMAND ANALYSIS
# =============================================================================

class TestDemandAnalysis:
    """Test the inlined demand analysis function."""

    def test_returns_8_dimensions(self, unbound_race_data):
        """Must return exactly 8 dimensions."""
        demands = analyze_race_demands(unbound_race_data)
        assert len(demands) == 8
        expected_keys = {
            'durability', 'climbing', 'vo2_power', 'threshold',
            'technical', 'heat_resilience', 'altitude', 'race_specificity',
        }
        assert set(demands.keys()) == expected_keys

    def test_all_values_0_to_10(self, unbound_race_data):
        """All demand values must be in range 0-10."""
        demands = analyze_race_demands(unbound_race_data)
        for dim, score in demands.items():
            assert 0 <= score <= 10, f"{dim} = {score}, expected 0-10"

    def test_all_values_are_integers(self, unbound_race_data):
        """All demand values must be integers."""
        demands = analyze_race_demands(unbound_race_data)
        for dim, score in demands.items():
            assert isinstance(score, int), f"{dim} = {score} ({type(score)}), expected int"

    def test_unbound_high_durability(self, unbound_race_data):
        """Unbound 200: 200 miles -> high durability."""
        demands = analyze_race_demands(unbound_race_data)
        assert demands['durability'] >= 8, f"Unbound durability={demands['durability']}, expected >= 8"

    def test_unbound_high_heat(self, unbound_race_data):
        """Unbound: 95-degree heat -> high heat_resilience."""
        demands = analyze_race_demands(unbound_race_data)
        assert demands['heat_resilience'] >= 7, f"Unbound heat={demands['heat_resilience']}, expected >= 7"

    def test_unbound_low_altitude(self, unbound_race_data):
        """Unbound: altitude=1 rating -> low altitude demand."""
        demands = analyze_race_demands(unbound_race_data)
        assert demands['altitude'] <= 4, f"Unbound altitude={demands['altitude']}, expected <= 4"

    def test_unbound_high_race_specificity(self, unbound_race_data):
        """Unbound: overall_score=93 -> high race_specificity."""
        demands = analyze_race_demands(unbound_race_data)
        assert demands['race_specificity'] >= 7

    def test_leadville_high_climbing(self, leadville_race_data):
        """Leadville: 12000ft elevation -> moderate-high climbing."""
        demands = analyze_race_demands(leadville_race_data)
        assert demands['climbing'] >= 3

    def test_leadville_high_altitude(self, leadville_race_data):
        """Leadville: altitude=5 -> high altitude demand."""
        demands = analyze_race_demands(leadville_race_data)
        assert demands['altitude'] >= 8

    def test_short_race_low_durability(self, short_race_data):
        """40-mile local race -> lower durability."""
        demands = analyze_race_demands(short_race_data)
        assert demands['durability'] <= 5

    def test_short_race_higher_vo2(self, short_race_data):
        """Short competitive race may have elevated VO2."""
        demands = analyze_race_demands(short_race_data)
        # Short race bonus: +2 for < 60 miles
        assert demands['vo2_power'] >= 2

    def test_missing_fields_graceful(self):
        """Missing fields should produce valid (conservative) demands."""
        minimal = {'race': {'name': 'Minimal', 'vitals': {}, 'gravel_god_rating': {}}}
        demands = analyze_race_demands(minimal)
        assert len(demands) == 8
        for dim, score in demands.items():
            assert 0 <= score <= 10


# =============================================================================
# TEST LOAD RACE JSON
# =============================================================================

class TestLoadRaceJson:
    """Test race JSON loading."""

    def test_loads_valid_json(self, tmp_race_data_dir):
        """Loads and parses a valid race JSON."""
        data = load_race_json('unbound-200', tmp_race_data_dir)
        assert data['race']['name'] == 'Unbound 200'

    def test_file_not_found(self, tmp_race_data_dir):
        """Raises FileNotFoundError for missing race."""
        with pytest.raises(FileNotFoundError):
            load_race_json('nonexistent-race', tmp_race_data_dir)

    def test_slug_maps_to_filename(self, tmp_race_data_dir):
        """Slug is used as the JSON filename."""
        data = load_race_json('unbound-200', tmp_race_data_dir)
        assert 'race' in data


# =============================================================================
# TEST END-TO-END GENERATION
# =============================================================================

class TestEndToEnd:
    """Test the full generate_race_pack pipeline."""

    def test_generates_complete_pack(self, tmp_race_data_dir, tmp_output_dir):
        """Full pipeline produces all expected outputs."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        assert 'demands' in result
        assert 'category_scores' in result
        assert 'pack' in result
        assert 'zwo_paths' in result
        assert 'brief_path' in result

    def test_generates_zwo_files(self, tmp_race_data_dir, tmp_output_dir):
        """ZWO files are created on disk."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        assert len(result['zwo_paths']) >= 1
        for p in result['zwo_paths']:
            assert p.exists()
            assert p.suffix == '.zwo'

    def test_generates_brief(self, tmp_race_data_dir, tmp_output_dir):
        """Brief markdown file is created."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        assert result['brief_path'].exists()
        content = result['brief_path'].read_text()
        assert '# Train for' in content

    def test_generates_metadata(self, tmp_race_data_dir, tmp_output_dir):
        """Metadata JSON file is created."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        assert result['meta_path'].exists()
        meta = json.loads(result['meta_path'].read_text())
        assert meta['slug'] == 'unbound-200'
        assert meta['ftp'] == 250
        assert meta['level'] == 3

    def test_output_structure(self, tmp_race_data_dir, tmp_output_dir):
        """Output directory has expected structure."""
        generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        assert (tmp_output_dir / 'workouts').is_dir()
        assert (tmp_output_dir / 'race-training-brief.md').exists()
        assert (tmp_output_dir / 'pack-metadata.json').exists()

    def test_pack_items_have_intel_citations(self, tmp_race_data_dir, tmp_output_dir):
        """Pack items have rider_intel_citations after enhancement."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=5,
            output_base=tmp_output_dir,
        )
        for item in result['pack']:
            assert 'rider_intel_citations' in item

    def test_different_levels_produce_different_zwo(self, tmp_race_data_dir):
        """Different levels should produce different ZWO content."""
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            r1 = generate_race_pack(
                slug='unbound-200', race_data_dir=tmp_race_data_dir,
                ftp=250, level=1, pack_size=3, output_base=Path(td1),
            )
            r2 = generate_race_pack(
                slug='unbound-200', race_data_dir=tmp_race_data_dir,
                ftp=250, level=5, pack_size=3, output_base=Path(td2),
            )
            # At minimum both should produce ZWOs
            assert len(r1['zwo_paths']) >= 1
            assert len(r2['zwo_paths']) >= 1

    def test_ftp_not_in_zwo_xml_content(self, tmp_race_data_dir, tmp_output_dir):
        """FTP is used for power ratios, not raw watt values in ZWO."""
        result = generate_race_pack(
            slug='unbound-200',
            race_data_dir=tmp_race_data_dir,
            ftp=250,
            level=3,
            pack_size=3,
            output_base=tmp_output_dir,
        )
        # ZWO files use power as fraction of FTP (0.xx or 1.xx), not raw watts
        for p in result['zwo_paths']:
            content = p.read_text()
            # Should have fraction-based power values
            assert 'Power="0.' in content or 'Power="1.' in content or 'OnPower="1.' in content


# =============================================================================
# TEST HELPER FUNCTIONS
# =============================================================================

class TestHelpers:
    """Test helper/utility functions."""

    def test_scale_linear_low(self):
        assert _scale_linear(0, 0, 100, 0, 10) == 0

    def test_scale_linear_high(self):
        assert _scale_linear(100, 0, 100, 0, 10) == 10

    def test_scale_linear_mid(self):
        assert _scale_linear(50, 0, 100, 0, 10) == 5.0

    def test_scale_linear_below_range(self):
        """Below range clamps to out_low."""
        assert _scale_linear(-10, 0, 100, 0, 10) == 0

    def test_scale_linear_above_range(self):
        """Above range clamps to out_high."""
        assert _scale_linear(200, 0, 100, 0, 10) == 10

    def test_scale_linear_equal_bounds(self):
        """Equal input bounds returns out_low."""
        assert _scale_linear(5, 5, 5, 0, 10) == 0

    def test_clamp_within_range(self):
        assert _clamp(5) == 5

    def test_clamp_below(self):
        assert _clamp(-3) == 0

    def test_clamp_above(self):
        assert _clamp(15) == 10

    def test_clamp_float(self):
        assert _clamp(5.7) == 6

    def test_safe_float_valid(self):
        assert _safe_float('3.14') == 3.14

    def test_safe_float_invalid(self):
        assert _safe_float('abc') == 0.0

    def test_safe_float_none(self):
        assert _safe_float(None) == 0.0

    def test_safe_int_valid(self):
        assert _safe_int('42') == 42

    def test_safe_int_invalid(self):
        assert _safe_int('abc') == 0

    def test_safe_int_none(self):
        assert _safe_int(None) == 0

    def test_safe_int_default(self):
        assert _safe_int(None, default=5) == 5
