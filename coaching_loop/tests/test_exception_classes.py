"""Gate: W-rules + exception classes -- canonical EXCEPTION_CLASS map."""

from __future__ import annotations

import pytest

from coaching_loop.exception_classes import (
    EXCEPTION_CLASS,
    ExceptionClassMismatchError,
    assert_all_exceptions_consistent,
    assert_exception_class_consistent,
    has_blocking_exception,
    is_blocking,
    overridable_exception_ids,
)


def test_blocking_set_is_w6_w7_a3():
    blocking = {t for t, cls in EXCEPTION_CLASS.items() if cls == "blocking"}
    assert blocking == {"W-6", "W-7", "A3"}


def test_overridable_set_is_w1_through_w5():
    overridable = {t for t, cls in EXCEPTION_CLASS.items() if cls == "overridable"}
    assert overridable == {"W-1", "W-2", "W-3", "W-4", "W-5"}


@pytest.mark.parametrize("exc_type", ["W-6", "W-7", "A3"])
def test_is_blocking_true_for_blocking_types(exc_type):
    assert is_blocking(exc_type) is True


@pytest.mark.parametrize("exc_type", ["W-1", "W-2", "W-3", "W-4", "W-5"])
def test_is_blocking_false_for_overridable_types(exc_type):
    assert is_blocking(exc_type) is False


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        is_blocking("W-99")


def test_consistent_exception_passes():
    assert_exception_class_consistent({"exception_id": "e1", "type": "W-6", "blocking": True})
    assert_exception_class_consistent({"exception_id": "e2", "type": "W-1", "blocking": False})


def test_mismatched_exception_rejected():
    # A wire exception claiming a blocking W-rule is overridable must be
    # rejected -- "re-validated at approvals parsing, mismatch -> reject".
    with pytest.raises(ExceptionClassMismatchError):
        assert_exception_class_consistent({"exception_id": "e1", "type": "W-6", "blocking": False})
    with pytest.raises(ExceptionClassMismatchError):
        assert_exception_class_consistent({"exception_id": "e2", "type": "W-1", "blocking": True})


def test_assert_all_exceptions_consistent_short_circuits_on_first_bad_one():
    exceptions = [
        {"exception_id": "e1", "type": "W-1", "blocking": False},
        {"exception_id": "e2", "type": "A3", "blocking": False},  # wrong
    ]
    with pytest.raises(ExceptionClassMismatchError):
        assert_all_exceptions_consistent(exceptions)


def test_has_blocking_exception():
    assert has_blocking_exception([{"type": "W-1"}, {"type": "W-6"}]) is True
    assert has_blocking_exception([{"type": "W-1"}, {"type": "W-2"}]) is False
    assert has_blocking_exception([]) is False


def test_overridable_exception_ids_names_exactly_the_overridable_set():
    exceptions = [
        {"exception_id": "e1", "type": "W-1"},
        {"exception_id": "e2", "type": "W-6"},
        {"exception_id": "e3", "type": "W-3"},
    ]
    assert overridable_exception_ids(exceptions) == {"e1", "e3"}
