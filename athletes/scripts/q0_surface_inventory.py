"""Closed, byte-exact E1 Q0 athlete-surface capture and comparison."""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.policy import SMTP
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


CUSTOMER_DELIVERABLES = (
    "training_guide.html", "training_guide.pdf", "dashboard.html",
    "plan_preview.html", "fueling.yaml",
)
TP_KINDS = {
    "workout_upsert", "calendar_note_upsert", "attachment_upsert",
    "mental_task_upsert", "course_entitlement_grant", "threshold_update",
    "zone_update",
}
TP_OPERATION_FIELDS = (
    "op_id", "logical_id", "kind", "disposition", "payload",
    "expected_digest", "prior_payload", "before_value", "predecessor",
    "rollback_strategy", "remote_marker",
)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class Q0Mismatch(AssertionError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            info = zipfile.ZipInfo(name.replace(os.sep, "/"), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, payload)
    return output.getvalue()


def customer_bundle_members(athlete_dir: Path | str) -> list[tuple[str, bytes]]:
    root = Path(athlete_dir)
    members = [(name, (root / name).read_bytes())
               for name in CUSTOMER_DELIVERABLES if (root / name).is_file()]
    workouts = root / "workouts"
    if workouts.is_dir():
        members.extend((str(path.relative_to(root)), path.read_bytes())
                       for path in sorted(workouts.rglob("*")) if path.is_file())
    return members


def trainingpeaks_projection(contract: Mapping[str, Any],
                             athlete_dir: Path | str) -> bytes:
    """Serialize every athlete field plus all adapter bookkeeping exactly."""
    root = Path(athlete_dir)
    operations = []
    for operation in contract.get("operations", []):
        row = {field: operation.get(field) for field in TP_OPERATION_FIELDS}
        row["raw_attachment_bytes_hex"] = None
        if operation.get("kind") == "attachment_upsert":
            payload = operation.get("payload") or operation.get("prior_payload") or {}
            ref = payload.get("bytes_ref")
            path = root / str(ref) if ref else None
            if path is not None and path.is_file():
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != payload.get("sha256"):
                    raise Q0Mismatch("attachment bytes do not match apply payload digest")
                row["raw_attachment_bytes_hex"] = raw.hex()
        operations.append(row)
    return canonical_json(operations)


def deterministic_mime_bytes(*, order_id: str, revision: int,
                             sender: str, recipient: str, subject: str,
                             plain_body: str, html_body: str,
                             guide_name: str, guide_bytes: bytes,
                             at: datetime) -> bytes:
    """Build the fixed RFC 5322/MIME representation required by §6.7."""
    token = hashlib.sha256(f"{order_id}:r{revision}".encode()).hexdigest()[:24]
    message = MIMEMultipart("mixed", boundary=f"gg-{token}-mixed")
    message["Date"] = format_datetime(at.astimezone(timezone.utc))
    message["Message-ID"] = f"<{order_id}.r{revision}@q0.gravelgod.invalid>"
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    alternative = MIMEMultipart("alternative", boundary=f"gg-{token}-alternative")
    alternative.attach(MIMEText(plain_body, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alternative)
    attachment = MIMEBase("application", (
        "pdf" if guide_name.lower().endswith(".pdf") else "html"))
    attachment.set_payload(guide_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=guide_name)
    message.attach(attachment)
    return message.as_bytes(policy=SMTP)


def followup_bytes(sequence: list[Mapping[str, Any]], first_name: str) -> bytes:
    rows = [{"day": row["day"], "subject": row["subject"],
             "body": row["template"].format(first_name=first_name)}
            for row in sequence]
    if [row["day"] for row in rows] != [1, 3, 7]:
        raise Q0Mismatch("follow-up inventory is not exactly day 1/3/7")
    return canonical_json(rows)


def capture_q0(*, athlete_dir: Path | str, contract: Mapping[str, Any],
               endure_payload: Mapping[str, Any], mime_bytes: bytes,
               followups: bytes, published_dir: Path | str | None = None
               ) -> dict[str, bytes]:
    root = Path(athlete_dir)
    result: dict[str, bytes] = {}
    for workout in sorted((root / "workouts").glob("*.zwo")):
        result[f"zwo/{workout.name}"] = workout.read_bytes()
    for name in CUSTOMER_DELIVERABLES:
        path = root / name
        if path.is_file():
            result[f"file/{name}"] = path.read_bytes()
        else:
            result[f"availability/{name}"] = b"not-emitted"
    members = customer_bundle_members(root)
    result["bundle/member_inventory.json"] = canonical_json([
        {"name": name, "bytes_hex": payload.hex()} for name, payload in members
    ])
    result["bundle/customer.zip"] = _zip_bytes(members)
    result["trainingpeaks/operations.json"] = trainingpeaks_projection(contract, root)
    result["endure/payload.json"] = canonical_json(endure_payload)
    result["gmail/draft.eml"] = mime_bytes
    result["followups/day-1-3-7.json"] = followups
    if published_dir is not None:
        published = Path(published_dir)
        for name in ("training_guide.html", "training_guide.pdf"):
            path = published / name
            if path.is_file():
                result[f"published/{name}"] = path.read_bytes()
            else:
                result[f"availability/published/{name}"] = b"not-emitted"
    else:
        result["availability/published-guide"] = b"publishing-disabled"
    return result


def compare_q0(baseline: Mapping[str, bytes], current: Mapping[str, bytes]) -> None:
    if set(baseline) != set(current):
        missing = sorted(set(baseline) - set(current))
        added = sorted(set(current) - set(baseline))
        raise Q0Mismatch(f"surface inventory changed: missing={missing}, added={added}")
    changed = [name for name in sorted(baseline)
               if baseline[name] != current[name]]
    if changed:
        raise Q0Mismatch(f"athlete-facing bytes changed: {changed}")


def digest_inventory(inventory: Mapping[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(payload).hexdigest()
            for name, payload in sorted(inventory.items())}
