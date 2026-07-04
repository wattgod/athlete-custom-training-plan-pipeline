#!/usr/bin/env python3
"""Pin discipline detection so road athletes get road branding/skills.

Regression coverage for the bug where a road-discipline athlete whose target
race name lacks an obvious road keyword (and isn't dual-listed) was classified
'gravel' by default — shipping a "Gravel Skills" chapter and gravel branding in
a road athlete's guide.

The fix has two layers, both exercised here with REAL snapshot data
(config/races.json via known_races._snapshot_races):

  1. DB-discipline path (primary): when a race is UNAMBIGUOUS in the snapshot
     (present under exactly one discipline), match_race returns that discipline,
     intake_to_plan carries it onto target_race.discipline, and
     derive_discipline returns it directly.

  2. Keyword fallback (secondary): for dual-listed / discipline-ambiguous events
     the DB can't disambiguate (discipline=None), so derive_discipline keyword-
     matches the race name. Strengthened for common road event brands.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (HERE, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import importlib.util

import pytest

from archetype import derive_discipline
from known_races import match_race, _snapshot_races
import intake_to_plan


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_webhook_app():
    """Import webhook/app.py (its _questionnaire_to_markdown) by path."""
    # app.py does `from email_templates import ...` — resolvable only with
    # the webhook dir on sys.path (it runs with CWD=webhook/ in production).
    webhook_dir = os.path.join(REPO_ROOT, "webhook")
    if webhook_dir not in sys.path:
        sys.path.insert(0, webhook_dir)
    spec = importlib.util.spec_from_file_location(
        "webhook_app_for_test", os.path.join(REPO_ROOT, "webhook", "app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_WEBHOOK = _load_webhook_app()


def _profile_for_race(race_name, *, date="2027-09-12", distance="100 miles"):
    """Build a profile through the REAL intake path for a single A-race.

    Mirrors production: web questionnaire JSON -> _questionnaire_to_markdown ->
    parse_intake_markdown -> build_profile. Returns the profile dict.
    """
    intake = {
        "name": "Discipline Test Athlete",
        "email": "discipline-test@synthetic.local",
        "sex": "Male",
        "age": 35,
        "weight": 165,
        "height_ft": 5,
        "height_in": 10,
        "ftp": 250,
        "years_cycling": "5",
        "prior_plan_experience": "2",
        "hours_per_week": "10",
        "trainer_access": "smart trainer",
        "long_ride_days": ["Saturday"],
        "interval_days": ["Tuesday", "Thursday"],
        "off_days": ["Monday"],
        "strength_current": "none",
        "strength_want": "no",
        "strength_equipment": "minimal",
        "sleep_quality": "good",
        "stress_level": "moderate",
        "injuries": "None",
        "notes": "",
        "races": [
            {"name": race_name, "date": date, "distance": distance,
             "priority": "A", "goal": "Finish Strong"},
        ],
    }
    md = _WEBHOOK._questionnaire_to_markdown(
        intake, name=intake["name"], email=intake["email"])
    parsed = intake_to_plan.parse_intake_markdown(md)
    return intake_to_plan.build_profile(parsed)


def _road_only_snapshot_race():
    """A race name present under exactly the 'road' discipline in the snapshot."""
    snap = _snapshot_races()
    for info in snap.values():
        if info.get("discipline") == "road":
            return info["name"]
    pytest.skip("no road-only race in snapshot (config/races.json missing?)")


def _gravel_only_snapshot_race():
    """A gravel-only race whose name round-trips discipline='gravel' via match_race."""
    snap = _snapshot_races()
    for info in snap.values():
        if info.get("discipline") != "gravel":
            continue
        m = match_race(info["name"])
        if m and m[1].get("discipline") == "gravel":
            return info["name"]
    pytest.skip("no round-tripping gravel-only race in snapshot")


# --------------------------------------------------------------------------- #
# (a) Road-only snapshot race -> 'road' through the intake path (DB-discipline)
# --------------------------------------------------------------------------- #
class TestRoadDiscipline:
    def test_road_only_snapshot_race_resolves_road_in_match(self):
        name = _road_only_snapshot_race()
        matched = match_race(name)
        assert matched is not None, f"{name!r} should match the snapshot"
        assert matched[1].get("discipline") == "road"

    def test_road_only_race_yields_road_through_intake_path(self):
        """The core bug: a road-only race must reach derive_discipline == 'road'
        via target_race.discipline, NOT fall through to the gravel default."""
        name = _road_only_snapshot_race()
        profile = _profile_for_race(name)
        assert profile["target_race"].get("discipline") == "road", (
            "DB discipline must be carried onto target_race.discipline")
        assert derive_discipline(profile) == "road"

    def test_road_brand_keyword_events_classified_road(self):
        """Road event brands that lack a generic road word but are road-only /
        road-dominant in the DB are caught by the strengthened keyword fallback.
        These previously defaulted to gravel."""
        for name in ("GFNY Bremen", "L'Etape Slovakia by Tour de France",
                     "Taiwan KOM Challenge", "La Marmotte"):
            assert derive_discipline({"target_race": {"name": name}}) == "road", name

    def test_mtb_brand_events_classified_mtb(self):
        """Famous MTB events whose names carry no 'mtb' word (Iceman Cometh,
        Whiskey Off-Road, Marji Gesick) were defaulting to gravel, so MTB
        athletes got the gravel skills chapter. The strengthened keyword
        fallback now classifies them mtb."""
        for name in ("Iceman Cometh", "WHISKEY OFF-ROAD", "Marji Gesick",
                     "Chequamegon MTB"):
            assert derive_discipline({"target_race": {"name": name}}) == "mtb", name

    def test_true_grit_gravel_not_misread_as_mtb(self):
        # 'true grit' is deliberately NOT an mtb keyword — it names a GRAVEL
        # race. Guard against a future regression that adds it.
        assert derive_discipline(
            {"target_race": {"name": "Lauf True Grit Gravel Epic"}}) == "gravel"


# --------------------------------------------------------------------------- #
# (b) Gravel race stays gravel
# --------------------------------------------------------------------------- #
class TestGravelStaysGravel:
    def test_gravel_only_race_stays_gravel_through_intake_path(self):
        name = _gravel_only_snapshot_race()
        profile = _profile_for_race(name)
        # Either DB discipline says gravel, or the name's 'gravel' keyword wins —
        # either way the athlete must NOT be misclassified as road.
        assert derive_discipline(profile) == "gravel", name

    def test_gravel_fondo_names_are_not_misread_as_road(self):
        """'fondo' is a road keyword, but the gravel keyword is checked first,
        so a 'Gravel Fondo' event must resolve gravel, never road."""
        for name in ("Cowichan Crusher Gravel Fondo", "Gravel Fondo Louisiana",
                     "Unbound Gravel 200"):
            assert derive_discipline({"target_race": {"name": name}}) == "gravel", name

    def test_explicit_gravel_discipline_wins(self):
        profile = {"discipline": "gravel",
                   "target_race": {"name": "Gran Fondo Stelvio"}}
        # explicit profile discipline beats any keyword/DB inference
        assert derive_discipline(profile) == "gravel"


# --------------------------------------------------------------------------- #
# (c) Dual-listed event -> falls to keyword logic (no DB discipline)
# --------------------------------------------------------------------------- #
class TestDualListedFallsToKeyword:
    def test_dual_listed_name_has_no_db_discipline(self):
        """Names present under BOTH gravel and road in the snapshot are marked
        discipline=None so the guide's keyword logic decides."""
        snap = _snapshot_races()
        # Find a name that exists under >1 discipline (set discipline to None).
        dual = next((info["name"] for info in snap.values()
                     if info.get("discipline") is None), None)
        if dual is None:
            pytest.skip("no dual-listed (None-discipline) race in snapshot")
        matched = match_race(dual)
        assert matched is not None
        assert matched[1].get("discipline") is None

    def test_dual_listed_road_keyword_resolves_road(self):
        """A dual-listed event whose name carries a road keyword ('giro') must
        resolve road purely through keyword logic (DB discipline is None)."""
        name = "Sparkassen Munsterland Giro"
        matched = match_race(name)
        if matched is None or matched[1].get("discipline") is not None:
            pytest.skip("Munsterland Giro not dual-listed in this snapshot")
        profile = _profile_for_race(name)
        assert profile["target_race"].get("discipline") in (None, "road")
        assert derive_discipline(profile) == "road"

    def test_dual_listed_no_keyword_falls_to_gravel_default(self):
        """A dual-listed event with NO road keyword in its name has no signal
        anywhere, so it correctly falls to the 'gravel' default (core audience).
        This pins the documented fallback behavior, not a bug."""
        profile = {"target_race": {"name": "66 Degrés Sud", "discipline": None}}
        assert derive_discipline(profile) == "gravel"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
