#!/usr/bin/env python3
"""
Generate Athlete Plan

Main entry point for generating personalized training plan from athlete profile.
Integrates with unified_plan_generator from gravel-landing-page-project.
"""

import yaml
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Find gravel-landing-page-project in multiple locations
def find_generator_path():
    """Find the unified generator in various possible locations."""
    script_dir = Path(__file__).parent
    
    possible_paths = [
        # GitHub Actions: sibling directory at workspace root
        script_dir.parent.parent.parent / "gravel-landing-page-project" / "races",
        # Local: sibling directory at home level
        Path.home() / "gravel-landing-page-project" / "races",
        # PYTHONPATH (set by GitHub Actions)
        # This is handled by normal import
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "unified_plan_generator.py").exists():
            return path
    
    return None

# Add generator path to sys.path
generator_path = find_generator_path()
if generator_path:
    sys.path.insert(0, str(generator_path))
    print(f"✅ Found unified generator at: {generator_path}")

# Try to import unified generator
try:
    from unified_plan_generator import UnifiedPlanGenerator, generate_unified_plan
    UNIFIED_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Unified generator not available: {e}")
    UNIFIED_AVAILABLE = False


def load_profile(athlete_id: str) -> Dict:
    """Load athlete profile."""
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    
    with open(profile_path, 'r') as f:
        return yaml.safe_load(f)


def load_derived(athlete_id: str) -> Dict:
    """Load derived values."""
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")
    if not derived_path.exists():
        raise FileNotFoundError(f"Derived values not found. Run derive_classifications.py first.")
    
    with open(derived_path, 'r') as f:
        return yaml.safe_load(f)


def load_weekly_structure(athlete_id: str) -> Optional[Dict]:
    """Load custom weekly structure if exists."""
    structure_path = Path(f"athletes/{athlete_id}/weekly_structure.yaml")
    if structure_path.exists():
        with open(structure_path, 'r') as f:
            return yaml.safe_load(f)
    return None


def get_race_data(race_id: str) -> Dict:
    """Load race data from unified system."""
    # Try multiple locations for race data
    possible_paths = [
        generator_path / f"{race_id}.json" if generator_path else None,
        Path.home() / "gravel-landing-page-project" / "races" / f"{race_id}.json",
    ]
    
    for race_path in possible_paths:
        if race_path and race_path.exists():
            with open(race_path, 'r') as f:
                return json.load(f)
    
    # Return default race data
    return {
        "race_metadata": {
            "name": "Generic Gravel Race",
            "date": "June"
        }
    }


def generate_athlete_plan(athlete_id: str) -> Dict:
    """
    Generate personalized training plan from athlete profile.
    
    Returns generation result dict.
    """
    if not UNIFIED_AVAILABLE:
        print("⚠️  Unified generator not available - creating placeholder plan")
        # Create placeholder plan config
        output_dir = Path(f"athletes/{athlete_id}/plans/current")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        placeholder = {
            "status": "pending_generation",
            "athlete_id": athlete_id,
            "created": datetime.now().isoformat(),
            "note": "Full plan generation requires unified generator from gravel-landing-page-project"
        }
        
        with open(output_dir / "plan_config.yaml", 'w') as f:
            yaml.dump(placeholder, f, default_flow_style=False)
        
        print(f"✅ Placeholder plan created at {output_dir}")
        return {"status": "placeholder", "path": str(output_dir)}
    
    # Load data
    profile = load_profile(athlete_id)
    derived = load_derived(athlete_id)
    weekly_structure = load_weekly_structure(athlete_id)
    
    # Extract race info
    target_race = profile.get("target_race", {})
    race_id = target_race.get("race_id", "unbound_gravel_200")
    race_date = target_race.get("date", "2025-06-07")
    
    # Get race data
    race_data = get_race_data(race_id)
    
    # Create output directory
    year = datetime.now().year
    output_dir = Path(f"athletes/{athlete_id}/plans/{year}-{race_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Also create current symlink/copy
    current_dir = Path(f"athletes/{athlete_id}/plans/current")
    current_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plan using unified generator
    print(f"\n{'='*50}")
    print(f"Generating plan for {athlete_id}")
    print(f"{'='*50}")
    print(f"  Tier: {derived['tier']}")
    print(f"  Plan Weeks: {derived['plan_weeks']}")
    print(f"  Strength Frequency: {derived['strength_frequency']}x/week")
    print(f"  Race: {target_race.get('name', race_id)}")
    print(f"  Race Date: {race_date}")
    print(f"  Equipment: {derived.get('equipment_tier', 'unknown')}")
    if derived.get('exercise_exclusions'):
        print(f"  Exercise Exclusions: {len(derived['exercise_exclusions'])} exercises")
    print()
    
    # Generate plan using unified generator with athlete-specific overrides
    result = generate_unified_plan(
        race_id=race_id,
        tier_id=derived["tier"],
        plan_weeks=derived["plan_weeks"],
        race_date=race_date,
        output_dir=str(output_dir),
        race_data=race_data,
        weekly_structure_override=weekly_structure,
        exercise_exclusions=derived.get("exercise_exclusions", []),
        equipment_available=profile.get("strength_equipment", [])
    )
    
    # Save athlete-specific plan config
    plan_config = {
        "athlete_id": athlete_id,
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tier": derived["tier"],
        "plan_weeks": derived["plan_weeks"],
        "race": {
            "id": race_id,
            "name": target_race.get("name", ""),
            "date": race_date
        },
        "strength_frequency": derived["strength_frequency"],
        "exercise_exclusions": derived.get("exercise_exclusions", []),
        "equipment_tier": derived.get("equipment_tier", "unknown"),
        "key_days": derived.get("key_day_candidates", []),
        "strength_days": derived.get("strength_day_candidates", [])
    }
    
    # Save to both output_dir and current_dir
    for config_dir in [output_dir, current_dir]:
        config_path = config_dir / "plan_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(plan_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n{'='*50}")
    print(f"✅ Plan generated successfully!")
    print(f"{'='*50}")
    print(f"   Output: {output_dir}")
    print(f"   Cycling workouts: {result.get('files_generated', {}).get('cycling', 0)}")
    print(f"   Strength workouts: {result.get('files_generated', {}).get('strength', 0)}")
    
    return result


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_athlete_plan.py <athlete_id>")
        print("\nExample:")
        print("  python generate_athlete_plan.py john-doe")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    
    try:
        result = generate_athlete_plan(athlete_id)
        print("\n✅ Plan generation complete!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
