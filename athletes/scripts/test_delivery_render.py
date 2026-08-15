"""Contract tests for the pure DeliveryIR rendering helpers."""

import json
import re
from pathlib import Path

import pytest

from delivery_render import (
    build_fuel_ladder,
    decorate_day_off,
    load_brand,
    render_fuel_block,
    render_hydration_block,
    render_if_planned,
    render_title,
)
from plan_ir import PlanIR, RaceSnapshot, Segment, Session, Week


BRAND = load_brand("gravelgod")


def _bike(date, minutes, *, title="Tempo", segments=None, structure=None,
          week_type="build", simulation=False, dress=False):
    return Week(number=1, week_type=week_type, sessions=[Session(
        date=date, title=title, display_name=title, sport="cycling",
        type="workout", origin="prescribed", tp_kind="bike",
        duration_s=minutes * 60, tss=80, tss_planned=80,
        total_time_planned=minutes / 60, segments=segments or [],
        structure=structure, is_simulation=simulation,
        is_dress_rehearsal=dress,
    )])


def test_title_uses_emitted_structure_not_archetype_lie():
    session = Session(
        date="2026-08-27", title="3x15 Tempo", display_name="3x15 Tempo - Level 4/6",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=60 * 60, tss=60,
        segments=[Segment(name="tempo", kind="intervals", seconds=24 * 60,
                          repeat=3, on_seconds=8 * 60, on_power=.90,
                          off_seconds=3 * 60, off_power=.5)],
    )

    assert render_title(session, BRAND) == "Tempo - 3x8min @90% - 60min - RPE6-7"


def test_title_parses_main_set_for_structure_free_rpe_athlete():
    session = Session(
        date="2026-08-27", title="Tempo", display_name="Tempo - Level 2/6",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=3590, tss=45, control_metric="rpe",
        description="PURPOSE:\nSteady work\n\nMAIN SET:\n- 3 x 8min at 90% FTP\n",
    )

    assert render_title(session, BRAND) == "Tempo - 3x8min @90% - 60min - RPE6-7"


@pytest.mark.parametrize(("session", "expected"), [
    (Session(None, "Endurance", "cycling", "workout", "prescribed", 90 * 60, 40,
             tp_kind="bike", display_name="Endurance"), "Endurance - 90min - RPE3"),
    (Session(None, "Strength", "strength", "strength", "prescribed", 60, 0,
             tp_kind="strength", strength_template="Foundation Strength A"),
     "Foundation Strength A - 30min"),
    (Session(None, "Rest Day", "cycling", "rest", "rest", 0, 0,
             tp_kind="day_off"), "Day Off"),
    (Session(None, "RACE_DAY_Mammoth Tuff", "cycling", "race", "event", 0, 0,
             tp_kind="race", race={"name": "Mammoth Tuff"}), "RACE DAY — Mammoth Tuff"),
])
def test_title_grammar_per_kind(session, expected):
    assert render_title(session, BRAND) == expected


def test_if_planned_is_power_structure_only():
    structured = Session(
        None, "Intervals", "cycling", "workout", "prescribed", 60 * 60, 64,
        tp_kind="bike", tss_planned=64,
        structure={"primaryIntensityMetric": "percentOfFtp"},
        segments=[Segment("work", 600, "steady_state", power_target=.9)],
    )
    rpe = Session(
        None, "RPE intervals", "cycling", "workout", "prescribed", 60 * 60, 64,
        tp_kind="bike", tss_planned=64, control_metric="rpe",
        structure={"primaryIntensityMetric": "percentOfFtp"},
        segments=[Segment("work", 600, "steady_state", power_target=.9)],
    )
    strength = Session(None, "Strength", "strength", "strength", "prescribed", 30 * 60, 10,
                       tp_kind="strength")
    race = Session(None, "Race", "cycling", "race", "event", 4 * 3600, 250,
                   tp_kind="race")

    assert render_if_planned(structured) == .8
    assert render_if_planned(rpe) is None
    assert render_if_planned(strength) is None
    assert render_if_planned(race) is None


def test_day_off_decoration_variants():
    assert decorate_day_off("2026-09-16", "race", "2026-09-19")["title"] == "Day Off — Race Week Rest"
    assert decorate_day_off("2026-09-18", "race", "2026-09-19")["title"] == "Day Off — Race Prep"
    assert decorate_day_off("2026-09-20", "race", "2026-09-19")["title"] == "Day Off — Well Done"
    assert decorate_day_off("2026-09-02", "build", "2026-09-19")["title"] == "Day Off"


def test_fuel_ladder_reaches_race_rate_then_explicitly_steps_back_for_taper():
    weeks = [
        _bike("2026-08-22", 130, week_type="build"),
        _bike("2026-08-29", 300, title="Race Sim", week_type="build", simulation=True),
        _bike("2026-09-05", 300, title="Race Sim", week_type="peak", simulation=True, dress=True),
        _bike("2026-09-12", 100, title="Endurance", week_type="taper"),
        Week(number=5, week_type="race", sessions=[Session(
            "2026-09-19", "Mammoth Tuff", "cycling", "race", "event", 6 * 3600, 280,
            tp_kind="race",
        )]),
    ]
    plan = PlanIR(athlete=None, race_snapshot=RaceSnapshot(name="Mammoth Tuff", date="2026-09-19"),
                  fueling=None, weeks=weeks)
    ladder = build_fuel_ladder(plan, {"prescription": {
        "race_target_g_per_hour": 66, "race_range_g_per_hour": [59, 73],
    }})

    build_rates = [ladder[day] for day in ("2026-08-22", "2026-08-29", "2026-09-05")]
    assert build_rates == sorted(build_rates)
    assert ladder["final_rehearsal_date"] == "2026-09-05"
    assert ladder["2026-09-05"] == 66
    assert ladder["2026-09-12"] < 66
    assert ladder["2026-09-19"] == 66
    assert "use the ladder" in render_fuel_block("2026-09-05", ladder)


def test_hydration_copy_is_thirst_led_and_excludes_eah_hazards():
    hydration = render_hydration_block().lower()
    assert "drink to thirst" in hydration
    assert "500-750 ml/hr" in hydration
    assert "500-1000 mg sodium" in hydration
    assert "never heavier" in hydration
    assert "don't wait until thirsty" not in hydration
    assert "clear urine" not in hydration


def test_guillermo_structured_workouts_keep_fixture_duration_segment():
    fixture = json.loads((Path(__file__).resolve().parents[2] / "references" /
                          "guillermo-2026-08.json").read_text())
    for workout in fixture["workouts"]:
        if workout["kind"] != "bike" or not workout.get("structure"):
            continue
        session = Session(
            date=workout["date"], title=workout["title"], display_name=workout["title"],
            sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
            duration_s=round(workout["totalTimePlanned"] * 3600),
            tss=round(workout["tssPlanned"]), tss_planned=workout["tssPlanned"],
            total_time_planned=workout["totalTimePlanned"], structure=workout["structure"],
        )
        expected = re.search(r"- (\d+)min -", workout["title"])
        actual = re.search(r"- (\d+)min -", render_title(session, BRAND))
        assert expected, workout["title"]
        assert actual, render_title(session, BRAND)
        assert actual.group(1) == expected.group(1)


def test_unknown_brand_fails_closed():
    with pytest.raises(ValueError, match="Unknown delivery brand"):
        load_brand("not-a-brand")


def test_defining_set_never_contradicts_hard_rpe():
    # Real graded card: "Anaerobic Test - 29min @55% - RPE9-10" — the filler
    # spin headlined a test whose work is a target-free 3min all-out.
    session = Session(
        date="2026-08-20", title="Anaerobic Test", display_name="Anaerobic Test",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=62 * 60, tss=36, is_field_test=True,
        description="MAIN SET:\n- 29min @ 55% FTP\n- 3min free ride\n\n"
                    "-3-minute all-out test - go hard from the start, hold on",
        segments=[Segment(name="spin", kind="steady_state", seconds=29 * 60,
                          power_target=".55")],
    )
    title = render_title(session, BRAND)
    assert "@55" not in title
    assert "3min all-out" in title
    assert title.endswith("RPE9-10")


def test_repeated_single_rep_segments_group_into_rep_count():
    # Surge rides emit 15 separate one-rep interval segments; the title must
    # carry 15x, not a bare 6s.
    surges = [Segment(name=f"burst{i}", kind="intervals", seconds=6, repeat=1,
                      on_seconds=6, on_power=1.5) for i in range(15)]
    session = Session(
        date="2026-09-20", title="Endurance with Surges",
        display_name="Endurance with Surges", sport="cycling", type="workout",
        origin="prescribed", tp_kind="bike", duration_s=248 * 60, tss=212,
        segments=surges,
    )
    assert "15x6s @150%" in render_title(session, BRAND)
