import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine_preview_provider import (
    engine_version,
    generate_preview_source,
    voice_version,
)
from preview_service import (
    PreviewCache,
    PreviewProviderUnavailable,
    build_public_preview,
)


def _request():
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


def _request_v2(brand="gravel_god", discipline="gravel"):
    request = _request()
    request.update({
        "schema_version": "training-plan-preview-request/v2",
        "brand": brand,
        "plan_weeks": 21,
    })
    request["race"].update({
        "discipline": discipline,
        "date": "2027-06-05",
        "expected_duration_hours": 12,
    })
    request["rider"].update({
        "goal_type": "compete",
        "control_method": "power",
        "ftp_watts": 250,
        "strength_equipment": "full-gym",
    })
    return request


def test_real_motoren_provider_passes_public_projection_end_to_end():
    response, cache_hit = build_public_preview(
        _request(), provider=generate_preview_source,
        engine_version=engine_version(), voice_version=voice_version(),
        cache=PreviewCache(),
    )
    sessions = [
        session for day in response["week"]["days"]
        for session in day["sessions"]
    ]
    assert not cache_hit
    assert response["engine_version"].startswith("motoren/")
    assert response["voice_version"].startswith("voice/")
    assert any(session["kind"] == "strength" for session in sessions)
    assert all(session["purpose"] for session in sessions)
    assert all(session["coach_note"] for session in sessions)
    assert all(
        session.get("structure", {}).get("polyline")
        for session in sessions if session["kind"] == "bike"
    )


def test_motoren_versions_are_public_contract_tokens():
    assert re.fullmatch(r"motoren/[A-Za-z0-9._+:-]+", engine_version())
    assert re.fullmatch(r"voice/[A-Za-z0-9._+:-]+", voice_version())


@pytest.mark.parametrize("brand,discipline", [
    ("gravel_god", "gravel"),
    ("roadie_labs", "road"),
])
def test_v2_motoren_plan_passes_projection_end_to_end(brand, discipline):
    response, cache_hit = build_public_preview(
        _request_v2(brand, discipline), provider=generate_preview_source,
        engine_version=engine_version(), voice_version=voice_version(),
        cache=PreviewCache(),
    )
    assert not cache_hit
    assert response["schema_version"] == "training-plan-preview/v2"
    assert len(response["planned_volume"]) == 21
    for sample in response["sample_weeks"]:
        volume = response["planned_volume"][sample["week_number"] - 1]
        assert sample["target_minutes"] == volume["target_minutes"]
        assert sample["target_tss"] == volume["target_tss"]


def test_motoren_failure_maps_to_generic_provider_unavailable():
    with pytest.raises(
            PreviewProviderUnavailable,
            match="could not generate a complete public preview"):
        generate_preview_source({})


def test_xc_ski_fails_closed_instead_of_returning_bike_workouts():
    request = _request()
    request["brand"] = "xc_ski_labs"
    request["race"].update({
        "slug": "birkebeinerrennet",
        "name": "Birkebeinerrennet",
        "discipline": "xc_ski",
    })
    with pytest.raises(
            PreviewProviderUnavailable,
            match="does not yet provide a native XC-ski preview"):
        generate_preview_source(request)
