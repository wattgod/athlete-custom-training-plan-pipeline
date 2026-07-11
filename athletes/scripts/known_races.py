#!/usr/bin/env python3
"""
Single source of truth for known race data, aliases, and matching logic.

All race metadata (dates, distances, elevations) lives here.
Other scripts import from this module rather than duplicating the data.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

# The curated KNOWN_RACES below carry hand-tuned aliases and are authoritative.
# Beyond them, match_race falls back to the full 1,184-race snapshot
# (config/races.json, built by build_race_snapshot.py) so a real customer's
# race validates against the actual database, not just this hand-list.
_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "config" / "races.json"


@lru_cache(maxsize=1)
def _snapshot_races() -> Dict[str, Dict[str, Any]]:
    """Load the race snapshot, normalized to the KNOWN_RACES field shape
    (distance_mi -> distance_miles). Keyed by 'discipline:slug'."""
    if not _SNAPSHOT_PATH.exists():
        return {}
    try:
        data = json.loads(_SNAPSHOT_PATH.read_text())
    except Exception:
        return {}
    races = data.get("races", {})
    # Names listed under more than one discipline (an event in both the
    # gravel AND road DBs) are discipline-AMBIGUOUS — don't claim a
    # discipline for them; let the guide's keyword logic decide.
    by_name = {}
    for e in races.values():
        by_name.setdefault((e.get("name") or "").strip().lower(), set()).add(
            e.get("discipline"))
    ambiguous = {n for n, ds in by_name.items() if len(ds) > 1}

    out = {}
    for key, e in races.items():
        if not e.get("date"):
            continue  # date validation needs a specific date
        name = e.get("name", "")
        disc = e.get("discipline")
        if name.strip().lower() in ambiguous:
            disc = None
        out[key] = {
            "name": name,
            "date": e.get("date"),
            "distance_miles": e.get("distance_mi"),
            "elevation_ft": e.get("elevation_ft") or 0,
            "discipline": disc,
            "location": e.get("location", ""),
        }
    return out


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
        # reconciled to race-data/unbound-100.json (Opus, Jul 11 2026)
        'date': '2026-05-30',
        'name': 'Unbound Gravel 100',
        'distance_miles': 104,
        'elevation_ft': 4000,
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
        # 2026 course is shorter -- 141mi was the old distance (Matti, Jul 10 2026)
        'date': '2026-06-28',
        'name': 'SBT GRVL',
        'distance_miles': 108,
        'elevation_ft': 8189,
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
        # Course length changes year to year (104mi in 2023, 99.6mi in
        # 2025). 100 matches race-data/big-sugar.json (this repo's source
        # of truth, corroborated by the 1,184-race snapshot) and the
        # current course. The old 104 was a stale 2023 figure — caught by
        # gravel-race-automation/scripts/validate_race_data.py.
        'distance_miles': 100,
        'elevation_ft': 9500,
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

# Generic terms shared across most race names. Matching on these alone produces
# false positives (e.g. "Gravel Blinduro Czech" → "Unbound Gravel 200").
_MATCH_STOP_WORDS = frozenset({
    'gravel', 'race', 'ride', 'rally', 'classic', 'championship',
    'championships', 'the', 'of', 'and', 'cycling', 'event', 'open',
    'tour', 'de', 'la', 'le', 'el',
    '50', '75', '100', '150', '200', '300', '350',
})


def _discriminative_tokens(text: str) -> set:
    return set(text.lower().split()) - _MATCH_STOP_WORDS


def lookup_by_slug(slug: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Resolve a race by its canonical SLUG — exact, no fuzzy guessing.

    This is the preferred path: the customer picked a specific race on the
    site, so the questionnaire carries its slug (e.g. 'bwr-north-carolina').
    Looking it up by ID removes the entire class of name-matching bugs
    (substring over-match, wrong edition, date mismatch). The slug is the
    race-data filename / race-index key. Returns (race_id, info) or None.
    """
    if not slug:
        return None
    s = slug.strip().lower().strip('/')
    # 1. Curated KNOWN_RACES are keyed by slug directly.
    if s in KNOWN_RACES:
        return s, KNOWN_RACES[s]
    # 2. Snapshot keys are 'discipline:slug' — match the slug part. Prefer a
    #    discipline-specific key but accept the bare slug too.
    snap = _snapshot_races()
    if s in snap:
        return s, snap[s]
    for key, info in snap.items():
        if key.split(':', 1)[-1] == s:
            return key, info
    return None


def match_race(name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Match a user-provided race name to a known race.

    Order of precedence:
      1. Exact alias (RACE_ALIASES)
      2. Substring containment, gated on discriminative content
         (rejects matches that share only stop words)
      3. Token overlap ≥ 2 on discriminative tokens

    Returns (race_id, race_info) or None.
    """
    normalized = name.strip().lower()

    # 1. Direct alias match
    if normalized in RACE_ALIASES:
        race_id = RACE_ALIASES[normalized]
        return race_id, KNOWN_RACES[race_id]

    # 2. EXACT full-name match (KNOWN_RACES, then the snapshot) — must beat
    #    substring containment below. "Belgian Waffle Ride North Carolina" is
    #    an exact snapshot entry (Oct, NC); the shorter curated "Belgian Waffle
    #    Ride" (May, San Diego) is a SUBSTRING of it, so substring-first
    #    matching grabbed the wrong race + wrong date and the integrity gate
    #    killed every build of that race. Exact also rescues single-token names
    #    ("Prosecco Cycling") that the <2-token guard below would reject.
    name_disc = _discriminative_tokens(normalized)
    for race_id, info in KNOWN_RACES.items():
        if info['name'].lower() == normalized:
            return race_id, info
    snap = _snapshot_races()
    for race_id, info in snap.items():
        if info["name"].lower() == normalized:
            return race_id, info

    # 3. Substring containment with discriminative content
    for race_id, info in KNOWN_RACES.items():
        race_name_lower = info['name'].lower()
        if normalized in race_name_lower or race_name_lower in normalized:
            race_disc = _discriminative_tokens(race_name_lower)
            # Substring match counts only if the shared content includes a
            # discriminative token (not just stop words).
            if name_disc & race_disc:
                return race_id, info

    # 3b. Substring containment against alias keys ("unbound 200 2026" → "unbound 200")
    for alias, race_id in RACE_ALIASES.items():
        if alias in normalized:
            alias_disc = _discriminative_tokens(alias)
            if alias_disc and (alias_disc & name_disc) == alias_disc:
                return race_id, KNOWN_RACES[race_id]

    # 4. Token overlap ≥ 2 on discriminative tokens (needs >=2 to be safe
    #    against coincidental single-stop-word collisions).
    if len(name_disc) < 2:
        return None

    best_match = None
    best_score = 1
    for race_id, info in KNOWN_RACES.items():
        race_disc = _discriminative_tokens(info['name'].lower())
        overlap = len(name_disc & race_disc)
        if overlap > best_score:
            best_score = overlap
            best_match = (race_id, info)

    if best_match:
        return best_match

    # 5. Fall back to strongest discriminative-token overlap in the snapshot.
    best_score = 1
    for race_id, info in snap.items():
        overlap = len(name_disc & _discriminative_tokens(info["name"].lower()))
        if overlap > best_score:
            best_score = overlap
            best_match = (race_id, info)
    return best_match
