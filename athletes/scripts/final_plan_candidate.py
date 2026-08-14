"""Build and freeze the closed ``FinalPlanCandidate/v1`` E1 artifact."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml

from archetype import derive_discipline
from earned_selection import (
    CONFIG_DIR, ROOT, VERSION_VECTOR, canonical_digest, canonical_json,
    validate_manifest_pin,
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
GUIDE_REPO_INPUTS = (
    "athletes/scripts/training_guide_builder.py",
    "athletes/scripts/brand_config.py",
    "athletes/scripts/calculate_fueling.py",
    "athletes/scripts/canonical_training_model.py",
    "athletes/scripts/archetype.py",
    "athletes/scripts/block_chain.py",
    "athletes/scripts/block_builder.py",
    "athletes/scripts/series_tracker.py",
    "athletes/scripts/workout_selector.py",
    "athletes/config/methodology_profiles.yaml",
    "athletes/config/brands.yaml",
    "athletes/config/workout_selection.yaml",
    "athletes/config/workout_library.yaml",
    "athletes/config/tss_guardrails.yaml",
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


def revision_dir_for_candidate(athlete_dir: Path, revision: int) -> Path:
    """Resolve the immutable order revision selected by the webhook.

    Production supplies the exact §5.3 directory. Standalone/local generation
    gets an explicitly revisioned staging directory rather than silently using
    the mutable athlete root.
    """
    selected = os.environ.get("GG_E1_REVISION_DIR", "").strip()
    if selected:
        path = Path(selected)
        if path.name != f"r{revision}" or path.parent.name != "revisions":
            raise FinalPlanCandidateError("E1 revision path is malformed")
        return path
    return athlete_dir / ".e1-revisions" / f"r{revision}"


def load_snapshot_manifest(revision_dir: Path, *,
                           expected_pin: Optional[Mapping[str, Any]] = None
                           ) -> tuple[Dict[str, Any], Dict[str, Any]]:
    snapshot = revision_dir / "certification_manifest.json"
    try:
        manifest = json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalPlanCandidateError("MANIFEST_SNAPSHOT_UNAVAILABLE") from exc
    if (manifest.get("schema_version") != "certification_manifest/v1"
            or manifest.get("version_vector") != VERSION_VECTOR):
        raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH")
    pin = {
        "snapshot_path": "certification_manifest.json",
        "snapshot_digest": canonical_digest(manifest),
        "manifest_version": manifest["schema_version"],
        "version_vector": copy.deepcopy(manifest["version_vector"]),
        "promotion_digests": [
            item["digest"] for item in manifest.get("promotion_artifacts", [])
        ],
    }
    if expected_pin is not None:
        try:
            validate_manifest_pin(expected_pin, manifest)
        except Exception as exc:
            raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH") from exc
    return manifest, pin


def snapshot_manifest(athlete_dir: Path, *, revision_dir: Optional[Path] = None,
                      revision: int = 1) -> tuple[Dict[str, Any], Dict[str, Any]]:
    source = CONFIG_DIR / "workout_certification.json"
    try:
        manifest = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalPlanCandidateError("MANIFEST_SNAPSHOT_UNAVAILABLE") from exc
    if (manifest.get("schema_version") != "certification_manifest/v1"
            or manifest.get("version_vector") != VERSION_VECTOR):
        raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH")
    revision_dir = revision_dir or revision_dir_for_candidate(athlete_dir, revision)
    revision_dir.mkdir(parents=True, exist_ok=True)
    snapshot = revision_dir / "certification_manifest.json"
    snapshot.write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                                   allow_nan=False) + "\n", encoding="utf-8")
    reread = json.loads(snapshot.read_text(encoding="utf-8"))
    if reread != manifest:
        raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH")
    pin = {
        "snapshot_path": "certification_manifest.json",
        "snapshot_digest": canonical_digest(manifest),
        "manifest_version": "certification_manifest/v1",
        "version_vector": copy.deepcopy(VERSION_VECTOR),
        "promotion_digests": [item["digest"] for item in manifest["promotion_artifacts"]],
    }
    # Keep the existing private work artifact for downstream copy/readers, but
    # it is only a byte-checked mirror of the revision-local authority.
    athlete_snapshot = athlete_dir / "certification_manifest.json"
    athlete_snapshot.write_bytes(snapshot.read_bytes())
    mirrored = json.loads(athlete_snapshot.read_text(encoding="utf-8"))
    if canonical_digest(mirrored) != pin["snapshot_digest"]:
        raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH")
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
    if manifest is None:
        raise FinalPlanCandidateError("MANIFEST_SNAPSHOT_UNAVAILABLE")
    if manifest_pin is None:
        raise FinalPlanCandidateError("MANIFEST_PIN_MISSING")
    try:
        validate_manifest_pin(manifest_pin, manifest)
    except Exception as exc:
        raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH") from exc
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
            "race": (None if not raw.get("race") else {
                "priority": raw["race"].get("priority"),
                "race_id": raw["race"].get("race_id"),
            }),
            "provenance": {
                "producer_id": producer_id,
                "producer_version": producer_version,
                "template_id": template_id,
                "template_version": template_version,
                "source_digests": source_digests,
                "transformation_parameters": copy.deepcopy(
                    raw.get("transformation_parameters") or {}),
                "overlay_ids": copy.deepcopy(raw.get("overlay_ids") or []),
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
    guide_inputs.extend({
        "path": f"repo:{name}",
        "sha256": _digest_named(f"repo:{name}", athlete_dir),
    } for name in GUIDE_REPO_INPUTS)
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
    validate_candidate(candidate, manifest=manifest, athlete_dir=athlete_dir)
    return candidate


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_SESSION_ID = re.compile(r"w\d{2}\.\d{4}-\d{2}-\d{2}\.\d{2}\Z")
_WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday"}


def _closed(value: Any, keys: set[str], where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise FinalPlanCandidateError(f"candidate {where} does not match closed schema")
    return value


def _sha(value: Any, where: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise FinalPlanCandidateError(f"candidate {where} digest invalid")


def _number(value: Any, where: str, *, nullable: bool = False,
            positive: bool = False) -> None:
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FinalPlanCandidateError(f"candidate {where} number invalid")
    if value < (0 if not positive else 0) or (positive and value == 0):
        raise FinalPlanCandidateError(f"candidate {where} number invalid")


def _path_digest(item: Any, where: str) -> None:
    row = _closed(item, {"path", "sha256"}, where)
    path = row["path"]
    if (not isinstance(path, str) or not path.startswith(("repo:", "athlete:"))
            or path.split(":", 1)[1].startswith("/")
            or ".." in Path(path.split(":", 1)[1]).parts):
        raise FinalPlanCandidateError(f"candidate {where} path invalid")
    _sha(row["sha256"], f"{where}.sha256")


def validate_candidate(candidate: Mapping[str, Any], *,
                       manifest: Optional[Mapping[str, Any]] = None,
                       athlete_dir: Optional[Path] = None) -> None:
    root_keys = {"schema_version", "generation_revision", "generated_at", "mode",
                 "version_vector", "manifest_pin", "athlete", "race", "plan",
                 "config_digests", "guide_inputs", "legacy_compliance_projection",
                 "weeks", "sessions"}
    if set(candidate) != root_keys or candidate.get("schema_version") != CANDIDATE_VERSION:
        raise FinalPlanCandidateError("candidate root does not match closed schema")
    if candidate.get("mode") not in {"A", "B"} or candidate.get("version_vector") != VERSION_VECTOR:
        raise FinalPlanCandidateError("candidate mode/version vector invalid")
    if (not isinstance(candidate.get("generation_revision"), int)
            or candidate["generation_revision"] < 1
            or not isinstance(candidate.get("generated_at"), str)
            or not candidate["generated_at"].endswith(("Z", "+00:00"))):
        raise FinalPlanCandidateError("candidate generation identity invalid")

    pin = _closed(candidate["manifest_pin"], {
        "snapshot_path", "snapshot_digest", "manifest_version",
        "version_vector", "promotion_digests"}, "manifest_pin")
    if (pin["snapshot_path"] != "certification_manifest.json"
            or pin["manifest_version"] != "certification_manifest/v1"
            or pin["version_vector"] != VERSION_VECTOR
            or not isinstance(pin["promotion_digests"], list)):
        raise FinalPlanCandidateError("candidate manifest pin invalid")
    _sha(pin["snapshot_digest"], "manifest_pin.snapshot_digest")
    for digest in pin["promotion_digests"]:
        _sha(digest, "manifest_pin.promotion_digests")
    if manifest is not None:
        try:
            validate_manifest_pin(pin, manifest)
        except Exception as exc:
            raise FinalPlanCandidateError("MANIFEST_PIN_MISMATCH") from exc

    athlete = _closed(candidate["athlete"], {
        "athlete_id", "training_age_years", "available_cycling_hours",
        "available_cycling_days", "preferred_off_days", "strength_declined",
        "requested_metric", "control_metric", "control_basis"}, "athlete")
    if (not isinstance(athlete["athlete_id"], str) or not athlete["athlete_id"]
            or athlete["requested_metric"] not in {"power", "hr", "rpe"}
            or athlete["control_metric"] not in {"power", "hr", "rpe"}
            or athlete["control_basis"] not in {
                "ftp", "lthr", "hrmax", "rpe", "rpe_pending_lthr"}
            or not isinstance(athlete["strength_declined"], bool)):
        raise FinalPlanCandidateError("candidate athlete values invalid")
    _number(athlete["training_age_years"], "athlete.training_age_years", nullable=True)
    _number(athlete["available_cycling_hours"], "athlete.available_cycling_hours",
            nullable=True, positive=True)
    days = athlete["available_cycling_days"]
    if days is not None and (not isinstance(days, int) or isinstance(days, bool)
                             or not 0 <= days <= 7):
        raise FinalPlanCandidateError("candidate available cycling days invalid")
    if (not isinstance(athlete["preferred_off_days"], list)
            or any(day not in _WEEKDAYS for day in athlete["preferred_off_days"])):
        raise FinalPlanCandidateError("candidate preferred off days invalid")

    race = _closed(candidate["race"], {"race_id", "race_date", "discipline", "priority"}, "race")
    if (race["race_id"] is not None and not isinstance(race["race_id"], str)) or (
            not isinstance(race["race_date"], str) or not _DATE.fullmatch(race["race_date"])) or (
            race["discipline"] not in {"gravel", "road", "mtb"}) or race["priority"] != "A":
        raise FinalPlanCandidateError("candidate race values invalid")
    plan = _closed(candidate["plan"], {"methodology_id", "render_style", "calendar_start",
                                            "calendar_end", "weekly_structure_prescribes_strength"}, "plan")
    if (not isinstance(plan["methodology_id"], str)
            or plan["render_style"] not in {"POLARIZED", "G_SPOT", "PYRAMIDAL"}
            or not all(isinstance(plan[key], str) and _DATE.fullmatch(plan[key])
                       for key in ("calendar_start", "calendar_end"))
            or not isinstance(plan["weekly_structure_prescribes_strength"], bool)):
        raise FinalPlanCandidateError("candidate plan values invalid")

    if (not isinstance(candidate["config_digests"], Mapping)
            or set(candidate["config_digests"]) != set(CONFIG_PATHS)):
        raise FinalPlanCandidateError("candidate config digests incomplete")
    for key, digest in candidate["config_digests"].items():
        _sha(digest, f"config_digests.{key}")
        if (athlete_dir is not None
                and _digest_named(CONFIG_PATHS[key], athlete_dir) != digest):
            raise FinalPlanCandidateError("candidate config digest mismatch")
    guide_inputs = candidate["guide_inputs"]
    if not isinstance(guide_inputs, list):
        raise FinalPlanCandidateError("candidate guide inputs missing")
    for index, item in enumerate(guide_inputs):
        _path_digest(item, f"guide_inputs[{index}]")
        if athlete_dir is not None and _digest_named(item["path"], athlete_dir) != item["sha256"]:
            raise FinalPlanCandidateError("candidate guide input digest mismatch")
    guide_paths = [item["path"] for item in guide_inputs]
    required_guides = ({f"athlete:{name}" for name in GUIDE_INPUTS}
                       | {f"repo:{name}" for name in GUIDE_REPO_INPUTS})
    if (guide_paths != sorted(guide_paths) or len(guide_paths) != len(set(guide_paths))
            or not required_guides <= set(guide_paths)):
        raise FinalPlanCandidateError("candidate guide input closure invalid")

    projection = _closed(candidate["legacy_compliance_projection"], {
        "schema_version", "target_hours", "off_days", "max_intensity", "weeks",
        "all_violations_present", "all_violations", "projection_sha256"},
        "legacy_compliance_projection")
    if projection["schema_version"] != "legacy_compliance_projection/v1":
        raise FinalPlanCandidateError("candidate legacy projection version invalid")
    expected_projection = canonical_digest({
        key: value for key, value in projection.items() if key != "projection_sha256"})
    if projection["projection_sha256"] != expected_projection:
        raise FinalPlanCandidateError("candidate legacy projection digest invalid")
    _number(projection["target_hours"], "legacy.target_hours")
    if (not isinstance(projection["off_days"], list)
            or not isinstance(projection["max_intensity"], int)
            or projection["max_intensity"] < 0
            or not isinstance(projection["all_violations_present"], bool)
            or (projection["all_violations"] is not None
                and not isinstance(projection["all_violations"], list))):
        raise FinalPlanCandidateError("candidate legacy projection values invalid")
    for wi, week in enumerate(projection["weeks"]):
        week = _closed(week, {"plan_week", "phase", "week_type", "total_tss",
                              "total_duration", "days"}, f"legacy.weeks[{wi}]")
        if not isinstance(week["days"], list):
            raise FinalPlanCandidateError("candidate legacy days invalid")
        for di, day in enumerate(week["days"]):
            day = _closed(day, {"day", "name", "role", "duration", "workout", "sessions"},
                          f"legacy.weeks[{wi}].days[{di}]")
            if day["workout"] is not None:
                _closed(day["workout"], {"duration"}, "legacy workout")
            if not isinstance(day["sessions"], list):
                raise FinalPlanCandidateError("candidate legacy sessions invalid")
            for nested in day["sessions"]:
                _closed(nested, {"intensity"}, "legacy nested session")

    sessions = candidate.get("sessions")
    if not isinstance(sessions, list):
        raise FinalPlanCandidateError("candidate sessions missing")
    keys = [(s.get("week"), s.get("date"), s.get("daily_ordinal")) for s in sessions]
    ids = [s.get("id") for s in sessions]
    if keys != sorted(keys) or len(keys) != len(set(keys)) or len(ids) != len(set(ids)):
        raise FinalPlanCandidateError("candidate session identity/order invalid")
    session_keys = {"id", "week", "date", "daily_ordinal", "title", "description",
        "sport", "session_type", "role", "origin", "is_assessment",
        "long_ride_registered", "progression_level", "fueling_source_tier",
        "fueling_class", "duration_s", "tss", "tss_planned", "total_time_planned",
        "tp_kind", "workout_type_value_id", "control_metric", "control_basis",
        "target_summary", "purpose", "segments", "archetype", "series", "strength",
        "race", "provenance"}
    segment_keys = {"id", "name", "seconds", "kind", "provenance_role", "target",
                    "repeat", "on_seconds", "off_seconds"}
    target_keys = {"type", "value", "low", "high", "on", "off"}
    provenance_keys = {"producer_id", "producer_version", "template_id",
                       "template_version", "source_digests",
                       "transformation_parameters", "overlay_ids"}
    for index, session in enumerate(sessions):
        _closed(session, session_keys, f"sessions[{index}]")
        if (not isinstance(session["id"], str) or not _SESSION_ID.fullmatch(session["id"])
                or session["id"] != f"w{session['week']:02d}.{session['date']}.{session['daily_ordinal']:02d}"
                or session["sport"] not in {"cycling", "strength", "rest"}
                or session["tp_kind"] not in {"bike", "strength", "race", "day_off"}
                or not isinstance(session["is_assessment"], bool)
                or not isinstance(session["long_ride_registered"], bool)):
            raise FinalPlanCandidateError("candidate session values invalid")
        provenance = _closed(session["provenance"], provenance_keys,
                             f"sessions[{index}].provenance")
        if (not all(isinstance(provenance[key], str) and provenance[key]
                    for key in ("producer_id", "producer_version", "template_id", "template_version"))
                or not isinstance(provenance["transformation_parameters"], Mapping)
                or not isinstance(provenance["overlay_ids"], list)):
            raise FinalPlanCandidateError("candidate provenance values invalid")
        paths = []
        for si, item in enumerate(provenance["source_digests"]):
            _path_digest(item, f"sessions[{index}].source_digests[{si}]")
            if athlete_dir is not None and _digest_named(item["path"], athlete_dir) != item["sha256"]:
                raise FinalPlanCandidateError("candidate provenance source digest mismatch")
            paths.append(item["path"])
        if not paths or paths != sorted(paths) or len(paths) != len(set(paths)):
            raise FinalPlanCandidateError("candidate provenance digests invalid")
        for si, segment in enumerate(session["segments"]):
            _closed(segment, segment_keys, f"sessions[{index}].segments[{si}]")
            _closed(segment["target"], target_keys,
                    f"sessions[{index}].segments[{si}].target")
        if session["purpose"] is not None:
            _closed(session["purpose"], {"class", "subtype", "assignment_status",
                                          "main_set_rule", "main_set_segment_ids"},
                    f"sessions[{index}].purpose")
        if session["archetype"] is not None:
            archetype = _closed(session["archetype"], {"archetype_id", "level", "category",
                                                        "variation", "manifest_row_id"},
                                f"sessions[{index}].archetype")
            if session["progression_level"] != archetype["level"]:
                raise FinalPlanCandidateError("candidate native progression mismatch")
            expected_tuple = ("nate_workout_generator.native_archetype", "v1",
                              "native_archetype", "v1")
            actual_tuple = tuple(provenance[key] for key in (
                "producer_id", "producer_version", "template_id", "template_version"))
            if actual_tuple != expected_tuple:
                raise FinalPlanCandidateError("candidate native producer tuple mismatch")
        else:
            try:
                contract = _contract(session["origin"], provenance["template_id"])
            except FinalPlanCandidateError:
                raise
            expected_tuple = (contract[5], contract[6], provenance["template_id"], contract[7])
            actual_tuple = tuple(provenance[key] for key in (
                "producer_id", "producer_version", "template_id", "template_version"))
            if actual_tuple != expected_tuple:
                raise FinalPlanCandidateError("candidate producer tuple mismatch")
        if session["origin"] == "PRE_PLAN_GENERATOR":
            parameters = provenance["transformation_parameters"]
            template = provenance["template_id"]
            if template == "pre_plan_rest":
                expected_parameters = {
                    "authored_duration_minutes": 0,
                    "final_duration_seconds": 60,
                    "renderer": "FreeRide",
                }
            else:
                expected_source = {
                    "pre_plan_easy": ([40, 45], [0.60]),
                    "pre_plan_endurance": ([80], [0.65]),
                    "pre_plan_strength_prep": ([35], [0]),
                }.get(template)
                if expected_source is None:
                    raise FinalPlanCandidateError("candidate W00 template invalid")
                expected_parameters = {
                    "authored_duration_minutes": parameters.get(
                        "authored_duration_minutes"),
                    "power": parameters.get("power"),
                    "workout_type": "Easy",
                    "rounded_duration_minutes": session["duration_s"] // 60,
                }
                if (parameters.get("authored_duration_minutes") not in expected_source[0]
                        or parameters.get("power") not in expected_source[1]):
                    raise FinalPlanCandidateError("candidate W00 transformation invalid")
            if parameters != expected_parameters or provenance["overlay_ids"] != []:
                raise FinalPlanCandidateError("candidate W00 provenance invalid")
        if session["series"] is not None:
            _closed(session["series"], {"series_id", "series_index", "series_total",
                                         "tracker_slot", "raw_display_name", "family_key",
                                         "resolved_replacement_id"}, f"sessions[{index}].series")
        if session["strength"] is not None:
            _closed(session["strength"], {"artifact_present", "artifact_valid", "template_id",
                                           "phase", "intensity", "frequency"},
                    f"sessions[{index}].strength")
        if session["race"] is not None:
            _closed(session["race"], {"priority", "race_id"}, f"sessions[{index}].race")

    weeks = candidate.get("weeks")
    if not isinstance(weeks, list):
        raise FinalPlanCandidateError("candidate weeks missing")
    week_keys = {"week", "monday", "sunday", "cycling_phase", "week_type",
        "meso_block_id", "meso_block_index", "ordinal_in_meso_block", "is_paid",
        "is_race_week", "block_note_template_id", "available_cycling_hours",
        "target_cycling_tss", "reported_cycling_tss", "strength_prescribed",
        "weekly_structure_state", "strength_artifact_state", "strength_phase",
        "strength_frequency", "session_ids"}
    for index, week in enumerate(weeks):
        _closed(week, week_keys, f"weeks[{index}]")
        if (not isinstance(week["week"], int)
                or not _DATE.fullmatch(str(week["monday"]))
                or not _DATE.fullmatch(str(week["sunday"]))
                or not isinstance(week["is_paid"], bool)
                or not isinstance(week["is_race_week"], bool)
                or not isinstance(week["session_ids"], list)):
            raise FinalPlanCandidateError("candidate week values invalid")
        expected_ids = [session["id"] for session in sessions if session["week"] == week["week"]]
        if week["session_ids"] != expected_ids:
            raise FinalPlanCandidateError("candidate week/session identity mismatch")


def freeze_candidate(path: Path | str, candidate: Mapping[str, Any]) -> str:
    validate_candidate(candidate, athlete_dir=Path(path).parent)
    payload = canonical_json(candidate)
    Path(path).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
