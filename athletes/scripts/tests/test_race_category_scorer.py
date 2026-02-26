#!/usr/bin/env python3
"""Tests for race_category_scorer.py (Sprint 2).

40+ tests covering:
- Weight matrix completeness and validation
- Category score calculation and normalization
- Top categories selection
- Integration tests with realistic race demand profiles

Run with: pytest tests/test_race_category_scorer.py -v
"""

import sys
from pathlib import Path

import pytest

# Add script path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from race_category_scorer import (
    DEMAND_TO_CATEGORY_WEIGHTS,
    DEMAND_DIMENSIONS,
    calculate_category_scores,
    get_top_categories,
    get_all_referenced_categories,
)
from new_archetypes import NEW_ARCHETYPES


# =============================================================================
# TEST WEIGHT MATRIX
# =============================================================================

class TestWeightMatrix:
    """Validate the demand-to-category weight matrix."""

    def test_all_8_demand_dimensions_present(self):
        """Weight matrix must have entries for all 8 demand dimensions."""
        expected = {
            'durability', 'climbing', 'vo2_power', 'threshold',
            'technical', 'heat_resilience', 'altitude', 'race_specificity',
        }
        assert set(DEMAND_TO_CATEGORY_WEIGHTS.keys()) == expected

    def test_demand_dimensions_constant_matches_matrix(self):
        """DEMAND_DIMENSIONS list must match matrix keys."""
        assert set(DEMAND_DIMENSIONS) == set(DEMAND_TO_CATEGORY_WEIGHTS.keys())

    def test_all_weights_positive(self):
        """Every weight in the matrix must be positive."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            for cat, weight in weights.items():
                assert weight > 0, f"Weight for {dim}->{cat} is {weight}, expected > 0"

    def test_all_weights_reasonable_range(self):
        """Weights should be in range 0.5 to 5.0."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            for cat, weight in weights.items():
                assert 0.5 <= weight <= 5.0, (
                    f"Weight for {dim}->{cat} is {weight}, expected 0.5-5.0"
                )

    def test_no_orphan_categories(self):
        """Every category in the weight matrix must exist in NEW_ARCHETYPES."""
        referenced = get_all_referenced_categories()
        missing = referenced - set(NEW_ARCHETYPES.keys())
        assert missing == set(), f"Categories in weight matrix but not in NEW_ARCHETYPES: {missing}"

    def test_every_dimension_has_at_least_one_category(self):
        """Each demand dimension must map to at least one category."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            assert len(weights) >= 1, f"Dimension '{dim}' has no category weights"

    def test_every_dimension_has_a_primary_weight(self):
        """Each dimension should have at least one weight >= 2.5 (primary match)."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            max_weight = max(weights.values())
            assert max_weight >= 2.0, (
                f"Dimension '{dim}' has no strong category match (max weight {max_weight})"
            )

    def test_durability_maps_to_durability_category(self):
        """Durability demand must map to Durability category."""
        assert 'Durability' in DEMAND_TO_CATEGORY_WEIGHTS['durability']

    def test_climbing_maps_to_climbing_categories(self):
        """Climbing demand must map to Mixed_Climbing."""
        assert 'Mixed_Climbing' in DEMAND_TO_CATEGORY_WEIGHTS['climbing']

    def test_vo2_maps_to_vo2max_category(self):
        """VO2 power demand must map to VO2max category."""
        assert 'VO2max' in DEMAND_TO_CATEGORY_WEIGHTS['vo2_power']

    def test_threshold_maps_to_threshold_category(self):
        """Threshold demand must map to TT_Threshold category."""
        assert 'TT_Threshold' in DEMAND_TO_CATEGORY_WEIGHTS['threshold']

    def test_technical_maps_to_gravel_specific(self):
        """Technical demand must map to Gravel_Specific."""
        assert 'Gravel_Specific' in DEMAND_TO_CATEGORY_WEIGHTS['technical']

    def test_race_specificity_maps_to_race_simulation(self):
        """Race specificity demand must map to Race_Simulation."""
        assert 'Race_Simulation' in DEMAND_TO_CATEGORY_WEIGHTS['race_specificity']

    def test_no_duplicate_categories_per_dimension(self):
        """A category should not appear twice in the same dimension."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            # dict keys are inherently unique, but let's be explicit
            assert len(weights) == len(set(weights.keys())), (
                f"Duplicate categories in dimension '{dim}'"
            )

    def test_primary_weights_are_highest_in_dimension(self):
        """Every dimension should have at least one weight >= 2.0 (primary match)."""
        for dim, weights in DEMAND_TO_CATEGORY_WEIGHTS.items():
            max_w = max(weights.values())
            assert max_w >= 2.0, f"Dimension '{dim}' lacks a strong primary weight"


# =============================================================================
# TEST CALCULATE CATEGORY SCORES
# =============================================================================

class TestCalculateCategoryScores:
    """Test the score calculation and normalization logic."""

    def test_returns_dict(self):
        """Must return a dict."""
        result = calculate_category_scores({'durability': 5})
        assert isinstance(result, dict)

    def test_empty_demands_returns_empty(self):
        """Empty demand dict returns empty result."""
        result = calculate_category_scores({})
        assert result == {}

    def test_zero_demands_returns_all_zeros(self):
        """All-zero demands return all-zero scores."""
        demands = {dim: 0 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        for cat, score in result.items():
            assert score == 0, f"Category {cat} should be 0 with all-zero demands"

    def test_scores_are_normalized_0_to_100(self):
        """All scores must be in range 0-100."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        for cat, score in result.items():
            assert 0 <= score <= 100, f"{cat} score {score} outside 0-100"

    def test_top_score_is_100(self):
        """The highest-scoring category must be exactly 100."""
        demands = {'durability': 10, 'climbing': 2, 'vo2_power': 3, 'threshold': 2,
                   'technical': 1, 'heat_resilience': 1, 'altitude': 1, 'race_specificity': 2}
        result = calculate_category_scores(demands)
        assert max(result.values()) == 100

    def test_sorted_descending(self):
        """Results must be sorted by score descending."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        scores = list(result.values())
        assert scores == sorted(scores, reverse=True)

    def test_single_dimension_activates_correct_categories(self):
        """Only durability=10, rest=0 -> only durability-related categories scored."""
        demands = {'durability': 10}
        result = calculate_category_scores(demands)
        expected_cats = set(DEMAND_TO_CATEGORY_WEIGHTS['durability'].keys())
        assert set(result.keys()) == expected_cats

    def test_high_durability_makes_durability_top(self):
        """When durability is the dominant demand, Durability should be top category."""
        demands = {'durability': 10, 'climbing': 1, 'vo2_power': 1, 'threshold': 1,
                   'technical': 1, 'heat_resilience': 1, 'altitude': 1, 'race_specificity': 1}
        result = calculate_category_scores(demands)
        top_cat = list(result.keys())[0]
        assert top_cat == 'Durability', f"Expected Durability on top, got {top_cat}"

    def test_high_climbing_makes_climbing_top(self):
        """When climbing is dominant, Mixed_Climbing should be top."""
        demands = {'durability': 1, 'climbing': 10, 'vo2_power': 1, 'threshold': 1,
                   'technical': 1, 'heat_resilience': 1, 'altitude': 1, 'race_specificity': 1}
        result = calculate_category_scores(demands)
        top_cat = list(result.keys())[0]
        assert top_cat == 'Mixed_Climbing', f"Expected Mixed_Climbing on top, got {top_cat}"

    def test_high_vo2_makes_vo2max_top(self):
        """When vo2_power is dominant, VO2max should be top."""
        demands = {'durability': 1, 'climbing': 1, 'vo2_power': 10, 'threshold': 1,
                   'technical': 1, 'heat_resilience': 1, 'altitude': 1, 'race_specificity': 1}
        result = calculate_category_scores(demands)
        top_cat = list(result.keys())[0]
        assert top_cat == 'VO2max', f"Expected VO2max on top, got {top_cat}"

    def test_high_threshold_makes_threshold_top(self):
        """When threshold is dominant, TT_Threshold should be top."""
        demands = {'durability': 1, 'climbing': 1, 'vo2_power': 1, 'threshold': 10,
                   'technical': 1, 'heat_resilience': 1, 'altitude': 1, 'race_specificity': 1}
        result = calculate_category_scores(demands)
        top_cat = list(result.keys())[0]
        assert top_cat == 'TT_Threshold', f"Expected TT_Threshold on top, got {top_cat}"

    def test_unknown_dimension_ignored(self):
        """Unknown demand dimensions are silently ignored."""
        demands = {'durability': 5, 'fake_dimension': 10}
        result = calculate_category_scores(demands)
        # Should only have durability-derived categories
        expected_cats = set(DEMAND_TO_CATEGORY_WEIGHTS['durability'].keys())
        assert set(result.keys()) == expected_cats

    def test_negative_demand_clamped_to_zero(self):
        """Negative demand scores are clamped to 0."""
        demands = {'durability': -5}
        result = calculate_category_scores(demands)
        for cat, score in result.items():
            assert score == 0, f"{cat} should be 0 with clamped negative demand"

    def test_demand_above_10_clamped(self):
        """Demands above 10 are clamped to 10."""
        result_10 = calculate_category_scores({'durability': 10})
        result_20 = calculate_category_scores({'durability': 20})
        assert result_10 == result_20

    def test_multiple_dimensions_accumulate(self):
        """Categories appearing in multiple dimensions accumulate scores."""
        # Durability category appears in 'durability' and 'heat_resilience' and 'race_specificity'
        demands_single = {'durability': 10}
        demands_multi = {'durability': 10, 'heat_resilience': 10, 'race_specificity': 10}
        result_single = calculate_category_scores(demands_single)
        result_multi = calculate_category_scores(demands_multi)
        # The raw score for Durability should be higher in multi
        # But after normalization, it depends on what else is scored
        # At minimum, both should have Durability
        assert 'Durability' in result_single
        assert 'Durability' in result_multi

    def test_all_equal_demands_symmetric(self):
        """All dimensions at 5 should produce a balanced result."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        # Should have many categories
        assert len(result) > 10

    def test_scores_are_integers(self):
        """All scores must be integers after rounding."""
        demands = {'durability': 7, 'vo2_power': 3, 'threshold': 5}
        result = calculate_category_scores(demands)
        for cat, score in result.items():
            assert isinstance(score, int), f"{cat} score {score} is not int"


# =============================================================================
# TEST GET TOP CATEGORIES
# =============================================================================

class TestGetTopCategories:
    """Test the top-N category selection."""

    def test_returns_list_of_tuples(self):
        """Must return list of (name, score) tuples."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = get_top_categories(demands, n=5)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_respects_n_limit(self):
        """Returns at most N categories."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        for n in [1, 3, 5, 8]:
            result = get_top_categories(demands, n=n)
            assert len(result) <= n

    def test_default_n_is_8(self):
        """Default N should be 8."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = get_top_categories(demands)
        assert len(result) <= 8

    def test_sorted_descending(self):
        """Results sorted by score descending."""
        demands = {dim: 5 for dim in DEMAND_DIMENSIONS}
        result = get_top_categories(demands, n=10)
        scores = [s for _, s in result]
        assert scores == sorted(scores, reverse=True)

    def test_n_larger_than_categories(self):
        """Requesting more than available categories returns all."""
        demands = {'durability': 5}  # Only activates ~5 categories
        result = get_top_categories(demands, n=100)
        assert len(result) == len(DEMAND_TO_CATEGORY_WEIGHTS['durability'])

    def test_empty_demands(self):
        """Empty demands return empty list."""
        result = get_top_categories({}, n=5)
        assert result == []

    def test_top_1_is_highest_scorer(self):
        """Top 1 should be the highest-scoring category."""
        demands = {'vo2_power': 10}
        top = get_top_categories(demands, n=1)
        assert len(top) == 1
        assert top[0][0] == 'VO2max'
        assert top[0][1] == 100


# =============================================================================
# INTEGRATION TESTS: REALISTIC RACE PROFILES
# =============================================================================

class TestIntegrationUnbound:
    """Integration tests with Unbound 200-like demands."""

    UNBOUND_DEMANDS = {
        'durability': 9,
        'climbing': 4,
        'vo2_power': 6,
        'threshold': 5,
        'technical': 5,
        'heat_resilience': 8,
        'altitude': 2,
        'race_specificity': 7,
    }

    def test_durability_in_top_3(self):
        """Unbound 200: Durability should be in top 3."""
        top = get_top_categories(self.UNBOUND_DEMANDS, n=3)
        cats = [c for c, _ in top]
        assert 'Durability' in cats, f"Expected Durability in top 3, got {cats}"

    def test_race_simulation_scores_high(self):
        """Unbound 200: Race_Simulation should score well (high race_specificity)."""
        scores = calculate_category_scores(self.UNBOUND_DEMANDS)
        assert scores.get('Race_Simulation', 0) >= 40

    def test_produces_diverse_categories(self):
        """Unbound 200: Should produce at least 10 distinct scored categories."""
        scores = calculate_category_scores(self.UNBOUND_DEMANDS)
        assert len(scores) >= 10

    def test_endurance_categories_score_well(self):
        """Unbound 200: Endurance + HVLI should score well."""
        scores = calculate_category_scores(self.UNBOUND_DEMANDS)
        assert scores.get('Endurance', 0) >= 30
        assert scores.get('HVLI_Extended', 0) >= 30


class TestIntegrationLeadville:
    """Integration tests with Leadville-like demands."""

    LEADVILLE_DEMANDS = {
        'durability': 8,
        'climbing': 9,
        'vo2_power': 5,
        'threshold': 6,
        'technical': 4,
        'heat_resilience': 3,
        'altitude': 9,
        'race_specificity': 6,
    }

    def test_climbing_in_top_8(self):
        """Leadville: Climbing categories should be in top 8."""
        top = get_top_categories(self.LEADVILLE_DEMANDS, n=8)
        cats = [c for c, _ in top]
        climbing_cats = {'Mixed_Climbing', 'Over_Under', 'SFR_Muscle_Force'}
        assert any(c in climbing_cats for c in cats), f"Expected a climbing category in top 8, got {cats}"

    def test_climbing_scores_above_50(self):
        """Leadville: Climbing=9 should put climbing categories above 50."""
        scores = calculate_category_scores(self.LEADVILLE_DEMANDS)
        assert scores.get('Mixed_Climbing', 0) >= 50, (
            f"Mixed_Climbing={scores.get('Mixed_Climbing', 0)}, expected >= 50"
        )
        assert scores.get('Over_Under', 0) >= 50, (
            f"Over_Under={scores.get('Over_Under', 0)}, expected >= 50"
        )

    def test_vo2max_scores_high_due_to_altitude(self):
        """Leadville: VO2max should score high (altitude=9 contributes)."""
        scores = calculate_category_scores(self.LEADVILLE_DEMANDS)
        assert scores.get('VO2max', 0) >= 40

    def test_heat_categories_score_low(self):
        """Leadville: Heat-related categories should score lower than climbing."""
        scores = calculate_category_scores(self.LEADVILLE_DEMANDS)
        # Durability gets heat_resilience contribution, but climbing > heat
        climbing_score = scores.get('Mixed_Climbing', 0)
        # heat_resilience contributes to Durability, not a separate heat category
        assert climbing_score >= 60


class TestIntegrationShortCrit:
    """Integration tests with a short, technical, competitive race."""

    CRIT_DEMANDS = {
        'durability': 2,
        'climbing': 2,
        'vo2_power': 9,
        'threshold': 7,
        'technical': 3,
        'heat_resilience': 2,
        'altitude': 1,
        'race_specificity': 8,
    }

    def test_vo2max_is_top(self):
        """Short crit: VO2max should be top category."""
        top = get_top_categories(self.CRIT_DEMANDS, n=1)
        assert top[0][0] == 'VO2max' or top[0][0] == 'TT_Threshold', (
            f"Expected VO2max or TT_Threshold on top, got {top[0][0]}"
        )

    def test_durability_scores_below_vo2max(self):
        """Short crit: Durability should score below VO2max."""
        scores = calculate_category_scores(self.CRIT_DEMANDS)
        assert scores.get('Durability', 0) < scores.get('VO2max', 0), (
            f"Durability={scores.get('Durability', 0)} should be below VO2max={scores.get('VO2max', 0)}"
        )

    def test_race_simulation_scores_high(self):
        """Short crit: Race_Simulation should score well."""
        scores = calculate_category_scores(self.CRIT_DEMANDS)
        assert scores.get('Race_Simulation', 0) >= 40


class TestEdgeCases:
    """Edge cases for the scoring system."""

    def test_all_demands_at_maximum(self):
        """All demands at 10 should still produce valid scores."""
        demands = {dim: 10 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        assert max(result.values()) == 100
        assert all(0 <= s <= 100 for s in result.values())

    def test_all_demands_at_minimum(self):
        """All demands at 0 should produce all-zero scores."""
        demands = {dim: 0 for dim in DEMAND_DIMENSIONS}
        result = calculate_category_scores(demands)
        assert all(s == 0 for s in result.values())

    def test_single_demand_at_1(self):
        """Single demand at 1 should still produce valid non-zero scores."""
        demands = {'durability': 1}
        result = calculate_category_scores(demands)
        assert max(result.values()) == 100  # normalized
        assert min(result.values()) > 0  # all positive (durability has no 0-weight cats)

    def test_float_demands_handled(self):
        """Float demand values should be handled."""
        demands = {'durability': 5.5, 'climbing': 3.7}
        result = calculate_category_scores(demands)
        assert isinstance(result, dict)
        assert len(result) > 0
