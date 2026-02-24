#!/usr/bin/env python3
"""
Pre-Regeneration Quality Gate

This script MUST be run before generating any athlete package.
It runs all tests and validates athlete files.

FAILURE TO RUN THIS SCRIPT BEFORE GENERATION IS A CRITICAL ERROR.

Created: Feb 2026
Reason: Bug #17 - Code was modified without running tests first.
"""

import sys
import subprocess
from pathlib import Path


def run_tests() -> tuple[bool, str]:
    """Run all tests and return pass/fail status."""
    scripts_dir = Path(__file__).parent

    # Get list of test files (glob pattern must be expanded by Python)
    test_files = list(scripts_dir.glob('test_*.py'))
    test_file_names = [f.name for f in test_files]

    if not test_file_names:
        return False, "No test files found"

    result = subprocess.run(
        [sys.executable, '-m', 'pytest'] + test_file_names + ['-v', '--tb=short'],
        cwd=scripts_dir,
        capture_output=True,
        text=True
    )

    # Count passes and failures
    output = result.stdout + result.stderr
    passed = 'passed' in output and 'failed' not in output.lower().split('passed')[0]

    return passed, output


def validate_athlete_files(athlete_id: str) -> tuple[bool, list]:
    """Validate that required athlete files exist and are valid."""
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id

    errors = []

    required_files = [
        'profile.yaml',
        'derived.yaml',
        'plan_dates.yaml',
        'methodology.yaml',
    ]

    for filename in required_files:
        filepath = athlete_dir / filename
        if not filepath.exists():
            errors.append(f"Missing required file: {filename}")
        else:
            # Check file is valid YAML
            try:
                import yaml
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
                if not data:
                    errors.append(f"Empty file: {filename}")
            except Exception as e:
                errors.append(f"Invalid YAML in {filename}: {e}")

    return len(errors) == 0, errors


def check_lessons_learned_acknowledgment() -> bool:
    """Check if lessons learned has been updated recently."""
    lessons_file = Path(__file__).parent / 'ATHLETE_CUSTOM_TRAINING_PLAN_PIPELINE_LESSONS_LEARNED.md'

    if not lessons_file.exists():
        print("WARNING: Lessons learned file not found!")
        return False

    # Just verify it exists and is readable
    content = lessons_file.read_text()
    if 'MANDATORY AUTOMATED QUALITY GATES' not in content:
        print("WARNING: Lessons learned may be outdated - missing quality gates section")
        return False

    return True


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("PRE-REGENERATION QUALITY GATE")
        print("=" * 60)
        print("")
        print("Usage: python3 pre_regenerate_check.py <athlete_id>")
        print("")
        print("This script MUST be run before generating any athlete package.")
        print("It validates:")
        print("  1. All tests pass (67 tests)")
        print("  2. Required athlete files exist and are valid")
        print("  3. Lessons learned document is current")
        print("")
        print("DO NOT SKIP THIS STEP.")
        sys.exit(1)

    athlete_id = sys.argv[1]

    print("=" * 60)
    print("PRE-REGENERATION QUALITY GATE")
    print("=" * 60)
    print(f"Athlete: {athlete_id}")
    print("")

    all_passed = True

    # Gate 1: Lessons learned acknowledgment
    print("1. Checking lessons learned document...")
    if check_lessons_learned_acknowledgment():
        print("   ✅ Lessons learned document found and current")
    else:
        print("   ⚠️  Warning with lessons learned document")

    # Gate 2: Athlete files
    print("")
    print("2. Validating athlete files...")
    files_ok, file_errors = validate_athlete_files(athlete_id)
    if files_ok:
        print("   ✅ All required files present and valid")
    else:
        print("   ❌ File validation failed:")
        for err in file_errors:
            print(f"      - {err}")
        all_passed = False

    # Gate 3: Tests
    print("")
    print("3. Running all tests...")
    tests_ok, test_output = run_tests()

    # Extract summary line
    for line in test_output.split('\n'):
        if 'passed' in line or 'failed' in line:
            if '==' in line:
                print(f"   {line.strip()}")

    if tests_ok:
        print("   ✅ All tests passed")
    else:
        print("   ❌ Some tests failed - fix before proceeding")
        all_passed = False

    print("")
    print("-" * 60)

    if all_passed:
        print("✅ PRE-REGENERATION CHECK PASSED")
        print("")
        print("You may now run:")
        print(f"  python3 generate_athlete_package.py {athlete_id}")
        print("")
        print("After generation, you MUST run:")
        print(f"  python3 validate_workout_distribution.py {athlete_id}")
        print(f"  python3 test_athlete_integrity.py {athlete_id}")
        sys.exit(0)
    else:
        print("❌ PRE-REGENERATION CHECK FAILED")
        print("")
        print("DO NOT proceed with package generation until all issues are fixed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
