#!/usr/bin/env python3
"""Phase 1-disabled TrainingPeaks browser-apply tooling.

The status/gate and historical receipt-validation helpers remain for the
Phase 4/5 worker migration, but Phase 1 cannot emit an executable browser job
or a driver runbook. Coaches apply manually in TrainingPeaks and record APPLIED
through the authenticated fulfillment transition with evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # network features degrade; local-only flows still work
    requests = None  # type: ignore[assignment]

MANIFEST_FILENAME = "tp_manifest.json"
EXPECTED_KINDS = ("bike", "strength", "day_off", "race")
AUTOMATED_APPLY_DISABLED_MESSAGE = (
    "AUTOMATED TRAININGPEAKS APPLY IS DISABLED FOR PHASE 1. "
    "Automated apply returns in Phase 4/5 via the worker. Until then, the coach "
    "must apply manually in the TrainingPeaks UI and record APPLIED through the "
    "authenticated fulfillment transition with evidence."
)


class ApplyOrderError(ValueError):
    """A malformed package/manifest/receipt or an invalid operator request."""


class ApprovalGateError(ApplyOrderError):
    """The APPROVED preflight failed. ``main()`` maps this to exit code 3."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApplyOrderError(message)


# ---------------------------------------------------------------------------
# Package / manifest loading + validation
# ---------------------------------------------------------------------------

def resolve_package_dir(package_path: Path, extract_root: Optional[Path] = None) -> Path:
    """Return a directory containing ``tp_manifest.json``, unzipping if needed."""
    package_path = Path(package_path)
    require(package_path.exists(), f"package not found: {package_path}")
    if package_path.is_dir():
        return package_path
    require(zipfile.is_zipfile(package_path), f"package is neither a directory nor a zip: {package_path}")
    dest = Path(extract_root) if extract_root else Path(tempfile.mkdtemp(prefix="tp_apply_pkg_"))
    with zipfile.ZipFile(package_path) as zf:
        zf.extractall(dest)
    return dest


def default_output_dir(package_path: Path) -> Path:
    package_path = Path(package_path)
    return package_path if package_path.is_dir() else package_path.parent


def load_manifest(package_dir: Path) -> Dict[str, Any]:
    manifest_path = find_manifest_path(package_dir)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApplyOrderError(f"{manifest_path}: invalid JSON ({exc})") from exc
    validate_manifest(manifest)
    return manifest


def find_manifest_path(package_dir: Path) -> Path:
    """Locate the exact manifest bytes that must match the server seal."""
    manifest_path = package_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        candidates = sorted(package_dir.rglob(MANIFEST_FILENAME))
        require(bool(candidates), f"{MANIFEST_FILENAME} not found under {package_dir}")
        manifest_path = candidates[0]
    return manifest_path


def validate_manifest(manifest: Dict[str, Any]) -> None:
    """Validate ``tp_manifest.json`` schema + expected counts.

    Raises ``ApplyOrderError`` on the first problem found. Schema mirrors
    ``athletes/scripts/plan_ir.py:project_tp_manifest`` — this function never
    re-derives plan facts, only checks the projection is internally
    consistent (architecture rule #1: tp_manifest is a projection of PlanIR).
    """
    require(isinstance(manifest, dict), "manifest must be a JSON object")
    for key in ("version", "plan_title", "expected", "sessions"):
        require(key in manifest, f"manifest missing required key: {key!r}")
    require(isinstance(manifest["plan_title"], str) and manifest["plan_title"].strip(),
            "manifest.plan_title must be a non-empty string")

    expected = manifest["expected"]
    require(isinstance(expected, dict), "manifest.expected must be an object")
    for key in (*EXPECTED_KINDS, "total"):
        require(key in expected, f"manifest.expected missing key: {key!r}")
        require(isinstance(expected[key], int) and expected[key] >= 0,
                f"manifest.expected.{key} must be a non-negative int")
    require(expected["total"] == sum(expected[k] for k in EXPECTED_KINDS),
            "manifest.expected.total does not equal the sum of its kind counts")

    sessions = manifest["sessions"]
    require(isinstance(sessions, list) and bool(sessions), "manifest.sessions must be a non-empty list")

    tallied = {kind: 0 for kind in EXPECTED_KINDS}
    for index, session in enumerate(sessions):
        require(isinstance(session, dict), f"manifest.sessions[{index}] must be an object")
        for key in ("date", "title", "tp_kind", "order_on_day"):
            require(key in session, f"manifest.sessions[{index}] missing key: {key!r}")
        kind = session["tp_kind"]
        require(kind in EXPECTED_KINDS,
                f"manifest.sessions[{index}].tp_kind is not one of {EXPECTED_KINDS}: {kind!r}")
        tallied[kind] += 1
        if kind == "strength":
            require(bool(session.get("strength_template")),
                    f"manifest.sessions[{index}] is strength but has no strength_template")
            require(session.get("workout_type_value_id") != 2,
                    f"manifest.sessions[{index}] is strength but carries a bike workoutTypeValueId (2)")

    require(len(sessions) == expected["total"],
            f"manifest carries {len(sessions)} sessions but expected.total is {expected['total']}")
    for kind in EXPECTED_KINDS:
        require(tallied[kind] == expected[kind],
                f"manifest session tally for {kind!r} ({tallied[kind]}) "
                f"does not match expected.{kind} ({expected[kind]})")


# ---------------------------------------------------------------------------
# Railway fulfillment-status gate
# ---------------------------------------------------------------------------

def fetch_fulfillment_status(server: str, token: str, order_id: str, *, timeout: float = 15.0) -> Dict[str, Any]:
    require(requests is not None, "the 'requests' package is required for --server checks")
    url = server.rstrip("/") + f"/api/fulfillment/{order_id}/status"
    response = requests.get(url, headers={"X-Cron-Secret": token}, timeout=timeout)
    if response.status_code == 401:
        raise ApplyOrderError(f"unauthorized against {server} — check --auth env var / CRON_SECRET")
    if response.status_code == 404:
        raise ApplyOrderError(f"no fulfillment state found for order {order_id!r} on {server}")
    response.raise_for_status()
    return response.json()


def post_applied_transition(server: str, token: str, order_id: str, coach: str,
                             evidence: Dict[str, Any], *, timeout: float = 15.0) -> Dict[str, Any]:
    require(requests is not None, "the 'requests' package is required for --server transitions")
    url = server.rstrip("/") + f"/api/fulfillment/{order_id}/transition"
    payload = {"to": "APPLIED", "coach": coach, "platform": "trainingpeaks",
               "evidence": json.dumps(evidence, sort_keys=True)}
    response = requests.post(url, headers={"X-Cron-Secret": token}, json=payload, timeout=timeout)
    if response.status_code == 401:
        raise ApplyOrderError(f"unauthorized against {server} — check --auth env var / CRON_SECRET")
    if response.status_code == 409:
        detail = response.json().get("error", response.text) if response.content else response.text
        raise ApplyOrderError(f"transition refused: {detail}")
    response.raise_for_status()
    return response.json()


def check_approval_gate(
    *, server: Optional[str], token: Optional[str], order_id: str,
    athlete_id: str, generation_revision: int, model_seal: str,
    manifest_sha256: str,
) -> Dict[str, Any]:
    """Validate the retained live binding contract for the future worker."""
    if not server:
        raise ApprovalGateError(
            "no --server given — the legacy local bypass is disabled; use the "
            "order-scoped gated path"
        )
    require(bool(token),
            "--auth env var must resolve to a non-empty token when --server is given")
    status = fetch_fulfillment_status(server, token, order_id)
    approval = status.get("approval") or {}
    failures = []
    if status.get("legacy"):
        failures.append("order is a legacy quarantine")
    if status.get("delivery_platform") != "trainingpeaks":
        failures.append("delivery_platform is not trainingpeaks")
    if status.get("status") != "APPROVED":
        failures.append(f"status is {status.get('status')!r}, not APPROVED")
    if not status.get("seal_verified") or not status.get("release_authorized"):
        failures.append("server did not verify release authority")
    if status.get("order_id") != order_id:
        failures.append("order_id mismatch")
    if status.get("athlete_id") != athlete_id:
        failures.append("athlete_id mismatch")
    if status.get("generation_revision") != generation_revision:
        failures.append("generation_revision mismatch")
    if status.get("model_seal") != model_seal:
        failures.append("model_seal mismatch")
    if approval.get("model_seal") != model_seal:
        failures.append("approval is not bound to model_seal")
    if approval.get("release_manifest_digest") != status.get("release_manifest_digest"):
        failures.append("approval is not bound to release manifest")
    if status.get("tp_manifest_sha256") != manifest_sha256:
        failures.append("tp_manifest bytes do not match the sealed order artifact")
    if not status.get("apply_gate_url") or not status.get("apply_gate_token"):
        failures.append("server did not issue a short-lived live apply gate")
    if failures:
        raise ApprovalGateError(
            f"refusing to apply order {order_id}: " + "; ".join(failures)
        )
    return status


# ---------------------------------------------------------------------------
# apply_job.json emission (hard-disabled for Phase 1)
# ---------------------------------------------------------------------------

def build_apply_job(manifest: Dict[str, Any], *, athlete_tp_id: str, target_date: Optional[str],
                     start_type: int, binding: Dict[str, Any], strength_module: Any = None,
                     uuid_factory: Any = None) -> Dict[str, Any]:
    """Refuse every executable browser-job construction path in Phase 1."""
    raise ApprovalGateError(AUTOMATED_APPLY_DISABLED_MESSAGE)


# ---------------------------------------------------------------------------
# Receipt validation (--receipt mode)
# ---------------------------------------------------------------------------

def _combined_expected(expected: Dict[str, Any]) -> Dict[str, Any]:
    """TP's ranged readback cannot distinguish a race-tagged bike workout from
    an ordinary one (both share ``workoutTypeValueId`` 2) — a real platform
    constraint, not a shortcut. Verification folds bike+race into one count;
    strength (9) and day_off (7) stay distinguishable by type id."""
    return {
        "bike_and_race": expected.get("bike", 0) + expected.get("race", 0),
        "strength": expected.get("strength", 0),
        "day_off": expected.get("day_off", 0),
        "total": expected.get("total", 0),
    }


def validate_receipt(receipt: Dict[str, Any], manifest: Dict[str, Any], *, apply_enabled: bool) -> List[str]:
    """Validate a completed ``window.__APPLY_RECEIPT__`` against manifest
    expected counts. Returns a list of problems; empty means acceptance-clean."""
    if not isinstance(receipt, dict):
        return ["receipt must be a JSON object"]

    problems: List[str] = []
    if not receipt.get("finishedAt"):
        problems.append("receipt.finishedAt is not set — run did not reach a terminal state")
    failures = receipt.get("failures")
    if failures:
        problems.append(f"receipt reports {len(failures)} failure(s): {failures[:3]!r}")
    if not receipt.get("planId"):
        problems.append("receipt.planId is missing")
    if not receipt.get("planPersonId"):
        problems.append("receipt.planPersonId is missing")

    expected = _combined_expected(manifest["expected"])
    verified = receipt.get("verified")
    if not isinstance(verified, dict):
        problems.append("receipt.verified is missing or not an object")
    else:
        for kind in expected:
            if verified.get(kind) != expected.get(kind):
                problems.append(
                    f"receipt.verified.{kind} ({verified.get(kind)!r}) != "
                    f"manifest expected.{kind} ({expected.get(kind)!r})"
                )

    if apply_enabled:
        applied = receipt.get("applied")
        if not isinstance(applied, dict) or applied.get("status") != "ok":
            problems.append("receipt.applied.status is not 'ok' but job.apply.enabled was true")
        athlete_verified = receipt.get("athleteVerified")
        if not isinstance(athlete_verified, dict):
            problems.append("receipt.athleteVerified is missing but job.apply.enabled was true")
        else:
            for kind in expected:
                if athlete_verified.get(kind) != expected.get(kind):
                    problems.append(
                        f"receipt.athleteVerified.{kind} ({athlete_verified.get(kind)!r}) != "
                        f"manifest expected.{kind} ({expected.get(kind)!r})"
                    )
    return problems


def print_registry_commands(*, plan_title: str, plan_id: Optional[int], status: str = "applied") -> None:
    """Print (never run) the cross-repo registry commands. The registry lives
    in ``gravel-god-training-plans``, a different repo — this CLI must not
    write there. Signature matches that repo's ``register`` subcommand
    (gravel-god-training-plans#3): the title is a POSITIONAL arg and the kind
    is derived from it (``[CUSTOM]`` → custom) — there is no ``--kind`` flag.
    """
    plan_id_arg = str(plan_id) if plan_id is not None else "<planId>"
    print("\nCross-repo registry (run from the gravel-god-training-plans checkout, NOT here):")
    print(f"  python3 tools/plan_registry.py register {shlex.quote(plan_title)} "
          f"--plan-id {plan_id_arg} --status {status}")
    print("  python3 tools/plan_registry.py check")


# ---------------------------------------------------------------------------
# Operator runbook (hard-disabled for Phase 1)
# ---------------------------------------------------------------------------

def print_runbook(job_path: Path, receipt_path: Path, driver_path: Path) -> None:
    raise ApprovalGateError(AUTOMATED_APPLY_DISABLED_MESSAGE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_job_mode(args: argparse.Namespace, manifest: Dict[str, Any], token: Optional[str]) -> int:
    raise ApprovalGateError(AUTOMATED_APPLY_DISABLED_MESSAGE)


def _run_receipt_mode(args: argparse.Namespace, manifest: Dict[str, Any], token: Optional[str]) -> int:
    check_approval_gate(
        server=args.server, token=token, order_id=args.order_id,
        athlete_id=args.athlete_id,
        generation_revision=args.generation_revision,
        model_seal=args.model_seal,
        manifest_sha256=args.manifest_sha256,
    )
    receipt_path = Path(args.receipt)
    require(receipt_path.exists(), f"receipt not found: {receipt_path}")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApplyOrderError(f"{receipt_path}: invalid JSON ({exc})") from exc

    apply_enabled = bool(args.target_date)
    job_path = args.out or (default_output_dir(args.package) / "apply_job.json")
    if job_path.exists():
        try:
            apply_enabled = bool(json.loads(job_path.read_text(encoding="utf-8"))
                                  .get("apply", {}).get("enabled"))
        except (OSError, json.JSONDecodeError):
            pass

    problems = validate_receipt(receipt, manifest, apply_enabled=apply_enabled)
    if problems:
        print("receipt FAILED validation:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"receipt OK — plan {receipt.get('planId')} / planPerson {receipt.get('planPersonId')} "
          f"verified against manifest expected counts {manifest['expected']}")

    if args.server:
        require(bool(token), "--auth env var must resolve to a non-empty token when --server is given")
        evidence = {
            "planId": receipt.get("planId"),
            "planPersonId": receipt.get("planPersonId"),
            "verified": receipt.get("verified"),
            "applied": receipt.get("applied"),
            "athleteVerified": receipt.get("athleteVerified"),
            "finishedAt": receipt.get("finishedAt"),
        }
        result = post_applied_transition(args.server, token, args.order_id, args.coach, evidence)
        print(f"POSTed APPLIED transition: {result}")

    print_registry_commands(plan_title=manifest["plan_title"], plan_id=receipt.get("planId"))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("athlete_id", help="pipeline athlete id (e.g. example_athlete)")
    parser.add_argument("--order-id", required=True,
                        help="immutable order id whose sealed revision is being applied")
    parser.add_argument("--generation-revision", required=True, type=int,
                        help="sealed generation revision approved by the coach")
    parser.add_argument("--model-seal", required=True,
                        help="model seal shown by the authoritative order state")
    parser.add_argument("--package", required=True, type=Path,
                        help="path to the full delivery package (zip or extracted dir) "
                             "containing tp_manifest.json")
    parser.add_argument("--server", default=None,
                        help="Railway webhook base URL, e.g. https://gravelgod-webhook.up.railway.app")
    parser.add_argument("--auth", default="CRON_SECRET",
                        help="env var name holding the X-Cron-Secret token (default: CRON_SECRET)")
    parser.add_argument("--athlete-tp-id", default=None,
                        help="retained for future worker migration; browser job emission is disabled")
    parser.add_argument("--target-date", default=None,
                        help="retained for future worker migration; browser apply is disabled")
    parser.add_argument("--start-type", type=int, choices=(1, 3), default=1,
                        help="1=start-on (default), 3=end-on")
    parser.add_argument("--out", type=Path, default=None,
                        help="historical receipt companion path; no job is emitted in Phase 1")
    parser.add_argument("--receipt", type=Path, default=None,
                        help="validate a historical completed receipt; creates no browser work")
    parser.add_argument("--coach", default=os.environ.get("USER", "coach"),
                        help="coach name recorded on the APPLIED transition (receipt mode + --server only)")
    args = parser.parse_args(argv)

    try:
        package_dir = resolve_package_dir(args.package)
        manifest = load_manifest(package_dir)
        manifest_path = find_manifest_path(package_dir)
        args.manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        token = os.environ.get(args.auth, "") if args.server else None

        if args.receipt:
            return _run_receipt_mode(args, manifest, token)
        return _run_job_mode(args, manifest, token)
    except ApprovalGateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except (ApplyOrderError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
