#!/usr/bin/env python3
"""
Derive Classifications from Athlete Profile

Auto-calculates tier, phase, exclusions, and other derived values.
"""

import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from constants import (
    DAY_ORDER_FULL,
    TIER_HOURS_AYAHUASCA_MAX,
    TIER_HOURS_FINISHER_MAX,
    TIER_HOURS_COMPETE_MAX,
)


def derive_tier(profile: Dict) -> str:
    """
    Classify athlete into tier based on responses.

    Primary factor: available cycling hours
    Modifiers: goal type, training history
    """
    hours = profile.get("weekly_availability", {}).get("cycling_hours_target", 0)
    goal = profile.get("target_race", {}).get("goal_type", "finish")
    history = profile.get("training_history", {}).get("years_structured", 0)

    # Primary factor: available hours (use centralized constants)
    if hours <= TIER_HOURS_AYAHUASCA_MAX:
        base_tier = "ayahuasca"
    elif hours <= TIER_HOURS_FINISHER_MAX:
        base_tier = "finisher"
    elif hours <= TIER_HOURS_COMPETE_MAX:
        base_tier = "compete"
    else:
        base_tier = "podium"
    
    # Modifiers based on goal and history
    if goal == "podium" and base_tier in ["finisher", "compete"]:
        # Ambitious goal but limited time - stay at base tier but note mismatch
        # Could add warning here
        pass
    
    if goal == "finish" and base_tier == "podium":
        # Lots of time but modest goal - could train as compete
        base_tier = "compete"
    
    if history < 2 and base_tier in ["compete", "podium"]:
        # New to structured training - cap at compete regardless of hours
        base_tier = "compete"
    
    return base_tier


def calculate_plan_weeks(profile: Dict) -> int:
    """Calculate plan duration in weeks."""
    target_race = profile.get("target_race")
    if not target_race or not target_race.get("date"):
        # No race date - default to 12 weeks
        return 12
    
    race_date_str = target_race["date"]
    try:
        race_date = datetime.strptime(race_date_str, "%Y-%m-%d")
    except ValueError:
        return 12
    
    # Get start date
    plan_start = profile.get("plan_start", {}).get("preferred_start", "next_monday")
    if plan_start == "next_monday":
        # Calculate next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)
    else:
        try:
            start_date = datetime.strptime(plan_start, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.now()
    
    # Calculate weeks
    delta = race_date - start_date
    weeks = max(8, min(24, delta.days // 7))  # Clamp between 8-24 weeks
    
    return weeks


def determine_starting_phase(profile: Dict) -> str:
    """
    Determine where to start in the training progression.
    
    May skip "Learn to Lift" if athlete has strength background.
    """
    current_phase = profile.get("recent_training", {}).get("current_phase", "off-season")
    strength_background = profile.get("training_history", {}).get("strength_background", "none")
    years_structured = profile.get("training_history", {}).get("years_structured", 0)
    
    # If coming from off-season or recovery, start at base_1
    if current_phase in ["off-season", "recovery"]:
        return "base_1"
    
    # If already in base phase and has strength background, might skip Learn to Lift
    if current_phase == "base" and strength_background in ["intermediate", "advanced"]:
        return "base_2"  # Skip to later base phase
    
    # If in build phase, continue from build_1
    if current_phase == "build":
        return "build_1"
    
    # Default: start at base_1
    return "base_1"


def determine_strength_frequency(profile: Dict, tier: str) -> int:
    """
    Determine strength sessions per week.
    
    Based on:
    - Tier (from hours)
    - Max sessions athlete will do
    - Strength background
    """
    max_sessions = profile.get("weekly_availability", {}).get("strength_sessions_max", 2)
    strength_background = profile.get("training_history", {}).get("strength_background", "none")
    
    # Base frequency by tier (for base phase)
    tier_frequencies = {
        "ayahuasca": 3,
        "finisher": 2,
        "compete": 2,
        "podium": 2
    }
    
    base_frequency = tier_frequencies.get(tier, 2)
    
    # Adjust based on athlete's max
    frequency = min(base_frequency, max_sessions)
    
    # If no strength background, cap at 2x/week
    if strength_background == "none" and frequency > 2:
        frequency = 2
    
    return frequency


def classify_equipment(profile: Dict) -> str:
    """Classify equipment level: minimal, moderate, full."""
    equipment = profile.get("strength_equipment", [])
    
    has_barbell = "barbell" in equipment
    has_gym = "gym_membership" in equipment
    has_squat_rack = "squat_rack" in equipment
    
    if has_gym or (has_barbell and has_squat_rack):
        return "full"
    
    has_db = "dumbbells" in equipment
    has_kb = "kettlebells" in equipment
    has_bands = "resistance_bands" in equipment
    
    if has_db or has_kb or has_bands:
        return "moderate"
    
    return "minimal"  # Bodyweight only


def get_exercise_exclusions(profile: Dict) -> List[str]:
    """
    Build list of exercises to exclude based on injuries/limitations.
    """
    exclusions = []
    
    # From current injuries
    current_injuries = profile.get("injury_history", {}).get("current_injuries", [])
    for injury in current_injuries:
        # Direct exclusions
        if injury.get("exercises_to_avoid"):
            exclusions.extend(injury["exercises_to_avoid"])
        
        # Auto-exclude based on injury area
        area = injury.get("area", "").lower()
        severity = injury.get("severity", "minor")
        
        if area == "knee" and severity != "minor":
            exclusions.extend([
                "Jump Squat",
                "Box Jump",
                "Split Squat Jump",
                "Pistol Squat",
                "Bulgarian Split Squat"  # If severe
            ])
        
        elif area == "shoulder":
            exclusions.extend([
                "Overhead Press",
                "Pike Push-Up",
                "Pull-Up",
                "Turkish Get-Up"
            ])
        
        elif area == "back" and severity != "minor":
            exclusions.extend([
                "Deadlift",
                "Good Morning",
                "Barbell Row",
                "Heavy Back Squat"
            ])
        
        elif area == "hip":
            exclusions.extend([
                "Hip Thrust",
                "Single-Leg Glute Bridge"
            ])
    
    # From movement limitations
    limitations = profile.get("movement_limitations", {})
    
    if limitations.get("deep_squat") in ["significantly_limited", "painful"]:
        exclusions.extend([
            "Pistol Squat",
            "Deep Goblet Squat",
            "Ass-to-Grass Squat"
        ])
    
    if limitations.get("overhead_reach") in ["significantly_limited", "painful"]:
        exclusions.extend([
            "Overhead Press",
            "Turkish Get-Up",
            "Overhead Carry"
        ])
    
    if limitations.get("single_leg_balance") in ["significantly_limited", "painful"]:
        exclusions.extend([
            "Single-Leg RDL",
            "Bulgarian Split Squat",
            "Pistol Squat"
        ])
    
    return list(set(exclusions))  # Deduplicate


def identify_key_days(profile: Dict) -> List[str]:
    """
    Identify best days for key cycling sessions (intervals, long rides).
    
    Criteria:
    - is_key_day_ok == true
    - availability == "available"
    - max_duration_min >= 60 (for intervals) or >= 180 (for long rides)
    """
    key_days = []
    preferred_days = profile.get("preferred_days", {})
    
    for day, prefs in preferred_days.items():
        if (prefs.get("availability") == "available" and
            prefs.get("is_key_day_ok") == True and
            prefs.get("max_duration_min", 0) >= 60):
            key_days.append(day)
    
    return key_days


def identify_strength_days(profile: Dict, strength_frequency: int, key_days: List[str]) -> List[str]:
    """
    Identify best days for strength sessions.
    
    Criteria:
    - Not within 48 hours before a key day (unless key day is long ride and strength is AM)
    - Strength OK on same day as key session if: AM strength + PM intervals, or AM strength + PM long ride
    - availability == "available" or "limited"
    - Has AM time slot (preferred) or PM
    - max_duration_min >= 30
    """
    strength_days = []
    preferred_days = profile.get("preferred_days", {})

    # Days to avoid: day before key days (48h rule)
    # Exception: If key day is Saturday (long ride) and has AM slot, strength can be AM same day
    avoid_days = set()
    for key_day in key_days:
        key_idx = DAY_ORDER_FULL.index(key_day)
        # Day before (48h rule)
        if key_idx > 0:
            avoid_days.add(DAY_ORDER_FULL[key_idx - 1])
    
    # Find candidate days
    candidates = []
    for day, prefs in preferred_days.items():
        availability = prefs.get("availability", "unavailable")
        if availability == "unavailable":
            continue
        
        max_duration = prefs.get("max_duration_min", 0)
        if max_duration < 30:
            continue
        
        time_slots = prefs.get("time_slots", [])
        if not time_slots:
            continue
        
        # Check if this is a key day
        is_key = day in key_days
        
        # If key day, strength can only be AM (before PM intervals/long ride)
        if is_key:
            if "am" not in time_slots:
                continue  # Can't do strength on key day without AM slot
            # Prefer non-key days, but allow key days if needed
            priority = 1  # Lower priority for key days
        else:
            # Non-key day - check if it's avoided (day before key)
            if day in avoid_days:
                continue
            priority = 0  # Higher priority for non-key days
        
        # Prefer days with AM slots
        has_am = "am" in time_slots
        candidates.append((day, priority, has_am, max_duration))
    
    # Sort by: priority (non-key first), then has AM slot, then max duration
    candidates.sort(key=lambda x: (x[1], not x[2], -x[3]))
    
    # Select top N
    strength_days = [day for day, _, _, _ in candidates[:strength_frequency]]
    
    return strength_days


def derive_all(profile: Dict) -> Dict:
    """
    Derive all classifications from profile.
    
    Returns dict with all derived values.
    """
    tier = derive_tier(profile)
    plan_weeks = calculate_plan_weeks(profile)
    starting_phase = determine_starting_phase(profile)
    strength_frequency = determine_strength_frequency(profile, tier)
    equipment_tier = classify_equipment(profile)
    exercise_exclusions = get_exercise_exclusions(profile)
    key_days = identify_key_days(profile)
    strength_days = identify_strength_days(profile, strength_frequency, key_days)
    
    # Risk factors
    risk_factors = []
    if profile.get("health_factors", {}).get("sleep_hours_avg", 8) < 7:
        risk_factors.append("low_sleep")
    if profile.get("health_factors", {}).get("stress_level") in ["high", "very_high"]:
        risk_factors.append("high_stress")
    if profile.get("recent_training", {}).get("coming_off_injury"):
        risk_factors.append("returning_from_injury")
    if profile.get("training_history", {}).get("years_structured", 0) < 1:
        risk_factors.append("new_to_structured_training")
    
    return {
        "tier": tier,
        "plan_weeks": plan_weeks,
        "starting_phase": starting_phase,
        "strength_frequency": strength_frequency,
        "equipment_tier": equipment_tier,
        "risk_factors": risk_factors,
        "exercise_exclusions": exercise_exclusions,
        "key_day_candidates": key_days,
        "strength_day_candidates": strength_days,
        "derived_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python derive_classifications.py <athlete_id>")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    
    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)
    
    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)
    
    derived = derive_all(profile)
    
    # Save derived values
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")
    derived_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(derived_path, 'w') as f:
        yaml.dump(derived, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Derived classifications saved to {derived_path}")
    print(f"\nDerived Values:")
    print(f"  Tier: {derived['tier']}")
    print(f"  Plan Weeks: {derived['plan_weeks']}")
    print(f"  Starting Phase: {derived['starting_phase']}")
    print(f"  Strength Frequency: {derived['strength_frequency']}x/week")
    print(f"  Equipment Tier: {derived['equipment_tier']}")
    print(f"  Exercise Exclusions: {len(derived['exercise_exclusions'])} exercises")
    print(f"  Key Days: {', '.join(derived['key_day_candidates'])}")
    print(f"  Strength Days: {', '.join(derived['strength_day_candidates'])}")

