#!/usr/bin/env python3
"""Materialize the reviewed Earned Selection E1 registries.

The specification intentionally carries the initial immutable ID map, the
600-row purpose assignment, and the quality-gate registry as normative data.
This maintainer command extracts those reviewed bytes/rows without asking a
second hand-authored copy to drift.  Runtime code consumes only the committed
files under ``athletes/config``; it never reads the specification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "SPEC_EARNED_SELECTION.md"
CONFIG = ROOT / "athletes" / "config"


def _section(text: str, start: str, end: str | None) -> str:
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0] if end else body


def _fence(section: str, language: str) -> str:
    match = re.search(rf"```{language}\n(.*?)\n```", section, re.S)
    if not match:
        raise RuntimeError(f"missing {language} block")
    return match.group(1) + "\n"


def _purpose_registry(text: str) -> dict:
    section = _section(
        text,
        "### A5.3 Explicit 600-row assignment",
        "## Appendix 6",
    )
    row_pattern = re.compile(
        r"^\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| `([^`]+)` "
        r"\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \|$",
        re.M,
    )
    rows = []
    for match in row_pattern.finditer(section):
        row_id, purpose_class, subtype, rule, assessment, long_ride, status = match.groups()
        rows.append({
            "row_id": row_id,
            "purpose": {
                "class": purpose_class,
                "subtype": subtype,
                "assignment_status": status,
                "main_set_rule": rule,
            },
            "is_assessment": assessment == "true",
            "long_ride_registered": long_ride == "true",
        })
    if len(rows) != 600 or len({row["row_id"] for row in rows}) != 600:
        raise RuntimeError(f"expected 600 unique purpose rows, got {len(rows)}")
    return {
        "schema_version": "purpose_registry/v1",
        "registry_version": "purpose_registry/v1",
        "owner_id": "matti-gravel-god",
        "assignment_status": "hypothesis",
        "rows": rows,
    }


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    id_section = _section(text, "## Appendix 4", "## Appendix 5")
    id_bytes = _fence(id_section, "json")
    parsed_ids = json.loads(id_bytes)
    if parsed_ids.get("schema_version") != "archetype_ids/v1":
        raise RuntimeError("unexpected archetype ID schema")
    (CONFIG / "archetype_ids.json").write_text(id_bytes, encoding="utf-8")

    _write_yaml(CONFIG / "purpose_registry.yaml", _purpose_registry(text))

    gate_section = _section(text, "## Appendix 6", "## Appendix 7")
    gate_bytes = _fence(gate_section, "yaml")
    gates = yaml.safe_load(gate_bytes)
    if gates.get("schema_version") != "quality_gates/v1":
        raise RuntimeError("unexpected quality gate schema")
    (CONFIG / "quality_gates.yaml").write_text(gate_bytes, encoding="utf-8")

    # These appendices are table-defined rather than fenced payloads. Keep one
    # named materializer responsible for deterministic bytes and reject a
    # missing/wrong semantic registry instead of inventing policy from code.
    managed = {
        "rule_registry.yaml": "rule_registry/v1",
        "non_native_producers.yaml": "non_native_producers/v1",
        "phase_purpose_registry.yaml": "phase_purpose_registry/v1",
    }
    for name, version in managed.items():
        path = CONFIG / name
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise RuntimeError(f"{name} is unavailable or malformed") from exc
        if not isinstance(value, dict) or value.get("schema_version") != version:
            raise RuntimeError(f"{name} has the wrong schema version")
        _write_yaml(path, value)
    _write_yaml(CONFIG / "earned_selection_rollout.yaml", {
        "mode": "A", "rollout_phase": "E1",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
