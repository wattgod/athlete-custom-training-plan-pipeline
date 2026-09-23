"""Small, source-traced race execution cues for matched race IDs.

The course facts remain in race_intel.json. These are coaching inferences from
those facts, kept separate so a race-DB sync cannot present them as raw data.
"""

import json
from datetime import date
from html import escape
from pathlib import Path

_CUES_PATH = Path(__file__).resolve().parent.parent / "config" / "race_execution_cues.json"


def cues_for(race_id: str) -> dict:
    if not race_id:
        return {}
    try:
        return json.loads(_CUES_PATH.read_text()).get(race_id, {})
    except (OSError, json.JSONDecodeError):
        return {}


def race_card_cues(race_id: str) -> str:
    choices = cues_for(race_id).get("race_choices") or []
    if not choices:
        return ""
    return "\nCOURSE CHOICES:\n" + "\n".join(f"- {choice}" for choice in choices) + "\n"


def guide_cues(race_id: str) -> str:
    cues = cues_for(race_id)
    if not cues:
        return ""
    dimensions = cues.get("training_dimensions") or []
    choices = cues.get("race_choices") or []
    if not dimensions and not choices:
        return ""
    return (
        "<h4>Practice in training</h4><ul>"
        + "".join(f"<li>{escape(item)}</li>" for item in dimensions)
        + "</ul><h4>Race-day decisions</h4><ul>"
        + "".join(f"<li>{escape(item)}</li>" for item in choices)
        + "</ul>"
    )


def long_ride_dimension_cue(events: list, session_date: str, role: str,
                            week_type: str) -> str:
    """AE-1.7/AE-3.7: one sourced terrain/position objective on prep long rides."""
    if role != "long_ride" or week_type != "load":
        return ""
    try:
        ride_day = date.fromisoformat(session_date)
    except (TypeError, ValueError):
        return ""
    upcoming = []
    for event in events or []:
        if str(event.get("priority") or "").upper() != "A":
            continue
        try:
            days = (date.fromisoformat(str(event.get("date"))) - ride_day).days
        except (TypeError, ValueError):
            continue
        if 1 <= days <= 56 and cues_for(str(event.get("race_id") or "")):
            upcoming.append((days, event))
    if not upcoming:
        return ""
    days, event = min(upcoming, key=lambda item: item[0])
    dimensions = cues_for(event["race_id"]).get("training_dimensions") or []
    if not dimensions:
        return ""
    index = ((56 - days) // 7) % len(dimensions)
    repeat = "Again: " if (56 - days) // 7 >= len(dimensions) else ""
    return f"RACE PRACTICE:\n{event['name']}: {repeat}{dimensions[index]}"
