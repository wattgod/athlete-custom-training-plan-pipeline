"""TP READ fixture contract: schema tests over the synthetic fixture set."""

from __future__ import annotations

import copy

import pytest
from jsonschema.exceptions import ValidationError

from coaching_loop.fixtures.loader import (
    EXCLUDED_FIXTURE_ATHLETE_ID,
    RESERVED_FIXTURE_ATHLETE_ID,
    SYNTHETIC_ATHLETE_ID,
    load_tp_snapshot,
)
from coaching_loop.validation import validate_tp_fixture


@pytest.mark.parametrize(
    "athlete_id",
    [SYNTHETIC_ATHLETE_ID, EXCLUDED_FIXTURE_ATHLETE_ID, RESERVED_FIXTURE_ATHLETE_ID],
)
def test_every_synthetic_fixture_validates(athlete_id):
    validate_tp_fixture(load_tp_snapshot(athlete_id))


def test_fixture_exercises_every_status_value():
    snapshot = load_tp_snapshot(SYNTHETIC_ATHLETE_ID)
    statuses = {w["status"] for w in snapshot["workouts"]}
    assert statuses == {"planned", "completed", "skipped", "race"}


def test_fixture_exercises_null_slot_for_non_loop_owned_sport():
    snapshot = load_tp_snapshot(SYNTHETIC_ATHLETE_ID)
    non_loop = [w for w in snapshot["workouts"] if not w["loop_owned"]]
    assert non_loop
    assert all(w["slot"] is None for w in non_loop)


def test_fixture_comments_are_derived_form_only():
    snapshot = load_tp_snapshot(SYNTHETIC_ATHLETE_ID)
    assert snapshot["comments"]
    for comment in snapshot["comments"]:
        assert set(comment.keys()) == {"comment_id", "workout_id", "lexicon", "length"}
        assert set(comment["lexicon"].keys()) == {"version", "hits"}


def test_schema_rejects_raw_comment_text_field():
    snapshot = copy.deepcopy(load_tp_snapshot(SYNTHETIC_ATHLETE_ID))
    snapshot["comments"][0]["text"] = "this is raw athlete text and must never validate"
    with pytest.raises(ValidationError):
        validate_tp_fixture(snapshot)


def test_schema_requires_exactly_seven_calendar_days():
    snapshot = copy.deepcopy(load_tp_snapshot(SYNTHETIC_ATHLETE_ID))
    snapshot["calendar"]["days"] = snapshot["calendar"]["days"][:6]
    with pytest.raises(ValidationError):
        validate_tp_fixture(snapshot)


def test_schema_rejects_missing_required_workout_field():
    snapshot = copy.deepcopy(load_tp_snapshot(SYNTHETIC_ATHLETE_ID))
    del snapshot["workouts"][0]["status"]
    with pytest.raises(ValidationError):
        validate_tp_fixture(snapshot)


def test_schema_rejects_wrong_schema_version():
    snapshot = copy.deepcopy(load_tp_snapshot(SYNTHETIC_ATHLETE_ID))
    snapshot["schema_version"] = "tp-fixture-v2"
    with pytest.raises(ValidationError):
        validate_tp_fixture(snapshot)


def test_schema_rejects_additional_top_level_property():
    snapshot = copy.deepcopy(load_tp_snapshot(SYNTHETIC_ATHLETE_ID))
    snapshot["extra_field"] = "not in contract"
    with pytest.raises(ValidationError):
        validate_tp_fixture(snapshot)
