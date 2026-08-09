"""Field-complete, socket-free legacy-to-D0 migration comparison.

The legacy side consumes the exact pure request records extracted from the
hard-disabled adapter.  The D0 side consumes contract operations independently.
Only operation classes and fields the legacy adapter actually supported are
eligible for parity; D0 additions are returned as explicit migration deltas.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping


LEGACY_SUPPORTED_KINDS = {
    "workout_upsert", "calendar_note_upsert", "attachment_upsert",
    "course_entitlement_grant",
}

# These are migration dispositions, not parity claims.  The implementation
# notes record the corresponding product/spec decision for Phase 5 cutover.
INTENTIONAL_D0_DIFFERENCES = {
    "mental_task_upsert": "new_d0_operation_not_written_by_legacy",
    "threshold_update": "new_d0_positional_operation_not_written_by_legacy",
    "zone_update": "new_d0_positional_operation_not_written_by_legacy",
    "update": "d0_supersession_updates_legacy_skipped_done_keys",
    "delete": "d0_supersession_removes_resources_legacy_left_installed",
    "workout_external_marker": "legacy_external_id_to_d0_logical_remote_marker",
    "workout_sport_type": "legacy_sport_type_to_d0_tp_workout_type",
    "workout_segments": "legacy_segments_to_d0_tp_native_structure",
}
ALLOWED_DIFFERENCE_DISPOSITIONS = frozenset(INTENTIONAL_D0_DIFFERENCES.values())


class ParityError(AssertionError):
    """A remote-effect delta has no exact migration disposition."""


def contract_key(operation: Mapping[str, Any]) -> str:
    marker = f":{operation['kind']}:"
    logical_key = str(operation["logical_id"]).split(marker, 1)[-1]
    return f"{operation['kind']}:{logical_key}"


def _normalized_payload(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize the shared final-remote facts without inventing fields."""
    kind = str(record["kind"])
    payload = record["payload"]
    source = record["source"]
    if kind == "workout_upsert":
        return {
            # D0 deliberately changes the marker format, sport/workout type
            # representation, and segments representation. Keep the historical
            # six request fields in the comparison so those conversions are
            # visible and independently classified rather than discarded.
            "external_id": (payload.get("external_id") if source == "legacy"
                            else record.get("remote_marker")),
            "date": payload.get("date"),
            "title": payload.get("title"),
            "duration": (payload.get("duration") if source == "legacy"
                         else payload.get("total_seconds")),
            "sportType": (payload.get("sportType") if source == "legacy"
                          else payload.get("tp_workout_type")),
            "segments": (copy.deepcopy(payload.get("segments"))
                         if source == "legacy"
                         else copy.deepcopy(payload.get("structure"))),
        }
    if kind == "calendar_note_upsert":
        return {
            "date": payload.get("date"), "title": payload.get("title"),
            "body": (payload.get("text", "") if source == "legacy"
                     else payload.get("body", "")),
        }
    if kind == "attachment_upsert":
        parent_key = payload.get("parent_logical_key")
        if source == "d0":
            parent_id = str(payload.get("parent_logical_id") or "")
            parent_key = parent_id.split(":workout_upsert:", 1)[-1]
        return {
            "parent_logical_key": parent_key,
            "filename": payload.get("filename"),
            "sha256": payload.get("sha256"),
            "bytes_ref": payload.get("bytes_ref"),
        }
    if kind == "course_entitlement_grant":
        return {"product_id": payload.get("product_id")}
    if kind == "mental_task_upsert":
        return {
            "date": payload.get("date"), "title": payload.get("title"),
            "body": payload.get("body", ""),
        }
    return copy.deepcopy(dict(payload))


@dataclass
class FakeRemoteModel:
    """A field-complete remote with the legacy adapter's real done semantics."""

    state: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    legacy_done: set[str] = field(default_factory=set)
    d0_dispositions: Dict[str, str] = field(default_factory=dict)

    def apply_legacy_requests(self, requests: Iterable[Mapping[str, Any]]) -> None:
        for request in requests:
            operation_key = str(request["key"])
            if operation_key in self.legacy_done:
                continue
            remote_key = f"{request['kind']}:{request['logical_key']}"
            self.state[remote_key] = {
                "source": "legacy", "kind": str(request["kind"]),
                "path": str(request["path"]),
                "operation_key": operation_key,
                "payload": copy.deepcopy(dict(request["payload"])),
            }
            self.legacy_done.add(operation_key)

    def apply_contract(self, contract: Mapping[str, Any]) -> None:
        for operation in contract.get("operations") or []:
            key = contract_key(operation)
            disposition = operation["disposition"]
            if disposition in {"create", "update"}:
                self.state[key] = {
                    "source": "d0", "kind": operation["kind"],
                    "op_id": operation["op_id"],
                    "logical_id": operation["logical_id"],
                    "remote_marker": operation.get("remote_marker"),
                    "payload": copy.deepcopy(operation["payload"]),
                }
            elif disposition == "delete":
                self.state.pop(key, None)
            elif disposition == "keep":
                if key not in self.state:
                    raise AssertionError(f"keep referenced absent remote object: {key}")
            else:
                raise AssertionError(f"unknown disposition: {disposition}")
            self.d0_dispositions[key] = str(disposition)

    def raw_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Expose every request field for probes against invented behavior."""
        return copy.deepcopy(dict(sorted(self.state.items())))

    def normalized_snapshot(
        self, *, kinds: set[str] | None = None,
    ) -> Dict[str, Dict[str, Any]]:
        selected = kinds if kinds is not None else set(
            record["kind"] for record in self.state.values())
        return {
            key: {"kind": record["kind"], "payload": _normalized_payload(record)}
            for key, record in sorted(self.state.items())
            if record["kind"] in selected
        }

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Compatibility alias for normalized state."""
        return self.normalized_snapshot()


def classify_migration_differences(
    legacy: FakeRemoteModel, d0: FakeRemoteModel,
) -> Dict[str, Dict[str, Any]]:
    """Classify every non-parity delta instead of silently equating it."""
    legacy_state = legacy.normalized_snapshot()
    d0_state = d0.normalized_snapshot()
    result: Dict[str, Dict[str, Any]] = {}

    def add(key: str, disposition: str, legacy_value: Any, d0_value: Any) -> None:
        if disposition not in ALLOWED_DIFFERENCE_DISPOSITIONS:
            raise ParityError(f"unknown migration disposition for {key}: {disposition}")
        result[key] = {
            "disposition": disposition,
            "legacy": copy.deepcopy(legacy_value),
            "d0": copy.deepcopy(d0_value),
        }

    for key in sorted(set(legacy_state) | set(d0_state)):
        legacy_record = legacy_state.get(key)
        d0_record = d0_state.get(key)
        if legacy_record == d0_record:
            continue
        kind = key.split(":", 1)[0]
        if legacy_record is None:
            if kind not in {"mental_task_upsert", "threshold_update", "zone_update"}:
                raise ParityError(f"unclassified D0-only remote effect: {key}")
            add(key, INTENTIONAL_D0_DIFFERENCES[kind], None, d0_record)
            continue
        if d0_record is None:
            if d0.d0_dispositions.get(key) != "delete":
                raise ParityError(f"unclassified legacy-only remote effect: {key}")
            add(key, INTENTIONAL_D0_DIFFERENCES["delete"], legacy_record, None)
            continue
        if legacy_record.get("kind") != d0_record.get("kind"):
            raise ParityError(f"remote kind changed without disposition: {key}")

        legacy_payload = legacy_record.get("payload") or {}
        d0_payload = d0_record.get("payload") or {}
        if set(legacy_payload) != set(d0_payload):
            raise ParityError(f"normalized field inventory changed for {key}")
        for field_name in sorted(legacy_payload):
            legacy_value = legacy_payload[field_name]
            d0_value = d0_payload[field_name]
            if legacy_value == d0_value:
                continue
            delta_key = f"{key}:{field_name}"
            if d0.d0_dispositions.get(key) == "update":
                add(delta_key, INTENTIONAL_D0_DIFFERENCES["update"],
                    legacy_value, d0_value)
            elif kind == "workout_upsert" and field_name == "external_id":
                add(delta_key, INTENTIONAL_D0_DIFFERENCES["workout_external_marker"],
                    legacy_value, d0_value)
            elif kind == "workout_upsert" and field_name == "sportType":
                add(delta_key, INTENTIONAL_D0_DIFFERENCES["workout_sport_type"],
                    legacy_value, d0_value)
            elif kind == "workout_upsert" and field_name == "segments":
                add(delta_key, INTENTIONAL_D0_DIFFERENCES["workout_segments"],
                    legacy_value, d0_value)
            else:
                raise ParityError(
                    f"unclassified shared remote-field delta: {delta_key}")
    return result
