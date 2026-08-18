"""Coverage for the pure, coach-facing DeliveryIR note renderer."""

import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pytest

from delivery_notes import render_notes, _week_sequence, _quality_sessions
from delivery_render import load_brand, render_title


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


def test_taper_briefing_uses_taper_wording_not_recovery_wording():
    """Real defect: the WEEK 7 TAPER briefing opened with 'Recovery week —
    the volume drop is the training', reusing the mid-plan recovery week's
    short-form line -- taper aliases into the same 'recovery' word-copy
    family internally, but athlete-facing wording must say TAPER."""
    plan = _plan(weeks=8)
    plan["weeks"][1]["week_type"] = "recovery"  # earlier recovery week
    plan["weeks"][6]["week_type"] = "taper"      # week 7
    notes = _notes(plan)
    taper = next(note for note in notes if note["type"] == "weekly_briefing"
                 and note["title"].startswith("WEEK 7"))
    assert "Taper —" in taper["body"]
    assert "Recovery week —" not in taper["body"]


def test_recovery_week_briefing_label_outranks_base_phase():
    plan = _plan()
    plan["weeks"][1]["phase"] = "base"
    plan["weeks"][1]["week_type"] = "recovery"
    notes = render_notes(plan, {"prescription": {"race_target_g_per_hour": 70}},
                         load_brand("gravelgod"), None)
    recovery = next(note for note in notes if note["type"] == "weekly_briefing"
                    and note["title"].startswith("WEEK 2 —"))
    assert recovery["title"] == "WEEK 2 — RECOVERY"


def _bike_session(session_date, title, duration_min, **extra):
    return {"date": str(session_date), "title": title, "tp_kind": "bike",
            "duration_s": duration_min * 60, **extra}


def test_recovery_week_sequence_never_calls_a_short_ride_the_long_ride():
    """Regression: Week 4 (recovery) used to say 'Monday's 70-minute
    Endurance — Position Focus is the long ride' -- a recovery week's
    trimmed long ride is not "the long ride" and the sequence should
    describe the week's actual job instead."""
    week = {
        "number": 4, "phase": "base", "week_type": "recovery",
        "sessions": [
            _bike_session(date(2026, 9, 7), "Endurance — Position Focus", 70),
            _bike_session(date(2026, 9, 8), "Openers", 20),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "is the long ride" not in sequence
    assert "recovery week" in sequence.lower()


def test_recovery_week_names_the_long_ride_when_present():
    """Regression: a recovery week with a 210-minute Z2 long ride (the
    week's biggest session, TSS 140) went unnamed in the briefing sequence
    even though the same note's FUEL LADDER section referenced 'this
    week's long ride' -- the same session, described two different ways."""
    week = {
        "number": 3, "phase": "build", "week_type": "recovery",
        "sessions": [
            _bike_session(date(2026, 9, 3), "Tune-Up", 35),
            _bike_session(date(2026, 9, 6), "Endurance", 210),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "210-minute" in sequence
    assert "Sunday" in sequence  # 2026-09-06 is a Sunday
    assert "stays strictly Z2 — long but easy is the assignment" in sequence


def test_recovery_week_without_a_long_ride_omits_the_z2_sentence():
    week = {
        "number": 4, "phase": "base", "week_type": "recovery",
        "sessions": [
            _bike_session(date(2026, 9, 7), "Endurance — Position Focus", 70),
            _bike_session(date(2026, 9, 8), "Openers", 20),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "stays strictly Z2" not in sequence


def test_race_week_sequence_never_calls_the_sharpener_the_long_ride():
    """Regression: race week used to say 'Monday's 58-minute Stars In Your
    Eyes is the long ride' -- the sharpener is not a long ride."""
    week = {
        "number": 9, "phase": "race", "week_type": "race",
        "sessions": [
            _bike_session(date(2026, 10, 13), "Stars In Your Eyes", 58),
            _bike_session(date(2026, 10, 15), "Openers", 20),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "is the long ride" not in sequence


def test_race_week_walks_every_intensity_session_including_monday_sharpener():
    """Real defect: a race week's Monday RPE8-9 intensity session ('Glycolytic
    Power', no ``level`` field, matching none of _QUALITY_KEYWORDS) was
    silently dropped from key_sessions while a Wed sharpener and Fri
    openers were named -- the note undersold the week and claimed
    'Everything else stays easy' about a day that wasn't."""
    week = {
        "number": 9, "phase": "race", "week_type": "race",
        "sessions": [
            _bike_session(date(2026, 10, 12), "Glycolytic Power - 6x60s @145% - RPE8-9", 59,
                          segments=[{"kind": "intervals", "repeat": 6, "on_seconds": 60,
                                     "on_power": 1.45, "off_seconds": 120, "off_power": 0.5}]),
            _bike_session(date(2026, 10, 14), "Stars In Your Eyes", 58),
            _bike_session(date(2026, 10, 16), "Openers", 20),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "Glycolytic Power" in sequence
    assert "Stars In Your Eyes" in sequence
    assert "Openers" in sequence
    assert "The remaining rides stay easy" in sequence
    assert "Everything else stays easy" not in sequence


def test_normal_load_week_still_gets_the_long_ride_label():
    """The fix must not remove the label from a week that actually earns it:
    base/build/peak, week_type load, bike >= 90min."""
    week = {
        "number": 3, "phase": "build", "week_type": "load",
        "sessions": [
            _bike_session(date(2026, 9, 1), "VO2 Intervals", 60),
            _bike_session(date(2026, 9, 6), "Endurance", 200),
        ],
    }
    sequence = _week_sequence(week, _quality_sessions(week))
    assert "is the long ride" in sequence


def test_briefing_includes_level_bearing_structured_float_sets_without_keyword_match():
    plan = _plan()
    float_sets = plan["weeks"][0]["sessions"][0]
    float_sets.update({
        "title": "Float Sets", "display_name": "Float Sets", "level": 4,
        "segments": [{"kind": "intervals", "repeat": 3, "on_seconds": 600,
                      "on_power": .92, "off_seconds": 120, "off_power": .5}],
    })

    first_briefing = next(note for note in _notes(plan)
                          if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 1"))
    assert "Float Sets" in first_briefing["body"]


def test_start_here_quality_weekdays_use_fact_classification_and_exclude_simulations():
    start = date(2026, 8, 10)
    weeks = []
    for number in (1, 2):
        monday = start + timedelta(days=(number - 1) * 7)
        weeks.append({
            "number": number, "phase": "build", "week_type": "build",
            "sessions": [
                {"date": str(monday + timedelta(days=1)), "title": "Float Sets",
                 "tp_kind": "bike", "duration_s": 60 * 60, "level": 3,
                 "segments": [{"kind": "intervals", "repeat": 3, "on_seconds": 600,
                               "on_power": .90, "off_seconds": 120, "off_power": .5}]},
                {"date": str(monday + timedelta(days=5)), "title": "Race Simulation",
                 "tp_kind": "bike", "duration_s": 4 * 60 * 60, "is_simulation": True},
                {"date": str(monday), "title": "Day Off", "tp_kind": "day_off"},
            ],
        })
    plan = {
        "brand": "gravelgod", "athlete": {"name": "Test Athlete"}, "weeks": weeks,
        "race_snapshot": {"name": "Test Race", "date": "2026-08-29"},
    }

    start_here = _by_type(_notes(plan))["start_here"]["body"]
    assert "quality lands on tuesday" in start_here.lower()
    assert "quality lands on saturday" not in start_here.lower()


def test_start_here_omits_one_off_quality_weekdays_from_the_standing_pattern():
    plan = _plan()
    for number, week in enumerate(plan["weeks"], start=1):
        # Thursday is the recurring quality day. Saturday is a one-off FTP
        # test in week 1, not a normal quality-day pattern.
        monday = date.fromisoformat(week["sessions"][0]["date"])
        week["phase"] = "build"
        week["sessions"] = [
            {"date": str(monday + timedelta(days=3)), "title": "Threshold Work",
             "tp_kind": "bike", "duration_s": 60 * 60},
            {"date": str(monday + timedelta(days=5)),
             "title": "FTP Test" if number == 1 else "Endurance Ride",
             "tp_kind": "bike", "duration_s": 60 * 60,
             "is_field_test": number == 1},
            {"date": str(monday + timedelta(days=6)), "title": "Day Off", "tp_kind": "day_off"},
        ]
    start_here = _by_type(_notes(plan))["start_here"]["body"].lower()
    assert "quality lands on thursday" in start_here
    assert "saturday" not in start_here


def test_briefing_uses_the_same_corrected_name_as_the_rendered_calendar_card():
    plan = _plan()
    session = plan["weeks"][1]["sessions"][0]
    session.update({
        "title": "VO2max 40/20", "display_name": "VO2max 40/20",
        "segments": [{"kind": "intervals", "repeat": 6, "on_seconds": 40,
                      "on_power": 1.20, "off_seconds": 15, "off_power": .5}],
    })
    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 2"))
    rendered_name = render_title(session, load_brand("gravelgod")).split(" - ", 1)[0]
    assert rendered_name in briefing["body"]
    assert "VO2max 40/20" not in briefing["body"]


def test_briefing_keeps_the_weeks_simulation_when_three_weekday_sessions_are_keyed():
    plan = _plan()
    week = plan["weeks"][3]
    monday = date.fromisoformat(week["sessions"][0]["date"])
    week["sessions"] = [
        {"date": str(monday + timedelta(days=1)), "title": "VO2 Intervals", "tp_kind": "bike",
         "duration_s": 60 * 60},
        {"date": str(monday + timedelta(days=2)), "title": "Threshold Work", "tp_kind": "bike",
         "duration_s": 60 * 60},
        {"date": str(monday + timedelta(days=3)), "title": "Tempo Work", "tp_kind": "bike",
         "duration_s": 60 * 60},
        {"date": str(monday + timedelta(days=5)), "title": "Race Simulation — Act 2", "tp_kind": "bike",
         "duration_s": 4 * 60 * 60, "is_simulation": True, "is_dress_rehearsal": True},
    ]
    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 4"))
    assert "VO2 Intervals" in briefing["body"]
    assert "Threshold Work" in briefing["body"]
    assert "Tempo Work" not in briefing["body"]
    assert "Race Simulation — Act 2" in briefing["body"]
    assert "Dress rehearsal" in briefing["body"]


def test_briefing_keeps_a_weekend_field_test_in_the_key_session_list():
    plan = _plan()
    week = plan["weeks"][0]
    monday = date.fromisoformat(week["sessions"][0]["date"])
    week["sessions"] = [
        {"date": str(monday + timedelta(days=1)), "title": "Anaerobic Test",
         "tp_kind": "bike", "duration_s": 30 * 60, "is_field_test": True},
        {"date": str(monday + timedelta(days=5)), "title": "FTP Test",
         "tp_kind": "bike", "duration_s": 60 * 60, "is_field_test": True},
    ]

    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 1"))
    key_sessions = briefing["body"].split("THE WEEK IN SEQUENCE", 1)[0]
    assert "Anaerobic Test" in key_sessions
    assert "FTP Test" in key_sessions


def test_briefing_lists_every_simulation_and_marks_the_dress_rehearsal():
    plan = _plan()
    week = plan["weeks"][3]
    monday = date.fromisoformat(week["sessions"][0]["date"])
    week["sessions"] = [
        {"date": str(monday + timedelta(days=3)), "title": "40/15s",
         "tp_kind": "bike", "duration_s": 50 * 60},
        {"date": str(monday + timedelta(days=4)), "title": "Short Race Simulation",
         "tp_kind": "bike", "duration_s": 90 * 60, "is_simulation": True},
        {"date": str(monday + timedelta(days=6)), "title": "Race Simulation — Full Course",
         "tp_kind": "bike", "duration_s": 210 * 60, "is_simulation": True,
         "is_dress_rehearsal": True},
    ]

    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 4"))
    key_sessions = briefing["body"].split("THE WEEK IN SEQUENCE", 1)[0]
    assert "Short Race Simulation" in key_sessions
    assert "Race Simulation — Full Course" in key_sessions
    assert "Dress rehearsal" in key_sessions


def test_taper_briefing_names_the_sharp_cadence_and_burst_sessions():
    plan = _plan()
    week = plan["weeks"][2]
    monday = date.fromisoformat(week["sessions"][0]["date"])
    week.update({"phase": "taper", "week_type": "taper", "sessions": [
        {"date": str(monday + timedelta(days=1)), "title": "Thirty-Fifteens",
         "tp_kind": "bike", "duration_s": 45 * 60},
        {"date": str(monday + timedelta(days=3)), "title": "Cadence Work",
         "tp_kind": "bike", "duration_s": 45 * 60},
        {"date": str(monday + timedelta(days=6)), "title": "Taper Burst Endurance",
         "tp_kind": "bike", "duration_s": 90 * 60},
    ]})

    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 3"))
    assert "Thirty-Fifteens" in briefing["body"]
    assert "Cadence Work" in briefing["body"]
    assert "Taper Burst Endurance" in briefing["body"]


def test_week_sequence_uses_the_actual_quality_weekday_without_a_stock_day_name():
    plan = _plan()
    week = plan["weeks"][1]
    monday = date.fromisoformat(week["sessions"][0]["date"])
    week["sessions"] = [
        {"date": str(monday + timedelta(days=3)), "title": "Threshold Work",
         "tp_kind": "bike", "duration_s": 60 * 60},
        {"date": str(monday + timedelta(days=6)), "title": "Endurance Ride",
         "tp_kind": "bike", "duration_s": 180 * 60},
    ]

    briefing = next(note for note in _notes(plan)
                    if note["type"] == "weekly_briefing" and note["title"].startswith("WEEK 2"))
    sequence = briefing["body"].split("THE WEEK IN SEQUENCE\n", 1)[1].split("\n\nFUEL LADDER", 1)[0]
    assert "Thursday's 60-minute Threshold Work" in sequence
    assert "Tuesday" not in sequence


def test_start_here_off_day_line_carries_recovery_taper_caveat():
    """Regression: 'Off day is Tuesday.' read as a blanket rule even though
    recovery/taper weeks routinely add a second rest day."""
    start = date(2026, 8, 10)  # Monday
    weeks = []
    for number in (1, 2):
        monday = start + timedelta(days=(number - 1) * 7)
        weeks.append({
            "number": number, "phase": "build", "week_type": "build",
            "sessions": [
                {"date": str(monday + timedelta(days=1)), "title": "Day Off", "tp_kind": "day_off"},
                {"date": str(monday + timedelta(days=3)), "title": "Threshold Work",
                 "tp_kind": "bike", "duration_s": 60 * 60},
                {"date": str(monday + timedelta(days=5)), "title": "Endurance Ride",
                 "tp_kind": "bike", "duration_s": 180 * 60},
            ],
        })
    plan = {
        "brand": "gravelgod", "athlete": {"name": "Test Athlete"}, "weeks": weeks,
        "race_snapshot": {"name": "Test Race", "date": "2026-08-29"},
    }
    start_here = _by_type(_notes(plan))["start_here"]["body"]
    assert "Off day is Tuesday (recovery and taper weeks may add a second rest day)" in start_here


def test_weekly_briefing_calls_out_a_recovery_weeks_added_off_day():
    """Regression: a recovery week that adds a Saturday off day beyond the
    plan's normal Tuesday-only pattern gave no transparency about the
    schedule deviation in its own weekly briefing."""
    start = date(2026, 8, 10)  # Monday
    weeks = []
    for number in (1, 2, 3, 4):
        monday = start + timedelta(days=(number - 1) * 7)
        is_recovery = number == 3
        sessions = [
            {"date": str(monday + timedelta(days=1)), "title": "Day Off", "tp_kind": "day_off"},
            {"date": str(monday + timedelta(days=3)), "title": "Threshold Work",
             "tp_kind": "bike", "duration_s": 60 * 60},
        ]
        if is_recovery:
            sessions.append({"date": str(monday + timedelta(days=5)), "title": "Day Off",
                             "tp_kind": "day_off"})
        else:
            sessions.append({"date": str(monday + timedelta(days=5)), "title": "Endurance Ride",
                             "tp_kind": "bike", "duration_s": 180 * 60})
        weeks.append({
            "number": number, "phase": "build",
            "week_type": "recovery" if is_recovery else "build",
            "sessions": sessions,
        })
    plan = {
        "brand": "gravelgod", "athlete": {"name": "Test Athlete"}, "weeks": weeks,
        "race_snapshot": {"name": "Test Race", "date": "2026-10-10"},
    }
    notes = _notes(plan)
    recovery_briefing = next(note for note in notes if note["type"] == "weekly_briefing"
                             and note["title"].startswith("WEEK 3"))
    normal_briefing = next(note for note in notes if note["type"] == "weekly_briefing"
                           and note["title"].startswith("WEEK 1"))
    assert "This week adds a Saturday rest day — that's deliberate." in recovery_briefing["body"]
    assert "This week adds" not in normal_briefing["body"]


def test_start_here_uses_singular_week_and_grit_has_no_fixture_date_residue():
    notes = _notes(_plan(weeks=1))
    assert "1 week to High Country Gravel" in _by_type(notes)["start_here"]["body"]
    grit_body = "\n".join(note["body"] for note in notes if note["type"].startswith("grit_"))
    assert "19 September" not in grit_body
    assert "by race day" in grit_body


def test_weekly_briefing_fuel_ladder_cites_the_weeks_longest_ride():
    """Regression: the briefing's FUEL LADDER line quoted whichever session
    in the week's sessions list matched a ladder date first (a shorter
    Saturday ride) instead of the rate the ladder pins for the week's
    actual longest ride (Sunday's Race Simulation)."""
    week1_sat, week1_sun = date(2026, 8, 15), date(2026, 8, 16)
    week2_sat, week2_sun = date(2026, 8, 22), date(2026, 8, 23)
    race_day = week2_sun + timedelta(days=14)
    plan = {
        "brand": "gravelgod",
        "athlete": {"name": "Test Athlete", "key_markers": {"control_metric": "power"}},
        "race_snapshot": {"name": "Test Gravel", "date": str(race_day), "distance_miles": 80},
        "events": [],
        "weeks": [
            {
                "number": 1, "phase": "build", "week_type": "build",
                "sessions": [
                    _bike_session(week1_sat, "Endurance", 120),
                    _bike_session(week1_sun, "Race Simulation", 230, is_simulation=True),
                ],
            },
            {
                "number": 2, "phase": "build", "week_type": "build",
                "sessions": [
                    _bike_session(week2_sat, "Endurance", 120),
                    _bike_session(week2_sun, "Dress Rehearsal", 230,
                                  is_simulation=True, is_dress_rehearsal=True),
                ],
            },
        ],
    }
    notes = render_notes(plan, {"prescription": {"race_target_g_per_hour": 70}},
                         load_brand("gravelgod"), None)
    briefing = next(note for note in notes if note["type"] == "weekly_briefing"
                    and note["title"].startswith("WEEK 1"))
    assert "This week's long ride: 55 g/hr." in briefing["body"]
    assert "50 g/hr" not in briefing["body"]


def test_hydration_block_owns_its_single_heading_in_the_fuel_ladder_note():
    fuel_note = _by_type(_notes(_plan()))["fuel_ladder"]["body"]
    assert fuel_note.count("HYDRATION") == 1


def test_block_notes_avoid_banned_hydration_doctrine_language():
    notes = (Path(__file__).resolve().parent.parent / "config" / "block_notes.yaml").read_text()
    banned = ("clear urine", "don't wait until thirsty", "hydrate aggressively")
    assert not any(phrase in notes.lower() for phrase in banned)


def test_anaerobic_after_test_note_never_gives_ftp_math():
    plan = _plan()
    session = plan["weeks"][0]["sessions"][1]
    session["title"] = "Anaerobic Test"
    session["display_name"] = "Anaerobic Test"
    session["is_field_test"] = True
    session["description"] = "MAIN SET:\n- 20x0:30 @ 120% FTP, 0:30 recovery\n- 20min build"
    notes = _notes(plan)
    note = _by_type(notes)["after_test"]
    assert "repeatability" in note["body"]
    assert "0.95" not in note["body"]


def test_briefing_long_ride_uses_the_cards_collapsed_name_not_the_archetype():
    plan = _plan()
    long_ride = plan["weeks"][0]["sessions"][2]
    long_ride["title"] = "Endurance Blocks"
    long_ride["display_name"] = "Endurance Blocks"
    long_ride["duration_s"] = 9480
    long_ride["segments"] = [
        {"kind": "steady_state", "duration_s": 9480, "work_percent_ftp": 68},
    ]
    body = " ".join(n["body"] for n in _notes(plan) if n["type"] == "weekly_briefing")
    assert "Endurance Blocks" not in body



def test_sim_touch_is_not_a_rehearsal():
    """A curated midweek race_sim touch sharpens; only Act-class sims and
    the dress rehearsal earn 'rehearsal' language (v21 regrade)."""
    plan = _plan()
    wk = plan["weeks"][0]
    touch = dict(wk["sessions"][1])
    touch.update(title="Peak and Fade", display_name="Peak and Fade",
                 is_simulation=True, is_dress_rehearsal=False,
                 is_field_test=False,
                 library_item_id=999, date=touch["date"])
    reh = dict(wk["sessions"][2])
    reh.update(title="Race Simulation — Act 2 of 2 — Dress Rehearsal",
               display_name="Race Simulation — Act 2 of 2 — Dress Rehearsal",
               is_simulation=True, is_dress_rehearsal=True, duration_s=15000)
    wk["sessions"] = [wk["sessions"][0], touch, reh]
    body = next(n["body"] for n in _notes(plan) if n["type"] == "weekly_briefing")
    import re
    seq = re.search(r"THE WEEK IN SEQUENCE\n([^\n]+)", body).group(1)
    assert "sharpens the race shape" in seq
    assert "Peak and Fade" in seq
    assert seq.index("sharpens") < seq.index("rehearsal")


_UK_SPELLING_RE = re.compile(
    r"practis|organis|fuell|colour|behaviour|centre|tyre", re.IGNORECASE,
)


def _string_constants(module_path: Path):
    """Every string literal in a module's AST -- brand copy lives in plain
    string/docstring constants, never f-string expressions or comments."""
    import ast
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def test_grit_4_is_titled_home_stretch_not_last_three_days():
    # Regression: Gravel Grit note 4 posts on the race-week Tuesday, 4 days
    # before a Saturday race -- "The Last Three Days" was inaccurate by a
    # day. Renamed to "The Home Stretch".
    note = _by_type(_notes(_plan()))["grit_4"]
    assert "The Home Stretch" in note["title"]
    assert "The Last Three Days" not in note["title"]


def test_uk_spelling_regex_catches_capitalized_tyre_forms():
    """Regression: 'Tyres checked.' shipped in the race-week FRIDAY NIGHT
    note (delivery_notes.py) and the UK-spelling regex had no 'tyre'
    pattern at all, so the existing scan test never flagged it."""
    assert _UK_SPELLING_RE.search("Tyres checked.")
    assert _UK_SPELLING_RE.search("Tyre pressure")
    assert _UK_SPELLING_RE.search("tyre pressure")


def test_no_uk_spellings_in_athlete_facing_copy():
    """Regression: 'FUELLING', 'practised', 'Practise', 'organised' shipped
    in athlete-facing notes -- this pipeline's copy is American English."""
    here = Path(__file__).resolve().parent
    for filename in ("delivery_notes.py", "delivery_render.py"):
        for value in _string_constants(here / filename):
            match = _UK_SPELLING_RE.search(value)
            assert not match, (
                f"{filename}: UK spelling {match.group(0)!r} found in "
                f"string constant: {value[:80]!r}"
            )


def test_start_here_carries_masters_line_for_50_plus():
    plan = _plan()
    plan["athlete"]["age"] = 52
    notes = _notes(plan)
    body = next(n["body"] for n in notes if n["title"].startswith("START HERE"))
    assert "at 52" in body and "load-bearing" in body
    plan["athlete"]["age"] = 34
    body_young = next(n["body"] for n in _notes(plan) if n["title"].startswith("START HERE"))
    assert "load-bearing at your age" not in body_young


def test_taper_bursts_label_requires_actual_hard_work():
    from delivery_notes import _taper_specialty
    easy = {"tp_kind": "bike", "title": "FatMax Development - 100min @60%",
            "display_name": "FatMax Development", "archetype_id": "fatmax_bursts",
            "segments": [{"kind": "steady", "seconds": 6000, "power": 0.6}]}
    hard = {"tp_kind": "bike", "title": "Alactic Bursts - 8x8s",
            "display_name": "Alactic Bursts", "archetype_id": "alactic_bursts",
            "segments": [{"kind": "intervals", "repeat": 8, "on_seconds": 8,
                          "on_power": 1.8, "off_seconds": 172, "off_power": 0.55}]}
    assert _taper_specialty(easy) is None
    assert _taper_specialty(hard) == "bursts"
