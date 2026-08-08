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
    *, required_fields: Iterable[str], revision: int,
) -> List[Dict[str, Any]]:
    """Fail closed when a declared athlete/review-facing derivation is absent.

    The inventory is deliberately explicit at each owning artifact. Adding a
    computed output therefore requires adding its provenance record in the
    same change instead of silently expanding an unreviewable output surface.
    """
    normalized = validate_registry(records)
    fields = [record["field"] for record in normalized]
    required = sorted(set(required_fields))
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
    result = []
    for record in validate_registry(records):
        result.append({
            **record,
            "id": f"{str(namespace).strip().upper()}_{record['id']}",
            "value": get_field(document, record["field"]),
        })
    return result
