#!/usr/bin/env python3
"""
Methodology Selection Engine

Selects the optimal training methodology for an athlete based on:
- Weekly training hours available
- Training history and experience level
- Goal type (finish, compete, podium)
- Race demands (distance, terrain, duration)
- Lifestyle factors (stress, recovery, schedule variability)
- Athlete preferences (past success/failure with approaches)

Based on the endurance_training_systems_master_table methodology matrix.

All 13 methodologies are defined in config/methodologies.yaml and scored
objectively. Athlete free-text preferences are NOT used for scoring —
only explicit past_failure_with (hard veto, -50pts) and past_success_with
(+10pts) from intake extraction.

Methodologies Available:
1. Traditional (Pyramidal) - High volume base, progressive intensity
2. Polarized (80/20) - Easy or hard, minimal middle
3. Sweet Spot / Threshold - Time-efficient threshold focus
4. HIIT-Focused - Minimal volume, maximal intensity
5. Block Periodization - Concentrated overload phases
6. Reverse Periodization - Intensity first, volume later
7. Autoregulated (HRV-Based) - Readiness-driven load adjustment
8. MAF / Low-HR (LT1) - Aerobic base building at low HR
9. Critical Power / W' - Surge repeatability focus
10. INSCYD / Metabolic - VO2max/VLamax profiling
11. Double-Threshold (Norwegian) - Lactate-capped threshold doubles
12. HVLI / LSD-Centric - Massive low-intensity volume
13. GOAT - Adaptive composite system (pyramidal + polarized + blocks)
"""

import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))
from constants import get_athlete_file


def _load_methodologies() -> Dict:
    """Load methodology definitions from YAML config."""
    config_path = Path(__file__).parent / "config" / "methodologies.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            # Convert ideal_hours from list to tuple for compatibility
            for key, method in data.items():
                if isinstance(method.get('ideal_hours'), list):
                    method['ideal_hours'] = tuple(method['ideal_hours'])
            return data
    # Fallback to inline definition if config missing
    return _METHODOLOGIES_FALLBACK


@dataclass
class MethodologyCandidate:
    """Represents a candidate methodology with scoring."""
    name: str
    score: float
    reasons: List[str]
    warnings: List[str]
    configuration: Dict


# Fallback methodology definitions (used if config/methodologies.yaml missing)
_METHODOLOGIES_FALLBACK = {
    "time_crunched": {
        "name": "Time-Crunched",
        "description": "Every session earns its place. One protected long ride, the rest short and sharp \u2014 no junk miles.",
        "philosophy": "Make every hour count: density over volume, with the long ride kept sacred.",
        "min_hours": 3, "max_hours": 9, "ideal_hours": (4, 7),
        "best_for": ["time_crunched", "busy_professionals", "consistent_short_sessions", "gravel_racing"],
        "not_for": ["ultra_endurance", "high_volume_seekers"],
        "experience_required": "beginner",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "high",
        "intensity_distribution": {"z1_z2": 0.70, "z3": 0.10, "z4_z5": 0.20},
        "strength_approach": "optional_short_efficient",
        "key_workouts": ["protected_long_ride", "vo2max_intervals", "threshold_repeats"],
        "progression_style": "increase_density",
        "testing_frequency": "4_6_weeks"
    },
    "g_spot": {
        "name": "G Spot (Read the Room)",
        "description": "Train the productive zone between tempo and threshold \u2014 then read the room: hold the targets when you're fresh, ease off when you're cooked.",
        "philosophy": "The most productive stimulus you can absorb, with built-in permission to autoregulate the effort by feel against the day's target.",
        "min_hours": 5, "max_hours": 13, "ideal_hours": (6, 10),
        "best_for": ["productive_efficiency", "self_aware_athletes", "variable_stress", "masters", "gravel_racing"],
        "not_for": ["rigid_plan_wanters", "pure_sprinters"],
        "experience_required": "beginner",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "high",
        "intensity_distribution": {"z1_z2": 0.65, "z3": 0.25, "z4_z5": 0.10},
        "strength_approach": "optional_short_efficient",
        "key_workouts": ["g_spot_intervals", "over_unders", "long_z2"],
        "progression_style": "increase_density",
        "testing_frequency": "4_6_weeks"
    },
    "polarized_80_20": {
        "name": "Polarized (80/20)",
        "description": "Most training genuinely easy, the hard days genuinely hard, the gray-zone middle kept minimal.",
        "philosophy": "Hard/easy separation maximizes adaptation when you have the hours to ride easy.",
        "min_hours": 8, "max_hours": 22, "ideal_hours": (10, 16),
        "best_for": ["tolerance_building", "recovery_friendly", "structured_athletes", "durability", "long_events", "high_volume"],
        "not_for": ["very_low_volume"],
        "experience_required": "intermediate",
        "stress_tolerance": "high",
        "schedule_flexibility": "moderate",
        "intensity_distribution": {"z1_z2": 0.80, "z3": 0.00, "z4_z5": 0.20},
        "strength_approach": "year_round_heavy_explosive",
        "key_workouts": ["long_z2", "vo2max_intervals", "threshold_repeats"],
        "progression_style": "increase_hard_work_maintain_ratio",
        "testing_frequency": "4_6_weeks"
    },
    "traditional_pyramidal": {
        "name": "Traditional (Pyramidal)",
        "description": "Build a big aerobic base first, then sharpen \u2014 the forgiving, proven path to a first finish.",
        "philosophy": "Volume \u2192 intensity \u2192 specificity. Build the engine before you tune it.",
        "min_hours": 7, "max_hours": 30, "ideal_hours": (10, 18),
        "best_for": ["first_timers", "finishers", "long_events", "durability", "predictable_performance", "base_building"],
        "not_for": ["very_short_leadup", "very_low_volume"],
        "experience_required": "beginner",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "moderate",
        "intensity_distribution": {"z1_z2": 0.75, "z3": 0.15, "z4_z5": 0.10},
        "strength_approach": "heavy_base_maintenance_build",
        "key_workouts": ["long_z2", "tempo_progression", "threshold_intervals"],
        "progression_style": "volume_then_intensity",
        "testing_frequency": "phase_end"
    },
}

# Load from YAML config, fall back to inline definition
METHODOLOGIES = _load_methodologies() if Path(Path(__file__).parent / "config" / "methodologies.yaml").exists() else _METHODOLOGIES_FALLBACK


def calculate_methodology_score(
    methodology: Dict,
    profile: Dict,
    derived: Dict,
    race_demands: Dict
) -> MethodologyCandidate:
    """
    Score a methodology for a specific athlete.

    Returns MethodologyCandidate with score (0-100), reasons, and warnings.
    """
    score = 50.0  # Start at neutral
    reasons = []
    warnings = []

    method_name = methodology["name"]

    # ==========================================================================
    # HOURS MATCH (±30 points)
    # ==========================================================================
    hours = profile.get("weekly_availability", {}).get("cycling_hours_target", 10)
    min_h, max_h = methodology["min_hours"], methodology["max_hours"]
    ideal_min, ideal_max = methodology["ideal_hours"]

    if hours < min_h:
        # Below minimum - major penalty
        deficit = min_h - hours
        penalty = min(30, deficit * 5)
        score -= penalty
        warnings.append(f"Below minimum hours ({hours}h < {min_h}h required)")
    elif hours > max_h:
        # Above maximum - moderate penalty
        excess = hours - max_h
        penalty = min(20, excess * 3)
        score -= penalty
        warnings.append(f"Above maximum hours ({hours}h > {max_h}h typical)")
    elif ideal_min <= hours <= ideal_max:
        # In ideal range - bonus
        score += 20
        reasons.append(f"Ideal hours match ({hours}h in {ideal_min}-{ideal_max}h sweet spot)")
    else:
        # In acceptable range but not ideal
        score += 10
        reasons.append(f"Acceptable hours ({hours}h within {min_h}-{max_h}h range)")

    # ==========================================================================
    # EXPERIENCE MATCH (±15 points)
    # ==========================================================================
    years_structured = profile.get("training_history", {}).get("years_structured", 0)
    try:
        years_structured = int(years_structured) if years_structured else 0
    except (ValueError, TypeError):
        years_structured = 0

    exp_required = methodology["experience_required"]

    if exp_required == "advanced" and years_structured < 3:
        score -= 15
        warnings.append(f"Requires advanced experience ({years_structured} years may be insufficient)")
    elif exp_required == "intermediate" and years_structured < 1:
        score -= 10
        warnings.append(f"Requires intermediate experience (new to structured training)")
    elif exp_required == "beginner":
        score += 5
        reasons.append("Beginner-friendly methodology")
    elif years_structured >= 3 and exp_required != "advanced":
        score += 5
        reasons.append("Experience exceeds requirements")

    # ==========================================================================
    # STRESS/LIFESTYLE MATCH (±15 points)
    # ==========================================================================
    stress_level = profile.get("health_factors", {}).get("stress_level", "moderate")
    sleep_hours = profile.get("health_factors", {}).get("sleep_hours_avg", 7)
    work_hours = profile.get("work", {}).get("hours_per_week") or 0

    method_stress_tolerance = methodology["stress_tolerance"]

    # High life stress needs stress-tolerant methodology
    if stress_level in ["high", "very_high"]:
        if method_stress_tolerance in ["very_high", "high", "variable"]:
            score += 10
            reasons.append("Handles high life stress well")
        elif method_stress_tolerance == "low":
            score -= 15
            warnings.append("High training stress may conflict with high life stress")

    # Low sleep impacts recovery
    if sleep_hours < 6.5:
        if method_stress_tolerance in ["very_high", "high"]:
            score += 5
            reasons.append("Recovery-friendly for low sleep")
        else:
            score -= 5
            warnings.append("Low sleep may limit recovery from training stress")

    # ==========================================================================
    # SCHEDULE FLEXIBILITY MATCH (±10 points)
    # ==========================================================================
    # Check for schedule variability indicators
    travel_frequency = profile.get("schedule_constraints", {}).get("travel_frequency", "none")
    work_schedule = profile.get("schedule_constraints", {}).get("work_schedule", "9-5")
    family_commitments = profile.get("schedule_constraints", {}).get("family_commitments", "")

    needs_flexibility = (
        travel_frequency in ["frequent", "multi"] or
        work_schedule == "variable" or
        bool(family_commitments)
    )

    method_flexibility = methodology["schedule_flexibility"]

    if needs_flexibility:
        if method_flexibility in ["very_high", "high"]:
            score += 10
            reasons.append("Flexible enough for variable schedule")
        elif method_flexibility == "low":
            score -= 10
            warnings.append("Requires consistent schedule execution")

    # ==========================================================================
    # RACE DEMANDS MATCH (±15 points)
    # ==========================================================================
    race_distance = race_demands.get("distance_miles", 100)
    race_duration_hrs = race_demands.get("duration_hours", 8)
    terrain_technical = race_demands.get("technical_difficulty", "moderate")
    has_repeated_surges = race_demands.get("repeated_surges", False)

    best_for = methodology["best_for"]
    not_for = methodology["not_for"]

    # Ultra/long events
    if race_distance >= 150 or race_duration_hrs >= 10:
        if "long_events" in best_for or "durability" in best_for:
            score += 15
            reasons.append("Excellent for ultra-distance events")
        elif "ultra_endurance" in not_for or "short_events" in best_for:
            score -= 15
            warnings.append("Not designed for ultra-distance events")

    # Time-crunched with short event
    if hours <= 6:
        if "time_crunched" in best_for:
            score += 10
            reasons.append("Designed for time-crunched athletes")

    # Surge repeatability (crits, technical terrain)
    if has_repeated_surges or terrain_technical in ["high", "very_high"]:
        if methodology.get("name") in ["Critical Power / W'", "HIIT-Focused"]:
            score += 10
            reasons.append("Good for repeated surge demands")

    # ==========================================================================
    # GOAL TYPE MATCH (±10 points)
    # ==========================================================================
    goal_type = profile.get("target_race", {}).get("goal_type", "finish")

    if goal_type == "podium":
        if methodology["experience_required"] == "advanced":
            score += 5
            reasons.append("Advanced methodology for podium goals")
        elif "time_crunched" in best_for:
            score -= 10
            warnings.append("Time-crunched approach may limit podium potential")
        # Zero high-intensity allocation cannot produce podium fitness.
        # Without this, a podium-chasing Cat 3 scored MAF / Low-HR at 100
        # ("beginner-friendly", "finish-focused") over Polarized.
        # (intensity_distribution is a free-text string for some
        # methodologies — only dicts carry a usable z4_z5 number.)
        _dist = methodology.get("intensity_distribution", {})
        z4_z5 = _dist.get("z4_z5", 0.1) if isinstance(_dist, dict) else 0.1
        if z4_z5 <= 0.0:
            score -= 20
            warnings.append(
                "Zero-intensity methodology conflicts with podium goal"
            )
    elif goal_type == "finish":
        if "recovery_friendly" in best_for or "beginner" in methodology["experience_required"]:
            score += 5
            reasons.append("Appropriate for finish-focused goal")
        # First-timers / finishers belong on the base-heavy Traditional path
        # (build the engine before tuning it) — boost it for low-experience
        # finish goals so it wins over the more intensity-forward options.
        if "first_timers" in best_for and years_structured <= 2:
            score += 12
            reasons.append("Base-heavy build suits a first-timer finish goal")

    # ==========================================================================
    # ATHLETE PREFERENCES (±10 points)
    # ==========================================================================
    prefs = profile.get("methodology_preferences", {})
    past_success = prefs.get("past_success_with", "").lower()
    past_failure = prefs.get("past_failure_with", "").lower()

    method_name_lower = method_name.lower()

    if past_success:
        if any(kw in method_name_lower for kw in past_success.split()):
            score += 10
            reasons.append("Past success with this approach")

    if past_failure:
        # Split on semicolons (multiple failures) and individual words
        failure_terms = []
        for segment in past_failure.split(';'):
            failure_terms.extend(segment.strip().lower().split())
        if any(kw in method_name_lower for kw in failure_terms if len(kw) > 2):
            score -= 50
            warnings.append(f"VETO: Athlete explicitly rejected this approach ('{past_failure}')")

    # ==========================================================================
    # SPECIAL CONDITIONS
    # ==========================================================================
    # Winter/indoor start
    indoor_tolerance = profile.get("training_environment", {}).get("indoor_riding_tolerance", "")
    if indoor_tolerance in ["love_it", "tolerate_it"]:
        if methodology.get("name") == "Reverse Periodization":
            score += 5
            reasons.append("Good for indoor-heavy early training")

    # Masters athletes
    age = profile.get("health_factors", {}).get("age") or profile.get("age")
    dist = methodology.get("intensity_distribution")
    z1z2 = dist.get("z1_z2") if isinstance(dist, dict) else None
    z4z5 = dist.get("z4_z5") if isinstance(dist, dict) else None

    if age and age >= 50:
        if methodology["stress_tolerance"] in ["very_high", "high", "variable"]:
            score += 10
            reasons.append("Recovery-friendly for masters athletes")
        # MEDICAL SAFETY: steer masters away from very-hard methodologies.
        # A 50%+-hard plan (HIIT-Focused) for a masters returner is an
        # overtraining/injury risk and a coaching-liability flag.
        if z4z5 is not None and z4z5 >= 0.30:
            penalty = 25 if z4z5 >= 0.45 else 15
            score -= penalty
            warnings.append(
                f"High-intensity load ({z4z5*100:.0f}% hard) is aggressive for a masters athlete")

    # DELIVERABILITY: the block-builder enforces 2-3 intensity days/week +
    # VO2max every 14 days (CRITICAL compliance rules), so the plan it emits
    # is always ~70-85% easy by time. Methodologies whose distribution falls
    # outside that band can't be faithfully delivered — the guide would claim
    # a distribution the workouts don't match (the avatar judge's recurring
    # Zone-Distribution failure). Down-rank the undeliverable extremes.
    if z1z2 is not None:
        if z1z2 >= 0.90:        # e.g. MAF/LT1 95% easy — builder injects required intensity
            score -= 20
            warnings.append("Near-zero-intensity distribution not deliverable under compliance rules")
        elif z4z5 is not None and z4z5 >= 0.40:  # e.g. HIIT 50% hard — builder caps intensity
            score -= 20
            warnings.append("Very-high-intensity distribution not deliverable under compliance rules")
    elif not isinstance(dist, dict):
        # Adaptive/readiness/block-dependent distributions can't be faithfully
        # delivered by the fixed-calendar builder either — prefer a concrete,
        # deliverable methodology.
        score -= 15
        warnings.append("Adaptive distribution not deliverable by the calendar-based builder")

    # Coming off injury
    coming_off_injury = profile.get("recent_training", {}).get("coming_off_injury", False)
    if coming_off_injury:
        if "injury_return" in best_for or "base_rebuild" in best_for:
            score += 15
            reasons.append("Appropriate for return from injury")
        elif methodology["stress_tolerance"] == "low":
            score -= 10
            warnings.append("High-stress approach may not suit injury return")

    # ==========================================================================
    # BUILD CONFIGURATION
    # ==========================================================================
    # Normalize the distribution to a dict so every downstream consumer
    # (guide, coaching brief, preview) can rely on .get() — adaptive
    # methodologies use string descriptors otherwise.
    _norm_dist = methodology["intensity_distribution"]
    if not isinstance(_norm_dist, dict) or "z1_z2" not in _norm_dist:
        # builder's real, deliverable shape (polarized-ish)
        _norm_dist = {"z1_z2": 0.80, "z3": 0.05, "z4_z5": 0.15}

    configuration = {
        "methodology": methodology["name"],
        "intensity_distribution": _norm_dist,
        # Honest qualitative description of what the plan actually emphasizes —
        # the guide leads with this, not aspirational exact percentages.
        "emphasis": methodology.get("emphasis", ""),
        "strength_approach": methodology["strength_approach"],
        "key_workouts": methodology["key_workouts"],
        "progression_style": methodology["progression_style"],
        "testing_frequency": methodology["testing_frequency"]
    }

    # Clamp score to 0-100
    score = max(0, min(100, score))

    return MethodologyCandidate(
        name=methodology["name"],
        score=score,
        reasons=reasons,
        warnings=warnings,
        configuration=configuration
    )


def select_methodology(
    profile: Dict,
    derived: Dict,
    race_data: Optional[Dict] = None
) -> Dict:
    """
    Select optimal training methodology for an athlete.

    Args:
        profile: Athlete profile dict
        derived: Derived classifications dict
        race_data: Optional race-specific data

    Returns:
        Dict with selected methodology, score, reasoning, and configuration
    """
    # Build race demands from race data or profile
    race_demands = {}

    if race_data:
        race_demands = {
            "distance_miles": race_data.get("distance_miles", 100),
            "duration_hours": race_data.get("duration_hours", 8),
            "technical_difficulty": race_data.get("race_characteristics", {}).get("technical_difficulty", "moderate"),
            "repeated_surges": race_data.get("race_characteristics", {}).get("repeated_surges", False),
            "altitude_feet": race_data.get("race_metadata", {}).get("avg_elevation_feet", 0)
        }
    else:
        # Extract from profile
        target_race = profile.get("target_race", {})
        race_demands = {
            "distance_miles": target_race.get("distance_miles", 100),
            "duration_hours": 8,  # Default estimate
            "technical_difficulty": "moderate",
            "repeated_surges": False,
            "altitude_feet": 0
        }

    # Score all methodologies
    candidates = []
    for method_id, methodology in METHODOLOGIES.items():
        candidate = calculate_methodology_score(
            methodology, profile, derived, race_demands
        )
        candidates.append((method_id, candidate))

    # Sort by score descending
    candidates.sort(key=lambda x: x[1].score, reverse=True)

    # Select top methodology
    selected_id, selected = candidates[0]

    # Get runner-up for comparison
    runner_up_id, runner_up = candidates[1] if len(candidates) > 1 else (None, None)

    # Build result
    result = {
        "selected_methodology": selected.name,
        "methodology_id": selected_id,
        "score": selected.score,
        "reasons": selected.reasons,
        "warnings": selected.warnings,
        "configuration": selected.configuration,
        "alternatives": [
            {
                "name": c.name,
                "score": c.score,
                "key_reason": c.reasons[0] if c.reasons else "Viable alternative"
            }
            for _, c in candidates[1:4]  # Top 3 alternatives
        ],
        "selection_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Add recommendation confidence
    if selected.score >= 75:
        result["confidence"] = "high"
        result["confidence_note"] = "Strong match for athlete profile"
    elif selected.score >= 60:
        result["confidence"] = "moderate"
        result["confidence_note"] = "Good match with some considerations"
    else:
        result["confidence"] = "low"
        result["confidence_note"] = "Review warnings and consider alternatives"

    return result


def get_methodology_details(methodology_id: str) -> Dict:
    """Get full details for a methodology."""
    return METHODOLOGIES.get(methodology_id, {})


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python select_methodology.py <athlete_id>")
        print("\nThis script selects the optimal training methodology based on:")
        print("  - Available training hours")
        print("  - Training experience")
        print("  - Lifestyle factors (stress, schedule variability)")
        print("  - Race demands (distance, duration, terrain)")
        print("  - Athlete preferences")
        print("\nMethodologies available:")
        for method_id, method in METHODOLOGIES.items():
            print(f"  • {method['name']}: {method['description']}")
        sys.exit(1)

    athlete_id = sys.argv[1]

    # Load profile and derived
    profile_path = get_athlete_file(athlete_id, "profile.yaml")
    derived_path = get_athlete_file(athlete_id, "derived.yaml")

    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    derived = {}
    if derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)

    # Select methodology
    result = select_methodology(profile, derived)

    # Save result
    methodology_path = get_athlete_file(athlete_id, "methodology.yaml")
    with open(methodology_path, 'w') as f:
        yaml.dump(result, f, default_flow_style=False, sort_keys=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Methodology Selection: {athlete_id}")
    print(f"{'='*60}\n")

    print(f"✅ SELECTED: {result['selected_methodology']}")
    print(f"   Score: {result['score']}/100 ({result['confidence']} confidence)")
    print(f"   {result['confidence_note']}")
    print()

    if result['reasons']:
        print("📋 Reasons:")
        for reason in result['reasons']:
            print(f"   • {reason}")
        print()

    if result['warnings']:
        print("⚠️  Warnings:")
        for warning in result['warnings']:
            print(f"   • {warning}")
        print()

    print("🔄 Alternatives:")
    for alt in result['alternatives']:
        print(f"   • {alt['name']} ({alt['score']}/100) - {alt['key_reason']}")
    print()

    print(f"💾 Saved to: {methodology_path}")


if __name__ == "__main__":
    main()
