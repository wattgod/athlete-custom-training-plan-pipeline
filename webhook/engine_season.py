"""
Engine Season — request-scoped bridge between POST /engine/season and the
pipeline's season-planning brain (Convergence Phase 2).

Week typing is NOT reimplemented here: `calculate_plan_dates` in
athletes/scripts is the SINGLE SOURCE OF TRUTH for phases, recovery weeks,
taper, race week, and the B/C-race mini-taper overlay. This module only
validates the request, calls it, and maps its output onto the contract the
Endure Labs consumer Zod-validates against.

Contract (build EXACTLY this — the Endure consumer is built against it):

    Request:
      {
        "athlete": {"hours_per_week": num REQUIRED,
                    "experience_years"?: num, "age"?: num,
                    "discipline"?: "gravel"|"road"|"mtb"},
        "races": [{"name": str, "date": "YYYY-MM-DD",
                   "priority": "A"|"B"|"C", "discipline"?: str,
                   "distance_mi"?: num, "elevation_ft"?: num}, ...],
        "start_date": "YYYY-MM-DD" REQUIRED,
        "methodology"?: engine enum (same as /engine/block)
      }
      >= 1 A-race dated after start_date is REQUIRED; the nearest future
      A-race is the season anchor. Season length (start → anchor, counted in
      Mon-Sun calendar weeks inclusive) must be 4-40 weeks.

    Response 200:
      {
        "weeks": [{"number": 1-based int, "start_date", "end_date",
                   "phase": base|build|peak|taper|race|recovery|transition,
                   "type": load|recovery|taper|race|testing,
                   "block": {"index": int, "position": int, "length": int},
                   "races": [{"name", "priority", "date"}],
                   "note"?: str}],
        "phases": [{"phase", "start_date", "end_date", "weeks": int}],
        "blocks": [{"index", "phase", "start_date", "weeks": int}],
        "engine": {"version", "generated_ms"}
      }

    - weeks[].block.index is 0-based (blocks[week.block.index] is that
      week's block); block.position is 1-based within the block, mirroring
      /engine/block week numbering.
    - blocks partition the season: every week belongs to exactly one block,
      every block is 2-4 weeks — each blocks[] entry feeds straight into
      /engine/block as {"phase", "weeks", "start_date"}.

Mapping notes:
- calculate_plan_dates weeks carry {phase, is_race_week, is_recovery_week,
  b_race?}. Contract type derives as: race week → 'race'; taper phase →
  'taper'; is_recovery_week → 'recovery'; else 'load'. ('testing' is in the
  contract enum but the season brain does not type FTP-test weeks — never
  emitted.)
- start_date is snapped to the Monday of its calendar week
  (calculate_plan_dates plans start on Monday of Week 1); a mid-week
  start_date falls inside week 1.
- B/C races between start and the anchor are passed as b_events, so the
  mini-taper overlay lands exactly as the pipeline computes it (recovery
  flag cleared on the race's week, phase preserved).
- Block splitting: weeks are first segmented into contiguous same-phase
  runs; the taper run merges with the race week into a single 'race'
  segment (matching /engine/block, where phase='race' yields taper weeks
  ending in a race week); any remaining 1-week run merges into its previous
  run (or next, if first). Each segment is then partitioned into 2-4-week
  blocks by a deterministic DP that prefers splitting right after recovery
  weeks and prefers 3-week blocks (cost = sum(|size-3|) + 2 per interior
  boundary not following a recovery week).
- Block phase: 'race' if the block contains the race week, else the phase
  of the block's first week.
"""

import functools
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Shared enums/helpers — single source with /engine/block (engine_adapter
# also puts athletes/scripts on sys.path, which calculate_plan_dates needs).
from engine_adapter import (  # noqa: F401
    DISCIPLINES,
    ENGINE_VERSION,
    METHODOLOGIES,
    MIN_HOURS,
    _SCRIPTS_DIR,
    _is_num,
)

from calculate_plan_dates import (  # noqa: E402
    calculate_plan_dates,
    validate_plan_dates,
)

PRIORITIES = {'A', 'B', 'C'}
MIN_SEASON_WEEKS = 4
MAX_SEASON_WEEKS = 40
BLOCK_MIN_WEEKS = 2
BLOCK_MAX_WEEKS = 4
PAST_START_GRACE_DAYS = 7


class SeasonBuildError(Exception):
    """The season calendar failed the source-of-truth's own validation
    (only reachable via edge starts the request validator allows, e.g. a
    slightly-past start_date whose window collapses). Carries contract
    field errors for a 400 body."""

    def __init__(self, fields: Dict[str, str]):
        super().__init__('season_build_failed')
        self.fields = fields


@functools.lru_cache(maxsize=1)
def _methodology_meso_patterns() -> Dict[str, Optional[str]]:
    """methodology id → meso_pattern from the pipeline's methodologies.yaml
    (currently 3:1 across the board; read from config so the season endpoint
    tracks any future change). Missing file/keys fall back to
    calculate_plan_dates' own DEFAULT_MESO_PATTERN via None."""
    path = Path(_SCRIPTS_DIR) / 'config' / 'methodologies.yaml'
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except OSError:  # pragma: no cover — config ships with the repo
        return {}
    return {k: v.get('meso_pattern')
            for k, v in data.items() if isinstance(v, dict)}


def _parse_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------

def validate_request(payload: Any) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Validate the /engine/season request body.

    Returns (params, field_errors). If field_errors is non-empty the caller
    must return 400 with them; params is only meaningful when errors is empty.
    """
    errors: Dict[str, str] = {}
    params: Dict[str, Any] = {}

    if not isinstance(payload, dict):
        return {}, {'body': 'Request body must be a JSON object'}

    # ---- athlete ----------------------------------------------------------
    # hours_per_week uses the same bounds as /engine/block so a season that
    # validates here never 400s downstream when its blocks are generated.
    athlete = payload.get('athlete')
    if not isinstance(athlete, dict):
        errors['athlete'] = 'Required object'
        athlete = {}

    hours = athlete.get('hours_per_week')
    if not _is_num(hours) or not (MIN_HOURS <= hours <= 40):
        errors['athlete.hours_per_week'] = (
            f'Required number between {MIN_HOURS} and 40')

    exp = athlete.get('experience_years')
    if exp is not None and (not _is_num(exp) or exp < 0):
        errors['athlete.experience_years'] = 'Must be a non-negative number'

    age = athlete.get('age')
    if age is not None and (not _is_num(age) or not (10 <= age <= 100)):
        errors['athlete.age'] = 'Must be a number between 10 and 100'

    discipline = athlete.get('discipline')
    if discipline is not None and discipline not in DISCIPLINES:
        errors['athlete.discipline'] = f"Must be one of {sorted(DISCIPLINES)}"

    # ---- start_date --------------------------------------------------------
    start_raw = payload.get('start_date')
    start_dt = _parse_date(start_raw)
    if start_dt is None:
        errors['start_date'] = 'Required string YYYY-MM-DD'
    else:
        today = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)
        if start_dt < today - timedelta(days=PAST_START_GRACE_DAYS):
            errors['start_date'] = (
                f'Must be no more than {PAST_START_GRACE_DAYS} days in the '
                f'past')

    # ---- races -------------------------------------------------------------
    races_raw = payload.get('races')
    clean_races: List[Dict[str, Any]] = []
    if not isinstance(races_raw, list) or not races_raw:
        errors['races'] = 'Required non-empty array of races'
    else:
        for i, race in enumerate(races_raw):
            if not isinstance(race, dict):
                errors[f'races[{i}]'] = 'Must be an object'
                continue
            ok = True
            name = race.get('name')
            if not isinstance(name, str) or not name.strip():
                errors[f'races[{i}].name'] = 'Required non-empty string'
                ok = False
            race_dt = _parse_date(race.get('date'))
            if race_dt is None:
                errors[f'races[{i}].date'] = 'Required string YYYY-MM-DD'
                ok = False
            priority = race.get('priority')
            if priority not in PRIORITIES:
                errors[f'races[{i}].priority'] = "Must be 'A', 'B', or 'C'"
                ok = False
            race_disc = race.get('discipline')
            if race_disc is not None and race_disc not in DISCIPLINES:
                errors[f'races[{i}].discipline'] = (
                    f"Must be one of {sorted(DISCIPLINES)}")
                ok = False
            for fld in ('distance_mi', 'elevation_ft'):
                v = race.get(fld)
                if v is not None and (not _is_num(v) or v < 0):
                    errors[f'races[{i}].{fld}'] = (
                        'Must be a non-negative number')
                    ok = False
            if ok:
                clean_races.append({
                    'name': name.strip(),
                    'date': race['date'],
                    'priority': priority,
                    'dt': race_dt,
                })

    # ---- methodology (optional; null means default, mirrors /engine/block) -
    methodology = payload.get('methodology') or 'polarized_80_20'
    if methodology not in METHODOLOGIES:
        errors['methodology'] = f"Must be one of {sorted(METHODOLOGIES)}"
        methodology = 'polarized_80_20'

    # ---- anchor + season window ---------------------------------------------
    # Nearest future A-race (relative to start_date) anchors the season.
    if start_dt is not None and clean_races and 'races' not in errors:
        a_races = [r for r in clean_races
                   if r['priority'] == 'A' and r['dt'] > start_dt]
        if not a_races:
            errors['races'] = (
                'At least one A-priority race dated after start_date is '
                'required')
        else:
            anchor = min(a_races, key=lambda r: (r['dt'], r['name']))
            # Season length in Mon-Sun calendar weeks, inclusive of both the
            # start week and the race week (calculate_plan_dates' counting).
            start_monday = start_dt - timedelta(days=start_dt.weekday())
            race_monday = anchor['dt'] - timedelta(days=anchor['dt'].weekday())
            plan_weeks = (race_monday - start_monday).days // 7 + 1
            if not (MIN_SEASON_WEEKS <= plan_weeks <= MAX_SEASON_WEEKS):
                errors['season'] = (
                    f'Season must be {MIN_SEASON_WEEKS}-{MAX_SEASON_WEEKS} '
                    f'weeks from start_date to the anchor A-race '
                    f'(got {plan_weeks})')
            params.update({
                'anchor': anchor,
                'plan_weeks': plan_weeks,
                'start_monday': start_monday.strftime('%Y-%m-%d'),
            })

    params.update({
        'start_date': start_raw if isinstance(start_raw, str) else '',
        'races': sorted(clean_races, key=lambda r: (r['date'], r['name'])),
        'methodology': methodology,
    })
    return params, errors


# ---------------------------------------------------------------------------
# Block partitioning
# ---------------------------------------------------------------------------

def _split_sizes(types: List[str]) -> List[int]:
    """Partition one same-phase segment into 2-4-week block sizes.

    Deterministic DP: cost = sum(|size - 3|) for the 3-week preference,
    + 2 for every interior boundary that does NOT immediately follow a
    recovery week (i.e. splits land at recovery weeks when possible, so a
    load/load/load/recovery run becomes exactly one 4-week block).
    """
    n = len(types)
    unreachable = (10 ** 9, None)
    dp: List[Tuple[int, Optional[Tuple[int, ...]]]] = [unreachable] * (n + 1)
    dp[0] = (0, ())
    for i in range(1, n + 1):
        for size in (BLOCK_MAX_WEEKS, 3, BLOCK_MIN_WEEKS):
            j = i - size
            if j < 0 or dp[j][1] is None:
                continue
            cost = dp[j][0] + abs(size - 3)
            if j > 0 and types[j - 1] != 'recovery':
                cost += 2
            if cost < dp[i][0]:
                dp[i] = (cost, dp[j][1] + (size,))
    sizes = dp[n][1]
    if sizes is None:  # pragma: no cover — segments are always >= 2 weeks
        raise ValueError(f'Cannot partition a {n}-week segment into '
                         f'{BLOCK_MIN_WEEKS}-{BLOCK_MAX_WEEKS}-week blocks')
    return list(sizes)


def _partition_blocks(weeks_out: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Partition contract weeks into 2-4-week blocks (annotating each week's
    `block` field in place) and return the contract `blocks` array."""
    # 1. Contiguous same-phase runs (index lists into weeks_out).
    runs: List[Dict[str, Any]] = []
    for i, week in enumerate(weeks_out):
        if runs and runs[-1]['phase'] == week['phase']:
            runs[-1]['idx'].append(i)
        else:
            runs.append({'phase': week['phase'], 'idx': [i]})

    # 2. The taper run joins the race week into one 'race' segment —
    #    /engine/block phase='race' generates taper weeks ending in a race
    #    week, so this is the block shape a caller regenerates faithfully.
    merged: List[Dict[str, Any]] = []
    i = 0
    while i < len(runs):
        run = runs[i]
        if (run['phase'] == 'taper' and i + 1 < len(runs)
                and runs[i + 1]['phase'] == 'race'):
            merged.append({'phase': 'race',
                           'idx': run['idx'] + runs[i + 1]['idx']})
            i += 2
        else:
            merged.append(run)
            i += 1
    runs = merged

    # 3. Runs shorter than the block minimum merge into the previous run
    #    (or the next, when first) until every segment is splittable.
    while len(runs) > 1:
        short = next((i for i, r in enumerate(runs)
                      if len(r['idx']) < BLOCK_MIN_WEEKS), None)
        if short is None:
            break
        if short > 0:
            runs[short - 1]['idx'].extend(runs[short]['idx'])
        else:
            runs[1]['idx'] = runs[0]['idx'] + runs[1]['idx']
        runs.pop(short)

    # 4. Split each segment and annotate weeks.
    blocks: List[Dict[str, Any]] = []
    for seg in runs:
        sizes = _split_sizes([weeks_out[i]['type'] for i in seg['idx']])
        cursor = 0
        for size in sizes:
            idxs = seg['idx'][cursor:cursor + size]
            cursor += size
            block_index = len(blocks)
            first_week = weeks_out[idxs[0]]
            phase = ('race'
                     if any(weeks_out[i]['type'] == 'race' for i in idxs)
                     else first_week['phase'])
            blocks.append({
                'index': block_index,
                'phase': phase,
                'start_date': first_week['start_date'],
                'weeks': size,
            })
            for position, week_i in enumerate(idxs, start=1):
                weeks_out[week_i]['block'] = {
                    'index': block_index,
                    'position': position,
                    'length': size,
                }
    return blocks


# ---------------------------------------------------------------------------
# Season generation
# ---------------------------------------------------------------------------

def generate_season(params: Dict[str, Any]) -> Dict[str, Any]:
    """params (from validate_request) → contract response dict.

    Raises SeasonBuildError (→ 400) if the built calendar fails
    calculate_plan_dates' own CRITICAL validation.
    """
    t0 = time.perf_counter()
    anchor = params['anchor']

    # B/C races feed the source-of-truth's mini-taper overlay; races outside
    # the window simply never match a week (calculate_plan_dates skips them).
    b_events = [{'name': r['name'], 'date': r['date']}
                for r in params['races'] if r['priority'] in ('B', 'C')]

    plan = calculate_plan_dates(
        anchor['date'],
        plan_weeks=params['plan_weeks'],
        preferred_start=params['start_monday'],
        b_events=b_events,
        meso_pattern=_methodology_meso_patterns().get(params['methodology']),
    )

    critical = [e for e in validate_plan_dates(plan, anchor['date'])
                if e.startswith('CRITICAL')]
    if critical:
        raise SeasonBuildError({
            'start_date': ('Season calendar failed validation: '
                           + '; '.join(critical))})

    weeks_out: List[Dict[str, Any]] = []
    for week in plan['weeks']:
        monday = week['monday']
        sunday = week['sunday']
        if week['is_race_week']:
            week_type = 'race'
        elif week['phase'] == 'taper':
            week_type = 'taper'
        elif week.get('is_recovery_week'):
            week_type = 'recovery'
        else:
            week_type = 'load'

        week_races = [
            {'name': r['name'], 'priority': r['priority'], 'date': r['date']}
            for r in params['races'] if monday <= r['date'] <= sunday
        ]

        entry: Dict[str, Any] = {
            'number': week['week'],
            'start_date': monday,
            'end_date': sunday,
            'phase': week['phase'],
            'type': week_type,
            'races': week_races,
        }
        if week['is_race_week']:
            entry['note'] = f"Race week — {anchor['name']} on {anchor['date']}"
        elif week.get('b_race'):
            b = week['b_race']
            entry['note'] = (
                f"{b['name']} on {b['date']} — mini-taper overlay "
                f"({week['phase']} phase preserved)")
        elif week_type == 'recovery':
            entry['note'] = 'Recovery week'
        weeks_out.append(entry)

    blocks = _partition_blocks(weeks_out)

    phases_out: List[Dict[str, Any]] = []
    for week in weeks_out:
        if phases_out and phases_out[-1]['phase'] == week['phase']:
            phases_out[-1]['weeks'] += 1
            phases_out[-1]['end_date'] = week['end_date']
        else:
            phases_out.append({
                'phase': week['phase'],
                'start_date': week['start_date'],
                'end_date': week['end_date'],
                'weeks': 1,
            })

    generated_ms = int(round((time.perf_counter() - t0) * 1000))
    return {
        'weeks': weeks_out,
        'phases': phases_out,
        'blocks': blocks,
        'engine': {
            'version': ENGINE_VERSION,
            'generated_ms': generated_ms,
        },
    }
