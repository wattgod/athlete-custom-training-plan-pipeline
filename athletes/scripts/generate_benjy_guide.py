#!/usr/bin/env python3
"""
Generate custom guide for Benjy Duke - SBT GRVL 75
"""

import sys
import json
import yaml
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'guides' / 'gravel-god-guides' / 'generators'))

from guide_generator import generate_guide


def load_yaml(filepath):
    """Load YAML file"""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def main():
    # Paths
    athlete_dir = Path(__file__).parent.parent / 'benjy-duke'
    race_data_path = Path(__file__).parent.parent.parent.parent / 'guides' / 'gravel-god-guides' / 'race_data' / 'sbt_grvl_75.json'
    output_path = athlete_dir / 'training_guide.html'

    print("=" * 60)
    print("Generating Custom Guide for Benjy Duke")
    print("=" * 60)

    # Load athlete data
    print("\n1. Loading athlete data...")
    profile = load_yaml(athlete_dir / 'profile.yaml')
    derived = load_yaml(athlete_dir / 'derived.yaml')
    methodology = load_yaml(athlete_dir / 'methodology.yaml')
    fueling = load_yaml(athlete_dir / 'fueling.yaml')

    # Load plan_dates if exists
    plan_dates_path = athlete_dir / 'plan_dates.yaml'
    plan_dates = load_yaml(plan_dates_path) if plan_dates_path.exists() else {}

    print(f"   Athlete: {profile.get('name', 'Unknown')}")
    print(f"   Target Race: {profile.get('target_race', {}).get('name', 'Unknown')}")
    print(f"   Plan Weeks: {derived.get('plan_weeks', 'Unknown')}")
    print(f"   Plan Start: {plan_dates.get('plan_start', 'Unknown')}")
    print(f"   Race Date: {plan_dates.get('race_date', 'Unknown')}")
    print(f"   Methodology: {methodology.get('selected_methodology', 'Unknown')}")
    print(f"   Hourly Carb Target: {fueling.get('carbohydrates', {}).get('hourly_target', 'Unknown')}g")

    # Load race data
    print("\n2. Loading race data...")
    with open(race_data_path, 'r') as f:
        race_data = json.load(f)
    print(f"   Race: {race_data.get('name', 'Unknown')}")
    print(f"   Distance: {race_data.get('distance_miles', 'Unknown')} miles")
    print(f"   Elevation: {race_data.get('elevation_gain_feet', 'Unknown')} feet")

    # Build athlete_data dict
    athlete_data = {
        'profile': profile,
        'derived': derived,
        'methodology': methodology,
        'fueling': fueling,
        'plan_dates': plan_dates
    }

    # Generate guide
    print("\n3. Generating custom guide...")
    tier_name = derived.get('tier', 'AYAHUASCA').upper()
    ability_level = derived.get('ability_level', 'Intermediate')

    result = generate_guide(
        race_data=race_data,
        tier_name=tier_name,
        ability_level=ability_level,
        output_path=str(output_path),
        athlete_data=athlete_data
    )

    print(f"\n4. Guide generated successfully!")
    print(f"   Output: {result}")
    print(f"   File size: {output_path.stat().st_size:,} bytes")

    # Quick verification
    print("\n5. Verifying key content...")
    with open(output_path, 'r') as f:
        content = f.read()

    checks = [
        ('Benjy', 'Athlete name'),
        ('SBT GRVL', 'Race name'),
        ('HIIT-Focused', 'Methodology'),
        ('80g/hr', 'Carb target'),
        ('28 weeks', 'Plan duration'),
    ]

    for term, desc in checks:
        if term in content:
            print(f"   PASS: {desc} found ({term})")
        else:
            print(f"   WARN: {desc} not found ({term})")

    print("\n" + "=" * 60)
    print(f"DONE - Open guide at:\n{output_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
