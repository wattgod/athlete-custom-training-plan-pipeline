"""Closed ``workout_quality_report/v1`` builder for E1 Mode A."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml

from earned_selection import (
    CONFIG_DIR, VERSION_VECTOR, canonical_digest, canonical_json,
    evaluate_purpose_gate, score_design_dose,
)
from earned_selection_rules import execute_rules


REPORT_VERSION = "workout_quality_report/v1"


class WorkoutQualityReportError(ValueError):
    pass


def _count_verdicts(records: list[Mapping[str, Any]]) -> Dict[str, Any]:
    observed = Counter(record["observed_verdict"] for record in records)
    effective = Counter(record["effective_verdict"] for record in records)
    return {
        "total": len(records),
        "observed": {key: observed.get(key, 0) for key in
                     ("PASS", "FAIL", "NOT_APPLICABLE", "UNAVAILABLE")},
        "effective": {key: effective.get(key, 0) for key in
                      ("PASS", "FAIL", "NOT_ENFORCED", "NOT_APPLICABLE", "UNAVAILABLE")},
    }


def _aggregate(gates: list[Mapping[str, Any]]) -> str:
    if any(gate["effective_verdict"] == "FAIL" for gate in gates):
        return "FAIL"
    if any(gate["effective_verdict"] == "UNAVAILABLE"
           or gate["observed_verdict"] == "UNAVAILABLE" for gate in gates):
        return "UNAVAILABLE"
    if any(gate["observed_verdict"] == "FAIL"
           and gate["effective_verdict"] == "NOT_ENFORCED" for gate in gates):
        return "PASS_WITH_OBSERVED_FAIL"
    if gates and all(gate["observed_verdict"] == "NOT_APPLICABLE" for gate in gates):
        return "NOT_APPLICABLE"
    return "PASS"


def _finding(identifier: str, revision: int, code: str, severity: str,
             subject_ids: list[str], metric: Mapping[str, Any], message: str,
             *, source: str = "workout_quality_report") -> Dict[str, Any]:
    return {
        "schema_version": "quality_finding/v1", "id": identifier,
        "generation_revision": revision, "source": source, "code": code,
        "severity": severity, "subject": {"kind": "session", "ids": subject_ids},
        "metric": copy.deepcopy(metric),
        "basis": "workout_quality_report/v1 observed Mode A result",
        "sensitivity": "internal", "message": message,
        "version_vector": copy.deepcopy(VERSION_VECTOR),
    }


def evaluate_pre_guide(candidate: Mapping[str, Any],
                       manifest: Mapping[str, Any]) -> Dict[str, Any]:
    """Run every D1-only check before canonical/guide projection."""
    revision = candidate["generation_revision"]
    from earned_selection import validate_manifest_pin
    validate_manifest_pin(candidate["manifest_pin"], manifest)
    manifest_rows = {row["row_id"]: row for row in manifest["rows"]}
    sessions = []
    findings: list[Dict[str, Any]] = []
    manifest_records, final_records = [], []
    for session in candidate["sessions"]:
        archetype = session.get("archetype")
        manifest_row = manifest_rows.get((archetype or {}).get("manifest_row_id"))
        if manifest_row:
            manifest_gate = {
                "row_id": manifest_row["row_id"],
                "row_digest": canonical_digest(manifest_row),
                "observed_verdict": manifest_row["observed_verdict"],
                "effective_verdict": manifest_row["effective_verdict"],
            }
        else:
            manifest_gate = {"row_id": None, "row_digest": None,
                             "observed_verdict": "NOT_APPLICABLE",
                             "effective_verdict": "NOT_APPLICABLE"}
        manifest_records.append(manifest_gate)
        purpose = session.get("purpose")
        dose = score_design_dose(
            session.get("segments") or [],
            main_set_segment_ids=(purpose or {}).get("main_set_segment_ids", []),
        )
        if session.get("sport") == "cycling" and purpose:
            final_gates = evaluate_purpose_gate(
                archetype_id=(archetype or {}).get("archetype_id"), purpose=purpose,
                is_assessment=session["is_assessment"], dose=dose,
                final_session=True,
            )
        else:
            final_gates = []
        final_records.extend(final_gates)
        aggregate = _aggregate([manifest_gate] + final_gates)
        finding_ids = []
        if aggregate == "PASS_WITH_OBSERVED_FAIL":
            identifier = f"QUALITY_DOSE_{session['id']}"
            finding_ids.append(identifier)
            findings.append(_finding(
                identifier, revision, "WORKOUT_DOSE_MISMATCH", "critical",
                [session["id"]], {"aggregate_verdict": aggregate, "dose": dose},
                "Observed hypothesis gate failure; not enforced in E1."))
        if manifest_row and manifest_row["observed_verdict"] in {"FAIL", "UNAVAILABLE"}:
            identifier = f"QUALITY_LIBRARY_{session['id']}"
            finding_ids.append(identifier)
            findings.append(_finding(
                identifier, revision, "LIBRARY_UNCERTIFIED", "critical",
                [session["id"]], {"row_id": manifest_row["row_id"],
                                  "observed_verdict": manifest_row["observed_verdict"]},
                "Selected native row has an observed E1 certification finding."))
        sessions.append({
            "session_id": session["id"], "week": session["week"],
            "date": session["date"], "daily_ordinal": session["daily_ordinal"],
            "sport": session["sport"], "origin": session["origin"],
            "is_assessment": session["is_assessment"],
            "long_ride_registered": session["long_ride_registered"],
            "fueling_class": session["fueling_class"],
            "control_metric": session.get("control_metric") or "none",
            "control_basis": session.get("control_basis") or "none",
            "archetype": copy.deepcopy(archetype),
            "series_identity": (session.get("series") or {}).get("series_id"),
            "transformation_parameters": copy.deepcopy(
                session["provenance"]["transformation_parameters"]),
            "source_digests": copy.deepcopy(session["provenance"]["source_digests"]),
            "dose": dose, "manifest_gate": manifest_gate,
            "final_gates": final_gates, "aggregate_verdict": aggregate,
            "quality_finding_ids": sorted(finding_ids),
        })

    plan_series = []
    grouped = defaultdict(list)
    session_by_id = {item["session_id"]: item for item in sessions}
    for session in candidate["sessions"]:
        identity = (session.get("series") or {}).get("series_id")
        if identity and session.get("sport") == "cycling":
            grouped[identity].append(session)
    for identity in sorted(grouped):
        ordered = sorted(grouped[identity], key=lambda item: (
            item["week"], item["date"], item["daily_ordinal"]))
        ids = [item["id"] for item in ordered]
        doses = [session_by_id[item["id"]]["dose"].get("design_tss") for item in ordered]
        if len(doses) < 2:
            result, finding_id = "NOT_APPLICABLE", None
        elif any(value is None for value in doses):
            result, finding_id = "UNAVAILABLE", f"QUALITY_SERIES_{hashlib.sha256(identity.encode()).hexdigest()[:12]}"
        elif any(later < prior for prior, later in zip(doses, doses[1:])):
            result, finding_id = "WARNING", f"QUALITY_SERIES_{hashlib.sha256(identity.encode()).hexdigest()[:12]}"
        else:
            result, finding_id = "PASS", None
        if finding_id:
            findings.append(_finding(
                finding_id, revision, "SERIES_DOSE_REGRESSION" if result == "WARNING"
                else "SERIES_DOSE_UNAVAILABLE", "warning", ids,
                {"design_tss": doses}, "Final sealed series dose observation."))
        plan_series.append({"series_identity": identity, "session_ids": ids,
                            "design_tss": doses, "result": result,
                            "finding_id": finding_id})

    rubric = execute_rules(candidate, stage="PRE_GUIDE", manifest=manifest)
    for row in rubric:
        if row["finding_id"]:
            findings.append(_finding(
                row["finding_id"], revision, row["output_code"],
                row["severity"].lower(), row["subject_ids"], row["metric"],
                row["message"]))
    return {"sessions": sessions, "findings": findings,
            "manifest_records": manifest_records, "final_records": final_records,
            "plan_series": plan_series, "rubric": rubric}


def build_report(candidate: Mapping[str, Any], candidate_sha256: str,
                 manifest: Mapping[str, Any], guide_bytes: bytes, *,
                 pre_guide: Optional[Mapping[str, Any]] = None,
                 post_guide: Optional[list[Mapping[str, Any]]] = None,
                 post_render_results: Optional[list[Mapping[str, Any]]] = None
                 ) -> tuple[Dict[str, Any], list[Dict[str, Any]], list[Dict[str, Any]]]:
    revision = candidate["generation_revision"]
    pre = copy.deepcopy(pre_guide or evaluate_pre_guide(candidate, manifest))
    sessions = pre["sessions"]
    findings = pre["findings"]
    manifest_records = pre["manifest_records"]
    final_records = pre["final_records"]
    plan_series = pre["plan_series"]
    rubric = sorted(pre["rubric"] + copy.deepcopy(post_guide or execute_rules(
        candidate, guide_html=guide_bytes.decode("utf-8"), stage="POST_GUIDE",
        manifest=manifest)), key=lambda row: row["rule_id"])
    if [row["rule_id"] for row in rubric] != [f"R{i:02d}" for i in range(1, 27)]:
        raise WorkoutQualityReportError("pre/post rubric merge is incomplete")
    for row in rubric:
        if row["stage"] == "POST_GUIDE" and row["finding_id"]:
            findings.append(_finding(
                row["finding_id"], revision, row["output_code"],
                row["severity"].lower(), row["subject_ids"], row["metric"],
                row["message"]))
    blockers = [{
        "id": row["output_code"], "source": "earned_selection_rules",
        "severity": row["severity"], "message": row["message"],
        "review_value": {"rule_id": row["rule_id"], "result": row["result"],
                         "subject_ids": row["subject_ids"], "metric": row["metric"]},
        "basis": "Appendix 3 A3.0 production-equivalent verdict",
        "sensitivity": "internal",
    } for row in rubric if row["routed_to_blocking_issues"]]
    guide_sha = hashlib.sha256(guide_bytes).hexdigest()
    guide_sources = {item["path"]: item["sha256"] for item in candidate["guide_inputs"]}
    guide_evidence_sha = canonical_digest({
        "candidate_sha256": candidate_sha256, "guide_sha256": guide_sha,
        "guide_source_digests": guide_sources,
    })
    finding_by_id = {finding["id"]: finding for finding in findings}
    if len(finding_by_id) != len(findings):
        raise WorkoutQualityReportError("duplicate quality finding ID")
    counts = Counter(item["aggregate_verdict"] for item in sessions)
    rubric_counts = Counter(item["result"] for item in rubric)
    rollout = yaml.safe_load((CONFIG_DIR / "earned_selection_rollout.yaml").read_text())
    report = {
        "schema_version": REPORT_VERSION, "generation_revision": revision,
        "generated_at": candidate["generated_at"],
        "rollout_phase": rollout["rollout_phase"],
        "canonical_candidate_sha256": candidate_sha256,
        "guide_evidence_sha256": guide_evidence_sha,
        "version_vector": copy.deepcopy(VERSION_VECTOR),
        "gate_summary": {
            "counts": {"sessions": len(sessions), "pass": counts["PASS"],
                       "fail": counts["FAIL"],
                       "pass_with_observed_fail": counts["PASS_WITH_OBSERVED_FAIL"],
                       "not_applicable": counts["NOT_APPLICABLE"],
                       "unavailable": counts["UNAVAILABLE"]},
            "artifact_counts": {"quality_findings": len(finding_by_id),
                                "rubric_blockers": sum(
                                    row["routed_to_blocking_issues"] for row in rubric)},
            "gate_result_counts": {
                "manifest_gates": _count_verdicts(manifest_records),
                "final_gates": _count_verdicts(final_records),
                "rubric": {"total": 26, "results": {key: rubric_counts[key]
                    for key in ("PASS", "FAIL", "WARNING", "NOT_APPLICABLE", "UNAVAILABLE")}},
            },
            "sessions": sessions, "rubric": rubric, "plan_series": plan_series,
            "post_render_results": copy.deepcopy(post_render_results or []),
        },
        "manifest_pin": copy.deepcopy(candidate["manifest_pin"]),
    }
    validate_report(report, candidate)
    return report, sorted(findings, key=lambda item: item["id"]), blockers


def validate_report(report: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    if report.get("schema_version") != REPORT_VERSION:
        raise WorkoutQualityReportError("unknown report version")
    if report.get("version_vector") != VERSION_VECTOR:
        raise WorkoutQualityReportError("report version vector mismatch")
    if report.get("manifest_pin") != candidate.get("manifest_pin"):
        raise WorkoutQualityReportError("report manifest pin mismatch")
    rollout_path = CONFIG_DIR / "earned_selection_rollout.yaml"
    rollout_digest = hashlib.sha256(rollout_path.read_bytes()).hexdigest()
    if candidate.get("config_digests", {}).get("rollout") != rollout_digest:
        raise WorkoutQualityReportError("candidate rollout digest mismatch")
    rollout = yaml.safe_load(rollout_path.read_text(encoding="utf-8"))
    if report.get("rollout_phase") != rollout.get("rollout_phase"):
        raise WorkoutQualityReportError("report rollout phase is not authoritative")
    sessions = report["gate_summary"]["sessions"]
    if [item["session_id"] for item in sessions] != [item["id"] for item in candidate["sessions"]]:
        raise WorkoutQualityReportError("report/candidate session identity mismatch")
    for frozen, observed in zip(candidate["sessions"], sessions):
        purpose = frozen.get("purpose")
        expected = (evaluate_purpose_gate(
            archetype_id=(frozen.get("archetype") or {}).get("archetype_id"),
            purpose=purpose, is_assessment=frozen["is_assessment"],
            dose=observed["dose"], final_session=True)
            if frozen.get("sport") == "cycling" and purpose else [])
        if [gate["gate_id"] for gate in observed["final_gates"]] != [
                gate["gate_id"] for gate in expected]:
            raise WorkoutQualityReportError("final applicable gate set mismatch")
    counts = report["gate_summary"]["counts"]
    if (counts["sessions"] != len(sessions) or sum(counts[key] for key in
            ("pass", "fail", "pass_with_observed_fail", "not_applicable", "unavailable"))
            != len(sessions)):
        raise WorkoutQualityReportError("report session count equation failed")
    rubric = report["gate_summary"]["rubric"]
    if len(rubric) != 26 or {row["rule_id"] for row in rubric} != {
            f"R{i:02d}" for i in range(1, 27)}:
        raise WorkoutQualityReportError("report rubric is incomplete")
    projection_digest = candidate["legacy_compliance_projection"]["projection_sha256"]
    for row in rubric:
        expected_routing = (row["severity"] == "CRITICAL" and row["result"] == "FAIL"
                            and (row["blocking_since"] == "pre-existing"
                                 or report["rollout_phase"] == "E3"))
        if row["routed_to_blocking_issues"] is not expected_routing:
            raise WorkoutQualityReportError("rubric blocker routing mismatch")
        if row["blocking_since"] == "pre-existing" and row["metric"].get(
                "legacy_compliance_projection_sha256") != projection_digest:
            raise WorkoutQualityReportError("legacy rubric projection digest mismatch")
    gate_counts = report["gate_summary"]["gate_result_counts"]
    for name in ("manifest_gates", "final_gates"):
        collection = gate_counts[name]
        if (sum(collection["observed"].values()) != collection["total"]
                or sum(collection["effective"].values()) != collection["total"]):
            raise WorkoutQualityReportError(f"{name} count equation failed")
    if gate_counts["manifest_gates"]["total"] != len(sessions):
        raise WorkoutQualityReportError("manifest gate count is not one per session")
    if gate_counts["final_gates"]["total"] != sum(
            len(item["final_gates"]) for item in sessions):
        raise WorkoutQualityReportError("final gate count equation failed")
    if sum(gate_counts["rubric"]["results"].values()) != 26:
        raise WorkoutQualityReportError("rubric count equation failed")
    blocker_count = sum(row["routed_to_blocking_issues"] for row in rubric)
    if report["gate_summary"]["artifact_counts"]["rubric_blockers"] != blocker_count:
        raise WorkoutQualityReportError("rubric blocker count equation failed")
    finding_ids = {
        identifier for item in sessions for identifier in item["quality_finding_ids"]
    } | {row["finding_id"] for row in rubric if row["finding_id"]} | {
        row["finding_id"] for row in report["gate_summary"]["plan_series"]
        if row["finding_id"]
    }
    if report["gate_summary"]["artifact_counts"]["quality_findings"] != len(finding_ids):
        raise WorkoutQualityReportError("quality finding count equation failed")


def report_derived_records(report: Mapping[str, Any]) -> list[Dict[str, Any]]:
    digest = canonical_digest(report)
    records = [{
        "id": "QUALITY_GATE_SUMMARY", "field": "gate_summary", "class": "inferred",
        "basis": "workout_quality_report/v1 results computed from frozen final sessions and rule_registry/v1",
        "inputs": {"artifact": "workout_quality_report.json",
                   "artifact_sha256": digest,
                   "canonical_candidate_sha256": report["canonical_candidate_sha256"],
                   "guide_evidence_sha256": report["guide_evidence_sha256"],
                   "version_vector": copy.deepcopy(report["version_vector"]),
                   "session_ids": [item["session_id"] for item in report["gate_summary"]["sessions"]]},
        "sensitivity": "internal", "at": report["generated_at"],
        "revision": report["generation_revision"],
    }, {
        "id": "QUALITY_MANIFEST_PIN", "field": "manifest_pin", "class": "inferred",
        "basis": "revision-local certification_manifest/v1 snapshot selected and digest-verified before scoring",
        "inputs": {"artifact": "certification_manifest.json",
                   "snapshot_path": report["manifest_pin"]["snapshot_path"],
                   "snapshot_digest": report["manifest_pin"]["snapshot_digest"],
                   "manifest_version": report["manifest_pin"]["manifest_version"],
                   "version_vector": copy.deepcopy(report["manifest_pin"]["version_vector"]),
                   "promotion_digests": copy.deepcopy(report["manifest_pin"]["promotion_digests"])},
        "sensitivity": "internal", "at": report["generated_at"],
        "revision": report["generation_revision"],
    }]
    from derived_registry import assert_registry_covers
    assert_registry_covers(
        dict(report), records, artifact="workout_quality_report",
        revision=report["generation_revision"],
    )
    return records


def write_report(path: Path | str, report: Mapping[str, Any]) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")
