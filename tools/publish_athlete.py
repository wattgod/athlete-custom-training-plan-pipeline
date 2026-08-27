#!/usr/bin/env python3
"""Generalized Phase 5 kernel publisher.

Parameterizes the one-off publish scripts proven 3x against a live
TrainingPeaks calendar (cheesehead-publish/publish_cheesehead.py,
sonja-publish/publish_sonja.py, steve-publish/publish_steve.py -- all under
the coach's private ``TrainingPeaksPublisher`` directory, never in this
repo). Those three scripts were byte-identical except for a handful of
per-order constants (athlete slug, TP athlete id, order id, revision/wave
bookkeeping) and a growing pile of clone-and-sed drift (steve-publish was a
clone of sonja-publish that still said "Sonja" in half its comments). This
tool is the single parameterized replacement -- same bindings, same state
machine, same worker, no fallback.

Stages (each stops on the first failure):
  0. offline: bootstrap-or-load fulfillment state, identity bind, build the
     adoption contract from the baseline inventory, apply the wave-cutoff
     filter, normalize creates (integral-float + internal-space collapse),
     refuse on a baseline row that tuple-matches a desired create but
     differs in content (a CONFLICT, not a silent drop -- see
     _create_matches_baseline) unless --waiver-reason covers it, assert
     EXPECTED_CREATES, record the release's own expected cadence-structure
     count for stage 4 to check, seal the release, APPROVE with
     confirmations (waiving blockers only if --waiver-reason is supplied).
  1. transport: pinned engine commit (read from the plugin's
     compatibility.json ``engine.inspected_commit``) verified against the
     repo's actual HEAD at runtime, refusing on a dirty tree or on drift;
     reviewed Playwriter binary + browser payload digests; plugin
     capability bindings; a fresh Playwriter session; preflight.
  2. barrier: fresh GET-only inventory must equal the inventory the
     adoption contract was built from (READ BARRIER).
  3. execute: the work dir's own tp_phase5_execute_verbose.py (never
     checked into this repo -- it is a private, per-installation verbose
     fork of tools/tp_phase5_execute.py), pinned by sha256 against
     tools/tp_phase5_executor.sha256 (override with --allow-executor-hash
     for a deliberate, reviewed update), run under a one-time,
     10-minute-TTL capability. Its reported ``status`` must be a
     documented success status (EXECUTE_SUCCESS_STATUSES) -- anything
     else is a hard failure even if the process exit code was 0.
  4. readback: after-inventory; every created card (workout AND note)
     present; every protected workout AND note row unchanged; if stage 0
     recorded an expected cadence-structure count, the landed count for
     this release's own creates must equal it exactly, not merely be
     printed (see compute_publication_summary).
  (stage "inventory" is a standalone GET-only read, used to produce the
  next wave's --baseline file without touching fulfillment state.)

Multi-wave publishing = rerun this same command with a bumped --revision,
--wave-cutoff, --expected-creates, and --baseline (the live post-previous-
wave inventory) -- exactly the manual cheesehead r4->r5 / sonja / steve
wave-bump flow.

CLI:
  python3 tools/publish_athlete.py --athlete-dir <dir> --tp-athlete-id <id> \\
      --order-id <id> --work-dir <private dir> \\
      --stage {inventory|offline|barrier|all} \\
      [--revision N] [--wave-cutoff DATE] [--expected-creates N] \\
      [--baseline <file>]

Every artifact this tool writes (release/, records/, capabilities/,
receipts, inventories) lives under --work-dir, which must be a private,
non-git directory (mirrors ``playwriter_session_cwd_must_be_private_non_git``
in the plugin's compatibility.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[1]
PLUGIN = Path(os.environ.get("GG_TP_PLUGIN_DIR") or "/Users/mattirowe/plugins/endure-coaching-ops")
PREFLIGHT = PLUGIN / "skills/trainingpeaks-publisher/scripts/check_playwriter_transport.py"
READ_INVENTORY = PLUGIN / "skills/trainingpeaks-publisher/scripts/read_trainingpeaks_inventory.py"
COMPATIBILITY = PLUGIN / "compatibility.json"

# Transport binary pins. Independent of the engine commit pin (which is read
# from compatibility.json at runtime, see stage_transport) -- these pin the
# out-of-repo Playwriter build and the in-repo browser payload script that
# every proven run so far has used unchanged.
PLAYWRITER = Path(os.environ.get("GG_TP_PLAYWRITER_BIN")
                   or "/Users/mattirowe/Documents/Codex/2026-08-21/build-u/work/playwriter-0.4.0")
EXPECTED_BIN_SHA = "237def9c5e67babccf1bff7991be4b48ef9fdb67e71c8774d6e2a8dd8f43a68e"
EXPECTED_PAYLOAD_SHA = "1299f9ef0cd8cbca4c18a799674635451508ed2a1b9de21c8983113044767808"
# Canonical hash of the proven, per-installation tp_phase5_execute_verbose.py
# fork (never checked into this repo -- see stage_execute). Committing only
# the hash, not the private file, lets --work-dir's copy be pinned without
# leaking the private script.
EXECUTOR_HASH_FILE = REPO / "tools/tp_phase5_executor.sha256"
EXECUTE_SUCCESS_STATUSES = {"applied"}
PROFILE = "stormspandies@gmail.com"
BROWSER_KEY = "install:Chrome:108u6s61090h4e"
VERSION = "0.4.0"
CAPABILITY_AUDIENCE = "gg-trainingpeaks-worker"
CAPABILITY_KID = "phase5-cap-k1"
GRANT_KID = "phase5-grant-k1"
# Wide enough to never clip a real plan's calendar footprint; the read
# window only bounds inventory GETs, never writes. Override with
# --window-start/--window-end for a tighter live read.
DEFAULT_WINDOW = ("2020-01-01", "2035-12-31")

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "webhook"))
sys.path.insert(0, str(REPO / "athletes/scripts"))
from athletes.scripts.apply_contract import validate_contract  # noqa: E402
from delivery.trainingpeaks import phase5_service as _ps  # noqa: E402
from delivery.trainingpeaks.worker_service import CapabilityCodec  # noqa: E402
from fulfillment_state import (  # noqa: E402
    APPROVED, _canonical_model_seal_from_release, finalize_transitional_release,
    load, merge_generation_blockers, transition, write_generation,
)
from d2_identity import record_identity_result  # noqa: E402

RELEASE_ARTIFACT_NAMES = (
    "canonical_training_model.json", "profile.yaml", "methodology.yaml",
    "fueling.yaml", "plan_dates.yaml", "plan_ir.json",
)


class PublishAthleteError(RuntimeError):
    pass


# --------------------------------------------------------------- normalize
def stable(value: Any) -> Any:
    """Collapse integral JSON floats (36.0 -> 36) -- TP echoes integers."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()}
    return value


# TP's athlete-calendar API collapses runs of internal spaces in
# description text ("minutes.  Note" -> "minutes. Note") on write --
# found 2026-08-25 when a library-authored double space landed one byte
# short of its contract and the read barrier correctly refused. Only
# collapse runs NOT at line start so intentional indentation survives.
# (2026-08-25: this normalization now also runs upstream, at generation
# time, in delivery_render.sanitize_athlete_description -- see
# athletes/scripts/delivery_render.py. It stays here too as a belt-and-
# suspenders pass over the sealed payload bytes, exactly like the
# proven scripts, since a payload can carry text this tool didn't
# generate (e.g. hand-edited library copy).)
_SPACE_RUN = re.compile(r"(?<=\S)  +(?=\S)")


def collapse_spaces(value: Any) -> Any:
    if isinstance(value, str):
        return _SPACE_RUN.sub(" ", value)
    if isinstance(value, dict):
        return {k: (collapse_spaces(v) if k in ("description", "title") else v)
                for k, v in value.items()}
    return value


# The athlete-calendar (TP) layer normalizes description text FURTHER than
# the internal-space collapse above -- found 2026-08-25 on a live Juan
# Echeverri apply (TP 1683197): besides collapsing internal double-spaces,
# TP also strips LINE-LEADING whitespace on continuation lines
# ("\n  changes" -> "\nchanges"). 6 of 23 descriptions differed by 2-16
# chars on readback until normalized this way. This is athlete-layer-only:
# the plan LIBRARY layer (plans/v1) does NOT do this (library readback
# stayed byte-exact with indentation) -- never apply
# normalize_athlete_description() to a library comparison, and never fold
# this into delivery_render.py's generation-side sanitizer (indentation
# must survive on the library layer).
_LEADING_LINE_WS = re.compile(r"\n[ \t]+")


def normalize_athlete_description(value: Any) -> str:
    """Normalize a description the same way TP's athlete-calendar layer
    does on write/read, so a desired-vs-landed (or desired-vs-baseline)
    comparison is apples to apples. Apply to BOTH sides of any such
    comparison."""
    text = str(value or "").strip()
    text = _SPACE_RUN.sub(" ", text)
    text = _LEADING_LINE_WS.sub("\n", text)
    return text


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(stable(value), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_executor_sha256() -> str:
    if not EXECUTOR_HASH_FILE.is_file():
        raise PublishAthleteError(f"missing canonical executor hash file: {EXECUTOR_HASH_FILE}")
    value = EXECUTOR_HASH_FILE.read_text().strip()
    if not value:
        raise PublishAthleteError(f"{EXECUTOR_HASH_FILE} is empty")
    return value


def resolve_executor_sha(executor: Path, *, allow_executor_hash: Optional[str] = None) -> str:
    """Pin the private, per-installation tp_phase5_execute_verbose.py fork
    (never checked into this repo) to the canonical hash committed at
    tools/tp_phase5_executor.sha256, isolated from stage_execute's
    transport/capability plumbing so it can be unit-tested directly.
    Returns the executor's own sha256 on success; raises PublishAthleteError
    on a mismatch not covered by --allow-executor-hash."""
    executor_sha = file_sha(executor)
    canonical_sha = canonical_executor_sha256()
    allowed = {canonical_sha}
    if allow_executor_hash:
        allowed.add(allow_executor_hash)
    if executor_sha not in allowed:
        raise PublishAthleteError(
            f"{executor} sha256={executor_sha} does not match the canonical, proven "
            f"executor pinned at {EXECUTOR_HASH_FILE} (sha256={canonical_sha}). This "
            "private, per-installation script must be byte-identical to the proven "
            "fork. If this drift is a deliberate, reviewed update, pass "
            "--allow-executor-hash <sha256> to override.")
    return executor_sha


def run(cmd, *, cwd=REPO, env=None, timeout=600) -> str:
    done = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise PublishAthleteError(
            f"{cmd[0]} failed ({done.returncode}): STDERR={done.stderr[-1500:]} STDOUT={done.stdout[-1500:]}")
    return done.stdout


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


# ------------------------------------------------------------- pure logic
def validate_baseline_schema(baseline: dict) -> None:
    """Schema gate on a provider inventory file before it is trusted as an
    adoption-contract baseline. Mirrors what
    tools/tp_build_adoption_contract.py itself enforces (contract_version +
    athlete_id identity, workouts/notes as lists) -- checked here too so a
    malformed or stale baseline fails loudly before any subprocess runs,
    not with a buried traceback from the contract builder."""
    if not isinstance(baseline, dict):
        raise PublishAthleteError("baseline inventory must be a JSON object")
    if baseline.get("contract_version") != "trainingpeaks_provider_inventory/v1":
        raise PublishAthleteError(
            "baseline inventory has the wrong contract_version "
            f"(got {baseline.get('contract_version')!r})")
    if not str(baseline.get("athlete_id") or ""):
        raise PublishAthleteError("baseline inventory is missing athlete_id")
    for key in ("workouts", "notes"):
        if not isinstance(baseline.get(key), list):
            raise PublishAthleteError(f"baseline inventory {key!r} must be a list")
    if "events" in baseline and not isinstance(baseline["events"], list):
        raise PublishAthleteError("baseline inventory 'events' must be a list")


def filter_and_normalize_operations(
    operations: list[dict], *, baseline: dict, wave_cutoff: Optional[str],
    expected_creates: int, waiver_reason: Optional[str] = None,
) -> tuple[list[dict], int, int]:
    """Wave filter + integral-float/space normalization + the
    EXPECTED_CREATES assertion, isolated from the state machine so it can
    be unit-tested with a synthetic operation list.

    - A create whose (kind, date, title) already exists on the baseline
      calendar is only dropped as "already landed" when its CONTENT also
      matches the baseline row (description, post-sanitization bytes; for
      workouts also structure-presence) for every field the baseline row
      actually carries. A tuple match with a content MISMATCH -- e.g. an
      existing blank-body card that would otherwise silently swallow a
      desired full-body card -- is a CONFLICT: refuse (raise) unless
      --waiver-reason explicitly covers it. Never silently drop.
    - Defer (drop) a create beyond --wave-cutoff to a later wave.
    - Normalize every surviving create's payload (stable() +
      collapse_spaces()) and recompute expected_digest over the normalized
      bytes, matching what TP will actually echo back.
    - Assert the exact create count before returning -- refuse to seal on
      any mismatch rather than silently publish a different plan shape.

    Returns (kept_operations, dropped_count, deferred_count).
    """
    existing = {("workout_upsert", str(w["date"])[:10], w["title"]): w
                for w in baseline.get("workouts") or []}
    existing.update({("calendar_note_upsert", str(n["date"])[:10], n["title"]): n
                      for n in baseline.get("notes") or []})
    kept_ops, dropped, deferred = [], 0, 0
    conflicts: list[dict] = []
    for op in operations:
        if op["disposition"] == "create":
            payload = op["payload"]
            op_date = str(payload["date"])[:10]
            key = (op["kind"], op_date, payload["title"])
            baseline_row = existing.get(key)
            if baseline_row is not None:
                if _create_matches_baseline(op, payload, baseline_row):
                    dropped += 1
                else:
                    conflicts.append({
                        "kind": op["kind"], "date": op_date, "title": payload["title"],
                    })
                continue
            if wave_cutoff and op_date > wave_cutoff:
                deferred += 1
                continue
        kept_ops.append(op)

    if conflicts:
        listing = "; ".join(f"{c['kind']}/{c['date']}/{c['title']!r}" for c in conflicts)
        if not waiver_reason:
            raise PublishAthleteError(
                f"CONFLICT: {len(conflicts)} desired create(s) match an existing baseline "
                f"row by (kind, date, title) but differ in content (description or "
                f"structure-presence) -- refusing to silently drop: {listing}. Pass "
                "--waiver-reason to override deliberately.")
        print(f"waived {len(conflicts)} content conflict(s) ({waiver_reason}): {listing}")
        dropped += len(conflicts)

    for op in kept_ops:
        if op["disposition"] == "create" and op.get("payload") is not None:
            op["payload"] = collapse_spaces(op["payload"])
            op["payload"] = stable(op["payload"])
            op["expected_digest"] = digest(op["payload"])
    creates = [o for o in kept_ops if o["disposition"] == "create"]
    if len(creates) != expected_creates:
        raise PublishAthleteError(
            f"expected exactly {expected_creates} missing creates, got {len(creates)} "
            "— refusing to seal")
    return kept_ops, dropped, deferred


def _create_matches_baseline(op: dict, payload: dict, baseline_row: dict) -> bool:
    """A tuple-matching create is only a genuine already-landed duplicate if
    every field the baseline row actually carries agrees with the desired
    payload's FINAL bytes (post normalize_athlete_description, matching
    what TP echoes back). A field the baseline row doesn't carry at all
    (e.g. a summary inventory read that omits description text) can't be
    compared, so it is not grounds for a conflict."""
    if "description" in baseline_row:
        desired_description = normalize_athlete_description(payload.get("description"))
        existing_description = normalize_athlete_description(baseline_row.get("description"))
        if desired_description != existing_description:
            return False
    if op["kind"] == "workout_upsert" and "structure" in baseline_row:
        if bool(payload.get("structure")) != bool(baseline_row.get("structure")):
            return False
    return True


# ------------------------------------------------------------------- ctx
class Ctx:
    def __init__(self, args: argparse.Namespace):
        self.athlete_dir = args.athlete_dir.resolve()
        self.tp_athlete_id = str(args.tp_athlete_id)
        self.order_id = str(args.order_id)
        self.work_dir = args.work_dir.resolve()
        self.revision = args.revision
        self.wave_cutoff = args.wave_cutoff
        self.expected_creates = args.expected_creates
        self.waiver_reason = args.waiver_reason
        self.allow_executor_hash = args.allow_executor_hash
        self.window = (args.window_start, args.window_end)
        self.slug = args.athlete_dir.resolve().name
        self.identity_label = f"{self.slug}-{self.tp_athlete_id}"
        self.athlete = self.work_dir / "athlete"
        self.baseline = (args.baseline.resolve() if args.baseline
                          else self.work_dir / f"baseline-r{self.revision}.json")
        self.credential = f"chat-authorization-{self.order_id}"


# ------------------------------------------------------------- stage 0
def _bootstrap(ctx: Ctx, state_path: Path) -> dict:
    """Open revision 1 of this order's fulfillment state, seeded from
    --athlete-dir's own regenerated review catalog, and copy the pipeline
    artifacts this order will publish from into --work-dir/athlete. Mirrors
    sonja-publish/steve-publish's _bootstrap_from_steve, generalized to any
    source athlete dir rather than one hardcoded to Steve Wagner."""
    source_state_path = ctx.athlete_dir / "fulfillment_status.json"
    if not source_state_path.exists():
        raise PublishAthleteError(f"--athlete-dir has no fulfillment_status.json: {ctx.athlete_dir}")
    source_state = json.loads(source_state_path.read_text())
    if not source_state.get("order_id") or (source_state.get("generation_revision") or 0) < 1:
        raise PublishAthleteError("--athlete-dir fulfillment state is not a generated revision")

    ctx.athlete.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in RELEASE_ARTIFACT_NAMES:
        source = ctx.athlete_dir / name
        if not source.is_file():
            raise PublishAthleteError(f"--athlete-dir is missing required artifact: {name}")
        shutil.copy2(source, ctx.athlete / name)

    # The calendar_protection.requested=True flip happens on the WORK-DIR
    # COPY of canonical_training_model.json only -- never on --athlete-dir's
    # own file. tp_build_adoption_contract.py refuses to build an adoption
    # contract unless requested=True (it protects whatever the live
    # calendar inventory shows at build time); an order whose intake never
    # asked to preserve calendar items still needs that protection for
    # THIS publish, because the adoption contract is always built from the
    # live baseline, never a fabricated empty one (sonja/steve precedent,
    # 2026-08-24/25).
    canonical_path = ctx.athlete / "canonical_training_model.json"
    canonical_model = json.loads(canonical_path.read_text())
    protection = dict(canonical_model.get("calendar_protection") or {})
    if protection.get("requested") is not True:
        protection["requested"] = True
        canonical_model["calendar_protection"] = protection
        write_json(canonical_path, canonical_model)
        print("calendar_protection.requested flipped True on the work-dir copy only")

    blocking_issues = [
        {k: v for k, v in issue.items() if k not in {"waivable", "remediation"}}
        for issue in source_state.get("blocking_issues", [])
    ]
    required_confirmations = [
        {k: v for k, v in item.items() if k != "resolved_resolution"}
        for item in source_state.get("required_confirmations", [])
    ]
    derived_values = [
        {k: v for k, v in item.items() if k != "revision"}
        for item in source_state.get("derived_values", [])
    ]
    state = write_generation(
        state_path, ctx.identity_label, blocking_issues,
        order_id=ctx.order_id, delivery_platform="trainingpeaks",
        required_confirmations=required_confirmations,
        soft_confirmations=source_state.get("soft_confirmations") or [],
        derived_values=derived_values,
    )
    print("bootstrapped:", state["status"], "r", state["generation_revision"])
    assert state["generation_revision"] == 1
    state = record_identity_result(
        state_path, 1,
        {"outcome": "bound", "tp_athlete_id": ctx.tp_athlete_id, "candidates": []},
        capability_jti=f"{ctx.slug}-identity-offline-r1-fable",
    )
    print("identity bound:", state["platform_identity"]["tp_athlete_id"])
    return state


def stage_offline(ctx: Ctx) -> dict:
    state_path = ctx.athlete / "fulfillment_status.json"
    if not state_path.exists():
        _bootstrap(ctx, state_path)
    state = load(state_path)
    assert state["order_id"] == ctx.order_id
    assert state["delivery_platform"] == "trainingpeaks"
    if state["generation_revision"] < ctx.revision:
        # Wave bump: write_generation resets attempt/cancel/seal fields and
        # opens the next reviewable revision, carrying the immutable
        # order/platform identity and re-affirming the TP athlete binding.
        previous = state
        state = write_generation(
            state_path, ctx.identity_label, [],
            order_id=ctx.order_id, delivery_platform="trainingpeaks",
            required_confirmations=previous.get("required_confirmations") or [],
            soft_confirmations=previous.get("soft_confirmations") or [],
            derived_values=[{k: v for k, v in item.items() if k != "revision"}
                            for item in previous.get("derived_values") or []],
        )
        print("regenerated:", state["status"], "r", state["generation_revision"])
        assert state["generation_revision"] == ctx.revision
        state = record_identity_result(
            state_path, ctx.revision,
            {"outcome": "bound", "tp_athlete_id": ctx.tp_athlete_id, "candidates": []},
            capability_jti=f"{ctx.slug}-identity-live-r{ctx.revision}-fable",
        )
        print("identity bound:", state["platform_identity"]["tp_athlete_id"])
    assert state["generation_revision"] == ctx.revision
    assert (state.get("platform_identity") or {}).get("tp_athlete_id") == ctx.tp_athlete_id

    contract_out = ctx.work_dir / f"apply_contract_adoption_r{ctx.revision}.json"
    if state.get("model_seal"):
        print("release already sealed; reusing", state["model_seal"][:12])
    else:
        if not ctx.baseline.is_file():
            raise PublishAthleteError(f"--baseline file not found: {ctx.baseline}")
        baseline = json.loads(ctx.baseline.read_text())
        validate_baseline_schema(baseline)
        if not contract_out.exists():
            run([sys.executable, str(REPO / "tools/tp_build_adoption_contract.py"),
                 "--athlete-dir", str(ctx.athlete),
                 "--provider-inventory", str(ctx.baseline),
                 "--output", str(contract_out),
                 "--expected-owned-workouts", "0", "--expected-owned-notes", "0"])
            print("adoption contract built:", contract_out.name)
        merge_generation_blockers(state_path, ctx.revision, "apply_contract", [])
        contract = json.loads(contract_out.read_text())
        assert contract["order_id"] == ctx.order_id and contract["tp_athlete_id"] == ctx.tp_athlete_id
        assert contract["generation_revision"] == ctx.revision
        if ctx.expected_creates is None:
            raise PublishAthleteError("--expected-creates is required to seal a release")
        kept_ops, dropped, deferred = filter_and_normalize_operations(
            contract["operations"], baseline=baseline, wave_cutoff=ctx.wave_cutoff,
            expected_creates=ctx.expected_creates, waiver_reason=ctx.waiver_reason)
        print(f"deferred to next wave: {deferred}")
        contract["operations"] = kept_ops
        creates = [o for o in kept_ops if o["disposition"] == "create"]
        print(f"filtered {dropped} already-landed creates; contract r{ctx.revision}: "
              f"{len(creates)} creates, {len(kept_ops) - len(creates)} keeps")
        release = ctx.work_dir / f"release-r{ctx.revision}"
        if release.exists():
            shutil.rmtree(release)
        artifacts = release / "artifacts"
        artifacts.mkdir(parents=True, mode=0o700)
        for name in RELEASE_ARTIFACT_NAMES:
            shutil.copy2(ctx.athlete / name, artifacts / name)
        # Record the cadence-structure count THIS release's own creates
        # carry so readback can assert equality against what actually
        # lands, instead of merely printing a total (see stage 4 / main()
        # -- readback matches this against the cadence count among only
        # the workouts this release created).
        expected_cadence_count = sum(
            1 for o in creates
            if o["kind"] == "workout_upsert"
            and "roundOrStridePerMinute" in json.dumps((o.get("payload") or {}).get("structure") or {}))
        write_json(artifacts / "expected_cadence_count.json",
                   {"expected_cadence_count": expected_cadence_count})
        # Re-stamp the model seal over the FILTERED operation set, computed
        # by the exact function the release finalizer verifies with.
        write_json(artifacts / "apply_contract.json", contract)
        contract["model_seal"] = _canonical_model_seal_from_release(
            release, load(state_path), contract)
        write_json(artifacts / "apply_contract.json", contract)
        write_json(contract_out, contract)
        validate_contract(json.loads((artifacts / "apply_contract.json").read_text()))
        state = finalize_transitional_release(state_path, release, expected_revision=ctx.revision)
        assert state["model_seal"] == contract["model_seal"], "seal mismatch"
        print("sealed", state["model_seal"][:12])
    state = load(state_path)
    if state["status"] != APPROVED:
        decisions = [{"item_id": i["item_id"], "revision": ctx.revision, "disposition": "confirmed"}
                     for i in state["review_items"] if i["type"] in {"required_confirmation", "verified_fact"}]
        waiver = None
        if state["status"] == "BLOCKED_REVIEW":
            if not ctx.waiver_reason:
                raise PublishAthleteError(
                    "state is BLOCKED_REVIEW and no --waiver-reason was supplied — "
                    "refusing to auto-waive blockers")
            blocker_ids = sorted(issue["id"] for issue in state["blocking_issues"])
            waiver = {"rule_ids": blocker_ids, "reason": ctx.waiver_reason}
        state = transition(state_path, APPROVED, "matti-rowe", expected_revision=ctx.revision,
                           expected_catalog_digest=state["review_catalog_digest"],
                           review_decisions=decisions, credential=ctx.credential + f"-r{ctx.revision}",
                           waiver=waiver)
    print("state", state["status"], "seal", state["model_seal"][:12])
    return state


# ------------------------------------------------------------- stage 1
def stage_transport(ctx: Ctx) -> dict:
    actual_commit = run(["git", "rev-parse", "HEAD"]).strip()
    if run(["git", "status", "--porcelain"]).strip():
        raise PublishAthleteError("engine worktree is dirty")
    if file_sha(PLAYWRITER) != EXPECTED_BIN_SHA:
        raise PublishAthleteError("playwriter digest drift")
    if file_sha(REPO / "tools/tp_phase5_browser_payload.js") != EXPECTED_PAYLOAD_SHA:
        raise PublishAthleteError("browser payload digest drift")
    compat = json.loads(COMPATIBILITY.read_text())
    if compat["engine"]["inspected_commit"] != actual_commit:
        raise PublishAthleteError("plugin engine binding drift")
    caps = compat["capabilities"]
    if caps.get("trainingpeaks_read") is not True or caps.get("trainingpeaks_write") is not True:
        raise PublishAthleteError("TrainingPeaks capability disabled")
    if caps.get("zone_write") is not False:
        raise PublishAthleteError("zone capability must stay disabled")
    created = run([str(PLAYWRITER), "session", "new", "--browser", BROWSER_KEY],
                  cwd=ctx.work_dir, timeout=90)
    m = re.search(r"Session\s+(\d+)\s+created", created)
    if not m:
        raise PublishAthleteError("no fresh playwriter session")
    session = m.group(1)
    report = json.loads(run([
        sys.executable, str(PREFLIGHT), "--bin", str(PLAYWRITER), "--session", session,
        "--expected-version", VERSION, "--expected-profile", PROFILE,
        "--expected-browser-key", BROWSER_KEY, "--expected-session-cwd", str(ctx.work_dir),
        "--check-page"], cwd=ctx.work_dir))
    if not report.get("ready"):
        raise PublishAthleteError(f"preflight not ready: {report.get('blockers')}")
    binding = {
        "GG_TP_PLAYWRITER_BIN": str(PLAYWRITER), "GG_TP_PLAYWRITER_BIN_SHA256": EXPECTED_BIN_SHA,
        "GG_TP_PLAYWRITER_VERSION": VERSION, "GG_TP_PLAYWRITER_SESSION": session,
        "GG_TP_PLAYWRITER_PROFILE": PROFILE, "GG_TP_PLAYWRITER_BROWSER_KEY": BROWSER_KEY,
        "GG_TP_PLAYWRITER_SESSION_CWD": str(ctx.work_dir),
    }
    if report.get("execution_binding") != binding:
        raise PublishAthleteError("transport binding mismatch")
    print("transport ready, session", session)
    return binding


# ----------------------------------------------------------- stage 2/4
def inventory(ctx: Ctx, binding: dict, name: str) -> dict:
    out = ctx.work_dir / f"{ctx.slug}-{name}.json"
    run([sys.executable, str(READ_INVENTORY), "--compatibility", str(COMPATIBILITY),
         "--bin", str(PLAYWRITER), "--session", binding["GG_TP_PLAYWRITER_SESSION"],
         "--expected-version", VERSION, "--expected-bin-sha256", EXPECTED_BIN_SHA,
         "--expected-profile", PROFILE, "--expected-browser-key", BROWSER_KEY,
         "--session-root", str(ctx.work_dir), "--tp-athlete-id", ctx.tp_athlete_id,
         "--start", ctx.window[0], "--end", ctx.window[1], "--out", out.name],
        cwd=ctx.work_dir, timeout=300)
    return json.loads(out.read_text())


def rows_digest(inv: dict) -> str:
    return digest({"workouts": inv["workouts"], "notes": inv["notes"], "events": inv.get("events", [])})


def _has_cadence(row: dict) -> bool:
    return "roundOrStridePerMinute" in json.dumps(row.get("structure") or {})


def compute_publication_summary(
    before: dict, after: dict, contract: dict, *,
    execute_status: Optional[str], expected_cadence_count: Optional[int] = None,
) -> dict:
    """Pure readback verification, isolated from the state machine so it can
    be unit-tested with synthetic before/after inventories (mirrors
    filter_and_normalize_operations's isolation). Verifies:
      - every desired create (workout AND note) landed;
      - every protected WORKOUT row is unchanged (digest-stable);
      - every protected NOTE row is unchanged (digest-stable) -- readback
        used to check workouts only;
      - if the offline stage recorded an expected cadence-structure count
        for this release's own creates, the cadence count actually landed
        among those creates equals it EXACTLY, not merely a printed total;
      - every desired create that DID land carries the same description as
        requested, under athlete-layer normalization (normalize_athlete_
        description) -- both sides normalized the same way, since TP's
        athlete-calendar layer strips continuation-line leading whitespace
        on top of the internal-space collapse (Juan Echeverri TP 1683197,
        2026-08-25: 6/23 descriptions differed 2-16 chars unnormalized).
    ``summary["ok"]`` is False if any of the above fails.
    """
    creates = [o for o in contract["operations"] if o["disposition"] == "create"]
    want = {(o["kind"], str(o["payload"]["date"])[:10], o["payload"]["title"]) for o in creates}
    have = {("workout_upsert", str(w["date"])[:10], w["title"]) for w in after["workouts"]} | \
           {("calendar_note_upsert", str(n["date"])[:10], n["title"]) for n in after["notes"]}
    missing = sorted(want - have)

    after_workouts_by_key = {(str(w["date"])[:10], w["title"]): w for w in after["workouts"]}
    after_notes_by_key = {(str(n["date"])[:10], n["title"]): n for n in after.get("notes") or []}
    content_mismatches = []
    for o in creates:
        key = (str(o["payload"]["date"])[:10], o["payload"]["title"])
        landed = (after_workouts_by_key if o["kind"] == "workout_upsert"
                  else after_notes_by_key).get(key)
        if landed is None:
            continue  # already tracked in `missing`
        desired = normalize_athlete_description(o["payload"].get("description"))
        actual = normalize_athlete_description(landed.get("description"))
        if desired != actual:
            content_mismatches.append({"kind": o["kind"], "date": key[0], "title": key[1]})

    before_workouts = {str(w["id"]): w for w in before["workouts"]}
    after_workouts = {str(w["id"]): w for w in after["workouts"]}
    protected_workouts_changed = sorted(
        i for i, w in before_workouts.items()
        if digest(w) != digest(after_workouts.get(i)))

    before_notes = {str(n["id"]): n for n in before.get("notes") or []}
    after_notes = {str(n["id"]): n for n in after.get("notes") or []}
    protected_notes_changed = sorted(
        i for i, n in before_notes.items()
        if digest(n) != digest(after_notes.get(i)))

    total_cadence = sum(1 for w in after["workouts"] if _has_cadence(w))

    release_workout_keys = {(str(o["payload"]["date"])[:10], o["payload"]["title"])
                             for o in creates if o["kind"] == "workout_upsert"}
    release_cadence_landed = sum(
        1 for w in after["workouts"]
        if (str(w["date"])[:10], w["title"]) in release_workout_keys and _has_cadence(w))

    summary = {
        "created_expected": len(creates), "created_missing": missing,
        "protected_workouts_changed": protected_workouts_changed,
        "protected_notes_changed": protected_notes_changed,
        "after_workouts": len(after["workouts"]), "after_notes": len(after["notes"]),
        "after_structures_with_cadence": total_cadence,
        "release_cadence_landed": release_cadence_landed,
        "content_mismatches": content_mismatches,
        "execute_status": execute_status,
    }
    cadence_mismatch = False
    if expected_cadence_count is not None:
        summary["release_cadence_expected"] = expected_cadence_count
        cadence_mismatch = release_cadence_landed != expected_cadence_count

    summary["ok"] = not (missing or protected_workouts_changed or protected_notes_changed
                          or cadence_mismatch or content_mismatches)
    return summary


# ------------------------------------------------------------- stage 3
def stage_execute(ctx: Ctx, binding: dict, state: dict) -> dict:
    executor = ctx.work_dir / "tp_phase5_execute_verbose.py"
    if not executor.is_file():
        raise PublishAthleteError(
            f"missing {executor} — this private, per-installation verbose fork of "
            "tools/tp_phase5_execute.py must exist under --work-dir before execute")
    resolve_executor_sha(executor, allow_executor_hash=ctx.allow_executor_hash)
    contract_path = ctx.work_dir / f"release-r{ctx.revision}/artifacts/apply_contract.json"
    contract = json.loads(contract_path.read_text())
    capability_secret = secrets.token_urlsafe(48)
    grant_secret = secrets.token_urlsafe(48)
    codec = CapabilityCodec({CAPABILITY_KID: capability_secret}, audience=CAPABILITY_AUDIENCE)
    suffix = secrets.token_hex(10)
    jti = f"{ctx.slug}-apply-r{ctx.revision}-{suffix}"
    now = int(time.time())
    capability = codec.issue({
        "order_id": ctx.order_id, "tp_athlete_id": ctx.tp_athlete_id,
        "generation_revision": ctx.revision,
        # Sign with the SERVICE's digest so issuer and verifier cannot
        # disagree on canonicalization.
        "model_seal": state["model_seal"], "contract_digest": _ps._digest(contract),
        "approval_digest": _ps._digest(state["approval"]),
        "release_manifest_digest": state["release_manifest_digest"],
        "authorization_id": f"{ctx.slug}-authorization-r{ctx.revision}-{suffix}",
        "actor": "coach:matti-rowe", "scope": "trainingpeaks:athlete-calendar",
        "action": "trainingpeaks.apply", "audience": CAPABILITY_AUDIENCE,
        # worker_service caps capability TTL at 15 minutes; keep this well
        # under it (10 min) rather than pushing the cap.
        "iat": now - 1, "exp": now + 10 * 60, "jti": jti,
    }, kid=CAPABILITY_KID)
    cap_path = ctx.work_dir / "capabilities" / f"{jti}.txt"
    cap_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    cap_path.write_text(capability + "\n"); cap_path.chmod(0o600)
    staging = Path(tempfile.mkdtemp(prefix=f"staging-{ctx.slug}-", dir=ctx.work_dir)); staging.chmod(0o700)
    env = {**os.environ, **binding,
           # apply_contract.py flat-imports its athletes/scripts siblings
           # (delivery_notes); tp_phase5_execute only adds repo root + webhook.
           "PYTHONPATH": os.pathsep.join(str(x) for x in (REPO, REPO / "webhook", REPO / "athletes/scripts")),
           "GG_WORKER_CAPABILITY_KID": CAPABILITY_KID, "GG_WORKER_CAPABILITY_SECRET": capability_secret,
           "GG_TP_EXECUTION_GRANT_KID": GRANT_KID, "GG_TP_EXECUTION_GRANT_SECRET": grant_secret,
           "GG_TP_LIVE_WRITES_ENABLED": "1", "GG_TP_CANARY_ENABLED": "0"}
    try:
        output = run([sys.executable, str(executor),
                      "--contract", str(contract_path), "--state", str(ctx.athlete / "fulfillment_status.json"),
                      "--capability-file", str(cap_path), "--record-root", str(ctx.work_dir / "records"),
                      "--staging-root", str(staging)], env=env, timeout=40 * 60)
    finally:
        cap_path.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
    result = json.loads(output)
    result["_jti"] = jti
    return result


# ---------------------------------------------------------------- main
def _parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--athlete-dir", type=Path, required=True,
                         help="Pipeline-generated athlete dir this order publishes from "
                              "(fulfillment_status.json, canonical_training_model.json, etc.).")
    parser.add_argument("--tp-athlete-id", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--work-dir", type=Path, required=True,
                         help="Private, non-git directory (replaces PRIVATE_ROOT/<slug>-publish/).")
    parser.add_argument("--stage", choices=("inventory", "offline", "barrier", "all"), default="all")
    parser.add_argument("--revision", type=int, default=1)
    parser.add_argument("--wave-cutoff", default=None)
    parser.add_argument("--expected-creates", type=int, default=None)
    parser.add_argument("--baseline", type=Path, default=None,
                         help="Defaults to <work-dir>/baseline-r<revision>.json.")
    parser.add_argument("--waiver-reason", default=None,
                         help="Required only if the offline stage lands in BLOCKED_REVIEW, "
                              "or if a desired create content-conflicts with an existing "
                              "baseline row of the same (kind, date, title); "
                              "there is no auto-generated waiver text.")
    parser.add_argument("--allow-executor-hash", default=None,
                         help="Override the canonical tools/tp_phase5_executor.sha256 pin "
                              "with this sha256 -- only for a deliberate, reviewed update "
                              "to the private tp_phase5_execute_verbose.py fork.")
    parser.add_argument("--window-start", default=DEFAULT_WINDOW[0])
    parser.add_argument("--window-end", default=DEFAULT_WINDOW[1])
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    ctx = Ctx(args)

    if args.stage == "inventory":
        # GET-only: fresh provider inventory via the kernel's own reader,
        # used to produce the next wave's --baseline file.
        binding = stage_transport(ctx)
        inv = inventory(ctx, binding, "fresh")
        out = ctx.work_dir / f"{ctx.slug}-fresh.json"
        print("fresh inventory:", len(inv["workouts"]), "workouts", len(inv["notes"]), "notes ->", out)
        return 0

    state = stage_offline(ctx)
    if args.stage == "offline":
        return 0
    binding = stage_transport(ctx)
    before = inventory(ctx, binding, "barrier")
    if not ctx.baseline.is_file():
        raise PublishAthleteError(f"--baseline file not found: {ctx.baseline}")
    baseline = json.loads(ctx.baseline.read_text())
    if rows_digest(before) != rows_digest(baseline):
        raise PublishAthleteError(
            "READ BARRIER: live inventory drifted from the one the contract was built on; stop")
    print("read barrier ok:", len(before["workouts"]), "workouts", len(before["notes"]), "notes")
    if args.stage == "barrier":
        return 0

    result = stage_execute(ctx, binding, state)
    write_json(ctx.work_dir / "execute-result.json", result)
    print("execute:", {k: result.get(k) for k in ("status", "state_status", "receipt_count", "operation_count")
                        if k in result})
    if result.get("status") not in EXECUTE_SUCCESS_STATUSES:
        raise PublishAthleteError(
            f"executor did not report a success status (got {result.get('status')!r}, "
            f"expected one of {sorted(EXECUTE_SUCCESS_STATUSES)}; "
            f"error_type={result.get('error_type')!r} error_message={result.get('error_message')!r}) "
            "— refusing to treat this as a successful publish even if downstream counts look fine")
    after = inventory(ctx, binding, "after")
    release_dir = ctx.work_dir / f"release-r{ctx.revision}/artifacts"
    contract = json.loads((release_dir / "apply_contract.json").read_text())
    expected_cadence_count = None
    expected_cadence_path = release_dir / "expected_cadence_count.json"
    if expected_cadence_path.is_file():
        expected_cadence_count = json.loads(expected_cadence_path.read_text())["expected_cadence_count"]
    summary = compute_publication_summary(
        before, after, contract, execute_status=result.get("status"),
        expected_cadence_count=expected_cadence_count)
    write_json(ctx.work_dir / "publication-summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PublishAthleteError as exc:
        print(f"publish_athlete: {exc}", file=sys.stderr)
        sys.exit(1)
