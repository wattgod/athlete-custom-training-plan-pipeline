#!/usr/bin/env python3
"""
Single source of truth for known race data, aliases, and matching logic.

All race metadata (dates, distances, elevations) lives here.
Other scripts import from this module rather than duplicating the data.
"""

from typing import Dict, Optional, Tuple, Any


# ---------------------------------------------------------------------------
# Known races — full metadata
# ---------------------------------------------------------------------------
KNOWN_RACES: Dict[str, Dict[str, Any]] = {
    'unbound_gravel_200': {
        'date': '2026-05-30',
        'name': 'Unbound Gravel 200',
        'distance_miles': 200,
        'elevation_ft': 11000,
    },
    'unbound_gravel_100': {
        'date': '2026-05-30',
        'name': 'Unbound Gravel 100',
        'distance_miles': 100,
        'elevation_ft': 5500,
    },
    'unbound_gravel_50': {
        'date': '2026-05-30',
        'name': 'Unbound Gravel 50',
        'distance_miles': 50,
        'elevation_ft': 2800,
    },
    'unbound_xl': {
        'date': '2026-05-29',
        'name': 'Unbound XL',
        'distance_miles': 350,
        'elevation_ft': 19000,
    },
    'sbt_grvl': {
        'date': '2026-06-28',
        'name': 'SBT GRVL',
        'distance_miles': 141,
        'elevation_ft': 9000,
    },
    'sbt_grvl_75': {
        'date': '2026-06-28',
        'name': 'SBT GRVL 75',
        'distance_miles': 75,
        'elevation_ft': 6732,
    },
    'sbt_grvl_37': {
        'date': '2026-06-28',
        'name': 'SBT GRVL 37',
        'distance_miles': 37,
        'elevation_ft': 3200,
    },
    'leadville_100': {
        'date': '2026-08-15',
        'name': 'Leadville Trail 100 MTB',
        'distance_miles': 100,
        'elevation_ft': 12500,
    },
    'belgian_waffle_ride': {
        'date': '2026-05-17',
        'name': 'Belgian Waffle Ride',
        'distance_miles': 133,
        'elevation_ft': 11000,
    },
    'dirty_kanza_200': {
        'date': '2026-05-30',
        'name': 'Unbound Gravel 200',
        'distance_miles': 200,
        'elevation_ft': 11000,
    },
    'gravel_worlds': {
        'date': '2026-08-22',
        'name': 'Gravel Worlds',
        'distance_miles': 150,
        'elevation_ft': 7500,
    },
    'mid_south': {
        'date': '2026-03-14',
        'name': 'Mid South',
        'distance_miles': 100,
        'elevation_ft': 3000,
    },
    'big_sugar': {
        'date': '2026-10-17',
        'name': 'Big Sugar Gravel',
        'distance_miles': 104,
        'elevation_ft': 6000,
    },
    'boulder_roubaix': {
        'date': '2026-04-11',
        'name': 'Boulder Roubaix',
        'distance_miles': 60,
        'elevation_ft': 2500,
    },
}

# ---------------------------------------------------------------------------
# Simple race_id -> date mapping (backward compat for validation scripts)
# ---------------------------------------------------------------------------
KNOWN_RACE_DATES: Dict[str, str] = {
    race_id: info['date'] for race_id, info in KNOWN_RACES.items()
}

# ---------------------------------------------------------------------------
# Fuzzy aliases for matching user-typed race names
# ---------------------------------------------------------------------------
RACE_ALIASES: Dict[str, str] = {
    'unbound 200': 'unbound_gravel_200',
    'unbound gravel 200': 'unbound_gravel_200',
    'unbound200': 'unbound_gravel_200',
    'dk200': 'unbound_gravel_200',
    'dirty kanza': 'unbound_gravel_200',
    'dirty kanza 200': 'unbound_gravel_200',
    'unbound 100': 'unbound_gravel_100',
    'unbound gravel 100': 'unbound_gravel_100',
    'unbound 50': 'unbound_gravel_50',
    'unbound gravel 50': 'unbound_gravel_50',
    'unbound xl': 'unbound_xl',
    'unbound 350': 'unbound_xl',
    'sbt grvl': 'sbt_grvl',
    'sbt gravel': 'sbt_grvl',
    'steamboat': 'sbt_grvl',
    'sbt grvl 75': 'sbt_grvl_75',
    'sbt 75': 'sbt_grvl_75',
    'sbt grvl 37': 'sbt_grvl_37',
    'sbt 37': 'sbt_grvl_37',
    'leadville': 'leadville_100',
    'leadville 100': 'leadville_100',
    'belgian waffle ride': 'belgian_waffle_ride',
    'bwr': 'belgian_waffle_ride',
    'gravel worlds': 'gravel_worlds',
    'mid south': 'mid_south',
    'mid-south': 'mid_south',
    'big sugar': 'big_sugar',
    'big sugar gravel': 'big_sugar',
    'boulder roubaix': 'boulder_roubaix',
    'boulder roub': 'boulder_roubaix',
}


# ---------------------------------------------------------------------------
# Race matching function
# ---------------------------------------------------------------------------
def match_race(name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Fuzzy-match a user-provided race name to a known race.
    Returns (race_id, race_info) or None.
    """
    normalized = name.strip().lower()

    # Direct alias match
    if normalized in RACE_ALIASES:
        race_id = RACE_ALIASES[normalized]
        return race_id, KNOWN_RACES[race_id]

    # Substring matching on known race names
    for race_id, info in KNOWN_RACES.items():
        if normalized in info['name'].lower() or info['name'].lower() in normalized:
            return race_id, info

    # Token matching: if any known race name words match significantly
    name_tokens = set(normalized.split())
    best_match = None
    best_score = 0
    for race_id, info in KNOWN_RACES.items():
        race_tokens = set(info['name'].lower().split())
        overlap = len(name_tokens & race_tokens)
        if overlap > best_score and overlap >= 1:
            best_score = overlap
            best_match = (race_id, info)

    if best_match and best_score >= 1:
        return best_match

    return None
