from contextlib import ExitStack
from unittest.mock import patch

import block_compliance
from calculate_plan_dates import calculate_plan_dates
from block_compliance import (
    ae_1_14_ctl_retention_build,
    ae_1_16_race_day_tsb,
    ae_1_18_ctl_retention_taper,
    ae_1_19_tsb_rails,
    ae_1_19b_tsb_pressure,
    ae_1_22_bc_race_tsb,
    ae_1_4_weekly_ramp,
    ae_1_4b_monthly_ramp,
    ae_1_4c_monthly_ramp_warn_band,
    format_compliance_report,
    validate_plan,
)
from pmc_model import (
    ESTIMATED_TSS_PER_HOUR,
    TAU_ATL_DEFAULT,
    TAU_CTL,
    PMCState,
    build_trajectory,
    estimate_start_ctl,
    plan_daily_tss,
    simulate,
    step,
)


def _trajectory(
    *,
    race_tsb=15,
    race_ctl=100,
    build_ctl=100,
    taper_ctl=100,
    load_tsbs=(0,),
    weekly_deltas=(1,),
    monthly_ramps=(),
    b_races=(),
):
    return {
        "start_ctl": 100,
        "build_ctl": build_ctl,
        "taper_start_ctl": taper_ctl,
        "race_day": {
            "date": "2027-01-28",
            "ctl": race_ctl,
            "atl": race_ctl - race_tsb,
            "tsb": race_tsb,
        },
        "days": [
            {"date": f"2027-01-{i + 1:02d}", "week_type": "load", "tsb": tsb}
            for i, tsb in enumerate(load_tsbs)
        ],
        "weeks": [
            {
                "plan_week": i + 1,
                "week_type": "load",
                "start_ctl": 100,
                "end_ctl": 100 + delta,
                "ctl_delta": delta,
            }
            for i, delta in enumerate(weekly_deltas)
        ],
        "monthly_ramps": list(monthly_ramps),
        "b_races": list(b_races),
    }


def test_constants_state_and_step():
    assert TAU_CTL == 42
    assert TAU_ATL_DEFAULT == 7
    assert ESTIMATED_TSS_PER_HOUR == 55
    state = PMCState(10, 7)
    assert state.tsb == 3
    assert step(state, 10) == PMCState(10, 7 + 3 / 7)


def test_simulate_steady_state_and_response():
    steady = simulate([100] * 10, start_ctl=100)
    assert len(steady) == 10
    assert all(abs(state.ctl - 100) < 1e-9 for state in steady)
    assert abs(simulate([100] * 42, start_ctl=0)[-1].ctl - 63.6) < 0.5
    assert abs(simulate([100] * 7, start_ctl=0)[-1].atl - 66) < 1
    assert simulate([100], start_ctl=20)[0].atl == simulate(
        [100], start_ctl=20, start_atl=20
    )[0].atl


def test_estimate_start_ctl_measured_inferred_and_missing():
    measured = estimate_start_ctl({"fitness_markers": {"ctl": 61}})
    assert measured["ctl"] == 61
    assert measured["value_class"] == "measured"
    inferred = estimate_start_ctl(
        {"training_history": {"current_weekly_hours": 7}}
    )
    assert inferred["ctl"] == 55 * ((3 + 0.65) / 4)
    assert inferred["value_class"] == "inferred"
    assert estimate_start_ctl({"weekly_hours": 7})["ctl"] == 55 * ((3 + 0.65) / 4)
    assert estimate_start_ctl({})["ctl"] == 0


def test_estimate_start_ctl_uses_weekly_availability_fallback():
    result = estimate_start_ctl(
        {"weekly_availability": {"cycling_hours_target": 7}}
    )
    cycle_factor = (3 + 0.65) / 4
    assert result["ctl"] == 55 * cycle_factor
    assert result["inputs"]["hours_source"] == (
        "weekly_availability.cycling_hours_target"
    )
    assert "current hours not reported; assumed at plan target" in result["basis"]


def test_estimate_start_ctl_uses_plan_load_week_density():
    plan = {
        "weeks": [
            {
                "week_type": "load",
                "days": [
                    {"tss": 200, "duration": 300},
                    {"tss": 200, "duration": 300},
                ],
            },
            {
                "week_type": "recovery",
                "days": [{"tss": 400, "duration": 600}],
            },
        ]
    }
    result = estimate_start_ctl(
        {"training_history": {"current_weekly_hours": 7}},
        plan=plan,
    )
    cycle_factor = (3 + 0.65) / 4
    assert result["ctl"] == 40 * cycle_factor
    assert result["inputs"]["tss_per_hour"] == 40
    assert result["inputs"]["source"] == "plan_load_weeks"
    assert result["inputs"]["hours_source"] == (
        "training_history.current_weekly_hours"
    )
    assert result["inputs"]["cycle_factor"] == cycle_factor
    assert result["inputs"]["meso_pattern"] == "3:1"
    assert "40.0 TSS/h" in result["basis"]


def test_estimate_start_ctl_uses_explicit_meso_pattern():
    result = estimate_start_ctl(
        {"training_history": {"current_weekly_hours": 7}},
        plan={"weeks": []},
        meso_pattern="2:1",
    )
    assert result["ctl"] == 55 * 7 / 7 * ((2 + 0.65) / 3)
    assert result["inputs"]["meso_pattern"] == "2:1"


def _synthetic_plan():
    plan_dates = calculate_plan_dates(
        "2027-01-24",
        plan_weeks=4,
        clamp_past_start=False,
        b_events=[{"name": "B Event", "date": "2027-01-10"}],
    )
    plan = {
        "weeks": [
            {
                "plan_week": week["week"],
                "week_type": (
                    "taper" if week["phase"] == "taper"
                    else "race" if week["phase"] == "race"
                    else "load"
                ),
                "days": [
                    {"day": day["day"], "tss": 50}
                    for day in week["days"]
                ],
            }
            for week in plan_dates["weeks"]
        ]
    }
    return plan, plan_dates


def test_plan_daily_tss_and_trajectory_race_and_b_conventions():
    plan, plan_dates = _synthetic_plan()
    daily = plan_daily_tss(plan, plan_dates)
    assert len(daily) == 28
    assert all(entry["tss"] == 50 for entry in daily)
    plan["weeks"][0]["days"][0]["sessions"] = [{"tss": 20}]
    assert plan_daily_tss(plan, plan_dates)[0]["tss"] == 70
    trajectory = build_trajectory(
        plan,
        plan_dates,
        50,
        b_race_dates=["2027-01-10"],
    )
    assert len(trajectory["weeks"]) == 4
    taper = next(week for week in trajectory["weeks"] if week["week_type"] == "taper")
    assert trajectory["taper_start_ctl"] == taper["start_ctl"]
    race_index = next(
        i for i, day in enumerate(trajectory["days"])
        if day["date"] == trajectory["race_day"]["date"]
    )
    assert trajectory["race_day"]["tsb"] == trajectory["days"][race_index - 1]["tsb"]
    assert trajectory["b_races"] == [{"date": "2027-01-10", "tsb": trajectory["b_races"][0]["tsb"]}]


def test_plan_daily_tss_includes_nested_locked_session_load():
    plan, plan_dates = _synthetic_plan()
    plan["weeks"][0]["days"][0]["tss"] = 40
    plan["weeks"][0]["days"][0]["sessions"] = [{"tss": 30, "locked": True}]

    daily = plan_daily_tss(plan, plan_dates)

    assert daily[0]["tss"] == 70


def test_trajectory_uses_emitted_b_race_overlay_loads():
    plan_dates = {
        "race_date": "2027-01-09",
        "weeks": [{
            "week": 1,
            "phase": "build",
            "days": [
                {"day": day, "date": date}
                for day, date in zip(
                    ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
                    ("2027-01-04", "2027-01-05", "2027-01-06", "2027-01-07",
                     "2027-01-08", "2027-01-09", "2027-01-10"),
                )
            ],
        }],
    }
    plan = {
        "weeks": [{
            "plan_week": 1,
            "week_type": "load",
            "days": [
                {"day": day, "tss": 90 if day == "Thu" else 0}
                for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            ],
        }],
    }
    emitted = [
        {"date": "2027-01-07", "tss": 20},  # Saturday B-race -2 Easy
        {"date": "2027-01-08", "tss": 25},  # Saturday B-race -1 Openers
    ]

    trajectory = build_trajectory(plan, plan_dates, 0, daily_override=emitted)
    by_date = {day["date"]: day for day in trajectory["days"]}

    assert by_date["2027-01-07"]["tss"] == 20
    assert by_date["2027-01-08"]["tss"] == 25


def test_trajectory_rules_pass_and_fail():
    passing = _trajectory()
    assert ae_1_14_ctl_retention_build(passing)[0]
    assert ae_1_18_ctl_retention_taper(passing)[0]
    assert ae_1_16_race_day_tsb(passing)[0]
    assert ae_1_19_tsb_rails(passing)[0]
    assert ae_1_19b_tsb_pressure(passing)[0]
    assert ae_1_4_weekly_ramp(passing)[0]
    assert ae_1_4b_monthly_ramp(passing)[0]
    assert ae_1_4c_monthly_ramp_warn_band(passing)[0]
    assert ae_1_22_bc_race_tsb(passing)[0]

    assert not ae_1_14_ctl_retention_build(
        _trajectory(race_ctl=89, build_ctl=100)
    )[0]
    assert not ae_1_18_ctl_retention_taper(
        _trajectory(race_ctl=89, taper_ctl=100)
    )[0]
    assert not ae_1_16_race_day_tsb(_trajectory(race_tsb=2))[0]
    assert not ae_1_19_tsb_rails(_trajectory(load_tsbs=(-31,)))[0]
    assert not ae_1_19b_tsb_pressure(
        _trajectory(load_tsbs=(-21,) * 2 + (0,) * 8)
    )[0]
    assert not ae_1_4_weekly_ramp(_trajectory(weekly_deltas=(9,)))[0]
    monthly = ({"from_date": "2027-01-01", "to_date": "2027-01-29", "ctl_delta_per_28d": 13},)
    assert not ae_1_4b_monthly_ramp(
        _trajectory(monthly_ramps=monthly)
    )[0]
    warning_monthly = (
        {"from_date": "2027-01-01", "to_date": "2027-01-29", "ctl_delta_per_28d": 10.1},
    )
    assert not ae_1_4c_monthly_ramp_warn_band(
        _trajectory(monthly_ramps=warning_monthly)
    )[0]
    assert not ae_1_22_bc_race_tsb(
        _trajectory(b_races=({"date": "2027-01-10", "tsb": 2},))
    )[0]


def test_short_format_and_no_race_messages():
    assert ae_1_16_race_day_tsb(
        _trajectory(race_tsb=-50), short_format=True
    ) == (True, "CX/short-format band OPEN pending ruling — not gated")
    no_race = _trajectory()
    no_race["race_day"] = None
    assert ae_1_16_race_day_tsb(no_race) == (True, "no race day in calendar")
    assert ae_1_14_ctl_retention_build(no_race) == (True, "no race day in calendar")


def test_validate_plan_trajectory_is_opt_in_and_severity_split_is_explicit():
    plan = {"weeks": []}
    without = validate_plan(plan)
    assert not any(key.startswith("AE-") for key in without["rules"])
    trajectory = _trajectory(
        weekly_deltas=(1,) * 12,
        b_races=({"date": "2027-01-10", "tsb": 5},)
    )
    with_warning = validate_plan(plan, trajectory=trajectory)
    assert set(key for key in with_warning["rules"] if key.startswith("AE-")) == {
        "AE-1.14", "AE-1.18", "AE-1.16", "AE-1.19", "AE-1.19b",
        "AE-1.4", "AE-1.4b", "AE-1.4c", "AE-1.22",
    }
    assert with_warning["rules"]["AE-1.22"]["passed"] is False
    without_warning = validate_plan(
        plan,
        trajectory=_trajectory(weekly_deltas=(1,) * 12),
    )
    assert with_warning["critical_pass"] == without_warning["critical_pass"]
    report = format_compliance_report(with_warning)
    assert "AE-1.22 [WARNING]" in report
    assert {
        result["severity"]
        for key, result in with_warning["rules"].items()
        if key.startswith("AE-")
    } == {"CRITICAL", "WARNING"}
    assert {
        key for key, result in with_warning["rules"].items()
        if key.startswith("AE-") and result["severity"] == "CRITICAL"
    } == {
        "AE-1.14", "AE-1.16", "AE-1.18", "AE-1.19",
        "AE-1.4", "AE-1.4b",
    }
    assert {
        key for key, result in with_warning["rules"].items()
        if key.startswith("AE-") and result["severity"] == "WARNING"
    } == {"AE-1.19b", "AE-1.4c", "AE-1.22"}


def test_trajectory_failures_report_critical_and_advisory_rules():
    trajectory = _trajectory(
        race_tsb=0,
        race_ctl=0,
        build_ctl=100,
        taper_ctl=100,
        load_tsbs=(-31, -21),
        weekly_deltas=(9,),
        monthly_ramps=(
            {"from_date": "2027-01-01", "to_date": "2027-01-29", "ctl_delta_per_28d": 13},
            {"from_date": "2027-01-29", "to_date": "2027-02-26", "ctl_delta_per_28d": 10.1},
        ),
        b_races=({"date": "2027-01-10", "tsb": 5},),
    )
    rule_functions = (
        "r01_no_back_to_back_intensity",
        "r02_vo2max_frequency",
        "r03_recovery_tss_ceiling",
        "r04_recovery_intensity_ceiling",
        "r05_intensity_count",
        "r06_long_ride_present",
        "r08_fuel_tags",
        "r11_strength_present",
        "r14_series_coherence",
        "r19_hours_fit",
        "r20_off_days_respected",
    )
    with ExitStack() as stack:
        for function_name in rule_functions:
            stack.enter_context(
                patch.object(
                    block_compliance,
                    function_name,
                    return_value=(True, "pass"),
                )
            )
        result = validate_plan({"weeks": []}, trajectory=trajectory)
    assert all(
        not rule["passed"]
        for key, rule in result["rules"].items()
        if key.startswith("AE-")
    )
    assert result["critical_pass"] is False


def test_short_runway_ae_1_14_is_advisory():
    rule_functions = (
        "r01_no_back_to_back_intensity",
        "r02_vo2max_frequency",
        "r03_recovery_tss_ceiling",
        "r04_recovery_intensity_ceiling",
        "r05_intensity_count",
        "r06_long_ride_present",
        "r08_fuel_tags",
        "r11_strength_present",
        "r14_series_coherence",
        "r19_hours_fit",
        "r20_off_days_respected",
    )
    with ExitStack() as stack:
        for function_name in rule_functions:
            stack.enter_context(
                patch.object(
                    block_compliance,
                    function_name,
                    return_value=(True, "pass"),
                )
            )
        short = validate_plan(
            {"weeks": []},
            trajectory=_trajectory(
                race_ctl=89,
                build_ctl=100,
                taper_ctl=95,
                race_tsb=10,
                weekly_deltas=(1,) * 6,
            ),
        )
        long = validate_plan(
            {"weeks": []},
            trajectory=_trajectory(
                race_ctl=89,
                build_ctl=100,
                taper_ctl=95,
                race_tsb=10,
                weekly_deltas=(1,) * 12,
            ),
        )
    assert short["rules"]["AE-1.14"]["severity"] == "WARNING"
    assert short["critical_pass"] is True
    assert long["rules"]["AE-1.14"]["severity"] == "CRITICAL"
    assert long["critical_pass"] is False
