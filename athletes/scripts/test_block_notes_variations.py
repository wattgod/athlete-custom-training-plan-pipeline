"""Coverage for block_notes.yaml rotation (2026-08-29, Matti's ask: "I dig
the canonical load week recovery week text or block, but could use some
variations of it"). AE-6.5b (rest-day rotation) extends to weekly block
notes: identical copy repeating across a plan is a defect. Entry [0] of
every week type stays Matti's canonical text, byte-identical, forever;
entries [1:] are added rotation variations that must pass the AE-9.11
voice gate.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

import ae_lint
from delivery_notes import _load_week_copy, _rotate_block_note, render_notes
from delivery_render import load_brand

_BLOCK_NOTES_PATH = Path(__file__).resolve().parent.parent / "config" / "block_notes.yaml"

# Matti's original canonical text (pre-2026-08-29), verbatim. Entry [0] of
# each week type must equal these forever -- the ask was for MORE
# variations, never for editing what's already there.
_CANONICAL = {
    "load": (
        "LOAD WEEK — Your training load is higher than average. You're "
        "pushing for increased fitness through harder training than your "
        "body is used to. Mostly through increased weekly training time; "
        "sometimes more intensity. Rarely both.\n\n"
        "To succeed:\n"
        "1. Prioritize training — this is the week that counts\n"
        "2. Eat more, especially carbs\n"
        "3. Drink to thirst and keep sodium up — recovery days included\n"
        "4. Prioritize sleep (8+ hours)\n"
        "5. Monk mode — minimize social distractions\n\n"
        "By the end of the week, you should feel TIRED but not DESTROYED.\n"
    ),
    "medium": (
        "MEDIUM WEEK — Training load stays fairly constant. The purpose is "
        "to sustain your load but shift the composition of workouts.\n\n"
        "To succeed:\n"
        "1. Don't be tempted to do extra training\n"
        "2. Stay on top of nutrition, hydration, and sleep\n"
        "3. Pay attention to workouts — many seem like repeats but have an "
        "extra set or differ slightly\n\n"
        "End of week goal: Neutral — not too tired, not too rested.\n"
    ),
    "recovery": (
        "RECOVERY WEEK — Training load is lower. You're giving your body "
        "time to repair stress from load weeks so it can adapt.\n\n"
        "To succeed:\n"
        "1. Don't train more than planned\n"
        "2. Don't train harder than planned\n"
        "3. Don't be afraid to shorten workouts\n"
        "4. Do as much restorative movement as you want (yoga, stretching, "
        "walking)\n"
        "5. Great time to prioritize other things than training\n\n"
        "The goal: feel refreshed and excited to train harder again.\n"
    ),
    "race": (
        "RACE WEEK — Training prioritizes showing up rested, fueled, and "
        "ready to race.\n\n"
        "To succeed:\n"
        "1. Don't train more than planned before the race\n"
        "2. Don't train harder than planned before the race\n"
        "3. Don't radically change anything, especially your diet\n"
        "4. Spend time during the week on logistics\n"
        "5. Double down on sleep\n"
        "6. Minimize social life 1-2 days out\n\n"
        "The goal: perform well with good energy and medium-low fatigue.\n"
    ),
    "uber_load": (
        "UBER LOAD WEEK — Training load is significantly higher than "
        "average. This is a deliberate overreach — you'll end the week "
        "feeling depleted.\n\n"
        "IMPORTANT: By the end of the week, you should feel DESTROYED. "
        "This is a calculated risk. The adaptation comes in the recovery "
        "week that follows. If you don't recover properly after this, the "
        "whole thing backfires.\n\n"
        "Rules:\n"
        "1. Sleep is non-negotiable (9+ hours)\n"
        "2. Eat everything in sight\n"
        "3. Cancel all optional social commitments\n"
        "4. If anything feels wrong (sharp pain, illness), STOP "
        "immediately\n"
    ),
}


def _week_types():
    return yaml.safe_load(_BLOCK_NOTES_PATH.read_text())


def test_every_week_type_has_at_least_four_variations():
    data = _week_types()
    assert set(data) >= set(_CANONICAL)
    for key, variations in data.items():
        assert isinstance(variations, list), f"{key} is not a list of variations"
        assert len(variations) >= 4, f"{key} has only {len(variations)} variation(s)"


def test_canonical_entry_is_byte_identical_to_original():
    data = _week_types()
    for key, canonical in _CANONICAL.items():
        assert data[key][0] == canonical, f"{key} entry [0] drifted from the canonical text"


def test_new_variations_pass_ae_lint_voice_gate():
    """Entry [0] (canonical) predates AE-9.11 (ratified the same day this
    rotation was added) and is exempt by design -- see block_notes.yaml's
    header note. Every added variation must clear the gate."""
    data = _week_types()
    for key, variations in data.items():
        for index, text in enumerate(variations[1:], start=1):
            findings = ae_lint.lint_voice(
                [], notes=[{"title": key, "noteDate": "2026-01-01", "description": text}])
            assert findings == [], f"{key}[{index}] failed AE-9.11: {findings}"


def test_new_variations_avoid_banned_hydration_language():
    banned = ("clear urine", "don't wait until thirsty", "hydrate aggressively")
    text = _BLOCK_NOTES_PATH.read_text().lower()
    assert not any(phrase in text for phrase in banned)


def test_rotate_block_note_returns_different_variation_for_consecutive_weeks():
    variations = ["a", "b", "c", "d"]
    seen = {_rotate_block_note(variations, "guillermo-romero", week) for week in range(1, 9)}
    # 8 consecutive weeks over 4 variations must show at least 2 distinct
    # values, and no two adjacent weeks may repeat.
    assert len(seen) >= 2
    for week in range(1, 8):
        this_pick = _rotate_block_note(variations, "guillermo-romero", week)
        next_pick = _rotate_block_note(variations, "guillermo-romero", week + 1)
        assert this_pick != next_pick


def test_rotate_block_note_is_deterministic():
    variations = _week_types()["load"]
    first = _rotate_block_note(variations, "monika-renk", 3)
    second = _rotate_block_note(variations, "monika-renk", 3)
    assert first == second


def test_rotate_block_note_two_athletes_need_not_match():
    variations = ["a", "b", "c", "d"]
    picks = {_rotate_block_note(variations, seed, 1)
             for seed in ("guillermo-romero", "monika-renk", "steve-wagner", "brian-knapp")}
    assert len(picks) > 1


def test_rotate_block_note_empty_list_is_safe():
    assert _rotate_block_note([], "anyone", 1) == ""


def _plan(week_type, *, weeks=1, athlete_name="Test Athlete", athlete_id=None):
    start = date(2026, 9, 7)
    monday = start
    week = {
        "number": 1,
        "week_type": week_type,
        "sessions": [
            {"date": str(monday), "title": "VO2 Intervals", "tp_kind": "bike", "duration_s": 60 * 60},
            {"date": str(monday + timedelta(days=6)), "title": "Day Off", "tp_kind": "day_off"},
        ],
    }
    athlete = {"name": athlete_name, "key_markers": {"control_metric": "power"}}
    if athlete_id:
        athlete["id"] = athlete_id
    race = monday + timedelta(days=90)
    return {
        "brand": "gravelgod", "athlete": athlete,
        "race_snapshot": {"name": "Test Gravel", "date": str(race), "distance_miles": 100},
        "events": [], "weeks": [week],
    }


def test_weekly_briefing_uses_a_known_variation_for_the_week_type():
    """Integration: the rendered weekly-briefing body for a load week is
    exactly one of block_notes.yaml's load variations."""
    plan = _plan("load", athlete_id="guillermo-romero")
    notes = render_notes(plan, {"prescription": {"race_target_g_per_hour": 70}},
                          load_brand("gravelgod"), None)
    briefing = next(n for n in notes if n["type"] == "weekly_briefing")
    load_variations = _load_week_copy()["load"]
    assert any(variation in briefing["body"] for variation in load_variations)


def test_weekly_briefing_matches_the_rotation_function_exactly():
    """The descriptor _weekly_briefing selects for week 1 is exactly what
    _rotate_block_note computes for (athlete id, week number)."""
    plan = _plan("recovery", athlete_id="guillermo-romero")
    notes = render_notes(plan, {"prescription": {"race_target_g_per_hour": 70}},
                          load_brand("gravelgod"), None)
    briefing = next(n for n in notes if n["type"] == "weekly_briefing")
    recovery_variations = _load_week_copy()["recovery"]
    expected = _rotate_block_note(recovery_variations, "guillermo-romero", 1)
    assert expected.strip() in briefing["body"]
