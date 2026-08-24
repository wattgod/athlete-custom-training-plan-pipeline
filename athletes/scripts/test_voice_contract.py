"""Voice contract: no blank calendar days, story notes in the coach's voice,
fail-closed lint (Matti, Aug 23 2026)."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rest_day_cards as R
from story_notes import render_story_notes, _word_count
from voice_lint import lint_notes, lint_rest_cards, load_rules

RULES = load_rules()


def _plan(weeks=8):
    """Synthetic PlanIR: testing week, two base, recovery, build, peak, taper, race."""
    types = {1: "load", 2: "load", 3: "load", 4: "recovery", 5: "load", 6: "load", 7: "taper", 8: "race"}
    phases = {1: "base", 2: "base", 3: "base", 4: "build", 5: "build", 6: "peak", 7: "taper", 8: "race"}
    from datetime import date, timedelta
    start = date(2026, 8, 24)
    out = {"athlete": {"id": "t"}, "race_snapshot": {"name": "Big Sugar Gravel", "date": "2026-10-17"}, "weeks": []}
    for w in range(1, weeks + 1):
        d0 = start + timedelta(days=7 * (w - 1))
        sessions = [
            {"date": (d0).isoformat(), "title": "FTP Test" if w == 1 else "Ronnestad 30-15", "tp_kind": "bike",
             "archetype_id": "VO2max 30/30", "duration_s": 3600, "is_field_test": w == 1},
            {"date": (d0 + timedelta(days=1)).isoformat(), "title": "Rest Day", "tp_kind": "day_off", "description": "Off the bike, not off the plan."},
            {"date": (d0 + timedelta(days=2)).isoformat(), "title": "Descending-Cadence Ladder", "tp_kind": "bike", "archetype_id": "Cadence Work", "duration_s": 3800},
            {"date": (d0 + timedelta(days=6)).isoformat(), "title": "Z2 + Sprints", "tp_kind": "bike", "archetype_id": "Endurance", "duration_s": 9000},
        ]
        out["weeks"].append({"number": w, "phase": phases[w], "week_type": types[w], "sessions": sessions})
    return out


def test_rest_cards_cycle_and_never_blank():
    bodies = [R.rest_day_card("2026-09-0%d" % (i + 1), week={"week": 2, "phase": "base"}, athlete_seed="a", ordinal=i)["body"] for i in range(8)]
    assert all(b.strip() for b in bodies)
    assert bodies[:4] == bodies[4:8], "cycles through every variant before repeating"
    assert len(set(bodies[:4])) == 4, "no back-to-back repeats"
    assert R.rest_day_card("2026-10-16", week={"week": 8, "is_race_week": True}, race_date="2026-10-17")["title"] == "Day Off — Race Prep"
    assert R.rest_day_card("2026-10-18", week={"week": 9}, race_date="2026-10-17")["title"] == "Day Off — Well Done"
    assert R.rest_day_card("2026-08-23", week={"week": 0, "phase": "pre_plan"})["title"] == "Pre-Plan Rest"


def test_rest_cards_pass_voice_lint():
    cards = [R.rest_day_card("2026-09-01", week={"week": 2}, athlete_seed="a", ordinal=i) for i in range(4)]
    cards += [R.rest_day_card("2026-09-01", week={"week": 4, "is_recovery_week": True}, athlete_seed="a", ordinal=i) for i in range(2)]
    sessions = [{"tp_kind": "day_off", "date": "x", "title": c["title"], "description": c["body"]} for c in cards]
    assert lint_rest_cards(sessions, rules=RULES) == []


def test_blank_rest_day_is_a_critical_finding():
    findings = lint_rest_cards([{"tp_kind": "day_off", "date": "2026-09-01", "title": "Rest Day", "description": ""}], rules=RULES)
    assert findings and "blank calendar day" in findings[0]


def test_story_notes_have_beats_and_pass_lint():
    notes = render_story_notes(_plan())
    # AE-9.1 (2026-08-24 TP review): 8 Monday notes, plus a mid-week "feel"
    # note on the 4 load weeks (2, 3, 5, 6 -- Wednesday, the fixture's only
    # Thu/Wed/Tue/Fri session) and a pre-long-ride fuel note on every
    # non-testing, non-race week that carries a >=90min bike session
    # (2-7, all of them via the fixture's Sunday "Z2 + Sprints" ride) = 18.
    assert len(notes) == 18
    assert notes[0]["title"].startswith("Week 1") and "Testing" in notes[0]["title"]
    assert "FTP Test Monday" in notes[0]["body"]
    assert "Openers before Big Sugar Gravel" in notes[-1]["body"]
    assert all(_word_count(n["body"]) <= RULES["limits"]["weekly_note_max_words"] for n in notes)
    assert lint_notes(notes, rules=RULES) == []


def test_story_notes_never_repeat_a_sentence_across_weeks():
    notes = render_story_notes(_plan())
    sentences = Counter(s.strip() for n in notes for s in re.split(r"(?<=[.!?])\s+", n["body"]) if len(s.split()) >= 6)
    assert not [s for s, c in sentences.items() if c > 1]


def test_story_notes_are_deterministic():
    assert render_story_notes(_plan()) == render_story_notes(_plan())


def _plan_no_setup():
    """A recovery-then-load transition with NO earlier midweek 'legs heavy'
    note anywhere in the plan -- the AE-9.1c callback must not fire without
    its own setup."""
    from datetime import date, timedelta
    start = date(2026, 8, 24)
    out = {"athlete": {"id": "t2"}, "race_snapshot": {"name": "Big Sugar Gravel", "date": "2026-12-01"}, "weeks": []}
    for w, phase, wt in [(1, "base", "recovery"), (2, "build", "load")]:
        d0 = start + timedelta(days=7 * (w - 1))
        sessions = [
            {"date": d0.isoformat(), "title": "Endurance Ride", "tp_kind": "bike", "archetype_id": "Endurance", "duration_s": 3600},
            {"date": (d0 + timedelta(days=6)).isoformat(), "title": "Z2 + Sprints", "tp_kind": "bike", "archetype_id": "Endurance", "duration_s": 9000},
        ]
        out["weeks"].append({"number": w, "phase": phase, "week_type": wt, "sessions": sessions})
    return out


def test_story_notes_thread_legs_heavy_callback():
    """AE-9.1c: a genuine callback -- the fresh-legs-after-recovery line
    references an earlier midweek 'legs heavy' note -- appears in a
    multi-week plan, fires exactly once, and only after its setup note."""
    notes = render_story_notes(_plan())
    setup_idx = next(i for i, n in enumerate(notes) if "Legs heavy today is the load landing" in n["body"])
    payoffs = [i for i, n in enumerate(notes)
               if "from a few weeks back are exactly why this feels good now" in n["body"]]
    assert len(payoffs) == 1, "the callback should own its moment once, not repeat"
    assert payoffs[0] > setup_idx, "callback must never fire before its setup"


def test_story_notes_callback_never_fires_without_its_setup():
    """No earlier 'legs heavy' note exists in this plan -- the recovery-return
    position line must fall back to the plain variant, never the callback."""
    notes = render_story_notes(_plan_no_setup())
    week2 = next(n for n in notes if n["title"].startswith("Week 2"))
    assert "fresh legs" in week2["body"]
    assert "from a few weeks back" not in week2["body"]


def test_lint_catches_template_and_slop():
    bad = [{"date": "2026-08-24", "title": "Week 1", "body": "Add one controlled layer. Protect the key work. More is not the assignment."},
           {"date": "2026-08-31", "title": "Week 2", "body": "## Focus\nLet's dive in and unlock your potential!!"}]
    findings = lint_notes(bad, rules=RULES)
    assert any("more is not the assignment" in f for f in findings)
    assert any("unlock your potential" in f for f in findings)
    assert any("banned pattern" in f for f in findings)
