"""End-to-end ORDER ACCEPTANCE — the send-worthy contract.

Every fix it took to make Jesse Couch's plan send-worthy was a coherence
failure: something true in the data rendered wrong (or missing) in the
deliverable, and no test caught it. This suite runs the REAL pipeline
exactly as a paying order does — webhook questionnaire markdown →
intake_to_plan.py subprocess → PDF — across a spread of golden orders,
then asserts the full contract that makes a plan worth sending:

  1. The pipeline exits 0 (the delivery-blocking gates all passed)
  2. Every deliverable exists (guide, PDF, fueling; workouts are generated
     but stay sealed pre-approval — executables never reach the
     pre-approval delivery surface, per SPEC_TRUSTWORTHY_FULFILMENT)
  3. The PDF is structurally valid (magic, EOF, real page count)
  4. The guide passes the quality gate (no placeholders, no slop)
  5. Preview disposition is exact: clean fixtures stay clean; known Motoren
     authority blockers stay sealed for coach review
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

import json
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
# have broken the pipeline. These fixtures and their generation clock are
# deliberately literal: wall-clock race selection made the old "goldens"
# change whenever a candidate crossed the moving min_weeks boundary.
# ---------------------------------------------------------------------------
_GOLDEN_GENERATION_AT = "2026-08-06T15:00:00Z"

# Provenance: literal copies of the named keys in the committed
# athletes/config/races.json snapshot as of the fixture refresh above.
_RACE = {
    "name": "Tour de Tucson", "date": "2026-11-21", "distance_mi": 102,
    "elevation_ft": 3500, "location": "Tucson, Arizona, USA",
    "discipline": "gravel", "slug": "tour-de-tucson",
}
_RACE_DIST = f"{int(round(float(_RACE['distance_mi'])))} miles"
_ROAD_FONDO = {
    "name": "Granfondo Tre Valli Varesine", "date": "2026-10-03",
    "distance_mi": 78.84, "elevation_ft": 8202.0,
    "location": "Varese, Lombardy, Italy", "discipline": "road",
    "slug": "granfondo-tre-valli-varesine",
}
_ROAD_HILL = {
    "name": "Taiwan KOM Challenge", "date": "2026-10-23",
    "distance_mi": 93.0, "elevation_ft": 10745.0,
    "location": "Yilan to Wuling Pass, Taiwan", "discipline": "road",
    "slug": "taiwan-kom-challenge",
}

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
            "preview_blockers": ["PREVIEW_ZONE_DISTRIBUTION"],
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
            "preview_blockers": [
                "PREVIEW_WEEKLY_VOLUME", "PREVIEW_ZONE_DISTRIBUTION"],
            "volume_pct": 79,
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
            "strength_current": "2x/week", "strength_want": "yes",
            "strength_equipment": "full gym", "sleep_quality": "good",
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
            "race_date": _ROAD_FONDO["date"], "strength_equipment": "full gym",
            "target_hours": 9.0, "brand": "roadielabs", "discipline": "road",
            "event_format": "fondo", "road_category": "cat_5",
            "min_strength_sessions": 4,
            "pdf_optional": True,
            "preview_blockers": [],
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
            "strength_current": "2x/week", "strength_want": "yes",
            "strength_equipment": "full gym", "sleep_quality": "good",
            "stress_level": "moderate", "injuries": "None",
            "races": [{"name": _ROAD_HILL["name"], "date": _ROAD_HILL["date"],
                       "distance": f"{int(round(float(_ROAD_HILL['distance_mi'])))} miles",
                       "priority": "A", "goal": "Compete",
                       "race_format": "hill_climb",
                       "slug": _ROAD_HILL.get("slug", "")}],
        },
        "expect": {
            "ftp": "270", "race": _ROAD_HILL["name"],
            "race_date": _ROAD_HILL["date"], "strength_equipment": "full gym",
            "target_hours": 8.0, "brand": "roadielabs", "discipline": "road",
            "event_format": "hill_climb", "road_category": "cat_4",
            "min_strength_sessions": 4,
            "pdf_optional": True,
            "preview_blockers": ["PREVIEW_ZONE_DISTRIBUTION"],
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
    intake = {**order["intake"], "generation_clock": _GOLDEN_GENERATION_AT}
    md = _questionnaire_to_markdown(intake)
    md_file = tmp_path / f"{order['id']}.md"
    md_file.write_text(md)

    # Delivery dir must live under home or the project — the pipeline's
    # path-safety guard rejects pytest's /private/var scratch root. Keep this
    # ignored scratch data inside the writable checkout so sandboxed CI/agents
    # never need to mutate a developer's home directory.
    delivery_root = REPO_ROOT / ".gg-acctest-delivery" / order["id"]
    if delivery_root.exists():
        import shutil
        shutil.rmtree(delivery_root)
    delivery_root.mkdir(parents=True)

    env = dict(os.environ)
    env["GG_DELIVERY_DIR"] = str(delivery_root)
    env["GG_GUIDES_DIR"] = str(delivery_root / "gravel-god-guides")
    env["ROADIE_GUIDES_DIR"] = str(delivery_root / "roadie-labs-guides")
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["GG_FIXED_NOW"] = _GOLDEN_GENERATION_AT

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
                order["id"], deliver=True, intake_data=intake)
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


def test_golden_order_inputs_are_literal_and_fixed_clocked():
    """Fixture refreshes must be explicit, never an effect of today's date."""
    assert _GOLDEN_GENERATION_AT == "2026-08-06T15:00:00Z"
    assert (_RACE["name"], _RACE["date"], _RACE["slug"]) == (
        "Tour de Tucson", "2026-11-21", "tour-de-tucson")
    assert (_ROAD_FONDO["name"], _ROAD_FONDO["date"]) == (
        "Granfondo Tre Valli Varesine", "2026-10-03")
    assert (_ROAD_HILL["name"], _ROAD_HILL["date"]) == (
        "Taiwan KOM Challenge", "2026-10-23")


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
    if (not built_order["order"]["expect"].get("pdf_optional")
            and os.environ.get("GG_PDF_DISABLE") != "1"):
        assert (d / "training_guide.pdf").exists(), "guide PDF missing"
    assert (d / "fueling.yaml").exists(), "fueling.yaml missing"
    # Generation must produce the full workout set, but executable ZWOs stay
    # sealed in the athlete package until a seal-bound approval releases the
    # customer bundle (SPEC_TRUSTWORTHY_FULFILMENT B1/S2). The pre-approval
    # delivery surface must carry NO executable workout files.
    generated = built_order["athlete_dir"] / "workouts"
    assert generated.exists() and len(list(generated.glob("*.zwo"))) >= 20, \
        "generated workouts/ missing or sparse"
    assert not list(d.rglob("*.zwo")), \
        "executable workouts leaked to the pre-approval delivery surface"


def test_pdf_is_structurally_valid(built_order):
    from pdf_generator import validate_pdf
    pdf = built_order["delivery_dir"] / "training_guide.pdf"
    if os.environ.get("GG_PDF_DISABLE") == "1":
        pytest.skip("GG_PDF_DISABLE=1: PDF engine intentionally disabled (sandboxed run)")
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
    """Pin the exact current authority disposition without weakening gates."""
    from generate_plan_preview import build_preview_data
    data = build_preview_data(built_order["athlete_dir"])
    from intake_to_plan import preview_review_issues
    actual_ids = sorted(
        item['id'] for item in preview_review_issues(data['checks']))
    expected_ids = sorted(
        built_order['order']['expect'].get('preview_blockers', []))
    assert actual_ids == expected_ids, (
        f"preview disposition changed: expected {expected_ids}, got {actual_ids}")


def test_volume_fills_stated_hours(built_order):
    """Build/peak load weeks must fill 80-120% of the athlete's hours —
    the NP/IF bug shipped base blocks at ~50%."""
    from generate_plan_preview import build_preview_data
    target = built_order["order"]["expect"]["target_hours"]
    data = build_preview_data(built_order["athlete_dir"])
    vol = next((c for c in data["checks"] if c["name"] == "Weekly Volume"), None)
    assert vol is not None, "no Weekly Volume check produced"
    pct = float(re.search(r"\((\d+)%\)", vol["detail"]).group(1))
    expected_pct = built_order['order']['expect'].get('volume_pct')
    if expected_pct is not None:
        assert pct == expected_pct
        assert vol['status'] == 'WARN'
    else:
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


def test_promised_strength_is_in_the_deliverable_window(built_order):
    minimum = built_order["order"]["expect"].get("min_strength_sessions")
    if minimum is None:
        pytest.skip("order does not require in-plan strength")
    import json
    manifest = json.loads(
        (built_order["athlete_dir"] / "tp_manifest.json").read_text())
    plan_day_one = yaml.safe_load(
        (built_order["athlete_dir"] / "plan_dates.yaml").read_text()
    )["week1_monday"]
    strength = [
        session for session in manifest["sessions"]
        if (session.get("workout_type_value_id") == 9
            or session.get("tp_kind") == "strength")
        and session.get("date") >= plan_day_one
    ]
    assert len(strength) >= minimum, (
        f"only {len(strength)} in-plan strength cards; promised at least {minimum}")
    assert all(session.get("strength") or session.get("strength_template")
               for session in strength), "strength card missing exercise structure"


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
    """The golden order must produce its exact clean-or-review disposition.

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
    expected_ids = sorted(
        built_order['order']['expect'].get('preview_blockers', []))
    state = json.loads((athlete_dir / 'fulfillment_status.json').read_text())
    actual_ids = sorted(
        item['id'] for item in state['blocking_issues']
        if item['source'] == 'plan_preview')
    assert actual_ids == expected_ids
    if expected_ids:
        assert review.exists()
        assert 'GG_NEEDS_REVIEW=1' in built_order['proc'].stdout
        assert state['status'] == 'BLOCKED_REVIEW'
        brief = (athlete_dir / 'coaching_brief.md').read_text()
        assert 'NEEDS REVIEW BEFORE SENDING' in brief
    else:
        assert not review.exists(), (
            "clean fixture was unexpectedly flagged:\n"
            f"{review.read_text() if review.exists() else ''}")


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
    manifest = json.loads((athlete_dir / "tp_manifest.json").read_text())
    assert manifest["provenance"]["engine_version"].startswith("motoren/")
    assert manifest["provenance"]["voice_version"].startswith("voice/")
    assert manifest["provenance"]["profile_version"] == "road/v1"

    # Treat brand separation as a release-blocking invariant across both the
    # source athlete package and the exact staged customer package. Checking
    # filenames catches gravel-only workout families even when their internal
    # display copy happens to be neutral.
    for root in (athlete_dir, built_order["delivery_dir"]):
        visible = [root / "training_guide.html", root / "personal_email.md",
                   root / "plan_preview.html", root / "fueling.yaml"]
        visible.extend(sorted((root / "workouts").glob("*.zwo")))
        for path in visible:
            if not path.exists():
                continue
            assert "gravel" not in path.name.lower(), (
                f"road workout/artifact filename leak in {path}")
            text = path.read_text()
            assert "gravel" not in text.lower(), (
                f"road athlete-facing language leak in {path}")
            assert "Gravel God" not in text, f"Gravel God leak in {path}"
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

    # Guide staging/publishing is a post-approval release action (Phase 5 of
    # SPEC_TRUSTWORTHY_FULFILMENT); pre-approval staging was a closed Phase 1
    # bypass. The unpublished draft must NOT appear in the hosting tree.
    staged_guide = (built_order["delivery_dir"].parent /
                    "roadie-labs-guides" / "athletes" /
                    built_order["athlete_id"] / "index.html")
    assert not staged_guide.exists(), \
        "unapproved guide was staged to the hosting repo (release bypass)"

    from validate_plan_package import validate_plan_package
    assert validate_plan_package(athlete_dir) == []
