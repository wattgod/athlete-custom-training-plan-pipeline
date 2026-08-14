"""Closed §6 byte-comparison harness, including all seven TP kinds."""

from __future__ import annotations

import copy
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webhook"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_contract import KINDS
from email_templates import FOLLOWUP_SEQUENCE
from q0_surface_inventory import (
    TP_KINDS, Q0Mismatch, capture_q0, compare_q0,
    deterministic_mime_bytes, followup_bytes,
)


def _operation(kind: str, disposition: str, index: int, payload: dict | None):
    logical_id = f"order-q0:{kind}:fixture-{index}"
    return {
        "op_id": f"{logical_id}@r1", "logical_id": logical_id, "kind": kind,
        "disposition": disposition, "payload": payload,
        "expected_digest": (hashlib.sha256(str(payload).encode()).hexdigest()
                            if payload is not None else None),
        "prior_payload": None, "before_value": None,
        "predecessor": {"remote_id": f"remote-{index}"},
        "rollback_strategy": "fixture", "remote_marker": logical_id,
    }


def _fixture(tmp_path: Path):
    root = tmp_path / "athlete"
    (root / "workouts").mkdir(parents=True)
    files = {
        "training_guide.html": b"<html>guide</html>",
        "training_guide.pdf": b"%PDF-1.4\nfixture\n%%EOF\n",
        "dashboard.html": b"<html>dashboard</html>",
        "plan_preview.html": b"<html>preview</html>",
        "fueling.yaml": b"fuel: exact\n",
    }
    for name, payload in files.items():
        (root / name).write_bytes(payload)
    (root / "workouts" / "W01_Test.zwo").write_bytes(b"<workout_file/>")
    attachment = b"attachment bytes"
    (root / "generic.txt").write_bytes(attachment)
    payloads = {
        "workout_upsert": {"date": "2026-08-17", "title": "Workout",
                           "description": "exact", "tp_workout_type": 2,
                           "total_seconds": 3600, "tss_planned": 40,
                           "structure": {"steps": []}},
        "calendar_note_upsert": {"date": "2026-08-17", "title": "Note",
                                 "body": "exact note"},
        "attachment_upsert": {"parent_logical_id": "parent", "filename": "generic.txt",
                              "sha256": hashlib.sha256(attachment).hexdigest(),
                              "bytes_ref": "generic.txt"},
        "mental_task_upsert": {"date": "2026-08-17", "title": "Task",
                               "body": "exact task"},
        "course_entitlement_grant": {"product_id": "course:fixture"},
        "threshold_update": {"metric": "ftp", "after_value": 250, "unit": "W"},
        "zone_update": {"zone_set": "power", "after_table": [{"low": 0, "high": 100}]},
    }
    dispositions = ("create", "update", "keep", "delete", "create", "update", "keep")
    operations = [_operation(kind, dispositions[index], index, payloads[kind])
                  for index, kind in enumerate(sorted(TP_KINDS))]
    contract = {"operations": operations}
    mime = deterministic_mime_bytes(
        order_id="order-q0", revision=1, sender="coach@example.test",
        recipient="athlete@example.test", subject="Plan", plain_body="plain",
        html_body="<p>html</p>", guide_name="training_guide.pdf",
        guide_bytes=files["training_guide.pdf"],
        at=datetime(2026, 8, 6, 15, tzinfo=timezone.utc),
    )
    followups = followup_bytes(FOLLOWUP_SEQUENCE, "Rider")
    inventory = capture_q0(
        athlete_dir=root, contract=contract,
        endure_payload={"athlete": {"email": "athlete@example.test"},
                        "plan": {"name": "Plan"}},
        mime_bytes=mime, followups=followups, published_dir=root,
    )
    return inventory, contract


def test_closed_q0_inventory_compares_every_surface_and_tp_kind(tmp_path):
    inventory, contract = _fixture(tmp_path)
    assert TP_KINDS == KINDS
    assert {operation["kind"] for operation in contract["operations"]} == KINDS
    assert {operation["disposition"] for operation in contract["operations"]} == {
        "create", "update", "keep", "delete",
    }
    assert {
        "zwo/W01_Test.zwo", "file/training_guide.html",
        "file/training_guide.pdf", "file/dashboard.html",
        "file/plan_preview.html", "file/fueling.yaml",
        "bundle/member_inventory.json", "bundle/customer.zip",
        "trainingpeaks/operations.json", "endure/payload.json",
        "gmail/draft.eml", "followups/day-1-3-7.json",
        "published/training_guide.html", "published/training_guide.pdf",
    } == set(inventory)
    compare_q0(inventory, copy.deepcopy(inventory))

    for surface in sorted(inventory):
        changed = copy.deepcopy(inventory)
        changed[surface] += b"changed"
        with pytest.raises(Q0Mismatch, match="athlete-facing bytes changed"):
            compare_q0(inventory, changed)

    removed = copy.deepcopy(inventory)
    removed.pop("gmail/draft.eml")
    with pytest.raises(Q0Mismatch, match="surface inventory changed"):
        compare_q0(inventory, removed)


def test_fixed_mime_zip_and_followups_are_repeatable(tmp_path):
    first, _ = _fixture(tmp_path / "first")
    second, _ = _fixture(tmp_path / "second")
    compare_q0(first, second)
    assert b"\r\n" in first["gmail/draft.eml"]
