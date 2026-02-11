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

from guide_generator import generate_guide
from workout_library import (
    WorkoutLibrary,
    generate_progressive_interval_blocks,
    generate_progressive_endurance_blocks,
    generate_strength_zwo,
)

# Get logger
log = get_logger()


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

    description = f"""• STRUCTURE:
{structure}

• PURPOSE:
{purpose}

• EXECUTION:
{execution}

• RPE:
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
        if is_key_day:
            week_workout_tracker['hard_days'].append(day_abbrev)
            template = phase_templates.get('key_cardio')
            return cap_duration(template, max_duration)

        # For LIMITED or AVAILABLE days without key_day flag:
        # Distribute workouts with proper zone variety
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_idx = day_order.index(day_abbrev) if day_abbrev in day_order else 0
        prev_day = day_order[day_idx - 1] if day_idx > 0 else None

        # Check if previous day was hard
        prev_was_hard = prev_day in week_workout_tracker['hard_days']

        # Increment workout counter for variety
        week_workout_tracker['workout_count'] += 1
        workout_num = week_workout_tracker['workout_count']

        # Determine workout based on phase, recovery needs, and variety
        if prev_was_hard:
            # Easy day after hard day - Z1/Z2
            template = phase_templates.get('easy', ('Recovery', 'Easy spin', 30, 0.50))
        else:
            # Can do a harder workout - distribute zones based on phase
            week_workout_tracker['hard_days'].append(day_abbrev)

            if phase == 'base':
                # Base phase: Mostly Z2, introduce Z3 (tempo)
                # Pattern: Endurance, Tempo, Endurance, Tempo...
                if workout_num % 3 == 0:
                    template = phase_templates.get('tempo', ('Tempo', 'Tempo: 2x10min @ 85% FTP', 50, 0.72))
                else:
                    template = phase_templates.get('moderate', ('Endurance', 'Zone 2 steady state', 45, 0.65))

            elif phase == 'build':
                # Build phase: Z3/Z4 focus, introduce Z5
                # Pattern: Sweet Spot, Threshold, VO2max, Tempo...
                cycle = workout_num % 4
                if cycle == 0:
                    template = phase_templates.get('vo2max', ('VO2max', 'VO2max: 4x3min @ 110% FTP', 50, 0.80))
                elif cycle == 1:
                    template = phase_templates.get('key_cardio', ('Threshold', 'Threshold: 3x10min @ 95% FTP', 55, 0.78))
                elif cycle == 2:
                    template = phase_templates.get('moderate', ('Sweet_Spot', 'Sweet spot: 3x12min @ 88% FTP', 55, 0.75))
                else:
                    template = phase_templates.get('tempo', ('Tempo', 'Tempo: 2x15min @ 85% FTP', 50, 0.72))

            elif phase == 'peak':
                # Peak phase: Z5/Z6/Z7 emphasis - race-specific power
                # Pattern: VO2max, Threshold, Anaerobic, VO2max...
                cycle = workout_num % 4
                if cycle == 0:
                    template = phase_templates.get('vo2max', ('VO2max', 'VO2max: 5x3min @ 115% FTP', 50, 0.82))
                elif cycle == 1:
                    template = phase_templates.get('anaerobic', ('Anaerobic', 'Anaerobic: 8x30sec @ 150% FTP', 45, 0.70))
                elif cycle == 2:
                    template = phase_templates.get('moderate', ('Threshold', 'Threshold: 2x15min @ 100% FTP', 50, 0.78))
                else:
                    template = phase_templates.get('key_cardio', ('VO2max', 'VO2max: 4x4min @ 110% FTP', 55, 0.80))

            elif phase == 'taper':
                # Taper: Reduce volume, maintain intensity with openers
                if workout_num % 2 == 0:
                    template = phase_templates.get('vo2max', ('Openers', 'VO2 openers: 3x2min @ 110% FTP', 40, 0.65))
                else:
                    template = phase_templates.get('anaerobic', ('Sprints', 'Sprint openers: 4x15sec all-out', 35, 0.55))

            elif phase == 'race':
                # Race week: Minimal, just activation
                template = phase_templates.get('easy', ('Easy', 'Easy spin', 30, 0.50))

            elif phase == 'maintenance':
                # Maintenance: Keep all systems ticking
                cycle = workout_num % 3
                if cycle == 0:
                    template = phase_templates.get('vo2max', ('Threshold', 'Threshold touch: 2x8min @ 95% FTP', 45, 0.72))
                elif cycle == 1:
                    template = phase_templates.get('tempo', ('Tempo', 'Tempo: 2x12min @ 85% FTP', 45, 0.70))
                else:
                    template = phase_templates.get('moderate', ('Endurance', 'Zone 2 maintenance', 50, 0.62))
            else:
                # Default: moderate effort
                template = phase_templates.get('moderate', ('Endurance', 'Zone 2', 45, 0.62))

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
            blocks = []  # Reset blocks, we handle warmup/cooldown ourselves
            # 12m progressive warmup (45% -> 70%)
            blocks.append('    <Warmup Duration="720" PowerLow="0.45" PowerHigh="0.70"/>')
            # 5m @ RPE 6/10 (~80% FTP)
            blocks.append('    <SteadyState Duration="300" Power="0.80">')
            blocks.append('      <textevent timeoffset="0" message="5 minutes at RPE 6/10 - moderate effort"/>')
            blocks.append('    </SteadyState>')
            # 5m easy recovery (50%)
            blocks.append('    <SteadyState Duration="300" Power="0.50">')
            blocks.append('      <textevent timeoffset="0" message="5 minutes easy - recover before the blowout"/>')
            blocks.append('    </SteadyState>')
            # 5m blowout @ RPE 8-10 (~105% FTP) - go hard, find your legs
            blocks.append('    <SteadyState Duration="300" Power="1.05">')
            blocks.append('      <textevent timeoffset="0" message="5 min BLOWOUT - go hard! Start firm, adjust up or down"/>')
            blocks.append('      <textevent timeoffset="120" message="Find your rhythm - this clears the cobwebs before the test"/>')
            blocks.append('    </SteadyState>')
            # 5m easy recovery (50%)
            blocks.append('    <SteadyState Duration="300" Power="0.50">')
            blocks.append('      <textevent timeoffset="0" message="5 minutes easy - full recovery before the 20-minute test"/>')
            blocks.append('      <textevent timeoffset="240" message="Get ready. 20 minutes ALL OUT coming up."/>')
            blocks.append('    </SteadyState>')
            # 20m ALL OUT - FTP test (target ~100% but athlete should go by feel)
            blocks.append('    <FreeRide Duration="1200">')
            blocks.append('      <textevent timeoffset="0" message="20 MINUTES ALL OUT. Start conservatively at 8/10 RPE. 20 minutes is a LONG time."/>')
            blocks.append('      <textevent timeoffset="120" message="Settle into your rhythm. Find a pace you can hold for the full 20 minutes."/>')
            blocks.append('      <textevent timeoffset="300" message="5 minutes down. 15 to go. Stay steady, don\'t surge."/>')
            blocks.append('      <textevent timeoffset="600" message="Halfway! You\'re doing great. Maintain your effort."/>')
            blocks.append('      <textevent timeoffset="900" message="5 minutes left. Now you can start to push if you have anything left."/>')
            blocks.append('      <textevent timeoffset="1080" message="Final 2 minutes! Give it everything you have left."/>')
            blocks.append('    </FreeRide>')
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
            easy_start = int(main_duration * 0.1) * 60
            blocks.append(f'    <SteadyState Duration="{easy_start}" Power="0.62"/>')
            # 3 sets of 8 min (2min under @ 95%, 1min over @ 105%, repeat)
            for i in range(3):
                blocks.append('    <SteadyState Duration="120" Power="0.95">')
                blocks.append(f'      <textevent timeoffset="0" message="Under - 95% FTP, find your rhythm"/>')
                blocks.append('    </SteadyState>')
                blocks.append('    <SteadyState Duration="60" Power="1.05">')
                blocks.append(f'      <textevent timeoffset="0" message="OVER - 105% FTP, push through!"/>')
                blocks.append('    </SteadyState>')
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

            # Get workout template (custom or default)
            if use_custom_schedule:
                workout_template = get_workout_for_day(day_abbrev, phase, week_num)
            else:
                workout_template = phase_workouts.get(day_abbrev)

            if not workout_template:
                continue

            workout_type, description, duration, power = workout_template

            # Skip rest days and unavailable days FIRST (before FTP injection)
            if workout_type == 'Rest' or duration == 0:
                # But track if we're skipping a potential FTP test day
                if week_num == 1 and day_abbrev == 'Fri':
                    # FTP test needs alternate day - will use Thu or Sat
                    pass
                continue

            # FTP TEST INJECTION:
            # For custom schedules, find the best available key day for FTP tests
            # FTP test duration comes from constants.py

            def is_day_available_for_ftp(day: str) -> bool:
                """Check if a day has enough time for an FTP test."""
                if not use_custom_schedule:
                    return True
                avail = get_day_availability(day)
                if avail.get('availability') == 'unavailable':
                    return False
                if not avail.get('is_key_day_ok', True):
                    return False
                # Check duration - FTP test needs at least FTP_TEST_DURATION_MIN
                max_duration = avail.get('max_duration_min', 120)
                return max_duration >= FTP_TEST_DURATION_MIN

            # Week 1 FTP test - prefer days with enough time (Sun > Sat > Thu)
            if week_num == 1 and not ftp_test_week1_added:
                # Order by typical max duration (Sun usually has most time)
                ftp_day_candidates = ['Sun', 'Sat', 'Thu']
                if day_abbrev in ftp_day_candidates and is_day_available_for_ftp(day_abbrev):
                    workout_type = 'FTP_Test'
                    description = 'The Assessment - Functional Threshold. Establish your baseline FTP to set training zones.'
                    duration = FTP_TEST_DURATION_MIN
                    power = 0.82
                    ftp_test_week1_added = True
            # Pre-build FTP test
            elif first_build_week and week_num == first_build_week - 1 and not ftp_test_prebuild_added:
                ftp_day_candidates = ['Sun', 'Sat', 'Thu']
                if day_abbrev in ftp_day_candidates and is_day_available_for_ftp(day_abbrev):
                    workout_type = 'FTP_Test'
                    description = 'The Assessment - Functional Threshold. Retest before Build phase to update training zones.'
                    duration = FTP_TEST_DURATION_MIN
                    power = 0.82
                    ftp_test_prebuild_added = True

            if is_race_day:
                continue  # Skip race day

            # Create workout name
            workout_name = f"{workout_prefix}_{workout_type}"
            filename = f"{workout_name}.zwo"

            # Get week within phase from pre-calculated cache (PERFORMANCE)
            week_in_phase = week_in_phase_cache.get(week_num, 1)

            # Build description using v6.0 format with STRUCTURE, PURPOSE, EXECUTION, RPE
            full_description = format_workout_description(workout_type, duration, phase, week_num, day_abbrev)

            # Generate blocks - use progressive generators for intervals
            if workout_type in ('Intervals', 'VO2max'):
                # Use progressive interval generator
                blocks, progressive_name = generate_progressive_interval_blocks(
                    phase, week_num, week_in_phase, duration
                )
                # Update description with progressive workout name
                full_description = f"• STRUCTURE:\n{progressive_name} - {duration} min\n\n" + \
                    full_description.split('\n\n', 1)[1] if '\n\n' in full_description else full_description
                workout_name = f"{workout_prefix}_{workout_type}_{progressive_name.replace(' ', '_')}"
            elif workout_type == 'Endurance' and phase == 'base':
                # Use varied endurance generator for base phase
                blocks, endurance_name = generate_progressive_endurance_blocks(week_num, duration)
                # Update description with endurance variation name
                full_description = f"• STRUCTURE:\n{endurance_name} - {duration} min\n\n" + \
                    full_description.split('\n\n', 1)[1] if '\n\n' in full_description else full_description
            else:
                blocks = create_workout_blocks(duration, power, workout_type)

            if blocks is None:
                continue  # Skip if generator returned None

            filename = f"{workout_name}.zwo"

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
        # Prefer days marked as 'limited' or days that aren't key workout days
        def get_strength_days() -> list:
            """Find appropriate days for strength workouts based on athlete availability."""
            if not use_custom_schedule:
                return ['Wed', 'Thu']  # Default days

            suitable_days = []
            # Priority order: strength_only_days > limited availability > non-key days
            for day_full, prefs in preferred_days.items():
                if not isinstance(prefs, dict):
                    continue
                day_abbrev = DAY_FULL_TO_ABBREV.get(day_full.lower())
                if not day_abbrev:
                    continue

                availability = prefs.get('availability', 'available')
                is_key_ok = prefs.get('is_key_day_ok', True)
                workout_type = prefs.get('workout_type', '')

                # Skip rest/unavailable days
                if availability in ('rest', 'unavailable'):
                    continue

                # Prefer strength-only days first
                if workout_type == 'strength_only' or day_abbrev in strength_only_abbrevs:
                    suitable_days.insert(0, day_abbrev)
                # Then limited availability days (good for shorter strength sessions)
                elif availability == 'limited' and not is_key_ok:
                    suitable_days.append(day_abbrev)
                # Then non-key days
                elif not is_key_ok:
                    suitable_days.append(day_abbrev)

            # Return at least 2 days, filling with defaults if needed
            if len(suitable_days) < 2:
                defaults = ['Wed', 'Thu', 'Mon', 'Fri']
                for d in defaults:
                    if d not in suitable_days and len(suitable_days) < 2:
                        suitable_days.append(d)

            return suitable_days[:2]

        strength_days = get_strength_days()

        for week in weeks:
            week_num = week['week']
            phase = week['phase']

            # Skip strength during taper and race weeks (use STRENGTH_PHASES from constants)
            if phase not in STRENGTH_PHASES:
                continue

            for session in range(1, min(strength_sessions + 1, 3)):  # Max 2 sessions
                strength_blocks, strength_name = generate_strength_zwo(week_num, session)

                # Use athlete-appropriate strength day
                strength_day = strength_days[session - 1] if session <= len(strength_days) else strength_days[0]

                workout_name = f"W{week_num:02d}_{strength_day}_Strength_{strength_name.replace(' ', '_')}"
                filename = f"{workout_name}.zwo"

                full_description = f"Week {week_num} Strength Session {session}\n\n{strength_name}"

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

    # Find race data file
    step(2, "Loading race data...")
    race_id = profile.get('target_race', {}).get('race_id', '')

    if not GUIDES_DIR:
        error("Guides directory not configured. Check config.yaml paths.guides_repo")
        return {'success': False, 'error': 'Guides directory not configured'}

    race_data_path = GUIDES_DIR / 'race_data' / f'{race_id}.json'

    if not race_data_path.exists():
        race_files = list((GUIDES_DIR / 'race_data').glob('*.json'))
        error(f"Race data not found at {race_data_path}")
        detail(f"Available race files: {[f.name for f in race_files]}")
        detail(f"Please create {race_id}.json in {GUIDES_DIR / 'race_data'}/")
        detail(f"Or update profile.yaml race_id to match an existing file.")
        return {'success': False, 'error': f'Race data file not found: {race_id}.json'}

    race_data = load_json(race_data_path)
    detail(f"Loaded: {race_data_path.name}")

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

    tier_name = derived.get('tier', 'FINISHER').upper()
    ability_level = derived.get('ability_level', 'Intermediate')

    generate_guide(
        race_data=race_data,
        tier_name=tier_name,
        ability_level=ability_level,
        output_path=str(guide_path),
        athlete_data=athlete_data
    )

    # Generate ZWO workout files
    step(4, "Generating ZWO workout files...")
    zwo_files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)
    detail(f"Generated {len(zwo_files)} workout files")

    # Generate plan summary
    step(5, "Generating plan summary...")
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
