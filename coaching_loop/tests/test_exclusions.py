"""Hard scope boundary: code-enforced exclusion of athlete 418209.

docs/COACHING_LOOP_SPEC.md: "Checked (raise) in fetch, resolve, propose,
brief, approvals parsing, placement." This file proves both the raw
exclusions API and every one of the six entry-point stubs reject a
fixture bundle containing 418209, and that 5959039 is flagged
reserved-for-T0b (not excluded, not pilot-eligible) rather than excluded.
"""

from __future__ import annotations

import pytest

from coaching_loop.entry_points import ENTRY_POINTS
from coaching_loop.exclusions import (
    EXCLUDED_ATHLETE_IDS,
    RESERVED_ATHLETE_IDS,
    ExcludedAthleteError,
    NonCoercibleAthleteIdError,
    ReservedAthleteError,
    assert_not_excluded,
    assert_pilot_eligible,
    normalize_athlete_id,
)
from coaching_loop.fixtures.loader import (
    EXCLUDED_FIXTURE_ATHLETE_ID,
    RESERVED_FIXTURE_ATHLETE_ID,
    SYNTHETIC_ATHLETE_ID,
    load_tp_snapshot,
)


def test_excluded_set_is_exactly_418209():
    assert EXCLUDED_ATHLETE_IDS == frozenset({418209})


def test_reserved_set_is_exactly_5959039():
    assert RESERVED_ATHLETE_IDS == frozenset({5959039})


def test_reserved_athlete_not_in_excluded_set():
    # 5959039 is reserved for T0b, not excluded -- these must not overlap.
    assert RESERVED_ATHLETE_IDS.isdisjoint(EXCLUDED_ATHLETE_IDS)


@pytest.mark.parametrize("value", [418209, "418209", " 418209 ", 418209.0])
def test_assert_not_excluded_rejects_418209_any_coercible_form(value):
    with pytest.raises(ExcludedAthleteError):
        assert_not_excluded(value)


def test_assert_not_excluded_allows_pilot_athlete():
    assert assert_not_excluded(SYNTHETIC_ATHLETE_ID) == SYNTHETIC_ATHLETE_ID


def test_assert_not_excluded_allows_reserved_athlete():
    # 5959039 is NOT excluded -- fetch/resolve/etc must still work for it
    # once CL-T0b is authorized.
    assert assert_not_excluded(RESERVED_FIXTURE_ATHLETE_ID) == RESERVED_FIXTURE_ATHLETE_ID


def test_assert_pilot_eligible_rejects_reserved_athlete():
    with pytest.raises(ReservedAthleteError):
        assert_pilot_eligible(RESERVED_FIXTURE_ATHLETE_ID)


def test_assert_pilot_eligible_rejects_excluded_athlete():
    with pytest.raises(ExcludedAthleteError):
        assert_pilot_eligible(EXCLUDED_FIXTURE_ATHLETE_ID)


def test_assert_pilot_eligible_allows_synthetic_pilot_athlete():
    assert assert_pilot_eligible(SYNTHETIC_ATHLETE_ID) == SYNTHETIC_ATHLETE_ID


@pytest.mark.parametrize("value", [None, "not-a-number", object(), True, False, "12.5"])
def test_normalize_athlete_id_rejects_non_coercible(value):
    with pytest.raises(NonCoercibleAthleteIdError):
        normalize_athlete_id(value)


def test_normalize_athlete_id_coerces_int_like_strings():
    assert normalize_athlete_id("418209") == 418209


@pytest.mark.parametrize("layer", list(ENTRY_POINTS))
def test_every_entry_point_rejects_excluded_fixture_bundle(layer):
    """The 6-layer rule: fetch, resolve, propose, brief,
    approvals_parsing, placement each raise on a bundle carrying 418209."""
    bundle = {"athlete_id": EXCLUDED_FIXTURE_ATHLETE_ID, "snapshot": load_tp_snapshot(EXCLUDED_FIXTURE_ATHLETE_ID)}
    entry_fn = ENTRY_POINTS[layer]
    with pytest.raises(ExcludedAthleteError) as excinfo:
        entry_fn(bundle)
    assert excinfo.value.layer == layer
    assert excinfo.value.athlete_id == EXCLUDED_FIXTURE_ATHLETE_ID


@pytest.mark.parametrize("layer", list(ENTRY_POINTS))
def test_every_entry_point_accepts_pilot_fixture_bundle(layer):
    bundle = {"athlete_id": SYNTHETIC_ATHLETE_ID, "snapshot": load_tp_snapshot(SYNTHETIC_ATHLETE_ID)}
    entry_fn = ENTRY_POINTS[layer]
    result = entry_fn(bundle)
    assert result["athlete_id"] == SYNTHETIC_ATHLETE_ID


def test_six_named_layers_are_exactly_the_spec_list():
    assert set(ENTRY_POINTS) == {
        "fetch",
        "resolve",
        "propose",
        "brief",
        "approvals_parsing",
        "placement",
    }
