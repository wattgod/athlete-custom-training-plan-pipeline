import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from preview_contract import REQUEST_SCHEMA_VERSION
from preview_service import PreviewCache, build_public_preview


def _request(hours=8):
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "brand": "roadie_labs",
        "race": {
            "slug": "maratona-dles-dolomites",
            "name": "Maratona dles Dolomites",
            "discipline": "road",
            "demands": {"climbing": 10, "durability": 8},
        },
        "rider": {
            "hours_per_week": hours,
            "preferred_days": ["tue", "thu", "sat", "sun"],
            "experience_level": "intermediate",
        },
    }


def _source(hours=8):
    days = [{"day": day, "sessions": []} for day in
            ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]
    days[1]["sessions"] = [{
        "kind": "bike", "title": "Dolomites climbing torque",
        "purpose": "Build controlled climbing force for the race's repeated steep passes.",
        "duration_minutes": 90, "tss": 92,
        "intensity_label": "Sweet spot", "fuel_tag": "high",
        "fueling_guidance": "Start fed and take 30–45 g carbohydrate during the ride.",
        "coach_note": "Hold the first climb back; make the final repeat your cleanest.",
        "structure": {
            "primary_length_metric": "duration",
            "primary_intensity_metric": "percentOfFtp",
            "polyline": [[0, .5], [.2, .7], [.35, .9], [.55, .6], [.75, .9], [1, .5]],
            "steps": [
                {"type": "warmup", "label": "Progressive warm-up", "length_seconds": 1200, "intensity_target_min": .5, "intensity_target_max": .7},
                {"type": "interval", "label": "Climbing torque", "length_seconds": 900, "intensity_target_min": .86, "intensity_target_max": .94, "cadence_rpm": 70},
            ],
        },
    }]
    days[3]["sessions"] = [{
        "kind": "strength", "title": "Climbing strength — hinge and split stance",
        "purpose": "Build unilateral force and trunk control for long seated climbs.",
        "duration_minutes": 45, "tss": 35,
        "intensity_label": "Strength", "fuel_tag": "moderate",
        "fueling_guidance": "Eat normally before; pair protein and carbohydrate afterward.",
        "coach_note": "Move crisply and leave two reps in reserve.",
        "strength": {"focus": "Posterior chain and unilateral force", "exercises": [
            {"name": "Trap-bar deadlift", "sets": 4, "reps": "5", "rest_seconds": 150, "cue": "Push the floor away."},
            {"name": "Split squat", "sets": 3, "reps": "6/side", "rest_seconds": 90, "cue": "Keep the whole foot loaded."},
            {"name": "Calf raise", "sets": 3, "reps": "10/side", "rest_seconds": 60, "cue": "Pause at the top."},
        ]},
    }]
    days[5]["sessions"] = [{
        "kind": "bike", "title": f"{hours}h climbing-week long ride",
        "purpose": "Practice steady pass-to-pass pacing and fueling under accumulating fatigue.",
        "duration_minutes": hours * 60 - 135, "tss": hours * 20,
        "intensity_label": "Endurance", "fuel_tag": "practice",
        "fueling_guidance": "Practice the race fueling target.",
        "coach_note": "Keep the opening climbs controlled.",
        "structure": {
            "primary_length_metric": "duration",
            "primary_intensity_metric": "percentOfFtp",
            "polyline": [[0, .55], [.35, .7], [.5, .82], [.7, .64], [.9, .86], [1, .5]],
            "steps": [
                {"type": "endurance", "label": "Pass-to-pass endurance", "length_seconds": max(60, (hours * 60 - 150) * 60), "intensity_target_min": .58, "intensity_target_max": .74},
                {"type": "tempo", "label": "Final climb pressure", "length_seconds": 900, "intensity_target_min": .78, "intensity_target_max": .88},
            ],
        },
    }]
    return {"week": {
        "phase": "build", "type": "load", "target_minutes": hours * 60,
        "target_tss": hours * 50,
        "coach_note": "The long climb is the anchor.",
        "weekly_self_review": "What moved forward? What needs changing?",
        "comment_protocol": "Leave the result and how the legs felt.",
        "days": days,
    }}


def test_cache_reuses_identical_versioned_request():
    calls = []
    cache = PreviewCache()

    def provider(request):
        calls.append(copy.deepcopy(request))
        return _source(request["rider"]["hours_per_week"])

    first, first_hit = build_public_preview(
        _request(), provider=provider, engine_version="engine-a",
        voice_version="voice-a", cache=cache)
    second, second_hit = build_public_preview(
        _request(), provider=provider, engine_version="engine-a",
        voice_version="voice-a", cache=cache)
    assert not first_hit
    assert second_hit
    assert first == second
    assert len(calls) == 1


def test_engine_or_voice_change_invalidates_cache():
    calls = []
    cache = PreviewCache()

    def provider(request):
        calls.append(1)
        return _source(request["rider"]["hours_per_week"])

    for engine, voice in (("engine-a", "voice-a"),
                          ("engine-b", "voice-a"),
                          ("engine-b", "voice-b")):
        _response, cache_hit = build_public_preview(
            _request(), provider=provider, engine_version=engine,
            voice_version=voice, cache=cache)
        assert not cache_hit
    assert len(calls) == 3


def test_expiry_and_lru_bound_are_enforced():
    now = [0.0]
    cache = PreviewCache(ttl_seconds=10, max_entries=1, clock=lambda: now[0])
    cache.put("a", {"value": 1})
    assert cache.get("a") == {"value": 1}
    cache.put("b", {"value": 2})
    assert cache.get("a") is None
    now[0] = 11
    assert cache.get("b") is None
