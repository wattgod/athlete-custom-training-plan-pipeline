import random

import real_races


def test_pick_does_not_cross_requested_discipline(monkeypatch):
    races = [
        {
            "name": "Only Gravel Match",
            "date": "2026-10-10",
            "distance_mi": 30,
            "discipline": "gravel",
        }
    ]
    monkeypatch.setattr(real_races, "_load", lambda: races)

    result = real_races.pick(
        random.Random(1),
        discipline="road",
        min_weeks=1,
        max_weeks=52,
        today="2026-08-06",
        min_mi=1,
        max_mi=40,
    )

    assert result is None


def test_pick_returns_matching_requested_discipline(monkeypatch):
    races = [
        {
            "name": "Road Match",
            "date": "2026-10-10",
            "distance_mi": 30,
            "discipline": "road",
        },
        {
            "name": "Gravel Match",
            "date": "2026-10-10",
            "distance_mi": 30,
            "discipline": "gravel",
        },
    ]
    monkeypatch.setattr(real_races, "_load", lambda: races)

    result = real_races.pick(
        random.Random(1),
        discipline="road",
        min_weeks=1,
        max_weeks=52,
        today="2026-08-06",
        min_mi=1,
        max_mi=40,
    )

    assert result["name"] == "Road Match"
    assert result["discipline"] == "road"
