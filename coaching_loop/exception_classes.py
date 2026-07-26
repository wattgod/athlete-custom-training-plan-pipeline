"""Canonical EXCEPTION_CLASS code map — Gate: W-rules + exception classes.

docs/COACHING_LOOP_SPEC.md: "Blocking (unapprovable; resolved only by
dossier/proposal edit -> regeneration): W-6, W-7, A3 -- per the canonical
EXCEPTION_CLASS map; the approvals parser rejects approve AND
override_approve on any proposal carrying a blocking exception.
Overridable (W-1..W-5): override_approve must name EXACTLY the set of
overridable exception_ids on the proposal."

An exception's `blocking` field on the wire is DERIVED from this map at
emission (ProposalIR construction) and re-validated against this same map
at approvals parsing -- a mismatch is a reject, not a silent trust of
whatever the wire said (C2, "mismatch -> reject").
"""

from __future__ import annotations

BLOCKING = "blocking"
OVERRIDABLE = "overridable"

EXCEPTION_CLASS: dict[str, str] = {
    "W-1": OVERRIDABLE,
    "W-2": OVERRIDABLE,
    "W-3": OVERRIDABLE,
    "W-4": OVERRIDABLE,
    "W-5": OVERRIDABLE,
    "W-6": BLOCKING,
    "W-7": BLOCKING,
    "A3": BLOCKING,
}


def is_blocking(exception_type: str) -> bool:
    try:
        return EXCEPTION_CLASS[exception_type] == BLOCKING
    except KeyError as exc:
        raise ValueError(f"unknown exception type: {exception_type!r}") from exc


class ExceptionClassMismatchError(ValueError):
    """Raised when a wire exception's `blocking` field disagrees with EXCEPTION_CLASS."""


def assert_exception_class_consistent(exception: dict) -> None:
    exc_type = exception["type"]
    wire_blocking = exception["blocking"]
    canonical = is_blocking(exc_type)
    if wire_blocking != canonical:
        raise ExceptionClassMismatchError(
            f"exception {exception.get('exception_id')!r} type={exc_type!r} "
            f"claims blocking={wire_blocking!r}, canonical is {canonical!r}"
        )


def assert_all_exceptions_consistent(exceptions: list[dict]) -> None:
    for exception in exceptions:
        assert_exception_class_consistent(exception)


def has_blocking_exception(exceptions: list[dict]) -> bool:
    return any(is_blocking(e["type"]) for e in exceptions)


def overridable_exception_ids(exceptions: list[dict]) -> set[str]:
    return {e["exception_id"] for e in exceptions if not is_blocking(e["type"])}
