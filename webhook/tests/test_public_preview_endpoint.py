import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module


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
