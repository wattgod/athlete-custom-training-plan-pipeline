#!/usr/bin/env python3
"""Race category scorer -- maps demand vectors to archetype category scores.

Sprint 2 of the race-to-archetype mapping system.

Given a race's demand vector (8 dimensions, each 0-10), this module scores
every archetype category by weighted contribution of each demand dimension.

The weight matrix encodes training science relationships:
  - High durability demand -> Durability, HVLI_Extended, Endurance categories
  - High climbing demand -> Mixed_Climbing, Over_Under, SFR_Muscle_Force
  - etc.

Usage:
    from race_category_scorer import calculate_category_scores, get_top_categories

    demands = {'durability': 9, 'climbing': 4, 'vo2_power': 6, ...}
    scores = calculate_category_scores(demands)
    top = get_top_categories(demands, n=8)
"""

# =============================================================================
# DEMAND-TO-CATEGORY WEIGHT MATRIX
# =============================================================================
# Each demand dimension maps to categories it activates, with a weight
# multiplier reflecting how strongly that demand dimension should pull
# workouts from that category.
#
# Weights:
#   3.0 = primary match (this is THE category for that demand)
#   2.0-2.5 = strong secondary match
#   1.0-1.5 = supporting contribution
# =============================================================================

DEMAND_TO_CATEGORY_WEIGHTS = {
    'durability': {
        'Durability': 3.0,
        'HVLI_Extended': 2.5,
        'Endurance': 2.0,
        'Blended': 1.5,
        'Tempo': 1.0,
    },
    'climbing': {
        'Mixed_Climbing': 3.0,
        'Over_Under': 2.5,
        'SFR_Muscle_Force': 2.0,
        'TT_Threshold': 1.5,
        'G_Spot': 1.0,
    },
    'vo2_power': {
        'VO2max': 3.0,
        'Anaerobic_Capacity': 2.0,
        'Critical_Power': 1.5,
        'Sprint_Neuromuscular': 1.0,
    },
    'threshold': {
        'TT_Threshold': 3.0,
        'G_Spot': 2.5,
        'Norwegian_Double': 2.0,
        'Over_Under': 1.5,
        'Tempo': 1.0,
    },
    'technical': {
        'Gravel_Specific': 3.0,
        'Cadence_Work': 2.0,
        'Critical_Power': 2.0,
        'Race_Simulation': 1.5,
        'Anaerobic_Capacity': 1.0,
    },
    'heat_resilience': {
        'Durability': 2.0,
        'Endurance': 1.5,
        'HVLI_Extended': 1.0,
    },
    'altitude': {
        'VO2max': 2.5,
        'Endurance': 1.5,
        'LT1_MAF': 1.0,
    },
    'race_specificity': {
        'Race_Simulation': 3.0,
        'Gravel_Specific': 2.0,
        'Durability': 1.5,
        'Blended': 1.0,
    },
}

# All valid demand dimensions
DEMAND_DIMENSIONS = [
    'durability', 'climbing', 'vo2_power', 'threshold',
    'technical', 'heat_resilience', 'altitude', 'race_specificity',
]


def normalize_demand_vector(demands: dict, *, require_all: bool = True) -> dict:
    """Validate and normalize the public 8-axis race-demand vector.

    This is deliberately stricter than ``calculate_category_scores``.  The
    scorer remains tolerant for historical callers, while paid-plan intake and
    profile projection can fail closed instead of silently treating a typo or
    missing dimension as zero demand.
    """
    if not isinstance(demands, dict):
        raise ValueError("race demands must be an object")
    unknown = sorted(set(demands) - set(DEMAND_DIMENSIONS))
    if unknown:
        raise ValueError(f"unknown race-demand dimensions: {', '.join(unknown)}")
    missing = [key for key in DEMAND_DIMENSIONS if key not in demands]
    if require_all and missing:
        raise ValueError(f"missing race-demand dimensions: {', '.join(missing)}")

    normalized = {}
    for key in DEMAND_DIMENSIONS:
        if key not in demands:
            continue
        value = demands[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"race demand {key!r} must be numeric")
        value = float(value)
        if not 0 <= value <= 10:
            raise ValueError(f"race demand {key!r} must be between 0 and 10")
        normalized[key] = int(value) if value.is_integer() else value
    return normalized


def derive_race_demands(distance_mi=None, elevation_ft=None,
                        discipline: str = "") -> dict:
    """Derive a conservative full vector from verified course facts.

    Unknown facts stay neutral rather than being fabricated.  The same helper
    serves short blocks and full-season generation so their demand weighting
    cannot drift.
    """
    neutral = 5
    demands = {
        'vo2_power': neutral,
        'heat_resilience': neutral,
        'altitude': neutral,
        'race_specificity': neutral,
    }

    try:
        distance = float(distance_mi) if distance_mi is not None else None
    except (TypeError, ValueError):
        distance = None
    if distance is not None and distance <= 0:
        distance = None
    try:
        elevation = float(elevation_ft) if elevation_ft is not None else None
    except (TypeError, ValueError):
        elevation = None
    if elevation is not None and elevation < 0:
        elevation = None

    if distance is None:
        demands['durability'] = neutral
    elif distance >= 200:
        demands['durability'] = 10
    elif distance >= 150:
        demands['durability'] = 8
    elif distance >= 100:
        demands['durability'] = 6
    elif distance >= 75:
        demands['durability'] = 4
    elif distance >= 50:
        demands['durability'] = 2
    else:
        demands['durability'] = 1

    if elevation is None:
        demands['climbing'] = neutral
    elif distance:
        ratio = elevation / distance
        if ratio >= 175:
            demands['climbing'] = 9
        elif ratio >= 125:
            demands['climbing'] = 8
        elif ratio >= 90:
            demands['climbing'] = 6
        elif ratio >= 60:
            demands['climbing'] = 5
        elif ratio >= 35:
            demands['climbing'] = 3
        else:
            demands['climbing'] = 2
    else:
        demands['climbing'] = max(1, min(8, int(round(elevation / 2500))))

    if distance is None:
        demands['threshold'] = neutral
    else:
        if 75 <= distance <= 150:
            threshold = 7
        elif 50 <= distance < 75:
            threshold = 5
        elif distance > 150:
            threshold = 4
        else:
            threshold = 3
        if demands['climbing'] >= 6:
            threshold += 1
        demands['threshold'] = max(0, min(10, int(round(threshold))))

    demands['technical'] = {
        'mtb': 8, 'gravel': 5, 'road': 2,
    }.get(str(discipline or '').strip().lower(), neutral)
    return normalize_demand_vector(demands)


def demand_vector_for_profile(profile: dict) -> tuple:
    """Return ``(vector, source)`` for a paid-plan athlete profile."""
    profile = profile or {}
    target = profile.get('target_race', {}) or {}
    if target.get('training_demands') is not None:
        return normalize_demand_vector(target['training_demands']), 'explicit'
    if target.get('generic_demands') is not None:
        return normalize_demand_vector(target['generic_demands']), 'generic_profile'
    return (
        derive_race_demands(
            target.get('distance_miles'), target.get('elevation_ft'),
            profile.get('discipline') or target.get('discipline') or '',
        ),
        'verified_course_facts',
    )


def category_weights_for_profile(profile: dict) -> tuple:
    """Return ``(category weights, demand vector, provenance source)``."""
    demands, source = demand_vector_for_profile(profile)
    return calculate_category_scores(demands), demands, source


def calculate_category_scores(demands: dict) -> dict:
    """Score each archetype category for a race's demands.

    Args:
        demands: Dict with 8 dimensions, each 0-10.
                 Missing dimensions are treated as 0.
                 Values outside 0-10 are clamped.

    Returns:
        Dict mapping category name to normalized score 0-100, sorted descending.
    """
    category_scores = {}
    for demand_dim, demand_score in demands.items():
        if demand_dim not in DEMAND_TO_CATEGORY_WEIGHTS:
            continue
        # Clamp to 0-10
        clamped = max(0, min(10, demand_score))
        weights = DEMAND_TO_CATEGORY_WEIGHTS[demand_dim]
        for category, weight in weights.items():
            if category not in category_scores:
                category_scores[category] = 0.0
            category_scores[category] += clamped * weight

    # Normalize to 0-100
    if not category_scores:
        return {}
    max_score = max(category_scores.values())
    if max_score == 0:
        return {cat: 0 for cat in category_scores}
    for cat in category_scores:
        category_scores[cat] = round((category_scores[cat] / max_score) * 100)

    return dict(sorted(category_scores.items(), key=lambda x: -x[1]))


def get_top_categories(demands: dict, n: int = 8) -> list:
    """Get top N scored categories.

    Args:
        demands: Dict with 8 dimensions, each 0-10.
        n: Number of top categories to return (default 8).

    Returns:
        List of (category_name, score) tuples, sorted by score descending.
    """
    scores = calculate_category_scores(demands)
    return list(scores.items())[:n]


def get_all_referenced_categories() -> set:
    """Return the set of all category names referenced in the weight matrix.

    Useful for validation against the actual archetype registry.
    """
    cats = set()
    for weights in DEMAND_TO_CATEGORY_WEIGHTS.values():
        cats.update(weights.keys())
    return cats


if __name__ == '__main__':
    # Demo with Unbound-200-like demands
    unbound_demands = {
        'durability': 9,
        'climbing': 4,
        'vo2_power': 6,
        'threshold': 5,
        'technical': 5,
        'heat_resilience': 8,
        'altitude': 2,
        'race_specificity': 7,
    }
    print("UNBOUND 200 DEMAND PROFILE")
    print("=" * 50)
    for dim, score in unbound_demands.items():
        bar = "#" * score + "." * (10 - score)
        print(f"  {dim:20s} [{bar}] {score}/10")
    print()

    print("CATEGORY SCORES (normalized 0-100)")
    print("-" * 50)
    for cat, score in calculate_category_scores(unbound_demands).items():
        bar = "#" * (score // 5) + "." * (20 - score // 5)
        print(f"  {cat:25s} [{bar}] {score}")
    print()

    print(f"TOP 8 CATEGORIES:")
    for cat, score in get_top_categories(unbound_demands, n=8):
        print(f"  {score:3d}  {cat}")
