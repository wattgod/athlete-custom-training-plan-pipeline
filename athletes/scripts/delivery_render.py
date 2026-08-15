#!/usr/bin/env python3
"""Pure, brand-aware rendering helpers for the DeliveryIR projection.

This module deliberately does not write delivery artifacts or call TrainingPeaks.
It turns the enriched PlanIR facts into small, reviewable presentation values.
Both PlanIR dataclasses and JSON-shaped dictionaries are accepted at this boundary
because the projection is used before and after PlanIR serialization.
"""

from __future__ import annotations

import copy
import math
import re
from datetime import date as date_type
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


_BRANDS_PATH = Path(__file__).resolve().parent.parent / "config" / "brands.yaml"

# Title intensity is deliberately a small, explicit policy table rather than a
# guessed value derived from a workout name.  Ordering matters: an opener can
# contain >105% efforts but is still an RPE 7 priming session.
RPE_BANDS = (
    ("all_out", "RPE10"),
    ("anaerobic_or_test", "RPE9-10"),
    ("openers", "RPE7"),
    ("cadence_or_skill", "RPE5-6"),
    ("endurance", "RPE3"),
    ("high_intensity", "RPE8-9"),       # dominant work >=105% FTP
    ("threshold", "RPE6-7"),            # dominant work 88-104% FTP
    ("fallback", "RPE6-7"),
)


def load_brand(brand_key: str) -> Dict[str, Any]:
    """Load one configured brand, failing closed for missing or unknown keys."""
    key = str(brand_key or "").strip().lower()
    if not key:
        raise ValueError("A delivery brand key is required")
    try:
        with _BRANDS_PATH.open(encoding="utf-8") as handle:
            registry = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"Could not load brand registry: {exc}") from exc
    brands = registry.get("brands") or {}
    if key not in brands:
        raise ValueError(f"Unknown delivery brand: {brand_key!r}")
    return copy.deepcopy(brands[key])


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _session_kind(session: Any) -> str:
    kind = str(_get(session, "tp_kind") or "").lower()
    if kind:
        return kind
    session_type = str(_get(session, "type") or "").lower()
    if session_type in {"rest", "day_off"}:
        return "day_off"
    if session_type == "strength":
        return "strength"
    if session_type == "race":
        return "race"
    return "bike"


def _duration_minutes(session: Any) -> int:
    seconds = _number(_get(session, "duration_s"))
    if seconds and seconds > 0:
        return int(round(seconds / 60.0))
    hours = _number(_get(session, "total_time_planned"))
    return int(round(hours * 60.0)) if hours and hours > 0 else 0


def _number(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ")).strip(" -–—")


def _format_percent(value: Any) -> Optional[str]:
    number = _number(value)
    if number is None:
        return None
    if abs(number) <= 2:
        number *= 100
    if number <= 0:
        return None
    return f"{number:.0f}%" if number.is_integer() else f"{number:.1f}%"


def _segment_value(segment: Any, name: str, default: Any = None) -> Any:
    return _get(segment, name, default)


def _work_blocks_from_segments(session: Any) -> List[Tuple[int, int, Optional[str]]]:
    """Return ``(total_work_seconds, reps, percent)`` candidates from segments."""
    # Group identical work across segments: generators may emit 15 separate
    # one-rep interval segments for a surge ride — the title must say
    # "15x6s", not "6s" (a real graded delivery lost the rep count).
    grouped: Dict[Tuple[int, Optional[str]], int] = {}
    for segment in _get(session, "segments", []) or []:
        kind = str(_segment_value(segment, "kind") or "").lower()
        if kind == "intervals":
            reps = int(_number(_segment_value(segment, "repeat")) or 1)
            on_seconds = int(_number(_segment_value(segment, "on_seconds")) or 0)
            percent = _format_percent(_segment_value(segment, "on_power"))
            if on_seconds:
                grouped[(on_seconds, percent)] = grouped.get(
                    (on_seconds, percent), 0) + reps
        elif kind == "steady_state":
            seconds = int(_number(_segment_value(segment, "seconds")) or 0)
            percent = _format_percent(_segment_value(segment, "power_target"))
            if seconds and percent:
                grouped[(seconds, percent)] = grouped.get(
                    (seconds, percent), 0) + 1
    return [(seconds * reps, reps, percent)
            for (seconds, percent), reps in grouped.items()]


def _iter_tp_steps(structure: Any) -> Iterable[Dict[str, Any]]:
    """Yield the leaf steps in TP's captured structure shape."""
    if not isinstance(structure, dict):
        return []
    roots = structure.get("structure", structure.get("steps", [])) or []
    leaves: List[Dict[str, Any]] = []
    for root in roots:
        if not isinstance(root, dict):
            continue
        nested = root.get("steps")
        if isinstance(nested, list):
            leaves.extend(item for item in nested if isinstance(item, dict))
        else:
            leaves.append(root)
    return leaves


def _work_blocks_from_structure(session: Any) -> List[Tuple[int, int, Optional[str]]]:
    """Find repeated active TP steps when typed PlanIR segments are absent."""
    structure = _get(session, "structure")
    grouped: Dict[Tuple[int, Optional[str]], int] = {}
    for step in _iter_tp_steps(structure):
        if str(step.get("intensityClass") or "").lower() not in {"active", "interval"}:
            continue
        length = step.get("length") or {}
        seconds = _number(length.get("value") if isinstance(length, dict) else None)
        if not seconds:
            continue
        targets = step.get("targets") or []
        target = targets[0] if targets and isinstance(targets[0], dict) else {}
        percent = _format_percent(target.get("maxValue", target.get("minValue")))
        if percent:
            key = (int(seconds), percent)
            grouped[key] = grouped.get(key, 0) + 1
    return [(seconds * reps, reps, percent) for (seconds, percent), reps in grouped.items()]


def _defining_set_from_structure(session: Any) -> Optional[str]:
    blocks = _work_blocks_from_segments(session) or _work_blocks_from_structure(session)
    if not blocks:
        return None
    # The defining set is the WORK, not the longest block: a 3-minute all-out
    # after a 29-minute spin defines the session. Prefer hard blocks (>=88%),
    # break ties by volume; fall back to the longest block.
    def _pct_value(pct):
        try:
            return float(str(pct).strip().rstrip("%") or 0)
        except ValueError:
            return 0.0

    def _key(block):
        seconds, _, pct = block
        return (1 if _pct_value(pct) >= 88 else 0, seconds)
    total_seconds, reps, percent = max(blocks, key=_key)
    if not percent:
        return None
    each_seconds = total_seconds / max(1, reps)
    if each_seconds < 90:
        each = f"{int(round(each_seconds))}s"
    else:
        each = f"{max(1, int(round(each_seconds / 60.0)))}min"
    prefix = f"{reps}x" if reps > 1 else ""
    return f"{prefix}{each} @{_pct_value(percent):g}%"


_MAIN_SET = re.compile(r"\bMAIN\s+SET\s*:\s*(.+)", re.IGNORECASE)
_SET_WITH_POWER = re.compile(
    r"(?P<reps>\d+)\s*[x×]\s*(?P<minutes>\d+)\s*(?:min(?:utes?)?|m)"
    r"\s*(?:at|@)\s*(?P<percent>\d+(?:\.\d+)?)\s*%?",
    re.IGNORECASE,
)
_SINGLE_SET_WITH_POWER = re.compile(
    r"(?P<minutes>\d+)\s*(?:min(?:utes?)?|m)\s*(?:at|@)\s*"
    r"(?P<percent>\d+(?:\.\d+)?)\s*%?",
    re.IGNORECASE,
)


def _defining_set_from_description(description: Any) -> Optional[str]:
    """Extract a compact MAIN SET value for intentionally structure-free RPE work."""
    match = _MAIN_SET.search(str(description or ""))
    if not match:
        return None
    line = match.group(1).splitlines()[0].strip(" -•")
    interval = _SET_WITH_POWER.search(line)
    if interval:
        return (f"{interval.group('reps')}x{interval.group('minutes')}min "
                f"@{float(interval.group('percent')):g}%")
    single = _SINGLE_SET_WITH_POWER.search(line)
    if single:
        return f"{single.group('minutes')}min @{float(single.group('percent')):g}%"
    all_out = re.search(r"(\d+)\s*(?:min(?:utes?)?|m)\s*(all[- ]?out)", line, re.I)
    if all_out:
        return f"{all_out.group(1)}min all-out"
    return _clean_text(line) or None


def _interval_tokens(value: str) -> List[str]:
    return [f"{match.group(1)}x{match.group(2)}" for match in re.finditer(
        r"\b(\d+)\s*[x×]\s*(\d+)\s*(?:min(?:utes?)?|m)?\b", value, re.I)]


def _display_name(session: Any, defining_set: Optional[str]) -> str:
    name = _clean_text(_get(session, "display_name") or _get(session, "title"))
    name = re.sub(r"\s*[-–—]?\s*(?:level|l)\s*\d+(?:\s*/\s*\d+)?\s*$", "", name, flags=re.I)
    expected = set(_interval_tokens(defining_set or ""))
    for token in _interval_tokens(name):
        if token not in expected:
            name = re.sub(rf"\b{re.escape(token.split('x')[0])}\s*[x×]\s*{re.escape(token.split('x')[1])}\s*(?:min(?:utes?)?|m)?\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s*[-–—]\s*[-–—]\s*", " - ", name)
    return name.strip(" -–—") or "Workout"


def _power_values(session: Any) -> List[float]:
    values: List[float] = []
    for segment in _get(session, "segments", []) or []:
        for name in ("on_power", "power_target", "power_high", "power_low"):
            value = _number(_segment_value(segment, name))
            if value is not None:
                values.append(value * 100 if abs(value) <= 2 else value)
    for _, _, percent in _work_blocks_from_structure(session):
        value = _number(str(percent or "").rstrip("%"))
        if value is not None:
            values.append(value)
    return values


def _dominant_work_percent(session: Any) -> float:
    """Return the target of the largest work block, not a warm-up maximum."""
    blocks = _work_blocks_from_segments(session) or _work_blocks_from_structure(session)
    if blocks:
        _, _, percent = max(blocks, key=lambda block: block[0])
        value = _number(str(percent or "").rstrip("%"))
        if value is not None:
            return value
    values = _power_values(session)
    return max(values) if values else 0


def _rpe(session: Any, name: str) -> str:
    # NAME only for categorical matches — descriptions of interval workouts
    # almost always contain "recovery", which once demoted a 120% VO2 session
    # to RPE3. Dominant work intensity outranks everything except tests.
    text = name.lower()
    dominant = _dominant_work_percent(session)
    if re.search(r"\ball[- ]?out\b", text):
        return "RPE10"
    if _get(session, "is_field_test") or re.search(r"\b(?:anaerobic|ftp|field)\b.*\btest\b", text):
        return "RPE9-10"
    if "opener" in text:
        return "RPE7"
    if re.search(r"\b(?:cadence|skill|technique)\b", text):
        return "RPE5-6"
    if dominant >= 105:
        return "RPE8-9"
    if dominant >= 88:
        return "RPE6-7"
    if _get(session, "is_simulation"):
        return "RPE7"
    if re.search(r"\b(?:endurance|recovery|easy spin)\b", text):
        return "RPE3"
    return "RPE6-7"


def _is_plain_endurance(session: Any, name: str, defining_set: Optional[str]) -> bool:
    # NAME only — never the description: interval descriptions almost always
    # contain the word "recovery" (between efforts), which once collapsed an
    # FTP Test into "Endurance - RPE3" on a real generated plan.
    if _get(session, "is_field_test") or _get(session, "is_simulation"):
        return False
    named_easy = bool(re.search(
        r"\b(?:endurance|recovery|easy spin|pre-plan)\b", name.lower()))
    if not named_easy:
        return defining_set is None
    # A named-endurance ride carrying genuinely hard structured work (e.g.
    # bursts) is dimensioned, not plain.
    values = _power_values(session)
    return not values or max(values) < 88


def _strength_template(session: Any) -> str:
    template = _clean_text(_get(session, "strength_template") or _get(session, "display_name") or _get(session, "title"))
    template = re.sub(r"\s*[-–—]?\s*\d+\s*min(?:utes?)?\b", "", template, flags=re.I)
    template = re.sub(r"\s*[-–—]?\s*RPE\s*\d+(?:\s*[-–]\s*\d+)?\b", "", template, flags=re.I)
    return template.strip(" -–—") or "Strength"


def _race_name(session: Any) -> str:
    race = _get(session, "race") or {}
    if isinstance(race, dict) and race.get("name"):
        return _clean_text(race["name"])
    raw = _clean_text(_get(session, "display_name") or _get(session, "title"))
    raw = re.sub(r"^RACE[ _-]*DAY\s*[-–—:]?\s*", "", raw, flags=re.I)
    return raw or "Race"


def render_title(session: Any, brand_cfg: Dict[str, Any]) -> str:
    """Render the delivery title grammar from emitted session facts.

    ``brand_cfg`` is intentionally accepted at the template boundary even
    though these grammar tokens are brand-neutral.  It prevents a later brand
    name/copy addition from bypassing explicit brand dispatch.
    """
    if not isinstance(brand_cfg, dict):
        raise ValueError("render_title requires a resolved brand configuration")
    kind = _session_kind(session)
    if kind == "day_off":
        return "Day Off"
    if kind == "race":
        return f"RACE DAY — {_race_name(session)}"
    if kind == "strength":
        return f"{_strength_template(session)} - 30min"

    defining_set = _defining_set_from_structure(session)
    if defining_set is None:
        defining_set = _defining_set_from_description(_get(session, "description"))
    name = _display_name(session, defining_set)
    duration = _duration_minutes(session)
    if _is_plain_endurance(session, name, defining_set):
        return f"Endurance - {duration}min - RPE3"
    rpe = _rpe(session, name)
    # Honesty rule: the defining set must not contradict the RPE beside it.
    # A test whose work is a target-free all-out block once titled itself
    # "Anaerobic Test - 29min @55% - RPE9-10" — the filler spin, not the
    # test. Prefer the all-out effort from the description; otherwise drop
    # the set rather than headline easy riding on a hard session.
    if rpe in ("RPE8-9", "RPE9-10", "RPE10") and defining_set:
        if _set_percent(defining_set) is not None and _set_percent(defining_set) < 88:
            all_out = _all_out_set_from_description(_get(session, "description"))
            defining_set = all_out  # may be None -> set omitted below
    if defining_set is None:
        return f"{name} - {duration}min - {rpe}"
    return f"{name} - {defining_set} - {duration}min - {rpe}"


_ALL_OUT_SET = re.compile(
    r"(?P<minutes>\d+)\s*[- ]?\s*min(?:ute)?s?\s*(?:free\s*ride|all[- ]?out)"
    r"|(?:free\s*ride|all[- ]?out)\D{0,12}(?P<minutes2>\d+)\s*[- ]?\s*min",
    re.IGNORECASE,
)


def _set_percent(defining_set: str) -> Optional[float]:
    match = re.search(r"@\s*(\d+(?:\.\d+)?)\s*%", defining_set or "")
    return float(match.group(1)) if match else None


def _all_out_set_from_description(description: Any) -> Optional[str]:
    match = _ALL_OUT_SET.search(str(description or ""))
    if not match:
        return None
    minutes = match.group("minutes") or match.group("minutes2")
    return f"{minutes}min all-out"


def _has_power_structure(session: Any) -> bool:
    if str(_get(session, "control_metric") or "").lower() == "rpe":
        return False
    structure = _get(session, "structure")
    if not structure:
        return False
    if isinstance(structure, dict):
        metric = str(structure.get("primaryIntensityMetric") or "").lower()
        if metric and metric not in {"percentofftp", "power", "power_pct_ftp"}:
            return False
    if _power_values(session):
        return True
    # Canonical TP structures identify power through their primary metric even
    # when a minimal fixture does not expose individual target values.
    return isinstance(structure, dict) and str(
        structure.get("primaryIntensityMetric") or "").lower() == "percentofftp"


def render_if_planned(session: Any) -> Optional[float]:
    """Return TP IF for a structured power bike session, otherwise ``None``."""
    if _session_kind(session) != "bike" or not _has_power_structure(session):
        return None
    tss = _number(_get(session, "tss_planned"))
    if tss is None:
        tss = _number(_get(session, "tss"))
    hours = _duration_minutes(session) / 60.0
    if tss is None or hours <= 0:
        return None
    return round(math.sqrt(tss / (hours * 100.0)), 4)


def _as_date(value: Any) -> Optional[date_type]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_type):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def decorate_day_off(date: Any, week_type: Optional[str], race_date: Any) -> Dict[str, str]:
    """Render a standing rest card, with race-week and post-race variants."""
    current = _as_date(date)
    race = _as_date(race_date)
    normalized_week_type = str(week_type or "").lower()
    if current and race and current == race + timedelta(days=1):
        return {
            "title": "Day Off — Well Done",
            "body": "Nothing today. Eat, drink, sleep, and let the race land.",
        }
    if current and race and current == race - timedelta(days=1):
        return {
            "title": "Day Off — Race Prep",
            "body": "Travel, number pickup, bike check, and feet up. Keep everything familiar for tomorrow.",
        }
    if normalized_week_type == "race":
        return {
            "title": "Day Off — Race Week Rest",
            "body": "Rest completely today. Freshness is the work this week.",
        }
    return {
        "title": "Day Off",
        "body": "Rest completely today. Easy walking and normal life are enough.",
    }


def _plan_value(plan_ir: Any, name: str, default: Any = None) -> Any:
    return _get(plan_ir, name, default)


def _fueling_prescription(fueling: Any) -> Dict[str, Any]:
    if fueling is None:
        return {}
    if isinstance(fueling, dict):
        return dict(fueling.get("prescription") or fueling)
    data = _get(fueling, "to_dict")
    if callable(data):
        return dict(data())
    return {
        "race_target_g_per_hour": _get(fueling, "race_target_g_per_hour"),
        "race_range_g_per_hour": _get(fueling, "race_range_g_per_hour"),
    }


def _iter_plan_sessions(plan_ir: Any) -> Iterable[Tuple[Any, Any, Optional[str]]]:
    for week in _plan_value(plan_ir, "weeks", []) or []:
        week_type = _get(week, "week_type")
        for session in _get(week, "sessions", []) or []:
            yield week, session, week_type


def _race_date_from_plan(plan_ir: Any) -> Optional[str]:
    snapshot = _plan_value(plan_ir, "race_snapshot")
    race_date = _get(snapshot, "date") if snapshot else None
    if race_date:
        return str(race_date)
    for event in _plan_value(plan_ir, "events", []) or []:
        if str(_get(event, "priority") or "").upper() == "A" and _get(event, "date"):
            return str(_get(event, "date"))
    for _, session, _ in _iter_plan_sessions(plan_ir):
        if _session_kind(session) == "race" and _get(session, "date"):
            return str(_get(session, "date"))
    return None


def _rounded_five(value: float) -> int:
    return int(math.floor(value / 5.0 + 0.5) * 5)


def build_fuel_ladder(plan_ir: Any, fueling: Any) -> Dict[str, Any]:
    """Build deterministic long-ride carbohydrate rungs from plan facts.

    The rising portion uses every dated >=90 minute pre-taper bike session.
    Its last simulation (or final eligible ride when no simulation flag exists)
    is the dress rehearsal and reaches the race target.  Taper is intentionally
    a 5 g/hr step back; it is the sole allowed non-monotonic transition.
    """
    prescription = _fueling_prescription(fueling)
    target_value = _number(prescription.get("race_target_g_per_hour"))
    if target_value is None:
        raise ValueError("Fuel ladder requires prescription.race_target_g_per_hour")
    target = int(round(target_value))
    race_date = _race_date_from_plan(plan_ir)
    race = _as_date(race_date)
    pre_taper: List[Tuple[str, Any]] = []
    taper: List[Tuple[str, Any]] = []
    for _, session, week_type in _iter_plan_sessions(plan_ir):
        session_date = _get(session, "date")
        parsed_date = _as_date(session_date)
        if not session_date or not parsed_date or _session_kind(session) != "bike":
            continue
        if race and parsed_date >= race:
            continue
        if _duration_minutes(session) < 90:
            continue
        target_list = taper if str(week_type or "").lower() == "taper" else pre_taper
        target_list.append((str(session_date), session))
    pre_taper.sort(key=lambda item: item[0])
    taper.sort(key=lambda item: item[0])

    ladder: Dict[str, Any] = {}
    final_rehearsal_date: Optional[str] = None
    if pre_taper:
        dress_candidates = [item for item in pre_taper if _get(item[1], "is_dress_rehearsal")]
        sim_candidates = [item for item in pre_taper if _get(item[1], "is_simulation")]
        rehearsal = (dress_candidates[-1] if dress_candidates else
                      sim_candidates[-1] if sim_candidates else pre_taper[-1])
        rehearsal_index = pre_taper.index(rehearsal)
        rising = pre_taper[:rehearsal_index + 1]
        rung_count = len(rising)
        start = max(45, _rounded_five(target - 5 * rung_count))
        for index, (session_date, _) in enumerate(rising):
            if rung_count == 1:
                rate = target
            else:
                rate = _rounded_five(start + (target - start) * index / (rung_count - 1))
                if index == rung_count - 1:
                    rate = target
            ladder[session_date] = min(target, rate)
        # An unusual plan can have a non-simulation long ride after the dress
        # rehearsal; holding race rate preserves monotonicity rather than
        # silently sending the athlete backwards before taper.
        for session_date, _ in pre_taper[rehearsal_index + 1:]:
            ladder[session_date] = target
        final_rehearsal_date = rehearsal[0]

    taper_rate = max(45, _rounded_five(target - 5))
    for session_date, _ in taper:
        ladder[session_date] = taper_rate
    if race_date:
        ladder[str(race_date)] = target
    ladder["final_rehearsal_date"] = final_rehearsal_date
    return ladder


def render_fuel_block(date: Any, ladder: Dict[str, Any]) -> Optional[str]:
    """Render the per-session fuel note; the dated ladder always wins."""
    if not ladder:
        return None
    rate = ladder.get(str(date))
    if rate in (None, ""):
        return None
    if isinstance(rate, str):
        rate_text = rate
    else:
        rate_text = f"{int(round(float(rate)))} g/hr"
    return (f"FUEL LADDER: {rate_text}. Where an individual workout quotes a "
            "different number, use the ladder.")


def render_hydration_block() -> str:
    """Render the fixed, safety-reviewed hydration guidance for delivery notes."""
    return (
        "HYDRATION\n"
        "Drink to thirst. 500-750 ml/hr is a starting estimate to adjust for heat "
        "and sweat rate, not a quota to hit. Aim for 500-1000 mg sodium per hour. "
        "Finish a shade lighter than you started, never heavier."
    )
