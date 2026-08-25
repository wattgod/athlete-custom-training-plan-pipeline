import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from preview_contract import (
    REQUEST_SCHEMA_VERSION,
    RESPONSE_SCHEMA_VERSION,
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
