#!/usr/bin/env python3
"""PlanIR v0: a non-authoring aggregation of generated plan artifacts.

G0 intentionally reads the package the pipeline has already produced.  It is
not an input to ZWO, guide, or fueling generation yet; later tickets migrate
those serializers to project this object instead.
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


PLAN_IR_VERSION = "0.1"
ATHLETES_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Athlete:
    id: str
    name: Optional[str] = None
    sex: Optional[str] = None
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


@dataclass
class Week:
    number: int
    phase: Optional[str] = None
    sessions: List[Session] = field(default_factory=list)


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
    ftp = _first(markers, "ftp_watts", "ftp")
    key_markers = {
        key: markers.get(key)
        for key in ("w_kg", "resting_hr", "max_hr", "ftp_date")
        if markers.get(key) is not None
    }
    return Athlete(
        id=athlete_id,
        name=profile.get("name"),
        sex=sex,
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
    )


def _segment_from_dict(segment: Dict[str, Any]) -> Segment:
    return Segment(**segment)


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
             flat: Optional[float], intensity_class: str, begin: int) -> Dict[str, Any]:
    seconds = int(seconds)
    if low is not None and high is not None and _pct(high) > _pct(low):
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
            steps.append(_tp_step("Free Ride", seg.seconds, None, None, 0.0, "active", t))
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
        "polyline": [],
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

    return Session(
        date=date,
        title=title,
        sport=_sport_for_type(session_type),
        type=session_type,
        origin=_session_origin(session_type),
        duration_s=int(duration_sec),
        tss=int(metrics["tss"]),
        segments=segments,
        source_file=zwo_path.name,
        description=zwo_structure.get("description"),
        tp_kind=tp_kind,
        workout_type_value_id=workout_type_value_id,
        tss_planned=round(float(metrics["tss"]), 1),
        total_time_planned=round(duration_sec / 3600, 4) if duration_sec else 0.0,
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
    for week_data in plan_dates.get("weeks", []):
        week = Week(number=int(week_data.get("week", len(weeks) + 1)), phase=week_data.get("phase"))
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


def build_plan_ir(athlete_id: str) -> PlanIR:
    """Aggregate an athlete's existing outputs and write ``plan_ir.json``.

    Missing artifacts yield warnings and a partial object.  This makes G0 safe
    to invoke as an advisory final package step while historical packages have
    uneven artifact coverage.
    """
    athlete_dir = ATHLETES_DIR / athlete_id
    profile = _load_yaml(athlete_dir / "profile.yaml")
    fueling_data = _load_yaml(athlete_dir / "fueling.yaml")
    plan_dates = _load_yaml(athlete_dir / "plan_dates.yaml")
    _load_yaml(athlete_dir / "weekly_structure.yaml")  # Reflected input; scheduling moves to PlanIR in G4.

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
    )
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
