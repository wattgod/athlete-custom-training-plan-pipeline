#!/usr/bin/env python3
"""
Fueling Calculations Module

Generates personalized race-day fueling guidance based on:
- Athlete body composition (weight, sex)
- Race demands (distance, duration, elevation)
- Gut training progression throughout plan phases
- Real-world cycling energy expenditure data

Key outputs:
- Hourly carbohydrate targets (g/hr)
- Total carbohydrate targets for race
- Phase-by-phase gut training progression
- Fueling timeline and product recommendations

Based on sports nutrition research:
- 60-90g/hr carbs for trained athletes in events >2.5hrs
- ~0.42-0.60 kcal/kg/km base calorie rates for gravel cycling
- Gut training required to absorb high carb rates
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml


# =============================================================================
# CALORIE CALCULATION CONSTANTS
# =============================================================================

# Base calorie rates per kg body weight per km
# Validated against real-world data: 75kg rider, 75mi = ~4,500 kcal
# These rates account for rolling resistance, elevation, and typical gravel conditions
CALORIE_RATES = {
    "male": {
        "base": 0.50,      # kcal/kg/km baseline
        "min": 0.42,       # Flat, tailwind, efficient
        "max": 0.60        # Hilly, headwind, technical
    },
    "female": {
        "base": 0.45,      # Slightly lower metabolic rate
        "min": 0.38,
        "max": 0.55
    }
}

# Elevation adjustment: additional kcal per 1000ft of climbing per kg
ELEVATION_ADJUSTMENT_PER_1000FT = 0.02  # kcal/kg/km per 1000ft elevation

# Duration adjustment: metabolic efficiency decreases over time
DURATION_ADJUSTMENTS = {
    "under_4h": 0.95,      # Fresh, efficient
    "4_to_8h": 1.00,       # Baseline
    "8_to_12h": 1.05,      # Fatigue sets in
    "over_12h": 1.10       # Significant fatigue penalty
}


# =============================================================================
# CARBOHYDRATE TARGET CONSTANTS
# =============================================================================

# Hourly carb targets by goal/intensity (g/hr)
HOURLY_CARB_TARGETS = {
    "survival": {
        "target": 60,
        "range": [50, 70],
        "description": "Minimum effective dose for endurance events"
    },
    "finish": {
        "target": 70,
        "range": [60, 80],
        "description": "Solid fueling for completing the distance"
    },
    "compete": {
        "target": 80,
        "range": [70, 90],
        "description": "Competitive fueling to maintain race pace"
    },
    "podium": {
        "target": 90,
        "range": [80, 100],
        "description": "Maximum absorption for elite performance"
    }
}

# Gut training progression by phase (g/hr targets during training)
GUT_TRAINING_PHASES = {
    "base": {
        "weeks": "1-6",
        "target_range": [40, 50],
        "description": "Build tolerance - start conservative",
        "guidance": "Practice fueling on ALL rides over 90 minutes. Start with familiar products."
    },
    "build": {
        "weeks": "7-14",
        "target_range": [50, 70],
        "description": "Increase absorption capacity",
        "guidance": "Gradually increase carb intake on long rides. Test race-day products."
    },
    "peak": {
        "weeks": "15-18",
        "target_range": [60, 80],
        "description": "Race-rate practice",
        "guidance": "Simulate race fueling on long rides. Lock in your race-day products."
    },
    "race": {
        "weeks": "Race day",
        "target_range": [70, 90],
        "description": "Execute your fueling plan",
        "guidance": "Stick to the plan. Nothing new on race day."
    }
}


# =============================================================================
# CALORIE CALCULATION FUNCTIONS
# =============================================================================

def estimate_race_duration(distance_miles: float, goal_type: str, elevation_feet: int = 0) -> float:
    """
    Estimate race duration in hours based on distance, goal, and terrain.

    Args:
        distance_miles: Race distance in miles
        goal_type: "survival", "finish", "compete", or "podium"
        elevation_feet: Total elevation gain

    Returns:
        Estimated duration in hours
    """
    # Base speeds by goal type (mph)
    base_speeds = {
        "survival": 10.0,
        "finish": 12.0,
        "compete": 14.0,
        "podium": 16.0
    }

    base_speed = base_speeds.get(goal_type, 12.0)

    # Elevation penalty: reduce speed by 1mph per 5000ft of climbing per 100 miles
    elevation_penalty = (elevation_feet / 5000) * (100 / max(distance_miles, 50)) * 1.0
    adjusted_speed = max(8.0, base_speed - elevation_penalty)

    duration_hours = distance_miles / adjusted_speed

    return round(duration_hours, 1)


def calculate_race_calories(
    weight_kg: float,
    sex: str,
    distance_miles: float,
    elevation_feet: int = 0,
    duration_hours: Optional[float] = None,
    goal_type: str = "finish"
) -> Dict:
    """
    Calculate estimated calorie expenditure for a race.

    Uses validated rates: ~0.42-0.60 kcal/kg/km for gravel cycling.
    Example validation: 75kg male, 75mi (121km) = 0.50 * 75 * 121 = 4,538 kcal

    Args:
        weight_kg: Athlete weight in kg
        sex: "male" or "female"
        distance_miles: Race distance in miles
        elevation_feet: Total elevation gain
        duration_hours: Estimated duration (calculated if not provided)
        goal_type: "survival", "finish", "compete", or "podium"

    Returns:
        Dict with calorie estimates and breakdown
    """
    # Convert distance to km
    distance_km = distance_miles * 1.60934

    # Get base rate for sex
    rates = CALORIE_RATES.get(sex, CALORIE_RATES["male"])
    base_rate = rates["base"]

    # Elevation adjustment
    elevation_adjustment = (elevation_feet / 1000) * ELEVATION_ADJUSTMENT_PER_1000FT
    adjusted_rate = base_rate + elevation_adjustment

    # Duration-based adjustment
    if duration_hours is None:
        duration_hours = estimate_race_duration(distance_miles, goal_type, elevation_feet)

    if duration_hours < 4:
        duration_factor = DURATION_ADJUSTMENTS["under_4h"]
    elif duration_hours < 8:
        duration_factor = DURATION_ADJUSTMENTS["4_to_8h"]
    elif duration_hours < 12:
        duration_factor = DURATION_ADJUSTMENTS["8_to_12h"]
    else:
        duration_factor = DURATION_ADJUSTMENTS["over_12h"]

    adjusted_rate *= duration_factor

    # Clamp to min/max
    adjusted_rate = max(rates["min"], min(rates["max"], adjusted_rate))

    # Calculate total calories
    total_calories = adjusted_rate * weight_kg * distance_km

    # Calculate per-hour rate
    calories_per_hour = total_calories / duration_hours if duration_hours > 0 else 0

    return {
        "total_calories": round(total_calories),
        "calories_per_hour": round(calories_per_hour),
        "rate_kcal_kg_km": round(adjusted_rate, 3),
        "duration_hours": duration_hours,
        "distance_km": round(distance_km, 1),
        "weight_kg": weight_kg,
        "breakdown": {
            "base_rate": rates["base"],
            "elevation_adjustment": round(elevation_adjustment, 3),
            "duration_factor": duration_factor,
            "final_rate": round(adjusted_rate, 3)
        }
    }


# =============================================================================
# CARBOHYDRATE TARGET FUNCTIONS
# =============================================================================

def get_hourly_carb_target(goal_type: str = "finish") -> Dict:
    """
    Get recommended hourly carbohydrate target based on goal.

    Args:
        goal_type: "survival", "finish", "compete", or "podium"

    Returns:
        Dict with target, range, and description
    """
    return HOURLY_CARB_TARGETS.get(goal_type, HOURLY_CARB_TARGETS["finish"])


def calculate_total_carb_target(
    duration_hours: float,
    goal_type: str = "finish"
) -> Dict:
    """
    Calculate total carbohydrate target for a race.

    Args:
        duration_hours: Estimated race duration
        goal_type: "survival", "finish", "compete", or "podium"

    Returns:
        Dict with total grams and breakdown
    """
    hourly = get_hourly_carb_target(goal_type)
    target_grams = hourly["target"]
    min_grams, max_grams = hourly["range"]

    # Slight reduction in absorption capacity for very long events
    if duration_hours > 10:
        effectiveness = 0.95  # 5% reduction
    elif duration_hours > 8:
        effectiveness = 0.98
    else:
        effectiveness = 1.0

    adjusted_target = target_grams * effectiveness

    return {
        "hourly_target": round(adjusted_target),
        "hourly_range": [round(min_grams * effectiveness), round(max_grams * effectiveness)],
        "total_grams": round(adjusted_target * duration_hours),
        "total_range": [
            round(min_grams * effectiveness * duration_hours),
            round(max_grams * effectiveness * duration_hours)
        ],
        "duration_hours": duration_hours,
        "goal_type": goal_type,
        "effectiveness_factor": effectiveness
    }


def get_gut_training_phase(week: int, plan_weeks: int) -> Dict:
    """
    Get gut training guidance for a specific week.

    Args:
        week: Current week number
        plan_weeks: Total plan length

    Returns:
        Dict with phase info and guidance
    """
    # Determine phase based on plan position
    progress = week / plan_weeks

    if progress <= 0.35:
        phase = "base"
    elif progress <= 0.75:
        phase = "build"
    elif progress <= 0.95:
        phase = "peak"
    else:
        phase = "race"

    phase_info = GUT_TRAINING_PHASES[phase].copy()
    phase_info["current_week"] = week
    phase_info["plan_weeks"] = plan_weeks
    phase_info["phase_name"] = phase

    return phase_info


# =============================================================================
# FUELING CONTEXT GENERATION
# =============================================================================

def generate_fueling_context(
    profile: Dict,
    race_data: Optional[Dict] = None,
    plan_weeks: int = 12
) -> Dict:
    """
    Generate comprehensive fueling context for an athlete.

    Args:
        profile: Athlete profile dict
        race_data: Optional race-specific data
        plan_weeks: Training plan length

    Returns:
        Dict with complete fueling guidance
    """
    # Extract athlete data
    weight_kg = profile.get("fitness_markers", {}).get("weight_kg")
    sex = profile.get("fitness_markers", {}).get("sex", "male")

    # Handle missing weight
    if not weight_kg:
        # Try to get from form data
        weight_lbs = profile.get("fitness_markers", {}).get("weight_lbs")
        if weight_lbs:
            weight_kg = weight_lbs * 0.453592
        else:
            # Default assumption
            weight_kg = 75 if sex == "male" else 65

    # Extract race data
    target_race = profile.get("target_race", {})
    distance_miles = target_race.get("distance_miles", 100)
    goal_type = target_race.get("goal_type", "finish")

    if race_data:
        elevation_feet = race_data.get("elevation_feet", 0) or race_data.get("race_metadata", {}).get("elevation_feet", 0)
    else:
        elevation_feet = 0

    # Calculate duration
    duration_hours = estimate_race_duration(distance_miles, goal_type, elevation_feet)

    # Calculate calories
    calorie_data = calculate_race_calories(
        weight_kg=weight_kg,
        sex=sex,
        distance_miles=distance_miles,
        elevation_feet=elevation_feet,
        duration_hours=duration_hours,
        goal_type=goal_type
    )

    # Calculate carb targets
    carb_data = calculate_total_carb_target(duration_hours, goal_type)

    # Get gut training progression
    gut_training = []
    for week in range(1, plan_weeks + 1):
        gut_training.append(get_gut_training_phase(week, plan_weeks))

    # Build fueling timeline
    fueling_timeline = generate_fueling_timeline(
        duration_hours=duration_hours,
        hourly_carbs=carb_data["hourly_target"],
        distance_miles=distance_miles
    )

    return {
        "athlete": {
            "weight_kg": round(weight_kg, 1),
            "sex": sex
        },
        "race": {
            "distance_miles": distance_miles,
            "elevation_feet": elevation_feet,
            "duration_hours": duration_hours,
            "goal_type": goal_type
        },
        "calories": calorie_data,
        "carbohydrates": carb_data,
        "gut_training": {
            "phases": GUT_TRAINING_PHASES,
            "weekly_progression": gut_training
        },
        "fueling_timeline": fueling_timeline,
        "recommendations": generate_fueling_recommendations(
            duration_hours=duration_hours,
            hourly_carbs=carb_data["hourly_target"],
            total_carbs=carb_data["total_grams"]
        ),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def generate_fueling_timeline(
    duration_hours: float,
    hourly_carbs: int,
    distance_miles: float
) -> List[Dict]:
    """
    Generate hour-by-hour fueling timeline for race day.

    Args:
        duration_hours: Estimated race duration
        hourly_carbs: Target carbs per hour
        distance_miles: Race distance

    Returns:
        List of hourly fueling checkpoints
    """
    timeline = []
    miles_per_hour = distance_miles / duration_hours if duration_hours > 0 else 12

    for hour in range(int(duration_hours) + 1):
        mile_marker = round(hour * miles_per_hour)

        if hour == 0:
            checkpoint = {
                "hour": 0,
                "mile": 0,
                "action": "START",
                "carbs_target": 0,
                "cumulative_carbs": 0,
                "notes": "Top off with 30-50g in final 30min before start"
            }
        elif hour <= duration_hours:
            cumulative = hourly_carbs * hour
            checkpoint = {
                "hour": hour,
                "mile": min(mile_marker, distance_miles),
                "action": "FUEL",
                "carbs_target": hourly_carbs,
                "cumulative_carbs": cumulative,
                "notes": f"Target: {hourly_carbs}g carbs this hour"
            }

            # Add specific notes for race phases
            if hour <= 2:
                checkpoint["notes"] += " | Early race: establish rhythm, don't fall behind"
            elif hour >= duration_hours - 2:
                checkpoint["notes"] += " | Final push: maintain intake even if appetite drops"

        timeline.append(checkpoint)

    return timeline


def generate_fueling_recommendations(
    duration_hours: float,
    hourly_carbs: int,
    total_carbs: int
) -> Dict:
    """
    Generate product recommendations based on fueling needs.

    Args:
        duration_hours: Race duration
        hourly_carbs: Hourly carb target
        total_carbs: Total carb target

    Returns:
        Dict with product recommendations
    """
    # Calculate product quantities
    # Assume: gels ~25g, chews ~40g per pack, drink mix ~60g per bottle

    gels_needed = round(total_carbs / 25)
    chews_packs = round(total_carbs / 40)
    bottles_carb = round(total_carbs / 60)

    return {
        "hourly_target": f"{hourly_carbs}g/hr",
        "total_target": f"{total_carbs}g total",
        "example_products": {
            "gels_only": {
                "quantity": gels_needed,
                "frequency": f"1 gel every {round(60/3)}min" if hourly_carbs >= 75 else f"1 gel every {round(60/2.5)}min",
                "notes": "Simple but can cause palate fatigue"
            },
            "mixed_approach": {
                "gels": round(gels_needed * 0.4),
                "chews_packs": round(chews_packs * 0.3),
                "drink_mix_bottles": round(bottles_carb * 0.3),
                "notes": "Recommended: variety prevents palate fatigue"
            },
            "real_food_hybrid": {
                "gels": round(gels_needed * 0.3),
                "rice_cakes_bars": round(total_carbs * 0.3 / 30),  # ~30g per rice cake
                "drink_mix": round(bottles_carb * 0.4),
                "notes": "Good for ultra-distance: solid food + liquid carbs"
            }
        },
        "hydration": {
            "target_ml_per_hour": 500 + (100 if duration_hours > 6 else 0),
            "electrolytes": "500-1000mg sodium per hour depending on sweat rate",
            "notes": "Sip consistently. Don't wait until thirsty."
        },
        "pre_race": {
            "meal_timing": "3-4 hours before start",
            "meal_composition": "High carb, moderate protein, low fat/fiber",
            "example": "Oatmeal with banana, honey, and nut butter (avoid large amounts of fiber)",
            "final_top_off": "30-50g carbs 30min before start (gel or sports drink)"
        },
        "post_race": {
            "timing": "Within 30-60 minutes",
            "composition": "1.2g/kg carbs + 0.3g/kg protein",
            "example": "Chocolate milk, recovery shake, or real food meal"
        }
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python calculate_fueling.py <athlete_id>")
        print("\nThis script generates personalized fueling guidance:")
        print("  - Estimated calorie expenditure for race")
        print("  - Hourly carbohydrate targets")
        print("  - Gut training progression")
        print("  - Race-day fueling timeline")
        print("  - Product recommendations")
        sys.exit(1)

    athlete_id = sys.argv[1]

    # Load profile
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")

    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    # Load derived for plan_weeks
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")
    plan_weeks = 12
    if derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)
            plan_weeks = derived.get("plan_weeks", 12)

    # Generate fueling context
    fueling = generate_fueling_context(profile, plan_weeks=plan_weeks)

    # Save result
    fueling_path = Path(f"athletes/{athlete_id}/fueling.yaml")
    with open(fueling_path, 'w') as f:
        yaml.dump(fueling, f, default_flow_style=False, sort_keys=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Fueling Calculations: {athlete_id}")
    print(f"{'='*60}\n")

    race = fueling["race"]
    cals = fueling["calories"]
    carbs = fueling["carbohydrates"]

    print(f"🏁 Race: {race['distance_miles']} miles, ~{race['duration_hours']}h estimated")
    print(f"⚡ Energy: {cals['total_calories']:,} kcal ({cals['calories_per_hour']} kcal/hr)")
    print(f"🍞 Carbs: {carbs['hourly_target']}g/hr → {carbs['total_grams']}g total")
    print()

    print("📈 Gut Training Progression:")
    for phase, info in GUT_TRAINING_PHASES.items():
        print(f"   {phase.upper()} ({info['weeks']}): {info['target_range'][0]}-{info['target_range'][1]}g/hr")
    print()

    recs = fueling["recommendations"]
    print(f"📦 Example Fueling (mixed approach):")
    mixed = recs["example_products"]["mixed_approach"]
    print(f"   Gels: {mixed['gels']}")
    print(f"   Chews: {mixed['chews_packs']} packs")
    print(f"   Drink mix: {mixed['drink_mix_bottles']} bottles")
    print()

    print(f"💾 Saved to: {fueling_path}")


if __name__ == "__main__":
    main()
