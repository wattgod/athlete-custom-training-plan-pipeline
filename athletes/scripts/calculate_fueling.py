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

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from constants import get_athlete_file
from fueling_policy import build_fueling_prescription, tolerated_intake_from_profile


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

# Gut-training education templates. Week labels and personalized ranges are
# derived from the actual plan and canonical prescription below; this table no
# longer claims fixed BASE 1-6 / BUILD 7-14 / PEAK 15-18 bands.
GUT_TRAINING_PHASES = {
    "base": {
        "description": "Build tolerance - start conservative",
        "guidance": "Practice fueling on ALL rides over 90 minutes. Start with familiar products."
    },
    "build": {
        "description": "Increase absorption capacity",
        "guidance": "Gradually increase carb intake on long rides. Test race-day products."
    },
    "peak": {
        "description": "Race-rate practice",
        "guidance": "Simulate race fueling on long rides. Lock in your race-day products."
    },
    "taper": {
        "description": "Rehearse the settled plan",
        "guidance": "Keep familiar products and timing; reduce novelty, not consistency."
    },
    "race": {
        "description": "Execute your fueling plan",
        "guidance": "Stick to the plan. Nothing new on race day."
    }
}


# =============================================================================
# CALORIE CALCULATION FUNCTIONS
# =============================================================================

# Average speeds (mph) by discipline × goal. Road is far faster than gravel
# (smooth tarmac, drafting); using gravel speeds for a road event over-
# estimated a 96-mile road race at 8h when it's really ~5h, which then
# mis-calibrated the entire fueling plan.
_SPEED_BY_DISCIPLINE = {
    "road":   {"survival": 14.0, "finish": 16.0, "compete": 19.0, "podium": 22.0},
    "gravel": {"survival": 10.0, "finish": 12.0, "compete": 14.0, "podium": 16.0},
    "mtb":    {"survival": 7.0,  "finish": 9.0,  "compete": 11.0, "podium": 13.0},
}
_SPEED_FLOOR = {"road": 12.0, "gravel": 8.0, "mtb": 6.0}


def estimate_race_duration(distance_miles: float, goal_type: str,
                           elevation_feet: int = 0, discipline: str = "gravel") -> float:
    """
    Estimate race duration in hours based on distance, goal, terrain, and
    discipline (road events are much faster than gravel/mtb).
    """
    # A missing/zero/garbage distance must never yield a 0.0h race — that
    # anchors the entire nutrition section (carbs/hr, timeline) to a
    # zero-length event, which is nonsensical and potentially harmful.
    try:
        distance_miles = float(distance_miles)
    except (TypeError, ValueError):
        distance_miles = 0.0
    if distance_miles <= 0:
        distance_miles = 62.0  # median gravel/road event — sane fallback

    disc = (discipline or "gravel").lower()
    speeds = _SPEED_BY_DISCIPLINE.get(disc, _SPEED_BY_DISCIPLINE["gravel"])
    base_speed = speeds.get(goal_type, speeds["finish"])

    # Elevation penalty: reduce speed by 1mph per 5000ft of climbing per 100 miles
    elevation_penalty = (elevation_feet / 5000) * (100 / max(distance_miles, 50)) * 1.0
    adjusted_speed = max(_SPEED_FLOOR.get(disc, 8.0), base_speed - elevation_penalty)

    duration_hours = distance_miles / adjusted_speed

    return round(duration_hours, 1)


def calculate_race_calories(
    weight_kg: float,
    sex: str,
    distance_miles: float,
    elevation_feet: int = 0,
    duration_hours: Optional[float] = None,
    goal_type: str = "finish",
    discipline: str = "gravel"
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
        duration_hours = estimate_race_duration(distance_miles, goal_type, elevation_feet, discipline)

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
    # Legacy compatibility only. New callers must use FuelingPrescription.
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


def _phase_target_range(phase: str, prescription: Dict) -> List[int]:
    """Derive every personalized training range from one prescription."""
    target = int(prescription.get("race_target_g_per_hour") or 60)
    race_range = list(prescription.get("race_range_g_per_hour") or [target, target])
    if phase == "race":
        return [int(race_range[0]), int(race_range[1])]
    offsets = {
        "base": (20, 10),
        "lead_in": (20, 10),
        "build": (15, 5),
        "peak": (10, 0),
        "taper": (10, 0),
    }
    low_offset, high_offset = offsets.get(phase, (15, 5))
    low = max(30, target - low_offset)
    high = max(low, target - high_offset)
    return [low, high]


def get_gut_training_phase(week: int, plan_weeks: int,
                           prescription: Optional[Dict] = None) -> Dict:
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
    phase_info["week_label"] = f"W{week}"
    phase_info["plan_weeks"] = plan_weeks
    phase_info["phase_name"] = phase
    phase_info["target_range"] = _phase_target_range(
        phase, prescription or {"race_target_g_per_hour": 60})

    return phase_info


def _phase_inventory(progression: List[Dict]) -> Dict:
    inventory: Dict[str, Dict] = {}
    for week in progression:
        phase = week["phase_name"]
        entry = inventory.setdefault(phase, {
            **GUT_TRAINING_PHASES.get(
                phase, GUT_TRAINING_PHASES["base"]),
            "weeks": [],
            "target_range": week["target_range"],
        })
        entry["weeks"].append(week["week_label"])
    return inventory


def align_fueling_to_plan(athlete_dir: Path) -> Dict:
    """Rewrite gut-training labels from actual plan_dates, including W00."""
    athlete_dir = Path(athlete_dir)
    fueling_path = athlete_dir / "fueling.yaml"
    plan_dates_path = athlete_dir / "plan_dates.yaml"
    with fueling_path.open() as handle:
        fueling = yaml.safe_load(handle) or {}
    with plan_dates_path.open() as handle:
        plan_dates = yaml.safe_load(handle) or {}
    prescription = fueling.get("prescription") or {}
    paid_weeks = int(plan_dates.get("plan_weeks") or 0)
    progression = []
    for week in sorted(plan_dates.get("weeks") or [], key=lambda item: int(item.get("week", 0))):
        number = int(week.get("week", 0))
        raw_phase = str(week.get("phase") or "base").strip().lower()
        phase = "lead_in" if number == 0 else raw_phase
        template_phase = phase if phase in GUT_TRAINING_PHASES else "base"
        info = GUT_TRAINING_PHASES[template_phase].copy()
        info.update({
            "current_week": number,
            "week_label": "W00" if number == 0 else f"W{number}",
            "plan_weeks": paid_weeks,
            "phase_name": phase,
            "target_range": _phase_target_range(phase, prescription),
        })
        progression.append(info)
    fueling.setdefault("gut_training", {})["weekly_progression"] = progression
    fueling["gut_training"]["phases"] = _phase_inventory(progression)
    with fueling_path.open("w") as handle:
        yaml.dump(fueling, handle, default_flow_style=False, sort_keys=False)
    return fueling


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

    # Extract race data. A present-but-zero/None distance must NOT slip
    # through (dict.get's default only fires on a MISSING key) — fall back to
    # the race DB, then a sane default, so fueling is never anchored to 0.0h.
    target_race = profile.get("target_race", {})
    distance_miles = target_race.get("distance_miles")
    if not distance_miles or float(distance_miles) <= 0:
        rd = race_data or {}
        distance_miles = (rd.get("distance_miles")
                          or rd.get("race_metadata", {}).get("distance_miles")
                          or 100)
    goal_type = target_race.get("goal_type", "finish")
    try:
        from archetype import derive_discipline
        discipline = derive_discipline(profile)
    except Exception:
        discipline = "gravel"

    # Elevation, like distance above, must come from the athlete's target_race
    # first — the __main__ pipeline path passes no race_data, so reading only
    # race_data silently anchored fueling to 0 ft (understating race duration,
    # energy, and total carbs). Fall back to race_data, then 0.
    elevation_feet = target_race.get("elevation_ft") or target_race.get("elevation_feet")
    if not elevation_feet or float(elevation_feet) <= 0:
        rd = race_data or {}
        elevation_feet = (rd.get("elevation_feet", 0)
                          or rd.get("race_metadata", {}).get("elevation_feet", 0)
                          or 0)

    # Calculate duration (discipline-aware — road is much faster than gravel)
    duration_hours = estimate_race_duration(distance_miles, goal_type, elevation_feet, discipline)

    # Calculate calories
    calorie_data = calculate_race_calories(
        weight_kg=weight_kg,
        sex=sex,
        distance_miles=distance_miles,
        elevation_feet=elevation_feet,
        duration_hours=duration_hours,
        goal_type=goal_type,
        discipline=discipline
    )

    # One personalized prescription drives every serialized carb value.
    fitness = profile.get("fitness_markers", {})
    prescription = build_fueling_prescription(
        duration_hours=duration_hours,
        weight_kg=float(weight_kg),
        ftp_watts=fitness.get("ftp_watts"),
        goal_type=goal_type,
        gut_phase=profile.get("nutrition", {}).get("gut_training_phase", "build"),
        tolerated_g_per_hour=tolerated_intake_from_profile(profile),
        sex=sex,
    )
    p = prescription.to_dict()
    no_power = fitness.get("power_basis") == "none" or not fitness.get("ftp_watts")
    carb_data = {
        "hourly_target": p["race_target_g_per_hour"],
        "hourly_range": p["race_range_g_per_hour"],
        "total_grams": p["total_g"],
        "total_range": [round(p["race_range_g_per_hour"][0] * duration_hours),
                        round(p["race_range_g_per_hour"][1] * duration_hours)],
        "duration_hours": duration_hours,
        "goal_type": goal_type,
    }

    # Get gut training progression
    gut_training = []
    for week in range(1, plan_weeks + 1):
        gut_training.append(get_gut_training_phase(week, plan_weeks, p))

    # Build fueling timeline
    fueling_timeline = generate_fueling_timeline(
        duration_hours=duration_hours,
        hourly_carbs=carb_data["hourly_target"],
        distance_miles=distance_miles
    )

    fueling = {
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
            "phases": _phase_inventory(gut_training),
            "weekly_progression": gut_training
        },
        "fueling_timeline": fueling_timeline,
        "prescription": p,
        "fueling_basis": {
            "kind": p.get("inputs", {}).get("basis"),
            "power_used": not no_power,
            "label": (
                "Duration + intensity descriptor + body-mass bounds"
                if no_power else "Measured power + duration + body mass"
            ),
            "reanchor": fitness.get("reanchor") if no_power else None,
        },
        "recommendations": generate_fueling_recommendations(
            duration_hours=duration_hours,
            hourly_carbs=carb_data["hourly_target"],
            total_carbs=carb_data["total_grams"]
        ) | {"hydration": p["hydration"]},
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    from derived_registry import (assert_registry_covers,
                                  entry as derived_entry)
    derived_at = str(
        (profile.get('fulfillment') or {}).get('generation_at')
        or datetime.now().astimezone().isoformat()
    )
    revision = int((profile.get('fulfillment') or {}).get('generation_revision') or 1)
    policy_inputs = p.get('inputs', {})
    duration_inputs = {
        'distance_miles': distance_miles, 'elevation_feet': elevation_feet,
        'discipline': discipline, 'goal_type': goal_type,
    }

    def record(identifier, field, basis, inputs, sensitivity='sensitive'):
        return derived_entry(
            id=identifier, field=field, value_class='inferred', basis=basis,
            inputs=inputs, sensitivity=sensitivity, at=derived_at,
            revision=revision,
        )

    derived_records = [
        record('RACE_DURATION_HOURS', 'race.duration_hours',
               'race distance, elevation, discipline, and goal pace model',
               duration_inputs, 'personal'),
        record('RACE_CALORIES', 'calories',
               'body mass, modeled duration, course load, sex, and goal model',
               {**duration_inputs, 'weight_kg': weight_kg, 'sex': sex}),
        record('FUELING_HOURLY_TARGET', 'carbohydrates.hourly_target',
               str(policy_inputs.get('basis') or 'fueling policy'), policy_inputs),
        record('FUELING_HOURLY_RANGE', 'carbohydrates.hourly_range',
               'canonical fueling-policy physiological range', policy_inputs),
        record('FUELING_TOTAL_TARGET', 'carbohydrates.total_grams',
               'hourly prescription multiplied by modeled event duration',
               {'hourly_target': p['race_target_g_per_hour'],
                'duration_hours': duration_hours}),
        record('FUELING_TOTAL_RANGE', 'carbohydrates.total_range',
               'hourly prescription bounds multiplied by modeled event duration',
               {'hourly_range': p['race_range_g_per_hour'],
                'duration_hours': duration_hours}),
        record('GUT_PHASES', 'gut_training.phases',
               'plan-week inventory of the canonical gut-training progression',
               {'plan_weeks': plan_weeks, 'prescription': policy_inputs}),
        record('GUT_WEEKLY_PROGRESSION', 'gut_training.weekly_progression',
               'week-indexed canonical gut-training progression',
               {'plan_weeks': plan_weeks, 'prescription': policy_inputs}),
        record('FUELING_TIMELINE', 'fueling_timeline',
               'hourly target distributed across modeled event duration and distance',
               {'duration_hours': duration_hours,
                'hourly_target': carb_data['hourly_target'],
                'distance_miles': distance_miles}),
        record('FUELING_PRESCRIPTION', 'prescription',
               str(policy_inputs.get('basis') or 'fueling policy'), policy_inputs),
        record('FUELING_BASIS', 'fueling_basis',
               'truthful power-basis selection for fueling',
               {'power_basis': fitness.get('power_basis'),
                'ftp_present': fitness.get('ftp_watts') is not None}, 'personal'),
        record('FUELING_RECOMMENDATIONS', 'recommendations',
               'canonical prescription rendered as athlete-facing recommendations',
               {'duration_hours': duration_hours,
                'hourly_target': carb_data['hourly_target'],
                'total_carbs': carb_data['total_grams']}),
        record('HYDRATION_TARGET', 'recommendations.hydration',
               'canonical fueling-policy hydration prescription', policy_inputs),
    ]
    fueling['_derived'] = assert_registry_covers(
        fueling, derived_records,
        required_fields=[
            'race.duration_hours', 'calories',
            'carbohydrates.hourly_target', 'carbohydrates.hourly_range',
            'carbohydrates.total_grams', 'carbohydrates.total_range',
            'gut_training.phases', 'gut_training.weekly_progression',
            'fueling_timeline', 'prescription', 'fueling_basis',
            'recommendations', 'recommendations.hydration',
        ],
        revision=revision,
    )
    return fueling


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
    profile_path = get_athlete_file(athlete_id, "profile.yaml")

    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    # Load derived for plan_weeks
    derived_path = get_athlete_file(athlete_id, "derived.yaml")
    plan_weeks = 12
    if derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)
            plan_weeks = derived.get("plan_weeks", 12)

    # Generate fueling context
    fueling = generate_fueling_context(profile, plan_weeks=plan_weeks)

    # Save result
    fueling_path = get_athlete_file(athlete_id, "fueling.yaml")
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
    print("🍞 Carbs: computed — values available in authenticated review")
    print()

    print("📈 Gut Training Progression:")
    for phase, info in fueling["gut_training"]["phases"].items():
        labels = ', '.join(info['weeks'])
        print(f"   {phase.upper()} ({labels}): {info['target_range'][0]}-{info['target_range'][1]}g/hr")
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
