"""C2: 'order deletes -> replaces -> adds' -- not JSON-Schema-expressible
(cross-item ordering), enforced by coaching_loop.validation.check_tp_op_ordering."""

from __future__ import annotations

import pytest

from coaching_loop.validation import TpOpOrderingError, check_tp_op_ordering


def _session(op: str) -> dict:
    return {"tp_op": {"op": op}}


def test_all_adds_passes():
    check_tp_op_ordering([_session("add"), _session("add")])


def test_correct_order_delete_then_replace_then_add_passes():
    check_tp_op_ordering([_session("delete"), _session("replace"), _session("add")])


def test_delete_after_add_rejected():
    with pytest.raises(TpOpOrderingError):
        check_tp_op_ordering([_session("add"), _session("delete")])


def test_replace_after_add_rejected():
    with pytest.raises(TpOpOrderingError):
        check_tp_op_ordering([_session("add"), _session("replace")])


def test_empty_sessions_passes():
    check_tp_op_ordering([])


def test_single_session_passes():
    check_tp_op_ordering([_session("replace")])
