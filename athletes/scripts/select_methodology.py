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

import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MethodologyCandidate:
    """Represents a candidate methodology with scoring."""
    name: str
    score: float
    reasons: List[str]
    warnings: List[str]
    configuration: Dict


# Methodology definitions with selection criteria
METHODOLOGIES = {
    "traditional_pyramidal": {
        "name": "Traditional (Pyramidal)",
        "description": "Build large aerobic base, then sharpen with intensity",
        "philosophy": "Volume → intensity → density → specificity",
        "min_hours": 10,
        "max_hours": 30,
        "ideal_hours": (12, 20),
        "best_for": ["long_events", "durability", "predictable_performance"],
        "not_for": ["time_crunched", "short_events", "low_volume"],
        "experience_required": "intermediate",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "moderate",
        "intensity_distribution": {"z1_z2": 0.75, "z3": 0.15, "z4_z5": 0.10},
        "strength_approach": "heavy_base_maintenance_build",
        "key_workouts": ["long_z2", "tempo_progression", "threshold_intervals"],
        "progression_style": "volume_then_intensity",
        "testing_frequency": "phase_end"
    },

    "polarized_80_20": {
        "name": "Polarized (80/20)",
        "description": "Most training easy, small amount very hard, minimal middle zone",
        "philosophy": "Hard/easy separation maximizes adaptation",
        "min_hours": 8,
        "max_hours": 20,
        "ideal_hours": (10, 15),
        "best_for": ["tolerance_building", "recovery_friendly", "structured_athletes"],
        "not_for": ["very_low_volume", "sprint_specialists"],
        "experience_required": "intermediate",
        "stress_tolerance": "high",  # Handles life stress well
        "schedule_flexibility": "moderate",
        "intensity_distribution": {"z1_z2": 0.80, "z3": 0.00, "z4_z5": 0.20},
        "strength_approach": "year_round_heavy_explosive",
        "key_workouts": ["long_z2", "vo2max_intervals", "threshold_repeats"],
        "progression_style": "increase_hard_work_maintain_ratio",
        "testing_frequency": "4_6_weeks"
    },

    "sweet_spot_threshold": {
        "name": "Sweet Spot / Threshold",
        "description": "Emphasize sub-threshold intervals to maximize FTP",
        "philosophy": "Time-efficient threshold focus",
        "min_hours": 6,
        "max_hours": 12,
        "ideal_hours": (7, 10),
        "best_for": ["ftp_gains", "time_efficient", "indoor_training"],
        "not_for": ["ultra_endurance", "durability_focus"],
        "experience_required": "beginner",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "high",  # Works with variable schedules
        "intensity_distribution": {"z1_z2": 0.50, "z3": 0.35, "z4_z5": 0.15},
        "strength_approach": "optional_short_efficient",
        "key_workouts": ["sweet_spot_intervals", "over_unders", "tempo_blocks"],
        "progression_style": "increase_density",
        "testing_frequency": "4_6_weeks"
    },

    "hiit_focused": {
        "name": "HIIT-Focused",
        "description": "Frequent maximal intervals, minimal volume",
        "philosophy": "Leverage high-intensity stimulus with minimal time",
        "min_hours": 3,
        "max_hours": 6,
        "ideal_hours": (4, 6),
        "best_for": ["time_crunched", "short_events", "existing_fitness"],
        "not_for": ["beginners", "ultra_endurance", "durability_building"],
        "experience_required": "intermediate",  # Must have base fitness
        "stress_tolerance": "low",  # High neural/metabolic stress
        "schedule_flexibility": "high",
        "intensity_distribution": {"z1_z2": 0.30, "z3": 0.20, "z4_z5": 0.50},
        "strength_approach": "crucial_max_power",
        "key_workouts": ["vo2max_intervals", "tabata", "sprint_repeats"],
        "progression_style": "increase_intensity_not_volume",
        "testing_frequency": "block_end"
    },

    "block_periodization": {
        "name": "Block Periodization",
        "description": "Target one capacity intensely per block, then shift focus",
        "philosophy": "Concentrated overload → consolidation → next capacity",
        "min_hours": 10,
        "max_hours": 25,
        "ideal_hours": (12, 18),
        "best_for": ["limiter_fixing", "advanced_athletes", "specific_goals"],
        "not_for": ["beginners", "many_races", "inconsistent_schedule"],
        "experience_required": "advanced",
        "stress_tolerance": "high",
        "schedule_flexibility": "low",  # Needs consistent execution
        "intensity_distribution": "block_dependent",
        "strength_approach": "separate_block",
        "key_workouts": ["block_specific"],
        "progression_style": "overload_consolidation_staircase",
        "testing_frequency": "block_end"
    },

    "reverse_periodization": {
        "name": "Reverse Periodization",
        "description": "Intensity early, volume later",
        "philosophy": "Build top-end first, then extend durability",
        "min_hours": 6,
        "max_hours": 15,
        "ideal_hours": (8, 12),
        "best_for": ["winter_constrained", "short_leadup", "indoor_start"],
        "not_for": ["ultra_events", "big_base_needed"],
        "experience_required": "intermediate",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "moderate",
        "intensity_distribution": {"early": {"z4_z5": 0.30}, "late": {"z1_z2": 0.75}},
        "strength_approach": "early_max_then_maintenance",
        "key_workouts": ["early_vo2max", "late_long_rides"],
        "progression_style": "intensity_then_volume",
        "testing_frequency": "transition_points"
    },

    "autoregulated_hrv": {
        "name": "Autoregulated (HRV-Based)",
        "description": "Use daily readiness to adjust intensity/volume",
        "philosophy": "Train hard when ready, back off when not",
        "min_hours": 6,
        "max_hours": 20,
        "ideal_hours": (8, 15),
        "best_for": ["variable_stress", "masters", "recovery_sensitive"],
        "not_for": ["rigid_schedule", "beginners_needing_structure"],
        "experience_required": "intermediate",
        "stress_tolerance": "variable",  # Adapts to stress
        "schedule_flexibility": "very_high",
        "intensity_distribution": "readiness_dependent",
        "strength_approach": "autoregulated_heavy_when_ready",
        "key_workouts": ["readiness_driven"],
        "progression_style": "guided_by_readiness",
        "testing_frequency": "green_days"
    },

    "maf_low_hr": {
        "name": "MAF / Low-HR (LT1)",
        "description": "Build aerobic engine by staying under LT1",
        "philosophy": "Aerobic base through constrained low intensity",
        "min_hours": 8,
        "max_hours": 20,
        "ideal_hours": (10, 15),
        "best_for": ["base_rebuild", "injury_return", "fat_adaptation"],
        "not_for": ["need_quick_gains", "time_crunched"],
        "experience_required": "beginner",
        "stress_tolerance": "very_high",  # Very low stress training
        "schedule_flexibility": "high",
        "intensity_distribution": {"z1_z2": 0.95, "z3": 0.05, "z4_z5": 0.00},
        "strength_approach": "foundational_mobility_durability",
        "key_workouts": ["long_z2_hr_capped", "aerobic_strides"],
        "progression_style": "duration_at_hr_cap",
        "testing_frequency": "3_4_weeks"
    },

    "goat_composite": {
        "name": "GOAT (Gravel Optimized Adaptive Training)",
        "description": "Integrates pyramidal base, polarized weeks, limiter blocks, autoregulation",
        "philosophy": "Best of all approaches, adapted to athlete and phase",
        "min_hours": 8,
        "max_hours": 25,
        "ideal_hours": (10, 18),
        "best_for": ["most_athletes", "flexible_adaptive", "gravel_specific"],
        "not_for": ["pure_intuitive", "refuse_monitoring"],
        "experience_required": "intermediate",
        "stress_tolerance": "moderate",
        "schedule_flexibility": "high",
        "intensity_distribution": "phase_adaptive",
        "strength_approach": "integrated_year_round",
        "key_workouts": ["phase_specific_rotating"],
        "progression_style": "block_polarized_volume_modulation",
        "testing_frequency": "signal_triggered"
    }
}


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
    elif goal_type == "finish":
        if "recovery_friendly" in best_for or "beginner" in methodology["experience_required"]:
            score += 5
            reasons.append("Appropriate for finish-focused goal")

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
        if any(kw in method_name_lower for kw in past_failure.split()):
            score -= 10
            warnings.append("Past failure with this approach")

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
    age = profile.get("health_factors", {}).get("age")
    if age and age >= 50:
        if methodology["stress_tolerance"] in ["very_high", "high", "variable"]:
            score += 10
            reasons.append("Recovery-friendly for masters athletes")

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
    configuration = {
        "methodology": methodology["name"],
        "intensity_distribution": methodology["intensity_distribution"],
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
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")

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
    methodology_path = Path(f"athletes/{athlete_id}/methodology.yaml")
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
