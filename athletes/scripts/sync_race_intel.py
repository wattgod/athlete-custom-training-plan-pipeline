#!/usr/bin/env python3
"""Sync race intel from the gravel-race-automation race database into a
self-contained, checked-in bundle (athletes/config/race_intel.json).

The pipeline runs without the race-DB repo checked out (Railway prod, CI).
Course-specific facts for the race-day card (surface, features, aid
characterization, house tire pick, rider intel) live in that separate repo,
so this script bundles ONLY the fields the race-day card renderer needs, keyed
by the pipeline's own race_id (known_races.py). Nothing at request time
depends on the source repo being present -- only the bundled JSON is read.

Run manually whenever the race DB changes; commit the regenerated output:

    python3 sync_race_intel.py

Fact-conservative: a race with no match in the DB, or with a matched race
that carries none of the tracked fields, gets no entry -- the card renderer
must never invent content for a race outside this bundle.
"""

import glob
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from known_races import KNOWN_RACES

SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = SCRIPTS_DIR.parent / "config" / "race_intel.json"
RACE_DB_DIR = (Path.home() / "Documents" / "GravelGod"
               / "gravel-race-automation" / "race-data")


def _normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _load_race_files(race_db_dir: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (by_slug, by_name) indexes built from every race-data JSON
    file's ``race`` object. ``by_name`` indexes both ``name`` and
    ``display_name`` (first file wins a collision -- collisions are not
    expected across a real race database)."""
    by_slug: Dict[str, Any] = {}
    by_name: Dict[str, Any] = {}
    for fp in sorted(glob.glob(str(race_db_dir / "*.json"))):
        try:
            data = json.loads(Path(fp).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        race = data.get("race", data)
        if not isinstance(race, dict):
            continue
        by_slug[Path(fp).stem] = race
        for candidate in (race.get("name"), race.get("display_name")):
            norm = _normalize(candidate)
            if norm and norm not in by_name:
                by_name[norm] = race
    return by_slug, by_name


def _match_race(race_id: str, info: Dict[str, Any],
                by_slug: Dict[str, Any], by_name: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Match a known_races.py entry to a race-data file by id (slug) first,
    then by name -- the KNOWN_RACES race_id and the race-data filename stem
    agree for most entries (e.g. 'big_sugar' -> 'big-sugar.json')."""
    candidate_slug = race_id.replace("_", "-")
    if candidate_slug in by_slug:
        return by_slug[candidate_slug]
    norm = _normalize(info.get("name"))
    if norm and norm in by_name:
        return by_name[norm]
    return None


def _extract_intel(race: Dict[str, Any]) -> Dict[str, Any]:
    """Fact-conservative extraction: only fields actually present in the
    source race make it into the bundle -- no invented content, no claims
    beyond the data."""
    intel: Dict[str, Any] = {}

    terrain = race.get("terrain") or {}
    surface = terrain.get("surface")
    if surface:
        intel["surface"] = str(surface).strip()
    features = terrain.get("features") or []
    cleaned_features = [str(f).strip() for f in features if str(f).strip()]
    if cleaned_features:
        intel["features"] = cleaned_features

    vitals = race.get("vitals") or {}
    aid_stations = vitals.get("aid_stations")
    if aid_stations:
        intel["aid_stations"] = str(aid_stations).strip()

    primary_tires = (race.get("tire_recommendations") or {}).get("primary") or []
    if primary_tires:
        top = primary_tires[0] or {}
        name = top.get("name")
        if name:
            tire: Dict[str, Any] = {"name": str(name).strip()}
            width = top.get("recommended_width_mm")
            if width:
                tire["width_mm"] = width
            intel["top_tire"] = tire

    terrain_notes = ((race.get("youtube_data") or {}).get("rider_intel") or {}).get(
        "terrain_notes") or []
    notes = [str(note.get("text")).strip() for note in terrain_notes
             if isinstance(note, dict) and note.get("text")]
    if notes:
        intel["rider_intel_notes"] = notes[:2]

    return intel


def build(race_db_dir: Path = RACE_DB_DIR) -> Dict[str, Dict[str, Any]]:
    """Build the race_id -> intel bundle. Returns {} (no-op) when the
    source race-DB repo is not checked out -- this must never raise, since
    it can be invoked from an environment that intentionally lacks it."""
    if not race_db_dir.exists():
        return {}
    by_slug, by_name = _load_race_files(race_db_dir)
    bundle: Dict[str, Dict[str, Any]] = {}
    for race_id, info in sorted(KNOWN_RACES.items()):
        matched = _match_race(race_id, info, by_slug, by_name)
        if matched is None:
            continue
        intel = _extract_intel(matched)
        if intel:
            bundle[race_id] = intel
    return bundle


def main() -> None:
    bundle = build()
    # sort_keys + preserved (source-ordered) list contents keep re-runs
    # against an unchanged race DB byte-identical -- idempotent by design.
    OUTPUT_PATH.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(bundle)} race intel entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
