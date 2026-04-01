#!/usr/bin/env python3
"""
Kitchen Sink Archetypes — multi-energy-system race simulation workouts.

These are the block-builder's signature "hit everything" sessions.
Each hits threshold, VO2max, neuromuscular, and endurance in a single workout.

Structure reverse-engineered from:
- Block-builder workout-library.md (duration/TSS per variant)
- SKILL.md descriptions ("hits every energy system")
- TSS/IF analysis to constrain power targets

All Kitchen Sink variants are ONE family for series coherence.
"""

# Kitchen Sink archetypes use the 'segments' format (Format B)
# Each segment: {'type': 'steady'|'intervals', 'duration': seconds, 'power': ftp_fraction}

KITCHEN_SINK_ARCHETYPES = {
    'Kitchen_Sink': [
        # ===================================================================
        # Drain Cleaner — 2:48 / 194 TSS / IF 0.83
        # Structure: Warmup → Threshold block → VO2 intervals → Tempo → Sprints → Cooldown
        # ===================================================================
        {
            'name': 'Drain Cleaner',
            'levels': {
                '1': {
                    'description': 'Kitchen Sink — Drain Cleaner. Hits every energy system: '
                                   'threshold sustained, VO2max intervals, tempo, sprints. '
                                   'The full flush.',
                    'structure': '15min warmup, 10min @ 95% FTP, 5min recovery, '
                                 '4x3min @ 115% FTP w/ 2min recovery, 5min recovery, '
                                 '10min @ 85% tempo, 6x30sec sprint @ 150% w/ 90sec recovery, '
                                 '15min cooldown',
                    'execution': 'Pace the threshold block. Attack the VO2 intervals. '
                                 'Settle into tempo. Empty the tank on sprints.',
                    'segments': [
                        {'type': 'steady', 'duration': 600, 'power': 0.95},  # Threshold
                        {'type': 'steady', 'duration': 300, 'power': 0.55},  # Recovery
                        {'type': 'intervals', 'duration': 180, 'power': 1.12, 'repeats': 3, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},  # Recovery
                        {'type': 'steady', 'duration': 600, 'power': 0.85},  # Tempo
                        {'type': 'intervals', 'duration': 30, 'power': 1.45, 'repeats': 4, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '2': {
                    'description': 'Kitchen Sink — Drain Cleaner L2. Extended sets.',
                    'structure': '15min warmup, 12min @ 95%, 5min rec, 4x3min @ 115% w/ 2min rec, '
                                 '5min rec, 12min @ 85%, 6x30sec @ 150% w/ 90sec rec, 15min cooldown',
                    'execution': 'Same structure, longer sustained blocks.',
                    'segments': [
                        {'type': 'steady', 'duration': 720, 'power': 0.95},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'intervals', 'duration': 180, 'power': 1.15, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'steady', 'duration': 720, 'power': 0.85},
                        {'type': 'intervals', 'duration': 30, 'power': 1.50, 'repeats': 6, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '3': {
                    'description': 'Kitchen Sink — Drain Cleaner L3. More intervals, higher power.',
                    'segments': [
                        {'type': 'steady', 'duration': 720, 'power': 0.97},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'intervals', 'duration': 180, 'power': 1.17, 'repeats': 5, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'steady', 'duration': 720, 'power': 0.87},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 7, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '4': {
                    'description': 'Kitchen Sink — Drain Cleaner L4. Race intensity.',
                    'segments': [
                        {'type': 'steady', 'duration': 900, 'power': 0.97},
                        {'type': 'steady', 'duration': 240, 'power': 0.55},
                        {'type': 'intervals', 'duration': 210, 'power': 1.18, 'repeats': 5, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'steady', 'duration': 720, 'power': 0.88},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 8, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '5': {
                    'description': 'Kitchen Sink — Drain Cleaner L5. Extended race simulation.',
                    'segments': [
                        {'type': 'steady', 'duration': 900, 'power': 0.98},
                        {'type': 'steady', 'duration': 240, 'power': 0.55},
                        {'type': 'intervals', 'duration': 240, 'power': 1.18, 'repeats': 5, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'steady', 'duration': 900, 'power': 0.88},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 8, 'rest_duration': 60, 'rest_power': 0.50},
                    ],
                },
                '6': {
                    'description': 'Kitchen Sink — Drain Cleaner L6. Maximum load.',
                    'segments': [
                        {'type': 'steady', 'duration': 1200, 'power': 0.98},
                        {'type': 'steady', 'duration': 240, 'power': 0.55},
                        {'type': 'intervals', 'duration': 240, 'power': 1.20, 'repeats': 6, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 300, 'power': 0.55},
                        {'type': 'steady', 'duration': 900, 'power': 0.90},
                        {'type': 'intervals', 'duration': 30, 'power': 1.60, 'repeats': 10, 'rest_duration': 60, 'rest_power': 0.50},
                    ],
                },
            },
        },

        # ===================================================================
        # La Balanguera — progressive series (3:04→4:21→5:28)
        # Structure: Long endurance base with embedded intensity blocks
        # ===================================================================
        {
            'name': 'La Balanguera',
            'levels': {
                '1': {
                    'description': 'La Balanguera 1. Endurance base with threshold and VO2 insertions.',
                    'structure': '15min warmup, 20min Z2, 2x8min @ 95% w/ 4min rec, '
                                 '15min Z2, 3x3min @ 110% w/ 2min rec, 20min Z2, cooldown',
                    'segments': [
                        {'type': 'steady', 'duration': 1200, 'power': 0.65},
                        {'type': 'intervals', 'duration': 480, 'power': 0.95, 'repeats': 2, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 900, 'power': 0.65},
                        {'type': 'intervals', 'duration': 180, 'power': 1.10, 'repeats': 3, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 1200, 'power': 0.65},
                    ],
                },
                '2': {
                    'description': 'La Balanguera 2. Extended endurance + higher intensity.',
                    'segments': [
                        {'type': 'steady', 'duration': 1800, 'power': 0.65},
                        {'type': 'intervals', 'duration': 480, 'power': 0.97, 'repeats': 3, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 1200, 'power': 0.65},
                        {'type': 'intervals', 'duration': 180, 'power': 1.12, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 1800, 'power': 0.65},
                    ],
                },
                '3': {
                    'description': 'La Balanguera 3. Full race simulation volume.',
                    'segments': [
                        {'type': 'steady', 'duration': 2400, 'power': 0.65},
                        {'type': 'intervals', 'duration': 600, 'power': 0.97, 'repeats': 3, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 1500, 'power': 0.65},
                        {'type': 'intervals', 'duration': 240, 'power': 1.15, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 2400, 'power': 0.65},
                        {'type': 'intervals', 'duration': 30, 'power': 1.50, 'repeats': 5, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '4': {
                    'description': 'La Balanguera 4. Higher threshold power.',
                    'segments': [
                        {'type': 'steady', 'duration': 2400, 'power': 0.67},
                        {'type': 'intervals', 'duration': 600, 'power': 0.98, 'repeats': 3, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 1500, 'power': 0.67},
                        {'type': 'intervals', 'duration': 240, 'power': 1.17, 'repeats': 5, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 2400, 'power': 0.67},
                        {'type': 'intervals', 'duration': 30, 'power': 1.50, 'repeats': 6, 'rest_duration': 90, 'rest_power': 0.50},
                    ],
                },
                '5': {
                    'description': 'La Balanguera 5. Race-day intensity.',
                    'segments': [
                        {'type': 'steady', 'duration': 2700, 'power': 0.68},
                        {'type': 'intervals', 'duration': 600, 'power': 0.98, 'repeats': 4, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 1800, 'power': 0.68},
                        {'type': 'intervals', 'duration': 240, 'power': 1.18, 'repeats': 5, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 2700, 'power': 0.68},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 8, 'rest_duration': 60, 'rest_power': 0.50},
                    ],
                },
                '6': {
                    'description': 'La Balanguera 6. Maximum race simulation.',
                    'segments': [
                        {'type': 'steady', 'duration': 3000, 'power': 0.70},
                        {'type': 'intervals', 'duration': 720, 'power': 1.00, 'repeats': 4, 'rest_duration': 240, 'rest_power': 0.55},
                        {'type': 'steady', 'duration': 1800, 'power': 0.70},
                        {'type': 'intervals', 'duration': 240, 'power': 1.20, 'repeats': 6, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 3000, 'power': 0.70},
                        {'type': 'intervals', 'duration': 30, 'power': 1.60, 'repeats': 10, 'rest_duration': 60, 'rest_power': 0.50},
                    ],
                },
            },
        },

        # ===================================================================
        # Hyttevask — shorter Kitchen Sink (2:00 / 135 TSS)
        # Norwegian "house cleaning" — compact multi-system session
        # ===================================================================
        {
            'name': 'Hyttevask',
            'levels': {
                '1': {
                    'description': 'Hyttevask — compact kitchen sink. Threshold ramp + VO2 + sprints.',
                    'segments': [
                        {'type': 'steady', 'duration': 480, 'power': 0.90},   # Tempo ramp
                        {'type': 'steady', 'duration': 300, 'power': 0.95},   # Threshold
                        {'type': 'steady', 'duration': 180, 'power': 0.55},   # Recovery
                        {'type': 'intervals', 'duration': 120, 'power': 1.12, 'repeats': 3, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 20, 'power': 1.50, 'repeats': 4, 'rest_duration': 40, 'rest_power': 0.50},
                    ],
                },
                '2': {
                    'description': 'Hyttevask L2. Longer blocks, higher power.',
                    'segments': [
                        {'type': 'steady', 'duration': 540, 'power': 0.92},
                        {'type': 'steady', 'duration': 360, 'power': 0.97},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 150, 'power': 1.15, 'repeats': 3, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 25, 'power': 1.50, 'repeats': 5, 'rest_duration': 40, 'rest_power': 0.50},
                    ],
                },
                '3': {
                    'description': 'Hyttevask L3. Extended VO2 block.',
                    'segments': [
                        {'type': 'steady', 'duration': 600, 'power': 0.93},
                        {'type': 'steady', 'duration': 420, 'power': 0.97},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 180, 'power': 1.15, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 6, 'rest_duration': 40, 'rest_power': 0.50},
                    ],
                },
                '4': {
                    'description': 'Hyttevask L4.',
                    'segments': [
                        {'type': 'steady', 'duration': 600, 'power': 0.95},
                        {'type': 'steady', 'duration': 480, 'power': 0.98},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 180, 'power': 1.17, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 180, 'power': 0.55},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 7, 'rest_duration': 40, 'rest_power': 0.50},
                    ],
                },
                '5': {
                    'description': 'Hyttevask L5.',
                    'segments': [
                        {'type': 'steady', 'duration': 720, 'power': 0.95},
                        {'type': 'steady', 'duration': 480, 'power': 0.98},
                        {'type': 'steady', 'duration': 150, 'power': 0.55},
                        {'type': 'intervals', 'duration': 210, 'power': 1.18, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 150, 'power': 0.55},
                        {'type': 'intervals', 'duration': 30, 'power': 1.55, 'repeats': 8, 'rest_duration': 40, 'rest_power': 0.50},
                    ],
                },
                '6': {
                    'description': 'Hyttevask L6.',
                    'segments': [
                        {'type': 'steady', 'duration': 720, 'power': 0.97},
                        {'type': 'steady', 'duration': 600, 'power': 1.00},
                        {'type': 'steady', 'duration': 120, 'power': 0.55},
                        {'type': 'intervals', 'duration': 240, 'power': 1.20, 'repeats': 4, 'rest_duration': 120, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 120, 'power': 0.55},
                        {'type': 'intervals', 'duration': 30, 'power': 1.60, 'repeats': 10, 'rest_duration': 30, 'rest_power': 0.50},
                    ],
                },
            },
        },
    ],
}
