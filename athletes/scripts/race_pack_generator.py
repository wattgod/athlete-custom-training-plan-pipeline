#!/usr/bin/env python3
"""Race pack generator -- end-to-end CLI orchestrator.

Sprint 5 of the race-to-archetype mapping system.

Generates a race-specific training pack:
1. Loads race JSON from --race-data-dir
2. Computes demand vector (inline analysis)
3. Scores archetype categories
4. Selects workout pack
5. Generates ZWO files
6. Enhances with rider intel
7. Generates coaching brief
8. Copies everything to ~/Downloads/{slug}-training-pack/

Usage:
    python3 race_pack_generator.py --race unbound-200 \\
        --ftp 250 --level 3 --pack-size 10 \\
        --race-data-dir /path/to/race-data

    # Or with defaults:
    python3 race_pack_generator.py --race unbound-200
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# Add script directory for local imports
_module_dir = Path(__file__).resolve().parent
if str(_module_dir) not in sys.path:
    sys.path.insert(0, str(_module_dir))

from race_category_scorer import calculate_category_scores, get_top_categories
from race_pack_selector import select_workout_pack, generate_race_pack_zwos
from race_intel_enhancer import enhance_with_rider_intel, generate_race_brief


# =============================================================================
# DEFAULT RACE DATA DIRECTORY
# =============================================================================
# The authoritative race data lives in the gravel-race-automation repo.
# This default assumes both repos are checked out under ~/Documents/GravelGod/
DEFAULT_RACE_DATA_DIR = Path.home() / 'Documents' / 'GravelGod' / 'gravel-race-automation' / 'race-data'


# =============================================================================
# INLINE DEMAND ANALYSIS
# =============================================================================
# This is a consumer copy of the demand analysis logic.
# The authoritative implementation lives in gravel-race-automation.
# This version reads the same race JSON format and produces the same
# 8-dimension demand vector (each 0-10).
# =============================================================================

_HEAT_KEYWORDS = ['heat', 'hot', 'hydration', 'sun exposure', 'humidity', 'heat adaptation', 'overheating']


def _safe_numeric_str(val, default=0.0) -> float:
    """Parse numeric from string like '4,500-9,116' — takes first number."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).replace(',', '')
        return float(s.split('-')[0].strip())
    except (ValueError, IndexError):
        return default


def analyze_race_demands(race_data: dict) -> dict:
    """Compute an 8-dimension demand vector from race JSON data.

    This is a consumer copy of the authoritative implementation in
    gravel-race-automation/scripts/race_demand_analyzer.py.
    Must produce IDENTICAL results for the same input.

    Returns:
        Dict with 8 keys, each integer 0-10.
    """
    race = race_data.get('race', {})
    vitals = race.get('vitals', {})
    rating = race.get('gravel_god_rating', {})
    climate_block = race.get('climate', {})

    def _g(d, k, default=0):
        v = d.get(k)
        return default if v is None else v

    demands = {}

    # --- Durability: distance thresholds + bikepacking boost ---
    dist = _safe_numeric_str(vitals.get('distance_mi'), 0)
    if dist >= 200: dur = 10
    elif dist >= 150: dur = 8
    elif dist >= 100: dur = 6
    elif dist >= 75: dur = 4
    elif dist >= 50: dur = 2
    else: dur = 1
    if _g(rating, 'discipline', 'gravel') == 'bikepacking':
        dur += 2
    demands['durability'] = _clamp(dur)

    # --- Climbing: elevation_score * 1.5 + elevation_ft / 5000 ---
    elev_ft = _safe_numeric_str(vitals.get('elevation_ft'), 0)
    elev_score = _g(rating, 'elevation', 0)
    demands['climbing'] = _clamp(round(elev_score * 1.5 + elev_ft / 5000))

    # --- VO2 Power: (field_depth + prestige) * 1.0 ---
    field_depth = _g(rating, 'field_depth', 0)
    prestige = _g(rating, 'prestige', 0)
    demands['vo2_power'] = _clamp(round((field_depth + prestige) * 1.0))

    # --- Threshold: distance bands + climbing boost ---
    if 75 <= dist <= 150: thr = 7
    elif 50 <= dist < 75: thr = 5
    elif dist > 150: thr = 4
    else: thr = 3
    if elev_score >= 3:
        thr += 1
    demands['threshold'] = _clamp(thr)

    # --- Technical: technicality * 2 ---
    demands['technical'] = _clamp(_g(rating, 'technicality', 0) * 2)

    # --- Heat Resilience: climate score base + intel/challenges keywords ---
    climate_score = _g(rating, 'climate', 0)
    if climate_score >= 5: heat = 10
    elif climate_score == 4: heat = 6
    else: heat = 0
    # Rider intel boost
    intel = race.get('youtube_data', {}).get('rider_intel', {})
    st = (_g(intel, 'search_text', '') or '').lower()
    if any(kw in st for kw in _HEAT_KEYWORDS):
        heat += 2
    # Climate challenges boost
    challenges_text = ' '.join(climate_block.get('challenges', [])).lower()
    if any(kw in challenges_text for kw in _HEAT_KEYWORDS):
        heat += 1
    demands['heat_resilience'] = _clamp(heat)

    # --- Altitude: altitude_score * 2 ---
    demands['altitude'] = _clamp(_g(rating, 'altitude', 0) * 2)

    # --- Race Specificity: (5 - tier) * 2 + prestige ---
    tier = _g(rating, 'tier', 4)
    demands['race_specificity'] = _clamp(round((5 - tier) * 2 + prestige))

    return demands


def _scale_linear(value: float, low: float, high: float, out_low: float, out_high: float) -> float:
    """Linear interpolation from [low, high] -> [out_low, out_high]."""
    if high <= low:
        return out_low
    ratio = (value - low) / (high - low)
    ratio = max(0.0, min(1.0, ratio))
    return out_low + ratio * (out_high - out_low)


def _clamp(value, lo=0, hi=10) -> int:
    """Clamp to integer in [lo, hi]."""
    return max(lo, min(hi, int(round(value))))


def _safe_float(val, default=0.0) -> float:
    """Safely convert to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0) -> int:
    """Safely convert to int."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# =============================================================================
# RACE JSON LOADING
# =============================================================================

def load_race_json(slug: str, race_data_dir: Path) -> dict:
    """Load a race JSON file by slug.

    Args:
        slug: Race slug (e.g., 'unbound-200').
        race_data_dir: Directory containing {slug}.json files.

    Returns:
        Parsed race data dict.

    Raises:
        FileNotFoundError: If race JSON not found.
    """
    filepath = race_data_dir / f"{slug}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Race JSON not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# =============================================================================
# ORCHESTRATOR
# =============================================================================

def generate_race_pack(
    slug: str,
    race_data_dir: Path = None,
    ftp: int = 200,
    level: int = 3,
    pack_size: int = 10,
    output_base: Path = None,
) -> dict:
    """End-to-end race pack generation.

    Args:
        slug: Race slug (e.g., 'unbound-200').
        race_data_dir: Path to race-data directory.
        ftp: Functional threshold power in watts.
        level: Archetype level 1-6.
        pack_size: Number of workouts in pack.
        output_base: Base output directory (default: ~/Downloads/{slug}-training-pack).

    Returns:
        Dict with keys: slug, demands, category_scores, pack, zwo_paths, brief_path, output_dir.
    """
    if race_data_dir is None:
        race_data_dir = DEFAULT_RACE_DATA_DIR

    if output_base is None:
        output_base = Path.home() / 'Downloads' / f"{slug}-training-pack"

    # 1. Load race JSON
    race_data = load_race_json(slug, race_data_dir)

    # 2. Compute demand vector
    demands = analyze_race_demands(race_data)

    # 3. Score categories
    category_scores = calculate_category_scores(demands)

    # 4. Select workout pack
    pack = select_workout_pack(category_scores, pack_size=pack_size)

    # 5. Generate ZWO files
    zwo_dir = output_base / 'workouts'
    zwo_paths = generate_race_pack_zwos(pack, zwo_dir, ftp=ftp, level=level)

    # 6. Enhance with rider intel
    pack = enhance_with_rider_intel(pack, race_data)

    # 7. Generate brief
    brief_md = generate_race_brief(race_data, pack, demands)
    brief_path = output_base / 'race-training-brief.md'
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_md, encoding='utf-8')

    # 8. Write demands and scores for reference
    meta = {
        'slug': slug,
        'ftp': ftp,
        'level': level,
        'demands': demands,
        'category_scores': category_scores,
        'pack': [
            {
                'category': item['category'],
                'archetype_name': item['archetype_name'],
                'relevance_score': item['relevance_score'],
                'level': item['level'],
                'citations': len(item.get('rider_intel_citations', [])),
            }
            for item in pack
        ],
    }
    meta_path = output_base / 'pack-metadata.json'
    meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')

    return {
        'slug': slug,
        'demands': demands,
        'category_scores': category_scores,
        'pack': pack,
        'zwo_paths': zwo_paths,
        'brief_path': brief_path,
        'meta_path': meta_path,
        'output_dir': output_base,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate a race-specific training pack with ZWO files and coaching brief.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 race_pack_generator.py --race unbound-200
    python3 race_pack_generator.py --race leadville-trail-100-mtb --ftp 280 --level 4
    python3 race_pack_generator.py --race steamboat-gravel --pack-size 8
        """,
    )
    parser.add_argument('--race', required=True, help='Race slug (e.g., unbound-200)')
    parser.add_argument('--ftp', type=int, default=200, help='FTP in watts (default: 200)')
    parser.add_argument('--level', type=int, default=3, choices=range(1, 7), help='Archetype level 1-6 (default: 3)')
    parser.add_argument('--pack-size', type=int, default=10, help='Number of workouts (default: 10)')
    parser.add_argument('--race-data-dir', type=Path, default=None, help='Path to race-data directory')
    parser.add_argument('--output-dir', type=Path, default=None, help='Output directory (default: ~/Downloads/{slug}-training-pack)')

    args = parser.parse_args()

    print(f"GRAVEL GOD RACE PACK GENERATOR")
    print(f"{'=' * 50}")
    print(f"Race:       {args.race}")
    print(f"FTP:        {args.ftp}W")
    print(f"Level:      {args.level}/6")
    print(f"Pack size:  {args.pack_size}")
    print()

    try:
        result = generate_race_pack(
            slug=args.race,
            race_data_dir=args.race_data_dir,
            ftp=args.ftp,
            level=args.level,
            pack_size=args.pack_size,
            output_base=args.output_dir,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Print summary
    print("DEMAND PROFILE")
    print("-" * 50)
    for dim in ['durability', 'climbing', 'vo2_power', 'threshold',
                'technical', 'heat_resilience', 'altitude', 'race_specificity']:
        score = result['demands'].get(dim, 0)
        bar = "#" * score + "." * (10 - score)
        print(f"  {dim:20s} [{bar}] {score}/10")
    print()

    print("TOP CATEGORY SCORES")
    print("-" * 50)
    for cat, score in list(result['category_scores'].items())[:10]:
        print(f"  {score:3d}  {cat}")
    print()

    print(f"WORKOUT PACK ({len(result['pack'])} workouts)")
    print("-" * 50)
    for i, item in enumerate(result['pack'], 1):
        citations = len(item.get('rider_intel_citations', []))
        intel_tag = f" [{citations} citations]" if citations else ""
        print(f"  {i:2d}. [{item['relevance_score']:3d}] {item['category']:25s} | {item['archetype_name']}{intel_tag}")
    print()

    print(f"OUTPUT")
    print("-" * 50)
    print(f"  Directory:  {result['output_dir']}")
    print(f"  ZWO files:  {len(result['zwo_paths'])}")
    print(f"  Brief:      {result['brief_path']}")
    print(f"  Metadata:   {result['meta_path']}")
    print()
    print("Done.")


if __name__ == '__main__':
    main()
