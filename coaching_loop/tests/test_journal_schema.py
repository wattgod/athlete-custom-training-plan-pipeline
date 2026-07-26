"""C3 loop-journal record schema tests -- one record per journal record type."""

from __future__ import annotations

import copy

import pytest
from jsonschema.exceptions import ValidationError

from coaching_loop.validation import validate_journal_record

_PROPOSAL_ID = "prop-" + "a" * 16
_OTHER_PROPOSAL_ID = "prop-" + "b" * 16

VALID_RECORDS = {
    "PROPOSED": {
        "record_type": "PROPOSED",
        "run_id": "run-0001",
        "ts": "2026-07-25T13:00:00Z",
        "week_start": "2026-07-27",
        "revision": 1,
        "proposal_id": _PROPOSAL_ID,
        "content_hash": "c" * 64,
        "input_manifest_hash": "d" * 64,
        "origin": "engine",
    },
    "REPLAY": {
        "record_type": "REPLAY",
        "run_id": "run-0002",
        "ts": "2026-08-01T13:00:00Z",
        "week_start": "2026-07-27",
        "revision_ref": 1,
        "proposal_id": _PROPOSAL_ID,
    },
    "REPROPOSED_UNCHANGED": {
        "record_type": "REPROPOSED_UNCHANGED",
        "run_id": "run-0003",
        "ts": "2026-08-08T13:00:00Z",
        "week_start": "2026-07-27",
        "revision_ref": 1,
        "proposal_id": _PROPOSAL_ID,
    },
    "APPROVED": {
        "record_type": "APPROVED",
        "run_id": "run-0004",
        "ts": "2026-07-26T09:00:00Z",
        "proposal_id": _PROPOSAL_ID,
        "approval_hash": "e" * 64,
        "operator": "matti",
    },
    "EDITED_SUPERSEDED": {
        "record_type": "EDITED_SUPERSEDED",
        "run_id": "run-0005",
        "ts": "2026-07-26T09:05:00Z",
        "old_proposal_id": _PROPOSAL_ID,
        "new_proposal_id": _OTHER_PROPOSAL_ID,
        "operator": "matti",
    },
    "REJECTED": {
        "record_type": "REJECTED",
        "run_id": "run-0006",
        "ts": "2026-07-26T09:10:00Z",
        "proposal_id": _PROPOSAL_ID,
        "operator": "matti",
    },
    "EXPIRED": {
        "record_type": "EXPIRED",
        "run_id": "run-0007",
        "ts": "2026-08-04T00:00:00Z",
        "proposal_id": _PROPOSAL_ID,
    },
    "STATE_APPLIED": {
        "record_type": "STATE_APPLIED",
        "run_id": "run-0004",
        "ts": "2026-07-26T09:00:01Z",
        "state_hash_before": "f" * 64,
        "state_hash_after": "1" * 64,
    },
}


@pytest.mark.parametrize("record_type", list(VALID_RECORDS))
def test_valid_record_of_every_type_validates(record_type):
    validate_journal_record(VALID_RECORDS[record_type])


def test_all_eight_record_types_covered():
    assert set(VALID_RECORDS) == {
        "PROPOSED",
        "REPLAY",
        "REPROPOSED_UNCHANGED",
        "APPROVED",
        "EDITED_SUPERSEDED",
        "REJECTED",
        "EXPIRED",
        "STATE_APPLIED",
    }


def test_unknown_record_type_rejected():
    bad = {"record_type": "MADE_UP", "run_id": "run-x", "ts": "2026-07-26T09:00:00Z"}
    with pytest.raises(ValidationError):
        validate_journal_record(bad)


def test_proposed_missing_origin_rejected():
    bad = copy.deepcopy(VALID_RECORDS["PROPOSED"])
    del bad["origin"]
    with pytest.raises(ValidationError):
        validate_journal_record(bad)


def test_proposed_wrong_proposal_id_shape_rejected():
    bad = copy.deepcopy(VALID_RECORDS["PROPOSED"])
    bad["proposal_id"] = "not-a-valid-id"
    with pytest.raises(ValidationError):
        validate_journal_record(bad)


def test_replay_cannot_be_typoed_as_proposed_fields():
    # REPLAY doesn't carry content_hash/input_manifest_hash -- adding
    # them (additionalProperties: false) must fail.
    bad = copy.deepcopy(VALID_RECORDS["REPLAY"])
    bad["content_hash"] = "c" * 64
    with pytest.raises(ValidationError):
        validate_journal_record(bad)


def test_state_applied_field_names_are_before_after():
    record = VALID_RECORDS["STATE_APPLIED"]
    assert record["state_hash_before"] != record["state_hash_after"]
