"""sol r2 f12 / v1.0 scope: 'ProposalIR header carries capability_profile:
"v1.0-proposal-only"; schema validation REJECTS any tp_op other than add
under that profile.'
"""

from __future__ import annotations

import copy

import pytest
from jsonschema.exceptions import ValidationError

from coaching_loop.validation import validate_proposal_ir, validate_tp_op_grammar


def test_add_op_passes_under_v1_0_profile(full_proposal):
    assert full_proposal["capability_profile"] == "v1.0-proposal-only"
    validate_proposal_ir(full_proposal)  # every session already {op: add}


@pytest.mark.parametrize(
    "tp_op",
    [
        {"op": "replace", "target_workout_id": "wo-1", "target_fingerprint": "fp-1"},
        {"op": "delete", "target_workout_id": "wo-1", "target_fingerprint": "fp-1"},
    ],
)
def test_non_add_op_rejected_under_v1_0_profile(full_proposal, tp_op):
    bad = copy.deepcopy(full_proposal)
    bad["sessions"][0]["tp_op"] = tp_op
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_non_add_op_rejected_even_when_only_one_of_several_sessions_is_bad(full_proposal):
    bad = copy.deepcopy(full_proposal)
    assert len(bad["sessions"]) >= 2, "fixture must exercise multiple sessions"
    bad["sessions"][1]["tp_op"] = {"op": "delete", "target_workout_id": "wo-9", "target_fingerprint": "fp-9"}
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_unknown_capability_profile_value_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["capability_profile"] = "v1.1-full-ops"
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_missing_op_key_rejected(full_proposal):
    bad = copy.deepcopy(full_proposal)
    bad["sessions"][0]["tp_op"] = {}
    with pytest.raises(ValidationError):
        validate_proposal_ir(bad)


def test_add_op_rejects_stray_fields():
    # {op: add} takes no other keys -- catches a caller accidentally
    # carrying replace/delete fields on an add op.
    with pytest.raises(ValidationError):
        validate_tp_op_grammar({"op": "add", "target_workout_id": "wo-1"})


class TestFullOpGrammarSpecifiedNowForV1_1:
    """C2: 'Full op grammar (v1.1+, specified now): add | replace{...} |
    delete{...}.' These validate the grammar shape directly (bypassing
    the v1.0 header restriction) to prove the grammar itself is complete,
    even though nothing in v1.0 can ever emit a non-add op."""

    def test_add(self):
        validate_tp_op_grammar({"op": "add"})

    def test_replace_requires_target_fields(self):
        validate_tp_op_grammar(
            {"op": "replace", "target_workout_id": "wo-1", "target_fingerprint": "fp-1"}
        )
        with pytest.raises(ValidationError):
            validate_tp_op_grammar({"op": "replace"})

    def test_delete_requires_target_fields(self):
        validate_tp_op_grammar(
            {"op": "delete", "target_workout_id": "wo-1", "target_fingerprint": "fp-1"}
        )
        with pytest.raises(ValidationError):
            validate_tp_op_grammar({"op": "delete"})

    def test_unknown_op_rejected(self):
        with pytest.raises(ValidationError):
            validate_tp_op_grammar({"op": "reorder"})
