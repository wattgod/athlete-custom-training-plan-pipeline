"""Golden-digest tests for the derived-id formulas, computed with a
hashlib call in the test itself (not by importing coaching_loop.hashing's
H_str/H_view helpers as the oracle) -- proves the ID formulas match C1's
literal text, not just "whatever the implementation currently does":

    proposal_id = "prop-" + H(athlete_id|week_start|content_hash)[:16]
    session_id  = "sess-" + H(session_content_hash|ordinal)[:12]
"""

from __future__ import annotations

import hashlib

from coaching_loop.hashing import proposal_id, session_content_hash, session_id


def test_proposal_id_golden_digest():
    athlete_id, week_start, content_hash_value = 900001, "2026-07-27", "b" * 64
    composite = f"{athlete_id}|{week_start}|{content_hash_value}"
    expected_full = hashlib.sha256(composite.encode("utf-8")).hexdigest()
    expected = "prop-" + expected_full[:16]
    assert proposal_id(athlete_id, week_start, content_hash_value) == expected


def test_session_id_golden_digest():
    sch, ordinal = "c" * 64, 5
    composite = f"{sch}|{ordinal}"
    expected_full = hashlib.sha256(composite.encode("utf-8")).hexdigest()
    expected = "sess-" + expected_full[:12]
    assert session_id(sch, ordinal) == expected


def test_session_content_hash_golden_digest_over_a_known_session():
    session = {
        "day": "2026-07-28",
        "sport": "bike",
        "slot": "quality",
        "source": "library",
        "library_item_id": "sst-3x12",
        "structure": None,
        "description": "SST 3x12",
        "duration_hours": 1.5,
        "tss_est": 85,
        # Extra field NOT in the session-view -- must not affect the hash.
        "tp_op": {"op": "add"},
    }
    # Independently reconstruct the exact canonical string by hand,
    # matching canonical_json's documented rules (sorted keys, no
    # whitespace, integral float as int) rather than calling
    # canonical_json() itself.
    expected_canonical = (
        '{"day":"2026-07-28","description":"SST 3x12","duration_hours":1.5,'
        '"library_item_id":"sst-3x12","slot":"quality","source":"library",'
        '"sport":"bike","structure":null,"tss_est":85}'
    )
    expected = hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest()
    assert session_content_hash(session) == expected


def test_proposal_id_changes_if_any_composite_component_changes():
    base = proposal_id(900001, "2026-07-27", "b" * 64)
    assert proposal_id(900002, "2026-07-27", "b" * 64) != base
    assert proposal_id(900001, "2026-08-03", "b" * 64) != base
    assert proposal_id(900001, "2026-07-27", "c" * 64) != base
