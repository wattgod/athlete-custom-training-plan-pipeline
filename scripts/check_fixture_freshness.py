#!/usr/bin/env python3
"""Gate the age of date-pinned acceptance fixtures.

Pinned fixtures inject a frozen clock into generation, so they never rot
mechanically — the past-date validators honor the pinned clock, not the
wall clock. What this gate bounds is *drift from reality*: goldens
generated against a months-old clock stop resembling the orders the
pipeline actually receives. Policy:

- order-acceptance goldens FAIL when the pinned generation clock is more
  than MAX_PIN_AGE_DAYS old (WARN beyond WARN_PIN_AGE_DAYS). Refreshing is
  a deliberate act in a dedicated PR — docs/runbooks/GOLDEN_REFRESH.md.
- athlete-m is EXEMPT: its dates are normative fixture contract in
  docs/SPEC_TRUSTWORTHY_FULFILMENT.md and may only change with the spec.
- Every pinned fixture must keep its race date in the pinned clock's
  future; a violation is a configuration error, not staleness.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MAX_PIN_AGE_DAYS = 180
WARN_PIN_AGE_DAYS = 120
REFRESH_MESSAGE = (
    "The acceptance goldens' pinned generation clock is more than "
    f"{MAX_PIN_AGE_DAYS} days old. Refresh goldens in a dedicated PR; "
    "follow docs/runbooks/GOLDEN_REFRESH.md."
)


class FixtureFreshnessError(ValueError):
    """Pinned clock or race fixture data is missing or inconsistent."""


@dataclass(frozen=True)
class PinnedRace:
    suite: str
    name: str
    race_date: date
    generation_at: datetime
    source: str
    exempt: bool = False


def _parse_datetime(value: object, *, source: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise FixtureFreshnessError(f"invalid pinned clock in {source}") from exc
    if parsed.tzinfo is None:
        raise FixtureFreshnessError(f"pinned clock lacks timezone in {source}")
    return parsed


def _parse_date(value: object, *, source: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise FixtureFreshnessError(f"invalid pinned race date in {source}") from exc


def load_pinned_races() -> list[PinnedRace]:
    """Import acceptance constants and read athlete-m's literal JSON fixtures."""
    from athletes.scripts import test_order_acceptance as acceptance

    acceptance_source = "athletes/scripts/test_order_acceptance.py"
    golden_clock = _parse_datetime(
        acceptance._GOLDEN_GENERATION_AT, source=acceptance_source)
    races: list[PinnedRace] = []
    seen: set[tuple[str, str]] = set()
    for order in acceptance.GOLDEN_ORDERS:
        for race in (order.get("intake") or {}).get("races") or []:
            key = (str(race.get("name") or ""), str(race.get("date") or ""))
            if key in seen:
                continue
            seen.add(key)
            races.append(PinnedRace(
                suite="order-acceptance",
                name=key[0],
                race_date=_parse_date(key[1], source=acceptance_source),
                generation_at=golden_clock,
                source=acceptance_source,
            ))

    fixture_root = REPO_ROOT / "tests" / "fixtures" / "athlete_m"
    clock_path = fixture_root / "clock.json"
    race_path = fixture_root / "race_snapshot.json"
    intake_path = fixture_root / "intake.json"
    clock = json.loads(clock_path.read_text(encoding="utf-8"))
    race = json.loads(race_path.read_text(encoding="utf-8"))
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    athlete_clock = _parse_datetime(clock.get("generation_at"), source=str(clock_path))
    athlete_race_date = _parse_date(race.get("date"), source=str(race_path))
    intake_dates = {
        _parse_date(item.get("date"), source=str(intake_path))
        for item in intake.get("races") or []
        if item.get("priority") == "A"
    }
    if intake_dates != {athlete_race_date}:
        raise FixtureFreshnessError(
            "athlete-m intake and race snapshot pin different A-race dates")
    races.append(PinnedRace(
        suite="athlete-m",
        name=str(race.get("name") or "athlete-m A race"),
        race_date=athlete_race_date,
        generation_at=athlete_clock,
        source="tests/fixtures/athlete_m/{clock.json,race_snapshot.json,intake.json}",
        exempt=True,
    ))
    if not races:
        raise FixtureFreshnessError("no pinned races were found")
    return races


def assess_fixture_freshness(
    fixtures: Iterable[PinnedRace], *, today: date,
) -> list[dict[str, object]]:
    """Classify fixtures as PASS, WARN, FAIL, or EXEMPT against an injected date."""
    results = []
    for fixture in fixtures:
        if fixture.race_date <= fixture.generation_at.date():
            raise FixtureFreshnessError(
                f"pinned race '{fixture.name}' ({fixture.race_date.isoformat()}) "
                f"is not after the pinned clock "
                f"({fixture.generation_at.date().isoformat()}) in {fixture.source}")
        pin_age = (today - fixture.generation_at.date()).days
        if fixture.exempt:
            status = "EXEMPT"
        elif pin_age > MAX_PIN_AGE_DAYS:
            status = "FAIL"
        elif pin_age > WARN_PIN_AGE_DAYS:
            status = "WARN"
        else:
            status = "PASS"
        results.append({
            "suite": fixture.suite,
            "name": fixture.name,
            "race_date": fixture.race_date.isoformat(),
            "pinned_clock": fixture.generation_at.isoformat(),
            "pin_age_days": pin_age,
            "status": status,
            "source": fixture.source,
        })
    return results


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    try:
        results = assess_fixture_freshness(load_pinned_races(), today=date.today())
    except (OSError, json.JSONDecodeError, FixtureFreshnessError) as exc:
        print(f"FAIL fixture freshness configuration: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(
            f"{result['status']:6}  pin {result['pinned_clock'][:10]} "
            f"({result['pin_age_days']:>4}d old)  race {result['race_date']}  "
            f"{result['suite']}: {result['name']}"
        )
    failures = [result for result in results if result["status"] == "FAIL"]
    if failures:
        print(REFRESH_MESSAGE, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
