"""Tests for tools/weekly_draft_plan.py.

The four subprocess-calling steps (``_run_generate_full_package``,
``_run_build_tp_plan_payload``, ``_run_profile_refresh``,
``_run_athlete_layer``) and ``build_code_manifest`` (real ``git``) are
monkeypatched to fixture writers per the exec brief -- no real subprocess
or git call happens in this file. The "script not found -> skipped with a
note" branches for ``profile_refresh.py`` / ``athlete_layer.py`` are
exercised by NOT monkeypatching those two and pointing ``repo_root`` at a
scratch directory that genuinely lacks the scripts.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from coaching_loop.exclusions import ExcludedAthleteError
from tools import weekly_draft_plan as wdp

ATHLETE_ID = "test-athlete"
FAKE_CODE_MANIFEST = {"git_sha": "deadbeefcafe", "dirty": False, "dirty_paths": []}


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fake_code_manifest(monkeypatch):
    """No real git repo backs the scratch repo_root used in these tests."""
    monkeypatch.setattr(wdp, "build_code_manifest", lambda repo_root: dict(FAKE_CODE_MANIFEST))


@pytest.fixture
def env(tmp_path):
    repo_root = tmp_path / "repo"
    builds_root = tmp_path / "builds"
    packets_dir = tmp_path / "packets"
    athlete_dir = repo_root / "athletes" / ATHLETE_ID
    athlete_dir.mkdir(parents=True)
    packets_dir.mkdir(parents=True)

    profile = {
        "name": "Test Athlete",
        "athlete_id": ATHLETE_ID,
        "fulfillment": {"weeks_purchased": 2},
        "target_race": {},
    }
    (athlete_dir / "profile.yaml").write_text(yaml.safe_dump(profile))

    plan_dates = {
        "plan_start": "2026-09-28",
        "weeks": [
            {"week": 1, "monday": "2026-09-28", "sunday": "2026-10-04"},
            {"week": 2, "monday": "2026-10-05", "sunday": "2026-10-11"},
        ],
    }
    (athlete_dir / "plan_dates.yaml").write_text(yaml.safe_dump(plan_dates))
    (athlete_dir / "library_variety.json").write_text(
        json.dumps({"sessions_resolved": 4, "distinct_items": 3})
    )
    (athlete_dir / "library_fallbacks.json").write_text(json.dumps([{"item_id": 1}]))

    packet = {"tp_athlete_id": 999001, "fetched_at": "2026-09-18T12:00:00Z"}
    (packets_dir / f"{ATHLETE_ID}.json").write_text(json.dumps(packet))

    return {
        "repo_root": repo_root,
        "builds_root": builds_root,
        "packets_dir": packets_dir,
        "packet_path": packets_dir / f"{ATHLETE_ID}.json",
        "athlete_dir": athlete_dir,
    }


def _fake_generate_full_package(*, repo_root, athlete_id):
    return None


def _fake_build_tp_plan_payload(*, repo_root, athlete_dir, out_dir, plan_day_one=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_payload = [
        {"title": "Endurance", "workoutDay": "2026-09-28T00:00:00",
         "totalTimePlanned": 1.5, "tssPlanned": 60},
        {"title": "Endurance", "workoutDay": "2026-09-30T00:00:00",
         "totalTimePlanned": 1.0, "tssPlanned": 40},
        {"title": "Endurance", "workoutDay": "2026-10-06T00:00:00",
         "totalTimePlanned": 2.0, "tssPlanned": 80},
    ]
    notes_payload = [
        {"title": "Week 1", "noteDate": "2026-09-28", "description": "Go easy."},
        {"title": "Week 2", "noteDate": "2026-10-05", "description": "Build."},
    ]
    lint = {
        "race_date": None, "workouts": 3, "fail": 0, "warn": 1,
        "findings": [], "allow_known_fails": [], "unresolved_fails": [],
        "plan_day_one": "2026-09-28",
    }
    (out_dir / "plan_payload.json").write_text(json.dumps(plan_payload))
    (out_dir / "notes_payload.json").write_text(json.dumps(notes_payload))
    (out_dir / "lint.json").write_text(json.dumps(lint))


@pytest.fixture
def stub_heavy_steps(monkeypatch):
    """Monkeypatch the two steps that always run in the "built" path.
    profile_refresh / athlete_layer are left alone so their natural
    "script not found" skip path is exercised (repo_root is a scratch
    dir without those scripts)."""
    monkeypatch.setattr(wdp, "_run_generate_full_package", _fake_generate_full_package)
    monkeypatch.setattr(wdp, "_run_build_tp_plan_payload", _fake_build_tp_plan_payload)


def _run(env, *, run_date="2026-09-21", force=False):
    return wdp.run(
        ATHLETE_ID,
        packet_path=env["packet_path"],
        run_date=run_date,
        builds_root=env["builds_root"],
        repo_root=env["repo_root"],
        force=force,
    )


# --------------------------------------------------------------------------
# _next_monday
# --------------------------------------------------------------------------

@pytest.mark.parametrize("d, expected", [
    (date(2026, 9, 21), date(2026, 9, 21)),  # already a Monday
    (date(2026, 9, 22), date(2026, 9, 28)),  # Tuesday -> next Monday
    (date(2026, 9, 27), date(2026, 9, 28)),  # Sunday -> next Monday
])
def test_next_monday(d, expected):
    assert wdp._next_monday(d) == expected


# --------------------------------------------------------------------------
# title rules
# --------------------------------------------------------------------------

def test_title_race_bound():
    profile = {"name": "Edward Shapiro", "fulfillment": {"weeks_purchased": 7},
               "target_race": {"name": "Shawangunk Grit"}}
    assert wdp._draft_title(profile) == "DRAFT — Edward Shapiro — Shawangunk Grit 7wk"


def test_title_targetless_block():
    profile = {"name": "Forest Hietpas", "fulfillment": {"weeks_purchased": 4},
               "target_race": {}}
    assert wdp._draft_title(profile) == "DRAFT — Forest Hietpas — Block 4wk"


def test_title_missing_weeks_still_labels_block():
    profile = {"name": "Nobody", "fulfillment": {}, "target_race": {}}
    assert wdp._draft_title(profile) == "DRAFT — Nobody — Block"


# --------------------------------------------------------------------------
# trigger rule
# --------------------------------------------------------------------------

def test_first_run_builds(env, stub_heavy_steps):
    manifest = _run(env)
    assert manifest["status"] == "built"
    assert manifest["weeks"] == 2
    assert manifest["notes_count"] == 2
    assert manifest["per_week"][0]["hours"] == 2.5
    assert manifest["per_week"][0]["tss"] == 100.0
    assert manifest["per_week"][1]["hours"] == 2.0
    assert manifest["lint"] == {"fail": 0, "warn": 1, "allow_listed": 0}
    assert manifest["variety"] == {"sessions_resolved": 4, "distinct_items": 3}
    assert manifest["fallbacks"] == 1
    assert manifest["plan_day_one"] == "2026-09-28"
    assert manifest["code_manifest"] == FAKE_CODE_MANIFEST
    assert any("athlete_layer.py not found" in n for n in manifest["notes"])
    assert any("profile_refresh.py not found" in n for n in manifest["notes"])

    state = json.loads((env["builds_root"] / ATHLETE_ID / wdp.STATE_FILENAME).read_text())
    assert state["window_start"] == "2026-09-21"
    assert state["inputs_sha256"] == manifest["inputs_sha256"]
    assert state["plan_title"] == manifest["title"]


def test_same_window_same_hash_skips(env, stub_heavy_steps):
    first = _run(env, run_date="2026-09-21")
    assert first["status"] == "built"

    # Same run date again: next-Monday is unchanged (2026-09-21 is already
    # a Monday) and nothing about the athlete's inputs changed -- neither
    # trigger fires.
    second = _run(env, run_date="2026-09-21")
    assert second["status"] == "skipped"
    assert any("no trigger" in n for n in second["notes"])
    state = json.loads((env["builds_root"] / ATHLETE_ID / wdp.STATE_FILENAME).read_text())
    assert state["inputs_sha256"] == first["inputs_sha256"]
    assert state["window_start"] == "2026-09-21"


def test_window_roll_forces_rebuild_even_with_same_inputs(env, stub_heavy_steps):
    first = _run(env, run_date="2026-09-21")
    assert first["status"] == "built"
    # Nothing about the athlete's inputs changed, but a week has passed.
    second = _run(env, run_date="2026-09-28")
    assert second["status"] == "built"
    assert second["inputs_sha256"] == first["inputs_sha256"]

    state = json.loads((env["builds_root"] / ATHLETE_ID / wdp.STATE_FILENAME).read_text())
    assert state["window_start"] == "2026-09-28"


def test_force_flag_forces_rebuild(env, stub_heavy_steps):
    first = _run(env, run_date="2026-09-21")
    assert first["status"] == "built"
    second = _run(env, run_date="2026-09-21", force=True)
    assert second["status"] == "built"


# --------------------------------------------------------------------------
# holds
# --------------------------------------------------------------------------

def test_holds_stop_the_build(env, stub_heavy_steps, monkeypatch):
    called = []
    monkeypatch.setattr(
        wdp, "_run_generate_full_package",
        lambda **kw: called.append("generate") or _fake_generate_full_package(**kw),
    )
    athlete_build_dir = env["builds_root"] / ATHLETE_ID
    athlete_build_dir.mkdir(parents=True)
    refresh_diff = {
        "window_start": "2026-09-21",
        "holds": [{"type": "ftp_mismatch", "message": "TP FTP 250W vs profile 300W",
                    "sources": ["tp_settings", "profile.yaml"]}],
    }
    (athlete_build_dir / wdp.REFRESH_DIFF_FILENAME).write_text(json.dumps(refresh_diff))

    manifest = _run(env)
    assert manifest["status"] == "held"
    assert manifest["refresh_diff"]["holds"] == refresh_diff["holds"]
    assert called == []  # generate_full_package never ran


# --------------------------------------------------------------------------
# plan_id preservation
# --------------------------------------------------------------------------

def test_plan_id_preserved_across_rebuilds(env, stub_heavy_steps):
    athlete_build_dir = env["builds_root"] / ATHLETE_ID
    athlete_build_dir.mkdir(parents=True)
    (athlete_build_dir / wdp.STATE_FILENAME).write_text(json.dumps({
        "plan_id": "tp-plan-123", "plan_title": None,
        "window_start": None, "inputs_sha256": None, "last_run": None,
    }))

    manifest = _run(env)
    assert manifest["plan_id"] == "tp-plan-123"
    state = json.loads((athlete_build_dir / wdp.STATE_FILENAME).read_text())
    assert state["plan_id"] == "tp-plan-123"


# --------------------------------------------------------------------------
# exclusions
# --------------------------------------------------------------------------

def test_excluded_athlete_raises(env, stub_heavy_steps):
    env["packet_path"].write_text(json.dumps({"tp_athlete_id": 418209}))
    with pytest.raises(ExcludedAthleteError):
        _run(env)


def test_exclusion_check_skipped_without_numeric_id(env, stub_heavy_steps):
    env["packet_path"].write_text(json.dumps({"fetched_at": "2026-09-18T12:00:00Z"}))
    manifest = _run(env)
    assert manifest["status"] == "built"
    assert any("exclusions check skipped" in n for n in manifest["notes"])


# --------------------------------------------------------------------------
# manifest fields
# --------------------------------------------------------------------------

def test_manifest_has_required_fields(env, stub_heavy_steps):
    manifest = _run(env)
    for key in (
        "athlete_id", "name", "title", "plan_id", "plan_day_one", "weeks",
        "per_week", "notes_count", "lint", "variety", "fallbacks",
        "refresh_diff", "inputs_sha256", "code_manifest", "status", "notes",
    ):
        assert key in manifest, key
    assert manifest["title"] == "DRAFT — Test Athlete — Block 2wk"
