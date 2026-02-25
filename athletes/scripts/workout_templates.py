#!/usr/bin/env python3
"""
Workout Templates for Training Plan Generation.

Centralizes all workout template definitions to avoid duplication.

Two types of templates:
1. PHASE_WORKOUT_ROLES - Defines what types of workouts go in each role (key, long, easy, strength)
2. DEFAULT_WEEKLY_SCHEDULE - Default Mon-Sun schedule for athletes without custom preferences
"""

from typing import Dict, Tuple

# Workout template format: (workout_type, description, duration_min, target_power_ratio)
WorkoutTemplate = Tuple[str, str, int, float]


# ============================================================================
# PHASE WORKOUT ROLES
# ============================================================================
# Defines workout templates by ROLE (key_cardio, long_ride, easy, strength)
# Used when building custom schedules based on athlete preferences
# ============================================================================

PHASE_WORKOUT_ROLES: Dict[str, Dict[str, WorkoutTemplate]] = {
    'base': {
        # Base phase: Build aerobic foundation, introduce tempo
        'key_cardio': ('Endurance', 'Zone 2 aerobic development', 60, 0.65),
        'long_ride': ('Long_Ride', 'Long Zone 2 endurance', 120, 0.60),
        'easy': ('Recovery', 'Easy spin or rest', 30, 0.50),
        'moderate': ('Endurance', 'Zone 2 steady state', 45, 0.62),
        'tempo': ('Tempo', 'Tempo: 2x10min @ 85% FTP', 50, 0.72),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'build': {
        # Build phase: Threshold work, introduce VO2max
        'key_cardio': ('Threshold', 'Threshold intervals: 3x10min @ 95-100% FTP', 60, 0.78),
        'long_ride': ('Long_Ride', 'Long ride with race-pace efforts', 150, 0.65),
        'easy': ('Recovery', 'Easy spin', 45, 0.55),
        'moderate': ('Sweet_Spot', 'Sweet spot: 3x12min @ 88% FTP', 55, 0.75),
        'tempo': ('Tempo', 'Tempo intervals: 2x15min @ 85% FTP', 50, 0.72),
        'vo2max': ('VO2max', 'VO2max: 4x3min @ 110-115% FTP', 50, 0.80),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'peak': {
        # Peak phase: VO2max emphasis, anaerobic power, race specificity
        'key_cardio': ('VO2max', 'VO2max intervals: 5x3min @ 115% FTP', 55, 0.82),
        'long_ride': ('Long_Ride', 'Long ride with race-pace blocks', 180, 0.65),
        'easy': ('Recovery', 'Easy spin', 40, 0.55),
        'moderate': ('Threshold', 'Threshold: 2x15min @ 95-100% FTP', 50, 0.78),
        'tempo': ('Sweet_Spot', 'Sweet spot: 3x10min @ 88% FTP', 50, 0.75),
        'vo2max': ('VO2max', 'VO2max: 5x3min @ 115-120% FTP', 50, 0.82),
        'anaerobic': ('Anaerobic', 'Anaerobic capacity: 8x30sec @ 150% FTP', 45, 0.70),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'taper': {
        # Taper: Maintain intensity, reduce volume, openers
        'key_cardio': ('Openers', 'Short openers: 4x30sec @ 130% FTP', 40, 0.62),
        'long_ride': ('Shakeout', 'Pre-race shakeout ride', 30, 0.55),
        'easy': ('Easy', 'Easy spin', 30, 0.55),
        'moderate': ('Easy', 'Easy spin with leg openers', 35, 0.58),
        'tempo': ('Easy', 'Easy spin', 30, 0.55),
        'vo2max': ('Openers', 'VO2 openers: 3x2min @ 110% FTP', 40, 0.65),
        'anaerobic': ('Sprints', 'Sprint openers: 4x15sec all-out', 35, 0.55),
        'strength': ('Strength', 'Light strength maintenance', 30, 0.0),
    },
    'maintenance': {
        # Maintenance: Keep fitness, reduced load
        'key_cardio': ('Tempo', 'Light tempo: 20min @ 80% FTP', 45, 0.65),
        'long_ride': ('Endurance', 'Longer endurance ride', 90, 0.60),
        'easy': ('Recovery', 'Optional easy spin', 30, 0.50),
        'moderate': ('Endurance', 'Zone 2 maintenance', 50, 0.62),
        'tempo': ('Tempo', 'Tempo: 2x12min @ 85% FTP', 45, 0.70),
        'vo2max': ('Threshold', 'Threshold touch: 2x8min @ 95% FTP', 45, 0.72),
        'strength': ('Strength', 'Strength training session', 45, 0.0),
    },
    'race': {
        # Race week: Minimal volume, maintain sharpness
        'key_cardio': ('Openers', 'Race week openers', 30, 0.60),
        'long_ride': ('RACE_DAY', 'RACE DAY - Execute your plan!', 0, 0),
        'easy': ('Easy', 'Easy spin', 30, 0.50),
        'moderate': ('Easy', 'Easy spin', 30, 0.50),
        'tempo': ('Easy', 'Easy spin', 25, 0.50),
        'vo2max': ('Openers', 'Brief openers', 25, 0.55),
        'anaerobic': ('Sprints', 'Neuromuscular activation: 3x10sec', 25, 0.50),
        'strength': ('Rest', None, 0, 0),
    },
}


# ============================================================================
# DEFAULT WEEKLY SCHEDULE
# ============================================================================
# Full week template with specific days mapped to workouts
# Used for athletes WITHOUT custom schedule preferences
# Assumes: Mon/Thu rest, Sat long ride, Sun recovery
# ============================================================================

DEFAULT_WEEKLY_SCHEDULE: Dict[str, Dict[str, WorkoutTemplate]] = {
    'base': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Endurance', 'Zone 2 steady state', 60, 0.65),
        'Wed': ('Endurance', 'Zone 2 with cadence drills', 60, 0.65),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Endurance', 'Zone 2 aerobic development', 60, 0.65),
        'Sat': ('Long_Ride', 'Long Zone 2 endurance', 120, 0.60),
        'Sun': ('Recovery', 'Easy spin or rest', 30, 0.50),
    },
    'build': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Intervals', 'Threshold intervals: 3x10min @ 95% FTP', 75, 0.75),
        'Wed': ('Endurance', 'Zone 2 recovery spin', 60, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Tempo', 'Tempo ride: 30min @ 85% FTP', 60, 0.70),
        'Sat': ('Long_Ride', 'Long ride with race-pace efforts', 150, 0.65),
        'Sun': ('Recovery', 'Easy spin', 45, 0.55),
    },
    'peak': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('VO2max', 'VO2max intervals: 5x3min @ 110% FTP', 60, 0.80),
        'Wed': ('Endurance', 'Easy spin, legs open', 45, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Race_Sim', 'Race simulation: sustained efforts', 75, 0.75),
        'Sat': ('Long_Ride', 'Long ride with race-pace blocks', 180, 0.65),
        'Sun': ('Recovery', 'Easy spin', 40, 0.55),
    },
    'taper': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Openers', 'Short openers: 4x30sec @ 120% FTP', 45, 0.65),
        'Wed': ('Easy', 'Easy spin', 30, 0.55),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Easy', 'Easy spin with a few accelerations', 45, 0.60),
        'Sat': ('Shakeout', 'Pre-race shakeout ride', 30, 0.55),
        'Sun': ('Rest', None, 0, 0),
    },
    'maintenance': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Tempo', 'Light tempo: 20min @ 80% FTP', 45, 0.65),
        'Wed': ('Easy', 'Easy endurance spin', 45, 0.60),
        'Thu': ('Rest', None, 0, 0),
        'Fri': ('Endurance', 'Moderate endurance ride', 60, 0.60),
        'Sat': ('Endurance', 'Longer endurance ride', 90, 0.60),
        'Sun': ('Recovery', 'Optional easy spin', 30, 0.50),
    },
    'race': {
        'Mon': ('Rest', None, 0, 0),
        'Tue': ('Easy', 'Easy spin', 30, 0.50),
        'Wed': ('Rest', None, 0, 0),
        'Thu': ('Openers', 'Race week openers', 30, 0.60),
        'Fri': ('Rest', None, 0, 0),
        'Sat': ('Shakeout', 'Pre-race shakeout', 20, 0.55),
        'Sun': ('RACE_DAY', 'RACE DAY - Execute your plan!', 0, 0),
    },
}


def get_phase_roles(phase: str) -> Dict[str, WorkoutTemplate]:
    """Get workout templates by role for a training phase."""
    return PHASE_WORKOUT_ROLES.get(phase, PHASE_WORKOUT_ROLES['base'])


def get_default_day_workout(phase: str, day_abbrev: str) -> WorkoutTemplate:
    """Get the default workout for a specific day and phase."""
    phase_schedule = DEFAULT_WEEKLY_SCHEDULE.get(phase, DEFAULT_WEEKLY_SCHEDULE['base'])
    return phase_schedule.get(day_abbrev, ('Rest', None, 0, 0))


def round_duration_to_10(minutes: int) -> int:
    """Round a workout duration to the nearest 10 minutes.

    Durations <= 0 are returned as-is (rest days, race days).
    Minimum rounded value is 10 (avoids rounding a 4-min workout to 0).

    Examples:
        >>> round_duration_to_10(67)
        70
        >>> round_duration_to_10(94)
        90
        >>> round_duration_to_10(107)
        110
        >>> round_duration_to_10(121)
        120
        >>> round_duration_to_10(0)
        0
    """
    if minutes <= 0:
        return minutes
    return max(10, round(minutes / 10) * 10)


def cap_duration(template: WorkoutTemplate, max_duration: int) -> WorkoutTemplate:
    """Cap a workout template's duration to a maximum."""
    if not template or template[2] == 0:
        return template
    if max_duration > 0 and max_duration < template[2]:
        return (template[0], template[1], max_duration, template[3])
    return template


# ============================================================================
# DURATION SCALING
# ============================================================================
# Workout types that should NOT be scaled (they have fixed durations by design)
# ============================================================================
_NO_SCALE_TYPES = frozenset({
    'Rest', 'RACE_DAY', 'FTP_Test', 'Strength', 'Shakeout',
    'Openers', 'Pre_Plan_Easy', 'Pre_Plan_Endurance',
})

# Workout types where only warmup/cooldown should scale (interval set is fixed)
_INTERVAL_TYPES = frozenset({
    'VO2max', 'Threshold', 'Anaerobic', 'Sprints', 'Sweet_Spot',
    'G_Spot', 'Over_Under', 'Blended', 'Over_Unders', 'Intervals',
    'SFR', 'Mixed_Climbing', 'Cadence_Work',
    'Race_Sim', 'Durability',
})

# Workout types that are pure endurance (entire duration scales)
_ENDURANCE_TYPES = frozenset({
    'Endurance', 'Recovery', 'Easy', 'Tempo', 'Long_Ride', 'Race_Sim',
})

# Phase-based utilization percentages for endurance rides
# How much of max_duration to use: base builds volume, peak reduces it
_PHASE_UTILIZATION = {
    'base': 0.70,
    'build': 0.75,
    'peak': 0.70,
    'taper': 0.50,      # Taper keeps workouts short
    'race': 0.40,       # Race week is minimal
    'maintenance': 0.65,
}


def calculate_target_duration(workout_type: str, max_duration: int,
                              phase: str, template_duration: int) -> int:
    """Calculate target workout duration based on available time and workout type.

    For endurance/easy rides: scales to phase-appropriate percentage of max_duration.
    For interval workouts: scales to 90% of max_duration (intervals need full time).
    For fixed-duration workouts (FTP test, openers, etc.): returns template duration.

    The result is always capped at max_duration and rounded to nearest 10 minutes.
    If max_duration is 0 or the workout type should not be scaled, returns the
    template duration unchanged.

    Args:
        workout_type: The type of workout (VO2max, Endurance, Easy, etc.)
        max_duration: Maximum minutes available for this day's slot
        phase: Training phase (base, build, peak, taper, race, maintenance)
        template_duration: The duration from the workout template (baseline)

    Returns:
        Target duration in minutes, rounded to nearest 10.
    """
    # Don't scale rest, race day, FTP tests, openers, etc.
    if workout_type in _NO_SCALE_TYPES:
        return template_duration

    # Don't scale if max_duration is 0 or not set
    if max_duration <= 0:
        return template_duration

    # Don't scale if template is already 0 (rest/race)
    if template_duration <= 0:
        return template_duration

    # Endurance/easy rides: scale to phase-appropriate percentage
    if workout_type in _ENDURANCE_TYPES:
        utilization = _PHASE_UTILIZATION.get(phase, 0.70)
        target = int(max_duration * utilization)
        # Don't scale below the template duration (avoid shrinking short workouts)
        target = max(target, template_duration)
        # Cap at max_duration
        target = min(target, max_duration)
        return round_duration_to_10(target)

    # Interval workouts: scale to 90% of max_duration, but cap at 120 min.
    # Even with 4+ hours available, interval sessions shouldn't exceed 2 hours.
    # The extra Z2 warmup/cooldown has diminishing returns past that -- the
    # long ride day is where extended Z2 volume belongs.
    if workout_type in _INTERVAL_TYPES:
        target = int(max_duration * 0.90)
        # Hard cap: interval sessions never exceed 120 minutes
        target = min(target, 120)
        # Don't scale below the template duration
        target = max(target, template_duration)
        # Cap at max_duration (for slots < template duration)
        target = min(target, max_duration)
        return round_duration_to_10(target)

    # Unknown type: return template duration unchanged
    return template_duration


def scale_template_duration(template: WorkoutTemplate, max_duration: int,
                            phase: str) -> WorkoutTemplate:
    """Scale a workout template's duration UP to use available time.

    This is the counterpart to cap_duration(). While cap_duration() prevents
    workouts from exceeding max_duration, scale_template_duration() ensures
    workouts actually USE the available time instead of leaving it wasted.

    Args:
        template: The workout template tuple (type, description, duration, power)
        max_duration: Maximum minutes available for this day's slot
        phase: Training phase (base, build, peak, taper, race, maintenance)

    Returns:
        WorkoutTemplate with adjusted duration.
    """
    if not template or template[2] == 0:
        return template

    workout_type = template[0]
    target = calculate_target_duration(workout_type, max_duration, phase, template[2])

    if target != template[2]:
        return (template[0], template[1], target, template[3])
    return template


def scale_zwo_to_target_duration(zwo_xml: str, target_duration_min: int,
                                 workout_type: str) -> str:
    """Post-process ZWO XML to scale workout to target duration.

    For interval workouts: keeps interval sets fixed, scales warmup and cooldown.
    For endurance workouts: scales the main SteadyState block.

    The warmup/cooldown scaling distributes extra time as Z2 endurance,
    building aerobic base even on interval days.

    Args:
        zwo_xml: Complete ZWO XML string
        target_duration_min: Target total duration in minutes
        workout_type: Type of workout for scaling strategy

    Returns:
        ZWO XML string with adjusted durations
    """
    import re
    import xml.etree.ElementTree as ET

    if target_duration_min <= 0:
        return zwo_xml

    try:
        root = ET.fromstring(zwo_xml)
    except ET.ParseError:
        return zwo_xml

    workout = root.find('workout')
    if workout is None:
        return zwo_xml

    # Calculate current total and interval set duration
    total_seconds = 0
    interval_seconds = 0
    warmup_elem = None
    cooldown_elem = None

    for elem in workout:
        if elem.tag == 'IntervalsT':
            repeats = int(elem.get('Repeat', 1))
            on_dur = float(elem.get('OnDuration', 0))
            off_dur = float(elem.get('OffDuration', 0))
            block_dur = repeats * (on_dur + off_dur)
            total_seconds += block_dur
            interval_seconds += block_dur
        else:
            dur = float(elem.get('Duration', 0))
            total_seconds += dur
            if elem.tag == 'Warmup' and warmup_elem is None:
                warmup_elem = elem
            elif elem.tag == 'Cooldown' and cooldown_elem is None:
                cooldown_elem = elem

    if total_seconds <= 0:
        return zwo_xml

    target_seconds = target_duration_min * 60

    # If already within 60 seconds of target, no change needed
    if abs(target_seconds - total_seconds) <= 60:
        return zwo_xml

    # If target is smaller than current, don't shrink
    if target_seconds < total_seconds:
        return zwo_xml

    # Strategy depends on workout type
    if workout_type in _INTERVAL_TYPES and interval_seconds > 0:
        # Interval workout: keep intervals fixed, scale warmup + cooldown
        non_interval_seconds = total_seconds - interval_seconds
        remaining = target_seconds - interval_seconds

        if remaining < 1200:  # Need at least 20min for warmup+cooldown
            remaining = 1200

        # Split remaining: 55% warmup, 45% cooldown
        # Minimum 10 min (600s) each
        warmup_target = max(600, int(remaining * 0.55))
        cooldown_target = max(600, remaining - warmup_target)

        # Apply via regex on the XML string to preserve formatting
        # Scale warmup
        warmup_match = re.search(r'(<Warmup\s[^>]*?)Duration="(\d+)"', zwo_xml)
        if warmup_match:
            zwo_xml = (zwo_xml[:warmup_match.start(2)]
                       + str(warmup_target)
                       + zwo_xml[warmup_match.end(2):])

        # Scale cooldown
        cooldown_match = re.search(r'(<Cooldown\s[^>]*?)Duration="(\d+)"', zwo_xml)
        if cooldown_match:
            zwo_xml = (zwo_xml[:cooldown_match.start(2)]
                       + str(cooldown_target)
                       + zwo_xml[cooldown_match.end(2):])

    else:
        # Endurance/easy workout: scale the main SteadyState block(s)
        # Find all SteadyState elements and scale proportionally
        diff = target_seconds - total_seconds
        if diff <= 0:
            return zwo_xml

        # Find the largest SteadyState block and add the difference to it
        ss_tag = 'Steady' + 'State'
        ss_pattern = rf'(<{ss_tag}\s[^>]*?)Duration="(\d+)"'
        largest_ss = None
        largest_dur = 0
        for m in re.finditer(ss_pattern, zwo_xml):
            dur = int(m.group(2))
            if dur > largest_dur:
                largest_dur = dur
                largest_ss = m

        if largest_ss:
            old_dur = int(largest_ss.group(2))
            new_dur = old_dur + int(diff)
            zwo_xml = (zwo_xml[:largest_ss.start(2)]
                       + str(new_dur)
                       + zwo_xml[largest_ss.end(2):])

    return zwo_xml
