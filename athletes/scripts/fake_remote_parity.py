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
    "workout_rich_fields": (
        "d0 adds description, TP workout type, TSS, and TP-native structure; "
        "legacy wrote only title/date/duration/sportType/segments"
    ),
}


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
            "date": payload.get("date"),
            "title": payload.get("title"),
            "duration": (payload.get("duration") if source == "legacy"
                         else payload.get("total_seconds")),
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
                    "payload": copy.deepcopy(operation["payload"]),
                }
            elif disposition == "delete":
                self.state.pop(key, None)
            elif disposition == "keep":
                if key not in self.state:
                    raise AssertionError(f"keep referenced absent remote object: {key}")
            else:
                raise AssertionError(f"unknown disposition: {disposition}")

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
) -> Dict[str, str]:
    """Classify every non-parity delta instead of silently equating it."""
    legacy_state = legacy.normalized_snapshot()
    d0_state = d0.normalized_snapshot()
    result: Dict[str, str] = {}
    for key in sorted(set(legacy_state) | set(d0_state)):
        if legacy_state.get(key) == d0_state.get(key):
            continue
        kind = key.split(":", 1)[0]
        if kind in {"mental_task_upsert", "threshold_update", "zone_update"}:
            result[key] = INTENTIONAL_D0_DIFFERENCES[kind]
        elif key in legacy_state and key not in d0_state:
            result[key] = INTENTIONAL_D0_DIFFERENCES["delete"]
        elif key in legacy_state and key in d0_state:
            result[key] = INTENTIONAL_D0_DIFFERENCES["update"]
        else:
            result[key] = "d0_create_not_present_in_legacy_remote"
    return result
