#!/usr/bin/env python3
"""
Build a consolidated real-race snapshot from the gravel + road databases.

The pipeline must not depend on sibling repos being checked out at runtime
(CI, the webhook box). This refreshes a self-contained
athletes/config/races.json from the two race-data repos:

    gravel-race-automation/race-data/*.json   (gravel)
    road-race-automation/race-data/*.json      (road)

Each entry: {slug, name, date (ISO when known), distance_mi, elevation_ft,
discipline, location}. Run when the race DBs change:

    python3 build_race_snapshot.py
"""

import calendar
import glob
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SNAPSHOT = SCRIPTS_DIR.parent / "config" / "races.json"
GG_ROOT = Path.home() / "Documents" / "GravelGod"
SOURCES = [
    (GG_ROOT / "gravel-race-automation" / "race-data", "gravel"),
    (GG_ROOT / "road-race-automation" / "race-data", "road"),
]

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def parse_iso(date_specific, fallback_year=2026):
    """Parse messy race dates into ISO. Handles 'YYYY: Month Day',
    'Month Day', and 'YYYY-MM-DD'. Returns None if no specific day."""
    if not date_specific:
        return None
    s = str(date_specific).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return s[:10]
    # "2026: March 28"  /  "March 28"  /  "Mar 28"
    year = fallback_year
    ym = re.search(r"(\d{4})\s*:", s)
    if ym:
        year = int(ym.group(1))
    dm = re.search(r"([A-Za-z]+)\s+(\d{1,2})", s)
    if not dm:
        return None
    mon = _MONTHS.get(dm.group(1).lower())
    if not mon:
        return None
    try:
        return date(year, mon, int(dm.group(2))).isoformat()
    except ValueError:
        return None


def build():
    out = {}
    counts = {}
    for src_dir, discipline in SOURCES:
        files = sorted(glob.glob(str(src_dir / "*.json")))
        counts[discipline] = 0
        for fp in files:
            try:
                d = json.load(open(fp))
            except Exception:
                continue
            r = d.get("race", d)
            vit = r.get("vitals", {}) or {}
            slug = Path(fp).stem
            name = r.get("name") or vit.get("name") or slug
            iso = parse_iso(vit.get("date_specific") or vit.get("date"))
            entry = {
                "slug": slug,
                "name": name,
                "date": iso,
                "distance_mi": vit.get("distance_mi") or r.get("distance_miles"),
                "elevation_ft": vit.get("elevation_ft") or r.get("elevation_feet"),
                "discipline": discipline,
                "location": vit.get("location") or "",
                "source_urls": r.get("source_urls") or vit.get("source_urls") or [],
                "source_type": r.get("source_type") or "race_database",
                # A snapshot build time is NOT fact verification time.  Leaving
                # this null forces the provenance gate to ask a coach rather
                # than laundering an old course record into a fresh one.
                "verified_at": r.get("verified_at") or vit.get("verified_at") or r.get("last_verified"),
                "event_year": (int(iso[:4]) if iso else None),
                "course_variant": r.get("course_variant") or vit.get("course_variant"),
                "category": r.get("category") or vit.get("category"),
                "sex": r.get("sex") or vit.get("sex"),
            }
            # gravel + road can share a slug — namespace by discipline
            key = f"{discipline}:{slug}"
            # Championship records may legitimately share a slug while having
            # distinct men's/women's or route facts.  Never overwrite one
            # into an unqualified event record.
            if key in out:
                qualifier = re.sub(r"[^a-z0-9]+", "-", str(entry.get("category") or entry.get("sex") or entry.get("course_variant") or "variant").lower()).strip("-")
                key = f"{key}:{qualifier or 'variant'}"
            out[key] = entry
            counts[discipline] += 1

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_generated": date.today().isoformat(),
               "_counts": counts, "races": out}
    SNAPSHOT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    dated = sum(1 for e in out.values() if e["date"])
    print(f"wrote {SNAPSHOT}")
    print(f"  {counts} = {sum(counts.values())} races, {dated} with a specific date")
    return payload


if __name__ == "__main__":
    build()
