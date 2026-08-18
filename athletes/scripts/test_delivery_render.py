"""Contract tests for the pure DeliveryIR rendering helpers."""

import json
import math
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


def test_alternating_two_power_endurance_archetype_counts_every_block():
    # Real graded defect: "Aerobic Base" alternates gently between ~68%
    # and ~72% every 20min across a 3h ride ("so it doesn't go dead") --
    # eight 20-min blocks total, four at each power. The title-deriving
    # tie-break grouped them into two separate 4-rep bands and arbitrarily
    # picked one, undercounting the title to "4x20min @68%". Both bands
    # tie for defining-block rank and sit close together (a real hard/easy
    # interval contrast sits much further apart), so they must combine
    # into one count spanning the actual range ridden.
    session = Session(
        date="2026-08-27", title="Aerobic Base", display_name="Aerobic Base",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=180 * 60, tss=142, library_item_id=14416906,
        segments=[
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.68),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.72),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.68),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.72),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.68),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.72),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.68),
            Segment(name="steady", kind="steady_state", seconds=1200, power_target=.72),
        ],
    )
    title = render_title(session, BRAND)
    assert "8x20min" in title
    assert "4x20min" not in title


def test_main_set_prefers_highest_work_block_over_easy_bookends():
    # Real graded defect: "Discount Fair" (curated item 14355846) is a
    # 15min@56-75% bookend + 4x(6min Hard + 4min Easy, both targeted
    # 76-90%) + 15min@56-75% bookend. The two Z2 bookends (1800s total)
    # outranked the 4x6min tempo work (1440s total) because the ranking
    # fallback picked the longest block, not the hardest. seconds x pct
    # ("work") must decide: 1800*66=118,800 for the bookends vs
    # 1440*83=119,520 for the tempo blocks -- the tempo work wins the
    # title, not the padding.
    session = Session(
        date="2026-09-21", title="Discount Fair", display_name="Discount Fair",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=70 * 60, tss=60, library_item_id=14355846,
        structure={
            "primaryIntensityMetric": "percentOfFtp",
            "structure": [
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Steady State",
                     "length": {"unit": "second", "value": 900},
                     "targets": [{"minValue": 66}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Work",
                     "length": {"unit": "second", "value": 360},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "rest", "name": "Recovery",
                     "length": {"unit": "second", "value": 240},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Work",
                     "length": {"unit": "second", "value": 360},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "rest", "name": "Recovery",
                     "length": {"unit": "second", "value": 240},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Work",
                     "length": {"unit": "second", "value": 360},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "rest", "name": "Recovery",
                     "length": {"unit": "second", "value": 240},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Work",
                     "length": {"unit": "second", "value": 360},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "rest", "name": "Recovery",
                     "length": {"unit": "second", "value": 240},
                     "targets": [{"minValue": 83}]},
                ]},
                {"length": {"unit": "repetition", "value": 1}, "steps": [
                    {"intensityClass": "active", "name": "Steady State",
                     "length": {"unit": "second", "value": 900},
                     "targets": [{"minValue": 66}]},
                ]},
            ],
        },
    )
    title = render_title(session, BRAND)
    assert "4x6min @83%" in title
    assert "2x15min" not in title


def test_openers_title_discloses_its_biggest_effort_not_just_the_reps():
    # Real graded defect: "Pre-Race Openers" titled itself "3x30s @125%"
    # and never mentioned the standalone "2min @120%" effort that precedes
    # it in the same session (main-set ranking picks one winning block
    # group, dropping the lead-in). Openers must lead with the longest
    # supra-threshold effort. Scoped to display names carrying "opener".
    session = Session(
        date="2026-09-15", title="Pre-Race Openers", display_name="Pre-Race Openers",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=25 * 60, tss=20,
        segments=[
            Segment(name="lead-in", kind="steady_state", seconds=120, power_target=1.20),
            Segment(name="stabs", kind="intervals", seconds=630, repeat=3,
                    on_seconds=30, on_power=1.25, off_seconds=120, off_power=.55),
        ],
    )
    title = render_title(session, BRAND)
    assert "2min @120% + 3x30s @125%" in title


def test_non_opener_title_unaffected_by_the_disclosure_rule():
    # The same shape on a non-opener session must render exactly as before
    # -- the disclosure rule is scoped to "opener" display names only.
    session = Session(
        date="2026-09-15", title="Race Simulation", display_name="Race Simulation",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=25 * 60, tss=20,
        segments=[
            Segment(name="lead-in", kind="steady_state", seconds=120, power_target=1.20),
            Segment(name="stabs", kind="intervals", seconds=630, repeat=3,
                    on_seconds=30, on_power=1.25, off_seconds=120, off_power=.55),
        ],
    )
    title = render_title(session, BRAND)
    assert "2min @120% + 3x30s @125%" not in title
    assert "3x30s @125%" in title


def test_library_session_authored_rpe_wins_over_structure_derived_rpe():
    # Real graded defect: a library-resolved session with dominant power 80%
    # (structure-derived RPE5-6) carried the coach's own authored "RPE3-4"
    # in its canonical name. The card must honor the authored call, not
    # overwrite it with the dominant-power heuristic.
    session = Session(
        date="2026-08-27", title="High Cadence Intervals - RPE3-4",
        display_name="High Cadence Intervals - RPE3-4",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=51 * 60, tss=50, library_item_id=42001,
        segments=[Segment(name="cadence", kind="intervals", seconds=25 * 60,
                          repeat=4, on_seconds=5 * 60, on_power=.80,
                          off_seconds=60, off_power=.5)],
    )
    title = render_title(session, BRAND)
    assert title.endswith("RPE3-4")
    assert "RPE5-6" not in title
    assert title.count("RPE") == 1


def test_suspect_authored_rpe_is_a_lint_matter_not_a_renderer_override():
    # Real graded defect: curated item 14357243 ("Torque - HC") carries an
    # authored RPE8-9 on a 65%-FTP high-cadence drill. The renderer does
    # NOT overrule the coach's authored token -- the item is excluded from
    # selection via tp_library_snapshot's lint_manual_review entry instead,
    # so it can never ship until fixed at the source in TrainingPeaks.
    from tp_library_snapshot import _MANUAL_REVIEW
    assert 14357243 in _MANUAL_REVIEW
    session = Session(
        date="2026-08-28", title="Cadence HC - RPE8-9",
        display_name="Cadence HC - RPE8-9",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=35 * 60, tss=30, library_item_id=14357243, library_rpe_text="8-9",
        segments=[Segment(name="intervals", kind="intervals", seconds=1200,
                          repeat=5, on_seconds=60, on_power=.82,
                          off_seconds=180, off_power=.55)],
    )
    title = render_title(session, BRAND)
    assert title.endswith("RPE8-9")  # authored always wins at render time


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
    (Session(None, "Strength", "strength", "strength", "prescribed", 45 * 60, 0,
             tp_kind="strength", strength_template="Foundation Strength A"),
     "Foundation Strength A - 45min"),
    (Session(None, "Rest Day", "cycling", "rest", "rest", 0, 0,
             tp_kind="day_off"), "Day Off"),
    (Session(None, "RACE_DAY_Mammoth Tuff", "cycling", "race", "event", 0, 0,
             tp_kind="race", race={"name": "Mammoth Tuff"}), "RACE DAY — Mammoth Tuff"),
])
def test_title_grammar_per_kind(session, expected):
    assert render_title(session, BRAND) == expected


def test_strength_title_normalizes_lowercase_template_key_without_changing_words():
    session = Session(
        None, "Strength", "strength", "strength", "prescribed", 45 * 60, 0,
        tp_kind="strength", strength_template="foundation_a",
    )
    assert render_title(session, BRAND) == "Foundation A - 45min"


def test_simulation_title_uses_act_name_not_an_arbitrary_interval_set():
    session = Session(
        date="2026-08-29", title="Race Simulation — Act 1 of 3",
        display_name="Race Simulation — Act 1 of 3", sport="cycling",
        type="workout", origin="prescribed", tp_kind="bike", duration_s=300 * 60,
        tss=250, is_simulation=True,
        segments=[Segment(name="pyramid rep", kind="intervals", seconds=9 * 60,
                          repeat=3, on_seconds=3 * 60, on_power=.90,
                          off_seconds=60, off_power=.5)],
    )

    assert render_title(session, BRAND) == "Race Simulation — Act 1 of 3 - 300min - RPE6-7"


def test_title_corrects_stale_work_rest_pattern_from_emitted_intervals():
    session = Session(
        date="2026-08-27", title="VO2max 40/20", display_name="VO2max 40/20",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=35 * 60, tss=50,
        segments=[Segment(name="VO2", kind="intervals", seconds=6 * 55,
                          repeat=6, on_seconds=40, on_power=1.20,
                          off_seconds=15, off_power=.5)],
    )

    assert render_title(session, BRAND) == "VO2max 40/15 - 6x40s @120% - 35min - RPE8-9"


def test_title_corrects_stale_work_rest_pattern_from_captured_tp_structure():
    session = Session(
        date="2026-08-27", title="VO2max 40/20", display_name="VO2max 40/20",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=35 * 60, tss=50,
        structure={"primaryIntensityMetric": "percentOfFtp", "structure": [{
            "length": {"unit": "repetition", "value": 6}, "steps": [
                {"intensityClass": "active", "length": {"unit": "second", "value": 40},
                 "targets": [{"minValue": 120}]},
                {"intensityClass": "rest", "length": {"unit": "second", "value": 15},
                 "targets": [{"maxValue": 50}]},
            ],
        }]},
    )

    assert render_title(session, BRAND).startswith("VO2max 40/15 - ")


def test_title_renders_repeating_short_effort_pyramid_as_one_set():
    session = Session(
        date="2026-09-15", title="Stars In Your Eyes 6x40s",
        display_name="Stars In Your Eyes 6x40s", sport="cycling", type="workout",
        origin="prescribed", tp_kind="bike", duration_s=60 * 60, tss=70,
        segments=[
            Segment(name="20s", kind="intervals", seconds=180, repeat=3,
                    on_seconds=20, on_power=1.50, off_seconds=40, off_power=.55),
            Segment(name="30s", kind="intervals", seconds=225, repeat=3,
                    on_seconds=30, on_power=1.55, off_seconds=45, off_power=.55),
            Segment(name="40s", kind="intervals", seconds=300, repeat=3,
                    on_seconds=40, on_power=1.60, off_seconds=60, off_power=.55),
        ],
    )

    assert render_title(session, BRAND) == (
        "Stars In Your Eyes - 3x(20/30/40s) @150-160% - 60min - RPE8-9")


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
    # Regression: race day is a bike-typed FreeRide with no power structure --
    # it must not be the one bike card left with a null IF. IF is derived
    # from TSS/duration the same way TP derives it: sqrt(TSS / (hours*100)).
    assert render_if_planned(race) == round(math.sqrt(250 / (4 * 100.0)), 4)


def test_race_day_card_emits_if_planned_from_snapshot_tss_and_duration():
    """Regression: verified live, the race day card was the only bike-typed
    card with ifPlanned null. 394 TSS over an expected 9.3333h race ->
    IF = sqrt(394 / (9.3333*100)) ~= 0.65."""
    race = Session(None, "Race Day", "cycling", "race", "event",
                   int(9.3333 * 3600), 394, tp_kind="race", tss_planned=394)
    if_planned = render_if_planned(race)
    assert if_planned is not None
    assert round(if_planned, 2) == 0.65


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


def test_rpe_metric_structure_never_renders_percent_title():
    """Real shipped defect: 'Muscle Recruitment Progressions' (the plan's
    only primaryIntensityMetric=='rpe' item) titled as '19x60s @5%' —
    RPE-5 targets rendered through the %FTP grammar."""
    session = Session(
        date="2026-09-18", title="Muscle Recruitment Progressions",
        display_name="Muscle Recruitment Progressions",
        sport="cycling", type="workout", origin="prescribed", tp_kind="bike",
        duration_s=3600, tss=40, library_item_id=14356256, library_rpe_text="5-6",
        structure={"primaryIntensityMetric": "rpe", "structure": [
            {"length": {"value": 19}, "steps": [
                {"name": "On", "length": {"value": 60}, "targets": [{"minValue": 5}]},
                {"name": "Off", "length": {"value": 120}, "targets": [{"minValue": 3}]}]}]},
    )
    title = render_title(session, BRAND)
    assert "@5%" not in title and "@ 5%" not in title
    assert title.endswith("RPE5-6")
