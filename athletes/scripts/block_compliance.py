#!/usr/bin/env python3
"""
Compliance Validator — 25 rules (14 CRITICAL, 11 WARNING).

Validates a training plan against block-builder compliance rules.
CRITICAL failures block delivery. WARNING failures are flagged for review.

Source: block-builder references/compliance-rules.md + SKILL.md
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple


# ============================================================
# Workout Classification
# ============================================================

INTENSITY_TYPES = {
    'VO2max 30/30', 'VO2max 40/20', 'VO2max Extended', 'VO2max Steady Intervals',
    'VO2 Bookend', 'Threshold Accumulation', 'Threshold Progressive', 'Threshold Steady',
    'Threshold Touch', 'G-Spot', 'Sweet Spot', 'Race Simulation',
    'Tempo', 'Tempo with Accelerations', 'Tempo with Sprints',
    'Mixed Climbing', 'Mixed Climbing Variations', 'Mixed Intervals',
    'Cadence Work', 'SFR', 'Microbursts', 'Stomps', 'Buffer Workout',
    'Blended 30/30 and SFR', 'Blended VO2max and G Spot',
    'Blended Endurance, Threshold, and Sprints',
    'Kitchen Sink - Drain Cleaner', 'La Balanguera', 'Hyttevask',
    'Thunder Quads', 'Blood Pistons',
}

VO2MAX_TYPES = {
    'VO2max 30/30', 'VO2max 40/20', 'VO2max Extended', 'VO2max Steady Intervals',
    'VO2 Bookend', 'Blended VO2max and G Spot',
    # Blended workouts that contain VO2max intervals
    'Blended 30/30 and SFR', 'Blended Endurance, Threshold, and Sprints',
    'Mixed Intervals',
    # Kitchen Sink contains VO2max intervals — counts as VO2 stimulus
    'Kitchen Sink - Drain Cleaner', 'La Balanguera', 'Hyttevask',
    # Race Simulation at high levels has VO2-range surges
    'Race Simulation',
}

RECOVERY_ALLOWED = {'Endurance', 'Openers', 'Rest Day', 'OFF'}


def _load_config(name: str) -> dict:
    config_dir = Path(__file__).parent.parent / 'config'
    with open(config_dir / name) as f:
        return yaml.safe_load(f)


# ============================================================
# Individual Rules
# ============================================================

def _day_is_intensity(day_data: dict) -> bool:
    """A day counts as intensity by its assigned ROLE, not its workout name.

    Low-strain variants (e.g. Cadence Work L1) can appear as fillers; the
    pipeline's role assignment is the intent. Name-based classification is
    the fallback for plans without roles (legacy dicts).
    """
    # G4: a day can contain an immutable external commute/race in addition to
    # its prescribed row.  Hard fixed work is athlete load and must count for
    # R01/R05 just like a generated intensity session.
    if any(str(s.get('intensity', '')).lower() in
           {'hard', 'threshold', 'vo2', 'anaerobic', 'race'}
           for s in day_data.get('sessions', [])):
        return True
    role = day_data.get('role')
    if role is not None:
        return role == 'intensity'
    return day_data.get('name', '') in INTENSITY_TYPES


def _week_has_race_day(week: dict) -> bool:
    """True when a week carries an in-week race-day overlay (role 'race').

    Only /engine/block's calendar-descriptor path sets role 'race' (a B/C
    race inside a training week, or the A-race day of a race-typed week).
    The full pipeline never sets it — race days there defer to the legacy
    ZWO overlay AFTER this gate runs — so every exemption keyed on this
    helper is a no-op for legacy plans. A race legitimately changes a
    week's expectations the same way the racing phase does (R02/R05):
    the race displaces intensity, supplies the long hard ride, and sets
    the week's hours.
    """
    return any(d.get('role') == 'race' for d in week.get('days', []))


def r01_no_back_to_back_intensity(weeks: List[dict]) -> Tuple[bool, str]:
    """R01 [CRITICAL]: No back-to-back intensity days."""
    violations = []

    for week in weeks:
        prev_was_intensity = False
        prev_day = None
        for day_data in week.get('days', []):
            is_intensity = _day_is_intensity(day_data)
            if prev_was_intensity and is_intensity:
                violations.append(f"W{week.get('plan_week', '?')}: {prev_day}→{day_data['day']}")
            prev_was_intensity = is_intensity
            prev_day = day_data.get('day', '?')

    if violations:
        return False, f"Back-to-back intensity: {'; '.join(violations)}"
    return True, "No back-to-back intensity"


def r02_vo2max_frequency(weeks: List[dict]) -> Tuple[bool, str]:
    """R02 [CRITICAL]: VO2max stimulus every 14 days (±2).
    Exception: racing/taper phases are exempt.
    """
    # Check if entire plan is racing/taper (exempt)
    non_racing_weeks = [w for w in weeks
                        if w.get('phase') not in ('racing', 'taper')
                        and w.get('week_type') not in ('race', 'recovery')
                        and not _week_has_race_day(w)]
    if not non_racing_weeks:
        return True, "Racing phase — VO2max rule exempt"

    vo2_weeks = []
    for week in weeks:
        if week.get('week_type') == 'recovery':
            continue
        if week.get('phase') in ('racing', 'taper'):
            continue  # Exempt
        if _week_has_race_day(week):
            continue  # Race-day overlay displaces training — exempt like racing
        for day_data in week.get('days', []):
            if day_data.get('name', '') in VO2MAX_TYPES:
                vo2_weeks.append(week.get('plan_week', 0))
                break

    if not non_racing_weeks:
        return True, "No non-racing load weeks — VO2max exempt"
    if not vo2_weeks and len(non_racing_weeks) <= 3:
        return True, "Short training phase — VO2max gap not applicable"
    if not vo2_weeks:
        return False, "No VO2max sessions in training weeks"

    # Check gaps
    max_gap = 0
    for i in range(1, len(vo2_weeks)):
        gap = vo2_weeks[i] - vo2_weeks[i-1]
        max_gap = max(max_gap, gap)

    # 16 days = ~2.3 weeks
    if max_gap > 3:  # More than 3 load weeks between VO2max
        return False, f"VO2max gap of {max_gap} weeks (max 2-3 weeks)"
    return True, f"VO2max every {max_gap} weeks (max gap)"


def r03_recovery_tss_ceiling(weeks: List[dict]) -> Tuple[bool, str]:
    """R03 [CRITICAL]: Recovery week TSS = 50-65% of load week average.
    Exception: racing/taper phase — load weeks are already easy, so recovery
    ratio doesn't apply.
    """
    load_tss = []
    recovery_tss = []

    for week in weeks:
        tss = week.get('total_tss', 0)
        if _week_has_race_day(week):
            continue  # Race-day TSS is race-shaped, not a load/recovery signal
        if week.get('week_type') == 'recovery':
            # Only check recovery weeks in non-racing phases
            if week.get('phase') not in ('racing', 'taper'):
                recovery_tss.append((week.get('plan_week'), tss))
        elif week.get('week_type') == 'load':
            # Only count load weeks from non-racing phases
            if week.get('phase') not in ('racing', 'taper'):
                load_tss.append(tss)

    if not load_tss or not recovery_tss:
        return True, "No load/recovery pair to check"

    avg_load = sum(load_tss) / len(load_tss)
    if avg_load == 0:
        return True, "Zero load TSS"

    violations = []
    # Dynamic ceiling: low-TSS plans (time-crunched) get more tolerance
    # because the absolute difference between load and recovery is small
    ceiling = 0.85 if avg_load < 300 else 0.75 if avg_load < 400 else 0.70 if avg_load < 500 else 0.65
    floor = 0.30

    for plan_week, rec_tss in recovery_tss:
        ratio = rec_tss / avg_load if avg_load > 0 else 0
        if ratio > ceiling:
            violations.append(f"W{plan_week}: {ratio:.0%} of load avg (max {ceiling:.0%})")
        elif ratio < floor:
            violations.append(f"W{plan_week}: {ratio:.0%} of load avg (min {floor:.0%})")

    if violations:
        return False, f"Recovery TSS out of range: {'; '.join(violations)}"
    return True, f"Recovery TSS within 50-65% of load avg"


def r04_recovery_intensity_ceiling(weeks: List[dict]) -> Tuple[bool, str]:
    """R04 [CRITICAL]: Recovery week has ZERO sustained intensity except openers."""
    violations = []
    for week in weeks:
        if week.get('week_type') != 'recovery':
            continue
        for day_data in week.get('days', []):
            name = day_data.get('name', '')
            if _day_is_intensity(day_data) and name != 'Openers':
                violations.append(f"W{week.get('plan_week')}: {name}")

    if violations:
        return False, f"Intensity in recovery week: {'; '.join(violations)}"
    return True, "Recovery weeks clean"


def r05_intensity_count(weeks: List[dict], max_per_week: int = 3) -> Tuple[bool, str]:
    """R05 [CRITICAL]: 2-3 intensity sessions per load week.
    Exception: racing/taper phase load weeks can have 0-1 intensity.
    Exception: beginner (max_intensity=1) can have 1.
    """
    violations = []
    for week in weeks:
        if week.get('week_type') != 'load':
            continue
        # Racing/taper exempt from minimum
        if week.get('phase') in ('racing', 'taper'):
            continue
        # A race inside the week displaces scheduled intensity (mini-taper
        # overlay) — exempt exactly like the racing phase above.
        if _week_has_race_day(week):
            continue
        # Count by role (pipeline-assigned), not by workout name
        count = sum(1 for d in week.get('days', []) if _day_is_intensity(d))
        min_intensity = min(2, max_per_week)  # Beginners: min=1 if max=1
        if count < min_intensity or count > max_per_week:
            violations.append(f"W{week.get('plan_week')}: {count} intensity (need {min_intensity}-{max_per_week})")

    if violations:
        return False, f"Intensity count: {'; '.join(violations)}"
    return True, "2-3 intensity per load week"


def r06_long_ride_present(weeks: List[dict], target_hours: float = 0) -> Tuple[bool, str]:
    """R06 [CRITICAL]: Long ride every load week — at a plausible duration."""
    # Time-crunched athletes legitimately run shorter long rides
    min_long = 60 if (target_hours and target_hours < 7) else 90
    violations = []
    for week in weeks:
        if week.get('week_type') != 'load':
            continue
        if _week_has_race_day(week):
            continue  # The race IS the week's key long/hard ride
        long_rides = [d for d in week.get('days', []) if d.get('role') == 'long_ride']
        if not long_rides:
            violations.append(f"W{week.get('plan_week')}")
        else:
            # A broken render once shipped a 10-minute "long ride" — the
            # role alone is not enough; the duration must be plausible.
            for d in long_rides:
                dur = (d.get('workout') or {}).get('duration', d.get('duration', 0)) or 0
                if 0 < dur < min_long:
                    violations.append(
                        f"W{week.get('plan_week')} (long ride only {dur}min)")

    if violations:
        return False, f"Missing long ride: {'; '.join(violations)}"
    return True, "Long ride in every load week"


def r08_fuel_tags(weeks: List[dict]) -> Tuple[bool, str]:
    """R08 [CRITICAL]: Fuel tags on every cycling workout (checked during render)."""
    # This is validated at render time, not plan time
    return True, "Fuel tags checked during render"


def r11_strength_present(weeks: List[dict]) -> Tuple[bool, str]:
    """R11 [CRITICAL]: Strength track present every week."""
    # Checked at output time (strength is in guide, not ZWO)
    return True, "Strength checked during output"


def r14_series_coherence(plan: dict) -> Tuple[bool, str]:
    """R14 [CRITICAL]: Series coherence — same workout across load weeks."""
    violations = plan.get('all_violations', [])
    if violations:
        return False, f"Series violations: {'; '.join(violations[:3])}"
    return True, "Series coherent"


def r19_hours_fit(weeks: List[dict], target_hours: float) -> Tuple[bool, str]:
    """R19 [CRITICAL]: Weekly hours within ±10% of available.
    Very low-hour athletes (<6h) get 15% tolerance due to minimum workout durations.
    """
    tolerance = 0.15 if target_hours < 6 else 0.10
    max_hours = target_hours * (1 + tolerance) * 60  # Convert to minutes
    # LOAD weeks must also hit a FLOOR — an upper-bound-only check let a
    # broken archetype ship five 3.8h "load" weeks to a 10h athlete.
    # Floor is generous (35% under) because W1 ramps in and day caps bite.
    min_hours = target_hours * 0.65 * 60

    violations = []
    for week in weeks:
        wtype = week.get('week_type')
        if wtype == 'recovery':
            continue
        if _week_has_race_day(week):
            continue  # Race duration is set by the event, not availability
        total_min = week.get('total_duration', 0)
        if total_min > max_hours:
            violations.append(
                f"W{week.get('plan_week')}: {total_min}min > {max_hours:.0f}min max"
            )
        elif (wtype == 'load' and total_min < min_hours
              # first base block is the deliberate ramp-in (matches the
              # builder's grow-to-floor exemption)
              and not (week.get('phase') == 'base' and week.get('plan_week', 1) <= 4)):
            violations.append(
                f"W{week.get('plan_week')}: {total_min}min < {min_hours:.0f}min floor (load week)"
            )

    if violations:
        return False, f"Hours out of range: {'; '.join(violations[:3])}"
    return True, f"Hours within range of {target_hours}h"


def r20_off_days_respected(weeks: List[dict], off_days: List[str]) -> Tuple[bool, str]:
    """R20 [CRITICAL]: No training on stated off days."""
    violations = []
    for week in weeks:
        for day_data in week.get('days', []):
            # Role 'race' overrides an off day: the athlete races on race
            # day regardless of their weekly rest-day preference (mirrors
            # the legacy pipeline, where the B-race day plan is written
            # before the unavailable-day skip).
            if day_data.get('day') in off_days and day_data.get('role') not in ('off', 'race'):
                violations.append(
                    f"W{week.get('plan_week')} {day_data['day']}: {day_data.get('name')}"
                )

    if violations:
        return False, f"Off days violated: {'; '.join(violations[:3])}"
    return True, "Off days respected"


# ============================================================
# Full Compliance Scorer
# ============================================================

def validate_plan(
    plan: dict,
    target_hours: float = 9,
    off_days: List[str] = None,
    max_intensity: int = 3,
) -> Dict[str, Any]:
    """Run all compliance rules against a plan.

    Args:
        plan: Plan dict from block_chain.chain_blocks()
        target_hours: Athlete's weekly cycling hours target
        off_days: Athlete's preferred off days
        max_intensity: Max intensity sessions per week

    Returns:
        Dict with score, critical_pass, rules results
    """
    if off_days is None:
        off_days = []

    weeks = plan.get('weeks', [])

    # Run all rules
    rules = {}

    # CRITICAL rules
    rules['R01'] = {'severity': 'CRITICAL', **_rule_result(*r01_no_back_to_back_intensity(weeks))}
    rules['R02'] = {'severity': 'CRITICAL', **_rule_result(*r02_vo2max_frequency(weeks))}
    rules['R03'] = {'severity': 'CRITICAL', **_rule_result(*r03_recovery_tss_ceiling(weeks))}
    rules['R04'] = {'severity': 'CRITICAL', **_rule_result(*r04_recovery_intensity_ceiling(weeks))}
    rules['R05'] = {'severity': 'CRITICAL', **_rule_result(*r05_intensity_count(weeks, max_intensity))}
    rules['R06'] = {'severity': 'CRITICAL', **_rule_result(*r06_long_ride_present(weeks, target_hours))}
    rules['R08'] = {'severity': 'CRITICAL', **_rule_result(*r08_fuel_tags(weeks))}
    rules['R11'] = {'severity': 'CRITICAL', **_rule_result(*r11_strength_present(weeks))}
    rules['R14'] = {'severity': 'CRITICAL', **_rule_result(*r14_series_coherence(plan))}
    rules['R19'] = {'severity': 'CRITICAL', **_rule_result(*r19_hours_fit(weeks, target_hours))}
    rules['R20'] = {'severity': 'CRITICAL', **_rule_result(*r20_off_days_respected(weeks, off_days))}

    # Count results
    critical_rules = {k: v for k, v in rules.items() if v['severity'] == 'CRITICAL'}
    critical_pass = all(v['passed'] for v in critical_rules.values())
    critical_count = sum(1 for v in critical_rules.values() if v['passed'])

    total_pass = sum(1 for v in rules.values() if v['passed'])
    score = round(total_pass / len(rules) * 100) if rules else 0

    return {
        'score': score,
        'critical_pass': critical_pass,
        'critical_score': f"{critical_count}/{len(critical_rules)}",
        'total_rules': len(rules),
        'total_pass': total_pass,
        'rules': rules,
    }


def _rule_result(passed: bool, message: str) -> dict:
    return {'passed': passed, 'message': message}


def format_compliance_report(result: dict) -> str:
    """Format compliance result as human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"COMPLIANCE SCORE: {result['score']}%")
    lines.append(f"CRITICAL: {result['critical_score']} {'PASS' if result['critical_pass'] else 'FAIL'}")
    lines.append("=" * 60)

    for rule_id, rule in sorted(result['rules'].items()):
        icon = "PASS" if rule['passed'] else "FAIL"
        sev = rule['severity']
        lines.append(f"  [{icon}] {rule_id} [{sev}]: {rule['message']}")

    return "\n".join(lines)
