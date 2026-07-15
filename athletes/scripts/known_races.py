#!/usr/bin/env python3
"""
Single source of truth for known race data, aliases, and matching logic.

All race metadata (dates, distances, elevations) lives here.
Other scripts import from this module rather than duplicating the data.
"""

import difflib
import json
import re
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# The curated KNOWN_RACES below carry hand-tuned aliases and are authoritative.
# Beyond them, match_race falls back to the full 1,184-race snapshot
# (config/races.json, built by build_race_snapshot.py) so a real customer's
# race validates against the actual database, not just this hand-list.
_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "config" / "races.json"
MAX_FACT_AGE_DAYS = 365


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
            "source_urls": e.get("source_urls") or [],
            "source_type": e.get("source_type"),
            "verified_at": e.get("verified_at"),
            "event_year": e.get("event_year"),
            "course_variant": e.get("course_variant"),
            "category": e.get("category"),
            "sex": e.get("sex"),
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

# Generic terms shared across most race names. Matching on these alone produces
# false positives (e.g. "Gravel Blinduro Czech" → "Unbound Gravel 200").
_MATCH_STOP_WORDS = frozenset({
    'gravel', 'race', 'ride', 'rally', 'classic', 'championship',
    'championships', 'the', 'of', 'and', 'cycling', 'event', 'open',
    'tour', 'de', 'la', 'le', 'el',
    '50', '75', '100', '150', '200', '300', '350',
})

# Textual stop words only — numeric tokens ('200', '100') ARE kept for the
# fuzzy similarity score: the distance number is exactly what separates
# "Unbound Gravel 200" from "Unbound Gravel 100", and dropping it collapses
# the margin between the right race and its distance variants.
_TEXT_STOP_WORDS = frozenset(w for w in _MATCH_STOP_WORDS if not w.isdigit())

# Fuzzy acceptance: measured against the full 1,000+ candidate pool, real
# typo variants ("Unbund Gravel 200", "belgian wafle ride") score >= 0.93
# while the best WRONG-race score observed for clearly-unknown names tops
# out around 0.78 ("Tour de France" → "L'Etape Dubai"). 0.85 sits above
# every observed wrong-race score with headroom on both sides.
FUZZY_MATCH_THRESHOLD = 0.85
# The winner must also beat the best DIFFERENT-named candidate by this
# margin. Distance variants of one event (200/100/50) score within ~0.10 of
# each other; genuine typos keep a >= 0.09 margin, while ambiguous inputs
# ("Unbound Gravel 150" — a distance that doesn't exist) land in a near-tie
# and are conservatively treated as UNMATCHED for the coach to verify.
FUZZY_MATCH_MARGIN = 0.05


def _discriminative_tokens(text: str) -> set:
    return set(text.lower().split()) - _MATCH_STOP_WORDS


def _normalize_race_name(name: str) -> str:
    """Lowercase, strip punctuation to spaces, collapse whitespace."""
    s = re.sub(r'[^a-z0-9]+', ' ', (name or '').lower())
    return re.sub(r'\s+', ' ', s).strip()


def _match_tokens(text: str) -> set:
    """Tokens used for fuzzy similarity: drop textual stop words but KEEP
    numbers (the distance discriminates editions). Falls back to all tokens
    for names made entirely of stop words."""
    tokens = set(_normalize_race_name(text).split())
    return (tokens - _TEXT_STOP_WORDS) or tokens


def fuzzy_score(query: str, candidate: str) -> float:
    """Similarity in [0, 1]: 0.6 × whole-string difflib ratio +
    0.4 × mean best-token difflib ratio. Stdlib only, deterministic."""
    qn, cn = _normalize_race_name(query), _normalize_race_name(candidate)
    if not qn or not cn:
        return 0.0
    char = difflib.SequenceMatcher(None, qn, cn).ratio()
    q_tok, c_tok = _match_tokens(query), _match_tokens(candidate)
    if q_tok and c_tok:
        tok = sum(
            max(difflib.SequenceMatcher(None, t, u).ratio() for u in c_tok)
            for t in q_tok
        ) / len(q_tok)
    else:
        tok = 0.0
    return 0.6 * char + 0.4 * tok


@lru_cache(maxsize=1)
def _fuzzy_candidate_pool() -> Tuple[Tuple[str, str], ...]:
    """(race_id, matchable_name) pairs: curated names, snapshot names, and
    alias keys (an alias is just another spelling of its race)."""
    pool = [(rid, info['name']) for rid, info in KNOWN_RACES.items()]
    pool += [(rid, info['name']) for rid, info in _snapshot_races().items()]
    pool += [(rid, alias) for alias, rid in RACE_ALIASES.items()]
    return tuple(pool)


def _race_info_for_id(race_id: str) -> Optional[Dict[str, Any]]:
    if race_id in KNOWN_RACES:
        return KNOWN_RACES[race_id]
    return _snapshot_races().get(race_id)


def race_provenance_issue(info: Dict[str, Any], requested_date: str = '',
                          requested_category: str = '', requested_sex: str = '',
                          *, today: date | None = None) -> Optional[str]:
    """Return a coach-blocking provenance defect, or ``None`` for usable facts.

    This is deliberately separate from fuzzy identity matching: a confidently
    matched name still cannot authorize facts from another edition/course.
    """
    sources = info.get('source_urls') or []
    if not sources or not info.get('source_type'):
        return 'Race facts have no recorded source URL and source type.'
    verified = info.get('verified_at')
    if not verified:
        return 'Race facts have no recorded verification date.'
    try:
        verified_day = datetime.fromisoformat(str(verified).replace('Z', '+00:00')).date()
    except ValueError:
        return f'Race facts have an invalid verification date: {verified!r}.'
    if ((today or date.today()) - verified_day).days > MAX_FACT_AGE_DAYS:
        return f'Race facts were verified {verified_day.isoformat()}, older than {MAX_FACT_AGE_DAYS} days.'
    requested_year = str(requested_date or '')[:4]
    fact_year = str(info.get('event_year') or str(info.get('date') or '')[:4])
    if requested_year and fact_year and requested_year != fact_year:
        return f'Requested {requested_year} but race facts are edition {fact_year}.'
    def normalized(value: str) -> str:
        return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())
    if requested_category and info.get('category') and normalized(requested_category) != normalized(info['category']):
        return f"Requested category {requested_category!r} does not match sourced course category {info['category']!r}."
    if requested_sex and info.get('sex'):
        aliases = {'female': 'women', 'f': 'women', 'male': 'men', 'm': 'men'}
        asked = aliases.get(normalized(requested_sex), normalized(requested_sex))
        facts = aliases.get(normalized(info['sex']), normalized(info['sex']))
        if asked != facts:
            return f"Requested sex {requested_sex!r} does not match sourced course sex {info['sex']!r}."
    return None


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


def match_race_scored(
    name: str,
) -> Tuple[Optional[Tuple[str, Dict[str, Any]]], Dict[str, Any]]:
    """
    Match a user-provided race name to a known race, with match metadata.

    Order of precedence:
      1. Exact alias (RACE_ALIASES), punctuation-insensitive
      2. Exact full-name match (KNOWN_RACES, then the snapshot)
      3. Substring containment, gated on discriminative content
      3b. Alias-key substring (longest alias wins: "SBT GRVL 75 mile"
          must hit 'sbt grvl 75', not the shorter 'sbt grvl')
      4. Conservative fuzzy: fuzzy_score >= FUZZY_MATCH_THRESHOLD AND a
         >= FUZZY_MATCH_MARGIN lead over the best different-named candidate.
         Near-ties (e.g. distance variants) are treated as UNMATCHED.

    NEVER falls back to a default race. An unconfident match returns
    (None, meta) — the caller must build a generic profile and flag the
    coach, not guess.

    Returns ((race_id, race_info) | None, meta) where meta is
    {'method': 'alias'|'exact'|'substring'|'fuzzy'|'none', 'score': float,
     'matched_slug': str|None, 'near_misses': [{'slug','name','score'}]}.
    """
    def _meta(method, score, slug, near=()):
        return {
            'method': method,
            'score': round(float(score), 3),
            'matched_slug': slug.split(':', 1)[-1] if slug else None,
            'near_misses': list(near),
        }

    raw_lower = (name or '').strip().lower()
    normalized = _normalize_race_name(name)
    if not normalized:
        return None, _meta('none', 0.0, None)

    # 1. Direct alias match (raw, then punctuation-normalized)
    alias_id = RACE_ALIASES.get(raw_lower)
    if alias_id is None:
        alias_id = _normalized_aliases().get(normalized)
    if alias_id is not None:
        return (alias_id, KNOWN_RACES[alias_id]), _meta('alias', 1.0, alias_id)

    # 2. EXACT full-name match (KNOWN_RACES, then the snapshot) — must beat
    #    substring containment below. "Belgian Waffle Ride North Carolina" is
    #    an exact snapshot entry (Oct, NC); the shorter curated "Belgian Waffle
    #    Ride" (May, San Diego) is a SUBSTRING of it, so substring-first
    #    matching grabbed the wrong race + wrong date and the integrity gate
    #    killed every build of that race. Exact also rescues single-token names
    #    ("Prosecco Cycling") that token guards would reject.
    name_disc = _discriminative_tokens(normalized)
    for race_id, info in KNOWN_RACES.items():
        if _normalize_race_name(info['name']) == normalized:
            return (race_id, info), _meta('exact', 1.0, race_id)
    snap = _snapshot_races()
    for race_id, info in snap.items():
        if _normalize_race_name(info["name"]) == normalized:
            return (race_id, info), _meta('exact', 1.0, race_id)

    # 3. Substring containment with discriminative content. Longest race
    #    name wins so the most specific edition is chosen ("SBT GRVL 75
    #    mile" must hit 'SBT GRVL 75', not the shorter 'SBT GRVL').
    substring_hits = []
    for race_id, info in KNOWN_RACES.items():
        race_name_norm = _normalize_race_name(info['name'])
        if normalized in race_name_norm or race_name_norm in normalized:
            race_disc = _discriminative_tokens(race_name_norm)
            # Substring match counts only if the shared content includes a
            # discriminative token (not just stop words).
            if name_disc & race_disc:
                substring_hits.append((len(race_name_norm), race_id, info))
    if substring_hits:
        _len, race_id, info = max(substring_hits, key=lambda h: h[0])
        return (race_id, info), _meta('substring', 0.95, race_id)

    # 3b. Substring containment against alias keys ("unbound 200 2026" →
    #     "unbound 200"). Longest alias first so the most specific edition
    #     wins ('sbt grvl 75' beats 'sbt grvl').
    for alias, race_id in sorted(RACE_ALIASES.items(),
                                 key=lambda kv: -len(kv[0])):
        if alias in normalized:
            alias_disc = _discriminative_tokens(alias)
            if alias_disc and (alias_disc & name_disc) == alias_disc:
                return (race_id, KNOWN_RACES[race_id]), _meta(
                    'substring', 0.95, race_id)

    # 4. Conservative fuzzy match over the full candidate pool.
    scored = sorted(
        ((fuzzy_score(name, cand_name), race_id, cand_name)
         for race_id, cand_name in _fuzzy_candidate_pool()),
        reverse=True,
    )
    # Collapse to the best score per DISTINCT normalized name — the same
    # event appears under several ids/aliases and must not count as its own
    # runner-up ("Unbound Gravel 200" vs alias "unbound 200").
    distinct: List[Tuple[float, str, str]] = []
    seen = set()
    for s, race_id, cand_name in scored:
        key = _normalize_race_name(cand_name)
        if key in seen:
            continue
        seen.add(key)
        distinct.append((s, race_id, cand_name))
        if len(distinct) >= 5:
            break

    near = []
    _near_slugs = set()
    for s, rid, cname in distinct:
        slug = rid.split(':', 1)[-1]
        if slug in _near_slugs:
            continue
        _near_slugs.add(slug)
        near.append({'slug': slug, 'name': cname, 'score': round(s, 3)})
        if len(near) >= 3:
            break
    if distinct:
        top_score, top_id, _top_name = distinct[0]
        runner_up = distinct[1][0] if len(distinct) > 1 else 0.0
        if (top_score >= FUZZY_MATCH_THRESHOLD
                and (top_score - runner_up) >= FUZZY_MATCH_MARGIN):
            info = _race_info_for_id(top_id)
            if info is not None:
                return (top_id, info), _meta('fuzzy', top_score, top_id, near)

    return None, _meta('none', distinct[0][0] if distinct else 0.0, None, near)


@lru_cache(maxsize=1)
def _normalized_aliases() -> Dict[str, str]:
    return {_normalize_race_name(k): v for k, v in RACE_ALIASES.items()}


def match_race(name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Match a user-provided race name to a known race.

    Backward-compatible wrapper around match_race_scored(): returns
    (race_id, race_info) or None. There is NO default race — an unknown
    name returns None and the caller handles it honestly.
    """
    matched, _meta = match_race_scored(name)
    return matched


# ---------------------------------------------------------------------------
# Generic (unmatched) race profile
# ---------------------------------------------------------------------------
# When a race can't be confidently matched, the plan must be built from what
# the athlete actually told us — NEVER silently mapped to a real race.

def generic_race_demands(distance_miles: float = 0,
                         discipline: Optional[str] = None) -> Dict[str, int]:
    """Neutral 8-dimension demand vector (each 0-10) for an unmatched race,
    shaped for race_category_scorer.calculate_category_scores().

    Assumptions (deliberately neutral, disclosed to the coach):
    - durability scales with distance; climbing is mid-range (unknown course);
    - technicality follows discipline (mtb > gravel > road);
    - no altitude or heat assumptions (unknown venue).
    """
    d = float(distance_miles or 0)
    if d >= 150:
        durability = 9
    elif d >= 100:
        durability = 7
    elif d >= 60:
        durability = 5
    elif d > 0:
        durability = 3
    else:
        durability = 5
    return {
        'durability': durability,
        'climbing': 5,
        'vo2_power': 6 if 0 < d < 60 else 4,
        'threshold': 6 if 0 < d < 100 else 5,
        'technical': {'mtb': 8, 'gravel': 5, 'road': 2}.get(discipline, 4),
        'heat_resilience': 3,
        'altitude': 0,
        'race_specificity': 5,
    }


def build_generic_race_profile(name: str, date: str = '',
                               distance_miles: float = 0,
                               discipline: Optional[str] = None,
                               ) -> Dict[str, Any]:
    """Race info for an UNMATCHED race, same field shape as KNOWN_RACES
    entries so it flows through every consumer unchanged.

    Uses the athlete's own inputs verbatim. elevation_ft stays 0 — we never
    fabricate athlete-facing numbers for a course we don't know (the guide
    drops empty badges; the coach brief discloses the assumption).
    """
    return {
        'name': (name or '').strip(),
        'date': date or '',
        'distance_miles': distance_miles or 0,
        'elevation_ft': 0,
        'discipline': discipline if discipline in ('gravel', 'road', 'mtb') else None,
        'location': '',
        'generic': True,
        'demands': generic_race_demands(distance_miles, discipline),
    }
