#!/usr/bin/env python3
"""
weekly_packet/v1 — schema, validation, and derived reads for the weekly
per-athlete evidence packet.

Spec: docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md, Part B,
revision 2, decision 5. The packet is produced by a separate read-only
browser script (`tools/tp_weekly_packet.js`, out of scope here) and handed
to `profile_refresh.refresh()` as a plain dict. This module owns:

- the documented shape (`PACKET_SCHEMA` / `validate`)
- `load_6wk`: per-ISO-week demonstrated hours/TSS for the last 6 complete
  weeks, plus the latest CTL reading
- `decision_fields`: the subset of the packet that can change a coaching
  decision, with ids and timestamps stripped, for hashing (C1-style
  canonical hash discipline; see coaching_loop/canonical_json.py)

No network calls. No TP writes. This module only reads the dict it is
given.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

SCHEMA = "weekly_packet/v1"

# Top-level sections every weekly_packet/v1 packet must carry.
REQUIRED_TOP_LEVEL = (
    "schema",
    "athlete_key",
    "tp_athlete_id",
    "as_of",
    "settings",
    "events",
    "pmc_daily",
    "workouts",
    "notes",
    "source_manifest",
)

REQUIRED_SETTINGS_FIELDS = ("ftp_watts", "weight_kg")
REQUIRED_SOURCE_MANIFEST_FIELDS = ("captured_at", "endpoints")

# Per-item shapes, documented for readers; validate() only checks the
# container-level contract (present, right container type), not that every
# item has every key -- upstream fields can legitimately be null/missing
# for an athlete with a thin TP history.
EVENT_FIELDS = ("id", "date", "name", "priority")
PMC_DAY_FIELDS = ("date", "ctl", "atl", "tsb", "tss_actual", "tss_planned")
WORKOUT_FIELDS = (
    "workout_id", "date", "title", "type_id",
    "dur_planned_h", "dur_actual_h", "tss_planned", "tss_actual",
)
NOTE_FIELDS = ("note_id", "date", "title", "description", "comments")
COMMENT_FIELDS = ("id", "date", "author", "text")

LIST_SECTIONS = ("events", "pmc_daily", "workouts", "notes")


class WeeklyPacketError(ValueError):
    """Raised by validate() when a packet does not meet the weekly_packet/v1 contract."""


def _parse_date(value: Any) -> date:
    """Parse a YYYY-MM-DD (optionally with a time component) into a date."""
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    return datetime.strptime(text, "%Y-%m-%d").date()


def validate(packet: Dict[str, Any]) -> None:
    """Raise WeeklyPacketError if `packet` does not meet weekly_packet/v1.

    Collects every problem before raising so a single failed packet run
    tells the caller everything that is wrong, not just the first thing.
    """
    if not isinstance(packet, dict):
        raise WeeklyPacketError(f"packet must be a dict, got {type(packet).__name__}")

    errors: List[str] = []

    schema = packet.get("schema")
    if schema != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, got {schema!r}")

    for field in ("athlete_key", "tp_athlete_id", "as_of"):
        if not packet.get(field) and packet.get(field) != 0:
            errors.append(f"missing required field: {field}")

    settings = packet.get("settings")
    if not isinstance(settings, dict):
        errors.append("missing required section: settings")
    else:
        for field in REQUIRED_SETTINGS_FIELDS:
            if field not in settings:
                errors.append(f"settings missing required field: {field}")

    for section in LIST_SECTIONS:
        value = packet.get(section, None)
        if not isinstance(value, list):
            errors.append(f"missing required section (must be a list): {section}")

    source_manifest = packet.get("source_manifest")
    if not isinstance(source_manifest, dict):
        errors.append("missing required section: source_manifest")
    else:
        for field in REQUIRED_SOURCE_MANIFEST_FIELDS:
            if field not in source_manifest:
                errors.append(f"source_manifest missing required field: {field}")

    if packet.get("as_of"):
        try:
            _parse_date(packet["as_of"])
        except (ValueError, TypeError):
            errors.append(f"as_of is not a valid date: {packet.get('as_of')!r}")

    if errors:
        raise WeeklyPacketError(
            f"invalid weekly_packet/v1 packet ({len(errors)} problem"
            f"{'s' if len(errors) != 1 else ''}): " + "; ".join(errors)
        )


def _monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def load_6wk(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Per-ISO-week {hours_actual, tss_actual, tss_planned} for the last 6
    complete weeks as of packet['as_of'], oldest first, plus ctl_latest
    from the most recent pmc_daily row.

    A "complete" week is one that ended before the Monday of the week
    containing `as_of` -- the current, still-in-progress week is never
    included.
    """
    as_of = _parse_date(packet["as_of"])
    current_monday = _monday_of(as_of)
    last_complete_monday = current_monday - timedelta(days=7)

    weeks: List[Dict[str, Any]] = []
    for i in range(6):
        week_start = last_complete_monday - timedelta(weeks=(5 - i))
        week_end = week_start + timedelta(days=6)
        hours_actual = 0.0
        tss_actual = 0.0
        tss_planned = 0.0
        for workout in packet.get("workouts") or []:
            workout_date = workout.get("date")
            if not workout_date:
                continue
            try:
                d = _parse_date(workout_date)
            except (ValueError, TypeError):
                continue
            if week_start <= d <= week_end:
                hours_actual += float(workout.get("dur_actual_h") or 0)
                tss_actual += float(workout.get("tss_actual") or 0)
                tss_planned += float(workout.get("tss_planned") or 0)
        weeks.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "hours_actual": round(hours_actual, 2),
            "tss_actual": round(tss_actual, 1),
            "tss_planned": round(tss_planned, 1),
        })

    ctl_latest: Optional[float] = None
    pmc_daily = packet.get("pmc_daily") or []
    dated_rows = [row for row in pmc_daily if row.get("date")]
    if dated_rows:
        latest_row = max(dated_rows, key=lambda row: row["date"])
        ctl_latest = latest_row.get("ctl")

    return {"weeks": weeks, "ctl_latest": ctl_latest}


def decision_fields(packet: Dict[str, Any]) -> Dict[str, Any]:
    """The subset of `packet` that can change a plan decision, ids and
    timestamps stripped -- this is what profile_refresh hashes (with
    workbook_rows / commitments / code_manifest folded in separately).

    ftp_watts and weight_kg from settings; events with only date/name/
    priority (id dropped); note comment texts (author/id/date dropped),
    ordered by (note date, note title, comment order) so two packets with
    the same substance but different ids/timestamps/review windows hash
    identically.
    """
    settings = packet.get("settings") or {}

    events = sorted(
        (
            {
                "date": event.get("date"),
                "name": event.get("name"),
                "priority": event.get("priority"),
            }
            for event in (packet.get("events") or [])
        ),
        key=lambda e: (e.get("date") or "", e.get("name") or ""),
    )

    notes_sorted = sorted(
        (packet.get("notes") or []),
        key=lambda n: (n.get("date") or "", n.get("title") or ""),
    )
    note_comment_texts: List[str] = []
    for note in notes_sorted:
        for comment in note.get("comments") or []:
            note_comment_texts.append(comment.get("text", ""))

    return {
        "ftp_watts": settings.get("ftp_watts"),
        "weight_kg": settings.get("weight_kg"),
        "events": events,
        "note_comment_texts": note_comment_texts,
    }
