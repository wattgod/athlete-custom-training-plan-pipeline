#!/usr/bin/env python3
"""
Integrity tests for athlete data files.
Validates consistency across profile.yaml, derived.yaml, plan_dates.yaml, etc.

Run with: python3 test_athlete_integrity.py [athlete_id]
"""

import sys
import yaml
from datetime import datetime
from pathlib import Path


class IntegrityError:
    def __init__(self, level: str, message: str):
        self.level = level  # CRITICAL, ERROR, WARNING
        self.message = message

    def __str__(self):
        return f"[{self.level}] {self.message}"


def load_yaml_safe(path: Path) -> dict:
    """Load YAML file, return empty dict if not found."""
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def validate_workout_schedule_alignment(workouts_dir: Path, profile: dict, plan_dates: dict, derived: dict) -> list:
    """
    Validate generated workouts align with athlete's schedule preferences.

    Checks:
    1. No workouts on rest days (Monday by default, or as configured)
    2. Workout durations don't exceed daily max_duration_min
    3. Long rides occur on preferred long day
    4. Key workouts (intervals, FTP tests) only on is_key_day_ok days
    5. FTP tests exist (Week 1 baseline + pre-Build retest)
    """
    import re
    errors = []

    # Get athlete preferences
    preferred_days = profile.get('preferred_days', {})
    schedule_constraints = profile.get('schedule_constraints', {})
    preferred_long_day = schedule_constraints.get('preferred_long_day', 'Saturday or Sunday')
    preferred_off_days = schedule_constraints.get('preferred_off_days', [])

    # Map day abbreviations to full names for preference lookup
    day_map = {
        'Mon': 'monday', 'Tue': 'tuesday', 'Wed': 'wednesday',
        'Thu': 'thursday', 'Fri': 'friday', 'Sat': 'saturday', 'Sun': 'sunday'
    }

    # Track FTP tests found
    ftp_tests_found = []

    # Workout type classifications
    key_workout_types = ['FTP_Test', 'Intervals', 'VO2max', 'Race_Sim', 'Tempo']
    long_ride_types = ['Long_Ride']

    def get_zwo_duration(zwo_path: Path) -> int:
        """Parse a ZWO file and return total duration in minutes."""
        try:
            with open(zwo_path, 'r') as f:
                content = f.read()
            # Find all Duration="SECONDS" attributes
            import re
            durations = re.findall(r'Duration="(\d+)"', content)
            total_seconds = sum(int(d) for d in durations)
            return total_seconds // 60
        except Exception:
            return 60  # Default fallback

    # Parse all workout files
    workout_files = list(workouts_dir.glob('*.zwo'))

    for workout_file in workout_files:
        filename = workout_file.name

        # Parse filename: W01_Fri_Feb20_Endurance.zwo
        match = re.match(r'W(\d+)_(\w{3})_\w+\d+_(.+)\.zwo', filename)
        if not match:
            continue

        week_num = int(match.group(1))
        day_abbrev = match.group(2)
        workout_type = match.group(3)

        day_full = day_map.get(day_abbrev)
        if not day_full:
            continue

        day_prefs = preferred_days.get(day_full, {})

        # Track FTP tests
        if workout_type == 'FTP_Test':
            ftp_tests_found.append((week_num, day_abbrev, filename))

        # === CHECK 1: No workouts on unavailable days ===
        availability = day_prefs.get('availability', 'available')
        if availability == 'unavailable':
            errors.append(IntegrityError("ERROR",
                f"Workout on unavailable day: {filename} ({day_full} marked unavailable)"))

        # === CHECK 2: Duration doesn't exceed max ===
        max_duration = day_prefs.get('max_duration_min')
        if max_duration:
            # Parse actual duration from ZWO file
            workout_duration = get_zwo_duration(workout_file)
            # Long rides in later phases can be longer - allow 1.5x max for Long_Ride
            if workout_type == 'Long_Ride':
                effective_max = max_duration * 1.5
            else:
                effective_max = max_duration

            if workout_duration > effective_max:
                errors.append(IntegrityError("WARNING",
                    f"Workout exceeds time limit: {filename} ({workout_duration}min on {day_full} with {max_duration}min max)"))

        # === CHECK 3: Key workouts only on key-day-ok days ===
        is_key_day_ok = day_prefs.get('is_key_day_ok', True)
        if workout_type in key_workout_types and not is_key_day_ok:
            errors.append(IntegrityError("WARNING",
                f"Key workout on non-key day: {filename} ({day_full} not marked as key day)"))

        # === CHECK 4: Long rides on preferred long day ===
        if workout_type in long_ride_types:
            preferred_long_lower = preferred_long_day.lower()
            day_full_lower = day_full.lower()

            # Check if this day is in the preferred long day string
            if day_full_lower not in preferred_long_lower:
                # Only warn if it's not on a weekend when weekend is preferred
                if 'saturday' not in preferred_long_lower or day_full_lower not in ['saturday', 'sunday']:
                    if 'sunday' not in preferred_long_lower or day_full_lower not in ['saturday', 'sunday']:
                        errors.append(IntegrityError("WARNING",
                            f"Long ride not on preferred day: {filename} (preferred: {preferred_long_day})"))

    # === CHECK 5: FTP tests exist ===
    if not any(w[0] == 1 for w in ftp_tests_found):
        errors.append(IntegrityError("ERROR",
            "No FTP test in Week 1 - baseline test required"))

    # Check for pre-Build FTP test
    weeks = plan_dates.get('weeks', [])
    first_build_week = None
    for week in weeks:
        if week.get('phase') == 'build':
            first_build_week = week.get('week')
            break

    if first_build_week and first_build_week > 2:
        pre_build_week = first_build_week - 1
        if not any(w[0] == pre_build_week for w in ftp_tests_found):
            errors.append(IntegrityError("WARNING",
                f"No FTP test before Build phase (expected in Week {pre_build_week})"))

    # === CHECK 6: Validate strength-only days have only strength workouts ===
    strength_only_days = schedule_constraints.get('strength_only_days', [])
    strength_abbrevs = [day_map.get(d, d)[:3].title() for d in strength_only_days]

    for workout_file in workout_files:
        filename = workout_file.name
        match = re.match(r'W(\d+)_(\w{3})_\w+\d+_(.+)\.zwo', filename)
        if not match:
            continue
        day_abbrev = match.group(2)
        workout_type = match.group(3)

        # Check strength-only days only have strength workouts
        if day_abbrev in strength_abbrevs and workout_type != 'Strength':
            errors.append(IntegrityError("ERROR",
                f"Non-strength workout on strength-only day: {filename} ({day_abbrev} is strength-only)"))

    # Summary info
    if ftp_tests_found:
        ftp_weeks = sorted(set(w[0] for w in ftp_tests_found))
        # Not an error, just info logged during verbose runs

    return errors


def validate_athlete_integrity(athlete_dir: Path) -> list:
    """
    Validate all athlete files are internally consistent.
    Returns list of IntegrityError objects.
    """
    errors = []

    # Load all files
    profile = load_yaml_safe(athlete_dir / 'profile.yaml')
    derived = load_yaml_safe(athlete_dir / 'derived.yaml')
    plan_dates = load_yaml_safe(athlete_dir / 'plan_dates.yaml')
    methodology = load_yaml_safe(athlete_dir / 'methodology.yaml')
    fueling = load_yaml_safe(athlete_dir / 'fueling.yaml')

    # Check required files exist
    if profile is None:
        errors.append(IntegrityError("CRITICAL", "profile.yaml not found"))
        return errors  # Can't continue without profile

    if derived is None:
        errors.append(IntegrityError("ERROR", "derived.yaml not found - run classification"))

    if plan_dates is None:
        errors.append(IntegrityError("ERROR", "plan_dates.yaml not found - run calculate_plan_dates.py"))

    # === RACE DATE CONSISTENCY ===
    profile_race_date = profile.get('target_race', {}).get('date')
    if not profile_race_date:
        errors.append(IntegrityError("CRITICAL", "No target_race.date in profile.yaml"))
    else:
        # Check derived matches
        if derived:
            derived_race_date = derived.get('race_date')
            if derived_race_date and derived_race_date != profile_race_date:
                errors.append(IntegrityError("CRITICAL",
                    f"Race date mismatch: profile={profile_race_date}, derived={derived_race_date}"))

        # Check plan_dates matches
        if plan_dates:
            plan_race_date = plan_dates.get('race_date')
            if plan_race_date and plan_race_date != profile_race_date:
                errors.append(IntegrityError("CRITICAL",
                    f"Race date mismatch: profile={profile_race_date}, plan_dates={plan_race_date}"))

    # === PLAN WEEKS CONSISTENCY ===
    if derived and plan_dates:
        derived_weeks = derived.get('plan_weeks')
        plan_weeks = plan_dates.get('plan_weeks')
        if derived_weeks and plan_weeks and derived_weeks != plan_weeks:
            errors.append(IntegrityError("ERROR",
                f"Plan weeks mismatch: derived={derived_weeks}, plan_dates={plan_weeks}"))

        # Check weeks list length matches plan_weeks
        weeks_list = plan_dates.get('weeks', [])
        if len(weeks_list) != plan_weeks:
            errors.append(IntegrityError("CRITICAL",
                f"Weeks list length ({len(weeks_list)}) != plan_weeks ({plan_weeks})"))

    # === PLAN START CONSISTENCY ===
    if derived and plan_dates:
        derived_start = derived.get('plan_start')
        plan_start = plan_dates.get('plan_start')
        if derived_start and plan_start and derived_start != plan_start:
            errors.append(IntegrityError("ERROR",
                f"Plan start mismatch: derived={derived_start}, plan_dates={plan_start}"))

    # === RACE WEEK VALIDATION ===
    if plan_dates and profile_race_date:
        weeks = plan_dates.get('weeks', [])
        if weeks:
            race_week = weeks[-1]
            if not race_week.get('is_race_week'):
                errors.append(IntegrityError("CRITICAL", "Final week not marked as race week"))

            # Race date must be within race week
            race_dt = datetime.strptime(profile_race_date, '%Y-%m-%d')
            race_week_mon = datetime.strptime(race_week['monday'], '%Y-%m-%d')
            race_week_sun = datetime.strptime(race_week['sunday'], '%Y-%m-%d')

            if not (race_week_mon <= race_dt <= race_week_sun):
                errors.append(IntegrityError("CRITICAL",
                    f"Race date {profile_race_date} not in race week {race_week['monday']}-{race_week['sunday']}"))

            # Check is_race_day flag is set correctly
            race_day_found = False
            for day in race_week.get('days', []):
                if day.get('date') == profile_race_date:
                    if not day.get('is_race_day'):
                        errors.append(IntegrityError("ERROR",
                            f"Race day {profile_race_date} not marked is_race_day=true"))
                    race_day_found = True
                elif day.get('is_race_day'):
                    errors.append(IntegrityError("ERROR",
                        f"Wrong day marked as race day: {day.get('date')}"))

            if not race_day_found:
                errors.append(IntegrityError("ERROR", "Race day not found in race week days"))

    # === ATHLETE ID CONSISTENCY ===
    profile_id = profile.get('athlete_id')
    dir_name = athlete_dir.name

    if profile_id != dir_name:
        errors.append(IntegrityError("WARNING",
            f"athlete_id ({profile_id}) != directory name ({dir_name})"))

    if derived:
        derived_id = derived.get('athlete_id')
        if derived_id and derived_id != profile_id:
            errors.append(IntegrityError("ERROR",
                f"athlete_id mismatch: profile={profile_id}, derived={derived_id}"))

    # === METHODOLOGY VALIDATION ===
    if methodology:
        selected = methodology.get('selected_methodology')
        if not selected:
            errors.append(IntegrityError("ERROR", "No selected_methodology in methodology.yaml"))

        score = methodology.get('score')
        if score is not None and (score < 0 or score > 100):
            errors.append(IntegrityError("ERROR", f"Invalid methodology score: {score}"))

    # === FUELING VALIDATION ===
    if fueling:
        # Check race distance matches
        fueling_distance = fueling.get('race', {}).get('distance_miles')
        profile_distance = profile.get('target_race', {}).get('distance_miles')

        if fueling_distance and profile_distance:
            if abs(fueling_distance - profile_distance) > 0.1:
                errors.append(IntegrityError("WARNING",
                    f"Fueling distance ({fueling_distance}) != profile distance ({profile_distance})"))

        # Check hourly carb target is reasonable
        hourly_carb = fueling.get('carbohydrates', {}).get('hourly_target')
        if hourly_carb:
            if hourly_carb < 30 or hourly_carb > 120:
                errors.append(IntegrityError("WARNING",
                    f"Unusual hourly carb target: {hourly_carb}g (expected 30-120g)"))

    # === WORKOUT SCHEDULE ALIGNMENT ===
    workouts_dir = athlete_dir / 'workouts'
    if workouts_dir.exists() and profile and plan_dates:
        workout_errors = validate_workout_schedule_alignment(
            workouts_dir, profile, plan_dates, derived
        )
        errors.extend(workout_errors)

    # === GENERATED GUIDE QC ===
    guide_path = athlete_dir / 'training_guide.html'
    if guide_path.exists() and derived:
        with open(guide_path, 'r', encoding='utf-8') as f:
            guide_content = f.read()

        plan_weeks = derived.get('plan_weeks', 12)

        # Check for hardcoded "12-week" that should be dynamic
        if plan_weeks != 12:
            if '12-Week Arc' in guide_content or '12-week plan' in guide_content:
                errors.append(IntegrityError("ERROR",
                    f"Guide contains hardcoded '12-week' but plan is {plan_weeks} weeks - regenerate guide"))

            # Check correct week count appears
            if f'{plan_weeks}-Week Arc' not in guide_content:
                errors.append(IntegrityError("ERROR",
                    f"Guide missing '{plan_weeks}-Week Arc' - regenerate guide"))

        # === CHECK: Guide contains correct race name ===
        target_race_name = profile.get('target_race', {}).get('name', '')
        if target_race_name:
            # Check the race name appears in the guide
            if target_race_name not in guide_content:
                errors.append(IntegrityError("CRITICAL",
                    f"Guide does not contain target race name '{target_race_name}' - wrong race data used!"))

            # Check for wrong race names (common mistakes)
            wrong_races = ['Unbound', 'UNBOUND', 'DK200', 'Dirty Kanza']
            if 'SBT' in target_race_name.upper() or 'GRVL' in target_race_name.upper():
                for wrong_race in wrong_races:
                    if wrong_race in guide_content and wrong_race not in target_race_name:
                        errors.append(IntegrityError("CRITICAL",
                            f"Guide contains '{wrong_race}' but target race is '{target_race_name}' - wrong race data!"))

            # Similarly check if target is Unbound but guide shows SBT
            if 'Unbound' in target_race_name or 'unbound' in target_race_name.lower():
                if 'SBT GRVL' in guide_content or 'Steamboat' in guide_content:
                    errors.append(IntegrityError("CRITICAL",
                        f"Guide contains SBT GRVL data but target race is '{target_race_name}' - wrong race data!"))

        # === CHECK: Race date in guide matches profile ===
        target_race_date = profile.get('target_race', {}).get('date', '')
        if target_race_date:
            # Parse date to check month
            try:
                race_dt = datetime.strptime(target_race_date, '%Y-%m-%d')
                race_month = race_dt.strftime('%B')  # e.g., "June"
                race_month_short = race_dt.strftime('%b')  # e.g., "Jun"
                race_month_num = race_dt.strftime('%m')  # e.g., "06"

                # Guide should mention the race month or date somewhere
                # Accept: "June", "Jun", "2026-06-", or the full race date
                month_referenced = (
                    race_month in guide_content or
                    race_month_short in guide_content or
                    f'-{race_month_num}-' in guide_content or
                    target_race_date in guide_content
                )

                if not month_referenced:
                    errors.append(IntegrityError("WARNING",
                        f"Guide may not reference race month ({race_month}) - verify race date is correct"))
            except ValueError:
                pass  # Date parsing failed, skip this check

    # === DATE SANITY CHECKS ===
    if plan_dates:
        plan_start_str = plan_dates.get('plan_start')
        plan_end_str = plan_dates.get('plan_end')

        if plan_start_str and plan_end_str:
            plan_start = datetime.strptime(plan_start_str, '%Y-%m-%d')
            plan_end = datetime.strptime(plan_end_str, '%Y-%m-%d')

            if plan_start >= plan_end:
                errors.append(IntegrityError("CRITICAL",
                    f"Plan start ({plan_start_str}) >= plan end ({plan_end_str})"))

            # Check plan isn't unreasonably long
            days = (plan_end - plan_start).days
            if days > 365:
                errors.append(IntegrityError("WARNING",
                    f"Plan is {days} days ({days//7} weeks) - unusually long"))

            # Check plan start isn't too far in the past
            today = datetime.now()
            if plan_start < today:
                days_past = (today - plan_start).days
                if days_past > 14:
                    errors.append(IntegrityError("WARNING",
                        f"Plan start is {days_past} days in the past"))

    return errors


def validate_known_races(profile: dict) -> list:
    """Validate against known race calendar."""
    errors = []

    # Known 2026 race dates (add more as needed)
    # Sources:
    # - Unbound: https://www.unboundgravel.com/ (May 28-31, 2026, 200 on Saturday May 30)
    # - SBT GRVL: https://www.sbtgrvl.com/ (June 26-28, 2026, race Sunday June 28)
    KNOWN_RACES = {
        'sbt_grvl': '2026-06-28',  # SBT GRVL - Sunday June 28, 2026
        'unbound_gravel_200': '2026-05-30',  # Unbound 200 - Saturday May 30, 2026
        'unbound_gravel_100': '2026-05-30',  # Unbound 100 - Saturday May 30, 2026
        'unbound_gravel_50': '2026-05-30',   # Unbound 50
        'unbound_xl': '2026-05-29',  # Unbound XL (350) - Friday May 29
    }

    race_id = profile.get('target_race', {}).get('race_id', '')
    profile_date = profile.get('target_race', {}).get('date')

    # Check if race_id matches a known race
    for known_id, known_date in KNOWN_RACES.items():
        if known_id in race_id.lower():
            if profile_date != known_date:
                errors.append(IntegrityError("CRITICAL",
                    f"Race date for {race_id} should be {known_date}, not {profile_date}"))
            break

    return errors


def validate_guide_deployment(athlete_id: str, guide_url: str = None) -> list:
    """
    Validate the training guide is deployed and accessible.

    Checks:
    1. Guide URL returns HTTP 200
    2. Guide content contains expected athlete name
    3. Guide is not a 404 page masquerading as 200
    """
    import urllib.request
    import urllib.error

    errors = []

    # Default URL pattern
    if guide_url is None:
        guide_url = f"https://wattgod.github.io/gravel-god-guides/athletes/{athlete_id}/"

    try:
        # Check URL is accessible
        req = urllib.request.Request(guide_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            content = response.read().decode('utf-8', errors='ignore')

            if status != 200:
                errors.append(IntegrityError("CRITICAL",
                    f"Guide URL returned HTTP {status}: {guide_url}"))

            # Check it's not a 404 page disguised as 200
            if '404' in content[:1000] and 'not found' in content.lower()[:1000]:
                errors.append(IntegrityError("CRITICAL",
                    f"Guide URL appears to be a 404 page: {guide_url}"))

            # Check for expected content markers
            if '<title>' not in content:
                errors.append(IntegrityError("ERROR",
                    f"Guide URL returned invalid HTML (no title): {guide_url}"))

            # Check guide contains "Custom Training Plan" or similar
            if 'Training Plan' not in content and 'training plan' not in content.lower():
                errors.append(IntegrityError("ERROR",
                    f"Guide URL does not appear to be a training guide: {guide_url}"))

    except urllib.error.HTTPError as e:
        errors.append(IntegrityError("CRITICAL",
            f"Guide URL returned HTTP {e.code}: {guide_url}"))
    except urllib.error.URLError as e:
        errors.append(IntegrityError("CRITICAL",
            f"Guide URL unreachable: {guide_url} - {e.reason}"))
    except Exception as e:
        errors.append(IntegrityError("ERROR",
            f"Error checking guide URL {guide_url}: {str(e)}"))

    return errors


def run_integrity_check(athlete_id: str, check_deployment: bool = False) -> bool:
    """Run full integrity check for an athlete."""
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id

    if not athlete_dir.exists():
        print(f"ERROR: Athlete directory not found: {athlete_dir}")
        return False

    print("=" * 60)
    print(f"INTEGRITY CHECK: {athlete_id}")
    print("=" * 60)

    # Run validations
    errors = validate_athlete_integrity(athlete_dir)

    # Also validate against known races
    profile = load_yaml_safe(athlete_dir / 'profile.yaml')
    if profile:
        errors.extend(validate_known_races(profile))

    # Check guide deployment if requested
    if check_deployment:
        print("\n🌐 Checking guide deployment...")
        deployment_errors = validate_guide_deployment(athlete_id)
        errors.extend(deployment_errors)
        if not deployment_errors:
            print(f"   ✓ Guide accessible at: https://wattgod.github.io/gravel-god-guides/athletes/{athlete_id}/")

    # Categorize errors
    critical = [e for e in errors if e.level == "CRITICAL"]
    error_level = [e for e in errors if e.level == "ERROR"]
    warnings = [e for e in errors if e.level == "WARNING"]

    # Print results
    if critical:
        print("\n🚨 CRITICAL ISSUES:")
        for e in critical:
            print(f"   {e}")

    if error_level:
        print("\n❌ ERRORS:")
        for e in error_level:
            print(f"   {e}")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for e in warnings:
            print(f"   {e}")

    # Summary
    print("\n" + "-" * 40)
    print(f"Critical: {len(critical)}, Errors: {len(error_level)}, Warnings: {len(warnings)}")

    if critical:
        print("❌ INTEGRITY CHECK FAILED - CRITICAL ISSUES")
        return False
    elif error_level:
        print("⚠️  INTEGRITY CHECK PASSED WITH ERRORS")
        return True  # Passed but with issues
    elif warnings:
        print("✅ INTEGRITY CHECK PASSED (with warnings)")
        return True
    else:
        print("✅ INTEGRITY CHECK PASSED")
        return True


def run_all_athletes() -> bool:
    """Run integrity check for all athletes."""
    athletes_dir = Path(__file__).parent.parent
    all_passed = True

    for athlete_dir in sorted(athletes_dir.iterdir()):
        if athlete_dir.is_dir() and (athlete_dir / 'profile.yaml').exists():
            if not run_integrity_check(athlete_dir.name):
                all_passed = False
            print()

    return all_passed


if __name__ == '__main__':
    if len(sys.argv) > 1:
        check_deployment = '--check-deployment' in sys.argv or '-d' in sys.argv
        args = [a for a in sys.argv[1:] if not a.startswith('-')]

        if '--all' in sys.argv:
            success = run_all_athletes()
        elif args:
            success = run_integrity_check(args[0], check_deployment=check_deployment)
        else:
            print("Usage: python3 test_athlete_integrity.py <athlete_id> [-d|--check-deployment]")
            print("       python3 test_athlete_integrity.py --all")
            print("\nOptions:")
            print("  -d, --check-deployment  Validate guide is accessible at live URL")
            sys.exit(1)
    else:
        print("Usage: python3 test_athlete_integrity.py <athlete_id> [-d|--check-deployment]")
        print("       python3 test_athlete_integrity.py --all")
        print("\nOptions:")
        print("  -d, --check-deployment  Validate guide is accessible at live URL")
        sys.exit(1)

    sys.exit(0 if success else 1)
