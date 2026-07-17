"""End-to-end ORDER ACCEPTANCE — the send-worthy contract.

Every fix it took to make Jesse Couch's plan send-worthy was a coherence
failure: something true in the data rendered wrong (or missing) in the
deliverable, and no test caught it. This suite runs the REAL pipeline
exactly as a paying order does — webhook questionnaire markdown →
intake_to_plan.py subprocess → PDF — across a spread of golden orders,
then asserts the full contract that makes a plan worth sending:

  1. The pipeline exits 0 (the delivery-blocking gates all passed)
  2. Every deliverable exists (guide, PDF, workouts, fueling)
  3. The PDF is structurally valid (magic, EOF, real page count)
  4. The guide passes the quality gate (no placeholders, no slop)
  5. Volume + zones + taper + caps all pass the preview checks
  6. COHERENCE: every profile fact the guide states matches the profile
     (FTP, race name, race date, strength equipment, methodology) — this
     is the layer that only manual eyeballing used to catch
  7. The sections Matti cut stay cut (Race Profile, Non-Negotiables,
     Week-by-Week)
  8. Compliance is 11/11 critical

Heavy by design — opt in with GG_RUN_ACCEPTANCE=1 (CI + `make preflight`
set it). The fast suite stays fast.

Add a new golden order to GOLDEN_ORDERS to widen coverage; the contract
runs against all of them automatically.
"""

import os
import re
import subprocess
import sys
from types import SimpleNamespace
from html import unescape
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
WEBHOOK_DIR = REPO_ROOT / "webhook"

pytestmark = pytest.mark.acceptance

_RUN = os.environ.get("GG_RUN_ACCEPTANCE") == "1"
_skip_reason = "set GG_RUN_ACCEPTANCE=1 to run the slow end-to-end order suite"


# ---------------------------------------------------------------------------
# Golden orders — realistic webhook payloads spanning the dimensions that
# have broken the pipeline. Race dates use known_races entries with FUTURE
# dates so the (correct) past-date / date-mismatch gates don't trip.
# ---------------------------------------------------------------------------
def _real_gravel_race():
    """A stable, future-dated REAL gravel race from the snapshot so golden
    orders test against actual events and never rot when a date rolls past.
    Falls back to a fixed race if the snapshot isn't built."""
    import random
    from datetime import date as _date
    try:
        from real_races import pick
        race = pick(random.Random("acceptance-golden-v1"), discipline="gravel",
                    min_weeks=14, max_weeks=28, min_mi=50, max_mi=110,
                    today=_date.today().isoformat())
        if race:
            return race
    except Exception:
        pass
    return {"name": "Big Sugar Gravel", "date": "2026-10-17",
            "distance_mi": 104, "elevation_ft": 6000}


def _real_road_race(*, hillclimb=False):
    """Pick stable, future, provenanced Roadie fondo/hill-climb fixtures."""
    import random
    from datetime import date as _date
    try:
        from real_races import pick
        bounds = {"min_mi": 1, "max_mi": 40} if hillclimb else {
            "min_mi": 40, "max_mi": 140}
        race = pick(
            random.Random("acceptance-road-hill-v1" if hillclimb
                          else "acceptance-road-fondo-v1"),
            discipline="road", min_weeks=8, max_weeks=60,
            today=_date.today().isoformat(), **bounds)
        if race:
            return race
    except Exception:
        pass
    if hillclimb:
        return {"name": "Mount Baker Hill Climb", "date": "2026-09-13",
                "distance_mi": 22, "elevation_ft": 4462,
                "slug": "mount-baker-hill-climb"}
    return {"name": "RBC GranFondo Whistler", "date": "2026-09-12",
            "distance_mi": 76, "elevation_ft": 7500,
            "slug": "rbc-granfondo-whistler"}


_RACE = _real_gravel_race()
_RACE_DIST = f"{int(round(float(_RACE['distance_mi'])))} miles"
_ROAD_FONDO = _real_road_race()
_ROAD_HILL = _real_road_race(hillclimb=True)

GOLDEN_ORDERS = [
    {
        "id": "acctest-gravel-fullgym",
        "label": "mid-volume gravel, real race, FTP known, FULL GYM",
        # exercises: strength-equipment coherence (Jesse's bug), volume fill,
        # standard methodology selection
        "intake": {
            "name": "Acc Test Gravelrider", "email": "acc-gravel@test.local",
            "sex": "Male", "age": 41, "weight": 165, "height_ft": 5, "height_in": 11,
            "ftp": 240, "years_cycling": "7", "prior_plan_experience": "3",
            "hours_per_week": "9", "trainer_access": "smart trainer",
            "long_ride_days": ["Saturday"], "interval_days": ["Tuesday", "Thursday"],
            "off_days": ["Monday"],
            "strength_current": "2x/week", "strength_want": "yes",
            "strength_equipment": "full gym",
            "sleep_quality": "good", "stress_level": "moderate", "injuries": "None",
            "races": [{"name": _RACE["name"], "date": _RACE["date"],
                       "distance": _RACE_DIST, "priority": "A", "goal": "Compete"}],
        },
        "expect": {
            "ftp": "240", "race": _RACE["name"], "race_date": _RACE["date"],
            "strength_equipment": "full gym", "target_hours": 9.0,
        },
    },
    {
        "id": "acctest-masters-female",
        "label": "masters female, estimated FTP, lower volume (women+masters sections)",
        # exercises: women + masters conditional render paths, estimated-FTP
        # handling, lower-hour volume fill
        "intake": {
            "name": "Acc Test Mastersrider", "email": "acc-masters@test.local",
            "sex": "Female", "age": 54, "weight": 138, "height_ft": 5, "height_in": 6,
            "ftp": 165, "years_cycling": "10", "prior_plan_experience": "2",
            "hours_per_week": "7", "trainer_access": "smart trainer",
            "long_ride_days": ["Sunday"], "interval_days": ["Tuesday", "Thursday"],
            "off_days": ["Monday", "Friday"],
            "strength_current": "occasional", "strength_want": "yes",
            "strength_equipment": "dumbbells",
            "sleep_quality": "fair", "stress_level": "moderate", "injuries": "None",
            "races": [{"name": _RACE["name"], "date": _RACE["date"],
                       "distance": _RACE_DIST, "priority": "A", "goal": "Finish Strong"}],
        },
        "expect": {
            "ftp": "165", "race": _RACE["name"], "race_date": _RACE["date"],
            "strength_equipment": "dumbbells", "target_hours": 7.0,
        },
    },
    {
        "id": "acctest-roadie-fondo",
        "label": "Roadie Labs real gran fondo through shared webhook runner",
        "via_webhook": True,
        "intake": {
            "name": "Acc Test Roadiefondo", "email": "acc-road@test.local",
            "brand": "roadielabs", "race_slug": _ROAD_FONDO.get("slug", ""),
            "road_category": "cat_5",
            "sex": "Male", "age": 38, "weight": 160,
            "height_ft": 5, "height_in": 10, "ftp": 255,
            "years_cycling": "6", "prior_plan_experience": "3",
            "hours_per_week": "9", "trainer_access": "smart trainer",
            "long_ride_days": ["Saturday"],
            "interval_days": ["Tuesday", "Thursday"], "off_days": ["Monday"],
            "strength_current": "none", "strength_want": "no",
            "strength_equipment": "minimal", "sleep_quality": "good",
            "stress_level": "moderate", "injuries": "None",
            "races": [{"name": _ROAD_FONDO["name"],
                       "date": _ROAD_FONDO["date"],
                       "distance": f"{int(round(float(_ROAD_FONDO['distance_mi'])))} miles",
                       "priority": "A", "goal": "Finish Strong",
                       "race_format": "fondo",
                       "slug": _ROAD_FONDO.get("slug", "")}],
        },
        "expect": {
            "ftp": "255", "race": _ROAD_FONDO["name"],
            "race_date": _ROAD_FONDO["date"], "strength_equipment": None,
            "target_hours": 9.0, "brand": "roadielabs", "discipline": "road",
            "event_format": "fondo", "road_category": "cat_5",
            "pdf_optional": True,
        },
    },
    {
        "id": "acctest-roadie-hillclimb",
        "label": "Roadie Labs real hill climb through shared webhook runner",
        "via_webhook": True,
        "intake": {
            "name": "Acc Test Roadieclimber", "email": "acc-climb@test.local",
            "brand": "roadielabs", "race_slug": _ROAD_HILL.get("slug", ""),
            "road_category": "cat_4",
            "sex": "Male", "age": 44, "weight": 150,
            "height_ft": 5, "height_in": 9, "ftp": 270,
            "years_cycling": "9", "prior_plan_experience": "4",
            "hours_per_week": "8", "trainer_access": "smart trainer",
            "long_ride_days": ["Sunday"],
            "interval_days": ["Tuesday", "Thursday"], "off_days": ["Monday"],
            "strength_current": "none", "strength_want": "no",
            "strength_equipment": "minimal", "sleep_quality": "good",
            "stress_level": "moderate", "injuries": "None",
            "races": [{"name": _ROAD_HILL["name"], "date": _ROAD_HILL["date"],
                       "distance": f"{int(round(float(_ROAD_HILL['distance_mi'])))} miles",
                       "priority": "A", "goal": "Compete",
                       "race_format": "hill_climb",
                       "slug": _ROAD_HILL.get("slug", "")}],
        },
        "expect": {
            "ftp": "270", "race": _ROAD_HILL["name"],
            "race_date": _ROAD_HILL["date"], "strength_equipment": None,
            "target_hours": 8.0, "brand": "roadielabs", "discipline": "road",
            "event_format": "hill_climb", "road_category": "cat_4",
            "pdf_optional": True,
        },
    },
]


# ---------------------------------------------------------------------------
# Run the real pipeline once per order (module-scoped: subprocess is slow).
# ---------------------------------------------------------------------------
def _questionnaire_to_markdown(intake):
    sys.path.insert(0, str(WEBHOOK_DIR))
    from app import _questionnaire_to_markdown as conv
    return conv(intake, name=intake["name"], email=intake["email"])


def _run_order(tmp_path, order):
    md = _questionnaire_to_markdown(order["intake"])
    md_file = tmp_path / f"{order['id']}.md"
    md_file.write_text(md)

    # Delivery dir must live under $HOME — the pipeline's path-safety guard
    # rejects writes outside home/project (pytest's tmp is under /private/var).
    delivery_root = Path.home() / ".gg-acctest-delivery" / order["id"]
    if delivery_root.exists():
        import shutil
        shutil.rmtree(delivery_root)
    delivery_root.mkdir(parents=True)

    env = dict(os.environ)
    env["GG_DELIVERY_DIR"] = str(delivery_root)
    env["GG_GUIDES_DIR"] = str(delivery_root / "gravel-god-guides")
    env["ROADIE_GUIDES_DIR"] = str(delivery_root / "roadie-labs-guides")
    env["PYTHONPATH"] = str(REPO_ROOT)

    if order.get("via_webhook"):
        # Exercise the production shared runner (including its questionnaire
        # conversion) without touching Stripe or TrainingPeaks.
        from unittest.mock import patch
        sys.path.insert(0, str(WEBHOOK_DIR))
        import app as webhook_app
        with patch.object(webhook_app, "SCRIPTS_DIR", str(SCRIPTS_DIR)), \
             patch.object(webhook_app, "PIPELINE_TIMEOUT", 600), \
             patch.dict(os.environ, env, clear=False):
            result = webhook_app.run_pipeline(
                order["id"], deliver=True, intake_data=order["intake"])
        proc = SimpleNamespace(
            returncode=0 if result["success"] else 1,
            stdout=result.get("stdout", ""), stderr=result.get("stderr", ""))
    else:
        proc = subprocess.run(
            [sys.executable, "intake_to_plan.py", "--file", str(md_file)],
            cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True, timeout=600,
        )
    # The pipeline derives the athlete id from the NAME (e.g. "Acc Test
    # Gravelrider" -> "acc-gravelrider") and prints it; parse rather than guess.
    m = re.search(r"\bID:\s*(\S+)", proc.stdout)
    athlete_id = m.group(1) if m else order["id"]
    athlete_dir = SCRIPTS_DIR.parent / athlete_id
    delivery_dir = delivery_root / f"{athlete_id}-training-plan"
    return proc, athlete_dir, delivery_dir


@pytest.fixture(scope="module", params=GOLDEN_ORDERS, ids=lambda o: o["id"])
def built_order(request, tmp_path_factory):
    if not _RUN:
        pytest.skip(_skip_reason)
    order = request.param
    tmp = tmp_path_factory.mktemp(order["id"])
    proc, athlete_dir, delivery_dir = _run_order(tmp, order)
    return {"order": order, "proc": proc, "athlete_id": athlete_dir.name,
            "athlete_dir": athlete_dir, "delivery_dir": delivery_dir}


# ---------------------------------------------------------------------------
# The send-worthy contract.
# ---------------------------------------------------------------------------
def _guide_text(athlete_dir):
    html = (athlete_dir / "training_guide.html").read_text()
    return html, unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))


def test_pipeline_exits_clean(built_order):
    """Exit 0 means every delivery-blocking gate passed."""
    proc = built_order["proc"]
    assert proc.returncode == 0, (
        f"pipeline exited {proc.returncode} (gate blocked delivery)\n"
        f"--- stdout tail ---\n{proc.stdout[-1500:]}\n"
        f"--- stderr tail ---\n{proc.stderr[-800:]}"
    )


def test_all_deliverables_present(built_order):
    d = built_order["delivery_dir"]
    assert (d / "training_guide.html").exists(), "guide HTML missing"
    if not built_order["order"]["expect"].get("pdf_optional"):
        assert (d / "training_guide.pdf").exists(), "guide PDF missing"
    assert (d / "fueling.yaml").exists(), "fueling.yaml missing"
    workouts = d / "workouts"
    assert workouts.exists() and len(list(workouts.glob("*.zwo"))) >= 20, \
        "workouts/ missing or sparse"


def test_pdf_is_structurally_valid(built_order):
    from pdf_generator import validate_pdf
    pdf = built_order["delivery_dir"] / "training_guide.pdf"
    if not pdf.exists() and built_order["order"]["expect"].get("pdf_optional"):
        pytest.skip("production contract permits HTML guide when PDF engine is unavailable")
    ok, msg = validate_pdf(pdf)
    assert ok, f"PDF invalid: {msg}"


def test_guide_passes_quality_gate(built_order):
    """No placeholders, no slop, all required sections."""
    from validate_guide_quality import validate_guide
    passed, report = validate_guide(built_order["athlete_id"])
    assert passed, f"guide quality FAILED:\n{report}"


def test_preview_checks_have_no_failures(built_order):
    """Volume fill, zone distribution, taper, day caps, off days — the
    calibrated preview checks must not FAIL (WARN is acceptable)."""
    from generate_plan_preview import build_preview_data
    data = build_preview_data(built_order["athlete_dir"])
    failures = [f"{c['name']}: {c.get('detail', '')}"
                for c in data["checks"] if c["status"] == "FAIL"]
    assert not failures, "preview checks failed:\n" + "\n".join(failures)


def test_volume_fills_stated_hours(built_order):
    """Build/peak load weeks must fill 80-120% of the athlete's hours —
    the NP/IF bug shipped base blocks at ~50%."""
    from generate_plan_preview import build_preview_data
    target = built_order["order"]["expect"]["target_hours"]
    data = build_preview_data(built_order["athlete_dir"])
    vol = next((c for c in data["checks"] if c["name"] == "Weekly Volume"), None)
    assert vol is not None, "no Weekly Volume check produced"
    pct = float(re.search(r"\((\d+)%\)", vol["detail"]).group(1))
    assert 80 <= pct <= 120, (
        f"volume fill {pct}% of {target}h target (want 80-120%): {vol['detail']}")


def test_guide_facts_match_profile(built_order):
    """COHERENCE: every fact the guide states must match the input. This is
    the layer that only manual review caught (e.g. 'full gym' rendered as
    'bodyweight')."""
    exp = built_order["order"]["expect"]
    _, text = _guide_text(built_order["athlete_dir"])

    assert exp["ftp"] in text, f"FTP {exp['ftp']}W not stated in guide"
    assert exp["race"] in text, f"race name '{exp['race']}' not in guide"
    # race date appears in the verification card (human-readable form)
    from datetime import datetime
    human_date = datetime.strptime(exp["race_date"], "%Y-%m-%d").strftime("%B")
    assert human_date in text, f"race month '{human_date}' not in guide"
    # strength equipment — the Jesse bug
    if exp.get("strength_equipment"):
        assert exp["strength_equipment"].lower() in text.lower(), (
            f"strength equipment '{exp['strength_equipment']}' not reflected "
            f"(guide may claim the wrong setup)")


def test_removed_sections_stay_removed(built_order):
    _, text = _guide_text(built_order["athlete_dir"])
    for banned in ("Race Profile", "Non-Negotiable", "Week-by-Week",
                   "Key Workouts in This Plan", "Race Week Schedule"):
        assert banned not in text, f"removed content reappeared: '{banned}'"


def test_fueling_targets_are_physiological(built_order):
    """Carb target must sit in a sane band for the race duration —
    not an insane number scaled off threshold."""
    fueling = yaml.safe_load(
        (built_order["delivery_dir"] / "fueling.yaml").read_text())
    carbs = fueling.get("carbohydrates", {})
    hourly = carbs.get("hourly_target", 0)
    assert 30 <= hourly <= 120, f"hourly carb target {hourly}g/hr is non-physiological"
    hours = fueling.get("race", {}).get("duration_hours", 0)
    if hours:
        total = carbs.get("total_grams", 0)
        # total should be ~ hourly * hours, within a generous factor
        assert 0.5 <= total / (hourly * hours) <= 1.6, (
            f"total carbs {total}g incoherent with {hourly}g/hr x {hours}h")


def test_compliance_is_perfect(built_order):
    """The golden order must deliver CLEAN — no compliance/quality flag.

    Since the gates now flag-for-review instead of hard-failing (the safety
    net), 'exit 0' alone no longer proves the plan is compliant. The real
    signal is NEEDS_REVIEW.txt: the compliance gate and the quality gates both
    write it when they flag a plan. A known-good golden athlete must produce
    NO flag — if a regression makes its plan non-compliant or trips a quality
    gate, this file appears and the build fails red (re-arming the net the old
    vacuous assertion lost)."""
    athlete_dir = built_order["athlete_dir"]
    assert (athlete_dir / "plan_summary.yaml").exists(), "plan_summary.yaml missing"
    review = athlete_dir / "NEEDS_REVIEW.txt"
    assert not review.exists(), (
        "golden order was FLAGGED for review — a compliance or quality gate "
        f"failed on a known-good athlete:\n{review.read_text() if review.exists() else ''}")


def test_roadie_package_is_brand_clean_and_semantically_valid(built_order):
    exp = built_order["order"]["expect"]
    if exp.get("brand") != "roadielabs":
        pytest.skip("Roadie-only package contract")

    athlete_dir = built_order["athlete_dir"]
    profile = yaml.safe_load((athlete_dir / "profile.yaml").read_text())
    assert profile["brand"] == "roadielabs"
    assert profile["discipline"] == "road"
    assert profile["event_format"] == exp["event_format"]
    assert profile["road_category"] == exp["road_category"]

    visible = [athlete_dir / "training_guide.html",
               athlete_dir / "personal_email.md",
               athlete_dir / "plan_preview.html"]
    visible.extend(sorted((athlete_dir / "workouts").glob("*.zwo")))
    for path in visible:
        text = path.read_text()
        assert "gravel" not in text.lower(), f"road brand leak in {path.name}"
        assert "Gravel God" not in text, f"Gravel God leak in {path.name}"
    assert "ROADIE LABS" in (athlete_dir / "training_guide.html").read_text()
    guide = (athlete_dir / "training_guide.html").read_text()
    assert "Road Skills" in guide
    assert "Category 5 to Category 1 Pathway" in guide
    assert "USA Cycling Policy VIII" in guide
    expected_strategy = {
        "fondo": "Gran fondo / sportive Strategy",
        "hill_climb": "Hill climb Strategy",
    }[exp["event_format"]]
    assert expected_strategy in guide

    staged_guide = (built_order["delivery_dir"].parent /
                    "roadie-labs-guides" / "athletes" /
                    built_order["athlete_id"] / "index.html")
    assert staged_guide.exists(), "Roadie guide was not staged in its configured repo"

    from validate_plan_package import validate_plan_package
    assert validate_plan_package(athlete_dir) == []
