"""Shared fixtures for coaching_loop tests."""

from __future__ import annotations

import pytest

from coaching_loop.fixtures.loader import (
    load_code_manifest,
    load_dossier,
    load_engine_state,
    load_lexicon_manifest,
    load_proposal_skeleton,
    load_tp_snapshot,
)
from coaching_loop.hashing import build_artifact_chain


def _build_chain():
    return build_artifact_chain(
        dossier=load_dossier(),
        engine_state=load_engine_state(),
        snapshot=load_tp_snapshot(),
        proposal_without_ids=load_proposal_skeleton(),
        code_manifest=load_code_manifest(),
        lexicon=load_lexicon_manifest(),
    )


@pytest.fixture
def artifact_chain():
    """The full C1 artifact chain built from the synthetic fixture set."""
    return _build_chain()


@pytest.fixture
def full_proposal(artifact_chain):
    """A schema-shaped ProposalIR v1 instance, header fields filled in
    from the artifact chain, ready to validate against proposal_ir.schema.json."""
    chain = artifact_chain
    proposal = dict(chain["proposal"])
    proposal.setdefault("status", "proposed")
    proposal.setdefault("origin", "engine")
    proposal["revision"] = 1
    proposal["input_manifest"] = {
        "snapshot_hash": chain["snapshot_hash"],
        "dossier_rev": chain["dossier_rev"],
        "engine_state_hash": chain["engine_state_hash"],
        "code_manifest": load_code_manifest(),
        "lexicon": load_lexicon_manifest(),
    }
    return proposal
