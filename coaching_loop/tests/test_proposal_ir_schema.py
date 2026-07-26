"""C2 ProposalIR v1 schema tests over the artifact-chain-derived proposal."""

from __future__ import annotations

import copy

import pytest
from jsonschema.exceptions import ValidationError

from coaching_loop.validation import validate_proposal_ir


def test_full_proposal_from_artifact_chain_validates(full_proposal):
    validate_proposal_ir(full_proposal)


def test_engine_state_next_cross_reference_resolves(full_proposal):
    # Proves the $ref to engine_state_base_view.schema.json resolved and
    # was actually applied, not silently skipped -- corrupt it and
    # confirm the referenced schema's own constraints fire through the
    # $ref.
    bad = copy.deepcopy(full_proposal)
    del bad["engine_state_next"]["season"]
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_engine_state_next_rejects_state_rev(full_proposal):
    # C1 #2: "the stored state_rev field is set to this value and is NOT
    # part of the view" -- engine_state_next is base-state-view form and
    # must reject state_rev outright, not merely omit it as optional.
    bad = copy.deepcopy(full_proposal)
    bad["engine_state_next"]["state_rev"] = "a" * 64
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "capability_profile",
        "proposal_id",
        "content_hash",
        "athlete_id",
        "week_start",
        "revision",
        "status",
        "input_manifest",
        "origin",
        "sessions",
        "adaptation_decisions",
        "flags",
        "exceptions",
        "coverage_report",
        "load_summary",
        "engine_state_next",
    ],
)
def test_every_header_field_is_required(full_proposal, field):
    bad = copy.deepcopy(full_proposal)
    del bad[field]
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_unknown_status_value_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["status"] = "made_up_status"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_all_five_status_values_individually_valid(full_proposal):
    for status in ("proposed", "approved", "edited_superseded", "rejected", "expired"):
        candidate = copy.deepcopy(full_proposal)
        candidate["status"] = status
        validate_proposal_ir(candidate)


def test_unknown_origin_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["origin"] = "coach_wrote_it_by_hand"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_proposal_id_shape_enforced(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["proposal_id"] = "prop-not-hex"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_session_missing_required_field_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    del bad["sessions"][0]["duration_hours"]
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_session_unknown_slot_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["sessions"][0]["slot"] = "made_up_slot"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_exception_blocking_field_must_be_boolean(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["exceptions"] = [{"exception_id": "exc-1", "type": "W-6", "blocking": "yes"}]
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_exception_valid_shape_accepted(full_proposal):
    good = copy.deepcopy(full_proposal)
    good["exceptions"] = [{"exception_id": "exc-1", "type": "W-6", "blocking": True}]
    validate_proposal_ir(good)


def test_additional_top_level_property_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["not_in_contract"] = "nope"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)
