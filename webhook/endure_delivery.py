"""Endure Labs plan delivery — pipeline side of Phase 4b (push + coexistence).

Implements the PINNED contract from endurelabs
specs/plan-delivery-on-endure/design.md (§3, ratified Jul 6 2026):

    POST {ENDURE_DELIVERY_URL}/api/delivery/purchased-plan
    Header: X-Delivery-Secret: {ENDURE_DELIVERY_SECRET}
    Body: {
      "order_id": str,
      "athlete": {"email", "name", "ftp"?, "weight_kg"?, "age"?,
                  "hours_per_week", "experience_years"?, "off_days"?,
                  "long_ride_day"?, "limiters"?, "constraints"?},
      "races": [{"name", "date", "priority",
                 "discipline"?, "distance_mi"?, "elevation_ft"?}],
      "plan": {"name", "start_date"},
      "intake": {raw questionnaire dict}
    }
    200: {"order_id","athlete_id","plan_id","block_id","invitation_id",
          "status": "delivered"|"already_delivered"} | 401 | 400 | 5xx

Design rules (order-killer-prevention):
- The feature is entirely OFF unless BOTH ENDURE_DELIVERY_URL and
  ENDURE_DELIVERY_SECRET are set (kill switch: unset the URL on Railway).
- Delivery NEVER fails the order. Every function here either returns a
  result dict or raises EndureMappingError, which the caller (app.py)
  converts to a failed-delivery record + TrainingPeaks fallback. The full
  ZWO package is always generated regardless of target.
- Default target stays "trainingpeaks" until Matti manually flips
  DELIVERY_TARGET_DEFAULT=endure (Decision 2: after 5 consecutive
  successful Endure deliveries). The streak counter here just informs.

Zero Flask dependencies so tests can import it standalone.
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger('gravel-god-webhook.endure')

# Path appended to ENDURE_DELIVERY_URL (contract-pinned)
DELIVERY_PATH = '/api/delivery/purchased-plan'

# Streak file lives next to the job records on the persistent volume
STREAK_FILENAME = '.endure_delivery_streak.json'

# Serializes streak read-modify-write within this process (cross-process
# safety comes from atomic tempfile + os.replace, same as job records).
_streak_lock = threading.Lock()

VALID_TARGETS = ('trainingpeaks', 'endure')


class EndureMappingError(Exception):
    """Profile could not be mapped onto the delivery contract.

    Raised for missing REQUIRED contract fields (email, hours_per_week).
    Callers treat it as a failed delivery → TrainingPeaks fallback.
    """


# =============================================================================
# CONFIG — read env at call time so the Railway kill switch (unset the URL)
# applies to queued/retried jobs too, and so tests can monkeypatch.
# =============================================================================

def delivery_url() -> str:
    return os.environ.get('ENDURE_DELIVERY_URL', '').strip().rstrip('/')


def delivery_secret() -> str:
    return os.environ.get('ENDURE_DELIVERY_SECRET', '').strip()


def app_url() -> str:
    """Endure web app base URL (coach review links)."""
    return os.environ.get('ENDURE_APP_URL', 'https://endurelabs.app').rstrip('/')


def request_timeout() -> float:
    try:
        return float(os.environ.get('ENDURE_DELIVERY_TIMEOUT', '20'))
    except ValueError:
        return 20.0


def is_enabled() -> bool:
    """Feature is ON only when both URL and secret are configured."""
    return bool(delivery_url() and delivery_secret())


def resolve_delivery_target(metadata: dict = None) -> str:
    """Resolve the delivery target for one order.

    Precedence:
      1. Feature disabled (env unset) → always "trainingpeaks"
      2. Per-order override: Stripe metadata['delivery_target'] (operator
         sets it on the checkout session / via the Stripe dashboard)
      3. Env default: DELIVERY_TARGET_DEFAULT (flip is MANUAL — Decision 2)
      4. "trainingpeaks"
    """
    if not is_enabled():
        return 'trainingpeaks'

    override = ((metadata or {}).get('delivery_target') or '').strip().lower()
    if override in VALID_TARGETS:
        return override

    default = os.environ.get('DELIVERY_TARGET_DEFAULT', '').strip().lower()
    if default in VALID_TARGETS:
        return default

    return 'trainingpeaks'


# =============================================================================
# PROFILE → CONTRACT MAPPING
#
# Input is the build_profile() output (profile.yaml) from
# athletes/scripts/intake_to_plan.py — field names and units below are
# verbatim from that function. All units already match the contract
# (watts, kg, hours/week, miles, feet): only names change.
# =============================================================================

def build_delivery_payload(profile: dict, order_id: str,
                           intake: dict = None) -> dict:
    """Map a pipeline profile.yaml dict onto the pinned contract body.

    Raises EndureMappingError when a REQUIRED contract field is missing
    (email, hours_per_week) — recoverable via the TP fallback, never fatal
    to the order.
    """
    if not isinstance(profile, dict) or not profile:
        raise EndureMappingError('profile is empty')

    fitness = profile.get('fitness_markers') or {}
    availability = profile.get('weekly_availability') or {}
    schedule = profile.get('schedule_constraints') or {}
    history = profile.get('training_history') or {}
    health = profile.get('health_factors') or {}
    racing = profile.get('racing') or {}

    email = (profile.get('email') or '').strip()
    if not email:
        raise EndureMappingError('profile has no email')

    hours = availability.get('cycling_hours_target')
    if not hours or hours <= 0:
        raise EndureMappingError('profile has no cycling_hours_target')

    athlete = {
        'email': email,
        'name': profile.get('name', ''),
        'hours_per_week': hours,
    }

    # Optional fields — omitted when absent, never sent as null/0.
    ftp = fitness.get('ftp_watts')
    if ftp:
        athlete['ftp'] = int(ftp)
    weight_kg = fitness.get('weight_kg')
    if weight_kg:
        athlete['weight_kg'] = float(weight_kg)
    age = health.get('age')
    if age:
        athlete['age'] = int(age)
    experience_years = history.get('years_cycling')
    if experience_years:
        athlete['experience_years'] = int(experience_years)
    off_days = schedule.get('preferred_off_days')
    if off_days:
        athlete['off_days'] = list(off_days)
    long_ride_day = schedule.get('preferred_long_day')
    if long_ride_day:
        athlete['long_ride_day'] = long_ride_day
    limiters = (racing.get('obstacles') or '').strip()
    if limiters:
        athlete['limiters'] = limiters
    constraints = _build_constraints_text(profile)
    if constraints:
        athlete['constraints'] = constraints

    races = _map_races(profile)
    target = profile.get('target_race') or {}
    plan_start = (profile.get('plan_start') or {}).get('preferred_start', '')

    race_name = target.get('name', '')
    plan_name = (f'Custom Training Plan — {race_name}' if race_name
                 else f'Custom Training Plan — {athlete["name"] or email}')

    return {
        'order_id': order_id or '',
        'athlete': athlete,
        'races': races,
        'plan': {
            'name': plan_name,
            'start_date': plan_start,
        },
        'intake': intake or {},
    }


def _build_constraints_text(profile: dict) -> str:
    """Coach-visible constraint summary: injuries, medical, volume warning."""
    parts = []
    injuries = (profile.get('injury_history') or {}).get('current_injuries') or []
    for inj in injuries:
        desc = (inj.get('description') or '').strip() if isinstance(inj, dict) else str(inj)
        if desc:
            parts.append(f'Current injury: {desc}')
    health = profile.get('health_factors') or {}
    medical = (health.get('medical_conditions') or '').strip()
    if medical and medical.lower() not in ('none', 'n/a'):
        parts.append(f'Medical: {medical}')
    volume_warning = (profile.get('weekly_availability') or {}).get('volume_warning')
    if volume_warning:
        parts.append(str(volume_warning))
    travel = profile.get('travel_dates') or []
    if travel:
        parts.append(f'Travel dates: {travel}')
    return '; '.join(parts)


def _map_races(profile: dict) -> list:
    """A-race + b_events → contract races array.

    Event dicts in profile.yaml carry {name, date, distance_miles, goal,
    priority}. Elevation and discipline live only on target_race, so they
    are attached to the matching A event.
    """
    target = profile.get('target_race') or {}
    target_name = target.get('name', '')
    target_discipline = (target.get('discipline')
                         or target.get('generic_discipline')
                         or profile.get('discipline_default')
                         or '')

    races = []
    for event in (profile.get('a_events') or []) + (profile.get('b_events') or []):
        race = {
            'name': event.get('name', ''),
            'date': event.get('date', ''),
            'priority': event.get('priority', 'B'),
        }
        distance_mi = event.get('distance_miles')
        if distance_mi:
            race['distance_mi'] = float(distance_mi)
        if race['priority'] == 'A' and race['name'] == target_name:
            elevation_ft = target.get('elevation_ft')
            if elevation_ft:
                race['elevation_ft'] = int(elevation_ft)
            if target_discipline:
                race['discipline'] = target_discipline
        races.append(race)
    return races


# =============================================================================
# DELIVERY CALL — timeout + ONE retry, never raises
# =============================================================================

def deliver_purchased_plan(payload: dict) -> dict:
    """POST the payload to Endure. Returns a delivery record dict:

        {'ok': bool,
         'status': 'delivered' | 'already_delivered' | 'failed',
         'athlete_id' / 'plan_id' / 'block_id' / 'invitation_id': str (on ok),
         'review_url': str (on ok),
         'error': str | None,
         'attempts': int,
         'delivered_at': iso timestamp (on ok)}

    Retries ONCE on transport errors and 5xx. 4xx (bad payload / bad
    secret) is not retryable — the retry would fail identically.
    Never raises.
    """
    if not is_enabled():
        return {'ok': False, 'status': 'failed', 'attempts': 0,
                'error': 'Endure delivery not configured '
                         '(ENDURE_DELIVERY_URL / ENDURE_DELIVERY_SECRET unset)'}

    url = delivery_url() + DELIVERY_PATH
    headers = {'X-Delivery-Secret': delivery_secret()}
    timeout = request_timeout()
    last_error = 'unknown error'

    for attempt in (1, 2):
        try:
            resp = requests.post(url, json=payload, headers=headers,
                                 timeout=timeout)
        except requests.RequestException as e:
            # Timeout / connection error — retryable. No PII in the message
            # (payload is never logged).
            last_error = f'request failed: {type(e).__name__}'
            logger.warning(f"Endure delivery attempt {attempt} failed: {last_error}")
            continue

        if resp.status_code == 200:
            try:
                body = resp.json()
            except ValueError:
                body = {}
            status = body.get('status', 'delivered')
            if status not in ('delivered', 'already_delivered'):
                status = 'delivered'
            record = {
                'ok': True,
                'status': status,
                'attempts': attempt,
                'error': None,
                'delivered_at': datetime.now().isoformat(),
            }
            for key in ('athlete_id', 'plan_id', 'block_id', 'invitation_id'):
                if body.get(key):
                    record[key] = body[key]
            if record.get('athlete_id'):
                record['review_url'] = coach_review_url(record['athlete_id'])
            return record

        if 500 <= resp.status_code < 600:
            last_error = f'HTTP {resp.status_code}'
            logger.warning(f"Endure delivery attempt {attempt}: {last_error}")
            continue

        # 4xx — permanent for this payload; do not retry.
        detail = ''
        try:
            err_body = resp.json()
            detail = str(err_body.get('error', ''))[:200]
        except ValueError:
            pass
        return {'ok': False, 'status': 'failed', 'attempts': attempt,
                'error': f'HTTP {resp.status_code}'
                         + (f': {detail}' if detail else '')}

    return {'ok': False, 'status': 'failed', 'attempts': 2,
            'error': last_error}


def coach_review_url(endure_athlete_id: str) -> str:
    """Deep link to the coach approval UI for a delivered plan.

    Endure route: /coach/athletes/[id]/plan (existing approval surface —
    spec §3 step 3: coach reviews block 1 in the existing approval UI).
    """
    return f'{app_url()}/coach/athletes/{endure_athlete_id}/plan'


# =============================================================================
# STREAK COUNTER (Decision 2) — durable JSON on the persistent volume.
#
# Counts consecutive successful delivery POSTs. This is the pipeline-side
# signal only; the full "successful delivery" definition (invite accepted +
# block-1 activities visible in week 1) is measured Endure-side. Flipping
# DELIVERY_TARGET_DEFAULT stays MANUAL — this counter just informs.
# =============================================================================

def _streak_path(data_dir: str) -> Path:
    return Path(data_dir) / STREAK_FILENAME


def read_streak(data_dir: str) -> dict:
    """Load the streak record. Returns zeroed record if absent/unreadable."""
    default = {
        'consecutive_successes': 0,
        'total_successes': 0,
        'total_failures': 0,
        'last_order_id': None,
        'last_status': None,
        'updated_at': None,
    }
    path = _streak_path(data_dir)
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text())
        default.update({k: data[k] for k in default if k in data})
        return default
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Unreadable streak file {path.name}: {e}")
        return default


def record_delivery_result(success: bool, order_id: str, data_dir: str) -> dict:
    """Record one delivery outcome; returns the updated streak record.

    - Success: consecutive_successes += 1 — unless this order_id was the
      last one counted (idempotent re-posts / already_delivered retries
      must not double-count).
    - Failure: consecutive_successes resets to 0.

    Atomic write (tempfile + os.replace). Never raises.
    """
    with _streak_lock:
        streak = read_streak(data_dir)
        repeat_order = bool(order_id) and streak.get('last_order_id') == order_id

        if success:
            if not (repeat_order and streak.get('last_status') == 'success'):
                streak['consecutive_successes'] += 1
                streak['total_successes'] += 1
            streak['last_status'] = 'success'
        else:
            streak['consecutive_successes'] = 0
            streak['total_failures'] += 1
            streak['last_status'] = 'failure'

        streak['last_order_id'] = order_id or streak.get('last_order_id')
        streak['updated_at'] = datetime.now().isoformat()

        try:
            path = _streak_path(data_dir)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f'.{path.name}.tmp')
            with open(tmp, 'w') as f:
                json.dump(streak, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except OSError as e:
            logger.error(f"Failed to persist Endure streak: {e}")

        return streak
