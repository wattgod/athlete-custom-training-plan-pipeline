"""D0 offline projection for the normative ``apply_contract/v1``.

This module deliberately has no HTTP, browser, credential, or apply code.  It
turns the canonical PlanIR projection plus an optional fake-server inspection
snapshot into a complete reconciliation document and validates that document
before it is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
import re

from jsonschema import Draft202012Validator

from delivery_notes import render_coached_weekly_notes


CONTRACT_VERSION = "apply_contract/v1"
DATED_KINDS = {
    "workout_upsert", "calendar_note_upsert", "attachment_upsert",
    "mental_task_upsert",
}
MARKER_KINDS = set(DATED_KINDS)
SINGLETON_KINDS = {"threshold_update", "zone_update"}
ENTITLEMENT_KIND = "course_entitlement_grant"
KINDS = DATED_KINDS | SINGLETON_KINDS | {ENTITLEMENT_KIND}
DISPOSITIONS = {"create", "update", "keep", "delete"}
INVENTORY_FIELDS = {
    "remote_id", "desired_digest", "payload_snapshot_ref", "kind", "last_op_id",
}
SUPPORTED_TP_WORKOUT_TYPES = frozenset({2, 7, 9})
LEGACY_PRIOR_TP_WORKOUT_TYPES = frozenset({2, 7, 9, 100})
SnapshotReader = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class OperationProvenance:
    """Immutable operation provenance from a sealed containing contract.

    ``contract_digest`` is the trusted SHA-256 of ``contract_bytes`` in the
    canonical D0 serialization.  Keeping the complete contract bytes in the
    record lets the consumer prove that the looked-up operation is a member of
    the revision whose digest and model seal were verified by the reader.
    """

    contract_bytes: bytes
    contract_digest: str
    model_seal: str


OperationReader = Callable[[str], OperationProvenance]


class ApplyContractError(ValueError):
    """The offline contract is incomplete, ambiguous, or schema-invalid."""


MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS = 360
_VISIBLE_INTERNAL_TAG = re.compile(
    r"\[[A-Z][A-Z0-9 _-]{0,40}:\s*[^\]]*\]", re.IGNORECASE)
_FUEL_TAG = re.compile(
    r"^\[(FUEL|LONG-RIDE FUEL|RACE FUEL):\s*([^\]]+)\]\s*$",
    re.IGNORECASE,
)
_ATHLETE_WEEK_BOILERPLATE = re.compile(
    r"^.+?\s+-\s+Week\s+\d+/\d+\s+-\s+\d+\s+weeks?\s+to\s+.+$",
    re.IGNORECASE | re.MULTILINE,
)
_PHASE_BOILERPLATE = re.compile(
    r"^Phase:\s*.+$", re.IGNORECASE | re.MULTILINE)
_DROP_DESCRIPTION_SECTION = re.compile(
    r"(?ms)^\s*(?:PURPOSE|DIMENSIONS):\s*.*?(?=^\s*[A-Z][A-Z -]{2,}:\s*|\Z)"
)
_DESCRIPTION_SECTION = re.compile(
    r"^\s*[•*-]?\s*(?P<label>FUEL|FUELING PLAN|NUTRITION|HYDRATION|"
    r"EXECUTION|HOW TO RIDE IT|AUDIBLE|POSITION|CADENCE):\s*"
    r"(?P<body>.*?)(?=^\s*[•*-]?\s*[A-Z][A-Z /-]{2,}:\s*|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def _clean_description_detail(value: str) -> str:
    value = re.split(r"\n\s*\n", value, maxsplit=1)[0]
    lines = []
    for raw in value.splitlines():
        line = re.sub(r"^\s*[•*-]\s*", "", raw).strip()
        if not line:
            continue
        line = re.sub(
            r"\bPractice this prescription\.?", "", line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _concise_structured_description(text: str) -> str:
    # Some legacy generators flattened headings into one long line. Restore
    # section boundaries before selecting only details that are not already in
    # TrainingPeaks' executable step graph.
    text = re.sub(
        r"\s+(?=(?:WARM-UP|MAIN SET|COOL-DOWN|EXECUTION|HOW TO RIDE IT|"
        r"FUEL|NUTRITION|HYDRATION|AUDIBLE|POSITION|CADENCE|PRESCRIPTION):)",
        "\n", text, flags=re.IGNORECASE,
    )
    details = []
    seen_labels = set()
    for match in _DESCRIPTION_SECTION.finditer(text):
        label = match.group("label").upper()
        if label == "FUELING PLAN":
            label = "FUEL"
        if label in seen_labels:
            continue
        value = _clean_description_detail(match.group("body"))
        if not value or (label == "AUDIBLE" and len(value) < 12):
            continue
        seen_labels.add(label)
        display_label = "How to ride it" if label == "HOW TO RIDE IT" else label.title()
        details.append(f"{display_label}: {value}")
    if details:
        return "\n".join(details)
    if (len(text.strip()) <= MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS
            and not re.search(
                r"(?im)^\s*(?:WARM-UP|MAIN SET|COOL-DOWN|PRESCRIPTION):",
                text,
            )):
        return text.strip()
    return "Follow the structure. Hold the written effort. No bonus rounds."


def _concise_race_description(text: str) -> str:
    carbs = re.search(r"Carbs/hour:\s*(\d+)\s*g", text, re.IGNORECASE)
    start = re.search(r"Start fueling at\s*([^,\n]+)", text, re.IGNORECASE)
    first = re.search(r"First third:.*?\(RPE\s*([\d-]+)\)", text, re.IGNORECASE)
    middle = re.search(r"Middle third:.*?RPE\s*([\d-]+)", text, re.IGNORECASE)
    lines = []
    if first:
        lines.append(f"Start controlled at RPE {first.group(1)}.")
    if middle:
        lines.append(f"Settle at RPE {middle.group(1)}.")
    if carbs:
        fuel = f"Fuel {carbs.group(1)} g/hr"
        if start:
            fuel += f" from {start.group(1).strip()}"
        lines.append(fuel + ".")
    lines.extend([
        "Climb at an effort you can repeat all day.",
        "Smooth beats fast. Heroics remain optional and generally unhelpful.",
    ])
    return " ".join(lines)


def _visible_workout_description(value: Any, *, structured: bool) -> str:
    """Project concise athlete copy while leaving executable structure alone."""
    text = str(value or "").replace("\r\n", "\n")
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        fuel = _FUEL_TAG.fullmatch(line)
        if fuel:
            lines.extend(["FUEL:", fuel.group(2).strip()])
            continue
        if _ATHLETE_WEEK_BOILERPLATE.fullmatch(line):
            continue
        if _PHASE_BOILERPLATE.fullmatch(line):
            continue
        if re.fullmatch(r"GO GET IT(?:,\s*[^!]+)?!", line, re.IGNORECASE):
            continue
        if re.match(r"^Level\s+\d+:\s*", line, re.IGNORECASE):
            continue
        lines.append(raw.strip())
    text = "\n".join(lines)
    if structured:
        text = _DROP_DESCRIPTION_SECTION.sub("", text)
        text = _concise_structured_description(text)
    elif re.search(r"(?im)^\s*RACE DAY:", text):
        text = _concise_race_description(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS:
        clipped = text[:MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS + 1]
        boundary = max(clipped.rfind(". "), clipped.rfind("\n"))
        if boundary >= MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS // 2:
            clipped = clipped[:boundary + 1]
        else:
            clipped = clipped[:MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS].rstrip()
        text = clipped.strip()
    if _VISIBLE_INTERNAL_TAG.search(text):
        raise ApplyContractError("athlete-facing workout description contains internal tag")
    return text


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def bind_operation_provenance(
    contract: Mapping[str, Any], *, contract_digest: str, model_seal: str,
) -> OperationProvenance:
    """Bind a loaded contract to digest/seal values from immutable storage."""
    if not isinstance(contract_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", contract_digest
    ):
        raise ApplyContractError("loaded apply contract digest is invalid")
    if not isinstance(model_seal, str) or not re.fullmatch(
        r"[0-9a-f]{64}", model_seal
    ):
        raise ApplyContractError("loaded apply contract model seal is invalid")
    contract_bytes = canonical_json(contract)
    actual_digest = hashlib.sha256(contract_bytes).hexdigest()
    if actual_digest != contract_digest:
        raise ApplyContractError("loaded apply contract digest mismatch")
    if contract.get("model_seal") != model_seal:
        raise ApplyContractError("loaded apply contract model seal mismatch")
    return OperationProvenance(
        contract_bytes=contract_bytes,
        contract_digest=contract_digest,
        model_seal=model_seal,
    )


PAYLOAD_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "workout_upsert": {
        "type": "object", "additionalProperties": False,
        "required": ["date", "title", "description", "tp_workout_type",
                     "total_seconds", "tss_planned", "structure"],
        "properties": {
            "date": {"type": ["string", "null"]}, "title": {"type": "string"},
            "description": {"type": ["string", "null"]},
            "tp_workout_type": {"type": "integer",
                                "enum": sorted(SUPPORTED_TP_WORKOUT_TYPES)},
            "total_seconds": {"type": "integer", "minimum": 0},
            "tss_planned": {"type": ["number", "null"]},
            "structure": {"type": ["object", "null"]},
        },
    },
    "calendar_note_upsert": {
        "type": "object", "additionalProperties": False,
        "required": ["date", "title", "body"],
        "properties": {"date": {"type": ["string", "null"]},
                       "title": {"type": "string"}, "body": {"type": "string"}},
    },
    "attachment_upsert": {
        "type": "object", "additionalProperties": False,
        "required": ["parent_logical_id", "filename", "sha256", "bytes_ref"],
        "properties": {"parent_logical_id": {"type": "string"},
                       "filename": {"type": "string"}, "sha256": {"type": "string"},
                       "bytes_ref": {"type": "string"}},
    },
    "mental_task_upsert": {
        "type": "object", "additionalProperties": False,
        "required": ["date", "title", "body"],
        "properties": {"date": {"type": ["string", "null"]},
                       "title": {"type": "string"}, "body": {"type": "string"}},
    },
    ENTITLEMENT_KIND: {
        "type": "object", "additionalProperties": False,
        "required": ["product_id"], "properties": {"product_id": {"type": "string"}},
    },
    "threshold_update": {
        "type": "object", "additionalProperties": False,
        "required": ["metric", "after_value", "unit"],
        "properties": {"metric": {"type": "string"},
                       "after_value": {"type": ["number", "integer", "string"]},
                       "unit": {"type": "string"}},
    },
    "zone_update": {
        "type": "object", "additionalProperties": False,
        "required": ["zone_set", "after_table"],
        "properties": {"zone_set": {"type": "string"},
                       "after_table": {"type": ["array", "object"]}},
    },
}

# Desired payloads stay strict. A correction revision may still need an exact
# before-image for a malformed legacy object so it can update it by remote ID
# and restore that image if the controlled attempt rolls back.
PRIOR_PAYLOAD_SCHEMAS = dict(PAYLOAD_SCHEMAS)
PRIOR_PAYLOAD_SCHEMAS["workout_upsert"] = {
    **PAYLOAD_SCHEMAS["workout_upsert"],
    "properties": {
        **PAYLOAD_SCHEMAS["workout_upsert"]["properties"],
        "tp_workout_type": {
            "type": "integer", "enum": sorted(LEGACY_PRIOR_TP_WORKOUT_TYPES),
        },
    },
}


def _operation_branch(kind: str, disposition: str) -> Dict[str, Any]:
    dated = kind in DATED_KINDS
    singleton = kind in SINGLETON_KINDS
    payload_required = disposition in {"create", "update"}
    digest_required = disposition in {"create", "update", "keep"}
    prior_required = dated and disposition in {"update", "delete"}
    before_required = singleton and disposition == "update"
    strategy = (
        "delete_by_remote_id" if dated and disposition == "create" else
        "restore_prior_payload" if dated and disposition == "update" else
        "recreate_from_prior_payload" if dated and disposition == "delete" else
        "restore_before_image" if singleton and disposition == "update" else "none"
    )
    if dated:
        predecessor_schema = ({"$ref": "#/$defs/dated_predecessor"}
                              if disposition in {"update", "keep", "delete"}
                              else {"type": "null"})
        marker_schema = {"type": "string"}
    elif singleton:
        predecessor_schema = {"oneOf": [{"type": "null"},
                                          {"$ref": "#/$defs/positional_predecessor"}]}
        marker_schema = {"type": "null"}
    else:
        predecessor_schema = {"oneOf": [{"type": "null"},
                                          {"$ref": "#/$defs/positional_predecessor"}]}
        marker_schema = {"type": "null"}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["op_id", "logical_id", "kind", "disposition", "payload",
                     "expected_digest", "prior_payload", "before_image",
                     "remote_marker", "predecessor", "rollback"],
        "properties": {
            "op_id": {"type": "string", "minLength": 1},
            "logical_id": {"type": "string", "minLength": 1},
            "kind": {"const": kind}, "disposition": {"const": disposition},
            "payload": PAYLOAD_SCHEMAS[kind] if payload_required else {"type": "null"},
            "expected_digest": ({"type": "string", "pattern": "^[0-9a-f]{64}$"}
                                if digest_required else {"type": "null"}),
            "prior_payload": (PRIOR_PAYLOAD_SCHEMAS[kind]
                              if prior_required else {"type": "null"}),
            "before_image": ({"type": "object"} if before_required else {"type": "null"}),
            "remote_marker": marker_schema, "predecessor": predecessor_schema,
            "rollback": {"type": "object", "additionalProperties": False,
                         "required": ["strategy"],
                         "properties": {"strategy": {"const": strategy}}},
        },
    }


def contract_schema() -> Dict[str, Any]:
    branches = []
    for kind in sorted(DATED_KINDS):
        for disposition in ("create", "update", "keep", "delete"):
            branches.append(_operation_branch(kind, disposition))
    for kind in sorted(SINGLETON_KINDS):
        for disposition in ("update", "keep"):
            branches.append(_operation_branch(kind, disposition))
    for disposition in ("create", "keep"):
        branches.append(_operation_branch(ENTITLEMENT_KIND, disposition))
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://gravelgod.com/schemas/apply_contract-v1.json",
        "title": "Gravel God apply_contract/v1", "type": "object",
        "additionalProperties": False,
        "required": ["contract_version", "order_id", "tp_athlete_id",
                     "generation_revision", "model_seal", "operations", "compat"],
        "properties": {
            "contract_version": {"const": CONTRACT_VERSION},
            "order_id": {"type": "string", "minLength": 1},
            "tp_athlete_id": {"type": "string", "minLength": 1},
            "generation_revision": {"type": "integer", "minimum": 1},
            "model_seal": {"type": "string"},
            "operations": {"type": "array", "items": {"oneOf": branches}},
            "compat": {"type": "object", "additionalProperties": False,
                       "required": ["min_reader"],
                       "properties": {"min_reader": {"const": CONTRACT_VERSION}}},
        },
        "$defs": {
            "dated_predecessor": {"type": "object", "additionalProperties": False,
                "required": ["op_id", "remote_id"], "properties": {
                    "op_id": {"type": "string", "minLength": 1},
                    "remote_id": {"type": "string", "minLength": 1}}},
            "positional_predecessor": {"type": "object", "additionalProperties": False,
                "required": ["op_id", "remote_id"], "properties": {
                    "op_id": {"type": "string", "minLength": 1},
                    "remote_id": {"type": "null"}}},
        },
    }


def schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "apply_contract_v1.schema.json"


def assert_checked_schema_current() -> None:
    checked = json.loads(schema_path().read_text(encoding="utf-8"))
    if checked != contract_schema():
        raise ApplyContractError("checked apply-contract schema is not generated definition")


def _schema_validate(contract: Dict[str, Any]) -> None:
    assert_checked_schema_current()
    errors = sorted(Draft202012Validator(contract_schema()).iter_errors(contract),
                    key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "contract"
        raise ApplyContractError(f"schema validation failed at {location}: {error.message}")


def _validate_workout_payload(
    payload: Mapping[str, Any], context: str, *, allow_legacy: bool = False,
) -> None:
    """Reject payloads that are schema-shaped but not publishable workouts."""
    type_id = payload.get("tp_workout_type")
    seconds = payload.get("total_seconds")
    tss = payload.get("tss_planned")
    structure = payload.get("structure")
    allowed = (LEGACY_PRIOR_TP_WORKOUT_TYPES
               if allow_legacy else SUPPORTED_TP_WORKOUT_TYPES)
    if type_id not in allowed:
        raise ApplyContractError(f"{context} has unsupported tp_workout_type")
    if not allow_legacy:
        description = str(payload.get("description") or "")
        if _VISIBLE_INTERNAL_TAG.search(description):
            raise ApplyContractError(
                f"{context} athlete-facing description contains internal tag")
        if structure is not None:
            if len(description) > MAX_VISIBLE_WORKOUT_DESCRIPTION_CHARS:
                raise ApplyContractError(
                    f"{context} athlete-facing description exceeds max length")
            if (_ATHLETE_WEEK_BOILERPLATE.search(description)
                    or _PHASE_BOILERPLATE.search(description)
                    or re.search(r"(?m)^\s*PURPOSE:\s*$", description)):
                raise ApplyContractError(
                    f"{context} athlete-facing description contains boilerplate")
    if type_id == 100:
        if (not isinstance(seconds, int) or isinstance(seconds, bool)
                or seconds < 0):
            raise ApplyContractError(
                f"{context} legacy workout has invalid duration")
        return
    if type_id == 7:
        if seconds != 0 or tss is not None or structure is not None:
            raise ApplyContractError(f"{context} day-off payload is inconsistent")
        return
    if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds <= 0:
        raise ApplyContractError(
            f"{context} substantive workout requires positive duration")
    if type_id == 2 and structure is None and tss is None:
        raise ApplyContractError(
            f"{context} bike/race workout lacks both structure and planned TSS")
    if structure is not None:
        blocks = structure.get("structure")
        if not isinstance(blocks, list) or not blocks:
            raise ApplyContractError(
                f"{context} workout structure must contain blocks")


def _logical_id(order_id: str, kind: str, logical_key: str) -> str:
    return f"{order_id}:{kind}:{logical_key}"


def _desired_resources(
    ir: Dict[str, Any], order_id: str, athlete_dir: Optional[Path],
    singleton_desires: Mapping[str, Dict[str, Any]],
    *, delivery_platform: Optional[str] = None,
    protected_resources: Optional[Mapping[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    desired: Dict[str, Dict[str, Any]] = {}
    per_date: Dict[str, int] = defaultdict(int)
    workout_by_date: Dict[str, tuple[str, str]] = {}
    for week in ir.get("weeks", []):
        for session in week.get("sessions", []):
            date = str(session.get("date") or "undated")
            per_date[date] += 1
            key = f"{date}#{per_date[date]}"
            logical_id = _logical_id(order_id, "workout_upsert", key)
            workout_by_date.setdefault(date, (key, logical_id))
            desired[logical_id] = {"kind": "workout_upsert", "logical_key": key,
                "date": session.get("date"), "payload": {
                    "date": session.get("date"), "title": str(session.get("title") or "Untitled session"),
                    "description": _visible_workout_description(
                        session.get("description"),
                        structured=session.get("structure") is not None),
                    "tp_workout_type": session.get("workout_type_value_id"),
                    # Day-off cards must never carry residual duration/TSS
                    # from a rest ZWO (a 1-minute 1-TSS Day Off shipped on a
                    # graded delivery).
                    "total_seconds": (0 if str(session.get("tp_kind") or "") == "day_off"
                                      else int(session.get("duration_s") or 0)),
                    "tss_planned": (None if str(session.get("tp_kind") or "") == "day_off"
                                    else session.get("tss_planned")),
                    "structure": (None if str(session.get("tp_kind") or "") == "day_off"
                                  else session.get("structure")),
                }}

    # AE-9.3/AE-9.4 (2026-08-24 TP review, round-2 addendum): mirror the
    # workout loop's per_date collision handling above -- the fixed
    # self-review and comment-protocol notes are deliberately dated onto a
    # date another note already claims (self-review shares a short week's
    # last day with its own midweek note; the Day-1 protocol note always
    # shares its date with that week's Monday note). Without a sequence
    # number, same-date notes would collide on `note_id` and silently
    # overwrite each other in `desired` -- exactly the collision
    # fulfillment_manifest.py's matching fix guards against.
    note_per_date: Dict[str, int] = defaultdict(int)
    for note in render_coached_weekly_notes(ir):
        date = str(note["date"])
        note_per_date[date] += 1
        sequence = note_per_date[date]
        note_key = f"weekly-briefing-{date}" if sequence == 1 else f"weekly-briefing-{date}-{sequence}"
        note_id = _logical_id(order_id, "calendar_note_upsert", note_key)
        desired[note_id] = {
            "kind": "calendar_note_upsert",
            "logical_key": note_key,
            "date": date,
            "payload": {
                "date": date,
                "title": str(note["title"]),
                "body": str(note["body"]),
            },
        }

    for logical_id, raw in (protected_resources or {}).items():
        resource = dict(raw)
        kind = str(resource.get("kind") or "")
        if kind not in {"workout_upsert", "calendar_note_upsert"}:
            raise ApplyContractError("protected resource has unsupported kind")
        prefix = f"{order_id}:{kind}:"
        if not str(logical_id).startswith(prefix):
            raise ApplyContractError("protected resource identity mismatch")
        if logical_id in desired:
            raise ApplyContractError("protected resource collides with plan output")
        logical_key = str(logical_id)[len(prefix):]
        desired[str(logical_id)] = {
            "kind": kind,
            "logical_key": logical_key,
            "date": (resource.get("payload") or {}).get("date"),
            "payload": dict(resource.get("payload") or {}),
        }

    trainingpeaks_only = str(delivery_platform or "").lower() == "trainingpeaks"

    for index, note in ([] if trainingpeaks_only else
                        enumerate(ir.get("notes") or [], 1)):
        if note.get("kind") not in {"mental_training", "mental_task"}:
            continue
        date = note.get("date")
        slug = str(note.get("id") or f"mental-task-{index}")
        logical_id = _logical_id(order_id, "mental_task_upsert", slug)
        desired[logical_id] = {"kind": "mental_task_upsert", "logical_key": slug,
            "date": date, "payload": {"date": date,
                "title": str(note.get("title") or slug.replace("_", " ").title()),
                "body": str(note.get("body") or note.get("text") or "")}}

    attachments = ([] if trainingpeaks_only else
                   list(ir.get("attachments") or []))
    if not attachments and not trainingpeaks_only:
        guide_name = ("training_guide.pdf" if athlete_dir and
                      (athlete_dir / "training_guide.pdf").is_file()
                      else "training_guide.html")
        attachments = [{"id": "guide", "kind": "guide", "path": guide_name}]
    for index, attachment in enumerate(attachments, 1):
        raw_path = str(attachment.get("path") or "training_guide.html")
        filename = Path(raw_path).name
        default_parent = next(
            iter(workout_by_date.values()),
            ("undated#1", _logical_id(order_id, "workout_upsert", "undated#1")),
        )
        parent_logical_key = str(
            attachment.get("parent_logical_key") or default_parent[0])
        parent_logical_id = str(
            attachment.get("parent_logical_id") or default_parent[1])
        if parent_logical_id != _logical_id(
                order_id, "workout_upsert", parent_logical_key):
            raise ApplyContractError("attachment parent logical key/id disagree")
        logical_key = f"{parent_logical_key}:{filename}"
        logical_id = _logical_id(order_id, "attachment_upsert", logical_key)
        file_path = athlete_dir / raw_path if athlete_dir else None
        file_bytes = file_path.read_bytes() if file_path and file_path.is_file() else b""
        desired[logical_id] = {"kind": "attachment_upsert", "logical_key": logical_key,
            "date": None, "payload": {"parent_logical_id": parent_logical_id, "filename": filename,
                "sha256": hashlib.sha256(file_bytes).hexdigest(), "bytes_ref": raw_path}}

    entitlements = ([] if trainingpeaks_only else
                    list(ir.get("entitlements") or []))
    if not entitlements and not trainingpeaks_only:
        race = ir.get("race_snapshot") or {}
        entitlements = [{"product_id": str(race.get("name") or "course") + ":" + str(race.get("date") or "undated")}]
    for entitlement in entitlements:
        product_id = str(entitlement.get("product_id") or entitlement.get("external_id")
                         or entitlement.get("race") or "course")
        logical_id = _logical_id(order_id, ENTITLEMENT_KIND, product_id)
        desired[logical_id] = {"kind": ENTITLEMENT_KIND, "logical_key": product_id,
                               "date": None, "payload": {"product_id": product_id}}

    for singleton_name, spec in singleton_desires.items():
        kind = str(spec.get("kind") or "")
        if kind not in SINGLETON_KINDS:
            raise ApplyContractError("singleton desire has invalid kind")
        logical_id = _logical_id(order_id, kind, singleton_name)
        desired[logical_id] = {"kind": kind, "logical_key": singleton_name,
                               "date": None, "payload": dict(spec["payload"])}
    return desired


def _predecessor(record: Dict[str, Any], dated: bool) -> Dict[str, Any]:
    remote_id = record.get("remote_id")
    if dated and not str(remote_id or "").strip():
        raise ApplyContractError("dated inventory predecessor requires remote_id")
    return {"op_id": str(record.get("last_op_id") or ""),
            "remote_id": str(remote_id) if dated else None}


def _validate_null_positional_provenance(
    logical_id: str, record: Dict[str, Any], operation_reader: OperationReader,
    *, current_revision: int, order_id: str, tp_athlete_id: str,
) -> None:
    """Prove a null snapshot descends only from a verified adoption keep."""
    next_op_id = str(record["last_op_id"])
    child_revision = current_revision
    seen_op_ids = set()
    while True:
        if next_op_id in seen_op_ids:
            raise ApplyContractError(
                "null positional snapshot provenance contains a cycle")
        seen_op_ids.add(next_op_id)
        try:
            bound = operation_reader(next_op_id)
        except Exception as exc:
            raise ApplyContractError(
                "could not resolve durable positional predecessor provenance") from exc

        if not isinstance(bound, OperationProvenance):
            raise ApplyContractError(
                "positional predecessor requires contract-bound provenance")
        if (not isinstance(bound.contract_bytes, bytes)
                or not isinstance(bound.contract_digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", bound.contract_digest)
                or hashlib.sha256(bound.contract_bytes).hexdigest()
                != bound.contract_digest):
            raise ApplyContractError(
                "positional predecessor containing contract digest mismatch")
        try:
            containing_contract = json.loads(bound.contract_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApplyContractError(
                "positional predecessor containing contract is invalid") from exc
        if not isinstance(containing_contract, dict):
            raise ApplyContractError(
                "positional predecessor containing contract is invalid")
        try:
            is_canonical = canonical_json(containing_contract) == bound.contract_bytes
        except (TypeError, ValueError) as exc:
            raise ApplyContractError(
                "positional predecessor containing contract is invalid") from exc
        if (not is_canonical
                or not isinstance(bound.model_seal, str)
                or containing_contract.get("model_seal") != bound.model_seal
                or not re.fullmatch(r"[0-9a-f]{64}", bound.model_seal)):
            raise ApplyContractError(
                "positional predecessor containing contract seal mismatch")
        _schema_validate(containing_contract)
        predecessor_revision = containing_contract["generation_revision"]
        if (containing_contract["order_id"] != order_id
                or containing_contract["tp_athlete_id"] != tp_athlete_id):
            raise ApplyContractError(
                "positional predecessor containing contract identity mismatch")
        if (predecessor_revision >= child_revision
                or predecessor_revision > current_revision):
            raise ApplyContractError(
                "positional predecessor revisions are not strictly descending")
        matches = [
            operation for operation in containing_contract["operations"]
            if operation["op_id"] == next_op_id
        ]
        if len(matches) != 1:
            raise ApplyContractError(
                "positional predecessor lookup is not bound to its containing contract")
        provenance = matches[0]
        if provenance["op_id"] != f"{provenance['logical_id']}@r{predecessor_revision}":
            raise ApplyContractError(
                "positional predecessor op_id does not bind logical_id and revision")

        if (provenance.get("logical_id") != logical_id
                or provenance.get("kind") != record["kind"]
                or provenance.get("expected_digest") != record["desired_digest"]):
            raise ApplyContractError(
                "positional predecessor provenance does not match inventory")
        if (provenance.get("disposition") != "keep"
                or provenance.get("payload") is not None):
            raise ApplyContractError(
                "null positional snapshot is legal only for a verified never-written keep")

        predecessor = provenance.get("predecessor")
        if predecessor is None:
            return
        if (not isinstance(predecessor, Mapping)
                or set(predecessor) != {"op_id", "remote_id"}
                or predecessor.get("remote_id") is not None
                or not isinstance(predecessor.get("op_id"), str)
                or not predecessor["op_id"].strip()):
            raise ApplyContractError(
                "null positional snapshot has invalid predecessor provenance")
        next_op_id = predecessor["op_id"]
        child_revision = predecessor_revision


def _validate_inventory(
    inventory: Mapping[str, Dict[str, Any]],
    operation_reader: Optional[OperationReader] = None,
    *, current_revision: int, order_id: str, tp_athlete_id: str,
) -> Dict[str, Dict[str, Any]]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for logical_id, raw in inventory.items():
        if not isinstance(raw, dict) or set(raw) != INVENTORY_FIELDS:
            raise ApplyContractError(
                "effective inventory record must contain exactly the normative five fields")
        record = dict(raw)
        if record.get("kind") not in KINDS:
            raise ApplyContractError("effective inventory kind is invalid")
        remote_id = record.get("remote_id")
        if remote_id is not None and not str(remote_id).strip():
            raise ApplyContractError("effective inventory remote_id is invalid")
        digest = str(record.get("desired_digest") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ApplyContractError("effective inventory digest is invalid")
        snapshot_ref = record.get("payload_snapshot_ref")
        if snapshot_ref is not None and not str(snapshot_ref).strip():
            raise ApplyContractError("effective inventory snapshot reference is invalid")
        if record["kind"] in DATED_KINDS:
            if not str(remote_id or "").strip():
                raise ApplyContractError(
                    "dated effective inventory requires a non-empty remote_id")
            if not str(snapshot_ref or "").strip():
                raise ApplyContractError(
                    "dated effective inventory requires payload_snapshot_ref")
        elif remote_id is not None:
            raise ApplyContractError(
                "positional effective inventory requires a null remote_id")
        if not str(record.get("last_op_id") or "").strip():
            raise ApplyContractError("effective inventory last_op_id is required")
        if snapshot_ref is None and record["kind"] not in DATED_KINDS:
            if operation_reader is None:
                raise ApplyContractError(
                    "null positional snapshot requires durable last-operation provenance")
            _validate_null_positional_provenance(
                str(logical_id), record, operation_reader,
                current_revision=current_revision, order_id=order_id,
                tp_athlete_id=tp_athlete_id)
        normalized[str(logical_id)] = record
    return normalized


def _read_prior_payload(
    record: Dict[str, Any], kind: str, snapshot_reader: Optional[SnapshotReader],
) -> Dict[str, Any]:
    ref = record.get("payload_snapshot_ref")
    if not str(ref or "").strip():
        raise ApplyContractError("dated supersession requires payload_snapshot_ref")
    if snapshot_reader is None:
        raise ApplyContractError("dated supersession requires an explicit snapshot reader")
    try:
        payload = dict(snapshot_reader(str(ref)))
    except Exception as exc:
        raise ApplyContractError("could not resolve immutable payload snapshot") from exc
    errors = list(Draft202012Validator(
        PRIOR_PAYLOAD_SCHEMAS[kind]).iter_errors(payload))
    if errors:
        raise ApplyContractError("payload snapshot does not match its canonical kind schema")
    if digest_payload(payload) != record["desired_digest"]:
        raise ApplyContractError("payload snapshot digest does not match inventory")
    return payload


def _operation(
    order_id: str, revision: int, logical_id: str, resource: Optional[Dict[str, Any]],
    inventory_record: Optional[Dict[str, Any]], inspection: Dict[str, Any],
    snapshot_reader: Optional[SnapshotReader],
) -> Dict[str, Any]:
    kind = (resource or inventory_record or {}).get("kind")
    if kind not in KINDS:
        raise ApplyContractError(f"unknown inventory kind for {logical_id}")
    dated, singleton = kind in DATED_KINDS, kind in SINGLETON_KINDS
    payload = resource.get("payload") if resource else None
    desired_digest = digest_payload(payload) if payload is not None else None
    predecessor = _predecessor(inventory_record, dated) if inventory_record else None
    before_image = None
    prior_payload = None

    if resource is None:
        if dated:
            disposition = "delete"
            prior_payload = _read_prior_payload(
                inventory_record, kind, snapshot_reader)
        else:
            # Positional resources cannot be deleted by this contract.  A no-
            # longer-desired singleton remains unchanged; an entitlement is
            # irreversible-by-us and remains a verified keep/coach cleanup.
            disposition = "keep"
            desired_digest = inventory_record.get("desired_digest")
            if not str(desired_digest or ""):
                raise ApplyContractError("positional keep requires inventory digest")
    elif singleton:
        current = (inspection.get("singletons") or {}).get(resource["logical_key"])
        if inventory_record and inventory_record.get("desired_digest") == desired_digest:
            disposition = "keep"
        elif not inventory_record and isinstance(current, dict) and digest_payload(current) == desired_digest:
            disposition = "keep"
            desired_digest = digest_payload(current)
        else:
            disposition = "update"
            if not isinstance(current, dict):
                raise ApplyContractError("singleton update requires inspection before_image")
            before_image = current
    elif kind == ENTITLEMENT_KIND:
        present = resource["logical_key"] in set(inspection.get("entitlements") or [])
        if inventory_record or present:
            disposition = "keep"
            desired_digest = (inventory_record or {}).get("desired_digest") or digest_payload(payload)
        else:
            disposition = "create"
    elif inventory_record is None:
        disposition = "create"
    elif inventory_record.get("desired_digest") == desired_digest:
        disposition = "keep"
        desired_digest = inventory_record["desired_digest"]
    else:
        disposition = "update"
        prior_payload = _read_prior_payload(
            inventory_record, kind, snapshot_reader)

    if disposition in {"keep", "delete"}:
        payload = None
    strategy = (
        "delete_by_remote_id" if dated and disposition == "create" else
        "restore_prior_payload" if dated and disposition == "update" else
        "recreate_from_prior_payload" if dated and disposition == "delete" else
        "restore_before_image" if singleton and disposition == "update" else "none"
    )
    remote_marker = logical_id if kind in MARKER_KINDS else None
    return {
        "op_id": f"{logical_id}@r{revision}", "logical_id": logical_id,
        "kind": kind, "disposition": disposition, "payload": payload,
        "expected_digest": desired_digest if disposition != "delete" else None,
        "prior_payload": prior_payload, "before_image": before_image,
        "remote_marker": remote_marker, "predecessor": predecessor,
        "rollback": {"strategy": strategy},
    }


def _sort_key(operation: Dict[str, Any]) -> tuple:
    kind, disposition = operation["kind"], operation["disposition"]
    if kind in SINGLETON_KINDS:
        return (0, "", 0, operation["logical_id"])
    payload = operation.get("payload") or operation.get("prior_payload") or {}
    date = str(payload.get("date") or "9999-99-99")
    kind_rank = {"workout_upsert": 0, "calendar_note_upsert": 1,
                 "mental_task_upsert": 2, "attachment_upsert": 3}.get(kind, 4)
    if kind in DATED_KINDS and disposition in {"delete", "update"}:
        return (1, date, kind_rank, operation["logical_id"])
    if kind == ENTITLEMENT_KIND:
        return (4, date, kind_rank, operation["logical_id"])
    return (2, date, kind_rank, operation["logical_id"])


def validate_contract(
    contract: Dict[str, Any], *,
    effective_remote_inventory: Optional[Mapping[str, Dict[str, Any]]] = None,
    last_operation_reader: Optional[OperationReader] = None,
) -> Dict[str, Any]:
    """Schema and semantic validation; safe to call on any loaded contract."""
    _schema_validate(contract)
    operations = contract["operations"]
    logical_ids = [op["logical_id"] for op in operations]
    if len(logical_ids) != len(set(logical_ids)):
        raise ApplyContractError("duplicate logical_id")
    revision = contract["generation_revision"]
    inventory_supplied = effective_remote_inventory is not None
    inventory = _validate_inventory(
        effective_remote_inventory or {}, last_operation_reader,
        current_revision=revision, order_id=contract["order_id"],
        tp_athlete_id=contract["tp_athlete_id"])
    known_identities = set(logical_ids) | set(inventory)
    for op in operations:
        prefix = f"{contract['order_id']}:{op['kind']}:"
        if not op["logical_id"].startswith(prefix):
            raise ApplyContractError("logical_id does not match order and kind")
        logical_key = op["logical_id"][len(prefix):]
        expected_logical = _logical_id(contract["order_id"], op["kind"], logical_key)
        if op["logical_id"] != expected_logical:
            raise ApplyContractError("logical_id does not match order and kind")
        dated_key = r"(?:\d{4}-\d{2}-\d{2}|undated)#(?:[1-9]\d*)"
        slug = r"[A-Za-z0-9][A-Za-z0-9._-]*"
        valid_key = (
            bool(re.fullmatch(dated_key, logical_key))
            if op["kind"] == "workout_upsert" else
            bool(re.fullmatch(slug, logical_key))
            if op["kind"] in {"calendar_note_upsert", "mental_task_upsert",
                              "threshold_update", "zone_update"} else
            bool(re.fullmatch(dated_key + r":[^/:]+", logical_key))
            if op["kind"] == "attachment_upsert" else
            bool(logical_key.strip())
        )
        if not valid_key:
            raise ApplyContractError(f"invalid logical key grammar for {op['kind']}")
        if op["kind"] == "attachment_upsert":
            parent_key, key_filename = logical_key.rsplit(":", 1)
            expected_parent_id = _logical_id(
                contract["order_id"], "workout_upsert", parent_key)
            for payload_name in ("payload", "prior_payload"):
                attachment_payload = op.get(payload_name)
                if attachment_payload is None:
                    continue
                if attachment_payload.get("filename") != key_filename:
                    raise ApplyContractError(
                        f"attachment {payload_name} filename does not match logical key")
                if attachment_payload.get("parent_logical_id") != expected_parent_id:
                    raise ApplyContractError(
                        f"attachment {payload_name} parent does not match logical key")
            if expected_parent_id not in known_identities:
                raise ApplyContractError(
                    "attachment parent workout identity does not exist")
        if op["op_id"] != f"{op['logical_id']}@r{revision}":
            raise ApplyContractError("op_id does not bind logical_id and revision")
        if op["remote_marker"] is not None and op["logical_id"] not in op["remote_marker"]:
            raise ApplyContractError("remote marker does not embed logical_id")
        if op["kind"] == "workout_upsert":
            for payload_name in ("payload", "prior_payload"):
                workout_payload = op.get(payload_name)
                if workout_payload is not None:
                    _validate_workout_payload(
                        workout_payload, f"{op['op_id']} {payload_name}",
                        allow_legacy=payload_name == "prior_payload")
        if op["payload"] is not None and op["expected_digest"] != digest_payload(op["payload"]):
            raise ApplyContractError("expected_digest does not match payload")
        if inventory_supplied:
            record = inventory.get(op["logical_id"])
            if bool(record) != bool(op["predecessor"]):
                raise ApplyContractError("predecessor presence does not match inventory")
            if record and op["predecessor"] != _predecessor(record, op["kind"] in DATED_KINDS):
                raise ApplyContractError("predecessor does not match inventory")
            if (record and op["kind"] == "attachment_upsert"
                    and op.get("prior_payload") is not None
                    and digest_payload(op["prior_payload"]) != record["desired_digest"]):
                raise ApplyContractError(
                    "attachment prior_payload digest does not match predecessor snapshot")
    if inventory_supplied and set(inventory) - set(logical_ids):
        raise ApplyContractError("contract omits effective inventory dispositions")
    if operations != sorted(operations, key=_sort_key):
        raise ApplyContractError("operations violate normative execution order")
    return contract


def model_seal_sources(
    canonical_model: Dict[str, Any], review_items: Iterable[Dict[str, Any]],
    guide_sources: Dict[str, Any], operations: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    return {"canonical_model": canonical_model, "review_items": list(review_items),
            "guide_sources": guide_sources,
            "operation_payloads": [{"logical_id": op["logical_id"], "kind": op["kind"],
                                    "disposition": op["disposition"], "payload": op["payload"]}
                                   for op in operations]}


def compute_model_seal(
    canonical_model: Dict[str, Any], review_items: Iterable[Dict[str, Any]],
    guide_sources: Dict[str, Any], operations: Iterable[Dict[str, Any]],
) -> str:
    return digest_payload(model_seal_sources(canonical_model, review_items, guide_sources, operations))


def guide_source_digests(athlete_dir: Path | str) -> Dict[str, str]:
    """Stable source inventory used by guide rendering and S2's model seal."""
    root = Path(athlete_dir)
    result = {}
    for name in ("profile.yaml", "methodology.yaml", "fueling.yaml", "plan_dates.yaml"):
        path = root / name
        if path.is_file():
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def build_contract(
    ir: Dict[str, Any], *, order_id: str, tp_athlete_id: str,
    generation_revision: int, canonical_model: Dict[str, Any],
    review_items: Iterable[Dict[str, Any]], guide_sources: Dict[str, Any],
    athlete_dir: Path | str | None = None,
    effective_remote_inventory: Optional[Mapping[str, Dict[str, Any]]] = None,
    inspection: Optional[Dict[str, Any]] = None,
    singleton_desires: Optional[Mapping[str, Dict[str, Any]]] = None,
    payload_snapshot_reader: Optional[SnapshotReader] = None,
    last_operation_reader: Optional[OperationReader] = None,
    delivery_platform: Optional[str] = None,
    protected_resources: Optional[Mapping[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    revision = int(generation_revision)
    inventory = _validate_inventory(
        effective_remote_inventory or {}, last_operation_reader,
        current_revision=revision, order_id=str(order_id),
        tp_athlete_id=str(tp_athlete_id))
    inspection = dict(inspection or {})
    protection = canonical_model.get("calendar_protection") or {}
    if protection.get("requested"):
        evidence = protection.get("inventory_evidence") or {}
        surfaces = evidence.get("read_surfaces") or []
        counts = evidence.get("counts") or {}
        if (effective_remote_inventory is None or protected_resources is None
                or evidence.get("contract_version")
                != "trainingpeaks_calendar_inventory_evidence/v1"
                or evidence.get("complete") is not True
                or not re.fullmatch(
                    r"[0-9a-f]{64}",
                    str(evidence.get("provider_inventory_sha256") or ""))
                or set(surfaces) != {"workouts", "notes", "events"}
                or not all(
                    isinstance(counts.get(name), int)
                    and not isinstance(counts.get(name), bool)
                    and counts.get(name) >= 0
                    for name in surfaces)
                or counts.get("workouts", 0) + counts.get("notes", 0)
                != len(effective_remote_inventory)):
            raise ApplyContractError(
                "calendar protection requires complete current inventory evidence")
    desired = _desired_resources(
        ir, str(order_id), Path(athlete_dir) if athlete_dir else None,
        singleton_desires or {},
        delivery_platform=delivery_platform,
        protected_resources=protected_resources,
    )
    operations = [
        _operation(str(order_id), revision, logical_id,
                   desired.get(logical_id), inventory.get(logical_id), inspection,
                   payload_snapshot_reader)
        for logical_id in sorted(set(desired) | set(inventory))
    ]
    operations.sort(key=_sort_key)
    if (protection.get("requested") and protected_resources
            and not any(operation.get("disposition") == "keep"
                        for operation in operations)):
        raise ApplyContractError(
            "calendar protection requires at least one explicit keep operation")
    if protection.get("requested") and any(
            operation.get("disposition") == "delete" for operation in operations):
        raise ApplyContractError(
            "calendar protection forbids delete operations")
    seal = compute_model_seal(canonical_model, review_items, guide_sources, operations)
    contract = {"contract_version": CONTRACT_VERSION, "order_id": str(order_id),
                "tp_athlete_id": str(tp_athlete_id),
                "generation_revision": revision, "model_seal": seal,
                "operations": operations, "compat": {"min_reader": CONTRACT_VERSION}}
    return validate_contract(
        contract, effective_remote_inventory=inventory,
        last_operation_reader=last_operation_reader)


def emit_contract(path: Path | str, contract: Dict[str, Any], *,
                  effective_remote_inventory: Optional[Mapping[str, Dict[str, Any]]] = None,
                  last_operation_reader: Optional[OperationReader] = None) -> None:
    """Validate every emitted contract, then atomically persist it."""
    validate_contract(
        contract, effective_remote_inventory=effective_remote_inventory,
        last_operation_reader=last_operation_reader)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(contract, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
