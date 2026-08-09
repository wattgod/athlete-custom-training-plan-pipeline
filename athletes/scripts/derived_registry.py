"""Versioned provenance records for values computed by the plan pipeline.

The registry is deliberately small and dependency-free so intake, fueling,
canonical-model projection, and the webhook state layer can validate the same
shape.  A registry entry describes *how* a value came to exist; the value
itself remains at ``field`` in the owning artifact and is copied into the
authenticated review catalog by the fulfillment state owner.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


REGISTRY_VERSION = "derived_registry/v1"
DERIVATION_CLASSES = {
    "measured",
    "athlete_reported",
    "defaulted",
    "inferred",
    "externally_observed",
}
SENSITIVITIES = {"public", "internal", "personal", "sensitive"}

# Authoritative inventories for every artifact that owns review-facing derived
# values.  Callers may not supply their own coverage list: adding an output to
# a strict artifact fails until this schema and the owning provenance records
# are updated together.  Optional fields are still schema-owned; they are
# required exactly when the owning document contains them.
ARTIFACT_DERIVED_SCHEMAS = {
    "profile": {
        "required": (
            "health_factors.age", "fitness_markers.sex",
            "fitness_markers.weight_kg", "fitness_markers.power_basis",
            "fitness_markers.control_metric", "fitness_markers.control_basis",
            "discipline",
        ),
        "optional": ("fitness_markers.ftp_watts", "fitness_markers.w_kg"),
        "optional_non_null": True,
        "strict_top_level": False,
    },
    "fueling": {
        "required": (
            "race.duration_hours", "calories",
            "carbohydrates.hourly_target", "carbohydrates.hourly_range",
            "carbohydrates.total_grams", "carbohydrates.total_range",
            "gut_training.phases", "gut_training.weekly_progression",
            "fueling_timeline", "prescription", "fueling_basis",
            "recommendations", "recommendations.hydration",
        ),
        "optional": (), "optional_non_null": False, "strict_top_level": False,
    },
    "summary": {
        "required": (
            "generated_date", "race.date", "race.distance_miles",
            "plan.weeks", "plan.start_date", "plan.end_date",
            "plan.methodology", "plan.methodology_score", "plan.tier",
            "plan.ability_level", "fueling.hourly_carb_target",
            "fueling.total_carbs", "fueling.estimated_duration_hours",
            "control.metric", "control.basis", "control.week_1_field_test",
            "control.reanchor", "files.workout_count",
        ),
        "optional": (), "optional_non_null": False, "strict_top_level": False,
    },
    "derived": {
        "required": (
            "tier", "plan_weeks", "starting_phase", "strength_frequency",
            "equipment_tier", "risk_factors", "exercise_exclusions",
            "key_day_candidates", "strength_day_candidates", "derived_date",
        ),
        "optional": ("plan_start", "plan_end", "race_weekday"),
        "optional_non_null": False,
        "strict_top_level": True,
    },
    "methodology": {
        "required": (
            "selected_methodology", "methodology_id", "score", "reasons",
            "warnings", "configuration", "alternatives", "selection_date",
            "confidence", "confidence_note",
        ),
        "optional": (), "optional_non_null": False, "strict_top_level": True,
    },
    "calendar": {
        "required": (
            "race_date", "race_weekday", "plan_weeks", "plan_start",
            "plan_start_short", "plan_end", "week1_monday",
            "race_week_monday", "weeks", "workout_naming_convention",
            "workout_example", "day_abbreviations", "month_abbreviations",
        ),
        "optional": (), "optional_non_null": False, "strict_top_level": True,
    },
    "schedule": {
        "required": ("description", "days"),
        "optional": (), "optional_non_null": False, "strict_top_level": True,
    },
}


class DerivedRegistryError(ValueError):
    """A derived-value record is incomplete or unsafe to publish."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def entry(
    *,
    id: str,
    field: str,
    value_class: str,
    basis: str,
    inputs: Any,
    sensitivity: str,
    revision: int,
    at: str | None = None,
) -> Dict[str, Any]:
    """Build and validate one normative A3 ``_derived`` entry."""
    record = {
        "id": str(id or "").strip(),
        "field": str(field or "").strip(),
        "class": str(value_class or "").strip(),
        "basis": str(basis or "").strip(),
        "inputs": copy.deepcopy(inputs),
        "sensitivity": str(sensitivity or "").strip(),
        "at": str(at or utc_now()).strip(),
        "revision": revision,
    }
    return validate_entry(record)


def validate_entry(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise DerivedRegistryError("derived-value entry must be an object")
    required = ("id", "field", "class", "basis", "inputs", "sensitivity", "at")
    if any(key not in record for key in required):
        raise DerivedRegistryError("derived-value entry is missing required fields")
    if any(not str(record.get(key) or "").strip() for key in ("id", "field", "basis", "at")):
        raise DerivedRegistryError("derived-value identity, field, basis, and time are required")
    if record.get("class") not in DERIVATION_CLASSES:
        raise DerivedRegistryError("unknown derived-value class")
    if record.get("sensitivity") not in SENSITIVITIES:
        raise DerivedRegistryError("unknown derived-value sensitivity")
    if "revision" not in record:
        raise DerivedRegistryError("derived-value revision is required")
    revision = record.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DerivedRegistryError("derived-value revision must be a positive integer")
    # Reject unserializable/non-finite values without importing the state layer.
    import json
    try:
        json.dumps(record.get("inputs"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise DerivedRegistryError("derived-value inputs must be canonical JSON") from exc
    return copy.deepcopy(record)


def validate_registry(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = [validate_entry(record) for record in records]
    ids = [record["id"] for record in normalized]
    if len(ids) != len(set(ids)):
        raise DerivedRegistryError("duplicate derived-value id")
    return sorted(normalized, key=lambda record: record["id"])


def registry_document(records: Iterable[Dict[str, Any]], *, revision: int = 1) -> Dict[str, Any]:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DerivedRegistryError("registry revision must be a positive integer")
    entries = validate_registry(records)
    if any(record["revision"] != revision for record in entries):
        raise DerivedRegistryError("entry revision must match registry revision")
    return {
        "version": REGISTRY_VERSION,
        "revision": revision,
        "entries": entries,
    }


def assert_registry_covers(
    document: Dict[str, Any], records: Iterable[Dict[str, Any]],
    *, artifact: str, revision: int,
) -> List[Dict[str, Any]]:
    """Fail closed against the registry owner's authoritative artifact schema."""
    schema = ARTIFACT_DERIVED_SCHEMAS.get(str(artifact or "").strip())
    if schema is None:
        raise DerivedRegistryError("unknown derived-value artifact schema")
    normalized = validate_registry(records)
    fields = [record["field"] for record in normalized]
    required = set(schema["required"])
    for field in schema["optional"]:
        try:
            value = get_field(document, field)
        except DerivedRegistryError:
            continue
        if schema.get("optional_non_null") and value is None:
            continue
        required.add(field)
    required = sorted(required)
    if schema["strict_top_level"]:
        declared_roots = {field.split(".", 1)[0]
                          for field in (*schema["required"], *schema["optional"])}
        actual_roots = set(document) - {"_derived"}
        undeclared = sorted(actual_roots - declared_roots)
        if undeclared:
            raise DerivedRegistryError(
                f"undeclared computed output(s) for {artifact}: {undeclared}")
    if len(fields) != len(set(fields)):
        raise DerivedRegistryError("duplicate derived-value field")
    if sorted(fields) != required:
        missing = sorted(set(required) - set(fields))
        extra = sorted(set(fields) - set(required))
        raise DerivedRegistryError(
            f"derived-value coverage mismatch; missing={missing}, extra={extra}"
        )
    if any(record["revision"] != revision for record in normalized):
        raise DerivedRegistryError("derived-value entry revision is stale")
    for field in required:
        get_field(document, field)
    return normalized


def get_field(document: Dict[str, Any], field: str) -> Any:
    """Resolve a dotted field from an artifact for review-catalog projection."""
    value: Any = document
    for part in str(field).split("."):
        if not isinstance(value, dict) or part not in value:
            raise DerivedRegistryError(f"derived-value field is missing: {field}")
        value = value[part]
    return copy.deepcopy(value)


def materialize(
    document: Dict[str, Any], records: Iterable[Dict[str, Any]], *, namespace: str,
) -> List[Dict[str, Any]]:
    """Copy typed values beside provenance for the server-only review state."""
    import json
    result = []
    for record in validate_registry(records):
        # State is JSON. Normalize mapping keys and tuple/list distinctions
        # before its review-catalog digest is computed so the atomic write's
        # JSON round trip cannot invalidate the state it just created.
        value = json.loads(json.dumps(
            get_field(document, record["field"]), allow_nan=False))
        result.append({
            **record,
            "id": f"{str(namespace).strip().upper()}_{record['id']}",
            "value": value,
        })
    return result
