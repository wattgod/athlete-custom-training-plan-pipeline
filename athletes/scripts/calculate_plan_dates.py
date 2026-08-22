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

import os
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from constants import (
    DAY_ORDER, DAY_ORDER_DISPLAY, DAY_FULL_TO_ABBREV,
    PLAN_WEEKS_MIN, PLAN_WEEKS_MAX,
)
from derived_registry import assert_registry_covers, entry as derived_entry


class PlanDateValidationError(Exception):
    """Raised when plan dates fail validation."""
    pass


def generation_now() -> datetime:
    """Injectable production clock used by deterministic replay gates."""
    fixed = os.environ.get('GG_FIXED_NOW', '').strip()
    if fixed:
        return datetime.fromisoformat(fixed.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.now()


def monday_on_or_after(day: datetime) -> datetime:
    """Monday of `day` when it is Monday; otherwise the following Monday."""
    return day + timedelta(days=(7 - day.weekday()) % 7)


def paid_weeks_calendar_max(race_date_str: str, generation_at: str = None) -> int:
    """Max paid weeks that fit without Week 1 starting before generation.

    Week 1 Monday = monday_on_or_after(generation_date).
    Race-week Monday = Monday of the race date.
    calendar_max = (race_week_monday - week1_monday).days // 7 + 1
    Floored at 1 when the race is still in the future.
    """
    if generation_at:
        generation_date = datetime.fromisoformat(
            str(generation_at).replace('Z', '+00:00')).replace(tzinfo=None)
    else:
        generation_date = generation_now()
    generation_date = generation_date.replace(
        hour=0, minute=0, second=0, microsecond=0)
    week1_monday = monday_on_or_after(generation_date)
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    race_week_monday = race_date - timedelta(days=race_date.weekday())
    calendar_max = (race_week_monday - week1_monday).days // 7 + 1
    if calendar_max < 1 and race_date >= generation_date:
        return 1
    return calendar_max


def _fit_weeks_to_calendar(
    requested_weeks: int,
    race_week_monday: datetime,
    start_monday: datetime,
) -> tuple:
    """Clamp requested weeks to Mondays that fit; never invent a 4-week floor.

    If the start Monday is after race week (race this weekend), deliver 1
    week targeting race week.
    """
    days_available = (race_week_monday - start_monday).days
    available_weeks = days_available // 7 + 1
    if available_weeks < 1:
        return 1, race_week_monday
    plan_weeks = min(requested_weeks, available_weeks)
    week1_monday = race_week_monday - timedelta(weeks=plan_weeks - 1)
    return plan_weeks, week1_monday


def post_event_recovery_weeks_for_horizon(
    race_date_str: str, planning_horizon_end: str | None,
) -> int:
    """Map an exact Sunday horizon to the supported post-event extension."""
    if not planning_horizon_end:
        return 0
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    race_week_sunday = race_date + timedelta(days=6 - race_date.weekday())
    horizon = datetime.strptime(str(planning_horizon_end), '%Y-%m-%d')
    delta_days = (horizon - race_week_sunday).days
    if delta_days < 0 or horizon.weekday() != 6 or delta_days % 7:
        raise ValueError(
            "planning_horizon_end must be a Sunday on or after race-week Sunday")
    recovery_weeks = delta_days // 7
    if recovery_weeks > 1:
        raise ValueError("planning horizon requests more than one recovery week")
    return recovery_weeks


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

    # 1. Exactly one race week must contain the target event. Recovery may
    # follow it when the sealed planning horizon explicitly requests that.
    race_weeks = [week for week in weeks if week.get('is_race_week')]
    race_week = race_weeks[0] if len(race_weeks) == 1 else None
    if len(race_weeks) != 1:
        errors.append(f"CRITICAL: Expected exactly one race week, found {len(race_weeks)}")
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

    # 6. Weeks after race week must be explicit post-event recovery.
    if race_week:
        race_index = weeks.index(race_week)
        for week in weeks[race_index + 1:]:
            if (week.get('phase') != 'recovery'
                    or not week.get('is_recovery_week')
                    or not week.get('is_post_event_recovery')
                    or week.get('is_race_week')):
                errors.append(
                    f"CRITICAL: Week {week.get('week')} after race must be post-event recovery")

    if weeks and plan_dates['plan_end'] != weeks[-1]['sunday']:
        errors.append("CRITICAL: Plan end must match final week Sunday")

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
    today = generation_now().replace(hour=0, minute=0, second=0, microsecond=0)
    if plan_start < today:
        days_past = (today - plan_start).days
        errors.append(f"WARNING: Plan start is {days_past} days in the past")

    return errors


def parse_meso_pattern(pattern: str) -> tuple:
    """Parse meso pattern string like '3:1' into (load_weeks, recovery_weeks)."""
    try:
        parts = pattern.split(':')
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return (3, 1)  # Safe default


def calculate_plan_dates(race_date_str: str, plan_weeks: int = 12,
                         preferred_start: str = None,
                         heavy_training_end: str = None,
                         b_events: list = None,
                         meso_pattern: str = None,
                         travel_dates: list = None,
                         generation_revision: int = 1,
                         derived_at: str = None,
                         clamp_past_start: bool = True,
                         post_event_recovery_weeks: int = 0) -> dict:
    """
    Calculate all plan dates working backwards from race date.

    Args:
        race_date_str: Race date in YYYY-MM-DD format
        plan_weeks: Number of weeks in the plan
        preferred_start: Optional preferred start date (plan may start later if race is sooner)
        heavy_training_end: Optional date when heavy training must end (e.g., "2026-06-01")
                           Weeks after this date will be maintenance/taper instead of build/peak
        b_events: Optional list of B-priority events from profile, each with 'name' and 'date'
        clamp_past_start: When True (fulfillment default), Week 1 never
            starts before the generation date. Endure season planning
            passes False so a mid-week request can still include the
            current Monday.

    Returns:
        Dict with plan timing information

    Raises:
        ValueError: If plan_weeks < 1 or > 52 (unreasonable to generate 2 years)
    """
    # Sanity bounds on plan_weeks — 1+ paid weeks are valid; 52 is the hard cap.
    if plan_weeks < PLAN_WEEKS_MIN:
        raise ValueError(f"Plan must be at least {PLAN_WEEKS_MIN} week")
    if plan_weeks > PLAN_WEEKS_MAX:
        raise ValueError(f"Plan cannot exceed {PLAN_WEEKS_MAX} weeks")
    if (not isinstance(post_event_recovery_weeks, int)
            or isinstance(post_event_recovery_weeks, bool)
            or not 0 <= post_event_recovery_weeks <= 1):
        raise ValueError("post_event_recovery_weeks must be 0 or 1")

    # Parse race date
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    today = generation_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Race week ends on Sunday after race (or race day if Sunday)
    # Race week starts on Monday of that week
    race_weekday = race_date.weekday()  # 0=Monday, 6=Sunday
    race_week_monday = race_date - timedelta(days=race_weekday)

    # Week 1 Monday is (plan_weeks - 1) weeks before race week Monday
    week1_monday = race_week_monday - timedelta(weeks=plan_weeks - 1)

    # Preferred start may only delay the plan. Snap mid-week values forward
    # to a Monday, and never honor a preferred Monday that is already past.
    if preferred_start:
        preferred = monday_on_or_after(
            datetime.strptime(preferred_start, '%Y-%m-%d'))
        if clamp_past_start and preferred < today:
            preferred = monday_on_or_after(today)
        if preferred > week1_monday:
            plan_weeks, week1_monday = _fit_weeks_to_calendar(
                plan_weeks, race_week_monday, preferred)

    # SESSION_PREDATES_GENERATION is a real blocker. Working backwards from
    # race week can land Week 1 before today when the athlete has a mid-week
    # preferred_start. Always finish with a Week 1 on or after today when
    # clamp_past_start is True. Endure season planning passes False.
    if clamp_past_start and week1_monday < today:
        plan_weeks, week1_monday = _fit_weeks_to_calendar(
            plan_weeks, race_week_monday, monday_on_or_after(today))

    race_plan_weeks = plan_weeks

    # Month abbreviations
    month_abbrev = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Generate week-by-week dates
    week_dates = []
    for week_num in range(1, race_plan_weeks + 1):
        week_monday = week1_monday + timedelta(weeks=week_num - 1)
        week_sunday = week_monday + timedelta(days=6)

        # Determine phase based on position in plan and constraints
        progress = week_num / race_plan_weeks

        # Check if this week is after heavy_training_end constraint
        in_maintenance_period = False
        if heavy_training_end:
            heavy_end_dt = datetime.strptime(heavy_training_end, '%Y-%m-%d')
            # If week starts on or after heavy_training_end, it's maintenance
            if week_monday >= heavy_end_dt:
                in_maintenance_period = True

        if week_num == race_plan_weeks:
            phase = 'race'
        elif week_num >= race_plan_weeks - 1:
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
            'is_race_week': week_num == race_plan_weeks,
            'days': days
        })

    # ---------------------------------------------------------------
    # Recovery week marking: insert deload weeks per mesocycle pattern.
    # Runs AFTER phase assignment but BEFORE B-race overlay.
    # Recovery weeks preserve their training phase but get is_recovery_week=True.
    # ---------------------------------------------------------------
    from constants import RECOVERY_WEEK_MIN_PLAN_WEEKS, DEFAULT_MESO_PATTERN
    effective_pattern = meso_pattern or DEFAULT_MESO_PATTERN
    load_weeks, recovery_weeks = parse_meso_pattern(effective_pattern)
    cycle_length = load_weeks + recovery_weeks

    for week_data in week_dates:
        week_data['is_recovery_week'] = False  # Default

    if race_plan_weeks >= RECOVERY_WEEK_MIN_PLAN_WEEKS:
        for week_data in week_dates:
            wn = week_data['week']
            phase = week_data['phase']
            # Never mark taper or race weeks as recovery
            if phase in ('taper', 'race'):
                continue
            # Position within the mesocycle (0-indexed)
            position_in_cycle = (wn - 1) % cycle_length
            if position_in_cycle >= load_weeks:
                week_data['is_recovery_week'] = True

    # A sealed horizon may explicitly add one complete recovery week after
    # the target-event week. The race-week semantics above remain unchanged.
    for offset in range(1, post_event_recovery_weeks + 1):
        week_num = race_plan_weeks + offset
        week_monday = race_week_monday + timedelta(weeks=offset)
        week_sunday = week_monday + timedelta(days=6)
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
                'is_race_day': False,
            })
        week_dates.append({
            'week': week_num,
            'monday': week_monday.strftime('%Y-%m-%d'),
            'monday_short': f"{month_abbrev[week_monday.month - 1]}{week_monday.day}",
            'sunday': week_sunday.strftime('%Y-%m-%d'),
            'sunday_short': f"{month_abbrev[week_sunday.month - 1]}{week_sunday.day}",
            'phase': 'recovery',
            'is_race_week': False,
            'is_recovery_week': True,
            'is_post_event_recovery': True,
            'days': days,
        })

    total_plan_weeks = len(week_dates)

    if post_event_recovery_weeks and b_events:
        recovery_start = race_week_monday + timedelta(weeks=1)
        recovery_end = datetime.strptime(week_dates[-1]['sunday'], '%Y-%m-%d')
        for b_event in b_events:
            if not b_event.get('date'):
                continue
            b_date = datetime.strptime(b_event['date'], '%Y-%m-%d')
            if recovery_start <= b_date <= recovery_end:
                raise ValueError(
                    "post-event recovery week contains a later B event")

    # ---------------------------------------------------------------
    # B-race overlay: mark weeks containing B-priority events
    # This runs AFTER primary phase assignment so it doesn't disrupt
    # the overall plan structure (base/build/peak/taper/race).
    # If a B-race falls on a recovery week, clear recovery flag.
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
                    # B-race overrides recovery — athlete needs to race, not rest
                    if week_data.get('is_recovery_week'):
                        week_data['is_recovery_week'] = False

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

    # ---------------------------------------------------------------
    # Travel-day overlay: athletes lose training days to travel
    # (flights to races, relocations). Mark them so the renderer swaps
    # the planned workout for an optional shakeout. Race/B-race day
    # flags take precedence downstream.
    # ---------------------------------------------------------------
    if travel_dates:
        travel_set = {str(t).strip() for t in travel_dates if t}
        for week_data in week_dates:
            for day_data in week_data['days']:
                if day_data['date'] in travel_set:
                    day_data['is_travel_day'] = True

    result = {
        'race_date': race_date_str,
        'race_weekday': DAY_ORDER_DISPLAY[race_weekday],
        'plan_weeks': total_plan_weeks,
        'plan_start': week1_monday.strftime('%Y-%m-%d'),
        'plan_start_short': f"{month_abbrev[week1_monday.month - 1]}{week1_monday.day}",
        'plan_end': week_dates[-1]['sunday'],
        'week1_monday': week1_monday.strftime('%Y-%m-%d'),
        'race_week_monday': race_week_monday.strftime('%Y-%m-%d'),
        'weeks': week_dates,
        'workout_naming_convention': 'W{week:02d}_{day}_{month}{day}_{name}.zwo',
        'workout_example': f"W01_Mon_{month_abbrev[week1_monday.month - 1]}{week1_monday.day}_Endurance.zwo",
        'day_abbreviations': DAY_FULL_TO_ABBREV,
        'month_abbreviations': {i+1: m for i, m in enumerate(month_abbrev)}
    }

    registry_at = str(
        derived_at or generation_now().isoformat().replace('+00:00', 'Z'))
    common_inputs = {
        'race_date': race_date_str,
        'requested_plan_weeks': race_plan_weeks,
        'preferred_start': preferred_start,
        'heavy_training_end': heavy_training_end,
        'meso_pattern': effective_pattern,
        'b_event_count': len(b_events or []),
        'travel_date_count': len(travel_dates or []),
        'post_event_recovery_weeks': post_event_recovery_weeks,
    }

    def record(identifier, field, basis, inputs=None, sensitivity='personal'):
        return derived_entry(
            id=identifier, field=field, value_class='inferred', basis=basis,
            inputs=common_inputs if inputs is None else inputs,
            sensitivity=sensitivity, at=registry_at,
            revision=generation_revision)

    records = [
        record('CALENDAR_RACE_DATE', 'race_date', 'target race calendar fact'),
        record('CALENDAR_RACE_WEEKDAY', 'race_weekday', 'weekday derived from target race date'),
        record('CALENDAR_PLAN_WEEKS', 'plan_weeks',
               'available Mondays through race week plus explicit post-event recovery'),
        record('CALENDAR_PLAN_START', 'plan_start', 'first Monday in the final plan window'),
        record('CALENDAR_PLAN_START_SHORT', 'plan_start_short', 'display projection of plan start'),
        record('CALENDAR_PLAN_END', 'plan_end', 'Sunday ending the explicit planning horizon'),
        record('CALENDAR_WEEK1_MONDAY', 'week1_monday', 'canonical first-week boundary'),
        record('CALENDAR_RACE_WEEK_MONDAY', 'race_week_monday', 'Monday containing target race'),
        record('CALENDAR_WEEKS', 'weeks',
               'calendar owner phase, recovery, race, travel, and day overlays'),
        record('CALENDAR_NAMING', 'workout_naming_convention',
               'stable calendar-derived workout naming contract', sensitivity='internal'),
        record('CALENDAR_EXAMPLE', 'workout_example',
               'display example projected from Week 1 Monday', sensitivity='internal'),
        record('CALENDAR_DAY_ABBREVIATIONS', 'day_abbreviations',
               'canonical weekday abbreviation table', {'source': 'constants.DAY_FULL_TO_ABBREV'},
               'internal'),
        record('CALENDAR_MONTH_ABBREVIATIONS', 'month_abbreviations',
               'canonical month abbreviation table', {'source': 'calendar month table'},
               'internal'),
    ]
    result['_derived'] = assert_registry_covers(
        result, records, artifact='calendar', revision=generation_revision)

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
        ("Plan weeks", plan_dates['plan_weeks'], plan_dates['plan_weeks'] >= PLAN_WEEKS_MIN),
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
    athletes_dir = Path(os.environ.get('GG_ATHLETES_BASE_DIR', Path(__file__).parent.parent))
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

    # Load meso_pattern from methodology.yaml if available
    meso_pattern = None
    methodology_path = athlete_dir / 'methodology.yaml'
    if methodology_path.exists():
        with open(methodology_path, 'r') as f:
            meth_data = yaml.safe_load(f) or {}
            meso_pattern = meth_data.get('configuration', {}).get('meso_pattern')
            if not meso_pattern:
                meso_pattern = meth_data.get('meso_pattern')

    # Get B-events and travel dates from profile
    b_events = profile.get('b_events', [])
    travel_dates = profile.get('travel_dates', [])

    # Calculate dates with constraints (including recovery week marking)
    fulfillment = profile.get('fulfillment') or {}
    generation_revision = int(fulfillment.get('generation_revision') or 1)
    derived_at = str(fulfillment.get('generation_at') or '') or None
    post_event_recovery_weeks = post_event_recovery_weeks_for_horizon(
        race_date, fulfillment.get('planning_horizon_end'))
    plan_dates = calculate_plan_dates(
        race_date, plan_weeks, preferred_start, heavy_training_end, b_events,
        meso_pattern, travel_dates, generation_revision, derived_at,
        post_event_recovery_weeks=post_event_recovery_weeks)

    # Print summary
    print("=" * 60)
    print(f"Plan Calendar: {args.athlete_id}")
    print("=" * 60)
    print(f"\nRace: {profile.get('target_race', {}).get('name', 'Unknown')}")
    print(f"Race Date: {plan_dates['race_date']} ({plan_dates['race_weekday']})")
    print(f"Plan Duration: {plan_dates['plan_weeks']} weeks")
    print(f"Plan Start: {plan_dates['plan_start']} (Week 1 Monday)")
    print(f"Plan End: {plan_dates['plan_end']} (Planning Horizon Sunday)")

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
        replaced = {'plan_start', 'plan_end', 'plan_weeks', 'race_weekday'}
        records = [record for record in (derived.get('_derived') or [])
                   if record.get('field') not in replaced]
        calendar_inputs = {
            'race_date': race_date,
            'preferred_start': preferred_start,
            'calendar_plan_weeks': plan_dates['plan_weeks'],
        }
        for identifier, field, basis in (
            ('CLASSIFICATION_PLAN_WEEKS', 'plan_weeks',
             'final calendar week count after start-date constraints'),
            ('CLASSIFICATION_PLAN_START', 'plan_start', 'final calendar start boundary'),
            ('CLASSIFICATION_PLAN_END', 'plan_end', 'final calendar end boundary'),
            ('CLASSIFICATION_RACE_WEEKDAY', 'race_weekday',
             'weekday derived from the target race date'),
        ):
            records.append(derived_entry(
                id=identifier, field=field, value_class='inferred', basis=basis,
                inputs=calendar_inputs, sensitivity='personal',
                at=str(derived_at or generation_now().isoformat().replace('+00:00', 'Z')),
                revision=generation_revision))
        derived['_derived'] = assert_registry_covers(
            derived, records, artifact='derived', revision=generation_revision)

        with open(derived_path, 'w') as f:
            yaml.dump(derived, f, default_flow_style=False, sort_keys=False)

        print(f"📝 Updated: {derived_path}")


if __name__ == '__main__':
    main()
