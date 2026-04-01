#!/usr/bin/env python3
"""
SFR Series Archetypes — Sustained Force Repetitions.

Low-cadence, high-force pedaling to build neuromuscular strength on the bike.
Thunder Quads = the primary 6-level progression.
Blood Pistons = advanced 3-level variant (higher force, shorter recovery).

Source: block-builder references/workout-library.md Base SFR series
"""

SFR_SERIES_ARCHETYPES = {
    'SFR_Series': [
        # ===================================================================
        # Thunder Quads — 6-level SFR progression (1:00→1:30)
        # Low cadence (50-60 RPM), seated, high force
        # ===================================================================
        {
            'name': 'Thunder Quads',
            'levels': {
                '1': {
                    'description': 'Thunder Quads L1. Seated low-cadence force work. '
                                   '50-55 RPM, focus on smooth pedal stroke.',
                    'structure': '10min warmup, 4x4min @ 85% FTP @ 50rpm w/ 3min recovery, cooldown',
                    'execution': 'Stay seated. Push big gear, smooth circles. '
                                 'NO mashing — if form breaks, reduce power.',
                    'intervals': (4, 240),  # 4 × 4min
                    'on_power': 0.85,
                    'off_power': 0.50,
                    'off_duration': 180,
                    'cadence': 52,
                },
                '2': {
                    'description': 'Thunder Quads L2. 5x4min, slightly higher power.',
                    'intervals': (5, 240),
                    'on_power': 0.87,
                    'off_power': 0.50,
                    'off_duration': 180,
                    'cadence': 53,
                },
                '3': {
                    'description': 'Thunder Quads L3. 5x5min, building force endurance.',
                    'intervals': (5, 300),
                    'on_power': 0.88,
                    'off_power': 0.50,
                    'off_duration': 180,
                    'cadence': 55,
                },
                '4': {
                    'description': 'Thunder Quads L4. 6x4min, higher power.',
                    'intervals': (6, 240),
                    'on_power': 0.90,
                    'off_power': 0.50,
                    'off_duration': 150,
                    'cadence': 55,
                },
                '5': {
                    'description': 'Thunder Quads L5. 6x5min, reduced recovery.',
                    'intervals': (6, 300),
                    'on_power': 0.90,
                    'off_power': 0.50,
                    'off_duration': 150,
                    'cadence': 55,
                },
                '6': {
                    'description': 'Thunder Quads L6. 6x5min, maximum force.',
                    'intervals': (6, 300),
                    'on_power': 0.92,
                    'off_power': 0.50,
                    'off_duration': 120,
                    'cadence': 55,
                },
            },
        },

        # ===================================================================
        # Blood Pistons — advanced SFR (higher power, longer efforts)
        # ===================================================================
        {
            'name': 'Blood Pistons',
            'levels': {
                '1': {
                    'description': 'Blood Pistons L1. Extended force work at threshold.',
                    'structure': '10min warmup, 3x6min @ 92% FTP @ 50rpm w/ 4min recovery, '
                                 '10min tempo @ 80%, cooldown',
                    'segments': [
                        {'type': 'intervals', 'duration': 360, 'power': 0.92, 'repeats': 3, 'rest_duration': 240, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 600, 'power': 0.80},
                    ],
                    'cadence': 50,
                },
                '2': {
                    'description': 'Blood Pistons L2. 4x6min, higher power.',
                    'segments': [
                        {'type': 'intervals', 'duration': 360, 'power': 0.93, 'repeats': 4, 'rest_duration': 210, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 600, 'power': 0.82},
                    ],
                    'cadence': 50,
                },
                '3': {
                    'description': 'Blood Pistons L3. 4x7min, approaching threshold.',
                    'segments': [
                        {'type': 'intervals', 'duration': 420, 'power': 0.95, 'repeats': 4, 'rest_duration': 210, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 600, 'power': 0.83},
                    ],
                    'cadence': 50,
                },
                '4': {
                    'description': 'Blood Pistons L4. Maximum SFR load.',
                    'segments': [
                        {'type': 'intervals', 'duration': 420, 'power': 0.96, 'repeats': 5, 'rest_duration': 180, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 600, 'power': 0.85},
                    ],
                    'cadence': 52,
                },
                '5': {
                    'description': 'Blood Pistons L5. Extended race force.',
                    'segments': [
                        {'type': 'intervals', 'duration': 480, 'power': 0.97, 'repeats': 5, 'rest_duration': 180, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 720, 'power': 0.85},
                    ],
                    'cadence': 52,
                },
                '6': {
                    'description': 'Blood Pistons L6. Peak force development.',
                    'segments': [
                        {'type': 'intervals', 'duration': 480, 'power': 0.98, 'repeats': 6, 'rest_duration': 150, 'rest_power': 0.50},
                        {'type': 'steady', 'duration': 720, 'power': 0.87},
                    ],
                    'cadence': 55,
                },
            },
        },
    ],
}
