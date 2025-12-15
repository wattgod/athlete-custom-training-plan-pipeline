#!/usr/bin/env python3
"""
Validate Athlete Profile

Checks profile completeness, validates field values, and warns on suspicious inputs.
"""

import yaml
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[1]


def validate_date(date_str: str, future_only: bool = False) -> bool:
    """Validate date format and optionally check if future."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        if future_only and date <= datetime.now():
            return False
        return True
    except ValueError:
        return False


def validate_profile(profile: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validate athlete profile.
    
    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # Section 1: Basics & Goals
    if not profile.get("name"):
        errors.append("Missing required field: name")
    
    email = profile.get("email", "")
    if not email:
        errors.append("Missing required field: email")
    elif not validate_email(email):
        errors.append(f"Invalid email format: {email}")
    
    primary_goal = profile.get("primary_goal")
    valid_goals = ["specific_race", "general_fitness", "base_building", "return_from_injury"]
    if primary_goal not in valid_goals:
        errors.append(f"Invalid primary_goal: {primary_goal}. Must be one of: {valid_goals}")
    
    # If specific_race, validate target_race
    if primary_goal == "specific_race":
        target_race = profile.get("target_race", {})
        if not target_race:
            errors.append("Missing target_race (required when primary_goal == 'specific_race')")
        else:
            if not target_race.get("name"):
                errors.append("Missing target_race.name")
            if not target_race.get("race_id"):
                errors.append("Missing target_race.race_id")
            if not target_race.get("date"):
                errors.append("Missing target_race.date")
            elif not validate_date(target_race["date"], future_only=True):
                errors.append(f"Invalid or non-future date: {target_race['date']}")
            if not target_race.get("goal_type") in ["finish", "compete", "podium"]:
                errors.append("Invalid target_race.goal_type")
    
    # Section 2: Current State
    training_history = profile.get("training_history", {})
    if not training_history:
        errors.append("Missing required section: training_history")
    else:
        if training_history.get("years_structured", 0) < 0:
            errors.append("years_structured cannot be negative")
        if training_history.get("highest_weekly_hours", 0) < 0:
            errors.append("highest_weekly_hours cannot be negative")
        if training_history.get("current_weekly_hours", 0) < 0:
            errors.append("current_weekly_hours cannot be negative")
        
        # Warnings
        if training_history.get("highest_weekly_hours", 0) > 30:
            warnings.append(f"Very high weekly hours: {training_history['highest_weekly_hours']} hours/week")
    
    # Section 3: Availability
    weekly_availability = profile.get("weekly_availability", {})
    if not weekly_availability:
        errors.append("Missing required section: weekly_availability")
    else:
        total_hours = weekly_availability.get("total_hours_available", 0)
        cycling_hours = weekly_availability.get("cycling_hours_target", 0)
        
        if total_hours <= 0:
            errors.append("total_hours_available must be > 0")
        if cycling_hours <= 0:
            errors.append("cycling_hours_target must be > 0")
        if cycling_hours > total_hours:
            errors.append("cycling_hours_target cannot exceed total_hours_available")
        
        # Warnings
        if total_hours > 30:
            warnings.append(f"Very high total hours: {total_hours} hours/week")
        if cycling_hours > 25:
            warnings.append(f"Very high cycling hours: {cycling_hours} hours/week")
    
    # Validate preferred_days
    preferred_days = profile.get("preferred_days", {})
    required_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in required_days:
        if day not in preferred_days:
            errors.append(f"Missing preferred_days.{day}")
        else:
            day_prefs = preferred_days[day]
            availability = day_prefs.get("availability")
            if availability not in ["available", "limited", "unavailable"]:
                errors.append(f"Invalid availability for {day}: {availability}")
            
            time_slots = day_prefs.get("time_slots", [])
            if availability != "unavailable" and not time_slots:
                errors.append(f"{day} marked as available/limited but no time_slots specified")
            
            max_duration = day_prefs.get("max_duration_min", 0)
            if max_duration < 0:
                errors.append(f"max_duration_min for {day} cannot be negative")
            if max_duration > 480:
                warnings.append(f"Very long max duration for {day}: {max_duration} minutes")
    
    # Section 4: Equipment
    cycling_equipment = profile.get("cycling_equipment", {})
    if not cycling_equipment:
        errors.append("Missing required section: cycling_equipment")
    
    strength_equipment = profile.get("strength_equipment", [])
    if not isinstance(strength_equipment, list):
        errors.append("strength_equipment must be a list")
    elif len(strength_equipment) == 0:
        warnings.append("No strength equipment specified - will be limited to bodyweight only")
    
    # Section 5: Health
    health_factors = profile.get("health_factors", {})
    if not health_factors:
        errors.append("Missing required section: health_factors")
    else:
        age = health_factors.get("age", 0)
        if age < 13 or age > 100:
            errors.append(f"Invalid age: {age}")
        
        sleep_hours = health_factors.get("sleep_hours_avg", 0)
        if sleep_hours < 4 or sleep_hours > 12:
            warnings.append(f"Unusual sleep hours: {sleep_hours} hours/night")
    
    # Section 6: Training Preferences
    methodology = profile.get("methodology_preferences", {})
    if methodology:
        for key in ["polarized", "pyramidal", "threshold_focused", "hiit_focused", "high_volume", "time_crunched"]:
            value = methodology.get(key)
            if value is not None and (value < 1 or value > 5):
                errors.append(f"Invalid rating for {key}: {value} (must be 1-5)")
    
    # Section 8: Admin
    plan_start = profile.get("plan_start", {})
    if plan_start:
        preferred_start = plan_start.get("preferred_start", "")
        if preferred_start and preferred_start != "next_monday":
            if not validate_date(preferred_start):
                errors.append(f"Invalid plan_start.preferred_start: {preferred_start}")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def main():
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: python validate_profile.py <athlete_id>")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    
    if not profile_path.exists():
        print(f"Error: Profile not found: {profile_path}")
        sys.exit(1)
    
    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)
    
    is_valid, errors, warnings = validate_profile(profile)
    
    print(f"\n{'='*60}")
    print(f"Profile Validation: {athlete_id}")
    print(f"{'='*60}\n")
    
    if errors:
        print("❌ ERRORS (must fix):")
        for error in errors:
            print(f"  • {error}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS (review):")
        for warning in warnings:
            print(f"  • {warning}")
        print()
    
    if is_valid:
        print("✅ Profile is valid!")
        sys.exit(0)
    else:
        print(f"❌ Profile has {len(errors)} error(s) that must be fixed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

