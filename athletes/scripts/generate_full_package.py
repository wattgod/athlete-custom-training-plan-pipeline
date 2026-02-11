#!/usr/bin/env python3
"""
Generate Full Athlete Package

One-command pipeline that runs all steps to generate a complete training package:
1. Validate profile
2. Derive classifications (tier, plan weeks, etc.)
3. Select methodology
4. Calculate fueling
5. Build weekly structure
6. Calculate plan dates
7. Generate workouts (ZWO files)
8. Generate HTML guide
9. Generate dashboard
10. Optionally deliver via email

Usage:
    python generate_full_package.py <athlete_id> [--deliver] [--skip-validation]
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import Tuple, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from constants import get_athlete_dir, get_athlete_file, get_athlete_current_plan_dir
from logger import get_logger

logger = get_logger()


class PipelineStep:
    """Represents a step in the generation pipeline."""

    def __init__(self, name: str, script: str, required: bool = True):
        self.name = name
        self.script = script
        self.required = required
        self.success = False
        self.error = None
        self.duration = 0.0


def run_step(step: PipelineStep, athlete_id: str, scripts_dir: Path) -> bool:
    """Run a single pipeline step."""
    script_path = scripts_dir / step.script

    if not script_path.exists():
        step.error = f"Script not found: {script_path}"
        return False

    start = datetime.now()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), athlete_id],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per step
        )

        step.duration = (datetime.now() - start).total_seconds()

        if result.returncode == 0:
            step.success = True
            return True
        else:
            step.error = result.stderr or result.stdout or f"Exit code {result.returncode}"
            return False

    except subprocess.TimeoutExpired:
        step.error = "Timeout after 5 minutes"
        return False
    except Exception as e:
        step.error = str(e)
        return False


def check_prerequisites(athlete_id: str) -> Tuple[bool, str]:
    """Check that required files exist before running pipeline."""
    profile_path = get_athlete_file(athlete_id, "profile.yaml")

    if not profile_path.exists():
        return False, f"Profile not found: {profile_path}"

    return True, ""


def run_pipeline(
    athlete_id: str,
    skip_validation: bool = False,
    deliver: bool = False,
    verbose: bool = True
) -> Tuple[bool, List[PipelineStep]]:
    """
    Run the full generation pipeline for an athlete.

    Returns: (success, list of steps with results)
    """
    scripts_dir = Path(__file__).parent

    # Check prerequisites
    ok, error = check_prerequisites(athlete_id)
    if not ok:
        if verbose:
            print(f"ERROR: {error}")
        return False, []

    # Define pipeline steps
    steps = [
        PipelineStep("Validate Profile", "validate_profile.py", required=not skip_validation),
        PipelineStep("Derive Classifications", "derive_classifications.py"),
        PipelineStep("Select Methodology", "select_methodology.py"),
        PipelineStep("Calculate Fueling", "calculate_fueling.py"),
        PipelineStep("Build Weekly Structure", "build_weekly_structure.py"),
        PipelineStep("Calculate Plan Dates", "calculate_plan_dates.py"),
        PipelineStep("Generate Workouts", "generate_athlete_package.py"),
        PipelineStep("Generate HTML Guide", "generate_html_guide.py"),
        PipelineStep("Generate Dashboard", "generate_dashboard.py"),
    ]

    if deliver:
        steps.append(PipelineStep("Deliver Package", "deliver_package.py", required=False))

    if verbose:
        print(f"\n{'='*60}")
        print(f"GENERATING PACKAGE: {athlete_id}")
        print(f"{'='*60}\n")

    all_success = True

    for i, step in enumerate(steps, 1):
        if verbose:
            print(f"[{i}/{len(steps)}] {step.name}...", end=" ", flush=True)

        if not step.required and skip_validation:
            if verbose:
                print("SKIPPED")
            continue

        success = run_step(step, athlete_id, scripts_dir)

        if verbose:
            if success:
                print(f"OK ({step.duration:.1f}s)")
            else:
                print(f"FAILED")
                print(f"    Error: {step.error}")

        if not success and step.required:
            all_success = False
            if verbose:
                print(f"\nPipeline stopped at step: {step.name}")
            break

    if verbose:
        print(f"\n{'='*60}")
        if all_success:
            print("SUCCESS: Package generated")
            output_dir = get_athlete_current_plan_dir(athlete_id)
            print(f"Output: {output_dir}")
        else:
            print("FAILED: See errors above")
        print(f"{'='*60}\n")

    return all_success, steps


def main():
    parser = argparse.ArgumentParser(
        description="Generate complete training package for an athlete"
    )
    parser.add_argument("athlete_id", help="Athlete ID (directory name)")
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Send package via email after generation"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip profile validation step"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )

    args = parser.parse_args()

    success, steps = run_pipeline(
        args.athlete_id,
        skip_validation=args.skip_validation,
        deliver=args.deliver,
        verbose=not args.quiet
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
