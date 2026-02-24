#!/usr/bin/env python3
"""
Calculate plan dates working backwards from race date.

Plan Dating Standards:
- Race week = final week of plan
- Week 1 = first training week (furthest from race)
- Plan starts on Monday of Week 1
- Each week runs Monday-Sunday
- Workouts named: W{week:02d}_{day}_{month}{day_num}_{workout_name}.zwo
  e.g., W01_Mon_Feb16_Endurance.zwo, W19_Sat_Jun27_Race_Simulation.zwo

Day abbreviations: Mon, Tue, Wed, Thu, Fri, Sat, Sun
Month abbreviations: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
"""

import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from constants import DAY_ORDER, DAY_ORDER_DISPLAY, DAY_FULL_TO_ABBREV


class PlanDateValidationError(Exception):
    """Raised when plan dates fail validation."""
    pass


def validate_plan_dates(plan_dates: dict, race_date_str: str) -> list:
    """
    Validate plan dates for sanity.

    Returns list of errors (empty if valid).
    """
    errors = []

    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    plan_start = datetime.strptime(plan_dates['plan_start'], '%Y-%m-%d')
    plan_end = datetime.strptime(plan_dates['plan_end'], '%Y-%m-%d')
    plan_weeks = plan_dates['plan_weeks']
    weeks = plan_dates.get('weeks', [])

    # 1. Race date must be within race week
    race_week = weeks[-1] if weeks else None
    if race_week:
        race_week_monday = datetime.strptime(race_week['monday'], '%Y-%m-%d')
        race_week_sunday = datetime.strptime(race_week['sunday'], '%Y-%m-%d')
        if not (race_week_monday <= race_date <= race_week_sunday):
            errors.append(f"CRITICAL: Race date {race_date_str} not in race week ({race_week['monday']} - {race_week['sunday']})")

    # 2. Plan start must be before race date
    if plan_start >= race_date:
        errors.append(f"CRITICAL: Plan start {plan_dates['plan_start']} must be before race date {race_date_str}")

    # 3. Plan end must be on or after race date
    if plan_end < race_date:
        errors.append(f"CRITICAL: Plan end {plan_dates['plan_end']} must be on or after race date {race_date_str}")

    # 4. Plan weeks must match actual weeks list
    if len(weeks) != plan_weeks:
        errors.append(f"CRITICAL: plan_weeks ({plan_weeks}) doesn't match weeks list length ({len(weeks)})")

    # 5. Week 1 must start on plan_start
    if weeks and weeks[0]['monday'] != plan_dates['plan_start']:
        errors.append(f"CRITICAL: Week 1 Monday ({weeks[0]['monday']}) doesn't match plan_start ({plan_dates['plan_start']})")

    # 6. Final week must be race week
    if weeks and not weeks[-1]['is_race_week']:
        errors.append(f"CRITICAL: Final week must be race week")

    # 7. Weeks must be consecutive
    for i in range(1, len(weeks)):
        prev_sunday = datetime.strptime(weeks[i-1]['sunday'], '%Y-%m-%d')
        curr_monday = datetime.strptime(weeks[i]['monday'], '%Y-%m-%d')
        if (curr_monday - prev_sunday).days != 1:
            errors.append(f"CRITICAL: Gap between week {i} and week {i+1}")

    # 8. Week numbers must be sequential
    for i, week in enumerate(weeks):
        if week['week'] != i + 1:
            errors.append(f"CRITICAL: Week number mismatch at index {i}: expected {i+1}, got {week['week']}")

    # 9. Plan must be at least 6 weeks
    if plan_weeks < 6:
        errors.append(f"WARNING: Plan is only {plan_weeks} weeks (minimum recommended: 6)")

    # 10. Plan start should not be in the past (warning only)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if plan_start < today:
        days_past = (today - plan_start).days
        errors.append(f"WARNING: Plan start is {days_past} days in the past")

    return errors


def calculate_plan_dates(race_date_str: str, plan_weeks: int = 12,
                         preferred_start: str = None,
                         heavy_training_end: str = None,
                         b_events: list = None) -> dict:
    """
    Calculate all plan dates working backwards from race date.

    Args:
        race_date_str: Race date in YYYY-MM-DD format
        plan_weeks: Number of weeks in the plan
        preferred_start: Optional preferred start date (plan may start later if race is sooner)
        heavy_training_end: Optional date when heavy training must end (e.g., "2026-06-01")
                           Weeks after this date will be maintenance/taper instead of build/peak
        b_events: Optional list of B-priority events from profile, each with 'name' and 'date'

    Returns:
        Dict with plan timing information

    Raises:
        ValueError: If plan_weeks < 4 (can't fit base+build+taper) or > 52 (unreasonable)
    """
    # Sanity bounds on plan_weeks
    if plan_weeks < 4:
        raise ValueError("Plan must be at least 4 weeks")
    if plan_weeks > 52:
        raise ValueError("Plan cannot exceed 52 weeks")

    # Parse race date
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Race week ends on Sunday after race (or race day if Sunday)
    # Race week starts on Monday of that week
    race_weekday = race_date.weekday()  # 0=Monday, 6=Sunday
    race_week_monday = race_date - timedelta(days=race_weekday)

    # Week 1 Monday is (plan_weeks - 1) weeks before race week Monday
    week1_monday = race_week_monday - timedelta(weeks=plan_weeks - 1)

    # Check if we need to adjust for preferred start
    if preferred_start:
        preferred = datetime.strptime(preferred_start, '%Y-%m-%d')
        # If preferred start is after calculated Week 1, we have fewer weeks
        if preferred > week1_monday:
            # Recalculate plan_weeks based on available time
            days_available = (race_week_monday - preferred).days
            available_weeks = days_available // 7 + 1  # +1 for race week
            if available_weeks < plan_weeks:
                plan_weeks = max(6, available_weeks)  # Minimum 6-week plan
                week1_monday = race_week_monday - timedelta(weeks=plan_weeks - 1)

    # If Week 1 would be in the past, start from next Monday
    if week1_monday < today:
        # Find next Monday
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, start next Monday
        adjusted_start = today + timedelta(days=days_until_monday)

        # Recalculate available weeks
        days_available = (race_week_monday - adjusted_start).days
        available_weeks = days_available // 7 + 1
        plan_weeks = max(6, available_weeks)
        week1_monday = adjusted_start

    # Month abbreviations
    month_abbrev = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Generate week-by-week dates
    week_dates = []
    for week_num in range(1, plan_weeks + 1):
        week_monday = week1_monday + timedelta(weeks=week_num - 1)
        week_sunday = week_monday + timedelta(days=6)

        # Determine phase based on position in plan and constraints
        progress = week_num / plan_weeks

        # Check if this week is after heavy_training_end constraint
        in_maintenance_period = False
        if heavy_training_end:
            heavy_end_dt = datetime.strptime(heavy_training_end, '%Y-%m-%d')
            # If week starts on or after heavy_training_end, it's maintenance
            if week_monday >= heavy_end_dt:
                in_maintenance_period = True

        if week_num == plan_weeks:
            phase = 'race'
        elif week_num >= plan_weeks - 1:
            phase = 'taper'
        elif in_maintenance_period:
            # After heavy training ends, switch to maintenance
            phase = 'maintenance'
        elif progress >= 0.75:
            phase = 'peak'
        elif progress >= 0.5:
            phase = 'build'
        else:
            phase = 'base'

        # Generate day-by-day info for this week
        days = []
        for day_offset in range(7):
            day_date = week_monday + timedelta(days=day_offset)
            day_abbrev = DAY_ORDER[day_offset]
            month = month_abbrev[day_date.month - 1]
            day_num = day_date.day

            days.append({
                'day': day_abbrev,
                'date': day_date.strftime('%Y-%m-%d'),
                'date_short': f"{month}{day_num}",
                'workout_prefix': f"W{week_num:02d}_{day_abbrev}_{month}{day_num}",
                'is_race_day': day_date == race_date
            })

        week_dates.append({
            'week': week_num,
            'monday': week_monday.strftime('%Y-%m-%d'),
            'monday_short': f"{month_abbrev[week_monday.month - 1]}{week_monday.day}",
            'sunday': week_sunday.strftime('%Y-%m-%d'),
            'sunday_short': f"{month_abbrev[week_sunday.month - 1]}{week_sunday.day}",
            'phase': phase,
            'is_race_week': week_num == plan_weeks,
            'days': days
        })

    # ---------------------------------------------------------------
    # B-race overlay: mark weeks containing B-priority events
    # This runs AFTER primary phase assignment so it doesn't disrupt
    # the overall plan structure (base/build/peak/taper/race).
    # ---------------------------------------------------------------
    if b_events:
        for b_event in b_events:
            b_date_str = b_event.get('date')
            b_name = b_event.get('name', 'B-Race')
            if not b_date_str:
                continue  # Skip B-events without a date

            b_date = datetime.strptime(b_date_str, '%Y-%m-%d')

            for week_data in week_dates:
                w_monday = datetime.strptime(week_data['monday'], '%Y-%m-%d')
                w_sunday = datetime.strptime(week_data['sunday'], '%Y-%m-%d')

                if w_monday <= b_date <= w_sunday:
                    # Mark this week as containing a B-race
                    week_data['b_race'] = {
                        'name': b_name,
                        'date': b_date_str,
                        'phase': week_data['phase'],  # Original phase preserved
                    }

                    # Mark the specific day as a B-race day
                    for day_data in week_data['days']:
                        if day_data['date'] == b_date_str:
                            day_data['is_b_race_day'] = True

                        # Mark the day before the race as an opener day
                        day_dt = datetime.strptime(day_data['date'], '%Y-%m-%d')
                        if day_dt == b_date - timedelta(days=1):
                            day_data['is_b_race_opener'] = True

                        # For build/peak phases, mark 2 days before as easy
                        if week_data['phase'] in ('build', 'peak'):
                            if day_dt == b_date - timedelta(days=2):
                                day_data['is_b_race_easy'] = True

                    break  # Found the week, move to next B-event

    result = {
        'race_date': race_date_str,
        'race_weekday': DAY_ORDER_DISPLAY[race_weekday],
        'plan_weeks': plan_weeks,
        'plan_start': week1_monday.strftime('%Y-%m-%d'),
        'plan_start_short': f"{month_abbrev[week1_monday.month - 1]}{week1_monday.day}",
        'plan_end': (race_week_monday + timedelta(days=6)).strftime('%Y-%m-%d'),
        'week1_monday': week1_monday.strftime('%Y-%m-%d'),
        'race_week_monday': race_week_monday.strftime('%Y-%m-%d'),
        'weeks': week_dates,
        'workout_naming_convention': 'W{week:02d}_{day}_{month}{day}_{name}.zwo',
        'workout_example': f"W01_Mon_{month_abbrev[week1_monday.month - 1]}{week1_monday.day}_Endurance.zwo",
        'day_abbreviations': DAY_FULL_TO_ABBREV,
        'month_abbreviations': {i+1: m for i, m in enumerate(month_abbrev)}
    }

    return result


def format_week_calendar(week_dates: list, race_date: str) -> str:
    """Format week dates for display with validation markers."""
    lines = []
    lines.append("Week  | Phase  | Start (Mon) | End (Sun)   | Notes")
    lines.append("------|--------|-------------|-------------|------")

    for week in week_dates:
        notes = ""
        if week['is_race_week']:
            notes = f"RACE WEEK - Race on {race_date}"
        elif week.get('b_race'):
            b = week['b_race']
            notes = f"B-RACE: {b['name']} on {b['date']}"

        lines.append(
            f"W{week['week']:02d}   | {week['phase']:<6} | {week['monday']} | {week['sunday']} | {notes}"
        )

    return "\n".join(lines)


def run_sanity_checks(plan_dates: dict, race_date_str: str, athlete_id: str) -> bool:
    """Run all sanity checks and print results."""
    print("\n🔍 SANITY CHECKS:")
    print("-" * 40)

    errors = validate_plan_dates(plan_dates, race_date_str)

    # Additional display checks
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    plan_start = datetime.strptime(plan_dates['plan_start'], '%Y-%m-%d')

    checks = [
        ("Race date", race_date_str, True),
        ("Race day of week", plan_dates['race_weekday'], True),
        ("Plan weeks", plan_dates['plan_weeks'], plan_dates['plan_weeks'] >= 6),
        ("Plan start", plan_dates['plan_start'], plan_start <= race_date),
        ("Plan end", plan_dates['plan_end'], True),
        ("W01 starts on", plan_dates['week1_monday'], plan_dates['week1_monday'] == plan_dates['plan_start']),
        ("Race week starts", plan_dates['race_week_monday'], True),
    ]

    all_passed = True
    for name, value, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {value}")
        if not passed:
            all_passed = False

    # Print errors
    if errors:
        print("\n⚠️  VALIDATION ISSUES:")
        for error in errors:
            if error.startswith("CRITICAL"):
                print(f"  ✗ {error}")
                all_passed = False
            else:
                print(f"  ⚡ {error}")

    # Final verdict
    print("\n" + "-" * 40)
    if all_passed and not any(e.startswith("CRITICAL") for e in errors):
        print("✅ ALL SANITY CHECKS PASSED")
    else:
        print("❌ SANITY CHECKS FAILED - DO NOT USE THIS PLAN")

    return all_passed


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Calculate plan dates from race date')
    parser.add_argument('athlete_id', help='Athlete ID')
    parser.add_argument('--weeks', type=int, help='Override plan weeks')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing plan_dates.yaml')

    args = parser.parse_args()

    # Load athlete data
    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / args.athlete_id

    if not athlete_dir.exists():
        print(f"ERROR: Athlete directory not found: {athlete_dir}")
        sys.exit(1)

    # Load profile
    profile_path = athlete_dir / 'profile.yaml'
    if not profile_path.exists():
        print(f"ERROR: Profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    # Get race date
    race_date = profile.get('target_race', {}).get('date')
    if not race_date:
        print("ERROR: No target race date in profile")
        sys.exit(1)

    # Validate-only mode
    if args.validate_only:
        plan_dates_path = athlete_dir / 'plan_dates.yaml'
        if not plan_dates_path.exists():
            print(f"ERROR: No plan_dates.yaml to validate: {plan_dates_path}")
            sys.exit(1)

        with open(plan_dates_path, 'r') as f:
            plan_dates = yaml.safe_load(f)

        passed = run_sanity_checks(plan_dates, race_date, args.athlete_id)
        sys.exit(0 if passed else 1)

    # Get preferred start
    preferred_start = profile.get('plan_start', {}).get('preferred_start')

    # Load derived.yaml if exists to get plan_weeks and constraints
    derived_path = athlete_dir / 'derived.yaml'
    plan_weeks = args.weeks
    heavy_training_end = None
    if not plan_weeks and derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)
            plan_weeks = derived.get('plan_weeks', 12)
            heavy_training_end = derived.get('heavy_training_end')
    elif not plan_weeks:
        plan_weeks = 12

    # Get B-events from profile
    b_events = profile.get('b_events', [])

    # Calculate dates with constraints
    plan_dates = calculate_plan_dates(race_date, plan_weeks, preferred_start, heavy_training_end, b_events)

    # Print summary
    print("=" * 60)
    print(f"Plan Calendar: {args.athlete_id}")
    print("=" * 60)
    print(f"\nRace: {profile.get('target_race', {}).get('name', 'Unknown')}")
    print(f"Race Date: {plan_dates['race_date']} ({plan_dates['race_weekday']})")
    print(f"Plan Duration: {plan_dates['plan_weeks']} weeks")
    print(f"Plan Start: {plan_dates['plan_start']} (Week 1 Monday)")
    print(f"Plan End: {plan_dates['plan_end']} (Race Week Sunday)")

    print(f"\nWorkout Naming: {plan_dates['workout_naming_convention']}")
    print(f"Example: {plan_dates['workout_example']}")

    print(f"\n{format_week_calendar(plan_dates['weeks'], plan_dates['race_date'])}")

    # Run sanity checks
    passed = run_sanity_checks(plan_dates, race_date, args.athlete_id)

    if not passed:
        print("\n⛔ NOT SAVING - Fix errors first")
        sys.exit(1)

    # Save to plan_dates.yaml
    output_path = athlete_dir / 'plan_dates.yaml'
    with open(output_path, 'w') as f:
        yaml.dump(plan_dates, f, default_flow_style=False, sort_keys=False)

    print(f"\n💾 Saved to: {output_path}")

    # Also update derived.yaml with corrected dates
    if derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)

        derived['plan_start'] = plan_dates['plan_start']
        derived['plan_end'] = plan_dates['plan_end']
        derived['plan_weeks'] = plan_dates['plan_weeks']
        derived['race_weekday'] = plan_dates['race_weekday']

        with open(derived_path, 'w') as f:
            yaml.dump(derived, f, default_flow_style=False, sort_keys=False)

        print(f"📝 Updated: {derived_path}")


if __name__ == '__main__':
    main()
