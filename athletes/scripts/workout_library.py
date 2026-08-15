#!/usr/bin/env python3
"""
Workout library with progressive variations.

Provides varied workout structures that progress across the training plan.
No more identical workouts week after week.
"""

from typing import Dict, List, Optional, Tuple
import random


class WorkoutLibrary:
    """Library of workout variations with progression."""

    # Interval workout progressions
    # Each tuple: (name, intervals, on_duration_sec, off_duration_sec, on_power, off_power)
    INTERVAL_PROGRESSIONS = {
        'build': [
            # Week 1-2: Intro to intensity
            ('Tempo Intervals', 3, 600, 300, 0.88, 0.55),  # 3x10min @ 88%
            ('Sweet Spot Blocks', 2, 900, 300, 0.90, 0.55),  # 2x15min @ 90%
            # Week 3-4: Building
            ('Threshold Builders', 3, 600, 300, 0.95, 0.55),  # 3x10min @ 95%
            ('Over-Unders', 4, 480, 240, 0.95, 0.85),  # 4x8min alternating
            # Week 5+: Full intensity
            ('Threshold Classics', 3, 720, 300, 0.95, 0.55),  # 3x12min @ 95%
            ('Race Pace Blocks', 4, 600, 300, 0.92, 0.55),  # 4x10min @ 92%
        ],
        'peak': [
            # VO2max progressions
            ('VO2 Starters', 4, 180, 180, 1.08, 0.50),  # 4x3min @ 108%
            ('VO2 Builders', 5, 180, 180, 1.10, 0.50),  # 5x3min @ 110%
            ('VO2 Classics', 5, 240, 180, 1.10, 0.50),  # 5x4min @ 110%
            ('VO2 Extended', 4, 300, 240, 1.08, 0.50),  # 4x5min @ 108%
            ('VO2 Race Prep', 6, 180, 150, 1.12, 0.50),  # 6x3min @ 112%
        ],
    }

    # Endurance workout progressions (Z2 with variations)
    ENDURANCE_PROGRESSIONS = [
        # (name, structure_type, description)
        ('Z2 Steady', 'steady', 'Consistent Zone 2 effort'),
        ('Z2 Cadence', 'cadence', 'Zone 2 with cadence drills every 10 minutes'),
        ('Z2 Single Leg', 'drills', 'Zone 2 with single leg focus drills'),
        ('Z2 Big Gear', 'strength', 'Zone 2 with big gear low cadence intervals'),
        ('Z2 Spin Ups', 'spinups', 'Zone 2 with high cadence spin-ups'),
        ('Z2 Tempo Touch', 'tempo_touch', 'Zone 2 with brief tempo surges'),
    ]

    # Long ride progressions
    LONG_RIDE_PROGRESSIONS = {
        'base': [
            ('Endurance Builder', 0.65, 0.0, 'Pure Zone 2 endurance'),
            ('Aerobic Foundation', 0.65, 0.0, 'Building aerobic base'),
            ('Long & Steady', 0.65, 0.0, 'Consistent pacing practice'),
        ],
        'build': [
            ('Race Simulation Lite', 0.65, 0.80, '70% Z2, 30% tempo'),
            ('Sustained Effort', 0.65, 0.85, 'Z2 with tempo blocks'),
            ('Progressive Long', 0.65, 0.82, 'Build intensity through ride'),
        ],
        'peak': [
            ('Race Rehearsal', 0.65, 0.85, 'Full race simulation'),
            ('Over-Distance', 0.65, 0.80, 'Beyond race distance at moderate pace'),
            ('Specificity Ride', 0.68, 0.88, 'Race-specific terrain simulation'),
        ],
    }

    # Strength workout templates
    STRENGTH_WORKOUTS = [
        {
            'name': 'Foundation Strength A',
            'focus': 'Lower body + core',
            'exercises': [
                ('Goblet Squat', '3x12'),
                ('Romanian Deadlift', '3x10'),
                ('Step Ups', '3x10 each'),
                ('Plank', '3x45sec'),
                ('Dead Bug', '3x10 each'),
                ('Glute Bridge', '3x15'),
            ],
        },
        {
            'name': 'Foundation Strength B',
            'focus': 'Upper body + core',
            'exercises': [
                ('Push Ups', '3x12'),
                ('Bent Over Row', '3x12'),
                ('Single Leg Deadlift', '3x8 each'),
                ('Side Plank', '3x30sec each'),
                ('Bird Dog', '3x10 each'),
                ('Hip Flexor Stretch', '2x30sec each'),
            ],
        },
        {
            'name': 'Power Development',
            'focus': 'Explosive power',
            'exercises': [
                ('Jump Squat', '3x8'),
                ('Box Step Up (fast)', '3x10 each'),
                ('Medicine Ball Slam', '3x10'),
                ('Single Leg Hop', '3x8 each'),
                ('Plank to Push Up', '3x8'),
                ('Lateral Lunge', '3x10 each'),
            ],
        },
        {
            'name': 'Cycling-Specific',
            'focus': 'Cycling muscles',
            'exercises': [
                ('Bulgarian Split Squat', '3x10 each'),
                ('Calf Raises', '3x15'),
                ('Hip Hinge', '3x12'),
                ('Copenhagen Plank', '3x20sec each'),
                ('Superman Hold', '3x30sec'),
                ('Foam Roll IT Band', '2x60sec each'),
            ],
        },
        {
            'name': 'Mobility and Stability',
            'focus': 'Recovery and flexibility',
            'exercises': [
                ('Cat-Cow', '2x10'),
                ('World\'s Greatest Stretch', '2x5 each'),
                ('90-90 Hip Stretch', '2x30sec each'),
                ('Thoracic Rotation', '2x10 each'),
                ('Ankle Circles', '2x10 each'),
                ('Pigeon Pose', '2x45sec each'),
            ],
        },
    ]

    # Full-gym sessions intentionally live beside, rather than replace, the
    # long-standing home-basic library above.  A customer who selected
    # home-basic keeps that exact dumbbell/bodyweight rotation; only an
    # explicit full-gym answer receives barbell/trap-bar programming.
    _FULL_GYM_PROGRAMS = {
        'anatomical_adaptation': {
            'title': 'Anatomical Adaptation', 'duration_min': 45,
            'focus': 'Build durable movement patterns with submaximal compound lifts',
            'sessions': [
                [
                    ('Back Squat', '3x10 @ RPE6 — leave 4 reps in reserve'),
                    ('Romanian Deadlift', '3x10 @ RPE6 — leave 4 reps in reserve'),
                    ('Barbell Hip Thrust', '3x10 @ RPE6 — leave 4 reps in reserve'),
                    ('Pallof Press', '3x10 each @ light, controlled effort — leave 4 reps in reserve'),
                ],
                [
                    ('Trap Bar Deadlift', '3x8 @ RPE6 — leave 4 reps in reserve'),
                    ('Bulgarian Split Squat', '3x8 each @ RPE6 — leave 4 reps in reserve'),
                    ('Barbell Bench Press', '3x10 @ RPE6 — leave 4 reps in reserve'),
                    ('Bent Over Row', '3x10 @ RPE6 — leave 4 reps in reserve'),
                ],
            ],
        },
        'max_strength': {
            'title': 'Max Strength', 'duration_min': 45,
            'focus': 'Build force with controlled, non-grinding compound lifts',
            'sessions': [
                [
                    ('Back Squat', '4x6 @ RPE7 — leave 2 reps in reserve'),
                    ('Romanian Deadlift', '3x8 @ RPE7 — leave 2 reps in reserve'),
                    ('Barbell Hip Thrust', '3x8 @ RPE7 — leave 2 reps in reserve'),
                    ('Pallof Press', '3x10 each @ moderate effort — leave 2 reps in reserve'),
                ],
                [
                    ('Trap Bar Deadlift', '4x5 @ RPE7 — leave 2 reps in reserve'),
                    ('Bulgarian Split Squat', '3x6 each @ RPE7 — leave 2 reps in reserve'),
                    ('Barbell Bench Press', '3x6 @ RPE7 — leave 2 reps in reserve'),
                    ('Bent Over Row', '3x8 @ RPE7 — leave 2 reps in reserve'),
                ],
            ],
        },
        'maintenance': {
            'title': 'Maintenance', 'duration_min': 40,
            'focus': 'Keep strength while preserving freshness for cycling quality',
            'sessions': [
                [
                    ('Back Squat', '3x5 @ RPE7 — leave 2 reps in reserve'),
                    ('Romanian Deadlift', '3x6 @ RPE7 — leave 2 reps in reserve'),
                    ('Pallof Press', '3x8 each @ moderate effort — leave 2 reps in reserve'),
                ],
                [
                    ('Trap Bar Deadlift', '3x5 @ RPE7 — leave 2 reps in reserve'),
                    ('Barbell Hip Thrust', '3x6 @ RPE7 — leave 2 reps in reserve'),
                    ('Bent Over Row', '3x8 @ RPE7 — leave 2 reps in reserve'),
                ],
            ],
        },
        'power': {
            'title': 'Power', 'duration_min': 35,
            'focus': 'Express existing strength with fast, controlled compound lifts',
            'sessions': [
                [
                    ('Back Squat', '3x3 @ 55-65% 1RM, RPE6 — drive the concentric fast; lower under control'),
                    ('Romanian Deadlift', '3x4 @ 55-65% 1RM, RPE6 — stand fast; lower under control'),
                    ('Barbell Hip Thrust', '3x4 @ 55-65% 1RM, RPE6 — drive the concentric fast; lower under control'),
                    ('Pallof Press', '2x8 each @ light, controlled effort'),
                ],
                [
                    ('Trap Bar Deadlift', '3x3 @ 55-65% 1RM, RPE6 — stand fast; lower under control'),
                    ('Bulgarian Split Squat', '3x4 each @ 55-65% 1RM, RPE6 — drive up fast; lower under control'),
                    ('Barbell Bench Press', '3x4 @ 55-65% 1RM, RPE6 — press fast; lower under control'),
                    ('Bent Over Row', '2x6 @ moderate, controlled effort'),
                ],
            ],
        },
        'deload': {
            'title': 'Deload', 'duration_min': 30,
            'focus': 'Rehearse the movement patterns with intentionally easy loads',
            'sessions': [
                [
                    ('Back Squat', '2x8 @ RPE5 — leave 5 reps in reserve'),
                    ('Romanian Deadlift', '2x8 @ RPE5 — leave 5 reps in reserve'),
                    ('Pallof Press', '2x8 each @ easy effort — leave 5 reps in reserve'),
                ],
                [
                    ('Trap Bar Deadlift', '2x6 @ RPE5 — leave 5 reps in reserve'),
                    ('Barbell Hip Thrust', '2x8 @ RPE5 — leave 5 reps in reserve'),
                    ('Bent Over Row', '2x8 @ RPE5 — leave 5 reps in reserve'),
                ],
            ],
        },
    }

    _BODYWEIGHT_PROGRAMS = {
        'title': 'Bodyweight Strength', 'duration_min': 30,
        'focus': 'Maintain movement quality without external load',
        'sessions': [
            [
                ('Bodyweight Squat', '3x12 @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Single-Leg Glute Bridge', '3x10 each @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Push-Up', '3x8 @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Dead Bug', '3x10 each @ controlled bodyweight effort — leave 3 reps in reserve'),
            ],
            [
                ('Reverse Lunge', '3x8 each @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Single-Leg Calf Raise', '3x12 each @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Bird Dog', '3x10 each @ controlled bodyweight effort — leave 3 reps in reserve'),
                ('Side Plank', '3x30sec each @ controlled bodyweight effort — leave 3 reps in reserve'),
            ],
        ],
    }

    @classmethod
    def get_interval_workout(cls, phase: str, week_in_phase: int) -> Dict:
        """Get appropriate interval workout for the phase and week."""
        progressions = cls.INTERVAL_PROGRESSIONS.get(phase, cls.INTERVAL_PROGRESSIONS['build'])

        # Cycle through progressions based on week
        idx = (week_in_phase - 1) % len(progressions)
        name, repeats, on_dur, off_dur, on_power, off_power = progressions[idx]

        return {
            'name': name,
            'intervals': repeats,
            'on_duration': on_dur,
            'off_duration': off_dur,
            'on_power': on_power,
            'off_power': off_power,
        }

    @classmethod
    def get_endurance_workout(cls, week_num: int) -> Dict:
        """Get varied endurance workout based on week."""
        idx = (week_num - 1) % len(cls.ENDURANCE_PROGRESSIONS)
        name, structure, description = cls.ENDURANCE_PROGRESSIONS[idx]

        return {
            'name': name,
            'structure': structure,
            'description': description,
        }

    @classmethod
    def get_long_ride_workout(cls, phase: str, week_in_phase: int) -> Dict:
        """Get long ride workout for the phase."""
        progressions = cls.LONG_RIDE_PROGRESSIONS.get(phase, cls.LONG_RIDE_PROGRESSIONS['base'])

        idx = (week_in_phase - 1) % len(progressions)
        name, z2_power, tempo_power, description = progressions[idx]

        return {
            'name': name,
            'z2_power': z2_power,
            'tempo_power': tempo_power,
            'description': description,
        }

    @classmethod
    def get_strength_workout(
        cls,
        week_num: int,
        session_num: int = 1,
        equipment_tier: str = 'home-basic',
        phase: str = 'base',
        is_recovery_week: bool = False,
        is_masters: bool = False,
    ) -> Dict:
        """Get strength workout for the week.

        ``home-basic`` deliberately returns the legacy library unchanged.
        ``full-gym`` returns periodized compound lifts; ``none`` returns a
        bodyweight-only session. ``session_num`` is 1 or 2 within a week.
        """
        tier = (equipment_tier or 'home-basic').strip().lower()
        if tier == 'full-gym':
            program_key = cls._full_gym_program_key(phase, is_recovery_week)
            program = cls._FULL_GYM_PROGRAMS[program_key]
            exercises = list(program['sessions'][(session_num - 1) % 2])
            if is_masters:
                exercises = [
                    (exercise, prescription.replace(
                        'leave 2 reps in reserve',
                        'leave at least 3 reps in reserve'))
                    for exercise, prescription in exercises
                ]
            letter = 'A' if session_num == 1 else 'B'
            return {
                'name': f"{program['title']} {letter} - {program['duration_min']}min",
                'focus': program['focus'],
                'duration_min': program['duration_min'],
                'exercises': exercises,
            }

        if tier == 'none':
            program = cls._BODYWEIGHT_PROGRAMS
            letter = 'A' if session_num == 1 else 'B'
            return {
                'name': f"{program['title']} {letter} - {program['duration_min']}min",
                'focus': program['focus'],
                'duration_min': program['duration_min'],
                'exercises': list(program['sessions'][(session_num - 1) % 2]),
            }

        # Rotate through workouts, alternating A/B pattern
        if session_num == 1:
            # First session: Foundation A, Power, Cycling-Specific (cycle)
            options = [0, 2, 3]  # Indices into STRENGTH_WORKOUTS
        else:
            # Second session: Foundation B, Mobility (cycle)
            options = [1, 4]

        idx = (week_num - 1) % len(options)
        workout = cls.STRENGTH_WORKOUTS[options[idx]]

        return workout

    @staticmethod
    def _full_gym_program_key(phase: str, is_recovery_week: bool) -> str:
        """Map the cycling calendar to AA → Max → Maintenance → Deload."""
        if is_recovery_week:
            return 'deload'
        if phase == 'base':
            return 'anatomical_adaptation'
        if phase == 'build':
            return 'max_strength'
        if phase == 'peak':
            return 'power'
        return 'maintenance'


def generate_progressive_interval_blocks(
    phase: str,
    week_num: int,
    week_in_phase: int,
    duration_min: int
) -> Tuple[str, str]:
    """
    Generate interval workout blocks with progression.

    Returns (blocks_xml, workout_name).
    """
    workout = WorkoutLibrary.get_interval_workout(phase, week_in_phase)

    blocks = []

    # Warmup
    warmup_min = max(10, int(duration_min * 0.15))
    blocks.append(f'    <Warmup Duration="{warmup_min * 60}" PowerLow="0.45" PowerHigh="0.70"/>')

    # Pre-interval activation - NO nested textevent in SteadyState (breaks TrainingPeaks)
    blocks.append('    <SteadyState Duration="180" Power="0.80"/>')
    blocks.append('    <SteadyState Duration="120" Power="0.55"/>')

    # Main intervals
    blocks.append(f'    <IntervalsT Repeat="{workout["intervals"]}" '
                  f'OnDuration="{workout["on_duration"]}" OnPower="{workout["on_power"]}" '
                  f'OffDuration="{workout["off_duration"]}" OffPower="{workout["off_power"]}">')
    blocks.append(f'      <textevent timeoffset="0" message="{workout["name"]} - interval start"/>')
    blocks.append('    </IntervalsT>')

    # Cooldown
    blocks.append('    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.45"/>')

    return '\n'.join(blocks) + '\n', workout['name']


def generate_progressive_endurance_blocks(
    week_num: int,
    duration_min: int
) -> Tuple[str, str]:
    """
    Generate endurance workout blocks with variations.

    Returns (blocks_xml, workout_name).
    """
    workout = WorkoutLibrary.get_endurance_workout(week_num)

    blocks = []

    # Warmup
    warmup_min = max(5, int(duration_min * 0.1))
    blocks.append(f'    <Warmup Duration="{warmup_min * 60}" PowerLow="0.45" PowerHigh="0.65"/>')

    main_duration = duration_min - warmup_min - 5

    # CRITICAL: SteadyState with nested textevent BREAKS TrainingPeaks import
    # Only IntervalsT can have nested textevent. SteadyState must be self-closing.
    if workout['structure'] == 'steady':
        # Pure steady Z2 - self-closing tag only
        blocks.append(f'    <SteadyState Duration="{main_duration * 60}" Power="0.65"/>')

    elif workout['structure'] == 'cadence':
        # Z2 with cadence drills every 10 minutes
        num_drills = main_duration // 10
        drill_duration = 60  # 1 minute high cadence
        z2_duration = (main_duration * 60 - num_drills * drill_duration) // (num_drills + 1)

        for i in range(num_drills):
            blocks.append(f'    <SteadyState Duration="{z2_duration}" Power="0.65"/>')
            blocks.append(f'    <SteadyState Duration="{drill_duration}" Power="0.60" Cadence="100"/>')
        blocks.append(f'    <SteadyState Duration="{z2_duration}" Power="0.65"/>')

    elif workout['structure'] == 'tempo_touch':
        # Z2 with brief tempo surges
        num_surges = 4
        surge_duration = 180  # 3 min tempo
        z2_between = (main_duration * 60 - num_surges * surge_duration) // (num_surges + 1)

        for i in range(num_surges):
            blocks.append(f'    <SteadyState Duration="{z2_between}" Power="0.65"/>')
            blocks.append(f'    <SteadyState Duration="{surge_duration}" Power="0.82"/>')
        blocks.append(f'    <SteadyState Duration="{z2_between}" Power="0.65"/>')

    else:
        # Default steady state
        blocks.append(f'    <SteadyState Duration="{main_duration * 60}" Power="0.65"/>')

    # Cooldown
    blocks.append('    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.45"/>')

    return '\n'.join(blocks) + '\n', workout['name']


def generate_strength_workout_text(week_num: int, session_num: int = 1) -> str:
    """Generate strength workout as text (not ZWO - strength isn't on trainer)."""
    workout = WorkoutLibrary.get_strength_workout(week_num, session_num)

    lines = [
        f"# {workout['name']}",
        f"Focus: {workout['focus']}",
        "",
        "## Warmup (5 minutes)",
        "- Jumping jacks: 30 seconds",
        "- Leg swings: 10 each leg",
        "- Arm circles: 10 each direction",
        "- Bodyweight squats: 10 reps",
        "",
        "## Main Workout",
    ]

    for exercise, reps in workout['exercises']:
        lines.append(f"- {exercise}: {reps}")

    lines.extend([
        "",
        "## Cooldown (5 minutes)",
        "- Light stretching",
        "- Focus on hips, quads, hamstrings",
        "",
        "---",
        f"Week {week_num} | Session {session_num}",
    ])

    return '\n'.join(lines)


def generate_strength_zwo(
    week_num: int,
    session_num: int = 1,
    duration_min: int = 30,
    equipment_tier: str = 'home-basic',
    phase: str = 'base',
    is_recovery_week: bool = False,
    is_masters: bool = False,
) -> str:
    """Generate a strength-focused ZWO file (very low power, prompts for exercises).

    CRITICAL: No nested textevent in SteadyState, Warmup, or Cooldown - breaks TrainingPeaks.
    """
    workout = WorkoutLibrary.get_strength_workout(
        week_num, session_num, equipment_tier=equipment_tier, phase=phase,
        is_recovery_week=is_recovery_week, is_masters=is_masters)
    duration_min = workout.get('duration_min', duration_min)

    blocks = []

    # This is a "virtual" trainer workout that prompts for strength exercises
    # Very low power to keep legs moving while doing bodyweight exercises
    # NO nested textevent - use self-closing tags only

    blocks.append('    <Warmup Duration="300" PowerLow="0.30" PowerHigh="0.40"/>')

    # Each exercise gets a segment - self-closing SteadyState only
    exercise_duration = ((duration_min - 10) * 60) // len(workout['exercises'])

    for i, (exercise, reps) in enumerate(workout['exercises']):
        blocks.append(f'    <SteadyState Duration="{exercise_duration}" Power="0.35"/>')

    blocks.append('    <Cooldown Duration="300" PowerLow="0.40" PowerHigh="0.30"/>')

    return '\n'.join(blocks) + '\n', workout


if __name__ == '__main__':
    # Test the library
    print("=== Interval Progressions ===")
    for week in range(1, 6):
        workout = WorkoutLibrary.get_interval_workout('build', week)
        print(f"Week {week}: {workout['name']} - {workout['intervals']}x{workout['on_duration']//60}min @ {int(workout['on_power']*100)}%")

    print("\n=== Strength Workouts ===")
    for week in range(1, 5):
        for session in [1, 2]:
            workout = WorkoutLibrary.get_strength_workout(week, session)
            print(f"Week {week} Session {session}: {workout['name']}")
