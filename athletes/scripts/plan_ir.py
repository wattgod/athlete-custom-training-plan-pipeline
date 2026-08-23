#!/usr/bin/env python3
"""PlanIR v0: a platform-neutral projection of the canonical session model.

Production reads ``canonical_training_model.json`` and never re-derives session
targets from published ZWOs. The historical artifact-reflection branch remains
available only for incomplete pre-Phase-3 packages and compatibility fixtures.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from fueling_policy import FuelingPrescription, prescription_from_fueling
from zwo_parser import parse_zwo, parse_zwo_structure
from tp_polyline import compute_polyline


PLAN_IR_VERSION = "0.2"
ATHLETES_DIR = Path(os.environ.get(
    'GG_ATHLETES_BASE_DIR', Path(__file__).resolve().parent.parent))


@dataclass
class Athlete:
    id: str
    name: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    ftp: Optional[float] = None
    key_markers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RaceSnapshot:
    name: Optional[str] = None
    date: Optional[str] = None
    distance_miles: Optional[float] = None
    elevation_feet: Optional[float] = None
    goal: Optional[str] = None
    source: Optional[str] = None
    source_urls: List[str] = field(default_factory=list)
    source_type: Optional[str] = None
    verified_at: Optional[str] = None
    event_year: Optional[int] = None
    course_variant: Optional[str] = None
    race_metadata: Optional[Dict[str, Any]] = None


@dataclass
class Segment:
    name: str
    seconds: int
    kind: str
    power_low: Optional[float] = None
    power_high: Optional[float] = None
    power_target: Optional[float] = None
    repeat: Optional[int] = None
    on_seconds: Optional[int] = None
    on_power: Optional[float] = None
    off_seconds: Optional[int] = None
    off_power: Optional[float] = None
    # Phase 3 canonical target. Exactly one target type is present for models
    # built from canonical_training_model.json; legacy power fields remain for
    # backward-compatible reflection of historical packages.
    target: Optional[Dict[str, Any]] = None


@dataclass
class Session:
    date: Optional[str]
    title: str
    sport: str
    type: str
    origin: str
    duration_s: int
    tss: int
    segments: List[Segment] = field(default_factory=list)
    source_file: Optional[str] = None
    # -- D1 TP-native projection extensions (Architecture rule #1: the TP
    # output is a versioned projection of PlanIR, never a parallel truth).
    # All optional/default-None so existing consumers of Session keep
    # working unchanged against historical/partial packages.
    description: Optional[str] = None
    tp_kind: Optional[str] = None  # 'bike' | 'strength' | 'race' | 'day_off'
    workout_type_value_id: Optional[int] = None  # TP numeric type: 2/9/7
    tss_planned: Optional[float] = None
    total_time_planned: Optional[float] = None  # hours
    structure: Optional[Dict[str, Any]] = None
    series_id: Optional[str] = None
    series_index: Optional[int] = None
    series_total: Optional[int] = None
    order_on_day: Optional[int] = None
    strength_template: Optional[str] = None
    archetype_id: Optional[str] = None
    display_name: Optional[str] = None
    filename_stem: Optional[str] = None
    # Not in the original D1 field list, but required by the Session-kind
    # semantics section ("B-race days are bike workouts flagged
    # race: {priority: 'B'}"): carries {'priority': 'A'|'B'} for race/
    # B-race sessions, None otherwise.
    race: Optional[Dict[str, Any]] = None
    control_metric: Optional[str] = None
    control_basis: Optional[str] = None
    target_summary: Optional[str] = None
    level: Optional[int] = None
    is_simulation: bool = False
    is_dress_rehearsal: bool = False
    is_field_test: bool = False
    # C4 (docs/SPEC_LIBRARY_SELECTION.md D4): set when this session was
    # resolved to a curated TrainingPeaks library item. Carried from
    # naming_manifest.json (generate_athlete_package.py's resolution pass
    # writes it as an extra _record_tp_session field for resolved days).
    library_item_id: Optional[Any] = None
    # The coach-authored RPE token from the curated item's canonical name
    # (e.g. "3-4"); the delivery renderer must prefer it over any
    # structure-derived RPE guess.
    library_rpe_text: Optional[str] = None


@dataclass
class Week:
    number: int
    phase: Optional[str] = None
    sessions: List[Session] = field(default_factory=list)
    week_type: Optional[str] = None


@dataclass
class Fulfillment:
    status: str = "GENERATED"


@dataclass
class PlanIR:
    athlete: Athlete
    race_snapshot: RaceSnapshot
    fueling: Optional[FuelingPrescription]
    weeks: List[Week] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    entitlements: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    fulfillment: Fulfillment = field(default_factory=Fulfillment)
    plan_ir_version: str = PLAN_IR_VERSION
    brand: Optional[str] = None
    training_age_class: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready representation of this versioned IR."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanIR":
        """Reconstruct PlanIR from ``to_dict`` output without loss."""
        fueling_data = data.get("fueling")
        fueling = FuelingPrescription(**fueling_data) if fueling_data else None
        weeks = [
            Week(
                number=week["number"],
                phase=week.get("phase"),
                week_type=week.get("week_type"),
                sessions=[
                    Session(
                        **{
                            **{key: value for key, value in session.items() if key != "segments"},
                            "segments": [Segment(**segment) for segment in session.get("segments", [])],
                        }
                    )
                    for session in week.get("sessions", [])
                ],
            )
            for week in data.get("weeks", [])
        ]
        return cls(
            athlete=Athlete(**data["athlete"]),
            race_snapshot=RaceSnapshot(**data.get("race_snapshot", {})),
            fueling=fueling,
            weeks=weeks,
            notes=list(data.get("notes", [])),
            entitlements=list(data.get("entitlements", [])),
            attachments=list(data.get("attachments", [])),
            fulfillment=Fulfillment(**data.get("fulfillment", {})),
            plan_ir_version=data.get("plan_ir_version", PLAN_IR_VERSION),
            brand=data.get("brand"),
            training_age_class=data.get("training_age_class"),
            events=list(data.get("events", [])),
        )


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        warnings.warn(f"PlanIR: optional artifact missing: {path.name}", RuntimeWarning, stacklevel=2)
        return {}
    try:
        with path.open() as handle:
            return yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        warnings.warn(f"PlanIR: could not read {path.name}: {exc}", RuntimeWarning, stacklevel=2)
        return {}


def _number(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _source(data: Dict[str, Any]) -> Optional[str]:
    value = _first(data, "source", "source_url", "source_urls")
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def _athlete_from_profile(athlete_id: str, profile: Dict[str, Any]) -> Athlete:
    markers = profile.get("fitness_markers", {}) or {}
    athlete_values = profile.get("athlete", {}) or {}
    weight = _first(profile, "weight_kg")
    if weight is None:
        weight = _first(markers, "weight_kg") or _first(athlete_values, "weight_kg")
    sex = _first(profile, "sex") or _first(markers, "sex") or _first(athlete_values, "sex")
    age = (_first(profile.get("health_factors", {}) or {}, "age")
           or _first(profile, "age") or _first(markers, "age")
           or _first(athlete_values, "age"))
    ftp = _first(markers, "ftp_watts", "ftp")
    key_markers = {
        key: markers.get(key)
        for key in ("w_kg", "resting_hr", "max_hr", "lthr", "ftp_date",
                    "power_basis", "control_metric", "control_basis", "reanchor")
        if markers.get(key) is not None
    }
    return Athlete(
        id=athlete_id,
        name=profile.get("name"),
        sex=sex,
        age=int(age) if age is not None else None,
        weight_kg=_number(weight),
        ftp=_number(ftp),
        key_markers=key_markers,
    )


def _race_from_artifacts(profile: Dict[str, Any], fueling: Dict[str, Any], plan_dates: Dict[str, Any]) -> RaceSnapshot:
    target = profile.get("target_race", {}) or {}
    fueling_race = fueling.get("race", {}) or {}
    race = profile.get("race", {}) or {}
    event_year = _first(target, "event_year") or _first(race, "event_year")
    try:
        event_year = int(event_year) if event_year is not None else None
    except (TypeError, ValueError):
        event_year = None
    return RaceSnapshot(
        name=_first(target, "name") or _first(fueling_race, "name"),
        date=_first(target, "date") or plan_dates.get("race_date"),
        distance_miles=_number(_first(target, "distance_miles") or _first(race, "distance_miles") or _first(fueling_race, "distance_miles")),
        elevation_feet=_number(_first(target, "elevation_feet", "elevation_ft") or _first(race, "elevation_feet", "elevation_ft") or _first(fueling_race, "elevation_feet", "elevation_ft")),
        goal=_first(target, "goal_type", "goal") or _first(race, "goal_type") or _first(fueling_race, "goal_type"),
        source=_source(target) or _source(race),
        source_urls=list(target.get('source_urls') or race.get('source_urls') or []),
        source_type=_first(target, 'source_type') or _first(race, 'source_type'),
        verified_at=_first(target, "verified_at") or _first(race, "verified_at"),
        event_year=event_year,
        course_variant=_first(target, "course_variant") or _first(race, "course_variant"),
        race_metadata=target.get("race_metadata"),
    )


_LEVEL_PATTERN = re.compile(r"-Level\s+(\d+)\s*/\s*6\s*:", re.I)
# Ported from post_render_validator.FIELD_TEST_PATTERNS.  Keep this local so
# PlanIR remains independent of the webhook/render validation path.
_FIELD_TEST_PATTERNS = (
    re.compile(r"\b(?:ftp|power)\b.*\btest\b|\btest\b.*\bftp\b", re.I),
    re.compile(r"\b(?:lthr|heart rate|hr)\b.*\btest\b|\btest\b.*\blthr\b", re.I),
    re.compile(r"\brpe\b.*\btest\b|\bfield test\b", re.I),
    # The anaerobic repeatability assessment is a test (it measures and
    # records), and briefings must treat it like one.
    re.compile(r"\banaerobic\b.*\btest\b", re.I),
)
_SIMULATION_PATTERN = re.compile(r"\brace\s+sim\b|\bsimulation\b|\bact\s", re.I)


def _level_from_description(description: Optional[str]) -> Optional[int]:
    """Extract the emitted progression level from a ZWO description."""
    match = _LEVEL_PATTERN.search(description or "")
    return int(match.group(1)) if match else None


def _normalize_years(value: Any) -> Optional[float]:
    """Return the conservative lower bound represented by a years answer."""
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.match(
        r"^\s*(\d+(?:\.\d+)?)\s*(?:\+|(?:-\s*\d+(?:\.\d+)?)?)\s*$",
        str(value),
    )
    return float(match.group(1)) if match else None


def training_age_class(profile: Dict[str, Any]) -> Optional[str]:
    """Classify athlete experience from the supplied training history."""
    history = profile.get("training_history") or {}
    years_cycling = _normalize_years(history.get("years_cycling"))
    years_structured = _normalize_years(history.get("years_structured"))
    if years_cycling is None and years_structured is None:
        return None
    if (years_cycling is not None and years_cycling >= 5) or (
            years_structured is not None and years_structured >= 3):
        return "experienced"
    return "developing"


def _brand_from_profile(profile: Dict[str, Any]) -> Optional[str]:
    brand = profile.get("brand")
    if brand not in (None, ""):
        return str(brand)
    brands = _load_yaml(Path(__file__).resolve().parent.parent / "config" / "brands.yaml")
    default_brand = brands.get("default_brand")
    return str(default_brand) if default_brand not in (None, "") else None


def _event_ledger(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project athlete-supplied A/B/C event facts without derived details."""
    events: List[Dict[str, Any]] = []
    for key, priority in (("a_events", "A"), ("b_events", "B"), ("c_events", "C")):
        for event in profile.get(key) or []:
            if not isinstance(event, dict):
                continue
            events.append({
                "name": event.get("name"),
                "date": event.get("date"),
                "priority": event.get("priority") or priority,
                "mandatory": bool(event.get("mandatory")),
            })
    return events


def _week_type_lookup(plan_dates: Dict[str, Any]) -> Dict[int, str]:
    """Read explicit calendar types, else use plan_dates' canonical mapping."""
    from block_chain import derive_week_descriptors

    derived = {
        int(descriptor["plan_week"]): descriptor["week_type"]
        for descriptor in derive_week_descriptors(plan_dates)
    }
    week_types = {}
    for week in plan_dates.get("weeks", []):
        try:
            number = int(week["week"])
        except (KeyError, TypeError, ValueError):
            continue
        explicit = week.get("week_type")
        week_types[number] = str(explicit) if explicit not in (None, "") else derived.get(number)
    return week_types


def _is_simulation(session: Session, week_type: Optional[str]) -> bool:
    label = " ".join(filter(None, (session.archetype_id, session.title)))
    label = label.replace("_", " ").replace("-", " ")
    return bool(_SIMULATION_PATTERN.search(label)) or (
        session.tp_kind == "bike" and session.duration_s >= 4 * 60 * 60 and week_type == "load")


def _annotate_delivery_context(weeks: List[Week]) -> None:
    """Populate session-only delivery facts once calendar weeks are assembled."""
    for week in weeks:
        for session in week.sessions:
            session.level = _level_from_description(session.description)
            session.is_simulation = _is_simulation(session, week.week_type)
            session.is_field_test = session.type == "ftp_test" or any(
                pattern.search(session.title) for pattern in _FIELD_TEST_PATTERNS)

    first_taper_or_race = next(
        (index for index, week in enumerate(weeks)
         if week.week_type in {"taper", "race"}),
        None,
    )
    if first_taper_or_race is None:
        return
    simulations = [
        session
        for week in weeks[:first_taper_or_race]
        for session in week.sessions
        if session.is_simulation
    ]
    if simulations:
        simulations[-1].is_dress_rehearsal = True


def _segment_from_dict(segment: Dict[str, Any]) -> Segment:
    return Segment(**{
        key: value for key, value in segment.items()
        if key in Segment.__dataclass_fields__
    })


# =============================================================================
# TP PROJECTION (D1): tp_kind -> TP numeric workoutTypeValueId, and a
# typed-segment -> TP `structure` converter. The converter reuses the
# already-parsed Segment list (itself produced by zwo_parser's shared typed
# parser) rather than re-parsing ZWO XML -- see build_tp_bodies.py in
# gravel-god-training-plans/tools/ for the captured TP structure convention
# this mirrors (step/targets/intensityClass shape, FreeRide -> minValue 0).
# =============================================================================

TP_WORKOUT_TYPE_VALUE_ID = {
    'bike': 2,
    'race': 2,   # A-race is a FreeRide-equivalent bike workout in TP terms
    'strength': 9,
    'day_off': 7,
}


def _default_tp_kind(session_type: str) -> str:
    """Fallback tp_kind when no naming_manifest.json entry exists (older
    packages, or a session PlanIR synthesized itself, e.g. rest days)."""
    if session_type == "rest":
        return "day_off"
    if session_type == "strength":
        return "strength"
    if session_type == "race":
        return "race"
    return "bike"


def _load_naming_manifest(athlete_dir: Path) -> Dict[str, Any]:
    """Read the naming_manifest.json sidecar generate_athlete_package.py
    writes next to the ZWOs -- carries per-session TP-projection metadata
    that can't be re-derived from a rendered ZWO file alone (tp_kind,
    series identity, strength template, archetype id, ...)."""
    path = athlete_dir / "workouts" / "naming_manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"PlanIR: could not read naming_manifest.json: {exc}", RuntimeWarning, stacklevel=2)
        return {}


def _pct(value: Optional[float]) -> int:
    return int(round((value or 0.0) * 100))


def _tp_step(name: str, seconds: int, low: Optional[float], high: Optional[float],
             flat: Optional[float], intensity_class: str, begin: int,
             all_out: bool = False) -> Dict[str, Any]:
    seconds = int(seconds)
    if all_out:
        targets = [{"minValue": 120, "maxValue": 170}]
    elif low is not None and high is not None and _pct(high) > _pct(low):
        targets = [{"minValue": _pct(low), "maxValue": _pct(high)}]
    else:
        target_value = flat if flat is not None else (high if high is not None else low)
        targets = [{"minValue": _pct(target_value)}]
    return {
        "type": "step",
        "length": {"value": 1, "unit": "repetition"},
        "steps": [{
            "name": name,
            "length": {"value": seconds, "unit": "second"},
            "targets": targets,
            "intensityClass": intensity_class,
        }],
        "begin": begin,
        "end": begin + seconds,
    }


def _tp_structure_from_segments(segments: List[Segment]) -> Optional[Dict[str, Any]]:
    """Convert already-typed Segments into a TP structure dict. Intervals are
    unrolled -- each on/off gets its own step, per the reference build."""
    steps: List[Dict[str, Any]] = []
    t = 0
    for seg in segments:
        if seg.kind == "warmup":
            mid = (seg.power_low + seg.power_high) / 2 if seg.power_low is not None and seg.power_high is not None else seg.power_high
            steps.append(_tp_step("Warm Up", seg.seconds, seg.power_low, seg.power_high, mid, "warmUp", t))
        elif seg.kind == "cooldown":
            mid = (seg.power_low + seg.power_high) / 2 if seg.power_low is not None and seg.power_high is not None else seg.power_low
            steps.append(_tp_step("Cool Down", seg.seconds, seg.power_low, seg.power_high, mid, "coolDown", t))
        elif seg.kind == "ramp":
            mid = (seg.power_low + seg.power_high) / 2 if seg.power_low is not None and seg.power_high is not None else seg.power_high
            steps.append(_tp_step("Ramp", seg.seconds, seg.power_low, seg.power_high, mid, "active", t))
        elif seg.kind == "steady_state":
            steps.append(_tp_step("Steady State", seg.seconds, None, None, seg.power_target, "active", t))
        elif seg.kind == "intervals":
            for _ in range(seg.repeat or 1):
                on_step = _tp_step("Steady State", seg.on_seconds, None, None, seg.on_power, "active", t)
                steps.append(on_step)
                t = on_step["end"]
                off_step = _tp_step("Steady State", seg.off_seconds, None, None, seg.off_power, "rest", t)
                steps.append(off_step)
                t = off_step["end"]
            continue  # begin/end already advanced per on/off step above
        elif seg.kind == "free_ride":
            all_out = bool(re.search(r"all[- ]?out|max(?:imal)? effort|\bmax sprint\b",
                                     seg.name or "", re.I))
            steps.append(_tp_step(seg.name or "Free Ride", seg.seconds, None, None,
                                  0.0, "active", t, all_out=all_out))
        else:
            continue
        t = steps[-1]["end"]
    if not steps:
        return None
    return {
        "structure": steps,
        "primaryLengthMetric": "duration",
        "primaryIntensityMetric": "percentOfFtp",
        "primaryIntensityTargetOrRange": "target",
        "polyline": compute_polyline(steps),
    }


def _session_type(title: str, is_race_day: bool) -> str:
    normalized = title.upper().replace(" ", "_")
    if is_race_day or "RACE_DAY" in normalized:
        return "race"
    if "REST" in normalized or "DAY_OFF" in normalized:
        return "rest"
    if "FTP" in normalized and "TEST" in normalized:
        return "ftp_test"
    if "STRENGTH" in normalized:
        return "strength"
    return "workout"


def _session_origin(session_type: str) -> str:
    if session_type == "race":
        return "event"
    if session_type == "rest":
        return "rest"
    return "prescribed"


def _sport_for_type(session_type: str) -> str:
    return "strength" if session_type == "strength" else "cycling"


def _round_time_planned_hours(duration_sec: float) -> float:
    """Round a session's planned duration to the nearest whole minute before
    projecting it to hours, so the delivered TP `totalTimePlanned` -- and any
    H:MM:SS clock TP renders from it -- reads "4:10:00" instead of a ragged
    "4:09:44" built straight from the raw segment-second sum. `tssPlanned`
    is left as round(tss, 1), unaffected by this.
    """
    if not duration_sec:
        return 0.0
    whole_minutes = round(duration_sec / 60)
    return round((whole_minutes * 60) / 3600, 4)


def _session_from_zwo(zwo_path: Path, date: Optional[str], is_race_day: bool, ftp: Optional[float],
                       manifest: Optional[Dict[str, Any]] = None) -> Session:
    zwo_structure = parse_zwo_structure(zwo_path)
    # TSS is relative to power ratios, but the shared preview parser needs a
    # numeric FTP to retain its established result shape.  This fallback is
    # calculation-only and is never written back to athlete facts.
    metrics = parse_zwo(zwo_path, ftp or 200.0)
    title = zwo_structure["name"].replace("_", " ")
    session_type = _session_type(title, is_race_day)
    segments = [_segment_from_dict(segment) for segment in zwo_structure["segments"]]

    entry = (manifest or {}).get(zwo_path.stem, {})
    tp_kind = entry.get("tp_kind") or _default_tp_kind(session_type)
    workout_type_value_id = entry.get("workout_type_value_id")
    if workout_type_value_id is None:
        workout_type_value_id = TP_WORKOUT_TYPE_VALUE_ID.get(tp_kind)
    # structure absent for strength/race/day_off (D1) -- only bike sessions
    # carry executable TP targets.
    structure = _tp_structure_from_segments(segments) if tp_kind == "bike" else None
    duration_sec = metrics["duration_sec"]

    # C4 (D4): library-resolved sessions carry library_item_id straight
    # from the naming manifest -- the browser-based TP placement job looks
    # up the item's verbatim structure/description by this ID (C1); this
    # projection's own structure/description/segments stay the normal
    # ZWO-derived (already-unrolled, C2-converted) representation, matching
    # every other session (test_tp_projection.py's unrolled-structure
    # invariant applies uniformly, resolved or not).
    library_item_id = entry.get("library_item_id")

    # R1 fix wave (SPEC_LIBRARY_SELECTION.md regrade): same override as
    # canonical_training_model._compiler_session -- for a library-resolved
    # session the AUTHORED tss/if_planned (naming_manifest.json's
    # library_tss/library_if_planned) are authoritative, not the internal
    # C2-ZWO-derived normalized-power recompute.
    _library_tss = entry.get("library_tss")
    _tss_value = _library_tss if _library_tss is not None else metrics["tss"]

    return Session(
        date=date,
        title=title,
        sport=_sport_for_type(session_type),
        type=session_type,
        origin=_session_origin(session_type),
        duration_s=int(duration_sec),
        tss=int(round(_tss_value)),
        segments=segments,
        source_file=zwo_path.name,
        description=zwo_structure.get("description"),
        tp_kind=tp_kind,
        workout_type_value_id=workout_type_value_id,
        tss_planned=round(float(_tss_value), 1),
        total_time_planned=_round_time_planned_hours(duration_sec),
        structure=structure,
        series_id=entry.get("series_id"),
        series_index=entry.get("series_index"),
        series_total=entry.get("series_total"),
        order_on_day=entry.get("order_on_day"),
        strength_template=entry.get("strength_template"),
        archetype_id=entry.get("archetype_id"),
        display_name=entry.get("display_name") or title,
        filename_stem=zwo_path.stem,
        race=entry.get("race"),
        level=_level_from_description(zwo_structure.get("description")),
        library_item_id=library_item_id,
        library_rpe_text=entry.get("library_rpe_text"),
    )


def _rest_session(date: Optional[str]) -> Session:
    return Session(
        date=date,
        title="Rest Day",
        sport="cycling",
        type="rest",
        origin="rest",
        duration_s=0,
        tss=0,
        tp_kind="day_off",
        workout_type_value_id=TP_WORKOUT_TYPE_VALUE_ID["day_off"],
        tss_planned=0.0,
        total_time_planned=0.0,
        display_name="Rest Day",
    )


def _week_number_from_filename(path: Path) -> Optional[int]:
    match = re.match(r"W(\d+)_", path.name)
    return int(match.group(1)) if match else None


def _build_weeks(
    athlete_dir: Path,
    plan_dates: Dict[str, Any],
    athlete: Athlete,
    recurring_sessions: List[Dict[str, Any]] | None = None,
) -> List[Week]:
    zwo_paths = sorted((athlete_dir / "workouts").glob("*.zwo")) if (athlete_dir / "workouts").exists() else []
    if not zwo_paths:
        warnings.warn("PlanIR: optional artifact missing: workouts/*.zwo", RuntimeWarning, stacklevel=2)

    manifest = _load_naming_manifest(athlete_dir)
    remaining = set(zwo_paths)
    weeks: List[Week] = []
    week_types = _week_type_lookup(plan_dates)
    for week_data in plan_dates.get("weeks", []):
        week_number = int(week_data.get("week", len(weeks) + 1))
        week = Week(
            number=week_number,
            phase=week_data.get("phase"),
            week_type=week_types.get(week_number),
        )
        for day in week_data.get("days", []):
            prefix = day.get("workout_prefix", "")
            matches = sorted(path for path in remaining if path.stem.startswith(prefix)) if prefix else []
            is_race_day = bool(day.get("is_race_day") or day.get("is_b_race_day"))
            if matches:
                for match in matches:
                    remaining.remove(match)
                    week.sessions.append(_session_from_zwo(match, day.get("date"), is_race_day, athlete.ftp, manifest))
            else:
                # Calendar days without a rendered ZWO are real rest days in the
                # v0 reflection, rather than omitted holes in the plan calendar.
                week.sessions.append(_rest_session(day.get("date")))
        # G4: repeat immutable athlete sessions on their calendar day.  They
        # are not generated ZWOs, but they are canonical plan load and must
        # survive into every platform-neutral serializer.
        for raw in recurring_sessions or []:
            if not raw.get('locked'):
                continue
            for day in week_data.get('days', []):
                if str(day.get('day_name', day.get('day', '')))[:3].title() != raw.get('day'):
                    continue
                week.sessions.append(Session(
                    date=day.get('date'), title=raw.get('title') or 'Fixed external session',
                    sport='cycling', type='external_fixed', origin='athlete_fixed',
                    duration_s=int(raw.get('duration_min', 0)) * 60,
                    tss=int(raw.get('tss', 0) or 0), source_file=None,
                ))
        weeks.append(week)

    # A partial plan_dates file should not hide emitted workouts.  Preserve them
    # in their filename week (or a final unnumbered bucket) with unknown dates.
    by_number: Dict[int, Week] = {week.number: week for week in weeks}
    for zwo_path in sorted(remaining):
        number = _week_number_from_filename(zwo_path) or 0
        week = by_number.get(number)
        if week is None:
            week = Week(number=number)
            by_number[number] = week
            weeks.append(week)
        week.sessions.append(_session_from_zwo(zwo_path, None, "RACE_DAY" in zwo_path.name.upper(), athlete.ftp, manifest))
    return sorted(weeks, key=lambda week: week.number)


def _fulfillment_from_file(athlete_dir: Path) -> Fulfillment:
    path = athlete_dir / "fulfillment_status.json"
    if not path.exists():
        return Fulfillment()
    try:
        data = json.loads(path.read_text())
        status = data.get("status", "GENERATED") if isinstance(data, dict) else "GENERATED"
        return Fulfillment(status=str(status))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"PlanIR: could not read fulfillment_status.json: {exc}", RuntimeWarning, stacklevel=2)
        return Fulfillment()


def _plan_ir_from_canonical(
    athlete_id: str,
    athlete_dir: Path,
    model: Dict[str, Any],
    profile: Dict[str, Any],
    fueling_data: Dict[str, Any],
    plan_dates: Dict[str, Any],
) -> PlanIR:
    """Build PlanIR strictly as a canonical-model projection."""
    from canonical_training_model import project_tp_structure

    athlete = _athlete_from_profile(athlete_id, profile)
    control = model.get("athlete") or {}
    by_week: Dict[int, Week] = {}
    week_types = _week_type_lookup(plan_dates)
    for raw in model.get("sessions") or []:
        week_number = int(raw.get("week") or 0)
        week = by_week.setdefault(
            week_number, Week(
                number=week_number,
                phase=raw.get("phase"),
                week_type=week_types.get(week_number),
            ))
        segments = []
        for segment in raw.get("segments") or []:
            target = segment.get("target") or {}
            legacy_power = {}
            if target.get("type") == "power_pct_ftp":
                on_power = target.get("on")
                off_power = target.get("off")
                legacy_power = {
                    "power_low": (min(on_power, off_power)
                                  if on_power is not None and off_power is not None
                                  else target.get("low")),
                    "power_high": (max(on_power, off_power)
                                   if on_power is not None and off_power is not None
                                   else target.get("high")),
                    "power_target": target.get("value"),
                    "on_power": on_power,
                    "off_power": off_power,
                }
            segments.append(Segment(
                name=str(segment.get("name") or segment.get("kind") or "segment"),
                seconds=int(segment.get("seconds") or 0),
                kind=str(segment.get("kind") or "steady_state"),
                repeat=segment.get("repeat"),
                on_seconds=segment.get("on_seconds"),
                off_seconds=segment.get("off_seconds"),
                target=target,
                **legacy_power,
            ))
        description = raw.get("description")
        if control.get("control_metric") == "rpe" and raw.get("target_summary"):
            description = ((description or "").rstrip()
                           + f"\n\nPRESCRIPTION: {raw['target_summary']}").strip()
        week.sessions.append(Session(
            date=raw.get("date"), title=str(raw.get("title") or "Untitled session"),
            sport=str(raw.get("sport") or "cycling"),
            type=str(raw.get("session_type") or "workout"),
            origin=str(raw.get("origin") or "prescribed"),
            duration_s=int(raw.get("duration_s") or 0),
            tss=int(raw.get("tss") or 0), segments=segments,
            source_file=raw.get("source_file"), description=description,
            tp_kind=raw.get("tp_kind"),
            workout_type_value_id=raw.get("workout_type_value_id"),
            tss_planned=raw.get("tss_planned"),
            total_time_planned=raw.get("total_time_planned"),
            structure=project_tp_structure(raw, control),
            series_id=raw.get("series_id"), series_index=raw.get("series_index"),
            series_total=raw.get("series_total"), order_on_day=raw.get("order_on_day"),
            strength_template=raw.get("strength_template"),
            archetype_id=raw.get("archetype_id"),
            display_name=raw.get("display_name") or raw.get("title"),
            filename_stem=raw.get("filename_stem"), race=raw.get("race"),
            control_metric=control.get("control_metric"),
            control_basis=control.get("control_basis"),
            target_summary=raw.get("target_summary"),
            level=_level_from_description(description),
            library_item_id=raw.get("library_item_id"),
            library_rpe_text=raw.get("library_rpe_text"),
        ))
    prescription_data = model.get("fueling") or (
        prescription_from_fueling(fueling_data) if fueling_data else None)
    fueling = FuelingPrescription(**prescription_data) if prescription_data else None
    race_data = dict(model.get("race_snapshot") or {})
    target_race = profile.get("target_race") or {}
    if "race_metadata" in target_race:
        race_data["race_metadata"] = target_race["race_metadata"]
    plan_ir = PlanIR(
        athlete=athlete,
        race_snapshot=RaceSnapshot(**{
            key: value for key, value in race_data.items()
            if key in RaceSnapshot.__dataclass_fields__
        }),
        fueling=fueling, weeks=sorted(by_week.values(), key=lambda item: item.number),
        notes=list(model.get("notes") or []),
        entitlements=list(model.get("entitlements") or []),
        attachments=list(model.get("attachments") or []),
        fulfillment=_fulfillment_from_file(athlete_dir),
        brand=_brand_from_profile(profile),
        training_age_class=training_age_class(profile),
        events=_event_ledger(profile),
    )
    _annotate_delivery_context(plan_ir.weeks)
    return plan_ir


def build_plan_ir(
    athlete_id: str,
    *,
    prefer_canonical: bool = True,
    plan_dates_override: Optional[Dict[str, Any]] = None,
) -> PlanIR:
    """Aggregate an athlete's existing outputs and write ``plan_ir.json``.

    Missing artifacts yield warnings and a partial object.  This makes G0 safe
    to invoke as an advisory final package step while historical packages have
    uneven artifact coverage.
    """
    athlete_dir = ATHLETES_DIR / athlete_id
    profile = _load_yaml(athlete_dir / "profile.yaml")
    fueling_data = _load_yaml(athlete_dir / "fueling.yaml")
    plan_dates = (plan_dates_override if plan_dates_override is not None
                  else _load_yaml(athlete_dir / "plan_dates.yaml"))
    _load_yaml(athlete_dir / "weekly_structure.yaml")  # Reflected input; scheduling moves to PlanIR in G4.

    canonical_path = athlete_dir / "canonical_training_model.json"
    if prefer_canonical and canonical_path.exists():
        from canonical_training_model import load_canonical_model
        plan_ir = _plan_ir_from_canonical(
            athlete_id, athlete_dir, load_canonical_model(canonical_path),
            profile, fueling_data, plan_dates,
        )
    else:
        athlete = _athlete_from_profile(athlete_id, profile)
        prescription_data = prescription_from_fueling(fueling_data) if fueling_data else None
        fueling = FuelingPrescription(**prescription_data) if prescription_data else None
        target = profile.get('target_race', {}) or {}
        mental = profile.get('mental_game', {}) or {}
        mental_tasks = [
            {'kind': 'mental_training', 'id': key, 'text': str(value)}
            for key, value in mental.items() if value not in (None, '', 'none', 'no')
        ]
        guide_path = 'training_guide.pdf' if (athlete_dir / 'training_guide.pdf').exists() else 'training_guide.html'
        plan_ir = PlanIR(
            athlete=athlete,
            race_snapshot=_race_from_artifacts(profile, fueling_data, plan_dates),
            fueling=fueling,
            weeks=_build_weeks(athlete_dir, plan_dates, athlete,
                               profile.get('recurring_sessions', []) or []),
            notes=mental_tasks,
            entitlements=[{'kind': 'course', 'race': target.get('name'),
                           'race_date': target.get('date'), 'race_id': target.get('race_id')}],
            attachments=[{'id': 'guide', 'kind': 'guide', 'path': guide_path}],
            fulfillment=_fulfillment_from_file(athlete_dir),
            brand=_brand_from_profile(profile),
            training_age_class=training_age_class(profile),
            events=_event_ledger(profile),
        )
        _annotate_delivery_context(plan_ir.weeks)
    output_path = athlete_dir / "plan_ir.json"
    payload = json.dumps(plan_ir.to_dict(), indent=2, sort_keys=True) + "\n"
    # Atomic write: a sibling temp file then os.replace, so an I/O failure or a
    # kill never truncates an already-valid plan_ir.json. build_plan_ir runs
    # several times per package (the last re-projects the final fulfillment
    # state), so a partial write would otherwise corrupt a good artifact.
    try:
        fd, tmp = tempfile.mkstemp(dir=str(athlete_dir), prefix=".plan_ir.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, output_path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError as exc:
        warnings.warn(f"PlanIR: could not write plan_ir.json: {exc}", RuntimeWarning, stacklevel=2)
    return plan_ir


_TP_MANIFEST_VERSION = 1


def project_tp_manifest(plan_ir: PlanIR) -> Dict[str, Any]:
    """Project ``tp_manifest.json`` from an already-built PlanIR.

    Architecture rule #1: the TP output is a versioned PROJECTION of
    PlanIR, never a parallel truth -- this function reads PlanIR.Session's
    D1 extension fields only; it never re-derives plan facts.
    """
    counts = {"bike": 0, "strength": 0, "day_off": 0, "race": 0}
    sessions: List[Dict[str, Any]] = []
    for week in plan_ir.weeks:
        for session in week.sessions:
            if session.tp_kind in counts:
                counts[session.tp_kind] += 1
            sessions.append({
                "date": session.date,
                "title": session.title,
                "display_name": session.display_name,
                "filename_stem": session.filename_stem,
                "description": session.description,
                "tp_kind": session.tp_kind,
                "workout_type_value_id": session.workout_type_value_id,
                "tss_planned": session.tss_planned,
                "total_time_planned": session.total_time_planned,
                "structure": session.structure,
                "series_id": session.series_id,
                "series_index": session.series_index,
                "series_total": session.series_total,
                "order_on_day": session.order_on_day,
                "strength_template": session.strength_template,
                "archetype_id": session.archetype_id,
                "race": session.race,
                "control_metric": session.control_metric,
                "control_basis": session.control_basis,
                "target_summary": session.target_summary,
                "library_item_id": session.library_item_id,
                "library_rpe_text": session.library_rpe_text,
            })

    plan_weeks = max((w.number for w in plan_ir.weeks if w.number and w.number > 0), default=0)
    athlete_name = plan_ir.athlete.name or "Athlete"
    race_name = plan_ir.race_snapshot.name or "Race"
    return {
        "version": _TP_MANIFEST_VERSION,
        "plan_title": f"{athlete_name} · {race_name} · {plan_weeks}wk [CUSTOM]",
        "athlete": athlete_name,
        "race": {
            "name": plan_ir.race_snapshot.name,
            "date": plan_ir.race_snapshot.date,
            "priority": "A",
        },
        "control": {
            "metric": plan_ir.athlete.key_markers.get("control_metric"),
            "basis": plan_ir.athlete.key_markers.get("control_basis"),
            "power_basis": plan_ir.athlete.key_markers.get("power_basis"),
            "reanchor": plan_ir.athlete.key_markers.get("reanchor"),
        },
        "expected": {
            "bike": counts["bike"],
            "strength": counts["strength"],
            "day_off": counts["day_off"],
            "race": counts["race"],
            "total": sum(counts.values()),
        },
        "sessions": sessions,
    }


def build_tp_manifest(athlete_id: str) -> Dict[str, Any]:
    """Build + atomically write ``tp_manifest.json`` from the athlete's
    already-assembled ``plan_ir.json``. Callers run this after
    ``build_plan_ir`` (see generate_athlete_package.py step 6)."""
    athlete_dir = ATHLETES_DIR / athlete_id
    plan_ir_path = athlete_dir / "plan_ir.json"
    try:
        plan_ir = PlanIR.from_dict(json.loads(plan_ir_path.read_text()))
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        warnings.warn(f"tp_manifest: could not read plan_ir.json: {exc}", RuntimeWarning, stacklevel=2)
        return {}

    manifest = project_tp_manifest(plan_ir)
    output_path = athlete_dir / "tp_manifest.json"
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    try:
        fd, tmp = tempfile.mkstemp(dir=str(athlete_dir), prefix=".tp_manifest.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, output_path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError as exc:
        warnings.warn(f"tp_manifest: could not write tp_manifest.json: {exc}", RuntimeWarning, stacklevel=2)
    return manifest


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 plan_ir.py <athlete_id>")
        raise SystemExit(2)
    build_plan_ir(sys.argv[1])
