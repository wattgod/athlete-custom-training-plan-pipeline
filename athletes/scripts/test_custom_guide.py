#!/usr/bin/env python3
"""
Test script for custom guide generation with athlete data.
Tests the integration of methodology + fueling + guide generator.
"""

import sys
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
    athlete_dir = Path(__file__).parent.parent / 'test-full-v4'
    race_data_path = Path(__file__).parent.parent.parent.parent / 'guides' / 'gravel-god-guides' / 'race_data' / 'unbound_gravel_200.json'
    output_path = athlete_dir / 'custom_guide_test.html'

    print("=" * 60)
    print("Testing Custom Guide Generation")
    print("=" * 60)

    # Load athlete data
    print("\n1. Loading athlete data...")
    profile = load_yaml(athlete_dir / 'profile.yaml')
    derived = load_yaml(athlete_dir / 'derived.yaml')
    methodology = load_yaml(athlete_dir / 'methodology.yaml')
    fueling = load_yaml(athlete_dir / 'fueling.yaml')

    print(f"   Athlete: {profile.get('name', 'Unknown')}")
    print(f"   Target Race: {profile.get('target_race', {}).get('name', 'Unknown')}")
    print(f"   Plan Weeks: {derived.get('plan_weeks', 'Unknown')}")
    print(f"   Methodology: {methodology.get('selected_methodology', 'Unknown')}")
    print(f"   Hourly Carb Target: {fueling.get('carbohydrates', {}).get('hourly_target', 'Unknown')}g")

    # Load race data
    print("\n2. Loading race data...")
    import json
    with open(race_data_path, 'r') as f:
        race_data = json.load(f)
    print(f"   Race: {race_data.get('name', race_data.get('race_metadata', {}).get('name', 'Unknown'))}")

    # Build athlete_data dict
    athlete_data = {
        'profile': profile,
        'derived': derived,
        'methodology': methodology,
        'fueling': fueling
    }

    # Generate guide
    print("\n3. Generating custom guide...")
    tier_name = derived.get('tier', 'COMPETE').upper()
    ability_level = 'Intermediate'  # Could derive from profile

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

    # Verify key placeholders were substituted
    print("\n5. Verifying substitutions...")
    with open(output_path, 'r') as f:
        content = f.read()

    checks = [
        ('{{SELECTED_METHODOLOGY}}', 'Methodology'),
        ('{{HOURLY_CARB_TARGET}}', 'Hourly carb target'),
        ('{{TOTAL_CARB_TARGET}}', 'Total carb target'),
        ('{{INTENSITY_Z1_Z2}}', 'Intensity distribution'),
        ('{{PLAN_TITLE}}', 'Plan title'),
        ('{{', 'Any unsubstituted placeholders'),
    ]

    all_passed = True
    for placeholder, name in checks:
        if placeholder == '{{':
            # Check for any remaining placeholders
            import re
            remaining = re.findall(r'\{\{[A-Z_]+\}\}', content)
            if remaining:
                print(f"   WARNING: Found unsubstituted placeholders: {remaining[:5]}...")
                all_passed = False
            else:
                print(f"   PASS: No unsubstituted placeholders found")
        elif placeholder in content:
            print(f"   FAIL: {name} not substituted ({placeholder} still present)")
            all_passed = False
        else:
            print(f"   PASS: {name} substituted correctly")

    # Check custom sections are present
    if 'Your Selected Training Methodology' in content:
        print(f"   PASS: Custom methodology section included")
    else:
        print(f"   FAIL: Custom methodology section missing")
        all_passed = False

    if 'Your Personalized Fueling Targets' in content:
        print(f"   PASS: Custom fueling section included")
    else:
        print(f"   FAIL: Custom fueling section missing")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED - Review output above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
