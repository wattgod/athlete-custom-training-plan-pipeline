"""C1: canonical JSON encoding is the foundation every hash relies on."""

from __future__ import annotations

import hashlib
import unicodedata

from coaching_loop.canonical_json import canonical_bytes, canonical_json


def test_sorted_keys():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b == '{"a":2,"b":1}'


def test_no_incidental_whitespace():
    encoded = canonical_json({"a": [1, 2, 3]})
    assert " " not in encoded
    assert "\n" not in encoded


def test_integral_floats_become_ints():
    assert canonical_json({"tss": 85.0}) == '{"tss":85}'


def test_non_integral_floats_rounded_to_six_decimals():
    encoded = canonical_json({"x": 1.0 / 3})
    assert encoded == '{"x":0.333333}'


def test_nfc_normalizes_strings():
    # Built explicitly via unicodedata so this test does not depend on
    # source-file encoding normalization: NFD ('e' + combining acute,
    # U+0065 U+0301) vs NFC (precomposed U+00E9), same visible word.
    base = "cafe" + "́"  # NFD form of the accented final letter
    nfd = unicodedata.normalize("NFD", base)
    nfc = unicodedata.normalize("NFC", base)
    assert nfd != nfc
    assert canonical_json({"name": nfd}) == canonical_json({"name": nfc})


def test_nested_structures_normalized_recursively():
    encoded = canonical_json({"sessions": [{"b": 2.0, "a": 1.0}]})
    assert encoded == '{"sessions":[{"a":1,"b":2}]}'


def test_key_order_independence_end_to_end():
    obj1 = {"z": 1, "a": {"y": 2, "x": 3}}
    obj2 = {"a": {"x": 3, "y": 2}, "z": 1}
    assert canonical_json(obj1) == canonical_json(obj2)


def test_canonical_bytes_is_utf8_of_canonical_json():
    obj = {"name": "synthetic"}
    assert canonical_bytes(obj) == canonical_json(obj).encode("utf-8")


def test_bool_is_not_coerced_through_the_float_branch():
    # bool is an int subclass; must not be misrouted into float rounding.
    encoded = canonical_json({"dirty": False, "flag": True})
    assert encoded == '{"dirty":false,"flag":true}'


def test_hash_stability_smoke():
    digest1 = hashlib.sha256(canonical_bytes({"a": 1, "b": [1, 2, 3.0]})).hexdigest()
    digest2 = hashlib.sha256(canonical_bytes({"b": [1, 2, 3.0], "a": 1})).hexdigest()
    assert digest1 == digest2
