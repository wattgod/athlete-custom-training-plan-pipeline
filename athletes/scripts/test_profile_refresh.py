"""Tests for profile_refresh: window roll, holds, add-only writes, hash
stability, YAML text surgery, and the --write gate.

Fixtures are synthetic (fake name/email/coach text) -- never a copy of a
real athlete's profile.yaml. See docs/specs/2026-09-18-variety-and-
weekly-dynamic-plans.md, Part B, revision 2, for the decisions under test.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # collect from the repo root too

import yaml

import profile_refresh
from constants import DAY_ORDER_FULL
from profile_refresh import (
    apply_changes_to_yaml_text,
    main as cli_main,
    refresh,
    write_profile_changes,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixture builders (synthetic data only)
# ---------------------------------------------------------------------------


def _preferred_days():
    return {
        day: {"availability": "available", "time_slots": ["am"], "max_duration_min": 90}
        for day in DAY_ORDER_FULL
    }


def _race_bound_profile(**overrides):
    profile = {
        "name": "Race Bound Test Athlete",
        "email": "race-bound@example.com",
        "athlete_id": "race-bound-test",
        "tp_athlete_id": 9000001,
        "primary_goal": "specific_race",
        "fulfillment": {
            "effective_date": "2026-09-21",
            "planning_horizon_end": "2026-11-08",
            "weeks_purchased": 7,
        },
        "target_race": {
            "name": "Synthetic Gravel Classic",
            "race_id": "synthetic_gravel_classic",
            "date": "2026-11-07",
            "goal_type": "compete",
        },
        "fitness_markers": {"ftp_watts": 270, "weight_kg": 79.0},
        "training_history": {
            "years_structured": 5, "highest_weekly_hours": 13.0,
            "current_weekly_hours": 8.5,
        },
        "weekly_availability": {
            "total_hours_available": 10, "cycling_hours_target": 9.5,
        },
        "preferred_days": _preferred_days(),
        "cycling_equipment": {"smart_trainer": True},
        "strength_equipment": ["minimal"],
        "health_factors": {"age": 45, "sleep_hours_avg": 7},
        "a_events": [
            {"name": "Synthetic Gravel Classic", "date": "2026-11-07",
             "priority": "A"},
        ],
        "b_events": [],
    }
    profile.update(overrides)
    return profile


def _targetless_profile(**overrides):
    profile = {
        "name": "Targetless Test Athlete",
        "email": "targetless@example.com",
        "athlete_id": "targetless-test",
        "tp_athlete_id": 9000002,
        "primary_goal": "base_building",
        "fulfillment": {
            "effective_date": "2026-09-28",
            "planning_horizon_end": "2026-10-25",
            "weeks_purchased": 4,
        },
        "target_race": {},
        "coached_block": {
            "phase": "base",
            "focus": "Rebuild frequency and rhythm.",
            "week_types": ["load", "load", "load", "recovery"],
        },
        "fitness_markers": {"ftp_watts": 300, "weight_kg": 75.0},
        "training_history": {
            "years_structured": 0, "highest_weekly_hours": 11.7,
            "current_weekly_hours": 6.5,
        },
        "weekly_availability": {
            "total_hours_available": 7, "cycling_hours_target": 4.5,
        },
        "preferred_days": _preferred_days(),
        "cycling_equipment": {"smart_trainer": True},
        "strength_equipment": ["minimal"],
        "health_factors": {"age": 40, "sleep_hours_avg": 7},
        "a_events": [],
        "b_events": [],
        "life_calendar": {"source": "synthetic", "commitments": []},
    }
    profile.update(overrides)
    return profile


def _write_profile(athlete_dir: Path, profile: dict) -> None:
    athlete_dir.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(profile, sort_keys=False, default_flow_style=False)
    (athlete_dir / "profile.yaml").write_text(text)


def _packet(**overrides):
    packet = {
        "schema": "weekly_packet/v1",
        "athlete_key": "race-bound-test",
        "tp_athlete_id": 9000001,
        "as_of": "2026-09-18",
        "settings": {"ftp_watts": 270, "weight_kg": 79.0},
        "events": [],
        "pmc_daily": [],
        "workouts": [],
        "notes": [],
        "source_manifest": {"captured_at": "2026-09-18T12:00:00Z", "endpoints": []},
    }
    packet.update(overrides)
    return packet


# ---------------------------------------------------------------------------
# Window roll
# ---------------------------------------------------------------------------


def test_race_bound_roll_shrinks_weeks_as_the_race_approaches(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet()

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff.holds == []
    assert diff.window == {
        "mode": "race_bound",
        "start": "2026-10-05",
        "end": "2026-11-08",
        "weeks": 5,
        "rotate_steps": 2,
    }
    changed = {c["path"]: c["new"] for c in diff.profile_changes}
    assert changed["fulfillment.effective_date"] == "2026-10-05"
    # planning_horizon_end (2026-11-08) is unchanged from the original
    # profile, so no change record is emitted for it -- window already
    # asserts the resulting value above.
    assert changed["fulfillment.weeks_purchased"] == 5


def test_race_bound_roll_unchanged_today_produces_no_changes(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet()

    diff = refresh(
        athlete_dir, packet, today="2026-09-18", repo_root=_REPO_ROOT)

    assert diff.holds == []
    assert diff.window["start"] == "2026-09-21"
    assert diff.window["weeks"] == 7
    assert diff.profile_changes == []


def test_targetless_roll_advances_a_week_and_rotates_week_types(tmp_path):
    athlete_dir = tmp_path / "targetless-test"
    _write_profile(athlete_dir, _targetless_profile())
    packet = _packet(athlete_key="targetless-test", tp_athlete_id=9000002,
                      settings={"ftp_watts": 300, "weight_kg": 75.0})

    diff = refresh(
        athlete_dir, packet, today="2026-10-01", repo_root=_REPO_ROOT)

    assert diff.holds == []
    assert diff.window == {
        "mode": "targetless",
        "start": "2026-10-05",
        "end": "2026-11-01",
        "weeks": 4,
        "rotate_steps": 1,
    }
    changed = {c["path"]: c["new"] for c in diff.profile_changes}
    assert changed["coached_block.week_types"] == ["load", "load", "recovery", "load"]
    assert changed["fulfillment.effective_date"] == "2026-10-05"
    assert changed["fulfillment.planning_horizon_end"] == "2026-11-01"


# ---------------------------------------------------------------------------
# Holds
# ---------------------------------------------------------------------------


def test_ftp_mismatch_holds_and_blocks_write(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet(settings={"ftp_watts": 265, "weight_kg": 79.0})

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff.profile_changes == []
    codes = {h["code"] for h in diff.holds}
    assert "ftp_mismatch" in codes
    hold = next(h for h in diff.holds if h["code"] == "ftp_mismatch")
    assert "265" in hold["message"] and "270" in hold["message"]


def test_race_date_mismatch_holds_and_blocks_write(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet(events=[
        {"id": "tp-1", "date": "2026-11-14", "name": "Synthetic Gravel Classic",
         "priority": "A"},
    ])

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff.profile_changes == []
    codes = {h["code"] for h in diff.holds}
    assert "race_date_mismatch" in codes


def test_race_too_soon_holds(tmp_path):
    profile = _race_bound_profile()
    profile["target_race"]["date"] = "2026-09-25"
    profile["fulfillment"]["planning_horizon_end"] = "2026-09-27"
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, profile)
    packet = _packet()

    diff = refresh(
        athlete_dir, packet, today="2026-09-18", repo_root=_REPO_ROOT)

    assert diff.profile_changes == []
    codes = {h["code"] for h in diff.holds}
    assert "race_too_soon" in codes


def test_excluded_athlete_holds(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet(tp_athlete_id=418209)  # coaching_loop.exclusions.EXCLUDED_ATHLETE_IDS

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff.profile_changes == []
    codes = {h["code"] for h in diff.holds}
    assert "excluded_athlete" in codes


# ---------------------------------------------------------------------------
# Add-only events and commitments
# ---------------------------------------------------------------------------


def test_new_tp_event_added_existing_kept(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet(events=[
        # Matches the profile's existing a_events entry -- must be kept,
        # never duplicated.
        {"id": "tp-1", "date": "2026-11-07", "name": "Synthetic Gravel Classic",
         "priority": "A"},
        # A genuinely new event.
        {"id": "tp-2", "date": "2026-12-05", "name": "Synthetic Winter Grind",
         "priority": "B"},
    ])

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff.holds == []
    event_changes = [c for c in diff.profile_changes if c["path"].endswith("[]")]
    assert len(event_changes) == 1
    assert event_changes[0]["path"] == "b_events[]"
    assert event_changes[0]["new"]["name"] == "Synthetic Winter Grind"


def test_new_event_with_no_priority_is_reported_not_written(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet(events=[
        {"id": "tp-3", "date": "2026-12-12", "name": "Synthetic Unpicked Event",
         "priority": None},
    ])

    diff = refresh(
        athlete_dir, packet, today="2026-09-29", repo_root=_REPO_ROOT)

    # An unset priority never reaches b_events (every b_events entry drives a
    # taper overlay); with no c_events list it is reported only.
    assert [c for c in diff.profile_changes if c["path"].endswith("[]")] == []
    assert "Synthetic Unpicked Event" in diff.history_section

def test_commitments_dedupe_by_date_and_title(tmp_path):
    profile = _targetless_profile()
    profile["life_calendar"]["commitments"] = [
        {"date": "2026-10-09", "title": "Existing commitment"},
    ]
    athlete_dir = tmp_path / "targetless-test"
    _write_profile(athlete_dir, profile)
    packet = _packet(athlete_key="targetless-test", tp_athlete_id=9000002,
                      settings={"ftp_watts": 300, "weight_kg": 75.0})

    diff = refresh(
        athlete_dir, packet, today="2026-10-01", repo_root=_REPO_ROOT,
        commitments=[
            {"date": "2026-10-09", "title": "Existing commitment"},  # dup, skipped
            {"date": "2026-11-01", "title": "New commitment"},
        ],
    )

    commitment_changes = [
        c for c in diff.profile_changes
        if c["path"] == "life_calendar.commitments[]"
    ]
    assert len(commitment_changes) == 1
    assert commitment_changes[0]["new"]["title"] == "New commitment"


# ---------------------------------------------------------------------------
# Hash stability
# ---------------------------------------------------------------------------


def test_hash_stable_across_ids_timestamps_and_review_window(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())

    packet_a = _packet(
        as_of="2026-09-18",
        events=[{"id": "e1", "date": "2026-12-05", "name": "Synthetic Winter Grind",
                 "priority": "B"}],
        notes=[{"note_id": "n1", "date": "2026-09-15", "title": "Review",
                 "description": "x",
                 "comments": [{"id": "c1", "date": "2026-09-16",
                               "author": "Coach", "text": "Same text"}]}],
    )
    packet_b = _packet(
        as_of="2026-09-25",
        events=[{"id": "e2-different", "date": "2026-12-05",
                  "name": "Synthetic Winter Grind", "priority": "B"}],
        notes=[{"note_id": "n2-different", "date": "2026-09-22",
                 "title": "Review", "description": "different body",
                 "comments": [{"id": "c2-different", "date": "2026-09-23",
                               "author": "Different Author", "text": "Same text"}]}],
    )

    diff_a = refresh(athlete_dir, packet_a, today="2026-09-29", repo_root=_REPO_ROOT)
    diff_b = refresh(athlete_dir, packet_b, today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff_a.inputs_sha256 == diff_b.inputs_sha256


def test_hash_changes_when_ftp_changes(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())

    diff_a = refresh(
        athlete_dir, _packet(settings={"ftp_watts": 270, "weight_kg": 79.0}),
        today="2026-09-29", repo_root=_REPO_ROOT)
    diff_b = refresh(
        athlete_dir, _packet(settings={"ftp_watts": 271, "weight_kg": 79.0}),
        today="2026-09-29", repo_root=_REPO_ROOT)

    assert diff_a.inputs_sha256 != diff_b.inputs_sha256


# ---------------------------------------------------------------------------
# YAML text surgery / byte-identical round trip
# ---------------------------------------------------------------------------


def test_unchanged_profile_round_trips_byte_identical(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    original_bytes = (athlete_dir / "profile.yaml").read_bytes()

    diff = refresh(
        athlete_dir, _packet(), today="2026-09-18", repo_root=_REPO_ROOT)
    assert diff.profile_changes == []  # nothing to write this run

    write_profile_changes(athlete_dir, diff.profile_changes)

    assert (athlete_dir / "profile.yaml").read_bytes() == original_bytes


def test_apply_changes_preserves_unrelated_comments():
    original_text = (
        "fulfillment:\n"
        "  effective_date: '2026-09-21'\n"
        "  planning_horizon_end: '2026-11-08'\n"
        "  weeks_purchased: 7\n"
        "sex: male  # comment that must survive untouched\n"
        "a_events: []\n"
        "b_events: []\n"
    )
    changes = [
        {"path": "fulfillment.effective_date", "old": "2026-09-21",
         "new": "2026-10-05", "source": "engine:window_roll"},
        {"path": "fulfillment.weeks_purchased", "old": 7, "new": 5,
         "source": "engine:window_roll"},
        {"path": "b_events[]", "old": None,
         "new": {"name": "New Race", "date": "2026-12-05", "priority": "B"},
         "source": "packet:events"},
    ]

    new_text = apply_changes_to_yaml_text(original_text, changes)

    assert "effective_date: '2026-10-05'" in new_text
    assert "weeks_purchased: 5" in new_text
    assert "planning_horizon_end: '2026-11-08'" in new_text  # untouched
    assert "sex: male  # comment that must survive untouched" in new_text  # untouched
    assert "- name: New Race" in new_text
    assert "  date: '2026-12-05'" in new_text
    assert "  priority: B" in new_text

    reparsed = yaml.safe_load(new_text)
    assert reparsed["fulfillment"]["effective_date"] == "2026-10-05"
    assert reparsed["fulfillment"]["weeks_purchased"] == 5
    assert reparsed["b_events"] == [
        {"name": "New Race", "date": "2026-12-05", "priority": "B"}]


def test_apply_changes_with_no_changes_returns_original_text_unchanged():
    original_text = "sex: male\n"
    assert apply_changes_to_yaml_text(original_text, []) == original_text


# ---------------------------------------------------------------------------
# --write gate
# ---------------------------------------------------------------------------


def test_cli_without_write_flag_touches_nothing(tmp_path, monkeypatch):
    athlete_id = "race-bound-test"
    athletes_base = tmp_path / "athletes"
    athlete_dir = athletes_base / athlete_id
    _write_profile(athlete_dir, _race_bound_profile())
    monkeypatch.setattr(
        profile_refresh, "get_athlete_dir", lambda aid: athletes_base / aid)

    original_bytes = (athlete_dir / "profile.yaml").read_bytes()
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()))
    history_path = tmp_path / "history" / "coaching_history.md"

    exit_code = cli_main([
        athlete_id, "--packet", str(packet_path),
        "--history", str(history_path), "--today", "2026-09-29",
    ])

    assert exit_code == 0
    assert (athlete_dir / "profile.yaml").read_bytes() == original_bytes
    assert not history_path.exists()
    assert not (history_path.parent / "refresh_diff.json").exists()


def test_cli_with_write_flag_persists_profile_history_and_diff(tmp_path, monkeypatch):
    athlete_id = "race-bound-test"
    athletes_base = tmp_path / "athletes"
    athlete_dir = athletes_base / athlete_id
    _write_profile(athlete_dir, _race_bound_profile())
    monkeypatch.setattr(
        profile_refresh, "get_athlete_dir", lambda aid: athletes_base / aid)

    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()))
    history_path = tmp_path / "history" / "coaching_history.md"

    exit_code = cli_main([
        athlete_id, "--packet", str(packet_path),
        "--history", str(history_path), "--today", "2026-09-29",
        "--write",
    ])

    assert exit_code == 0
    new_profile = yaml.safe_load((athlete_dir / "profile.yaml").read_text())
    assert new_profile["fulfillment"]["effective_date"] == "2026-10-05"
    assert new_profile["fulfillment"]["weeks_purchased"] == 5
    assert history_path.exists()
    assert "### Window" in history_path.read_text()
    assert (history_path.parent / "refresh_diff.json").exists()


def test_a_block_that_has_not_started_is_never_pulled_earlier(tmp_path):
    athlete_dir = tmp_path / "targetless-test"
    profile = _targetless_profile()
    profile["fulfillment"]["effective_date"] = "2026-10-12"
    profile["fulfillment"]["planning_horizon_end"] = "2026-11-08"
    _write_profile(athlete_dir, profile)
    packet = _packet(athlete_key="targetless-test", tp_athlete_id=9000002,
                      settings={"ftp_watts": 300, "weight_kg": 75.0})

    diff = refresh(athlete_dir, packet, today="2026-10-01", repo_root=_REPO_ROOT)

    assert diff.window["start"] == "2026-10-12"
    assert diff.window["rotate_steps"] == 0
    assert not [c for c in diff.profile_changes if c["path"].startswith("fulfillment.")]
    assert not [c for c in diff.profile_changes if c["path"] == "coached_block.week_types"]


def test_same_date_event_with_a_different_spelling_is_not_added_again(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet()
    packet["events"] = [{"id": "e-9", "date": _race_bound_profile()["target_race"]["date"],
                         "name": "Schwangunk", "priority": None}]
    diff = refresh(athlete_dir, packet, today="2026-09-18", repo_root=_REPO_ROOT)
    assert not [c for c in diff.profile_changes if c["path"].endswith("_events[]")]
    assert "Schwangunk" in diff.history_section


def test_c_priority_events_never_reach_b_events_and_race_week_is_untouched(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    _write_profile(athlete_dir, _race_bound_profile())
    packet = _packet()
    race = _race_bound_profile()["target_race"]["date"]
    packet["events"] = [
        {"id": "c1", "date": "2026-10-03", "name": "Local CX", "priority": "C"},
        {"id": "x1", "date": race[:8] + "0" + str(int(race[8:]) - 1) if int(race[8:]) > 1 else race, "name": "Shakeout", "priority": "B"},
    ]
    diff = refresh(athlete_dir, packet, today="2026-09-18", repo_root=_REPO_ROOT)
    paths = [c["path"] for c in diff.profile_changes]
    assert "b_events[]" not in paths
    assert "Local CX" in diff.history_section


def test_missing_profile_section_is_a_hold_not_a_crash(tmp_path):
    athlete_dir = tmp_path / "race-bound-test"
    profile = _race_bound_profile()
    profile.pop("b_events", None)
    _write_profile(athlete_dir, profile)
    packet = _packet()
    packet["events"] = [{"id": "b1", "date": "2026-10-10", "name": "Tune-up Race", "priority": "B"}]
    diff = refresh(athlete_dir, packet, today="2026-09-18", repo_root=_REPO_ROOT)
    assert [h["code"] for h in diff.holds] == ["profile_key_missing"]
    assert diff.profile_changes == []
