"""The six exclusion-enforcement layers named by the spec.

docs/COACHING_LOOP_SPEC.md, Hard scope boundaries: "Checked (raise) in
fetch, resolve, propose, brief, approvals parsing, placement."

Real fetch/resolve/propose/brief/approvals-parsing/placement logic lands
in later tickets (T1, T2a, T3c, T6, T7). What CL-T0a guarantees now is
that every one of those six boundaries runs `assert_not_excluded` before
any bundle-specific logic can see the athlete id — so a later ticket
cannot reintroduce access to an excluded athlete by skipping the check.
Each function here is a minimal pass-through stub: normalize + assert,
then return the bundle unchanged (with athlete_id normalized to int).
"""

from __future__ import annotations

from typing import Any, Mapping

from coaching_loop.exclusions import assert_not_excluded


def _athlete_id_of(bundle: Mapping[str, Any]) -> Any:
    return bundle.get("athlete_id")


def fetch_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 1: TP read fetch. Raises ExcludedAthleteError for 418209."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="fetch")
    return {**bundle, "athlete_id": athlete_id}


def resolve_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 2: WeekContext / season resolution."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="resolve")
    return {**bundle, "athlete_id": athlete_id}


def propose_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 3: proposal generation."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="propose")
    return {**bundle, "athlete_id": athlete_id}


def brief_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 4: coach review brief assembly."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="brief")
    return {**bundle, "athlete_id": athlete_id}


def approvals_parsing_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 5: C4 approvals entry parsing."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="approvals_parsing")
    return {**bundle, "athlete_id": athlete_id}


def placement_entry(bundle: Mapping[str, Any]) -> dict:
    """Layer 6: TP placement (v1.1+, CL-T7)."""
    athlete_id = assert_not_excluded(_athlete_id_of(bundle), layer="placement")
    return {**bundle, "athlete_id": athlete_id}


ENTRY_POINTS = {
    "fetch": fetch_entry,
    "resolve": resolve_entry,
    "propose": propose_entry,
    "brief": brief_entry,
    "approvals_parsing": approvals_parsing_entry,
    "placement": placement_entry,
}
