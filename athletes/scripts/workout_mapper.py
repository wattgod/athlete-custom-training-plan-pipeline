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
import html
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure script dir on path (flat layout — all files in athletes/scripts/)
_SCRIPT_DIR = str(Path(__file__).parent.resolve())
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from nate_workout_generator import generate_nate_zwo


# Race-week sharpness is a session-dose policy, not an archetype-progression
# prize.  These are deliberately evaluated after the calendar has selected the
# sharpener slot, against the rendered ZWO's actual duration/TSS/IF.  That
# protects us from a future archetype or duration-scaling change quietly
# turning race week into a hard training session again.
RACE_WEEK_SHARPENER_WINDOW = {
    'min_if': 0.78,
    'max_if': 0.86,
    'min_tss': 55,
    'max_tss': 75,
}

# Levels are dose variants for the same race-week session.  They are not the
# usual six-level development ladder: race week calls for the smallest dose
# that preserves snap.  Each variant retains two short pyramids, three-minute
# easy recovery between sets, and generous easy-riding padding.
_RACE_WEEK_SHARPENER_DOSES = {
    1: {'duration_min': 58, 'powers': (1.40, 1.50, 1.55)},
    2: {'duration_min': 62, 'powers': (1.40, 1.50, 1.55)},
}


def _render_race_eve_openers(
    workout_name: Optional[str] = None,
    author: str = 'Gravel God Training',
    display_name: Optional[str] = None,
) -> str:
    """Race-eve activation with a whole-session dose below 40 TSS / 0.80 IF."""
    name = html.escape(display_name or workout_name or 'Openers', quote=False)
    escaped_author = html.escape(author or 'Gravel God Training', quote=False)
    description = '''WARM-UP:
-10min building from Z1 to Z2

MAIN SET:
-7min relaxed Z2, then 2min @ 120% FTP
-3min easy Z1
-3x30sec @ 125% FTP with 2min easy Z1 between efforts
-Cadence: 100-120rpm on the short stabs; 90-100rpm while riding easy

COOL-DOWN:
-10min easy spin Z1-Z2

PURPOSE:
Race-eve activation: wake the legs without creating fatigue.

EXECUTION:
-The 2-minute effort is controlled, not a test. Finish feeling more ready than tired.'''
    return f'''<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>{escaped_author}</author>
  <name>{name}</name>
  <description>{description}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="600" PowerLow="0.50" PowerHigh="0.70" CadenceLow="90" CadenceHigh="100"/>
    <SteadyState Duration="420" Power="0.65" CadenceLow="90" CadenceHigh="100"/>
    <SteadyState Duration="120" Power="1.20" CadenceLow="100" CadenceHigh="120"/>
    <SteadyState Duration="180" Power="0.55" CadenceLow="90" CadenceHigh="100"/>
    <IntervalsT Repeat="3" OnDuration="30" OnPower="1.25" CadenceLow="100" CadenceHigh="120" OffDuration="120" OffPower="0.55"/>
    <Cooldown Duration="600" PowerLow="0.65" PowerHigh="0.45" CadenceLow="90" CadenceHigh="100"/>
  </workout>
</workout_file>'''


def _render_race_week_sharpener(
    level: int,
    workout_name: Optional[str] = None,
    author: str = 'Gravel God Training',
    display_name: Optional[str] = None,
) -> str:
    """Render the coach-approved 20/30/40 race-week sharpener.

    The deliberately long easy padding is part of the prescription: it keeps
    a few high-quality efforts inside a whole-session dose that freshens the
    athlete rather than adding a final hard workout before the event.
    """
    dose = _RACE_WEEK_SHARPENER_DOSES.get(
        min(level, max(_RACE_WEEK_SHARPENER_DOSES)), _RACE_WEEK_SHARPENER_DOSES[2])
    target = dose['duration_min'] * 60
    p20, p30, p40 = dose['powers']
    warmup, cooldown = 900, 600
    # One set is 20/30/40sec with real Z1 recoveries.  The three-minute reset
    # is retained between the two sets; any remaining time is low-Z2 padding.
    set_seconds = (20 + 60) + (30 + 120) + (40 + 120)
    between_sets = 180
    fixed_seconds = warmup + cooldown + 2 * set_seconds + between_sets
    padding = max(0, target - fixed_seconds)
    # Long easy blocks are whole minutes so the executable description never
    # produces misleading ``M:SS`` prose for a session the athlete reads in
    # minutes.  Sub-minute efforts remain exact below.
    pre_padding = (padding // 120) * 60
    post_padding = padding - pre_padding
    cadence = ' CadenceLow="100" CadenceHigh="120"'
    set_xml = f'''    <SteadyState Duration="20" Power="{p20:.2f}"{cadence}/>
    <SteadyState Duration="60" Power="0.55" CadenceLow="100" CadenceHigh="110"/>
    <SteadyState Duration="30" Power="{p30:.2f}"{cadence}/>
    <SteadyState Duration="120" Power="0.55" CadenceLow="100" CadenceHigh="110"/>
    <SteadyState Duration="40" Power="{p40:.2f}"{cadence}/>
    <SteadyState Duration="120" Power="0.55" CadenceLow="100" CadenceHigh="110"/>'''
    name = html.escape(display_name or workout_name or 'Stars In Your Eyes', quote=False)
    escaped_author = html.escape(author or 'Gravel God Training', quote=False)
    description = (
        'WARM-UP:\n'
        '-15min building from Z1 to Z2\n\n'
        'MAIN SET:\n'
        '-2 x (20sec @ {p20:.0%}, 30sec @ {p30:.0%}, 40sec @ {p40:.0%} FTP)\n'
        '-1min / 2min / 2min easy Z1 between the 20sec / 30sec / 40sec efforts\n'
        '-3min easy Z1 between sets; use the remaining ride as relaxed Z2 padding\n'
        '-Cadence: 100-120rpm on efforts; 100-110rpm on recoveries\n\n'
        'COOL-DOWN:\n'
        '-10min easy spin Z1-Z2\n\n'
        'PURPOSE:\n'
        'Race-week activation: arrive sharp without accumulating fatigue.\n\n'
        'EXECUTION:\n'
        '-Keep every effort crisp, never maximal. The easy riding and full set break are prescribed recovery, not optional.'
    ).format(p20=p20, p30=p30, p40=p40)
    return f'''<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>{escaped_author}</author>
  <name>{name}</name>
  <description>{description}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="{warmup}" PowerLow="0.50" PowerHigh="0.70" CadenceLow="90" CadenceHigh="100"/>
    <SteadyState Duration="{pre_padding}" Power="0.65" CadenceLow="90" CadenceHigh="100"/>
{set_xml}
    <SteadyState Duration="{between_sets}" Power="0.55" CadenceLow="100" CadenceHigh="110"/>
{set_xml}
    <SteadyState Duration="{post_padding}" Power="0.65" CadenceLow="90" CadenceHigh="100"/>
    <Cooldown Duration="{cooldown}" PowerLow="0.65" PowerHigh="0.45" CadenceLow="90" CadenceHigh="100"/>
  </workout>
</workout_file>'''


def calibrate_race_week_sharpener(
    requested_level: int = 2,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the post-selection sharpener dose that passes its rendered cap.

    Masters athletes and athletes reporting high life stress begin one dose
    lower.  Their safety policy is an upper cap (not a minimum stimulus): a
    slightly easier activation is preferable to manufacturing intensity just
    to hit a numerical floor in race week.
    """
    from zwo_parser import parse_zwo_text

    is_reduced = (athlete_age is not None and athlete_age >= 50) or (
        str(stress_level or '').lower() in {'high', 'very_high'})
    start_level = min(max(_RACE_WEEK_SHARPENER_DOSES), max(1, requested_level))
    if is_reduced:
        start_level = max(1, start_level - 1)

    candidates = []
    for level in range(start_level, 0, -1):
        metrics = parse_zwo_text(_render_race_week_sharpener(level))
        candidate = {'level': level, **metrics}
        candidates.append(candidate)
        if (metrics['intensity_factor'] <= RACE_WEEK_SHARPENER_WINDOW['max_if']
                and metrics['tss'] <= RACE_WEEK_SHARPENER_WINDOW['max_tss']
                and (is_reduced or (
                    metrics['intensity_factor'] >= RACE_WEEK_SHARPENER_WINDOW['min_if']
                    and metrics['tss'] >= RACE_WEEK_SHARPENER_WINDOW['min_tss']))):
            return candidate

    # Never make the race-week load stronger to chase a floor.  This fallback
    # is intentionally the lightest candidate, with the measured values kept
    # for the caller/test report.
    return candidates[-1]


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
    'Thirty-Fifteens':          ('vo2max', 7),   # Ronnestad 30/15 taper stimulus
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
    'Taper Burst Endurance':    ('endurance', 2),  # Z2 with 6s alactic bursts
    'Rest Day':                 ('recovery', 1),   # Rest Day
    'Openers':                  ('endurance', 0),  # Pre-Race Openers
    'FTP Test':                 ('testing', 1),    # 20min FTP Test
    'Anaerobic Test':           ('testing', 2),    # House 360 anaerobic protocol
    'Stars In Your Eyes':       ('anaerobic', 3),  # 20/30/40 race-week sharpener
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


def _resolve_for_discipline(name: str, discipline: str) -> Optional[Tuple[str, int]]:
    """Discipline-safe renderer mapping.

    The canonical Microbursts selector historically points at the
    Gravel_Specific archetype family. That is correct for Gravel God, but a
    Roadie criterium plan then rotates into athlete-visible names such as
    "Gravel Race Simulation." Road plans use the equivalent Burst Intervals
    family instead.
    """
    if (discipline or "").lower() == "road" and name == "Microbursts":
        return ("sprint", 5)  # Burst Intervals
    return resolve_workout(name)


def render_workout(
    name: str,
    level: int = 3,
    methodology: str = 'POLARIZED',
    workout_name: Optional[str] = None,
    variation_offset: int = 0,
    author: str = 'Gravel God Training',
    discipline: str = 'gravel',
    display_name: Optional[str] = None,
) -> Optional[str]:
    """Render a block-builder workout name to ZWO XML.

    Args:
        name: Block-builder canonical workout name (e.g., 'VO2max 30/30')
        level: Progression level 1-6
        methodology: Training methodology for archetype selection
        workout_name: Optional ZWO file name override
        variation_offset: Added to base variation to cycle through archetypes
            within a category. Caller increments per workout to get variety.
        display_name: Optional clean, coach-facing name for the ZWO <name>
            element (no filename/date prefix). Takes priority over
            workout_name for <name> when both are given.

    Returns:
        ZWO XML string, or None if the workout can't be rendered.
    """
    mapping = _resolve_for_discipline(name, discipline)
    if mapping is None:
        return None

    if name == 'Stars In Your Eyes':
        return _render_race_week_sharpener(
            level, workout_name, author, display_name=display_name)

    if name == 'Openers' and level >= 2:
        return _render_race_eve_openers(workout_name, author, display_name=display_name)

    # Scaling the old long-ride surge archetype down to a taper duration also
    # shortened its 14-minute gaps, turning the intended alactic seasoning
    # into a much denser session.  This dedicated renderer keeps the six-second
    # bursts about fourteen minutes apart at every taper duration.
    if name == 'Taper Burst Endurance':
        return _render_taper_burst_endurance(
            level, workout_name, author, display_name=display_name)

    nate_type, base_variation = mapping

    # ----------------------------------------------------------------
    # SIMPLE ENDURANCE: Match TP library exactly.
    # TP Endurance L1-L6 = steady Z2 ride + cooldown. No segments,
    # no alternating power, no surges. Just ride at 70% for the duration.
    # This is what a real coach prescribes for easy days.
    # ----------------------------------------------------------------
    if name == 'Endurance':
        return _render_simple_endurance(level, workout_name, author, display_name=display_name)

    # Pin certain workout types to their exact archetype — no variation cycling.
    PINNED_TYPES = {'Openers', 'FTP Test', 'Anaerobic Test', 'Rest Day', 'Endurance with Surges', 'Taper Burst Endurance', 'Thirty-Fifteens', 'Stars In Your Eyes', 'NP/IF Target',
                     'Race Simulation', 'Kitchen Sink - Drain Cleaner', 'La Balanguera',
                     'Hyttevask', 'Thunder Quads', 'Blood Pistons'}
    effective_variation = base_variation
    if name not in PINNED_TYPES and variation_offset > 0:
        effective_variation = base_variation + variation_offset

    zwo = generate_nate_zwo(
        workout_type=nate_type,
        level=level,
        methodology=methodology,
        variation=effective_variation,
        workout_name=workout_name,
        author=author,
        discipline=discipline,
        display_name=display_name,
    )
    if zwo:
        return zwo

    # The planner (block-builder) explicitly requested this workout; the
    # Nate generator's methodology avoid-list must not veto it into None
    # (MAF_LT1 refused VO2max work, silently dropping those days to legacy
    # templates). The planner's selection wins — render under POLARIZED.
    if methodology != 'POLARIZED':
        return generate_nate_zwo(
            workout_type=nate_type,
            level=level,
            methodology='POLARIZED',
            variation=effective_variation,
            workout_name=workout_name,
            author=author,
            discipline=discipline,
            display_name=display_name,
        )
    return None


# TP Library Endurance: steady Z2 + cooldown. Level scales duration only.
_ENDURANCE_LEVELS = {
    1: {'duration_min': 70,  'power': 0.68},
    2: {'duration_min': 100, 'power': 0.69},
    3: {'duration_min': 130, 'power': 0.70},
    4: {'duration_min': 160, 'power': 0.70},
    5: {'duration_min': 190, 'power': 0.70},
    6: {'duration_min': 250, 'power': 0.70},
}

_TAPER_BURST_LEVELS = {1: 90, 2: 120, 3: 150, 4: 180, 5: 210, 6: 240}
_TAPER_BURST_COUNTS = {1: 5, 2: 7, 3: 9, 4: 11, 5: 13, 6: 15}


def _render_taper_burst_endurance(level: int, workout_name: Optional[str] = None,
                                  author: str = 'Gravel God Training',
                                  display_name: Optional[str] = None) -> str:
    """Z2 endurance with one 6-second alactic burst every ~14 minutes."""
    total_sec = _TAPER_BURST_LEVELS.get(level, _TAPER_BURST_LEVELS[3]) * 60
    burst_count = _TAPER_BURST_COUNTS.get(level, _TAPER_BURST_COUNTS[3])
    # Offset the warmup by the short-burst remainder so every visible Z2
    # segment stays on a whole minute.  The post-render description checker
    # (and, more importantly, athlete readability) should never say 13:48.
    warmup_sec = 600 - ((burst_count * 6) % 60)
    cooldown_sec = 600
    main_sec = max(840, total_sec - warmup_sec - cooldown_sec)
    # Keep all *between-burst* gaps at fourteen minutes.  Any remainder is
    # split before the first and after the final burst, where it does not
    # change the prescribed cadence.
    edge_total = main_sec - burst_count * 6 - max(0, burst_count - 1) * 840
    first_edge = edge_total // 2
    final_edge = edge_total - first_edge
    main_blocks = []
    main_blocks.append(f'    <SteadyState Duration="{first_edge}" Power="0.70"/>')
    for i in range(burst_count):
        main_blocks.append('    <SteadyState Duration="6" Power="1.50"/>')
        if i < burst_count - 1:
            main_blocks.append('    <SteadyState Duration="840" Power="0.70"/>')
    main_blocks.append(f'    <SteadyState Duration="{final_edge}" Power="0.70"/>')
    name = display_name or workout_name or f'Taper_Burst_Endurance_L{level}'
    description = (
        'MAIN SET:\n'
        '- Ride Z2 at 70% FTP\n'
        '- Every ~14min: 6sec full-gas alactic burst, then settle immediately\n\n'
        'PURPOSE:\n'
        'Keep neuromuscular snap during the taper without accumulating fatigue.'
    )
    return f'''<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>{author}</author>
  <name>{name}</name>
  <description>{description}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="{warmup_sec}" PowerLow="0.50" PowerHigh="0.70"/>
{chr(10).join(main_blocks)}
    <Cooldown Duration="{cooldown_sec}" PowerLow="0.70" PowerHigh="0.45"/>
  </workout>
</workout_file>'''

def _render_simple_endurance(level: int, workout_name: Optional[str] = None,
                             author: str = 'Gravel God Training',
                             display_name: Optional[str] = None) -> str:
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

    name = display_name or workout_name or f'Endurance_L{level}'
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
  <author>{author}</author>
  <name>{name}</name>
  <description>{desc}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="{warmup_sec}" PowerLow="0.50" PowerHigh="{power:.2f}"/>
    <SteadyState Duration="{main_sec}" Power="{power:.2f}"/>
    <Cooldown Duration="{cooldown_sec}" PowerLow="{power:.2f}" PowerHigh="0.45"/>
  </workout>
</workout_file>"""


def resolve_display_name(
    name: str,
    methodology: str = 'POLARIZED',
    variation_offset: int = 0,
    discipline: str = 'gravel',
) -> str:
    """Resolve the personality name of the archetype a workout renders as.

    'SFR' is what the selection matrix calls it; 'Thunder Quads' is what
    the athlete sees on the calendar. Mirrors render_workout's archetype
    choice (same pinning + variation rules) so the title always matches
    the rendered content. Falls back to the canonical name.
    """
    if name == 'Endurance':
        return 'Endurance'

    mapping = _resolve_for_discipline(name, discipline)
    if mapping is None:
        return name

    nate_type, base_variation = mapping
    PINNED = {'Openers', 'FTP Test', 'Rest Day', 'Endurance with Surges', 'Taper Burst Endurance', 'Thirty-Fifteens', 'Stars In Your Eyes',
              'NP/IF Target', 'Race Simulation', 'Kitchen Sink - Drain Cleaner',
              'La Balanguera', 'Hyttevask', 'Thunder Quads', 'Blood Pistons'}
    effective_variation = base_variation
    if name not in PINNED and variation_offset > 0:
        effective_variation = base_variation + variation_offset

    try:
        from nate_workout_generator import select_archetype_for_workout
        arch = select_archetype_for_workout(nate_type, methodology, effective_variation)
        if not arch:
            arch = select_archetype_for_workout(nate_type, 'POLARIZED', effective_variation)
        if arch and arch.get('name'):
            return arch['name']
    except Exception:
        pass
    return name


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
