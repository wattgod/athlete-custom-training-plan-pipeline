"""Canonical metric-neutral per-session training model (A1.1).

Phase 3 keeps the mature calendar/block builder, but all downstream plan
payloads consume this artifact.  The transitional workout renderer is used as
an internal authored-shape adapter while the model is assembled; HR/RPE
packages then remove those temporary ZWO files before any package artifact is
published.  Each segment has exactly one typed prescription source.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from derived_registry import entry as derived_entry, validate_registry
from tp_polyline import compute_polyline


MODEL_VERSION = "canonical_training_model/v1"
TARGET_TYPES = {"power_pct_ftp", "pct_lthr", "pct_hrmax", "rpe", "free"}


class CanonicalModelError(ValueError):
    """The canonical model or a projection violates A1 invariants."""


def _num(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def determine_control(profile: Dict[str, Any]) -> Dict[str, Any]:
    fitness = profile.get("fitness_markers", {}) or {}
    ftp = _num(fitness.get("ftp_watts"))
    power_basis = str(fitness.get("power_basis") or ("measured" if ftp else "none"))
    requested = str(
        fitness.get("requested_metric") or fitness.get("training_metric") or ""
    ).lower()
    lthr = _num(fitness.get("lthr"))
    hrmax = _num(fitness.get("max_hr"))

    if requested == "power" and power_basis == "measured" and ftp:
        metric, basis = "power", "ftp"
    elif requested == "hr" or (requested not in {"power", "rpe"} and (lthr or hrmax)):
        metric = "hr"
        basis = "lthr" if lthr else ("hrmax" if hrmax else "rpe_pending_lthr")
    elif requested == "rpe":
        metric, basis = "rpe", "rpe"
    elif power_basis == "measured" and ftp:
        metric, basis = "power", "ftp"
    elif lthr or hrmax:
        metric, basis = "hr", "lthr" if lthr else "hrmax"
    else:
        metric, basis = "rpe", "rpe"

    return {
        "control_metric": metric,
        "control_basis": basis,
        "power_basis": "measured" if power_basis == "measured" and ftp else "none",
        "ftp_watts": int(round(ftp)) if metric == "power" and ftp else None,
        "lthr_bpm": int(round(lthr)) if lthr else None,
        "hrmax_bpm": int(round(hrmax)) if hrmax else None,
        "requested_metric": requested or metric,
        "reanchor": fitness.get("reanchor") or {
            "required": metric != "power",
            "week": 1,
            "test": "field_test",
            "action": "Update the measured anchor after the Week 1 field test.",
        },
    }


def _piecewise(value: float, points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    if value <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if value <= x1:
            fraction = (value - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return pts[-1][1]


def _hr_ratio(value: float, basis: str) -> float:
    if basis == "lthr":
        points = ((.35, .55), (.55, .68), (.75, .83), (.87, .94),
                  (1.05, 1.05), (1.20, 1.12), (1.50, 1.16))
    else:
        points = ((.35, .48), (.55, .60), (.75, .75), (.87, .85),
                  (1.05, .92), (1.20, .98), (1.50, 1.00))
    return round(_piecewise(value, points), 3)


def _rpe(value: float) -> int:
    if value < .55:
        return 2
    if value < .76:
        return 4
    if value < .88:
        return 6
    if value < 1.06:
        return 8
    if value < 1.21:
        return 9
    return 10


def _target_value(value: Optional[float], target_type: str) -> Any:
    if value is None:
        return None
    if target_type == "power_pct_ftp":
        return round(value, 3)
    if target_type == "pct_lthr":
        return _hr_ratio(value, "lthr")
    if target_type == "pct_hrmax":
        return _hr_ratio(value, "hrmax")
    if target_type == "rpe":
        return _rpe(value)
    return None


def _segment_target(segment: Dict[str, Any], control: Dict[str, Any]) -> Dict[str, Any]:
    if segment.get("kind") == "free_ride":
        return {"type": "free"}
    if control["control_metric"] == "power":
        target_type = "power_pct_ftp"
    elif control["control_metric"] == "hr" and control["control_basis"] == "lthr":
        target_type = "pct_lthr"
    elif control["control_metric"] == "hr" and control["control_basis"] == "hrmax":
        target_type = "pct_hrmax"
    else:
        target_type = "rpe"

    if segment.get("kind") == "intervals":
        return {
            "type": target_type,
            "on": _target_value(_num(segment.get("on_power")), target_type),
            "off": _target_value(_num(segment.get("off_power")), target_type),
        }
    low = _num(segment.get("power_low"))
    high = _num(segment.get("power_high"))
    flat = _num(segment.get("power_target"))
    target: Dict[str, Any] = {"type": target_type}
    if low is not None:
        target["low"] = _target_value(low, target_type)
    if high is not None:
        target["high"] = _target_value(high, target_type)
    if flat is not None:
        target["value"] = _target_value(flat, target_type)
    if len(target) == 1:
        target["value"] = _target_value(.5, target_type)
    return target


def _metric_field_test_title(control: Dict[str, Any]) -> str:
    if control["control_metric"] == "power":
        return "FTP Field Test"
    if control["requested_metric"] == "hr" and control["control_basis"] == "lthr":
        return "LTHR Field Test"
    if control["requested_metric"] == "hr" and control["control_basis"] == "hrmax":
        return "HRmax Field Test"
    if control["requested_metric"] == "hr":
        return "HR Field Test"
    return "RPE Field Test"


_WATT_FIGURE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:w|watts?)\b", re.I)
_FTP_TARGET = re.compile(r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%\s*FTP\b", re.I)


def metric_neutral_text(value: Any, control: Dict[str, Any]) -> str:
    text = str(value or "")
    if control["control_metric"] == "power":
        return text
    text = _WATT_FIGURE.sub("measured output", text)
    text = _FTP_TARGET.sub("the prescribed effort", text)
    text = re.sub(r"\bFTP\s+test\b", "field test", text, flags=re.I)
    text = re.sub(r"\bFTP\b", "training anchor", text, flags=re.I)
    text = re.sub(r"\bwatts?\b", "output", text, flags=re.I)
    text = re.sub(r"\bpower\b", "effort", text, flags=re.I)
    text = re.sub(r"\bZWO files?\b", "structured workouts", text, flags=re.I)
    return text


def _canonical_segment(segment: Dict[str, Any], control: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "name": segment.get("name") or str(segment.get("kind") or "segment"),
        "seconds": int(segment.get("seconds") or 0),
        "kind": str(segment.get("kind") or "steady_state"),
        "target": _segment_target(segment, control),
    }
    for key in ("repeat", "on_seconds", "off_seconds"):
        if segment.get(key) is not None:
            result[key] = int(segment[key])
    return result


def target_summary(target: Dict[str, Any]) -> str:
    kind = target.get("type")
    if kind == "free":
        return "Self-paced field effort"
    label = {
        "power_pct_ftp": "% of measured FTP",
        "pct_lthr": "% LTHR",
        "pct_hrmax": "% HRmax",
        "rpe": "RPE",
    }.get(kind, str(kind))
    if "on" in target:
        on, off = target.get("on"), target.get("off")
        if kind in {"power_pct_ftp", "pct_lthr", "pct_hrmax"}:
            return f"{round(float(on) * 100)} / {round(float(off) * 100)} {label}"
        return f"{label} {on} / {off}"
    low, high, value = target.get("low"), target.get("high"), target.get("value")
    if kind in {"power_pct_ftp", "pct_lthr", "pct_hrmax"}:
        if low is not None and high is not None:
            return f"{round(float(low) * 100)}-{round(float(high) * 100)} {label}"
        chosen = value if value is not None else high if high is not None else low
        return f"{round(float(chosen) * 100)} {label}"
    chosen = value if value is not None else high if high is not None else low
    return f"{label} {chosen}"


def build_canonical_model(
    athlete_id: str,
    athlete_dir: Path | str,
    *,
    plan_dates: Optional[Dict[str, Any]] = None,
    authored_dir: Path | str | None = None,
) -> Dict[str, Any]:
    """Build the canonical artifact from the finalized calendar/render shape."""
    athlete_dir = Path(athlete_dir)
    import yaml
    profile = yaml.safe_load((athlete_dir / "profile.yaml").read_text()) or {}
    control = determine_control(profile)

    # Bootstrap through the mature authored workout shape exactly once.
    # For non-power plans ``authored_dir`` is a short-lived private compiler
    # directory, never the athlete artifact tree. Subsequent PlanIR, preview,
    # contract and guide projections read canonical_training_model.json.
    import plan_ir as plan_ir_module
    if authored_dir is None or Path(authored_dir).resolve() == athlete_dir.resolve():
        original_base = plan_ir_module.ATHLETES_DIR
        try:
            plan_ir_module.ATHLETES_DIR = athlete_dir.parent
            reflected = plan_ir_module.build_plan_ir(
                athlete_id, prefer_canonical=False, plan_dates_override=plan_dates)
        finally:
            plan_ir_module.ATHLETES_DIR = original_base
    else:
        import yaml
        source_dir = Path(authored_dir)
        fueling_data = yaml.safe_load((athlete_dir / "fueling.yaml").read_text()) or {}
        plan_dates_data = plan_dates or (
            yaml.safe_load((athlete_dir / "plan_dates.yaml").read_text()) or {})
        athlete = plan_ir_module._athlete_from_profile(athlete_id, profile)
        prescription_data = plan_ir_module.prescription_from_fueling(fueling_data)
        target = profile.get("target_race", {}) or {}
        mental = profile.get("mental_game", {}) or {}
        guide_path = ("training_guide.pdf" if (athlete_dir / "training_guide.pdf").exists()
                      else "training_guide.html")
        reflected = plan_ir_module.PlanIR(
            athlete=athlete,
            race_snapshot=plan_ir_module._race_from_artifacts(
                profile, fueling_data, plan_dates_data),
            fueling=(plan_ir_module.FuelingPrescription(**prescription_data)
                     if prescription_data else None),
            weeks=plan_ir_module._build_weeks(
                source_dir, plan_dates_data, athlete,
                profile.get("recurring_sessions", []) or []),
            notes=[{"kind": "mental_training", "id": key, "text": str(value)}
                   for key, value in mental.items()
                   if value not in (None, "", "none", "no")],
            entitlements=[{"kind": "course", "race": target.get("name"),
                           "race_date": target.get("date"),
                           "race_id": target.get("race_id")}],
            attachments=[{"id": "guide", "kind": "guide", "path": guide_path}],
            fulfillment=plan_ir_module._fulfillment_from_file(athlete_dir),
        )

    sessions: List[Dict[str, Any]] = []
    field_test_title = _metric_field_test_title(control)
    for week in reflected.weeks:
        ordinals_by_date: Dict[str, int] = {}
        for raw_session in week.sessions:
            date_key = str(raw_session.date or "undated")
            ordinals_by_date[date_key] = ordinals_by_date.get(date_key, 0) + 1
            ordinal = ordinals_by_date[date_key]
            raw = raw_session.__dict__.copy()
            raw_segments = [segment.__dict__.copy() for segment in raw_session.segments]
            is_field_test = raw_session.type == "ftp_test" or "field test" in raw_session.title.lower()
            title = field_test_title if is_field_test else metric_neutral_text(raw_session.title, control)
            description = metric_neutral_text(raw_session.description, control)
            if is_field_test:
                description = (description.rstrip() + "\n\nRE-ANCHOR: Complete this Week 1 field test, "
                               "record the measured result, and update future targets.").strip()
            segments = [_canonical_segment(segment, control) for segment in raw_segments]
            summaries = [target_summary(segment["target"]) for segment in segments]
            sessions.append({
                "week": week.number,
                "phase": week.phase,
                "date": raw_session.date,
                "daily_ordinal": ordinal,
                "title": title,
                "description": description,
                "sport": raw_session.sport,
                "session_type": raw_session.type,
                "origin": raw_session.origin,
                "duration_s": raw_session.duration_s,
                "tss": raw_session.tss,
                "segments": segments,
                "target_summary": "; ".join(dict.fromkeys(summaries)),
                "source_file": raw_session.source_file if control["control_metric"] == "power" else None,
                "filename_stem": raw_session.filename_stem,
                "tp_kind": raw_session.tp_kind,
                "workout_type_value_id": raw_session.workout_type_value_id,
                "tss_planned": raw_session.tss_planned,
                "total_time_planned": raw_session.total_time_planned,
                "series_id": raw_session.series_id,
                "series_index": raw_session.series_index,
                "series_total": raw_session.series_total,
                "order_on_day": raw_session.order_on_day,
                "strength_template": raw_session.strength_template,
                "archetype_id": raw_session.archetype_id,
                "display_name": title,
                "race": raw_session.race,
            })

    generated_at = str((profile.get("fulfillment") or {}).get("generation_at") or "")
    if not generated_at:
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    model = {
        "model_version": MODEL_VERSION,
        "athlete": {
            "id": athlete_id,
            "name": profile.get("name"),
            **control,
        },
        "race_snapshot": reflected.race_snapshot.__dict__,
        "sessions": sessions,
        "notes": reflected.notes,
        "attachments": reflected.attachments,
        "entitlements": reflected.entitlements,
        "fueling": reflected.fueling.to_dict() if reflected.fueling else None,
        "derived_values": validate_registry([
            derived_entry(
                id="CANONICAL_CONTROL", field="athlete.control_metric",
                value_class="inferred",
                basis="measured-anchor availability and athlete-requested metric",
                inputs={
                    "requested_metric": control["requested_metric"],
                    "power_basis": control["power_basis"],
                    "control_basis": control["control_basis"],
                },
                sensitivity="personal", at=generated_at,
            ),
            derived_entry(
                id="CANONICAL_SESSION_TARGETS", field="sessions",
                value_class="inferred",
                basis=("authored relative-intensity segments projected through the "
                       f"{control['control_basis']} target rule"),
                inputs={
                    "session_count": len(sessions),
                    "control_metric": control["control_metric"],
                    "control_basis": control["control_basis"],
                },
                sensitivity="personal", at=generated_at,
            ),
        ]),
    }
    validate_canonical_model(model)
    _atomic_json(athlete_dir / "canonical_training_model.json", model)

    if control["control_metric"] != "power":
        for zwo in (athlete_dir / "workouts").glob("*.zwo"):
            zwo.unlink()
    return model


def validate_canonical_model(model: Dict[str, Any]) -> None:
    if not isinstance(model, dict) or model.get("model_version") != MODEL_VERSION:
        raise CanonicalModelError("unknown canonical model version")
    athlete = model.get("athlete") or {}
    if athlete.get("control_metric") not in {"power", "hr", "rpe"}:
        raise CanonicalModelError("invalid control metric")
    if athlete.get("power_basis") not in {"measured", "none"}:
        raise CanonicalModelError("invalid power basis")
    if athlete.get("power_basis") == "none" and athlete.get("ftp_watts") is not None:
        raise CanonicalModelError("null-power model carries an FTP value")
    for session in model.get("sessions") or []:
        for segment in session.get("segments") or []:
            target = segment.get("target") or {}
            if target.get("type") not in TARGET_TYPES:
                raise CanonicalModelError("segment has no typed target")
            if set(target) == {"type"} and target.get("type") != "free":
                raise CanonicalModelError("segment target has no prescription value")


def load_canonical_model(path: Path | str) -> Dict[str, Any]:
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_canonical_model(model)
    return model


def _step_target(target: Dict[str, Any], key: str = "value") -> List[Dict[str, int]]:
    kind = target.get("type")
    if kind == "free":
        return []
    if key in {"on", "off"}:
        value = target.get(key)
        return [{"minValue": int(round(float(value) * 100))}] if kind != "rpe" else []
    low, high, value = target.get("low"), target.get("high"), target.get("value")
    if kind == "rpe":
        return []
    if low is not None and high is not None and float(high) > float(low):
        return [{"minValue": int(round(float(low) * 100)),
                 "maxValue": int(round(float(high) * 100))}]
    chosen = value if value is not None else high if high is not None else low
    return [{"minValue": int(round(float(chosen) * 100))}]


def project_tp_structure(session: Dict[str, Any], control: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Project TP-native structure; RPE remains explicit in description."""
    if session.get("tp_kind") != "bike" or control.get("control_metric") == "rpe":
        return None
    steps: List[Dict[str, Any]] = []
    cursor = 0

    def append(name: str, seconds: int, target: Dict[str, Any], intensity: str, key: str = "value") -> None:
        nonlocal cursor
        block = {
            "type": "step",
            "length": {"value": 1, "unit": "repetition"},
            "steps": [{
                "name": name,
                "length": {"value": int(seconds), "unit": "second"},
                "targets": _step_target(target, key),
                "intensityClass": intensity,
            }],
            "begin": cursor,
            "end": cursor + int(seconds),
        }
        steps.append(block)
        cursor = block["end"]

    for segment in session.get("segments") or []:
        target = segment["target"]
        if segment.get("kind") == "intervals":
            for _ in range(int(segment.get("repeat") or 1)):
                append("Work", int(segment.get("on_seconds") or 0), target, "active", "on")
                append("Recovery", int(segment.get("off_seconds") or 0), target, "rest", "off")
        else:
            intensity = "warmUp" if segment.get("kind") == "warmup" else (
                "coolDown" if segment.get("kind") == "cooldown" else "active")
            append(segment.get("name") or "Step", int(segment.get("seconds") or 0), target, intensity)
    if not steps:
        return None
    metric = {
        "power": "percentOfFtp",
        "hr:lthr": "percentOfThresholdHr",
        "hr:hrmax": "percentOfMaxHr",
    }.get(f"{control.get('control_metric')}:{control.get('control_basis')}")
    if control.get("control_metric") == "power":
        metric = "percentOfFtp"
    if not metric:
        return None
    return {
        "structure": steps,
        "primaryLengthMetric": "duration",
        "primaryIntensityMetric": metric,
        "primaryIntensityTargetOrRange": "target",
        "polyline": compute_polyline(steps),
    }


def _atomic_json(path: Path, value: Dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
