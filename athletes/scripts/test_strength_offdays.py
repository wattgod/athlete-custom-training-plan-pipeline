"""Strength must never land on an off day (the avatar judge's recurring
Off-Days contract failure: strength was hardcoded to Tue/Thu even when the
athlete rested those days)."""

from generate_athlete_package import select_strength_days


def _avail(off, long_day="Sat"):
    off = set(off)
    return lambda d: d not in off and d != long_day


def test_avoids_tuesday_when_off():
    days = select_strength_days(_avail({"Tue", "Wed", "Fri"}))
    assert "Tue" not in days and "Wed" not in days and "Fri" not in days
    assert len(days) == 2


def test_avoids_long_ride_day():
    days = select_strength_days(_avail(set(), long_day="Sun"))
    assert "Sun" not in days


def test_prefers_tue_thu_when_available():
    assert select_strength_days(_avail(set())) == ["Tue", "Thu"]


def test_respects_explicit_strength_days():
    # athlete-specified days win, but still filtered to available ones
    days = select_strength_days(_avail({"Tue"}), strength_only_abbrevs=["Mon", "Thu"])
    assert days == ["Mon", "Thu"]


def test_never_returns_off_day_even_when_squeezed():
    # only Mon + Thu available; both off-respecting and gap >= 2
    days = select_strength_days(_avail({"Tue", "Wed", "Fri", "Sun"}, long_day="Sat"))
    assert all(d in ("Mon", "Thu") for d in days)


def test_gap_enforced_in_fallback():
    # available: Mon, Tue only (adjacent) → fallback can't find a 2-gap pair
    days = select_strength_days(_avail({"Wed", "Thu", "Fri", "Sun"}, long_day="Sat"))
    assert "Wed" not in days and "Thu" not in days and "Fri" not in days
