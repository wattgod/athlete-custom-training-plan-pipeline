"""Dedicated E1 fixtures for identity, scoring, certification, and Q0 rails."""

from __future__ import annotations

import copy
import builtins
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from archetype_identity import load_id_map, resolve_live
from archetype_registry import ALL_ARCHETYPES, get_archetype
from canonical_training_model import (CanonicalModelError, MODEL_VERSION,
                                      validate_canonical_model)
from earned_selection import prescribed_trace, score_design_dose, wbal_nadir_kj
from nate_workout_generator import (generate_blocks_from_archetype,
                                    select_archetype_for_workout)
import nate_workout_generator as nate
from workout_mapper import WORKOUT_MAP, _resolve_for_discipline
from workout_mapper import render_workout
from selection_migration_proof import (_selection, iter_reachable_selection_cases,
                                       projected_filename, selection_case_count)
import generate_athlete_package
import select_methodology


CONFIG = Path(__file__).resolve().parents[1] / "config"


def _steady(seconds: int, value: float, target_type: str = "power_pct_ftp"):
    return {"id": "seg-0001", "kind": "steady", "seconds": seconds,
            "target": {"type": target_type, "value": value}}


@pytest.mark.parametrize(("segment", "expected"), [
    ({"kind": "ramp", "seconds": 0,
      "target": {"type": "power_pct_ftp", "low": .4, "high": .8}}, []),
    ({"kind": "ramp", "seconds": 1,
      "target": {"type": "power_pct_ftp", "low": .4, "high": .8}}, [.4]),
    ({"kind": "ramp", "seconds": 3,
      "target": {"type": "power_pct_ftp", "low": .4, "high": .8}}, [.4, .6, .8]),
    ({"kind": "ramp", "seconds": 3,
      "target": {"type": "power_pct_ftp", "low": .8, "high": .4}}, [.8, .6, .4]),
    ({"kind": "steady", "seconds": 3,
      "target": {"type": "power_pct_ftp", "value": .7}}, [.7, .7, .7]),
])
def test_trace_goldens(segment, expected):
    result = prescribed_trace([segment])
    assert result["status"] == "OK"
    assert result["trace"] == pytest.approx(expected)


def test_interval_and_free_ride_trace_goldens():
    interval = {"kind": "intervals", "seconds": 6, "repeat": 2,
                "on_seconds": 2, "off_seconds": 1,
                "target": {"type": "power_pct_ftp", "on": 1.2, "off": .5}}
    result = prescribed_trace([interval])
    assert result["trace"] == [1.2, 1.2, .5, 1.2, 1.2, .5]

    mixed = score_design_dose([interval, {
        "kind": "free_ride", "seconds": 30, "target": {"type": "free"}}])
    assert mixed["status"] == "APPLICABLE"
    assert mixed["trace_seconds"] == 6 and mixed["free_seconds"] == 30
    assert mixed["has_free_segments"] is True

    pure = score_design_dose([{
        "kind": "free_ride", "seconds": 60, "target": {"type": "free"}}])
    assert pure == {
        "status": "NOT_APPLICABLE", "reason": "EMPTY_PRESCRIBED_TRACE",
        "trace_seconds": 0, "free_seconds": 60, "has_free_segments": True,
        "design_if": None, "design_tss": None, "design_kj": None,
        "t_at_vo2max_seconds": None, "wbal_nadir_kj": None,
    }

    broken = dict(interval, seconds=5)
    assert score_design_dose([broken])["status"] == "UNAVAILABLE"


@pytest.mark.parametrize(("name", "segments", "seconds", "design_if", "design_tss"), [
    ("40/20", [{"kind": "intervals", "seconds": 360, "repeat": 6,
                "on_seconds": 40, "off_seconds": 20,
                "target": {"type": "power_pct_ftp", "on": 1.2, "off": .5}}],
     360, 1.088384813081717, 11.845815013469243),
    ("30/30", [{"kind": "intervals", "seconds": 480, "repeat": 8,
                "on_seconds": 30, "off_seconds": 30,
                "target": {"type": "power_pct_ftp", "on": 1.15, "off": .5}}],
     480, .9755565749441555, 12.68947507889029),
    ("5x3", [{"kind": "intervals", "seconds": 1800, "repeat": 5,
              "on_seconds": 180, "off_seconds": 180,
              "target": {"type": "power_pct_ftp", "on": 1.1, "off": .55}}],
     1800, .9391120668457795, 44.09657370476759),
    ("threshold", [_steady(1200, .95)], 1200, .95, 30.08333333333333),
    ("endurance", [_steady(3600, .7)], 3600, .7, 49.0),
    ("recovery", [_steady(1800, .5)], 1800, .5, 12.5),
    ("rpe_pending_lthr", [_steady(600, 4, "rpe")], 600, .65, 7.041666666666667),
])
def test_known_workout_dose_goldens(name, segments, seconds, design_if, design_tss):
    result = score_design_dose(segments)
    assert result["status"] == "APPLICABLE", name
    assert result["trace_seconds"] == seconds
    assert result["design_if"] == pytest.approx(design_if)
    assert result["design_tss"] == pytest.approx(design_tss)


def test_assessment_and_empty_sentinel_goldens():
    # Assessment is an orthogonal contract flag; the truthful free effort has
    # no fabricated prescribed dose. An empty sentinel has the same exact
    # §1.2 zero-trace result.
    for segments in ([{"kind": "free_ride", "seconds": 1200,
                       "target": {"type": "free"}}], []):
        result = score_design_dose(segments)
        assert result["status"] == "NOT_APPLICABLE"
        assert result["design_tss"] is None
        assert result["has_free_segments"] is True


@pytest.mark.parametrize(("trace", "expected"), [
    ([1.0] * 60, 20.0),
    ([1.2] * 60, 17.625),
    ([1.2] * 60 + [.6] * 60, 17.625),
    ([1.2] * 600, -3.75),
])
def test_wbal_reference_goldens(trace, expected):
    assert wbal_nadir_kj(trace) == pytest.approx(expected, abs=1e-9)


def test_manifest_regenerates_byte_semantically_and_mode_a_is_complete():
    stored = json.loads((CONFIG / "workout_certification.json").read_text())
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "manifest.json"
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        subprocess.run([
            sys.executable, str(Path(__file__).with_name(
                "certify_workout_library.py")),
            "--generated-at", stored["generated_at"], "--output", str(output),
        ], check=True, env=env, capture_output=True, text=True)
        rebuilt = json.loads(output.read_text())
    assert rebuilt == stored
    assert len(rebuilt["rows"]) == 600
    assert {row["row_id"] for row in rebuilt["rows"]} == {
        row["row_id"] for row in json.loads(json.dumps(stored["rows"]))}
    assert all(row["gates"] for row in rebuilt["rows"])
    assert all(gate["effective_verdict"] == "NOT_ENFORCED"
               for row in rebuilt["rows"] for gate in row["gates"])


def test_all_ordered_slots_and_levels_preserve_pre_migration_render_bytes():
    id_map = load_id_map()
    for category, live_rows in ALL_ARCHETYPES.items():
        slots = id_map["categories"][category]
        for index in range(len(slots) + 1):
            legacy = copy.deepcopy(live_rows[index % len(live_rows)])
            resolved = resolve_live(category, index, ALL_ARCHETYPES)
            assert resolved["name"] == legacy["name"]
            assert resolved["archetype_id"] == slots[index % len(slots)]["archetype_id"]
            resolved_without_id = {k: v for k, v in resolved.items() if k != "archetype_id"}
            assert resolved_without_id == legacy
            for level in range(1, 7):
                assert generate_blocks_from_archetype(resolved, level) == (
                    generate_blocks_from_archetype(legacy, level))


def test_reachable_mapper_selection_is_exhaustively_name_equivalent(monkeypatch):
    """Factorized exhaustive tuple proof.

    The render-byte half is exhaustive over every immutable slot/wrap and L1-L6
    above. This half exhausts every mapper name, customer render mapping,
    discipline branch, and a complete category wrap. Phase is not an input to
    either selector function, so no profile sampling can hide a phase branch.
    """
    original = nate.get_archetype_by_category_and_index
    use_legacy = False

    def resolver(category, index=0):
        if use_legacy:
            rows = ALL_ARCHETYPES[category]
            return copy.deepcopy(rows[index % len(rows)])
        return original(category, index)

    monkeypatch.setattr(nate, "get_archetype_by_category_and_index", resolver)
    render_styles = {"time_crunched": "POLARIZED", "g_spot": "G_SPOT",
                     "polarized_80_20": "POLARIZED",
                     "traditional_pyramidal": "PYRAMIDAL"}
    for workout_name in WORKOUT_MAP:
        if workout_name == "Endurance":
            continue  # deterministic non-native renderer; no archetype selection
        for discipline in ("gravel", "road", "mtb"):
            nate_type, base = _resolve_for_discipline(workout_name, discipline)
            probe = select_archetype_for_workout(nate_type, "POLARIZED", base)
            if probe is None:
                continue
            category, _ = get_archetype(probe["name"])
            count = len(ALL_ARCHETYPES[category])
            pinned = workout_name in {
                "Openers", "FTP Test", "Rest Day", "Endurance with Surges",
                "NP/IF Target", "Race Simulation", "Kitchen Sink - Drain Cleaner",
                "La Balanguera", "Hyttevask", "Thunder Quads", "Blood Pistons"}
            for render_style in render_styles.values():
                for offset in range(count + 1):
                    variation = base if pinned else base + offset
                    use_legacy = True
                    legacy = select_archetype_for_workout(
                        nate_type, render_style, variation)
                    if legacy is None and render_style != "POLARIZED":
                        legacy = select_archetype_for_workout(
                            nate_type, "POLARIZED", variation)
                    use_legacy = False
                    migrated = select_archetype_for_workout(
                        nate_type, render_style, variation)
                    if migrated is None and render_style != "POLARIZED":
                        migrated = select_archetype_for_workout(
                            nate_type, "POLARIZED", variation)
                    assert (migrated or {}).get("name") == (legacy or {}).get("name")


def test_exhaustive_reachable_tuple_category_name_filename_and_zwo_bytes(monkeypatch):
    """Binding §5.2 proof: every 70,656 reachable tuple, including N wrap."""
    assert selection_case_count() == 70_656
    original = nate.get_archetype_by_category_and_index
    legacy_mode = False

    def resolver(category, index=0):
        if legacy_mode:
            rows = ALL_ARCHETYPES[category]
            return copy.deepcopy(rows[index % len(rows)])
        return original(category, index)

    monkeypatch.setattr(nate, "get_archetype_by_category_and_index", resolver)
    cache = {}
    compared = 0
    for case in iter_reachable_selection_cases():
        key = (case.render_style, case.discipline, case.workout_type,
               case.variation_offset, case.level)
        if key not in cache:
            legacy_mode = True
            legacy = _selection(case.workout_type, case.discipline,
                                case.render_style, case.variation_offset)
            legacy_bytes = render_workout(
                case.workout_type, level=case.level,
                methodology=case.render_style,
                variation_offset=case.variation_offset,
                discipline=case.discipline,
                workout_name="selection_migration_proof")
            legacy_mode = False
            migrated = _selection(case.workout_type, case.discipline,
                                  case.render_style, case.variation_offset)
            migrated_bytes = render_workout(
                case.workout_type, level=case.level,
                methodology=case.render_style,
                variation_offset=case.variation_offset,
                discipline=case.discipline,
                workout_name="selection_migration_proof")
            legacy_category = get_archetype(legacy["name"])[0]
            migrated_category = get_archetype(migrated["name"])[0]
            legacy_filename = projected_filename(case, legacy)
            migrated_filename = projected_filename(case, migrated)
            cache[key] = (legacy_category, legacy["name"], legacy_filename,
                          legacy_bytes, migrated_category, migrated["name"],
                          migrated_filename, migrated_bytes)
        (legacy_category, legacy_name, legacy_filename, legacy_bytes,
         migrated_category, migrated_name, migrated_filename,
         migrated_bytes) = cache[key]
        assert migrated_category == legacy_category
        assert migrated_name == legacy_name
        assert migrated_filename == legacy_filename
        assert migrated_bytes.encode("utf-8") == legacy_bytes.encode("utf-8")
        compared += 1
    assert compared == 70_656


@pytest.mark.parametrize("render_style", ["", "polarized", "UNKNOWN"])
def test_render_style_fails_closed(render_style):
    with pytest.raises(ValueError, match="Unknown render style"):
        select_archetype_for_workout("vo2max", render_style, 0)


def test_methodology_authorities_fail_closed_when_missing_malformed_or_unknown(monkeypatch):
    real_open = builtins.open

    def missing(path, *args, **kwargs):
        if str(path).endswith("methodologies.yaml"):
            raise FileNotFoundError(path)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", missing)
    with pytest.raises(RuntimeError, match="unavailable or malformed"):
        select_methodology._load_methodologies()
    monkeypatch.setattr(builtins, "open", real_open)

    monkeypatch.setattr(select_methodology.yaml, "safe_load",
                        lambda _stream: {"unknown": {}})
    with pytest.raises(RuntimeError, match="closed customer IDs"):
        select_methodology._load_methodologies()

    monkeypatch.setattr(generate_athlete_package.yaml, "safe_load",
                        lambda _text: {"render_styles": {"unknown": "POLARIZED"}})
    with pytest.raises(RuntimeError, match="closed E1 map"):
        generate_athlete_package._load_methodology_map()


def _identity_model(sessions):
    return {"model_version": MODEL_VERSION,
            "athlete": {"control_metric": "power", "control_basis": "ftp",
                        "power_basis": "measured", "ftp_watts": 250},
            "sessions": sessions}


def test_session_id_round_trip_and_same_day_double_order():
    sessions = [{"id": f"w01.2026-01-05.{ordinal:02d}", "week": 1,
                 "date": "2026-01-05", "daily_ordinal": ordinal,
                 "segments": []} for ordinal in (1, 2)]
    validate_canonical_model(_identity_model(sessions))


@pytest.mark.parametrize("sessions", [
    [{"id": "w01.None.01", "week": 1, "date": None,
      "daily_ordinal": 1, "segments": []}],
    [{"id": "w01.2026-01-05.00", "week": 1, "date": "2026-01-05",
      "daily_ordinal": 0, "segments": []}],
    [{"id": "w01.2026-01-05.01", "week": 1, "date": "2026-01-05",
      "daily_ordinal": 1, "segments": []},
     {"id": "w01.2026-01-05.01", "week": 1, "date": "2026-01-05",
      "daily_ordinal": 1, "segments": []}],
])
def test_session_identity_missing_or_collision_fails_closed(sessions):
    with pytest.raises(CanonicalModelError):
        validate_canonical_model(_identity_model(sessions))
