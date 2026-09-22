#!/usr/bin/env python3
"""
Block Builder — constructs a single 3-week training block.

Standard block = 2 Load weeks + 1 Recovery week.
Each load week gets intensity, long ride, and filler workouts assigned
from the phase × archetype matrix. Recovery week is sacred (Endurance L1-L2 + Openers only).

Source: block-builder SKILL.md Steps 3-6
"""

from typing import Dict, List, Any, Optional
from workout_selector import (
    select_workouts_for_week,
    get_workout_tss,
    get_workout_duration,
    estimate_week_tss,
    _road_ae31_level,
)
from series_tracker import SeriesTracker
from taper_prescription import (
    RACE_WEEK_DAILY_LOAD_FRACTION,
    TAPER_DAILY_LOAD_FRACTION,
)

# AE-2.7 (amended 2026-09-17) session-floor constants -- see apply_session_floor.
SESSION_FLOOR_MIN = 60
SESSION_FLOOR_MIN_OPT_IN = 45          # explicit athlete request only
WEEKDAY_TARGET_MAX_MIN = 120
_Z2_TSS_PER_MIN = 0.70                 # ~42 TSS/h, IF .65 -- the added minutes are Z2


# Day template: standard week structure
# Intensity days are non-consecutive, long ride on weekend
STANDARD_DAY_TEMPLATE = {
    # day: role
    'Mon': 'off_or_strength',
    'Tue': 'intensity',
    'Wed': 'filler',
    'Thu': 'intensity',
    'Fri': 'off_or_strength',
    'Sat': 'long_ride',
    'Sun': 'filler',
}

DAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def build_block(
    phase: str,
    archetype: str,
    block_number: int,
    base_level: int,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    available_days: int = 6,
    hours_per_week: float = 10,
    series_tracker: Optional[SeriesTracker] = None,
) -> Dict[str, Any]:
    """Build a single 3-week training block.

    Args:
        phase: Training phase ('base', 'build', 'race_prep', 'racing')
        archetype: Athlete archetype
        block_number: Block sequence number (1-indexed)
        base_level: Starting workout level for this block
        max_level: Maximum level (training age constraint)
        max_intensity: Max intensity sessions per week
        off_days: Athlete's preferred off days (e.g., ['Mon', 'Fri'])
        long_ride_day: Preferred long ride day
        available_days: Total training days per week
        series_tracker: Optional tracker for cross-block coherence

    Returns:
        Block dict with 3 weeks of day-by-day workout assignments
    """
    if off_days is None:
        off_days = ['Mon']
    if series_tracker is None:
        series_tracker = SeriesTracker()

    series_tracker.start_block()

    # Build day template from athlete preferences
    day_roles = _build_day_template(off_days, long_ride_day, max_intensity)

    weeks = []

    # Week 1: Load
    w1 = _build_week(
        week_num=1,
        week_type='load',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=1,
        hours_per_week=hours_per_week,
    )
    weeks.append(w1)

    series_tracker.advance_week()

    # Week 2: Load (+1 level)
    w2 = _build_week(
        week_num=2,
        week_type='load',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=2,
        hours_per_week=hours_per_week,
    )
    weeks.append(w2)

    series_tracker.advance_week()

    # Week 3: Recovery (sacred)
    w3 = _build_week(
        week_num=3,
        week_type='recovery',
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=1,  # Recovery: max 1 (openers only)
        series_tracker=series_tracker,
        week_in_block=3,
        hours_per_week=hours_per_week,
    )
    weeks.append(w3)

    series_tracker.end_block()

    # Validate series coherence
    violations = series_tracker.validate_block()

    return {
        'block_number': block_number,
        'phase': phase,
        'archetype': archetype,
        'base_level': base_level,
        'weeks': weeks,
        'series_violations': violations,
    }


def build_calendar_week(
    week_type: str,
    phase: str,
    archetype: str,
    block_number: int,
    week_in_block: int,
    base_level: int,
    max_level: int = 6,
    max_intensity: int = 3,
    off_days: List[str] = None,
    long_ride_day: str = 'Sat',
    hours_per_week: float = 10,
    series_tracker: Optional[SeriesTracker] = None,
    discipline: str = 'gravel',
    day_caps: Dict[str, int] = None,
    methodology: str = 'polarized_80_20',
    category_weights: Dict[str, float] = None,
    avoid_series: set = None,
    methodology_profile: Dict[str, Any] = None,
    event_format: str = None,
    race_day: Optional[str] = None,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
    session_floor_min: int = SESSION_FLOOR_MIN,
    grow_to_weekday_target: bool = True,
    preferred_intensity_days: Optional[List[str]] = None,
    floor_pct_override: Optional[float] = None,
    taper_budget_minutes: Optional[float] = None,
    taper_long_ride_cap_minutes: Optional[float] = None,
    race_week_target_tss: Optional[float] = None,
    race_week_tss_per_hour: float = 55.0,
) -> Dict[str, Any]:
    """Build one week whose type and phase come from the calendar (plan_dates).

    Unlike build_block(), this does not impose a Load/Load/Recovery rhythm —
    the caller (build_plan_from_calendar) supplies week_type per week from
    plan_dates.yaml, the single source of scheduling truth.

    category_weights / avoid_series / methodology_profile (all optional,
    default None → behavior unchanged) bias WHICH names fill the
    intensity/long-ride slots — see workout_selector.select_workouts_for_week.
    """
    if off_days is None:
        off_days = ['Mon']
    if series_tracker is None:
        series_tracker = SeriesTracker()
        series_tracker.start_block()

    day_roles = _build_day_template(off_days, long_ride_day, max_intensity, week_type=week_type,
                                    preferred_intensity_days=preferred_intensity_days)

    week = _build_week(
        week_num=week_in_block,
        week_type=week_type,
        phase=phase,
        archetype=archetype,
        day_roles=day_roles,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        series_tracker=series_tracker,
        week_in_block=week_in_block,
        hours_per_week=hours_per_week,
        block_number=block_number,
        discipline=discipline,
        day_caps=day_caps,
        methodology=methodology,
        category_weights=category_weights,
        avoid_series=avoid_series,
        methodology_profile=methodology_profile,
        event_format=event_format,
        race_day=race_day,
        athlete_age=athlete_age,
        stress_level=stress_level,
        session_floor_min=session_floor_min,
        grow_to_weekday_target=grow_to_weekday_target,
        floor_pct_override=floor_pct_override,
        taper_budget_minutes=taper_budget_minutes,
        taper_long_ride_cap_minutes=taper_long_ride_cap_minutes,
        race_week_target_tss=race_week_target_tss,
        race_week_tss_per_hour=race_week_tss_per_hour,
    )
    week['block_number'] = block_number
    return week


def _build_day_template(
    off_days: List[str],
    long_ride_day: str,
    max_intensity: int,
    week_type: Optional[str] = None,
    preferred_intensity_days: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Build a day-by-day role template from athlete preferences.

    Rules:
    1. Mark off days first
    2. Place long ride on preferred day
    3. Place intensity on non-consecutive days
    4. Fill remaining with filler (endurance)
    """
    roles = {}

    # Step 1: Off days
    for day in off_days:
        roles[day] = 'off'

    # Step 2: Long ride day
    roles[long_ride_day] = 'long_ride'

    # Step 3: Place intensity days.
    # Preference order matches coach practice: Tue/Thu are the canonical
    # quality days (fresh after Monday, buffered from the weekend long ride).
    PREFERRED_INTENSITY_ORDER = ['Tue', 'Thu', 'Mon', 'Wed', 'Fri', 'Sat', 'Sun']
    available = [d for d in PREFERRED_INTENSITY_ORDER if d not in roles]

    if week_type == 'testing':
        # Testing weeks are an assessment battery, not two interchangeable
        # quality days: the coach's design intent (workout_selector's
        # _select_testing_week docstring) is FTP earlier in the week,
        # anaerobic later, because the anaerobic test's %FTP targets depend
        # on a fresh FTP number. The generic preference-order pick below
        # ("Tue/Thu are canonical") is chronologically blind -- on a
        # Tue-off schedule it picked Thu then wrapped back to Monday, which
        # a downstream chronological zip then read as FTP-Monday /
        # Anaerobic-Thursday, ahead of the very FTP test meant to set its
        # zones. Pick the earliest viable day for FTP, then the earliest
        # LATER viable day (>= 2 days after when one exists) for anaerobic.
        # This intentionally does NOT apply the long-ride adjacency
        # exclusion used below -- a short anaerobic assessment the day
        # before the long ride is coach-acceptable; wrapping it earlier
        # than the FTP test it depends on is not.
        if available:
            ftp_day = available[0]
            ftp_idx = DAY_ORDER.index(ftp_day)
            later = sorted(
                (d for d in available
                 if d != ftp_day and DAY_ORDER.index(d) > ftp_idx),
                key=lambda d: DAY_ORDER.index(d),
            )
            gapped = [d for d in later if DAY_ORDER.index(d) - ftp_idx >= 2]
            anaerobic_day = (gapped or later or [None])[0]
            intensity_days = [ftp_day] + ([anaerobic_day] if anaerobic_day else [])
            intensity_days = intensity_days[:max(1, max_intensity)]
            for d in intensity_days:
                roles[d] = 'intensity'
    else:
        # Place intensity on available non-consecutive days. Must not be
        # adjacent to other intensity days OR to the long ride day.
        hard_days = [long_ride_day]  # Long ride counts as "hard" for adjacency
        intensity_days = []
        # Explicit coach/athlete-stated interval days (profile
        # availability_roles.interval_days with schedule_constraints.
        # explicit_interval_days) are taken first, in calendar order, and
        # are allowed next to the long ride: the athlete asked for that
        # adjacency (e.g. Tue intervals, Wed long, Thu/Sat easy). R01
        # (no back-to-back INTENSITY days) still holds -- two explicit
        # days that touch each other are reduced to the first.
        for d in sorted((d for d in (preferred_intensity_days or []) if d in DAY_ORDER),
                        key=DAY_ORDER.index):
            if len(intensity_days) >= max_intensity:
                break
            if d in roles or d not in available:
                continue
            # Cyclic adjacency: the weekday template repeats, so an explicit
            # Sunday touches the next Monday (R01 checks across week seams).
            if any(min(abs(DAY_ORDER.index(x) - DAY_ORDER.index(d)),
                       7 - abs(DAY_ORDER.index(x) - DAY_ORDER.index(d))) <= 1
                   for x in intensity_days):
                continue
            intensity_days.append(d)
            hard_days.append(d)
            roles[d] = 'intensity'
        for d in available:
            if len(intensity_days) >= max_intensity:
                break
            d_idx = DAY_ORDER.index(d)
            adjacent_to_hard = any(
                abs(DAY_ORDER.index(existing) - d_idx) <= 1
                for existing in hard_days
            )
            if not adjacent_to_hard:
                intensity_days.append(d)
                hard_days.append(d)
                roles[d] = 'intensity'

    # Step 4: Fill remaining with filler
    for day in DAY_ORDER:
        if day not in roles:
            roles[day] = 'filler'

    return roles


# Matti ruling 2026-09-17 (AE-2.7 amendment): "an hour should be a minimum,
# with the average for a 9-5, ~10 h/wk rider being ~1.5 h on a weekday
# (warm-up and cool-down included)". 35/40/45-minute cards are a defect
# unless the athlete's questionnaire or correspondence explicitly asks for
# short sessions. The old behaviour -- shrinking a session to fit the weekly
# budget or a day cap -- produced stubs like a 32-minute race simulation and
# a 35-minute Tune-Up on a recovery Tuesday. The floor is applied LAST and
# is allowed to overshoot the weekly budget: volume is never the reason to
# ship a pointless card.


def weekday_target_minutes(days: List[Dict[str, Any]], hours_per_week: float,
                           floor_min: int) -> int:
    """What a normal weekday ride should average for this athlete this
    week: the weekly hours left after the long ride, spread over the other
    riding days, clamped to [floor, 2 h]. A 10 h/wk rider with a 3 h long
    ride and four other rides lands at ~105 min."""
    riding = [d for d in days if d.get('duration', 0) > 0
              and d.get('role') not in ('off', 'race', 'rest')
              and d.get('name') != 'Rest Day']
    long_min = max((d.get('duration', 0) for d in riding if d.get('role') == 'long_ride'), default=0)
    others = max(len(riding) - (1 if long_min else 0), 1)
    target = (hours_per_week * 60 - long_min) / others
    return int(max(floor_min, min(WEEKDAY_TARGET_MAX_MIN, round(target))))


def apply_session_floor(days: List[Dict[str, Any]], *, hours_per_week: float,
                        day_caps: Optional[Dict[str, int]] = None,
                        week_type: str = 'load',
                        floor_min: int = SESSION_FLOOR_MIN,
                        grow_to_weekday_target: bool = True,
                        target_scale: float = 1.0,
                        grow_fillers_to_target: bool = False,
                        max_minutes: Optional[float] = None) -> List[str]:
    """Grow every under-floor riding session in place. Returns the names of
    the sessions that were extended (for logging/tests).

    Exempt: off/rest/race days, the race-week Openers (a 40-min opener is
    the point), and any day whose availability cap is itself below the
    floor -- the athlete's stated cap IS the explicit short-session request.
    A session under the floor grows to the weekday target (not merely to
    the floor) when ``grow_to_weekday_target`` is on; the extra minutes are
    modelled as Z2 for TSS and the renderer extends the Z2 portions of the
    session, so the quality set is untouched.
    """
    grown: List[str] = []
    target = floor_min
    if grow_to_weekday_target:
        target = max(floor_min, int(round(weekday_target_minutes(days, hours_per_week, floor_min) * target_scale)))
    # The FLOOR is mandatory and may overshoot the week; growth beyond the
    # floor toward the weekday target spends only what the R19 budget
    # (hours x tolerance) still has room for, so the ratified +-10% hours
    # gate keeps binding.
    headroom = float('inf')
    if max_minutes is not None:
        headroom = max(0.0, float(max_minutes) - sum(x.get('duration', 0) for x in days))
    for d in days:
        dur = d.get('duration', 0)
        if dur <= 0 or d.get('role') in ('off', 'race', 'rest') or d.get('name') == 'Rest Day':
            continue
        if week_type == 'race' and d.get('name') in {'Openers', 'Cadence Work'}:
            continue
        cap = (day_caps or {}).get(d.get('day'), 0) or 0
        if cap and cap < floor_min:
            continue                      # athlete-stated short day
        if d.get('taper_capped'):
            continue                      # taper volume cap permits a sub-floor ride
        d['session_floor_min'] = max(
            floor_min, int(d.get('session_floor_min') or 0))
        # Downstream trims must not go under this floor.
        if dur >= floor_min and not (grow_fillers_to_target and d.get('role') == 'filler' and dur < target):
            continue
        new_dur = target if d.get('role') != 'long_ride' else floor_min
        if cap:
            new_dur = min(new_dur, cap)
        mandatory = max(dur, min(new_dur, floor_min))     # up to the floor: always
        optional = max(0, new_dur - mandatory)             # floor -> target: budgeted
        spend = min(optional, headroom)
        new_dur = mandatory + int(spend)
        if new_dur <= dur:
            continue
        headroom -= max(0.0, new_dur - max(dur, floor_min))
        d['tss'] = round(d.get('tss', 0) + (new_dur - dur) * _Z2_TSS_PER_MIN)
        d['floor_extended_min'] = new_dur - dur
        d['duration'] = new_dur
        grown.append(d.get('name', ''))
    return grown


def _evict_over_budget_fillers(
    days: List[Dict[str, Any]],
    *,
    week_type: str,
    max_minutes: Optional[float],
    floor_min: int,
    day_caps: Optional[Dict[str, int]] = None,
) -> List[str]:
    """Drop disposable fillers without crossing the AE-1.17 lower band."""
    if week_type not in ('taper', 'race') or max_minutes is None:
        return []

    def _floor_duration(day: Dict[str, Any]) -> int:
        duration = int(day.get('duration', 0) or 0)
        if duration <= 0 or day.get('name') == 'Rest Day':
            return 0
        if day.get('taper_capped'):
            return duration
        if week_type == 'race' and day.get('name') in {'Openers', 'Cadence Work'}:
            return duration
        cap = (day_caps or {}).get(day.get('day'), 0) or 0
        if cap and cap < floor_min:
            return duration
        floor = max(floor_min, int(day.get('session_floor_min') or 0))
        return max(duration, floor)

    floored_total = sum(_floor_duration(day) for day in days)
    lower_bound = (
        max_minutes
        * RACE_WEEK_DAILY_LOAD_FRACTION
        / TAPER_DAILY_LOAD_FRACTION
    )
    removed: List[str] = []
    candidates = sorted(
        (
            day for day in days
            if day.get('role') == 'filler'
            and day.get('duration', 0) > 0
            and day.get('name') not in {'Rest Day', 'Stars In Your Eyes', 'Openers'}
            and not day.get('race_week_extended')
        ),
        key=lambda day: (day.get('tss', 0), day.get('day', '')),
    )
    for day in candidates:
        if floored_total <= max_minutes:
            break
        candidate_minutes = _floor_duration(day)
        if floored_total - candidate_minutes < lower_bound:
            break
        floored_total -= candidate_minutes
        removed.append(day.get('name', ''))
        day.update({
            'name': 'Rest Day',
            'level': 1,
            'tss': 0,
            'duration': 0,
            'role': 'filler',
        })
        day.pop('floor_extended_min', None)
        day.pop('session_floor_min', None)
    return removed


def _fit_workout_to_cap(workout: Dict[str, Any], cap: int) -> Dict[str, Any]:
    """Fit a workout to a per-day duration cap.

    Steps the level down until the library duration fits; as a last resort
    hard-caps the duration (the renderer scales the ZWO to match) with TSS
    scaled proportionally. Without this, athletes with '45min weekdays' got
    3-hour Wednesday workouts that only the WEEKLY budget noticed.
    """
    if not cap or cap <= 0 or workout.get('duration', 0) <= cap:
        return workout
    name = workout.get('name', '')
    level = workout.get('level', 1)
    while level > 1:
        level -= 1
        dur = get_workout_duration(name, level)
        if 0 < dur <= cap:
            workout['level'] = level
            workout['duration'] = dur
            workout['tss'] = get_workout_tss(name, level)
            return workout
    orig_dur = workout.get('duration', 0) or 1
    workout['tss'] = round(workout.get('tss', 0) * cap / orig_dur)
    workout['duration'] = cap
    return workout


def trim_week_to_budget(
    days: List[Dict[str, Any]],
    week_type: str,
    hours_per_week: float,
    budget_minutes: Optional[float] = None,
) -> Optional[float]:
    """Shrink-only pass: trim ``days`` in place until total duration fits
    the athlete's weekly-hour budget for this week type.

    Converts fillers to Rest Day first (starting from the end of the
    week), then down-levels the longest intensity/long-ride workout a
    level at a time, then shaves any remainder off the single longest
    remaining session. Never grows a week — callers that also need
    growth (e.g. the grow-to-floor pass in ``_build_week``) do that
    separately and re-call this afterward to correct any overage growth
    reintroduces.

    Budget math must match block_compliance.r19_hours_fit exactly (same
    tolerance breakpoints) so a plan that passes this trim also passes
    the R19 compliance gate.

    Idempotent and safe to call again on a week that was mutated *after*
    an earlier trim pass (e.g. a post-build overlay like
    ``protect_post_simulation_recovery`` reintroducing minutes) — this is
    the only way such overlays stay inside the athlete's stated hours.

    Returns the computed max_minutes budget, or None for week types with
    no budget (mutates nothing in that case).
    """
    if week_type in ('load', 'testing'):
        tolerance = 1.15 if hours_per_week < 6 else 1.10
        max_minutes = hours_per_week * 60 * tolerance
    elif week_type == 'recovery':
        # Preserve enough low-intensity volume to meet the 50-65% recovery
        # TSS floor against the preceding load block.  The old 0.55 cap,
        # combined with Rest-Day pseudo-TSS, emitted closer to 40%.
        max_minutes = hours_per_week * 60 * 0.80
    elif week_type == 'taper':
        max_minutes = hours_per_week * 60 * 0.70
    elif week_type == 'race':
        max_minutes = hours_per_week * 60 * 0.60
    else:
        max_minutes = None

    if max_minutes is None:
        return None
    if budget_minutes is not None and week_type == 'taper':
        max_minutes = min(max_minutes, float(budget_minutes))

    # AE-2.7 (amended 2026-09-17): the weekly budget (R19) still binds, but
    # a session is never shrunk under its floor to meet it -- an over-budget
    # week loses whole filler days (below) before any session gets shorter,
    # and the down-level / shave steps stop at the floor.

    total_duration = sum(d.get('duration', 0) for d in days)
    if total_duration > max_minutes:
        if week_type != 'taper':
            for i in range(len(days) - 1, -1, -1):
                if total_duration <= max_minutes:
                    break
                if days[i]['role'] == 'filler' and days[i]['name'] != 'Rest Day':
                    removed_dur = days[i]['duration']
                    days[i] = {
                        'day': days[i]['day'], 'name': 'Rest Day', 'level': 1,
                        'tss': 0, 'duration': 0, 'role': 'filler',
                    }
                    total_duration -= removed_dur

        # Floor growth is optional volume, the budget is not: give back the
        # weekday-target extension on grown sessions (back to their floor)
        # before any level comes off (2026-09-19: the growth pushed a load
        # week over budget and the loop below levelled the LONG RIDE down to
        # 60 min -- an R06 fail on three golden orders).
        total_duration = sum(d.get('duration', 0) for d in days)
        for d in sorted((x for x in days if x.get('floor_extended_min')),
                        key=lambda x: -int(x.get('floor_extended_min') or 0)):
            if total_duration <= max_minutes:
                break
            ext = int(d.get('floor_extended_min') or 0)
            floor = int(d.get('session_floor_min') or 0)
            give = min(
                ext,
                max(0, int(d.get('duration', 0)) - floor),
                int(total_duration - max_minutes) + 1,
            )
            if give <= 0:
                continue
            d['duration'] = d['duration'] - give
            d['tss'] = max(0, round(d.get('tss', 0) - give * 0.70))
            d['floor_extended_min'] = ext - give
            if d['floor_extended_min'] <= 0:
                d.pop('floor_extended_min', None)
            total_duration -= give

        # Fillers exhausted but still over budget (time-crunched athletes in
        # high-level blocks): step the longest intensity workout down a level
        # at a time; the long ride is levelled only when no intensity day can
        # give, and never under R06's plausible-duration floor (90 min, 60 for
        # athletes under 7 h/wk) -- "long ride every load week" outranks the
        # weekly tolerance band.
        _r06_min = 60 if (hours_per_week and hours_per_week < 7) else 90
        total_duration = sum(d.get('duration', 0) for d in days)
        while total_duration > max_minutes:
            intensity = [d for d in days if d.get('role') == 'intensity' and d.get('level', 1) > 1]
            long_rides = [d for d in days if d.get('role') == 'long_ride' and d.get('level', 1) > 1
                          and week_type == 'load'
                          and get_workout_duration(d['name'], d['level'] - 1) >= _r06_min]
            if week_type != 'load':
                long_rides = [d for d in days if d.get('role') == 'long_ride' and d.get('level', 1) > 1]
            fillers = [
                d for d in days
                if d.get('role') == 'filler'
                and d.get('name') != 'Rest Day'
                and d.get('level', 1) > 1
            ]
            candidates = intensity or long_rides or fillers
            if not candidates:
                break
            longest = max(candidates, key=lambda d: d.get('duration', 0))
            new_level = longest['level'] - 1
            new_dur = get_workout_duration(longest['name'], new_level)
            new_tss = get_workout_tss(longest['name'], new_level)
            if new_dur <= 0:
                # Library gap — treat as unloweable, stop trying this one
                longest['level'] = 1
                continue
            _floor = int(longest.get('session_floor_min') or 0)
            if new_dur < _floor:
                # AE-2.7: down-level the set, keep the day at the floor (Z2)
                new_tss = round(new_tss + (_floor - new_dur) * 0.70)
                longest['floor_extended_min'] = _floor - new_dur
                new_dur = _floor
            else:
                longest.pop('floor_extended_min', None)
            total_duration -= (longest['duration'] - new_dur)
            longest['level'] = new_level
            longest['duration'] = new_dur
            longest['tss'] = new_tss

        # A library can leave a small remainder after every eligible session
        # is at L1 (for example, 397 min against a 396-min budget).  The
        # emitted renderer already supports duration scaling, so trim the
        # longest remaining ride rather than shipping an over-budget week.
        total_duration = sum(d.get('duration', 0) for d in days)
        if total_duration > max_minutes:
            candidates = [d for d in days if d.get('duration', 0) > 0
                          and d.get('name') != 'Rest Day']
            if candidates:
                longest = max(candidates, key=lambda d: d['duration'])
                old_duration = longest['duration']
                _shave_floor = int(longest.get('session_floor_min') or 0)
                if longest.get('role') == 'long_ride' and week_type == 'load':
                    _shave_floor = max(_shave_floor, _r06_min)  # R06 outranks the shave
                new_duration = max(1, _shave_floor,
                                   old_duration - (total_duration - max_minutes))
                longest['duration'] = new_duration
                longest['tss'] = round(longest['tss'] * new_duration / old_duration)

    return max_minutes


def _build_week(
    week_num: int,
    week_type: str,
    phase: str,
    archetype: str,
    day_roles: Dict[str, str],
    base_level: int,
    max_level: int,
    max_intensity: int,
    series_tracker: SeriesTracker,
    week_in_block: int,
    hours_per_week: float = 10,
    block_number: int = 1,
    discipline: str = 'gravel',
    day_caps: Dict[str, int] = None,
    methodology: str = 'polarized_80_20',
    category_weights: Dict[str, float] = None,
    avoid_series: set = None,
    methodology_profile: Dict[str, Any] = None,
    event_format: str = None,
    race_day: Optional[str] = None,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
    session_floor_min: int = SESSION_FLOOR_MIN,
    grow_to_weekday_target: bool = True,
    floor_pct_override: Optional[float] = None,
    taper_budget_minutes: Optional[float] = None,
    taper_long_ride_cap_minutes: Optional[float] = None,
    race_week_target_tss: Optional[float] = None,
    race_week_tss_per_hour: float = 55.0,
) -> Dict[str, Any]:
    """Build a single week with day-by-day workout assignments."""

    # Race day itself still defers to the legacy A-race overlay at render
    # time.  The block builder only supplies the deliberate house shape
    # around it: sharpener, easy endurance, day-before openers, and explicit
    # rest on every other available day.
    if week_type == 'race':
        return _build_race_week(
            week_num=week_num,
            phase=phase,
            off_days=[d for d, role in day_roles.items() if role == 'off'],
            race_day=race_day,
            day_caps=day_caps,
            hours_per_week=hours_per_week,
            athlete_age=athlete_age,
            stress_level=stress_level,
            session_floor_min=session_floor_min,
            target_pre_race_tss=race_week_target_tss,
            tss_per_hour=race_week_tss_per_hour,
        )

    # Get workout menu for this week
    workout_menu = select_workouts_for_week(
        phase=phase,
        archetype=archetype,
        week_type=week_type,
        week_in_block=week_in_block,
        base_level=base_level,
        max_level=max_level,
        max_intensity=max_intensity,
        hours_per_week=hours_per_week,
        block_number=block_number,
        discipline=discipline,
        methodology=methodology,
        category_weights=category_weights,
        avoid_series=avoid_series,
        methodology_profile=methodology_profile,
        event_format=event_format,
    )

    # Organize menu by role
    intensity_workouts = [w for w in workout_menu if w['role'] == 'intensity']
    taper_sharpener = None
    if week_type == 'taper':
        from workout_mapper import calibrate_race_week_sharpener
        taper_sharpener = calibrate_race_week_sharpener(
            requested_level=2, athlete_age=athlete_age,
            stress_level=stress_level)
    long_ride_workout = next((w for w in workout_menu if w['role'] == 'long_ride'), None)
    filler_workout = next((w for w in workout_menu if w['role'] == 'filler'), None)
    rest_workout = next((w for w in workout_menu if w['role'] == 'rest'), None)

    # Assign workouts to days
    days = []
    intensity_idx = 0
    total_tss = 0
    filler_count = 0  # Track filler days for recovery week rest alternation

    for day in DAY_ORDER:
        role = day_roles.get(day, 'filler')
        workout = None

        if role == 'off':
            workout = {'name': 'OFF', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'off'}

        elif role == 'intensity' and intensity_idx < len(intensity_workouts):
            w = intensity_workouts[intensity_idx]
            if week_type == 'taper' and intensity_idx == 0:
                w = {
                    'name': 'Stars In Your Eyes',
                    'level': taper_sharpener['level'],
                    'role': 'intensity',
                    'duration': round(taper_sharpener['duration_min']),
                    'tss': taper_sharpener['tss'],
                    'session_floor_min': round(
                        taper_sharpener['duration_min']),
                }
            elif week_type == 'taper' and intensity_idx > 0:
                w = {
                    'name': 'Cadence Work',
                    'level': 1,
                    'role': 'filler',
                }
            # Track series coherence
            slot = w.get('slot', f'intensity_{intensity_idx + 1}')
            tracked = series_tracker.assign(slot, w['name'], w['level'])
            tracked_level = tracked['level']
            if discipline == 'road':
                # Series coherence can advance a family beyond the level the
                # selector requested. Re-apply the AE-3.1 library bound at the
                # final emitted assignment seam (AE-3.1).
                tracked_level = _road_ae31_level(
                    tracked['name'], tracked_level)
            tss = w.get('tss', get_workout_tss(tracked['name'], tracked_level))
            dur = w.get('duration', get_workout_duration(tracked['name'], tracked_level))
            workout = {
                'name': tracked['name'],
                'level': tracked_level,
                'tss': tss,
                'duration': dur,
                'role': w.get('role', 'intensity'),
                'series_coherent': tracked['coherent'],
            }
            if w.get('session_floor_min') is not None:
                workout['session_floor_min'] = w['session_floor_min']
            intensity_idx += 1

        elif role == 'long_ride' and long_ride_workout:
            w = long_ride_workout
            tss = get_workout_tss(w['name'], w['level'])
            dur = get_workout_duration(w['name'], w['level'])
            workout = {
                'name': w['name'],
                'level': w['level'],
                'tss': tss,
                'duration': dur,
                'role': 'long_ride',
            }

        elif role == 'intensity' and week_type == 'recovery':
            # Recovery week: intensity slots that aren't openers become filler
            w = filler_workout or {'name': 'Endurance', 'level': 1}
            tss = get_workout_tss(w['name'], w['level'])
            dur = get_workout_duration(w['name'], w['level'])
            workout = {
                'name': w['name'], 'level': w['level'],
                'tss': tss, 'duration': dur, 'role': 'filler',
            }

        else:
            # Race week: mostly rest. One easy ride (Wed), rest of filler = Rest Day.
            if week_type == 'race' and filler_count != 1:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'filler'}
            elif week_type == 'race' and filler_count == 1:
                # One easy ride mid-week
                workout = {'name': 'Endurance', 'level': 1, 'tss': 55, 'duration': 50, 'role': 'filler'}
            elif week_type == 'recovery' and filler_count > 0 and filler_count % 3 == 0:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'filler'}
            else:
                w = filler_workout or {'name': 'Endurance', 'level': 1}
                f_name = w['name']
                f_level = w['level']
                # Cycle the filler pool across filler days for variety.
                # Shift the cycle by week so the same weekday doesn't get the
                # same variant every single week.
                pool = w.get('pool')
                if pool and week_type in ('load', 'testing', 'taper'):
                    f_name = pool[(filler_count + week_in_block - 1) % len(pool)]
                    if get_workout_duration(f_name, f_level) <= 0:
                        # Unknown level for this variant — clamp to a level
                        # the library defines, else fall back to Endurance.
                        for try_level in range(min(f_level, 6), 0, -1):
                            if get_workout_duration(f_name, try_level) > 0:
                                f_level = try_level
                                break
                        else:
                            f_name = 'Endurance'
                if f_name == 'Cadence Work' and week_type == 'load':
                    # Cadence is a skill series, not disposable filler: keep
                    # its familiar session but progress one level per load
                    # week (longer work blocks / higher-rpm holds) just like
                    # the named intensity series.
                    f_level = min(f_level + max(0, week_in_block - 1), max_level)
                # The generic Endurance Blocks renderer snaps its component
                # segments to whole minutes and can render one minute longer
                # than its catalog duration.  Do not put that variant exactly
                # on a stated cap; choose the standard Endurance member of the
                # same existing filler pool so the emitted file stays within
                # the athlete's availability, not merely the planner card.
                cap = (day_caps or {}).get(day, 0)
                if (f_name == 'Endurance Blocks' and cap
                        and get_workout_duration(f_name, f_level) >= cap):
                    f_name, f_level = 'Endurance', 1
                tss = get_workout_tss(f_name, f_level)
                dur = get_workout_duration(f_name, f_level)
                workout = {
                    'name': f_name,
                    'level': f_level,
                    'tss': tss,
                    'duration': dur,
                    'role': 'filler',
                }
            filler_count += 1

        # Per-day duration cap (athlete availability). Off days excluded.
        if day_caps and workout.get('role') != 'off' and workout.get('duration', 0) > 0:
            workout = _fit_workout_to_cap(workout, day_caps.get(day, 0))
        if (week_type == 'taper' and workout.get('role') == 'long_ride'
                and taper_long_ride_cap_minutes is not None):
            if workout.get('duration', 0) > taper_long_ride_cap_minutes:
                original_duration = workout['duration']
                workout['duration'] = int(taper_long_ride_cap_minutes)
                workout['tss'] = round(
                    workout['tss'] * workout['duration'] / original_duration)
            workout['taper_capped'] = True
            workout['session_floor_min'] = int(taper_long_ride_cap_minutes)

        total_tss += workout.get('tss', 0)
        days.append({
            'day': day,
            **workout,
        })

    # Post-assignment budget trim: convert filler days to rest (starting
    # from the end) until within budget, then down-level, then shave any
    # remainder. See trim_week_to_budget for the per-week-type budget math
    # (load = hours x 1.10/1.15, recovery x 0.80, taper x 0.70, race x 0.60).
    max_minutes = trim_week_to_budget(
        days, week_type, hours_per_week,
        budget_minutes=taper_budget_minutes)
    total_tss = sum(d.get('tss', 0) for d in days)

    # Grow-to-floor: the trim above only shrinks. Without growth, LOAD
    # weeks for high-volume athletes filled at ~50% of stated hours (a
    # 16h GOAT got 8.2h base weeks). Level UP until the week reaches the
    # floor — long ride first (cheapest quality volume), then fillers —
    # respecting per-day caps and the level ceiling.  The first base block is
    # the deliberate ramp-in unless an explicit schedule owns its floor.
    if (max_minutes is not None and week_type == 'load'
            and not (phase == 'base' and block_number <= 1
                     and floor_pct_override is None)):
        # Phase-aware floor preserves periodized PROGRESSION: base ramps
        # (lower floor, rising per block) while build/peak fill near target.
        # A flat 0.80 floor made W1 as big as W19.
        if floor_pct_override is not None:
            floor_pct = floor_pct_override
        elif phase == 'base':
            floor_pct = min(0.62 + 0.05 * max(block_number - 1, 0), 0.75)
        elif phase == 'build':
            floor_pct = 0.82
        elif phase == 'peak':
            floor_pct = 0.86
        else:
            floor_pct = 0.72
        floor_minutes = hours_per_week * 60 * floor_pct
        total_duration = sum(d.get('duration', 0) for d in days)
        guard = 0
        while total_duration < floor_minutes and guard < 40:
            guard += 1
            candidates = [d for d in days
                          if d.get('role') in ('long_ride', 'filler')
                          and d.get('name') != 'Rest Day'
                          and d.get('level', 1) < max_level]
            # long ride grows before fillers
            candidates.sort(key=lambda d: (d.get('role') != 'long_ride',
                                           d.get('duration', 0)))
            grew = False
            for d in candidates:
                new_level = d['level'] + 1
                new_dur = get_workout_duration(d['name'], new_level)
                new_tss = get_workout_tss(d['name'], new_level)
                if new_dur <= d.get('duration', 0):
                    continue
                cap = (day_caps or {}).get(d['day'], 0)
                if cap and new_dur > cap:
                    continue
                delta = new_dur - d['duration']
                if total_duration + delta > max_minutes:
                    continue
                # don't overshoot the floor by more than 8% — overshoot in
                # base weeks flattened the base->peak volume progression
                if total_duration + delta > floor_minutes * 1.08:
                    continue
                total_duration += (new_dur - d['duration'])
                total_tss += (new_tss - d.get('tss', 0))
                d['level'] = new_level
                d['duration'] = new_dur
                d['tss'] = new_tss
                grew = True
                break
            if not grew:
                break

    # The grow-to-floor pass can land on a floating-point budget boundary
    # (e.g. 396.00000000000006) and reintroduce a one-minute overage. Keep
    # the emitted calendar within the integer-minute availability contract.
    if max_minutes is not None:
        total_duration = sum(d.get('duration', 0) for d in days)
        integer_budget = int(max_minutes)
        if total_duration > integer_budget:
            candidates = [d for d in days if d.get('duration', 0) > 0
                          and d.get('name') != 'Rest Day']
            if candidates:
                longest = max(candidates, key=lambda d: d['duration'])
                old_duration = longest['duration']
                new_duration = max(1, old_duration - (total_duration - integer_budget))
                longest['duration'] = new_duration
                longest['tss'] = round(longest['tss'] * new_duration / old_duration)

    _evict_over_budget_fillers(
        days,
        week_type=week_type,
        max_minutes=(
            taper_budget_minutes
            if taper_budget_minutes is not None else max_minutes
        ),
        floor_min=session_floor_min,
        day_caps=day_caps,
    )

    # AE-2.7 (amended 2026-09-17): the session floor is applied LAST and may
    # overshoot the weekly budget -- see apply_session_floor. Growth to the
    # weekday TARGET is a load-week behaviour; recovery and taper weeks, and
    # the deliberate first-base-block ramp-in, get the floor only so the
    # periodised volume shape (ramp, dip, taper) survives.
    # A recovery week's Z2 fillers grow to the same weekday
    # target) so R03's 50-65% recovery ratio survives the load weeks
    # growing; taper and the first-base-block ramp-in get the floor only.
    _grow = (grow_to_weekday_target and week_type in ('load', 'recovery')
             and not (phase == 'base' and block_number <= 1))
    apply_session_floor(days, hours_per_week=hours_per_week, day_caps=day_caps,
                        week_type=week_type, floor_min=session_floor_min,
                        grow_to_weekday_target=_grow,
                        target_scale=1.0, max_minutes=max_minutes,
                        # recovery Z2 fillers track the (grown) load weeks so
                        # R03's 50-65% ratio holds; nothing hard is added.
                        grow_fillers_to_target=(week_type == 'recovery'))
    # If the floor pushed the week over the R19 budget, the week loses whole
    # filler days (from the end) rather than any session getting shorter --
    # "fewer, longer sessions" is the ruling's intent. Long ride, intensity
    # and the race-week shape are never touched here.
    if max_minutes is not None:
        _total = sum(d.get('duration', 0) for d in days)
        # smallest filler first: a 3% overage must not cost the Sunday ride
        if week_type not in ('taper', 'race'):
            for d in sorted((x for x in days if x.get('role') == 'filler'
                             and x.get('name') != 'Rest Day' and x.get('duration', 0) > 0),
                            key=lambda x: x.get('duration', 0)):
                if _total <= int(max_minutes):
                    break
                _total -= d['duration']
                d.update({'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'filler'})
                d.pop('floor_extended_min', None); d.pop('session_floor_min', None)
    total_tss = sum(d.get('tss', 0) for d in days)

    return {
        'week_num': week_num,
        'week_type': week_type,
        'phase': phase,
        'total_tss': total_tss,
        'total_duration': sum(d.get('duration', 0) for d in days),
        'days': days,
    }


def _build_race_week(
    week_num: int,
    phase: str,
    off_days: List[str],
    race_day: Optional[str],
    day_caps: Optional[Dict[str, int]],
    hours_per_week: float = 10,
    athlete_age: Optional[int] = None,
    stress_level: Optional[str] = None,
    session_floor_min: int = SESSION_FLOOR_MIN,
    target_pre_race_tss: Optional[float] = None,
    tss_per_hour: float = 55.0,
) -> Dict[str, Any]:
    """Build the coach-approved race-week microcycle.

    The race is represented as a zero-load placeholder because the existing
    rendering overlay owns the actual race-day plan.  That keeps the planner
    and renderer responsibilities separate while making every surrounding
    rest day explicit in the calendar model.
    """
    race_day = race_day if race_day in DAY_ORDER else 'Sat'
    race_index = DAY_ORDER.index(race_day)
    # Openers go the day BEFORE the race, never wrapped to Sunday (a Monday
    # race has no eve inside its own week -> no opener). If race eve is
    # unavailable, move the activation to the latest available earlier day
    # instead of dropping it.
    # Prefer race eve. If that day is genuinely unavailable, preserve the
    # athlete's constraint and move the activation to the latest available
    # earlier day instead of silently dropping it from the week.
    pre_race_days = list(reversed(DAY_ORDER[:race_index]))
    opener_day = next(
        (day for day in pre_race_days if day not in off_days), None)

    def _session(name, level, role, duration=None, tss=None):
        duration = get_workout_duration(name, level) if duration is None else duration
        tss = get_workout_tss(name, level) if tss is None else tss
        return {'name': name, 'level': level, 'tss': tss, 'duration': duration, 'role': role}

    # The sharpener is selected as a race-week slot first, then calibrated
    # against the actual rendered ZWO dose.  This avoids relying on a stale
    # library estimate or a single hand-tuned archetype level.
    from workout_mapper import calibrate_race_week_sharpener
    sharpener_dose = calibrate_race_week_sharpener(
        requested_level=2, athlete_age=athlete_age, stress_level=stress_level)

    # Quality-day preference is intentionally the same as the normal week
    # template.  Do not place the sharpener adjacent to day-before openers.
    sharpener_day = next(
        (day for day in ('Tue', 'Thu', 'Mon', 'Wed', 'Fri', 'Sat', 'Sun')
         if day not in off_days and day not in (race_day, opener_day)
         and DAY_ORDER.index(day) < race_index
         and (opener_day is None
              or abs(DAY_ORDER.index(day) - DAY_ORDER.index(opener_day)) > 1)),
        None,
    )
    easy_day = next(
        (day for day in ('Wed', 'Thu', 'Tue', 'Mon', 'Fri', 'Sat', 'Sun')
         if day not in off_days and day not in (race_day, opener_day, sharpener_day)
         and DAY_ORDER.index(day) < race_index),
        None,
    )

    days = []
    for day in DAY_ORDER:
        if day == race_day:
            workout = {'name': 'RACE_DAY', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'race'}
        elif day in off_days:
            workout = {'name': 'OFF', 'level': 0, 'tss': 0, 'duration': 0, 'role': 'off'}
        elif day == opener_day:
            workout = _session('Openers', 2, 'intensity')
        elif day == sharpener_day:
            workout = _session(
                'Stars In Your Eyes', sharpener_dose['level'], 'intensity',
                duration=round(sharpener_dose['duration_min']),
                tss=sharpener_dose['tss'],
            )
        elif day == easy_day:
            # Keep this deliberate middle-of-week ride in the 45-60min house
            # range rather than emitting a normal 70min Endurance L1.
            workout = _session('Endurance', 1, 'filler', duration=50, tss=39)
        else:
            if DAY_ORDER.index(day) < race_index - 1:
                workout = _session(
                    'Cadence Work', 1, 'filler', duration=45, tss=35)
            else:
                workout = {'name': 'Rest Day', 'level': 1, 'tss': 0, 'duration': 0, 'role': 'rest'}

        if day_caps and workout['role'] not in ('off', 'race') and workout['duration'] > 0:
            workout = _fit_workout_to_cap(workout, day_caps.get(day, 0))
        days.append({'day': day, **workout})

    _evict_over_budget_fillers(
        days,
        week_type='race',
        max_minutes=hours_per_week * 60 * 0.60,
        floor_min=session_floor_min,
        day_caps=day_caps,
    )
    apply_session_floor(days, hours_per_week=hours_per_week, day_caps=day_caps, week_type='race',
                        floor_min=session_floor_min, grow_to_weekday_target=False)

    load_shortfall_tss = None
    if target_pre_race_tss is not None:
        pre_race_days = days[:race_index]
        eligible = [
            day for day in pre_race_days
            if day.get('name') in ('Endurance', 'Cadence Work')
            and day.get('role') == 'filler'
            and day.get('duration', 0) > 0
        ]
        current_tss = sum(day.get('tss', 0) for day in pre_race_days)
        deficit = max(0.0, float(target_pre_race_tss) - current_tss)
        capacities = []
        for day in eligible:
            cap = (day_caps or {}).get(day['day'], 90) or 90
            capacities.append(max(0, min(int(cap), 90) - day['duration']))
        total_capacity = sum(capacities)
        if deficit > 0 and total_capacity > 0 and tss_per_hour > 0:
            requested_minutes = deficit * 60 / tss_per_hour
            extension_minutes = min(float(total_capacity), requested_minutes)
            raw_extensions = [
                capacity * extension_minutes / total_capacity
                for capacity in capacities
            ]
            extensions = [int(value) for value in raw_extensions]
            remainder = round(extension_minutes - sum(extensions))
            for index in sorted(
                    range(len(eligible)),
                    key=lambda item: raw_extensions[item] - extensions[item],
                    reverse=True):
                if remainder <= 0:
                    break
                if extensions[index] < capacities[index]:
                    extensions[index] += 1
                    remainder -= 1
            for day, extension in zip(eligible, extensions):
                if extension <= 0:
                    continue
                original_duration = day['duration']
                day['duration'] += extension
                duration_factor = max(
                    1.0, day['duration'] / original_duration)
                day['tss'] = max(
                    day.get('tss', 0),
                    round(day['tss'] * duration_factor),
                    round(day['duration'] * tss_per_hour / 60),
                )
                day['race_week_extended'] = True
            current_tss = sum(day.get('tss', 0) for day in pre_race_days)
        load_shortfall_tss = round(max(0.0, target_pre_race_tss - current_tss), 1)

    result = {
        'week_num': week_num,
        'week_type': 'race',
        'phase': phase,
        'total_tss': sum(d['tss'] for d in days),
        'total_duration': sum(d['duration'] for d in days),
        'days': days,
    }
    if load_shortfall_tss:
        result['load_shortfall_tss'] = load_shortfall_tss
    return result
