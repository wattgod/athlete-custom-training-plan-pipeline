#!/usr/bin/env python3
"""Adopt marked legacy TrainingPeaks objects into a canonical correction.

This tool performs no provider calls and no mutations. It consumes a current
GET-only provider inventory, maps exact visible legacy lineage markers to the
current order, protects every unmarked workout/note, seals event-card evidence,
and delegates all operation construction to ``apply_contract.build_contract``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "athletes" / "scripts"))
sys.path.insert(0, str(ROOT / "webhook"))

from apply_contract import (  # noqa: E402
    build_contract,
    digest_payload,
    emit_contract,
    guide_source_digests,
)
from d2_identity import d2_contract_inputs  # noqa: E402
from fulfillment_state import load as load_state  # noqa: E402


class AdoptionContractError(ValueError):
    pass


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdoptionContractError(f"{path.name} is unavailable or invalid") from exc
    if not isinstance(value, dict):
        raise AdoptionContractError(f"{path.name} must contain an object")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def provider_payload(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    if kind == "workout_upsert":
        return {
            "date": str(row.get("date") or ""),
            "title": str(row.get("title") or ""),
            "description": str(row.get("description") or ""),
            "tp_workout_type": row.get("workoutTypeValueId"),
            "total_seconds": round(float(row.get("totalTimePlanned") or 0) * 3600),
            "tss_planned": row.get("tssPlanned"),
            "structure": row.get("structure"),
        }
    if kind == "calendar_note_upsert":
        return {
            "date": str(row.get("date") or ""),
            "title": str(row.get("title") or ""),
            "body": str(row.get("description") or ""),
        }
    raise AdoptionContractError("provider inventory contains unsupported kind")


def _snapshot(snapshot_dir: Path, payload: dict[str, Any]) -> str:
    snapshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    digest = digest_payload(payload)
    path = snapshot_dir / f"{digest}.json"
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") != encoded:
        raise AdoptionContractError("payload snapshot digest collision")
    path.write_text(encoded, encoding="utf-8")
    path.chmod(0o600)
    return str(path.resolve())


def _marker(text: str, *, order_id: str, expected_kind: str) -> str | None:
    pattern = re.compile(
        r"\[GG:(?P<logical>" + re.escape(order_id)
        + r":(?P<kind>workout_upsert|calendar_note_upsert):[^\]\r\n]+)\]"
    )
    matches = list(pattern.finditer(str(text or "")))
    if not matches:
        return None
    if len(matches) != 1 or matches[0].group("kind") != expected_kind:
        raise AdoptionContractError("legacy lineage marker is ambiguous or kind-mismatched")
    return matches[0].group("logical")


def build_adoption(
    *, athlete_dir: Path, provider_inventory_path: Path, output_path: Path,
    expected_owned_workouts: int, expected_owned_notes: int,
) -> dict[str, Any]:
    state = load_state(athlete_dir / "fulfillment_status.json")
    provider = _json(provider_inventory_path)
    plan_ir = _json(athlete_dir / "plan_ir.json")
    canonical_path = athlete_dir / "canonical_training_model.json"
    canonical_model = _json(canonical_path)

    order_id = str(state.get("order_id") or "")
    tp_id = str((state.get("platform_identity") or {}).get("tp_athlete_id") or "")
    revision = int(state.get("generation_revision") or 0)
    if (state.get("status") not in {"GENERATED", "BLOCKED_REVIEW"}
            or state.get("delivery_platform") != "trainingpeaks"
            or not order_id or not tp_id or revision < 1):
        raise AdoptionContractError("current revision is not a bound generated TP plan")
    if (provider.get("contract_version")
            != "trainingpeaks_provider_inventory/v1"
            or str(provider.get("athlete_id") or "") != tp_id):
        raise AdoptionContractError("provider inventory identity or version mismatch")
    rows_by_kind = {
        "workout_upsert": provider.get("workouts") or [],
        "calendar_note_upsert": provider.get("notes") or [],
    }
    if any(not isinstance(rows, list) for rows in rows_by_kind.values()):
        raise AdoptionContractError("provider inventory rows are invalid")
    events = provider.get("events") or []
    if not isinstance(events, list):
        raise AdoptionContractError("provider event inventory is invalid")

    snapshots: dict[str, dict[str, Any]] = {}
    effective_inventory: dict[str, dict[str, Any]] = {}
    protected: dict[str, dict[str, Any]] = {}
    owned_counts = {"workout_upsert": 0, "calendar_note_upsert": 0}
    snapshot_dir = athlete_dir / "adoption_snapshots"

    for kind, rows in rows_by_kind.items():
        for row in rows:
            if not isinstance(row, dict) or not str(row.get("id") or ""):
                raise AdoptionContractError("provider row has no stable remote identity")
            remote_id = str(row["id"])
            payload = provider_payload(kind, row)
            logical_id = _marker(
                str(row.get("description") or ""),
                order_id=order_id, expected_kind=kind,
            )
            is_protected = logical_id is None
            if logical_id is None:
                # Protected (unmarked) provider rows. The logical-key grammar
                # in apply_contract.validate_contract differs by kind: a
                # workout key must be "YYYY-MM-DD#<n>", so the numeric remote
                # id is the sequence (the Aug 23 2026 publisher did the same);
                # notes keep the "protected-<date>-<id>" slug.
                if kind == "workout_upsert":
                    sequence = (remote_id if remote_id.isdigit()
                                else str(int(digest_payload({"id": remote_id})[:12], 16)))
                    logical_id = f"{order_id}:{kind}:{payload.get('date')}#{sequence}"
                else:
                    logical_id = (
                        f"{order_id}:{kind}:protected-"
                        f"{payload.get('date')}-{remote_id}"
                    )
            else:
                owned_counts[kind] += 1
            if logical_id in effective_inventory:
                raise AdoptionContractError("provider resources collide logically")
            ref = _snapshot(snapshot_dir, payload)
            snapshots[ref] = payload
            effective_inventory[logical_id] = {
                "remote_id": remote_id,
                "desired_digest": digest_payload(payload),
                "payload_snapshot_ref": ref,
                "kind": kind,
                "last_op_id": f"external-provider-{remote_id}",
            }
            if is_protected:
                protected[logical_id] = {"kind": kind, "payload": payload}

    expected = {
        "workout_upsert": int(expected_owned_workouts),
        "calendar_note_upsert": int(expected_owned_notes),
    }
    if owned_counts != expected:
        raise AdoptionContractError(
            f"owned marker counts differ from the reviewed expectation: {owned_counts}")

    evidence = {
        "contract_version": "trainingpeaks_calendar_inventory_evidence/v1",
        "provider_inventory_contract_version": provider["contract_version"],
        "provider_inventory_sha256": _digest(provider),
        "retrieved_at": provider.get("retrieved_at"),
        "period": copy.deepcopy(provider.get("period") or {}),
        "complete": True,
        "read_surfaces": ["events", "notes", "workouts"],
        "counts": {
            "workouts": len(rows_by_kind["workout_upsert"]),
            "notes": len(rows_by_kind["calendar_note_upsert"]),
            "events": len(events),
        },
        "event_resources": [
            {"remote_id": str(row.get("id") or ""), "digest": _digest(row)}
            for row in events if isinstance(row, dict)
        ],
    }
    protection = dict(canonical_model.get("calendar_protection") or {})
    if protection.get("requested") is not True:
        raise AdoptionContractError("canonical model did not request calendar protection")
    protection["inventory_evidence"] = evidence
    canonical_model["calendar_protection"] = protection

    def read_snapshot(ref: str) -> dict[str, Any]:
        try:
            return snapshots[ref]
        except KeyError as exc:
            raise AdoptionContractError("unknown adoption snapshot") from exc

    _tp_id, singleton_desires, inspection = d2_contract_inputs(state)
    contract = build_contract(
        plan_ir,
        order_id=order_id,
        tp_athlete_id=tp_id,
        generation_revision=revision,
        canonical_model=canonical_model,
        review_items=state.get("review_items") or [],
        guide_sources=guide_source_digests(athlete_dir),
        athlete_dir=athlete_dir,
        effective_remote_inventory=effective_inventory,
        protected_resources=protected,
        payload_snapshot_reader=read_snapshot,
        singleton_desires=singleton_desires,
        inspection=inspection,
        delivery_platform="trainingpeaks",
    )
    _atomic_json(canonical_path, canonical_model)
    emit_contract(output_path, contract)
    return contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--athlete-dir", type=Path, required=True)
    parser.add_argument("--provider-inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-owned-workouts", type=int, required=True)
    parser.add_argument("--expected-owned-notes", type=int, required=True)
    args = parser.parse_args()
    contract = build_adoption(
        athlete_dir=args.athlete_dir.resolve(),
        provider_inventory_path=args.provider_inventory.resolve(),
        output_path=args.output.resolve(),
        expected_owned_workouts=args.expected_owned_workouts,
        expected_owned_notes=args.expected_owned_notes,
    )
    counts: dict[str, int] = {}
    for operation in contract["operations"]:
        disposition = str(operation["disposition"])
        counts[disposition] = counts.get(disposition, 0) + 1
    print(json.dumps({
        "order_id": contract["order_id"],
        "generation_revision": contract["generation_revision"],
        "operation_count": len(contract["operations"]),
        "dispositions": counts,
        "model_seal": contract["model_seal"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
