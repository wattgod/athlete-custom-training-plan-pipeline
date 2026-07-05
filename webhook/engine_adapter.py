"""
Engine Adapter — request-scoped bridge between POST /engine/block and the
deterministic block-builder core (Convergence Phase 1).

Contract (FROZEN — Endure Labs Zod-validates against it, see
endurelabs specs/deterministic-block-core/design.md):

    request JSON  → validate_request() → params dict
    params dict   → generate_block()   → contract response dict
                                         (raises ComplianceFailure → 422)

Design constraints honored here:
- REQUEST-SCOPED: no filesystem reads/writes per request. The core's config
  YAMLs (workout library / selection matrix / strength periodization) are
  static package data loaded once per process and cached.
- Week typing reuses the derive_week_descriptors() descriptor SHAPE from
  block_chain ({'plan_week', 'phase', 'week_type'}) so Phase 2+ can swap in
  full-season calculate_plan_dates typing without touching the mapper.
- Strength (compliance R11): at plan level block_compliance auto-passes R11
  (strength is validated at render/output time in the legacy pipeline, which
  this endpoint does not run). Endure blocks carry strength via the per-week
  `strengthProtocol` field instead — satisfied by construction, never a
  hard-fail. R08 (fuel tags) likewise auto-passes at plan level; fuelTag is
  emitted on every workout here.
- ADDITIVE July 2026: each week also carries a structured `strength` object
  (sessions with day/name/focus/durationMinutes/exercises + avoidSameDayAs)
  derived from the same strength_periodization.yaml entry that composes the
  `strengthProtocol` string. Purely additive — no existing field or request
  validation changed. Shape documented at _structured_strength below.
- `rationale` is ALWAYS "" — the caller's LLM writes prose later.
"""

import os
import re
import sys
import time
import functools
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Core module imports — the block-builder core lives in athletes/scripts.
# Repo-relative path works both locally and in the Railway image
# (/app/webhook/../athletes/scripts == $SCRIPTS_DIR). The env var is only a
# fallback because webhook tests point SCRIPTS_DIR at a mock directory.
# ---------------------------------------------------------------------------
_REPO_SCRIPTS = Path(__file__).resolve().parent.parent / 'athletes' / 'scripts'
if (_REPO_SCRIPTS / 'block_chain.py').exists():
    _SCRIPTS_DIR = str(_REPO_SCRIPTS)
else:  # pragma: no cover — container path fallback
    _SCRIPTS_DIR = os.environ.get('SCRIPTS_DIR', str(_REPO_SCRIPTS))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from archetype import (  # noqa: E402
    determine_archetype,
    get_training_age_constraints,
    MASTERS_AGE,
    MASTERS_MAX_INTENSITY,
)
from block_chain import build_plan_from_calendar  # noqa: E402
from block_compliance import (  # noqa: E402
    validate_plan,
    INTENSITY_TYPES,
)
from race_category_scorer import calculate_category_scores  # noqa: E402
from workout_selector import load_methodology_profile  # noqa: E402

import yaml  # noqa: E402

ENGINE_VERSION = (
    os.environ.get('RAILWAY_GIT_COMMIT_SHA')
    or os.environ.get('GIT_SHA')
    or 'dev'
)[:12]

# ---------------------------------------------------------------------------
# Contract enums (frozen — Endure Zod-validates against these exact values)
# ---------------------------------------------------------------------------
REQUEST_PHASES = {
    'base', 'build', 'stabilize', 'peak',
    'taper', 'race', 'recovery', 'transition',
}
METHODOLOGIES = {
    'polarized_80_20', 'time_crunched', 'g_spot', 'traditional_pyramidal',
}
DISCIPLINES = {'gravel', 'road', 'mtb'}
BLOCK_WEEKS = {2, 3, 4}

DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
_DAY_ABBREV = {'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 'thu': 'Thu',
               'fri': 'Fri', 'sat': 'Sat', 'sun': 'Sun'}
_ABBREV_DAY = {v: k for k, v in _DAY_ABBREV.items()}

# Engine week_type → contract week type enum (load|recovery|medium|race|testing).
# The contract has no 'taper' value: taper weeks ship as 'medium' (that is how
# Endure's UI describes reduced-but-not-recovery weeks).
_WEEK_TYPE_OUT = {
    'load': 'load',
    'recovery': 'recovery',
    'taper': 'medium',
    'race': 'race',
    'testing': 'testing',
}

# Request phase → plan_dates calendar phase consumed by
# block_chain.CALENDAR_PHASE_MAP ('stabilize' rides the maintenance mapping;
# 'recovery'/'transition' are easy weeks typed recovery on a base calendar).
_PHASE_TO_CALENDAR = {
    'base': 'base',
    'build': 'build',
    'stabilize': 'maintenance',
    'peak': 'peak',
    'taper': 'taper',
    'race': 'race',
    'recovery': 'base',
    'transition': 'base',
}

FUEL_TAG_VALUES = {'high', 'moderate', 'practice', 'none'}

# ---------------------------------------------------------------------------
# Input domain bounds (empirical, from a 7,680-combination compliance sweep
# across all phases × weeks × hours × experience × age × progression seeds):
# - Below 4h/week the library's minimum buildable week (openers + long ride +
#   rest days at L1) exceeds the R19 hours ceiling → hard 400.
# - 4-4.5h sits on marginal rule boundaries (R03 86% vs 85%) → generation
#   uses an effective floor of 4.5h (≤35min/week overshoot, inside the
#   time-crunched 15% tolerance the core already applies).
# - Above the per-training-age ceiling the level cap makes weeks unfillable
#   (R19 floor) → effective hours are clamped; a 20h request from a 0-year
#   athlete gets the biggest week a max_level-2 library can honestly fill.
# ---------------------------------------------------------------------------
MIN_HOURS = 4
EFFECTIVE_MIN_HOURS = 4.5
MAX_HOURS_BY_LEVEL = {1: 14, 2: 14, 3: 14, 4: 16, 5: 17, 6: 19}

# Names that are rest-ish → fuelTag 'none' (mirrors the keyword veto in
# generate_athlete_package._get_fuel_tag_for_type).
_NO_FUEL_KEYWORDS = ('recovery', 'easy', 'shakeout', 'rest', 'openers', 'off')


# ---------------------------------------------------------------------------
# Race demand vector (Phase 2) — event-specific selection bias
#
# /engine/block receives race METADATA (name/date/distance_mi/discipline and,
# new, elevation_ft) rather than a known-race slug, so the 8-dim demand
# vector is derived from conservative heuristics instead of the full
# gravel-race-automation race_demand_analyzer (whose distance/threshold bands
# are mirrored here — consumer-copy parity notes in race_pack_generator.py).
# Dimensions with no wire signal sit at the NEUTRAL midpoint 5, so unknown
# data never pushes selection anywhere.
#
# HEURISTIC TABLE (all values clamped to 0-10 integers):
#
#   dimension        | source                     | rule
#   -----------------|----------------------------|--------------------------
#   durability       | distance_mi                | >=200 -> 10, >=150 -> 8,
#                    |  (race_demand_analyzer     | >=100 -> 6, >=75 -> 4,
#                    |   parity bands)            | >=50 -> 2, >0 -> 1;
#                    |                            | unknown -> 5
#   climbing         | elevation_ft / distance_mi | ft/mi >=175 -> 9,
#                    |                            | >=125 -> 8, >=90 -> 6,
#                    |                            | >=60 -> 5, >=35 -> 3,
#                    |                            | else 2; elevation without
#                    |                            | distance -> round(ft/2500)
#                    |                            | clamped 1-8; unknown -> 5
#   vo2_power        | (no wire signal)           | 5
#   threshold        | distance_mi (+climbing)    | 75-150 -> 7, 50-<75 -> 5,
#                    |  (analyzer parity bands)   | >150 -> 4, <50 -> 3;
#                    |                            | +1 if climbing >= 6;
#                    |                            | unknown -> 5
#   technical        | discipline                 | mtb -> 8, gravel -> 5,
#                    |                            | road -> 2
#   heat_resilience  | (no wire signal)           | 5
#   altitude         | (no wire signal)           | 5
#   race_specificity | (no wire signal)           | 5
#
# The vector maps to workout-category weights via the existing
# race_category_scorer weight matrix; those weights bias which names fill
# the intensity/long-ride slots (workout_selector._pick_option). The bias
# only re-orders EXISTING slot pools — it never widens a pool, never touches
# week structure, and the R01-R11 compliance gate still runs unchanged.
# ---------------------------------------------------------------------------

_DEMAND_NEUTRAL = 5


def _clamp10(v: float) -> int:
    return max(0, min(10, int(round(v))))


def derive_race_demands(distance_mi: Optional[float],
                        elevation_ft: Optional[float],
                        discipline: str) -> Dict[str, int]:
    """Conservative 8-dim demand vector from race metadata (table above)."""
    demands: Dict[str, int] = {
        'vo2_power': _DEMAND_NEUTRAL,
        'heat_resilience': _DEMAND_NEUTRAL,
        'altitude': _DEMAND_NEUTRAL,
        'race_specificity': _DEMAND_NEUTRAL,
    }

    # durability — race_demand_analyzer distance bands
    if distance_mi is None:
        demands['durability'] = _DEMAND_NEUTRAL
    elif distance_mi >= 200:
        demands['durability'] = 10
    elif distance_mi >= 150:
        demands['durability'] = 8
    elif distance_mi >= 100:
        demands['durability'] = 6
    elif distance_mi >= 75:
        demands['durability'] = 4
    elif distance_mi >= 50:
        demands['durability'] = 2
    else:
        demands['durability'] = 1

    # climbing — elevation/distance ratio (ft per mile)
    if elevation_ft is None:
        demands['climbing'] = _DEMAND_NEUTRAL
    elif distance_mi:
        ratio = elevation_ft / distance_mi
        if ratio >= 175:
            demands['climbing'] = 9
        elif ratio >= 125:
            demands['climbing'] = 8
        elif ratio >= 90:
            demands['climbing'] = 6
        elif ratio >= 60:
            demands['climbing'] = 5
        elif ratio >= 35:
            demands['climbing'] = 3
        else:
            demands['climbing'] = 2
    else:
        demands['climbing'] = max(1, min(8, _clamp10(elevation_ft / 2500)))

    # threshold — analyzer distance bands + climbing boost
    if distance_mi is None:
        demands['threshold'] = _DEMAND_NEUTRAL
    else:
        if 75 <= distance_mi <= 150:
            thr = 7
        elif 50 <= distance_mi < 75:
            thr = 5
        elif distance_mi > 150:
            thr = 4
        else:
            thr = 3
        if demands['climbing'] >= 6:
            thr += 1
        demands['threshold'] = _clamp10(thr)

    # technical — discipline heuristic
    demands['technical'] = {'mtb': 8, 'gravel': 5, 'road': 2}.get(
        discipline, _DEMAND_NEUTRAL)

    return demands


def _race_category_weights(race: Optional[Dict[str, Any]],
                           discipline: str) -> Optional[Dict[str, int]]:
    """race request object → workout-category weights (None when no race).

    LENIENT on field types: the race object always accepted arbitrary shapes
    (the contract is frozen; distance_mi was read-but-unused before Phase 2),
    so a non-numeric distance/elevation is treated as UNKNOWN — never a 400.
    """
    if not isinstance(race, dict):
        return None

    dist = race.get('distance_mi')
    dist = float(dist) if (_is_num(dist) and dist > 0) else None
    elev = race.get('elevation_ft')
    elev = float(elev) if (_is_num(elev) and elev >= 0) else None

    demands = derive_race_demands(dist, elev, discipline)
    return calculate_category_scores(demands) or None


class ComplianceFailure(Exception):
    """Generation succeeded structurally but the compliance gate has CRITICAL
    failures. Carries the contract-shaped compliance payload for the 422 body."""

    def __init__(self, compliance: Dict[str, Any]):
        super().__init__('compliance_failed')
        self.compliance = compliance


# ---------------------------------------------------------------------------
# Strength protocol (parallel track — never counted in cycling hours)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _strength_phases() -> dict:
    path = Path(_SCRIPTS_DIR).parent / 'config' / 'strength_periodization.yaml'
    with open(path) as f:
        return yaml.safe_load(f).get('phases', {})


# Request phase → strength periodization phase key. Recovery weeks always
# deload regardless of block phase (recovery_week_is_always_deload).
_STRENGTH_PHASE_KEY = {
    'base': 'anatomical_adaptation',
    'build': 'maintenance',
    'stabilize': 'maintenance',
    'peak': 'race_prep',
    'taper': 'racing',
    'race': 'racing',
    'recovery': 'deload',
    'transition': 'deload',
}


def _strength_phase_key(request_phase: str, week_type: str) -> str:
    """Strength periodization phase key for a week (shared by the legacy
    prose `strengthProtocol` and the structured `strength` object — both
    MUST derive from the same key so they can never disagree)."""
    return 'deload' if week_type in ('recovery',) else _STRENGTH_PHASE_KEY.get(
        request_phase, 'maintenance')


def _strength_protocol(request_phase: str, week_type: str) -> str:
    key = _strength_phase_key(request_phase, week_type)
    cfg = _strength_phases().get(key, {})
    label = key.replace('_', ' ').title()
    sets_reps = cfg.get('sets_reps', '')
    load = cfg.get('load', '')
    freq = cfg.get('frequency', '')
    if not sets_reps:
        return label
    if load and load != 'none':
        return f"{label} — {sets_reps} @ {load}, {freq}"
    return f"{label} — {sets_reps}, {freq}"


# ---------------------------------------------------------------------------
# Structured strength (ADDITIVE contract field, July 2026)
#
# Each week additionally carries a machine-readable `strength` object derived
# from the SAME strength_periodization.yaml phase entry that composes the
# `strengthProtocol` prose string (which is unchanged for backward compat):
#
#     "strength": {
#       "sessions": [
#         {"day": "tue" | null,          # contract day key; null = consumer places it
#          "name": "Maintenance A",       # phase label + session letter
#          "focus": "maintenance",        # strength periodization phase key
#          "durationMinutes": 40,         # deterministic estimate
#          "exercises": [
#            {"name": "Back Squat",
#             "sets": 3,                  # null for bodyweight (deload) work
#             "reps": 5,                  # null for bodyweight (deload) work
#             "intensityPct": 75}         # %1RM; null when load is "none"
#          ]}
#       ],
#       "avoidSameDayAs": ["threshold", "vo2max"]
#     }
#
# Deterministic parsing rules (ranges in the YAML are prescriptions like
# "2-3 × 15-20" @ "50-60% 1RM", "2-3x/week"): take the LOWER bound of every
# range — strength is a parallel track and the engine errs conservative.
# Day placement: sessions land only on 'filler' days (easy rides / Rest Day)
# — never on athlete off-days (unavailable), intensity days (YAML rule
# never_pair_with_key_interval), or the long ride. Sessions are spaced >=2
# days apart when possible (>=1 otherwise); if the layout can't absorb a
# session, its day is null and the consumer places it.
# ---------------------------------------------------------------------------

_STRENGTH_AVOID_SAME_DAY_AS = ['threshold', 'vo2max']
_SESSION_LETTERS = ['A', 'B', 'C']


def _range_low(text: str) -> Optional[int]:
    """Leading integer of '3' / '2-3' / '15-20'; None if non-numeric."""
    m = re.match(r'\s*(\d+)', text or '')
    return int(m.group(1)) if m else None


def _parse_sets_reps(sets_reps: str) -> Tuple[Optional[int], Optional[int]]:
    """'3 × 5' → (3, 5); '2-3 × 15-20' → (2, 15); 'bodyweight only' → (None, None)."""
    parts = (sets_reps or '').replace('x', '×').split('×')
    if len(parts) != 2:
        return None, None
    return _range_low(parts[0]), _range_low(parts[1])


def _parse_intensity_pct(load: str) -> Optional[int]:
    """'75% 1RM' → 75; '50-60% 1RM' → 50; 'none'/'' → None."""
    if not load or load == 'none':
        return None
    return _range_low(load)


def _parse_frequency(freq: str) -> int:
    """'2-3x/week' → 2; '1x/week' → 1; unparseable → 1."""
    return _range_low(freq) or 1


def _strength_session_days(week_days: List[dict], n: int) -> List[Optional[str]]:
    """Pick n contract day keys for strength sessions from a built week.

    Candidates are 'filler'-role days only: off days are athlete-unavailable,
    intensity days are vetoed (never_pair_with_key_interval), and the long
    ride is the week's key endurance session. Greedy earliest-first with a
    >=2-day gap, relaxed to >=1 if the week is too tight; unplaceable
    sessions get day=None (consumer schedules them).
    """
    candidate_idx = sorted(
        DAY_KEYS.index(_ABBREV_DAY[d['day']])
        for d in week_days if d.get('role') == 'filler'
    )
    picked: List[int] = []
    for gap in (2, 1):
        picked = []
        last = -10
        for idx in candidate_idx:
            if idx - last >= gap:
                picked.append(idx)
                last = idx
                if len(picked) == n:
                    break
        if len(picked) == n:
            break
    return [DAY_KEYS[i] for i in picked] + [None] * (n - len(picked))


def _structured_strength(request_phase: str, week_type: str,
                         week_days: List[dict]) -> Dict[str, Any]:
    """Machine-readable strength prescription for one week (see block comment
    above for the shape). Derived from the same strength_periodization.yaml
    entry as the `strengthProtocol` string."""
    key = _strength_phase_key(request_phase, week_type)
    cfg = _strength_phases().get(key, {})
    label = key.replace('_', ' ').title()

    sets, reps = _parse_sets_reps(cfg.get('sets_reps', ''))
    pct = _parse_intensity_pct(cfg.get('load', ''))
    n_sessions = _parse_frequency(cfg.get('frequency', ''))

    ex_cfg = cfg.get('exercises') or {}
    primary = list(ex_cfg.get('primary') or [])
    secondary = list(ex_cfg.get('secondary') or [])
    supplementary = list(ex_cfg.get('supplementary') or [])

    days = _strength_session_days(week_days, n_sessions)

    sessions = []
    for i in range(n_sessions):
        # Session A: primary lifts + supplementary (core); B: primary +
        # secondary (accessories); C+: primary only. Deterministic.
        if i == 0:
            names = primary + supplementary
        elif i == 1:
            names = primary + secondary
        else:
            names = list(primary)
        if not names:  # config gap — still emit an honest empty session
            names = list(primary)
        if sets is None:
            duration = 20  # bodyweight circuit (deload)
        else:
            # 10min warmup + ~2.5min per working set, rounded up to 5.
            raw = 10 + len(names) * sets * 2.5
            duration = int(-(-raw // 5) * 5)
        sessions.append({
            'day': days[i],
            'name': f"{label} {_SESSION_LETTERS[min(i, len(_SESSION_LETTERS) - 1)]}",
            'focus': key,
            'durationMinutes': duration,
            'exercises': [
                {'name': nm, 'sets': sets, 'reps': reps, 'intensityPct': pct}
                for nm in names
            ],
        })
    return {
        'sessions': sessions,
        'avoidSameDayAs': list(_STRENGTH_AVOID_SAME_DAY_AS),
    }


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_request(payload: Any) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Validate the /engine/block request body.

    Returns (params, field_errors). If field_errors is non-empty the caller
    must return 400 with them; params is only meaningful when errors is empty.
    """
    errors: Dict[str, str] = {}
    params: Dict[str, Any] = {}

    if not isinstance(payload, dict):
        return {}, {'body': 'Request body must be a JSON object'}

    # ---- athlete ----------------------------------------------------------
    athlete = payload.get('athlete')
    if not isinstance(athlete, dict):
        errors['athlete'] = 'Required object'
        athlete = {}

    hours = athlete.get('hours_per_week')
    if not _is_num(hours) or not (MIN_HOURS <= hours <= 40):
        errors['athlete.hours_per_week'] = (
            f'Required number between {MIN_HOURS} and 40 '
            f'(the workout library cannot build a compliant week under '
            f'{MIN_HOURS}h)')
        hours = 8

    ftp = athlete.get('ftp')
    if ftp is not None and (not _is_num(ftp) or ftp <= 0):
        errors['athlete.ftp'] = 'Must be a positive number when provided'

    exp = athlete.get('experience_years', 3)
    if not _is_num(exp) or exp < 0:
        errors['athlete.experience_years'] = 'Must be a non-negative number'
        exp = 3

    age = athlete.get('age', 35)
    if not _is_num(age) or not (10 <= age <= 100):
        errors['athlete.age'] = 'Must be a number between 10 and 100'
        age = 35

    race = payload.get('race')
    if race is not None and not isinstance(race, dict):
        errors['race'] = 'Must be an object when provided'
        race = None

    discipline = athlete.get('discipline')
    if discipline is None and isinstance(race, dict):
        discipline = race.get('discipline')
    if discipline is None:
        discipline = 'gravel'
    if discipline not in DISCIPLINES:
        errors['athlete.discipline'] = (
            f"Must be one of {sorted(DISCIPLINES)}")
        discipline = 'gravel'

    # ---- availability (optional; default: Mon off, no caps, Sat long ride)
    availability = athlete.get('availability')
    off_days: List[str] = ['Mon']
    day_caps: Dict[str, int] = {}
    long_ride_day = 'Sat'
    if availability is not None:
        if not isinstance(availability, dict):
            errors['athlete.availability'] = 'Must be an object keyed by day'
        else:
            off_days = []
            for key, spec in availability.items():
                if key not in _DAY_ABBREV:
                    errors[f'athlete.availability.{key}'] = (
                        f"Unknown day key (expected one of {DAY_KEYS})")
                    continue
                if not isinstance(spec, dict):
                    errors[f'athlete.availability.{key}'] = 'Must be an object'
                    continue
                abbrev = _DAY_ABBREV[key]
                available = spec.get('available', True)
                if not isinstance(available, bool):
                    errors[f'athlete.availability.{key}.available'] = 'Must be a boolean'
                    available = True
                cap = spec.get('max_duration_min')
                if cap is not None and (not _is_num(cap) or cap < 0):
                    errors[f'athlete.availability.{key}.max_duration_min'] = (
                        'Must be a non-negative number')
                    cap = None
                if not available:
                    off_days.append(abbrev)
                elif cap:
                    day_caps[abbrev] = int(cap)
            # Days not mentioned default to available/uncapped.
            available_days = [_DAY_ABBREV[d] for d in DAY_KEYS
                              if _DAY_ABBREV[d] not in off_days]
            if len(available_days) < 3 and 'athlete.availability' not in errors:
                errors['athlete.availability'] = (
                    'At least 3 available days are required to build a week')
            if available_days:
                # Long ride: weekend-first (coach default), then the day
                # with the most room; uncapped counts as unlimited.
                pref = ['Sat', 'Sun', 'Fri', 'Mon', 'Tue', 'Wed', 'Thu']
                long_ride_day = max(
                    available_days,
                    key=lambda d: (d in ('Sat', 'Sun'),
                                   day_caps.get(d) or 10 ** 6,
                                   -pref.index(d)),
                )

    # ---- block ------------------------------------------------------------
    block = payload.get('block')
    if not isinstance(block, dict):
        errors['block'] = 'Required object'
        block = {}

    phase = block.get('phase')
    if phase not in REQUEST_PHASES:
        errors['block.phase'] = f"Must be one of {sorted(REQUEST_PHASES)}"
        phase = 'base'

    weeks = block.get('weeks')
    if not isinstance(weeks, int) or isinstance(weeks, bool) or weeks not in BLOCK_WEEKS:
        errors['block.weeks'] = 'Must be 2, 3, or 4'
        weeks = 3

    start_date = block.get('start_date')
    if not isinstance(start_date, str):
        errors['block.start_date'] = 'Required string YYYY-MM-DD'
    else:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            errors['block.start_date'] = 'Must be a valid YYYY-MM-DD date'

    # ---- methodology (optional) --------------------------------------------
    # None/absent both mean "use the default" — clients that JSON-serialize
    # optional fields send explicit null (observed: Endure adapter 2026-07-02).
    #
    # Phase 2 decision B: an EXPLICIT methodology engages its selection
    # profile (methodology_profiles.yaml) so the four methods deliver
    # measurably different zone/intensity mixes. Absent/null stays on the
    # historical default selection — byte-identical to pre-profile behavior
    # (pinned by tests), so existing Endure requests never shift under a
    # deploy.
    methodology_raw = payload.get('methodology')
    methodology = methodology_raw or 'polarized_80_20'
    # isinstance guard: a non-string (e.g. object) is unhashable for the set
    # membership test — report a field error instead of a 500.
    if not isinstance(methodology, str) or methodology not in METHODOLOGIES:
        errors['methodology'] = f"Must be one of {sorted(METHODOLOGIES)}"
        methodology = 'polarized_80_20'
    methodology_profile = (
        load_methodology_profile(methodology)
        if isinstance(methodology_raw, str) and methodology_raw in METHODOLOGIES
        else None)

    # ---- previous (optional progression seed) ------------------------------
    previous = payload.get('previous')
    prev_levels: List[int] = []
    prev_series: List[str] = []
    if previous is not None:
        if not isinstance(previous, dict):
            errors['previous'] = 'Must be an object when provided'
        else:
            series_used = previous.get('seriesUsed')
            if series_used is not None and (
                    not isinstance(series_used, list)
                    or not all(isinstance(s, str) for s in series_used)):
                errors['previous.seriesUsed'] = 'Must be a list of strings'
            elif series_used:
                prev_series = [s for s in series_used if s]
            levels = previous.get('levels')
            if levels is not None:
                if not isinstance(levels, dict) or not all(
                        _is_num(v) for v in levels.values()):
                    errors['previous.levels'] = (
                        'Must be an object of numeric levels')
                else:
                    prev_levels = [max(1, min(6, int(v)))
                                   for v in levels.values()]

    # ---- derived engine parameters -----------------------------------------
    constraints = get_training_age_constraints(int(exp))
    max_level = constraints['max_level']
    max_intensity = constraints['max_intensity_per_week']
    if age >= MASTERS_AGE:
        max_intensity = min(max_intensity, MASTERS_MAX_INTENSITY)

    # Effective hours: clamp into the buildable domain for this training age
    # (see MAX_HOURS_BY_LEVEL comment). Archetype MUST derive from the
    # clamped value — deriving it from raw hours selects goat/volume workout
    # menus that the clamped budget then cannot fill.
    effective_hours = min(max(float(hours), EFFECTIVE_MIN_HOURS),
                          MAX_HOURS_BY_LEVEL.get(max_level, 14))

    # Availability budget: when EVERY available day is capped, the weekly
    # ceiling is the sum of the caps. Stated hours above that are
    # unachievable (R19 floor can never be met) — clamp to the budget, and
    # reject an availability whose budget is below the minimum buildable week.
    if availability is not None and day_caps:
        available_abbrevs = [_DAY_ABBREV[d] for d in DAY_KEYS
                             if _DAY_ABBREV[d] not in off_days]
        if all(d in day_caps for d in available_abbrevs):
            budget_hours = sum(day_caps.values()) / 60.0
            if budget_hours < EFFECTIVE_MIN_HOURS:
                errors['athlete.availability'] = (
                    f'Availability caps total {budget_hours:.1f}h/week — '
                    f'below the {EFFECTIVE_MIN_HOURS}h minimum buildable week')
            effective_hours = min(effective_hours, max(budget_hours,
                                                       EFFECTIVE_MIN_HOURS))

    # Progression seed: a chained plan raises the block base level (and the
    # variety-rotation index) by one per completed block, so the previous
    # block's max level is the natural continuation point.
    if prev_levels:
        starting_level = min(max(prev_levels) + 1, max_level)
    else:
        starting_level = 1
    # Standalone blocks assume an ACTIVE athlete: rotation seed >= 2 keeps the
    # builder's grow-to-floor volume logic on (the full-season "block 1
    # ramp-in" exemption produces load weeks too small for a single block's
    # recovery ratio to pass R03 at high volume).
    phase_block_start = max(2, starting_level)

    # Race demand vector → workout-category weights (None when no race →
    # selection byte-identical to today). Never raises for odd race fields.
    category_weights = _race_category_weights(race, discipline)

    params.update({
        'phase': phase,
        'weeks': weeks,
        'start_date': start_date if isinstance(start_date, str) else '',
        'hours_per_week': effective_hours,
        'discipline': discipline,
        'methodology': methodology,
        'archetype': determine_archetype(effective_hours),
        'max_level': max_level,
        'max_intensity': max_intensity,
        'off_days': off_days,
        'day_caps': day_caps or None,
        'long_ride_day': long_ride_day,
        'starting_level': starting_level,
        'phase_block_start': phase_block_start,
        # Phase 2 selection bias (all None/empty → historical behavior):
        'category_weights': category_weights,
        'avoid_series': set(prev_series) or None,
        # Non-None ONLY for an explicit request methodology — decision B
        # differentiation is selection-level and opt-in per request.
        'methodology_profile': methodology_profile,
    })
    return params, errors


# ---------------------------------------------------------------------------
# Week descriptors — block-scoped Phase 1 typing, derive_week_descriptors SHAPE
# ---------------------------------------------------------------------------

def build_week_descriptors(phase: str, weeks: int) -> List[Dict[str, Any]]:
    """Standalone-block week typing.

    Load-bearing phases: 2 weeks = load/load, 3 = load/load/recovery,
    4 = load/load/load/recovery (matches how Endure's UI describes weeks).
    taper → all taper weeks; race → taper weeks ending in a race week;
    recovery/transition → all recovery weeks.
    """
    cal_phase = _PHASE_TO_CALENDAR[phase]
    if phase in ('base', 'build', 'stabilize', 'peak'):
        types = ['load'] * weeks if weeks == 2 else ['load'] * (weeks - 1) + ['recovery']
        phases = [cal_phase] * weeks
    elif phase == 'taper':
        types = ['taper'] * weeks
        phases = ['taper'] * weeks
    elif phase == 'race':
        types = ['taper'] * (weeks - 1) + ['race']
        phases = ['taper'] * (weeks - 1) + ['race']
    else:  # recovery, transition
        types = ['recovery'] * weeks
        phases = [cal_phase] * weeks

    return [
        {'plan_week': i + 1, 'phase': p, 'week_type': t}
        for i, (p, t) in enumerate(zip(phases, types))
    ]


# ---------------------------------------------------------------------------
# Contract mapping
# ---------------------------------------------------------------------------

def _fuel_tag(name: str, role: str) -> str:
    """Map a workout to the contract fuelTag enum (high|moderate|practice|none).

    Mirrors generate_athlete_package._get_fuel_tag_for_type: race sims get
    practice fuel, intensity gets high, rest-ish gets none, everything else
    (endurance/long rides) gets moderate.
    """
    lower = name.lower()
    if role == 'off':
        return 'none'
    if 'race sim' in lower or 'race simulation' in lower:
        return 'practice'
    if any(k in lower for k in _NO_FUEL_KEYWORDS):
        return 'none'
    if name in INTENSITY_TYPES or role == 'intensity':
        return 'high'
    return 'moderate'


def _map_week(week: dict, number: int, total_weeks: int,
              request_phase: str) -> Dict[str, Any]:
    week_type = week.get('week_type', 'load')
    out_type = _WEEK_TYPE_OUT.get(week_type, 'load')

    workouts = []
    for day in week.get('days', []):
        role = day.get('role', 'filler')
        if role == 'off':
            continue  # Off days carry no workout — availability is respected.
        name = day.get('name', 'Endurance')
        level = day.get('level', 1)
        entry = {
            'day': _ABBREV_DAY[day['day']],
            'coachName': name,
            'durationMinutes': int(day.get('duration', 0)),
            'estimatedTss': int(day.get('tss', 0)),
            'fuelTag': _fuel_tag(name, role),
            'isIntensity': role == 'intensity',
        }
        notes_bits = []
        if level and name not in ('Rest Day', 'OFF'):
            notes_bits.append(f"Level {level}")
        if role == 'long_ride':
            notes_bits.append('long ride')
        if notes_bits:
            entry['notes'] = ' — '.join(notes_bits)
        workouts.append(entry)

    return {
        'number': number,
        'type': out_type,
        'workouts': workouts,
        'strengthProtocol': _strength_protocol(request_phase, week_type),
        # ADDITIVE (July 2026): structured twin of strengthProtocol — same
        # YAML source, machine-readable. See _structured_strength.
        'strength': _structured_strength(
            request_phase, week_type, week.get('days', [])),
        'blockNote': (
            f"{request_phase.capitalize()} block, week {number} of "
            f"{total_weeks} — {out_type} week."
        ),
        'targetTss': int(week.get('total_tss', 0)),
        'targetHours': round(week.get('total_duration', 0) / 60, 1),
    }


def _build_and_gate(params: Dict[str, Any],
                    starting_level: int) -> Tuple[dict, Dict[str, Any]]:
    """One build + compliance-gate pass. Returns (plan, compliance).

    phase_block_start tracks starting_level (block index and base level
    advance together in a chained plan), floored at 2 so standalone blocks
    keep the grow-to-floor volume logic (see validate_request).
    """
    descriptors = build_week_descriptors(params['phase'], params['weeks'])

    plan = build_plan_from_calendar(
        descriptors,
        archetype=params['archetype'],
        max_level=params['max_level'],
        max_intensity=params['max_intensity'],
        off_days=params['off_days'],
        long_ride_day=params['long_ride_day'],
        starting_level=starting_level,
        hours_per_week=params['hours_per_week'],
        discipline=params['discipline'],
        day_caps=params['day_caps'],
        methodology=params['methodology'],
        phase_block_start=max(2, starting_level),
        category_weights=params.get('category_weights'),
        avoid_series=params.get('avoid_series'),
        methodology_profile=params.get('methodology_profile'),
    )

    compliance_raw = validate_plan(
        plan,
        target_hours=params['hours_per_week'],
        off_days=params['off_days'],
        max_intensity=params['max_intensity'],
    )
    violations = [
        f"{rule_id}: {rule['message']}"
        for rule_id, rule in sorted(compliance_raw['rules'].items())
        if rule['severity'] == 'CRITICAL' and not rule['passed']
    ]
    compliance = {
        'passed': bool(compliance_raw['critical_pass']),
        'violations': violations,
    }
    return plan, compliance


def generate_block(params: Dict[str, Any]) -> Dict[str, Any]:
    """params (from validate_request) → contract response dict.

    Raises ComplianceFailure when the compliance gate has CRITICAL failures.

    Progression step-down: if the seeded starting_level produces a
    non-compliant block (e.g. a previous block ended at L6 but the athlete's
    hours cannot absorb L6 work), deterministically step the level down and
    rebuild — exactly what a coach does when an athlete's availability drops.
    The FIRST failure is reported if no level fits (bounded: <=6 passes,
    ~0.1ms each).
    """
    t0 = time.perf_counter()

    plan = None
    compliance = None
    first_failure: Optional[Dict[str, Any]] = None
    for level in range(params['starting_level'], 0, -1):
        plan, compliance = _build_and_gate(params, level)
        if compliance['passed']:
            break
        if first_failure is None:
            first_failure = compliance
    if not compliance['passed']:
        raise ComplianceFailure(first_failure or compliance)

    weeks_out = [
        _map_week(week, i + 1, params['weeks'], params['phase'])
        for i, week in enumerate(plan.get('weeks', []))
    ]

    # seriesUsed: distinct intensity/long-ride series names, first-use order.
    series_used: List[str] = []
    for week in plan.get('weeks', []):
        for day in week.get('days', []):
            if day.get('role') in ('intensity', 'long_ride'):
                name = day.get('name', '')
                if name and name not in series_used:
                    series_used.append(name)

    generated_ms = int(round((time.perf_counter() - t0) * 1000))
    return {
        'weeks': weeks_out,
        'seriesUsed': series_used,
        'rationale': '',
        'compliance': compliance,
        'engine': {
            'version': ENGINE_VERSION,
            'generated_ms': generated_ms,
        },
    }
