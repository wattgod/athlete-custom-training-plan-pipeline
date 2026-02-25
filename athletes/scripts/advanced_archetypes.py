#!/usr/bin/env python3
"""
Advanced archetype additions for the Gravel God training system.
Sprint 2 expansion: 16 new archetypes across 8 categories.

Ronnestad 30/15, Ronnestad 40/20, Float Sets, Hard Starts, Criss-Cross,
Late-Race VO2max, TTE Extension, Structured Fartlek, FatMax/VLamax Suppression,
Heat Acclimation, Burst Intervals, Attacks/Repeatability, BPA, Kitchen Sink,
Gravel Race Simulation, Glycolytic Power.

All segment-based archetypes use helper functions to compute exact durations.
Manual segment enumeration is banned — it's how the Criss-Cross bug happened.
"""


# =============================================================================
# HELPER FUNCTIONS — compute segments programmatically, never enumerate by hand
# =============================================================================

def _criss_cross(total_sec, interval_sec, floor_power, ceiling_power):
    """Generate alternating floor/ceiling segments for exactly total_sec.

    >>> segs = _criss_cross(900, 120, 0.80, 1.00)
    >>> sum(s['duration'] for s in segs)
    900
    """
    segments = []
    elapsed = 0
    is_floor = True
    while elapsed + interval_sec <= total_sec:
        power = floor_power if is_floor else ceiling_power
        segments.append({'type': 'steady', 'duration': interval_sec, 'power': power})
        elapsed += interval_sec
        is_floor = not is_floor
    remaining = total_sec - elapsed
    if remaining > 0:
        power = floor_power if is_floor else ceiling_power
        segments.append({'type': 'steady', 'duration': remaining, 'power': power})
    return segments


def _base_with_efforts(total_sec, efforts, base_power):
    """Distribute effort blocks evenly within a base-power ride.

    Guarantees sum(segment durations) == total_sec exactly.

    Args:
        total_sec: Total segment duration in seconds (excludes warmup/cooldown)
        efforts: List of (duration_sec, power) tuples for each effort block
        base_power: Power for base riding between efforts

    >>> segs = _base_with_efforts(4800, [(30, 0.85)] * 3, 0.65)
    >>> sum(s['duration'] for s in segs)
    4800
    """
    total_effort = sum(d for d, _ in efforts)
    total_base = total_sec - total_effort
    if total_base <= 0:
        # Edge case: more effort than total time — just stack efforts
        return [{'type': 'steady', 'duration': d, 'power': p} for d, p in efforts]
    n_gaps = len(efforts) + 1
    gap = total_base // n_gaps
    remainder = total_base - gap * n_gaps

    segments = []
    # First gap absorbs integer remainder for exact total
    segments.append({'type': 'steady', 'duration': gap + remainder, 'power': base_power})
    for dur, power in efforts:
        segments.append({'type': 'steady', 'duration': dur, 'power': power})
        segments.append({'type': 'steady', 'duration': gap, 'power': base_power})
    return segments


def _hard_start_reps(reps, burst_dur, burst_power, hold_dur, hold_power,
                     rest_dur, rest_power=0.55):
    """Generate burst -> threshold hold segments with recovery between reps.

    Last rep has no trailing recovery (cooldown follows immediately).

    >>> segs = _hard_start_reps(3, 15, 1.50, 300, 0.95, 180)
    >>> len([s for s in segs if s['power'] >= 1.50])
    3
    """
    segments = []
    for i in range(reps):
        segments.append({'type': 'steady', 'duration': burst_dur, 'power': burst_power})
        segments.append({'type': 'steady', 'duration': hold_dur, 'power': hold_power})
        if i < reps - 1 and rest_dur > 0:
            segments.append({'type': 'steady', 'duration': rest_dur, 'power': rest_power})
    return segments


def _attack_reps(base_dur, base_power, num_attacks, attack_dur, attack_power,
                 rest_dur, rest_power):
    """Generate tempo base then repeated attack efforts with tempo recovery.

    Last attack has no trailing recovery (cooldown follows).

    >>> segs = _attack_reps(300, 0.82, 5, 30, 1.30, 180, 0.82)
    >>> len([s for s in segs if s['power'] >= 1.30])
    5
    """
    segments = [{'type': 'steady', 'duration': base_dur, 'power': base_power}]
    for i in range(num_attacks):
        segments.append({'type': 'steady', 'duration': attack_dur, 'power': attack_power})
        if i < num_attacks - 1:
            segments.append({'type': 'steady', 'duration': rest_dur, 'power': rest_power})
    return segments


# =============================================================================
# VO2MAX ADDITIONS: Ronnestad 30/15, Ronnestad 40/20, Float Sets
# =============================================================================

VO2MAX_ADVANCED = [
    {
        'name': 'Ronnestad 30/15',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 1 set: 6x 30sec ON @ 105% FTP / 15sec OFF',
                'execution': 'Intro to short-short intervals. Smooth power, high cadence, no surging',
                'cadence_prescription': '95-105rpm (high turnover)',
                'cadence': 100,
                'position_prescription': 'Seated, hands on hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'segments': [
                    {'type': 'intervals', 'repeats': 6, 'on_duration': 30, 'on_power': 1.05, 'off_duration': 15, 'off_power': 0.55}
                ]
            },
            '2': {
                'structure': '15min warmup Z2, 1 set: 9x 30sec ON @ 110% FTP / 15sec OFF',
                'execution': 'Building rep count. Keep ON power consistent through all reps',
                'segments': [
                    {'type': 'intervals', 'repeats': 9, 'on_duration': 30, 'on_power': 1.10, 'off_duration': 15, 'off_power': 0.55}
                ]
            },
            '3': {
                'structure': '15min warmup Z2, 1 set: 13x 30sec ON @ 115% FTP / 15sec OFF',
                'execution': 'Full Ronnestad set. 9.75min accumulated VO2max time',
                'segments': [
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.15, 'off_duration': 15, 'off_power': 0.55}
                ]
            },
            '4': {
                'structure': '15min warmup Z2, 2 sets: 9x 30sec ON @ 120% FTP / 15sec OFF, 3min rest between sets',
                'execution': 'Multi-set protocol. Recover well between sets, hold form in second set',
                'segments': [
                    {'type': 'intervals', 'repeats': 9, 'on_duration': 30, 'on_power': 1.20, 'off_duration': 15, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 9, 'on_duration': 30, 'on_power': 1.20, 'off_duration': 15, 'off_power': 0.55}
                ]
            },
            '5': {
                'structure': '15min warmup Z2, 2 sets: 13x 30sec ON @ 125% FTP / 15sec OFF, 3min rest between sets',
                'execution': 'Full double Ronnestad. Massive VO2max accumulation',
                'segments': [
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.25, 'off_duration': 15, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.25, 'off_duration': 15, 'off_power': 0.55}
                ]
            },
            '6': {
                'structure': '15min warmup Z2, 3 sets: 13x 30sec ON @ 130% FTP / 15sec OFF, 3min rest between sets',
                'execution': 'Maximum protocol. 3 full Ronnestad sets. Elite VO2max stimulus',
                'segments': [
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.30, 'off_duration': 15, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.30, 'off_duration': 15, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 13, 'on_duration': 30, 'on_power': 1.30, 'off_duration': 15, 'off_power': 0.55}
                ]
            }
        }
    },
    {
        'name': 'Ronnestad 40/20',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 1 set: 5x 40sec ON @ 100% FTP / 20sec OFF',
                'execution': 'Longer ON interval variant. Slightly more sustained than 30/15',
                'cadence_prescription': '90-100rpm',
                'cadence': 95,
                'position_prescription': 'Seated, hands on hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'segments': [
                    {'type': 'intervals', 'repeats': 5, 'on_duration': 40, 'on_power': 1.00, 'off_duration': 20, 'off_power': 0.55}
                ]
            },
            '2': {
                'structure': '15min warmup Z2, 1 set: 7x 40sec ON @ 105% FTP / 20sec OFF',
                'execution': 'Building rep count. Hold power targets precisely',
                'segments': [
                    {'type': 'intervals', 'repeats': 7, 'on_duration': 40, 'on_power': 1.05, 'off_duration': 20, 'off_power': 0.55}
                ]
            },
            '3': {
                'structure': '15min warmup Z2, 1 set: 10x 40sec ON @ 108% FTP / 20sec OFF',
                'execution': 'Full set of 10 reps. Manage pacing through extended set',
                'segments': [
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.08, 'off_duration': 20, 'off_power': 0.55}
                ]
            },
            '4': {
                'structure': '15min warmup Z2, 2 sets: 7x 40sec ON @ 112% FTP / 20sec OFF, 3min rest between sets',
                'execution': 'Multi-set protocol. Second set tests mental fortitude',
                'segments': [
                    {'type': 'intervals', 'repeats': 7, 'on_duration': 40, 'on_power': 1.12, 'off_duration': 20, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 7, 'on_duration': 40, 'on_power': 1.12, 'off_duration': 20, 'off_power': 0.55}
                ]
            },
            '5': {
                'structure': '15min warmup Z2, 2 sets: 10x 40sec ON @ 115% FTP / 20sec OFF, 3min rest between sets',
                'execution': 'Full double set. 13+ min of accumulated work',
                'segments': [
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.15, 'off_duration': 20, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.15, 'off_duration': 20, 'off_power': 0.55}
                ]
            },
            '6': {
                'structure': '15min warmup Z2, 3 sets: 10x 40sec ON @ 120% FTP / 20sec OFF, 3min rest between sets',
                'execution': 'Maximum protocol. 20min accumulated work across 3 sets',
                'segments': [
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.20, 'off_duration': 20, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.20, 'off_duration': 20, 'off_power': 0.55},
                    {'type': 'steady', 'duration': 180, 'power': 0.55},
                    {'type': 'intervals', 'repeats': 10, 'on_duration': 40, 'on_power': 1.20, 'off_duration': 20, 'off_power': 0.55}
                ]
            }
        }
    },
    {
        'name': 'Float Sets',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x 3min @ 106% FTP with 3min tempo float @ 80% FTP between',
                'execution': 'VO2max intervals with tempo recovery instead of easy. Stay engaged during floats',
                'cadence_prescription': '90-100rpm',
                'cadence': 95,
                'position_prescription': 'Seated, hands on hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (3, 180),
                'on_power': 1.06,
                'off_power': 0.80,
                'off_duration': 180,
                'duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 3x 4min @ 108% FTP with 3min tempo float @ 82% FTP',
                'execution': 'Extended ON duration. Float recovery keeps HR elevated for greater stimulus',
                'intervals': (3, 240),
                'on_power': 1.08,
                'off_power': 0.82,
                'off_duration': 180,
                'duration': 240
            },
            '3': {
                'structure': '15min warmup Z2, 4x 4min @ 110% FTP with 3min tempo float @ 82% FTP',
                'execution': 'Added volume. The floats prevent full recovery — this is intentional',
                'intervals': (4, 240),
                'on_power': 1.10,
                'off_power': 0.82,
                'off_duration': 180,
                'duration': 240
            },
            '4': {
                'structure': '15min warmup Z2, 4x 4min @ 112% FTP with 2.5min tempo float @ 83% FTP',
                'execution': 'Compressed recovery. Fatigue accumulates faster — manage early reps conservatively',
                'intervals': (4, 240),
                'on_power': 1.12,
                'off_power': 0.83,
                'off_duration': 150,
                'duration': 240
            },
            '5': {
                'structure': '15min warmup Z2, 5x 4min @ 115% FTP with 2.5min tempo float @ 84% FTP',
                'execution': 'High volume float set. 20min of VO2max work with minimal true recovery',
                'intervals': (5, 240),
                'on_power': 1.15,
                'off_power': 0.84,
                'off_duration': 150,
                'duration': 240
            },
            '6': {
                'structure': '15min warmup Z2, 5x 5min @ 120% FTP with 2min tempo float @ 85% FTP',
                'execution': 'Maximum float protocol. 25min of VO2max work, never dropping below tempo',
                'intervals': (5, 300),
                'on_power': 1.20,
                'off_power': 0.85,
                'off_duration': 120,
                'duration': 300
            }
        }
    },
]


# =============================================================================
# TT_THRESHOLD ADDITIONS: Criss-Cross, TTE Extension, BPA
# =============================================================================

THRESHOLD_ADVANCED = [
    {
        'name': 'Criss-Cross Intervals',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 15min criss-cross: alternate 2min @ 80% / 2min @ 100% FTP',
                'execution': 'Oscillate between tempo floor and threshold ceiling. Smooth transitions',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'After warmup',
                'fueling': '60-70g CHO/hr',
                'segments': _criss_cross(900, 120, 0.80, 1.00),
            },
            '2': {
                'structure': '15min warmup Z2, 20min criss-cross: alternate 2min @ 82% / 2min @ 102% FTP',
                'execution': 'Extended duration. Feel the rhythm of the oscillation',
                'segments': _criss_cross(1200, 120, 0.82, 1.02),
            },
            '3': {
                'structure': '15min warmup Z2, 25min criss-cross: alternate 90sec @ 83% / 90sec @ 105% FTP',
                'execution': 'Faster oscillation with wider power gap. Demanding mentally and physically',
                'segments': _criss_cross(1500, 90, 0.83, 1.05),
            },
            '4': {
                'structure': '15min warmup Z2, 30min criss-cross: alternate 90sec @ 83% / 90sec @ 107% FTP',
                'execution': 'Extended criss-cross. Never fully recover, never fully crack',
                'segments': _criss_cross(1800, 90, 0.83, 1.07),
            },
            '5': {
                'structure': '15min warmup Z2, 35min criss-cross: alternate 60sec @ 84% / 60sec @ 108% FTP',
                'execution': 'Rapid oscillation. Every minute is a transition. Race-realistic power variability',
                'segments': _criss_cross(2100, 60, 0.84, 1.08),
            },
            '6': {
                'structure': '15min warmup Z2, 40min criss-cross: alternate 60sec @ 85% / 60sec @ 110% FTP',
                'execution': 'Maximum criss-cross. 40min of relentless oscillation. Mental and physical test',
                'segments': _criss_cross(2400, 60, 0.85, 1.10),
            }
        }
    },
    {
        'name': 'TTE Extension',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2x 15min @ 95% FTP with 5min recovery between',
                'execution': 'Build threshold duration. Steady power, controlled breathing',
                'cadence_prescription': '85-95rpm (race cadence)',
                'cadence': 90,
                'position_prescription': 'Seated, aero if possible',
                'timing_prescription': 'Fresh',
                'fueling': '60-80g CHO/hr',
                'segments': [
                    {'type': 'steady', 'duration': 900, 'power': 0.95},
                    {'type': 'steady', 'duration': 300, 'power': 0.55},
                    {'type': 'steady', 'duration': 900, 'power': 0.95},
                ]
            },
            '2': {
                'structure': '15min warmup Z2, 2x 18min @ 96% FTP with 5min recovery',
                'execution': 'Extending time at threshold. Focus on relaxed upper body',
                'segments': [
                    {'type': 'steady', 'duration': 1080, 'power': 0.96},
                    {'type': 'steady', 'duration': 300, 'power': 0.55},
                    {'type': 'steady', 'duration': 1080, 'power': 0.96},
                ]
            },
            '3': {
                'structure': '15min warmup Z2, 2x 22min @ 97% FTP with 5min recovery',
                'execution': 'Approaching single-effort territory. Each rep is a mental exercise',
                'segments': [
                    {'type': 'steady', 'duration': 1320, 'power': 0.97},
                    {'type': 'steady', 'duration': 300, 'power': 0.55},
                    {'type': 'steady', 'duration': 1320, 'power': 0.97},
                ]
            },
            '4': {
                'structure': '15min warmup Z2, 1x 35min @ 98% FTP continuous',
                'execution': 'Single sustained effort. Break it into 5min mental chunks',
                'segments': [
                    {'type': 'steady', 'duration': 2100, 'power': 0.98},
                ]
            },
            '5': {
                'structure': '15min warmup Z2, 1x 45min @ 99% FTP continuous',
                'execution': 'Extended TTE push. This is where race fitness is built',
                'segments': [
                    {'type': 'steady', 'duration': 2700, 'power': 0.99},
                ]
            },
            '6': {
                'structure': '15min warmup Z2, 1x 60min @ 100% FTP continuous',
                'execution': 'Maximum TTE. Full hour at threshold. Elite endurance test',
                'segments': [
                    {'type': 'steady', 'duration': 3600, 'power': 1.00},
                ]
            }
        }
    },
    {
        'name': 'BPA (Best Possible Average)',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 20min sustained effort @ 90% FTP',
                'execution': 'Single effort, best average power for the duration. Start conservative',
                'cadence_prescription': '85-95rpm (self-selected)',
                'cadence': 90,
                'position_prescription': 'Race position, aero if possible',
                'timing_prescription': 'Fresh',
                'fueling': '60-80g CHO/hr',
                'single_effort': True,
                'duration': 1200,
                'power': 0.90
            },
            '2': {
                'structure': '15min warmup Z2, 25min sustained effort @ 92% FTP',
                'execution': 'Extended BPA. Find your rhythm and hold it',
                'single_effort': True,
                'duration': 1500,
                'power': 0.92
            },
            '3': {
                'structure': '15min warmup Z2, 30min sustained effort @ 94% FTP',
                'execution': 'Half-hour BPA. Classic testing and racing duration',
                'single_effort': True,
                'duration': 1800,
                'power': 0.94
            },
            '4': {
                'structure': '15min warmup Z2, 40min sustained effort @ 96% FTP',
                'execution': 'Extended single effort. Mental fortitude is key',
                'single_effort': True,
                'duration': 2400,
                'power': 0.96
            },
            '5': {
                'structure': '15min warmup Z2, 50min sustained effort @ 98% FTP',
                'execution': 'Near-FTP for 50min. Pace conservatively — no heroics early',
                'single_effort': True,
                'duration': 3000,
                'power': 0.98
            },
            '6': {
                'structure': '15min warmup Z2, 60min sustained effort @ 100% FTP',
                'execution': 'Full hour at FTP. The definitive threshold test',
                'single_effort': True,
                'duration': 3600,
                'power': 1.00
            }
        }
    },
]


# =============================================================================
# RACE_SIMULATION ADDITIONS: Hard Starts, Structured Fartlek,
#                             Attacks/Repeatability, Kitchen Sink
# =============================================================================

RACE_SIM_ADVANCED = [
    {
        'name': 'Hard Starts',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x (15sec burst @ 150% FTP + 5min hold @ 95% FTP), 3min recovery',
                'execution': 'Simulate race starts and climbs. Explosive burst then settle to threshold',
                'cadence_prescription': 'Burst: 110+rpm, Hold: 85-95rpm',
                'cadence': 90,
                'position_prescription': 'Burst: standing, Hold: seated',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'segments': _hard_start_reps(3, 15, 1.50, 300, 0.95, 180),
            },
            '2': {
                'structure': '15min warmup Z2, 3x (20sec @ 160% FTP + 6min @ 97% FTP), 3min recovery',
                'execution': 'Longer bursts, higher hold power. Settling quickly is the skill',
                'segments': _hard_start_reps(3, 20, 1.60, 360, 0.97, 180),
            },
            '3': {
                'structure': '15min warmup Z2, 4x (20sec @ 170% FTP + 7min @ 98% FTP), 3min recovery',
                'execution': 'Four hard starts. Each one should feel like opening a race gap',
                'segments': _hard_start_reps(4, 20, 1.70, 420, 0.98, 180),
            },
            '4': {
                'structure': '15min warmup Z2, 4x (25sec @ 175% FTP + 8min @ 100% FTP), 2.5min recovery',
                'execution': 'Longer burst, FTP hold, shorter recovery. Race realistic',
                'segments': _hard_start_reps(4, 25, 1.75, 480, 1.00, 150),
            },
            '5': {
                'structure': '15min warmup Z2, 5x (25sec @ 185% FTP + 8min @ 102% FTP), 2.5min recovery',
                'execution': 'Five hard starts. Supra-threshold hold. Race selection intensity',
                'segments': _hard_start_reps(5, 25, 1.85, 480, 1.02, 150),
            },
            '6': {
                'structure': '15min warmup Z2, 5x (30sec @ 200% FTP + 10min @ 105% FTP), 2min recovery',
                'execution': 'Maximum protocol. Sprint-to-threshold. Race-winning efforts',
                'segments': _hard_start_reps(5, 30, 2.00, 600, 1.05, 120),
            }
        }
    },
    {
        'name': 'Structured Fartlek',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 8x 20sec @ 120% FTP with 90sec @ 65% FTP recovery',
                'execution': 'Structured freedom riding. Hit power targets precisely, relax between',
                'cadence_prescription': 'Efforts: 95-110rpm, Recovery: self-selected',
                'cadence': 95,
                'position_prescription': 'Varies — seated and standing mix',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (8, 20),
                'on_power': 1.20,
                'off_power': 0.65,
                'off_duration': 90,
                'duration': 20
            },
            '2': {
                'structure': '15min warmup Z2, 10x 25sec @ 125% FTP with 80sec @ 68% FTP recovery',
                'execution': 'More reps, slightly longer efforts. Develop repeatable snap',
                'intervals': (10, 25),
                'on_power': 1.25,
                'off_power': 0.68,
                'off_duration': 80,
                'duration': 25
            },
            '3': {
                'structure': '15min warmup Z2, 10x 30sec @ 130% FTP with 75sec @ 70% FTP recovery',
                'execution': 'Classic fartlek structure. Each effort should feel decisive',
                'intervals': (10, 30),
                'on_power': 1.30,
                'off_power': 0.70,
                'off_duration': 75,
                'duration': 30
            },
            '4': {
                'structure': '15min warmup Z2, 12x 30sec @ 135% FTP with 70sec @ 70% FTP recovery',
                'execution': 'Increased volume with tighter recovery. Simulate race surges',
                'intervals': (12, 30),
                'on_power': 1.35,
                'off_power': 0.70,
                'off_duration': 70,
                'duration': 30
            },
            '5': {
                'structure': '15min warmup Z2, 12x 35sec @ 140% FTP with 65sec @ 72% FTP recovery',
                'execution': 'Extended efforts with compressed recovery. Race-decisive power',
                'intervals': (12, 35),
                'on_power': 1.40,
                'off_power': 0.72,
                'off_duration': 65,
                'duration': 35
            },
            '6': {
                'structure': '15min warmup Z2, 15x 40sec @ 150% FTP with 60sec @ 75% FTP recovery',
                'execution': 'Maximum fartlek. 15 race-intensity surges. Empty every match',
                'intervals': (15, 40),
                'on_power': 1.50,
                'off_power': 0.75,
                'off_duration': 60,
                'duration': 40
            }
        }
    },
    {
        'name': 'Attacks and Repeatability',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 5min tempo @ 82% FTP, 5x 30sec @ 130% FTP with 3min @ 82% recovery',
                'execution': 'Simulate race attacks from tempo riding. Recover at tempo, not easy',
                'cadence_prescription': 'Attacks: 100-110rpm, Tempo: 85-95rpm',
                'cadence': 95,
                'position_prescription': 'Attacks: out of saddle, Tempo: seated',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'segments': _attack_reps(300, 0.82, 5, 30, 1.30, 180, 0.82),
            },
            '2': {
                'structure': '15min warmup Z2, 5min tempo @ 83%, 6x 40sec @ 140% FTP with 3min @ 83% recovery',
                'execution': 'Longer attacks, incomplete recovery. Building repeatability',
                'segments': _attack_reps(300, 0.83, 6, 40, 1.40, 180, 0.83),
            },
            '3': {
                'structure': '15min warmup Z2, 5min tempo @ 84%, 6x 45sec @ 150% FTP with 2.5min @ 84% recovery',
                'execution': 'Higher attack power with compressed recovery at tempo',
                'segments': _attack_reps(300, 0.84, 6, 45, 1.50, 150, 0.84),
            },
            '4': {
                'structure': '15min warmup Z2, 5min tempo @ 85%, 7x 50sec @ 160% FTP with 2.5min @ 85% recovery',
                'execution': 'Seven attacks. Fatigue accumulates — later attacks test true repeatability',
                'segments': _attack_reps(300, 0.85, 7, 50, 1.60, 150, 0.85),
            },
            '5': {
                'structure': '15min warmup Z2, 5min tempo @ 85%, 8x 55sec @ 170% FTP with 2min @ 85% recovery',
                'execution': 'Eight attacks with minimal recovery. Race crunch time simulation',
                'segments': _attack_reps(300, 0.85, 8, 55, 1.70, 120, 0.85),
            },
            '6': {
                'structure': '15min warmup Z2, 5min tempo @ 85%, 8x 60sec @ 180% FTP with 2min @ 85% recovery',
                'execution': 'Maximum attack protocol. Near-sprint power with tempo recovery',
                'segments': _attack_reps(300, 0.85, 8, 60, 1.80, 120, 0.85),
            }
        }
    },
    {
        'name': 'Kitchen Sink All-Systems',
        'levels': {
            '1': {
                'structure': '10min warmup Z2, 10min Z2, 8min tempo, 6min threshold, 3min VO2max, 2x 15sec sprint, cooldown',
                'execution': 'Touch every energy system in one session. Progressive intensity build',
                'cadence_prescription': 'Varies by zone — match effort to cadence',
                'cadence': 90,
                'position_prescription': 'Varies by effort type',
                'timing_prescription': 'Fresh',
                'fueling': '60-80g CHO/hr',
                'segments': [
                    {'type': 'steady', 'duration': 600, 'power': 0.65},
                    {'type': 'steady', 'duration': 480, 'power': 0.80},
                    {'type': 'steady', 'duration': 360, 'power': 0.95},
                    {'type': 'steady', 'duration': 180, 'power': 1.10},
                    {'type': 'steady', 'duration': 15, 'power': 1.50},
                    {'type': 'steady', 'duration': 60, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.50},
                ]
            },
            '2': {
                'structure': '10min warmup Z2, 12min Z2, 10min tempo, 8min threshold, 4min VO2max, 3x 15sec sprint, cooldown',
                'execution': 'Extended at each zone. More time in the pain cave',
                'segments': [
                    {'type': 'steady', 'duration': 720, 'power': 0.65},
                    {'type': 'steady', 'duration': 600, 'power': 0.80},
                    {'type': 'steady', 'duration': 480, 'power': 0.96},
                    {'type': 'steady', 'duration': 240, 'power': 1.12},
                    {'type': 'steady', 'duration': 15, 'power': 1.55},
                    {'type': 'steady', 'duration': 60, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.55},
                    {'type': 'steady', 'duration': 60, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.55},
                ]
            },
            '3': {
                'structure': '10min warmup Z2, 15min Z2, 12min tempo, 10min threshold, 5min VO2max, 4x 15sec sprint, cooldown',
                'execution': 'Full system stress. Manage fueling as intensity builds',
                'segments': [
                    {'type': 'steady', 'duration': 900, 'power': 0.65},
                    {'type': 'steady', 'duration': 720, 'power': 0.82},
                    {'type': 'steady', 'duration': 600, 'power': 0.97},
                    {'type': 'steady', 'duration': 300, 'power': 1.13},
                    {'type': 'steady', 'duration': 15, 'power': 1.60},
                    {'type': 'steady', 'duration': 45, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.60},
                    {'type': 'steady', 'duration': 45, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.60},
                    {'type': 'steady', 'duration': 45, 'power': 0.55},
                    {'type': 'steady', 'duration': 15, 'power': 1.60},
                ]
            },
            '4': {
                'structure': '10min warmup Z2, 18min Z2, 14min tempo, 12min threshold, 6min VO2max, 5x 20sec sprint, cooldown',
                'execution': 'Extended all-systems session. Deeper into each zone',
                'segments': [
                    {'type': 'steady', 'duration': 1080, 'power': 0.65},
                    {'type': 'steady', 'duration': 840, 'power': 0.83},
                    {'type': 'steady', 'duration': 720, 'power': 0.98},
                    {'type': 'steady', 'duration': 360, 'power': 1.15},
                    {'type': 'steady', 'duration': 20, 'power': 1.65},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.65},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.65},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.65},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.65},
                ]
            },
            '5': {
                'structure': '10min warmup Z2, 20min Z2, 15min tempo, 15min threshold, 8min VO2max, 6x 20sec sprint, cooldown',
                'execution': 'Near-maximum kitchen sink. Every system challenged deeply',
                'segments': [
                    {'type': 'steady', 'duration': 1200, 'power': 0.66},
                    {'type': 'steady', 'duration': 900, 'power': 0.84},
                    {'type': 'steady', 'duration': 900, 'power': 0.99},
                    {'type': 'steady', 'duration': 480, 'power': 1.16},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.70},
                ]
            },
            '6': {
                'structure': '10min warmup Z2, 25min Z2, 18min tempo, 18min threshold, 10min VO2max, 8x 20sec sprint, cooldown',
                'execution': 'Maximum all-systems. Race simulation touching every zone',
                'segments': [
                    {'type': 'steady', 'duration': 1500, 'power': 0.67},
                    {'type': 'steady', 'duration': 1080, 'power': 0.85},
                    {'type': 'steady', 'duration': 1080, 'power': 1.00},
                    {'type': 'steady', 'duration': 600, 'power': 1.18},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                    {'type': 'steady', 'duration': 40, 'power': 0.55},
                    {'type': 'steady', 'duration': 20, 'power': 1.75},
                ]
            }
        }
    },
]


# =============================================================================
# DURABILITY ADDITIONS: Late-Race VO2max
# =============================================================================

DURABILITY_ADVANCED = [
    {
        'name': 'Late-Race VO2max',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 60min endurance @ 68% FTP, then 3x 3min @ 106% FTP with 3min recovery',
                'execution': 'Pre-fatigue then VO2max. Tests ability to produce power when tired',
                'cadence_prescription': 'Endurance: 80-90rpm, VO2max: 90-100rpm',
                'cadence': 90,
                'position_prescription': 'Seated throughout',
                'timing_prescription': 'Allow full ride time',
                'fueling': '60-80g CHO/hr — practice race fueling',
                'tired_vo2': True,
                'base_duration': 3600,
                'base_power': 0.68,
                'intervals': (3, 180),
                'on_power': 1.06,
                'off_power': 0.55,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 70min endurance @ 69% FTP, then 3x 4min @ 108% FTP with 3min recovery',
                'execution': 'Longer preload, extended VO2 intervals. Mental game of going hard when tired',
                'tired_vo2': True,
                'base_duration': 4200,
                'base_power': 0.69,
                'intervals': (3, 240),
                'on_power': 1.08,
                'off_power': 0.55,
                'off_duration': 180
            },
            '3': {
                'structure': '15min warmup Z2, 75min endurance @ 70% FTP, then 4x 4min @ 110% FTP with 3min recovery',
                'execution': 'Four VO2max efforts after 75min of riding. Race-specific durability',
                'tired_vo2': True,
                'base_duration': 4500,
                'base_power': 0.70,
                'intervals': (4, 240),
                'on_power': 1.10,
                'off_power': 0.55,
                'off_duration': 180
            },
            '4': {
                'structure': '15min warmup Z2, 80min endurance @ 70% FTP, then 4x 5min @ 112% FTP with 3min recovery',
                'execution': 'Extended preload and VO2 duration. This is where gravel races are won',
                'tired_vo2': True,
                'base_duration': 4800,
                'base_power': 0.70,
                'intervals': (4, 300),
                'on_power': 1.12,
                'off_power': 0.55,
                'off_duration': 180
            },
            '5': {
                'structure': '15min warmup Z2, 85min endurance @ 71% FTP, then 5x 4min @ 114% FTP with 2.5min recovery',
                'execution': 'Five VO2max efforts after nearly 90min. Shortened recovery adds difficulty',
                'tired_vo2': True,
                'base_duration': 5100,
                'base_power': 0.71,
                'intervals': (5, 240),
                'on_power': 1.14,
                'off_power': 0.55,
                'off_duration': 150
            },
            '6': {
                'structure': '15min warmup Z2, 90min endurance @ 72% FTP, then 5x 5min @ 115% FTP with 2.5min recovery',
                'execution': 'Maximum durability protocol. 90min preload then race-intensity VO2max',
                'tired_vo2': True,
                'base_duration': 5400,
                'base_power': 0.72,
                'intervals': (5, 300),
                'on_power': 1.15,
                'off_power': 0.55,
                'off_duration': 150
            }
        }
    },
]


# =============================================================================
# ENDURANCE ADDITIONS: Heat Acclimation Protocol
# =============================================================================

ENDURANCE_ADVANCED = [
    {
        'name': 'Heat Acclimation Protocol',
        'levels': {
            '1': {
                'structure': '10min warmup Z2, 50min ride: endurance @ 65% FTP with 2x 5min thermal blocks @ 72% FTP',
                'execution': 'Structured heat adaptation. Thermal blocks raise core temp. Hydrate aggressively',
                'cadence_prescription': '80-90rpm',
                'cadence': 85,
                'position_prescription': 'Seated, minimize cooling',
                'timing_prescription': 'Hottest part of day or overdressed',
                'fueling': '60-80g CHO/hr, 1L+ fluid/hr',
                'segments': _base_with_efforts(3000, [(300, 0.72)] * 2, 0.65),
            },
            '2': {
                'structure': '10min warmup Z2, 60min ride: endurance @ 66% FTP with 3x 5min thermal blocks @ 73% FTP',
                'execution': 'Three thermal stress blocks. Monitor RPE — stop if dizzy or nauseous',
                'segments': _base_with_efforts(3600, [(300, 0.73)] * 3, 0.66),
            },
            '3': {
                'structure': '10min warmup Z2, 70min ride: endurance @ 67% FTP with 3x 7min thermal blocks @ 74% FTP',
                'execution': 'Extended thermal blocks. Body should be adapting — sweating earlier, lower HR',
                'segments': _base_with_efforts(4200, [(420, 0.74)] * 3, 0.67),
            },
            '4': {
                'structure': '10min warmup Z2, 75min ride: endurance @ 68% FTP with 4x 7min thermal blocks @ 75% FTP',
                'execution': 'Four thermal stress blocks. Progressive adaptation protocol',
                'segments': _base_with_efforts(4500, [(420, 0.75)] * 4, 0.68),
            },
            '5': {
                'structure': '10min warmup Z2, 80min ride: endurance @ 69% FTP with 4x 10min thermal blocks @ 76% FTP',
                'execution': 'Extended thermal blocks at higher power. Deep heat adaptation stimulus',
                'segments': _base_with_efforts(4800, [(600, 0.76)] * 4, 0.69),
            },
            '6': {
                'structure': '10min warmup Z2, 90min ride: endurance @ 70% FTP with 5x 10min thermal blocks @ 78% FTP',
                'execution': 'Maximum heat protocol. 90min with aggressive thermal stress. Full race heat prep',
                'segments': _base_with_efforts(5400, [(600, 0.78)] * 5, 0.70),
            }
        }
    },
]


# =============================================================================
# SPRINT_NEUROMUSCULAR ADDITIONS: Burst Intervals
# =============================================================================

SPRINT_ADVANCED = [
    {
        'name': 'Burst Intervals',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 45min ride: endurance @ 65% FTP with 8x 10sec bursts @ 150% FTP',
                'execution': 'Neuromuscular bursts within endurance riding. Explosive, then immediately settle',
                'cadence_prescription': 'Bursts: 110+rpm, Endurance: 80-90rpm',
                'cadence': 85,
                'position_prescription': 'Bursts: standing, Endurance: seated',
                'timing_prescription': 'After warmup',
                'fueling': '60-70g CHO/hr',
                'segments': _base_with_efforts(2700, [(10, 1.50)] * 8, 0.65),
            },
            '2': {
                'structure': '15min warmup Z2, 50min ride: endurance @ 66% FTP with 10x 10sec bursts @ 160% FTP',
                'execution': 'More bursts, higher power. Develop snap and neuromuscular recruitment',
                'segments': _base_with_efforts(3000, [(10, 1.60)] * 10, 0.66),
            },
            '3': {
                'structure': '15min warmup Z2, 55min ride: endurance @ 67% FTP with 12x 12sec bursts @ 170% FTP',
                'execution': 'Twelve bursts, longer duration. Scattered to simulate race demands',
                'segments': _base_with_efforts(3300, [(12, 1.70)] * 12, 0.67),
            },
            '4': {
                'structure': '15min warmup Z2, 60min ride: endurance @ 68% FTP with 12x 13sec bursts @ 180% FTP',
                'execution': 'Higher burst power, longer ride. Race-intensity neuromuscular work',
                'segments': _base_with_efforts(3600, [(13, 1.80)] * 12, 0.68),
            },
            '5': {
                'structure': '15min warmup Z2, 65min ride: endurance @ 69% FTP with 14x 14sec bursts @ 190% FTP',
                'execution': 'Fourteen high-power bursts. Simulates constant race accelerations',
                'segments': _base_with_efforts(3900, [(14, 1.90)] * 14, 0.69),
            },
            '6': {
                'structure': '15min warmup Z2, 70min ride: endurance @ 70% FTP with 15x 15sec bursts @ 200% FTP',
                'execution': 'Maximum burst protocol. 15 all-out neuromuscular efforts. Race-day snap',
                'segments': _base_with_efforts(4200, [(15, 2.00)] * 15, 0.70),
            }
        }
    },
]


# =============================================================================
# GRAVEL_SPECIFIC ADDITIONS: Gravel Race Simulation
# =============================================================================

def _gravel_sim_efforts(num_sectors, sector_dur, sector_power,
                        num_surges, surge_dur, surge_power,
                        sprint_finish=False):
    """Build interleaved sector/surge effort list for gravel race sim."""
    efforts = []
    surge_interval = max(1, num_sectors // max(num_surges, 1))
    sector_count = 0
    surge_count = 0
    for _ in range(num_sectors):
        efforts.append((sector_dur, sector_power))
        sector_count += 1
        if surge_count < num_surges and sector_count % surge_interval == 0:
            efforts.append((surge_dur, surge_power))
            surge_count += 1
    while surge_count < num_surges:
        efforts.append((surge_dur, surge_power))
        surge_count += 1
    if sprint_finish:
        efforts.append((30, 1.50))
    return efforts


GRAVEL_ADVANCED = [
    {
        'name': 'Gravel Race Simulation',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2hr structured ride: Z2 @ 65% FTP with 3 gravel sectors @ 105% (3min each), 2 tempo surges @ 82% (5min each)',
                'execution': 'Race simulation with sectors. Practice fueling every 30min. Settle quickly after efforts',
                'cadence_prescription': 'Z2: 80-90rpm, Sectors: 70-85rpm (gravel cadence)',
                'cadence': 85,
                'position_prescription': 'Varies — practice positions for all terrain',
                'timing_prescription': 'Weekend long ride slot',
                'fueling': '80-90g CHO/hr — practice race nutrition plan',
                'segments': _base_with_efforts(
                    7200,
                    _gravel_sim_efforts(3, 180, 1.05, 2, 300, 0.82),
                    0.65
                ),
            },
            '2': {
                'structure': '15min warmup Z2, 2.5hr ride: Z2 @ 65% FTP with 4 sectors @ 107% (3min), 2 surges @ 83% (5min)',
                'execution': 'Extended simulation. Four sectors with increasing intensity in later sectors',
                'segments': _base_with_efforts(
                    9000,
                    _gravel_sim_efforts(4, 180, 1.07, 2, 300, 0.83),
                    0.65
                ),
            },
            '3': {
                'structure': '15min warmup Z2, 3hr ride: Z2 @ 65% FTP with 5 sectors @ 108% (4min), 3 surges @ 84% (5min)',
                'execution': 'Three-hour race simulation. Nail the fueling — 80-90g CHO/hr throughout',
                'segments': _base_with_efforts(
                    10800,
                    _gravel_sim_efforts(5, 240, 1.08, 3, 300, 0.84),
                    0.65
                ),
            },
            '4': {
                'structure': '15min warmup Z2, 3.5hr ride: Z2 @ 65% FTP with 6 sectors @ 110% (4min), 3 surges @ 85% (5min)',
                'execution': 'Six sectors across 3.5 hours. Simulate late-race fatigue decisions',
                'segments': _base_with_efforts(
                    12600,
                    _gravel_sim_efforts(6, 240, 1.10, 3, 300, 0.85),
                    0.65
                ),
            },
            '5': {
                'structure': '15min warmup Z2, 4hr ride: Z2 @ 65% FTP with 7 sectors @ 112% (5min), 4 surges @ 85% (5min)',
                'execution': 'Four-hour simulation. Deep into race-length fatigue. Manage power late',
                'segments': _base_with_efforts(
                    14400,
                    _gravel_sim_efforts(7, 300, 1.12, 4, 300, 0.85),
                    0.65
                ),
            },
            '6': {
                'structure': '15min warmup Z2, 4.5hr ride: Z2 @ 65% FTP with 8 sectors @ 115% (5min), 4 surges @ 85% (5min), sprint finish',
                'execution': 'Maximum race simulation. Full ultra-distance prep with fueling and pacing practice',
                'segments': _base_with_efforts(
                    16200,
                    _gravel_sim_efforts(8, 300, 1.15, 4, 300, 0.85, sprint_finish=True),
                    0.65
                ),
            }
        }
    },
]


# =============================================================================
# INSCYD ADDITIONS: FatMax/VLamax Suppression, Glycolytic Power
# =============================================================================

INSCYD_ADVANCED = [
    {
        'name': 'FatMax VLamax Suppression',
        'levels': {
            '1': {
                'structure': '10min warmup Z2, 80min ride: endurance @ 65% FTP with 3x 30sec accelerations @ 85% FTP',
                'execution': 'Extended Z2 with brief tempo pops to suppress VLamax. Stay aerobic',
                'cadence_prescription': '80-90rpm (steady)',
                'cadence': 85,
                'position_prescription': 'Seated, relaxed',
                'timing_prescription': 'Fasted or low-glycogen preferred',
                'fueling': '40-50g CHO/hr (deliberately lower)',
                'segments': _base_with_efforts(4800, [(30, 0.85)] * 3, 0.65),
            },
            '2': {
                'structure': '10min warmup Z2, 100min ride: endurance @ 67% FTP with 4x 30sec @ 85% FTP',
                'execution': 'Longer Z2 base with more accelerations. Fat oxidation adaptation',
                'segments': _base_with_efforts(6000, [(30, 0.85)] * 4, 0.67),
            },
            '3': {
                'structure': '10min warmup Z2, 120min ride: endurance @ 68% FTP with 5x 30sec @ 85% FTP',
                'execution': 'Two-hour VLamax suppression session. Stay in fat-burning zone',
                'segments': _base_with_efforts(7200, [(30, 0.85)] * 5, 0.68),
            },
            '4': {
                'structure': '10min warmup Z2, 140min ride: endurance @ 70% FTP with 6x 30sec @ 85% FTP',
                'execution': 'Extended session at upper Z2. Metabolic crossover should be shifting',
                'segments': _base_with_efforts(8400, [(30, 0.85)] * 6, 0.70),
            },
            '5': {
                'structure': '10min warmup Z2, 160min ride: endurance @ 72% FTP with 7x 30sec @ 85% FTP',
                'execution': 'Near-maximum VLamax suppression volume. Deep aerobic adaptation',
                'segments': _base_with_efforts(9600, [(30, 0.85)] * 7, 0.72),
            },
            '6': {
                'structure': '10min warmup Z2, 180min ride: endurance @ 75% FTP with 8x 30sec @ 85% FTP',
                'execution': 'Maximum FatMax protocol. 3-hour session at top of Z2 with VLamax suppression pops',
                'segments': _base_with_efforts(10800, [(30, 0.85)] * 8, 0.75),
            }
        }
    },
    {
        'name': 'Glycolytic Power',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 6x 15sec @ 150% FTP with 3min recovery between',
                'execution': 'Short max efforts to develop glycolytic power. Full recovery between reps',
                'cadence_prescription': '100-120rpm (high power output)',
                'cadence': 110,
                'position_prescription': 'Standing for efforts, seated recovery',
                'timing_prescription': 'Fresh, well-fueled',
                'fueling': '60-70g CHO/hr',
                'intervals': (6, 15),
                'on_power': 1.50,
                'off_power': 0.55,
                'off_duration': 180,
                'duration': 15
            },
            '2': {
                'structure': '15min warmup Z2, 8x 20sec @ 160% FTP with 3min recovery',
                'execution': 'Longer efforts at higher power. Push glycolytic system harder',
                'intervals': (8, 20),
                'on_power': 1.60,
                'off_power': 0.55,
                'off_duration': 180,
                'duration': 20
            },
            '3': {
                'structure': '15min warmup Z2, 8x 30sec @ 170% FTP with 3min recovery',
                'execution': 'Classic glycolytic development. 30sec all-out with full recovery',
                'intervals': (8, 30),
                'on_power': 1.70,
                'off_power': 0.55,
                'off_duration': 180,
                'duration': 30
            },
            '4': {
                'structure': '15min warmup Z2, 10x 30sec @ 180% FTP with 2.5min recovery',
                'execution': 'Higher volume, compressed recovery. Building glycolytic capacity',
                'intervals': (10, 30),
                'on_power': 1.80,
                'off_power': 0.55,
                'off_duration': 150,
                'duration': 30
            },
            '5': {
                'structure': '15min warmup Z2, 10x 40sec @ 185% FTP with 2.5min recovery',
                'execution': 'Extended glycolytic efforts. Deep into anaerobic territory',
                'intervals': (10, 40),
                'on_power': 1.85,
                'off_power': 0.55,
                'off_duration': 150,
                'duration': 40
            },
            '6': {
                'structure': '15min warmup Z2, 12x 45sec @ 200% FTP with 2min recovery',
                'execution': 'Maximum glycolytic protocol. Near-sprint power for extended reps',
                'intervals': (12, 45),
                'on_power': 2.00,
                'off_power': 0.55,
                'off_duration': 120,
                'duration': 45
            }
        }
    },
]


# =============================================================================
# COMBINED EXPORT DICTIONARY
# =============================================================================

ADVANCED_ARCHETYPES = {
    'VO2max': VO2MAX_ADVANCED,
    'TT_Threshold': THRESHOLD_ADVANCED,
    'Race_Simulation': RACE_SIM_ADVANCED,
    'Durability': DURABILITY_ADVANCED,
    'Endurance': ENDURANCE_ADVANCED,
    'Sprint_Neuromuscular': SPRINT_ADVANCED,
    'Gravel_Specific': GRAVEL_ADVANCED,
    'INSCYD': INSCYD_ADVANCED,
}
