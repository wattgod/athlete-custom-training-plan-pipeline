#!/usr/bin/env python3
"""
Generate Athlete Plan

Main entry point for generating personalized training plan from athlete profile.
"""

import yaml
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add unified generator path (assumes it's in parent repo)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "gravel-landing-page-project" / "races"))

try:
    from unified_plan_generator import UnifiedPlanGenerator, generate_unified_plan
    UNIFIED_AVAILABLE = True
except ImportError:
    print("⚠️  Unified generator not found. Install from gravel-landing-page-project/races")
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
    race_path = Path(__file__).parent.parent.parent.parent / "gravel-landing-page-project" / "races" / f"{race_id}.json"
    
    if race_path.exists():
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
        raise RuntimeError("Unified generator not available")
    
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
    
    # Generate plan using unified generator
    print(f"Generating plan for {athlete_id}...")
    print(f"  Tier: {derived['tier']}")
    print(f"  Plan Weeks: {derived['plan_weeks']}")
    print(f"  Race: {target_race.get('name', race_id)}")
    print(f"  Race Date: {race_date}")
    print()
    
    # Note: UnifiedPlanGenerator doesn't yet support weekly_structure_override
    # This is a placeholder for future enhancement
    result = generate_unified_plan(
        race_id=race_id,
        tier_id=derived["tier"],
        plan_weeks=derived["plan_weeks"],
        race_date=race_date,
        output_dir=str(output_dir),
        race_data=race_data
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
        "exercise_exclusions": derived["exercise_exclusions"],
        "equipment_tier": derived["equipment_tier"],
        "key_days": derived["key_day_candidates"],
        "strength_days": derived["strength_day_candidates"]
    }
    
    config_path = output_dir / "plan_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(plan_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Plan generated successfully!")
    print(f"   Output: {output_dir}")
    print(f"   Cycling workouts: {result['files_generated']['cycling']}")
    print(f"   Strength workouts: {result['files_generated']['strength']}")
    
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

