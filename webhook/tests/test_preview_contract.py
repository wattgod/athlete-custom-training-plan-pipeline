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
                 "intensity_target_min": 0.5, "intensity_target_max": 0.7},
                {"type": "interval", "length_seconds": 720,
                 "intensity_target_min": 0.88, "intensity_target_max": 0.98,
                 "cadence_rpm": 88},
            ],
        },
        "library_item_id": "must-never-escape",
        "source_file": "/private/workouts/foo.zwo",
    }]
    days[5]["sessions"] = [{
        "kind": "bike",
        "title": "Long ride — late-race pressure",
        "duration_minutes": 240,
        "tss": 210,
        "intensity_label": "Endurance",
        "fuel_tag": "practice",
        "fueling_guidance": "Practice 80–90 g carbohydrate per hour.",
        "coach_note": "Keep the first three hours boring. Finish on race posture.",
    }]
    return {
        "week": {
            "phase": "build",
            "type": "load",
            "target_minutes": 480,
            "target_tss": 420,
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


def test_voice_version_tracks_checked_in_contract_sources():
    value = resolve_voice_version()
    assert value.startswith("github-voice-")
    assert len(value) == len("github-voice-") + 12
