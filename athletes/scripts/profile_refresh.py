#!/usr/bin/env python3
"""
Weekly per-athlete profile refresh.

Spec: docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md, Part B,
revision 2. Folds a weekly_packet/v1 evidence packet (weekly_packet.py)
into `athletes/<id>/profile.yaml` -- but only a fixed whitelist of fields
(the window roll, add-only TP events, add-only life_calendar commitments).
Everything else the packet or caller supplies (self-review text, comments,
Drive workbook rows) goes to a private history file, never into the
tracked profile.

`refresh()` never writes anything. It reads profile.yaml and returns a
RefreshDiff describing what *would* change. The CLI's --write flag is the
only thing that touches disk, and it writes exactly three things: the
whitelist edits to profile.yaml (preserving key order and comments via
targeted text surgery, not a full re-dump), the history section appended
to the caller-supplied history file, and refresh_diff.json beside it.

A hold (FTP mismatch, race-date mismatch, too-soon-to-race, or a code-
excluded athlete) blocks the *entire* write for that run -- not just the
field in question. No network calls. No TP writes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from calculate_plan_dates import monday_on_or_after  # noqa: E402
from constants import get_athlete_dir  # noqa: E402
from validate_profile import validate_profile  # noqa: E402
import weekly_packet  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from coaching_loop.canonical_json import canonical_bytes  # noqa: E402
from coaching_loop.code_manifest import build_code_manifest  # noqa: E402
from coaching_loop.exclusions import (  # noqa: E402
    ExcludedAthleteError,
    NonCoercibleAthleteIdError,
    assert_not_excluded,
)


# ---------------------------------------------------------------------------
# RefreshDiff
# ---------------------------------------------------------------------------


@dataclass
class RefreshDiff:
    profile_changes: List[Dict[str, Any]]
    holds: List[Dict[str, Any]]
    history_section: str
    inputs_sha256: str
    window: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "profile_changes": self.profile_changes,
            "holds": self.holds,
            "history_section": self.history_section,
            "inputs_sha256": self.inputs_sha256,
            "window": self.window,
        }


# ---------------------------------------------------------------------------
# Small date helpers
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> date:
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    return datetime.strptime(text, "%Y-%m-%d").date()


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return _parse_date(value)


def _next_monday(today: date) -> date:
    dt = monday_on_or_after(datetime.combine(today, datetime.min.time()))
    return dt.date()


# ---------------------------------------------------------------------------
# Window roll (decision 1, revision 2)
# ---------------------------------------------------------------------------


def _rotate_week_types(week_types: List[str]) -> List[str]:
    """Roll a targetless coached-block rhythm forward one week: drop the
    first entry, append the pattern's own first entry back on -- which is
    exactly what sliding a one-week window across an infinitely repeating
    copy of `week_types` produces."""
    if not week_types:
        return []
    return list(week_types[1:]) + [week_types[0]]


def _compute_window(profile: Dict[str, Any], today: date) -> Dict[str, Any]:
    """{mode, start, end, weeks} per revision-2 decision 1. Race-bound
    when target_race.date is set; targetless otherwise."""
    target_race = profile.get("target_race") or {}
    race_date_str = target_race.get("date")
    effective_date = _next_monday(today)

    if race_date_str:
        race_date = _parse_date(race_date_str)
        race_week_monday = race_date - timedelta(days=race_date.weekday())
        weeks_to_race_week = max(
            (race_week_monday - effective_date).days // 7 + 1, 1)

        post_race_extra = 0
        old_horizon_str = (profile.get("fulfillment") or {}).get(
            "planning_horizon_end")
        race_week_sunday = race_week_monday + timedelta(days=6)
        if old_horizon_str:
            try:
                old_horizon = _parse_date(old_horizon_str)
                if old_horizon > race_week_sunday:
                    post_race_extra = 1
            except (ValueError, TypeError):
                pass

        weeks_purchased = weeks_to_race_week + post_race_extra
        planning_horizon_end = effective_date + timedelta(
            days=weeks_purchased * 7 - 1)
        return {
            "mode": "race_bound",
            "start": effective_date.isoformat(),
            "end": planning_horizon_end.isoformat(),
            "weeks": weeks_purchased,
        }

    planning_horizon_end = effective_date + timedelta(days=27)
    existing_week_types = (profile.get("coached_block") or {}).get(
        "week_types") or []
    weeks_purchased = len(existing_week_types) if existing_week_types else 4
    return {
        "mode": "targetless",
        "start": effective_date.isoformat(),
        "end": planning_horizon_end.isoformat(),
        "weeks": weeks_purchased,
    }


def _record_scalar_change(
    changes: List[Dict[str, Any]], container: Dict[str, Any], key: str,
    new_value: Any, path: str, source: str,
) -> None:
    old_value = container.get(key)
    if old_value != new_value:
        changes.append({
            "path": path, "old": old_value, "new": new_value, "source": source,
        })
    container[key] = new_value


def _apply_window(
    candidate: Dict[str, Any], window: Dict[str, Any],
    changes: List[Dict[str, Any]],
) -> None:
    fulfillment = candidate.setdefault("fulfillment", {})
    _record_scalar_change(
        changes, fulfillment, "effective_date", window["start"],
        "fulfillment.effective_date", "engine:window_roll")
    _record_scalar_change(
        changes, fulfillment, "planning_horizon_end", window["end"],
        "fulfillment.planning_horizon_end", "engine:window_roll")
    _record_scalar_change(
        changes, fulfillment, "weeks_purchased", window["weeks"],
        "fulfillment.weeks_purchased", "engine:window_roll")

    if window["mode"] == "targetless":
        coached_block = candidate.setdefault("coached_block", {})
        old_week_types = coached_block.get("week_types") or []
        new_week_types = _rotate_week_types(old_week_types)
        if new_week_types and new_week_types != old_week_types:
            changes.append({
                "path": "coached_block.week_types",
                "old": old_week_types,
                "new": new_week_types,
                "source": "engine:window_roll",
            })
        if new_week_types:
            coached_block["week_types"] = new_week_types


# ---------------------------------------------------------------------------
# Holds (decision 2, revision 2)
# ---------------------------------------------------------------------------


def _check_exclusion_hold(packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tp_id = packet.get("tp_athlete_id")
    try:
        assert_not_excluded(tp_id, layer="profile_refresh")
    except ExcludedAthleteError as exc:
        return {
            "code": "excluded_athlete",
            "message": str(exc),
            "sources": ["packet.tp_athlete_id"],
        }
    except NonCoercibleAthleteIdError:
        # Not an int-coercible id -- nothing to check it against.
        return None
    return None


def _check_ftp_hold(
    packet: Dict[str, Any], profile: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    packet_ftp = (packet.get("settings") or {}).get("ftp_watts")
    profile_ftp = (profile.get("fitness_markers") or {}).get("ftp_watts")
    if packet_ftp is None or profile_ftp is None or packet_ftp == profile_ftp:
        return None
    return {
        "code": "ftp_mismatch",
        "message": (
            f"packet FTP {packet_ftp}W differs from profile FTP "
            f"{profile_ftp}W"),
        "sources": [
            "packet.settings.ftp_watts", "profile.fitness_markers.ftp_watts"],
    }


def _find_a_race_event(packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for event in packet.get("events") or []:
        if str(event.get("priority") or "").upper() == "A":
            return event
    return None


def _check_race_date_hold(
    packet: Dict[str, Any], profile: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    profile_date = (profile.get("target_race") or {}).get("date")
    if not profile_date:
        return None
    tp_event = _find_a_race_event(packet)
    if not tp_event or not tp_event.get("date"):
        return None
    if tp_event["date"] == profile_date:
        return None
    return {
        "code": "race_date_mismatch",
        "message": (
            f"TP race date {tp_event['date']} differs from profile "
            f"target_race.date {profile_date}"),
        "sources": [
            "packet.events[priority=A].date", "profile.target_race.date"],
    }


def _check_race_too_soon_hold(
    profile: Dict[str, Any], today: date,
) -> Optional[Dict[str, Any]]:
    race_date_str = (profile.get("target_race") or {}).get("date")
    if not race_date_str:
        return None
    days_to_race = (_parse_date(race_date_str) - today).days
    if days_to_race >= 14:
        return None
    return {
        "code": "race_too_soon",
        "message": f"{days_to_race} day(s) to race (need at least 14)",
        "sources": ["profile.target_race.date"],
    }


# ---------------------------------------------------------------------------
# Add-only writes: a_events/b_events, life_calendar.commitments
# ---------------------------------------------------------------------------


def _apply_events(
    candidate: Dict[str, Any], packet: Dict[str, Any],
    changes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Add-only merge of packet TP events into a_events/b_events. Returns
    a report list (one entry per packet event) for the 'Events seen'
    history section."""
    a_events = candidate.setdefault("a_events", [])
    b_events = candidate.setdefault("b_events", [])
    existing_keys = {
        (str(e.get("date")), str(e.get("name")).strip().lower())
        for e in (a_events + b_events)
    }

    seen: List[Dict[str, Any]] = []
    for event in packet.get("events") or []:
        date_val = event.get("date")
        name_val = event.get("name")
        if not date_val or not name_val:
            continue
        key = (str(date_val), str(name_val).strip().lower())
        if key in existing_keys:
            seen.append({"event": event, "added": False, "target": None})
            continue

        priority = event.get("priority")
        flagged = not priority
        if str(priority or "").upper() == "A":
            target_list, target_name = a_events, "a_events"
        else:
            target_list, target_name = b_events, "b_events"

        new_entry: Dict[str, Any] = {
            "name": name_val, "date": date_val, "priority": priority or "B",
        }
        if flagged:
            new_entry["flagged"] = True

        target_list.append(new_entry)
        existing_keys.add(key)
        changes.append({
            "path": f"{target_name}[]",
            "old": None,
            "new": new_entry,
            "source": "packet:events",
        })
        seen.append({"event": event, "added": True, "target": target_name})

    return seen


def _apply_commitments(
    candidate: Dict[str, Any], commitments: Optional[List[Dict[str, Any]]],
    changes: List[Dict[str, Any]],
) -> None:
    if not commitments:
        return
    life_calendar = candidate.setdefault("life_calendar", {})
    existing = life_calendar.setdefault("commitments", [])
    existing_keys = {
        (str(c.get("date")), str(c.get("title")).strip().lower())
        for c in existing
    }
    for commitment in commitments:
        date_val = commitment.get("date")
        title_val = commitment.get("title")
        if not date_val or not title_val:
            continue
        key = (str(date_val), str(title_val).strip().lower())
        if key in existing_keys:
            continue
        existing.append(commitment)
        existing_keys.add(key)
        changes.append({
            "path": "life_calendar.commitments[]",
            "old": None,
            "new": commitment,
            "source": "caller:commitments",
        })


# ---------------------------------------------------------------------------
# History markdown
# ---------------------------------------------------------------------------


def _render_history_markdown(
    *, today: date, window: Dict[str, Any], changes: List[Dict[str, Any]],
    holds: List[Dict[str, Any]], packet: Dict[str, Any],
    events_seen: List[Dict[str, Any]], load_6wk_data: Dict[str, Any],
    workbook_rows: Optional[List[Dict[str, Any]]],
) -> str:
    lines: List[str] = []
    lines.append(f"## Weekly Refresh — {today.isoformat()}")
    lines.append("")

    lines.append("### Window")
    lines.append(f"- mode: {window['mode']}")
    lines.append(f"- start: {window['start']}")
    lines.append(f"- end: {window['end']}")
    lines.append(f"- weeks: {window['weeks']}")
    lines.append("")

    lines.append("### Profile changes")
    if changes:
        for change in changes:
            lines.append(
                f"- {change['path']}: {change['old']!r} -> "
                f"{change['new']!r} (source: {change['source']})")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("### Holds")
    if holds:
        for hold in holds:
            sources = ", ".join(hold.get("sources") or [])
            lines.append(f"- {hold['code']}: {hold['message']} (sources: {sources})")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("### Self-review and comments")
    any_entries = False
    for note in sorted(packet.get("notes") or [], key=lambda n: n.get("date") or ""):
        any_entries = True
        lines.append(
            f"- [note {note.get('note_id')}, {note.get('date')}] "
            f"{note.get('title', '')}")
        if note.get("description"):
            lines.append(f"  {note['description']}")
        for comment in note.get("comments") or []:
            lines.append(
                f"  - comment [id={comment.get('id')}, {comment.get('date')}, "
                f"author={comment.get('author')}]: "
                f"\"{comment.get('text', '')}\"")
    if workbook_rows:
        any_entries = True
        for i, row in enumerate(workbook_rows):
            row_id = row.get("row_id", i)
            lines.append(f"- [workbook row {row_id}] {json.dumps(row, sort_keys=True)}")
    if not any_entries:
        lines.append("- none")
    lines.append("")

    lines.append("### Events seen")
    if events_seen:
        for item in events_seen:
            event = item["event"]
            status = f"added -> {item['target']}" if item["added"] else "existing"
            lines.append(
                f"- {event.get('name')} ({event.get('priority')}) "
                f"{event.get('date')} [{status}]")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("### Load (6-week table)")
    weeks = load_6wk_data.get("weeks") or []
    if weeks:
        lines.append("| week start | hours | tss actual | tss planned |")
        lines.append("|---|---|---|---|")
        for week in weeks:
            lines.append(
                f"| {week['week_start']} | {week['hours_actual']} | "
                f"{week['tss_actual']} | {week['tss_planned']} |")
    lines.append(f"- ctl_latest: {load_6wk_data.get('ctl_latest')}")
    lines.append("")

    lines.append("### Skipped")
    lines.append("- fitness_markers.ftp_watts (coach-owned; compared for a hold, never written)")
    lines.append("- fitness_markers.weight_kg (not in the whitelist)")
    lines.append("- self-review and comment text (recorded above only)")
    lines.append("- Drive workbook rows (context only)")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------


def refresh(
    athlete_dir: Any,
    packet: Dict[str, Any],
    *,
    workbook_rows: Optional[List[Dict[str, Any]]] = None,
    commitments: Optional[List[Dict[str, Any]]] = None,
    rules_text: Optional[str] = None,
    today: Any,
    repo_root: Any,
) -> RefreshDiff:
    """Compute (never write) the weekly refresh for one athlete.

    Reads athlete_dir/profile.yaml. Returns a RefreshDiff describing the
    whitelist edits that would be made, any holds, and the history section
    for the caller (usually the CLI's --write path) to persist.
    """
    weekly_packet.validate(packet)

    athlete_dir = Path(athlete_dir)
    profile_path = athlete_dir / "profile.yaml"
    original_text = profile_path.read_text()
    profile = yaml.safe_load(original_text) or {}

    today_date = _coerce_date(today)

    holds: List[Dict[str, Any]] = []
    for hold in (
        _check_exclusion_hold(packet),
        _check_ftp_hold(packet, profile),
        _check_race_date_hold(packet, profile),
        _check_race_too_soon_hold(profile, today_date),
    ):
        if hold:
            holds.append(hold)

    window = _compute_window(profile, today_date)

    candidate = copy.deepcopy(profile)
    changes: List[Dict[str, Any]] = []
    _apply_window(candidate, window, changes)
    events_seen = _apply_events(candidate, packet, changes)
    _apply_commitments(candidate, commitments, changes)

    is_valid, errors, _warnings = validate_profile(candidate)
    if not is_valid:
        holds.append({
            "code": "validate_profile_failed",
            "message": "; ".join(errors),
            "sources": ["candidate_profile"],
        })

    if holds:
        changes = []  # a hold blocks the entire write, not just one field

    load_6wk_data = weekly_packet.load_6wk(packet)

    code_manifest = build_code_manifest(repo_root)
    hash_payload = {
        "profile_as_written": candidate,
        "rules_text": rules_text,
        "decision_fields": weekly_packet.decision_fields(packet),
        "workbook_rows": workbook_rows,
        "commitments": commitments,
        "code_manifest": code_manifest,
    }
    inputs_sha256 = hashlib.sha256(canonical_bytes(hash_payload)).hexdigest()

    history_section = _render_history_markdown(
        today=today_date, window=window, changes=changes, holds=holds,
        packet=packet, events_seen=events_seen, load_6wk_data=load_6wk_data,
        workbook_rows=workbook_rows,
    )

    return RefreshDiff(
        profile_changes=changes,
        holds=holds,
        history_section=history_section,
        inputs_sha256=inputs_sha256,
        window=window,
    )


# ---------------------------------------------------------------------------
# YAML text surgery -- targeted edits that preserve key order, comments,
# and formatting for every line not being changed. Used only by the
# --write path; refresh() itself never calls this.
# ---------------------------------------------------------------------------


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_end(lines: List[str], start_idx: int, own_indent: int) -> int:
    """Index of the first line after `start_idx` that is not part of the
    value block started there (blank lines and block-sequence items at the
    same indent as the key are part of the block; a plain key at the same
    indent, or any line at a shallower indent, ends it)."""
    n = len(lines)
    dash_prefix = " " * own_indent + "- "
    for i in range(start_idx + 1, n):
        line = lines[i]
        if line.strip() == "":
            continue
        current_indent = _line_indent(line)
        if current_indent < own_indent:
            return i
        if current_indent == own_indent:
            if line.startswith(dash_prefix):
                continue
            return i
        # deeper indent: still nested under this key
    return n


def _locate_key(
    lines: List[str], path: List[str], start: int = 0,
    end: Optional[int] = None, indent: int = 0,
) -> "tuple[int, int]":
    if end is None:
        end = len(lines)
    key = path[0]
    pattern = re.compile(rf"^{' ' * indent}{re.escape(key)}:(\s|$)")
    key_idx = None
    for i in range(start, end):
        if pattern.match(lines[i]):
            key_idx = i
            break
    if key_idx is None:
        raise KeyError(".".join(path))
    block_end = _block_end(lines, key_idx, indent)
    if len(path) == 1:
        return key_idx, block_end
    return _locate_key(lines, path[1:], key_idx + 1, block_end, indent + 2)


def _format_scalar_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    if _DATE_RE.match(text):
        return f"'{text}'"
    needs_quote = (
        text == "" or text != text.strip()
        or text.lower() in ("true", "false", "null", "~", "yes", "no")
        or any(ch in text for ch in ':#{}[]&*!|>%@`"\n')
        or text.startswith("'") or text.startswith("-")
    )
    if needs_quote:
        return "'" + text.replace("'", "''") + "'"
    return text


def _set_scalar(lines: List[str], path: List[str], new_value: Any) -> None:
    key_idx, _block_end_idx = _locate_key(lines, path)
    line = lines[key_idx]
    indent = _line_indent(line)
    newline = "\n" if line.endswith("\n") else ""
    lines[key_idx] = (
        f"{' ' * indent}{path[-1]}: {_format_scalar_value(new_value)}{newline}")


def _set_scalar_list(lines: List[str], path: List[str], items: List[str]) -> None:
    key_idx, block_end = _locate_key(lines, path)
    line = lines[key_idx]
    indent = _line_indent(line)
    newline = "\n" if line.endswith("\n") else "\n"
    new_lines = [f"{' ' * indent}{path[-1]}:{newline}"]
    for item in items:
        new_lines.append(f"{' ' * indent}- {item}{newline}")
    lines[key_idx:block_end] = new_lines


def _format_block_mapping_item(
    item: Dict[str, Any], indent: int, newline: str,
) -> List[str]:
    out: List[str] = []
    for idx, (key, value) in enumerate(item.items()):
        value_str = _format_scalar_value(value)
        if idx == 0:
            prefix = f"{' ' * indent}- "
        else:
            prefix = " " * (indent + 2)
        out.append(f"{prefix}{key}: {value_str}{newline}")
    return out


def _append_block_list_items(
    lines: List[str], path: List[str], new_items: List[Dict[str, Any]],
) -> None:
    key_idx, block_end = _locate_key(lines, path)
    line = lines[key_idx]
    indent = _line_indent(line)
    newline = "\n" if line.endswith("\n") else "\n"
    stripped = line.strip()
    after_colon = stripped.split(":", 1)[1].strip() if ":" in stripped else ""

    rendered: List[str] = []
    for item in new_items:
        rendered.extend(_format_block_mapping_item(item, indent, newline))

    if after_colon == "[]":
        lines[key_idx:key_idx + 1] = [f"{' ' * indent}{path[-1]}:{newline}"] + rendered
    elif after_colon == "":
        lines[block_end:block_end] = rendered
    else:
        raise ValueError(
            f"cannot append to flow-style list at {'.'.join(path)!r}: {stripped!r}")


def apply_changes_to_yaml_text(
    original_text: str, changes: List[Dict[str, Any]],
) -> str:
    """Apply `changes` (a RefreshDiff.profile_changes list) to the raw
    profile.yaml text, touching only the lines that change. An empty
    `changes` list returns `original_text` unmodified -- byte-identical."""
    if not changes:
        return original_text

    lines = original_text.splitlines(keepends=True)
    append_groups: Dict["tuple[str, ...]", List[Dict[str, Any]]] = {}

    for change in changes:
        path = change["path"]
        if path.endswith("[]"):
            list_path = tuple(path[:-2].split("."))
            append_groups.setdefault(list_path, []).append(change["new"])
        elif path == "coached_block.week_types":
            _set_scalar_list(
                lines, ["coached_block", "week_types"],
                [str(item) for item in change["new"]])
        else:
            _set_scalar(lines, path.split("."), change["new"])

    for list_path, items in append_groups.items():
        _append_block_list_items(lines, list(list_path), items)

    return "".join(lines)


def write_profile_changes(athlete_dir: Any, changes: List[Dict[str, Any]]) -> None:
    """Persist `changes` to athlete_dir/profile.yaml via text surgery.
    A no-op (no read, no write) when `changes` is empty."""
    if not changes:
        return
    profile_path = Path(athlete_dir) / "profile.yaml"
    original_text = profile_path.read_text()
    new_text = apply_changes_to_yaml_text(original_text, changes)
    if new_text != original_text:
        profile_path.write_text(new_text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Weekly per-athlete profile refresh (whitelist-only writes).")
    parser.add_argument("athlete_id")
    parser.add_argument("--packet", required=True, help="Path to a weekly_packet/v1 JSON file")
    parser.add_argument("--history", required=True, help="Path to the private coaching_history.md file")
    parser.add_argument("--today", required=True, help="YYYY-MM-DD")
    parser.add_argument("--workbook-rows", default=None, help="Path to a JSON file of Drive workbook rows")
    parser.add_argument("--commitments", default=None, help="Path to a JSON file of life_calendar commitments")
    parser.add_argument("--rules", default=None, help="Path to a per-athlete rules YAML (hashed, not applied here)")
    parser.add_argument(
        "--write", action="store_true",
        help="Persist profile.yaml, the history file, and refresh_diff.json. "
             "Without it, nothing is written.")
    args = parser.parse_args(argv)

    athlete_dir = get_athlete_dir(args.athlete_id)

    with open(args.packet) as fh:
        packet = json.load(fh)

    workbook_rows = None
    if args.workbook_rows:
        with open(args.workbook_rows) as fh:
            workbook_rows = json.load(fh)

    commitments = None
    if args.commitments:
        with open(args.commitments) as fh:
            commitments = json.load(fh)

    rules_text = None
    if args.rules:
        rules_text = Path(args.rules).read_text()

    diff = refresh(
        athlete_dir, packet,
        workbook_rows=workbook_rows, commitments=commitments,
        rules_text=rules_text, today=args.today, repo_root=_REPO_ROOT,
    )

    print(f"Window: {diff.window}")
    print(f"Holds: {len(diff.holds)}")
    print(f"Profile changes: {len(diff.profile_changes)}")
    for hold in diff.holds:
        print(f"  HOLD {hold['code']}: {hold['message']}")

    if not args.write:
        print("(--write not given; nothing written)")
        return 0

    write_profile_changes(athlete_dir, diff.profile_changes)

    history_path = Path(args.history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "a") as fh:
        fh.write(diff.history_section)
        fh.write("\n")

    diff_path = history_path.parent / "refresh_diff.json"
    with open(diff_path, "w") as fh:
        json.dump(diff.as_dict(), fh, indent=2, default=str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
