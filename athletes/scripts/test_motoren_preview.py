import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "tests" / "fixtures"))

import pytest

from motoren_preview import (
    ENGINE_VERSION,
    MotorenPreviewError,
    _git_short_sha,
    engine_version,
    generate_preview_source,
    voice_version,
)

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "motoren_preview_fixture.json"


def _request(**overrides):
    base = {
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
    for key, value in overrides.items():
        base[key] = value
    return base


def _normalized(payload):
    """Match preview_contract.normalize_request's output shape (sorted
    demands, sorted/deduped preferred_days) without importing the vendored
    copy at module scope -- generate_preview_source only depends on the
    normalized shape, not on preview_contract itself."""
    return {
        "schema_version": payload["schema_version"],
        "brand": payload["brand"],
        "race": {
            "slug": payload["race"]["slug"],
            "name": payload["race"]["name"],
            "discipline": payload["race"]["discipline"],
            "demands": dict(sorted(payload["race"]["demands"].items())),
        },
        "rider": {
            "hours_per_week": payload["rider"]["hours_per_week"],
            "preferred_days": sorted(
                set(payload["rider"]["preferred_days"]),
                key=("mon", "tue", "wed", "thu", "fri", "sat", "sun").index,
            ),
            "experience_level": payload["rider"]["experience_level"],
        },
        **({"preset_id": payload["preset_id"]} if payload.get("preset_id") else {}),
    }


DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _active_sessions(source):
    return [
        session
        for day in source["week"]["days"]
        for session in day["sessions"]
    ]


class TestDeterminism:
    def test_engine_version_uses_railway_revision_without_git(self, monkeypatch):
        monkeypatch.setenv(
            "RAILWAY_GIT_COMMIT_SHA",
            "abcdef1234567890abcdef1234567890abcdef12",
        )
        assert _git_short_sha() == "abcdef1"

    def test_two_calls_are_byte_identical(self):
        request = _normalized(_request())
        first = generate_preview_source(request)
        second = generate_preview_source(request)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    def test_different_requests_can_diverge(self):
        a = generate_preview_source(_normalized(_request()))
        b = generate_preview_source(_normalized(_request(
            rider={"hours_per_week": 14, "preferred_days": ["mon", "wed", "fri", "sun"],
                   "experience_level": "advanced"})))
        assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


class TestPreferredDaysHonored:
    def test_sessions_only_on_preferred_days(self):
        request = _normalized(_request())
        source = generate_preview_source(request)
        preferred = set(request["rider"]["preferred_days"])
        for day in source["week"]["days"]:
            if day["sessions"]:
                assert day["day"] in preferred

    def test_seven_days_in_calendar_order(self):
        source = generate_preview_source(_normalized(_request()))
        days = [d["day"] for d in source["week"]["days"]]
        assert days == list(DAY_KEYS)


class TestHoursCredible:
    @pytest.mark.parametrize("hours", [4, 6, 8, 12, 18])
    def test_target_minutes_within_tolerance_of_request_hours(self, hours):
        request = _normalized(_request(rider={
            "hours_per_week": hours,
            "preferred_days": ["mon", "wed", "fri", "sun"],
            "experience_level": "intermediate",
        }))
        source = generate_preview_source(request)
        available = hours * 60
        target = source["week"]["target_minutes"]
        assert int(available * 0.6) <= target <= available + 15

    def test_target_minutes_matches_sum_of_session_durations(self):
        request = _normalized(_request())
        source = generate_preview_source(request)
        total = sum(s["duration_minutes"] for s in _active_sessions(source))
        assert abs(total - source["week"]["target_minutes"]) <= 15


class TestStrengthCompleteness:
    def test_at_least_one_complete_strength_session(self):
        source = generate_preview_source(_normalized(_request()))
        strength_sessions = [
            s for s in _active_sessions(source) if s["kind"] == "strength"]
        assert strength_sessions
        for session in strength_sessions:
            assert session["strength"]["focus"]
            exercises = session["strength"]["exercises"]
            assert 3 <= len(exercises) <= 12
            for exercise in exercises:
                assert exercise["name"]
                assert 1 <= exercise["sets"] <= 12
                assert exercise["reps"]
                assert exercise["cue"]
                if "rest_seconds" in exercise:
                    assert 0 <= exercise["rest_seconds"] <= 600


class TestNotesPresence:
    def test_self_review_and_protocol_verbatim(self):
        from story_notes import SELF_REVIEW_BODY, COMMENT_PROTOCOL_BODY
        source = generate_preview_source(_normalized(_request()))
        week = source["week"]
        assert week["weekly_self_review"] == SELF_REVIEW_BODY
        assert week["comment_protocol"] == COMMENT_PROTOCOL_BODY

    def test_week_coach_note_present_and_bounded(self):
        source = generate_preview_source(_normalized(_request()))
        note = source["week"]["coach_note"]
        assert note
        assert len(note) <= 700

    def test_every_active_session_has_a_coach_note(self):
        source = generate_preview_source(_normalized(_request()))
        for session in _active_sessions(source):
            assert session["coach_note"]


class TestDisciplineSessionQuality:
    def test_bike_sessions_have_structure_purpose_and_fueling(self):
        source = generate_preview_source(_normalized(_request()))
        bike_sessions = [s for s in _active_sessions(source) if s["kind"] == "bike"]
        assert len(bike_sessions) >= 2
        for session in bike_sessions:
            assert session["purpose"]
            assert session["fueling_guidance"]
            structure = session["structure"]
            assert structure["steps"]
            assert structure["polyline"]

    def test_titles_are_distinct(self):
        source = generate_preview_source(_normalized(_request()))
        titles = [s["title"].casefold() for s in _active_sessions(source)]
        assert len(titles) == len(set(titles))


class TestPolylineNormalized:
    def test_polyline_points_within_bounds(self):
        source = generate_preview_source(_normalized(_request()))
        for session in _active_sessions(source):
            structure = session.get("structure")
            if not structure:
                continue
            for x, y in structure["polyline"]:
                assert 0 <= x <= 1
                assert 0 <= y <= 2

    def test_steps_carry_sane_intensity_targets(self):
        source = generate_preview_source(_normalized(_request()))
        for session in _active_sessions(source):
            structure = session.get("structure")
            if not structure:
                continue
            for step in structure["steps"]:
                assert step["length_seconds"] >= 1
                for key in ("intensity_target_min", "intensity_target_max"):
                    if key in step:
                        assert 0 <= step[key] <= 2
                if "cadence_rpm" in step:
                    assert 30 <= step["cadence_rpm"] <= 200


class TestLeakCheckClean:
    def test_no_internal_tokens_in_serialized_output(self):
        source = generate_preview_source(_normalized(_request()))
        wire = json.dumps(source)
        for forbidden in (".py", "/athletes/", "plan_ir", "PlanIR",
                          "library_item_id", "source_file", "compliance"):
            assert forbidden.lower() not in wire.lower()


class TestVersions:
    def test_engine_version_shape(self):
        assert engine_version() == ENGINE_VERSION
        assert engine_version().startswith("motoren/")
        assert "+ae-2026-08-23" in engine_version()

    def test_voice_version_shape(self):
        assert voice_version().startswith("voice/")
        assert len(voice_version()) == len("voice/") + 8


class TestErrorHandling:
    def test_raises_motoren_preview_error_on_malformed_request(self):
        with pytest.raises(MotorenPreviewError):
            generate_preview_source({"rider": {}, "race": {}})

    def test_raises_motoren_preview_error_not_a_bare_exception(self):
        with pytest.raises(MotorenPreviewError):
            generate_preview_source({})


class TestFixture:
    def test_fixture_matches_current_generator_output(self):
        """The checked-in fixture is generate_preview_source() of the
        contract doc's example request. If this fails after an intentional
        engine/voice change, regenerate the fixture file."""
        assert _FIXTURE_PATH.exists()
        fixture = json.loads(_FIXTURE_PATH.read_text())
        regenerated = generate_preview_source(_normalized(_request()))
        assert fixture == regenerated


class TestIntegrationWithRealContract:
    """Copies the codex branch's preview_contract.py (vendored at
    tests/fixtures/codex_preview_contract.py, provenance comment inside) and
    asserts their build_public_preview()/project_response() accept this
    module's source and pass the real fail-closed quality gate."""

    def test_build_public_preview_accepts_our_source(self):
        from codex_preview_contract import project_response

        request = _request()
        source = generate_preview_source(_normalized(request))
        response = project_response(
            request, source, engine_version=engine_version(),
            voice_version="github-voice-test123")
        assert response["schema_version"] == "training-plan-preview/v1"
        assert response["engine_version"] == engine_version()
        assert response["week"]["days"][1]["sessions"] or any(
            day["sessions"] for day in response["week"]["days"])

    @pytest.mark.parametrize("hours,days,experience", [
        (4, ["mon", "wed", "fri"], "beginner"),
        (8, ["tue", "thu", "sat", "sun"], "intermediate"),
        (12, ["mon", "tue", "thu", "fri", "sat"], "advanced"),
        (18, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "advanced"),
    ])
    def test_contract_quality_gate_passes_across_request_shapes(
            self, hours, days, experience):
        from codex_preview_contract import project_response

        request = _request(rider={
            "hours_per_week": hours, "preferred_days": days,
            "experience_level": experience,
        })
        source = generate_preview_source(_normalized(request))
        response = project_response(
            request, source, engine_version=engine_version(),
            voice_version="github-voice-test123")
        assert response["week"]["target_minutes"] > 0

    def test_contract_quality_gate_passes_for_disciplines_and_demand_gaps(self):
        from codex_preview_contract import project_response

        for discipline, demands in (
            ("road", {"climbing": 9, "durability": 4}),
            ("mtb", {"technical": 10, "vo2_power": 7}),
            # A demand vector with NO keys the engine recognizes must still
            # degrade gracefully to a passing preview.
            ("gravel", {"unmapped_demand_xyz": 5}),
        ):
            request = _request(race={
                "slug": "test-race", "name": "Test Race",
                "discipline": discipline, "demands": demands,
            })
            source = generate_preview_source(_normalized(request))
            response = project_response(
                request, source, engine_version=engine_version(),
                voice_version="github-voice-test123")
            assert response["race"]["discipline"] == discipline
