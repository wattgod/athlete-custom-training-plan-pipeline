"""C3 base engine state schema tests -- STORED form vs base-state-view form.

engine_state.schema.json (STORED, engine_state.yaml shape) always carries
`state_rev`. engine_state_base_view.schema.json (the C1 #2 hash input,
and what a ProposalIR's `engine_state_next` must be) structurally
forbids it -- "the stored state_rev field is set to this value and is
NOT part of the view." These are deliberately two schemas, not one with
an optional field, so a proposal can never carry `engine_state_next.
state_rev` and validate.
"""

from __future__ import annotations

import copy

import pytest
from jsonschema.exceptions import ValidationError

from coaching_loop.fixtures.loader import (
    load_engine_state,
    load_proposal_skeleton,
    load_stored_engine_state,
)
from coaching_loop.hashing import base_state_view, engine_state_hash
from coaching_loop.validation import validate_engine_state, validate_engine_state_base_view


def test_synthetic_stored_engine_state_validates():
    validate_engine_state(load_stored_engine_state())


def test_synthetic_base_view_engine_state_validates():
    validate_engine_state_base_view(load_engine_state())


def test_stored_schema_requires_state_rev():
    state = copy.deepcopy(load_stored_engine_state())
    del state["state_rev"]
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_stored_schema_rejects_non_hex_state_rev():
    state = copy.deepcopy(load_stored_engine_state())
    state["state_rev"] = "not-hex"
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_base_view_schema_rejects_state_rev_outright():
    # The bug this schema split fixes: a base-state-view object (like
    # engine_state_next) must not validate if it carries state_rev at
    # all, present or absent from `required` is not enough -- it must be
    # structurally impossible.
    state = copy.deepcopy(load_engine_state())
    state["state_rev"] = "a" * 64
    with pytest.raises(ValidationError):
        validate_engine_state_base_view(state)


def test_engine_state_next_from_proposal_skeleton_validates_as_base_view():
    proposal = load_proposal_skeleton()
    validate_engine_state_base_view(proposal["engine_state_next"])


def test_engine_state_next_with_state_rev_is_rejected():
    # Direct regression test for the sol-review-confirmed conflation bug:
    # a ProposalIR whose engine_state_next carries state_rev must fail
    # proposal_ir.schema.json validation (exercised end-to-end in
    # test_proposal_ir_schema.py); here it's isolated to the
    # engine_state_next sub-schema itself.
    proposal = load_proposal_skeleton()
    es_next = copy.deepcopy(proposal["engine_state_next"])
    es_next["state_rev"] = "a" * 64
    with pytest.raises(ValidationError):
        validate_engine_state_base_view(es_next)


def test_stored_state_rev_matches_hash_of_its_own_base_view():
    # base_state_view() strips state_rev from the stored object; the
    # result must equal the plain base-view fixture and must hash to the
    # state_rev the loader attached.
    stored = load_stored_engine_state()
    base = load_engine_state()
    assert base_state_view(stored) == base
    assert engine_state_hash(stored) == stored["state_rev"]


def test_base_state_view_strips_state_rev():
    state = copy.deepcopy(load_stored_engine_state())
    view = base_state_view(state)
    assert "state_rev" not in view
    assert view["athlete_id"] == state["athlete_id"]


def test_schema_rejects_missing_season():
    state = copy.deepcopy(load_stored_engine_state())
    del state["season"]
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_schema_rejects_nothing_about_proposals_leaking_in():
    # C3: "NOTHING about proposals/approvals lives here." -- structurally
    # enforced by additionalProperties: false at the top level.
    state = copy.deepcopy(load_stored_engine_state())
    state["proposal_id"] = "prop-" + "a" * 16
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_ownership_registry_keys_must_be_dates():
    state = copy.deepcopy(load_stored_engine_state())
    state["ownership_registry"] = {"proposal_id": ["wo-1"]}
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_resolution_input_hash_must_be_sha256_hex():
    state = copy.deepcopy(load_stored_engine_state())
    state["season"]["resolution_input_hash"] = "not-a-hash"
    with pytest.raises(ValidationError):
        validate_engine_state(state)


def test_recent_races_is_a_rolling_list_of_typed_entries():
    proposal = load_proposal_skeleton()
    races = proposal["engine_state_next"]["recent_races"]
    assert races
    for race in races:
        assert set(race.keys()) == {"date", "sport", "priority"}
