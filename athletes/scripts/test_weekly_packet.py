"""Tests for weekly_packet: schema validation, load_6wk, decision_fields."""

import copy

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # collect from the repo root too

from weekly_packet import (
    SCHEMA,
    WeeklyPacketError,
    decision_fields,
    load_6wk,
    validate,
)


def _packet(**overrides):
    packet = {
        "schema": SCHEMA,
        "athlete_key": "test-athlete",
        "tp_athlete_id": 1234567,
        "as_of": "2026-09-18",
        "settings": {"ftp_watts": 270, "weight_kg": 79.0},
        "events": [
            {"id": "e1", "date": "2026-11-07", "name": "Test Race", "priority": "A"},
        ],
        "pmc_daily": [
            {"date": "2026-09-16", "ctl": 58.0, "atl": 60.0, "tsb": -2.0,
             "tss_actual": 80, "tss_planned": 75},
            {"date": "2026-09-17", "ctl": 58.4, "atl": 61.0, "tsb": -2.6,
             "tss_actual": 70, "tss_planned": 70},
        ],
        "workouts": [
            {"workout_id": "w1", "date": "2026-08-24", "title": "Endurance",
             "type_id": 1, "dur_planned_h": 2.0, "dur_actual_h": 2.1,
             "tss_planned": 100, "tss_actual": 105},
        ],
        "notes": [
            {"note_id": "n1", "date": "2026-09-15", "title": "Self review",
             "description": "Felt good this week.",
             "comments": [
                 {"id": "c1", "date": "2026-09-16", "author": "Coach",
                  "text": "Keep it up."},
             ]},
        ],
        "source_manifest": {
            "captured_at": "2026-09-18T12:00:00Z",
            "endpoints": ["settings", "events", "pmc", "workouts", "notes"],
        },
    }
    packet.update(overrides)
    return packet


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


def test_validate_accepts_a_complete_packet():
    validate(_packet())  # must not raise


def test_validate_raises_on_missing_sections():
    packet = _packet()
    del packet["settings"]
    del packet["pmc_daily"]
    with pytest.raises(WeeklyPacketError) as exc_info:
        validate(packet)
    message = str(exc_info.value)
    assert "settings" in message
    assert "pmc_daily" in message


def test_validate_raises_on_wrong_schema():
    packet = _packet(schema="weekly_packet/v2")
    with pytest.raises(WeeklyPacketError):
        validate(packet)


def test_validate_raises_on_missing_settings_field():
    packet = _packet()
    del packet["settings"]["weight_kg"]
    with pytest.raises(WeeklyPacketError) as exc_info:
        validate(packet)
    assert "weight_kg" in str(exc_info.value)


def test_validate_raises_on_missing_source_manifest_field():
    packet = _packet()
    del packet["source_manifest"]["endpoints"]
    with pytest.raises(WeeklyPacketError) as exc_info:
        validate(packet)
    assert "endpoints" in str(exc_info.value)


def test_validate_raises_when_list_section_is_not_a_list():
    packet = _packet(events="not-a-list")
    with pytest.raises(WeeklyPacketError):
        validate(packet)


# ---------------------------------------------------------------------------
# load_6wk()
# ---------------------------------------------------------------------------


def test_load_6wk_returns_six_complete_weeks_and_excludes_current_week():
    packet = _packet(as_of="2026-09-18")  # Friday, in the week of 2026-09-14
    # Last complete week ends the Sunday before the current week's Monday:
    # current Monday = 2026-09-14, last complete week = 2026-09-07..09-13.
    packet["workouts"] = [
        {"workout_id": "in_current_week", "date": "2026-09-16",
         "dur_actual_h": 99, "tss_actual": 999, "tss_planned": 999},
        {"workout_id": "in_last_complete_week", "date": "2026-09-10",
         "dur_actual_h": 2.0, "tss_actual": 100, "tss_planned": 90},
    ]
    result = load_6wk(packet)
    assert len(result["weeks"]) == 6
    last_week = result["weeks"][-1]
    assert last_week["week_start"] == "2026-09-07"
    assert last_week["week_end"] == "2026-09-13"
    assert last_week["hours_actual"] == 2.0
    assert last_week["tss_actual"] == 100
    assert last_week["tss_planned"] == 90
    # The in-progress week's workout must not leak into any bucket.
    total_hours = sum(w["hours_actual"] for w in result["weeks"])
    assert total_hours == 2.0


def test_load_6wk_sums_multiple_workouts_in_the_same_week():
    packet = _packet(as_of="2026-09-18")
    packet["workouts"] = [
        {"date": "2026-09-08", "dur_actual_h": 1.0, "tss_actual": 50, "tss_planned": 50},
        {"date": "2026-09-10", "dur_actual_h": 2.0, "tss_actual": 100, "tss_planned": 90},
    ]
    result = load_6wk(packet)
    last_week = result["weeks"][-1]
    assert last_week["hours_actual"] == 3.0
    assert last_week["tss_actual"] == 150


def test_load_6wk_ctl_latest_is_the_most_recent_pmc_row():
    packet = _packet()
    packet["pmc_daily"] = [
        {"date": "2026-09-16", "ctl": 58.0},
        {"date": "2026-09-17", "ctl": 58.4},
        {"date": "2026-09-15", "ctl": 57.5},
    ]
    result = load_6wk(packet)
    assert result["ctl_latest"] == 58.4


def test_load_6wk_ctl_latest_none_when_no_pmc_rows():
    packet = _packet(pmc_daily=[])
    result = load_6wk(packet)
    assert result["ctl_latest"] is None


# ---------------------------------------------------------------------------
# decision_fields()
# ---------------------------------------------------------------------------


def test_decision_fields_strips_ids_and_timestamps():
    packet = _packet()
    fields = decision_fields(packet)
    assert fields["ftp_watts"] == 270
    assert fields["weight_kg"] == 79.0
    assert fields["events"] == [
        {"date": "2026-11-07", "name": "Test Race", "priority": "A"}]
    assert fields["note_comment_texts"] == ["Keep it up."]
    # No raw ids, dates, or author fields anywhere in the result.
    blob = str(fields)
    assert "c1" not in blob
    assert "n1" not in blob
    assert "2026-09-16" not in blob
    assert "Coach" not in blob


def test_decision_fields_stable_across_ids_timestamps_and_review_window():
    packet_a = _packet(
        as_of="2026-09-18",
        events=[{"id": "e1", "date": "2026-11-07", "name": "Test Race", "priority": "A"}],
        notes=[{
            "note_id": "n1", "date": "2026-09-15", "title": "Self review",
            "description": "Felt good.",
            "comments": [{"id": "c1", "date": "2026-09-16", "author": "Coach",
                          "text": "Keep it up."}],
        }],
    )
    packet_b = _packet(
        as_of="2026-09-25",  # different review window
        events=[{"id": "e99-different", "date": "2026-11-07", "name": "Test Race",
                  "priority": "A"}],
        notes=[{
            "note_id": "n77-different", "date": "2026-09-22",
            "title": "Self review (later run)",
            "description": "Different note body entirely.",
            "comments": [{"id": "c99-different", "date": "2026-09-23",
                          "author": "Someone Else", "text": "Keep it up."}],
        }],
    )
    assert decision_fields(packet_a) == decision_fields(packet_b)


def test_decision_fields_changes_when_substance_changes():
    packet_a = _packet()
    packet_b = copy.deepcopy(packet_a)
    packet_b["settings"]["ftp_watts"] = 275
    assert decision_fields(packet_a) != decision_fields(packet_b)
