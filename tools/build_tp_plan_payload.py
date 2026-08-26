#!/usr/bin/env python3
"""Build a TP plan-container payload from a generated athlete package.

Extracts the agent-improvised payload build documented in the
`tp-dynamic-plan-builder` skill (payload-build section) and proven in the
round-4 Steve Wagner build (plan-builds/steve-wagner/) into a tested repo
tool, per that skill's "Pending hardening" note.

Reads ``tp_manifest.json`` + ``fulfillment_manifest.json`` from an athlete
package directory and writes, into ``--out-dir``:

  plan_payload.json   one entry per in-window session:
                       {title, workoutTypeValueId, workoutDay, description,
                        totalTimePlanned, tssPlanned, structure,
                        coachComments?}
                       ``coachComments`` is present only when the session
                       carries a ``pre_activity_comment``. ``structure``
                       comes verbatim from ``tp_manifest.json`` (the
                       pipeline's own TP structure projection), with a
                       defensive AE-8.4d zero-power re-check (see
                       ``suppress_zero_power``).

  notes_payload.json   ALL of ``fulfillment_manifest.json``'s
                        ``native_notes``, post-exclusion:
                        {title, noteDate, description}

  exclusions.json       W00 (pre-plan) sessions/notes dated before
                         plan-day-one, which a plan container cannot hold
                         (Day 1 = Monday of Week 1) -- listed here for
                         manual placement rather than silently dropped.
                         The one exception is the Day-1 comment-protocol
                         note (story_notes.COMMENT_PROTOCOL_TITLE), which is
                         re-dated to plan-day-one and shipped in
                         notes_payload.json instead of being excluded --
                         every athlete needs the comment protocol on Day 1,
                         and it would otherwise silently vanish because it
                         is always authored in Week 0.

  lint.json             ae_lint.lint_workout run over every plan_payload.json
                         entry (--race-date = tp_manifest.json's race date),
                         plus which FAIL findings were allow-listed via
                         --allow-known-fails.

Plan-day-one defaults to ``plan_dates.yaml``'s ``week1_monday`` in
--athlete-dir when --plan-day-one is not given.

Usage:
  python3 tools/build_tp_plan_payload.py --athlete-dir <dir> --out-dir <dir> \\
      [--plan-day-one YYYY-MM-DD] [--allow-known-fails <path.json>]

Exit codes: 0 clean (or all FAILs allow-listed), 1 unresolved FAIL findings,
2 usage/input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "athletes" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "athletes" / "scripts"))

import yaml  # noqa: E402

from ae_lint import lint_workout  # noqa: E402
from story_notes import COMMENT_PROTOCOL_TITLE  # noqa: E402


class PlanPayloadError(ValueError):
    """Raised for malformed/missing inputs the CLI cannot recover from."""


def require(condition: bool, message: str) -> None:
    """Mirrors tools/tp_apply_order.py's require() -- fail loudly, at the
    point of the bad input, rather than with a buried traceback later."""
    if not condition:
        raise PlanPayloadError(message)


def _validate_date(value: Any, *, context: str) -> str:
    """Every session/note date must be a real YYYY-MM-DD string -- a
    malformed date silently sorts wrong (string comparison against
    plan_day_one) or breaks TP's workoutDay/noteDate fields outright.
    Raises PlanPayloadError naming the offending entry."""
    if not isinstance(value, str) or not value:
        raise PlanPayloadError(f"{context}: missing or non-string date ({value!r})")
    try:
        _date.fromisoformat(value)
    except ValueError as exc:
        raise PlanPayloadError(f"{context}: malformed date {value!r} ({exc})") from exc
    return value


# --------------------------------------------------------------------- io

def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PlanPayloadError(f"{path}: cannot read ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise PlanPayloadError(f"{path}: invalid JSON ({exc})") from exc


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_json_atomic(path: Path, data: Any) -> None:
    """Write via a temp name and rename over the target -- a reader (or a
    prior run's stale file) never observes a half-written payload."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def default_plan_day_one(athlete_dir: Path) -> str:
    """Read week1_monday (Day 1 of the plan) from plan_dates.yaml."""
    path = athlete_dir / "plan_dates.yaml"
    if not path.exists():
        raise PlanPayloadError(
            f"{path} not found -- pass --plan-day-one YYYY-MM-DD explicitly")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise PlanPayloadError(f"{path}: invalid YAML ({exc})") from exc
    day_one = data.get("week1_monday")
    if not day_one:
        raise PlanPayloadError(f"{path} has no week1_monday key")
    return str(day_one)


# ------------------------------------------------------- AE-8.4d suppression

def _is_zero_power_leaf(leaf: Mapping[str, Any]) -> bool:
    targets = leaf.get("targets") or [{}]
    primary = targets[0] if targets else {}
    return primary.get("minValue") == 0 and "maxValue" not in primary


def suppress_zero_power(structure: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """AE-8.4d -- a session whose ZWO is all-FreeRide/zero-power projects NO
    TP structure (structure: null, text card), never a flat zero-power
    graph. ``canonical_training_model.project_tp_structure`` already applies
    this suppression at projection time; this is a defensive re-check on
    the payload builder's own output so a regression upstream (or a
    manifest built by an older pipeline HEAD) can never ship the AE-8.4d
    defect through this tool. Examines EVERY step in EVERY block (not just
    each block's first step) -- suppresses only when every single step
    carries a flat ``{minValue: 0}`` (no maxValue, no honest content
    anywhere in the structure). A zero-power first step followed by honest
    later work (e.g. a warmup ramp into real intervals) must NOT be
    suppressed."""
    if not structure:
        return structure
    blocks = structure.get("structure") or []
    if not blocks:
        return structure
    all_steps = []
    for block in blocks:
        steps = block.get("steps") or []
        if not steps:
            return structure
        all_steps.extend(steps)
    if all_steps and all(_is_zero_power_leaf(step) for step in all_steps):
        return None
    return structure


# ------------------------------------------------------------ plan payload

def build_plan_payload(
    sessions: Sequence[Mapping[str, Any]], plan_day_one: str,
) -> tuple[list[dict], list[dict]]:
    """Returns (entries, excluded_sessions).

    Same-day ordering follows the manifest's ``order_on_day`` contract
    (generate_athlete_package.py's TP projection post-pass: 0 = strength
    first, everything else on that date keeps emission order after it).
    Sessions are sorted by (date, order_on_day); ties -- two sessions with
    the same date AND the same order_on_day -- keep their original manifest
    order (Python's sort is stable, and windowed sessions are collected in
    manifest order before sorting)."""
    excluded: list[dict] = []
    windowed: list[Mapping[str, Any]] = []
    for session in sessions:
        date = session.get("date")
        title = session.get("title")
        if not date:
            raise PlanPayloadError(f"session {title!r}: missing date")
        _validate_date(date, context=f"session {title!r}")
        if date < plan_day_one:
            excluded.append({"date": date, "title": title})
            continue
        windowed.append(session)

    windowed.sort(key=lambda s: (s.get("date"), s.get("order_on_day") or 0))

    entries: list[dict] = []
    for session in windowed:
        date = session.get("date")
        entry: dict[str, Any] = {
            "title": session.get("title"),
            "workoutTypeValueId": session.get("workout_type_value_id"),
            "workoutDay": f"{date}T00:00:00",
            "description": session.get("description") or "",
            "totalTimePlanned": session.get("total_time_planned"),
            "tssPlanned": session.get("tss_planned"),
            "structure": suppress_zero_power(session.get("structure")),
        }
        comment = session.get("pre_activity_comment")
        if comment:
            entry["coachComments"] = comment
        entries.append(entry)
    return entries, excluded


# ----------------------------------------------------------- notes payload

def build_notes_payload(
    native_notes: Sequence[Mapping[str, Any]], plan_day_one: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (entries, excluded_notes, redated_notes).

    Two notes landing on the same (date, title) -- including a W00
    protocol note re-dated onto plan_day_one colliding with an already
    in-window note of the same title -- is a hard error: TP has no
    disambiguation for two same-titled notes on the same day, and silently
    shipping both (or dropping one) is exactly the silent-divergence this
    tool exists to refuse."""
    entries: list[dict] = []
    excluded: list[dict] = []
    redated: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for note in native_notes:
        date = note.get("date")
        title = note.get("title")
        _validate_date(date, context=f"note {title!r}")
        if date < plan_day_one:
            if title == COMMENT_PROTOCOL_TITLE:
                key = (plan_day_one, title)
                if key in seen:
                    raise PlanPayloadError(
                        f"duplicate protocol-note title {title!r} on {plan_day_one} "
                        "after re-dating")
                seen.add(key)
                entries.append({
                    "title": title,
                    "noteDate": plan_day_one,
                    "description": note.get("text") or "",
                })
                redated.append({
                    "title": title, "original_date": date,
                    "redated_to": plan_day_one,
                })
            else:
                excluded.append({"date": date, "title": title})
            continue
        key = (date, title)
        if key in seen:
            raise PlanPayloadError(f"duplicate note title {title!r} on {date}")
        seen.add(key)
        entries.append({
            "title": title,
            "noteDate": date,
            "description": note.get("text") or "",
        })
    return entries, excluded, redated


# ------------------------------------------------------------------- lint

def _finding_key(finding: Mapping[str, Any]) -> tuple:
    return (finding.get("day"), finding.get("rule"), finding.get("title"))


def load_known_fails(path: Path) -> set[tuple]:
    """--allow-known-fails file: a JSON list of {day, rule, title} objects
    identifying documented, coach-accepted FAIL findings that should not
    block emission. Matched by exact (day, rule, title) -- the msg field is
    dynamic (carries computed numbers) so it is not part of the key."""
    data = _read_json(path)
    if not isinstance(data, list):
        raise PlanPayloadError(
            f"{path}: expected a JSON list of {{day, rule, title}} objects")
    keys: set[tuple] = set()
    for item in data:
        if not isinstance(item, Mapping):
            raise PlanPayloadError(f"{path}: entries must be objects")
        keys.add((item.get("day"), item.get("rule"), item.get("title")))
    return keys


def run_lint(
    plan_entries: Sequence[Mapping[str, Any]], race_date: str | None,
    known_fails: set[tuple] | None = None,
) -> dict:
    race = None
    if race_date:
        try:
            race = datetime.strptime(race_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise PlanPayloadError(f"bad race date {race_date!r}: {exc}") from exc

    findings: list[dict] = []
    for entry in plan_entries:
        findings.extend(lint_workout(entry, race))

    fails = [f for f in findings if f["severity"] == "FAIL"]
    known = known_fails or set()
    unresolved = [f for f in fails if _finding_key(f) not in known]

    return {
        "race_date": race_date,
        "workouts": len(plan_entries),
        "fail": len(fails),
        "warn": len(findings) - len(fails),
        "findings": findings,
        "allow_known_fails": sorted(
            f"{d}|{r}|{t}" for (d, r, t) in known),
        "unresolved_fails": unresolved,
    }


# --------------------------------------------------------------------- run

def build(
    athlete_dir: Path, out_dir: Path,
    plan_day_one: str | None = None,
    known_fails: set[tuple] | None = None,
) -> dict:
    """Build plan_payload.json, notes_payload.json, exclusions.json, and
    lint.json into out_dir. Returns the lint report dict."""
    athlete_dir = Path(athlete_dir)
    out_dir = Path(out_dir)

    tp_manifest_path = athlete_dir / "tp_manifest.json"
    fulfillment_manifest_path = athlete_dir / "fulfillment_manifest.json"
    if not tp_manifest_path.exists():
        raise PlanPayloadError(f"{tp_manifest_path} not found")
    if not fulfillment_manifest_path.exists():
        raise PlanPayloadError(f"{fulfillment_manifest_path} not found")

    tp_manifest = _read_json(tp_manifest_path)
    fulfillment_manifest = _read_json(fulfillment_manifest_path)

    if plan_day_one is None:
        plan_day_one = default_plan_day_one(athlete_dir)
    _validate_date(plan_day_one, context="plan_day_one")

    sessions = tp_manifest.get("sessions") or []
    plan_entries, excluded_sessions = build_plan_payload(sessions, plan_day_one)
    require(
        bool(plan_entries),
        f"zero sessions remain after W00 filtering (plan_day_one={plan_day_one!r}, "
        f"{len(sessions)} raw sessions, {len(excluded_sessions)} excluded) -- "
        "refusing to build an empty plan payload")

    native_notes = fulfillment_manifest.get("native_notes") or []
    note_entries, excluded_notes, redated_notes = build_notes_payload(
        native_notes, plan_day_one)

    race_date = (tp_manifest.get("race") or {}).get("date")
    lint_report = run_lint(plan_entries, race_date, known_fails)
    lint_report["plan_day_one"] = plan_day_one

    out_dir.mkdir(parents=True, exist_ok=True)
    # exclusions.json and lint.json are always written -- they are
    # diagnostics, not the payload itself, and the coach needs lint.json
    # to see WHY the gate blocked.
    _write_json(out_dir / "exclusions.json", {
        "plan_day_one": plan_day_one,
        "excluded_sessions": excluded_sessions,
        "excluded_notes": excluded_notes,
        "redated_notes": redated_notes,
    })
    _write_json(out_dir / "lint.json", lint_report)

    plan_payload_path = out_dir / "plan_payload.json"
    notes_payload_path = out_dir / "notes_payload.json"
    if lint_report["unresolved_fails"]:
        # Gate blocked: never leave a plan/notes payload behind -- neither
        # a fresh partial one nor a stale one from an earlier successful
        # run into the same --out-dir.
        plan_payload_path.unlink(missing_ok=True)
        notes_payload_path.unlink(missing_ok=True)
    else:
        _write_json_atomic(plan_payload_path, plan_entries)
        _write_json_atomic(notes_payload_path, note_entries)

    return lint_report


# --------------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--athlete-dir", required=True, type=Path,
                         help="athlete package dir (tp_manifest.json + fulfillment_manifest.json)")
    parser.add_argument("--out-dir", required=True, type=Path,
                         help="destination for plan_payload.json / notes_payload.json / exclusions.json / lint.json")
    parser.add_argument("--plan-day-one", default=None,
                         help="YYYY-MM-DD; defaults to plan_dates.yaml's week1_monday")
    parser.add_argument("--allow-known-fails", type=Path, default=None,
                         help="JSON file: list of {day, rule, title} objects for FAIL findings that are "
                              "documented known gaps and must not block emission")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        known_fails = (load_known_fails(args.allow_known_fails)
                        if args.allow_known_fails else set())
        report = build(
            args.athlete_dir, args.out_dir,
            plan_day_one=args.plan_day_one,
            known_fails=known_fails,
        )
    except PlanPayloadError as exc:
        print(f"build_tp_plan_payload: {exc}", file=sys.stderr)
        return 2

    unresolved = report["unresolved_fails"]
    print(f"build_tp_plan_payload: plan-day-one {report['plan_day_one']} -- "
          f"{report['workouts']} workouts, {report['fail']} FAIL "
          f"({len(unresolved)} unresolved), {report['warn']} WARN")
    if unresolved:
        for f in unresolved:
            print(f"  FAIL {f['day']} {f['rule']:14} {f['title']}: {f['msg']}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
