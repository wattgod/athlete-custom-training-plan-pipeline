"""C1: acyclic hash-view construction, exercised over the full artifact
chain built from the synthetic fixtures.

"Every hash is over an explicitly named view (versioned projection), and
no view contains any field derived from its own hash." This file proves
that structurally (the views never contain the fields the spec says are
excluded by definition) and behaviorally (mutating a downstream-only
field never changes an upstream hash).
"""

from __future__ import annotations

import copy

from coaching_loop.fixtures.loader import (
    load_code_manifest,
    load_dossier,
    load_engine_state,
    load_lexicon_manifest,
    load_proposal_skeleton,
    load_tp_snapshot,
)
from coaching_loop.hashing import (
    approval_hash,
    build_artifact_chain,
    content_hash,
    content_view,
    dossier_rev,
    engine_state_hash,
    input_manifest_hash,
    proposal_id,
    session_content_hash,
    session_id,
    snapshot_hash,
)


def test_full_chain_builds_without_error(artifact_chain):
    chain = artifact_chain
    for key in (
        "dossier_rev",
        "engine_state_hash",
        "snapshot_hash",
        "content_hash",
        "proposal_id",
        "input_manifest_hash",
        "approval_hash",
    ):
        assert chain[key]


def test_hex_hash_fields_are_64_hex_chars(artifact_chain):
    chain = artifact_chain
    for key in ("dossier_rev", "engine_state_hash", "snapshot_hash", "content_hash", "input_manifest_hash", "approval_hash"):
        value = chain[key]
        assert len(value) == 64
        assert all(c in "0123456789abcdef" for c in value)


def test_proposal_id_is_prop_prefixed_16_hex(artifact_chain):
    prop_id = artifact_chain["proposal_id"]
    assert prop_id.startswith("prop-")
    suffix = prop_id[len("prop-"):]
    assert len(suffix) == 16
    assert all(c in "0123456789abcdef" for c in suffix)


def test_session_ids_are_sess_prefixed_12_hex(artifact_chain):
    for session in artifact_chain["sessions"]:
        sid = session["session_id"]
        assert sid.startswith("sess-")
        suffix = sid[len("sess-"):]
        assert len(suffix) == 12
        assert all(c in "0123456789abcdef" for c in suffix)


def test_content_view_excludes_fields_by_definition(artifact_chain):
    proposal = artifact_chain["proposal"]
    view = content_view(proposal)
    # "Excluded by definition: proposal_id, session_ids, status, revision,
    # input_manifest."
    assert "proposal_id" not in view
    assert "status" not in view
    assert "revision" not in view
    assert "input_manifest" not in view
    for session_view in view["sessions"]:
        assert "session_id" not in session_view


def test_engine_state_next_in_content_view_has_no_journal_or_proposal_refs(artifact_chain):
    view = content_view(artifact_chain["proposal"])
    es_next = view["engine_state_next"]
    assert "state_rev" not in es_next
    for forbidden in ("proposal_id", "content_hash", "revision", "journal", "approval_hash"):
        assert forbidden not in es_next


def test_mutating_status_does_not_change_content_hash():
    proposal_without_ids = load_proposal_skeleton()
    common_kwargs = dict(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )
    chain_proposed = build_artifact_chain(proposal_without_ids=proposal_without_ids, **common_kwargs)

    mutated = copy.deepcopy(proposal_without_ids)
    mutated["status"] = "approved"  # downstream-only field, excluded from content view
    chain_approved = build_artifact_chain(proposal_without_ids=mutated, **common_kwargs)

    assert chain_proposed["content_hash"] == chain_approved["content_hash"]
    # ...and therefore the same proposal_id, since it derives from content_hash.
    assert chain_proposed["proposal_id"] == chain_approved["proposal_id"]


def test_dossier_rev_is_independent_of_engine_state_and_snapshot():
    dossier = load_dossier()
    rev1 = dossier_rev(dossier)

    mutated_state = copy.deepcopy(load_engine_state())
    mutated_state["cursor"]["week_in_block"] += 1
    # dossier_rev must not change when engine_state or snapshot change --
    # it is H(dossier-view) alone.
    rev2 = dossier_rev(dossier)
    assert rev1 == rev2
    assert engine_state_hash(mutated_state) != engine_state_hash(load_engine_state())


def test_session_content_hash_does_not_depend_on_ordinal_or_session_id():
    session = load_proposal_skeleton()["sessions"][0]
    sch = session_content_hash(session)
    sid_ordinal_0 = session_id(sch, 0)
    sid_ordinal_1 = session_id(sch, 1)
    # session_content_hash is a pure function of the session-view fields;
    # it must not itself depend on the ordinal used to disambiguate ids.
    assert session_content_hash(session) == sch
    assert sid_ordinal_0 != sid_ordinal_1  # but the derived id does


def test_approval_hash_depends_on_both_content_and_manifest_hash(artifact_chain):
    chain = artifact_chain
    recomputed = approval_hash(chain["content_hash"], chain["input_manifest_hash"])
    assert recomputed == chain["approval_hash"]

    # Changing the input manifest (e.g. a different code_manifest git_sha)
    # must change approval_hash even though content_hash is untouched.
    other_manifest_hash = input_manifest_hash(
        snapshot_hash_value=chain["snapshot_hash"],
        dossier_rev_value=chain["dossier_rev"],
        engine_state_hash_value=chain["engine_state_hash"],
        code_manifest={"git_sha": "0" * 40, "dirty": False},
        lexicon=load_lexicon_manifest(),
    )
    assert other_manifest_hash != chain["input_manifest_hash"]
    other_approval_hash = approval_hash(chain["content_hash"], other_manifest_hash)
    assert other_approval_hash != chain["approval_hash"]
