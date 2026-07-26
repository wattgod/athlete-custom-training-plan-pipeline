"""C1 hash discipline — acyclic view construction order.

docs/COACHING_LOOP_SPEC.md, C1: "Every hash is over an explicitly named
view (versioned projection), and no view contains any field derived from
its own hash." This module implements the construction order exactly as
listed (1-7):

1. dossier_rev            = H(dossier-view)
2. engine_state_hash      = H(base-state-view)
3. snapshot_hash          = H(snapshot-view)
4. content_hash           = H(proposal-content-view)
5. proposal_id, session_content_hash, session_id (derived ids)
6. input_manifest_hash    = H(input-manifest-view)
7. approval_hash          = H(content_hash | input_manifest_hash)

Hash algorithm everywhere: SHA-256. `H_view` hashes a canonical-JSON view.
`H_str` hashes a pipe-joined composite string (used for the derived ids,
which are explicitly specified as H(a|b|c) over scalar components, not
over a JSON view).

Each view function is a pure projection: given the full object, return
ONLY the fields the spec names for that view, with the fields the spec
excludes "by definition" stripped out. This is what keeps the graph
acyclic — a view function must never reach into a field that was itself
produced by hashing this same view.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from coaching_loop.canonical_json import canonical_bytes

# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def H_view(view: Any) -> str:
    """SHA-256 hex digest of the canonical-JSON encoding of `view`."""
    return hashlib.sha256(canonical_bytes(view)).hexdigest()


def H_str(composite: str) -> str:
    """SHA-256 hex digest of a raw pipe-joined composite string.

    Used for the derived ids (`proposal_id`, `session_id`), which the
    spec defines as H(field|field|field) over scalar components rather
    than H(view) over a JSON object.
    """
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# 1. dossier_rev = H(dossier-view)  — "dossier file minus nothing (pure content)"
# --------------------------------------------------------------------------


def dossier_view(dossier: Mapping[str, Any]) -> dict:
    """Pure content of the dossier file. Nothing is stripped."""
    return dict(dossier)


def dossier_rev(dossier: Mapping[str, Any]) -> str:
    return H_view(dossier_view(dossier))


# --------------------------------------------------------------------------
# 2. engine_state_hash = H(base-state-view)
# --------------------------------------------------------------------------
#
# "the stored `state_rev` field is set to this value and is NOT part of
# the view." Any other bookkeeping the store adds on top of the pure
# state (e.g. a `state_rev` field written back after computing the hash)
# must be excluded here to avoid the state hashing itself.

_BASE_STATE_EXCLUDED_FIELDS = {"state_rev"}


def base_state_view(engine_state: Mapping[str, Any]) -> dict:
    return {k: v for k, v in engine_state.items() if k not in _BASE_STATE_EXCLUDED_FIELDS}


def engine_state_hash(engine_state: Mapping[str, Any]) -> str:
    return H_view(base_state_view(engine_state))


# --------------------------------------------------------------------------
# 3. snapshot_hash = H(snapshot-view)
# --------------------------------------------------------------------------


def snapshot_view(snapshot: Mapping[str, Any]) -> dict:
    return dict(snapshot)


def snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    return H_view(snapshot_view(snapshot))


# --------------------------------------------------------------------------
# C2 session view / session_content_hash / session_id
# --------------------------------------------------------------------------
#
# "session_content_hash = H(session-view: day|sport|slot|source|
# library_item_id|structure|description|duration_hours|tss_est)"
# "session_id = 'sess-' + H(session_content_hash|ordinal)[:12]
# (ordinal disambiguates identical sessions within a week)."

_SESSION_VIEW_FIELDS = (
    "day",
    "sport",
    "slot",
    "source",
    "library_item_id",
    "structure",
    "description",
    "duration_hours",
    "tss_est",
)


def session_view(session: Mapping[str, Any]) -> dict:
    return {field: session.get(field) for field in _SESSION_VIEW_FIELDS}


def session_content_hash(session: Mapping[str, Any]) -> str:
    return H_view(session_view(session))


def session_id(session_content_hash_value: str, ordinal: int) -> str:
    return "sess-" + H_str(f"{session_content_hash_value}|{ordinal}")[:12]


# --------------------------------------------------------------------------
# 4. content_hash = H(proposal-content-view)
# --------------------------------------------------------------------------
#
# "content_hash = H(proposal-content-view) = {schema_version,
# capability_profile, athlete_id, week_start, sessions[] WITHOUT
# session_ids, adaptation_decisions, flags, exceptions, coverage_report,
# load_summary, engine_state_next (base-state-view form — contains NO
# proposal/journal references, see C3)}. Excluded by definition:
# proposal_id, session_ids, status, revision, input_manifest."
#
# "session_ids" here is read to cover BOTH per-session identity fields
# (session_id AND session_content_hash), not just session_id: C1's
# numbered order places content_hash at step 4 and lists
# session_content_hash alongside session_id and proposal_id under the
# "Derived ids" step 5 that comes AFTER it. Excluding only session_id
# and leaving session_content_hash in the content view would make step 4
# implicitly depend on part of step 5, contradicting the stated order.

_CONTENT_VIEW_TOP_FIELDS = (
    "schema_version",
    "capability_profile",
    "athlete_id",
    "week_start",
    "adaptation_decisions",
    "flags",
    "exceptions",
    "coverage_report",
    "load_summary",
)


def _session_without_id(session: Mapping[str, Any]) -> dict:
    # C1's numbered order puts content_hash at step 4 and BOTH
    # session_content_hash and session_id under the "Derived ids" step 5
    # that follows it -- so both are downstream of content_hash and
    # neither belongs in the content view, not just session_id. This
    # strip is defensive: it fires whether or not the caller already
    # attached the derived fields to the session dict.
    return {k: v for k, v in session.items() if k not in ("session_id", "session_content_hash")}


def content_view(proposal: Mapping[str, Any]) -> dict:
    view = {field: proposal.get(field) for field in _CONTENT_VIEW_TOP_FIELDS}
    sessions = proposal.get("sessions", [])
    view["sessions"] = [_session_without_id(s) for s in sessions]
    # engine_state_next is itself reduced to base-state-view form so it
    # cannot smuggle in a proposal/journal reference (state_rev included).
    view["engine_state_next"] = base_state_view(proposal.get("engine_state_next", {}))
    return view


def content_hash(proposal: Mapping[str, Any]) -> str:
    return H_view(content_view(proposal))


# --------------------------------------------------------------------------
# 5. Derived ids
# --------------------------------------------------------------------------
#
# "proposal_id = 'prop-' + H(athlete_id|week_start|content_hash)[:16]"


def proposal_id(athlete_id: int, week_start: str, content_hash_value: str) -> str:
    return "prop-" + H_str(f"{athlete_id}|{week_start}|{content_hash_value}")[:16]


# --------------------------------------------------------------------------
# 6. input_manifest_hash = H(input-manifest-view)
# --------------------------------------------------------------------------
#
# "input_manifest_hash = H(input-manifest-view) where the manifest =
# {snapshot_hash, dossier_rev, engine_state_hash, code_manifest, lexicon:
# {version, content_sha}}."

_INPUT_MANIFEST_FIELDS = (
    "snapshot_hash",
    "dossier_rev",
    "engine_state_hash",
    "code_manifest",
    "lexicon",
)


def input_manifest_view(
    *,
    snapshot_hash_value: str,
    dossier_rev_value: str,
    engine_state_hash_value: str,
    code_manifest: Mapping[str, Any],
    lexicon: Mapping[str, Any],
) -> dict:
    return {
        "snapshot_hash": snapshot_hash_value,
        "dossier_rev": dossier_rev_value,
        "engine_state_hash": engine_state_hash_value,
        "code_manifest": dict(code_manifest),
        "lexicon": {"version": lexicon.get("version"), "content_sha": lexicon.get("content_sha")},
    }


def input_manifest_hash(
    *,
    snapshot_hash_value: str,
    dossier_rev_value: str,
    engine_state_hash_value: str,
    code_manifest: Mapping[str, Any],
    lexicon: Mapping[str, Any],
) -> str:
    view = input_manifest_view(
        snapshot_hash_value=snapshot_hash_value,
        dossier_rev_value=dossier_rev_value,
        engine_state_hash_value=engine_state_hash_value,
        code_manifest=code_manifest,
        lexicon=lexicon,
    )
    return H_view(view)


# --------------------------------------------------------------------------
# 7. approval_hash = H(content_hash | input_manifest_hash)
# --------------------------------------------------------------------------
#
# "approval_hash = H(content_hash | input_manifest_hash) — what an
# approval binds to."


def approval_hash(content_hash_value: str, input_manifest_hash_value: str) -> str:
    return H_str(f"{content_hash_value}|{input_manifest_hash_value}")


# --------------------------------------------------------------------------
# Full artifact chain builder — used by the acyclicity/determinism tests
# --------------------------------------------------------------------------


def build_artifact_chain(
    *,
    dossier: Mapping[str, Any],
    engine_state: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    proposal_without_ids: Mapping[str, Any],
    code_manifest: Mapping[str, Any],
    lexicon: Mapping[str, Any],
) -> dict:
    """Construct the full C1 artifact chain from fixtures, in spec order.

    `proposal_without_ids` must already carry sessions (each session
    missing `session_id` AND `session_content_hash`, since both are
    derived below), schema_version, capability_profile, athlete_id,
    week_start, adaptation_decisions, flags, exceptions, coverage_report,
    load_summary, and engine_state_next.

    Step order matches C1's numbered list exactly: content_hash (step 4)
    is computed from `proposal_without_ids` AS GIVEN, strictly before any
    derived id (step 5, which includes session_content_hash and
    session_id, not just proposal_id) is computed. The derived ids are
    purely additive afterward -- they are attached to the returned,
    schema-shaped proposal object but never fed back into content_hash.

    Returns every hash/id in the chain plus the fully-assembled proposal
    (with session_id and proposal_id filled in), for tests to inspect.
    """
    d_rev = dossier_rev(dossier)
    es_hash = engine_state_hash(engine_state)
    snap_hash = snapshot_hash(snapshot)

    # Step 4: content_hash, computed before any derived id exists.
    c_hash = content_hash(proposal_without_ids)

    prop_id = proposal_id(
        proposal_without_ids["athlete_id"],
        proposal_without_ids["week_start"],
        c_hash,
    )

    # Step 5: session_content_hash / session_id, derived AFTER
    # content_hash and never re-fed into it.
    sessions_with_ids = []
    for ordinal, session in enumerate(proposal_without_ids.get("sessions", [])):
        sch = session_content_hash(session)
        sid = session_id(sch, ordinal)
        sessions_with_ids.append({**session, "session_content_hash": sch, "session_id": sid})

    manifest_hash = input_manifest_hash(
        snapshot_hash_value=snap_hash,
        dossier_rev_value=d_rev,
        engine_state_hash_value=es_hash,
        code_manifest=code_manifest,
        lexicon=lexicon,
    )

    appr_hash = approval_hash(c_hash, manifest_hash)

    full_proposal = {
        **proposal_without_ids,
        "sessions": sessions_with_ids,
        "proposal_id": prop_id,
        "content_hash": c_hash,
    }

    return {
        "dossier_rev": d_rev,
        "engine_state_hash": es_hash,
        "snapshot_hash": snap_hash,
        "content_hash": c_hash,
        "proposal_id": prop_id,
        "input_manifest_hash": manifest_hash,
        "approval_hash": appr_hash,
        "sessions": sessions_with_ids,
        "proposal": full_proposal,
    }
