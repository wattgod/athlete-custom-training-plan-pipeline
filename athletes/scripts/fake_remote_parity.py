"""Field-aware, socket-free legacy-to-D0 remote-effect parity model."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping


DATED_KINDS = {
    "workout_upsert", "calendar_note_upsert", "attachment_upsert",
    "mental_task_upsert",
}


def _normalized_payload(kind: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    if kind == "attachment_upsert":
        parent = str(result.pop("parent_logical_id", ""))
        marker = ":workout_upsert:"
        result["parent_logical_key"] = parent.split(marker, 1)[-1]
    return result


def legacy_desired_state(
    manifest: Mapping[str, Any], *, singletons: Mapping[str, Dict[str, Any]] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Normalize every legacy operation class into complete remote fields."""
    result: Dict[str, Dict[str, Any]] = {}
    for item in manifest.get("workouts") or []:
        payload = {key: item.get(key) for key in (
            "date", "title", "description", "tp_workout_type",
            "total_seconds", "tss_planned", "structure")}
        result[f"workout_upsert:{item['logical_key']}"] = {
            "kind": "workout_upsert", "payload": payload}
    for item in manifest.get("native_notes") or []:
        result[f"calendar_note_upsert:{item['logical_key']}"] = {
            "kind": "calendar_note_upsert", "payload": {
                "date": item.get("date"), "title": item.get("title"),
                "body": item.get("text", "")}}
    for item in manifest.get("attachments") or []:
        result[f"attachment_upsert:{item['logical_key']}"] = {
            "kind": "attachment_upsert", "payload": {
                "parent_logical_key": item["parent_logical_key"],
                "filename": item["filename"], "sha256": item["sha256"],
                "bytes_ref": item["bytes_ref"]}}
    for item in manifest.get("mental_training_tasks") or []:
        result[f"mental_task_upsert:{item['logical_key']}"] = {
            "kind": "mental_task_upsert", "payload": {
                "date": item.get("date"),
                "title": str(item.get("title") or item["logical_key"].replace("_", " ").title()),
                "body": item.get("body", "")}}
    entitlement = manifest.get("course_entitlement")
    if entitlement:
        key = entitlement["logical_key"]
        result[f"course_entitlement_grant:{key}"] = {
            "kind": "course_entitlement_grant",
            "payload": {"product_id": entitlement["product_id"]}}
    for key, spec in (singletons or {}).items():
        result[f"{spec['kind']}:{key}"] = {
            "kind": spec["kind"], "payload": copy.deepcopy(spec["payload"])}
    return result


def contract_key(operation: Mapping[str, Any]) -> str:
    marker = f":{operation['kind']}:"
    return f"{operation['kind']}:{str(operation['logical_id']).split(marker, 1)[-1]}"


@dataclass
class FakeRemoteModel:
    """A complete normalized remote state, with field-aware mutations."""

    state: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def seed(self, desired: Mapping[str, Dict[str, Any]]) -> None:
        self.state = copy.deepcopy(dict(desired))

    def reconcile_legacy(self, desired: Mapping[str, Dict[str, Any]]) -> None:
        # Legacy desired-state adapter: dated objects absent from the next
        # manifest are deleted; positional resources remain unless supplied.
        for key in list(self.state):
            if self.state[key]["kind"] in DATED_KINDS and key not in desired:
                del self.state[key]
        for key, value in desired.items():
            self.state[key] = copy.deepcopy(value)

    def apply_contract(self, contract: Mapping[str, Any]) -> None:
        for operation in contract.get("operations") or []:
            key = contract_key(operation)
            disposition = operation["disposition"]
            if disposition in {"create", "update"}:
                self.state[key] = {
                    "kind": operation["kind"],
                    "payload": _normalized_payload(
                        operation["kind"], operation["payload"]),
                }
            elif disposition == "delete":
                self.state.pop(key, None)
            elif disposition == "keep":
                if key not in self.state:
                    raise AssertionError(f"keep referenced absent remote object: {key}")
            else:
                raise AssertionError(f"unknown disposition: {disposition}")

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return copy.deepcopy(dict(sorted(self.state.items())))
