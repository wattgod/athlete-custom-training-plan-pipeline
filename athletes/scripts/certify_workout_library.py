#!/usr/bin/env python3
"""Render and audit all 600 native archetype rows for E1 Mode A."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

from archetype_identity import load_id_map, validate_live_registry
from archetype_registry import ALL_ARCHETYPES, get_archetype_source
from earned_selection import (
    CONFIG_DIR, ROOT, VERSION_VECTOR, canonical_digest, canonical_json,
    evaluate_purpose_gate, file_digest, purpose_rows, quality_gates,
    score_design_dose, utc_now,
)
from nate_workout_generator import generate_blocks_from_archetype
from zwo_parser import parse_zwo_structure_text


OUTPUT = CONFIG_DIR / "workout_certification.json"
RENDERER_VERSION = "nate_archetype_renderer/v1"


def _canonical_segment(raw: Mapping[str, Any], index: int, total: int) -> Dict[str, Any]:
    kind = str(raw.get("kind") or "")
    if kind == "steady_state":
        target = {"type": "power_pct_ftp", "value": raw.get("power_target")}
        canonical_kind = "steady"
    elif kind in {"warmup", "cooldown", "ramp"}:
        target = {
            "type": "power_pct_ftp", "low": raw.get("power_low"),
            "high": raw.get("power_high"),
        }
        canonical_kind = kind
    elif kind == "intervals":
        target = {
            "type": "power_pct_ftp", "on": raw.get("on_power"),
            "off": raw.get("off_power"),
        }
        canonical_kind = kind
    elif kind == "free_ride":
        target = {"type": "free"}
        canonical_kind = kind
    else:
        raise ValueError(f"unknown rendered segment kind {kind!r}")
    provenance_role = (
        "renderer_warmup" if index == 1 and canonical_kind == "warmup" else
        "renderer_cooldown" if index == total and canonical_kind == "cooldown" else
        "source_body"
    )
    result = {
        "id": f"seg-{index:04d}", "name": str(raw.get("name") or canonical_kind),
        "seconds": int(raw.get("seconds") or 0), "kind": canonical_kind,
        "provenance_role": provenance_role, "target": target,
    }
    for key in ("repeat", "on_seconds", "off_seconds"):
        if raw.get(key) is not None:
            result[key] = int(raw[key])
    return result


def _render(archetype: Mapping[str, Any], level: int) -> tuple[str, list[Dict[str, Any]]]:
    blocks = generate_blocks_from_archetype(dict(archetype), level)
    xml = (
        "<?xml version='1.0' encoding='UTF-8'?>\n<workout_file>\n"
        f"  <name>{archetype['name']} L{level}</name>\n  <workout>\n"
        f"{blocks}\n  </workout>\n</workout_file>"
    )
    parsed = parse_zwo_structure_text(xml, source_name=str(archetype["name"]))
    raw_segments = parsed["segments"]
    segments = [_canonical_segment(item, index, len(raw_segments))
                for index, item in enumerate(raw_segments, 1)]
    return xml, segments


def _q3_gate(gate: Mapping[str, Any], observed: str,
             measurement: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "gate_id": gate["gate_id"], "gate_version": gate["gate_version"],
        "authority_status": gate["status"], "observed_verdict": observed,
        "effective_verdict": (
            "NOT_ENFORCED" if gate["status"] == "hypothesis" else observed),
        "measurement": dict(measurement), "criterion": {
            "operator": gate["operator"], "threshold": gate["threshold"],
            "unit": gate["unit"],
        }, "promotion_digest": None,
    }


def _aggregate(values: Iterable[str], *, effective: bool = False) -> str:
    values = list(values)
    if "FAIL" in values:
        return "FAIL"
    if "UNAVAILABLE" in values:
        return "UNAVAILABLE"
    if effective and "NOT_ENFORCED" in values:
        return "NOT_ENFORCED"
    if values and all(value == "NOT_APPLICABLE" for value in values):
        return "NOT_APPLICABLE"
    return "PASS"


def build_manifest(*, generated_at: str | None = None) -> Dict[str, Any]:
    validate_live_registry(ALL_ARCHETYPES)
    id_map = load_id_map()
    purposes = purpose_rows()
    gates_by_id = {gate["gate_id"]: gate for gate in quality_gates()["gates"]}
    rows: list[Dict[str, Any]] = []
    by_archetype: Dict[str, list[Dict[str, Any]]] = {}
    source_paths: set[Path] = {
        CONFIG_DIR / "archetype_ids.json", CONFIG_DIR / "purpose_registry.yaml",
        CONFIG_DIR / "quality_gates.yaml", CONFIG_DIR / "rule_registry.yaml",
        Path(__file__), Path(__file__).with_name("earned_selection.py"),
        Path(__file__).with_name("nate_workout_generator.py"),
    }
    for category, slots in id_map["categories"].items():
        live_by_name = {entry["name"]: entry for entry in ALL_ARCHETYPES[category]}
        for slot in slots:
            archetype_id = slot["archetype_id"]
            source_info = get_archetype_source(slot["name"]) or {}
            source_path = Path(__file__).with_name(source_info.get("file", "new_archetypes.py"))
            source_paths.add(source_path)
            for level in range(1, 7):
                row_id = f"{archetype_id}@L{level}"
                assignment = copy.deepcopy(purposes[row_id])
                xml, segments = _render(live_by_name[slot["name"]], level)
                rule = assignment["purpose"]["main_set_rule"]
                main_ids = ([segment["id"] for segment in segments
                             if segment["provenance_role"] == "source_body"]
                            if rule in {"SOURCE_BODY", "ASSESSMENT_BODY"} else [])
                purpose = assignment["purpose"] | {"main_set_segment_ids": main_ids}
                dose = score_design_dose(segments, main_set_segment_ids=main_ids)
                purpose_gate = evaluate_purpose_gate(
                    archetype_id=archetype_id, purpose=purpose,
                    is_assessment=assignment["is_assessment"], dose=dose,
                )[0]
                purpose_gate["promotion_digest"] = None
                row = {
                    "row_id": row_id, "archetype_id": archetype_id,
                    "category": category, "name": slot["name"], "level": level,
                    "catalog_status": slot["status"],
                    "replacement_id": slot["replacement_id"], "purpose": purpose,
                    "is_assessment": assignment["is_assessment"],
                    "long_ride_registered": assignment["long_ride_registered"],
                    "source": {
                        "path": f"repo:{source_path.relative_to(ROOT).as_posix()}",
                        "sha256": file_digest(source_path),
                        "renderer_version": RENDERER_VERSION,
                        "rendered_zwo_sha256": hashlib.sha256(xml.encode("utf-8")).hexdigest(),
                    },
                    "dose": dose, "gates": [purpose_gate],
                    "observed_verdict": purpose_gate["observed_verdict"],
                    "effective_verdict": purpose_gate["effective_verdict"],
                }
                rows.append(row)
                by_archetype.setdefault(archetype_id, []).append(row)

    exempt: list[str] = []
    for archetype_id, ladder in by_archetype.items():
        empty = [row["dose"]["status"] == "NOT_APPLICABLE" for row in ladder]
        if all(empty):
            exempt.append(archetype_id)
            tss_observed = density_observed = "NOT_APPLICABLE"
            tss_measurement = density_measurement = {"transitions": []}
        elif any(empty) or any(row["dose"]["status"] != "APPLICABLE" for row in ladder):
            tss_observed = density_observed = "UNAVAILABLE"
            tss_measurement = density_measurement = {"reason": "UNDEFINED_TRANSITION"}
        else:
            tss_deltas, density_deltas = [], []
            for prior, later in zip(ladder, ladder[1:]):
                tss_deltas.append(later["dose"]["design_tss"] - prior["dose"]["design_tss"])
                prior_density = prior["dose"]["design_tss"] / (prior["dose"]["trace_seconds"] / 60)
                later_density = later["dose"]["design_tss"] / (later["dose"]["trace_seconds"] / 60)
                density_deltas.append(later_density - prior_density)
            tss_observed = "PASS" if all(value >= 1.0 for value in tss_deltas) else "FAIL"
            density_observed = "PASS" if all(value >= -0.05 for value in density_deltas) else "FAIL"
            tss_measurement = {"transitions": tss_deltas}
            density_measurement = {"transitions": density_deltas}
        for row in ladder:
            row["gates"].extend([
                _q3_gate(gates_by_id["Q3_MIN_DESIGN_TSS_DELTA"], tss_observed,
                         tss_measurement),
                _q3_gate(gates_by_id["Q3_MIN_DENSITY_DELTA"], density_observed,
                         density_measurement),
            ])
            row["gates"].sort(key=lambda gate: gate["gate_id"])
            row["observed_verdict"] = _aggregate(
                gate["observed_verdict"] for gate in row["gates"])
            row["effective_verdict"] = _aggregate(
                (gate["effective_verdict"] for gate in row["gates"]), effective=True)

    observed_counts = Counter(row["observed_verdict"] for row in rows)
    effective_counts = Counter(row["effective_verdict"] for row in rows)
    return {
        "schema_version": "certification_manifest/v1",
        "generated_at": generated_at or utc_now(),
        "registry_digest": canonical_digest(
            yaml.safe_load((CONFIG_DIR / "purpose_registry.yaml").read_text())),
        "id_map_digest": canonical_digest(id_map),
        "version_vector": copy.deepcopy(VERSION_VECTOR),
        "promotion_artifacts": [],
        "source_digests": [
            {"path": f"repo:{path.relative_to(ROOT).as_posix()}",
             "sha256": file_digest(path)} for path in sorted(source_paths)
            if path.is_file()
        ],
        "rows": rows,
        "summary": {
            "row_count": 600,
            "active_row_count": sum(row["catalog_status"] == "active" for row in rows),
            "retired_row_count": sum(row["catalog_status"] == "retired" for row in rows),
            "observed_counts": dict(sorted(observed_counts.items())),
            "effective_counts": dict(sorted(effective_counts.items())),
            "q3_exempt_archetype_ids": sorted(exempt),
        },
    }


def write_manifest(path: Path = OUTPUT, *, generated_at: str | None = None) -> Dict[str, Any]:
    manifest = build_manifest(generated_at=generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=False, ensure_ascii=False,
                         allow_nan=False) + "\n"
    handle, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as tmp:
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-at")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest = write_manifest(args.output, generated_at=args.generated_at)
    print(f"certified {manifest['summary']['row_count']} rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
