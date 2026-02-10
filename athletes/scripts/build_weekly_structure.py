#!/usr/bin/env python3
"""
Build Custom Weekly Structure

Creates weekly structure from athlete preferences, respecting availability,
time constraints, and recovery rules.
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from constants import DAY_ORDER_FULL, get_athlete_file


def build_weekly_structure(
    preferred_days: Dict,
    key_days: List[str],
    strength_days: List[str],
    tier: str
) -> Dict:
    """
    Build custom weekly structure from athlete preferences.
    
    Args:
        preferred_days: Dict of day preferences from profile
        key_days: List of days that can handle key sessions
        strength_days: List of days for strength sessions
        tier: Athlete tier (ayahuasca, finisher, compete, podium)
    
    Returns:
        Weekly structure dict compatible with unified generator
    """
    structure = {
        "description": f"Custom weekly structure for {tier} tier",
        "days": {}
    }

    for day in DAY_ORDER_FULL:
        prefs = preferred_days.get(day, {})
        availability = prefs.get("availability", "unavailable")
        time_slots = prefs.get("time_slots", [])
        max_duration = prefs.get("max_duration_min", 0)
        is_key_ok = prefs.get("is_key_day_ok", False)
        
        # Initialize day structure
        day_struct = {
            "am": None,
            "pm": None,
            "is_key_day": False,
            "notes": "",
            "max_duration": max_duration
        }
        
        # Skip unavailable days
        if availability == "unavailable":
            structure["days"][day] = day_struct
            continue
        
        # Determine if this is a key day
        is_key = day in key_days and is_key_ok
        
        # Determine if this is a strength day
        is_strength = day in strength_days
        
        # Assign AM workout
        # Priority: Key sessions > Strength > Easy rides
        if "am" in time_slots:
            if day == "saturday" and max_duration >= 180 and is_key:
                # Saturday long ride takes priority
                day_struct["am"] = "long_ride"
                day_struct["is_key_day"] = True
                day_struct["notes"] = "Key session - long ride"
            elif is_key and not is_strength:
                # Key session (intervals) - but not if strength is scheduled
                day_struct["am"] = "intervals"
                day_struct["is_key_day"] = True
                day_struct["notes"] = "Key session - intervals or threshold"
            elif is_strength and not is_key:
                # Strength session on non-key day
                day_struct["am"] = "strength"
                day_struct["notes"] = "Strength session"
            elif is_strength and is_key:
                # Strength on key day (AM strength, PM intervals/long ride)
                day_struct["am"] = "strength"
                day_struct["notes"] = "Strength AM"
            else:
                day_struct["am"] = "easy_ride"
                day_struct["notes"] = "Easy ride or recovery"
        
        # Assign PM workout
        if "pm" in time_slots:
            # Don't double-book if AM already has a key session
            if day_struct["am"] in ["intervals", "long_ride"]:
                # PM can be easy ride or rest
                if tier in ["compete", "podium"] and day_struct["am"] == "intervals":
                    day_struct["pm"] = "easy_ride"
                    day_struct["notes"] += " + Easy spin PM"
                else:
                    day_struct["pm"] = None
            elif day_struct["am"] == "strength":
                # After strength AM, can do intervals/long ride PM if it's a key day
                if is_key:
                    if day == "saturday" and max_duration >= 180:
                        day_struct["pm"] = "long_ride"
                        day_struct["is_key_day"] = True
                        day_struct["notes"] = "Strength AM + Long ride PM"
                    else:
                        day_struct["pm"] = "intervals"
                        day_struct["is_key_day"] = True
                        day_struct["notes"] = "Strength AM + Intervals PM"
                elif max_duration >= 60:
                    # Easy ride PM after strength
                    day_struct["pm"] = "easy_ride"
                    day_struct["notes"] += " + Easy spin PM"
            elif is_key and not day_struct["is_key_day"]:
                # PM key session
                day_struct["pm"] = "intervals"
                day_struct["is_key_day"] = True
                day_struct["notes"] = "Key session - intervals PM"
            else:
                day_struct["pm"] = "easy_ride"
        
        # Special handling for Sunday (recovery day)
        if day == "sunday" and not is_key:
            # But allow strength on Sunday if it's a strength day
            if is_strength:
                day_struct["am"] = "strength"
                day_struct["notes"] = "Strength session"
            else:
                day_struct["am"] = "easy_ride_or_rest"
                day_struct["pm"] = None
                day_struct["notes"] = "Recovery day"
        
        structure["days"][day] = day_struct
    
    return structure


def main():
    """Test function."""
    if len(sys.argv) < 2:
        print("Usage: python build_weekly_structure.py <athlete_id>")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    
    # Load profile
    profile_path = get_athlete_file(athlete_id, "profile.yaml")
    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    # Load derived values
    derived_path = get_athlete_file(athlete_id, "derived.yaml")
    if not derived_path.exists():
        print(f"Error: Derived values not found. Run derive_classifications.py first.")
        sys.exit(1)

    with open(derived_path, 'r') as f:
        derived = yaml.safe_load(f)

    # Build structure
    structure = build_weekly_structure(
        preferred_days=profile.get("preferred_days", {}),
        key_days=derived.get("key_day_candidates", []),
        strength_days=derived.get("strength_day_candidates", []),
        tier=derived.get("tier", "finisher")
    )

    # Save structure
    structure_path = get_athlete_file(athlete_id, "weekly_structure.yaml")
    structure_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(structure_path, 'w') as f:
        yaml.dump(structure, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Weekly structure saved to {structure_path}")
    print(f"\nWeekly Structure:")
    for day, schedule in structure["days"].items():
        am = schedule.get("am") or "—"
        pm = schedule.get("pm") or "—"
        key = "🔑" if schedule.get("is_key_day") else ""
        print(f"  {day.title()} {key}: AM={am}, PM={pm}")


if __name__ == "__main__":
    main()

