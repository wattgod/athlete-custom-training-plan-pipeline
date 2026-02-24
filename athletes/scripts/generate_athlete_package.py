#!/usr/bin/env python3
"""
Generate complete athlete training package:
- Training guide (HTML)
- ZWO workout files (with progression)
- Strength workout files
- Plan summary

Usage: python3 generate_athlete_package.py <athlete_id>
"""

import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

# Add script path for local imports
sys.path.insert(0, str(Path(__file__).parent))

# Local imports - use centralized modules
from config_loader import get_config
from constants import (
    DAY_FULL_TO_ABBREV,
    DAY_ABBREV_TO_FULL,
    DAY_ORDER,
    FTP_TEST_DURATION_MIN,
    STRENGTH_PHASES,
)
from logger import get_logger, header, step, detail, success, error, warning
from pre_generation_validator import validate_athlete_data
from workout_templates import (
    PHASE_WORKOUT_ROLES,
    DEFAULT_WEEKLY_SCHEDULE,
    get_phase_roles,
    cap_duration,
)

# Get config and set up paths
config = get_config()
GUIDES_DIR = config.get_guides_dir()

# Add guides generator path if it exists
if GUIDES_DIR and (GUIDES_DIR / 'generators').exists():
    sys.path.insert(0, str(GUIDES_DIR / 'generators'))

# Use local generate_html_guide instead of external guide_generator
from generate_html_guide import generate_html_guide
from workout_library import (
    WorkoutLibrary,
    generate_progressive_interval_blocks,
    generate_progressive_endurance_blocks,
    generate_strength_zwo,
)
from exercise_lookup import get_video_url
from nate_workout_generator import (
    generate_nate_zwo,
    calculate_level_from_week,
    TRAINING_METHODOLOGIES,
)

# Get logger
log = get_logger()


# Map athlete methodology IDs to Nate generator methodology names
METHODOLOGY_MAP = {
    # Keys match config/methodologies.yaml IDs (returned by select_methodology.py)
    'traditional_pyramidal': 'PYRAMIDAL',
    'polarized_80_20': 'POLARIZED',
    'sweet_spot_threshold': 'G_SPOT',
    'hiit_focused': 'HIT',
    'block_periodization': 'BLOCK',
    'reverse_periodization': 'REVERSE',
    'autoregulated_hrv': 'HRV_AUTO',
    'maf_low_hr': 'MAF_LT1',
    'critical_power': 'CRITICAL_POWER',
    'inscyd': 'INSCYD',
    'norwegian_double_threshold': 'NORWEGIAN',
    'hvli_lsd': 'HVLI',
    'goat_composite': 'GOAT',
}


# Workout description templates per type (following v6.0 spec format)
WORKOUT_DESCRIPTIONS = {
    'Recovery': {
        'structure': '{duration} min easy spin @ Z1 (50-55% FTP)',
        'purpose': 'Active recovery. Blood flow without stress. Let your body adapt to previous training.',
        'execution': 'Keep it easy. If in doubt, go easier. No heroics.',
        'rpe': 'RPE 2-3 (very easy, conversational)',
    },
    'Easy': {
        'structure': '{duration} min easy spin @ Z1-Z2 (55-65% FTP)',
        'purpose': 'Recovery and aerobic maintenance. Easy means easy.',
        'execution': 'Smooth pedaling, relaxed. Could hold a conversation easily.',
        'rpe': 'RPE 2-3 (easy)',
    },
    'Endurance': {
        'structure': '{duration} min @ Z2 (65-75% FTP)',
        'purpose': 'Aerobic base building. This is where 80% of your training volume lives.',
        'execution': 'Steady effort, smooth cadence 85-95 rpm. Nose-breathe if possible.',
        'rpe': 'RPE 3-4 (moderate, sustainable for hours)',
    },
    'Tempo': {
        'structure': '{duration} min with tempo blocks @ Z3 (76-87% FTP)',
        'purpose': 'Muscular endurance. Building your ability to sustain moderate-hard efforts.',
        'execution': 'Controlled effort. Breathing harder but rhythmic. Stay seated.',
        'rpe': 'RPE 5-6 (comfortably hard)',
    },
    'Sweet_Spot': {
        'structure': '{duration} min with sweet spot intervals @ 88-94% FTP',
        'purpose': 'Maximum training stress with manageable recovery. The efficiency zone.',
        'execution': 'Hard enough to create adaptation, easy enough to repeat. Cadence 85-95 rpm.',
        'rpe': 'RPE 6-7 (hard but sustainable)',
    },
    'G_Spot': {
        'structure': '{duration} min with G SPOT intervals @ 88-94% FTP',
        'purpose': 'The Gravel God efficiency zone. Maximum training stress with manageable recovery. Builds FTP and muscular endurance simultaneously.',
        'execution': 'Hard enough to create adaptation, easy enough to repeat. Cadence 85-95 rpm. Stay focused on form.',
        'rpe': 'RPE 6-7 (hard but sustainable, controlled breathing)',
    },
    'Over_Under': {
        'structure': '{duration} min with over-under intervals alternating 88-92% FTP (under) and 105-108% FTP (over)',
        'purpose': 'Race simulation. Teaches your body to clear lactate while maintaining power. Essential for gravel where pace constantly changes.',
        'execution': 'Unders are controlled, overs are hard surges. Focus on quick transitions. Cadence drops may occur on overs - thats normal.',
        'rpe': 'RPE 7-8 (unders) to 8-9 (overs)',
    },
    'Blended': {
        'structure': '{duration} min multi-zone workout combining G SPOT base with VO2max bursts and varied cadence',
        'purpose': 'Race simulation. Real gravel demands varied efforts - this workout trains your body to handle constant zone changes.',
        'execution': 'Mix of zones, cadences, and positions. Simulate terrain by varying effort. Stand for power bursts, seated for steady blocks.',
        'rpe': 'RPE 5-8 (varies throughout workout)',
    },
    'Threshold': {
        'structure': '{duration} min with threshold intervals @ 95-100% FTP',
        'purpose': 'FTP development. Training your body to sustain race-winning power.',
        'execution': 'Right at your limit. Controlled suffering. Cadence 90-95 rpm.',
        'rpe': 'RPE 7-8 (hard, requires focus)',
    },
    'VO2max': {
        'structure': '{duration} min with VO2max intervals @ 110-120% FTP',
        'purpose': 'Maximum aerobic power. Raising your ceiling so everything below feels easier.',
        'execution': 'These hurt. Start at 110%, adjust based on feel. High cadence 95-105 rpm.',
        'rpe': 'RPE 8-9 (very hard, labored breathing)',
    },
    'Anaerobic': {
        'structure': '{duration} min with anaerobic intervals @ 121-150% FTP',
        'purpose': 'Anaerobic capacity. Short, explosive power for attacks and surges.',
        'execution': 'All-out efforts. Full recovery between. Quality over quantity.',
        'rpe': 'RPE 9-10 (maximum effort)',
    },
    'Sprints': {
        'structure': '{duration} min with sprint intervals @ maximal power',
        'purpose': 'Neuromuscular power. Pure speed and explosive force.',
        'execution': 'Maximum power from the gun. Out of saddle, full commitment.',
        'rpe': 'RPE 10 (all-out)',
    },
    'FTP_Test': {
        'structure': '60 min FTP test protocol: 15 min warmup, 5 min blowout, 5 min recovery, 20 min ALL OUT test, 15 min cooldown',
        'purpose': 'Establish your training zones. The 20-minute effort sets everything.',
        'execution': 'Start controlled, settle in, suffer through the middle, finish strong. Average power × 0.95 = FTP.',
        'rpe': 'RPE 9/10 for the 20-minute test (very hard, barely sustainable)',
    },
    'Long_Ride': {
        'structure': '{duration} min endurance ride with tempo blocks',
        'purpose': 'Building aerobic endurance and time in saddle. Race-specific duration work.',
        'execution': 'Mostly Z2 with some Z3 blocks. Practice fueling and hydration.',
        'rpe': 'RPE 3-5 (easy to moderate)',
    },
    'Openers': {
        'structure': '{duration} min with 4x30sec openers @ 120% FTP',
        'purpose': 'Pre-race activation. Wake up the legs without creating fatigue.',
        'execution': 'Short, sharp efforts. Full recovery between. Done when you feel snappy.',
        'rpe': 'RPE 7-8 for efforts (short and controlled)',
    },
}


def format_workout_description(workout_type: str, duration: int, phase: str, week_num: int, day_abbrev: str) -> str:
    """
    Format workout description following v6.0 spec with STRUCTURE, PURPOSE, EXECUTION, RPE sections.
    """
    template = WORKOUT_DESCRIPTIONS.get(workout_type, WORKOUT_DESCRIPTIONS['Endurance'])

    structure = template['structure'].format(duration=duration)
    purpose = template['purpose']
    execution = template['execution']
    rpe = template['rpe']

    description = f"""STRUCTURE:
{structure}

PURPOSE:
{purpose}

EXECUTION:
{execution}

RPE:
{rpe}"""

    return description


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    """Load JSON file."""
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def generate_zwo_files(athlete_dir: Path, plan_dates: dict, methodology: dict, derived: dict, profile: dict = None) -> list:
    """
    Generate ZWO workout files based on plan_dates, methodology, and athlete schedule preferences.

    Returns list of generated file paths.
    """
    zwo_dir = athlete_dir / 'workouts'
    # Clear existing workouts before regenerating
    if zwo_dir.exists():
        for old_file in zwo_dir.glob('*.zwo'):
            old_file.unlink()
    zwo_dir.mkdir(exist_ok=True)

    generated_files = []

    # Get methodology config
    methodology_config = methodology.get('configuration', {})
    key_workouts = methodology_config.get('key_workouts', [])
    intensity_dist = methodology_config.get('intensity_distribution', {})

    # Map athlete methodology to Nate generator methodology
    methodology_id = methodology.get('methodology_id', 'polarized')
    nate_methodology = METHODOLOGY_MAP.get(methodology_id, 'POLARIZED')
    total_weeks = plan_dates.get('plan_weeks', 12)

    # Extract athlete context for personalized workouts
    athlete_name = profile.get('name', 'Athlete').split()[0] if profile else 'Athlete'  # First name only
    target_race = profile.get('target_race', {}) if profile else {}
    race_name = target_race.get('name', 'A Event')
    race_date = plan_dates.get('race_date', '')
    # Heat acclimation benefits ALL athletes regardless of race elevation
    needs_heat_training = True

    weeks = plan_dates.get('weeks', [])

    # Build athlete-specific weekly structure from profile
    preferred_days = profile.get('preferred_days', {}) if profile else {}
    schedule_constraints = profile.get('schedule_constraints', {}) if profile else {}
    preferred_long_day = schedule_constraints.get('preferred_long_day', 'saturday')
    strength_only_days = schedule_constraints.get('strength_only_days', [])

    # Use centralized day mappings from constants.py
    strength_only_abbrevs = [DAY_FULL_TO_ABBREV.get(d.lower(), d) for d in strength_only_days]
    long_day_abbrev = DAY_FULL_TO_ABBREV.get(preferred_long_day.lower(), 'Sat')

    def get_day_availability(day_abbrev: str) -> dict:
        """Get availability info for a day from profile."""
        day_full = DAY_ABBREV_TO_FULL.get(day_abbrev, day_abbrev.lower())
        return preferred_days.get(day_full, {'availability': 'available'})

    # Track workout distribution across the week for proper hard/easy alternation
    # This ensures we don't stack hard days back-to-back and provides zone variety
    week_workout_tracker = {'hard_days': [], 'current_week': 0, 'workout_count': 0}

    def build_day_schedule(day_abbrev: str, phase: str, phase_templates: dict, week_num: int = 0) -> tuple:
        """
        Determine workout type for a specific day based on:
        1. Time availability (duration cap)
        2. Training phase (base/build/peak/taper)
        3. Hard/easy distribution across the week
        4. Zone variety (Z2-Z7) appropriate to phase

        LIMITED availability means TIME constraints, NOT intensity constraints.
        Athletes with 60 min can absolutely do VO2max, threshold, anaerobic work.

        Zone reference:
        - Z1: Recovery (<55% FTP)
        - Z2: Endurance (55-75% FTP)
        - Z3: Tempo (76-87% FTP)
        - Z4: Threshold (88-105% FTP)
        - Z5: VO2max (106-120% FTP)
        - Z6: Anaerobic Capacity (121-150% FTP)
        - Z7: Neuromuscular (maximal sprints)
        """
        avail = get_day_availability(day_abbrev)
        availability = avail.get('availability', 'available')
        workout_type = avail.get('workout_type', '')
        is_key_day = avail.get('is_key_day_ok', False)
        is_long_day = avail.get('is_long_day', False) or day_abbrev == long_day_abbrev
        max_duration = avail.get('max_duration_min', 120)

        # Reset tracker for new week
        if week_num != week_workout_tracker['current_week']:
            week_workout_tracker['hard_days'] = []
            week_workout_tracker['current_week'] = week_num
            week_workout_tracker['workout_count'] = 0

        # Unavailable or rest days = Rest
        if availability in ('unavailable', 'rest'):
            return ('Rest', None, 0, 0)

        # Strength-only days (e.g., travel days)
        if day_abbrev in strength_only_abbrevs or workout_type == 'strength_only':
            template = phase_templates.get('strength', ('Strength', 'Strength training session', 45, 0.0))
            return cap_duration(template, max_duration)

        # Long day (Saturday/Sunday typically) - this is a KEY session
        if is_long_day and phase != 'race':
            week_workout_tracker['hard_days'].append(day_abbrev)
            template = phase_templates.get('long_ride')
            return cap_duration(template, max_duration)

        # Designated KEY days get the primary interval session
        # BUT we still want methodology-aware selection, so fall through to methodology logic
        # (removed early return that bypassed methodology selection)

        # For LIMITED or AVAILABLE days:
        # Distribute workouts with proper zone variety
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_idx = day_order.index(day_abbrev) if day_abbrev in day_order else 0
        prev_day = day_order[day_idx - 1] if day_idx > 0 else None

        # Check if previous day was hard (VO2max, Threshold, Anaerobic need recovery)
        prev_was_hard = prev_day in week_workout_tracker['hard_days']

        # G SPOT Methodology Distribution Logic:
        # Target: 45% Z1-Z2, 30% Z3/G-Spot, 25% Z4-Z5
        # In a 7-day week with ~5-6 non-rest days:
        # - 2-3 easy days (Recovery/Endurance/Long Ride)
        # - 2 G-Spot/Tempo days
        # - 1-2 high intensity days (VO2max/Threshold/Over-Under)
        #
        # Only require Recovery after 2+ consecutive hard days (prevent overtraining)
        # Otherwise allow methodology-driven workout selection

        # Dynamic weekly structure derived from athlete profile
        # Quality days: all available/limited days (methodology cycle handles intensity %)
        # Easy days: unavailable/rest days only
        # Long day: from profile preference (handled above - returns early)
        #
        # The methodology cycle determines WHAT quality workout to do (endurance vs
        # intensity). For POLARIZED this means 80% endurance, 20% intensity among
        # quality days. For G_SPOT, more intensity slots. This approach works
        # regardless of whether the long day is Sat or Sun.
        all_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        quality_days = []
        easy_days = []
        for d in all_days:
            if d == long_day_abbrev:
                continue  # Long day handled above (returns early)
            d_avail = get_day_availability(d)
            if d_avail.get('availability') in ('unavailable', 'rest'):
                easy_days.append(d)
            else:
                quality_days.append(d)
        # Fallback if profile has no available days
        if not quality_days:
            quality_days = ['Mon', 'Wed', 'Thu', 'Fri']
            easy_days = [d for d in all_days if d not in quality_days and d != long_day_abbrev]
        n_quality = len(quality_days)

        # Find which quality day positions are key days (is_key_day_ok=true)
        # Intensity workouts should land on these positions, not arbitrary first slots
        key_positions = [i for i, d in enumerate(quality_days)
                         if get_day_availability(d).get('is_key_day_ok', False)]
        # Fallback: if no key days marked, use first and middle positions
        if not key_positions:
            key_positions = [0, n_quality // 2] if n_quality > 1 else [0]

        # Long day takes precedence (handled above - returns early for Sat)
        # Quality days get methodology-driven workouts
        is_quality_day = day_abbrev in quality_days

        if day_abbrev in easy_days:
            # True recovery day - Z1/Z2 easy spin
            # Don't increment workout counter - recovery doesn't affect methodology cycle
            template = phase_templates.get('easy', ('Recovery', 'Easy spin', 30, 0.50))
        else:
            # Increment workout counter ONLY for methodology-driven days
            week_workout_tracker['workout_count'] += 1
            workout_num = week_workout_tracker['workout_count']

            # Can do a harder workout - distribute zones based on phase
            week_workout_tracker['hard_days'].append(day_abbrev)

            # METHODOLOGY-AWARE WORKOUT SELECTION
            # Use the methodology's preferred workout distribution
            if nate_methodology == 'HIT':
                # HIIT: VO2max, Anaerobic, Sprints dominate - even in base phase
                # 4 quality sessions per week per methodology config
                if phase in ('base', 'build'):
                    cycle = workout_num % 4
                    if cycle == 0:
                        template = ('VO2max', 'VO2max: 5x3min @ 110-115% FTP', 50, 0.80)
                    elif cycle == 1:
                        template = ('Anaerobic', 'Anaerobic: 8x1min @ 130% FTP', 45, 0.75)
                    elif cycle == 2:
                        template = ('Sprints', 'Sprint repeats: 10x30sec all-out', 40, 0.70)
                    else:
                        template = ('Threshold', 'Threshold: 2x10min @ 100% FTP', 50, 0.78)
                elif phase == 'peak':
                    cycle = workout_num % 3
                    if cycle == 0:
                        template = ('VO2max', 'VO2max: 6x3min @ 115-120% FTP', 50, 0.82)
                    elif cycle == 1:
                        template = ('Anaerobic', 'Tabata: 8x20sec all-out', 35, 0.70)
                    else:
                        template = ('Sprints', 'Max sprints: 6x15sec', 35, 0.65)
                elif phase == 'taper':
                    template = ('Sprints', 'Openers: 4x15sec all-out', 30, 0.55)
                elif phase == 'race':
                    template = ('Easy', 'Easy activation', 25, 0.50)
                elif phase == 'maintenance':
                    cycle = workout_num % 3
                    if cycle == 0:
                        template = ('VO2max', 'VO2max touch: 4x3min @ 110% FTP', 45, 0.75)
                    elif cycle == 1:
                        template = ('Anaerobic', 'Anaerobic: 6x1min @ 125% FTP', 40, 0.70)
                    else:
                        template = ('Endurance', 'Easy endurance', 45, 0.62)
                else:
                    template = ('Endurance', 'Zone 2', 45, 0.62)

            elif nate_methodology == 'POLARIZED':
                # Polarized: 80% easy, 20% very hard (Z5+), minimal Z3/Z4
                # Use key_positions to place intensity on athlete's preferred key days.
                # (workout_num - 1) % n_quality gives 0-indexed position within the week.
                nq = max(n_quality, 1)
                cycle = (workout_num - 1) % nq
                # Primary key position (first key day, e.g. Wed)
                kp0 = key_positions[0] if key_positions else 0
                # Secondary key position (second key day, e.g. Sat)
                kp1 = key_positions[1] if len(key_positions) > 1 else (kp0 + nq // 2) % nq
                if phase == 'base':
                    # 1 intensity per week on primary key day
                    if cycle == kp0:
                        template = ('VO2max', 'VO2max: 4x4min @ 108-112% FTP', 55, 0.78)
                    else:
                        template = ('Endurance', 'Zone 2 steady', 50, 0.65)
                elif phase == 'build':
                    # 2 intensity per week on both key days
                    if cycle == kp0:
                        template = ('VO2max', 'VO2max: 5x4min @ 110-115% FTP', 55, 0.80)
                    elif cycle == kp1:
                        template = ('Anaerobic', 'Anaerobic: 6x1min @ 130% FTP', 45, 0.72)
                    else:
                        template = ('Endurance', 'Zone 2 steady', 50, 0.65)
                elif phase == 'peak':
                    # 2 intensity per week on both key days
                    if cycle == kp0:
                        template = ('VO2max', 'VO2max: 6x3min @ 115-120% FTP', 50, 0.82)
                    elif cycle == kp1:
                        template = ('Sprints', 'Neuromuscular: 8x20sec max', 40, 0.68)
                    else:
                        template = ('Endurance', 'Zone 2', 45, 0.62)
                elif phase == 'taper':
                    # 1 opener on primary key day, rest easy
                    if cycle == kp0:
                        template = ('VO2max', 'Openers: 3x2min @ 110% FTP', 35, 0.60)
                    else:
                        template = ('Easy', 'Easy spin', 30, 0.55)
                elif phase == 'race':
                    template = ('Easy', 'Activation', 25, 0.50)
                elif phase == 'maintenance':
                    if cycle == kp0:
                        template = ('VO2max', 'VO2max: 4x3min @ 110% FTP', 45, 0.75)
                    else:
                        template = ('Endurance', 'Zone 2 maintenance', 50, 0.62)
                else:
                    template = ('Endurance', 'Zone 2', 45, 0.62)

            elif nate_methodology == 'G_SPOT':
                # G SPOT: 45% Z1-Z2, 30% Z3 (G SPOT/Tempo), 25% Z4-Z5
                # The cycle drives methodology workouts; recovery/long ride add Z1-Z2
                # Use (workout_num - 1) for 0-indexed cycling
                cycle = (workout_num - 1)

                if phase == 'base':
                    # Base: Build aerobic foundation with G SPOT intro
                    # Cycle of 4: G_Spot, Tempo, G_Spot, Over_Under (varies intensity)
                    c = cycle % 4
                    if c == 0:
                        template = ('G_Spot', 'G SPOT Intro: 2x10min @ 88-90% FTP', 55, 0.89)
                    elif c == 1:
                        template = ('Tempo', 'Tempo Foundation: 2x12min @ 82-85% FTP', 50, 0.84)
                    elif c == 2:
                        template = ('G_Spot', 'G SPOT Builder: 3x8min @ 90% FTP', 50, 0.90)
                    else:
                        template = ('Over_Under', 'Over-Under Intro: 3x(3min under + 1min over)', 50, 0.92)
                elif phase == 'build':
                    # Build: Full G SPOT work with VO2max and threshold
                    # Cycle of 5: G_Spot, Over_Under, VO2max, Threshold, G_Spot
                    c = cycle % 5
                    if c == 0:
                        template = ('G_Spot', 'G SPOT Criss-Cross: 3x12min @ 88-94% FTP with surges', 55, 0.91)
                    elif c == 1:
                        template = ('Over_Under', 'Over-Unders: 4x(3min @ 90% + 1min @ 105%)', 55, 0.95)
                    elif c == 2:
                        template = ('VO2max', 'VO2max Builder: 4x4min @ 108-115% FTP', 55, 0.80)
                    elif c == 3:
                        template = ('Threshold', 'Threshold Blocks: 2x15min @ 95-100% FTP', 55, 0.97)
                    else:
                        template = ('G_Spot', 'G SPOT Progressive: 10-12-15min @ 90-92% FTP', 60, 0.91)
                elif phase == 'peak':
                    # Peak: Race-specific intensity with blended efforts
                    c = cycle % 5
                    if c == 0:
                        template = ('G_Spot', 'Race Pace G SPOT: 3x15min @ 92-94% FTP', 60, 0.93)
                    elif c == 1:
                        template = ('VO2max', 'VO2max Repeats: 5x3min @ 115-120% FTP', 50, 0.82)
                    elif c == 2:
                        template = ('Threshold', 'Threshold + Attacks: 15min FTP with 3x1min surges', 55, 0.98)
                    elif c == 3:
                        template = ('Over_Under', 'Race Sim Over-Unders: 5x(2min @ 88% + 2min @ 105%)', 55, 0.95)
                    else:
                        template = ('Blended', 'Gravel Simulation: G SPOT + VO2 bursts', 55, 0.88)
                elif phase == 'taper':
                    # Taper: SHORT openers only - no VO2max, no fatigue
                    # Day-specific taper protocol
                    if day_abbrev == 'Mon':
                        template = ('Easy', 'Taper: Easy spin, legs loose', 45, 0.55)
                    elif day_abbrev == 'Tue':
                        template = ('Openers', 'Openers: 4x30sec @ 110% + easy spin', 40, 0.60)
                    elif day_abbrev == 'Wed':
                        template = ('Easy', 'Taper: Z2 easy, stay fresh', 40, 0.55)
                    elif day_abbrev == 'Thu':
                        template = ('Openers', 'Openers: 3x1min @ race pace', 35, 0.65)
                    elif day_abbrev == 'Fri':
                        template = ('Shakeout', 'Shakeout: 20min easy spin only', 20, 0.50)
                    else:
                        template = ('Easy', 'Taper: Easy spin', 30, 0.50)
                elif phase == 'race':
                    # Race week: Day-specific protocol leading to race day
                    if day_abbrev == 'Mon':
                        template = ('Easy', 'Race Week: Easy spin, mental prep', 40, 0.50)
                    elif day_abbrev == 'Tue':
                        template = ('Openers', 'Race Week Openers: 3x30sec hard', 30, 0.55)
                    elif day_abbrev == 'Wed':
                        template = ('Easy', 'Race Week: Very easy, rest legs', 30, 0.50)
                    elif day_abbrev == 'Thu':
                        template = ('Openers', 'Race Week: Final openers 2x1min', 25, 0.55)
                    elif day_abbrev == 'Fri':
                        template = ('Shakeout', 'Race Week: Shakeout only, stay off feet', 20, 0.45)
                    elif day_abbrev == 'Sat':
                        template = ('Rest', 'Race Week: REST - hydrate, prep gear', 0, 0.0)
                    else:
                        template = ('Easy', 'Race Week: Easy activation', 25, 0.50)
                elif phase == 'maintenance':
                    c = cycle % 4
                    if c == 0:
                        template = ('G_Spot', 'G SPOT Maintenance: 2x10min @ 88-90% FTP', 50, 0.89)
                    elif c == 1:
                        template = ('VO2max', 'VO2max Touch: 3x3min @ 110% FTP', 45, 0.75)
                    elif c == 2:
                        template = ('Threshold', 'Threshold Touch: 2x8min @ 95% FTP', 45, 0.72)
                    else:
                        template = ('Endurance', 'Zone 2 maintenance', 50, 0.62)
                else:
                    template = ('Endurance', 'Zone 2', 45, 0.62)

            else:
                # Default PYRAMIDAL/other: Traditional progression
                if phase == 'base':
                    if workout_num % 3 == 0:
                        template = ('Tempo', 'Tempo: 2x10min @ 85% FTP', 50, 0.72)
                    else:
                        template = ('Endurance', 'Zone 2 steady state', 45, 0.65)
                elif phase == 'build':
                    cycle = workout_num % 4
                    if cycle == 0:
                        template = ('VO2max', 'VO2max: 4x3min @ 110% FTP', 50, 0.80)
                    elif cycle == 1:
                        template = ('Threshold', 'Threshold: 3x10min @ 95% FTP', 55, 0.78)
                    elif cycle == 2:
                        template = ('Sweet_Spot', 'Sweet spot: 3x12min @ 88% FTP', 55, 0.75)
                    else:
                        template = ('Tempo', 'Tempo: 2x15min @ 85% FTP', 50, 0.72)
                elif phase == 'peak':
                    cycle = workout_num % 4
                    if cycle == 0:
                        template = ('VO2max', 'VO2max: 5x3min @ 115% FTP', 50, 0.82)
                    elif cycle == 1:
                        template = ('Anaerobic', 'Anaerobic: 8x30sec @ 150% FTP', 45, 0.70)
                    elif cycle == 2:
                        template = ('Threshold', 'Threshold: 2x15min @ 100% FTP', 50, 0.78)
                    else:
                        template = ('VO2max', 'VO2max: 4x4min @ 110% FTP', 55, 0.80)
                elif phase == 'taper':
                    if workout_num % 2 == 0:
                        template = ('Openers', 'VO2 openers: 3x2min @ 110% FTP', 40, 0.65)
                    else:
                        template = ('Sprints', 'Sprint openers: 4x15sec all-out', 35, 0.55)
                elif phase == 'race':
                    template = ('Easy', 'Easy spin', 30, 0.50)
                elif phase == 'maintenance':
                    cycle = workout_num % 3
                    if cycle == 0:
                        template = ('Threshold', 'Threshold touch: 2x8min @ 95% FTP', 45, 0.72)
                    elif cycle == 1:
                        template = ('Tempo', 'Tempo: 2x12min @ 85% FTP', 45, 0.70)
                    else:
                        template = ('Endurance', 'Zone 2 maintenance', 50, 0.62)
                else:
                    template = ('Endurance', 'Zone 2', 45, 0.62)

        return cap_duration(template, max_duration)

    # Build custom workout templates per day based on athlete schedule
    def get_workout_for_day(day_abbrev: str, phase: str, week_num: int = 0) -> tuple:
        """Get the appropriate workout for a day and phase."""
        # Use centralized templates from workout_templates.py
        phase_templates = get_phase_roles(phase)
        return build_day_schedule(day_abbrev, phase, phase_templates, week_num)

    # Use custom schedule if profile has preferred_days, otherwise use centralized defaults
    use_custom_schedule = bool(preferred_days)

    # ZWO XML template - MUST match TrainingPeaks working format EXACTLY
    # Reference: Drop_Down_1_Updated.zwo (confirmed working)
    ZWO_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{name}</name>
  <description>{description}</description>
  <sportType>bike</sportType>
  <workout>
{blocks}  </workout>
</workout_file>"""

    def create_workout_blocks(duration_min: int, avg_power: float, workout_type: str) -> str:
        """Generate ZWO workout blocks with 4-space indent per v6.0 spec."""
        if duration_min == 0:
            return "    <FreeRide Duration=\"60\"/>\n"

        blocks = []

        # Warmup (10% of workout or min 5 min)
        warmup_min = max(5, int(duration_min * 0.1))
        blocks.append(f'    <Warmup Duration="{warmup_min * 60}" PowerLow="0.50" PowerHigh="0.68"/>')

        main_duration = duration_min - warmup_min - 5  # Save 5 min for cooldown

        if workout_type in ['Recovery', 'Easy', 'Shakeout']:
            # Steady easy effort
            blocks.append(f'    <SteadyState Duration="{main_duration * 60}" Power="{avg_power}"/>')

        elif workout_type == 'Endurance':
            # Zone 2 steady
            blocks.append(f'    <SteadyState Duration="{main_duration * 60}" Power="{avg_power}"/>')

        elif workout_type == 'Tempo':
            # Warmup more, then tempo block
            tempo_duration = int(main_duration * 0.6)
            easy_duration = main_duration - tempo_duration
            blocks.append(f'    <SteadyState Duration="{easy_duration * 60}" Power="0.60"/>')
            blocks.append(f'    <SteadyState Duration="{tempo_duration * 60}" Power="0.85"/>')

        elif workout_type == 'Intervals':
            # Use progressive intervals from workout library
            # week_num and phase passed via closure from outer scope
            return None  # Signal to use progressive generator

        elif workout_type == 'VO2max':
            # Use progressive VO2max from workout library
            return None  # Signal to use progressive generator

        elif workout_type == 'Openers':
            # 4x30sec hard
            blocks.append(f'    <SteadyState Duration="{(main_duration - 4) * 60}" Power="0.60"/>')
            blocks.append(f'    <IntervalsT Repeat="4" OnDuration="30" OnPower="1.20" OffDuration="60" OffPower="0.50"/>')

        elif workout_type == 'FTP_Test':
            # "The Assessment - Functional Threshold" (1:00:00, 68 TSS, IF 0.82)
            # Based on Gravel God standard FTP test protocol
            # Structure: 12m progressive warmup, 5m @ 6/10, 5m easy, 5m blowout, 5m easy, 20m ALL OUT, 10m cooldown
            # CRITICAL: No nested textevent in SteadyState - breaks TrainingPeaks import
            blocks = []  # Reset blocks, we handle warmup/cooldown ourselves
            # 12m progressive warmup (45% -> 70%)
            blocks.append('    <Warmup Duration="720" PowerLow="0.45" PowerHigh="0.70"/>')
            # 5m @ RPE 6/10 (~80% FTP)
            blocks.append('    <SteadyState Duration="300" Power="0.80"/>')
            # 5m easy recovery (50%)
            blocks.append('    <SteadyState Duration="300" Power="0.50"/>')
            # 5m blowout @ RPE 8-10 (~105% FTP) - go hard, find your legs
            blocks.append('    <SteadyState Duration="300" Power="1.05"/>')
            # 5m easy recovery (50%)
            blocks.append('    <SteadyState Duration="300" Power="0.50"/>')
            # 20m ALL OUT - FTP test @ 100% FTP (athlete should go max sustainable)
            blocks.append('    <SteadyState Duration="1200" Power="1.00"/>')
            # 10m cooldown
            blocks.append('    <Cooldown Duration="600" PowerLow="0.55" PowerHigh="0.40"/>')
            return '\n'.join(blocks) + '\n'

        elif workout_type == 'Long_Ride':
            # Long steady with some tempo blocks
            z2_duration = int(main_duration * 0.7) * 60
            tempo_duration = int(main_duration * 0.3) * 60
            blocks.append(f'    <SteadyState Duration="{z2_duration}" Power="0.65"/>')
            blocks.append(f'    <SteadyState Duration="{tempo_duration}" Power="0.80"/>')

        elif workout_type == 'Race_Sim':
            # Race simulation with sustained efforts
            blocks.append(f'    <SteadyState Duration="{int(main_duration * 0.3) * 60}" Power="0.65"/>')
            blocks.append(f'    <IntervalsT Repeat="3" OnDuration="600" OnPower="0.90" OffDuration="300" OffPower="0.60"/>')
            blocks.append(f'    <SteadyState Duration="{int(main_duration * 0.2) * 60}" Power="0.65"/>')

        elif workout_type == 'Sweet_Spot':
            # Sweet spot intervals (88-94% FTP) - sustainable but challenging
            # 3x10min @ 88% FTP with 3min rest
            easy_start = int(main_duration * 0.15) * 60  # Easy warmup continuation
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            blocks.append('    <IntervalsT Repeat="3" OnDuration="600" OnPower="0.88" OffDuration="180" OffPower="0.55">')
            blocks.append('      <textevent timeoffset="0" message="Sweet spot interval - comfortably hard, sustainable effort"/>')
            blocks.append('      <textevent timeoffset="300" message="Halfway through this block - stay smooth"/>')
            blocks.append('    </IntervalsT>')
            easy_end = max(60, (main_duration - 15 - (3*10 + 2*3)) * 60)  # Remaining time
            blocks.append(f'    <SteadyState Duration="{easy_end}" Power="0.60"/>')

        elif workout_type == 'G_Spot':
            # G SPOT intervals (88-94% FTP) - the Gravel God efficiency zone
            # Progressive blocks with varied durations - blended approach per Rule #15
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            # 3x10min @ 90% FTP with 3min rest, including cadence variation
            blocks.append('    <IntervalsT Repeat="3" OnDuration="600" OnPower="0.90" OffDuration="180" OffPower="0.55">')
            blocks.append('      <textevent timeoffset="0" message="G SPOT interval - the efficiency zone. Stay smooth."/>')
            blocks.append('      <textevent timeoffset="180" message="3 min in - try higher cadence 95+ rpm"/>')
            blocks.append('      <textevent timeoffset="360" message="Halfway - drop to 80 rpm, feel the power"/>')
            blocks.append('      <textevent timeoffset="480" message="Final 2 min - back to normal cadence, hold power"/>')
            blocks.append('    </IntervalsT>')
            # Add a short burst block for variety (blended workout dimension)
            blocks.append('    <SteadyState Duration="120" Power="0.55"/>')
            blocks.append('    <IntervalsT Repeat="4" OnDuration="30" OnPower="1.15" OffDuration="90" OffPower="0.50">')
            blocks.append('      <textevent timeoffset="0" message="SURGE! 30 seconds hard - simulate race attack"/>')
            blocks.append('    </IntervalsT>')
            blocks.append(f'    <SteadyState Duration="{max(60, int(main_duration * 0.05) * 60)}" Power="0.58"/>')

        elif workout_type == 'Over_Under':
            # Over-under intervals - alternating 88-92% (under) and 105-108% (over)
            # Teaches lactate clearance while maintaining power
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            # 4 sets: 3min under @ 90%, 1min over @ 106%
            for i in range(4):
                blocks.append('    <SteadyState Duration="180" Power="0.90"/>')
                blocks.append('    <SteadyState Duration="60" Power="1.06"/>')
                if i < 3:  # Rest between sets
                    blocks.append('    <SteadyState Duration="180" Power="0.50"/>')
            blocks.append(f'    <SteadyState Duration="{max(60, int(main_duration * 0.1) * 60)}" Power="0.58"/>')

        elif workout_type == 'Blended':
            # Blended multi-zone workout - simulates gravel race demands
            # Combines G SPOT base, VO2max bursts, tempo, and varied cadence
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            # Block 1: G SPOT with surges
            blocks.append('    <SteadyState Duration="300" Power="0.88"/>')
            blocks.append('    <IntervalsT Repeat="3" OnDuration="30" OnPower="1.20" OffDuration="90" OffPower="0.85">')
            blocks.append('      <textevent timeoffset="0" message="ATTACK! Surge over the climb"/>')
            blocks.append('    </IntervalsT>')
            # Block 2: Sustained tempo
            blocks.append('    <SteadyState Duration="180" Power="0.55"/>')
            blocks.append('    <SteadyState Duration="480" Power="0.82"/>')
            # Block 3: VO2max efforts
            blocks.append('    <SteadyState Duration="120" Power="0.55"/>')
            blocks.append('    <IntervalsT Repeat="3" OnDuration="120" OnPower="1.12" OffDuration="120" OffPower="0.50">')
            blocks.append('      <textevent timeoffset="0" message="VO2max effort - 2 min hard!"/>')
            blocks.append('    </IntervalsT>')
            # Block 4: Race-pace finish
            blocks.append('    <SteadyState Duration="120" Power="0.55"/>')
            blocks.append('    <SteadyState Duration="300" Power="0.92"/>')
            blocks.append(f'    <SteadyState Duration="{max(60, int(main_duration * 0.05) * 60)}" Power="0.55"/>')

        elif workout_type == 'Threshold':
            # Threshold intervals (Z4: 95-105% FTP)
            # 2-3x10-15min @ 95-100% FTP with 5min rest
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            blocks.append('    <IntervalsT Repeat="2" OnDuration="720" OnPower="0.97" OffDuration="300" OffPower="0.55">')
            blocks.append('      <textevent timeoffset="0" message="Threshold interval - right at FTP, controlled suffering"/>')
            blocks.append('      <textevent timeoffset="360" message="Halfway - maintain power, control breathing"/>')
            blocks.append('      <textevent timeoffset="600" message="Final 2 minutes - hold steady!"/>')
            blocks.append('    </IntervalsT>')
            blocks.append(f'    <SteadyState Duration="{max(60, int(main_duration * 0.1) * 60)}" Power="0.58"/>')

        elif workout_type == 'Anaerobic':
            # Anaerobic capacity intervals (Z6: 121-150% FTP)
            # 8x30sec @ 150% FTP with 2min rest - builds anaerobic capacity
            easy_start = int(main_duration * 0.15) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.60"/>')
            blocks.append('    <IntervalsT Repeat="8" OnDuration="30" OnPower="1.50" OffDuration="120" OffPower="0.45">')
            blocks.append('      <textevent timeoffset="0" message="ANAEROBIC - 30 seconds ALL OUT! Maximum effort!"/>')
            blocks.append('      <textevent timeoffset="15" message="Halfway - keep pushing!"/>')
            blocks.append('    </IntervalsT>')
            blocks.append(f'    <SteadyState Duration="{max(120, int(main_duration * 0.1) * 60)}" Power="0.55"/>')

        elif workout_type == 'Sprints':
            # Neuromuscular power (Z7: maximal sprints)
            # 6x10-15sec all-out with full recovery - pure power
            easy_start = int(main_duration * 0.2) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.58"/>')
            blocks.append('    <IntervalsT Repeat="6" OnDuration="12" OnPower="2.00" OffDuration="180" OffPower="0.40">')
            blocks.append('      <textevent timeoffset="0" message="SPRINT! Maximum power - out of the saddle!"/>')
            blocks.append('    </IntervalsT>')
            blocks.append(f'    <SteadyState Duration="{max(120, int(main_duration * 0.1) * 60)}" Power="0.55"/>')

        elif workout_type == 'Over_Unders':
            # Over-under intervals - great for building FTP and lactate tolerance
            # Alternating between 95% and 105% FTP
            # CRITICAL: No nested textevent in SteadyState - use self-closing tags
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            # 3 sets of 8 min (2min under @ 95%, 1min over @ 105%, repeat)
            for i in range(3):
                blocks.append('    <SteadyState Duration="120" Power="0.95"/>')
                blocks.append('    <SteadyState Duration="60" Power="1.05"/>')
                blocks.append('    <SteadyState Duration="120" Power="0.95"/>')
                blocks.append('    <SteadyState Duration="60" Power="1.05"/>')
                if i < 2:  # Rest between sets
                    blocks.append('    <SteadyState Duration="240" Power="0.50"/>')

        else:
            blocks.append(f'    <SteadyState Duration="{main_duration * 60}" Power="{avg_power}"/>')

        # Cooldown
        blocks.append(f'    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.45"/>')

        return '\n'.join(blocks) + '\n'

    # Track when we've added FTP tests and when build phase starts
    ftp_test_week1_added = False
    ftp_test_prebuild_added = False
    first_build_week = None

    # Pre-calculate week_in_phase for each week (PERFORMANCE: avoids O(n^2) loop)
    week_in_phase_cache = {}
    phase_counters = {}
    for week in weeks:
        week_num = week['week']
        phase = week['phase']
        if phase not in phase_counters:
            phase_counters[phase] = 0
        phase_counters[phase] += 1
        week_in_phase_cache[week_num] = phase_counters[phase]

        # Also find first build week while we're iterating
        if phase == 'build' and first_build_week is None:
            first_build_week = week_num

    # =========================================================================
    # PRE-PLAN WEEK (W00): Generate workouts for days before plan officially starts
    # This ensures athletes have guidance from day 1, not just from plan_start
    # =========================================================================
    def generate_pre_plan_week():
        """Generate pre-plan week workouts (W00) for days before official plan start."""
        from datetime import datetime, timedelta

        plan_start_str = plan_dates.get('plan_start', '')
        if not plan_start_str:
            return []

        plan_start = datetime.strptime(plan_start_str, '%Y-%m-%d')

        # Calculate days from today until plan start
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_until_start = (plan_start - today).days

        # Only generate pre-plan if plan starts in the future (1-7 days out)
        if days_until_start <= 0 or days_until_start > 7:
            return []

        pre_plan_files = []
        days_to_race = (datetime.strptime(race_date, '%Y-%m-%d') - today).days if race_date else 0

        # Generate workouts for each day from today until plan start
        for day_offset in range(days_until_start):
            current_date = today + timedelta(days=day_offset)
            day_abbrev = current_date.strftime('%a')[:3]  # Mon, Tue, etc.
            date_short = current_date.strftime('%b%-d')  # Feb11, Feb12, etc.
            days_to_plan_start = days_until_start - day_offset

            # Skip unavailable days in pre-plan week
            if use_custom_schedule:
                day_avail = get_day_availability(day_abbrev)
                if day_avail.get('availability') in ('unavailable', 'rest'):
                    continue

            # Pre-plan week workout structure
            if day_abbrev == 'Sat':
                # Longer endurance ride
                workout_type = 'Pre_Plan_Endurance'
                duration = 80
                power = 0.65
                description = f"""PRE-PLAN WEEK: Endurance Ride
{athlete_name} - {days_to_plan_start} days until plan starts

PURPOSE:
Longer easy ride to build aerobic base and test nutrition.

WORKOUT:
- 75-90 min at Z2 (60-70% FTP)
- Practice fueling: aim for 40-60g carbs/hour
- Stay hydrated

OUTDOOR STRONGLY ENCOURAGED:
- Build confidence on gravel/mixed terrain
- Practice reading the road ahead
- Test your nutrition strategy

Almost there, {athlete_name}!"""

            elif day_abbrev == 'Sun':
                # Rest day before plan starts
                workout_type = 'Pre_Plan_Rest'
                duration = 0
                power = 0
                description = f"""PRE-PLAN WEEK: Rest Day
{athlete_name} - Plan starts tomorrow!

PURPOSE:
Complete rest before your {total_weeks}-week journey begins.

TODAY:
- OFF the bike
- Light stretching or yoga if desired
- Focus on sleep, hydration, nutrition

PREP FOR TOMORROW:
- Charge devices (bike computer, HRM, etc.)
- Check bike mechanicals
- Review your training zones

{total_weeks} weeks to {race_name}.
Trust the process. One workout at a time.

Let's go, {athlete_name}! See you tomorrow."""

            elif day_abbrev == 'Thu':
                # Mobility/strength prep
                workout_type = 'Pre_Plan_Strength_Prep'
                duration = 35
                power = 0
                description = f"""PRE-PLAN WEEK: Strength Prep
{athlete_name} - {days_to_plan_start} days until plan starts

PURPOSE:
Light movement prep to activate muscles before structured strength begins.

WARM-UP (10 min):
- 5 min easy spin or walk
- Arm circles, leg swings, hip circles

MOBILITY CIRCUIT (15 min, 2 rounds):
- Cat-Cow stretches: 10 reps
- Hip 90/90 rotations: 8 each side
- Glute bridges: 12 reps
- Bird dogs: 8 each side
- Plank hold: 30 sec

ACTIVATION (10 min):
- Banded clamshells: 15 each side
- Banded lateral walks: 10 each direction
- Single leg balance: 30 sec each

NOTES:
- Keep everything light - no soreness tomorrow
- This is movement prep, not a hard workout

Good prep work, {athlete_name}!"""

            else:
                # Easy spin days (Mon, Tue, Wed, Fri)
                workout_type = 'Pre_Plan_Easy'
                duration = 45 if day_abbrev in ['Mon', 'Wed'] else 40
                power = 0.55
                description = f"""PRE-PLAN WEEK: Easy Spin
{athlete_name} - {days_to_plan_start} days until plan starts

PURPOSE:
Keep the legs moving. Easy effort only.

WORKOUT:
- {duration} min easy spin
- Z1-Z2 only (conversational pace)
- High cadence (90-100 rpm) if comfortable
- Focus on relaxed shoulders, loose grip

NOTES:
- Your {total_weeks}-week plan starts soon
- Use this time to dial in nutrition, sleep, recovery habits
- Check bike fit and equipment

Stay loose, {athlete_name}!"""

            # Build workout file
            filename = f"W00_{day_abbrev}_{date_short}_{workout_type}.zwo"

            if duration > 0:
                blocks = create_workout_blocks(duration, power, 'Easy')
            else:
                blocks = "    <FreeRide Duration=\"60\"/>\n"

            zwo_content = ZWO_TEMPLATE.format(
                name=filename.replace('.zwo', ''),
                description=description,
                blocks=blocks
            )

            zwo_path = zwo_dir / filename
            with open(zwo_path, 'w') as f:
                f.write(zwo_content)
            pre_plan_files.append(zwo_path)

        return pre_plan_files

    # Generate pre-plan week
    pre_plan_files = generate_pre_plan_week()
    generated_files.extend(pre_plan_files)

    for week in weeks:
        week_num = week['week']
        phase = week['phase']

        # Use custom schedule if available, otherwise use centralized default templates
        if use_custom_schedule:
            phase_workouts = None  # Will use get_workout_for_day instead
        else:
            phase_workouts = DEFAULT_WEEKLY_SCHEDULE.get(phase, DEFAULT_WEEKLY_SCHEDULE['base'])

        for day_info in week.get('days', []):
            day_abbrev = day_info['day']
            date_short = day_info['date_short']
            workout_prefix = day_info['workout_prefix']
            is_race_day = day_info.get('is_race_day', False)
            is_b_race_day = day_info.get('is_b_race_day', False)
            is_b_race_opener = day_info.get('is_b_race_opener', False)
            is_b_race_easy = day_info.get('is_b_race_easy', False)

            # -----------------------------------------------------------
            # B-RACE DAY: Generate a simplified race execution plan
            # This replaces whatever workout was scheduled for the day.
            # -----------------------------------------------------------
            if is_b_race_day:
                b_race_info = week.get('b_race', {})
                b_race_name = b_race_info.get('name', 'B-Race')
                b_race_plan_name = f"{workout_prefix}_RACE_DAY_{b_race_name.replace(' ', '_')}"
                b_race_filename = f"{b_race_plan_name}.zwo"

                b_race_description = f"""B-RACE DAY: {b_race_name}
Date: {day_info['date']}
Priority: B (training race - NOT the goal event)

THIS IS A TRAINING RACE:
- Race hard, but don't blow up your training block
- Use this as a fitness check and race-craft practice
- Target effort: 90-95% of A-race effort
- Practice fueling, pacing, and gear choices

PRE-RACE:
- 15 min easy warmup with 3x30sec openers
- Stay hydrated, eat familiar foods

PACING:
- Start conservative, find your rhythm
- Use the middle third to test race pace
- Final third: push if you feel good, back off if not

POST-RACE:
- Easy spin cooldown 15-20 min
- Resume normal training within 2 days
- This is a stepping stone to {race_name}, not the goal

GO RACE SMART, {athlete_name.upper()}!
"""

                b_race_zwo = f"""<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{b_race_plan_name}</name>
  <description>{b_race_description}</description>
  <sportType>bike</sportType>
  <workout>
    <FreeRide Duration="10800"/>
  </workout>
</workout_file>"""

                filepath = zwo_dir / b_race_filename
                with open(filepath, 'w') as f:
                    f.write(b_race_zwo)
                generated_files.append(filepath)
                continue  # Done with B-race day

            # Skip ZWO generation for unavailable days (integrity checker rejects them)
            if use_custom_schedule:
                day_avail = get_day_availability(day_abbrev)
                if day_avail.get('availability') in ('unavailable', 'rest'):
                    continue

            # Get workout template (custom or default)
            if use_custom_schedule:
                workout_template = get_workout_for_day(day_abbrev, phase, week_num)
            else:
                workout_template = phase_workouts.get(day_abbrev)

            if not workout_template:
                continue

            workout_type, description, duration, power = workout_template

            # -----------------------------------------------------------
            # B-RACE OPENER: Day before a B-race gets an easy opener workout
            # Replaces whatever intensity was scheduled.
            # -----------------------------------------------------------
            if is_b_race_opener:
                b_race_info = week.get('b_race', {})
                b_race_name = b_race_info.get('name', 'B-Race')
                workout_type = 'Openers'
                description = f'Pre-race openers for {b_race_name} (B-race tomorrow)'
                duration = min(duration, 40) if duration > 0 else 40  # Cap at 40 min
                power = 0.60

            # -----------------------------------------------------------
            # B-RACE EASY: 2 days before B-race (build/peak only)
            # Reduces intensity to easy riding for mini-taper.
            # -----------------------------------------------------------
            if is_b_race_easy:
                b_race_info = week.get('b_race', {})
                b_race_name = b_race_info.get('name', 'B-Race')
                workout_type = 'Easy'
                description = f'Easy spin - mini-taper for {b_race_name} (B-race in 2 days)'
                duration = min(duration, 45) if duration > 0 else 30
                power = 0.55

            # Generate Rest days as 1-min workouts with personalized instructions
            if workout_type == 'Rest' or duration == 0:
                weeks_to_race = total_weeks - week_num + 1
                rest_description = f"""REST DAY - {athlete_name}

COUNTDOWN: {weeks_to_race} weeks to {race_name}

TODAY'S FOCUS:
- Complete rest from cycling
- Active recovery allowed: walking, light stretching, yoga
- Prioritize sleep (7-9 hours)

RECOVERY CHECKLIST:
- Hydration: 2-3L water minimum
- Nutrition: Quality protein with each meal
- Mobility: 10-15 min light stretching if desired
- Mental: Visualize your race success

PHASE: {phase.upper()}
Week {week_num} of {total_weeks}

Remember: Adaptation happens during rest, not during training.
Trust the process, {athlete_name}."""

                rest_blocks = '    <SteadyState Duration="60" Power="0.30"/>\n'
                rest_content = ZWO_TEMPLATE.format(
                    name=f"{workout_prefix}_Rest",
                    description=rest_description,
                    blocks=rest_blocks
                )
                filepath = zwo_dir / f"{workout_prefix}_Rest.zwo"
                with open(filepath, 'w') as f:
                    f.write(rest_content)
                generated_files.append(filepath)
                continue

            # FTP TEST INJECTION:
            # For custom schedules, find the best available key day for FTP tests
            # FTP test duration comes from constants.py

            def is_day_available_for_ftp(day: str) -> bool:
                """Check if a day has enough time for an FTP test."""
                if not use_custom_schedule:
                    return True
                avail = get_day_availability(day)
                if avail.get('availability') in ('unavailable', 'rest'):
                    return False
                # Check duration - FTP test needs at least FTP_TEST_DURATION_MIN
                max_duration = avail.get('max_duration_min', 120)
                return max_duration >= FTP_TEST_DURATION_MIN

            def get_ftp_day_candidates() -> list:
                """Build FTP day candidates: key days first (excluding long day), then other days.

                The long ride day is excluded — in polarized training the long Z2 ride
                is the single most important workout for durability. FTP tests should
                land on a non-long key day (e.g. interval day or weekend non-long day).
                Falls back to ['Sat', 'Thu', 'Sun'] for non-custom schedules.
                """
                if not use_custom_schedule:
                    return ['Sat', 'Thu', 'Sun']

                key_days = []
                other_days = []
                for d in DAY_ORDER:
                    if d == long_day_abbrev:
                        continue  # Never put FTP test on the long ride day
                    if not is_day_available_for_ftp(d):
                        continue
                    avail = get_day_availability(d)
                    dur = avail.get('max_duration_min', 120)
                    if avail.get('is_key_day_ok', False):
                        key_days.append((d, dur))
                    else:
                        other_days.append((d, dur))
                # Sort each group by max_duration descending
                key_days.sort(key=lambda x: x[1], reverse=True)
                other_days.sort(key=lambda x: x[1], reverse=True)
                return [d for d, _ in key_days] + [d for d, _ in other_days]

            ftp_day_candidates = get_ftp_day_candidates()

            # Week 1 FTP test - prefer key days with most available time
            if week_num == 1 and not ftp_test_week1_added and ftp_day_candidates:
                if day_abbrev == ftp_day_candidates[0] and is_day_available_for_ftp(day_abbrev):
                    workout_type = 'FTP_Test'
                    description = 'The Assessment - Functional Threshold. Establish your baseline FTP to set training zones.'
                    duration = FTP_TEST_DURATION_MIN
                    power = 0.82
                    ftp_test_week1_added = True
            # Pre-build FTP test
            elif first_build_week and week_num == first_build_week - 1 and not ftp_test_prebuild_added and ftp_day_candidates:
                if day_abbrev == ftp_day_candidates[0] and is_day_available_for_ftp(day_abbrev):
                    workout_type = 'FTP_Test'
                    description = 'The Assessment - Functional Threshold. Retest before Build phase to update training zones.'
                    duration = FTP_TEST_DURATION_MIN
                    power = 0.82
                    ftp_test_prebuild_added = True

            if is_race_day:
                # Create RACE DAY PLAN - not a workout, but a race execution guide
                # Pull from fueling.yaml, race data, and training guide
                race_plan_name = f"{workout_prefix}_RACE_DAY_{race_name.replace(' ', '_')}"
                race_filename = f"{race_plan_name}.zwo"

                # Get fueling data (passed via derived or load directly)
                fueling_file = athlete_dir / 'fueling.yaml'
                fueling_data = {}
                if fueling_file.exists():
                    with open(fueling_file, 'r') as f:
                        fueling_data = yaml.safe_load(f) or {}

                race_info = fueling_data.get('race', {})
                carb_info = fueling_data.get('carbohydrates', {})

                duration_hours = race_info.get('duration_hours', 5)
                distance_miles = race_info.get('distance_miles', profile.get('target_race', {}).get('distance_miles', 75))
                hourly_carbs = carb_info.get('hourly_target', 80)
                total_carbs = carb_info.get('total_grams', 400)

                # Estimate TSS (rough: ~60-70 TSS/hour for a hard gravel race)
                estimated_tss = int(duration_hours * 65)

                # Build race day plan description
                race_description = f"""RACE DAY: {race_name}
Date: {day_info['date']}

TARGET METRICS:
- Distance: {distance_miles} miles
- Expected Duration: {duration_hours:.1f} hours
- Estimated TSS: {estimated_tss}

FUELING PLAN:
- Carbs/hour: {hourly_carbs}g (range: {carb_info.get('hourly_range', [70, 90])})
- Total carbs: {total_carbs}g over race
- Start fueling at 20 min, every 20-30 min thereafter
- Pre-race: 100-150g carbs 2-3 hours before start

PACING STRATEGY:
- First 30 min: EASY. Let others burn matches. You're playing the long game.
- Mile 10-40: Find your rhythm. Target G SPOT zone (88-94% FTP) on climbs.
- Final third: This is where you pass people. Increase effort as others fade.
- Technical sections: Smooth > Fast. Avoid mechanicals.

HYDRATION:
- 500-750ml/hour depending on heat
- Start hydrated (clear urine morning of race)
- Don't wait until thirsty

PRE-RACE CHECKLIST:
- [ ] Bike mechanically sound
- [ ] Tires appropriate pressure for conditions
- [ ] Bottles filled with fuel mix
- [ ] Pockets loaded (gels, bars, tool)
- [ ] Electronics charged (computer, lights if needed)
- [ ] Spare tube, CO2, multi-tool
- [ ] Race number attached
- [ ] Drop bags ready (if applicable)

RACE MORNING:
- Wake 3 hours before start
- Breakfast: familiar foods, high carb, low fiber
- Arrive 1 hour early for warmup
- 15 min easy spin warmup with 2-3 openers

GO GET IT, {athlete_name.upper()}!
"""

                # Create a minimal ZWO (TrainingPeaks needs it to be a workout file)
                race_zwo = f"""<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{race_plan_name}</name>
  <description>{race_description}</description>
  <sportType>bike</sportType>
  <workout>
    <FreeRide Duration="{int(duration_hours * 3600)}"/>
  </workout>
</workout_file>"""

                filepath = zwo_dir / race_filename
                with open(filepath, 'w') as f:
                    f.write(race_zwo)
                generated_files.append(filepath)
                continue  # Done with race day

            # Create workout name
            workout_name = f"{workout_prefix}_{workout_type}"
            filename = f"{workout_name}.zwo"

            # Get week within phase from pre-calculated cache (PERFORMANCE)
            week_in_phase = week_in_phase_cache.get(week_num, 1)

            # Build description using v6.0 format with STRUCTURE, PURPOSE, EXECUTION, RPE
            full_description = format_workout_description(workout_type, duration, phase, week_num, day_abbrev)

            # Generate blocks - use Nate generator for key workouts
            # Calculate progression level based on week in plan
            level = calculate_level_from_week(week_num, total_weeks)

            # Map workout types to Nate generator types
            nate_workout_types = {
                'VO2max': 'vo2max',
                'Anaerobic': 'anaerobic',
                'Sprints': 'sprint',
                'Threshold': 'threshold',
            }

            if workout_type in nate_workout_types:
                # Use Nate generator for high-intensity workouts
                nate_type = nate_workout_types[workout_type]
                try:
                    zwo_content = generate_nate_zwo(
                        workout_type=nate_type,
                        level=level,
                        methodology=nate_methodology,
                        workout_name=workout_name
                    )
                    if zwo_content:
                        # Inject personalized header into description
                        weeks_to_race = total_weeks - week_num + 1
                        personal_header = f"{athlete_name} - Week {week_num}/{total_weeks} - {weeks_to_race} weeks to {race_name}\nPhase: {phase.upper()}\n\n"

                        # Add heat training reminder (weeks 4-8 before race)
                        heat_reminder = ""
                        if needs_heat_training and 4 <= weeks_to_race <= 8:
                            heat_reminder = "\nHEAT ACCLIMATION:\n- Add 15-20 min sauna post-workout OR\n- Extra layers during warmup\n- Improves thermoregulation and race performance\n\n"

                        # Insert header after <description> tag
                        zwo_content = zwo_content.replace(
                            '<description>',
                            f'<description>{personal_header}',
                            1
                        )
                        # Insert heat reminder before EXECUTION if applicable
                        if heat_reminder and 'EXECUTION:' in zwo_content:
                            zwo_content = zwo_content.replace('EXECUTION:', f'{heat_reminder}EXECUTION:')

                        # Write the personalized content
                        filepath = zwo_dir / f"{workout_name}.zwo"
                        with open(filepath, 'w') as f:
                            f.write(zwo_content)
                        generated_files.append(filepath)
                        continue  # Skip the standard generation below
                except Exception as e:
                    # Fall back to standard generation if Nate generator fails
                    log.warning(f"Nate generator failed for {workout_type}: {e}, using fallback")

            # Fallback: use progressive generators or standard blocks
            if workout_type in ('Intervals', 'VO2max'):
                # Use progressive interval generator
                blocks, progressive_name = generate_progressive_interval_blocks(
                    phase, week_num, week_in_phase, duration
                )
                # Update description with progressive workout name
                full_description = f"STRUCTURE:\n{progressive_name} - {duration} min\n\n" + \
                    full_description.split('\n\n', 1)[1] if '\n\n' in full_description else full_description
                workout_name = f"{workout_prefix}_{workout_type}_{progressive_name.replace(' ', '_')}"
            elif workout_type == 'Endurance' and phase == 'base':
                # Use varied endurance generator for base phase
                blocks, endurance_name = generate_progressive_endurance_blocks(week_num, duration)
                # Update description with endurance variation name
                full_description = f"STRUCTURE:\n{endurance_name} - {duration} min\n\n" + \
                    full_description.split('\n\n', 1)[1] if '\n\n' in full_description else full_description
            else:
                blocks = create_workout_blocks(duration, power, workout_type)

            if blocks is None:
                continue  # Skip if generator returned None

            filename = f"{workout_name}.zwo"

            # Add personalized header to description
            weeks_to_race = total_weeks - week_num + 1
            personal_header = f"{athlete_name} - Week {week_num}/{total_weeks} - {weeks_to_race} weeks to {race_name}\nPhase: {phase.upper()}\n\n"

            # Add heat training reminder (weeks 4-8 before race)
            heat_reminder = ""
            if needs_heat_training and 4 <= weeks_to_race <= 8:
                heat_reminder = "\n\nHEAT ACCLIMATION:\n- Add 15-20 min sauna post-workout OR\n- Extra layers during warmup\n- Improves thermoregulation and race performance"

            full_description = personal_header + full_description + heat_reminder

            # Create ZWO content
            zwo_content = ZWO_TEMPLATE.format(
                name=workout_name,
                description=full_description,
                blocks=blocks
            )

            # Write file
            filepath = zwo_dir / filename
            with open(filepath, 'w') as f:
                f.write(zwo_content)

            generated_files.append(filepath)

    # Generate strength workouts - respect athlete availability
    strength_sessions = profile.get('strength', {}).get('sessions_per_week', 2) if profile else 2
    strength_enabled = config.get('workouts.strength.enabled', True)

    if strength_sessions > 0 and strength_enabled:
        strength_dir = zwo_dir

        # Find days suitable for strength workouts based on athlete schedule
        # CRITICAL: Strength days must be separated by at least 1 day for recovery
        # CRITICAL: Don't put strength on the same day as FTP tests or very hard workouts
        def get_strength_days() -> list:
            """
            Find appropriate days for strength workouts.

            Rules:
            1. Days must be separated (Mon/Wed, Mon/Thu, Tue/Thu, Tue/Fri - NOT Wed/Thu)
            2. Avoid days with FTP tests
            3. Prefer easy/recovery bike days for strength
            4. If athlete specified strength_only_days, use those
            """
            # Check for athlete-specified strength days
            if strength_only_abbrevs:
                return strength_only_abbrevs[:2]

            # Good pairings with 1+ day gap:
            # Mon/Wed, Mon/Thu, Tue/Thu, Tue/Fri, Wed/Fri
            valid_pairings = [
                ['Tue', 'Thu'],  # Best: easy days in our schedule (Tue is easy, Thu is quality but not FTP)
                ['Mon', 'Thu'],  # Good: quality day + quality day with gap
                ['Tue', 'Fri'],  # Good: easy day + quality day
                ['Mon', 'Wed'],  # OK: two quality days early week
                ['Wed', 'Fri'],  # OK: mid-week + end-week
            ]

            # Tue/Thu is best because Tue is an easy day in our weekly structure
            # This puts strength on a recovery day, not stacking with hard bike
            return ['Tue', 'Thu']

        strength_days = get_strength_days()

        # Track which days have FTP tests (don't schedule strength on these)
        ftp_test_days = set()
        for week in weeks:
            week_num = week['week']
            # FTP tests are typically in Week 1 and pre-Build week
            if week_num == 1:
                # Week 1 FTP test is usually Thursday
                ftp_test_days.add((week_num, 'Thu'))
            # Check if this is the week before Build phase starts
            if week.get('phase') == 'base':
                next_week_idx = weeks.index(week) + 1
                if next_week_idx < len(weeks) and weeks[next_week_idx].get('phase') == 'build':
                    ftp_test_days.add((week_num, 'Thu'))

        for week in weeks:
            week_num = week['week']
            phase = week['phase']

            # Skip strength during taper and race weeks (use STRENGTH_PHASES from constants)
            if phase not in STRENGTH_PHASES:
                continue

            for session in range(1, min(strength_sessions + 1, 3)):  # Max 2 sessions
                strength_blocks, strength_workout = generate_strength_zwo(week_num, session)

                # Use athlete-appropriate strength day
                strength_day = strength_days[session - 1] if session <= len(strength_days) else strength_days[0]

                # Skip strength if this day has an FTP test
                if (week_num, strength_day) in ftp_test_days:
                    continue  # Don't add strength on FTP test day

                # Get the date for this strength day from the week's days list
                date_short = ""
                for day_info in week.get('days', []):
                    if day_info['day'] == strength_day:
                        date_short = day_info['date_short']
                        break

                workout_name = f"W{week_num:02d}_{strength_day}_{date_short}_Strength_{strength_workout['name'].replace(' ', '_')}"
                filename = f"{workout_name}.zwo"

                # Build description with exercises and video links
                exercises_lines = []
                for ex, reps in strength_workout['exercises']:
                    video_url = get_video_url(ex)
                    if video_url:
                        exercises_lines.append(f"- {ex} - {reps}\n  Video: {video_url}")
                    else:
                        exercises_lines.append(f"- {ex} - {reps}")
                exercises_text = '\n'.join(exercises_lines)
                full_description = f"FOCUS: {strength_workout['focus']}\n\nEXERCISES:\n{exercises_text}\n\nEXECUTION:\nComplete all sets with good form. Rest 60-90 sec between sets."

                zwo_content = ZWO_TEMPLATE.format(
                    name=workout_name,
                    description=full_description,
                    blocks=strength_blocks
                )

                filepath = strength_dir / filename
                with open(filepath, 'w') as f:
                    f.write(zwo_content)

                generated_files.append(filepath)

    return generated_files


def generate_athlete_package(athlete_id: str) -> dict:
    """Generate complete training package for an athlete."""

    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id

    if not athlete_dir.exists():
        error(f"Athlete directory not found: {athlete_dir}")
        return {'success': False, 'error': 'Athlete not found'}

    header(f"GENERATING TRAINING PACKAGE: {athlete_id}")

    # Step 0: Pre-generation validation
    step(0, "Running pre-generation validation...")
    validation_result = validate_athlete_data(athlete_dir)

    if validation_result.warnings:
        for warn in validation_result.warnings:
            warning(warn)

    if not validation_result.is_valid:
        for err in validation_result.errors:
            error(err)
        error("Pre-generation validation failed - fix errors before generating")
        return {'success': False, 'error': 'Validation failed', 'errors': validation_result.errors}

    success("Validation passed")

    # Load all athlete data
    step(1, "Loading athlete data...")
    profile = load_yaml(athlete_dir / 'profile.yaml')
    derived = load_yaml(athlete_dir / 'derived.yaml')
    methodology = load_yaml(athlete_dir / 'methodology.yaml')
    fueling = load_yaml(athlete_dir / 'fueling.yaml')
    plan_dates = load_yaml(athlete_dir / 'plan_dates.yaml')

    # Validate required files (already done by pre-generation, but double-check)
    missing = []
    if not profile: missing.append('profile.yaml')
    if not derived: missing.append('derived.yaml')
    if not methodology: missing.append('methodology.yaml')
    if not fueling: missing.append('fueling.yaml')
    if not plan_dates: missing.append('plan_dates.yaml')

    if missing:
        error(f"Missing required files: {missing}")
        return {'success': False, 'error': f'Missing files: {missing}'}

    athlete_name = profile.get('name', 'Athlete')
    race_name = profile.get('target_race', {}).get('name', 'Race')
    race_date = plan_dates.get('race_date', '')
    plan_weeks = plan_dates.get('plan_weeks', 0)

    detail(f"Athlete: {athlete_name}")
    detail(f"Race: {race_name} ({race_date})")
    detail(f"Plan: {plan_weeks} weeks")
    detail(f"Methodology: {methodology.get('selected_methodology', 'Unknown')}")

    # Race data loading is optional - guide generator gets info from profile
    step(2, "Checking race data...")
    race_id = profile.get('target_race', {}).get('race_id', '')

    # Try to load race data if available, but don't fail if missing
    race_data = None
    if GUIDES_DIR:
        race_data_path = GUIDES_DIR / 'race_data' / f'{race_id}.json'
        if race_data_path.exists():
            race_data = load_json(race_data_path)
            detail(f"Loaded: {race_data_path.name}")
        else:
            detail(f"Race data file not found ({race_id}.json) - using profile data")

    # Build athlete_data dict for guide generator
    athlete_data = {
        'profile': profile,
        'derived': derived,
        'methodology': methodology,
        'fueling': fueling,
        'plan_dates': plan_dates
    }

    # Generate training guide
    step(3, "Generating training guide...")
    guide_path = athlete_dir / 'training_guide.html'

    # Use local HTML guide generator
    generate_html_guide(athlete_id, output_path=guide_path)

    # Generate ZWO workout files
    step(4, "Generating ZWO workout files...")
    zwo_files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    detail(f"Generated {len(zwo_files)} workout files")

    # Generate plan summary
    step(5, "Generating plan summary...")
    tier_name = derived.get('tier', 'FINISHER').upper()
    ability_level = derived.get('ability_level', 'Intermediate')

    summary = {
        'athlete_id': athlete_id,
        'athlete_name': athlete_name,
        'generated_date': datetime.now().isoformat(),
        'race': {
            'name': race_name,
            'date': race_date,
            'distance_miles': profile.get('target_race', {}).get('distance_miles'),
        },
        'plan': {
            'weeks': plan_weeks,
            'start_date': plan_dates.get('plan_start'),
            'end_date': plan_dates.get('plan_end'),
            'methodology': methodology.get('selected_methodology'),
            'methodology_score': methodology.get('score'),
            'tier': tier_name,
            'ability_level': ability_level,
        },
        'fueling': {
            'hourly_carb_target': fueling.get('carbohydrates', {}).get('hourly_target'),
            'total_carbs': fueling.get('carbohydrates', {}).get('total_grams'),
            'estimated_duration_hours': fueling.get('race', {}).get('duration_hours'),
        },
        'files': {
            'guide': str(guide_path),
            'workouts_dir': str(athlete_dir / 'workouts'),
            'workout_count': len(zwo_files),
        }
    }

    summary_path = athlete_dir / 'plan_summary.yaml'
    with open(summary_path, 'w') as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    detail(f"Saved: {summary_path}")

    # Final summary
    header("PACKAGE GENERATION COMPLETE")
    log.info(f"Output directory: {athlete_dir}")
    log.info(f"Training guide: training_guide.html")
    log.info(f"Workouts: workouts/ ({len(zwo_files)} files)")
    log.info(f"Summary: plan_summary.yaml")

    # List first few workouts
    if zwo_files:
        log.subheader("Sample workouts")
        for f in sorted(zwo_files)[:5]:
            detail(f"- {f.name}")
        if len(zwo_files) > 5:
            detail(f"... and {len(zwo_files) - 5} more")

    return {
        'success': True,
        'athlete_dir': str(athlete_dir),
        'guide_path': str(guide_path),
        'workout_count': len(zwo_files),
        'summary': summary
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_athlete_package.py <athlete_id>")
        sys.exit(1)

    athlete_id = sys.argv[1]
    result = generate_athlete_package(athlete_id)

    sys.exit(0 if result.get('success') else 1)
