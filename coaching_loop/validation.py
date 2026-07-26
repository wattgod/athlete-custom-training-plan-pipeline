"""JSON Schema loading + validation helpers for the coaching_loop schemas.

Builds one `referencing.Registry` so `proposal_ir.schema.json` can `$ref`
`engine_state.schema.json` (for `engine_state_next`) without duplicating
the base-state shape. Load-once, memoized at module import.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMAS_DIR = Path(__file__).parent / "schemas"

_SCHEMA_FILES = {
    "tp_fixture": "tp_fixture.schema.json",
    "proposal_ir": "proposal_ir.schema.json",
    "engine_state": "engine_state.schema.json",
    "engine_state_base_view": "engine_state_base_view.schema.json",
    "journal_record": "journal_record.schema.json",
}

# "date"/"date-time" in every schema are load-bearing (week_start,
# fetched_at, ts, ...) -- jsonschema does NOT enforce "format" unless a
# FormatChecker is attached; without this, any string passes. Draft
# 2020-12's built-in FormatChecker covers "date" out of the box but NOT
# "date-time" (that needs the optional rfc3339-validator package, which
# is not installed here) -- unregistered formats are silently treated as
# passing, so "date-time" would otherwise still validate anything.
# Register a minimal date-time checker via the stdlib instead of adding
# a new dependency.
_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time", raises=ValueError)
def _check_date_time(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return True


def _load_raw(name: str) -> dict:
    path = SCHEMAS_DIR / _SCHEMA_FILES[name]
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_RAW_SCHEMAS = {name: _load_raw(name) for name in _SCHEMA_FILES}

_REGISTRY = Registry().with_resources(
    (schema["$id"], Resource(contents=schema, specification=DRAFT202012))
    for schema in _RAW_SCHEMAS.values()
)


def load_schema(name: str) -> dict:
    """Return the raw schema dict for one of: tp_fixture, proposal_ir,
    engine_state, journal_record."""
    return _RAW_SCHEMAS[name]


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_RAW_SCHEMAS[name], registry=_REGISTRY, format_checker=_FORMAT_CHECKER)


def validate(instance: Any, schema_name: str) -> None:
    """Validate `instance` against the named schema. Raises
    jsonschema.exceptions.ValidationError on the first violation."""
    _validator(schema_name).validate(instance)


def iter_errors(instance: Any, schema_name: str):
    """Yield every ValidationError for `instance` against the named schema
    (does not raise) — useful for reporting all violations at once."""
    return _validator(schema_name).iter_errors(instance)


def validate_tp_fixture(instance: dict) -> None:
    validate(instance, "tp_fixture")


def validate_proposal_ir(instance: dict) -> None:
    validate(instance, "proposal_ir")


def validate_engine_state(instance: dict) -> None:
    validate(instance, "engine_state")


def validate_engine_state_base_view(instance: dict) -> None:
    validate(instance, "engine_state_base_view")


def validate_journal_record(instance: dict) -> None:
    validate(instance, "journal_record")


def validate_tp_op_grammar(tp_op: dict) -> None:
    """Validate a bare tp_op object against the full op grammar
    (add|replace|delete, $defs/tp_op in proposal_ir.schema.json),
    independent of the capability_profile header restriction that a full
    ProposalIR instance would additionally apply. Used to prove the
    grammar itself is fully specified now, per C2, even though v1.0
    enforcement only ever reaches `add`."""
    schema = {"$ref": "coaching_loop/schemas/proposal_ir.schema.json#/$defs/tp_op"}
    Draft202012Validator(schema, registry=_REGISTRY, format_checker=_FORMAT_CHECKER).validate(tp_op)


class WeekStartNotMondayError(ValueError):
    """Raised when a week_start value is a valid ISO date but not a Monday."""


def check_week_start_is_monday(week_start: str) -> None:
    """C2: 'week_start (athlete-tz ISO Monday)'. Not JSON-Schema-
    expressible (day-of-week is not a format keyword), so it is a
    supplementary check, same pattern as check_tp_op_ordering."""
    try:
        parsed = datetime.date.fromisoformat(week_start)
    except ValueError as exc:
        raise WeekStartNotMondayError(f"week_start is not a valid ISO date: {week_start!r}") from exc
    if parsed.weekday() != 0:
        raise WeekStartNotMondayError(
            f"week_start {week_start!r} is a {parsed.strftime('%A')}, not a Monday"
        )


# --------------------------------------------------------------------------
# Supplementary structural checks the JSON Schema itself cannot express
# --------------------------------------------------------------------------

_OP_ORDER = {"delete": 0, "replace": 1, "add": 2}


class TpOpOrderingError(ValueError):
    """Raised when a proposal's sessions are not ordered deletes -> replaces -> adds."""


def check_tp_op_ordering(sessions: list[dict]) -> None:
    """C2: 'order deletes -> replaces -> adds' for a proposal's sessions.

    Not expressible as a JSON Schema constraint (cross-item ordering), so
    it is enforced here as a supplementary check. v1.0-proposal-only
    proposals contain only `add` ops, so this is vacuous today and starts
    mattering once the full op grammar is reachable (v1.1+).
    """
    seen_ranks: list[int] = []
    for session in sessions:
        op = session["tp_op"]["op"]
        rank = _OP_ORDER[op]
        if seen_ranks and rank < seen_ranks[-1]:
            raise TpOpOrderingError(
                f"session op {op!r} (rank {rank}) appears after a higher-rank op "
                f"(rank {seen_ranks[-1]}) — sessions must be ordered deletes -> "
                f"replaces -> adds"
            )
        seen_ranks.append(rank)
