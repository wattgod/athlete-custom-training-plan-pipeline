#!/usr/bin/env python3
"""
Workout Distribution Validator

This script validates that generated workouts match the methodology's target zone distribution.
It MUST be run after workout generation and BEFORE package delivery.

FAILURE TO RUN THIS SCRIPT IS A CRITICAL ERROR.

Created: Feb 2026
Reason: Bug #16 - Plans were delivered with wrong zone ratios because distribution wasn't validated.
"""

import sys
import yaml
from pathlib import Path
from collections import defaultdict

# Zone classification for workout types
ZONE_CLASSIFICATION = {
    # Z1-Z2: Recovery, Easy, Endurance (sub-threshold)
    'Recovery': 'z1_z2',
    'Easy': 'z1_z2',
    'Endurance': 'z1_z2',
    'Shakeout': 'z1_z2',
    'Long_Ride': 'z1_z2',
    'Rest': 'z1_z2',

    # Pre-plan workouts (ramp-up week before official plan start)
    'Pre_Plan_Easy': 'z1_z2',
    'Pre_Plan_Endurance': 'z1_z2',
    'Pre_Plan_Rest': 'z1_z2',

    # Z3: Tempo, G SPOT, Sweet Spot (88-94% FTP is high Z3/low Z4)
    'Tempo': 'z3',
    'G_Spot': 'z3',
    'Sweet_Spot': 'z3',

    # Z4-Z5: Threshold, VO2max, Anaerobic, Over-Unders
    'Threshold': 'z4_z5',
    'VO2max': 'z4_z5',
    'Over_Under': 'z4_z5',
    'Blended': 'z4_z5',  # Blended has Z5 components
    'Openers': 'z4_z5',
    'Anaerobic': 'z4_z5',
    'Sprints': 'z4_z5',
    'Race_Sim': 'z4_z5',
}

# Workouts excluded from distribution counting (not training sessions)
EXCLUDED_PREFIXES = ('FTP_Test', 'RACE_DAY', 'Strength')

# Target distributions by methodology
METHODOLOGY_TARGETS = {
    'g_spot_threshold': {'z1_z2': 0.45, 'z3': 0.30, 'z4_z5': 0.25},
    'sweet_spot': {'z1_z2': 0.45, 'z3': 0.30, 'z4_z5': 0.25},
    'polarized': {'z1_z2': 0.80, 'z3': 0.00, 'z4_z5': 0.20},
    'pyramidal': {'z1_z2': 0.75, 'z3': 0.15, 'z4_z5': 0.10},
    'hiit_focused': {'z1_z2': 0.50, 'z3': 0.10, 'z4_z5': 0.40},
    'threshold_focused': {'z1_z2': 0.45, 'z3': 0.30, 'z4_z5': 0.25},
}

# Maximum allowed deviation from target (5%)
MAX_DEVIATION = 0.05


def classify_workout(filename: str) -> str | None:
    """Extract workout type from filename and classify into zone.

    Returns zone string, or None for excluded/unknown workouts.
    """
    # Filename format: W01_Mon_Feb16_G_Spot.zwo
    stem = Path(filename).stem
    parts = stem.split('_')

    # Get workout type (everything after the date)
    # W01_Mon_Feb16_G_Spot -> ['W01', 'Mon', 'Feb16', 'G', 'Spot']
    if len(parts) >= 4:
        workout_type = '_'.join(parts[3:])
    else:
        return None

    # Skip excluded workouts (assessments, race days, strength — not training sessions)
    for prefix in EXCLUDED_PREFIXES:
        if workout_type.startswith(prefix):
            return None

    return ZONE_CLASSIFICATION.get(workout_type, None)


def validate_distribution(athlete_id: str) -> tuple[bool, str]:
    """
    Validate workout distribution matches methodology target.

    Returns: (passed: bool, message: str)
    """
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id
    workouts_dir = athlete_dir / 'workouts'
    methodology_file = athlete_dir / 'methodology.yaml'

    # Check files exist
    if not workouts_dir.exists():
        return False, f"ERROR: Workouts directory not found: {workouts_dir}"

    if not methodology_file.exists():
        return False, f"ERROR: Methodology file not found: {methodology_file}"

    # Load methodology
    with open(methodology_file, 'r') as f:
        methodology = yaml.safe_load(f)

    methodology_id = methodology.get('methodology_id', 'polarized')
    target = METHODOLOGY_TARGETS.get(methodology_id)

    if not target:
        # Try to get from methodology config
        config = methodology.get('configuration', {})
        intensity_dist = config.get('intensity_distribution', {})
        if intensity_dist:
            target = {
                'z1_z2': intensity_dist.get('z1_z2', 0.45),
                'z3': intensity_dist.get('z3', 0.30),
                'z4_z5': intensity_dist.get('z4_z5', 0.25),
            }
        else:
            return False, f"ERROR: Unknown methodology '{methodology_id}' and no config found"

    # Count workouts by zone
    zone_counts = defaultdict(int)
    excluded_types = []
    unknown_types = []

    for workout in workouts_dir.glob('*.zwo'):
        stem = workout.stem
        parts = stem.split('_')
        workout_type = '_'.join(parts[3:]) if len(parts) >= 4 else stem

        # Check if excluded (assessments, race days, strength)
        is_excluded = any(workout_type.startswith(p) for p in EXCLUDED_PREFIXES)
        if is_excluded:
            excluded_types.append(workout_type)
            continue

        zone = ZONE_CLASSIFICATION.get(workout_type, None)
        if zone:
            zone_counts[zone] += 1
        else:
            unknown_types.append(workout_type)

    total = sum(zone_counts.values())
    if total == 0:
        return False, "ERROR: No non-strength workouts found"

    # Calculate actual distribution
    actual = {
        'z1_z2': zone_counts['z1_z2'] / total,
        'z3': zone_counts['z3'] / total,
        'z4_z5': zone_counts['z4_z5'] / total,
    }

    # Check deviations
    errors = []
    warnings = []

    for zone, target_pct in target.items():
        actual_pct = actual.get(zone, 0)
        deviation = actual_pct - target_pct

        if abs(deviation) > MAX_DEVIATION:
            errors.append(
                f"{zone.upper()}: {actual_pct*100:.1f}% (target: {target_pct*100:.1f}%, deviation: {deviation*100:+.1f}%)"
            )
        elif abs(deviation) > 0.02:  # Warning at 2%
            warnings.append(
                f"{zone.upper()}: {actual_pct*100:.1f}% (target: {target_pct*100:.1f}%, deviation: {deviation*100:+.1f}%)"
            )

    # Build report
    report = []
    report.append("=" * 60)
    report.append(f"WORKOUT DISTRIBUTION VALIDATION: {athlete_id}")
    report.append("=" * 60)
    report.append(f"Methodology: {methodology.get('selected_methodology', methodology_id)}")
    report.append(f"Total non-strength workouts: {total}")
    report.append("")
    report.append("Zone Distribution:")
    report.append(f"  Z1-Z2 (Recovery/Endurance): {zone_counts['z1_z2']:3d} = {actual['z1_z2']*100:5.1f}% (target: {target['z1_z2']*100:.0f}%)")
    report.append(f"  Z3 (Tempo/G SPOT):          {zone_counts['z3']:3d} = {actual['z3']*100:5.1f}% (target: {target['z3']*100:.0f}%)")
    report.append(f"  Z4-Z5 (Threshold/VO2max):   {zone_counts['z4_z5']:3d} = {actual['z4_z5']*100:5.1f}% (target: {target['z4_z5']*100:.0f}%)")
    report.append("")

    if excluded_types:
        report.append(f"Excluded (assessments/race days): {len(excluded_types)} ({', '.join(sorted(set(excluded_types)))})")
        report.append("")

    if unknown_types:
        report.append(f"Unknown workout types: {set(unknown_types)}")
        report.append("")

    if errors:
        report.append("❌ DISTRIBUTION ERRORS (>5% deviation):")
        for e in errors:
            report.append(f"   {e}")
        report.append("")

    if warnings:
        report.append("⚠️  DISTRIBUTION WARNINGS (2-5% deviation):")
        for w in warnings:
            report.append(f"   {w}")
        report.append("")

    if errors:
        report.append("❌ VALIDATION FAILED - DO NOT DELIVER THIS PACKAGE")
        report.append("")
        report.append("FIX REQUIRED: Adjust workout selection logic in generate_athlete_package.py")
        report.append("The distribution is off by more than 5% on one or more zones.")
        passed = False
    elif warnings:
        report.append("✅ VALIDATION PASSED (with warnings)")
        passed = True
    else:
        report.append("✅ VALIDATION PASSED")
        passed = True

    return passed, '\n'.join(report)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_workout_distribution.py <athlete_id>")
        print("")
        print("This script validates that workout distribution matches methodology targets.")
        print("It MUST be run after workout generation and BEFORE package delivery.")
        sys.exit(1)

    athlete_id = sys.argv[1]
    passed, report = validate_distribution(athlete_id)

    print(report)

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
