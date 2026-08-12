from datetime import date, datetime, timedelta, timezone

from scripts.check_fixture_freshness import (
    PinnedRace,
    assess_fixture_freshness,
    load_pinned_races,
)


def _fixture(today, days):
    return PinnedRace(
        suite="test", name="Pinned Race",
        race_date=today + timedelta(days=days),
        generation_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="synthetic",
    )


def test_freshness_pass_with_injected_clock():
    today = date(2026, 1, 1)
    result = assess_fixture_freshness([_fixture(today, 100)], today=today)
    assert result[0]["status"] == "PASS"


def test_freshness_warn_with_injected_clock():
    today = date(2026, 1, 1)
    result = assess_fixture_freshness([_fixture(today, 70)], today=today)
    assert result[0]["status"] == "WARN"


def test_freshness_fail_with_injected_clock():
    today = date(2026, 1, 1)
    result = assess_fixture_freshness([_fixture(today, 55)], today=today)
    assert result[0]["status"] == "FAIL"


def test_exactly_eight_weeks_is_warning_not_failure():
    today = date(2026, 1, 1)
    result = assess_fixture_freshness([_fixture(today, 56)], today=today)
    assert result[0]["status"] == "WARN"


def test_loader_imports_acceptance_and_athlete_m_pins():
    fixtures = load_pinned_races()
    assert {fixture.suite for fixture in fixtures} == {"order-acceptance", "athlete-m"}
    assert all(fixture.generation_at.tzinfo is not None for fixture in fixtures)
