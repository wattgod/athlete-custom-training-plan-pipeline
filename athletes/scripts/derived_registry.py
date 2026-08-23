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
# values. Callers may not supply their own coverage list. ``output_shape`` is a
# recursive, closed classification: every emitted key is either derived or an
# explicitly raw/non-derived aggregate. A derived aggregate record covers its
# declared descendants, but the descendant key inventory remains closed, so a
# new field under ``weeks``, ``days``, ``configuration``, etc. cannot inherit
# provenance accidentally.
DERIVED = "derived"
RAW = "raw"


def _optional(shape: Any) -> tuple[str, Any]:
    return ("optional", shape)


def _list(shape: Any) -> tuple[str, Any]:
    return ("list", shape)


def _map(keys: Iterable[str], shape: Any) -> tuple[str, frozenset[str], Any]:
    return ("map", frozenset(str(key) for key in keys), shape)


_PROFILE_RAW_ROOTS = (
    "name", "email", "athlete_id", "order_id", "delivery_platform",
    "fulfillment", "sex", "height_cm", "weight_kg", "primary_goal",
    "target_race", "brand", "road_category", "discipline_default",
    "a_events", "b_events", "c_events", "secondary_races", "racing",
    "training_history", "recent_training", "weekly_availability",
    "preferred_days", "availability_roles", "recurring_sessions",
    "availability_review_issues", "calendar_protection", "travel_dates",
    "schedule_constraints",
    "cycling_equipment", "strength_equipment", "training_environment",
    "injury_history", "movement_limitations", "strength", "devices",
    "work", "life_balance", "nutrition", "bike", "social", "coaching",
    "personal", "methodology_preferences", "workout_preferences",
    "strength_preferences", "coaching_style", "motivation", "mental_game",
    "lifestyle", "platforms", "communication", "plan_start",
)

_PROFILE_SHAPE = {key: RAW for key in _PROFILE_RAW_ROOTS} | {
    "health_factors": {
        "age": DERIVED,
        "sleep_quality": RAW,
        "sleep_hours_avg": RAW,
        "stress_level": RAW,
        "recovery_capacity": RAW,
        "medical_conditions": RAW,
        "medications": RAW,
        "health_notes": RAW,
    },
    "fitness_markers": {
        "ftp_watts": DERIVED,
        "ftp_estimated": RAW,
        "power_basis": DERIVED,
        "ftp_date": RAW,
        "weight_kg": DERIVED,
        "height_cm": RAW,
        "sex": DERIVED,
        "w_kg": DERIVED,
        "resting_hr": RAW,
        "max_hr": RAW,
        "lthr": RAW,
        "training_metric": RAW,
        "control_metric": DERIVED,
        "control_basis": DERIVED,
        "requested_metric": RAW,
        "reanchor": RAW,
    },
    "discipline": DERIVED,
    "event_format": _optional(RAW),
    "brand_discipline_conflict": _optional(RAW),
}

_FUELING_PHASE = {
    "description": DERIVED,
    "guidance": DERIVED,
    "weeks": _list(DERIVED),
    "target_range": _list(DERIVED),
}
_FUELING_WEEK = {
    "description": DERIVED,
    "guidance": DERIVED,
    "current_week": DERIVED,
    "week_label": DERIVED,
    "plan_weeks": DERIVED,
    "phase_name": DERIVED,
    "target_range": _list(DERIVED),
}
_FUELING_SHAPE = {
    "athlete": {"weight_kg": RAW, "sex": RAW},
    "race": {
        "distance_miles": RAW, "elevation_feet": RAW,
        "duration_hours": DERIVED, "goal_type": RAW,
    },
    "calories": {
        "total_calories": DERIVED, "calories_per_hour": DERIVED,
        "rate_kcal_kg_km": DERIVED, "duration_hours": DERIVED,
        "distance_km": DERIVED, "weight_kg": DERIVED,
        "breakdown": {
            "base_rate": DERIVED, "elevation_adjustment": DERIVED,
            "duration_factor": DERIVED, "final_rate": DERIVED,
        },
    },
    "carbohydrates": {
        "hourly_target": DERIVED, "hourly_range": _list(DERIVED),
        "total_grams": DERIVED, "total_range": _list(DERIVED),
        "duration_hours": RAW, "goal_type": RAW,
    },
    "gut_training": {
        "phases": _map(
            ("lead_in", "base", "build", "peak", "maintenance", "taper", "race"),
            _FUELING_PHASE,
        ),
        "weekly_progression": _list(_FUELING_WEEK),
    },
    "fueling_timeline": _list({
        "hour": DERIVED, "mile": DERIVED, "action": DERIVED,
        "carbs_target": DERIVED, "cumulative_carbs": DERIVED,
        "notes": DERIVED,
    }),
    "prescription": {
        "race_target_g_per_hour": DERIVED,
        "race_range_g_per_hour": _list(DERIVED),
        "total_g": DERIVED,
        "training_tiers": _map(("quality", "long_ride", "race_sim"), {
            "target_g_per_hour": DERIVED,
            "range_g_per_hour": _list(DERIVED),
        }),
        "hydration": {
            "target_ml_per_hour": DERIVED,
            "electrolytes": DERIVED,
        },
        "assumptions": _list(DERIVED),
        "inputs": {
            "basis": DERIVED, "duration_hours": DERIVED,
            "weight_kg": DERIVED, "goal_type": DERIVED,
            "gut_training_phase": DERIVED, "tolerated_g_per_hour": DERIVED,
            "ftp_watts": _optional(DERIVED),
            "intensity_factor": _optional(DERIVED),
            "absolute_work_watts": _optional(DERIVED),
            "intensity_descriptor": _optional(DERIVED),
            "deferred_to_field_test": _optional(DERIVED),
            "prescribed_range_g_per_hour": _optional(_list(DERIVED)),
        },
        "policy_version": DERIVED,
    },
    "fueling_basis": {
        "kind": DERIVED, "power_used": DERIVED, "label": DERIVED,
        "reanchor": RAW,
    },
    "recommendations": {
        "hourly_target": DERIVED, "total_target": DERIVED,
        "example_products": {
            "gels_only": {
                "quantity": DERIVED, "frequency": DERIVED, "notes": DERIVED,
            },
            "mixed_approach": {
                "gels": DERIVED, "chews_packs": DERIVED,
                "drink_mix_bottles": DERIVED, "notes": DERIVED,
            },
            "real_food_hybrid": {
                "gels": DERIVED, "rice_cakes_bars": DERIVED,
                "drink_mix": DERIVED, "notes": DERIVED,
            },
        },
        "hydration": {"target_ml_per_hour": DERIVED, "electrolytes": DERIVED},
        "pre_race": {
            "meal_timing": DERIVED, "meal_composition": DERIVED,
            "example": DERIVED, "final_top_off": DERIVED,
        },
        "post_race": {
            "timing": DERIVED, "composition": DERIVED, "example": DERIVED,
        },
    },
    "generated_date": RAW,
}

_METHODOLOGY_CONFIGURATION = {
    "methodology": DERIVED, "emphasis": DERIVED,
    "intensity_distribution": {
        "z1_z2": DERIVED, "z3": DERIVED, "z4_z5": DERIVED,
    },
    "strength_approach": DERIVED, "key_workouts": _list(DERIVED),
    "progression_style": DERIVED, "testing_frequency": DERIVED,
}

_CALENDAR_DAY = {
    "day": DERIVED, "date": DERIVED, "date_short": DERIVED,
    "workout_prefix": DERIVED, "is_race_day": DERIVED,
    "is_b_race_day": _optional(DERIVED),
    "is_b_race_opener": _optional(DERIVED),
    "is_b_race_easy": _optional(DERIVED),
    "is_travel_day": _optional(DERIVED),
}
_CALENDAR_WEEK = {
    "week": DERIVED, "monday": DERIVED, "monday_short": DERIVED,
    "sunday": DERIVED, "sunday_short": DERIVED, "phase": DERIVED,
    "is_race_week": DERIVED, "days": _list(_CALENDAR_DAY),
    "is_recovery_week": DERIVED,
    "is_post_event_recovery": _optional(DERIVED),
    "b_race": _optional({"name": DERIVED, "date": DERIVED, "phase": DERIVED}),
}

_DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_SCHEDULE_DAY = {
    "am": DERIVED, "pm": DERIVED, "is_key_day": DERIVED,
    "notes": DERIVED, "max_duration": DERIVED,
}

# Optional fields are still schema-owned; they are required exactly when the
# owning document contains them.
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
        "output_shape": _PROFILE_SHAPE,
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
        "optional": (), "optional_non_null": False, "output_shape": _FUELING_SHAPE,
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
        "optional": (), "optional_non_null": False,
        "output_shape": {
            "athlete_id": RAW, "athlete_name": RAW, "generated_date": DERIVED,
            "race": {"name": RAW, "date": DERIVED, "distance_miles": DERIVED},
            "plan": {
                "weeks": DERIVED, "start_date": DERIVED, "end_date": DERIVED,
                "methodology": DERIVED, "methodology_score": DERIVED,
                "tier": DERIVED, "ability_level": DERIVED,
            },
            "fueling": {
                "hourly_carb_target": DERIVED, "total_carbs": DERIVED,
                "estimated_duration_hours": DERIVED,
            },
            "control": {
                "metric": DERIVED, "basis": DERIVED,
                "week_1_field_test": DERIVED, "reanchor": DERIVED,
            },
            "files": {"guide": RAW, "workouts_dir": RAW, "workout_count": DERIVED},
        },
    },
    "derived": {
        "required": (
            "tier", "plan_weeks", "starting_phase", "strength_frequency",
            "equipment_tier", "risk_factors", "exercise_exclusions",
            "key_day_candidates", "strength_day_candidates", "derived_date",
        ),
        "optional": ("plan_start", "plan_end", "race_weekday"),
        "optional_non_null": False,
        "output_shape": {
            "tier": DERIVED, "plan_weeks": DERIVED, "starting_phase": DERIVED,
            "strength_frequency": DERIVED, "equipment_tier": DERIVED,
            "risk_factors": _list(DERIVED), "exercise_exclusions": _list(DERIVED),
            "key_day_candidates": _list(DERIVED),
            "strength_day_candidates": _list(DERIVED), "derived_date": DERIVED,
            "plan_start": _optional(DERIVED), "plan_end": _optional(DERIVED),
            "race_weekday": _optional(DERIVED),
        },
    },
    "methodology": {
        "required": (
            "selected_methodology", "methodology_id", "score", "reasons",
            "warnings", "configuration", "alternatives", "selection_date",
            "confidence", "confidence_note",
        ),
        "optional": (), "optional_non_null": False,
        "output_shape": {
            "selected_methodology": DERIVED, "methodology_id": DERIVED,
            "score": DERIVED, "reasons": _list(DERIVED),
            "warnings": _list(DERIVED), "configuration": _METHODOLOGY_CONFIGURATION,
            "alternatives": _list({
                "name": DERIVED, "score": DERIVED, "key_reason": DERIVED,
            }),
            "selection_date": DERIVED, "confidence": DERIVED,
            "confidence_note": DERIVED,
        },
    },
    "calendar": {
        "required": (
            "race_date", "race_weekday", "plan_weeks", "plan_start",
            "plan_start_short", "plan_end", "week1_monday",
            "race_week_monday", "weeks", "workout_naming_convention",
            "workout_example", "day_abbreviations", "month_abbreviations",
        ),
        "optional": (), "optional_non_null": False,
        "output_shape": {
            "race_date": DERIVED, "race_weekday": DERIVED, "plan_weeks": DERIVED,
            "plan_start": DERIVED, "plan_start_short": DERIVED, "plan_end": DERIVED,
            "week1_monday": DERIVED, "race_week_monday": DERIVED,
            "weeks": _list(_CALENDAR_WEEK), "workout_naming_convention": DERIVED,
            "workout_example": DERIVED,
            "day_abbreviations": _map(_DAY_NAMES, DERIVED),
            "month_abbreviations": _map(tuple(str(i) for i in range(1, 13)), DERIVED),
        },
    },
    "schedule": {
        "required": ("description", "days"),
        "optional": (), "optional_non_null": False,
        "output_shape": {"description": DERIVED, "days": _map(_DAY_NAMES, _SCHEDULE_DAY)},
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
    classified = _assert_output_shape(
        document, schema["output_shape"], artifact=str(artifact))
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
    for path, classification in classified:
        if classification != DERIVED:
            continue
        if (schema.get("optional_non_null") and path in schema["optional"]
                and get_field(document, path) is None):
            continue
        if not any(path == field or path.startswith(field + ".")
                   or path.startswith(field + "[]") for field in fields):
            raise DerivedRegistryError(
                f"derived output lacks provenance for {artifact}: {path}")
    for field in required:
        get_field(document, field)
    return normalized


def _assert_output_shape(
    value: Any, shape: Any, *, artifact: str, path: str = "",
) -> List[tuple[str, str]]:
    """Validate and classify every present artifact path recursively.

    Unknown keys are reported before missing required keys. This makes a
    negative probe that adds one output fail for that output even when it uses
    a deliberately minimal fixture.
    """
    if isinstance(shape, str) and shape in {DERIVED, RAW}:
        return [(path, shape)] if path else []

    if isinstance(shape, tuple):
        tag = shape[0]
        if tag == "optional":
            return _assert_output_shape(
                value, shape[1], artifact=artifact, path=path)
        if tag == "list":
            if not isinstance(value, list):
                raise DerivedRegistryError(
                    f"artifact output shape mismatch for {artifact}: {path} must be a list")
            classified: List[tuple[str, str]] = []
            for item in value:
                classified.extend(_assert_output_shape(
                    item, shape[1], artifact=artifact, path=f"{path}[]"))
            return classified
        if tag == "map":
            if not isinstance(value, dict):
                raise DerivedRegistryError(
                    f"artifact output shape mismatch for {artifact}: {path} must be an object")
            allowed = shape[1]
            unknown = sorted(str(key) for key in value if str(key) not in allowed)
            if unknown:
                rendered = [f"{path}.{key}" if path else key for key in unknown]
                raise DerivedRegistryError(
                    f"unclassified output path(s) for {artifact}: {rendered}")
            classified = []
            for key, item in value.items():
                child = f"{path}.{key}" if path else str(key)
                classified.extend(_assert_output_shape(
                    item, shape[2], artifact=artifact, path=child))
            return classified
        raise DerivedRegistryError("invalid artifact output schema")

    if not isinstance(shape, dict):
        raise DerivedRegistryError("invalid artifact output schema")
    if not isinstance(value, dict):
        raise DerivedRegistryError(
            f"artifact output shape mismatch for {artifact}: {path or '<root>'} must be an object")

    actual = set(value) - ({"_derived"} if not path else set())
    declared = set(shape)
    unknown = sorted(str(key) for key in actual - declared)
    if unknown:
        rendered = [f"{path}.{key}" if path else key for key in unknown]
        raise DerivedRegistryError(
            f"unclassified output path(s) for {artifact}: {rendered}")

    classified = []
    for key in sorted(actual, key=str):
        child_shape = shape[key]
        if isinstance(child_shape, tuple) and child_shape[0] == "optional":
            child_shape = child_shape[1]
        child = f"{path}.{key}" if path else str(key)
        classified.extend(_assert_output_shape(
            value[key], child_shape, artifact=artifact, path=child))

    missing = sorted(
        key for key, child_shape in shape.items()
        if key not in actual
        and not (isinstance(child_shape, tuple) and child_shape[0] == "optional")
    )
    if missing:
        rendered = [f"{path}.{key}" if path else key for key in missing]
        raise DerivedRegistryError(
            f"artifact output shape is missing path(s) for {artifact}: {rendered}")
    return classified


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
