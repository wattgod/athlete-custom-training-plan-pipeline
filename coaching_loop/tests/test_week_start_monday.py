"""C2: 'week_start (athlete-tz ISO Monday)'. Day-of-week is not a JSON
Schema format keyword, so coaching_loop.validation.check_week_start_is_monday
is a supplementary check (same pattern as check_tp_op_ordering)."""

from __future__ import annotations

import pytest

from coaching_loop.fixtures.loader import load_proposal_skeleton
from coaching_loop.validation import WeekStartNotMondayError, check_week_start_is_monday


def test_fixture_week_start_is_actually_a_monday():
    check_week_start_is_monday(load_proposal_skeleton()["week_start"])


def test_monday_passes():
    check_week_start_is_monday("2026-07-27")  # a Monday


@pytest.mark.parametrize("date_str", ["2026-07-28", "2026-07-29", "2026-08-02"])
def test_non_monday_rejected(date_str):
    with pytest.raises(WeekStartNotMondayError):
        check_week_start_is_monday(date_str)


def test_invalid_date_string_rejected():
    with pytest.raises(WeekStartNotMondayError):
        check_week_start_is_monday("not-a-date")
