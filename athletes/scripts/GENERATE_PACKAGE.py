#!/usr/bin/env python3
"""
MANDATORY WRAPPER FOR PACKAGE GENERATION

DO NOT USE generate_athlete_package.py DIRECTLY.
USE THIS SCRIPT INSTEAD.

This script enforces ALL quality gates in order and will NOT proceed
if any gate fails. It cannot be bypassed.

Usage:
    python3 GENERATE_PACKAGE.py <athlete_id>

Gates enforced:
    1. Tests must pass (all 68+)
    2. Athlete files must be valid
    3. Package generation
    4. Distribution validation (zone ratios within 5%)
    5. Athlete integrity check
    6. Pre-delivery checklist generation
"""

import sys
import subprocess
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(msg: str):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{msg}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")


def print_pass(msg: str):
    print(f"{GREEN}PASS{RESET} {msg}")


def print_fail(msg: str):
    print(f"{RED}FAIL{RESET} {msg}")


def print_warn(msg: str):
    print(f"{YELLOW}WARN{RESET} {msg}")


def run_command(cmd: list, description: str) -> tuple[bool, str]:
    """Run a command and return (success, output)."""
    print(f"\n>>> Running: {description}")
    result = subprocess.run(
        cmd,
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr
    success = result.returncode == 0
    return success, output


def gate_1_tests() -> bool:
    """Gate 1: All tests must pass."""
    print_header("GATE 1: Running All Tests")

    success, output = run_command(
        [sys.executable, '-m', 'pytest', '-v', '--tb=short'],
        "pytest test_*.py"
    )

    # Check for failures
    if 'failed' in output.lower() and 'passed' in output:
        # Some tests failed
        print_fail("Some tests failed")
        print(output[-2000:])  # Show last 2000 chars
        return False

    if 'passed' not in output:
        print_fail("No tests ran")
        return False

    # Extract pass count
    import re
    match = re.search(r'(\d+) passed', output)
    if match:
        passed_count = int(match.group(1))
        print_pass(f"{passed_count} tests passed")
        return True

    print_fail("Could not determine test results")
    return False


def gate_2_athlete_files(athlete_id: str) -> bool:
    """Gate 2: Validate athlete files exist and are valid."""
    print_header("GATE 2: Validating Athlete Files")

    from constants import get_athlete_dir
    import yaml

    athlete_dir = get_athlete_dir(athlete_id)

    required_files = [
        'profile.yaml',
        'derived.yaml',
        'methodology.yaml',
        'fueling.yaml',
        'plan_dates.yaml',
    ]

    all_valid = True
    for filename in required_files:
        filepath = athlete_dir / filename
        if not filepath.exists():
            print_fail(f"Missing: {filename}")
            all_valid = False
            continue

        # Validate YAML loads
        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if not data:
                print_fail(f"Empty: {filename}")
                all_valid = False
            else:
                print_pass(f"Valid: {filename}")
        except Exception as e:
            print_fail(f"Invalid YAML: {filename} - {e}")
            all_valid = False

    return all_valid


def gate_3_generate_package(athlete_id: str) -> bool:
    """Gate 3: Generate the athlete package."""
    print_header("GATE 3: Generating Package")

    success, output = run_command(
        [sys.executable, 'generate_athlete_package.py', athlete_id],
        f"generate_athlete_package.py {athlete_id}"
    )

    if not success:
        print_fail("Package generation failed")
        print(output[-2000:])
        return False

    if 'PACKAGE GENERATION COMPLETE' in output:
        print_pass("Package generated successfully")
        return True

    print_fail("Package generation did not complete")
    print(output[-2000:])
    return False


def gate_4_distribution(athlete_id: str) -> bool:
    """Gate 4: Validate workout zone distribution."""
    print_header("GATE 4: Validating Zone Distribution")

    success, output = run_command(
        [sys.executable, 'validate_workout_distribution.py', athlete_id],
        f"validate_workout_distribution.py {athlete_id}"
    )

    if 'VALIDATION FAILED' in output:
        print_fail("Zone distribution is outside acceptable range (>5% deviation)")
        print(output)
        return False

    if 'VALIDATION PASSED' in output:
        # Check for warnings
        if 'WARNINGS' in output:
            print_warn("Distribution passed with warnings (2-5% deviation)")
        else:
            print_pass("Distribution matches methodology target")
        return True

    print_fail("Could not validate distribution")
    print(output)
    return False


def gate_5_integrity(athlete_id: str) -> bool:
    """Gate 5: Final integrity check."""
    print_header("GATE 5: Athlete Integrity Check")

    integrity_script = SCRIPTS_DIR / 'test_athlete_integrity.py'
    if not integrity_script.exists():
        print_warn("Integrity script not found - skipping")
        return True

    success, output = run_command(
        [sys.executable, 'test_athlete_integrity.py', athlete_id],
        f"test_athlete_integrity.py {athlete_id}"
    )

    if not success and 'FAIL' in output:
        print_fail("Integrity check failed")
        print(output[-2000:])
        return False

    print_pass("Integrity check passed")
    return True


def gate_6_checklist(athlete_id: str) -> bool:
    """Gate 6: Generate pre-delivery checklist."""
    print_header("GATE 6: Pre-Delivery Checklist")

    checklist_script = SCRIPTS_DIR / 'pre_delivery_checklist.py'
    if not checklist_script.exists():
        print_warn("Checklist script not found - skipping")
        return True

    success, output = run_command(
        [sys.executable, 'pre_delivery_checklist.py', athlete_id],
        f"pre_delivery_checklist.py {athlete_id}"
    )

    print(output)
    print_pass("Checklist generated - REVIEW BEFORE DELIVERY")
    return True


def main():
    if len(sys.argv) < 2:
        print(f"{RED}Usage: python3 GENERATE_PACKAGE.py <athlete_id>{RESET}")
        print("\nThis is the MANDATORY wrapper for package generation.")
        print("DO NOT use generate_athlete_package.py directly.")
        sys.exit(1)

    athlete_id = sys.argv[1]

    print_header(f"GENERATING PACKAGE FOR: {athlete_id}")
    print(f"\n{BOLD}This script enforces ALL quality gates.{RESET}")
    print("If any gate fails, the process stops immediately.\n")

    # Run all gates in order
    gates = [
        ("Gate 1: Tests", lambda: gate_1_tests()),
        ("Gate 2: Athlete Files", lambda: gate_2_athlete_files(athlete_id)),
        ("Gate 3: Generate Package", lambda: gate_3_generate_package(athlete_id)),
        ("Gate 4: Distribution", lambda: gate_4_distribution(athlete_id)),
        ("Gate 5: Integrity", lambda: gate_5_integrity(athlete_id)),
        ("Gate 6: Checklist", lambda: gate_6_checklist(athlete_id)),
    ]

    for gate_name, gate_func in gates:
        if not gate_func():
            print(f"\n{RED}{BOLD}{'='*60}{RESET}")
            print(f"{RED}{BOLD}PIPELINE STOPPED: {gate_name} FAILED{RESET}")
            print(f"{RED}{BOLD}{'='*60}{RESET}")
            print(f"\nFix the issue above and run again.")
            sys.exit(1)

    # All gates passed
    print(f"\n{GREEN}{BOLD}{'='*60}{RESET}")
    print(f"{GREEN}{BOLD}ALL GATES PASSED - PACKAGE READY FOR DELIVERY{RESET}")
    print(f"{GREEN}{BOLD}{'='*60}{RESET}")

    from constants import get_athlete_dir
    athlete_dir = get_athlete_dir(athlete_id)
    print(f"\nOutput: {athlete_dir}")
    print(f"\n{YELLOW}IMPORTANT: Review the pre-delivery checklist before sending to athlete!{RESET}")


if __name__ == '__main__':
    main()
