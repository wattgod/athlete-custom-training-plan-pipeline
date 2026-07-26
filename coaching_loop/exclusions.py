"""Code-enforced athlete exclusion — Hard scope boundaries, CL-T0a.

docs/COACHING_LOOP_SPEC.md: "Exclusion (technical): coaching_loop/
exclusions.py -> EXCLUDED_ATHLETE_IDS: frozenset[int] = {418209} (Anthony,
Matti standing instruction 2026-07-23). normalize_athlete_id() -> int at
every module boundary (non-coercible -> error). Checked (raise) in fetch,
resolve, propose, brief, approvals parsing, placement. Lands in CL-T0a.
Removal requires a Matti-authored commit."

Athlete 5959039 is reserved for CL-T0b (live-mutation test athlete) per
§Ratified answers #1 and #5. It is NOT excluded — it may be fetched,
resolved, etc. once T0b is authorized — but it may never be a pilot
roster seat. `assert_pilot_eligible` enforces that distinction.

Do not remove or edit EXCLUDED_ATHLETE_IDS without an explicit
Matti-authored commit.
"""

from __future__ import annotations

from typing import Any

EXCLUDED_ATHLETE_IDS: frozenset[int] = frozenset({418209})

# Reserved for the CL-T0b live-mutation spike (test athlete 5959039).
# Not excluded from fetch/resolve/etc; excluded from pilot-roster
# eligibility only. See §Ratified answers #1, #5.
RESERVED_ATHLETE_IDS: frozenset[int] = frozenset({5959039})


class AthleteIdError(ValueError):
    """Base class for athlete-id boundary errors."""


class NonCoercibleAthleteIdError(AthleteIdError):
    """Raised when a value cannot be normalized to an int athlete id."""


class ExcludedAthleteError(AthleteIdError):
    """Raised when a code-excluded athlete id reaches an enforcement point."""

    def __init__(self, athlete_id: int, layer: str | None = None):
        self.athlete_id = athlete_id
        self.layer = layer
        where = f" at layer {layer!r}" if layer else ""
        super().__init__(f"athlete {athlete_id} is code-excluded{where}")


class ReservedAthleteError(AthleteIdError):
    """Raised when a pilot-roster check hits the T0b-reserved athlete id."""

    def __init__(self, athlete_id: int, layer: str | None = None):
        self.athlete_id = athlete_id
        self.layer = layer
        where = f" at layer {layer!r}" if layer else ""
        super().__init__(
            f"athlete {athlete_id} is reserved for CL-T0b (not pilot-eligible){where}"
        )


def normalize_athlete_id(value: Any) -> int:
    """Coerce `value` to an int athlete id; raise if it cannot be coerced.

    Bools are rejected explicitly (bool is an int subclass in Python, but
    an athlete id of `True`/`False` is always a bug, never a legitimate
    id) — spec's "non-coercible -> error" is read to include this case.
    """
    if isinstance(value, bool):
        raise NonCoercibleAthleteIdError(f"athlete_id must not be a bool: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or not (stripped.lstrip("-").isdigit()):
            raise NonCoercibleAthleteIdError(f"athlete_id not coercible to int: {value!r}")
        return int(stripped)
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise NonCoercibleAthleteIdError(f"athlete_id not coercible to int: {value!r}")
    raise NonCoercibleAthleteIdError(f"athlete_id not coercible to int: {value!r}")


def assert_not_excluded(value: Any, *, layer: str | None = None) -> int:
    """Normalize `value` and raise ExcludedAthleteError if it is excluded.

    Returns the normalized int athlete id on success. This is the single
    check that must run at every one of the spec's six enforcement
    layers: fetch, resolve, propose, brief, approvals parsing, placement.
    """
    athlete_id = normalize_athlete_id(value)
    if athlete_id in EXCLUDED_ATHLETE_IDS:
        raise ExcludedAthleteError(athlete_id, layer=layer)
    return athlete_id


def assert_pilot_eligible(value: Any, *, layer: str | None = None) -> int:
    """As `assert_not_excluded`, plus rejects the CL-T0b reserved id.

    Used for pilot-roster admission checks only (not a general per-request
    enforcement layer) — 5959039 must remain fetchable/resolvable for
    CL-T0b once authorized, just never seated in the v1.0 pilot.
    """
    athlete_id = assert_not_excluded(value, layer=layer)
    if athlete_id in RESERVED_ATHLETE_IDS:
        raise ReservedAthleteError(athlete_id, layer=layer)
    return athlete_id
