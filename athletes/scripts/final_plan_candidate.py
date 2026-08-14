"""Build and freeze the closed ``FinalPlanCandidate/v1`` E1 artifact."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml

from archetype import derive_discipline
from earned_selection import (
    CONFIG_DIR, ROOT, VERSION_VECTOR, canonical_digest, canonical_json,
)


CANDIDATE_VERSION = "FinalPlanCandidate/v1"
CONFIG_PATHS = {
    "archetype_ids": "repo:athletes/config/archetype_ids.json",
    "purpose_registry": "repo:athletes/config/purpose_registry.yaml",
    "quality_gates": "repo:athletes/config/quality_gates.yaml",
    "rule_registry": "repo:athletes/config/rule_registry.yaml",
    "producer_registry": "repo:athletes/config/non_native_producers.yaml",
    "phase_purpose_registry": "repo:athletes/config/phase_purpose_registry.yaml",
    "methodologies": "repo:athletes/scripts/config/methodologies.yaml",
    "methodology_profiles": "repo:athletes/config/methodology_profiles.yaml",
    "fueling_policy": "repo:athletes/scripts/fueling_policy.py",
    "plan_dates": "athlete:plan_dates.yaml",
    "weekly_structure": "athlete:weekly_structure.yaml",
    "block_notes": "repo:athletes/config/block_notes.yaml",
    "strength_periodization": "repo:athletes/config/strength_periodization.yaml",
    "tss_guardrails": "repo:athletes/config/tss_guardrails.yaml",
    "rollout": "repo:athletes/config/earned_selection_rollout.yaml",
}
GUIDE_INPUTS = (
    "profile.yaml", "derived.yaml", "plan_dates.yaml", "methodology.yaml",
    "fueling.yaml", "weekly_structure.yaml",
)
PHASES = {
    "pre_plan": "transition", "base": "base", "build": "build",
    "peak": "race_prep", "maintenance": "maintenance",
    "taper": "racing", "race": "racing",
}


class FinalPlanCandidateError(ValueError):
    pass


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FinalPlanCandidateError(f"required config unavailable: {path.name}") from exc
    if not isinstance(value, dict):
        raise FinalPlanCandidateError(f"required config malformed: {path.name}")
    return value


def _digest_named(path: str, athlete_dir: Path) -> str:
    prefix, relative = path.split(":", 1)
    source = ROOT / relative if prefix == "repo" else athlete_dir / relative
    try:
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError as exc:
        raise FinalPlanCandidateError(f"digest source unavailable: {path}") from exc


def snapshot_manifest(athlete_dir: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    source = CONFIG_DIR / "workout_certification.json"
    try:
        manifest = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalPlanCandidateError("certification manifest unavailable") from exc
    if (manifest.get("schema_version") != "certification_manifest/v1"
            or manifest.get("version_vector") != VERSION_VECTOR):
        raise FinalPlanCandidateError("certification manifest version mismatch")
    snapshot = athlete_dir / "certification_manifest.json"
    snapshot.write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                                   allow_nan=False) + "\n", encoding="utf-8")
    reread = json.loads(snapshot.read_text(encoding="utf-8"))
    if reread != manifest:
        raise FinalPlanCandidateError("certification snapshot copy mismatch")
    pin = {
        "snapshot_path": "certification_manifest.json",
        "snapshot_digest": canonical_digest(manifest),
        "manifest_version": "certification_manifest/v1",
        "version_vector": copy.deepcopy(VERSION_VECTOR),
        "promotion_digests": [item["digest"] for item in manifest["promotion_artifacts"]],
    }
    return manifest, pin


def _producer_registry() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "non_native_producers.yaml")


def _native_rows(manifest: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["row_id"]: row for row in manifest["rows"]}


def _contract(origin: str, template_id: str) -> tuple[
        Optional[Dict[str, Any]], str, bool, bool, Optional[int], str, str, str]:
    producer = (_producer_registry().get("producers") or {}).get(origin)
    if not isinstance(producer, dict):
        raise FinalPlanCandidateError(f"unknown producer origin {origin!r}")
    templates = producer.get("templates")
    if isinstance(templates, list):
        raw = None if template_id not in templates else {
            "purpose": None, "role": "strength", "is_assessment": False,
            "long_ride_registered": False, "main_set_rule": None,
        }
    else:
        raw = templates.get(template_id) if isinstance(templates, dict) else None
    if raw is None:
        raise FinalPlanCandidateError(f"unregistered producer template {origin}/{template_id}")
    if isinstance(raw, dict):
        purpose_string = raw.get("purpose")
        role = raw.get("role")
        assessment = bool(raw.get("is_assessment"))
        long_ride = bool(raw.get("long_ride_registered"))
        progression = raw.get("progression_level")
        rule = raw.get("main_set_rule", "SOURCE_BODY")
    elif isinstance(raw, str):
        purpose_string, role = raw, producer.get("role")
        assessment, long_ride, progression, rule = False, False, None, "SOURCE_BODY"
    else:
        purpose_string, role, assessment, long_ride = raw
        progression, rule = None, ("ASSESSMENT_BODY" if assessment else
                                   "NONE" if str(purpose_string).startswith("free/") else "SOURCE_BODY")
    purpose = None
    if purpose_string:
        purpose_class = str(purpose_string).split("/", 1)[0]
        purpose = {"class": purpose_class, "subtype": purpose_string,
                   "assignment_status": "hypothesis", "main_set_rule": rule,
                   "main_set_segment_ids": []}
    template_version = (raw.get("template_version") if isinstance(raw, dict) else None)
    template_version = str(template_version or producer.get("template_version") or "v1")
    return (purpose, role, assessment, long_ride, progression,
            str(producer["producer_id"]), str(producer["producer_version"]),
            template_version)


def _producer_source(producer_id: str) -> Path:
    if producer_id.startswith("workout_mapper."):
        return ROOT / "athletes/scripts/workout_mapper.py"
    if producer_id.startswith("workout_library."):
        return ROOT / "athletes/scripts/workout_library.py"
    if producer_id.startswith("canonical_training_model."):
        return ROOT / "athletes/scripts/canonical_training_model.py"
    if producer_id.startswith("plan_ir."):
        return ROOT / "athletes/scripts/plan_ir.py"
    return ROOT / "athletes/scripts/generate_athlete_package.py"


def _segments(raw_segments: list[Mapping[str, Any]], main_rule: str) -> list[Dict[str, Any]]:
    values = []
    total = len(raw_segments)
    for index, raw in enumerate(raw_segments, 1):
        kind = str(raw.get("kind") or "")
        provenance = ("renderer_warmup" if index == 1 and kind == "warmup" else
                      "renderer_cooldown" if index == total and kind == "cooldown" else
                      "source_body")
        source_target = raw.get("target") or {}
        target = {key: source_target.get(key) for key in
                  ("type", "value", "low", "high", "on", "off")}
        target["type"] = source_target.get("type")
        values.append({
            "id": f"seg-{index:04d}", "name": str(raw.get("name") or kind),
            "seconds": int(raw.get("seconds") or 0),
            "kind": "steady" if kind == "steady_state" else kind,
            "provenance_role": provenance, "target": target,
            "repeat": raw.get("repeat"), "on_seconds": raw.get("on_seconds"),
            "off_seconds": raw.get("off_seconds"),
        })
    return values


def _fuel(origin: str, source_tier: Any) -> tuple[Optional[str], Optional[str]]:
    if origin in {"CANONICAL_REST", "STRENGTH_TEMPLATE"}:
        return None, None
    if source_tier is None and origin == "ATHLETE_FIXED":
        source_tier = "empty"
    mapping = {"quality": "HIGH", "long_ride": "LONG_RIDE",
               "race_sim": "RACE", "empty": "NONE"}
    if source_tier not in mapping:
        raise FinalPlanCandidateError(
            f"fueling source tier unavailable for {origin}")
    return str(source_tier), mapping[source_tier]


def _weekly_structure(athlete_dir: Path, profile: Mapping[str, Any]) -> tuple[bool, str, int, bool]:
    try:
        value = _load_yaml(athlete_dir / "weekly_structure.yaml")
        days = value.get("days")
        if not isinstance(days, dict):
            raise FinalPlanCandidateError("weekly structure days malformed")
        count = sum(slot == "strength" for day in days.values() if isinstance(day, dict)
                    for slot in (day.get("am"), day.get("pm")))
        prescribed = count > 0
        state = "PRESCRIBES_STRENGTH" if prescribed else "DOES_NOT_PRESCRIBE"
    except FinalPlanCandidateError:
        prescribed, count, state = False, 0, "MALFORMED"
    include = (profile.get("strength") or {}).get("include_in_plan")
    declined = not prescribed and include is False
    if declined and state == "DOES_NOT_PRESCRIBE":
        state = "DECLINED"
    return prescribed, state, min(count, 3), declined


def _available_cycling_days(profile: Mapping[str, Any]) -> Optional[int]:
    preferred = profile.get("preferred_days")
    if not isinstance(preferred, dict):
        return None
    count = 0
    for value in preferred.values():
        if not isinstance(value, dict):
            return None
        availability = str(value.get("availability") or "").casefold()
        if availability not in {"unavailable", "rest"}:
            count += 1
    return count


def _target_weekly_tss(hours: Any, week_type: Optional[str]) -> Optional[float]:
    if not isinstance(hours, (int, float)) or isinstance(hours, bool) or hours < 0:
        return None
    guardrails = _load_yaml(CONFIG_DIR / "tss_guardrails.yaml").get("archetypes") or {}
    key = ("time_crunched" if hours < 8 else "specialist" if hours < 12
           else "volume" if hours < 15 else "goat")
    row = guardrails.get(key)
    if not isinstance(row, dict):
        raise FinalPlanCandidateError("TSS guardrail row is unavailable")
    if week_type in {"load", "testing", "medium"}:
        low, high = row["load_tss"]
        return (float(low) + float(high)) / 2.0
    if week_type == "uber_load":
        return float(row["load_tss"][1])
    if week_type == "recovery":
        low, high = row["recovery_tss"]
        return (float(low) + float(high)) / 2.0
    return None


def _strength_contract(cycling_phase: Optional[str], week_type: Optional[str],
                       phase_block_index: Optional[int]) -> tuple[Optional[str], Optional[str]]:
    if week_type == "recovery":
        return "deload", "deload"
    if cycling_phase == "transition":
        return "deload", "deload"
    if cycling_phase == "base":
        return (("AA", "adaptation") if phase_block_index == 0
                else ("max_strength", "max"))
    if cycling_phase == "build":
        return "maintenance", "maintenance"
    if cycling_phase == "maintenance":
        return "maintenance", "maintenance"
    if cycling_phase == "race_prep":
        return "maintenance_reduced", "reduced"
    if cycling_phase == "racing":
        return "key_lifts", "key_lifts"
    return None, None


def build_candidate(athlete_id: str, athlete_dir: Path | str,
                    canonical_model: Mapping[str, Any], *,
                    legacy_compliance_projection: Mapping[str, Any],
                    manifest: Optional[Mapping[str, Any]] = None,
                    manifest_pin: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    athlete_dir = Path(athlete_dir)
    profile = _load_yaml(athlete_dir / "profile.yaml")
    plan_dates = _load_yaml(athlete_dir / "plan_dates.yaml")
    methodology = _load_yaml(athlete_dir / "methodology.yaml")
    rollout = _load_yaml(CONFIG_DIR / "earned_selection_rollout.yaml")
    if rollout != {"mode": "A", "rollout_phase": "E1"}:
        raise FinalPlanCandidateError("E1 rollout config is not Mode A")
    if manifest is None or manifest_pin is None:
        manifest, manifest_pin = snapshot_manifest(athlete_dir)
    native_rows = _native_rows(manifest)
    prescribed_strength, structure_state, strength_frequency, declined = _weekly_structure(
        athlete_dir, profile)
    methodology_id = methodology.get("methodology_id")
    render_styles = _load_yaml(CONFIG_DIR / "methodology_profiles.yaml").get("render_styles")
    if methodology_id not in (render_styles or {}):
        raise FinalPlanCandidateError("unknown customer methodology ID")
    render_style = render_styles[methodology_id]

    candidate_sessions = []
    for raw in sorted(canonical_model.get("sessions", []),
                      key=lambda item: (item["week"], item["date"], item["daily_ordinal"])):
        origin = raw.get("producer_origin")
        if not origin:
            origin = "CANONICAL_REST" if raw.get("source_file") is None and raw.get(
                "session_type") in {"rest", "off"} else None
        if not origin:
            raise FinalPlanCandidateError(f"WORKOUT_ORIGIN_UNKNOWN: {raw.get('id')}")
        archetype = copy.deepcopy(raw.get("archetype"))
        if origin in {"NATIVE_ARCHETYPE", "LEGACY_NATE_ARCHETYPE"}:
            if not archetype or archetype.get("manifest_row_id") not in native_rows:
                raise FinalPlanCandidateError("native session has no immutable manifest row")
            manifest_row = native_rows[archetype["manifest_row_id"]]
            purpose = copy.deepcopy(manifest_row["purpose"])
            role = "intensity" if purpose["class"] in {
                "vo2max", "threshold", "wprime_drain", "mixed", "race_sim", "openers"
            } else "filler"
            assessment = bool(manifest_row["is_assessment"])
            long_ride = bool(manifest_row["long_ride_registered"])
            progression = archetype["level"]
            producer_id = "nate_workout_generator.native_archetype"
            producer_version = "v1"
            template_id = "native_archetype"
            template_version = "v1"
            if any(raw.get(key) != value for key, value in {
                    "producer_id": producer_id,
                    "producer_version": producer_version,
                    "template_id": template_id,
                    "template_version": template_version}.items()):
                raise FinalPlanCandidateError("native producer tuple mismatch")
            source_digests = [{"path": manifest_row["source"]["path"],
                               "sha256": manifest_row["source"]["sha256"]}]
        else:
            contract_template_id = (
                raw.get("strength_template") if origin == "STRENGTH_TEMPLATE"
                else raw.get("template_id")
            )
            template_id = str(contract_template_id or "canonical_rest_zero")
            (purpose, role, assessment, long_ride, progression,
             producer_id, producer_version, template_version) = _contract(
                origin, template_id)
            if any(raw.get(key) != value for key, value in {
                    "producer_id": producer_id,
                    "producer_version": producer_version}.items()):
                raise FinalPlanCandidateError("producer registry tuple mismatch")
            if raw.get("template_version") not in {None, template_version}:
                raise FinalPlanCandidateError("producer template version mismatch")
            source_path = _producer_source(producer_id)
            source_digests = [{
                "path": f"repo:{source_path.relative_to(ROOT).as_posix()}",
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            }]
            if raw.get("progression_level") is not None:
                progression = raw["progression_level"]
        segments = _segments(raw.get("segments") or [],
                             (purpose or {}).get("main_set_rule", "NONE"))
        if purpose is not None:
            purpose["main_set_segment_ids"] = [
                segment["id"] for segment in segments
                if segment["provenance_role"] == "source_body"
            ] if purpose["main_set_rule"] != "NONE" else []
        fuel_tier, fuel_class = _fuel(origin, raw.get("fueling_source_tier"))
        sport = "rest" if origin == "CANONICAL_REST" else (
            "strength" if origin == "STRENGTH_TEMPLATE" else "cycling")
        candidate_sessions.append({
            "id": raw["id"], "week": int(raw["week"]), "date": raw["date"],
            "daily_ordinal": int(raw["daily_ordinal"]), "title": raw.get("title") or "",
            "description": raw.get("description") or "", "sport": sport,
            "session_type": raw.get("session_type") or "", "role": role,
            "origin": origin, "is_assessment": assessment,
            "long_ride_registered": long_ride, "progression_level": progression,
            "fueling_source_tier": fuel_tier, "fueling_class": fuel_class,
            "duration_s": raw.get("duration_s"), "tss": raw.get("tss"),
            "tss_planned": raw.get("tss_planned"),
            "total_time_planned": raw.get("total_time_planned") or 0,
            "tp_kind": raw.get("tp_kind") or "day_off",
            "workout_type_value_id": raw.get("workout_type_value_id"),
            "control_metric": (canonical_model.get("athlete") or {}).get("control_metric")
                              if sport == "cycling" else "none",
            "control_basis": (canonical_model.get("athlete") or {}).get("control_basis")
                             if sport == "cycling" else None,
            "target_summary": raw.get("target_summary"), "purpose": purpose,
            "segments": segments, "archetype": archetype,
            "series": ({"series_id": raw["series_id"],
                        "series_index": int(raw.get("series_index") or 1),
                        "series_total": int(raw.get("series_total") or 1),
                        "tracker_slot": raw["series_id"],
                        "raw_display_name": raw.get("display_name") or raw.get("title") or "",
                        "family_key": (raw.get("display_name") or raw.get("title") or "").casefold(),
                        "resolved_replacement_id": None}
                       if raw.get("series_id") else None),
            "strength": (None if sport != "strength" else {
                "artifact_present": True, "artifact_valid": True,
                "template_id": raw.get("strength_template") or raw.get("template_id"),
                "phase": None, "intensity": None, "frequency": strength_frequency,
            }),
            "race": copy.deepcopy(raw.get("race")),
            "provenance": {
                "producer_id": producer_id,
                "producer_version": producer_version,
                "template_id": template_id,
                "template_version": template_version,
                "source_digests": source_digests,
                "transformation_parameters": {},
                "overlay_ids": [],
            },
        })

    by_week: Dict[int, list[Dict[str, Any]]] = {}
    for session in candidate_sessions:
        by_week.setdefault(session["week"], []).append(session)
    weeks = []
    block_number = -1
    phase_block_indexes: Dict[str, int] = {}
    active_phase: Optional[str] = None
    active_block_id: Optional[str] = None
    active_phase_block_index: Optional[int] = None
    ordinal_in_block = 0
    for raw in sorted(plan_dates.get("weeks") or [], key=lambda item: item["week"]):
        number = int(raw["week"])
        dates = [dt.date.fromisoformat(day["date"]) for day in raw.get("days", [])]
        sessions = by_week.get(number, [])
        phase = PHASES.get(raw.get("phase"))
        week_type = ("testing" if number == 1 and not raw.get("is_recovery_week") else
                     "recovery" if raw.get("is_recovery_week") else
                     "race" if raw.get("is_race_week") else
                     "taper" if raw.get("phase") == "taper" else "load")
        if number > 0:
            starts_cycle = (number - 1) % 4 == 0
            if active_block_id is None or phase != active_phase or starts_cycle:
                block_number += 1
                active_phase = phase
                active_block_id = f"meso-{block_number:03d}"
                active_phase_block_index = phase_block_indexes.get(str(phase), 0)
                phase_block_indexes[str(phase)] = active_phase_block_index + 1
                ordinal_in_block = 1
            else:
                ordinal_in_block += 1
        else:
            active_block_id = None
            active_phase_block_index = None
            ordinal_in_block = 0
        strength_phase, _ = _strength_contract(
            phase, week_type, active_phase_block_index)
        available_hours = (profile.get("weekly_availability") or {}).get(
            "cycling_hours_target")
        weeks.append({
            "week": number, "monday": min(dates).isoformat(),
            "sunday": max(dates).isoformat(), "cycling_phase": phase,
            "week_type": week_type, "meso_block_id": active_block_id,
            "meso_block_index": active_phase_block_index,
            "ordinal_in_meso_block": ordinal_in_block or None,
            "is_paid": number > 0, "is_race_week": bool(raw.get("is_race_week")),
            "block_note_template_id": week_type if week_type in {
                "load", "medium", "recovery", "race", "uber_load"} else None,
            "available_cycling_hours": available_hours,
            "target_cycling_tss": _target_weekly_tss(available_hours, week_type),
            "reported_cycling_tss": next((w.get("total_tss") for w in
                legacy_compliance_projection.get("weeks", []) if w.get("plan_week") == number), None),
            "strength_prescribed": prescribed_strength,
            "weekly_structure_state": structure_state,
            "strength_artifact_state": ("VALID" if any(s["sport"] == "strength" for s in sessions)
                                        else "ABSENT"),
            "strength_phase": strength_phase, "strength_frequency": strength_frequency,
            "session_ids": [session["id"] for session in sessions],
        })
        _, strength_intensity = _strength_contract(
            phase, week_type, active_phase_block_index)
        for session in sessions:
            if session["sport"] == "strength" and session.get("strength") is not None:
                session["strength"]["phase"] = strength_phase
                session["strength"]["intensity"] = strength_intensity
    training_history = profile.get("training_history") or {}
    control = canonical_model.get("athlete") or {}
    target = profile.get("target_race") or {}
    fulfillment = profile.get("fulfillment") or {}
    generated_at = str(fulfillment.get("generation_at") or "")
    revision = int(fulfillment.get("generation_revision") or 1)
    if not generated_at:
        raise FinalPlanCandidateError("profile must carry the injected generation clock")
    guide_inputs = [{"path": f"athlete:{name}",
                     "sha256": _digest_named(f"athlete:{name}", athlete_dir)}
                    for name in sorted(GUIDE_INPUTS)]
    staged_guide_dir = athlete_dir / "guide_inputs"
    if staged_guide_dir.is_dir():
        for staged in sorted(staged_guide_dir.glob("*.json")):
            relative = staged.relative_to(athlete_dir).as_posix()
            guide_inputs.append({
                "path": f"athlete:{relative}",
                "sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
            })
    guide_inputs.sort(key=lambda item: item["path"])
    candidate = {
        "schema_version": CANDIDATE_VERSION, "generation_revision": revision,
        "generated_at": generated_at, "mode": rollout["mode"],
        "version_vector": copy.deepcopy(VERSION_VECTOR),
        "manifest_pin": copy.deepcopy(manifest_pin),
        "athlete": {
            "athlete_id": str(profile.get("athlete_id") or athlete_id),
            "training_age_years": training_history.get("years_cycling",
                training_history.get("years_structured")),
            "available_cycling_hours": (profile.get("weekly_availability") or {}).get(
                "cycling_hours_target"),
            "available_cycling_days": _available_cycling_days(profile),
            "preferred_off_days": [str(value).lower() for value in
                (profile.get("schedule_constraints") or {}).get("preferred_off_days", [])],
            "strength_declined": declined,
            "requested_metric": control.get("requested_metric"),
            "control_metric": control.get("control_metric"),
            "control_basis": control.get("control_basis"),
        },
        "race": {"race_id": target.get("race_id"),
                 "race_date": plan_dates["race_date"],
                 "discipline": derive_discipline(profile), "priority": "A"},
        "plan": {"methodology_id": methodology_id, "render_style": render_style,
                 "calendar_start": plan_dates["plan_start"],
                 "calendar_end": plan_dates["plan_end"],
                 "weekly_structure_prescribes_strength": prescribed_strength},
        "config_digests": {key: _digest_named(path, athlete_dir)
                           for key, path in CONFIG_PATHS.items()},
        "guide_inputs": guide_inputs,
        "legacy_compliance_projection": copy.deepcopy(legacy_compliance_projection),
        "weeks": weeks, "sessions": candidate_sessions,
    }
    validate_candidate(candidate)
    return candidate


def validate_candidate(candidate: Mapping[str, Any]) -> None:
    root_keys = {"schema_version", "generation_revision", "generated_at", "mode",
                 "version_vector", "manifest_pin", "athlete", "race", "plan",
                 "config_digests", "guide_inputs", "legacy_compliance_projection",
                 "weeks", "sessions"}
    if set(candidate) != root_keys or candidate.get("schema_version") != CANDIDATE_VERSION:
        raise FinalPlanCandidateError("candidate root does not match closed schema")
    if candidate.get("mode") not in {"A", "B"} or candidate.get("version_vector") != VERSION_VECTOR:
        raise FinalPlanCandidateError("candidate mode/version vector invalid")
    sessions = candidate.get("sessions")
    if not isinstance(sessions, list):
        raise FinalPlanCandidateError("candidate sessions missing")
    keys = [(s.get("week"), s.get("date"), s.get("daily_ordinal")) for s in sessions]
    ids = [s.get("id") for s in sessions]
    if keys != sorted(keys) or len(keys) != len(set(keys)) or len(ids) != len(set(ids)):
        raise FinalPlanCandidateError("candidate session identity/order invalid")


def freeze_candidate(path: Path | str, candidate: Mapping[str, Any]) -> str:
    validate_candidate(candidate)
    payload = canonical_json(candidate)
    Path(path).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
