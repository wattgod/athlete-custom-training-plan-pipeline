"""Canonical JSON encoding — C1 hash discipline.

Spec (docs/COACHING_LOOP_SPEC.md, C1): "UTF-8, sorted keys, no whitespace,
integral floats as ints." Plus: "NFC-normalized strings; non-integral
floats rounded to 6 decimals."

This module has exactly one job: turn a JSON-able Python value into the
one true byte string that every hash in C1 is computed over. Two views
with the same logical content, built independently (different key order,
different float representations of the same number), must produce the
same canonical string and therefore the same hash.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, bool):
        # bool is a subclass of int; keep it a bool, never falls into the
        # float/int branches below.
        return value
    if isinstance(value, float):
        # Round FIRST, then re-check integrality on the rounded value --
        # a non-integral float can become integral after 6-decimal
        # rounding (e.g. 1.9999999 -> 2.0), and "integral floats as ints"
        # must still apply to that result.
        rounded = round(value, 6)
        if rounded.is_integer():
            return int(rounded)
        return rounded
    if isinstance(value, dict):
        # Keys are strings too -- NFC-normalize them for the same reason
        # values are normalized: two dicts differing only by Unicode
        # normalization form must hash identically.
        return {unicodedata.normalize("NFC", str(k)): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    """Return the canonical JSON string for `value`.

    UTF-8 text, sorted object keys, no incidental whitespace, integral
    floats collapsed to ints, non-integral floats rounded to 6 decimals,
    strings NFC-normalized.
    """
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_bytes(value: Any) -> bytes:
    """UTF-8 bytes of `canonical_json(value)` — what H() actually hashes."""
    return canonical_json(value).encode("utf-8")
