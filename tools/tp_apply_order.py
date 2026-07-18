#!/usr/bin/env python3
"""tp_apply_order.py — transactional TrainingPeaks apply orchestrator (D5).

Architecture: this CLI *prepares and validates only*. It never talks to
TrainingPeaks itself — ``tp_apply_driver.js`` executes inside a logged-in TP
browser tab (injected via playwriter by the operator, same runtime model as
``gravel-god-training-plans/tools/tp_load_plan.js``). This CLI:

  1. loads + validates ``tp_manifest.json`` from a package (dir or zip),
  2. gates on the athlete's Railway-authoritative fulfillment status
     (refuses to build a job unless APPROVED, or the operator explicitly
     opts into an unguarded local/dev run),
  3. emits ``apply_job.json`` for the driver to execute, and prints the
     operator runbook, OR
  4. (``--receipt``) validates a completed browser receipt against the
     manifest's expected counts and, with ``--server``, posts the APPLIED
     transition with the receipt as evidence.

See SPEC_tp_native_custom_plans.md, section "CLI (D5)".
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import requests
except ImportError:  # network features degrade; local-only flows still work
    requests = None  # type: ignore[assignment]

# rx_strength_docs.py is built in a parallel workstream (ws-c). Code to its
# documented interface; degrade gracefully if it hasn't landed yet.
try:
    from . import rx_strength_docs  # type: ignore
except ImportError:
    try:
        import rx_strength_docs  # type: ignore
    except ImportError:
        rx_strength_docs = None  # type: ignore[assignment]


MANIFEST_FILENAME = "tp_manifest.json"
EXPECTED_KINDS = ("bike", "strength", "day_off", "race")


class ApplyOrderError(ValueError):
    """A malformed package/manifest/receipt or an invalid operator request."""


class ApprovalGateError(ApplyOrderError):
    """The APPROVED preflight failed. ``main()`` maps this to exit code 3."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApplyOrderError(message)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


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
    manifest_path = package_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        candidates = sorted(package_dir.rglob(MANIFEST_FILENAME))
        require(bool(candidates), f"{MANIFEST_FILENAME} not found under {package_dir}")
        manifest_path = candidates[0]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApplyOrderError(f"{manifest_path}: invalid JSON ({exc})") from exc
    validate_manifest(manifest)
    return manifest


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


def _session_date_range(sessions: List[Dict[str, Any]]) -> Dict[str, str]:
    dates = sorted(s["date"] for s in sessions if s.get("date"))
    require(bool(dates), "manifest has no dated sessions to derive a range from")
    return {"start": dates[0], "end": dates[-1]}


# ---------------------------------------------------------------------------
# Railway fulfillment-status gate
# ---------------------------------------------------------------------------

def fetch_fulfillment_status(server: str, token: str, athlete_id: str, *, timeout: float = 15.0) -> Dict[str, Any]:
    require(requests is not None, "the 'requests' package is required for --server checks")
    url = server.rstrip("/") + f"/api/fulfillment/{athlete_id}/status"
    response = requests.get(url, headers={"X-Cron-Secret": token}, timeout=timeout)
    if response.status_code == 401:
        raise ApplyOrderError(f"unauthorized against {server} — check --auth env var / CRON_SECRET")
    if response.status_code == 404:
        raise ApplyOrderError(f"no fulfillment state found for athlete {athlete_id!r} on {server}")
    response.raise_for_status()
    return response.json()


def post_applied_transition(server: str, token: str, athlete_id: str, coach: str,
                             evidence: Dict[str, Any], *, timeout: float = 15.0) -> Dict[str, Any]:
    require(requests is not None, "the 'requests' package is required for --server transitions")
    url = server.rstrip("/") + f"/api/fulfillment/{athlete_id}/transition"
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


def check_approval_gate(*, server: Optional[str], token: Optional[str], athlete_id: str,
                         skip_approval_check: bool) -> Optional[Dict[str, Any]]:
    """Enforce the APPROVED preflight (spec D5 step 1 + sol r2 F1).

    With ``--server``: fetch the Railway-authoritative status and refuse
    unless it is APPROVED. Without ``--server`` (local/dev mode): refuse
    unless the operator explicitly passes ``--skip-approval-check`` — never a
    silent default. Raises ``ApprovalGateError`` on refusal.
    """
    if server:
        require(bool(token), "--auth env var must resolve to a non-empty token when --server is given")
        status = fetch_fulfillment_status(server, token, athlete_id)
        if status.get("status") != "APPROVED":
            raise ApprovalGateError(
                f"refusing to apply: {athlete_id} fulfillment status is "
                f"{status.get('status')!r}, not APPROVED (server={server}). "
                "Never call local transition() on a downloaded snapshot — this "
                "must be re-checked against Railway once the coach approves."
            )
        return status
    if not skip_approval_check:
        raise ApprovalGateError(
            "no --server given (local/dev mode) — refusing to build an apply job "
            "without verifying APPROVED status. Pass --skip-approval-check to "
            "proceed anyway (loud warning, no gate)."
        )
    print("WARNING: --skip-approval-check set with no --server — proceeding WITHOUT "
          "verifying the athlete's fulfillment status is APPROVED. Local/dev mode only; "
          "never do this against a real customer order.", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# apply_job.json emission
# ---------------------------------------------------------------------------

def _workout_entry(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": session["date"],
        "order_on_day": session.get("order_on_day", 0),
        "title": session.get("display_name") or session["title"],
        "workoutTypeValueId": session.get("workout_type_value_id"),
        "tssPlanned": session.get("tss_planned"),
        "totalTimePlanned": session.get("total_time_planned"),
        "description": session.get("description", ""),
        "structure": session.get("structure"),
        "race": session.get("race"),
    }


def _strength_entry(session: Dict[str, Any], strength_module: Any,
                     uuid_factory: Callable[[], str]) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "date": session["date"],
        "order_on_day": session.get("order_on_day", 0),
        "title": session.get("display_name") or session["title"],
        "template_key": session.get("strength_template"),
    }
    if strength_module is None:
        entry["pending_module"] = True
        entry["doc"] = None
        return entry
    # calendar_id (planPersonId) and doc_id are only known live in-browser
    # (the plan/rx-workout don't exist yet at CLI-build time) — the driver
    # resolves them onto this prebuilt doc immediately before the PUT.
    entry["doc"] = strength_module.build_strength_doc(
        entry["template_key"],
        calendar_id=None,
        prescribed_date=entry["date"],
        doc_id=None,
        uuid_factory=uuid_factory,
    )
    return entry


def build_apply_job(manifest: Dict[str, Any], *, athlete_tp_id: str, target_date: Optional[str],
                     start_type: int, strength_module: Any = None,
                     uuid_factory: Optional[Callable[[], str]] = None) -> Dict[str, Any]:
    """Emit the transactional ``apply_job.json`` payload for the JS driver."""
    require(bool(athlete_tp_id) and str(athlete_tp_id).strip(),
            "athlete_tp_id is required and must be non-empty — never guess an athlete")
    uuid_factory = uuid_factory or (lambda: str(uuid.uuid4()))

    sessions = manifest["sessions"]
    non_strength = [s for s in sessions if s.get("tp_kind") != "strength"]
    strength = [s for s in sessions if s.get("tp_kind") == "strength"]

    custom_exercises: List[Dict[str, Any]] = []
    pending_module = strength_module is None
    if strength_module is not None and hasattr(strength_module, "custom_exercises_needed"):
        custom_exercises = list(strength_module.custom_exercises_needed())

    date_range = _session_date_range(sessions)
    job: Dict[str, Any] = {
        "plan_title": manifest["plan_title"],
        "athlete_tp_id": str(athlete_tp_id),
        "duplicate_guard": {"title": manifest["plan_title"]},
        "workouts": [_workout_entry(s) for s in non_strength],
        "strength": [_strength_entry(s, strength_module, uuid_factory) for s in strength],
        "custom_exercises": custom_exercises,
        "apply": {
            "targetDate": target_date,
            "startType": start_type,
            "enabled": bool(target_date),
        },
        "verify": {
            "expected": manifest["expected"],
            "date_range": date_range,
        },
        "rollback": {
            "snapshot_range": date_range,
        },
    }
    if pending_module:
        job["strength_module_pending"] = True
    return job


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
    write there. Assumes the ``register`` subcommand + custom-key support
    from the spec's "Registry extension" workstream has landed; if it has
    not yet, these commands are the documented target, not a live guarantee.
    """
    plan_id_arg = str(plan_id) if plan_id is not None else "<planId>"
    print("\nCross-repo registry (run from the gravel-god-training-plans checkout, NOT here):")
    print("  python3 tools/plan_registry.py register --kind custom "
          f"--title {shlex.quote(plan_title)} --plan-id {plan_id_arg} --status {status}")
    print("  python3 tools/plan_registry.py check")


# ---------------------------------------------------------------------------
# Operator runbook
# ---------------------------------------------------------------------------

def print_runbook(job_path: Path, receipt_path: Path, driver_path: Path) -> None:
    print("\n" + "=" * 78)
    print("OPERATOR RUNBOOK — apply via a logged-in TrainingPeaks browser tab")
    print("=" * 78)
    print("1. Open app.trainingpeaks.com in the browser tab Claude controls")
    print("   (playwriter), logged in as the coach account.")
    print("2. Inject the driver, then run it against the job payload:")
    print(f"     - load the contents of {driver_path}")
    print(f"     - set window.__APPLY_JOB__ = <contents of {job_path}>")
    print("     - run: await window.applyJob(window.__APPLY_JOB__)")
    print("3. The driver writes live progress to window.__APPLY_RECEIPT__ — poll")
    print("   it (JSON.stringify(window.__APPLY_RECEIPT__)) to watch stage/posted/rxDone.")
    print("4. On a 401 (TP_SESSION_401) or any halt: reload the tab, re-run step 2.")
    print("   The driver resumes from receipt.planId (localStorage backup too).")
    print("5. When receipt.finishedAt is set, save window.__APPLY_RECEIPT__ to a file:")
    print(f"     {receipt_path}")
    print("6. Feed it back to this CLI:")
    print(f"     python3 tools/tp_apply_order.py <athlete-id> --package <package> "
          f"--receipt {receipt_path} [--server <railway-url> --auth CRON_SECRET]")
    print("=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_job_mode(args: argparse.Namespace, manifest: Dict[str, Any], token: Optional[str]) -> int:
    require(bool(args.athlete_tp_id) and str(args.athlete_tp_id).strip(),
            "--athlete-tp-id is required — never guess an athlete")
    check_approval_gate(server=args.server, token=token, athlete_id=args.athlete_id,
                        skip_approval_check=args.skip_approval_check)

    strength_module = rx_strength_docs
    if strength_module is None:
        print("WARNING: tools/rx_strength_docs.py not found — strength jobs will carry "
              "{pending_module: true} instead of prebuilt StructuredStrength docs.",
              file=sys.stderr)

    job = build_apply_job(manifest, athlete_tp_id=args.athlete_tp_id, target_date=args.target_date,
                          start_type=args.start_type, strength_module=strength_module)

    out_dir = default_output_dir(args.package)
    job_path = args.out or (out_dir / "apply_job.json")
    atomic_write_json(job_path, job)
    print(f"wrote {job_path} ({len(job['workouts'])} bike/day_off/race + "
          f"{len(job['strength'])} strength)")

    driver_path = Path(__file__).resolve().parent / "tp_apply_driver.js"
    receipt_path = out_dir / "receipt.json"
    print_runbook(job_path, receipt_path, driver_path)
    return 0


def _run_receipt_mode(args: argparse.Namespace, manifest: Dict[str, Any], token: Optional[str]) -> int:
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
        result = post_applied_transition(args.server, token, args.athlete_id, args.coach, evidence)
        print(f"POSTed APPLIED transition: {result}")

    print_registry_commands(plan_title=manifest["plan_title"], plan_id=receipt.get("planId"))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("athlete_id", help="pipeline athlete id (e.g. example_athlete)")
    parser.add_argument("--package", required=True, type=Path,
                        help="path to the full delivery package (zip or extracted dir) "
                             "containing tp_manifest.json")
    parser.add_argument("--server", default=None,
                        help="Railway webhook base URL, e.g. https://gravelgod-webhook.up.railway.app")
    parser.add_argument("--auth", default="CRON_SECRET",
                        help="env var name holding the X-Cron-Secret token (default: CRON_SECRET)")
    parser.add_argument("--athlete-tp-id", default=None,
                        help="TrainingPeaks numeric athlete id — REQUIRED for job emission, "
                             "never guessed/defaulted")
    parser.add_argument("--skip-approval-check", action="store_true",
                        help="local/dev mode only: bypass the APPROVED gate when --server is not given")
    parser.add_argument("--target-date", default=None,
                        help="apply targetDate YYYY-MM-DD; enables Stage 5 apply-to-athlete in the driver job")
    parser.add_argument("--start-type", type=int, choices=(1, 3), default=1,
                        help="1=start-on (default), 3=end-on")
    parser.add_argument("--out", type=Path, default=None,
                        help="output path for apply_job.json (default: <package-dir>/apply_job.json)")
    parser.add_argument("--receipt", type=Path, default=None,
                        help="validate a completed receipt.json instead of emitting a new job")
    parser.add_argument("--coach", default=os.environ.get("USER", "coach"),
                        help="coach name recorded on the APPLIED transition (receipt mode + --server only)")
    args = parser.parse_args(argv)

    try:
        package_dir = resolve_package_dir(args.package)
        manifest = load_manifest(package_dir)
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
