"""A1 deterministic offline fixtures for HR/LTHR, HRmax, and RPE control."""
from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

import plan_ir
from canonical_training_model import (CanonicalModelError, MODEL_VERSION,
                                      build_canonical_model,
                                      project_guide_html,
                                      publish_zwo_projection,
                                      validate_canonical_model)
from apply_contract import build_contract
from generate_plan_preview import build_preview_data
from plan_ir import build_plan_ir, project_tp_manifest
from validate_plan_package import validate_plan_package


CASES = json.loads(
    (Path(__file__).resolve().parents[2] / "tests" / "fixtures" /
     "truthful_power" / "control_cases.json").read_text())

PRESCRIPTION = {
    "race_target_g_per_hour": 65, "race_range_g_per_hour": [55, 75], "total_g": 260,
    "training_tiers": {"quality": {"target_g_per_hour": 55, "range_g_per_hour": [45, 65]},
                       "long_ride": {"target_g_per_hour": 60, "range_g_per_hour": [50, 70]},
                       "race_sim": {"target_g_per_hour": 65, "range_g_per_hour": [55, 75]}},
    "hydration": {"target_ml_per_hour": 600}, "assumptions": [],
    "inputs": {"basis": "duration_body_mass_intensity", "duration_hours": 4,
               "weight_kg": 70, "intensity_descriptor": "finish"},
    "policy_version": "fixture",
}


def _write_fixture(tmp_path, case):
    athletes = tmp_path / "athletes"
    root = athletes / case["id"]
    workouts = root / "workouts"
    workouts.mkdir(parents=True)
    profile = {
        "name": "Truthful Fixture", "weight_kg": 70,
        "fitness_markers": case["fitness_markers"],
        "fulfillment": {"generation_at": "2026-08-08T12:00:00Z"},
        "target_race": {"name": "Fixture Gravel", "date": "2026-09-01"},
    }
    plan_dates = {"race_date": "2026-09-01", "weeks": [{"week": 1, "phase": "base",
        "days": [{"date": "2026-08-14", "workout_prefix": "W01_Fri_Aug14"}]}]}
    (root / "profile.yaml").write_text(yaml.safe_dump(profile))
    (root / "fueling.yaml").write_text(yaml.safe_dump({"prescription": PRESCRIPTION}))
    (root / "plan_dates.yaml").write_text(yaml.safe_dump(plan_dates))
    (root / "weekly_structure.yaml").write_text("days: {}\n")
    (workouts / "W01_Fri_Aug14_FTP_TEST.zwo").write_text(
        "<?xml version='1.0'?><workout_file><name>FTP Field Test</name>"
        "<description>20 min at 95% FTP; record average watts.</description><workout>"
        "<Warmup Duration='600' PowerLow='0.45' PowerHigh='0.65'/>"
        "<SteadyState Duration='1200' Power='0.95'/>"
        "<Cooldown Duration='300' PowerLow='0.55' PowerHigh='0.40'/>"
        "</workout></workout_file>")
    return athletes, root, plan_dates


@pytest.mark.parametrize("case", CASES, ids=lambda item: item["id"])
def test_truthful_control_fixture_projects_without_watts(tmp_path, monkeypatch, case):
    athletes, root, plan_dates = _write_fixture(tmp_path, case)
    monkeypatch.setattr(plan_ir, "ATHLETES_DIR", athletes)
    model = build_canonical_model(case["id"], root, plan_dates=plan_dates)
    assert model["athlete"]["ftp_watts"] is None
    assert model["athlete"]["power_basis"] == "none"
    assert model["athlete"]["control_metric"] == case["metric"]
    assert model["athlete"]["control_basis"] == case["basis"]
    assert model["sessions"][0]["title"] == case["field_test"]
    assert "RE-ANCHOR" in model["sessions"][0]["description"]
    assert all(segment["target"]["type"] == case["target_type"]
               for segment in model["sessions"][0]["segments"])
    assert not list((root / "workouts").glob("*.zwo"))

    ir = build_plan_ir(case["id"])
    session = ir.weeks[0].sessions[0]
    if case["tp_target_type"]:
        assert session.structure["primaryIntensityMetric"] == case["tp_target_type"]
        assert session.structure["structure"][0]["steps"][0]["targets"]
    else:
        assert session.structure is None
        assert "PRESCRIPTION:" in session.description
    tp = project_tp_manifest(ir)
    serialized = json.dumps({"canonical": model, "plan_ir": ir.to_dict(), "tp": tp})
    assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:W|watts?)\b", serialized, re.I)
    assert not re.search(r"\b\d+(?:\.\d+)?\s*%\s*FTP\b", serialized, re.I)


def test_power_interval_plan_ir_matches_zwo_bounds(tmp_path, monkeypatch):
    """PlanIR's power compatibility fields describe the executable ZWO exactly."""
    case = {
        "id": "power-interval-fixture",
        "fitness_markers": {
            "ftp_watts": 250,
            "power_basis": "measured",
            "requested_metric": "power",
        },
    }
    athletes, root, plan_dates = _write_fixture(tmp_path, case)
    authored = root / "workouts" / "W01_Fri_Aug14_FTP_TEST.zwo"
    zwo = root / "workouts" / "W01_Fri_Aug14_VO2max_4020_1.zwo"
    authored.rename(zwo)
    zwo.write_text(
        "<?xml version='1.0'?><workout_file><name>Power Intervals</name>"
        "<description>MAIN SET:\n- 6x0:40 @ 120% FTP, 0:20 recovery @ 50% FTP"
        "</description><workout>"
        "<IntervalsT Repeat='6' OnDuration='40' OnPower='1.2' "
        "OffDuration='20' OffPower='0.5'/>"
        "</workout></workout_file>"
    )
    monkeypatch.setattr(plan_ir, "ATHLETES_DIR", athletes)

    build_canonical_model(case["id"], root, plan_dates=plan_dates)
    interval = build_plan_ir(case["id"]).weeks[0].sessions[0].segments[0]

    assert interval.on_power == 1.2
    assert interval.off_power == .5
    assert interval.power_low == .5
    assert interval.power_high == 1.2
    assert validate_plan_package(root) == []


def test_canonical_round_trip_is_the_only_session_projection_input(
    tmp_path, monkeypatch,
):
    """ZWO, PlanIR, preview, TP/polyline, and D0 share one finalized input."""
    case = {
        "id": "canonical-upstream-fixture",
        "fitness_markers": {
            "ftp_watts": 250, "power_basis": "measured",
            "requested_metric": "power",
        },
    }
    athletes, root, plan_dates = _write_fixture(tmp_path, case)
    authored = root / "workouts" / "W01_Fri_Aug14_FTP_TEST.zwo"
    authored_text = authored.read_text()
    authored.unlink()
    stem = "W01_Fri_Aug14_FTP_TEST"

    # Production's private compiler hands this document over in memory. No
    # published workout exists for canonicalization to reflect.
    model = build_canonical_model(
        case["id"], root, plan_dates=plan_dates,
        authored_documents={stem: authored_text},
        naming_manifest={stem: {
            "filename_stem": stem, "week_num": 1, "phase": "base",
            "tp_kind": "bike", "workout_type_value_id": 2,
        }},
    )
    session = model["sessions"][0]
    assert session["title"] == "FTP Field Test"
    assert session["segments"][1]["target"] == {
        "type": "power_pct_ftp", "value": .95,
    }

    # A competing legacy file cannot influence any projection and is removed
    # by publication from the already-finalized canonical model.
    (root / "workouts" / "legacy-wrong.zwo").write_text(
        "<workout_file><name>WRONG SOURCE</name><workout/></workout_file>")
    publish_zwo_projection(model, root)
    assert not (root / "workouts" / "legacy-wrong.zwo").exists()
    published = (root / "workouts" / f"{stem}.zwo").read_text()
    assert "FTP Field Test" in published and 'Power="0.95"' in published

    monkeypatch.setattr(plan_ir, "ATHLETES_DIR", athletes)
    ir = build_plan_ir(case["id"])
    projected = ir.weeks[0].sessions[0]
    assert projected.title == session["title"]
    assert projected.segments[1].target == session["segments"][1]["target"]
    tp = project_tp_manifest(ir)
    tp_session = tp["sessions"][0]
    assert tp_session["title"] == session["title"]
    assert tp_session["structure"]["primaryIntensityMetric"] == "percentOfFtp"
    assert tp_session["structure"]["polyline"]

    preview = build_preview_data(root)
    preview_session = next(
        day["workout"] for week in preview["weeks"] for day in week["days"]
        if day.get("workout")
    )
    assert preview_session["target_summary"] == session["target_summary"]

    contract = build_contract(
        ir.to_dict(), order_id="canonical-upstream-order",
        tp_athlete_id="tp-fixture", generation_revision=1,
        canonical_model=model, review_items=[], guide_sources={},
        athlete_dir=root,
    )
    workout = next(
        operation for operation in contract["operations"]
        if operation["kind"] == "workout_upsert")
    assert workout["payload"]["title"] == session["title"]
    assert workout["payload"]["structure"] == tp_session["structure"]


def test_guide_control_projection_comes_from_canonical_input(tmp_path):
    case = deepcopy(CASES[0])
    athletes, root, plan_dates = _write_fixture(tmp_path, case)
    authored = root / "workouts" / "W01_Fri_Aug14_FTP_TEST.zwo"
    stem, document = authored.stem, authored.read_text()
    authored.unlink()
    model = build_canonical_model(
        case["id"], root, plan_dates=plan_dates,
        authored_documents={stem: document}, naming_manifest={stem: {}},
    )
    template = (
        "<html><body><h1>Legacy FTP Test</h1>"
        "<p>Ride 20 min at 95% FTP and record 250 watts.</p></body></html>"
    )
    guide = project_guide_html(template, model)
    assert "LTHR Field Test" in guide
    assert model["athlete"]["reanchor"]["action"] in guide
    assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:W|watts?)\b", guide, re.I)
    assert not re.search(r"\b\d+(?:\.\d+)?\s*%\s*FTP\b", guide, re.I)


@pytest.mark.parametrize('target,kind', [
    ({'type': 'power_pct_ftp'}, 'steady_state'),
    ({'type': 'power_pct_ftp', 'value': .7, 'low': .6}, 'steady_state'),
    ({'type': 'free', 'value': .7}, 'free_ride'),
    ({'type': 'pct_lthr', 'low': .68, 'high': .83}, 'intervals'),
    ({'type': 'rpe', 'on': 11, 'off': 4}, 'intervals'),
])
def test_target_union_rejects_missing_mixed_forbidden_shapes(target, kind):
    model = {
        'model_version': MODEL_VERSION,
        'athlete': {'control_metric': 'power', 'power_basis': 'measured',
                    'ftp_watts': 250},
        'sessions': [{'segments': [{'kind': kind, 'target': target}]}],
    }
    with pytest.raises(CanonicalModelError):
        validate_canonical_model(model)


@pytest.mark.parametrize('athlete,segments', [
    ({'control_metric': 'rpe', 'control_basis': 'rpe', 'power_basis': 'none',
      'ftp_watts': None}, [
        {'kind': 'steady_state', 'target': {'type': 'rpe', 'value': 4}},
        {'kind': 'intervals', 'target': {'type': 'rpe', 'on': 9, 'off': 4}},
        {'kind': 'free_ride', 'target': {'type': 'free'}},
    ]),
    ({'control_metric': 'hr', 'control_basis': 'lthr', 'power_basis': 'none',
      'ftp_watts': None}, [
        {'kind': 'ramp', 'target': {'type': 'pct_lthr',
                                   'low': .68, 'high': .83}},
    ]),
    ({'control_metric': 'hr', 'control_basis': 'hrmax', 'power_basis': 'none',
      'ftp_watts': None}, [
        {'kind': 'intervals', 'target': {'type': 'pct_hrmax',
                                         'on': .92, 'off': .60}},
    ]),
])
def test_exact_target_union_accepts_each_branch(athlete, segments):
    validate_canonical_model({
        'model_version': MODEL_VERSION, 'athlete': athlete,
        'sessions': [{
            'id': 'w01.2026-01-05.01', 'week': 1,
            'date': '2026-01-05', 'daily_ordinal': 1,
            'segments': segments,
        }],
    })
