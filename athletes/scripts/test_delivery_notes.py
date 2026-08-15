"""Coverage for the pure, coach-facing DeliveryIR note renderer."""

from collections import Counter
from datetime import date, timedelta

import pytest

from delivery_notes import render_notes
from delivery_render import load_brand


def _plan(*, weeks=5, metric="power", altitude=True, later_event=True):
    start = date(2026, 8, 10)
    race = start + timedelta(days=weeks * 7 - 1)
    plan_weeks = []
    for number in range(1, weeks + 1):
        monday = start + timedelta(days=(number - 1) * 7)
        plan_weeks.append({
            "number": number,
            "week_type": "race" if number == weeks else "build",
            "sessions": [
                {"date": str(monday), "title": "VO2 Intervals", "tp_kind": "bike", "duration_s": 60 * 60},
                {"date": str(monday + timedelta(days=2)),
                 "title": "20-minute FTP Test" if number == 1 else "Threshold Work",
                 "tp_kind": "bike", "duration_s": 60 * 60, "is_field_test": number == 1},
                {"date": str(monday + timedelta(days=5)), "title": "Long Simulation", "tp_kind": "bike",
                 "duration_s": 3 * 60 * 60, "is_simulation": number >= 3,
                 "is_dress_rehearsal": number == weeks - 1},
                {"date": str(monday + timedelta(days=6)), "title": "Day Off", "tp_kind": "day_off"},
            ],
        })
    snapshot = {"name": "High Country Gravel", "date": str(race), "distance_miles": 80,
                "race_metadata": {"start_elevation_feet": 8000, "location": "FORBIDDEN"} if altitude else None}
    events = [{"name": "Autumn Classic", "date": str(race + timedelta(days=21)), "priority": "A"}] if later_event else []
    return {
        "brand": "gravelgod", "athlete": {"name": "Guillermo Romero", "key_markers": {"control_metric": metric}},
        "race_snapshot": snapshot, "events": events, "weeks": plan_weeks,
    }


def _notes(plan, brand="gravelgod"):
    return render_notes(plan, {"prescription": {"race_target_g_per_hour": 70}}, load_brand(brand), "https://guide.example/guillermo")


def _by_type(notes):
    return {note["type"]: note for note in notes}


def test_full_guillermo_render_has_complete_inventory_and_safe_copy():
    notes = _notes(_plan())
    types = [note["type"] for note in notes]
    assert {"start_here", "fuel_ladder", "altitude_heat", "checkin", "rehearsal_debrief", "race_week", "after_nurture"} <= set(types)
    assert {f"grit_{n}" for n in range(1, 5)} <= set(types)
    assert types.count("weekly_briefing") == 5
    assert all(note["date"] >= "2026-08-10" for note in notes)
    body = "\n".join(note["body"] for note in notes).lower()
    assert "{first_name}" not in body
    assert "clear urine" not in body and "don't wait until thirsty" not in body
    # Notes must carry the inbox a human answers, not the transactional
    # from-address (brands.yaml coaching_email).
    assert "gravelgodcoaching@gmail.com" in body
    assert "coach@gravelgod.com" not in body
    assert "FORBIDDEN" not in _by_type(notes)["race_week"]["body"]
    # The only @ in delivered prose is the approved coaching contact.
    assert all("@" not in note["body"].replace("gravelgodcoaching@gmail.com", "") for note in notes)


def test_four_week_plan_converges_without_note_collisions_and_keeps_grit():
    notes = _notes(_plan(weeks=4))
    count = Counter(note["date"] for note in notes)
    assert max(count.values()) <= 2
    assert {f"grit_{n}" for n in range(1, 5)} <= {note["type"] for note in notes}


def test_rpe_test_never_tells_athlete_to_apply_ftp_multiplier():
    plan = _plan(metric="rpe")
    plan["weeks"][0]["sessions"][1]["title"] = "RPE Field Test"
    note = _by_type(_notes(plan))["after_test"]
    assert "0.95" not in note["body"]
    assert "RPE" in _by_type(_notes(plan))["start_here"]["body"]


def test_missing_optional_anchors_omit_their_notes_and_bridge():
    notes = _notes(_plan(altitude=False, later_event=False))
    by_type = _by_type(notes)
    assert "altitude_heat" not in by_type
    assert "Autumn Classic" not in by_type["after_nurture"]["body"]


def test_unknown_brand_fails_closed():
    with pytest.raises(ValueError, match="Unknown delivery brand"):
        render_notes(_plan(), {"prescription": {"race_target_g_per_hour": 70}}, "not-a-brand", None)


def test_roadie_uses_generic_mental_skills_branding():
    plan = _plan()
    plan["brand"] = "roadielabs"
    note = _by_type(_notes(plan, "roadielabs"))["grit_1"]
    assert note["title"].startswith("MENTAL SKILLS")
