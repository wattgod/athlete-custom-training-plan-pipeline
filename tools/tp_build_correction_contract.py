#!/usr/bin/env python3
"""Build a receipt-bound TrainingPeaks correction from canonical PlanIR.

This tool performs no provider calls and no mutations. It consumes a fresh
read-only provider inventory plus the prior sealed apply receipt, preserves
unowned calendar objects, and delegates all reconciliation semantics and model
sealing to ``apply_contract.build_contract``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
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
from fulfillment_state import load as load_state  # noqa: E402


class CorrectionContractError(ValueError):
    pass


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorrectionContractError(f"{path.name} must contain an object")
    return value


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
    raise CorrectionContractError("provider inventory contains unsupported kind")


def _snapshot(snapshot_dir: Path, payload: dict[str, Any]) -> str:
    snapshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    digest = digest_payload(payload)
    path = snapshot_dir / f"{digest}.json"
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") != encoded:
        raise CorrectionContractError("payload snapshot digest collision")
    path.write_text(encoded, encoding="utf-8")
    path.chmod(0o600)
    return str(path.resolve())


def build_correction(
    *, athlete_dir: Path, prior_state_path: Path, prior_contract_path: Path,
    provider_inventory_path: Path, output_path: Path,
) -> dict[str, Any]:
    current = load_state(athlete_dir / "fulfillment_status.json")
    prior = load_state(prior_state_path)
    prior_contract = _json(prior_contract_path)
    provider = _json(provider_inventory_path)
    plan_ir = _json(athlete_dir / "plan_ir.json")
    canonical_model = _json(athlete_dir / "canonical_training_model.json")

    order_id = str(current.get("order_id") or "")
    tp_id = str((current.get("platform_identity") or {}).get("tp_athlete_id") or "")
    revision = int(current.get("generation_revision") or 0)
    if (current.get("status") not in {"GENERATED", "BLOCKED_REVIEW"}
            or current.get("delivery_platform") != "trainingpeaks"):
        raise CorrectionContractError("current revision is not a generated TP plan")
    if prior.get("status") != "APPLIED":
        raise CorrectionContractError("prior state is not provider-verified APPLIED")
    if (prior.get("order_id") != order_id
            or prior_contract.get("order_id") != order_id
            or prior_contract.get("tp_athlete_id") != tp_id
            or str(provider.get("athlete_id") or "") != tp_id
            or int(prior.get("generation_revision") or 0) >= revision):
        raise CorrectionContractError("correction identity or revision binding mismatch")

    prior_ops = {
        str(op.get("op_id")): op for op in prior_contract.get("operations") or []
        if isinstance(op, dict)
    }
    landed = (prior.get("application_attempt") or {}).get("landed") or []
    if len(prior_ops) != len(landed):
        raise CorrectionContractError("prior receipt set is incomplete")
    owner_by_remote: dict[tuple[str, str], dict[str, Any]] = {}
    for receipt in landed:
        op_id = str(receipt.get("op_id") or "")
        operation = prior_ops.get(op_id)
        remote_id = str(receipt.get("remote_id") or "")
        if (operation is None or not remote_id
                or receipt.get("kind") != operation.get("kind")):
            raise CorrectionContractError("prior receipt is not contract-exact")
        key = (str(operation["kind"]), remote_id)
        if key in owner_by_remote:
            raise CorrectionContractError("duplicate remote receipt identity")
        owner_by_remote[key] = operation

    rows: list[tuple[str, dict[str, Any]]] = []
    rows.extend(("workout_upsert", row) for row in provider.get("workouts") or [])
    rows.extend(("calendar_note_upsert", row) for row in provider.get("notes") or [])
    provider_keys = {(kind, str(row.get("id") or "")) for kind, row in rows}
    if set(owner_by_remote) - provider_keys:
        raise CorrectionContractError("a receipt-bound provider object is missing")

    snapshots: dict[str, dict[str, Any]] = {}
    effective_inventory: dict[str, dict[str, Any]] = {}
    protected: dict[str, dict[str, Any]] = {}
    snapshot_dir = athlete_dir / "correction_snapshots"
    per_date: dict[str, int] = {}

    for kind, row in rows:
        remote_id = str(row.get("id") or "")
        if not remote_id:
            raise CorrectionContractError("provider row has no remote ID")
        payload = provider_payload(kind, row)
        owner = owner_by_remote.get((kind, remote_id))
        if owner is not None:
            logical_id = str(owner["logical_id"])
            last_op_id = str(owner["op_id"])
            is_protected = owner.get("disposition") == "keep"
        else:
            date = str(payload.get("date") or "")
            if kind == "workout_upsert":
                per_date[date] = per_date.get(date, 1000000) + 1
                logical_key = f"{date}#{per_date[date]}"
            else:
                logical_key = f"protected-{date}-{remote_id}"
            logical_id = f"{order_id}:{kind}:{logical_key}"
            last_op_id = f"external-provider-{remote_id}"
            is_protected = True
        if logical_id in effective_inventory:
            raise CorrectionContractError("provider resources collide logically")
        ref = _snapshot(snapshot_dir, payload)
        snapshots[ref] = payload
        effective_inventory[logical_id] = {
            "remote_id": remote_id,
            "desired_digest": digest_payload(payload),
            "payload_snapshot_ref": ref,
            "kind": kind,
            "last_op_id": last_op_id,
        }
        if is_protected:
            protected[logical_id] = {"kind": kind, "payload": payload}

    def read_snapshot(ref: str) -> dict[str, Any]:
        try:
            return snapshots[ref]
        except KeyError as exc:
            raise CorrectionContractError("unknown correction snapshot") from exc

    contract = build_contract(
        plan_ir,
        order_id=order_id,
        tp_athlete_id=tp_id,
        generation_revision=revision,
        canonical_model=canonical_model,
        review_items=current.get("review_items") or [],
        guide_sources=guide_source_digests(athlete_dir),
        athlete_dir=athlete_dir,
        effective_remote_inventory=effective_inventory,
        protected_resources=protected,
        payload_snapshot_reader=read_snapshot,
        delivery_platform="trainingpeaks",
    )
    emit_contract(output_path, contract)
    return contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--athlete-dir", type=Path, required=True)
    parser.add_argument("--prior-state", type=Path, required=True)
    parser.add_argument("--prior-contract", type=Path, required=True)
    parser.add_argument("--provider-inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = build_correction(
        athlete_dir=args.athlete_dir.resolve(),
        prior_state_path=args.prior_state.resolve(),
        prior_contract_path=args.prior_contract.resolve(),
        provider_inventory_path=args.provider_inventory.resolve(),
        output_path=args.output.resolve(),
    )
    counts: dict[str, int] = {}
    for operation in contract["operations"]:
        counts[operation["disposition"]] = counts.get(operation["disposition"], 0) + 1
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
