#!/usr/bin/env python3
"""
Pre-Delivery Checklist Generator

This script generates a human-readable checklist that MUST be reviewed
before delivering any athlete package.

FAILURE TO REVIEW THIS CHECKLIST IS A CRITICAL ERROR.

Created: Feb 2026
Reason: Bug #16-18 - Packages were delivered without proper validation.
"""

import sys
import yaml
import subprocess
from pathlib import Path
from datetime import datetime


def generate_checklist(athlete_id: str) -> str:
    """Generate a comprehensive pre-delivery checklist."""
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id
    scripts_dir = Path(__file__).parent

    lines = []
    lines.append("=" * 70)
    lines.append(f"PRE-DELIVERY CHECKLIST: {athlete_id}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # Load athlete data
    profile_path = athlete_dir / 'profile.yaml'
    methodology_path = athlete_dir / 'methodology.yaml'

    if profile_path.exists():
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
        athlete_name = profile.get('name', athlete_id)
        race = profile.get('target_race', {})
        race_name = race.get('name', 'Unknown')
        race_date = race.get('date', 'Unknown')
    else:
        athlete_name = athlete_id
        race_name = 'Unknown'
        race_date = 'Unknown'

    if methodology_path.exists():
        with open(methodology_path, 'r') as f:
            methodology = yaml.safe_load(f)
        methodology_name = methodology.get('selected_methodology', 'Unknown')
    else:
        methodology_name = 'Unknown'

    lines.append(f"Athlete: {athlete_name}")
    lines.append(f"Race: {race_name} ({race_date})")
    lines.append(f"Methodology: {methodology_name}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("")

    # Section 1: Automated Validation Results
    lines.append("## 1. AUTOMATED VALIDATION RESULTS")
    lines.append("")

    # Run distribution validation
    result = subprocess.run(
        [sys.executable, 'validate_workout_distribution.py', athlete_id],
        cwd=scripts_dir,
        capture_output=True,
        text=True
    )
    dist_passed = result.returncode == 0

    if dist_passed:
        lines.append("  [✅] Distribution validation PASSED")
    else:
        lines.append("  [❌] Distribution validation FAILED - DO NOT DELIVER")
        lines.append("")
        # Include relevant lines from output
        for line in result.stdout.split('\n'):
            if 'Z1-Z2' in line or 'Z3' in line or 'Z4-Z5' in line or 'ERROR' in line:
                lines.append(f"       {line.strip()}")

    lines.append("")

    # Run integrity check
    result = subprocess.run(
        [sys.executable, 'test_athlete_integrity.py', athlete_id],
        cwd=scripts_dir,
        capture_output=True,
        text=True
    )
    integrity_passed = result.returncode == 0

    if integrity_passed:
        lines.append("  [✅] Integrity check PASSED")
    else:
        lines.append("  [⚠️] Integrity check has issues")

    # Extract any warnings/errors
    for line in result.stdout.split('\n'):
        if 'WARNING' in line or 'ERROR' in line or 'CRITICAL' in line:
            lines.append(f"       {line.strip()}")

    lines.append("")

    # Section 2: File Verification
    lines.append("## 2. FILE VERIFICATION")
    lines.append("")

    required_files = [
        ('training_guide.html', 'Training guide HTML'),
        ('training_guide.pdf', 'Training guide PDF'),
        ('plan_justification.md', 'Plan justification document'),
        ('profile.yaml', 'Athlete profile'),
        ('methodology.yaml', 'Methodology selection'),
        ('derived.yaml', 'Derived values'),
        ('plan_dates.yaml', 'Plan dates'),
    ]

    for filename, description in required_files:
        filepath = athlete_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            lines.append(f"  [✅] {description}: {filename} ({size:,} bytes)")
        else:
            lines.append(f"  [❌] {description}: {filename} - MISSING")

    # Count workouts
    workouts_dir = athlete_dir / 'workouts'
    if workouts_dir.exists():
        workout_count = len(list(workouts_dir.glob('*.zwo')))
        strength_count = len(list(workouts_dir.glob('*Strength*.zwo')))
        lines.append(f"  [✅] Workouts: {workout_count} total ({strength_count} strength)")
    else:
        lines.append(f"  [❌] Workouts directory MISSING")

    lines.append("")

    # Section 3: Manual Verification Checklist
    lines.append("## 3. MANUAL VERIFICATION (Check each item)")
    lines.append("")
    lines.append("  [ ] Reviewed plan_justification.md - decisions make sense")
    lines.append("  [ ] Opened training_guide.pdf - displays correctly")
    lines.append("  [ ] Spot-checked 3 random workouts - content looks correct")
    lines.append("  [ ] Verified athlete name appears in workout descriptions")
    lines.append("  [ ] Confirmed race name and date are correct")
    lines.append("  [ ] No 'Sweet Spot' references (should be 'G SPOT')")
    lines.append("  [ ] Strength workouts have dates in filename")
    lines.append("")

    # Section 4: Delivery Package Check
    lines.append("## 4. DELIVERY PACKAGE")
    lines.append("")

    downloads_path = Path.home() / 'Downloads' / f'{athlete_id}-training-plan'
    if downloads_path.exists():
        lines.append(f"  [✅] Package exists: {downloads_path}")

        # Check contents
        pdf_exists = (downloads_path / 'training_guide.pdf').exists()
        justification_exists = (downloads_path / 'plan_justification.md').exists()
        workouts_exist = (downloads_path / 'workouts').exists()

        if pdf_exists:
            lines.append("  [✅] training_guide.pdf present")
        else:
            lines.append("  [❌] training_guide.pdf MISSING from package")

        if justification_exists:
            lines.append("  [✅] plan_justification.md present")
        else:
            lines.append("  [❌] plan_justification.md MISSING from package")

        if workouts_exist:
            pkg_workout_count = len(list((downloads_path / 'workouts').glob('*.zwo')))
            lines.append(f"  [✅] workouts/ folder ({pkg_workout_count} files)")
        else:
            lines.append("  [❌] workouts/ folder MISSING from package")
    else:
        lines.append(f"  [❌] Package NOT FOUND: {downloads_path}")
        lines.append("")
        lines.append("  Create package with:")
        lines.append(f"    mkdir -p ~/Downloads/{athlete_id}-training-plan/workouts")
        lines.append(f"    cp {athlete_dir}/training_guide.pdf ~/Downloads/{athlete_id}-training-plan/")
        lines.append(f"    cp {athlete_dir}/plan_justification.md ~/Downloads/{athlete_id}-training-plan/")
        lines.append(f"    cp {athlete_dir}/workouts/*.zwo ~/Downloads/{athlete_id}-training-plan/workouts/")

    lines.append("")
    lines.append("-" * 70)
    lines.append("")

    # Final verdict
    if dist_passed and integrity_passed:
        lines.append("✅ AUTOMATED CHECKS PASSED")
        lines.append("")
        lines.append("Complete the manual verification above before delivering.")
    else:
        lines.append("❌ AUTOMATED CHECKS FAILED - DO NOT DELIVER")
        lines.append("")
        lines.append("Fix all issues before proceeding.")

    lines.append("")
    lines.append("=" * 70)

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pre_delivery_checklist.py <athlete_id>")
        print("")
        print("This generates a checklist that MUST be reviewed before delivery.")
        sys.exit(1)

    athlete_id = sys.argv[1]
    checklist = generate_checklist(athlete_id)
    print(checklist)

    # Also save to file
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id
    checklist_path = athlete_dir / 'PRE_DELIVERY_CHECKLIST.txt'

    with open(checklist_path, 'w') as f:
        f.write(checklist)

    print("")
    print(f"Checklist saved to: {checklist_path}")


if __name__ == '__main__':
    main()
