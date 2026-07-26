"""C5: 'Replay: same (snapshot, dossier, base state, code_manifest,
lexicon) -> identical content_hash.' This proves HASHING determinism --
build_artifact_chain called twice on byte-identical fixture inputs
yields identical hashes -- which is what the CI golden-replay test (owned
by later tickets) depends on. It is NOT a test of the full pure-function
generation signature ("(snapshot, dossier, base_engine_state,
code_manifest, lexicon) -- nothing else may be read", C1); that signature
belongs to actual proposal GENERATION (CL-T3c), which does not exist yet
-- `proposal_without_ids` here is a prebuilt fixture, not something these
five inputs produced.
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
from coaching_loop.hashing import build_artifact_chain


def _build():
    return build_artifact_chain(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        proposal_without_ids=load_proposal_skeleton(),
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )


def test_repeated_builds_from_identical_fixtures_are_byte_identical():
    chain1 = _build()
    chain2 = _build()
    assert chain1["content_hash"] == chain2["content_hash"]
    assert chain1["proposal_id"] == chain2["proposal_id"]
    assert chain1["input_manifest_hash"] == chain2["input_manifest_hash"]
    assert chain1["approval_hash"] == chain2["approval_hash"]


def test_key_order_does_not_affect_content_hash():
    proposal_without_ids = load_proposal_skeleton()
    reordered = {k: proposal_without_ids[k] for k in reversed(list(proposal_without_ids.keys()))}

    common_kwargs = dict(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )
    chain_a = build_artifact_chain(proposal_without_ids=proposal_without_ids, **common_kwargs)
    chain_b = build_artifact_chain(proposal_without_ids=reordered, **common_kwargs)
    assert chain_a["content_hash"] == chain_b["content_hash"]


def test_equivalent_float_and_int_tss_are_the_same_hash():
    proposal_without_ids = copy.deepcopy(load_proposal_skeleton())
    proposal_without_ids["sessions"][0]["tss_est"] = 85.0  # integral float

    proposal_without_ids_int = copy.deepcopy(load_proposal_skeleton())
    proposal_without_ids_int["sessions"][0]["tss_est"] = 85  # int

    common_kwargs = dict(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )
    chain_float = build_artifact_chain(proposal_without_ids=proposal_without_ids, **common_kwargs)
    chain_int = build_artifact_chain(proposal_without_ids=proposal_without_ids_int, **common_kwargs)
    assert chain_float["content_hash"] == chain_int["content_hash"]


def test_content_changing_field_changes_content_hash():
    baseline = _build()

    mutated = copy.deepcopy(load_proposal_skeleton())
    mutated["sessions"][0]["duration_hours"] = 2.0  # was 1.5

    changed = build_artifact_chain(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        proposal_without_ids=mutated,
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )
    assert changed["content_hash"] != baseline["content_hash"]
    assert changed["proposal_id"] != baseline["proposal_id"]


def test_different_code_manifest_changes_input_manifest_and_approval_hash_but_not_content_hash():
    baseline = _build()

    changed = build_artifact_chain(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        proposal_without_ids=load_proposal_skeleton(),
        code_manifest={"git_sha": "1" * 40, "dirty": True, "dirty_paths": ["coaching_loop/hashing.py"]},
        lexicon=load_lexicon_manifest(),
    )
    assert changed["content_hash"] == baseline["content_hash"]
    assert changed["input_manifest_hash"] != baseline["input_manifest_hash"]
    assert changed["approval_hash"] != baseline["approval_hash"]
