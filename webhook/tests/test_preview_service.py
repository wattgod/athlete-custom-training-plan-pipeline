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
    days[5]["sessions"] = [{
        "kind": "bike", "title": f"{hours}h climbing-week long ride",
        "duration_minutes": hours * 30, "tss": hours * 20,
        "intensity_label": "Endurance", "fuel_tag": "practice",
        "fueling_guidance": "Practice the race fueling target.",
        "coach_note": "Keep the opening climbs controlled.",
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
