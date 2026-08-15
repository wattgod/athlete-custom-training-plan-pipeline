#!/usr/bin/env python3
"""Coach-note rendering for the DeliveryIR projection.

The module is deliberately small and pure: it accepts either PlanIR objects or
their JSON-shaped form, reads the two approved configuration files, and returns
TrainingPeaks-note shaped dictionaries.  It does not publish a guide, inspect
course catalogues, or make network calls.
"""

from __future__ import annotations

import copy
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from delivery_render import (
    _dominant_work_percent,
    build_fuel_ladder,
    has_structured_work,
    load_brand,
    render_hydration_block,
)


_BLOCK_NOTES_PATH = Path(__file__).resolve().parent.parent / "config" / "block_notes.yaml"
_WEEK_TYPE_ALIASES = {
    "base": "medium", "build": "load", "peak": "load", "taper": "recovery",
    "test": "medium", "lead_in": "medium", "race": "race",
}


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _date_text(value: date) -> str:
    return value.isoformat()


def _display_date(value: date) -> str:
    return f"{value.strftime('%A')} {value.day} {value.strftime('%B')}"


def _iter_weeks(plan_ir: Any) -> Iterable[Any]:
    return _get(plan_ir, "weeks", []) or []


def _iter_sessions(plan_ir: Any) -> Iterable[tuple[Any, Any]]:
    for week in _iter_weeks(plan_ir):
        for session in _get(week, "sessions", []) or []:
            yield week, session


def _kind(session: Any) -> str:
    kind = str(_get(session, "tp_kind") or _get(session, "type") or "bike").lower()
    return "day_off" if kind in {"rest", "day_off"} else kind


def _duration_minutes(session: Any) -> int:
    value = _get(session, "duration_s")
    try:
        if value:
            return round(float(value) / 60)
        return round(float(_get(session, "total_time_planned") or 0) * 60)
    except (TypeError, ValueError):
        return 0


def _session_date(session: Any) -> Optional[date]:
    return _as_date(_get(session, "date"))


def _race(plan_ir: Any) -> tuple[Optional[date], Dict[str, Any]]:
    snapshot = _get(plan_ir, "race_snapshot") or {}
    race_day = _as_date(_get(snapshot, "date"))
    if race_day:
        return race_day, snapshot
    for event in _get(plan_ir, "events", []) or []:
        if str(_get(event, "priority") or "").upper() == "A":
            candidate = _as_date(_get(event, "date"))
            if candidate:
                return candidate, snapshot
    for _, session in _iter_sessions(plan_ir):
        if _kind(session) == "race":
            candidate = _session_date(session)
            if candidate:
                return candidate, snapshot
    return None, snapshot


def _first_name(plan_ir: Any) -> str:
    athlete = _get(plan_ir, "athlete") or {}
    supplied = _get(athlete, "first_name")
    if supplied:
        return str(supplied).strip().split()[0]
    name = str(_get(athlete, "name") or "Athlete").strip()
    return name.split()[0] if name else "Athlete"


def _brand(plan_ir: Any, brand_cfg: Any) -> Dict[str, Any]:
    """Resolve a registered brand even when callers pass an already-loaded cfg."""
    if isinstance(brand_cfg, str):
        brand = load_brand(brand_cfg)
        brand["_delivery_key"] = brand_cfg.strip().lower()
        return brand
    configured_key = None
    if isinstance(brand_cfg, dict):
        configured_key = brand_cfg.get("key") or brand_cfg.get("brand")
    configured_key = configured_key or _get(plan_ir, "brand")
    # Existing callers commonly pass ``load_brand('gravelgod')`` which has no
    # key.  Infer it only by exact registry contents, then still go through the
    # canonical loader so unknown brands fail closed.
    if not configured_key and isinstance(brand_cfg, dict):
        for key in ("gravelgod", "roadielabs"):
            if load_brand(key).get("name") == brand_cfg.get("name"):
                configured_key = key
                break
    brand = load_brand(configured_key)
    brand["_delivery_key"] = str(configured_key).lower()
    return brand


def _email(brand: Dict[str, Any]) -> str:
    # The coaching inbox a human answers — never the transactional
    # from-address unless nothing better exists.
    return str(brand.get("coaching_email")
               or (brand.get("email") or {}).get("from_email") or "")


def _load_week_copy() -> Dict[str, str]:
    try:
        with _BLOCK_NOTES_PATH.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"Could not load block notes: {exc}") from exc


def _week_start(week: Any) -> Optional[date]:
    dates = [_session_date(item) for item in (_get(week, "sessions", []) or [])]
    dates = [item for item in dates if item]
    return min(dates) if dates else None


def _monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _week_type(week: Any) -> str:
    raw = str(_get(week, "week_type") or _get(week, "phase") or "medium").lower()
    return _WEEK_TYPE_ALIASES.get(raw, raw)


def _session_title(session: Any) -> str:
    return str(_get(session, "display_name") or _get(session, "title") or "Workout").strip()


_QUALITY_KEYWORDS = (
    "vo2", "threshold", "tempo", "over-under", "test", "opener",
    "interval", "30/15", "stars", "cadence",
)


def _is_quality_session(session: Any) -> bool:
    """Classify quality from emitted facts before falling back to old titles."""
    if _kind(session) != "bike":
        return False
    if _get(session, "is_field_test") or _get(session, "is_simulation"):
        return True
    if (_get(session, "level") not in (None, "") and
            has_structured_work(session) and _dominant_work_percent(session) >= 88):
        return True
    # Older imported plans did not retain level/segment facts. Keep this
    # narrow title fallback so their briefings remain useful.
    return any(token in _session_title(session).lower() for token in _QUALITY_KEYWORDS)


def _quality_sessions(week: Any) -> List[Any]:
    """Return fact-classified key sessions, with simulations after weekday work."""
    # Weekday quality leads, simulations last — a briefing once led with the
    # Saturday surge ride while the actual Thursday key session went unnamed.
    keyed, sims = [], []
    for session in _get(week, "sessions", []) or []:
        if not _is_quality_session(session):
            continue
        if _get(session, "is_simulation"):
            sims.append(session)
        else:
            keyed.append(session)
    return (keyed + sims)[:3]


def _weekly_pattern(plan_ir: Any) -> str:
    # Modal weekdays over TRAINING weeks only. Summing day-offs across the
    # whole plan once told an athlete she had six off days (race week's rest
    # days polluted the set) and listed a quality day twice.
    from collections import Counter
    training_weeks = [w for w in (_get(plan_ir, "weeks", []) or [])
                      if str(_get(w, "phase") or "").lower()
                      in {"base", "build", "peak"}]
    if not training_weeks:
        return "Use the calendar as written. Protect the quality sessions and the long ride."
    off_count: Counter = Counter()
    long_count: Counter = Counter()
    quality_days: Counter = Counter()
    for week in training_weeks:
        bikes = []
        for session in _get(week, "sessions", []) or []:
            day = _session_date(session)
            if not day:
                continue
            if _kind(session) == "day_off":
                off_count[day.strftime("%A")] += 1
            elif _kind(session) == "bike":
                bikes.append((session, day))
        if bikes:
            _, long_day = max(bikes, key=lambda item: _duration_minutes(item[0]))
            long_count[long_day.strftime("%A")] += 1
        for session in _get(week, "sessions", []) or []:
            # The long day is already named in the preceding clause. A race
            # simulation is a key session for its briefing, but should not be
            # presented as a recurring midweek quality-day pattern.
            if not _is_quality_session(session) or _get(session, "is_simulation"):
                continue
            day = _session_date(session)
            if day:
                quality_days[day.strftime("%A")] += 1
    half = len(training_weeks) / 2.0
    off_days = sorted(day for day, count in off_count.items() if count >= half)
    quality = [day for day, _ in quality_days.most_common(2)]
    pieces = []
    if long_count:
        pieces.append(f"{long_count.most_common(1)[0][0]} is the long day and "
                      "the rest of the week protects it")
    if quality:
        pieces.append("quality lands on " + " and ".join(quality))
    if off_days:
        label = "off day is" if len(off_days) == 1 else "off days are"
        pieces.append(f"{label} " + " and ".join(off_days))
    if not pieces:
        return "Use the calendar as written."
    return ". ".join(piece[0].upper() + piece[1:] for piece in pieces) + "."


def _control_metric(plan_ir: Any) -> str:
    athlete = _get(plan_ir, "athlete") or {}
    markers = _get(athlete, "key_markers") or {}
    return str(_get(athlete, "control_metric") or markers.get("control_metric") or
               markers.get("control_basis") or "power").lower()


def _altitude_qualifies(snapshot: Any) -> bool:
    metadata = _get(snapshot, "race_metadata") or {}
    values = []
    for key in ("start_elevation_feet", "avg_elevation_feet", "average_elevation_feet",
                "start_elevation", "avg_elevation"):
        values.append(_get(metadata, key))
    for value in values:
        try:
            if float(value) > 5000:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _eligible_long_rides(plan_ir: Any) -> List[Any]:
    result = []
    race_day, _ = _race(plan_ir)
    for _, session in _iter_sessions(plan_ir):
        session_day = _session_date(session)
        if (_kind(session) == "bike" and session_day and _duration_minutes(session) >= 90 and
                (not race_day or session_day < race_day)):
            result.append(session)
    return sorted(result, key=lambda session: _session_date(session) or date.max)


def _later_event(plan_ir: Any, race_day: Optional[date]) -> Optional[Any]:
    if not race_day:
        return None
    later = [event for event in (_get(plan_ir, "events", []) or [])
             if (_as_date(_get(event, "date")) or date.min) > race_day]
    return min(later, key=lambda event: _as_date(_get(event, "date")) or date.max, default=None)


def _safe_ladder(plan_ir: Any, fueling: Any) -> Dict[str, Any]:
    try:
        return build_fuel_ladder(plan_ir, fueling)
    except ValueError:
        # A fuel prescription may be deferred for coach review.  Notes are an
        # enhancement, never a reason to strand an otherwise renderable order.
        return {}


def schedule_notes(plan_ir: Any, fueling: Any = None) -> List[Dict[str, Any]]:
    """Return collision-aware note anchors, with private rendering context.

    Briefings are allowed to share a day with one other note and always sort
    first. Grit notes move forward around non-briefing coaching notes; anchors
    without their prerequisite simply do not produce a candidate.
    """
    weeks = list(_iter_weeks(plan_ir))
    starts = [_week_start(week) for week in weeks]
    starts = [item for item in starts if item]
    if not starts:
        return []
    plan_start = min(starts)
    race_day, snapshot = _race(plan_ir)
    candidates: List[Dict[str, Any]] = [{"type": "start_here", "date": plan_start}]
    for week in weeks:
        start = _week_start(week)
        if start:
            phase = str(_get(week, "phase") or "").lower()
            if phase in {"pre_plan", "lead_in"}:
                continue  # START HERE covers arrival; no LOAD wall before the plan exists
            candidates.append({"type": "weekly_briefing", "date": _monday(start), "week": week})
    for _, session in _iter_sessions(plan_ir):
        if _get(session, "is_field_test") and _session_date(session):
            candidates.append({"type": "after_test", "date": _session_date(session), "session": session})
    long_rides = _eligible_long_rides(plan_ir)
    if long_rides and _safe_ladder(plan_ir, fueling):
        candidates.append({"type": "fuel_ladder", "date": _session_date(long_rides[0]) - timedelta(days=1)})
    if race_day and _altitude_qualifies(snapshot):
        candidates.append({"type": "altitude_heat", "date": race_day - timedelta(days=17)})
    if race_day:
        grit_dates = [
            _monday(starts[0]),
            plan_start + timedelta(days=max(1, (race_day - plan_start).days // 2)),
            race_day - timedelta(days=10),
            _monday(race_day),
        ]
        for number, when in enumerate(grit_dates, 1):
            candidates.append({"type": f"grit_{number}", "date": max(plan_start, when)})
        candidates.append({"type": "checkin", "date": plan_start + timedelta(days=max(1, (race_day - plan_start).days // 2))})
        candidates.append({"type": "race_week", "date": _monday(race_day)})
        candidates.append({"type": "after_nurture", "date": race_day + timedelta(days=1)})
    for _, session in _iter_sessions(plan_ir):
        if _get(session, "is_dress_rehearsal") and _session_date(session):
            candidates.append({"type": "rehearsal_debrief", "date": _session_date(session) + timedelta(days=1), "session": session})

    # Fixed anchors win ties.  Grit is deliberately last, because it is the
    # only series permitted to slide; briefing can then stack with it.
    order = {"start_here": 0, "weekly_briefing": 1, "after_test": 2, "fuel_ladder": 3,
             "altitude_heat": 4, "checkin": 5, "rehearsal_debrief": 6, "race_week": 7,
             "after_nurture": 8}
    candidates.sort(key=lambda item: (item["date"], order.get(item["type"], 99), item["type"]))
    scheduled: List[Dict[str, Any]] = []
    counts: Dict[date, int] = {}
    nonbriefing: set[date] = set()
    for candidate in candidates:
        when = candidate["date"]
        is_briefing = candidate["type"] == "weekly_briefing"
        is_grit = candidate["type"].startswith("grit_")
        if is_grit:
            while counts.get(when, 0) >= 2 or when in nonbriefing:
                when += timedelta(days=1)
        elif not is_briefing and (counts.get(when, 0) >= 2 or when in nonbriefing):
            # Briefings are the sole same-day companion.  Fixed coaching notes
            # move forward on a collision rather than producing two competing
            # pieces of advice on one day.
            while counts.get(when, 0) >= 2 or when in nonbriefing:
                when += timedelta(days=1)
        elif counts.get(when, 0) >= 2:
            while counts.get(when, 0) >= 2:
                when += timedelta(days=1)
        result = dict(candidate, date=when)
        scheduled.append(result)
        counts[when] = counts.get(when, 0) + 1
        if not is_briefing:
            nonbriefing.add(when)
    return sorted(scheduled, key=lambda item: (item["date"], 0 if item["type"] == "weekly_briefing" else 1, item["type"]))


def _start_here(plan_ir: Any, brand: Dict[str, Any], guide_url: Optional[str]) -> tuple[str, str]:
    race_day, snapshot = _race(plan_ir)
    race_name = str(_get(snapshot, "name") or "your race")
    plan_start = min(_week_start(w) for w in _iter_weeks(plan_ir) if _week_start(w))
    weeks = max(0, math.ceil((race_day - plan_start).days / 7)) if race_day else 0
    guide = (f"\n\n———\n\nYOUR FULL GUIDE\n{guide_url}\n\nRead sections 1 and 2 before the first long ride. The rest keeps."
             if guide_url else "")
    metric = _control_metric(plan_ir)
    if metric in {"power", "ftp", "watts"}:
        reading = "Each workout gives you percentages and RPE. Once your anchor is set, those percentages become your watts."
    elif metric in {"hr", "heart_rate", "lthr", "hrmax"}:
        reading = "Each workout gives you heart-rate bands and RPE. Heart rate lags on climbs and drifts late in a long ride; when it disagrees with RPE, trust RPE."
    else:
        reading = "Each workout gives you an RPE. RPE 3 is easy conversation, 5-6 is controlled work, 7-8 is hard, and 9-10 is reserved for short efforts and tests."
    week_label = "week" if weeks == 1 else "weeks"
    body = (f"{weeks} {week_label} to {race_name}" + (f", {_display_date(race_day)}." if race_day else ".") + guide +
            f"\n\n———\n\nHOW THE WEEK WORKS\n{_weekly_pattern(plan_ir)}\n\nIf a week falls apart, protect the long ride and the first quality session, then let the rest go."
            f"\n\n———\n\nREADING THE WORKOUTS\n{reading}"
            f"\n\n———\n\nNEED THIS ADJUSTED?\nEmail me at {_email(brand)}. Tell me what happened and what you want changed — travel, illness, a session that felt wrong, or a day that no longer works. Adjusting a plan is normal.")
    return f"START HERE — Your {race_name} Plan", body


_SHORT_WEEK_COPY = {
    "load": "Load week — same rules as before: eat more, sleep more, protect the key sessions, and finish the week tired but not destroyed.",
    "uber_load": "The biggest week of the block. Nothing new, everything deliberate.",
    "recovery": "Recovery week — the volume drop is the training. Do not add anything.",
    "medium": "Steady week. Ride what is written.",
}


def _weekly_briefing(plan_ir: Any, candidate: Dict[str, Any], fueling: Any,
                     seen_types: set | None = None) -> tuple[str, str]:
    week = candidate["week"]
    week_number = _get(week, "number", "")
    week_type = _week_type(week)
    phase = str(_get(week, "phase") or week_type or "").strip() or week_type
    # The phase describes the training block, but special calendar weeks are
    # the thing the athlete needs to see at a glance.  A recovery embedded in
    # Base is therefore RECOVERY, not BASE; copy selection still follows the
    # normalized week_type below.
    declared_type = str(_get(week, "week_type") or "").strip().lower()
    special_labels = {
        "recovery": "RECOVERY",
        "taper": "TAPER",
        "race": "RACE WEEK",
    }
    label = special_labels.get(
        declared_type,
        "RACE WEEK" if phase.lower() == "race" else phase.upper().replace("_", " "),
    )
    source = _load_week_copy()
    # The full block-notes wall lands once per week type; repeats get a
    # one-liner (eight identical monk-mode walls is not coaching).
    if seen_types is not None and week_type in seen_types and week_type in _SHORT_WEEK_COPY:
        descriptor = _SHORT_WEEK_COPY[week_type]
    else:
        descriptor = source.get(week_type, source.get("medium", ""))
        if seen_types is not None:
            seen_types.add(week_type)
    quality = _quality_sessions(week)
    sessions = ", ".join(_session_title(session) for session in quality[:3])
    ladder = _safe_ladder(plan_ir, fueling)
    rung = next((ladder.get(str(_get(session, "date")))
                 for session in (_get(week, "sessions", []) or [])
                 if ladder.get(str(_get(session, "date"))) not in (None, "")), None)
    append = (f"\n\nTHIS WEEK'S KEY SESSIONS\n{sessions}." if sessions else "")
    if rung:
        append += f"\n\nFUEL LADDER\nThis week's long ride: {rung} g/hr."
    return f"WEEK {week_number} — {label}", descriptor.strip() + append


def _after_test(plan_ir: Any, brand: Dict[str, Any], session: Any) -> tuple[str, str]:
    text = (" ".join([_session_title(session), str(_get(session, "description") or "")])).lower()
    metric = _control_metric(plan_ir)
    if "20" in text and any(token in text for token in ("ftp", "power", "20-minute", "20 min")):
        instruction = "Take your average power for the 20-minute effort and multiply it by 0.95. That is your FTP. Put it into TrainingPeaks: Settings > Zones > Power."
    elif metric in {"lthr", "hr", "heart_rate"} or "lthr" in text:
        instruction = "Use the sustained heart rate from the protocol as instructed to update your threshold heart rate in TrainingPeaks: Settings > Zones > Heart Rate. Do not turn it into an FTP number."
    elif metric == "hrmax" or "max hr" in text or "hrmax" in text:
        instruction = "Use the highest heart rate reached in the protocol to update your maximum heart rate in TrainingPeaks: Settings > Zones > Heart Rate."
    else:
        instruction = "Keep the RPE and pacing notes from the test. They are the anchor for how the next sessions should feel; no FTP calculation is needed."
    return ("AFTER TODAY'S TEST — Send Me The Number",
            instruction + f"\n\nTHEN SEND IT TO ME\nSend me the number and how it felt — whether you paced it well, had more at the end, or had to stop. {_email(brand)}")


def _fuel_ladder(plan_ir: Any, fueling: Any) -> tuple[str, str]:
    ladder = build_fuel_ladder(plan_ir, fueling)
    rows = []
    for session in _eligible_long_rides(plan_ir):
        session_day = str(_get(session, "date"))
        if session_day in ladder:
            rows.append(
                f"{_display_date(date.fromisoformat(session_day))} — "
                f"{ladder[session_day]} g/hr")
    race_day, _ = _race(plan_ir)
    if race_day and str(race_day) in ladder:
        rows.append(f"Race day — {ladder[str(race_day)]} g/hr")
    body = ("Your gut is trainable and it needs the repetitions, so the target climbs with the long rides rather than appearing on race morning.\n\n" +
            "\n".join(rows) + "\n\nSessions under 90 minutes are not on the ladder. Where an individual workout quotes a different number, use the ladder."
            "\n\n———\n\nWHAT THAT LOOKS LIKE\nRoughly 25-35 g every 25-30 minutes, starting inside the first half hour. Set a timer and read the labels rather than counting items."
            "\n\n———\n\n" + render_hydration_block())
    return "FUELLING — The Ladder", body


_GRIT = {
    1: ("Breathing, And Why It Is First", """The mental side of this gets the same treatment as the physical: a few short things, practised until they are automatic. This is the first.

———

CENTERING YOUR BIOLOGY
Under stress your breathing goes shallow and fast, which tells your nervous system there is a threat, which makes you feel worse, which makes the breathing worse. You can break that loop from either end, and breathing is the end you control.

———

THE 6-2-7 FORMULA
Breathe in for 6, hold for 2, out for 7. The long exhale is the active ingredient — it is what drops your heart rate.

Do it for two minutes before a hard session, and again in the first ten minutes of a race when everything feels too fast. Practise it now, on easy days, so it is available when you need it. A technique you have never rehearsed will not show up on race day."""),
    2: ("You Are Not Your Thoughts", """———

THE CHESS GAME
Somewhere in hour four your brain will offer you: "I can't hold this." "Everyone is stronger than me." "I should have trained more."

You do not have to argue with any of it. Arguing is playing the game. The move is to notice the thought, name it as a thought rather than a fact, and go back to what you were doing — the next ten miles, the next thing to eat.

———

PERFORMANCE STATEMENTS
Have two or three short phrases ready before race day. Not affirmations — instructions. Things like: "Smooth and steady." "Eat now." "Ride your own effort."

Short, specific, actionable. Write them down this week and use them on your long rides, so by race day they are a habit rather than something you are trying for the first time while suffering."""),
    3: ("Your Highlight Reel", """———

BUILD IT NOW
Think of three or four times you rode genuinely well. Not podiums necessarily — the day you held a wheel you did not expect to, the climb that went better than it should have, the ride you finished when you wanted to stop.

Write them down in detail. What you could see, what your legs felt like, what you told yourself.

———

WHY
Confidence is not a mood, it is evidence. When it deserts you at mile 50 you will not be able to conjure it, but you can recall it — and specific, sensory memories are far more usable than a general belief that you are fit.

Read them the night before the race. Run one of them in your head on the start line.

———

WHO YOU ARE ON THE BIKE
One more: finish the sentence "I am the kind of rider who ______" three times. How you describe yourself shapes what you attempt. If everything you write is about surviving, that is worth noticing before race day — you have done the work to say something better."""),
    4: ("The Last Three Days", """———

MUSIC
If music helps you, build the playlist this week rather than on the drive up. Be deliberate: something calm for the morning, something that lifts you for the last hour. What you listen to before a start genuinely shifts how you feel at it — pick accordingly rather than by accident.

———

THE NIGHT BEFORE
Read your highlight reel. Run through your performance statements. Then stop thinking about the race — the work is done and rehearsing it further only costs sleep.

———

ON THE LINE
Two minutes of 6-2-7 breathing. Everyone around you will look faster and more organised than you feel. They are not.

Your first job is to start easier than feels right. Everything after that is eating on time and riding your own effort.

You have done the work. Go and use it."""),
}


def _race_week(plan_ir: Any, brand: Dict[str, Any], guide_url: Optional[str]) -> tuple[str, str]:
    race_day, snapshot = _race(plan_ir)
    race_name = str(_get(snapshot, "name") or "your race")
    distance = _get(snapshot, "distance_miles")
    facts = f"Your entry says {distance:g} miles. " if isinstance(distance, (int, float)) else ""
    altitude = ("\n\nALTITUDE\nThe race starts high enough that familiar power and heart-rate numbers may not behave normally. Ride to RPE, start easier than feels right, and let the day come to you."
                if _altitude_qualifies(snapshot) else "")
    guide = f"\n\nWORTH RE-READING THIS WEEK\nRace Week and Race Day in your guide: {guide_url}" if guide_url else ""
    body = (f"Nothing you do this week adds fitness. Plenty could subtract it. {facts}"
            f"{altitude}\n\nPACING\nFirst third RPE 4-5, middle third RPE 5-6, and spend what is left in the last third. People will come past early. Ride your own effort."
            "\n\nWHEN IT GETS BAD\nBreak what remains into ten-mile pieces and ride the piece you are in. Eat something. Chest pain, confusion, or a headache that keeps building means stop and find a medic."
            "\n\nFRIDAY NIGHT\nBottles mixed. Food in pockets and counted. Kit laid out. Tyres checked. Computer charged. Then stop." + guide +
            f"\n\nANY LAST QUESTIONS\nSend them this week rather than Friday night — {_email(brand)}.")
    return f"RACE WEEK — {race_name}" + (f", {_display_date(race_day)}" if race_day else ""), body


def _render_candidate(plan_ir: Any, fueling: Any, brand: Dict[str, Any], guide_url: Optional[str], candidate: Dict[str, Any], seen_week_types: set | None = None) -> tuple[str, str]:
    kind = candidate["type"]
    if kind == "start_here": return _start_here(plan_ir, brand, guide_url)
    if kind == "weekly_briefing": return _weekly_briefing(plan_ir, candidate, fueling, seen_types=seen_week_types)
    if kind == "after_test": return _after_test(plan_ir, brand, candidate["session"])
    if kind == "fuel_ladder": return _fuel_ladder(plan_ir, fueling)
    if kind == "altitude_heat":
        return ("ALTITUDE AND HEAT — Two Different Problems", "High altitude sun and a changing day can make a familiar effort cost more. Sunscreen before the start, a layer you can carry, and no experiments with heat work this close to the race. Drink to thirst, and add sodium rather than volume when it is hot.")
    if kind.startswith("grit_"):
        number = int(kind.rsplit("_", 1)[1]); prefix = brand.get("mental_skills_name") or ("GRAVEL GRIT" if brand.get("_delivery_key") == "gravelgod" else "MENTAL SKILLS")
        suffix, body = _GRIT[number]
        return f"{prefix} {number} — {suffix}", body.replace("{first_name}", _first_name(plan_ir))
    if kind == "checkin":
        return ("CHECK-IN — How Is It Landing?", "Worth an honest audit:\n\n· Are you finishing the long rides, or surviving them?\n· Is your sleep holding up?\n· Is anything hurting that was not hurting three weeks ago?\n· Are you looking forward to riding, or dreading it?\n\nTwo or more of those pointing the wrong way and we should take something out now rather than later.\n\nNEED THIS ADJUSTED?\nEmail me at " + _email(brand) + ".")
    if kind == "rehearsal_debrief":
        return ("REHEARSAL DEBRIEF — Write It Down And Send It", "While yesterday is still fresh, note:\n\n· What you ate and when. Did you hit the target, or drift?\n· What your stomach did late in the ride.\n· What chafed, rubbed, went numb or ached.\n· What you ran out of.\n· How the last hour felt, honestly.\n· What you would change about pacing.\n\nSend it to me. There is enough time to fix kit, fuelling and pacing — but only if we know what broke.\n\n" + _email(brand))
    if kind == "race_week": return _race_week(plan_ir, brand, guide_url)
    if kind == "after_nurture":
        later = _later_event(plan_ir, _race(plan_ir)[0])
        bridge = (f"\n\n{_get(later, 'name')} is next. We can use what this race taught us to build the bridge into it." if later else "\n\nWhen you are ready, we can talk about the next block or coaching.")
        return ("AFTER — Tell Me How It Went", "Nothing today. Eat, drink, sleep.\n\nIf the legs feel stiff tomorrow, thirty minutes of easy spinning helps more than sitting still. Otherwise take the week easy and let it land.\n\nWhen you have had a day to think about it, send me your race notes: what worked, what you would change, what surprised you, and what you want to do next. That is what the next plan gets built on." + bridge + "\n\n" + _email(brand))
    raise ValueError(f"Unknown note type: {kind}")


def render_notes(plan_ir: dict, fueling: dict, brand_cfg: dict, guide_url: str | None) -> List[Dict[str, str]]:
    """Render ordered ``{date, type, title, body}`` note entries for one plan."""
    brand = _brand(plan_ir, brand_cfg)
    notes = []
    seen_week_types: set = set()
    for candidate in schedule_notes(plan_ir, fueling):
        title, body = _render_candidate(
            plan_ir, fueling, brand, guide_url, candidate,
            seen_week_types=seen_week_types)
        notes.append({"date": _date_text(candidate["date"]), "type": candidate["type"], "title": title, "body": body})
    return notes
