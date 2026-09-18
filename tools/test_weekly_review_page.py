"""Tests for tools/weekly_review_page.py.

Fixture set: a "built" athlete (with writes/holds-free refresh_diff,
per_week, lint, variety, fallbacks, and a notes payload with three Monday
notes), a "skipped" athlete, and a "held" athlete (holds present, no
build outputs).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import weekly_review_page as wrp

RUN_DATE = "2026-09-21"


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / wrp.MANIFEST_FILENAME).write_text(json.dumps(manifest))


@pytest.fixture
def builds_root(tmp_path):
    root = tmp_path / "builds"

    built_dir = root / "built-athlete" / f"weekly-{RUN_DATE}"
    _write_manifest(built_dir, {
        "athlete_id": "built-athlete",
        "name": "Built Athlete",
        "title": "DRAFT — Built Athlete — Block 4wk",
        "plan_id": None,
        "plan_day_one": "2026-09-21",
        "weeks": 2,
        "per_week": [
            {"week": 1, "hours": 6.5, "tss": 310},
            {"week": 2, "hours": 5.0, "tss": 250},
        ],
        "notes_count": 3,
        "lint": {"fail": 0, "warn": 2, "allow_listed": 1},
        "variety": {
            "distinct_items": 9, "distinct_families": 7,
            "series": [{"series_key": ["s1"], "family": "f1", "rungs": 2}],
            "pool_utilisation": {"tempo": {"used": 3, "pool": 60}},
        },
        "fallbacks": 2,
        "refresh_diff": {
            "holds": [],
            "writes": [
                {"path": "fitness_markers.ftp_watts", "old": 295, "new": 300, "source": "tp_settings"},
            ],
            "standing_contradictions": [],
            "demonstrated": {"hours_6wk": 6.2, "tss_6wk": 290, "ctl": 55.4},
        },
        "inputs_sha256": "abc123",
        "code_manifest": {"git_sha": "deadbeef", "dirty": False, "dirty_paths": []},
        "status": "built",
        "notes": ["athlete_layer.py not found yet -- layer step skipped"],
    })
    (built_dir / "notes_payload.json").write_text(json.dumps([
        {"title": "Week 1", "noteDate": "2026-09-21",
         "description": "Frequency first this block. The rest is optional."},
        {"title": "Mid-week check-in", "noteDate": "2026-09-23",
         "description": "Not a Monday note -- should be excluded."},
        {"title": "Week 2", "noteDate": "2026-09-28",
         "description": "Same rhythm, a little more in it."},
        {"title": "Week 3", "noteDate": "2026-10-05",
         "description": "Keep running six to twelve miles a week."},
        {"title": "Week 4", "noteDate": "2026-10-12",
         "description": "Fourth Monday note, should not appear (only first three)."},
    ]))

    skipped_dir = root / "skipped-athlete" / f"weekly-{RUN_DATE}"
    _write_manifest(skipped_dir, {
        "athlete_id": "skipped-athlete", "name": "Skipped Athlete",
        "title": "DRAFT — Skipped Athlete — Block 4wk", "plan_id": "tp-999",
        "plan_day_one": None, "weeks": 0, "per_week": [], "notes_count": 0,
        "lint": {}, "variety": {}, "fallbacks": 0,
        "refresh_diff": {"holds": [], "writes": [], "standing_contradictions": [], "demonstrated": {}},
        "inputs_sha256": "same-as-before", "code_manifest": {"git_sha": "deadbeef"},
        "status": "skipped", "notes": ["no trigger: window and inputs unchanged"],
    })

    held_dir = root / "held-athlete" / f"weekly-{RUN_DATE}"
    _write_manifest(held_dir, {
        "athlete_id": "held-athlete", "name": "Held Athlete",
        "title": "DRAFT — Held Athlete — Block 4wk", "plan_id": None,
        "plan_day_one": None, "weeks": 0, "per_week": [], "notes_count": 0,
        "lint": {}, "variety": {}, "fallbacks": 0,
        "refresh_diff": {
            "holds": [{"type": "ftp_mismatch",
                       "message": "TP FTP 250W vs profile 300W",
                       "sources": ["tp_settings", "profile.yaml"]}],
            "writes": [], "standing_contradictions": [], "demonstrated": {},
        },
        "inputs_sha256": "x", "code_manifest": {"git_sha": "deadbeef"},
        "status": "held", "notes": [],
    })

    return root


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def test_discover_athletes_finds_all_three(builds_root):
    found = wrp.discover_athletes(builds_root, RUN_DATE)
    ids = [athlete_id for athlete_id, _ in found]
    assert ids == ["built-athlete", "held-athlete", "skipped-athlete"]


def test_discover_athletes_ignores_other_run_dates(builds_root):
    found = wrp.discover_athletes(builds_root, "2099-01-01")
    assert found == []


def test_discover_athletes_empty_builds_root(tmp_path):
    assert wrp.discover_athletes(tmp_path / "nope", RUN_DATE) == []


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def test_first_sentence():
    assert wrp._first_sentence("Frequency first. Duration second.") == "Frequency first."
    assert wrp._first_sentence("No terminal punctuation") == "No terminal punctuation"
    assert wrp._first_sentence("") == ""
    assert wrp._first_sentence(None) == ""


def test_monday_notes_filters_and_sorts():
    notes = [
        {"noteDate": "2026-09-23", "description": "not monday"},
        {"noteDate": "2026-09-28", "description": "second monday"},
        {"noteDate": "2026-09-21", "description": "first monday"},
        {"noteDate": "not-a-date", "description": "garbage"},
    ]
    mondays = wrp._monday_notes(notes)
    assert [n["description"] for n in mondays] == ["first monday", "second monday"]


def test_first_name():
    assert wrp._first_name("Forest Hietpas") == "Forest"
    assert wrp._first_name("") == "the athlete"
    assert wrp._first_name(None) == "the athlete"


# --------------------------------------------------------------------------
# full page render
# --------------------------------------------------------------------------

def test_build_page_includes_all_statuses(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "Built Athlete" in page
    assert "Skipped Athlete" in page
    assert "Held Athlete" in page
    assert "BUILT" in page
    assert "SKIPPED" in page
    assert "HELD" in page


def test_build_page_profile_changes_table(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "fitness_markers.ftp_watts" in page
    assert "295" in page and "300" in page
    assert "tp_settings" in page


def test_build_page_holds_with_both_sources(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "ftp_mismatch" in page
    assert "tp_settings" in page
    assert "profile.yaml" in page


def test_build_page_block_shape_and_demonstrated(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "6.5" in page  # week 1 hours
    assert "310" in page  # week 1 tss
    assert "CTL 55" in page  # CTL


def test_build_page_three_lines_only_mondays_and_capped_at_three(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "Frequency first this block." in page
    assert "Same rhythm, a little more in it." in page
    assert "Keep running six to twelve miles a week." in page
    assert "Fourth Monday note" not in page
    assert "Not a Monday note" not in page
    assert "Three lines to Built" in page
    assert "DRAFT" in page


def test_build_page_lint_and_fallbacks(builds_root):
    page = wrp.build_page(builds_root, RUN_DATE)
    assert "fail 0" in page
    assert "warn 2" in page
    assert "allow-listed 1" in page


def test_build_page_no_athletes(tmp_path):
    page = wrp.build_page(tmp_path / "empty", RUN_DATE)
    assert "no athlete manifests found" in page


def test_run_1_banner_only_when_requested(builds_root):
    without = wrp.build_page(builds_root, RUN_DATE, run_1=False)
    assert "Run 1 note" not in without

    with_banner = wrp.build_page(builds_root, RUN_DATE, run_1=True)
    assert "Run 1 note" in with_banner
    assert "not a second copy to reconcile" in with_banner


def test_page_has_no_external_assets():
    page = wrp.render([], RUN_DATE, run_1=False)
    assert "http://" not in page
    assert "https://" not in page
    assert "<link" not in page
    assert "<script" not in page


def test_page_is_valid_shell():
    page = wrp.render([], RUN_DATE, run_1=False)
    assert page.startswith("<!doctype html>")
    assert "<title>" in page
    assert "<style>" in page


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_cli_writes_out_file(builds_root, tmp_path):
    out_path = tmp_path / "review.html"
    rc = wrp.main([
        "--builds-root", str(builds_root),
        "--run-date", RUN_DATE,
        "--out", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    content = out_path.read_text()
    assert "Built Athlete" in content
