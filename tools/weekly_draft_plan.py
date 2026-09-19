#!/usr/bin/env python3
"""Weekly per-athlete DRAFT dynamic plan orchestrator (Motoren spec Part B).

Spec: docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md, section
"B -- implementation plan" and "B -- revision 2" (revision 2 overrides
where they differ). One run per active athlete, triggered by Matti's
weekly review. Never touches TrainingPeaks and never writes an athlete's
live calendar -- this module writes only athletes/<id>/ (via the existing
tools it calls) and ``builds_root``. The actual TP upsert is a separate
browser-context script (``plan-builds/_shared/upsert_draft_plan.js``).

Per-athlete pipeline:
  1. Exclusions check (``coaching_loop.exclusions.assert_not_excluded``)
     -- see "Exclusions numeric id" below for how the id is sourced.
  2. Profile refresh: ``athletes/scripts/profile_refresh.py <id> --packet
     <packet_path> --history <builds_root>/<id>/coaching_history.md
     --today <run_date> --write``. Run as a subprocess; if the script does
     not exist yet (it is being built in parallel by another executor)
     the step is skipped with a logged note and the existing profile /
     rules / packet inputs are passed through unchanged.
  3. Read ``builds_root/<id>/weekly_draft_state.json``
     (``{plan_id, plan_title, window_start, inputs_sha256, last_run}``).
  4. Trigger rule (spec B decision 7): rebuild when the run's "next
     Monday" is later than ``state.window_start``, OR the inputs hash
     differs, OR ``--force``. Otherwise a "skipped" manifest is written
     and nothing else runs.
  5. Holds (spec B decision 2): a non-empty ``refresh_diff.json``
     ``"holds"`` list (FTP mismatch, race-date mismatch, <2 weeks to
     race, or a code-excluded athlete) stops the build with a "held"
     manifest before any generation runs.
  6. ``athletes/scripts/generate_full_package.py <id> --skip-validation``
     -- the 9-step Motoren orchestrator, run against the (now refreshed)
     profile.yaml. This satisfies the Motoren-only gate the same way
     ``intake_to_plan.py`` does: ``intake_to_plan.py`` builds a profile
     from an intake file and then calls this exact same 9-step
     orchestrator on it. There is no intake file for a weekly re-run of
     an existing coached athlete (the "intake" already happened and the
     profile is refreshed in place instead) -- so the orchestrator is
     invoked directly on the existing, refreshed profile.yaml, which is
     the documented legacy-fallback / existing-profile invocation form.
  7. ``tools/build_tp_plan_payload.py --athlete-dir <athlete_dir> --out-dir
     <run_dir>`` -- plan_payload.json / notes_payload.json / lint.json.
  8. ``tools/athlete_layer.py --rules <builds_root>/<id>/rules.yaml
     --in-dir <run_dir> --out-dir <run_dir>`` -- per-athlete rules
     (title format, optional-intensity text, strip rules, ...) applied on
     top of step 7's output, producing ``plan_payload_final.json`` /
     ``notes_payload_final.json``. Skipped with a logged note (same as
     step 2) if the script does not exist yet; step 7's plain output is
     used as-is in that case.
  9. ``draft_manifest.json`` is written into
     ``builds_root/<id>/weekly-<run_date>/`` and
     ``weekly_draft_state.json`` is updated: ``plan_id`` is preserved
     verbatim (this module never creates or mutates a TP plan id --
     that happens only when ``upsert_draft_plan.js`` runs and its
     receipt is recorded back into the state file by the runbook);
     ``window_start`` is taken from ``refresh_diff.json`` when the
     refresh step reported one, else the run's own "next Monday".

Exclusions numeric id (ASSUMPTION, flagged as an open question):
``coaching_loop.exclusions`` is keyed on TrainingPeaks' *numeric* athlete
id (e.g. 418209). This pipeline's ``athlete_id`` is always the directory
slug (``forest-hietpas``); there is no slug -> numeric-id table anywhere
in this repo. The one place a numeric TP id would naturally already be
present is the weekly packet itself (``weekly_packet/v1``, a TP-session
pull scoped to one athlete) -- so this module looks for
``packet["tp_athlete_id"]`` or ``packet["source_manifest"]["tp_athlete_id"]``
(also accepting ``athlete_numeric_id`` as an alias) and calls
``assert_not_excluded`` on it when present. When absent, the check is
logged as *skipped* in the manifest's ``notes`` -- never silently treated
as "not excluded". This is a real gap: until ``tools/tp_weekly_packet.js``
/ ``athletes/scripts/weekly_packet.py`` land and their schema is known,
the exclusion gate is best-effort. The pilot roster (Forest, Edward, Ari,
Judd, Mike Wallace) does not include the excluded athlete (418209) today.

refresh_diff.json contract (ASSUMED, since ``profile_refresh.py`` is being
built in parallel and this module does not own its schema): a dict read
from ``builds_root/<id>/refresh_diff.json`` (kept alongside the private
``coaching_history.md``, never committed to the repo, since both can
carry verbatim athlete text) with at least:
``{"window_start": "YYYY-MM-DD" | null,
"holds": [{"type", "message", "sources": [str, str]}],
"writes": [{"path", "old", "new", "source"}, ...],
"standing_contradictions": [...],
"demonstrated": {"hours_6wk": float, "tss_6wk": float, "ctl": float}}``.
Missing keys default to empty; an absent file (refresh skipped, or the
refresh made no holds/writes) is treated as "no holds, no window
override". The whole dict is passed through verbatim into
``draft_manifest.json["refresh_diff"]`` (this module does not interpret
``writes`` / ``demonstrated`` beyond reading ``holds`` and
``window_start`` -- ``tools/weekly_review_page.py`` is the consumer of
the rest of the shape).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coaching_loop.canonical_json import canonical_bytes  # noqa: E402
from coaching_loop.code_manifest import build_code_manifest  # noqa: E402
from coaching_loop.exclusions import ExcludedAthleteError, assert_not_excluded  # noqa: E402

STATE_FILENAME = "weekly_draft_state.json"
HISTORY_FILENAME = "coaching_history.md"
RULES_FILENAME = "rules.yaml"
REFRESH_DIFF_FILENAME = "refresh_diff.json"
MANIFEST_FILENAME = "draft_manifest.json"


class WeeklyDraftError(RuntimeError):
    """A pipeline step failed non-recoverably for one athlete."""


# --------------------------------------------------------------------------
# small IO / formatting helpers
# --------------------------------------------------------------------------

def _next_monday(run_date: date) -> date:
    """The run's "next Monday": ``run_date`` itself when it is already a
    Monday, else the closest upcoming Monday."""
    offset = (7 - run_date.weekday()) % 7
    return run_date if offset == 0 else run_date + timedelta(days=offset)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text())
    return loaded if isinstance(loaded, dict) else {}


def _json_safe(value: Any) -> Any:
    """Round-trip through json with ``default=str`` so every value handed
    to ``canonical_bytes`` is a plain JSON type (guards against yaml
    occasionally parsing an unquoted date-looking scalar as a
    ``datetime.date``)."""
    return json.loads(json.dumps(value, default=str))


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _draft_title(profile: Mapping[str, Any]) -> str:
    """Ratified format (spec B revision 2, decision 6):
    ``DRAFT -- <Name> -- <Race|Block> <N>wk``."""
    name = profile.get("name") or profile.get("athlete_id") or "Athlete"
    fulfillment = profile.get("fulfillment") or {}
    weeks = fulfillment.get("weeks_purchased")
    target = profile.get("target_race") or {}
    race = target.get("name")
    # An unpicked event slot ("TBD -- Oct 24 event slot") is not a race name;
    # label the draft by the block's phase instead.
    if not race or str(target.get("status") or "").lower() == "unpicked" or str(race).upper().startswith("TBD"):
        phase = (profile.get("coached_block") or {}).get("phase")
        label = str(phase).replace("_", " ").title() if phase else "Block"
    else:
        label = race
    n_wk = f"{weeks}wk" if weeks else ""
    tail = " ".join(part for part in (label, n_wk) if part)
    return f"DRAFT — {name} — {tail}" if tail else f"DRAFT — {name}"


# --------------------------------------------------------------------------
# exclusions
# --------------------------------------------------------------------------

def _numeric_tp_id_from_packet(packet: Mapping[str, Any] | None) -> Any:
    """See "Exclusions numeric id" in the module docstring."""
    if not packet:
        return None
    for key in ("tp_athlete_id", "athlete_numeric_id"):
        if packet.get(key) is not None:
            return packet[key]
    manifest = packet.get("source_manifest") or {}
    for key in ("tp_athlete_id", "athlete_numeric_id"):
        if manifest.get(key) is not None:
            return manifest[key]
    return None


def _check_exclusions(packet: Mapping[str, Any] | None, notes: list[str]) -> None:
    """Raises ``ExcludedAthleteError`` for a code-excluded athlete;
    otherwise returns. Logs a skip note when no numeric id is available
    to check -- never silently treats "unknown" as "not excluded"."""
    numeric_id = _numeric_tp_id_from_packet(packet)
    if numeric_id is None:
        notes.append(
            "exclusions check skipped: no numeric TP athlete id in the "
            "packet (weekly_packet/v1 does not carry one yet -- see "
            "module docstring)"
        )
        return
    assert_not_excluded(numeric_id, layer="weekly_draft_plan")


# --------------------------------------------------------------------------
# subprocess-calling steps (each a standalone function so tests can
# monkeypatch it with a fixture writer instead of really invoking the
# script)
# --------------------------------------------------------------------------

def _run_profile_refresh(
    *, repo_root: Path, athlete_id: str, packet_path: Path, history_path: Path,
    run_date: date, notes: list[str],
) -> bool:
    script = repo_root / "athletes" / "scripts" / "profile_refresh.py"
    if not script.exists():
        notes.append(
            "profile_refresh.py not found yet -- refresh skipped, inputs "
            "passed through unchanged"
        )
        return False
    cmd = [
        sys.executable, str(script), athlete_id,
        "--packet", str(packet_path),
        "--history", str(history_path),
        "--today", run_date.isoformat(),
        "--write",
    ]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise WeeklyDraftError(
            f"profile_refresh.py failed (exit {result.returncode}): "
            f"{result.stderr.strip()[-2000:]}"
        )
    return True


def _run_generate_full_package(*, repo_root: Path, athlete_id: str) -> None:
    script = repo_root / "athletes" / "scripts" / "generate_full_package.py"
    cmd = [sys.executable, str(script), athlete_id, "--skip-validation"]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise WeeklyDraftError(
            f"generate_full_package.py failed (exit {result.returncode}): "
            f"{result.stderr.strip()[-2000:]}"
        )


def _run_build_tp_plan_payload(
    *, repo_root: Path, athlete_dir: Path, out_dir: Path,
    plan_day_one: str | None = None,
) -> None:
    script = repo_root / "tools" / "build_tp_plan_payload.py"
    cmd = [
        sys.executable, str(script),
        "--athlete-dir", str(athlete_dir),
        "--out-dir", str(out_dir),
    ]
    if plan_day_one:
        cmd += ["--plan-day-one", plan_day_one]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise WeeklyDraftError(
            f"build_tp_plan_payload.py failed (exit {result.returncode}): "
            f"{result.stderr.strip()[-2000:]}"
        )


def _run_athlete_layer(
    *, repo_root: Path, rules_path: Path, in_dir: Path, out_dir: Path,
    notes: list[str],
) -> bool:
    script = repo_root / "tools" / "athlete_layer.py"
    if not script.exists():
        notes.append(
            "athlete_layer.py not found yet -- layer step skipped, "
            "build_tp_plan_payload.py output used as-is"
        )
        return False
    cmd = [
        sys.executable, str(script),
        "--rules", str(rules_path),
        "--in-dir", str(in_dir),
        "--out-dir", str(out_dir),
    ]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise WeeklyDraftError(
            f"athlete_layer.py failed (exit {result.returncode}): "
            f"{result.stderr.strip()[-2000:]}"
        )
    return True


# --------------------------------------------------------------------------
# refresh_diff / state
# --------------------------------------------------------------------------

def _load_refresh_diff(path: Path) -> dict:
    """Normalise profile_refresh's RefreshDiff.as_dict() onto the keys this
    module and the review page read. The producer writes ``profile_changes``,
    ``holds[{code,...}]`` and ``window{start,end,weeks,mode}``; the assumed
    shape (``writes``, ``holds[{type}]``, ``window_start``) is still accepted.
    ``demonstrated`` (6-week load) is filled by the caller from the packet."""
    data = _read_json(path)
    if not isinstance(data, dict):
        data = {}
    window = data.get("window") if isinstance(data.get("window"), dict) else {}
    data.setdefault("window_start", window.get("start"))
    data.setdefault("holds", [])
    for hold in data["holds"]:
        if isinstance(hold, dict):
            hold.setdefault("type", hold.get("code", ""))
            hold.setdefault("code", hold.get("type", ""))
    data.setdefault("writes", data.get("profile_changes") or [])
    data.setdefault("standing_contradictions", [])
    data.setdefault("demonstrated", {})
    return data


@dataclass
class DraftState:
    plan_id: str | None = None
    plan_title: str | None = None
    window_start: str | None = None
    inputs_sha256: str | None = None
    last_run: str | None = None

    @classmethod
    def load(cls, path: Path) -> "DraftState":
        data = _read_json(path)
        if not isinstance(data, dict):
            return cls()
        return cls(
            plan_id=data.get("plan_id"),
            plan_title=data.get("plan_title"),
            window_start=data.get("window_start"),
            inputs_sha256=data.get("inputs_sha256"),
            last_run=data.get("last_run"),
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "plan_title": self.plan_title,
            "window_start": self.window_start,
            "inputs_sha256": self.inputs_sha256,
            "last_run": self.last_run,
        }


def _inputs_hash(
    *, profile: Mapping[str, Any], rules: Mapping[str, Any],
    packet: Mapping[str, Any], code_manifest: Mapping[str, Any],
) -> str:
    """Spec B decision 7:
    ``coaching_loop.canonical_json.canonical_bytes`` over (profile.yaml,
    rules.yaml, packet fields that can change a decision, code manifest).
    Timestamps / review windows / ids / next-week plans are excluded --
    the packet's own ``fetched_at`` and ``source_manifest`` are the
    timestamp-shaped fields this module knows about; a finer per-field
    filter belongs to whichever module owns the packet schema."""
    packet_fields = None
    try:
        import weekly_packet as _wp  # athletes/scripts on sys.path (see run())
        packet_fields = _wp.decision_fields(packet)
    except Exception:  # noqa: BLE001 -- fall back to the coarse filter
        packet_fields = {
            k: v for k, v in packet.items()
            if k not in ("fetched_at", "source_manifest", "as_of", "pmc_daily", "workouts", "notes")
        }
    payload = {
        "profile": profile,
        "rules": rules,
        "packet_fields": packet_fields,
        "code_manifest": {"git_sha": code_manifest.get("git_sha")},
    }
    return hashlib.sha256(canonical_bytes(_json_safe(payload))).hexdigest()


# --------------------------------------------------------------------------
# manifest assembly
# --------------------------------------------------------------------------

def _per_week_totals(plan_payload: list[dict], plan_dates: Mapping[str, Any]) -> list[dict]:
    weeks = plan_dates.get("weeks") or []
    ranges: list[tuple[Any, date, date]] = []
    for week in weeks:
        try:
            monday = date.fromisoformat(str(week["monday"]))
            sunday = date.fromisoformat(str(week["sunday"]))
        except (KeyError, ValueError, TypeError):
            continue
        ranges.append((week.get("week"), monday, sunday))
    totals = {n: {"week": n, "hours": 0.0, "tss": 0.0} for n, _, _ in ranges}
    for entry in plan_payload:
        day_str = str(entry.get("workoutDay") or "")[:10]
        try:
            day = date.fromisoformat(day_str)
        except ValueError:
            continue
        for week_num, monday, sunday in ranges:
            if monday <= day <= sunday:
                totals[week_num]["hours"] += float(entry.get("totalTimePlanned") or 0)
                totals[week_num]["tss"] += float(entry.get("tssPlanned") or 0)
                break
    ordered = [totals[n] for n, _, _ in ranges]
    for row in ordered:
        row["hours"] = round(row["hours"], 2)
        row["tss"] = round(row["tss"], 1)
    return ordered


def _build_manifest(
    *, athlete_id: str, profile: Mapping[str, Any], status: str,
    plan_id: str | None, refresh_diff: Mapping[str, Any], inputs_sha256: str,
    code_manifest: Mapping[str, Any], notes: list[str],
    plan_day_one: str | None = None, per_week: list[dict] | None = None,
    notes_count: int = 0, lint: Mapping[str, Any] | None = None,
    variety: Mapping[str, Any] | None = None, fallbacks_count: int = 0,
) -> dict:
    per_week = per_week or []
    return {
        "athlete_id": athlete_id,
        "name": profile.get("name"),
        "title": _draft_title(profile),
        "plan_id": plan_id,
        "plan_day_one": plan_day_one,
        "weeks": len(per_week),
        "per_week": per_week,
        "notes_count": notes_count,
        "lint": dict(lint or {}),
        "variety": dict(variety or {}),
        "fallbacks": fallbacks_count,
        # Whole refresh_diff dict, verbatim (see the module docstring's
        # "refresh_diff.json contract") -- weekly_review_page.py reads
        # "writes" / "demonstrated" straight off this, this module only
        # acts on "holds" and "window_start".
        "refresh_diff": dict(refresh_diff),
        "inputs_sha256": inputs_sha256,
        "code_manifest": dict(code_manifest),
        "status": status,
        "notes": notes,
    }


# --------------------------------------------------------------------------
# run()
# --------------------------------------------------------------------------

def run(
    athlete_id: str,
    *,
    packet_path: str | Path,
    run_date: str | date,
    builds_root: str | Path,
    repo_root: str | Path,
    force: bool = False,
) -> dict:
    repo_root = Path(repo_root)
    builds_root = Path(builds_root)
    packet_path = Path(packet_path)
    if isinstance(run_date, str):
        run_date = date.fromisoformat(run_date)

    athlete_dir = repo_root / "athletes" / athlete_id
    athlete_build_dir = builds_root / athlete_id
    state_path = athlete_build_dir / STATE_FILENAME
    history_path = athlete_build_dir / HISTORY_FILENAME
    rules_path = athlete_build_dir / RULES_FILENAME
    refresh_diff_path = athlete_build_dir / REFRESH_DIFF_FILENAME
    run_dir = athlete_build_dir / f"weekly-{run_date.isoformat()}"

    notes: list[str] = []
    _scripts = str(repo_root / "athletes" / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)

    if not packet_path.exists():
        raise WeeklyDraftError(f"packet not found: {packet_path}")
    packet = json.loads(packet_path.read_text())

    # 1. exclusions -- a code-excluded athlete is a held manifest (spec B
    # decision 2), never an exception that drops them off the review page.
    try:
        _check_exclusions(packet, notes)
    except ExcludedAthleteError as exc:
        profile = _read_yaml(athlete_dir / "profile.yaml") if (athlete_dir / "profile.yaml").exists() else {}
        state = DraftState.load(state_path)
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = _build_manifest(
            athlete_id=athlete_id, profile=profile, status="held", plan_id=state.plan_id,
            refresh_diff={"holds": [{"type": "excluded_athlete", "code": "excluded_athlete",
                                     "message": str(exc), "sources": ["coaching_loop.exclusions", "packet.tp_athlete_id"]}],
                          "writes": [], "window_start": None, "demonstrated": {}},
            inputs_sha256=None, code_manifest=build_code_manifest(repo_root), notes=notes,
        )
        _write_json(run_dir / MANIFEST_FILENAME, manifest)
        return manifest

    # 2. profile refresh
    _run_profile_refresh(
        repo_root=repo_root, athlete_id=athlete_id, packet_path=packet_path,
        history_path=history_path, run_date=run_date, notes=notes,
    )

    profile = _read_yaml(athlete_dir / "profile.yaml")
    rules = _read_yaml(rules_path)
    refresh_diff = _load_refresh_diff(refresh_diff_path)
    # 6-week demonstrated load for the review page, straight from the packet.
    if not refresh_diff.get("demonstrated"):
        try:
            sys.path.insert(0, str(repo_root / "athletes" / "scripts"))
            import weekly_packet as _wp  # type: ignore
            _load = _wp.load_6wk(packet)
            _weeks = _load.get("weeks") or []
            refresh_diff["demonstrated"] = {
                "hours_6wk": round(sum(w.get("hours_actual") or 0 for w in _weeks) / max(1, len(_weeks)), 2),
                "tss_6wk": round(sum(w.get("tss_actual") or 0 for w in _weeks) / max(1, len(_weeks)), 1),
                "ctl": _load.get("ctl_latest"),
                "weeks": _weeks,
            }
        except Exception as exc:  # noqa: BLE001 -- review-only data, never blocks a build
            notes.append(f"demonstrated load unavailable: {type(exc).__name__}: {exc}")
    code_manifest = build_code_manifest(repo_root)
    inputs_sha256 = _inputs_hash(
        profile=profile, rules=rules, packet=packet, code_manifest=code_manifest,
    )

    # 3. state
    state = DraftState.load(state_path)

    # 4. trigger rule (spec B decision 7)
    next_monday = _next_monday(run_date)
    prior_window_start = (
        date.fromisoformat(state.window_start) if state.window_start else None
    )
    window_rolled = prior_window_start is None or next_monday > prior_window_start
    hash_changed = state.inputs_sha256 != inputs_sha256
    should_rebuild = bool(force or window_rolled or hash_changed)

    if not should_rebuild:
        notes.append("no trigger: window and inputs unchanged")
        manifest = _build_manifest(
            athlete_id=athlete_id, profile=profile, status="skipped",
            plan_id=state.plan_id, refresh_diff=refresh_diff,
            inputs_sha256=inputs_sha256, code_manifest=code_manifest, notes=notes,
        )
        _write_json(run_dir / MANIFEST_FILENAME, manifest)
        state.last_run = _utcnow_iso()
        _write_json(state_path, state.to_dict())
        return manifest

    # 5. holds
    holds = refresh_diff.get("holds") or []
    if holds:
        manifest = _build_manifest(
            athlete_id=athlete_id, profile=profile, status="held",
            plan_id=state.plan_id, refresh_diff=refresh_diff,
            inputs_sha256=inputs_sha256, code_manifest=code_manifest, notes=notes,
        )
        _write_json(run_dir / MANIFEST_FILENAME, manifest)
        state.last_run = _utcnow_iso()
        _write_json(state_path, state.to_dict())
        return manifest

    # 6. generate
    _run_generate_full_package(repo_root=repo_root, athlete_id=athlete_id)
    profile = _read_yaml(athlete_dir / "profile.yaml")

    # 7. build payload
    _run_build_tp_plan_payload(repo_root=repo_root, athlete_dir=athlete_dir, out_dir=run_dir)

    # 8. athlete layer
    layer_ran = _run_athlete_layer(
        repo_root=repo_root, rules_path=rules_path, in_dir=run_dir, out_dir=run_dir,
        notes=notes,
    )

    plan_payload_name = "plan_payload_final.json" if layer_ran else "plan_payload.json"
    notes_payload_name = "notes_payload_final.json" if layer_ran else "notes_payload.json"
    plan_payload = _read_json(run_dir / plan_payload_name) or []
    notes_payload = _read_json(run_dir / notes_payload_name) or []
    lint_raw = _read_json(run_dir / "lint.json") or {}
    lint = {
        "fail": lint_raw.get("fail", 0),
        "warn": lint_raw.get("warn", 0),
        "allow_listed": len(lint_raw.get("allow_known_fails") or []),
    }
    plan_dates = _read_yaml(athlete_dir / "plan_dates.yaml")
    plan_day_one = lint_raw.get("plan_day_one") or plan_dates.get("plan_start")
    per_week = _per_week_totals(plan_payload, plan_dates)
    variety = _read_json(athlete_dir / "library_variety.json") or {}
    fallbacks = _read_json(athlete_dir / "library_fallbacks.json") or []
    # library_fallbacks.json mixes slot fallbacks (no ``reason``) with per-item
    # exclusion records (``reason`` = lint_excluded / seated_only); only the
    # slots that rendered synthetic are the coach-facing count.
    if isinstance(fallbacks, list):
        fallbacks = [f for f in fallbacks if isinstance(f, dict) and not f.get("reason")]

    # 9. manifest + state
    manifest = _build_manifest(
        athlete_id=athlete_id, profile=profile, status="built",
        plan_id=state.plan_id, refresh_diff=refresh_diff,
        inputs_sha256=inputs_sha256, code_manifest=code_manifest, notes=notes,
        plan_day_one=plan_day_one, per_week=per_week,
        notes_count=len(notes_payload), lint=lint, variety=variety,
        fallbacks_count=len(fallbacks),
    )
    _write_json(run_dir / MANIFEST_FILENAME, manifest)

    new_window_start = refresh_diff.get("window_start") or next_monday.isoformat()
    state.window_start = new_window_start
    state.inputs_sha256 = inputs_sha256
    state.plan_title = manifest["title"]
    state.last_run = _utcnow_iso()
    _write_json(state_path, state.to_dict())
    return manifest


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--athlete", action="append", required=True, dest="athletes",
                         help="athlete directory slug; repeatable")
    parser.add_argument("--packets-dir", required=True,
                         help="directory holding <athlete>.json weekly_packet/v1 files")
    parser.add_argument("--run-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--builds-root", required=True,
                         help="private plan-builds root (outside the repo)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    packets_dir = Path(args.packets_dir)
    exit_code = 0
    for athlete_id in args.athletes:
        packet_path = packets_dir / f"{athlete_id}.json"
        try:
            manifest = run(
                athlete_id,
                packet_path=packet_path,
                run_date=args.run_date,
                builds_root=args.builds_root,
                repo_root=ROOT,
                force=args.force,
            )
            print(f"{athlete_id}: {manifest['status']}")
        except Exception as exc:  # noqa: BLE001 -- one athlete's failure must not stop the roster
            print(f"{athlete_id}: ERROR {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
