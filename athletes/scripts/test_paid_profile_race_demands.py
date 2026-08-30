"""Race-demand validation and paid-profile projection regressions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from race_category_scorer import (
    DEMAND_DIMENSIONS,
    category_weights_for_profile,
    derive_race_demands,
    normalize_demand_vector,
)


ALPINE_FONDO = {
    'durability': 8, 'climbing': 10, 'vo2_power': 7, 'threshold': 8,
    'technical': 2, 'heat_resilience': 4, 'altitude': 3,
    'race_specificity': 8,
}

DISTANCE_FONDO = {
    'durability': 10, 'climbing': 4, 'vo2_power': 4, 'threshold': 6,
    'technical': 2, 'heat_resilience': 5, 'altitude': 1,
    'race_specificity': 9,
}


def test_explicit_vector_is_complete_bounded_and_provenanced():
    weights, demands, source = category_weights_for_profile({
        'discipline': 'road',
        'target_race': {'training_demands': ALPINE_FONDO},
    })
    assert set(demands) == set(DEMAND_DIMENSIONS)
    assert source == 'explicit'
    assert weights['Mixed_Climbing'] > weights['Cadence_Work']


def test_same_fondo_format_can_carry_distinct_course_demands():
    alpine_weights, _, _ = category_weights_for_profile({
        'discipline': 'road', 'event_format': 'fondo',
        'target_race': {
            'event_format': 'fondo', 'training_demands': ALPINE_FONDO,
        },
    })
    distance_weights, _, _ = category_weights_for_profile({
        'discipline': 'road', 'event_format': 'fondo',
        'target_race': {
            'event_format': 'fondo', 'training_demands': DISTANCE_FONDO,
        },
    })
    assert alpine_weights != distance_weights
    assert alpine_weights['Mixed_Climbing'] > distance_weights['Mixed_Climbing']
    assert alpine_weights['TT_Threshold'] > distance_weights['TT_Threshold']


@pytest.mark.parametrize('bad', [
    {'durability': 5},
    {**ALPINE_FONDO, 'climbing': 11},
    {**ALPINE_FONDO, 'climbing': 'high'},
    {**ALPINE_FONDO, 'made_up_axis': 3},
])
def test_explicit_vector_fails_closed(bad):
    with pytest.raises(ValueError):
        normalize_demand_vector(bad)


def test_course_fact_derivation_is_full_and_road_specific():
    demands = derive_race_demands(100, 12000, 'road')
    assert set(demands) == set(DEMAND_DIMENSIONS)
    assert demands['climbing'] >= 6
    assert demands['technical'] == 2

