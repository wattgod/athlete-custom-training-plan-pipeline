import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from preview_contract import (
    REQUEST_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION_V2,
    RESPONSE_SCHEMA_VERSION,
    RESPONSE_SCHEMA_VERSION_V2,
    PreviewContractError,
    normalize_request,
    project_response,
    request_cache_key,
    resolve_voice_version,
)


def request_payload():
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "brand": "gravel_god",
        "preset_id": "committed-8",
        "race": {
            "slug": "unbound-200",
            "name": "Unbound Gravel 200",
            "discipline": "gravel",
            "demands": {"durability": 10, "heat": 8, "vo2_power": 6},
        },
        "rider": {
            "hours_per_week": 8,
            "preferred_days": ["sun", "tue", "thu", "sat"],
            "experience_level": "intermediate",
        },
    }


def request_payload_v2():
    payload = request_payload()
    payload.update({
        "schema_version": REQUEST_SCHEMA_VERSION_V2,
        "plan_weeks": 21,
    })
    payload["race"].update({
        "date": "2027-06-05",
        "expected_duration_hours": 12,
    })
    payload["rider"].update({
        "goal_type": "compete",
        "control_method": "power",
        "ftp_watts": 250,
        "strength_equipment": "full-gym",
        "day_caps_minutes": {"tue": 75, "thu": 90, "sat": 300},
    })
    return payload


def source_plan_v2():
    sys.path.insert(0, str(Path(__file__).parents[2] / "athletes" / "scripts"))
    from motoren_preview import generate_preview_source
    return generate_preview_source(normalize_request(request_payload_v2()))


def source_week():
    days = [{"day": day, "sessions": []} for day in
            ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]
    days[1]["sessions"] = [{
        "kind": "bike",
        "title": "3 x 12 min Flint Hills over-unders",
        "purpose": "Build the repeatable torque and pace control the Flint Hills demand late in the race.",
        "duration_minutes": 75,
        "tss": 82,
        "intensity_label": "Threshold",
        "fuel_tag": "high",
        "fueling_guidance": "Start fed. Take 30–45 g carbohydrate during the ride.",
        "coach_note": "DO the first rep under control. The last four minutes are the work.",
        "structure": {
            "primary_length_metric": "duration",
            "primary_intensity_metric": "percentOfFtp",
            "polyline": [[0, 0], [0.1, 0.55], [0.4, 0.95], [0.7, 0.88], [1, 0]],
            "steps": [
                {"type": "warmup", "length_seconds": 900,
                 "label": "Progressive gravel warm-up",
                 "intensity_target_min": 0.5, "intensity_target_max": 0.7},
                {"type": "interval", "length_seconds": 720,
                 "label": "Flint Hills over-under",
                 "intensity_target_min": 0.88, "intensity_target_max": 0.98,
                 "cadence_rpm": 88},
            ],
        },
        "library_item_id": "must-never-escape",
        "source_file": "/private/workouts/foo.zwo",
    }]
    days[3]["sessions"] = [{
        "kind": "strength",
        "title": "Gravel durability — hinge, split stance, trunk",
        "purpose": "Keep force production and posture intact when washboard and climbing fatigue start stacking up.",
        "duration_minutes": 45,
        "tss": 38,
        "intensity_label": "Strength",
        "fuel_tag": "moderate",
        "fueling_guidance": "Arrive normally fed; take 25–30 g protein with carbohydrate after the session.",
        "coach_note": "Leave two clean reps in reserve. The goal is durable force, not soreness.",
        "strength": {
            "focus": "Posterior chain, unilateral force, and anti-rotation",
            "exercises": [
                {"name": "Trap-bar deadlift", "sets": 4, "reps": "5", "rest_seconds": 150, "cue": "Push the floor away; stop before position changes."},
                {"name": "Rear-foot elevated split squat", "sets": 3, "reps": "6/side", "rest_seconds": 90, "cue": "Own the bottom and drive through the whole foot."},
                {"name": "Single-leg calf raise", "sets": 3, "reps": "10/side", "rest_seconds": 60, "cue": "Pause at full height; lower under control."},
                {"name": "Half-kneeling Pallof press", "sets": 3, "reps": "8/side", "rest_seconds": 45, "cue": "Ribs down; do not let the cable rotate you."},
            ],
        },
    }]
    days[5]["sessions"] = [{
        "kind": "bike",
        "title": "Long ride — late-race pressure",
        "purpose": "Turn race fueling and steady gravel power into something you can still execute after three hours.",
        "duration_minutes": 240,
        "tss": 210,
        "intensity_label": "Endurance",
        "fuel_tag": "practice",
        "fueling_guidance": "Practice 80–90 g carbohydrate per hour.",
        "coach_note": "Keep the first three hours boring. Finish on race posture.",
        "structure": {
            "primary_length_metric": "duration",
            "primary_intensity_metric": "percentOfFtp",
            "polyline": [[0, 0.55], [0.72, 0.65], [0.85, 0.8], [0.95, 0.88], [1, 0.5]],
            "steps": [
                {"type": "endurance", "label": "Steady gravel endurance", "length_seconds": 10800, "intensity_target_min": 0.58, "intensity_target_max": 0.72},
                {"type": "tempo", "label": "Late-race pressure", "length_seconds": 2700, "intensity_target_min": 0.78, "intensity_target_max": 0.88},
                {"type": "cooldown", "label": "Easy spin home", "length_seconds": 900, "intensity_target_min": 0.45, "intensity_target_max": 0.58},
            ],
        },
    }]
    return {
        "week": {
            "phase": "build",
            "type": "load",
            "target_minutes": 360,
            "target_tss": 330,
            "coach_note": "The long ride is the anchor. Tuesday teaches you to change pace without wasting matches.",
            "weekly_self_review": "What moved forward? What felt stuck? What needs changing next week?",
            "comment_protocol": "After each key workout, tell me the result, how the legs felt, and anything that changed the session.",
            "days": days,
            "compliance": {"private": True},
        },
        "source_file": "/private/plan.json",
    }


def test_request_normalizes_day_order_and_cache_key_is_stable():
    payload = request_payload()
    normalized = normalize_request(payload)
    assert normalized["rider"]["preferred_days"] == ["tue", "thu", "sat", "sun"]
    reordered = copy.deepcopy(payload)
    reordered["race"]["demands"] = {
        "vo2_power": 6, "durability": 10, "heat": 8}
    assert request_cache_key(payload) == request_cache_key(reordered)


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(schema_version="v0"),
    lambda p: p["rider"].update(hours_per_week=3),
    lambda p: p["rider"].update(preferred_days=["tue", "sat"]),
    lambda p: p["race"].update(slug="../unbound"),
    lambda p: p["race"].update(demands={"durability": 11}),
])
def test_bad_requests_fail_closed(mutation):
    payload = request_payload()
    mutation(payload)
    with pytest.raises(PreviewContractError):
        normalize_request(payload)


def test_response_is_versioned_and_private_fields_are_not_projected():
    response = project_response(
        request_payload(), source_week(), engine_version="e785ccb",
        voice_version="github-voice-test123")
    assert response["schema_version"] == RESPONSE_SCHEMA_VERSION
    assert response["engine_version"] == "e785ccb"
    assert response["voice_version"] == "github-voice-test123"
    assert response["week"]["days"][1]["sessions"][0]["structure"]["polyline"]
    assert response["week"]["weekly_self_review"].startswith("What moved")
    assert "library_item_id" not in repr(response)
    assert "source_file" not in repr(response)
    assert "compliance" not in repr(response)


def test_internal_tokens_in_visible_copy_fail_closed():
    source = source_week()
    source["week"]["days"][1]["sessions"][0]["coach_note"] = (
        "Use library_item_id 778")
    with pytest.raises(PreviewContractError, match="internal token"):
        project_response(
            request_payload(), source, engine_version="e785ccb",
            voice_version="github-voice-test123")


@pytest.mark.parametrize("mutation,match", [
    (lambda source: source["week"]["days"][3].update(sessions=[]),
     "complete strength session"),
    (lambda source: source["week"]["days"][5]["sessions"][0].update(
        purpose=""), "purpose is required"),
    (lambda source: source["week"]["days"][5]["sessions"][0].pop(
        "structure"), "structured steps and a polyline"),
    (lambda source: source["week"]["days"][5]["sessions"][0].update(
        title="3 x 12 min Flint Hills over-unders"),
     "titles must be distinct"),
])
def test_thin_or_generic_preview_weeks_fail_closed(mutation, match):
    source = source_week()
    mutation(source)
    with pytest.raises(PreviewContractError, match=match):
        project_response(
            request_payload(), source, engine_version="e785ccb",
            voice_version="github-voice-test123")


def test_strength_and_workout_purpose_are_public_first_class_fields():
    response = project_response(
        request_payload(), source_week(), engine_version="e785ccb",
        voice_version="github-voice-test123")
    tuesday = response["week"]["days"][1]["sessions"][0]
    thursday = response["week"]["days"][3]["sessions"][0]
    assert "Flint Hills" in tuesday["purpose"]
    assert tuesday["structure"]["steps"][0]["label"] == (
        "Progressive gravel warm-up")
    assert thursday["kind"] == "strength"
    assert len(thursday["strength"]["exercises"]) == 4
    assert thursday["strength"]["exercises"][0]["sets"] == 4


def test_voice_version_tracks_checked_in_contract_sources():
    value = resolve_voice_version()
    assert value.startswith("github-voice-")
    assert len(value) == len("github-voice-") + 12


def test_v2_request_normalizes_personalization_and_caps():
    normalized = normalize_request(request_payload_v2())
    assert normalized["schema_version"] == REQUEST_SCHEMA_VERSION_V2
    assert normalized["race"]["date"] == "2027-06-05"
    assert normalized["rider"]["control_method"] == "power"
    assert normalized["rider"]["day_caps_minutes"] == {
        "tue": 75, "thu": 90, "sat": 300}


def test_v2_road_event_format_is_allowlisted_echoed_and_cache_significant():
    payload = request_payload_v2()
    payload["brand"] = "roadie_labs"
    payload["race"].update({
        "slug": "downtown-crit",
        "name": "Downtown Criterium",
        "discipline": "road",
        "event_format": "criterium",
    })
    normalized = normalize_request(payload)
    assert normalized["race"]["event_format"] == "criterium"
    without_format = copy.deepcopy(payload)
    without_format["race"].pop("event_format")
    assert request_cache_key(payload) != request_cache_key(without_format)

    sys.path.insert(
        0, str(Path(__file__).parents[2] / "athletes" / "scripts"))
    from motoren_preview import generate_preview_source
    response = project_response(
        payload, generate_preview_source(normalized),
        engine_version="motoren/test", voice_version="voice/test")
    assert response["race"]["event_format"] == "criterium"
    assert response["plan"]["profile_version"] == "road/v1"


@pytest.mark.parametrize("event_format", [
    "generic_road", "criterium", "hill_climb", "time_trial",
    "stage_race", "fondo",
])
def test_v2_accepts_every_canonical_road_event_format(event_format):
    payload = request_payload_v2()
    payload["brand"] = "roadie_labs"
    payload["race"].update({
        "discipline": "road", "event_format": event_format})
    assert normalize_request(payload)["race"]["event_format"] == event_format


def test_v2_road_event_format_rejects_invalid_and_non_road_values():
    invalid = request_payload_v2()
    invalid["race"].update({
        "discipline": "road", "event_format": "cobble_classic"})
    with pytest.raises(PreviewContractError, match="not supported"):
        normalize_request(invalid)

    non_road = request_payload_v2()
    non_road["race"]["event_format"] = "criterium"
    with pytest.raises(PreviewContractError, match="only valid for road"):
        normalize_request(non_road)


def test_v2_road_projection_rejects_missing_or_stale_profile_version():
    payload = request_payload_v2()
    payload["brand"] = "roadie_labs"
    payload["race"].update({
        "discipline": "road", "event_format": "fondo"})
    source = source_plan_v2()
    with pytest.raises(PreviewContractError, match="profile version"):
        project_response(
            payload, source, engine_version="motoren/test",
            voice_version="voice/test")
    source["plan"]["profile_version"] = "road/v0"
    with pytest.raises(PreviewContractError, match="profile version"):
        project_response(
            payload, source, engine_version="motoren/test",
            voice_version="voice/test")


@pytest.mark.parametrize("mutation,match", [
    (lambda payload: payload["race"].update(date="next summer"), "ISO date"),
    (lambda payload: payload["rider"].update(control_method="pace"), "not supported"),
    (lambda payload: payload["rider"].pop("ftp_watts"), "must be a number"),
    (lambda payload: payload["rider"].update(day_caps_minutes={"mon": 60}), "preferred days"),
])
def test_bad_v2_personalization_fails_closed(mutation, match):
    payload = request_payload_v2()
    mutation(payload)
    with pytest.raises(PreviewContractError, match=match):
        normalize_request(payload)


def test_v2_projects_one_linked_plan_for_calendar_and_volume():
    source = source_plan_v2()
    response = project_response(
        request_payload_v2(), source, engine_version="motoren/test",
        voice_version="voice/test")
    assert response["schema_version"] == RESPONSE_SCHEMA_VERSION_V2
    assert len(response["planned_volume"]) == 21
    assert response["plan"]["sample_week_numbers"] == [
        week["week_number"] for week in response["sample_weeks"]]
    volume = {week["week_number"]: week for week in response["planned_volume"]}
    for sample in response["sample_weeks"]:
        summary = volume[sample["week_number"]]
        assert sample["phase"] == summary["phase"]
        assert sample["type"] == summary["type"]
        assert sample["target_minutes"] == summary["target_minutes"]
        assert sample["target_tss"] == summary["target_tss"]
        assert sample["start_date"] == sample["days"][0]["date"]
        assert sample["end_date"] == sample["days"][-1]["date"]
    assert "_library_backed" not in repr(response)
    assert "_engine_overlay" not in repr(response)


def test_v2_requested_volume_bar_returns_that_exact_calendar_week():
    payload = request_payload_v2()
    payload["sample_week_number"] = 9
    normalized = normalize_request(payload)
    sys.path.insert(0, str(Path(__file__).parents[2] / "athletes" / "scripts"))
    from motoren_preview import generate_preview_source
    response = project_response(
        payload, generate_preview_source(normalized),
        engine_version="motoren/test", voice_version="voice/test")
    sample = next(week for week in response["sample_weeks"] if week["week_number"] == 9)
    volume = response["planned_volume"][8]
    assert sample["target_minutes"] == volume["target_minutes"]
    assert sample["target_tss"] == volume["target_tss"]
    assert sample["start_date"] == volume["start_date"]


def test_v2_race_load_is_real_and_included_in_volume_curve():
    response = project_response(
        request_payload_v2(), source_plan_v2(), engine_version="motoren/test",
        voice_version="voice/test")
    race_week = next(week for week in response["sample_weeks"] if week["type"] == "race")
    race_session = next(
        session for day in race_week["days"] for session in day["sessions"]
        if session["kind"] == "race")
    assert race_session["duration_minutes"] == 720
    assert race_session["tss"] > 0
    assert "structure" not in race_session
    summary = response["planned_volume"][race_week["week_number"] - 1]
    assert summary["target_minutes"] >= race_session["duration_minutes"]
    assert summary["target_tss"] >= race_session["tss"]


def test_v2_rejects_unproven_workout_provenance():
    source = source_plan_v2()
    session = next(
        session for week in source["sample_weeks"] for day in week["days"]
        for session in day["sessions"] if session["kind"] == "bike")
    session.pop("_library_backed")
    with pytest.raises(PreviewContractError, match="coach workout library"):
        project_response(
            request_payload_v2(), source, engine_version="motoren/test",
            voice_version="voice/test")
