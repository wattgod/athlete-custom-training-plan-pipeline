"""drop_workouts rules key: remove a workout by date + title substring."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from athlete_layer import apply  # noqa: E402


def _w(day, title, type_id=2):
    return {"title": title, "workoutTypeValueId": type_id, "workoutDay": f"{day}T00:00:00",
            "description": "", "totalTimePlanned": 1.0, "tssPlanned": 50.0, "structure": None}


def test_drop_workouts_removes_only_the_named_card():
    plan = [_w("2026-11-21", "Rest Day", 7), _w("2026-11-20", "Rest Day", 7), _w("2026-11-21", "Endurance")]
    out, notes, changed = apply(plan, [], {"drop_workouts": [{"date": "2026-11-21", "title_contains": "Rest Day"}]})
    assert [(w["workoutDay"][:10], w["title"]) for w in out] == [("2026-11-20", "Rest Day"), ("2026-11-21", "Endurance")]
    assert any(c[1] == "dropped workout" for c in changed)


def test_drop_workouts_absent_is_noop():
    plan = [_w("2026-11-21", "Rest Day", 7)]
    out, _, changed = apply(plan, [], {})
    assert out == plan and not changed
