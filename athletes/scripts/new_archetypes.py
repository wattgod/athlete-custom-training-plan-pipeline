#!/usr/bin/env python3
"""
New archetype additions for the Gravel God training system.
Aligned with polarized (80/20) training philosophy.
No Sweet Spot - uses G-Spot (87-92% FTP) sparingly for durability work only.
"""

# =============================================================================
# VO2MAX ADDITIONS
# =============================================================================

VO2MAX_NEW = [
    {
        'name': '5x3 VO2 Classic',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x3min @ 108-112% FTP, 3min recovery between',
                'execution': 'Learning the format - shorter intervals, more repeats. Control the power',
                'cadence_prescription': '90-100rpm (high turnover)',
                'cadence': 95,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (4, 180),
                'on_power': 1.10,
                'off_power': 0.55,
                'duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 5x3min @ 110-115% FTP, 3min recovery between',
                'execution': 'Building volume - control the power, don\'t go too deep early',
                'intervals': (5, 180),
                'on_power': 1.12,
                'off_power': 0.55,
                'duration': 180
            },
            '3': {
                'structure': '15min warmup Z2, 6x3min @ 112-117% FTP, 3min recovery between',
                'execution': 'Full recovery between efforts. Build power through each interval',
                'intervals': (6, 180),
                'on_power': 1.15,
                'off_power': 0.55,
                'duration': 180
            },
            '4': {
                'structure': '15min warmup Z2, 6x3min @ 115-120% FTP, 2.5min recovery between',
                'execution': 'Reduced recovery - building tolerance. Control early, push late',
                'intervals': (6, 180),
                'on_power': 1.17,
                'off_power': 0.55,
                'duration': 180
            },
            '5': {
                'structure': '15min warmup Z2, 7x3min @ 118-123% FTP, 2.5min recovery between',
                'execution': 'Extended volume - maximum sustainable power',
                'intervals': (7, 180),
                'on_power': 1.20,
                'off_power': 0.55,
                'duration': 180
            },
            '6': {
                'structure': '15min warmup Z2, 8x3min @ 120-125% FTP, 2min recovery between',
                'execution': 'Maximum development - empty the tank on final intervals',
                'intervals': (8, 180),
                'on_power': 1.22,
                'off_power': 0.55,
                'duration': 180
            }
        }
    },
    {
        'name': 'Descending VO2 Pyramid',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 1 set: 4min @ 108% + 3min @ 110% + 2min @ 115% + 1min @ 120% FTP, 3min recovery between efforts',
                'execution': 'Learning the format - descending duration, ascending intensity',
                'cadence_prescription': '90-100rpm (high turnover)',
                'cadence': 95,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'pyramid': True,
                'efforts': [
                    {'duration': 240, 'power': 1.08},
                    {'duration': 180, 'power': 1.10},
                    {'duration': 120, 'power': 1.15},
                    {'duration': 60, 'power': 1.20}
                ],
                'recovery_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 1.5 sets: 4min @ 110% + 3min @ 112% + 2min @ 117% + 1min @ 122% FTP, 5min between sets',
                'execution': 'Building volume - maintain form through intensity increase',
                'pyramid': True,
                'sets': 1.5,
                'efforts': [
                    {'duration': 240, 'power': 1.10},
                    {'duration': 180, 'power': 1.12},
                    {'duration': 120, 'power': 1.17},
                    {'duration': 60, 'power': 1.22}
                ],
                'recovery_duration': 180,
                'set_recovery': 300
            },
            '3': {
                'structure': '15min warmup Z2, 2 sets: 4min @ 112% + 3min @ 115% + 2min @ 118% + 1min @ 125% FTP, 5min between sets',
                'execution': 'Full pyramid sets - mental game of knowing it gets shorter',
                'pyramid': True,
                'sets': 2,
                'efforts': [
                    {'duration': 240, 'power': 1.12},
                    {'duration': 180, 'power': 1.15},
                    {'duration': 120, 'power': 1.18},
                    {'duration': 60, 'power': 1.25}
                ],
                'recovery_duration': 180,
                'set_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 2 sets: 4min @ 115% + 3min @ 117% + 2min @ 120% + 1min @ 128% FTP, 5min between sets',
                'execution': 'Increased intensity - push hard on short efforts',
                'pyramid': True,
                'sets': 2,
                'efforts': [
                    {'duration': 240, 'power': 1.15},
                    {'duration': 180, 'power': 1.17},
                    {'duration': 120, 'power': 1.20},
                    {'duration': 60, 'power': 1.28}
                ],
                'recovery_duration': 180,
                'set_recovery': 300
            },
            '5': {
                'structure': '15min warmup Z2, 2.5 sets: 4min @ 117% + 3min @ 120% + 2min @ 123% + 1min @ 130% FTP, 5min between sets',
                'execution': 'Extended volume - race-realistic intensity changes',
                'pyramid': True,
                'sets': 2.5,
                'efforts': [
                    {'duration': 240, 'power': 1.17},
                    {'duration': 180, 'power': 1.20},
                    {'duration': 120, 'power': 1.23},
                    {'duration': 60, 'power': 1.30}
                ],
                'recovery_duration': 180,
                'set_recovery': 300
            },
            '6': {
                'structure': '15min warmup Z2, 3 sets: 4min @ 118% + 3min @ 122% + 2min @ 125% + 1min @ 135% FTP, 4min between sets',
                'execution': 'Maximum development - reduced recovery between sets, all-out final efforts',
                'pyramid': True,
                'sets': 3,
                'efforts': [
                    {'duration': 240, 'power': 1.18},
                    {'duration': 180, 'power': 1.22},
                    {'duration': 120, 'power': 1.25},
                    {'duration': 60, 'power': 1.35}
                ],
                'recovery_duration': 180,
                'set_recovery': 240
            }
        }
    },
    {
        'name': 'Norwegian 4x8',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x8min @ 88-90% HRmax (~105-108% FTP), 4min recovery between',
                'execution': 'Learning the Seiler format - controlled intensity, full recovery',
                'cadence_prescription': '85-95rpm (race cadence)',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (3, 480),
                'on_power': 1.06,
                'off_power': 0.55,
                'duration': 480
            },
            '2': {
                'structure': '15min warmup Z2, 4x8min @ 88-90% HRmax (~107-110% FTP), 4min recovery between',
                'execution': 'Classic Seiler format - research-backed optimal duration for masters',
                'intervals': (4, 480),
                'on_power': 1.08,
                'off_power': 0.55,
                'duration': 480
            },
            '3': {
                'structure': '15min warmup Z2, 4x8min @ 90% HRmax (~108-112% FTP), 3.5min recovery between',
                'execution': 'Reduced recovery - building tolerance while maintaining duration',
                'intervals': (4, 480),
                'on_power': 1.10,
                'off_power': 0.55,
                'duration': 480
            },
            '4': {
                'structure': '15min warmup Z2, 5x8min @ 90% HRmax (~110-113% FTP), 3.5min recovery between',
                'execution': 'Extended volume - accumulating time at VO2max workload',
                'intervals': (5, 480),
                'on_power': 1.11,
                'off_power': 0.55,
                'duration': 480
            },
            '5': {
                'structure': '15min warmup Z2, 5x8min @ 90-92% HRmax (~112-115% FTP), 3min recovery between',
                'execution': 'Increased intensity with reduced recovery - near race simulation',
                'intervals': (5, 480),
                'on_power': 1.13,
                'off_power': 0.55,
                'duration': 480
            },
            '6': {
                'structure': '15min warmup Z2, 6x8min @ 92% HRmax (~113-118% FTP), 3min recovery between',
                'execution': 'Maximum sustainable volume at VO2max - 48min total work',
                'intervals': (6, 480),
                'on_power': 1.15,
                'off_power': 0.55,
                'duration': 480
            }
        }
    },
    {
        'name': 'VO2max with Loaded Recovery',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x (3min @ 115% FTP + 2min @ 85% FTP), 3min Z1 between sets',
                'execution': 'Learning the format - VO2 effort followed by tempo recovery, not Z1',
                'cadence_prescription': '90-100rpm on, 85-90rpm recovery',
                'cadence': 95,
                'position_prescription': 'Seated throughout',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'loaded_recovery': True,
                'intervals': (3, 300),
                'on_power': 1.15,
                'loaded_power': 0.85,
                'loaded_duration': 120,
                'off_power': 0.50,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 4x (3min @ 117% FTP + 2min @ 85% FTP), 3min Z1 between sets',
                'execution': 'Building volume - tempo recovery keeps HR elevated',
                'loaded_recovery': True,
                'intervals': (4, 300),
                'on_power': 1.17,
                'loaded_power': 0.85,
                'loaded_duration': 120,
                'off_power': 0.50,
                'off_duration': 180
            },
            '3': {
                'structure': '15min warmup Z2, 4x (3min @ 118% FTP + 2.5min @ 87% FTP), 2.5min Z1 between sets',
                'execution': 'Extended tempo recovery - more time above threshold',
                'loaded_recovery': True,
                'intervals': (4, 330),
                'on_power': 1.18,
                'loaded_power': 0.87,
                'loaded_duration': 150,
                'off_power': 0.50,
                'off_duration': 150
            },
            '4': {
                'structure': '15min warmup Z2, 5x (3min @ 120% FTP + 2.5min @ 88% FTP), 2.5min Z1 between sets',
                'execution': 'Increased volume and intensity - race simulation',
                'loaded_recovery': True,
                'intervals': (5, 330),
                'on_power': 1.20,
                'loaded_power': 0.88,
                'loaded_duration': 150,
                'off_power': 0.50,
                'off_duration': 150
            },
            '5': {
                'structure': '15min warmup Z2, 5x (3.5min @ 120% FTP + 2.5min @ 88% FTP), 2min Z1 between sets',
                'execution': 'Extended VO2 efforts - reduced full recovery',
                'loaded_recovery': True,
                'intervals': (5, 360),
                'on_power': 1.20,
                'loaded_power': 0.88,
                'loaded_duration': 150,
                'off_power': 0.50,
                'off_duration': 120
            },
            '6': {
                'structure': '15min warmup Z2, 6x (3.5min @ 122% FTP + 2.5min @ 90% FTP), 2min Z1 between sets',
                'execution': 'Maximum development - G-Spot recovery keeps legs burning',
                'loaded_recovery': True,
                'intervals': (6, 360),
                'on_power': 1.22,
                'loaded_power': 0.90,
                'loaded_duration': 150,
                'off_power': 0.50,
                'off_duration': 120
            }
        }
    }
]


# =============================================================================
# THRESHOLD/TT ADDITIONS
# =============================================================================

THRESHOLD_NEW = [
    {
        'name': 'Single Sustained Threshold',
        'levels': {
            '1': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x20min @ 95-98% FTP, 10min cooldown',
                'execution': 'Mental toughness builder - one long effort, no breaks. Start conservative',
                'cadence_prescription': '85-95rpm (race cadence)',
                'cadence': 90,
                'position_prescription': 'Seated, aero if comfortable',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'single_effort': True,
                'duration': 1200,
                'power': 0.96
            },
            '2': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x25min @ 96-99% FTP, 10min cooldown',
                'execution': 'Building duration - find your rhythm and lock in',
                'single_effort': True,
                'duration': 1500,
                'power': 0.97
            },
            '3': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x30min @ 97-100% FTP, 10min cooldown',
                'execution': 'Classic TT duration - steady, controlled power throughout',
                'single_effort': True,
                'duration': 1800,
                'power': 0.98
            },
            '4': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x35min @ 98-101% FTP, 10min cooldown',
                'execution': 'Extended threshold - break it into mental thirds',
                'single_effort': True,
                'duration': 2100,
                'power': 0.99
            },
            '5': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x40min @ 98-101% FTP, 10min cooldown',
                'execution': 'Race-realistic duration - this is your FTP test effort',
                'single_effort': True,
                'duration': 2400,
                'power': 1.00
            },
            '6': {
                'structure': '20min warmup Z2 with 2x1min openers, 1x45min @ 98-102% FTP, 10min cooldown',
                'execution': 'Maximum threshold duration - mental fortress training',
                'single_effort': True,
                'duration': 2700,
                'power': 1.00
            }
        }
    },
    {
        'name': 'Threshold Ramps',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2x12min ramp: start @ 90% FTP, increase 2% every 3min to finish @ 98%, 5min recovery',
                'execution': 'Learning progressive building - smooth power increases',
                'cadence_prescription': '85-95rpm throughout',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'ramp': True,
                'intervals': (2, 720),
                'start_power': 0.90,
                'end_power': 0.98,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 300
            },
            '2': {
                'structure': '15min warmup Z2, 2x15min ramp: start @ 88% FTP, increase 2% every 3min to finish @ 100%, 5min recovery',
                'execution': 'Extended ramp - teaches negative splitting',
                'ramp': True,
                'intervals': (2, 900),
                'start_power': 0.88,
                'end_power': 1.00,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 300
            },
            '3': {
                'structure': '15min warmup Z2, 2x15min ramp: start @ 88% FTP, increase 2% every 3min to finish @ 102%, 5min recovery',
                'execution': 'Building to supra-threshold finish - race simulation',
                'ramp': True,
                'intervals': (2, 900),
                'start_power': 0.88,
                'end_power': 1.02,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 300
            },
            '4': {
                'structure': '15min warmup Z2, 3x12min ramp: start @ 88% FTP, increase 2.5% every 3min to finish @ 100%, 5min recovery',
                'execution': 'Increased volume - three ramps with steeper progression',
                'ramp': True,
                'intervals': (3, 720),
                'start_power': 0.88,
                'end_power': 1.00,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 300
            },
            '5': {
                'structure': '15min warmup Z2, 3x15min ramp: start @ 87% FTP, increase 2% every 3min to finish @ 101%, 4min recovery',
                'execution': 'Reduced recovery - building threshold capacity under fatigue',
                'ramp': True,
                'intervals': (3, 900),
                'start_power': 0.87,
                'end_power': 1.01,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 240
            },
            '6': {
                'structure': '15min warmup Z2, 3x18min ramp: start @ 85% FTP, increase 2% every 3min to finish @ 101%, 4min recovery',
                'execution': 'Maximum ramp duration - start easy, finish at threshold',
                'ramp': True,
                'intervals': (3, 1080),
                'start_power': 0.85,
                'end_power': 1.01,
                'step_duration': 180,
                'off_power': 0.55,
                'off_duration': 240
            }
        }
    },
    {
        'name': 'Descending Threshold',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 12min @ 96% + 10min @ 98% + 8min @ 100% FTP, 5min recovery between',
                'execution': 'Learning the format - getting shorter and harder as you tire',
                'cadence_prescription': '85-95rpm (race cadence)',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'descending': True,
                'efforts': [
                    {'duration': 720, 'power': 0.96},
                    {'duration': 600, 'power': 0.98},
                    {'duration': 480, 'power': 1.00}
                ],
                'recovery_duration': 300
            },
            '2': {
                'structure': '15min warmup Z2, 15min @ 96% + 12min @ 98% + 8min @ 100% FTP, 5min recovery between',
                'execution': 'Building duration - longer opener, same progression',
                'descending': True,
                'efforts': [
                    {'duration': 900, 'power': 0.96},
                    {'duration': 720, 'power': 0.98},
                    {'duration': 480, 'power': 1.00}
                ],
                'recovery_duration': 300
            },
            '3': {
                'structure': '15min warmup Z2, 15min @ 97% + 12min @ 99% + 10min @ 101% FTP, 5min recovery between',
                'execution': 'Increased intensity - finish above threshold',
                'descending': True,
                'efforts': [
                    {'duration': 900, 'power': 0.97},
                    {'duration': 720, 'power': 0.99},
                    {'duration': 600, 'power': 1.01}
                ],
                'recovery_duration': 300
            },
            '4': {
                'structure': '15min warmup Z2, 15min @ 97% + 12min @ 100% + 10min @ 102% + 5min @ 105% FTP, 4min recovery between',
                'execution': 'Added 4th effort - finish with VO2 kick',
                'descending': True,
                'efforts': [
                    {'duration': 900, 'power': 0.97},
                    {'duration': 720, 'power': 1.00},
                    {'duration': 600, 'power': 1.02},
                    {'duration': 300, 'power': 1.05}
                ],
                'recovery_duration': 240
            },
            '5': {
                'structure': '15min warmup Z2, 18min @ 97% + 14min @ 100% + 10min @ 103% + 5min @ 108% FTP, 4min recovery between',
                'execution': 'Extended opener - race simulation with strong finish',
                'descending': True,
                'efforts': [
                    {'duration': 1080, 'power': 0.97},
                    {'duration': 840, 'power': 1.00},
                    {'duration': 600, 'power': 1.03},
                    {'duration': 300, 'power': 1.08}
                ],
                'recovery_duration': 240
            },
            '6': {
                'structure': '15min warmup Z2, 20min @ 97% + 15min @ 100% + 10min @ 103% + 5min @ 110% FTP, 3min recovery between',
                'execution': 'Maximum development - reduced recovery, strong VO2 finish',
                'descending': True,
                'efforts': [
                    {'duration': 1200, 'power': 0.97},
                    {'duration': 900, 'power': 1.00},
                    {'duration': 600, 'power': 1.03},
                    {'duration': 300, 'power': 1.10}
                ],
                'recovery_duration': 180
            }
        }
    }
]


# =============================================================================
# SPRINT/NEUROMUSCULAR ADDITIONS
# =============================================================================

SPRINT_NEW = [
    {
        'name': 'Attack Repeats',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x30sec @ 150% FTP all-out, 3min recovery between',
                'execution': 'Race-breaking efforts - simulate attacking off the front',
                'cadence_prescription': '100-120rpm (high power, high turnover)',
                'cadence': 110,
                'position_prescription': 'Out of saddle for first 10sec, then seated',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (4, 30),
                'on_power': 1.50,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 5x30sec @ 150% FTP all-out, 2.5min recovery between',
                'execution': 'Building volume - reduced recovery simulates race fatigue',
                'intervals': (5, 30),
                'on_power': 1.50,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 150
            },
            '3': {
                'structure': '15min warmup Z2, 6x30sec @ 150% FTP all-out, 2.5min recovery between',
                'execution': 'Increased volume - maintain power across all repeats',
                'intervals': (6, 30),
                'on_power': 1.50,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 150
            },
            '4': {
                'structure': '15min warmup Z2, 6x30sec @ 155% FTP all-out, 2min recovery between',
                'execution': 'Increased intensity, reduced recovery - attack training',
                'intervals': (6, 30),
                'on_power': 1.55,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 120
            },
            '5': {
                'structure': '15min warmup Z2, 7x30sec @ 155% FTP all-out, 2min recovery between',
                'execution': 'Extended volume - race-realistic attack frequency',
                'intervals': (7, 30),
                'on_power': 1.55,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 120
            },
            '6': {
                'structure': '15min warmup Z2, 8x30sec @ 160% FTP all-out, 1.5min recovery between',
                'execution': 'Maximum development - repeated attacks with minimal recovery',
                'intervals': (8, 30),
                'on_power': 1.60,
                'off_power': 0.50,
                'duration': 30,
                'off_duration': 90
            }
        }
    },
    {
        'name': 'Sprint Buildups',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2 sets: 10sec + 15sec + 20sec + 30sec @ max, 2min between efforts, 5min between sets',
                'execution': 'Learning the format - progressive duration, all-out efforts',
                'cadence_prescription': 'Max sustainable for each duration',
                'cadence': 95,
                'position_prescription': 'Out of saddle',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'buildup': True,
                'sets': 2,
                'efforts': [10, 15, 20, 30],
                'on_power': 1.80,  # Approximate max
                'effort_recovery': 120,
                'set_recovery': 300
            },
            '2': {
                'structure': '15min warmup Z2, 2 sets: 10sec + 15sec + 20sec + 30sec @ max, 1.5min between efforts, 5min between sets',
                'execution': 'Reduced recovery between efforts - building repeatability',
                'buildup': True,
                'sets': 2,
                'efforts': [10, 15, 20, 30],
                'on_power': 1.80,
                'effort_recovery': 90,
                'set_recovery': 300
            },
            '3': {
                'structure': '15min warmup Z2, 3 sets: 10sec + 15sec + 20sec + 30sec @ max, 1.5min between efforts, 5min between sets',
                'execution': 'Increased volume - three full sets',
                'buildup': True,
                'sets': 3,
                'efforts': [10, 15, 20, 30],
                'on_power': 1.80,
                'effort_recovery': 90,
                'set_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 3 sets: 10sec + 15sec + 20sec + 30sec + 45sec @ max, 1.5min between efforts, 4min between sets',
                'execution': 'Added 45sec effort - extended anaerobic duration',
                'buildup': True,
                'sets': 3,
                'efforts': [10, 15, 20, 30, 45],
                'on_power': 1.70,
                'effort_recovery': 90,
                'set_recovery': 240
            },
            '5': {
                'structure': '15min warmup Z2, 3 sets: 10sec + 15sec + 20sec + 30sec + 45sec @ max, 1min between efforts, 4min between sets',
                'execution': 'Reduced recovery - race simulation',
                'buildup': True,
                'sets': 3,
                'efforts': [10, 15, 20, 30, 45],
                'on_power': 1.70,
                'effort_recovery': 60,
                'set_recovery': 240
            },
            '6': {
                'structure': '15min warmup Z2, 4 sets: 10sec + 15sec + 20sec + 30sec + 45sec @ max, 1min between efforts, 3min between sets',
                'execution': 'Maximum development - four sets, minimal recovery',
                'buildup': True,
                'sets': 4,
                'efforts': [10, 15, 20, 30, 45],
                'on_power': 1.70,
                'effort_recovery': 60,
                'set_recovery': 180
            }
        }
    },
    {
        'name': 'Peak and Fade',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x (10sec MAX + 20sec @ 80% of sprint), 3min recovery between',
                'execution': 'Learning the format - explosive start, controlled fade',
                'cadence_prescription': 'Max then settle to 90-100rpm',
                'cadence': 95,
                'position_prescription': 'Standing start, sit after 10sec',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'peak_fade': True,
                'intervals': (4, 30),
                'peak_duration': 10,
                'peak_power': 2.00,  # Max sprint
                'fade_duration': 20,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 5x (10sec MAX + 20sec @ 80% of sprint), 2.5min recovery between',
                'execution': 'Building volume - maintain peak power across repeats',
                'peak_fade': True,
                'intervals': (5, 30),
                'peak_duration': 10,
                'peak_power': 2.00,
                'fade_duration': 20,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 150
            },
            '3': {
                'structure': '15min warmup Z2, 5x (12sec MAX + 25sec @ 80% of sprint), 2.5min recovery between',
                'execution': 'Extended efforts - longer peak, longer fade',
                'peak_fade': True,
                'intervals': (5, 37),
                'peak_duration': 12,
                'peak_power': 2.00,
                'fade_duration': 25,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 150
            },
            '4': {
                'structure': '15min warmup Z2, 6x (12sec MAX + 25sec @ 80% of sprint), 2min recovery between',
                'execution': 'Increased volume with reduced recovery',
                'peak_fade': True,
                'intervals': (6, 37),
                'peak_duration': 12,
                'peak_power': 2.00,
                'fade_duration': 25,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 120
            },
            '5': {
                'structure': '15min warmup Z2, 6x (15sec MAX + 25sec @ 80% of sprint), 2min recovery between',
                'execution': 'Extended peak duration - longer max effort',
                'peak_fade': True,
                'intervals': (6, 40),
                'peak_duration': 15,
                'peak_power': 2.00,
                'fade_duration': 25,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 120
            },
            '6': {
                'structure': '15min warmup Z2, 7x (15sec MAX + 30sec @ 80% of sprint), 1.5min recovery between',
                'execution': 'Maximum development - sprint contest simulation',
                'peak_fade': True,
                'intervals': (7, 45),
                'peak_duration': 15,
                'peak_power': 2.00,
                'fade_duration': 30,
                'fade_power': 1.20,
                'off_power': 0.50,
                'off_duration': 90
            }
        }
    },
    {
        'name': 'ILT Single Leg Training',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x1min single leg (alternating), 1min both legs between, Z2 power',
                'execution': 'Learning the format - focus on smooth pedal stroke, eliminate dead spots',
                'cadence_prescription': '70-80rpm (lower than normal for control)',
                'cadence': 75,
                'position_prescription': 'Seated, hands relaxed',
                'timing_prescription': 'Fresh or recovery day',
                'fueling': 'Normal hydration',
                'ilt': True,
                'intervals': (4, 60),
                'power': 0.70,  # Z2 power
                'cadence': 75,
                'off_duration': 60
            },
            '2': {
                'structure': '15min warmup Z2, 5x1min single leg (alternating), 1min both legs between, Z2 power',
                'execution': 'Building volume - maintain smooth stroke throughout',
                'ilt': True,
                'intervals': (5, 60),
                'power': 0.70,
                'cadence': 75,
                'off_duration': 60
            },
            '3': {
                'structure': '15min warmup Z2, 6x1min single leg (alternating), 45sec both legs between, Z2 power',
                'execution': 'Reduced recovery - building endurance in the pattern',
                'ilt': True,
                'intervals': (6, 60),
                'power': 0.70,
                'cadence': 80,
                'off_duration': 45
            },
            '4': {
                'structure': '15min warmup Z2, 6x90sec single leg (alternating), 45sec both legs between, Z2 power',
                'execution': 'Extended duration - longer single leg efforts',
                'ilt': True,
                'intervals': (6, 90),
                'power': 0.70,
                'cadence': 80,
                'off_duration': 45
            },
            '5': {
                'structure': '15min warmup Z2, 8x90sec single leg (alternating), 30sec both legs between, Z2 power',
                'execution': 'Increased volume - minimal recovery between legs',
                'ilt': True,
                'intervals': (8, 90),
                'power': 0.70,
                'cadence': 85,
                'off_duration': 30
            },
            '6': {
                'structure': '15min warmup Z2, 8x2min single leg (alternating), 30sec both legs between, Z2 power',
                'execution': 'Maximum duration - 2min single leg efforts for pedaling efficiency',
                'ilt': True,
                'intervals': (8, 120),
                'power': 0.70,
                'cadence': 85,
                'off_duration': 30
            }
        }
    }
]


# =============================================================================
# ANAEROBIC CAPACITY (NEW CATEGORY)
# =============================================================================

ANAEROBIC_CAPACITY = [
    {
        'name': '2min Killers',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x2min @ 115% FTP, 4min recovery between',
                'execution': 'Learning lactate tolerance - these hurt. Pace evenly, don\'t blow up',
                'cadence_prescription': '90-100rpm (high turnover reduces muscle tension)',
                'cadence': 95,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (3, 120),
                'on_power': 1.15,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 240
            },
            '2': {
                'structure': '15min warmup Z2, 4x2min @ 115% FTP, 4min recovery between',
                'execution': 'Building volume - maintain power across all repeats',
                'intervals': (4, 120),
                'on_power': 1.15,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 240
            },
            '3': {
                'structure': '15min warmup Z2, 4x2min @ 118% FTP, 3.5min recovery between',
                'execution': 'Increased intensity, reduced recovery - building tolerance',
                'intervals': (4, 120),
                'on_power': 1.18,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 210
            },
            '4': {
                'structure': '15min warmup Z2, 5x2min @ 118% FTP, 3min recovery between',
                'execution': 'Extended volume - race-breaking power',
                'intervals': (5, 120),
                'on_power': 1.18,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 180
            },
            '5': {
                'structure': '15min warmup Z2, 5x2min @ 120% FTP, 2.5min recovery between',
                'execution': 'Reduced recovery - simulates repeated attacks',
                'intervals': (5, 120),
                'on_power': 1.20,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 150
            },
            '6': {
                'structure': '15min warmup Z2, 6x2min @ 120% FTP, 2min recovery between',
                'execution': 'Maximum development - 12min total at race-breaking power',
                'intervals': (6, 120),
                'on_power': 1.20,
                'off_power': 0.50,
                'duration': 120,
                'off_duration': 120
            }
        }
    },
    {
        'name': '90sec Repeats',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x90sec @ 120% FTP, 3min recovery between',
                'execution': 'Short, sharp efforts - race-breaking intensity',
                'cadence_prescription': '95-105rpm (high turnover)',
                'cadence': 100,
                'position_prescription': 'Seated or standing as needed',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (4, 90),
                'on_power': 1.20,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 5x90sec @ 120% FTP, 3min recovery between',
                'execution': 'Building volume - maintain power consistency',
                'intervals': (5, 90),
                'on_power': 1.20,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 180
            },
            '3': {
                'structure': '15min warmup Z2, 5x90sec @ 122% FTP, 2.5min recovery between',
                'execution': 'Increased intensity with reduced recovery',
                'intervals': (5, 90),
                'on_power': 1.22,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 150
            },
            '4': {
                'structure': '15min warmup Z2, 6x90sec @ 122% FTP, 2.5min recovery between',
                'execution': 'Extended volume - attack repeatability',
                'intervals': (6, 90),
                'on_power': 1.22,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 150
            },
            '5': {
                'structure': '15min warmup Z2, 6x90sec @ 125% FTP, 2min recovery between',
                'execution': 'Reduced recovery at high intensity - race simulation',
                'intervals': (6, 90),
                'on_power': 1.25,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 120
            },
            '6': {
                'structure': '15min warmup Z2, 8x90sec @ 125% FTP, 1.5min recovery between',
                'execution': 'Maximum development - repeated race-breaking efforts',
                'intervals': (8, 90),
                'on_power': 1.25,
                'off_power': 0.50,
                'duration': 90,
                'off_duration': 90
            }
        }
    },
    {
        'name': '1min All-Out Repeats',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x1min @ 130% FTP, 3min recovery between',
                'execution': 'Maximum 1min power - neuromuscular + anaerobic',
                'cadence_prescription': '100-110rpm (high turnover)',
                'cadence': 105,
                'position_prescription': 'Standing start, sit as needed',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'intervals': (4, 60),
                'on_power': 1.30,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 180
            },
            '2': {
                'structure': '15min warmup Z2, 5x1min @ 130% FTP, 2.5min recovery between',
                'execution': 'Building volume with reduced recovery',
                'intervals': (5, 60),
                'on_power': 1.30,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 150
            },
            '3': {
                'structure': '15min warmup Z2, 5x1min @ 135% FTP, 2.5min recovery between',
                'execution': 'Increased intensity - approaching sprint territory',
                'intervals': (5, 60),
                'on_power': 1.35,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 150
            },
            '4': {
                'structure': '15min warmup Z2, 6x1min @ 135% FTP, 2min recovery between',
                'execution': 'Extended volume - repeatability under fatigue',
                'intervals': (6, 60),
                'on_power': 1.35,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 120
            },
            '5': {
                'structure': '15min warmup Z2, 7x1min @ 135% FTP, 1.5min recovery between',
                'execution': 'Minimal recovery - race simulation',
                'intervals': (7, 60),
                'on_power': 1.35,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 90
            },
            '6': {
                'structure': '15min warmup Z2, 8x1min @ 140% FTP, 1.5min recovery between',
                'execution': 'Maximum development - 8min total at near-max power',
                'intervals': (8, 60),
                'on_power': 1.40,
                'off_power': 0.50,
                'duration': 60,
                'off_duration': 90
            }
        }
    }
]


# =============================================================================
# DURABILITY ADDITIONS
# =============================================================================

DURABILITY_NEW = [
    {
        'name': 'Tired VO2max',
        'levels': {
            '1': {
                'structure': '2hr Z2 endurance, then 2x4min @ 110% FTP with 4min recovery',
                'execution': 'VO2max when exhausted - these will feel harder than fresh. Good.',
                'cadence_prescription': '90-100rpm (maintain turnover)',
                'cadence': 95,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Late-ride (after 2hr)',
                'fueling': '60-80g CHO/hr throughout - critical for late quality',
                'tired_vo2': True,
                'base_duration': 7200,
                'base_power': 0.70,
                'intervals': (2, 240),
                'on_power': 1.10,
                'off_power': 0.55,
                'off_duration': 240
            },
            '2': {
                'structure': '2.5hr Z2 endurance, then 3x4min @ 112% FTP with 4min recovery',
                'execution': 'Building volume - VO2max efforts after extended base',
                'tired_vo2': True,
                'base_duration': 9000,
                'base_power': 0.70,
                'intervals': (3, 240),
                'on_power': 1.12,
                'off_power': 0.55,
                'off_duration': 240
            },
            '3': {
                'structure': '2.5hr Z2 endurance, then 3x4min @ 115% FTP with 3.5min recovery',
                'execution': 'Increased intensity with reduced recovery',
                'tired_vo2': True,
                'base_duration': 9000,
                'base_power': 0.70,
                'intervals': (3, 240),
                'on_power': 1.15,
                'off_power': 0.55,
                'off_duration': 210
            },
            '4': {
                'structure': '3hr Z2 endurance, then 4x4min @ 115% FTP with 3min recovery',
                'execution': 'Extended base duration - race-realistic fatigue',
                'tired_vo2': True,
                'base_duration': 10800,
                'base_power': 0.70,
                'intervals': (4, 240),
                'on_power': 1.15,
                'off_power': 0.55,
                'off_duration': 180
            },
            '5': {
                'structure': '3.5hr Z2 endurance, then 4x4min @ 117% FTP with 3min recovery',
                'execution': 'Extended pre-load - this is Unbound simulation',
                'tired_vo2': True,
                'base_duration': 12600,
                'base_power': 0.70,
                'intervals': (4, 240),
                'on_power': 1.17,
                'off_power': 0.55,
                'off_duration': 180
            },
            '6': {
                'structure': '4hr Z2 endurance, then 5x4min @ 118% FTP with 2.5min recovery',
                'execution': 'Maximum development - 4hr pre-load, 5 VO2 efforts',
                'tired_vo2': True,
                'base_duration': 14400,
                'base_power': 0.70,
                'intervals': (5, 240),
                'on_power': 1.18,
                'off_power': 0.55,
                'off_duration': 150
            }
        }
    },
    {
        'name': 'Double Day Simulation',
        'levels': {
            '1': {
                'structure': 'AM: 1.5hr Z2 easy. PM (4-6hr later): 3x8min @ 100% FTP with 5min recovery',
                'execution': 'Simulates stage race or back-to-back training - quality on tired legs',
                'cadence_prescription': '85-95rpm PM session',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Split session - 4-6hr between',
                'fueling': 'Refuel between sessions: 1.2g CHO/kg/hr + protein',
                'double_day': True,
                'am_duration': 5400,
                'am_power': 0.70,
                'pm_intervals': (3, 480),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 300
            },
            '2': {
                'structure': 'AM: 2hr Z2 easy. PM (4-6hr later): 3x10min @ 100% FTP with 5min recovery',
                'execution': 'Extended AM ride - building durability',
                'double_day': True,
                'am_duration': 7200,
                'am_power': 0.70,
                'pm_intervals': (3, 600),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 300
            },
            '3': {
                'structure': 'AM: 2hr Z2 easy. PM (4-6hr later): 3x12min @ 100% FTP with 4min recovery',
                'execution': 'Extended PM efforts - threshold durability',
                'double_day': True,
                'am_duration': 7200,
                'am_power': 0.70,
                'pm_intervals': (3, 720),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 240
            },
            '4': {
                'structure': 'AM: 2.5hr Z2 easy. PM (4-6hr later): 3x12min @ 100% FTP with 4min recovery',
                'execution': 'Extended AM - more pre-fatigue before quality',
                'double_day': True,
                'am_duration': 9000,
                'am_power': 0.70,
                'pm_intervals': (3, 720),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 240
            },
            '5': {
                'structure': 'AM: 2.5hr Z2 easy. PM (4-6hr later): 4x10min @ 100% FTP with 4min recovery',
                'execution': 'More PM volume - race simulation',
                'double_day': True,
                'am_duration': 9000,
                'am_power': 0.70,
                'pm_intervals': (4, 600),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 240
            },
            '6': {
                'structure': 'AM: 3hr Z2 easy. PM (4-6hr later): 4x12min @ 100% FTP with 3min recovery',
                'execution': 'Maximum development - 3hr AM, 48min threshold PM',
                'double_day': True,
                'am_duration': 10800,
                'am_power': 0.70,
                'pm_intervals': (4, 720),
                'pm_on_power': 1.00,
                'pm_off_power': 0.55,
                'pm_off_duration': 180
            }
        }
    },
    {
        'name': 'Progressive Fatigue Threshold',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x10min @ 98% FTP with 5min, 4min, 3min recovery (decreasing)',
                'execution': 'Learning the format - same effort, less recovery each time',
                'cadence_prescription': '85-95rpm (race cadence)',
                'cadence': 90,
                'position_prescription': 'Seated, on the hoods',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'progressive_fatigue': True,
                'intervals': 3,
                'effort_duration': 600,
                'on_power': 0.98,
                'recovery_sequence': [300, 240, 180]
            },
            '2': {
                'structure': '15min warmup Z2, 3x12min @ 98% FTP with 5min, 4min, 3min recovery (decreasing)',
                'execution': 'Extended efforts - building threshold under progressive fatigue',
                'progressive_fatigue': True,
                'intervals': 3,
                'effort_duration': 720,
                'on_power': 0.98,
                'recovery_sequence': [300, 240, 180]
            },
            '3': {
                'structure': '15min warmup Z2, 4x10min @ 99% FTP with 5min, 4min, 3min, 2min recovery (decreasing)',
                'execution': 'Added 4th effort - final recovery only 2min',
                'progressive_fatigue': True,
                'intervals': 4,
                'effort_duration': 600,
                'on_power': 0.99,
                'recovery_sequence': [300, 240, 180, 120]
            },
            '4': {
                'structure': '15min warmup Z2, 4x12min @ 99% FTP with 5min, 4min, 3min, 2min recovery (decreasing)',
                'execution': 'Extended efforts with progressive fatigue',
                'progressive_fatigue': True,
                'intervals': 4,
                'effort_duration': 720,
                'on_power': 0.99,
                'recovery_sequence': [300, 240, 180, 120]
            },
            '5': {
                'structure': '15min warmup Z2, 4x12min @ 100% FTP with 4min, 3min, 2min, 1.5min recovery (decreasing)',
                'execution': 'Increased intensity with aggressive recovery reduction',
                'progressive_fatigue': True,
                'intervals': 4,
                'effort_duration': 720,
                'on_power': 1.00,
                'recovery_sequence': [240, 180, 120, 90]
            },
            '6': {
                'structure': '15min warmup Z2, 5x10min @ 100% FTP with 4min, 3min, 2.5min, 2min, 1.5min recovery (decreasing)',
                'execution': 'Maximum development - 5 efforts, final recovery 90sec',
                'progressive_fatigue': True,
                'intervals': 5,
                'effort_duration': 600,
                'on_power': 1.00,
                'recovery_sequence': [240, 180, 150, 120, 90]
            }
        }
    }
]


# =============================================================================
# ENDURANCE ADDITIONS
# =============================================================================

ENDURANCE_NEW = [
    {
        'name': 'Pre-Race Openers',
        'levels': {
            '1': {
                'structure': '20min Z1-Z2 easy, 2x30sec @ 110% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Day before race - wake up the legs without creating fatigue',
                'cadence_prescription': '90-100rpm on efforts',
                'cadence': 95,
                'position_prescription': 'Seated, relaxed',
                'timing_prescription': 'Day before race or event',
                'fueling': 'Normal hydration only',
                'openers': True,
                'warmup_duration': 1200,
                'warmup_power': 0.65,
                'efforts': (2, 30),
                'effort_power': 1.10,
                'effort_recovery': 120,
                'cooldown_duration': 300
            },
            '2': {
                'structure': '25min Z1-Z2 easy, 3x30sec @ 110% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Standard openers - 3 short efforts to activate',
                'openers': True,
                'warmup_duration': 1500,
                'warmup_power': 0.65,
                'efforts': (3, 30),
                'effort_power': 1.10,
                'effort_recovery': 120,
                'cooldown_duration': 300
            },
            '3': {
                'structure': '30min Z1-Z2 easy, 3x45sec @ 110% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Extended efforts - slightly longer activation',
                'openers': True,
                'warmup_duration': 1800,
                'warmup_power': 0.65,
                'efforts': (3, 45),
                'effort_power': 1.10,
                'effort_recovery': 120,
                'cooldown_duration': 300
            },
            '4': {
                'structure': '30min Z1-Z2 easy, 4x30sec @ 115% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Increased intensity - sharper activation',
                'openers': True,
                'warmup_duration': 1800,
                'warmup_power': 0.65,
                'efforts': (4, 30),
                'effort_power': 1.15,
                'effort_recovery': 120,
                'cooldown_duration': 300
            },
            '5': {
                'structure': '35min Z1-Z2 easy, 4x45sec @ 115% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Extended openers - longer base ride with sharper efforts',
                'openers': True,
                'warmup_duration': 2100,
                'warmup_power': 0.65,
                'efforts': (4, 45),
                'effort_power': 1.15,
                'effort_recovery': 120,
                'cooldown_duration': 300
            },
            '6': {
                'structure': '40min Z1-Z2 easy, 5x30sec @ 120% FTP with 2min easy, 5min Z1 cooldown',
                'execution': 'Full openers session - extended base with sharp activation',
                'openers': True,
                'warmup_duration': 2400,
                'warmup_power': 0.65,
                'efforts': (5, 30),
                'effort_power': 1.20,
                'effort_recovery': 120,
                'cooldown_duration': 300
            }
        }
    },
    {
        'name': 'Terrain Simulation Z2',
        'levels': {
            '1': {
                'structure': '1.5hr Z2 with variable power: alternate 5min @ 70% / 5min @ 75% FTP throughout',
                'execution': 'Simulates rolling terrain - variable power within Z2',
                'cadence_prescription': '80-90rpm on "climbs", 90-100rpm on "descents"',
                'cadence': 90,
                'position_prescription': 'Vary between hoods and drops',
                'timing_prescription': 'Endurance day',
                'fueling': '60g CHO/hr',
                'terrain_sim': True,
                'duration': 5400,
                'low_power': 0.70,
                'high_power': 0.75,
                'segment_duration': 300
            },
            '2': {
                'structure': '2hr Z2 with variable power: alternate 5min @ 68% / 5min @ 77% FTP throughout',
                'execution': 'Extended duration with more variability',
                'terrain_sim': True,
                'duration': 7200,
                'low_power': 0.68,
                'high_power': 0.77,
                'segment_duration': 300
            },
            '3': {
                'structure': '2.5hr Z2 with variable power: alternate 4min @ 67% / 6min @ 78% FTP throughout',
                'execution': 'Uneven segments - longer "climbs"',
                'terrain_sim': True,
                'duration': 9000,
                'low_power': 0.67,
                'high_power': 0.78,
                'segment_duration_low': 240,
                'segment_duration_high': 360
            },
            '4': {
                'structure': '3hr Z2 with variable power: random 3-7min segments @ 65-80% FTP',
                'execution': 'Random variability - gravel race simulation',
                'terrain_sim': True,
                'duration': 10800,
                'power_range': (0.65, 0.80),
                'segment_range': (180, 420)
            },
            '5': {
                'structure': '3.5hr Z2 with variable power: random 3-8min segments @ 63-82% FTP',
                'execution': 'Extended random variability - race-realistic',
                'terrain_sim': True,
                'duration': 12600,
                'power_range': (0.63, 0.82),
                'segment_range': (180, 480)
            },
            '6': {
                'structure': '4hr Z2 with variable power: random 3-10min segments @ 60-85% FTP',
                'execution': 'Maximum duration with full variability range',
                'terrain_sim': True,
                'duration': 14400,
                'power_range': (0.60, 0.85),
                'segment_range': (180, 600)
            }
        }
    }
]


# =============================================================================
# RACE SIMULATION (NEW CATEGORY)
# =============================================================================

RACE_SIMULATION = [
    {
        'name': 'Breakaway Simulation',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2x (5min @ 110% FTP attack + 10min @ 88% FTP tempo hold), 5min recovery between',
                'execution': 'Learning the format - attack then hold. This is breakaway work',
                'cadence_prescription': '95-105rpm attack, 85-95rpm hold',
                'cadence': 100,
                'position_prescription': 'Out of saddle for attack start, seated for hold',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'breakaway': True,
                'intervals': 2,
                'attack_duration': 300,
                'attack_power': 1.10,
                'hold_duration': 600,
                'hold_power': 0.88,
                'recovery_duration': 300
            },
            '2': {
                'structure': '15min warmup Z2, 2x (5min @ 112% FTP attack + 12min @ 88% FTP tempo hold), 5min recovery between',
                'execution': 'Extended hold duration - sustaining the break',
                'breakaway': True,
                'intervals': 2,
                'attack_duration': 300,
                'attack_power': 1.12,
                'hold_duration': 720,
                'hold_power': 0.88,
                'recovery_duration': 300
            },
            '3': {
                'structure': '15min warmup Z2, 3x (5min @ 112% FTP attack + 10min @ 89% FTP tempo hold), 4min recovery between',
                'execution': 'Three breakaway attempts - race-realistic',
                'breakaway': True,
                'intervals': 3,
                'attack_duration': 300,
                'attack_power': 1.12,
                'hold_duration': 600,
                'hold_power': 0.89,
                'recovery_duration': 240
            },
            '4': {
                'structure': '15min warmup Z2, 3x (5min @ 115% FTP attack + 12min @ 90% FTP tempo hold), 4min recovery between',
                'execution': 'Increased intensity - harder attack, higher hold',
                'breakaway': True,
                'intervals': 3,
                'attack_duration': 300,
                'attack_power': 1.15,
                'hold_duration': 720,
                'hold_power': 0.90,
                'recovery_duration': 240
            },
            '5': {
                'structure': '15min warmup Z2, 3x (5min @ 115% FTP attack + 15min @ 90% FTP tempo hold), 3min recovery between',
                'execution': 'Extended hold with reduced recovery - race simulation',
                'breakaway': True,
                'intervals': 3,
                'attack_duration': 300,
                'attack_power': 1.15,
                'hold_duration': 900,
                'hold_power': 0.90,
                'recovery_duration': 180
            },
            '6': {
                'structure': '15min warmup Z2, 4x (5min @ 118% FTP attack + 12min @ 91% FTP tempo hold), 3min recovery between',
                'execution': 'Maximum development - 4 breakaway attempts, G-Spot holds',
                'breakaway': True,
                'intervals': 4,
                'attack_duration': 300,
                'attack_power': 1.18,
                'hold_duration': 720,
                'hold_power': 0.91,
                'recovery_duration': 180
            }
        }
    },
    {
        'name': 'Variable Pace Chaos',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 20min block: random 30sec-2min efforts @ 85-110% FTP, no pattern',
                'execution': 'Gravel race simulation - unpredictable power changes',
                'cadence_prescription': 'Variable - respond to terrain',
                'cadence': 90,
                'position_prescription': 'Change positions frequently',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'chaos': True,
                'block_duration': 1200,
                'power_range': (0.85, 1.10),
                'effort_range': (30, 120)
            },
            '2': {
                'structure': '15min warmup Z2, 25min block: random 30sec-2min efforts @ 83-112% FTP, no pattern',
                'execution': 'Extended chaos block - wider power range',
                'chaos': True,
                'block_duration': 1500,
                'power_range': (0.83, 1.12),
                'effort_range': (30, 120)
            },
            '3': {
                'structure': '15min warmup Z2, 2x15min blocks: random 30sec-2min efforts @ 80-115% FTP, 5min Z2 between',
                'execution': 'Two chaos blocks - recovery between',
                'chaos': True,
                'blocks': 2,
                'block_duration': 900,
                'power_range': (0.80, 1.15),
                'effort_range': (30, 120),
                'block_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 2x20min blocks: random 30sec-3min efforts @ 78-118% FTP, 5min Z2 between',
                'execution': 'Extended blocks with wider effort range',
                'chaos': True,
                'blocks': 2,
                'block_duration': 1200,
                'power_range': (0.78, 1.18),
                'effort_range': (30, 180),
                'block_recovery': 300
            },
            '5': {
                'structure': '15min warmup Z2, 3x15min blocks: random 30sec-3min efforts @ 75-120% FTP, 4min Z2 between',
                'execution': 'Three chaos blocks - race simulation',
                'chaos': True,
                'blocks': 3,
                'block_duration': 900,
                'power_range': (0.75, 1.20),
                'effort_range': (30, 180),
                'block_recovery': 240
            },
            '6': {
                'structure': '15min warmup Z2, 45min continuous: random 30sec-4min efforts @ 70-125% FTP, no breaks',
                'execution': 'Maximum chaos - 45min of unpredictable power',
                'chaos': True,
                'block_duration': 2700,
                'power_range': (0.70, 1.25),
                'effort_range': (30, 240)
            }
        }
    },
    {
        'name': 'Sector Simulation',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x (90sec @ 130% FTP sector + 3min @ 75% FTP recovery), 5min Z2 between sets of 2',
                'execution': 'Simulates gravel sectors - hard start, recovery, repeat',
                'cadence_prescription': '100-110rpm sectors, 85-95rpm recovery',
                'cadence': 105,
                'position_prescription': 'Out of saddle sector start',
                'timing_prescription': 'Fresh',
                'fueling': '60-70g CHO/hr',
                'sector_sim': True,
                'sectors_per_set': 2,
                'sets': 2,
                'sector_duration': 90,
                'sector_power': 1.30,
                'sector_recovery': 180,
                'sector_recovery_power': 0.75,
                'set_recovery': 300
            },
            '2': {
                'structure': '15min warmup Z2, 6x (90sec @ 130% FTP sector + 3min @ 75% FTP recovery), 5min Z2 between sets of 3',
                'execution': 'More sectors per set - building repeatability',
                'sector_sim': True,
                'sectors_per_set': 3,
                'sets': 2,
                'sector_duration': 90,
                'sector_power': 1.30,
                'sector_recovery': 180,
                'sector_recovery_power': 0.75,
                'set_recovery': 300
            },
            '3': {
                'structure': '15min warmup Z2, 6x (2min @ 125% FTP sector + 3min @ 77% FTP recovery), 4min Z2 between sets of 3',
                'execution': 'Extended sectors - longer hard efforts',
                'sector_sim': True,
                'sectors_per_set': 3,
                'sets': 2,
                'sector_duration': 120,
                'sector_power': 1.25,
                'sector_recovery': 180,
                'sector_recovery_power': 0.77,
                'set_recovery': 240
            },
            '4': {
                'structure': '15min warmup Z2, 8x (2min @ 125% FTP sector + 2.5min @ 78% FTP recovery), 4min Z2 between sets of 4',
                'execution': 'Four sectors per set, reduced recovery',
                'sector_sim': True,
                'sectors_per_set': 4,
                'sets': 2,
                'sector_duration': 120,
                'sector_power': 1.25,
                'sector_recovery': 150,
                'sector_recovery_power': 0.78,
                'set_recovery': 240
            },
            '5': {
                'structure': '15min warmup Z2, 9x (2min @ 128% FTP sector + 2.5min @ 80% FTP recovery), 3min Z2 between sets of 3',
                'execution': 'Three sets of three - race simulation',
                'sector_sim': True,
                'sectors_per_set': 3,
                'sets': 3,
                'sector_duration': 120,
                'sector_power': 1.28,
                'sector_recovery': 150,
                'sector_recovery_power': 0.80,
                'set_recovery': 180
            },
            '6': {
                'structure': '15min warmup Z2, 12x (2min @ 130% FTP sector + 2min @ 80% FTP recovery), 3min Z2 between sets of 4',
                'execution': 'Maximum development - 12 sectors, minimal recovery',
                'sector_sim': True,
                'sectors_per_set': 4,
                'sets': 3,
                'sector_duration': 120,
                'sector_power': 1.30,
                'sector_recovery': 120,
                'sector_recovery_power': 0.80,
                'set_recovery': 180
            }
        }
    }
]


# =============================================================================
# G-SPOT ARCHETYPES (87-92% FTP - Reality-Adjusted Zone)
# =============================================================================
# NOT Sweet Spot. G-Spot is the honest zone where adaptation happens.

G_SPOT_NEW = [
    {
        'name': 'G-Spot Intervals',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2x10min @ 87-89% FTP, 5min recovery between',
                'execution': 'Learning the zone - sustainable but challenging. Not Sweet Spot lies.',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Alternate: 5min seated, 5min hands in drops',
                'timing_prescription': 'Mid-week quality session',
                'fueling': '50-60g CHO/hr',
                'intervals': (2, 600),
                'on_power': 0.88,
                'off_power': 0.55,
                'duration': 600
            },
            '2': {
                'structure': '15min warmup Z2, 2x15min @ 88-90% FTP, 5min recovery between',
                'execution': 'Extended duration - building time-in-zone',
                'intervals': (2, 900),
                'on_power': 0.89,
                'off_power': 0.55,
                'duration': 900
            },
            '3': {
                'structure': '15min warmup Z2, 3x12min @ 89-91% FTP, 4min recovery between',
                'execution': 'Three intervals - building mental fortitude',
                'intervals': (3, 720),
                'on_power': 0.90,
                'off_power': 0.55,
                'duration': 720
            },
            '4': {
                'structure': '15min warmup Z2, 3x15min @ 89-91% FTP, 4min recovery between',
                'execution': 'Extended time-in-zone - threshold durability',
                'intervals': (3, 900),
                'on_power': 0.90,
                'off_power': 0.55,
                'duration': 900
            },
            '5': {
                'structure': '15min warmup Z2, 2x20min @ 90-92% FTP, 5min recovery between',
                'execution': '40 minutes total time-in-zone - race simulation',
                'intervals': (2, 1200),
                'on_power': 0.91,
                'off_power': 0.55,
                'duration': 1200
            },
            '6': {
                'structure': '15min warmup Z2, 2x25min @ 90-92% FTP, 5min recovery between',
                'execution': 'Maximum G-Spot development - 50 minutes TIZ',
                'intervals': (2, 1500),
                'on_power': 0.91,
                'off_power': 0.55,
                'duration': 1500
            }
        }
    },
    {
        'name': 'G-Spot Criss-Cross',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 20min alternating: 2min @ 92% FTP, 2min @ 85% FTP',
                'execution': 'Criss-cross pattern - surge and settle within the zone',
                'cadence_prescription': '90-95rpm on surges, 85rpm on settle',
                'cadence': 92,
                'position_prescription': 'Drops on surge, hoods on settle',
                'criss_cross': True,
                'total_duration': 1200,
                'high_power': 0.92,
                'low_power': 0.85,
                'interval_duration': 120
            },
            '2': {
                'structure': '15min warmup Z2, 25min alternating: 2min @ 92% FTP, 2min @ 85% FTP',
                'execution': 'Extended criss-cross - building surge repeatability',
                'criss_cross': True,
                'total_duration': 1500,
                'high_power': 0.92,
                'low_power': 0.85,
                'interval_duration': 120
            },
            '3': {
                'structure': '15min warmup Z2, 30min alternating: 2min @ 93% FTP, 2min @ 86% FTP',
                'execution': 'Full 30min criss-cross - race simulation',
                'criss_cross': True,
                'total_duration': 1800,
                'high_power': 0.93,
                'low_power': 0.86,
                'interval_duration': 120
            },
            '4': {
                'structure': '15min warmup Z2, 2x18min alternating: 2min @ 93% FTP, 2min @ 87% FTP, 5min recovery',
                'execution': 'Two blocks - sustained power variation',
                'criss_cross': True,
                'sets': 2,
                'total_duration': 1080,
                'high_power': 0.93,
                'low_power': 0.87,
                'interval_duration': 120,
                'set_recovery': 300
            },
            '5': {
                'structure': '15min warmup Z2, 2x22min alternating: 2min @ 94% FTP, 2min @ 87% FTP, 4min recovery',
                'execution': 'Extended blocks - threshold boundary work',
                'criss_cross': True,
                'sets': 2,
                'total_duration': 1320,
                'high_power': 0.94,
                'low_power': 0.87,
                'interval_duration': 120,
                'set_recovery': 240
            },
            '6': {
                'structure': '15min warmup Z2, 2x25min alternating: 90sec @ 95% FTP, 90sec @ 88% FTP, 4min recovery',
                'execution': 'Maximum criss-cross development - 50 minutes TIZ',
                'criss_cross': True,
                'sets': 2,
                'total_duration': 1500,
                'high_power': 0.95,
                'low_power': 0.88,
                'interval_duration': 90,
                'set_recovery': 240
            }
        }
    },
    {
        'name': 'G-Spot Progressive',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 20min building from 85% to 92% FTP',
                'execution': 'Progressive build - learn pacing through the zone',
                'ramp': True,
                'intervals': (1, 1200),
                'start_power': 0.85,
                'end_power': 0.92,
                'off_duration': 0
            },
            '2': {
                'structure': '15min warmup Z2, 25min building from 85% to 92% FTP',
                'execution': 'Extended progressive - patience in pacing',
                'ramp': True,
                'intervals': (1, 1500),
                'start_power': 0.85,
                'end_power': 0.92
            },
            '3': {
                'structure': '15min warmup Z2, 2x15min building from 86% to 93% FTP, 5min recovery',
                'execution': 'Two progressive builds - reset and repeat',
                'ramp': True,
                'intervals': (2, 900),
                'start_power': 0.86,
                'end_power': 0.93,
                'off_duration': 300
            },
            '4': {
                'structure': '15min warmup Z2, 2x18min building from 86% to 94% FTP, 4min recovery',
                'execution': 'Extended builds with higher ceiling',
                'ramp': True,
                'intervals': (2, 1080),
                'start_power': 0.86,
                'end_power': 0.94,
                'off_duration': 240
            },
            '5': {
                'structure': '15min warmup Z2, 2x20min building from 87% to 95% FTP, 4min recovery',
                'execution': 'Maximum progressive builds - threshold boundary',
                'ramp': True,
                'intervals': (2, 1200),
                'start_power': 0.87,
                'end_power': 0.95,
                'off_duration': 240
            },
            '6': {
                'structure': '15min warmup Z2, 30min building from 87% to 95% FTP + 10min @ 95% FTP hold',
                'execution': 'Progressive to threshold hold - ultimate pacing test',
                'ramp': True,
                'intervals': (1, 1800),
                'start_power': 0.87,
                'end_power': 0.95,
                'hold_duration': 600,
                'hold_power': 0.95
            }
        }
    }
]


# =============================================================================
# LT1/MAF ARCHETYPES (Low-HR, Aerobic Base Building)
# =============================================================================
# Full dimensions on all levels

LT1_MAF_NEW = [
    {
        'name': 'LT1 Capped Endurance',
        'levels': {
            '1': {
                'structure': '60min @ LT1 cap (Zone 2 ceiling). HR must not exceed LT1.',
                'execution': 'Patience is key - if HR drifts, reduce power. Build aerobic engine.',
                'cadence_prescription': '80-90rpm natural cadence - find your groove',
                'cadence': 85,
                'position_prescription': 'Comfortable position, alternate every 20min',
                'timing_prescription': 'Any time - low physiological stress',
                'fueling': '40-50g CHO/hr - practice race nutrition',
                'lt1_capped': True,
                'duration': 3600,
                'power': 0.70,
                'hr_cap': 'LT1'
            },
            '2': {
                'structure': '75min @ LT1 cap. Monitor HR drift - power may need to drop.',
                'execution': 'Extended duration - aerobic system development',
                'cadence_prescription': '80-90rpm - consistent, sustainable',
                'cadence': 85,
                'position_prescription': 'Comfortable, alternate hands every 15min',
                'timing_prescription': 'Morning preferred for fat oxidation',
                'fueling': '40-50g CHO/hr',
                'lt1_capped': True,
                'duration': 4500,
                'power': 0.70,
                'hr_cap': 'LT1'
            },
            '3': {
                'structure': '90min @ LT1 cap. This is MAF training - no cheating.',
                'execution': 'Build fat oxidation and aerobic efficiency',
                'cadence_prescription': '80-90rpm - self-selected comfort',
                'cadence': 85,
                'position_prescription': 'Alternate drops/hoods every 20min',
                'timing_prescription': 'Fasted or light breakfast for fat adaptation',
                'fueling': '50g CHO/hr - begin fueling practice',
                'lt1_capped': True,
                'duration': 5400,
                'power': 0.70,
                'hr_cap': 'LT1'
            },
            '4': {
                'structure': '2hr @ LT1 cap. Long aerobic development ride.',
                'execution': 'Durability through low intensity - patience builds champions',
                'cadence_prescription': '80-90rpm - maintain form throughout',
                'cadence': 85,
                'position_prescription': 'Position changes every 20min - build tolerance',
                'timing_prescription': 'Weekend long ride slot',
                'fueling': '50-60g CHO/hr - gut training',
                'lt1_capped': True,
                'duration': 7200,
                'power': 0.70,
                'hr_cap': 'LT1'
            },
            '5': {
                'structure': '2.5hr @ LT1 cap. Extended aerobic base.',
                'execution': 'Maximum aerobic development - fuel and hydrate properly',
                'cadence_prescription': '80-90rpm - efficiency over power',
                'cadence': 85,
                'position_prescription': 'Race position practice in final hour',
                'timing_prescription': 'Primary weekend long ride',
                'fueling': '60g CHO/hr - race simulation fueling',
                'lt1_capped': True,
                'duration': 9000,
                'power': 0.70,
                'hr_cap': 'LT1'
            },
            '6': {
                'structure': '3hr @ LT1 cap. Full aerobic base ride.',
                'execution': 'Peak aerobic development - monitor decoupling',
                'cadence_prescription': '80-90rpm - maintain even with fatigue',
                'cadence': 85,
                'position_prescription': 'Full position rotation - aero practice',
                'timing_prescription': 'Primary training block cornerstone',
                'fueling': '60-70g CHO/hr - aggressive fueling practice',
                'lt1_capped': True,
                'duration': 10800,
                'power': 0.70,
                'hr_cap': 'LT1'
            }
        }
    },
    {
        'name': 'MAF Test Protocol',
        'levels': {
            '1': {
                'structure': '10min warmup, 30min @ MAF HR (180-age), record average power',
                'execution': 'Monthly test to track aerobic progress. Power at MAF HR should increase.',
                'cadence_prescription': '85-90rpm - consistent for repeatability',
                'cadence': 87,
                'position_prescription': 'Same position every test - standardize',
                'timing_prescription': 'Same time of day, same conditions each test',
                'fueling': 'Fasted or standardized pre-test meal',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 1800,
                'hr_target': 'MAF'
            },
            '2': {
                'structure': '10min warmup, 30min @ MAF HR, compare to previous test',
                'execution': 'Track progress - power should increase at same HR over weeks',
                'cadence_prescription': '85-90rpm - match previous tests',
                'cadence': 87,
                'position_prescription': 'Identical to previous test',
                'timing_prescription': 'Consistent timing for valid comparison',
                'fueling': 'Standardized',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 1800,
                'hr_target': 'MAF'
            },
            '3': {
                'structure': '10min warmup, 30min @ MAF HR, analyze decoupling',
                'execution': 'Decoupling <5% indicates good aerobic fitness',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Consistent test position',
                'timing_prescription': 'Well-rested day',
                'fueling': 'Standardized pre-test protocol',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 1800,
                'hr_target': 'MAF'
            },
            '4': {
                'structure': '10min warmup, 45min @ MAF HR, extended test',
                'execution': 'Extended test - more data for decoupling analysis',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Consistent position',
                'timing_prescription': 'After recovery day',
                'fueling': 'Light fueling during test if needed',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 2700,
                'hr_target': 'MAF'
            },
            '5': {
                'structure': '10min warmup, 60min @ MAF HR, full test',
                'execution': 'Full hour test - definitive aerobic progress marker',
                'cadence_prescription': '85-90rpm - maintain consistency',
                'cadence': 87,
                'position_prescription': 'Standard test position throughout',
                'timing_prescription': 'Fresh legs - after rest day',
                'fueling': '30-40g CHO during test',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 3600,
                'hr_target': 'MAF'
            },
            '6': {
                'structure': '10min warmup, 60min @ MAF HR, analyze pace/power at fixed HR',
                'execution': 'Peak aerobic test - compare to baseline',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Standardized for comparison',
                'timing_prescription': 'End of base phase - peak aerobic fitness',
                'fueling': '30-40g CHO during test',
                'maf_test': True,
                'warmup_duration': 600,
                'test_duration': 3600,
                'hr_target': 'MAF'
            }
        }
    }
]


# =============================================================================
# CRITICAL POWER / W' ARCHETYPES
# =============================================================================
# NOTE: CP ≈ 95-98% of FTP. Power targets here are % of CP, not FTP.
# For ZWO generation, we convert: target_ftp = target_cp * 0.96
# e.g., 110% CP = 110% * 0.96 = 105.6% FTP

CRITICAL_POWER_NEW = [
    {
        'name': 'Above CP Repeats',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 4x2min @ 110% CP (~106% FTP), 4min recovery between',
                'execution': 'Work above CP depletes W\' - learning the sensation of W\' depletion',
                'cadence_prescription': '95-100rpm - high turnover for power',
                'cadence': 97,
                'position_prescription': 'Drops for power output',
                'timing_prescription': 'Fresh legs required - demanding session',
                'fueling': '60-70g CHO/hr - high glycolytic demand',
                'above_cp': True,
                'intervals': (4, 120),
                'on_power': 1.06,  # 110% CP ≈ 106% FTP
                'off_power': 0.55,
                'off_duration': 240
            },
            '2': {
                'structure': '15min warmup Z2, 5x2min @ 112% CP (~108% FTP), 4min recovery between',
                'execution': 'Building W\' tolerance - control the effort, feel the fade',
                'cadence_prescription': '95-100rpm',
                'cadence': 97,
                'position_prescription': 'Drops, aggressive',
                'timing_prescription': 'After rest day',
                'fueling': '60-70g CHO/hr',
                'above_cp': True,
                'intervals': (5, 120),
                'on_power': 1.08,  # 112% CP ≈ 108% FTP
                'off_power': 0.55,
                'off_duration': 240
            },
            '3': {
                'structure': '15min warmup Z2, 5x2.5min @ 112% CP (~108% FTP), 3.5min recovery',
                'execution': 'Extended above-CP work with reduced recovery',
                'cadence_prescription': '95-100rpm',
                'cadence': 97,
                'position_prescription': 'Drops throughout',
                'timing_prescription': 'Key session - protect with easy days',
                'fueling': '60-70g CHO/hr',
                'above_cp': True,
                'intervals': (5, 150),
                'on_power': 1.08,
                'off_power': 0.55,
                'off_duration': 210
            },
            '4': {
                'structure': '15min warmup Z2, 6x2.5min @ 115% CP (~110% FTP), 3min recovery',
                'execution': 'High W\' depletion - race-realistic surges',
                'cadence_prescription': '95-100rpm - maintain through fatigue',
                'cadence': 97,
                'position_prescription': 'Aggressive race position',
                'timing_prescription': 'Primary quality session of week',
                'fueling': '70g CHO/hr',
                'above_cp': True,
                'intervals': (6, 150),
                'on_power': 1.10,  # 115% CP ≈ 110% FTP
                'off_power': 0.55,
                'off_duration': 180
            },
            '5': {
                'structure': '15min warmup Z2, 6x3min @ 115% CP (~110% FTP), 3min recovery',
                'execution': 'Extended above-CP intervals - W\' development',
                'cadence_prescription': '95-100rpm',
                'cadence': 97,
                'position_prescription': 'Race position - drops',
                'timing_prescription': 'Peak training block',
                'fueling': '70g CHO/hr',
                'above_cp': True,
                'intervals': (6, 180),
                'on_power': 1.10,
                'off_power': 0.55,
                'off_duration': 180
            },
            '6': {
                'structure': '15min warmup Z2, 7x3min @ 118% CP (~113% FTP), 2.5min recovery',
                'execution': 'Maximum above-CP development - empty the tank on final reps',
                'cadence_prescription': '95-105rpm - whatever gets power',
                'cadence': 100,
                'position_prescription': 'Full race aggression',
                'timing_prescription': 'Peak fitness - before taper',
                'fueling': '70-80g CHO/hr',
                'above_cp': True,
                'intervals': (7, 180),
                'on_power': 1.13,  # 118% CP ≈ 113% FTP
                'off_power': 0.55,
                'off_duration': 150
            }
        }
    },
    {
        'name': 'W-Prime Depletion',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 3x (3min @ 115% CP + 2min @ 105% CP), 5min recovery',
                'execution': 'Deplete W\' then hold above CP - race simulation pattern',
                'cadence_prescription': '95-100rpm surge, 90rpm hold',
                'cadence': 97,
                'position_prescription': 'Drops for surge, hoods for hold',
                'timing_prescription': 'Fresh - demanding pattern',
                'fueling': '60-70g CHO/hr',
                'w_prime': True,
                'sets': 3,
                'surge_duration': 180,
                'surge_power': 1.10,  # 115% CP ≈ 110% FTP
                'hold_duration': 120,
                'hold_power': 1.01,   # 105% CP ≈ 101% FTP
                'set_recovery': 300
            },
            '2': {
                'structure': '15min warmup Z2, 4x (3min @ 115% CP + 2min @ 105% CP), 4min recovery',
                'execution': 'More sets - building W\' recharge capacity',
                'cadence_prescription': '95-100rpm surge, 90rpm hold',
                'cadence': 97,
                'position_prescription': 'Aggressive positioning',
                'timing_prescription': 'Key training day',
                'fueling': '60-70g CHO/hr',
                'w_prime': True,
                'sets': 4,
                'surge_duration': 180,
                'surge_power': 1.10,
                'hold_duration': 120,
                'hold_power': 1.01,
                'set_recovery': 240
            },
            '3': {
                'structure': '15min warmup Z2, 4x (3min @ 118% CP + 3min @ 105% CP), 4min recovery',
                'execution': 'Higher surge power, extended hold - deeper depletion',
                'cadence_prescription': '95-105rpm surge, 90rpm hold',
                'cadence': 100,
                'position_prescription': 'Full race position',
                'timing_prescription': 'Quality session',
                'fueling': '70g CHO/hr',
                'w_prime': True,
                'sets': 4,
                'surge_duration': 180,
                'surge_power': 1.13,  # 118% CP ≈ 113% FTP
                'hold_duration': 180,
                'hold_power': 1.01,
                'set_recovery': 240
            },
            '4': {
                'structure': '15min warmup Z2, 5x (3min @ 118% CP + 3min @ 107% CP), 3min recovery',
                'execution': 'Reduced recovery - race-realistic W\' management',
                'cadence_prescription': '95-105rpm surge, 90rpm hold',
                'cadence': 100,
                'position_prescription': 'Race simulation position',
                'timing_prescription': 'Peak training',
                'fueling': '70g CHO/hr',
                'w_prime': True,
                'sets': 5,
                'surge_duration': 180,
                'surge_power': 1.13,
                'hold_duration': 180,
                'hold_power': 1.03,  # 107% CP ≈ 103% FTP
                'set_recovery': 180
            },
            '5': {
                'structure': '15min warmup Z2, 5x (4min @ 120% CP + 3min @ 108% CP), 3min recovery',
                'execution': 'Extended surge duration - deep W\' depletion, test mental limits',
                'cadence_prescription': '95-105rpm',
                'cadence': 100,
                'position_prescription': 'Maximum aggression',
                'timing_prescription': 'Race-specific preparation',
                'fueling': '70-80g CHO/hr',
                'w_prime': True,
                'sets': 5,
                'surge_duration': 240,
                'surge_power': 1.15,  # 120% CP ≈ 115% FTP
                'hold_duration': 180,
                'hold_power': 1.04,   # 108% CP ≈ 104% FTP
                'set_recovery': 180
            },
            '6': {
                'structure': '15min warmup Z2, 6x (4min @ 120% CP + 3min @ 110% CP), 2.5min recovery',
                'execution': 'Maximum W\' development - crit/CX race simulation, all-out',
                'cadence_prescription': '95-105rpm - whatever produces power',
                'cadence': 100,
                'position_prescription': 'Full race mode',
                'timing_prescription': 'Peak fitness window',
                'fueling': '80g CHO/hr',
                'w_prime': True,
                'sets': 6,
                'surge_duration': 240,
                'surge_power': 1.15,
                'hold_duration': 180,
                'hold_power': 1.06,  # 110% CP ≈ 106% FTP
                'set_recovery': 150
            }
        }
    }
]


# =============================================================================
# NORWEGIAN DOUBLE-THRESHOLD ARCHETYPES
# =============================================================================
# Note: "Double Session" archetype generates AM session only.
# PM session should be generated as a separate workout with "_PM" suffix.

NORWEGIAN_DOUBLE = [
    {
        'name': 'Norwegian 4x8 Classic',
        'levels': {
            '1': {
                'structure': '20min warmup Z2, 4x8min @ 88-90% FTP (lactate capped at 3-4mmol), 2min recovery',
                'execution': 'Seiler format - control lactate, don\'t go anaerobic. Steady, controlled power.',
                'cadence_prescription': '85-90rpm steady - efficiency over force',
                'cadence': 87,
                'position_prescription': 'TT position if comfortable, otherwise drops',
                'timing_prescription': 'Morning session preferred, can repeat PM',
                'fueling': '60-70g CHO/hr - threshold work is glycolytic',
                'norwegian': True,
                'intervals': (4, 480),
                'on_power': 0.89,
                'off_power': 0.55,
                'off_duration': 120,
                'lactate_cap': 4.0
            },
            '2': {
                'structure': '20min warmup Z2, 4x8min @ 89-91% FTP (lactate capped at 3.5-4mmol), 2min recovery',
                'execution': 'Slight power increase - maintain lactate control, feel the sustainable burn',
                'cadence_prescription': '85-90rpm - smooth pedaling',
                'cadence': 87,
                'position_prescription': 'Aero when possible',
                'timing_prescription': 'Consistent time of day',
                'fueling': '60-70g CHO/hr',
                'norwegian': True,
                'intervals': (4, 480),
                'on_power': 0.90,
                'off_power': 0.55,
                'off_duration': 120,
                'lactate_cap': 4.0
            },
            '3': {
                'structure': '20min warmup Z2, 5x8min @ 90-92% FTP (lactate capped), 2min recovery',
                'execution': 'Added interval - building threshold volume, maintain control',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Race position practice',
                'timing_prescription': 'Morning primary, PM optional',
                'fueling': '60-70g CHO/hr',
                'norwegian': True,
                'intervals': (5, 480),
                'on_power': 0.91,
                'off_power': 0.55,
                'off_duration': 120,
                'lactate_cap': 4.0
            },
            '4': {
                'structure': '20min warmup Z2, 5x8min @ 91-93% FTP (lactate capped), 90sec recovery',
                'execution': 'Reduced recovery - threshold durability, lactate clearance',
                'cadence_prescription': '85-90rpm - maintain even as recovery shortens',
                'cadence': 87,
                'position_prescription': 'Sustainable race position',
                'timing_prescription': 'Key quality day',
                'fueling': '70g CHO/hr',
                'norwegian': True,
                'intervals': (5, 480),
                'on_power': 0.92,
                'off_power': 0.55,
                'off_duration': 90,
                'lactate_cap': 4.0
            },
            '5': {
                'structure': '20min warmup Z2, 6x8min @ 92-94% FTP (lactate capped), 90sec recovery',
                'execution': 'Maximum Norwegian format - 48 minutes TIZ, elite-level threshold volume',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'TT/aero position',
                'timing_prescription': 'Primary training block cornerstone',
                'fueling': '70g CHO/hr',
                'norwegian': True,
                'intervals': (6, 480),
                'on_power': 0.93,
                'off_power': 0.55,
                'off_duration': 90,
                'lactate_cap': 4.0
            },
            '6': {
                'structure': '20min warmup Z2, 6x10min @ 92-94% FTP (lactate capped), 2min recovery',
                'execution': 'Extended intervals - 60 minutes threshold volume, Ingebrigtsen-level',
                'cadence_prescription': '85-90rpm - smooth throughout 10min blocks',
                'cadence': 87,
                'position_prescription': 'Full race position',
                'timing_prescription': 'Peak threshold development',
                'fueling': '70-80g CHO/hr',
                'norwegian': True,
                'intervals': (6, 600),
                'on_power': 0.93,
                'off_power': 0.55,
                'off_duration': 120,
                'lactate_cap': 4.0
            }
        }
    },
    {
        'name': 'Norwegian Double AM',
        # NOTE: This generates the AM session. Generator should create separate PM file.
        'levels': {
            '1': {
                'structure': 'AM Session: 15min warmup, 3x8min @ 88% FTP, 2min recovery. PM session separate.',
                'execution': 'AM threshold session - PM session 6+ hours later is separate workout file',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Sustainable position',
                'timing_prescription': 'Morning - allow 6+ hours before PM session',
                'fueling': '50-60g CHO/hr - save glycogen for PM',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (3, 480),
                'on_power': 0.88,
                'off_power': 0.55,
                'off_duration': 120,
                'session_gap_hours': 6
            },
            '2': {
                'structure': 'AM Session: 15min warmup, 3x8min @ 89% FTP, 2min recovery',
                'execution': 'Building double-session capacity - respect the PM session',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Comfortable, sustainable',
                'timing_prescription': 'Early morning for maximum recovery before PM',
                'fueling': '50-60g CHO/hr',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (3, 480),
                'on_power': 0.89,
                'off_power': 0.55,
                'off_duration': 120
            },
            '3': {
                'structure': 'AM Session: 15min warmup, 4x8min @ 89% FTP, 2min recovery',
                'execution': 'Asymmetric day - harder AM, easier PM',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Race position practice',
                'timing_prescription': 'AM slot',
                'fueling': '60g CHO/hr',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (4, 480),
                'on_power': 0.89,
                'off_power': 0.55,
                'off_duration': 120
            },
            '4': {
                'structure': 'AM Session: 15min warmup, 4x8min @ 90% FTP, 2min recovery',
                'execution': 'Full doubles day - significant threshold volume across both sessions',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Aero/race position',
                'timing_prescription': 'Primary AM threshold',
                'fueling': '60g CHO/hr',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (4, 480),
                'on_power': 0.90,
                'off_power': 0.55,
                'off_duration': 120
            },
            '5': {
                'structure': 'AM Session: 15min warmup, 5x8min @ 90% FTP, 2min recovery',
                'execution': 'Extended AM session - building threshold dominance',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Full race position',
                'timing_prescription': 'Key AM quality session',
                'fueling': '60-70g CHO/hr',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (5, 480),
                'on_power': 0.90,
                'off_power': 0.55,
                'off_duration': 120
            },
            '6': {
                'structure': 'AM Session: 15min warmup, 5x8min @ 91% FTP, 2min recovery',
                'execution': 'Maximum AM doubles - elite threshold volume, PM session completes the day',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Full race aero',
                'timing_prescription': 'Peak double-day capacity',
                'fueling': '70g CHO/hr',
                'norwegian': True,
                'is_am_session': True,
                'intervals': (5, 480),
                'on_power': 0.91,
                'off_power': 0.55,
                'off_duration': 120
            }
        }
    },
    {
        'name': 'Norwegian Double PM',
        # NOTE: This is the PM complement to Norwegian Double AM
        'levels': {
            '1': {
                'structure': 'PM Session: 15min warmup, 3x8min @ 88% FTP, 2min recovery',
                'execution': 'PM threshold session - 6+ hours after AM session',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Sustainable position',
                'timing_prescription': 'Evening - 6+ hours after AM',
                'fueling': '50-60g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (3, 480),
                'on_power': 0.88,
                'off_power': 0.55,
                'off_duration': 120
            },
            '2': {
                'structure': 'PM Session: 15min warmup, 3x8min @ 89% FTP, 2min recovery',
                'execution': 'PM complement - match AM intensity',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Late afternoon/evening',
                'fueling': '50-60g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (3, 480),
                'on_power': 0.89,
                'off_power': 0.55,
                'off_duration': 120
            },
            '3': {
                'structure': 'PM Session: 15min warmup, 3x8min @ 89% FTP, 2min recovery',
                'execution': 'Easier PM after harder AM - asymmetric loading',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Evening session',
                'fueling': '50-60g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (3, 480),
                'on_power': 0.89,
                'off_power': 0.55,
                'off_duration': 120
            },
            '4': {
                'structure': 'PM Session: 15min warmup, 4x8min @ 88% FTP, 2min recovery',
                'execution': 'Full PM session - slightly lower power than AM',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Evening completion',
                'fueling': '60g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (4, 480),
                'on_power': 0.88,
                'off_power': 0.55,
                'off_duration': 120
            },
            '5': {
                'structure': 'PM Session: 15min warmup, 4x8min @ 88% FTP, 2min recovery',
                'execution': 'PM complement to extended AM',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Evening',
                'fueling': '60g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (4, 480),
                'on_power': 0.88,
                'off_power': 0.55,
                'off_duration': 120
            },
            '6': {
                'structure': 'PM Session: 15min warmup, 5x8min @ 88% FTP, 2min recovery',
                'execution': 'Maximum PM doubles - complete the elite threshold day',
                'cadence_prescription': '85-90rpm',
                'cadence': 87,
                'position_prescription': 'Sustainable race position',
                'timing_prescription': 'Evening completion of double day',
                'fueling': '60-70g CHO/hr',
                'norwegian': True,
                'is_pm_session': True,
                'intervals': (5, 480),
                'on_power': 0.88,
                'off_power': 0.55,
                'off_duration': 120
            }
        }
    }
]


# =============================================================================
# HVLI / LSD EXTENDED ARCHETYPES (High Volume Low Intensity)
# =============================================================================
# Full dimensions on all levels

HVLI_EXTENDED = [
    {
        'name': 'HVLI Extended Z2',
        'levels': {
            '1': {
                'structure': '3hr @ 65-70% FTP. Pure Zone 2 endurance.',
                'execution': 'Long slow distance - build durability and fat oxidation. No surges.',
                'cadence_prescription': '80-90rpm natural - find sustainable rhythm',
                'cadence': 85,
                'position_prescription': 'Comfortable, alternate every 30min between hoods/drops',
                'timing_prescription': 'Weekend long ride - primary volume day',
                'fueling': '50-60g CHO/hr - practice race fueling',
                'hvli': True,
                'duration': 10800,
                'power': 0.68
            },
            '2': {
                'structure': '3.5hr @ 65-70% FTP. Extended Zone 2.',
                'execution': 'Building volume - stay aerobic, no intensity spikes',
                'cadence_prescription': '80-90rpm - maintain through fatigue',
                'cadence': 85,
                'position_prescription': 'Rotate positions every 20-30min',
                'timing_prescription': 'Weekend primary ride',
                'fueling': '50-60g CHO/hr',
                'hvli': True,
                'duration': 12600,
                'power': 0.68
            },
            '3': {
                'structure': '4hr @ 65-70% FTP. Long Zone 2 development.',
                'execution': 'Significant aerobic development ride - mental game begins',
                'cadence_prescription': '80-90rpm - efficiency focus',
                'cadence': 85,
                'position_prescription': 'Practice race position in hour 3',
                'timing_prescription': 'Major training day',
                'fueling': '60g CHO/hr - gut training',
                'hvli': True,
                'duration': 14400,
                'power': 0.68
            },
            '4': {
                'structure': '4.5hr @ 65-70% FTP. Extended durability.',
                'execution': 'Building toward race-day durations - fuel aggressively',
                'cadence_prescription': '80-90rpm - maintain even as tired',
                'cadence': 85,
                'position_prescription': 'Full position rotation',
                'timing_prescription': 'Big volume day',
                'fueling': '60-70g CHO/hr',
                'hvli': True,
                'duration': 16200,
                'power': 0.68
            },
            '5': {
                'structure': '5hr @ 65-70% FTP. Major volume day.',
                'execution': 'Race-simulation duration - fuel and hydrate aggressively',
                'cadence_prescription': '80-90rpm - consistency is key',
                'cadence': 85,
                'position_prescription': 'Race position practice throughout',
                'timing_prescription': 'Key long ride - protect surrounding days',
                'fueling': '70-80g CHO/hr - race-day fueling',
                'hvli': True,
                'duration': 18000,
                'power': 0.68
            },
            '6': {
                'structure': '6hr @ 65-70% FTP. Maximum volume ride.',
                'execution': 'Ultra-distance preparation - mental and physical durability test',
                'cadence_prescription': '80-90rpm - whatever is sustainable',
                'cadence': 85,
                'position_prescription': 'Full race position rotation',
                'timing_prescription': 'Peak volume - biggest ride of block',
                'fueling': '80-90g CHO/hr - maximum gut training',
                'hvli': True,
                'duration': 21600,
                'power': 0.68
            }
        }
    },
    {
        'name': 'HVLI Terrain Simulation',
        'levels': {
            '1': {
                'structure': '3hr variable Z2: alternating 10min @ 70% FTP (flats) with 10min @ 65% FTP (recovery)',
                'execution': 'Simulating rolling terrain within Zone 2 - no hard efforts',
                'cadence_prescription': '85rpm on "climbs", 80rpm on "descents"',
                'cadence': 82,
                'position_prescription': 'Drops on high power, hoods on low',
                'timing_prescription': 'Weekend terrain simulation',
                'fueling': '50-60g CHO/hr',
                'hvli_terrain': True,
                'duration': 10800,
                'high_power': 0.70,
                'low_power': 0.65,
                'interval_duration': 600
            },
            '2': {
                'structure': '3.5hr variable Z2: alternating 10min @ 72% FTP with 10min @ 65% FTP',
                'execution': 'Extended terrain simulation - building variability tolerance',
                'cadence_prescription': '85-90rpm variation',
                'cadence': 87,
                'position_prescription': 'Race position practice',
                'timing_prescription': 'Primary terrain day',
                'fueling': '50-60g CHO/hr',
                'hvli_terrain': True,
                'duration': 12600,
                'high_power': 0.72,
                'low_power': 0.65,
                'interval_duration': 600
            },
            '3': {
                'structure': '4hr variable Z2: alternating 15min @ 72% FTP with 10min @ 65% FTP',
                'execution': 'Longer "climbs" within Zone 2 - sustained effort practice',
                'cadence_prescription': '80-85rpm on climbs, 90rpm on recovery',
                'cadence': 85,
                'position_prescription': 'Climbing position practice',
                'timing_prescription': 'Course-specific preparation',
                'fueling': '60g CHO/hr',
                'hvli_terrain': True,
                'duration': 14400,
                'high_power': 0.72,
                'low_power': 0.65,
                'high_interval': 900,
                'low_interval': 600
            },
            '4': {
                'structure': '4.5hr variable Z2 with occasional 5min surges to 75% FTP',
                'execution': 'Adding small surges - still aerobic, mimics race demands',
                'cadence_prescription': '85-90rpm on surges',
                'cadence': 87,
                'position_prescription': 'Race position on surges',
                'timing_prescription': 'Race-specific preparation',
                'fueling': '60-70g CHO/hr',
                'hvli_terrain': True,
                'duration': 16200,
                'high_power': 0.75,
                'low_power': 0.65,
                'surge_duration': 300
            },
            '5': {
                'structure': '5hr variable Z2 with course-specific power variations',
                'execution': 'Race-course simulation at aerobic intensity',
                'cadence_prescription': 'Match expected race cadence',
                'cadence': 90,
                'position_prescription': 'Full race position practice',
                'timing_prescription': 'Course simulation day',
                'fueling': '70-80g CHO/hr',
                'hvli_terrain': True,
                'duration': 18000,
                'high_power': 0.75,
                'low_power': 0.65
            },
            '6': {
                'structure': '6hr variable Z2 matching race-day power profile',
                'execution': 'Full race-day terrain simulation - dress rehearsal at Z2',
                'cadence_prescription': 'Race-day cadence targets',
                'position_prescription': 'Full race position',
                'timing_prescription': 'Final long ride before taper',
                'fueling': '80-90g CHO/hr - full race fueling',
                'hvli_terrain': True,
                'duration': 21600,
                'high_power': 0.75,
                'low_power': 0.65
            }
        }
    }
]


# =============================================================================
# TESTING PROTOCOL ARCHETYPES
# =============================================================================
# Proper testing workouts that generate actual ZWO files

TESTING_PROTOCOLS = [
    {
        'name': 'FTP Ramp Test',
        'levels': {
            '1': {
                'structure': '10min warmup @ 50%, then ramp from 100W increasing 20W every minute until failure',
                'execution': 'Ramp test protocol - FTP = 75% of max 1-minute power',
                'cadence_prescription': '85-95rpm - maintain as long as possible',
                'cadence': 90,
                'position_prescription': 'Hoods, seated - consistent position',
                'timing_prescription': 'Fresh legs - after rest day, morning preferred',
                'fueling': 'Fasted or light meal 2-3hr before',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 600,
                'warmup_power': 0.50,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            },
            '2': {
                'structure': 'Ramp test with 5min Z2 warmup extension',
                'execution': 'Extended warmup for those needing more preparation',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Consistent test position',
                'timing_prescription': 'Fresh, rested',
                'fueling': 'Standardized',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 900,
                'warmup_power': 0.55,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            },
            '3': {
                'structure': 'Ramp test - baseline establishment',
                'execution': 'First test of training block - establish baseline FTP',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Standard test position',
                'timing_prescription': 'Start of training block',
                'fueling': 'Standardized pre-test meal',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 600,
                'warmup_power': 0.50,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            },
            '4': {
                'structure': 'Ramp test - mid-block check',
                'execution': 'Mid-block progress check - compare to baseline',
                'cadence_prescription': '85-95rpm - match baseline test',
                'cadence': 90,
                'position_prescription': 'Identical to baseline',
                'timing_prescription': 'Mid-block, after recovery week',
                'fueling': 'Match baseline test',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 600,
                'warmup_power': 0.50,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            },
            '5': {
                'structure': 'Ramp test - peak fitness',
                'execution': 'Peak fitness assessment before taper',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Standard test position',
                'timing_prescription': 'End of build phase',
                'fueling': 'Standardized',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 600,
                'warmup_power': 0.50,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            },
            '6': {
                'structure': 'Ramp test - race readiness',
                'execution': 'Final FTP confirmation before race',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Race position',
                'timing_prescription': '7-10 days before race',
                'fueling': 'Race-day nutrition practice',
                'testing': True,
                'test_type': 'ramp',
                'warmup_duration': 600,
                'warmup_power': 0.50,
                'ramp_start_watts': 100,
                'ramp_increment': 20,
                'ramp_step_duration': 60
            }
        }
    },
    {
        'name': '20min FTP Test',
        'levels': {
            '1': {
                'structure': '20min warmup with 3x1min blowouts, then 20min all-out. FTP = 95% of 20min power.',
                'execution': 'Classic 20-minute test - pace conservatively first 5 minutes',
                'cadence_prescription': '90-95rpm - sustainable turnover',
                'cadence': 92,
                'position_prescription': 'TT position if comfortable, otherwise drops',
                'timing_prescription': 'Fresh legs, morning or early afternoon',
                'fueling': 'Light meal 2-3hr before, caffeine optional',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1200,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            },
            '2': {
                'structure': '20min FTP test with extended warmup',
                'execution': 'For those needing longer preparation',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'TT/drops',
                'timing_prescription': 'Fresh',
                'fueling': 'Standardized',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1500,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            },
            '3': {
                'structure': '20min FTP test - baseline',
                'execution': 'Baseline establishment',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'Standard',
                'timing_prescription': 'Block start',
                'fueling': 'Standardized',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1200,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            },
            '4': {
                'structure': '20min FTP test - progress check',
                'execution': 'Mid-block assessment',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'Match baseline',
                'timing_prescription': 'Mid-block',
                'fueling': 'Match baseline',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1200,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            },
            '5': {
                'structure': '20min FTP test - peak',
                'execution': 'Peak fitness assessment',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'Race position',
                'timing_prescription': 'End of build',
                'fueling': 'Optimized',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1200,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            },
            '6': {
                'structure': '20min FTP test - race prep',
                'execution': 'Final confirmation',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'Race position',
                'timing_prescription': 'Pre-race',
                'fueling': 'Race nutrition',
                'testing': True,
                'test_type': '20min_ftp',
                'warmup_duration': 1200,
                'blowout_intervals': (3, 60),
                'blowout_power': 1.20,
                'test_duration': 1200,
                'ftp_multiplier': 0.95
            }
        }
    },
    {
        'name': 'CP Test Protocol',
        'levels': {
            '1': {
                'structure': '3-minute all-out test after warmup. Establishes CP and W\'.',
                'execution': '3-minute all-out test - go hard from the start, hold on',
                'cadence_prescription': '100-110rpm - high turnover',
                'position_prescription': 'Drops, aggressive',
                'timing_prescription': 'Fresh legs required',
                'fueling': 'Light or fasted',
                'testing': True,
                'test_type': 'cp_3min',
                'warmup_duration': 1200,
                'test_duration': 180
            },
            '2': {
                'structure': '12-minute all-out test. Alternative CP determination.',
                'execution': '12-minute maximal effort - pace more conservatively',
                'cadence_prescription': '90-95rpm',
                'cadence': 92,
                'position_prescription': 'TT position',
                'timing_prescription': 'Fresh',
                'fueling': 'Light meal before',
                'testing': True,
                'test_type': 'cp_12min',
                'warmup_duration': 1200,
                'test_duration': 720
            },
            '3': {
                'structure': '3-12 combo: 3min all-out, rest 30min, 12min all-out',
                'execution': 'Full CP/W\' determination - two efforts same day',
                'cadence_prescription': 'Match effort duration',
                'cadence': 90,
                'position_prescription': 'Consistent between tests',
                'timing_prescription': 'Dedicated test day',
                'fueling': 'Refuel between efforts',
                'testing': True,
                'test_type': 'cp_combo',
                'warmup_duration': 1200,
                'test_1_duration': 180,
                'rest_duration': 1800,
                'test_2_duration': 720
            },
            '4': {
                'structure': 'CP test - baseline establishment',
                'execution': 'Baseline CP/W\' for training block',
                'cadence_prescription': 'Consistent',
                'cadence': 90,
                'position_prescription': 'Standard',
                'timing_prescription': 'Block start',
                'fueling': 'Standardized',
                'testing': True,
                'test_type': 'cp_3min',
                'warmup_duration': 1200,
                'test_duration': 180
            },
            '5': {
                'structure': 'CP test - progress check',
                'execution': 'Mid-block CP assessment',
                'cadence_prescription': 'Match baseline',
                'cadence': 90,
                'position_prescription': 'Match baseline',
                'timing_prescription': 'Mid-block',
                'fueling': 'Match baseline',
                'testing': True,
                'test_type': 'cp_3min',
                'warmup_duration': 1200,
                'test_duration': 180
            },
            '6': {
                'structure': 'CP test - race readiness',
                'execution': 'Final CP confirmation',
                'cadence_prescription': 'Race cadence',
                'cadence': 90,
                'position_prescription': 'Race position',
                'timing_prescription': 'Pre-race',
                'fueling': 'Race prep',
                'testing': True,
                'test_type': 'cp_3min',
                'warmup_duration': 1200,
                'test_duration': 180
            }
        }
    }
]


# =============================================================================
# RECOVERY ARCHETYPES
# =============================================================================

RECOVERY_NEW = [
    {
        'name': 'Active Recovery Spin',
        'levels': {
            '1': {
                'structure': '30min @ 50-55% FTP. True recovery - minimal load.',
                'execution': 'Flush ride - promote blood flow without adding stress',
                'cadence_prescription': '85-95rpm - light, easy spinning',
                'cadence': 90,
                'position_prescription': 'Comfortable, relaxed grip',
                'timing_prescription': 'Day after hard session or race',
                'fueling': 'Optional - water is fine',
                'recovery': True,
                'duration': 1800,
                'power': 0.52
            },
            '2': {
                'structure': '40min @ 50-55% FTP. Extended recovery spin.',
                'execution': 'Slightly longer flush - still minimal stress',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Relaxed',
                'timing_prescription': 'Recovery day',
                'fueling': 'Light if any',
                'recovery': True,
                'duration': 2400,
                'power': 0.52
            },
            '3': {
                'structure': '45min @ 50-55% FTP. Standard recovery ride.',
                'execution': 'Full recovery ride - no surges, no efforts',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Day between quality sessions',
                'fueling': 'Light',
                'recovery': True,
                'duration': 2700,
                'power': 0.53
            },
            '4': {
                'structure': '50min @ 50-55% FTP. Extended recovery.',
                'execution': 'Longer recovery for high-volume athletes',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Relaxed',
                'timing_prescription': 'Recovery day',
                'fueling': 'Light',
                'recovery': True,
                'duration': 3000,
                'power': 0.53
            },
            '5': {
                'structure': '60min @ 50-55% FTP. Full hour recovery.',
                'execution': 'Maximum recovery duration - still no intensity',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Extended recovery need',
                'fueling': 'Light',
                'recovery': True,
                'duration': 3600,
                'power': 0.53
            },
            '6': {
                'structure': '60min @ 50-55% FTP with optional mobility.',
                'execution': 'Full recovery with mobility focus',
                'cadence_prescription': '85-95rpm',
                'cadence': 90,
                'position_prescription': 'Position mobility work',
                'timing_prescription': 'Recovery priority day',
                'fueling': 'Light',
                'recovery': True,
                'duration': 3600,
                'power': 0.52
            }
        }
    },
    {
        'name': 'Rest Day',
        'levels': {
            '1': {
                'structure': 'Complete rest - no cycling. Optional stretching/mobility.',
                'execution': 'Full rest day - recovery is training',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': 'Scheduled rest or when HRV indicates',
                'fueling': 'Normal eating, focus on protein and sleep',
                'rest_day': True,
                'duration': 0,
                'power': 0
            },
            '2': {
                'structure': 'Complete rest with mobility work.',
                'execution': 'Rest + 20min stretching/foam rolling',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': 'Scheduled rest',
                'fueling': 'Recovery nutrition focus',
                'rest_day': True,
                'duration': 0,
                'power': 0
            },
            '3': {
                'structure': 'Complete rest.',
                'execution': 'Full rest - no exercise',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': 'Rest day',
                'fueling': 'Normal',
                'rest_day': True,
                'duration': 0,
                'power': 0
            },
            '4': {
                'structure': 'Complete rest.',
                'execution': 'Full rest',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': 'Rest day',
                'fueling': 'Normal',
                'rest_day': True,
                'duration': 0,
                'power': 0
            },
            '5': {
                'structure': 'Complete rest.',
                'execution': 'Full rest',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': 'Rest day',
                'fueling': 'Normal',
                'rest_day': True,
                'duration': 0,
                'power': 0
            },
            '6': {
                'structure': 'Complete rest - race week rest day.',
                'execution': 'Pre-race rest day',
                'cadence_prescription': 'N/A',
                'cadence': 0,
                'position_prescription': 'N/A',
                'timing_prescription': '2-3 days before race',
                'fueling': 'Carb loading if appropriate',
                'rest_day': True,
                'duration': 0,
                'power': 0
            }
        }
    }
]


# =============================================================================
# INSCYD / METABOLIC ARCHETYPES
# =============================================================================
# For VLamax reduction and metabolic profiling targets

INSCYD_NEW = [
    {
        'name': 'VLamax Reduction',
        'levels': {
            '1': {
                'structure': '90min @ 70-75% FTP with 4x20sec sprints. Long Z2 with glycolytic depletion.',
                'execution': 'Reduce VLamax through long aerobic work with strategic sprints to deplete glycolytic capacity',
                'cadence_prescription': '80-90rpm base, 110+ rpm sprints',
                'cadence': 85,
                'position_prescription': 'Comfortable, sprints in drops',
                'timing_prescription': 'Fasted morning for maximum effect',
                'fueling': 'Fasted or minimal - this is the point',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 5400,
                'power': 0.72,
                'sprint_intervals': (4, 20),
                'sprint_power': 2.0
            },
            '2': {
                'structure': '2hr @ 70-75% FTP with 5x20sec sprints distributed throughout.',
                'execution': 'Extended VLamax reduction - long duration, minimal glycolytic work',
                'cadence_prescription': '80-90rpm, high cadence sprints',
                'cadence': 85,
                'position_prescription': 'Endurance position',
                'timing_prescription': 'Fasted or low-carb',
                'fueling': 'Minimal - water and electrolytes',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 7200,
                'power': 0.72,
                'sprint_intervals': (5, 20),
                'sprint_power': 2.0
            },
            '3': {
                'structure': '2.5hr @ 70-75% FTP with 6x20sec sprints.',
                'execution': 'Extended aerobic with glycolytic depletion sprints',
                'cadence_prescription': '80-90rpm',
                'cadence': 85,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Fasted',
                'fueling': 'Minimal',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 9000,
                'power': 0.72,
                'sprint_intervals': (6, 20),
                'sprint_power': 2.0
            },
            '4': {
                'structure': '3hr @ 68-72% FTP with 6x20sec sprints.',
                'execution': 'Maximum VLamax reduction ride',
                'cadence_prescription': '80-90rpm',
                'cadence': 85,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Fasted, morning',
                'fueling': 'Water only',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 10800,
                'power': 0.70,
                'sprint_intervals': (6, 20),
                'sprint_power': 2.0
            },
            '5': {
                'structure': '3.5hr @ 68-72% FTP with 8x20sec sprints.',
                'execution': 'Extended VLamax reduction',
                'cadence_prescription': '80-90rpm',
                'cadence': 85,
                'position_prescription': 'Endurance',
                'timing_prescription': 'Fasted',
                'fueling': 'Minimal',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 12600,
                'power': 0.70,
                'sprint_intervals': (8, 20),
                'sprint_power': 2.0
            },
            '6': {
                'structure': '4hr @ 68-72% FTP with 10x20sec sprints.',
                'execution': 'Maximum VLamax reduction protocol',
                'cadence_prescription': '80-90rpm',
                'cadence': 85,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Fasted, dedicated day',
                'fueling': 'Minimal',
                'inscyd': True,
                'vlamax_reduction': True,
                'duration': 14400,
                'power': 0.70,
                'sprint_intervals': (10, 20),
                'sprint_power': 2.0
            }
        }
    },
    {
        'name': 'FatMax Development',
        'levels': {
            '1': {
                'structure': '90min fasted @ 65-70% FTP. Maximum fat oxidation zone.',
                'execution': 'Fasted ride at FatMax intensity - build fat oxidation capacity',
                'cadence_prescription': '80-85rpm - efficiency focus',
                'cadence': 82,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Morning, fasted (8+ hours since last meal)',
                'fueling': 'None - water only',
                'inscyd': True,
                'fatmax': True,
                'duration': 5400,
                'power': 0.67,
                'fasted': True
            },
            '2': {
                'structure': '2hr fasted @ 65-70% FTP.',
                'execution': 'Extended fasted FatMax ride',
                'cadence_prescription': '80-85rpm',
                'cadence': 82,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Morning fasted',
                'fueling': 'Water only',
                'inscyd': True,
                'fatmax': True,
                'duration': 7200,
                'power': 0.67,
                'fasted': True
            },
            '3': {
                'structure': '2.5hr fasted @ 65-68% FTP.',
                'execution': 'Extended FatMax development',
                'cadence_prescription': '80-85rpm',
                'cadence': 82,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Fasted',
                'fueling': 'Water/electrolytes only',
                'inscyd': True,
                'fatmax': True,
                'duration': 9000,
                'power': 0.66,
                'fasted': True
            },
            '4': {
                'structure': '3hr fasted @ 65-68% FTP.',
                'execution': 'Maximum fasted FatMax ride',
                'cadence_prescription': '80-85rpm',
                'cadence': 82,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Morning fasted',
                'fueling': 'Water/electrolytes',
                'inscyd': True,
                'fatmax': True,
                'duration': 10800,
                'power': 0.66,
                'fasted': True
            },
            '5': {
                'structure': '3hr @ 65-68% FTP, first 2hr fasted then begin fueling.',
                'execution': 'Train fat oxidation then practice fueling',
                'cadence_prescription': '80-85rpm',
                'cadence': 82,
                'position_prescription': 'Comfortable',
                'timing_prescription': 'Morning',
                'fueling': 'Begin fueling at 2hr mark',
                'inscyd': True,
                'fatmax': True,
                'duration': 10800,
                'power': 0.66,
                'partial_fasted': True
            },
            '6': {
                'structure': '4hr @ 65-68% FTP, first 2.5hr fasted.',
                'execution': 'Extended FatMax with transition to fueling',
                'cadence_prescription': '80-85rpm',
                'cadence': 82,
                'position_prescription': 'Sustainable',
                'timing_prescription': 'Major training day',
                'fueling': 'Begin fueling at 2.5hr',
                'inscyd': True,
                'fatmax': True,
                'duration': 14400,
                'power': 0.66,
                'partial_fasted': True
            }
        }
    }
]


# =============================================================================
# GRAVEL-SPECIFIC ARCHETYPES
# =============================================================================

GRAVEL_SPECIFIC = [
    {
        'name': 'Surge and Settle',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 2x (3 surges: 20sec @ 130% FTP, 90sec settle @ 85% FTP), 5min recovery between sets',
                'execution': 'Explosive out of saddle for each surge, then immediately settle to tempo. Practice rapid power changes.',
                'cadence_prescription': '100-120rpm surge, 85-90rpm settle',
                'cadence': 105,
                'position_prescription': 'Out of saddle for surges, seated in drops for settle',
                'timing_prescription': 'Fresh or moderate fatigue',
                'fueling': '60-70g CHO/hr',
                'surge_settle': True,
                'surges_per_set': 3,
                'sets': 2,
                'surge_duration': 20,
                'surge_power': 1.30,
                'settle_duration': 90,
                'settle_power': 0.85,
                'set_recovery': 300
            },
            '2': {
                'structure': '15min warmup Z2, 2x (4 surges: 20sec @ 135% FTP, 75sec settle @ 85% FTP), 5min recovery between sets',
                'execution': 'Added surge per set. Hold settle power steady between surges.',
                'surge_settle': True,
                'surges_per_set': 4,
                'sets': 2,
                'surge_duration': 20,
                'surge_power': 1.35,
                'settle_duration': 75,
                'settle_power': 0.85,
                'set_recovery': 300
            },
            '3': {
                'structure': '15min warmup Z2, 2x (5 surges: 20sec @ 138% FTP, 60sec settle @ 86% FTP), 4min recovery between sets',
                'execution': 'More surges, shorter settle. Building sustained surge capacity.',
                'surge_settle': True,
                'surges_per_set': 5,
                'sets': 2,
                'surge_duration': 20,
                'surge_power': 1.38,
                'settle_duration': 60,
                'settle_power': 0.86,
                'set_recovery': 240
            },
            '4': {
                'structure': '15min warmup Z2, 3x (4 surges: 25sec @ 140% FTP, 60sec settle @ 87% FTP), 4min recovery between sets',
                'execution': 'Three sets now. Longer surges, higher settle power. Manage fatigue across sets.',
                'surge_settle': True,
                'surges_per_set': 4,
                'sets': 3,
                'surge_duration': 25,
                'surge_power': 1.40,
                'settle_duration': 60,
                'settle_power': 0.87,
                'set_recovery': 240
            },
            '5': {
                'structure': '15min warmup Z2, 3x (5 surges: 25sec @ 145% FTP, 50sec settle @ 88% FTP), 3min recovery between sets',
                'execution': 'Race-realistic density. Reduced recovery between sets forces adaptation.',
                'surge_settle': True,
                'surges_per_set': 5,
                'sets': 3,
                'surge_duration': 25,
                'surge_power': 1.45,
                'settle_duration': 50,
                'settle_power': 0.88,
                'set_recovery': 180
            },
            '6': {
                'structure': '15min warmup Z2, 3x (6 surges: 30sec @ 150% FTP, 45sec settle @ 88% FTP), 3min recovery between sets',
                'execution': 'Maximum surge density and power. Full race-simulation intensity.',
                'surge_settle': True,
                'surges_per_set': 6,
                'sets': 3,
                'surge_duration': 30,
                'surge_power': 1.50,
                'settle_duration': 45,
                'settle_power': 0.88,
                'set_recovery': 180
            }
        }
    },
    {
        'name': 'Terrain Microbursts',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 15min @ 82% FTP with 5sec bursts @ 125% every 90sec',
                'execution': 'Maintain base power between bursts. Each burst is a quick acceleration - dont overthink it, just punch it.',
                'cadence_prescription': '88-92rpm base, 100-110rpm on bursts',
                'cadence': 92,
                'position_prescription': 'Seated in drops. Stand briefly for bursts.',
                'timing_prescription': 'Moderate fatigue OK',
                'fueling': '60-70g CHO/hr',
                'microbursts': True,
                'block_duration': 900,
                'base_power': 0.82,
                'burst_duration': 5,
                'burst_power': 1.25,
                'burst_interval': 90,
                'sets': 1,
                'set_recovery': 0
            },
            '2': {
                'structure': '15min warmup Z2, 20min @ 83% FTP with 6sec bursts @ 128% every 75sec',
                'execution': 'Longer block, slightly higher base and burst power. Stay smooth.',
                'microbursts': True,
                'block_duration': 1200,
                'base_power': 0.83,
                'burst_duration': 6,
                'burst_power': 1.28,
                'burst_interval': 75,
                'sets': 1,
                'set_recovery': 0
            },
            '3': {
                'structure': '15min warmup Z2, 2x 12min @ 85% FTP with 6sec bursts @ 132% every 60sec, 5min recovery',
                'execution': 'Two blocks now. More frequent bursts demand better recovery between punches.',
                'microbursts': True,
                'block_duration': 720,
                'base_power': 0.85,
                'burst_duration': 6,
                'burst_power': 1.32,
                'burst_interval': 60,
                'sets': 2,
                'set_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 2x 15min @ 87% FTP with 7sec bursts @ 135% every 50sec, 4min recovery',
                'execution': 'Higher base, longer bursts, tighter intervals. This is rocky singletrack simulation.',
                'microbursts': True,
                'block_duration': 900,
                'base_power': 0.87,
                'burst_duration': 7,
                'burst_power': 1.35,
                'burst_interval': 50,
                'sets': 2,
                'set_recovery': 240
            },
            '5': {
                'structure': '15min warmup Z2, 2x 15min @ 88% FTP with 8sec bursts @ 140% every 40sec, 4min recovery',
                'execution': 'Near-constant microburst frequency. Sustained power under repeated disruption.',
                'microbursts': True,
                'block_duration': 900,
                'base_power': 0.88,
                'burst_duration': 8,
                'burst_power': 1.40,
                'burst_interval': 40,
                'sets': 2,
                'set_recovery': 240
            },
            '6': {
                'structure': '15min warmup Z2, 3x 12min @ 90% FTP with 8sec bursts @ 145% every 35sec, 3min recovery',
                'execution': 'Maximum microburst density across three blocks. Race-day terrain simulation.',
                'microbursts': True,
                'block_duration': 720,
                'base_power': 0.90,
                'burst_duration': 8,
                'burst_power': 1.45,
                'burst_interval': 35,
                'sets': 3,
                'set_recovery': 180
            }
        }
    },
    {
        'name': 'Gravel Grind',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 20min @ 82% FTP with 4 terrain spikes (10sec @ 120% FTP)',
                'execution': 'Grinding sustained effort with sharp terrain spikes. Spikes are evenly distributed. Recover ON the base effort, not off.',
                'cadence_prescription': '85-90rpm base, 95-105rpm on spikes',
                'cadence': 90,
                'position_prescription': 'Drops for base, out of saddle for spikes',
                'timing_prescription': 'Can do on moderate fatigue',
                'fueling': '60-80g CHO/hr - practice race nutrition',
                'gravel_grind': True,
                'block_duration': 1200,
                'base_power': 0.82,
                'num_spikes': 4,
                'spike_duration': 10,
                'spike_power': 1.20,
                'sets': 1,
                'set_recovery': 0
            },
            '2': {
                'structure': '15min warmup Z2, 25min @ 83% FTP with 5 terrain spikes (10sec @ 125% FTP)',
                'execution': 'Longer grind block, more spikes. Hold base power through each spike recovery.',
                'gravel_grind': True,
                'block_duration': 1500,
                'base_power': 0.83,
                'num_spikes': 5,
                'spike_duration': 10,
                'spike_power': 1.25,
                'sets': 1,
                'set_recovery': 0
            },
            '3': {
                'structure': '15min warmup Z2, 2x 15min @ 85% FTP with 5 terrain spikes (12sec @ 128% FTP), 5min recovery',
                'execution': 'Two grinding blocks. Longer spikes test your ability to return to base quickly.',
                'gravel_grind': True,
                'block_duration': 900,
                'base_power': 0.85,
                'num_spikes': 5,
                'spike_duration': 12,
                'spike_power': 1.28,
                'sets': 2,
                'set_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 2x 18min @ 87% FTP with 6 terrain spikes (12sec @ 132% FTP), 4min recovery',
                'execution': 'Higher base power with more frequent spikes. This is hour-3-of-a-gravel-race territory.',
                'gravel_grind': True,
                'block_duration': 1080,
                'base_power': 0.87,
                'num_spikes': 6,
                'spike_duration': 12,
                'spike_power': 1.32,
                'sets': 2,
                'set_recovery': 240
            },
            '5': {
                'structure': '15min warmup Z2, 2x 20min @ 88% FTP with 7 terrain spikes (10sec @ 138% FTP), 4min recovery',
                'execution': 'Dense spike pattern on a high base. Spikes are sharper but shorter - punch and recover.',
                'gravel_grind': True,
                'block_duration': 1200,
                'base_power': 0.88,
                'num_spikes': 7,
                'spike_duration': 10,
                'spike_power': 1.38,
                'sets': 2,
                'set_recovery': 240
            },
            '6': {
                'structure': '15min warmup Z2, 2x 25min @ 90% FTP with 8 terrain spikes (8sec @ 145% FTP), 3min recovery',
                'execution': 'Maximum grind. High base with rapid-fire spikes. The 200-miler special.',
                'gravel_grind': True,
                'block_duration': 1500,
                'base_power': 0.90,
                'num_spikes': 8,
                'spike_duration': 8,
                'spike_power': 1.45,
                'sets': 2,
                'set_recovery': 180
            }
        }
    },
    {
        'name': 'Late Race Surge Protocol',
        'levels': {
            '1': {
                'structure': '15min warmup Z2, 15min Z2 preload, 1x (3min @ 92% + 2min @ 102% FTP)',
                'execution': 'The preload is NOT recovery. Its fatiguing Z2 to simulate hours of riding. Then hit efforts HARD.',
                'cadence_prescription': '85-90rpm preload, 90-95rpm efforts',
                'cadence': 90,
                'position_prescription': 'Hoods for preload, drops for efforts',
                'timing_prescription': 'Best on moderate fatigue - dont come in fresh',
                'fueling': '60-80g CHO/hr - fuel through the preload',
                'late_race': True,
                'preload_duration': 900,
                'preload_power': 0.68,
                'efforts': [
                    {'duration': 180, 'power': 0.92},
                    {'duration': 120, 'power': 1.02}
                ],
                'sets': 1,
                'set_recovery': 0
            },
            '2': {
                'structure': '15min warmup Z2, 20min Z2 preload, 1x (3min @ 95% + 2min @ 105% + 1min @ 112% FTP)',
                'execution': 'Longer preload, added third effort. Escalating intensity mimics late-race attacks.',
                'late_race': True,
                'preload_duration': 1200,
                'preload_power': 0.68,
                'efforts': [
                    {'duration': 180, 'power': 0.95},
                    {'duration': 120, 'power': 1.05},
                    {'duration': 60, 'power': 1.12}
                ],
                'sets': 1,
                'set_recovery': 0
            },
            '3': {
                'structure': '15min warmup Z2, 20min Z2 preload, 2x (3min @ 95% + 2min @ 108% + 1min @ 115% FTP), 5min recovery',
                'execution': 'Two full sets after preload. Second set is where the real adaptation happens.',
                'late_race': True,
                'preload_duration': 1200,
                'preload_power': 0.70,
                'efforts': [
                    {'duration': 180, 'power': 0.95},
                    {'duration': 120, 'power': 1.08},
                    {'duration': 60, 'power': 1.15}
                ],
                'sets': 2,
                'set_recovery': 300
            },
            '4': {
                'structure': '15min warmup Z2, 25min Z2 preload, 2x (4min @ 98% + 3min @ 110% + 1min @ 118% FTP), 5min recovery',
                'execution': 'Extended preload and longer efforts. This is the hour-5 push to the finish.',
                'late_race': True,
                'preload_duration': 1500,
                'preload_power': 0.70,
                'efforts': [
                    {'duration': 240, 'power': 0.98},
                    {'duration': 180, 'power': 1.10},
                    {'duration': 60, 'power': 1.18}
                ],
                'sets': 2,
                'set_recovery': 300
            },
            '5': {
                'structure': '15min warmup Z2, 25min Z2 preload, 2x (4min @ 100% + 3min @ 112% + 90sec @ 120% FTP), 4min recovery, then 3x 30sec @ 130% finishers',
                'execution': 'Full protocol with sprint finishers. The finishers simulate the final kick on empty legs.',
                'late_race': True,
                'preload_duration': 1500,
                'preload_power': 0.72,
                'efforts': [
                    {'duration': 240, 'power': 1.00},
                    {'duration': 180, 'power': 1.12},
                    {'duration': 90, 'power': 1.20}
                ],
                'sets': 2,
                'set_recovery': 240,
                'finisher_count': 3,
                'finisher_duration': 30,
                'finisher_power': 1.30
            },
            '6': {
                'structure': '15min warmup Z2, 30min Z2 preload, 2x (5min @ 102% + 3min @ 115% + 2min @ 122% FTP), 4min recovery, then 4x 30sec @ 135% finishers',
                'execution': 'Maximum late-race simulation. Longest preload, hardest efforts, most finishers. Empty the tank.',
                'late_race': True,
                'preload_duration': 1800,
                'preload_power': 0.72,
                'efforts': [
                    {'duration': 300, 'power': 1.02},
                    {'duration': 180, 'power': 1.15},
                    {'duration': 120, 'power': 1.22}
                ],
                'sets': 2,
                'set_recovery': 240,
                'finisher_count': 4,
                'finisher_duration': 30,
                'finisher_power': 1.35
            }
        }
    }
]


# =============================================================================
# COMBINED DICTIONARY FOR INTEGRATION
# =============================================================================

NEW_ARCHETYPES = {
    # Original Nate categories
    'VO2max': VO2MAX_NEW,
    'TT_Threshold': THRESHOLD_NEW,
    'Sprint_Neuromuscular': SPRINT_NEW,
    'Anaerobic_Capacity': ANAEROBIC_CAPACITY,
    'Durability': DURABILITY_NEW,
    'Endurance': ENDURANCE_NEW,
    'Race_Simulation': RACE_SIMULATION,
    # Methodology-specific categories
    'G_Spot': G_SPOT_NEW,
    'LT1_MAF': LT1_MAF_NEW,
    'Critical_Power': CRITICAL_POWER_NEW,
    'Norwegian_Double': NORWEGIAN_DOUBLE,
    'HVLI_Extended': HVLI_EXTENDED,
    # Testing, Recovery, Metabolic
    'Testing': TESTING_PROTOCOLS,
    'Recovery': RECOVERY_NEW,
    'INSCYD': INSCYD_NEW,
    # Gravel-specific workout patterns
    'Gravel_Specific': GRAVEL_SPECIFIC,
}


# =============================================================================
# MERGE IMPORTED ARCHETYPES (from Cursor ZWO dump: 34 types x 6 levels)
# =============================================================================
try:
    from imported_archetypes import IMPORTED_ARCHETYPES
    for _category, _archetypes in IMPORTED_ARCHETYPES.items():
        if _category in NEW_ARCHETYPES:
            # Append to existing category, avoiding duplicates by name
            existing_names = {a['name'] for a in NEW_ARCHETYPES[_category]}
            for arch in _archetypes:
                if arch['name'] not in existing_names:
                    NEW_ARCHETYPES[_category].append(arch)
        else:
            NEW_ARCHETYPES[_category] = list(_archetypes)
except ImportError:
    pass  # imported_archetypes.py not present — skip


if __name__ == '__main__':
    # Print summary of new archetypes
    print("NEW ARCHETYPES SUMMARY")
    print("=" * 60)

    total_archetypes = 0
    for category, archetypes in NEW_ARCHETYPES.items():
        print(f"\n{category}: {len(archetypes)} new archetypes")
        for arch in archetypes:
            print(f"  - {arch['name']} (6 levels)")
            total_archetypes += 1

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_archetypes} new archetypes")
    print(f"TOTAL WORKOUT VARIATIONS: {total_archetypes * 6}")
