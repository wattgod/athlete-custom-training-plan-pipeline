"""Canonical metric-neutral per-session training model (A1.1).

Phase 3 keeps the mature calendar/block builder as a private in-memory compiler,
then finalizes and validates this object before publication. ZWO, PlanIR,
preview, apply-contract, guide control evidence, and TP polyline are projections
of this authority. Each segment has exactly one typed prescription source.
"""

from __future__ import annotations

import json
import html
import math
import os
import re
import tempfile
from types import SimpleNamespace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from derived_registry import entry as derived_entry, validate_registry
from delivery_render import sanitize_athlete_description, sanitize_athlete_title
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


def normalize_target_effort(target_type: str, value: Any) -> Optional[float]:
    """Map one typed target to the legacy-neutral session-effort axis.

    Power ratios already use that axis. HR targets are inverted through the
    exact mapping used when the canonical prescription was authored; RPE uses
    the midpoint of its authored band. This deliberately avoids comparing raw
    %LTHR, %HRmax, or 0-10 RPE values with power-IF thresholds.
    """
    numeric = _num(value)
    if numeric is None:
        return None
    if target_type == "power_pct_ftp":
        return numeric
    if target_type == "pct_lthr":
        return _piecewise(numeric, (
            (.55, .35), (.68, .55), (.83, .75), (.94, .87),
            (1.05, 1.05), (1.12, 1.20), (1.16, 1.50),
        ))
    if target_type == "pct_hrmax":
        return _piecewise(numeric, (
            (.48, .35), (.60, .55), (.75, .75), (.85, .87),
            (.92, 1.05), (.98, 1.20), (1.00, 1.50),
        ))
    if target_type == "rpe":
        return _piecewise(numeric, (
            (1, .40), (2, .50), (4, .65), (6, .815),
            (8, .965), (9, 1.13), (10, 1.30),
        ))
    return None


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
_FTP_TARGET = re.compile(
    r"\b\d+(?:\.\d+)?\s*%(?:\s*(?:[-–]|->|→)\s*"
    r"\d+(?:\.\d+)?\s*%)?\s*FTP\b|"
    r"\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%\s*FTP\b",
    re.I,
)
_PERCENT_TARGET = re.compile(
    r"@?\s*\b\d+(?:\.\d+)?\s*%(?:\s*(?:[-–]|->|→)\s*"
    r"\d+(?:\.\d+)?\s*%)?|"
    r"@?\s*\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)\s*%",
    re.I,
)


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


def metric_neutral_description(value: Any, control: Dict[str, Any]) -> str:
    """Remove power-only prose from a non-power workout description.

    Descriptions are execution copy, not a compatibility dump. A relative
    percentage without an athlete power anchor is no more useful than watts,
    even when the executable structure has already been converted to RPE/HR.
    """
    text = metric_neutral_text(value, control)
    if control["control_metric"] == "power":
        return text
    text = re.sub(
        r"(?im)^\s*-?\s*Target effort:\s*\d+(?:\.\d+)?"
        r"(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%\s+of\s+"
        r"A-race effort\s*$",
        "- Target effort: hard and controlled. Saturday gets first claim.",
        text,
    )
    text = _PERCENT_TARGET.sub("the written effort", text)
    text = re.sub(
        r"the (?:written|prescribed) effort\s*(?:[-–]|->|→)\s*"
        r"the (?:written|prescribed) effort",
        "the written effort range",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bAverage effort\s*[×x]\s*0\.95\s*=\s*training anchor\.?",
        "Record the completed field-test effort for review.",
        text,
        flags=re.I,
    )
    return text


def project_guide_html(html_text: str, model: Dict[str, Any]) -> str:
    """Project control targets/re-anchor evidence from the canonical model."""
    validate_canonical_model(model)
    control = model["athlete"]
    if control["control_metric"] == "power":
        return html_text
    projected = metric_neutral_text(html_text, control)
    field_test = next((
        session for session in model.get("sessions") or []
        if "field test" in str(session.get("title") or "").lower()
    ), None)
    reanchor = control.get("reanchor") or {}
    evidence = (
        '<section id="canonical-control" class="section">'
        '<h2>Week 1 Control &amp; Re-anchor</h2>'
        f'<p><strong>{html.escape(str((field_test or {}).get("title") or "Field Test"))}</strong></p>'
        f'<p>{html.escape(str(reanchor.get("action") or "Record the measured result and update future targets."))}</p>'
        '</section>'
    )
    return projected.replace("</body>", evidence + "\n</body>", 1)


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
    zwo = segment.get("zwo")
    if isinstance(zwo, dict):
        zwo = json.loads(json.dumps(zwo))
        if control["control_metric"] != "power":
            for child in zwo.get("children") or []:
                attributes = child.get("attributes") or {}
                if "message" in attributes:
                    attributes["message"] = metric_neutral_text(
                        attributes["message"], control)
        result["zwo"] = zwo
    return result


def _compiler_session(
    stem: str, xml_text: str, *, date: Optional[str], is_race_day: bool,
    manifest: Dict[str, Any], ftp: Optional[float],
) -> SimpleNamespace:
    """Compile a private in-memory authoring document into neutral fields."""
    from zwo_parser import parse_zwo_structure_text, parse_zwo_text
    import plan_ir as plan_ir_module

    structure = parse_zwo_structure_text(xml_text, source_name=stem)
    metrics = parse_zwo_text(xml_text, ftp or 1.0, source_name=stem)
    title = structure["name"].replace("_", " ")
    session_type = plan_ir_module._session_type(title, is_race_day)
    entry = manifest.get(stem, {})
    tp_kind = entry.get("tp_kind") or plan_ir_module._default_tp_kind(session_type)
    workout_type_id = entry.get("workout_type_value_id")
    if workout_type_id is None:
        workout_type_id = plan_ir_module.TP_WORKOUT_TYPE_VALUE_ID.get(tp_kind)
    duration_s = int(metrics["duration_sec"])
    # R1 fix wave (SPEC_LIBRARY_SELECTION.md regrade, worst offender +78%):
    # `metrics["tss"]` is recomputed from the internal C2-converted ZWO via
    # normalized power -- min-only sprint targets render as flat Power
    # blocks there, which massively inflates 4th-power NP (an authored 57.9
    # TSS session placed as 103). For a library-resolved session the
    # AUTHORED tss/if_planned (carried through the naming manifest as
    # library_tss/library_if_planned, generate_athlete_package.py's
    # resolution pass) are authoritative end-to-end for every
    # athlete-facing number; the internal ZWO-derived metrics stay
    # untouched for the preview renderer, which is the only other consumer
    # of this same parse.
    _library_tss = entry.get("library_tss")
    _tss_value = _library_tss if _library_tss is not None else metrics["tss"]
    return SimpleNamespace(
        date=date, title=title,
        sport=plan_ir_module._sport_for_type(session_type), type=session_type,
        origin=plan_ir_module._session_origin(session_type), duration_s=duration_s,
        tss=int(round(_tss_value)),
        segments=[SimpleNamespace(**segment) for segment in structure["segments"]],
        source_file=f"{stem}.zwo", description=structure.get("description"),
        tp_kind=tp_kind, workout_type_value_id=workout_type_id,
        tss_planned=round(float(_tss_value), 1),
        total_time_planned=plan_ir_module._round_time_planned_hours(duration_s),
        series_id=entry.get("series_id"), series_index=entry.get("series_index"),
        series_total=entry.get("series_total"), order_on_day=entry.get("order_on_day"),
        strength_template=entry.get("strength_template"),
        archetype_id=entry.get("archetype_id"),
        display_name=entry.get("display_name") or title, filename_stem=stem,
        race=entry.get("race"), zwo_author=structure.get("author"),
        zwo_sport_type=structure.get("sport_type"),
        # C4 (docs/SPEC_LIBRARY_SELECTION.md D4): role and library_item_id
        # carry through from the naming manifest so the canonical model (and
        # everything projected from it -- plan_ir.json, tp_manifest.json)
        # can identify library-resolved sessions.
        role=entry.get("role"), library_item_id=entry.get("library_item_id"),
        library_rpe_text=entry.get("library_rpe_text"),
    )


def _compile_authored_weeks(
    documents: Dict[str, str], manifest: Dict[str, Any],
    plan_dates: Dict[str, Any], profile: Dict[str, Any],
) -> List[SimpleNamespace]:
    """Finalize calendar sessions without reading or globbing published ZWOs."""
    import plan_ir as plan_ir_module
    ftp = _num((profile.get("fitness_markers") or {}).get("ftp_watts"))
    remaining = set(documents)
    weeks: List[SimpleNamespace] = []
    for index, week_data in enumerate(plan_dates.get("weeks") or [], 1):
        sessions = []
        for day in week_data.get("days") or []:
            prefix = str(day.get("workout_prefix") or "")
            matches = sorted(stem for stem in remaining if prefix and stem.startswith(prefix))
            is_race = bool(day.get("is_race_day") or day.get("is_b_race_day"))
            if matches:
                for stem in matches:
                    remaining.remove(stem)
                    sessions.append(_compiler_session(
                        stem, documents[stem], date=day.get("date"),
                        is_race_day=is_race, manifest=manifest, ftp=ftp))
            else:
                sessions.append(plan_ir_module._rest_session(day.get("date")))
        for raw in profile.get("recurring_sessions") or []:
            if not raw.get("locked"):
                continue
            for day in week_data.get("days") or []:
                if str(day.get("day_name", day.get("day", "")))[:3].title() != raw.get("day"):
                    continue
                sessions.append(SimpleNamespace(
                    date=day.get("date"), title=raw.get("title") or "Fixed external session",
                    sport="cycling", type="external_fixed", origin="athlete_fixed",
                    duration_s=int(raw.get("duration_min", 0)) * 60,
                    tss=int(raw.get("tss", 0) or 0), segments=[], source_file=None,
                    description=None, tp_kind="bike", workout_type_value_id=2,
                    tss_planned=float(raw.get("tss", 0) or 0),
                    total_time_planned=float(raw.get("duration_min", 0)) / 60,
                    series_id=None, series_index=None, series_total=None,
                    order_on_day=None, strength_template=None, archetype_id=None,
                    display_name=raw.get("title") or "Fixed external session",
                    filename_stem=None, race=None, zwo_author=None,
                    zwo_sport_type=None,
                ))
        weeks.append(SimpleNamespace(
            number=int(week_data.get("week", index)),
            phase=week_data.get("phase"), sessions=sessions))
    by_number = {week.number: week for week in weeks}
    for stem in sorted(remaining):
        match = re.match(r"W(\d+)_", stem)
        number = int(match.group(1)) if match else 0
        week = by_number.get(number)
        if week is None:
            week = SimpleNamespace(number=number, phase=None, sessions=[])
            by_number[number] = week
            weeks.append(week)
        week.sessions.append(_compiler_session(
            stem, documents[stem], date=None,
            is_race_day="RACE_DAY" in stem.upper(), manifest=manifest, ftp=ftp))
    return weeks


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
    authored_documents: Optional[Dict[str, str]] = None,
    naming_manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Finalize the authority from private compiler documents before publish."""
    athlete_dir = Path(athlete_dir)
    import yaml
    profile = yaml.safe_load((athlete_dir / "profile.yaml").read_text()) or {}
    control = determine_control(profile)

    # Production passes in-memory compiler documents. No published ZWO path is
    # read, and the final ZWO projection is emitted only after this model has
    # validated and persisted. ``authored_dir`` remains compatibility-only for
    # historical fixtures and is not used by package generation.
    import plan_ir as plan_ir_module
    if authored_documents is not None:
        fueling_data = yaml.safe_load((athlete_dir / "fueling.yaml").read_text()) or {}
        plan_dates_data = plan_dates or (
            yaml.safe_load((athlete_dir / "plan_dates.yaml").read_text()) or {})
        athlete = plan_ir_module._athlete_from_profile(athlete_id, profile)
        prescription_data = plan_ir_module.prescription_from_fueling(fueling_data)
        target = profile.get("target_race", {}) or {}
        mental = profile.get("mental_game", {}) or {}
        reflected = SimpleNamespace(
            athlete=athlete,
            race_snapshot=plan_ir_module._race_from_artifacts(
                profile, fueling_data, plan_dates_data),
            fueling=(plan_ir_module.FuelingPrescription(**prescription_data)
                     if prescription_data else None),
            weeks=_compile_authored_weeks(
                dict(authored_documents), dict(naming_manifest or {}),
                plan_dates_data, profile),
            notes=[{"kind": "mental_training", "id": key, "text": str(value)}
                   for key, value in mental.items()
                   if value not in (None, "", "none", "no")],
            entitlements=[{"kind": "course", "race": target.get("name"),
                           "race_date": target.get("date"),
                           "race_id": target.get("race_id")}],
            attachments=[{"id": "guide", "kind": "guide",
                          "path": "training_guide.html"}],
        )
    elif authored_dir is None or Path(authored_dir).resolve() == athlete_dir.resolve():
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
            title = sanitize_athlete_title(
                field_test_title if is_field_test and
                control["control_metric"] != "power" else
                metric_neutral_text(raw_session.title, control))
            description = metric_neutral_description(
                raw_session.description, control)
            if is_field_test and control["control_metric"] != "power":
                description = (description.rstrip() + "\n\nRE-ANCHOR: Complete this Week 1 field test, "
                               "record the measured result, and update future targets.").strip()
            description = sanitize_athlete_description(description)
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
                # C4 (D4): getattr defaults -- the non-authored-documents
                # reflection branches build plain PlanIR Session objects,
                # which don't carry `role` (block-builder-only concept) and
                # may predate the `library_item_id` field.
                "role": getattr(raw_session, "role", None),
                "library_item_id": getattr(raw_session, "library_item_id", None),
                "library_rpe_text": getattr(raw_session, "library_rpe_text", None),
                "zwo_projection": ({
                    "author": getattr(raw_session, "zwo_author", None),
                    "sport_type": getattr(raw_session, "zwo_sport_type", None),
                } if getattr(raw_session, "source_file", None) else None),
            })

    generated_at = str((profile.get("fulfillment") or {}).get("generation_at") or "")
    generation_revision = int(
        (profile.get("fulfillment") or {}).get("generation_revision") or 1
    )
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
        "calendar_protection": dict(profile.get("calendar_protection") or {}),
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
                revision=generation_revision,
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
                revision=generation_revision,
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
    protection = model.get("calendar_protection") or {}
    if not isinstance(protection, dict):
        raise CanonicalModelError("calendar protection intent must be an object")
    if protection and not isinstance(protection.get("requested"), bool):
        raise CanonicalModelError("calendar protection requested must be boolean")
    if protection and not isinstance(protection.get("referenced_dates", []), list):
        raise CanonicalModelError("calendar protection referenced_dates must be an array")
    for session in model.get("sessions") or []:
        title = str(session.get("title") or "")
        if title and sanitize_athlete_title(title) != title:
            raise CanonicalModelError("athlete-visible title contains an internal token")
        description = str(session.get("description") or "")
        if description and sanitize_athlete_description(description) != description:
            raise CanonicalModelError(
                "athlete-visible description contains compiler-only copy")
        for segment in session.get("segments") or []:
            target = segment.get("target") or {}
            if target.get("type") not in TARGET_TYPES:
                raise CanonicalModelError("segment has no typed target")
            target_type = target["type"]
            expected_type = (
                "power_pct_ftp" if athlete.get("control_metric") == "power" else
                "pct_lthr" if athlete.get("control_metric") == "hr"
                and athlete.get("control_basis") == "lthr" else
                "pct_hrmax" if athlete.get("control_metric") == "hr"
                and athlete.get("control_basis") == "hrmax" else "rpe"
            )
            if target_type not in {expected_type, "free"}:
                raise CanonicalModelError("segment target type disagrees with plan control")
            allowed_shapes = (
                [{"type"}] if target_type == "free" else
                [{"type", "on", "off"}] if segment.get("kind") == "intervals" else
                [{"type", "value"}, {"type", "low", "high"}]
            )
            if set(target) not in allowed_shapes:
                raise CanonicalModelError(
                    "segment target is not one exact discriminated-union branch")
            if target_type == "free" and segment.get("kind") != "free_ride":
                raise CanonicalModelError("free target is permitted only on free rides")
            if target_type != "free":
                for key, value in target.items():
                    if key == "type" or _num(value) is None:
                        if key != "type":
                            raise CanonicalModelError("segment target value is not finite")
                if target_type == "rpe" and any(
                    not (1 <= float(value) <= 10)
                    for key, value in target.items() if key != "type"
                ):
                    raise CanonicalModelError("RPE target is outside 1-10")


def _power_attribute(segment: Dict[str, Any], attribute: str) -> str:
    target = segment["target"]
    mapping = {
        "Power": "value", "PowerLow": "low", "PowerHigh": "high",
        "OnPower": "on", "OffPower": "off",
    }
    if attribute in mapping:
        return f"{float(target[mapping[attribute]]):.2f}"
    if attribute == "Duration":
        return str(int(segment.get("seconds") or 0))
    if attribute == "Repeat":
        return str(int(segment.get("repeat") or 1))
    if attribute == "OnDuration":
        return str(int(segment.get("on_seconds") or 0))
    if attribute == "OffDuration":
        return str(int(segment.get("off_seconds") or 0))
    return str((segment.get("zwo") or {}).get("extra_attributes", {}).get(attribute, ""))


def render_zwo_bytes(session: Dict[str, Any], control: Dict[str, Any]) -> bytes:
    """Render one executable projection solely from a validated session."""
    if control.get("control_metric") != "power":
        raise CanonicalModelError("ZWO projection requires measured-power control")
    projection = session.get("zwo_projection") or {}
    def text_value(value: Any) -> str:
        return str(value or "").replace("&", "&amp;").replace("<", "&lt;")

    def attr_value(value: Any) -> str:
        return (str(value).replace("&", "&amp;").replace('"', "&quot;")
                .replace("<", "&lt;").replace(">", "&gt;"))

    lines = ["<?xml version='1.0' encoding='UTF-8'?>", "<workout_file>"]
    if projection.get("author"):
        lines.append(f"  <author>{text_value(projection['author'])}</author>")
    lines.append(f"  <name>{text_value(session.get('title') or 'Session')}</name>")
    lines.append(f"  <description>{text_value(session.get('description') or '')}</description>")
    if projection.get("sport_type"):
        lines.append(f"  <sportType>{text_value(projection['sport_type'])}</sportType>")
    lines.append("  <workout>")
    for segment in session.get("segments") or []:
        recipe = segment.get("zwo") or {}
        tag = str(recipe.get("tag") or "")
        if not tag:
            raise CanonicalModelError("published session lacks a ZWO render recipe")
        attributes = []
        for attribute in recipe.get("attribute_order") or []:
            attributes.append(
                f'{attribute}="{attr_value(_power_attribute(segment, attribute))}"')
        opening = f"    <{tag}" + (" " + " ".join(attributes) if attributes else "")
        children = recipe.get("children") or []
        if not children:
            space = " " if recipe.get("empty_element_space") else ""
            lines.append(opening + space + "/>")
            continue
        lines.append(opening + ">")
        for child_recipe in children:
            child_tag = str(child_recipe.get("tag") or "textevent")
            child_attrs = "".join(
                f' {key}="{attr_value(value)}"'
                for key, value in (child_recipe.get("attributes") or {}).items())
            child_text = text_value(child_recipe.get("text") or "")
            if child_text:
                lines.append(
                    f"      <{child_tag}{child_attrs}>{child_text}</{child_tag}>")
            else:
                space = " " if child_recipe.get("empty_element_space", True) else ""
                lines.append(f"      <{child_tag}{child_attrs}{space}/>")
        lines.append(f"    </{tag}>")
    lines.extend(["  </workout>", "</workout_file>"])
    return "\n".join(lines).encode("utf-8")


def publish_zwo_projection(
    model: Dict[str, Any], athlete_dir: Path | str,
) -> List[Path]:
    """Publish ZWO + naming manifest only after canonical finalization."""
    validate_canonical_model(model)
    athlete_dir = Path(athlete_dir)
    workout_dir = athlete_dir / "workouts"
    workout_dir.mkdir(parents=True, exist_ok=True)
    for stale in workout_dir.glob("*.zwo"):
        stale.unlink()
    control = model["athlete"]
    if control["control_metric"] != "power":
        manifest_path = workout_dir / "naming_manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()
        return []
    paths: List[Path] = []
    manifest: Dict[str, Any] = {}
    for session in model.get("sessions") or []:
        source_file = session.get("source_file")
        if not source_file:
            continue
        path = workout_dir / Path(str(source_file)).name
        path.write_bytes(render_zwo_bytes(session, control))
        paths.append(path)
        manifest[path.stem] = {
            key: session.get(key) for key in (
                "filename_stem", "date", "week", "phase", "tp_kind",
                "workout_type_value_id", "series_id", "series_index",
                "series_total", "order_on_day", "strength_template",
                "archetype_id", "display_name", "race",
                # C4 (D4): published naming_manifest.json must keep carrying
                # role/library_item_id -- plan_ir.py's _load_naming_manifest
                # reads this on-disk file, not the in-memory authoring one.
                "role", "library_item_id", "library_rpe_text",
            ) if session.get(key) is not None
        }
        manifest[path.stem]["week_num"] = manifest[path.stem].pop("week", None)
    (workout_dir / "naming_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return paths


def load_canonical_model(path: Path | str) -> Dict[str, Any]:
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_canonical_model(model)
    return model


def _step_target(target: Dict[str, Any], key: str = "value",
                 all_out: bool = False,
                 control_metric: Optional[str] = None) -> List[Dict[str, int]]:
    kind = target.get("type")
    if kind == "rpe":
        if key in {"on", "off"}:
            value = target.get(key)
            return [{"minValue": int(round(float(value))),
                     "maxValue": int(round(float(value)))}]
        low, high, value = target.get("low"), target.get("high"), target.get("value")
        if low is not None and high is not None:
            minimum, maximum = sorted((int(round(float(low))), int(round(float(high)))))
        else:
            chosen = value if value is not None else high if high is not None else low
            minimum = maximum = int(round(float(chosen)))
        minimum = max(0, min(10, minimum))
        maximum = max(minimum, min(10, maximum))
        return [{"minValue": minimum, "maxValue": maximum}]
    if kind == "free":
        if control_metric == "rpe":
            return ([{"minValue": 10, "maxValue": 10}] if all_out else
                    [{"minValue": 1, "maxValue": 10}])
        # A target-less step is invisible: TP accepts the POST but the
        # calendar mini-chart draws a GAP, the polyline omits the step, and
        # the workout-detail builder can refuse the whole structure (found
        # on a live graded delivery). Free efforts get an explicit display
        # band: all-out efforts a hard band, anything else the floor. The
        # canonical target itself stays the pure {"type": "free"} branch —
        # all_out is a projection-time display decision.
        if all_out:
            return [{"minValue": 120, "maxValue": 170}]
        return [{"minValue": 0}]
    if key in {"on", "off"}:
        value = target.get(key)
        return [{"minValue": int(round(float(value) * 100))}]
    low, high, value = target.get("low"), target.get("high"), target.get("value")
    if low is not None and high is not None and float(high) > float(low):
        return [{"minValue": int(round(float(low) * 100)),
                 "maxValue": int(round(float(high) * 100))}]
    chosen = value if value is not None else high if high is not None else low
    return [{"minValue": int(round(float(chosen) * 100))}]


def project_tp_structure(session: Dict[str, Any], control: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Project canonical bike segments into a TP-native structured workout."""
    if session.get("tp_kind") != "bike":
        return None
    steps: List[Dict[str, Any]] = []
    cursor = 0

    def append(name: str, seconds: int, target: Dict[str, Any], intensity: str,
               key: str = "value", all_out: bool = False) -> None:
        nonlocal cursor
        block = {
            "type": "step",
            "length": {"value": 1, "unit": "repetition"},
            "steps": [{
                "name": name,
                "length": {"value": int(seconds), "unit": "second"},
                "targets": _step_target(
                    target, key, all_out=all_out,
                    control_metric=control.get("control_metric")),
                "intensityClass": intensity,
                # TP's builder expects the full imported-step shape; steps
                # without notes rendered fine on cards but not in detail.
                "notes": "",
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
            all_out = bool(re.search(
                r"all[- ]?out|max(?:imal)? effort",
                " ".join(str(segment.get(f) or "")
                         for f in ("name", "description")),
                re.I))
            append(segment.get("name") or "Step", int(segment.get("seconds") or 0),
                   target, intensity, all_out=all_out)
    if not steps:
        return None
    # FIX 10 (Aug 17 2026 adversarial grade): this function only ever
    # projects COMPOSED sessions (Act sims, midweek sims, other
    # synthesized cards) -- curated library items are placed byte-verbatim
    # with their own TP structure and never reach this segments-based path.
    # A composed session's ZWO renderer emits its literal warm-up/cool-down
    # as plain <SteadyState> blocks (never a <Warmup>/<Cooldown> ZWO tag),
    # so the round-tripped segment ``kind`` above is "steady_state" and the
    # intensity check falls through to the generic "active" default -- the
    # composed card's first and last blocks read exactly like its hardest
    # interval. Every composed session structurally begins and ends with
    # its own real warm-up/cool-down (see act_race_sim.py's
    # _compose_with_units/_compose_midweek_with_units), so tag them
    # explicitly here rather than trusting the per-segment kind alone. A
    # single-block session has no distinct warm-up/cool-down to disclose.
    # An "intervals"-kind boundary segment (its emitted last step is a
    # Recovery/"rest" block, never "active") and a "free_ride" boundary
    # segment (an unstructured effort -- e.g. an all-out test -- must never
    # be mislabeled a cool-down) are excluded.
    boundary_segments = session.get("segments") or []
    if len(steps) >= 2 and boundary_segments:
        for segment, block_index, boundary_intensity in (
            (boundary_segments[0], 0, "warmUp"),
            (boundary_segments[-1], -1, "coolDown"),
        ):
            if segment.get("kind") in ("intervals", "free_ride"):
                continue
            leaf_step = steps[block_index]["steps"][0]
            if leaf_step["intensityClass"] == "active":
                leaf_step["intensityClass"] = boundary_intensity
    metric = {
        "power": "percentOfFtp",
        "hr:lthr": "percentOfThresholdHr",
            "hr:hrmax": "percentOfMaxHr",
            "rpe:rpe": "rpe",
    }.get(f"{control.get('control_metric')}:{control.get('control_basis')}")
    if control.get("control_metric") == "power":
        metric = "percentOfFtp"
    if not metric:
        return None
    return {
        "structure": steps,
        "primaryLengthMetric": "duration",
        "primaryIntensityMetric": metric,
        "primaryIntensityTargetOrRange": "range" if metric == "rpe" else "target",
        "polyline": compute_polyline(steps),
        "importedFromZwo": True,
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
