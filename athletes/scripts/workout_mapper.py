#!/usr/bin/env python3
"""
Workout Mapper — routes block-builder workout names to ZWO renderers.

Maps the 31 canonical workout types from the block-builder's workout-library.md
to the Nate generator's archetype system for ZWO rendering.

Three tiers:
  Tier 1: Intensity types → Nate generator (archetype variations)
  Tier 2: Endurance/Recovery types → Nate generator (newly wired)
  Tier 3: Kitchen Sink/SFR → New archetype definitions (TODO)

Usage:
    from workout_mapper import render_workout
    zwo_xml = render_workout('VO2max 30/30', level=3, methodology='POLARIZED')
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

# Ensure script dir on path (flat layout — all files in athletes/scripts/)
_SCRIPT_DIR = str(Path(__file__).parent.resolve())
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from nate_workout_generator import generate_nate_zwo


# =============================================================================
# BLOCK-BUILDER NAME → NATE GENERATOR MAPPING
# =============================================================================
# Each entry: 'Canonical Name' → (nate_type, variation_hint)
#
# nate_type: passed to generate_nate_zwo(workout_type=...)
# variation_hint: preferred archetype index within the category
#   (overrides the variation counter for deterministic selection)
#
# The Nate generator's select_archetype_for_workout() maps nate_type → category,
# then uses variation to pick a specific archetype within that category.
# =============================================================================

WORKOUT_MAP = {
    # === Tier 1: Intensity (13 types, well-tested) ===

    # VO2max family
    'VO2max 30/30':             ('vo2max', 4),   # VO2max 30/30 archetype
    'VO2max 40/20':             ('vo2max', 5),   # VO2max 40/20 archetype
    'VO2max Extended':          ('vo2max', 6),   # VO2max Extended archetype
    'VO2max Steady Intervals':  ('vo2max', 0),   # 5x3 VO2 Classic
    'VO2 Bookend':              ('durability', 3),  # Durability: VO2 Bookend

    # Threshold family
    'Threshold Accumulation':   ('threshold', 3),  # Threshold Accumulation
    'Threshold Progressive':    ('threshold', 1),  # Threshold Ramps
    'Threshold Steady':         ('threshold', 0),  # Single Sustained Threshold
    'Threshold Touch':          ('threshold', 4),  # Threshold Touch

    # G-Spot / Sweet Spot — route through tempo (g_spot vetoed by POLARIZED methodology)
    # G-Spot = 87-92% FTP sub-threshold, structurally similar to tempo
    'G-Spot':                   ('tempo_workout', 2),
    'Sweet Spot':               ('tempo_workout', 2),

    # Race Simulation
    'Race Simulation':          ('race_sim', 3),   # Race Simulation archetype

    # Tempo family
    'Tempo':                    ('tempo_workout', 2),  # 3x15 Tempo
    'Tempo with Accelerations': ('tempo_workout', 0),  # Tempo Accelerations
    'Tempo with Sprints':       ('tempo_workout', 1),  # Tempo Sprints

    # Climbing / Mixed
    'Mixed Climbing':           ('mixed_climbing', 0),
    'Mixed Climbing Variations':('mixed_climbing', 1),
    'Mixed Intervals':          ('blended', 0),

    # Cadence
    'Cadence Work':             ('cadence_work', 0),

    # Blended
    'Blended 30/30 and SFR':                   ('blended', 0),
    'Blended VO2max and G Spot':               ('blended', 1),
    'Blended Endurance, Threshold, and Sprints':('blended', 2),

    # SFR
    'SFR':                      ('sfr', 0),

    # Neuromuscular
    'Microbursts':              ('gravel_specific', 1),  # Terrain Microbursts
    'Stomps':                   ('sprint', 4),           # Stomps archetype

    # Durability
    'Buffer Workout':           ('durability', 4),       # Buffer Workout

    # === Tier 2: Endurance/Recovery (newly wired through Nate) ===

    'Endurance':                ('endurance', 3),  # Endurance Blocks
    'Endurance Blocks':         ('endurance', 3),  # Endurance Blocks (same)
    'Endurance with Surges':    ('endurance', 2),  # Endurance with Surges
    'Rest Day':                 ('recovery', 1),   # Rest Day
    'Openers':                  ('endurance', 0),  # Pre-Race Openers
    'FTP Test':                 ('testing', 1),    # 20min FTP Test
    'NP/IF Target':             ('endurance', 1),  # Terrain Simulation Z2

    # === Tier 3: Kitchen Sink + SFR series (new archetypes) ===

    'Kitchen Sink - Drain Cleaner': ('kitchen_sink', 0),
    'La Balanguera':                ('kitchen_sink', 1),
    'Hyttevask':                    ('kitchen_sink', 2),

    'Thunder Quads':                ('sfr_series', 0),
    'Blood Pistons':                ('sfr_series', 1),
}

# Normalized lookup: lowercase, stripped → canonical name
_NORMALIZED = {}
for canonical in WORKOUT_MAP:
    key = canonical.lower().strip().replace('-', ' ').replace('/', ' ')
    _NORMALIZED[key] = canonical


def _normalize_name(name: str) -> str:
    """Normalize a workout name for lookup."""
    return name.lower().strip().replace('-', ' ').replace('/', ' ')


def resolve_workout(name: str) -> Optional[Tuple[str, int]]:
    """Resolve a block-builder workout name to (nate_type, variation).

    Returns None if the name isn't in the mapping.
    """
    norm = _normalize_name(name)

    # Direct match
    canonical = _NORMALIZED.get(norm)
    if canonical:
        return WORKOUT_MAP[canonical]

    # Partial match: check if any canonical name starts with the input
    for key, canonical in _NORMALIZED.items():
        if key.startswith(norm) or norm.startswith(key):
            return WORKOUT_MAP[canonical]

    # Kitchen Sink family detection
    ks_keywords = ['kitchen sink', 'drain cleaner', 'la balanguera', 'hyttevask',
                   'kjokkenvask', 'haarsaar', 'rema tusen']
    if any(kw in norm for kw in ks_keywords):
        # TODO: Route to kitchen_sink archetype when available
        # For now, use race_sim as closest existing archetype
        return ('race_sim', 7)  # Kitchen Sink All-Systems

    # SFR series detection
    sfr_keywords = ['thunder quads', 'blood pistons', 'flooded stomps',
                    'over and out', 'tough as old boots']
    if any(kw in norm for kw in sfr_keywords):
        return ('sfr', 0)

    return None


def render_workout(
    name: str,
    level: int = 3,
    methodology: str = 'POLARIZED',
    workout_name: Optional[str] = None,
    variation_offset: int = 0,
) -> Optional[str]:
    """Render a block-builder workout name to ZWO XML.

    Args:
        name: Block-builder canonical workout name (e.g., 'VO2max 30/30')
        level: Progression level 1-6
        methodology: Training methodology for archetype selection
        workout_name: Optional ZWO file name override
        variation_offset: Added to base variation to cycle through archetypes
            within a category. Caller increments per workout to get variety.

    Returns:
        ZWO XML string, or None if the workout can't be rendered.
    """
    mapping = resolve_workout(name)
    if mapping is None:
        return None

    nate_type, base_variation = mapping

    # ----------------------------------------------------------------
    # SIMPLE ENDURANCE: Match TP library exactly.
    # TP Endurance L1-L6 = steady Z2 ride + cooldown. No segments,
    # no alternating power, no surges. Just ride at 70% for the duration.
    # This is what a real coach prescribes for easy days.
    # ----------------------------------------------------------------
    if name == 'Endurance':
        return _render_simple_endurance(level, workout_name)

    # Pin certain workout types to their exact archetype — no variation cycling.
    PINNED_TYPES = {'Openers', 'FTP Test', 'Rest Day', 'Endurance with Surges', 'NP/IF Target',
                     'Race Simulation', 'Kitchen Sink - Drain Cleaner', 'La Balanguera',
                     'Hyttevask', 'Thunder Quads', 'Blood Pistons'}
    effective_variation = base_variation
    if name not in PINNED_TYPES and variation_offset > 0:
        effective_variation = base_variation + variation_offset

    return generate_nate_zwo(
        workout_type=nate_type,
        level=level,
        methodology=methodology,
        variation=effective_variation,
        workout_name=workout_name,
    )


# TP Library Endurance: steady Z2 + cooldown. Level scales duration only.
_ENDURANCE_LEVELS = {
    1: {'duration_min': 70,  'power': 0.68},
    2: {'duration_min': 100, 'power': 0.69},
    3: {'duration_min': 130, 'power': 0.70},
    4: {'duration_min': 160, 'power': 0.70},
    5: {'duration_min': 190, 'power': 0.70},
    6: {'duration_min': 250, 'power': 0.70},
}

def _render_simple_endurance(level: int, workout_name: Optional[str] = None) -> str:
    """Render a simple endurance workout matching the TP library.

    Structure: Warmup → Steady Z2 → Cooldown.
    Level controls duration only. Power stays at ~70% FTP.
    This matches what a real coach puts on TrainingPeaks.
    """
    cfg = _ENDURANCE_LEVELS.get(level, _ENDURANCE_LEVELS[3])
    total_sec = cfg['duration_min'] * 60
    power = cfg['power']

    warmup_sec = 600  # 10min warmup
    cooldown_sec = 600  # 10min cooldown
    main_sec = total_sec - warmup_sec - cooldown_sec

    if main_sec < 600:  # Minimum 10min main set
        main_sec = 600
        warmup_sec = 300
        cooldown_sec = 300

    name = workout_name or f'Endurance_L{level}'
    desc = (
        f"MAIN SET:\n"
        f"- {main_sec // 60}min @ 66-75% FTP (RPE 3-4)\n"
        f"- Position: Alternate every 30 min: drops (aero) → hoods (power)\n"
        f"- Cadence: self-selected, comfortable endurance cadence\n\n"
        f"COOL-DOWN:\n"
        f"- {cooldown_sec // 60}min easy spin Z1-Z2 (RPE 2-3)\n\n"
        f"PURPOSE:\n"
        f"Aerobic base building. Easy riding builds mitochondrial density "
        f"and fat oxidation — the foundation everything else rests on.\n\n"
        f"Level {level}: Cadence and position focus. Same structure — refine the execution."
    )

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{name}</name>
  <description>{desc}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="{warmup_sec}" PowerLow="0.50" PowerHigh="{power:.2f}"/>
    <SteadyState Duration="{main_sec}" Power="{power:.2f}"/>
    <Cooldown Duration="{cooldown_sec}" PowerLow="{power:.2f}" PowerHigh="0.45"/>
  </workout>
</workout_file>"""


def get_mapped_types() -> list:
    """Return list of all mapped block-builder workout names."""
    return sorted(WORKOUT_MAP.keys())


def get_unmapped_tier3() -> list:
    """Return list of Tier 3 workout names that need new archetypes."""
    return [
        'Kitchen Sink - Drain Cleaner',
        'La Balanguera 1', 'La Balanguera 2', 'La Balanguera 3',
        'Hyttevask 1', 'Hyttevask 2', 'Hyttevask 3',
        'Kjokkenvask - De Tre Sostre', 'Kjokkenvask - Svake Knaer',
        'Haarsaar 1', 'Rema Tusen 1',
        'Thunder Quads', 'Blood Pistons', 'Flooded Stomps',
        'Over and Out', 'Tough as Old Boots',
    ]


if __name__ == '__main__':
    print(f"Mapped: {len(WORKOUT_MAP)} workout types")
    print(f"Unmapped Tier 3: {len(get_unmapped_tier3())} types (need new archetypes)")

    print("\n=== Render test ===")
    for name in ['VO2max 30/30', 'Endurance', 'Threshold Accumulation', 'Openers', 'Recovery']:
        zwo = render_workout(name, level=3, workout_name=f'test_{name.replace(" ", "_")}')
        status = f"{len(zwo)} bytes" if zwo else "FAILED"
        print(f"  {name}: {status}")
