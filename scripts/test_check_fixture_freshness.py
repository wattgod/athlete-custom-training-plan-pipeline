from datetime import date, datetime, timedelta, timezone

import pytest

from scripts.check_fixture_freshness import (
    FixtureFreshnessError,
    PinnedRace,
    assess_fixture_freshness,
    load_pinned_races,
)

_PIN = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fixture(*, pin=_PIN, race_days_after_pin=120, exempt=False):
    return PinnedRace(
        suite="test", name="Pinned Race",
        race_date=pin.date() + timedelta(days=race_days_after_pin),
        generation_at=pin,
        source="synthetic",
        exempt=exempt,
    )


def test_fresh_pin_passes():
    today = _PIN.date() + timedelta(days=30)
    result = assess_fixture_freshness([_fixture()], today=today)
    assert result[0]["status"] == "PASS"
    assert result[0]["pin_age_days"] == 30


def test_aging_pin_warns():
    today = _PIN.date() + timedelta(days=121)
    result = assess_fixture_freshness([_fixture(race_days_after_pin=200)], today=today)
    assert result[0]["status"] == "WARN"


def test_stale_pin_fails():
    today = _PIN.date() + timedelta(days=181)
    result = assess_fixture_freshness([_fixture(race_days_after_pin=200)], today=today)
    assert result[0]["status"] == "FAIL"


def test_exactly_max_age_still_passes_as_warn():
    today = _PIN.date() + timedelta(days=180)
    result = assess_fixture_freshness([_fixture(race_days_after_pin=200)], today=today)
    assert result[0]["status"] == "WARN"


def test_exempt_fixture_never_fails_regardless_of_age():
    today = _PIN.date() + timedelta(days=5000)
    result = assess_fixture_freshness(
        [_fixture(race_days_after_pin=120, exempt=True)], today=today)
    assert result[0]["status"] == "EXEMPT"


def test_race_on_or_before_pinned_clock_is_a_configuration_error():
    with pytest.raises(FixtureFreshnessError):
        assess_fixture_freshness(
            [_fixture(race_days_after_pin=0)], today=_PIN.date())


def test_loader_imports_acceptance_and_athlete_m_pins():
    fixtures = load_pinned_races()
    assert {fixture.suite for fixture in fixtures} == {"order-acceptance", "athlete-m"}
    assert all(fixture.generation_at.tzinfo is not None for fixture in fixtures)
    assert all(f.exempt for f in fixtures if f.suite == "athlete-m")
    assert not any(f.exempt for f in fixtures if f.suite == "order-acceptance")


def test_loader_pins_are_currently_healthy():
    """The committed pins must pass the gate on the real clock at commit time."""
    results = assess_fixture_freshness(load_pinned_races(), today=date.today())
    assert not [r for r in results if r["status"] == "FAIL"]
