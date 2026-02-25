#!/usr/bin/env python3
"""
ARCHETYPE REGISTRY — Single source of truth for the Gravel God workout system.

Run this file directly for a full system summary:
    python3 archetype_registry.py

=============================================================================
SYSTEM ARCHITECTURE
=============================================================================

Three data files merge at import time into NEW_ARCHETYPES (95 archetypes):

  new_archetypes.py          45 base archetypes (16 categories)
    ↓ merges at import
  imported_archetypes.py     34 imported archetypes (6 new + 6 augmented categories)
    ↓ merges at import
  advanced_archetypes.py     16 advanced archetypes (8 augmented categories)
    = 95 total across 22 categories, 570 variations (6 levels each)

MERGE RULES:
  - Imported/advanced archetypes append to existing categories (dedup by name)
  - New categories are added whole
  - Merge order: base → imported → advanced (first definition wins on name collision)
  - Merge happens in new_archetypes.py at module load time

ARCHETYPE FORMATS:
  Format A (intervals):  'intervals' tuple + 'on_power', 'off_power', 'off_duration'
  Format B (segments):   list of dicts with type/duration/power
  Format C (single):     'single_effort' = True + 'duration' + 'power'
  Format D (tired_vo2):  'tired_vo2' = True + 'base_duration' + 'intervals'

SEGMENT TYPES (Format B):
  steady, intervals, freeride, ramp

HELPER FUNCTIONS (advanced_archetypes.py):
  _criss_cross()        — alternating floor/ceiling power, exact duration
  _base_with_efforts()  — evenly distributed efforts within base ride, exact duration
  _hard_start_reps()    — burst → threshold hold with recovery
  _attack_reps()        — tempo base then repeated attacks
  _gravel_sim_efforts() — interleaved sectors and surges for race sim

PRODUCTION CONSUMER:
  nate_workout_generator.py imports NEW_ARCHETYPES from new_archetypes.py (line 162)

=============================================================================
"""

import copy


# Import the fully merged archetype dict (95 archetypes, 22 categories)
from new_archetypes import NEW_ARCHETYPES

# Also import individual sources for catalog tracking
from imported_archetypes import IMPORTED_ARCHETYPES
from advanced_archetypes import ADVANCED_ARCHETYPES

# The merged result — use this for all production and test access
ALL_ARCHETYPES = NEW_ARCHETYPES

# Expected counts — tests use these as guards
EXPECTED_TOTAL = 95
EXPECTED_CATEGORIES = 22
EXPECTED_VARIATIONS = EXPECTED_TOTAL * 6  # 570


# =============================================================================
# SOURCE TRACKING — answers "which file defines this archetype?"
# =============================================================================

def _build_source_map():
    """Build a map of archetype name → source file.

    Checks advanced first, then imported, then base (reverse merge order)
    so the most specific source wins.
    """
    source_map = {}

    # Base archetypes (new_archetypes.py defines the originals inline)
    # Everything in NEW_ARCHETYPES starts as base unless overridden below
    for category, archetypes in NEW_ARCHETYPES.items():
        for arch in archetypes:
            source_map[arch['name']] = {
                'file': 'new_archetypes.py',
                'category': category,
            }

    # Imported archetypes override base attribution
    for category, archetypes in IMPORTED_ARCHETYPES.items():
        for arch in archetypes:
            source_map[arch['name']] = {
                'file': 'imported_archetypes.py',
                'category': category,
            }

    # Advanced archetypes override everything
    for category, archetypes in ADVANCED_ARCHETYPES.items():
        for arch in archetypes:
            source_map[arch['name']] = {
                'file': 'advanced_archetypes.py',
                'category': category,
            }

    return source_map


# Precomputed at import time
_SOURCE_MAP = _build_source_map()


def get_archetype_source(name):
    """Return {'file': ..., 'category': ...} for an archetype by name.

    >>> get_archetype_source('Criss-Cross Intervals')
    {'file': 'advanced_archetypes.py', 'category': 'TT_Threshold'}
    """
    return _SOURCE_MAP.get(name)


def get_archetype(name):
    """Find an archetype by name across all categories.

    Returns (category, archetype_dict) or None.

    >>> cat, arch = get_archetype('Float Sets')
    >>> arch['levels']['1']['on_power']
    1.06
    """
    for category, archetypes in ALL_ARCHETYPES.items():
        for arch in archetypes:
            if arch['name'] == name:
                return category, arch
    return None


def list_archetypes(category=None, source_file=None):
    """List archetypes with metadata, optionally filtered.

    Args:
        category: Filter to a specific category (e.g. 'VO2max')
        source_file: Filter to a specific source (e.g. 'advanced_archetypes.py')

    Returns list of dicts: [{'name', 'category', 'source', 'levels', 'format'}, ...]
    """
    result = []
    categories = {category: ALL_ARCHETYPES[category]} if category else ALL_ARCHETYPES

    for cat, archetypes in categories.items():
        for arch in archetypes:
            source = _SOURCE_MAP.get(arch['name'], {})
            if source_file and source.get('file') != source_file:
                continue

            # Detect format
            l1 = arch['levels']['1']
            if l1.get('tired_vo2'):
                fmt = 'D (tired_vo2)'
            elif l1.get('single_effort'):
                fmt = 'C (single_effort)'
            elif 'segments' in l1:
                fmt = 'B (segments)'
            elif 'intervals' in l1 and isinstance(l1['intervals'], tuple):
                fmt = 'A (intervals)'
            else:
                fmt = 'unknown'

            result.append({
                'name': arch['name'],
                'category': cat,
                'source': source.get('file', 'unknown'),
                'levels': 6,
                'format': fmt,
            })
    return result


def validate_registry():
    """Run integrity checks. Returns (ok: bool, errors: list[str])."""
    errors = []

    # Count check
    total = sum(len(a) for a in ALL_ARCHETYPES.values())
    if total != EXPECTED_TOTAL:
        errors.append(f"Expected {EXPECTED_TOTAL} archetypes, got {total}")
    if len(ALL_ARCHETYPES) != EXPECTED_CATEGORIES:
        errors.append(
            f"Expected {EXPECTED_CATEGORIES} categories, got {len(ALL_ARCHETYPES)}")

    # Duplicate name check
    seen = {}
    for cat, archetypes in ALL_ARCHETYPES.items():
        for arch in archetypes:
            name = arch['name']
            if name in seen:
                errors.append(
                    f"Duplicate name '{name}' in {seen[name]} and {cat}")
            seen[name] = cat

    # Level completeness check
    for cat, archetypes in ALL_ARCHETYPES.items():
        for arch in archetypes:
            levels = set(arch.get('levels', {}).keys())
            expected = {'1', '2', '3', '4', '5', '6'}
            if levels != expected:
                errors.append(
                    f"{arch['name']}: has levels {levels}, expected {expected}")

    return (len(errors) == 0, errors)


# =============================================================================
# CLI SUMMARY — run `python3 archetype_registry.py` for full system status
# =============================================================================

def print_summary():
    """Print a complete system summary."""
    ok, errors = validate_registry()

    print("=" * 72)
    print("  GRAVEL GOD WORKOUT ARCHETYPE REGISTRY")
    print("=" * 72)
    print()

    # Validation status
    if ok:
        print(f"  STATUS: ALL CHECKS PASSED")
    else:
        print(f"  STATUS: {len(errors)} ERROR(S)")
        for e in errors:
            print(f"    - {e}")
    print()

    # Totals
    total = sum(len(a) for a in ALL_ARCHETYPES.values())
    print(f"  Total archetypes:  {total}")
    print(f"  Total categories:  {len(ALL_ARCHETYPES)}")
    print(f"  Total variations:  {total * 6}")
    print()

    # Source breakdown
    sources = {}
    for info in _SOURCE_MAP.values():
        f = info['file']
        sources[f] = sources.get(f, 0) + 1
    print("  BY SOURCE FILE:")
    for f in ['new_archetypes.py', 'imported_archetypes.py', 'advanced_archetypes.py']:
        count = sources.get(f, 0)
        print(f"    {f:<30s} {count:>3d} archetypes")
    print()

    # Category breakdown
    print("  BY CATEGORY:")
    for cat in sorted(ALL_ARCHETYPES.keys()):
        archetypes = ALL_ARCHETYPES[cat]
        names = [a['name'] for a in archetypes]
        print(f"    {cat:<25s} ({len(archetypes):>2d}): {', '.join(names)}")
    print()

    # Format breakdown
    formats = {}
    for info in list_archetypes():
        fmt = info['format']
        formats[fmt] = formats.get(fmt, 0) + 1
    print("  BY FORMAT:")
    for fmt in sorted(formats.keys()):
        print(f"    {fmt:<25s} {formats[fmt]:>3d} archetypes")
    print()

    print("=" * 72)
    print(f"  Source of truth: archetype_registry.py")
    print(f"  Data files: new_archetypes.py + imported_archetypes.py + advanced_archetypes.py")
    print(f"  Production consumer: nate_workout_generator.py (line 162)")
    print("=" * 72)


if __name__ == '__main__':
    print_summary()
