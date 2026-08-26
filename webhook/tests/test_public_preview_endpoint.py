import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module


def _valid_request():
    return {
        "schema_version": "training-plan-preview-request/v1",
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
            "preferred_days": ["tue", "thu", "sat", "sun"],
            "experience_level": "intermediate",
        },
    }


def test_preview_endpoint_fails_closed_until_final_provider_enabled(monkeypatch):
    monkeypatch.setattr(app_module, "PUBLIC_PLAN_PREVIEW_ENABLED", False)
    response = app_module.app.test_client().post(
        "/api/training-plan-preview", json={})
    assert response.status_code == 503
    assert response.get_json()["error"] == "preview_unavailable"


def test_preview_endpoint_sets_cache_and_cors_headers(monkeypatch):
    monkeypatch.setattr(app_module, "PUBLIC_PLAN_PREVIEW_ENABLED", True)
    monkeypatch.setattr(
        app_module, "build_public_preview",
        lambda *_args, **_kwargs: ({
            "schema_version": "training-plan-preview/v1",
            "engine_version": "engine-test",
            "voice_version": "voice-test",
            "week": {"days": []},
        }, False),
    )
    response = app_module.app.test_client().post(
        "/api/training-plan-preview",
        headers={"Origin": "https://gravelgodcycling.com"},
        json={"schema_version": "training-plan-preview-request/v1"},
    )
    assert response.status_code == 200
    assert response.headers["X-Preview-Cache"] == "MISS"
    assert "s-maxage=900" in response.headers["Cache-Control"]
    assert response.headers["Access-Control-Allow-Origin"] == (
        "https://gravelgodcycling.com")
    assert response.headers["Vary"] == "Origin"


def test_preview_endpoint_rejects_large_body_before_provider(monkeypatch):
    monkeypatch.setattr(app_module, "PUBLIC_PLAN_PREVIEW_ENABLED", True)
    response = app_module.app.test_client().post(
        "/api/training-plan-preview",
        data=b"x" * (app_module.PUBLIC_PLAN_PREVIEW_MAX_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_preview_endpoint_runs_real_motoren_provider(monkeypatch):
    monkeypatch.setattr(app_module, "PUBLIC_PLAN_PREVIEW_ENABLED", True)
    response = app_module.app.test_client().post(
        "/api/training-plan-preview",
        headers={"Origin": "https://gravelgodcycling.com"},
        json=_valid_request(),
    )
    assert response.status_code == 200
    payload = response.get_json()
    sessions = [
        session for day in payload["week"]["days"]
        for session in day["sessions"]
    ]
    assert payload["engine_version"].startswith("motoren/")
    assert payload["voice_version"].startswith("voice/")
    assert any(session["kind"] == "strength" for session in sessions)
