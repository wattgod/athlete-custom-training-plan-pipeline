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
- `rationale` is ALWAYS "" — the caller's LLM writes prose later.
"""

import os
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


def _strength_protocol(request_phase: str, week_type: str) -> str:
    key = 'deload' if week_type in ('recovery',) else _STRENGTH_PHASE_KEY.get(
        request_phase, 'maintenance')
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
    methodology = payload.get('methodology') or 'polarized_80_20'
    if methodology not in METHODOLOGIES:
        errors['methodology'] = f"Must be one of {sorted(METHODOLOGIES)}"
        methodology = 'polarized_80_20'

    # ---- previous (optional progression seed) ------------------------------
    previous = payload.get('previous')
    prev_levels: List[int] = []
    if previous is not None:
        if not isinstance(previous, dict):
            errors['previous'] = 'Must be an object when provided'
        else:
            series_used = previous.get('seriesUsed')
            if series_used is not None and (
                    not isinstance(series_used, list)
                    or not all(isinstance(s, str) for s in series_used)):
                errors['previous.seriesUsed'] = 'Must be a list of strings'
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
