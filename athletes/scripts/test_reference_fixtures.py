"""Regression checks for sanitized house-standard calendar references."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from capture_reference import (REFERENCE_CAPTURE_VERSION, capture_fixture,
                               payload_sha256)


ROOT = Path(__file__).resolve().parents[2]
REFERENCES = ROOT / "references"
CAPTURE = Path(__file__).with_name("capture_reference.py")


@pytest.mark.parametrize(
    ("fixture_name", "expected_workouts", "expected_notes"),
    [
        ("monika-standard-2026-08.json", 46, 19),
        ("guillermo-2026-08.json", 44, 18),
    ],
)
def test_fixture_headers_counts_and_payload_hash(
    fixture_name: str, expected_workouts: int, expected_notes: int,
):
    fixture = json.loads((REFERENCES / fixture_name).read_text(encoding="utf-8"))

    assert fixture["reference_capture_version"] == REFERENCE_CAPTURE_VERSION
    assert len(fixture["workouts"]) == expected_workouts
    assert len(fixture["notes"]) == expected_notes
    assert fixture["counts"]["notes"] == expected_notes
    observed_counts = Counter(workout["kind"] for workout in fixture["workouts"])
    assert fixture["counts"]["workouts_by_kind"] == {
        kind: observed_counts[kind]
        for kind in ("bike", "strength", "day_off", "race")
    }
    assert fixture["payload_sha256"] == payload_sha256(
        fixture["workouts"], fixture["notes"],
    )


def test_fixtures_contain_no_reference_athlete_pii_or_provider_ids():
    forbidden = ("monika", "renk", "guillermo", "romero", "@", "2947583", "3032265")
    for fixture_path in sorted(REFERENCES.glob("*.json")):
        contents = fixture_path.read_text(encoding="utf-8").casefold()
        assert not any(token in contents for token in forbidden), fixture_path.name


def test_monika_fixture_has_the_expected_calendar_composition():
    fixture = json.loads((REFERENCES / "monika-standard-2026-08.json").read_text())
    counts = Counter(workout["kind"] for workout in fixture["workouts"])

    assert counts["bike"] + counts["race"] == 36
    assert counts["day_off"] == 10
    assert len(fixture["notes"]) == 19


@pytest.mark.parametrize("raw", [
    {
        "workouts": [{
            "workoutId": 99, "athleteId": 2947583,
            "workoutDay": "2026-08-01T00:00:00", "workoutTypeValueId": 2,
            "title": "Monika's Ride", "description": (
                "Email monika.renk@example.com; see "
                "https://example.test/guides/monika-renk/"),
            "structure": None,
        }],
        "notes": [{
            "id": 44, "athleteId": 2947583, "noteDate": "2026-08-01T00:00:00",
            "title": "Renk note", "description": "Ask MONIKA for feedback.",
        }],
    },
    {
        "w": [{
            "workoutId": 99, "athleteId": 2947583,
            "workoutDay": "2026-08-01T00:00:00", "workoutTypeValueId": 2,
            "title": "Monika's Ride", "description": (
                "Email monika.renk@example.com; see "
                "https://example.test/guides/monika-renk/"),
            "structure": None,
        }],
        "n": [{
            "id": 44, "athleteId": 2947583, "noteDate": "2026-08-01T00:00:00",
            "title": "Renk note", "description": "Ask MONIKA for feedback.",
        }],
    },
])
def test_capture_normalizes_both_raw_shapes_and_scrubs_pii(raw: dict):
    fixture = capture_fixture(raw, athlete_name="Monika Renk", slug="monika-renk")
    contents = json.dumps(fixture).casefold()

    assert fixture["workouts"][0]["workoutId"] == 1
    assert fixture["workouts"][0]["athleteId"] == 1_000_001
    assert fixture["notes"][0]["id"] == 1
    assert fixture["workouts"][0]["structure"] == {}
    assert "{guide_url}" in contents
    assert "{coach_email}" in contents
    assert not any(token in contents for token in ("monika", "renk", "@", "2947583"))


def test_capture_is_byte_deterministic(tmp_path: Path):
    # Self-contained: the raw dumps live outside the repo (they carry real
    # athlete PII and are never committed), so the test synthesizes its own
    # raw input — which also exercises sanitization end to end.
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({
        "workouts": [
            {"workoutId": 42, "athleteId": 2947583,
             "workoutDay": "2026-08-06T00:00:00", "workoutTypeValueId": 2,
             "title": "VO2max - Testy Special - 60min - RPE9",
             "totalTimePlanned": 1.0, "tssPlanned": 70.0, "ifPlanned": 0.8,
             "description": "Testy Athlete rides hard. Mail testy@example.com. "
                            "Guide: https://intake.gravelgodcoaching.com/guides/testy-athlete/",
             "structure": None},
            {"workoutId": 43, "athleteId": 2947583,
             "workoutDay": "2026-08-07T00:00:00", "workoutTypeValueId": 7,
             "title": "Day Off", "totalTimePlanned": None, "tssPlanned": None,
             "ifPlanned": None, "description": "Rest, Testy.", "structure": None},
        ],
        "notes": [
            {"id": 9, "athleteId": 2947583,
             "noteDate": "2026-08-06T00:00:00",
             "title": "START HERE — Testy Athlete",
             "description": "Welcome Testy — reply to testy@example.com."},
        ],
    }))
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [
        sys.executable, str(CAPTURE), str(raw), "--athlete-name", "Testy Athlete",
        "--slug", "testy-athlete", "--out",
    ]

    subprocess.run(command + [str(first)], check=True, cwd=ROOT)
    subprocess.run(command + [str(second)], check=True, cwd=ROOT)

    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    scrubbed = first.read_text()
    for token in ("Testy", "Athlete", "testy@example.com", "2947583",
                  "guides/testy-athlete"):
        assert token not in scrubbed, token
