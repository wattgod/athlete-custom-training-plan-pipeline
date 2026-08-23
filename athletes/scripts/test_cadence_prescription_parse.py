"""parse_cadence_range must never turn a non-cadence digit into a cadence.

Regression: "Z2 self-selected, intervals per archetype" parsed as 2 rpm and
shipped CadenceLow="-3" CadenceHigh="7" in every VO2 Bookend / Buffer Workout
ZWO (found Aug 23 2026 when the TP projector started emitting cadence targets
and its 30-200 rpm guard fired on sealed athlete models).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from nate_workout_generator import parse_cadence_range
from tp_cadence import CADENCE_MAX_RPM, CADENCE_MIN_RPM
import new_archetypes, imported_archetypes, advanced_archetypes


@pytest.mark.parametrize("text,expected", [
    ("Z2 self-selected, intervals per archetype", None),
    ("Self-selected for max power; stay smooth on the 30/30s", None),
    ("Natural", None),
    ("Rider's choice", None),
    ("", None),
    ("Steady 5min", None),
    ("90-95rpm", (90, 95)),
    ("90–95 rpm", (90, 95)),
    ("Z3 @ 60-75rpm", (60, 75)),
    ("cadence 100-120rpm on the stabs", (100, 120)),
    ("90rpm", (85, 95)),
    ("100+ rpm", (95, 105)),
    ("85", (80, 90)),
    ("high cadence", (90, 100)),
    ("low cadence", (65, 75)),
])
def test_parse(text, expected):
    assert parse_cadence_range(text) == expected


def _every_prescription():
    out = []
    def walk(obj, path):
        if isinstance(obj, dict):
            cp = obj.get("cadence_prescription")
            if isinstance(cp, str):
                out.append((path + "/" + str(obj.get("name", "?")), cp))
            for v in obj.values():
                walk(v, path + "/" + str(obj.get("name", "")))
        elif isinstance(obj, list):
            for v in obj:
                walk(v, path)
    for mod in (new_archetypes, imported_archetypes, advanced_archetypes):
        for name in dir(mod):
            value = getattr(mod, name)
            if name.isupper() and isinstance(value, (list, dict)):
                walk(value, mod.__name__ + ":" + name)
    return out


def test_every_archetype_prescription_is_plausible_or_none():
    bad = []
    for path, text in _every_prescription():
        parsed = parse_cadence_range(text)
        if parsed and not all(CADENCE_MIN_RPM <= v <= CADENCE_MAX_RPM for v in parsed):
            bad.append((path, text, parsed))
    assert not bad, bad
