"""Above-sea-level altitude must flow snapshot -> profile/guide -> trigger.

The ALTITUDE_SECTION_MISSING post-render check and the guide's Altitude
Training section both read race_metadata.start_elevation_feet /
avg_elevation_feet. The snapshot is the only race source in the production
container, so if it does not carry the metadata both are dead (an 8,100 ft
race shipped a guide with no altitude section).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_race_snapshot
from known_races import lookup_by_slug, match_race
from training_guide_builder import (_conditional_triggers,
                                    _overlay_snapshot_race_metadata)


def _write_race(tmp_path, slug, vitals):
    (tmp_path / f"{slug}.json").write_text(json.dumps({
        "race": {"name": slug.replace("-", " ").title(), "vitals": vitals},
    }))


def test_snapshot_builder_emits_asl_race_metadata(tmp_path, monkeypatch):
    gravel = tmp_path / "gravel"
    gravel.mkdir()
    _write_race(gravel, "high-race", {
        "distance_mi": 60, "elevation_ft": 7000, "location": "Alta, Utah",
        "date_specific": "2026: July 4",
        "start_elevation_asl_ft": 8100, "avg_elevation_asl_ft": 8800,
    })
    _write_race(gravel, "flat-race", {
        "distance_mi": 60, "elevation_ft": 7000, "location": "Emporia, Kansas",
        "date_specific": "2026: July 5",
    })
    monkeypatch.setattr(build_race_snapshot, "SOURCES", [(gravel, "gravel")])
    monkeypatch.setattr(
        build_race_snapshot, "SNAPSHOT", tmp_path / "races.json")
    payload = build_race_snapshot.build()
    high = payload["races"]["gravel:high-race"]
    assert high["race_metadata"] == {
        "start_elevation_feet": 8100, "avg_elevation_feet": 8800}
    # Climbing gain alone must NEVER produce altitude metadata (the Unbound
    # "takes place at 11,000 feet" failure).
    assert "race_metadata" not in payload["races"]["gravel:flat-race"]


def test_committed_snapshot_carries_altitude_for_known_mountain_races():
    for slug, floor in (("mammoth-tuff", 8000), ("leadville-100", 10000)):
        entry = lookup_by_slug(slug)[1]
        meta = entry.get("race_metadata") or {}
        assert max(
            meta.get("start_elevation_feet", 0),
            meta.get("avg_elevation_feet", 0),
        ) > floor, f"{slug} lost its above-sea-level metadata"


def test_overlay_fills_from_snapshot_and_fires_trigger():
    race_data = {}
    _overlay_snapshot_race_metadata(race_data, "Mammoth Tuff")
    assert race_data["race_metadata"]["start_elevation_feet"] == 8100
    assert _conditional_triggers({}, race_data)["altitude"] is True


def test_overlay_never_overwrites_file_sourced_values():
    race_data = {"race_metadata": {"start_elevation_feet": 4200}}
    _overlay_snapshot_race_metadata(race_data, "Mammoth Tuff")
    assert race_data["race_metadata"]["start_elevation_feet"] == 4200


def test_overlay_is_a_noop_for_unknown_races():
    race_data = {}
    _overlay_snapshot_race_metadata(race_data, "Completely Unknown Race 9x")
    assert race_data["race_metadata"] == {}
    assert _conditional_triggers({}, race_data)["altitude"] is False


def test_snapshot_metadata_reaches_profile_lookup_shape():
    # intake_to_plan copies info['race_metadata'] into
    # profile.target_race.race_metadata — the exact field the post-render
    # ALTITUDE_SECTION_MISSING check reads. The lookup entry is that info.
    key, info = match_race("Mammoth Tuff")
    assert key == "gravel:mammoth-tuff"
    assert info["race_metadata"]["start_elevation_feet"] == 8100


def test_overlay_prefers_profile_metadata_over_name_matching():
    # Leadville: name-based match_race resolves to a curated alias with NO
    # metadata while the slug-resolved profile carries 10,200/11,000 ft.
    # The guide must read the profile source the validator compares against.
    profile = {"target_race": {"race_metadata": {
        "start_elevation_feet": 10200, "avg_elevation_feet": 11000}}}
    race_data = {}
    _overlay_snapshot_race_metadata(race_data, "Leadville 100", profile)
    assert race_data["race_metadata"]["start_elevation_feet"] == 10200
    assert _conditional_triggers({}, race_data)["altitude"] is True


def test_name_fallback_alone_misses_curated_aliases():
    # Documents WHY profile-first matters: without a profile, the curated
    # 'Leadville 100' alias shadows the snapshot record's metadata.
    race_data = {}
    _overlay_snapshot_race_metadata(race_data, "Leadville 100")
    assert race_data["race_metadata"] == {}


def test_discipline_twins_share_venue_metadata():
    # Engadin and Marmotte exist as gravel AND road with the same slug;
    # lookup returns the first match. Venue altitude is route-independent,
    # so BOTH namespaced twins must carry it or the first-match entry
    # silently suppresses altitude.
    snapshot = json.loads(
        (Path(__file__).parent.parent / "config" / "races.json").read_text()
    )["races"]
    for slug, expected_avg in (("engadin-radmarathon", 5840),
                               ("marmotte-granfondo-sestriere", 4560)):
        keys = [k for k in snapshot if k.split(":", 1)[-1] == slug]
        assert len(keys) == 2, f"{slug} twins missing from snapshot"
        for key in keys:
            meta = snapshot[key].get("race_metadata") or {}
            assert meta.get("avg_elevation_feet") == expected_avg, key


def test_truckee_entry_exists_with_builder_parity_fields():
    key, info = lookup_by_slug("truckee-tahoe-gravel")
    assert key == "gravel:truckee-tahoe-gravel"
    assert info["name"] == "Truckee Tahoe Gravel"
    assert info["date"] == "2026-06-27"
    assert info["distance_miles"] == 66
    assert info["elevation_ft"] == 4604
    assert info["race_metadata"] == {
        "start_elevation_feet": 5800, "avg_elevation_feet": 6076}
