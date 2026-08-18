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
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from delivery_render import (
    _dominant_work_percent,
    build_fuel_ladder,
    has_structured_work,
    load_brand,
    render_card_name,
    render_hydration_block,
    render_session_name,
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
    return render_session_name(session)


_QUALITY_KEYWORDS = (
    "vo2", "threshold", "tempo", "over-under", "test", "opener",
    "interval", "30/15", "stars", "cadence",
)


_SKILLS_ARCHETYPES = {"cadence work"}

_TITLE_RPE_RE = re.compile(r"RPE\s*(\d{1,2})", re.I)


def _authored_rpe_at_least(session: Any, threshold: int) -> bool:
    """Whether the session's own carried RPE fact meets/exceeds threshold.

    Checks the curated library's authored RPE token (``library_rpe_text``,
    the coach's own call -- see delivery_render._authored_rpe_token) as well
    as a literal ``RPE\\d`` in the session's display_name/title, so both
    library-resolved and hand-authored sessions are covered.
    """
    carried = str(_get(session, "library_rpe_text") or "").strip()
    text = " ".join(filter(None, [
        f"RPE{carried}" if carried else "",
        str(_get(session, "display_name") or ""),
        str(_get(session, "title") or ""),
    ]))
    match = _TITLE_RPE_RE.search(text)
    if not match:
        return False
    try:
        return int(match.group(1)) >= threshold
    except ValueError:
        return False


def _is_quality_session(session: Any) -> bool:
    """Classify quality from emitted facts before falling back to old titles."""
    if _kind(session) != "bike":
        return False
    if _get(session, "is_field_test") or _get(session, "is_simulation"):
        return True
    # R01: cadence/skills archetypes are classified by role, not by their
    # sub-threshold work percent — as fillers they are easy days and must
    # not read as a standing quality day in athlete-facing notes.
    if str(_get(session, "archetype_id") or "").strip().lower() in _SKILLS_ARCHETYPES:
        return False
    # FIX 3/4 (Aug 17 2026 adversarial grade): the dominant-work check used
    # to be gated behind `level`, a field only synthesized-plan sessions
    # carry. A real curated "Ronnestad 30-15" (IF .78-.80, RPE8-9) has no
    # `level` and its hyphenated title matched none of the slash-formatted
    # _QUALITY_KEYWORDS below, so it silently fell out of both the weekly
    # pattern (FIX 3) and the key-session briefing (FIX 4) -- the same gap
    # _race_week_is_key_session already worked around for race week alone.
    # Any bike session with dominant work >=88% FTP, or an authored RPE>=8,
    # is quality regardless of whether `level` is present.
    if has_structured_work(session) and _dominant_work_percent(session) >= 88:
        return True
    if _authored_rpe_at_least(session, 8):
        return True
    # Older imported plans did not retain level/segment facts. Keep this
    # narrow title fallback so their briefings remain useful.
    return any(token in _session_title(session).lower() for token in _QUALITY_KEYWORDS)


def _race_week_is_key_session(session: Any) -> bool:
    """Race week must walk EVERY intensity-role bike session in its note.

    Root cause of a real defect: _is_quality_session's dominant-power check
    is gated behind a ``level`` field that only synthesized-plan sessions
    carry — a real "Glycolytic Power - 6x60s @145% - RPE8-9" Monday
    sharpener with no ``level`` attribute failed that gate (and its curated
    name matched none of _QUALITY_KEYWORDS either), silently dropping it
    from the note while a Wed sharpener and Fri openers got named. Race
    week's job is honesty about every hard day, so the dominant-power check
    applies here without the ``level`` gate.
    """
    if _kind(session) != "bike":
        return False
    if has_structured_work(session) and _dominant_work_percent(session) >= 88:
        return True
    return _is_quality_session(session)


def _ordered_sessions(week: Any) -> List[Any]:
    """Return the calendar's sessions in date order, retaining input order for ties."""
    indexed = enumerate(_get(week, "sessions", []) or [])
    return [session for _, session in sorted(
        indexed, key=lambda item: (_session_date(item[1]) or date.max, item[0]))]


def _is_taper_week(week: Any) -> bool:
    return any(str(_get(week, name) or "").strip().lower() == "taper"
               for name in ("week_type", "phase"))


def _is_recovery_week(week: Any) -> bool:
    return any(str(_get(week, name) or "").strip().lower() == "recovery"
               for name in ("week_type", "phase"))


def _is_race_week(week: Any) -> bool:
    return any(str(_get(week, name) or "").strip().lower() == "race"
               for name in ("week_type", "phase"))


def _taper_specialty(session: Any) -> Optional[str]:
    """Return the taper-specific stimulus a session protects in the briefing.

    Titles are the durable delivery fact for imported and freshly-built plans;
    the 30/15 structure check covers plans whose title has been localized or
    otherwise renamed after generation.
    """
    if _kind(session) != "bike":
        return None
    # Names and archetype only — NEVER the description. A plain endurance
    # ride whose description carries a "Cadence: 85-95rpm" line must not
    # classify as taper cadence work (description-grep disease).
    text = " ".join(str(_get(session, name) or "") for name in (
        "title", "display_name", "archetype_id", "workout_type",
    )).lower()
    def _is_thirty_fifteen(segment: Any) -> bool:
        try:
            return (str(_get(segment, "kind") or "").lower() == "intervals" and
                    int(_get(segment, "on_seconds") or 0) == 30 and
                    int(_get(segment, "off_seconds") or 0) == 15)
        except (TypeError, ValueError):
            return False

    if (re.search(r"\b(?:thirty[- ]?fifteens?|30\s*[-/]\s*15)\b", text) or
            any(_is_thirty_fifteen(segment)
                for segment in (_get(session, "segments", []) or []))):
        return "sharpness"
    if re.search(r"\b(?:cadence|neuromuscular|microbursts?|stomps?)\b", text):
        return "cadence"
    if re.search(r"\bbursts?\b", text):
        # Name alone is not enough WHEN segments are available: a "FatMax
        # Development" ride (archetype family name carries "bursts") once
        # classified here at RPE2-3 with zero hard content, and the taper
        # briefing promised "bursts from" a plain endurance ride. With
        # emitted segments, require actual >=92% work; without them
        # (imported/renamed plans), the title stays the durable fact.
        segments = _get(session, "segments", []) or []
        if not segments:
            return "bursts"
        for segment in segments:
            on_power = _get(segment, "on_power") or 0
            power = _get(segment, "power") or 0
            hi = _get(segment, "power_high") or 0
            if max(float(on_power or 0), float(power or 0), float(hi or 0)) >= 0.92:
                return "bursts"
        return None
    return None


def _quality_sessions(week: Any) -> List[Any]:
    """Return a concise, calendar-ordered key-session list for one week.

    Tests and simulations are protected facts: they are never dropped because
    they land on a weekend or because a dress rehearsal shares a week with a
    shorter simulation. Taper specialty sessions are protected for the same
    reason. In an unusual week where protected sessions alone exceed four,
    honesty wins over the approximate four-item cap.
    """
    sessions = _ordered_sessions(week)
    protected = [
        session for session in sessions
        if (_get(session, "is_field_test") or _get(session, "is_simulation") or
            (_is_taper_week(week) and _taper_specialty(session)) or
            (_is_race_week(week) and _race_week_is_key_session(session)))
    ]
    selected_ids = {id(session) for session in protected}
    # A normal week still reads quickly: two conventional weekday quality
    # sessions are enough once the protected facts have been named. Taper
    # specialty work already tells that week's story, so it needs no filler.
    # Race week is protected the same way -- every intensity-role bike
    # session in it is already in `protected` above.
    added_quality = 0
    for session in sessions:
        session_day = _session_date(session)
        if (_is_taper_week(week) or _is_race_week(week) or added_quality >= 2 or
                id(session) in selected_ids or
                not _is_quality_session(session) or not session_day or
                session_day.weekday() >= 5):
            continue
        protected.append(session)
        selected_ids.add(id(session))
        added_quality += 1
    return [session for session in sessions if id(session) in selected_ids]


def _briefing_session_title(session: Any) -> str:
    """Name key sessions exactly as the calendar does, flagging rehearsals."""
    title = render_card_name(session)
    if _get(session, "is_dress_rehearsal") and "dress rehearsal" not in title.lower():
        return f"Dress rehearsal — {title}"
    return title


def _session_reference(session: Any) -> str:
    """Render a prose-ready, fact-only reference to an emitted session."""
    title = _briefing_session_title(session)
    duration = _duration_minutes(session)
    day = _session_date(session)
    detail = f"{duration}-minute {title}" if duration else title
    return f"{day.strftime('%A')}'s {detail}" if day else detail


def _join_references(references: List[str]) -> str:
    if len(references) < 2:
        return references[0] if references else ""
    if len(references) == 2:
        return " and ".join(references)
    return ", ".join(references[:-1]) + f", and {references[-1]}"


def _week_sequence(week: Any, key_sessions: List[Any]) -> str:
    """Explain the week's order, walking EVERY key session.

    The branch prose leads with the week's defining shape; any keyed
    session it didn't mention gets an explicit closing reference — a key
    list that names a session the sequence never walks reads as a
    forgotten one.
    """
    sentence = _week_sequence_base(week, key_sessions)
    missing = [session for session in key_sessions
               if _kind(session) == "bike"
               and _briefing_session_title(session).split(" (")[0] not in sentence]
    if missing:
        refs = _join_references([_session_reference(session) for session in missing])
        verb = "rounds" if len(missing) == 1 else "round"
        sentence = f"{sentence} {refs} {verb} out the week's key work."
    return sentence


def _week_sequence_base(week: Any, key_sessions: List[Any]) -> str:
    """Explain the actual week's order without inventing a stock schedule."""
    sessions = _ordered_sessions(week)
    tests = [session for session in sessions if _get(session, "is_field_test")]
    # "Rehearsal" language belongs only to the Act-class simulations (the
    # numbered long sims and the dress rehearsal). A curated midweek
    # race_sim touch ("Peak and Fade") is a sharpener — pooling it under
    # the same word once briefed it as a co-equal rehearsal beside the
    # actual dress rehearsal.
    simulations = [session for session in sessions
                   if _get(session, "is_simulation")
                   and (_get(session, "is_dress_rehearsal")
                        or "act" in str(_get(session, "display_name")
                                        or _get(session, "title") or "").lower())]
    sim_touches = [session for session in sessions
                   if _get(session, "is_simulation")
                   and session not in simulations]
    specialties = [(session, _taper_specialty(session)) for session in sessions
                   if _is_taper_week(week) and _taper_specialty(session)]
    test_ids = {id(session) for session in tests}
    simulation_ids = {id(session) for session in simulations} | {
        id(session) for session in sim_touches}
    specialty_ids = {id(session) for session, _ in specialties}
    protected_ids = test_ids | simulation_ids | specialty_ids
    quality = [session for session in key_sessions
               if id(session) not in protected_ids]
    bikes = [session for session in sessions if _kind(session) == "bike"]
    long_candidate = max(bikes, key=_duration_minutes) if bikes else None
    # Only a genuine base/build/peak load week earns the "long ride" label,
    # and only when the actual longest bike session is at least 90min.
    # Recovery weeks trim volume by design (a 70min Endurance ride is not
    # "the long ride"); race week replaces the long ride with a sharpener
    # (Stars In Your Eyes is not "the long ride" either). week_type is
    # checked first because a recovery/taper/race week can carry the
    # surrounding block's phase (e.g. phase=base, week_type=recovery).
    week_type_norm = str(_get(week, "week_type") or "").strip().lower()
    phase_norm = str(_get(week, "phase") or "").strip().lower()
    is_load_shaped_week = (week_type_norm not in ("recovery", "taper", "race")
                           and phase_norm not in ("recovery", "taper", "race"))
    long_ride = (long_candidate
                if long_candidate and is_load_shaped_week
                and _duration_minutes(long_candidate) >= 90
                else None)

    if tests:
        test_refs = _join_references([_session_reference(session) for session in tests])
        noun = "test" if len(tests) == 1 else "tests"
        sentence = f"{test_refs} {'is' if len(tests) == 1 else 'are'} this week's {noun}."
        if simulations:
            sim_refs = _join_references([_session_reference(session) for session in simulations])
            rehearsal = "rehearsal" if len(simulations) == 1 else "rehearsals"
            sentence += f" {sim_refs} {'is' if len(simulations) == 1 else 'are'} the {rehearsal}."
        elif long_ride and long_ride not in tests:
            sentence += f" {_session_reference(long_ride)} is the long ride."
        return sentence

    if _is_taper_week(week) and specialties:
        by_kind: Dict[str, List[str]] = {}
        for session, specialty in specialties:
            by_kind.setdefault(str(specialty), []).append(_session_reference(session))
        pieces = []
        if by_kind.get("sharpness"):
            pieces.append(f"sharpness from {_join_references(by_kind['sharpness'])}")
        if by_kind.get("cadence"):
            pieces.append(f"cadence from {_join_references(by_kind['cadence'])}")
        if by_kind.get("bursts"):
            pieces.append(f"bursts from {_join_references(by_kind['bursts'])}")
        return "This taper keeps " + _join_references(pieces) + "."

    if simulations or sim_touches:
        parts = []
        if quality:
            parts.append(f"{_session_reference(quality[0])} carries this week's structured work")
        if sim_touches:
            touch_refs = _join_references([_session_reference(s) for s in sim_touches])
            parts.append(f"{touch_refs} sharpens the race shape")
        if simulations:
            sim_refs = _join_references([_session_reference(s) for s in simulations])
            parts.append(f"{sim_refs} {'is' if len(simulations) == 1 else 'are'} the "
                         f"{'rehearsal' if len(simulations) == 1 else 'rehearsals'}")
        return "; ".join(parts) + "."

    if str(_get(week, "week_type") or "").strip().lower() == "race":
        # Race week walks EVERY key session by day and duration — the
        # sharpener and the day-before openers are both part of the story.
        refs = [_session_reference(session) for session in key_sessions
                if _kind(session) == "bike"]
        if refs:
            return (f"{_join_references(refs)} keep the legs sharp without "
                    "adding fatigue. The remaining rides stay easy — freshness "
                    "is the work this week.")

    if _is_recovery_week(week):
        # Describe the week's actual job rather than inheriting the
        # base/build/peak "carries structured work ... is the long ride"
        # phrasing, which mislabelled a 70min recovery-week Endurance ride
        # as "the long ride". A recovery week can still carry a genuine long
        # ride (90min+, same threshold _eligible_long_rides uses for the
        # FUEL LADDER section) -- it was going unnamed here even when it
        # was the week's single biggest session, contradicting the ladder's
        # own "this week's long ride" reference a few paragraphs later.
        recovery_long_ride = (long_candidate
                              if long_candidate and _duration_minutes(long_candidate) >= 90
                              else None)
        sentence = "This is a recovery week: easy volume through the week"
        if quality:
            sentence += f", plus {_session_reference(quality[0])} to keep the legs sharp"
        sentence += "."
        if recovery_long_ride:
            sentence += (f" {_session_reference(recovery_long_ride)} stays strictly "
                         "Z2 — long but easy is the assignment.")
        return sentence

    if quality and long_ride:
        quality_refs = _join_references([_session_reference(session) for session in quality[:2]])
        verb = "carries" if len(quality[:2]) == 1 else "carry"
        return (f"{quality_refs} {verb} this week's structured work. "
                f"{_session_reference(long_ride)} is the long ride.")
    if quality:
        return f"{_session_reference(quality[0])} carries this week's structured work."
    if long_ride:
        return f"{_session_reference(long_ride)} is the week's longest ride."
    return ""


def _training_weeks(plan_ir: Any) -> List[Any]:
    return [w for w in (_get(plan_ir, "weeks", []) or [])
           if str(_get(w, "phase") or "").lower() in {"base", "build", "peak"}]


def _modal_off_days(plan_ir: Any) -> List[str]:
    """Weekday names that recur as an off day in at least half of the plan's
    base/build/peak training weeks -- the plan's standing rest-day pattern.
    Recovery/taper/race weeks are excluded so an extra rest day they add
    doesn't get baked into the "normal week" pattern."""
    from collections import Counter
    training_weeks = _training_weeks(plan_ir)
    if not training_weeks:
        return []
    off_count: Counter = Counter()
    for week in training_weeks:
        for session in _get(week, "sessions", []) or []:
            day = _session_date(session)
            if day and _kind(session) == "day_off":
                off_count[day.strftime("%A")] += 1
    half = len(training_weeks) / 2.0
    return sorted(day for day, count in off_count.items() if count >= half)


def _weekly_pattern(plan_ir: Any) -> str:
    # Modal weekdays over TRAINING weeks only. Summing day-offs across the
    # whole plan once told an athlete she had six off days (race week's rest
    # days polluted the set) and listed a quality day twice.
    from collections import Counter
    training_weeks = _training_weeks(plan_ir)
    if not training_weeks:
        return "Use the calendar as written. Protect the quality sessions and the long ride."
    long_count: Counter = Counter()
    quality_days: Counter = Counter()
    for week in training_weeks:
        bikes = []
        for session in _get(week, "sessions", []) or []:
            day = _session_date(session)
            if not day:
                continue
            if _kind(session) == "bike":
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
    off_days = _modal_off_days(plan_ir)
    # A standing pattern needs to RECUR: a day only counts if it carries
    # quality in at least half the training weeks — one-off tests and
    # floating cadence placements belong in their weekly briefings, not in
    # START HERE's description of a normal week.
    quality = [day for day, count in quality_days.most_common(2)
               if count >= max(2, half)]
    pieces = []
    if long_count:
        pieces.append(f"{long_count.most_common(1)[0][0]} is the long day and "
                      "the rest of the week protects it")
    if quality:
        pieces.append("quality lands on " + " and ".join(quality))
    if off_days:
        label = "off day is" if len(off_days) == 1 else "off days are"
        # Blanket "off day is Tuesday" once read as an unconditional rule --
        # recovery/taper weeks deliberately add a second rest day, and the
        # weekly briefing calls that out per-week (see _weekly_briefing).
        # This caveat softens the standing pattern so it doesn't read as a
        # promise every week keeps.
        pieces.append(f"{label} " + " and ".join(off_days) +
                      " (recovery and taper weeks may add a second rest day)")
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
                # Monika's calendar opens with a WEEK 0 note; the lead-in
                # deserves its own framing, not silence under START HERE.
                candidates.append({"type": "week_zero", "date": _monday(start), "week": week})
                continue
            candidates.append({"type": "weekly_briefing", "date": _monday(start), "week": week})
    for _, session in _iter_sessions(plan_ir):
        if _get(session, "is_field_test") and _session_date(session):
            candidates.append({"type": "after_test", "date": _session_date(session), "session": session})
    long_rides = _eligible_long_rides(plan_ir)
    if long_rides and _safe_ladder(plan_ir, fueling):
        candidates.append({"type": "fuel_ladder", "date": _session_date(long_rides[0]) - timedelta(days=1)})
    if race_day and _altitude_qualifies(snapshot):
        candidates.append({"type": "altitude_heat", "date": race_day - timedelta(days=17)})
    # A plan that schedules heat-acclimation work gets the doctrine note the
    # day before that session — derived from a plan fact, not a race guess.
    heat_session = next(
        (session for _, session in _iter_sessions(plan_ir)
         if "heat acclimation" in str(_get(session, "display_name")
                                      or _get(session, "archetype_id") or "").lower()),
        None)
    if heat_session and _session_date(heat_session):
        candidates.append({"type": "heat_prep",
                           "date": _session_date(heat_session) - timedelta(days=1)})
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
    # Strength sits ON TOP of riding hours, not inside them — say so up
    # front, or the athlete adds up a peak week and thinks the plan broke
    # its own hours promise.
    has_strength = any(_kind(session) == "strength"
                       for _, session in _iter_sessions(plan_ir))
    hours_note = ("\n\nBig weeks run to the top of your riding hours; the "
                  "strength sessions you asked for sit on top of that, not "
                  "inside it." if has_strength else "")
    # Masters athletes should see that the plan's recovery architecture is
    # deliberate for THEIR physiology, not generic-adult defaults -- a
    # graded review found zero age-aware language on a 52-year-old's
    # calendar. One line, factual, no pandering.
    age = _get(_get(plan_ir, "athlete") or {}, "age")
    masters_note = ""
    if age is not None and int(age) >= 50:
        # Plurality follows the plan's own count of declared recovery weeks
        # (taper is a distinct declared_type -- a sharpening week, not a
        # recovery week -- and is deliberately excluded here). And only the
        # FTP test carries an enforced easy lead-in day under the 360
        # testing-week protocol; the Thursday anaerobic test's Wednesday is
        # a tempo ride, not an easy day.
        recovery_week_count = sum(
            1 for w in _iter_weeks(plan_ir)
            if str(_get(w, "week_type") or "").strip().lower() == "recovery"
        )
        recovery_phrase = ("the full recovery week" if recovery_week_count == 1
                           else "the full recovery weeks")
        masters_pieces = [recovery_phrase,
                          "the easy day before every FTP test"]
        if has_strength:
            masters_pieces.insert(0, "the strength work")
        masters_note = ("\n\nBuilt for recovery at " + str(int(age)) + ": "
                        + ", ".join(masters_pieces[:-1]) + " and "
                        + masters_pieces[-1]
                        + " are load-bearing at your age, not optional extras. "
                          "Skip a hard day before you ever skip recovery.")
    body = (f"{weeks} {week_label} to {race_name}" + (f", {_display_date(race_day)}." if race_day else ".") + guide +
            f"\n\n———\n\nHOW THE WEEK WORKS\n{_weekly_pattern(plan_ir)}{hours_note}{masters_note}\n\nIf a week falls apart, protect the long ride and the first quality session, then let the rest go."
            f"\n\n———\n\nREADING THE WORKOUTS\n{reading}"
            f"\n\n———\n\nNEED THIS ADJUSTED?\nEmail me at {_email(brand)}. Tell me what happened and what you want changed — travel, illness, a session that felt wrong, or a day that no longer works. Adjusting a plan is normal.")
    return f"START HERE — Your {race_name} Plan", body


_SHORT_WEEK_COPY = {
    "load": "Load week — same rules as before: eat more, sleep more, protect the key sessions, and finish the week tired but not destroyed.",
    "uber_load": "The biggest week of the block. Nothing new, everything deliberate.",
    "recovery": "Recovery week — the volume drop is the training. Do not add anything.",
    # _week_type() aliases "taper" -> "recovery" for wall-copy sharing (no
    # dedicated taper entry exists in block_notes.yaml), which once let a
    # WEEK 7 TAPER briefing open with this same "Recovery week —" line --
    # a taper is a sharpening week, not a recovery week, and needs its own
    # short-form wording even though it shares the recovery family's full
    # wall. Selected by `declared_type`, not the aliased `week_type` --
    # see _weekly_briefing.
    "taper": "Taper — the volume drop is the training. This is not a recovery week; it is a sharpening week.",
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
    # one-liner (eight identical monk-mode walls is not coaching). Taper
    # shares the "recovery" family's wall/seen-types bucket (week_type is
    # aliased above), but gets its own one-liner keyed by declared_type so
    # it never reuses the mid-plan "Recovery week —" phrasing.
    short_copy_key = "taper" if declared_type == "taper" else week_type
    if seen_types is not None and week_type in seen_types and short_copy_key in _SHORT_WEEK_COPY:
        descriptor = _SHORT_WEEK_COPY[short_copy_key]
    else:
        descriptor = source.get(week_type, source.get("medium", ""))
        if seen_types is not None:
            seen_types.add(week_type)
    quality = _quality_sessions(week)
    sessions = ", ".join(_briefing_session_title(session) for session in quality)
    sequence = _week_sequence(week, quality)
    ladder = _safe_ladder(plan_ir, fueling)
    week_sessions = _get(week, "sessions", []) or []
    # Cite the rate the ladder pins for the week's LONGEST ride, not merely
    # the first session in sessions-list order (that could be a Saturday
    # filler ride, leaving Sunday's actual long ride quoting the wrong rung).
    week_bikes = [session for session in week_sessions if _kind(session) == "bike"]
    longest_bike = max(week_bikes, key=_duration_minutes) if week_bikes else None
    rung = (ladder.get(str(_get(longest_bike, "date")))
            if longest_bike is not None else None)
    if rung in (None, ""):
        rung = next((ladder.get(str(_get(session, "date")))
                     for session in week_sessions
                     if ladder.get(str(_get(session, "date"))) not in (None, "")), None)
    append = (f"\n\nTHIS WEEK'S KEY SESSIONS\n{sessions}." if sessions else "")
    if sequence:
        append += f"\n\nTHE WEEK IN SEQUENCE\n{sequence}"
    if rung:
        append += f"\n\nFUEL LADDER\nThis week's long ride: {rung} g/hr."
    # START HERE describes the plan's standing off-day pattern; a week whose
    # actual off-day set adds to it (recovery/taper commonly add a Saturday)
    # should say so explicitly rather than silently deviating from what the
    # athlete was told to expect. A rest day on or after race day is an
    # automatic recovery day, not a scheduling decision -- it must never be
    # named in this "that's deliberate" callout (race week's Sunday-after-
    # the-race once got called out alongside a genuinely-added Thursday).
    race_day, _ = _race(plan_ir)
    week_off_days = sorted({
        day.strftime("%A") for day in
        (_session_date(session) for session in week_sessions if _kind(session) == "day_off")
        if day and not (race_day and day >= race_day)
    })
    extra_off_days = [day for day in week_off_days if day not in _modal_off_days(plan_ir)]
    if extra_off_days:
        noun = "rest day" if len(extra_off_days) == 1 else "rest days"
        article = "a " if len(extra_off_days) == 1 else ""
        append += (f"\n\nThis week adds {article}" + " and ".join(extra_off_days) +
                  f" {noun} — that's deliberate.")
    return f"WEEK {week_number} — {label}", descriptor.strip() + append


def _after_test(plan_ir: Any, brand: Dict[str, Any], session: Any) -> tuple[str, str]:
    # Dispatch on the session NAME, not the description: an anaerobic test's
    # description contains "20x0:30" and "120% FTP", which once matched the
    # FTP branch and told the athlete to compute FTP from a repeatability test.
    name = " ".join(str(_get(session, field) or "") for field in
                    ("title", "display_name", "archetype_id")).lower()
    text = (" ".join([_session_title(session), str(_get(session, "description") or "")])).lower()
    metric = _control_metric(plan_ir)
    if "anaerobic" in name:
        instruction = ("Record three things: your best 10-second peak power, your 1-minute average power, and the fade across the 30/30s (first five vs last five average; (first-last)/first x 100). No FTP math today — this test measures repeatability, not threshold.")
    elif ("ftp" in name or "threshold" in name) or ("20" in text and any(token in text for token in ("ftp", "power", "20-minute", "20 min"))):
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
    return "FUELING — The Ladder", body


_GRIT = {
    1: ("Breathing, And Why It Is First", """The mental side of this gets the same treatment as the physical: a few short things, practiced until they are automatic. This is the first.

———

CENTERING YOUR BIOLOGY
Under stress your breathing goes shallow and fast, which tells your nervous system there is a threat, which makes you feel worse, which makes the breathing worse. You can break that loop from either end, and breathing is the end you control.

———

THE 6-2-7 FORMULA
Breathe in for 6, hold for 2, out for 7. The long exhale is the active ingredient — it is what drops your heart rate.

Do it for two minutes before a hard session, and again in the first ten minutes of a race when everything feels too fast. Practice it now, on easy days, so it is available when you need it. A technique you have never rehearsed will not show up on race day."""),
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
    4: ("The Home Stretch", """———

MUSIC
If music helps you, build the playlist this week rather than on the drive up. Be deliberate: something calm for the morning, something that lifts you for the last hour. What you listen to before a start genuinely shifts how you feel at it — pick accordingly rather than by accident.

———

THE NIGHT BEFORE
Read your highlight reel. Run through your performance statements. Then stop thinking about the race — the work is done and rehearsing it further only costs sleep.

———

ON THE LINE
Two minutes of 6-2-7 breathing. Everyone around you will look faster and more organized than you feel. They are not.

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
            "\n\nFRIDAY NIGHT\nBottles mixed. Food in pockets and counted. Kit laid out. Tires checked. Computer charged. Then stop." + guide +
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
    if kind == "heat_prep":
        # Day-agnostic wording: the collision scheduler may shift this
        # note onto the ride's own day, so "tomorrow" could lie.
        #
        # FIX 8 (Aug 17 2026 adversarial grade): the note promised
        # "deliberate thermal-stress blocks" and told the athlete to "ride
        # the marked blocks" -- but the referenced workout is one
        # undifferentiated Z2 ride with nothing marked. The whole ride is
        # the heat session; the note must describe it that way.
        return ("HEAT PREP — Why The Heat Ride Is Overdressed",
                "One of this week's rides is a deliberate thermal-stress"
                " session. The adaptation is real — better sweat response,"
                " lower heart rate at the same effort in warm conditions —"
                " and it compounds over 10-14 days.\n\nHOW\nThe whole ride"
                " is the block: add the extra layer after the warm-up and"
                " hold it, or finish the ride with 15-20 minutes of sauna."
                " One or the other, not both.\n\nRULES\nEasy days only —"
                " never stack heat onto a test or interval day. Drink to"
                " thirst throughout. Feeling dizzy or nauseous means stop"
                " and cool down; the adaptation is not worth a bad day.")
    if kind == "week_zero":
        week = candidate.get("week") or {}
        sessions = [s for s in (_get(week, "sessions", []) or []) if _kind(s) == "bike"]
        ride_count = len(sessions)
        return ("WEEK 0 — Rolling In",
                f"The plan proper starts Monday. This week is a rolling start:"
                f" {ride_count} easy ride{'s' if ride_count != 1 else ''},"
                " nothing measured, nothing hard.\n\nUSE IT FOR\n- Zones in"
                " TrainingPeaks and devices charged and syncing\n- A first"
                " read of the guide (sections 1 and 2)\n- Legs that arrive at"
                " week one fresh, not flat\n\nIf life eats one of these"
                " rides, let it go. The plan has not started yet.")
    if kind.startswith("grit_"):
        number = int(kind.rsplit("_", 1)[1]); prefix = brand.get("mental_skills_name") or ("GRAVEL GRIT" if brand.get("_delivery_key") == "gravelgod" else "MENTAL SKILLS")
        suffix, body = _GRIT[number]
        return f"{prefix} {number} — {suffix}", body.replace("{first_name}", _first_name(plan_ir))
    if kind == "checkin":
        return ("CHECK-IN — How Is It Landing?", "Worth an honest audit:\n\n· Are you finishing the long rides, or surviving them?\n· Is your sleep holding up?\n· Is anything hurting that was not hurting three weeks ago?\n· Are you looking forward to riding, or dreading it?\n\nTwo or more of those pointing the wrong way and we should take something out now rather than later.\n\nNEED THIS ADJUSTED?\nEmail me at " + _email(brand) + ".")
    if kind == "rehearsal_debrief":
        return ("REHEARSAL DEBRIEF — Write It Down And Send It", "While yesterday is still fresh, note:\n\n· What you ate and when. Did you hit the target, or drift?\n· What your stomach did late in the ride.\n· What chafed, rubbed, went numb or ached.\n· What you ran out of.\n· How the last hour felt, honestly.\n· What you would change about pacing.\n\nSend it to me. There is enough time to fix kit, fueling and pacing — but only if we know what broke.\n\n" + _email(brand))
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
