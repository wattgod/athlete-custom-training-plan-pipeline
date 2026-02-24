#!/usr/bin/env python3
"""
Test script for custom guide generation with athlete data.
Tests the integration of methodology + fueling + guide generator.

Note: This test uses the local generate_html_guide module.
"""

import sys
import yaml
from pathlib import Path

# Add local scripts path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_html_guide import generate_html_guide


def load_yaml(filepath):
    """Load YAML file"""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def test_guide_generation_with_real_athlete():
    """Test guide generation with a real athlete if one exists."""
    # Find an athlete to test with
    athletes_dir = Path(__file__).parent.parent

    # Try kyle-cocowitch first, then any athlete with required files
    test_athletes = ['kyle-cocowitch']

    for athlete_dir in athletes_dir.iterdir():
        if athlete_dir.is_dir() and not athlete_dir.name.startswith('.'):
            if (athlete_dir / 'profile.yaml').exists():
                test_athletes.append(athlete_dir.name)

    for athlete_id in test_athletes:
        athlete_dir = athletes_dir / athlete_id
        if not (athlete_dir / 'profile.yaml').exists():
            continue

        print(f"Testing guide generation for: {athlete_id}")

        try:
            # Load athlete data
            profile = load_yaml(athlete_dir / 'profile.yaml')
            derived = load_yaml(athlete_dir / 'derived.yaml') if (athlete_dir / 'derived.yaml').exists() else {}
            methodology = load_yaml(athlete_dir / 'methodology.yaml') if (athlete_dir / 'methodology.yaml').exists() else {}

            print(f"   Athlete: {profile.get('name', 'Unknown')}")
            print(f"   Target Race: {profile.get('target_race', {}).get('name', 'Unknown')}")
            print(f"   Methodology: {methodology.get('selected_methodology', 'Unknown')}")

            # Generate guide
            output_path = athlete_dir / 'test_guide_output.html'
            result = generate_html_guide(athlete_id, output_path=output_path)

            assert result.exists(), f"Guide file not created: {result}"
            assert result.stat().st_size > 1000, f"Guide file too small: {result.stat().st_size} bytes"

            # Clean up test output
            if output_path.exists() and 'test_guide_output' in str(output_path):
                output_path.unlink()

            print(f"   PASS: Guide generated ({result.stat().st_size:,} bytes)")
            return True

        except Exception as e:
            print(f"   FAIL: {e}")
            return False

    print("No test athlete found with required files")
    return True  # Skip if no athlete available


def main():
    print("=" * 60)
    print("Testing Custom Guide Generation")
    print("=" * 60)

    if test_guide_generation_with_real_athlete():
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
