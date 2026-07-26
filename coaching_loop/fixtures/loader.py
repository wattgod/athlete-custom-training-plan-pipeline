"""Loader for the CL-T0a synthetic fixture set (coaching_loop/fixtures/synthetic/).

Single place tests and the validation script get fixture data from. Every
`load_*` function returns a plain Python dict/list straight off the JSON
file (`_note` documentation keys included -- callers that hash a fixture
must strip them; `strip_notes` does that).

The lexicon manifest (`{version, content_sha}`, as C1's input-manifest
view wants it) is NOT a static file: `content_sha` is computed here, at
load time, from `lexicon_terms.json` via the real hash function. Hard-
coding it would silently drift the moment the terms file changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from coaching_loop.hashing import H_view, engine_state_hash

SYNTHETIC_DIR = Path(__file__).parent / "synthetic"

SYNTHETIC_ATHLETE_ID = 900001
EXCLUDED_FIXTURE_ATHLETE_ID = 418209
RESERVED_FIXTURE_ATHLETE_ID = 5959039


def _load(filename: str) -> Any:
    with (SYNTHETIC_DIR / filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def strip_notes(obj: Any) -> Any:
    """Drop `_note` documentation keys before an object is hashed or
    schema-validated; fixture files carry them for human readers, but
    they are not part of any C1 view or C2/C3 schema."""
    if isinstance(obj, dict):
        return {k: strip_notes(v) for k, v in obj.items() if k != "_note"}
    if isinstance(obj, list):
        return [strip_notes(v) for v in obj]
    return obj


def load_dossier(athlete_id: int = SYNTHETIC_ATHLETE_ID) -> dict:
    return strip_notes(_load(f"dossier_{athlete_id}.json"))


def load_engine_state(athlete_id: int = SYNTHETIC_ATHLETE_ID) -> dict:
    """The base-state-view shape (no `state_rev`) -- what the fixture file
    on disk actually contains, and what coaching_loop.hashing functions
    take as `engine_state`/`base_engine_state` input. Validates against
    engine_state_base_view.schema.json, not engine_state.schema.json."""
    return strip_notes(_load(f"engine_state_{athlete_id}.json"))


def load_stored_engine_state(athlete_id: int = SYNTHETIC_ATHLETE_ID) -> dict:
    """The STORED form (engine_state.yaml shape): base-state-view plus a
    computed `state_rev`. Like the lexicon content_sha below, state_rev
    is computed live from the base view rather than hardcoded in the
    fixture file, so it can never drift from the content it names.
    Validates against engine_state.schema.json."""
    base = load_engine_state(athlete_id)
    return {**base, "state_rev": engine_state_hash(base)}


def load_tp_snapshot(athlete_id: int = SYNTHETIC_ATHLETE_ID) -> dict:
    return strip_notes(_load(f"tp_snapshot_{athlete_id}.json"))


def load_proposal_skeleton(athlete_id: int = SYNTHETIC_ATHLETE_ID) -> dict:
    return strip_notes(_load(f"proposal_skeleton_{athlete_id}.json"))


def load_code_manifest() -> dict:
    return strip_notes(_load("code_manifest.json"))


def load_lexicon_terms() -> dict:
    return strip_notes(_load("lexicon_terms.json"))


def load_lexicon_manifest() -> dict:
    """{version, content_sha} form C1's input-manifest view wants -- NOT
    the full terms file. content_sha is H_view(terms), computed fresh."""
    terms = load_lexicon_terms()
    return {"version": terms["version"], "content_sha": H_view(terms)}


def all_synthetic_athlete_ids() -> list[int]:
    return [SYNTHETIC_ATHLETE_ID]
