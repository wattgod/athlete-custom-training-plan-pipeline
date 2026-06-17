#!/usr/bin/env python3
"""
Real-race access for tests + the synthesizer.

Loads the committed athletes/config/races.json snapshot (built by
build_race_snapshot.py from the 1,184-race gravel + road databases) and
serves discipline-matched, future-dated, buildable races.
"""

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "config" / "races.json"


@lru_cache(maxsize=1)
def _load():
    if not SNAPSHOT.exists():
        return []
    data = json.loads(SNAPSHOT.read_text())
    return list(data.get("races", {}).values())


def buildable_races(discipline=None, min_weeks=8, max_weeks=30, today=None,
                    min_mi=25, max_mi=170):
    """Real races with a specific date far enough out to build a periodized
    plan, and a single-day-plausible distance. Filtered by discipline when
    given. (max_mi defaults exclude multi-day stage races / ultras.)"""
    base = (datetime.strptime(today, "%Y-%m-%d").date() if today else date.today())
    out = []
    for e in _load():
        if discipline and e.get("discipline") != discipline:
            continue
        iso = e.get("date")
        if not iso:
            continue
        try:
            rd = datetime.strptime(iso, "%Y-%m-%d").date()
        except ValueError:
            continue
        dist = e.get("distance_mi")
        if not dist or not (min_mi <= float(dist) <= max_mi):
            continue
        weeks = (rd - base).days / 7
        if min_weeks <= weeks <= max_weeks:
            out.append(e)
    return out


def pick(rng, discipline=None, min_weeks=8, max_weeks=30, today=None,
         min_mi=25, max_mi=170):
    """Pick one buildable real race (reproducible via the supplied rng).
    Falls back across disciplines, then to None if the snapshot is empty."""
    races = buildable_races(discipline, min_weeks, max_weeks, today, min_mi, max_mi)
    if not races and discipline:
        races = buildable_races(None, min_weeks, max_weeks, today, min_mi, max_mi)
    return rng.choice(races) if races else None
