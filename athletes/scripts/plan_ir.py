#!/usr/bin/env python3
"""PlanIR v0: a non-authoring aggregation of generated plan artifacts.

G0 intentionally reads the package the pipeline has already produced.  It is
not an input to ZWO, guide, or fueling generation yet; later tickets migrate
those serializers to project this object instead.
"""

from __future__ import annotations

import json
import re
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
        verified_at=_first(target, "verified_at") or _first(race, "verified_at"),
        event_year=event_year,
        course_variant=_first(target, "course_variant") or _first(race, "course_variant"),
    )


def _segment_from_dict(segment: Dict[str, Any]) -> Segment:
    return Segment(**segment)


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


def _session_from_zwo(zwo_path: Path, date: Optional[str], is_race_day: bool, ftp: Optional[float]) -> Session:
    structure = parse_zwo_structure(zwo_path)
    # TSS is relative to power ratios, but the shared preview parser needs a
    # numeric FTP to retain its established result shape.  This fallback is
    # calculation-only and is never written back to athlete facts.
    metrics = parse_zwo(zwo_path, ftp or 200.0)
    title = structure["name"].replace("_", " ")
    session_type = _session_type(title, is_race_day)
    return Session(
        date=date,
        title=title,
        sport=_sport_for_type(session_type),
        type=session_type,
        origin=_session_origin(session_type),
        duration_s=int(metrics["duration_sec"]),
        tss=int(metrics["tss"]),
        segments=[_segment_from_dict(segment) for segment in structure["segments"]],
        source_file=zwo_path.name,
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
    )


def _week_number_from_filename(path: Path) -> Optional[int]:
    match = re.match(r"W(\d+)_", path.name)
    return int(match.group(1)) if match else None


def _build_weeks(
    athlete_dir: Path,
    plan_dates: Dict[str, Any],
    athlete: Athlete,
) -> List[Week]:
    zwo_paths = sorted((athlete_dir / "workouts").glob("*.zwo")) if (athlete_dir / "workouts").exists() else []
    if not zwo_paths:
        warnings.warn("PlanIR: optional artifact missing: workouts/*.zwo", RuntimeWarning, stacklevel=2)

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
                    week.sessions.append(_session_from_zwo(match, day.get("date"), is_race_day, athlete.ftp))
            else:
                # Calendar days without a rendered ZWO are real rest days in the
                # v0 reflection, rather than omitted holes in the plan calendar.
                week.sessions.append(_rest_session(day.get("date")))
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
        week.sessions.append(_session_from_zwo(zwo_path, None, "RACE_DAY" in zwo_path.name.upper(), athlete.ftp))
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
    plan_ir = PlanIR(
        athlete=athlete,
        race_snapshot=_race_from_artifacts(profile, fueling_data, plan_dates),
        fueling=fueling,
        weeks=_build_weeks(athlete_dir, plan_dates, athlete),
        fulfillment=_fulfillment_from_file(athlete_dir),
    )
    output_path = athlete_dir / "plan_ir.json"
    try:
        output_path.write_text(json.dumps(plan_ir.to_dict(), indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        warnings.warn(f"PlanIR: could not write plan_ir.json: {exc}", RuntimeWarning, stacklevel=2)
    return plan_ir


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 plan_ir.py <athlete_id>")
        raise SystemExit(2)
    build_plan_ir(sys.argv[1])
