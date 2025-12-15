#!/usr/bin/env python3
"""
Generate Athlete Guide

Creates personalized training guide for athlete based on their profile and plan.
"""

import yaml
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict


def generate_athlete_guide(athlete_id: str, plan_dir: Path) -> Path:
    """
    Generate personalized training guide for athlete.
    
    Args:
        athlete_id: Athlete identifier
        plan_dir: Path to plan directory
    
    Returns:
        Path to generated guide file
    """
    # Load data
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")
    config_path = plan_dir / "plan_config.yaml"
    
    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)
    
    with open(derived_path, 'r') as f:
        derived = yaml.safe_load(f)
    
    with open(config_path, 'r') as f:
        plan_config = yaml.safe_load(f)
    
    # Build guide content
    guide_lines = []
    
    # Header
    guide_lines.append(f"# Personalized Training Plan: {profile.get('name', athlete_id)}")
    guide_lines.append("")
    guide_lines.append(f"**Generated**: {datetime.now().strftime('%B %d, %Y')}")
    guide_lines.append("")
    guide_lines.append("---")
    guide_lines.append("")
    
    # Overview
    guide_lines.append("## Plan Overview")
    guide_lines.append("")
    target_race = profile.get("target_race", {})
    if target_race:
        guide_lines.append(f"**Target Race**: {target_race.get('name', 'Unknown')}")
        guide_lines.append(f"**Race Date**: {target_race.get('date', 'Unknown')}")
        guide_lines.append(f"**Goal**: {target_race.get('goal_type', 'finish').title()}")
    guide_lines.append("")
    guide_lines.append(f"**Tier**: {derived['tier'].title()}")
    guide_lines.append(f"**Plan Duration**: {derived['plan_weeks']} weeks")
    guide_lines.append(f"**Strength Frequency**: {derived['strength_frequency']}x/week")
    guide_lines.append("")
    
    # Phase Progression
    guide_lines.append("## Phase Progression")
    guide_lines.append("")
    guide_lines.append("Your training will progress through these phases:")
    guide_lines.append("")
    guide_lines.append("1. **Base Phase** - Building aerobic foundation")
    guide_lines.append("   - Strength: Learn to Lift (movement patterns)")
    guide_lines.append("")
    guide_lines.append("2. **Build Phase** - Developing race-specific fitness")
    guide_lines.append("   - Strength: Lift Heavy Sh*t (max strength)")
    guide_lines.append("")
    guide_lines.append("3. **Peak Phase** - Sharpening and race simulation")
    guide_lines.append("   - Strength: Lift Fast (power conversion)")
    guide_lines.append("")
    guide_lines.append("4. **Taper Phase** - Arriving fresh")
    guide_lines.append("   - Strength: Don't Lose It (maintenance)")
    guide_lines.append("")
    
    # Weekly Structure
    guide_lines.append("## Your Weekly Schedule")
    guide_lines.append("")
    guide_lines.append("Based on your availability, here's your weekly structure:")
    guide_lines.append("")
    guide_lines.append("| Day | AM | PM | Notes |")
    guide_lines.append("|-----|----|----|-------|")
    
    weekly_structure_path = Path(f"athletes/{athlete_id}/weekly_structure.yaml")
    if weekly_structure_path.exists():
        with open(weekly_structure_path, 'r') as f:
            weekly_structure = yaml.safe_load(f)
        
        for day, schedule in weekly_structure.get("days", {}).items():
            am = schedule.get("am") or "—"
            pm = schedule.get("pm") or "—"
            key = "🔑" if schedule.get("is_key_day") else ""
            notes = schedule.get("notes", "")
            guide_lines.append(f"| {day.title()} {key} | {am} | {pm} | {notes} |")
    else:
        guide_lines.append("| *Weekly structure not yet generated* | | | |")
    
    guide_lines.append("")
    
    # Exercise Modifications
    exclusions = derived.get("exercise_exclusions", [])
    if exclusions:
        guide_lines.append("## Exercise Modifications")
        guide_lines.append("")
        guide_lines.append("Based on your injury history and movement limitations, ")
        guide_lines.append("the following exercises have been excluded or modified:")
        guide_lines.append("")
        for exclusion in exclusions:
            guide_lines.append(f"- {exclusion}")
        guide_lines.append("")
        guide_lines.append("Alternative exercises will be provided in your workouts.")
        guide_lines.append("")
    
    # Equipment
    guide_lines.append("## Equipment")
    guide_lines.append("")
    equipment = profile.get("strength_equipment", [])
    if equipment:
        guide_lines.append("Your plan is customized for your available equipment:")
        guide_lines.append("")
        for item in equipment:
            guide_lines.append(f"- {item.replace('_', ' ').title()}")
    else:
        guide_lines.append("Your plan uses bodyweight exercises only.")
    guide_lines.append("")
    
    # Key Days
    guide_lines.append("## Key Training Days")
    guide_lines.append("")
    key_days = derived.get("key_day_candidates", [])
    if key_days:
        guide_lines.append("Your key cycling sessions are scheduled on:")
        guide_lines.append("")
        for day in key_days:
            guide_lines.append(f"- {day.title()}")
        guide_lines.append("")
        guide_lines.append("These are your most important sessions. Prioritize these days.")
    guide_lines.append("")
    
    # Strength Days
    guide_lines.append("## Strength Training Days")
    guide_lines.append("")
    strength_days = derived.get("strength_day_candidates", [])
    if strength_days:
        guide_lines.append("Your strength sessions are scheduled on:")
        guide_lines.append("")
        for day in strength_days:
            guide_lines.append(f"- {day.title()}")
        guide_lines.append("")
        guide_lines.append("Strength sessions are placed to avoid interfering with key cycling sessions.")
    guide_lines.append("")
    
    # Risk Factors
    risk_factors = derived.get("risk_factors", [])
    if risk_factors:
        guide_lines.append("## Important Considerations")
        guide_lines.append("")
        guide_lines.append("The following factors may affect your training:")
        guide_lines.append("")
        risk_messages = {
            "low_sleep": "**Low Sleep**: Prioritize sleep for recovery. Consider reducing volume if sleep is consistently <7 hours.",
            "high_stress": "**High Stress**: Monitor recovery closely. Be flexible with training load.",
            "returning_from_injury": "**Returning from Injury**: Start conservatively. Listen to your body.",
            "new_to_structured_training": "**New to Structured Training**: Build gradually. Consistency > intensity."
        }
        for risk in risk_factors:
            if risk in risk_messages:
                guide_lines.append(f"- {risk_messages[risk]}")
        guide_lines.append("")
    
    # Next Steps
    guide_lines.append("## Next Steps")
    guide_lines.append("")
    guide_lines.append("1. Review your training calendar in the `calendar/` folder")
    guide_lines.append("2. Import ZWO files to TrainingPeaks (or your preferred platform)")
    guide_lines.append("3. Sync workouts to your bike computer/trainer")
    guide_lines.append("4. Start Week 1 on your planned start date")
    guide_lines.append("")
    guide_lines.append("**Questions?** Contact your coach or refer to the main training guide.")
    guide_lines.append("")
    
    # Write guide
    guide_path = plan_dir / "guide.md"
    with open(guide_path, 'w') as f:
        f.write("\n".join(guide_lines))
    
    return guide_path


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_athlete_guide.py <athlete_id> [plan_dir]")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    
    if len(sys.argv) >= 3:
        plan_dir = Path(sys.argv[2])
    else:
        # Find most recent plan
        plans_dir = Path(f"athletes/{athlete_id}/plans")
        if not plans_dir.exists():
            print(f"Error: No plans found for {athlete_id}")
            sys.exit(1)
        
        plan_dirs = sorted(plans_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not plan_dirs:
            print(f"Error: No plans found for {athlete_id}")
            sys.exit(1)
        
        plan_dir = plan_dirs[0]
    
    try:
        guide_path = generate_athlete_guide(athlete_id, plan_dir)
        print(f"✅ Guide generated: {guide_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

