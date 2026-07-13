"""
Step 7: Generate HTML Training Guide

Builds the training guide programmatically (no {{placeholder}} substitution).
Every section is generated from athlete data + race data. No AI at runtime.

This is THE product. 14 sections minimum. 50KB+ output.
Brand system: Gravel God desert editorial palette, two-voice typography
(Source Serif 4 editorial + Sometype Mono data), two-column layout with sticky TOC.
"""

import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


# ── Race duration estimation ─────────────────────────────────

# Average gravel speeds (mph) by tier — accounts for rest stops, navigation, terrain
_TIER_AVG_SPEED = {
    "time_crunched": 12.0,
    "finisher": 13.5,
    "compete": 15.5,
    "podium": 17.0,
}



def _race_display(race_name, race_distance) -> str:
    """Race name with distance appended ONLY when not already in the name
    (prevents "Unbound Gravel 200 200mi")."""
    name = str(race_name or "").strip()
    if not race_distance:
        return name
    if str(race_distance) in name:
        return name
    return f"{name} {race_distance}mi"

def _get_phase_boundaries(plan_duration: int) -> Dict:
    """Return phase boundaries for any plan duration.

    Used in training calendar, week-by-week table, and phase progression
    to ensure consistent phase labels everywhere.

    Returns dict with phase name → (start_week, end_week) inclusive.

    Formula: ~50% base, ~30% build, ~10% peak, ~10% taper (minimum 1 week each for peak/taper).
    """
    if plan_duration <= 8:
        return {
            "base": (1, max(1, plan_duration - 4)),
            "build": (max(2, plan_duration - 3), max(3, plan_duration - 2)),
            "peak": (max(4, plan_duration - 1), max(4, plan_duration - 1)),
            "taper": (plan_duration, plan_duration),
        }

    # For plans 9+ weeks: compute proportional boundaries
    taper_weeks = 2
    peak_weeks = 2
    remaining = plan_duration - taper_weeks - peak_weeks
    # Base gets ~60% of remaining, build gets ~40%
    base_weeks = round(remaining * 0.6)
    build_weeks = remaining - base_weeks

    base_end = base_weeks
    build_end = base_end + build_weeks
    peak_end = build_end + peak_weeks
    # taper_end = plan_duration

    return {
        "base": (1, base_end),
        "build": (base_end + 1, build_end),
        "peak": (build_end + 1, peak_end),
        "taper": (peak_end + 1, plan_duration),
    }


def _week_to_date(plan_start_date: str, week_num: int) -> date:
    """Return the first day of a given plan week (1-indexed).

    Week 1 starts on plan_start_date (whatever day of the week that is).
    """
    start = datetime.strptime(plan_start_date, "%Y-%m-%d").date()
    return start + timedelta(weeks=week_num - 1)


def _phase_date_range(plan_start_date: str, week_start: int, week_end: int) -> str:
    """Return 'Mon D - Mon D' date range string for a phase span."""
    d1 = _week_to_date(plan_start_date, week_start)
    # End date is 6 days after the start of the last week
    d2 = _week_to_date(plan_start_date, week_end) + timedelta(days=6)
    return f"{d1.strftime('%b %-d')} &ndash; {d2.strftime('%b %-d')}"


# Focus texts that imply a specific phase — used to detect conflicts
_PHASE_IMPLYING_FOCUS = {
    "build": ["Build Phase Begins", "Intensity Progression", "Peak Build Volume"],
    "peak": ["Peak Phase", "Race Specificity", "Final Quality"],
    "taper": ["Taper Week", "Race Week"],
}

# Replacement focus texts when the original conflicts with the computed phase
_PHASE_FOCUS_OVERRIDES = {
    # Original focus → replacement when it appears in a different phase
    "Build Phase Begins": "Progressive Volume",
    "Intensity Progression": "Volume Progression",
    "Peak Build Volume": "Peak Base Volume",
}


def _sanitize_focus_for_phase(focus: str, phase_type: str) -> str:
    """Override focus text that implies a different phase than the computed one."""
    for implied_phase, keywords in _PHASE_IMPLYING_FOCUS.items():
        if implied_phase != phase_type:
            for keyword in keywords:
                if keyword in focus:
                    return _PHASE_FOCUS_OVERRIDES.get(focus, focus.replace(keyword, keyword.replace("Build", "Base")))
    return focus


def _week_phase(wnum: int, plan_duration: int) -> tuple:
    """Return (phase_label, phase_type) for a given week number."""
    boundaries = _get_phase_boundaries(plan_duration)
    if wnum == plan_duration:
        return ("Race Week", "race")
    for phase_type, (start, end) in boundaries.items():
        if start <= wnum <= end:
            label = phase_type.upper() if phase_type != "race" else "Race Week"
            return (label, phase_type)
    return ("TAPER", "taper")


def _estimate_race_hours(distance_miles: float, elevation_ft: float, tier: str) -> float:
    """Estimate race duration from distance, elevation, and athlete tier.

    Uses tier-specific average speed + elevation penalty.
    Returns estimated hours (e.g., 8.5).
    """
    speed = _TIER_AVG_SPEED.get(tier, 13.5)
    base_hours = distance_miles / speed
    # Elevation penalty: ~18min per 1000ft of climbing
    elev_penalty = (elevation_ft / 1000) * 0.3
    return round(base_hours + elev_penalty, 1)


# ── Required guide sections (Gate 7 checks for these) ────────

# "non-negotiables" and "week-by-week overview" were REMOVED per coach
# review (Jun 2026) — do not re-add. Schedule content lives in the plan.
# Brand per discipline — a road athlete must not get a "GRAVEL GOD" footer
# or a gravel-cornering chapter. (Full Roadie Labs design-token/font port is
# a separate task; this fixes the visible brand + the discipline-specific
# skills chapter so the deliverable is correct for the athlete's sport.)
BRANDS = {
    "gravel": {"logo": "GRAVEL GOD", "tagline": "Custom training plans for gravel racing",
               "skills_title": "Gravel Skills"},
    "mtb": {"logo": "GRAVEL GOD", "tagline": "Custom training plans for off-road racing",
            "skills_title": "Mountain Bike Skills"},
    "road": {"logo": "ROADIE LABS", "tagline": "Custom training plans for road racing",
             "skills_title": "Road Skills"},
}


def _brand(discipline):
    return BRANDS.get((discipline or "gravel").lower(), BRANDS["gravel"])


REQUIRED_SECTIONS = [
    "training plan brief",
    "training zones",
    "how adaptation works",
    "weekly structure",
    "phase progression",
    "workout execution",
    "recovery protocol",
    "equipment checklist",
    "nutrition strategy",
    "mental preparation",
    "race week",
    "race day",
]

# Tier → methodology mapping (deterministic, no AI)
TIER_METHODOLOGY = {
    "time_crunched": {
        "name": "HIIT-Focused",
        "description": "Maximum adaptation from minimum hours. High-intensity interval training creates the largest fitness gains per hour invested.",
        "intensity": [("Z1-Z2 (Easy Aerobic)", "30%", "Aerobic base, fat adaptation, durability"),
                      ("Z3 (Tempo)", "20%", "Muscular endurance, sustained power"),
                      ("Z4-Z5 (Threshold+)", "50%", "FTP development, VO2max, race sharpness")],
        "key_workouts": ["VO2max intervals (3-5 min hard efforts)", "Tabata-style intervals", "G Spot over-unders", "Sprint repeats"],
        "progression": "Increase intensity, not volume. You don't have the hours for volume — make every session count.",
    },
    "finisher": {
        "name": "Traditional Pyramidal",
        "description": "The proven approach for mid-volume athletes. Large aerobic base with targeted high-intensity work. Builds durability for long race days.",
        "intensity": [("Z1-Z2 (Easy Aerobic)", "70%", "Aerobic base, fat adaptation, durability"),
                      ("Z3 (Tempo)", "15%", "Muscular endurance, sustained power"),
                      ("Z4-Z5 (Threshold+)", "15%", "FTP development, VO2max, race sharpness")],
        "key_workouts": ["Progressive long rides ({long_ride_target})", "G Spot intervals (2x20, 3x15)", "Tempo efforts on climbs", "Race-simulation rides"],
        "progression": "Build volume through base, then layer in intensity. Long rides are your most important session.",
    },
    "compete": {
        "name": "Polarized",
        "description": "Proven approach for high-volume athletes: go very easy or very hard, nothing in between. Maximizes adaptation while managing fatigue.",
        "intensity": [("Z1-Z2 (Easy Aerobic)", "80%", "Aerobic base, fat adaptation, durability"),
                      ("Z3 (Tempo)", "5%", "Used sparingly for race-specific pacing"),
                      ("Z4-Z5 (Threshold+)", "15%", "Targeted high-intensity for race sharpness")],
        "key_workouts": ["Long endurance rides (5-7 hours)", "VO2max intervals (4-6 min)", "Threshold over-unders", "Race-pace group rides"],
        "progression": "Volume is your engine. Intensity sharpens it. Don't sacrifice volume for more intervals.",
    },
    "podium": {
        "name": "High-Volume Polarized",
        "description": "Maximum training load for athletes who can handle it. Very high aerobic volume with surgical intensity. This is how professionals train.",
        "intensity": [("Z1-Z2 (Easy Aerobic)", "85%", "Massive aerobic engine, fat adaptation, durability"),
                      ("Z3 (Tempo)", "5%", "Race-specific pacing only"),
                      ("Z4-Z5 (Threshold+)", "10%", "Targeted high-intensity for race sharpness")],
        "key_workouts": ["Massive long rides (6-8+ hours)", "Back-to-back long days", "Race-simulation blocks", "VO2max intervals (5-8 min)"],
        "progression": "Volume volume volume. You have the hours — use them. Intensity is the seasoning, not the meal.",
    },
}

def _conditional_triggers(profile: Dict, race_data: Dict) -> Dict:
    """Single source of truth for which conditional sections fire.

    Returns dict with boolean keys: 'altitude', 'women', 'masters'.
    EVERY conditional check in the codebase MUST call this function.
    Duplicating this logic is a bug. See LESSONS_LEARNED.md Shortcut #9.
    """
    if not race_data:
        race_data = {}
    meta = race_data.get("race_metadata", {})
    # CRITICAL: race_data["elevation_feet"] is total CLIMBING (gain), not
    # altitude above sea level. Using it here once told an Unbound athlete
    # the race "takes place at 11,000 feet" (Emporia, KS sits at ~1,100).
    # Altitude fires ONLY on true above-sea-level signals.
    avg_elev = meta.get("avg_elevation_feet", 0) or 0
    start_elev = meta.get("start_elevation_feet", 0) or 0
    show_altitude = avg_elev > 5000 or start_elev > 5000

    sex = profile.get("demographics", {}).get("sex", "")
    show_women = bool(sex and sex.lower() == "female")

    # Masters gates on an explicit tier/persona signal first — e.g. a
    # pre-built "Masters" SKU intake carries profile['plan_tier'] == "Masters"
    # (or "Masters 50+"). This must win over age, because non-Masters base
    # intakes (Finisher/Time-Crunched/Save-My-Race "punchy" personas) share a
    # representative age of 40+ that used to trip an age>=40 gate regardless
    # of tier — the Finisher guide once shipped a "Masters Training
    # Considerations" section it had no business having. Falls back to age
    # >= 50 (matching the "Masters 50+" product name, not the old 40
    # threshold) only when no explicit plan_tier is present — e.g. a real
    # customer questionnaire, which has no notion of "plan_tier" at all and
    # where age is the only legitimate masters signal available.
    plan_tier = str(profile.get("plan_tier") or "").strip().lower()
    if plan_tier:
        show_masters = plan_tier.startswith("masters")
    else:
        age = profile.get("demographics", {}).get("age")
        show_masters = bool(age and int(age) >= 50)

    return {"altitude": show_altitude, "women": show_women, "masters": show_masters}


def _build_section_titles(profile: Dict, race_data: Dict):
    """Build section titles with sequential numbering (no ID gaps)."""
    try:
        from archetype import derive_discipline
        skills_title = _brand(derive_discipline(profile or {}))["skills_title"]
    except Exception:
        skills_title = "Gravel Skills"
    titles = [
        "Training Plan Brief",
        "Training Zones",
        "How Adaptation Works",
        "Weekly Structure",
        "Phase Progression",
        "Workout Execution",
        "Recovery Protocol",
        "Equipment Checklist",
        "Nutrition Strategy",
        "Mental Preparation",
        "Race Week",
        "Race Day",
        skills_title,
    ]

    triggers = _conditional_triggers(profile, race_data)
    if triggers["altitude"]:
        titles.append("Altitude Training")
    if triggers["women"]:
        titles.append("Women-Specific Considerations")
    if triggers["masters"]:
        titles.append("Masters Training Considerations")

    return [(f"section-{i+1}", title) for i, title in enumerate(titles)]


def generate_guide(
    profile: Dict,
    derived: Dict,
    plan_config: Dict,
    schedule: Dict,
    output_path: Path,
    base_dir: Path,
    store_mode: bool = False,
):
    """Generate a complete HTML training guide. Must be 50KB+.

    store_mode: True for marketplace/store SKU guides built from a generic
    base intake (no real athlete behind the numbers). Suppresses the
    personal YOUR PROFILE block (fake age/weight/FTP/height/years/hours)
    and reframes 1:1-questionnaire language. Real 1:1 customer guides
    (the default) are completely unaffected.
    """
    race_name = derived.get("race_name", "Your Race")
    race_distance = derived.get("race_distance_miles", "")
    tier = derived["tier"]
    level = derived["level"]
    plan_duration = plan_config["plan_duration"]
    athlete_name = profile["name"]

    # Load template if not already in plan_config (happens when regenerating from saved files)
    if "template" not in plan_config or not plan_config["template"]:
        from pipeline.step_05_template import select_template
        full_config = select_template(derived, base_dir)
        plan_config["template"] = full_config.get("template", {})
        if "ftp_test_weeks" not in plan_config:
            plan_config["ftp_test_weeks"] = full_config.get("ftp_test_weeks", [])

    # Load race data for guide content
    from pipeline.step_06_workouts import load_race_data

    race_data = load_race_data(race_name, race_distance, base_dir) if race_name else {}
    if race_data is None:
        race_data = {}

    # Cross-reference race date against the real race database (1,184-race
    # snapshot + curated known_races). The old import pulled from the gravel
    # repo's `pipeline` package, which isn't importable here — so date_xref
    # was always empty and EVERY race showed "not in database". Now local.
    race_date_str = derived.get("race_date", "")
    date_xref = _cross_reference_race_date(race_name, race_date_str) if race_name and race_date_str else {}

    html = _build_full_guide(
        athlete_name=athlete_name,
        race_name=race_name,
        race_distance=race_distance,
        tier=tier,
        level=level,
        plan_duration=plan_duration,
        profile=profile,
        derived=derived,
        schedule=schedule,
        plan_config=plan_config,
        race_data=race_data,
        date_xref=date_xref,
        store_mode=store_mode,
    )

    output_path.write_text(html, encoding="utf-8")


def _build_full_guide(
    athlete_name: str,
    race_name: str,
    race_distance,
    tier: str,
    level: str,
    plan_duration: int,
    profile: Dict,
    derived: Dict,
    schedule: Dict,
    plan_config: Dict,
    race_data: Dict,
    date_xref: Dict = None,
    store_mode: bool = False,
) -> str:
    """Build the complete HTML document with all sections using Gravel God brand system."""

    tier_display = tier.replace("_", " ").title()
    level_display = level.title()
    ftp = profile["fitness"].get("ftp_watts")

    # store_mode: the honest persona label for a marketplace SKU is the
    # product's own plan_tier ("Finisher", "Masters", "Save My Race"...),
    # not the internally-derived tier (which can disagree with the SKU
    # name) and never the fake base-intake "name" (e.g. "Finisher Gravel
    # Punchy") — that's a tier label wearing a person's name.
    persona_label = (profile.get("plan_tier") or tier_display) if store_mode else None

    # Brand by discipline — a road athlete gets ROADIE LABS + road skills,
    # never a GRAVEL GOD footer or gravel-cornering drills.
    try:
        from archetype import derive_discipline
        _discipline = derive_discipline(profile or {})
    except Exception:
        _discipline = "gravel"
    brand = _brand(_discipline)

    # Note: redundant "200 200mi" cleaned up in post-processing by generate_training_guide()
    template = plan_config.get("template", {})
    sched = profile.get("schedule", {})
    weekly_hours = sched.get("weekly_hours", derived.get("weekly_hours", ""))

    # Race data
    race_chars = race_data.get("race_characteristics", {})
    meta = race_data.get("race_metadata", {})
    location = meta.get("location", "")
    elevation = race_data.get("elevation_feet", meta.get("elevation_feet", ""))
    # store_mode + vitals.gain_display: some races' total climbing gain is
    # unverified or only a partial (named-climbs) sum — gain_display
    # overrides the numeric elevation_ft ONLY for the cover badge (see
    # _meta_badges). The numeric elevation above is untouched and keeps
    # feeding internal estimates (ride-hours, altitude trigger) as before.
    # Athlete (1:1) mode never honors this override.
    gain_display = race_data.get("gain_display") if store_mode else None
    mods = race_data.get("workout_modifications", {})
    non_negs = race_data.get("non_negotiables", {})
    race_specific = race_data.get("race_specific", {})

    # Ride realism index — drives all long ride target language
    _, max_weekly = _parse_hours_range(weekly_hours)
    elev_ft = float(elevation) if elevation else 0
    est_race_hrs = _estimate_race_hours(float(race_distance), elev_ft, tier) if race_distance else 0
    lr_ceiling = max_weekly * 0.4 if max_weekly > 0 else 0
    ride_realism = (lr_ceiling / est_race_hrs) if est_race_hrs > 0 else 1.0

    # Build all sections
    sections = []

    # store_mode: no real athlete behind these numbers — never show a fake
    # FTP as if it were a real test result. Zones/execution degrade to the
    # same "%FTP + test in Week 1" path a real customer sees before testing.
    effective_ftp = None if store_mode else ftp

    # 1. Training Plan Brief (hardcoded from questionnaire)
    sections.append(_section_training_plan_brief(
        athlete_name, race_name, race_distance, tier, tier_display,
        level_display, plan_duration, profile, derived, schedule, plan_config,
        date_xref=date_xref or {}, store_mode=store_mode,
    ))

    # Race Profile section REMOVED per coach review (Jun 2026) — it mostly
    # restated the cover badges and rendered default-built radar charts.
    # The date-verification card moved into section 1.

    # 3-14. Core sections.
    # REMOVED per coach review (Jun 2026): Non-Negotiables (pointless),
    # Week-by-Week Overview (the schedule lives in the training plan, not
    # the guide). Do not re-add calendar/schedule content to the guide.
    _fit = profile.get("fitness", {})
    sections.append(_section_training_zones(
        effective_ftp, tier, lthr=_fit.get("lthr"), max_hr=_fit.get("max_hr")))
    sections.append(_section_adaptation())
    sections.append(_section_weekly_structure(schedule, tier_display, weekly_hours, est_race_hrs))
    sections.append(_section_phase_progression(plan_duration, tier, ride_realism))
    sections.append(_section_workout_execution(tier, effective_ftp))
    sections.append(_section_recovery_protocol(tier, profile, store_mode=store_mode))
    sections.append(_section_equipment_checklist(profile, race_data))
    sections.append(_section_nutrition(race_data, tier, race_distance, profile, plan_duration, store_mode=store_mode))
    sections.append(_section_mental_preparation(race_data, race_distance, tier))
    sections.append(_section_race_week(race_data, tier, race_name, derived))
    sections.append(_section_race_day(race_data, tier, race_distance, race_name, weekly_hours))
    sections.append(_section_skills(race_data, _discipline))

    # Conditional sections — uses shared trigger logic (no duplication)
    triggers = _conditional_triggers(profile, race_data)
    next_section = 14  # first conditional is always after section 13
    if triggers["altitude"]:
        sections.append(_section_altitude_training(race_data, race_name, elevation, section_num=next_section))
        next_section += 1
    if triggers["women"]:
        sections.append(_section_women_specific(profile, race_data, race_name, section_num=next_section))
        next_section += 1
    if triggers["masters"]:
        sections.append(_section_masters_training(profile, derived, section_num=next_section))

    body = "\n\n".join(sections)

    # Build TOC dynamically
    section_titles = _build_section_titles(profile, race_data)
    toc_items = []
    for sid, title in section_titles:
        toc_items.append(f'          <li><a href="#{sid}">{title}</a></li>')
    toc_html = "\n".join(toc_items)

    # Duration estimate
    duration_est = race_data.get("duration_estimate", "")

    # store_mode: the <title> and <h1> must never present the fake base-
    # intake "name" as if it belonged to the buyer. Title by tier/persona
    # instead of by (fake) athlete name.
    page_title = (f"The {persona_label} Plan - {_race_display(race_name, race_distance)} Training Guide"
                  if store_mode else
                  f"{athlete_name} - {_race_display(race_name, race_distance)} Training Guide")
    page_h1 = (f"{_race_display(race_name, race_distance)} &ndash; The {persona_label} Plan ({plan_duration} weeks)"
               if store_mode else
               f"{_race_display(race_name, race_distance)} &ndash; Custom Plan for {athlete_name} ({plan_duration} weeks)")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>

    <!-- Fonts: Source Serif 4 (editorial) + Sometype Mono (data) -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Sometype+Mono:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet" />

    {_css(_discipline)}
</head>
<body>
  <main class="gg-guide-page">
    <div class="gg-guide-layout">

      <header class="guide-header">
        <h1>{page_h1}</h1>
        <div class="guide-meta">
{_meta_badges(race_name, race_distance, elevation, duration_est, plan_duration, location, gain_display=gain_display)}
        </div>
      </header>

      <nav class="gg-guide-toc">
        <h2>Contents</h2>
        <ol>
{toc_html}
        </ol>
      </nav>

      <div class="gg-guide-content">

{body}

      </div>

      <footer class="guide-footer">
        <div class="footer-logo">{brand['logo']}</div>
        <div class="footer-tagline">{brand['tagline']}</div>
        <p style="margin-top: 8px; font-family: var(--gg-font-data); font-size: 12px; color: var(--gg-color-secondary-brown);">
          {plan_duration} Weeks &middot; ENDURE Plan Engine
        </p>
      </footer>

    </div>
  </main>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ══════════════════════════════════════════════════════════════

def _section_training_plan_brief(
    athlete_name, race_name, race_distance, tier, tier_display,
    level_display, plan_duration, profile, derived, schedule, plan_config,
    date_xref=None, store_mode=False,
):
    """Section 1: Hardcoded athlete-specific overview from questionnaire data.

    store_mode: suppresses the personal YOUR PROFILE block (fake age/weight/
    FTP/height/years/hours from a generic base intake) and reframes
    1:1-questionnaire language for marketplace/store SKU guides.
    """
    persona_label = (profile.get("plan_tier") or tier_display) if store_mode else None
    demo = profile.get("demographics", {})
    fitness = profile.get("fitness", {})
    sched = profile.get("schedule", {})
    strength = profile.get("strength", {})
    # equipment can live in two profile shapes — prefer the explicit
    # strength_equipment list ("full-gym" printed as "bodyweight" once)
    _strength_equip_list = profile.get("strength_equipment") or []
    if _strength_equip_list and not strength.get("equipment"):
        strength = dict(strength)
        strength["equipment"] = ", ".join(
            str(e).replace("-", " ") for e in _strength_equip_list)
    health = profile.get("health", {})
    history = profile.get("training_history", {})

    age = demo.get("age", "")
    sex = demo.get("sex", "")
    weight_lbs = demo.get("weight_lbs", "")
    weight_kg = round(float(weight_lbs) / 2.205, 1) if weight_lbs else ""
    height_ft = demo.get("height_ft", "")
    height_in = demo.get("height_in", "")
    height_str = f"{height_ft}'{height_in}\"" if height_ft else ""

    weekly_hours = sched.get("weekly_hours", derived.get("weekly_hours", ""))
    years = history.get("years_cycling", "")
    ftp = fitness.get("ftp_watts")
    longest_ride = fitness.get("longest_ride_hours", "")
    trainer = profile.get("equipment", {}).get("trainer_type", "")
    sleep = health.get("sleep_quality", "")
    stress = health.get("stress_level", "")
    injuries = health.get("injuries_limitations", "")

    # Off/long/interval days
    off_days = sched.get("off_days", [])
    long_days = sched.get("long_ride_days", [])
    interval_days = sched.get("interval_days", [])
    strength_include = strength.get("include_in_plan", "")

    # Methodology
    meth = dict(TIER_METHODOLOGY.get(tier, TIER_METHODOLOGY["finisher"]))
    # Prefer the ACTUALLY-SELECTED methodology over the tier default so the
    # guide never contradicts the plan (the judge's top recurring finding).
    _meth_real = derived.get("_methodology_display") or {}
    if _meth_real.get("name"):
        meth.update({k: _meth_real[k] for k in ("name", "description", "progression")
                     if _meth_real.get(k)})

    # Compute long ride target text based on ride realism index
    race_dist = derived.get("race_distance_miles", 0)
    race_elev = derived.get("elevation_feet", 0) or 0
    est_race_hrs = _estimate_race_hours(race_dist, race_elev, tier) if race_dist else 0
    _, max_hrs = _parse_hours_range(weekly_hours)
    # Rough long ride ceiling: ~40% of weekly budget (2 long rides in a 6-session week)
    lr_ceiling = max_hrs * 0.4 if max_hrs > 0 else 0
    ride_realism = (lr_ceiling / est_race_hrs) if est_race_hrs > 0 else 1.0

    if ride_realism >= 0.6:
        long_ride_target = "building to 70-80% of race duration"
    elif ride_realism >= 0.3:
        ceiling_str = f"{lr_ceiling:.0f}"
        long_ride_target = (
            f"building to {ceiling_str}+ hours — compensate with race-specific "
            f"intensity and nutrition rehearsal"
        )
    else:
        long_ride_target = (
            "maximizing time in saddle; intensity quality and nutrition "
            "rehearsal compensate for volume"
        )

    # Training calendar with actual dates — uses plan_start_date from derived (single source of truth)
    plan_start_str = derived.get("plan_start_date", "")
    race_date_str = derived.get("race_date", "")
    calendar_html = ""
    if plan_start_str and race_date_str:
        try:
            race_date = datetime.strptime(str(race_date_str), "%Y-%m-%d")

            cal_rows = []
            for w in range(1, plan_duration + 1):
                week_start = _week_to_date(plan_start_str, w)
                week_end = week_start + timedelta(days=6)

                phase, phase_type = _week_phase(w, plan_duration)

                row_class = ' class="race-day-row"' if w == plan_duration else ""
                cal_rows.append(
                    f'<tr{row_class}><td>W{w:02d}</td>'
                    f'<td>{week_start.strftime("%Y-%m-%d")} - {week_end.strftime("%Y-%m-%d")}</td>'
                    f'<td><span class="phase-indicator phase-indicator--{phase_type}">{phase}</span></td></tr>'
                )

            plan_start_dt = datetime.strptime(plan_start_str, "%Y-%m-%d")
            last_week_start = _week_to_date(plan_start_str, plan_duration)
            start_day_name = plan_start_dt.strftime("%A")
            # Add mid-week start note if the plan doesn't start on Monday
            midweek_note = ""
            if plan_start_dt.weekday() != 0:  # 0 = Monday
                start_date_formatted = plan_start_dt.strftime("%B %-d, %Y")
                midweek_note = (
                    f'\n  <div class="gg-module gg-tactical"><div class="gg-label">YOUR PLAN STARTS ON A {start_day_name.upper()}</div>'
                    f"<p>Week 1 begins {start_day_name}, {start_date_formatted}. Follow your normal weekly template "
                    f"(Monday = Strength, Tuesday = Intervals, etc.) for whatever days remain in this first week. "
                    f"Look at the {start_day_name} slot in your weekly structure "
                    f"and start there. The first full Monday-to-Sunday cycle begins the following week.</p></div>"
                )
            calendar_html = f"""
  <h3>Your Training Calendar</h3>
  <p>Your {plan_duration}-week plan starts <strong>{plan_start_dt.strftime("%Y-%m-%d")} ({start_day_name})</strong> and ends race week
  <strong>{last_week_start.strftime("%Y-%m-%d")}</strong>.
  Race day is <strong>{race_date.strftime("%Y-%m-%d (%A)")}</strong>.</p>
  {midweek_note}
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Week</th><th>Dates</th><th>Phase</th></tr></thead>
  <tbody>
  {"".join(cal_rows)}
  </tbody>
  </table>
  </div>

  <h4>Workout File Naming</h4>
  <p>Your workout files follow this naming convention: <code>W{{week}}_{{daynum}}{{day}}_{{date}}_{{name}}.zwo</code></p>
  <p>Example: <code>W01_1Mon_Feb14_Endurance.zwo</code> = Week 1, Monday Feb 14, Endurance ride.
  Files sort chronologically &mdash; drag and drop in order to your TrainingPeaks calendar.</p>"""
        except (ValueError, TypeError):
            calendar_html = ""

    # Day-by-day schedule table removed per coach review (Jun 2026) — the
    # plan calendar owns the schedule; the brief shows only the shape
    days_info = schedule.get("days", {})
    date_card = _date_verification_card(derived, date_xref or {}, store_mode=store_mode)

    if store_mode:
        # No real athlete behind these numbers — a store buyer never filled
        # a questionnaire, so nothing here may claim personalization. The
        # fake age/weight/height/years/hours/FTP are suppressed entirely
        # (never shown as if they belonged to the buyer) and replaced with
        # an honest tier/persona description built from real plan config.
        _goal_description = (profile.get("target_race", {}).get("goal_description")
                             or f"Finish {_race_display(race_name, race_distance)} strong and healthy.")
        intro_html = f"""<p>This is the <strong>{_race_display(race_name, race_distance)}</strong> training plan built for
  the <strong>{persona_label}</strong> tier. Every phase, workout, and recommendation is calibrated
  to the demands of this race and this tier &mdash; set your own zones from your own FTP test and
  follow it exactly as written.</p>

  <h3>Built For</h3>
  <div class="data-card">
    <div class="data-card__header">THE {persona_label.upper()} ATHLETE</div>
    <div class="data-card__content">
      <p>{_goal_description}</p>
      <p>This {plan_duration}-week plan is structured for the {persona_label} tier &mdash; {meth['name']}
      training, scaled to this tier's typical availability and this race's demands.</p>
    </div>
  </div>"""

        methodology_reasons_html = f"""<h4>Why This Methodology Fits This Tier</h4>
      <ul>
        <li><strong>{meth['name']}</strong> is the proven approach for the {persona_label} tier</li>
        <li>{level_display}-level training distribution, built around this race's demands</li>
      </ul>"""

        health_notes_html = ""  # fake sleep/stress/injuries never shown as the buyer's own

        performance_html = f"""<p>Over {plan_duration} weeks, this plan builds race-specific fitness for the
  {persona_label} tier using the {meth['name']} approach. Execute consistently, fuel properly,
  and trust the process.</p>"""
    else:
        intro_html = f"""<p>Welcome to your <strong>{_race_display(race_name, race_distance)}</strong> training plan. This guide is built
  entirely from your questionnaire responses. Every number, every schedule, every recommendation
  is calibrated to your specific situation.</p>

  <h3>Your Profile</h3>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-card__value">{age}</div>
      <div class="stat-card__label">Age</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">{weight_lbs} lbs</div>
      <div class="stat-card__label">Weight ({weight_kg} kg)</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">{height_str}</div>
      <div class="stat-card__label">Height</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">{weekly_hours}h</div>
      <div class="stat-card__label">Weekly Hours</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">{years}</div>
      <div class="stat-card__label">Years Riding</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">{ftp if ftp else 'TBD'}{'W' if ftp else ''}</div>
      <div class="stat-card__label">FTP{' (test in Week 1)' if not ftp else ''}</div>
    </div>
  </div>"""

        methodology_reasons_html = f"""<h4>Why This Methodology Was Selected</h4>
      <ul>
        <li><strong>{weekly_hours} hours/week</strong> matches the {meth['name']} approach</li>
        <li><strong>{years} years</strong> of cycling experience at <strong>{level_display}</strong> level</li>
        <li><strong>{meth['name']}</strong> training distribution (based on your available hours)</li>
      </ul>"""

        health_notes_html = (
            f'<div class="gg-module gg-info"><div class="gg-label">HEALTH NOTES</div>'
            f'<p><strong>Sleep:</strong> {sleep} &mdash; <strong>Stress:</strong> {stress}'
            f'{f" &mdash; <strong>Injuries/Limitations:</strong> {injuries}" if injuries and injuries.lower() not in ("na", "none", "n/a", "") else ""}</p></div>'
        ) if sleep or stress else ""

        performance_html = f"""<p>With {weekly_hours} hours per week over {plan_duration} weeks, you're building race-specific fitness
  using the {meth['name']} approach. This plan is calibrated to your available time and experience level.
  Execute consistently, fuel properly, and trust the process.</p>"""

    return f"""<section id="section-1" class="gg-section">
  <h2>1 &middot; Training Plan Brief</h2>

  {intro_html}

{date_card}

  <div class="data-card">
    <div class="data-card__header">YOUR WEEK, AT A GLANCE</div>
    <div class="data-card__content">
      <p><strong>Off days:</strong> {', '.join(d.title() for d in off_days) if off_days else 'None specified'} &mdash;
      <strong>Long rides:</strong> {', '.join(d.title() for d in long_days) if long_days else 'Weekends'} &mdash;
      <strong>Intervals:</strong> {', '.join(d.title() for d in interval_days) if interval_days else 'Mid-week'}</p>
      {f'<p><strong>Strength training:</strong> Included ({strength.get("equipment", "bodyweight")})</p>' if strength_include and strength_include.lower() == "yes" else ''}
      {f'<p><strong>Indoor trainer:</strong> Available ({trainer})</p>' if trainer and trainer != "no" else ''}
      <p>The day-by-day schedule lives in your training calendar &mdash; that is the source of truth.</p>
    </div>
  </div>

  <h3>What Makes This Plan Different</h3>

  <div class="data-card">
    <div class="data-card__header">YOUR TRAINING METHODOLOGY: {meth['name'].upper()}</div>
    <div class="data-card__content">
      <p>{meth['description']}</p>

      {methodology_reasons_html}
    </div>
  </div>

  <h3>Progression Style</h3>
  <p>{meth['progression']}</p>

  {calendar_html}

  {health_notes_html}

  <h3>Performance Expectations</h3>
  {performance_html}
</section>"""


def _date_verification_card(derived, date_xref, store_mode: bool = False) -> str:
    """Race-date verification card — lives in section 1 since the Race
    Profile section was removed per coach review (Jun 2026). A wrong
    race date wrecks the taper; this stays.

    store_mode: no real athlete filled a questionnaire, so the QC
    "Date mismatch" warning (which compares a generic base-intake plan date
    against race-data's recorded date) is an internal authoring signal, not
    a real discrepancy the buyer needs to see — suppress it entirely. Also
    drop the "N days from today" countdown, which goes stale the day after
    the guide is generated; show the plan's target race date plainly instead.
    """
    # Build race date verification callout
    date_verification_html = ""
    if derived:
        race_date_str = derived.get("race_date", "")
        if race_date_str:
            try:
                rd = datetime.strptime(str(race_date_str), "%Y-%m-%d")
                day_of_week = rd.strftime("%A")
                date_display = rd.strftime("%B %d, %Y")

                if store_mode:
                    date_verification_html = f"""
  <div class="data-card" style="margin-top: 16px;">
    <div class="data-card__header">RACE DAY</div>
    <div class="data-card__content">
      <p><strong>{day_of_week}, {date_display}</strong></p>
    </div>
  </div>"""
                    return date_verification_html

                days_until = (rd.date() - date.today()).days

                # Determine verification status
                xref = date_xref or {}
                if xref.get("date_match") is True:
                    verify_icon = "&#10003;"  # checkmark
                    verify_color = "#1A8A82"
                    verify_text = f"Verified against race database ({xref.get('date_specific', '')})"
                elif xref.get("date_match") is False:
                    verify_icon = "&#9888;"  # warning
                    verify_color = "#B7950B"
                    verify_text = (
                        f"Date mismatch: race database says \"{xref.get('date_specific', '')}\". "
                        f"Please verify your race date."
                    )
                elif xref.get("matched"):
                    verify_icon = "&#8505;"  # info
                    verify_color = "#8c7568"
                    verify_text = "Race found in database but date could not be cross-referenced"
                else:
                    verify_icon = "&#8505;"  # info
                    verify_color = "#8c7568"
                    verify_text = "Race not in database — please verify your date independently"

                date_verification_html = f"""
  <div class="data-card" style="border-left: 4px solid {'#22c55e' if xref.get('date_match') else '#f59e0b'}; margin-top: 16px;">
    <div class="data-card__header">RACE DATE VERIFICATION</div>
    <div class="data-card__content">
      <table>
        <tbody>
          <tr><td><strong>Race Date</strong></td><td>{day_of_week}, {date_display}</td></tr>
          <tr><td><strong>Countdown</strong></td><td>{days_until} days from today</td></tr>
          <tr><td style="white-space: nowrap;"><strong>Status</strong></td><td><span style="color: {verify_color};">{verify_icon} {verify_text}</span></td></tr>
        </tbody>
      </table>
      <p style="margin-top: 8px; font-size: 0.85em; color: #666;">
        <strong>Triple-check:</strong> Confirm this is the correct date by visiting the official race website.
        A wrong date means your entire taper and peak will be off.
      </p>
    </div>
  </div>"""
            except ValueError:
                pass

    return date_verification_html

def _hr_bpm_band(pct_str: str, lthr: int) -> str:
    """Convert a '% of LTHR' band ('69-83%', '< 68%', '> 106%') to a bpm band
    off the athlete's measured threshold HR."""
    s = pct_str.replace("%", "").strip()
    if not s or s.upper() == "N/A":
        return "&mdash;"
    try:
        if s.startswith("< "):
            return f"&lt; {round(int(s[2:]) * lthr / 100)} bpm"
        if s.startswith("> "):
            return f"&gt; {round(int(s[2:]) * lthr / 100)} bpm"
        if "-" in s:
            lo, hi = s.split("-")
            return f"{round(int(lo) * lthr / 100)}-{round(int(hi) * lthr / 100)} bpm"
    except ValueError:
        pass
    return "&mdash;"


def _section_training_zones(ftp: Optional[int], tier: str,
                            lthr: Optional[int] = None,
                            max_hr: Optional[int] = None):
    zone_data = [
        ("1", "Active Recovery", "< 55%", "< 68%", "1-2", "Very easy, conversational. You should feel like you're barely working."),
        ("2", "Endurance", "56-75%", "69-83%", "3-4", "Easy effort. You can speak in full sentences. The bulk of your riding lives here."),
        ("3", "Tempo", "76-87%", "84-94%", "5-6", "Moderate. You can speak in short phrases. Comfortably hard."),
        ("GS", "G Spot", "88-93%", "92-96%", "6-7", "The G Spot between tempo and threshold. Maximum training stimulus with manageable fatigue."),
        ("4", "Threshold", "94-105%", "95-105%", "7-8", "Hard. Few words only. This is your FTP &mdash; sustainable for about 1 hour all-out."),
        ("5", "VO2max", "106-120%", "> 106%", "9", "Very hard, can barely speak. 3-8 minute efforts."),
        ("6", "Anaerobic", "> 120%", "N/A", "10", "Maximum effort. 30 seconds to 2 minutes."),
    ]

    if ftp:
        power_rows = []
        prev_high_w = 0  # each zone's floor = previous zone's ceiling + 1
        for zone, name, pct, hr, rpe, feel in zone_data:
            pct_range = pct.replace("%", "").replace("< ", "0-").replace("> ", "")
            if "-" in pct_range:
                low, high = pct_range.split("-")
                high_w = int(ftp * int(high) / 100)
                # contiguous watts — no 1-watt gaps or overlaps between zones
                low_w = 0 if prev_high_w == 0 else prev_high_w + 1
                watts = f"{low_w}-{high_w}W"
                prev_high_w = high_w
            else:
                watts = f"> {prev_high_w + 1}W" if prev_high_w else f"> {int(ftp * 1.2)}W"
            ss_class = ' class="race-day-row"' if zone == "GS" else ""
            bpm_cell = f'<td>{_hr_bpm_band(hr, lthr)}</td>' if lthr else ''
            power_rows.append(
                f'<tr{ss_class}><td><strong>{zone}</strong></td><td>{name}</td>'
                f'<td>{watts}</td><td>{pct} FTP</td><td>{hr} LTHR</td>{bpm_cell}<td>{rpe}</td>'
                f'<td>{feel}</td></tr>'
            )
        power_note = f'<p><strong>Your FTP: {ftp}W</strong>. After any retest, update your zones everywhere &mdash; head unit, Zwift, and this chart.</p>'
    else:
        power_rows = []
        for zone, name, pct, hr, rpe, feel in zone_data:
            ss_class = ' class="race-day-row"' if zone == "GS" else ""
            bpm_cell = f'<td>{_hr_bpm_band(hr, lthr)}</td>' if lthr else ''
            power_rows.append(
                f'<tr{ss_class}><td><strong>{zone}</strong></td><td>{name}</td>'
                f'<td>&mdash;</td><td>{pct} FTP</td><td>{hr} LTHR</td>{bpm_cell}<td>{rpe}</td>'
                f'<td>{feel}</td></tr>'
            )
        power_note = """<div class="gg-module gg-alert"><div class="gg-label">BEFORE YOU START: FTP TEST REQUIRED</div>
<p><strong>Complete an FTP test before the structured intervals begin.</strong>
Without your FTP, every zone target in this plan is a percentage of an unknown number. Until you test,
use RPE (Rate of Perceived Exertion) to guide intensity.</p>
<p>After testing, recalculate all zones: <strong>Zone watts = FTP &times; zone percentage.</strong>
If you use Zwift, TrainerRoad, or a Garmin &mdash; update your FTP setting immediately after testing.</p></div>"""

    rows_html = "\n".join(power_rows)

    # Real HR anchors when the athlete has tested (HR zones are % of LTHR, not
    # HRmax — Zone 4 ≈ threshold). Gives an HR-based rider true bpm targets.
    hr_bpm_header = '<th>HR (bpm)</th>' if lthr else ''
    if lthr:
        _maxhr = f' &middot; measured HRmax {max_hr} bpm' if max_hr else ''
        hr_note = (f'<p><strong>Your threshold HR (LTHR): {lthr} bpm</strong>{_maxhr}. '
                   f'The HR zones below are a percentage of your LTHR &mdash; Zone 4 '
                   f'(Threshold) sits right around {lthr} bpm. Use power as the primary '
                   f'target and HR as the cross-check; on a hot or fatigued day, trust HR.</p>')
    else:
        hr_note = ''

    return f"""<section id="section-2" class="gg-section">
  <h2>2 &middot; Training Zones</h2>

  <h3>The Point of Zones</h3>
  <p>Training zones aren't arbitrary numbers. Each zone targets a specific physiological system.
  Training in the wrong zone doesn't just reduce effectiveness &mdash; it actively harms your progression
  by creating the wrong type of fatigue without the right type of adaptation.</p>

  <p>Your plan controls how much time you spend in each zone &mdash; the zones are the vocabulary,
  the plan is the sentence. Your only job is to hit the prescribed zone when a workout calls for it.
  One caution that holds for every methodology: Zone 3 is the "gray zone" &mdash; too hard to recover
  from, too easy to create real adaptation. Ride it only when prescribed.</p>

  {power_note}
  {hr_note}

  <h3>The Zone Chart</h3>
  <div style="overflow-x: auto;">
  <table class="zone-table">
  <thead><tr><th>Zone</th><th>Name</th><th>Power</th><th>% FTP</th><th>% LTHR</th>{hr_bpm_header}<th>RPE</th><th>Feel</th></tr></thead>
  <tbody>
  {rows_html}
  </tbody>
  </table>
  </div>

  <h3>FTP Testing Protocol</h3>
  <p>When an FTP test appears on your calendar, here's how to execute the 20-minute protocol. There is
  <strong>one</strong> maximal effort &mdash; the 20-minute test. Everything before it is preparation.</p>
  <ol>
  <li>12 minutes progressive warmup (Z1 building to Z2)</li>
  <li>3 minutes at RPE 7 (moderate-hard), then 1 minute easy &mdash; just opening the legs</li>
  <li><strong>5-minute hard opener</strong> &mdash; ride this hard (RPE 8-9), NOT all-out. Its only job is to clear out your anaerobic system so the 20-minute number reflects sustainable power, not a sprint. This is not the test.</li>
  <li>10 minutes easy recovery (Z1) &mdash; fully recover before the test</li>
  <li><strong>20-MINUTE TIME TRIAL</strong> &mdash; this is the test. Start at an effort you're confident you can hold, then build. Even pacing beats going out hard and fading. This sets your FTP.</li>
  <li>10 minutes easy cooldown</li>
  </ol>
  <p><strong>Formula:</strong> FTP = 20-minute average power &times; 0.95</p>

  <div class="gg-module gg-alert">
    <div class="gg-label">WARNING</div>
    <p><strong>Don't test when tired.</strong> Do FTP tests when fresh &mdash; not after a hard training week. The test result
    sets ALL your training zones for the next 6 weeks. An inaccurate test means
    6 weeks of wrong-zone training.</p>
  </div>

  <h3>Critical Notes on Using Zones</h3>
  <ul>
  <li><strong>Easy means EASY.</strong> Zone 2 should feel almost too easy. If you're questioning whether you're going hard enough, you're in the right zone.</li>
  <li><strong>Hard means HARD.</strong> Zone 4+ intervals should leave you breathless. If you can hold a conversation, you're not in the right zone.</li>
  <li><strong>Don't fill the gap.</strong> The biggest mistake is spending too much time in Zone 3 (tempo). It feels productive but creates maximum fatigue with suboptimal adaptation.</li>
  <li><strong>Power > HR > RPE.</strong> Use power meter if available, heart rate as backup, RPE as last resort. Heart rate lags &mdash; use RPE for short intervals.</li>
  </ul>
</section>"""


def _section_adaptation():
    return """<section id="section-3" class="gg-section">
  <h2>3 &middot; How Adaptation Works</h2>

  <p>Every workout in this plan exists for a reason. Understanding the adaptation model
  helps you make smart decisions when life disrupts the plan.</p>

  <h3>The Foundational Model</h3>

  <div class="data-card">
    <div class="data-card__header">STEP 1: STRESS</div>
    <div class="data-card__content">
      <p>You apply a training stimulus (the workout). This creates controlled damage &mdash;
      micro-tears in muscle, glycogen depletion, cardiovascular stress.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">STEP 2: RECOVERY</div>
    <div class="data-card__content">
      <p>Your body repairs the damage. This takes 24-72 hours depending on workout intensity.
      Sleep, nutrition, and stress levels all affect recovery speed.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">STEP 3: SUPERCOMPENSATION</div>
    <div class="data-card__content">
      <p>Your body doesn't just repair &mdash; it overbuilds. You come back slightly stronger than before.
      This is the entire point of training.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">STEP 4: REPEAT</div>
    <div class="data-card__content">
      <p>Apply the next stress at the peak of supercompensation. Too soon = overtraining.
      Too late = detraining. The plan's timing handles this for you.</p>
    </div>
  </div>

  <h3>Where It Goes Wrong</h3>

  <div class="gg-module gg-blackpill">
    <div class="gg-label">THE #1 TRAINING MISTAKE</div>
    <p>Going too hard on easy days and too easy on hard days. This puts you in the "gray zone" &mdash;
    maximum fatigue, minimum adaptation. Trust the zones. Easy days should feel embarrassingly easy.
    Hard days should be genuinely hard.</p>
  </div>

  <div class="gg-module gg-alert">
    <div class="gg-label">THE #2 TRAINING MISTAKE</div>
    <p>Skipping recovery. Adaptation happens during rest, not during workouts. The workout is the
    stimulus. Sleep is where you get faster. Cutting sleep to fit in more training is
    counterproductive &mdash; you're removing the adaptation window.</p>
  </div>

  <h3>Practical Rules</h3>
  <ul>
  <li><strong>Never add intensity to an easy day.</strong> If the plan says Z2, stay in Z2. Even if you feel great.</li>
  <li><strong>Never add volume to a hard day.</strong> Hard days are about quality, not quantity. If you can do more, you didn't go hard enough.</li>
  <li><strong>If you miss a workout, skip it.</strong> Don't try to make it up by doubling the next day. The plan accounts for progressive overload &mdash; doubling creates injury risk.</li>
  <li><strong>If you're sick, stop.</strong> Training while sick extends illness duration by 2-3x. Take the days off. You'll lose less fitness from rest than from a week of half-effort sick training.</li>
  <li><strong>Sleep > training.</strong> If you have to choose between a 5am workout and 8 hours of sleep, choose sleep every time.</li>
  </ul>
</section>"""


def _section_weekly_structure(schedule: Dict, tier_display: str, weekly_hours: str = "",
                              est_race_hrs: float = 0):
    days = schedule.get("days", {})
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    # Calculate long ride duration from available hours
    _, max_hrs = _parse_hours_range(weekly_hours)

    # Session durations (hours) — use minimums to maximize long ride time
    session_min_hours = {
        "rest": 0,
        "intervals": 1.0,    # 60 min minimum
        "easy_ride": 0.75,    # 45 min minimum
        "strength": 0.5,     # 30 min minimum (bodyweight OK)
    }

    # Count non-long-ride hours and long ride days
    non_long_hours = 0
    long_ride_count = 0
    for day in all_days:
        info = days.get(day, {"session": "rest"})
        session = info["session"]
        if session == "long_ride":
            long_ride_count += 1
        else:
            non_long_hours += session_min_hours.get(session, 0.5)

    # Calculate per-long-ride duration
    if max_hrs > 0 and long_ride_count > 0:
        remaining = max(max_hrs - non_long_hours, 1.5)
        per_ride = remaining / long_ride_count
        # Floor: at least 1.5 hours for meaningful endurance work
        per_ride = max(per_ride, 1.5)
        # Cap by race duration: a long ride that wildly exceeds the race
        # (e.g. 6.8h for a 3.8h event) is a budget artifact, not coaching —
        # it contradicts the fueling section and worries the athlete. The
        # longest ride should approach race duration, not blow past it.
        if est_race_hrs and est_race_hrs > 0:
            per_ride = min(per_ride, est_race_hrs * 1.15)
            per_ride = max(per_ride, 1.5)
        # Range: base to peak (recovery weeks to build weeks)
        lr_lo = max(1.5, per_ride * 0.6)
        lr_hi = per_ride
        lr_lo_str = f"{lr_lo:.1f}".rstrip("0").rstrip(".")
        lr_hi_str = f"{lr_hi:.1f}".rstrip("0").rstrip(".")
        # When the floor collapses the range to a single value, don't render
        # a nonsensical "1.5-1.5 hours".
        long_ride_duration = (f"{lr_hi_str} hours" if lr_lo_str == lr_hi_str
                              else f"{lr_lo_str}-{lr_hi_str} hours")
    else:
        per_ride = 2.5
        long_ride_duration = "2-3 hours"

    # If long rides are short relative to available time, add a tactical note
    long_ride_note = ""
    if max_hrs > 0 and long_ride_count > 0 and per_ride < 3.0:
        long_ride_note = """<div class="gg-module gg-tactical">
    <div class="gg-label">YOUR BIGGEST OPPORTUNITY</div>
    <p>Your weekly structure fits your stated availability, but your long rides are shorter than ideal
    for a race of this distance. If you can make more time during Build and Peak phases to fit
    <strong>1-3 longer rides per month</strong> &mdash; whether that means clearing a Saturday morning,
    swapping a weekday session, or simply going beyond your normal hours that week &mdash;
    it will make a significant difference to your race-day durability. A single 3-4 hour ride
    is worth more than two 1.5 hour rides for building the endurance you'll need on race day.</p>
  </div>"""

    training_days = [d for d, v in days.items() if v["session"] != "rest"]
    key_days = [d for d, v in days.items() if v["session"] in ("long_ride", "intervals")]

    # Coach review (Jun 2026): NO day-by-day schedule table here. The
    # schedule lives in the training plan; this section explains the ROLE
    # of each session type so the athlete understands what they're doing.
    return f"""<section id="section-4" class="gg-section">
  <h2>4 &middot; Weekly Structure</h2>

  <p>Every week of your plan is built from the same four ingredients: a long ride, interval sessions,
  easy rides, and strength work. Your plan places them on specific days &mdash; follow the calendar.
  What matters here is understanding what each session type is <em>for</em>, because riders who
  understand the purpose execute better than riders who just follow orders.</p>

  <p>Your week has {len(training_days)} training days, {len(key_days)} of which are key sessions.
  Key sessions are the ones that drive adaptation. Everything else supports them.</p>

  <h3>Session Types Explained</h3>

  <div class="data-card">
    <div class="data-card__header">LONG RIDE</div>
    <div class="data-card__content">
      <p>The backbone of endurance preparation. Primarily Zone 2 with race-specific efforts mixed in
      during Build and Peak phases. Build duration progressively &mdash; don't jump to your peak duration of {long_ride_duration} in Week 1.</p>
    </div>
  </div>

  {long_ride_note}

  <div class="data-card">
    <div class="data-card__header">INTERVALS</div>
    <div class="data-card__content">
      <p>High-intensity sessions targeting specific energy systems. Follow the prescribed zones exactly.
      Full recovery between intervals is mandatory &mdash; cutting rest reduces the training stimulus.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">EASY RIDE</div>
    <div class="data-card__content">
      <p>Zone 1-2 only. Active recovery. The purpose is blood flow, not fitness. If you catch yourself
      hammering a Strava segment on an easy day, you're doing it wrong.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">STRENGTH</div>
    <div class="data-card__content">
      <p>Cycling-specific strength work. Focus on single-leg exercises, core stability, and hip strength.
      Keep it under 60 minutes. Heavy enough to be challenging, light enough to not wreck your legs
      for the next bike session.</p>
    </div>
  </div>

  <h3>When Life Interferes</h3>
  <p>The plan owns the schedule. When real life collides with it, these principles keep the
  damage contained:</p>
  <ul>
  <li><strong>Protect the key sessions first.</strong> If a week falls apart, keep one interval session and the long ride; let everything else go easy or disappear.</li>
  <li><strong>Never stack key sessions back-to-back</strong> to "catch up" &mdash; that creates fatigue without proportional adaptation. A missed session stays missed.</li>
  <li><strong>Illness: drop ALL intensity.</strong> Easy riding only if you feel up to it. Symptoms below the neck (chest, body aches) mean complete rest.</li>
  </ul>
</section>"""


def _section_phase_progression(plan_duration: int, tier: str, ride_realism: float = 1.0):
    # Long ride description adapts to what the athlete can actually do
    if ride_realism >= 0.6:
        base_lr_desc = "Long rides build from current fitness toward 60-70% of expected race duration."
    elif ride_realism >= 0.3:
        base_lr_desc = "Long rides build progressively. Your weekly budget limits ride length, so each long ride counts double &mdash; use them for race-pace fueling practice."
    else:
        base_lr_desc = "Long rides build progressively within your time budget. Quality over quantity &mdash; every long ride includes nutrition rehearsal and race-pace efforts to compensate for volume."

    # Coach review (Jun 2026): this section is GENERAL. No week numbers, no
    # dates, no cadence claims — the plan calendar owns all of that. This
    # explains what each phase is for so the athlete trusts the shape.
    phases = [
        ("Base", "base",
         f"The foundation. Mostly easy aerobic riding with progressive volume, plus strength work. "
         f"This phase feels too easy &mdash; that's the point. Aerobic base determines your ceiling; "
         f"there is no shortcut around it. {base_lr_desc}"),
        ("Build", "build",
         "Race-specific intensity enters: threshold and VO2max intervals, long rides with race-pace "
         "efforts. This is where it gets hard. Fatigue is expected &mdash; it's being managed "
         "deliberately through the recovery weeks your plan schedules."),
        ("Peak", "peak",
         "Maximum specificity. Race-simulation rides, dress-rehearsal fueling, intensity stays high "
         "while volume starts to drop. You should feel fitness arriving."),
        ("Taper", "taper",
         "Volume drops sharply; short, sharp efforts keep the engine awake. You cannot gain fitness "
         "now &mdash; you can only show up fresh or show up tired. Trust the training and rest."),
    ]

    phase_cards = []
    for name, phase_type, desc in phases:
        phase_cards.append(f"""  <div class="data-card">
    <div class="data-card__header"><span class="phase-indicator phase-indicator--{phase_type}">{name}</span></div>
    <div class="data-card__content">
      <p>{desc}</p>
    </div>
  </div>""")

    return f"""<section id="section-5" class="gg-section">
  <h2>5 &middot; Phase Progression</h2>
  <p>Your {plan_duration}-week plan moves through {len(phases)} phases, each with a specific purpose.
  The exact week ranges are in your training calendar &mdash; what matters here is why each phase
  exists, so you don't rush base to get to the "hard stuff." Base fitness determines your ceiling.</p>

{''.join(phase_cards)}

  <div class="gg-module gg-tactical">
    <div class="gg-label">RECOVERY WEEKS</div>
    <p>Your plan schedules regular recovery weeks &mdash; volume drops 30-40%, intensity drops to easy
    riding only. These weeks are where adaptation actually happens. Skipping them is the fastest path
    to overtraining and stalled progress. They are not optional.</p>
  </div>
</section>"""

def _parse_hours_range(hours_str: str):
    """Parse '5-7' or '10-12' into (lo, hi) floats. Returns (0, 0) on failure."""
    if not hours_str:
        return (0, 0)
    s = str(hours_str).replace("hrs", "").replace("hr", "").replace("+", "").strip()
    if "-" in s:
        parts = s.split("-")
        try:
            return (float(parts[0].strip()), float(parts[1].strip()))
        except (ValueError, IndexError):
            return (0, 0)
    try:
        v = float(s)
        return (v, v)
    except ValueError:
        return (0, 0)


def _scale_volume_hours(template_hrs: str, scale_factor: float) -> str:
    """Scale a template volume_hours string by a factor. Returns formatted range."""
    lo, hi = _parse_hours_range(template_hrs)
    if lo == 0 and hi == 0:
        return template_hrs
    scaled_lo = round(lo * scale_factor, 1)
    scaled_hi = round(hi * scale_factor, 1)
    # Clean up: remove .0 for whole numbers
    lo_s = str(int(scaled_lo)) if scaled_lo == int(scaled_lo) else str(scaled_lo)
    hi_s = str(int(scaled_hi)) if scaled_hi == int(scaled_hi) else str(scaled_hi)
    if lo_s == hi_s:
        return lo_s
    return f"{lo_s}-{hi_s}"


def _section_workout_execution(tier: str, ftp: Optional[int] = None):
    no_ftp_note = ""
    if ftp is None:
        no_ftp_note = """
  <div class="gg-module gg-alert"><div class="gg-label">UNTIL YOU COMPLETE YOUR FTP TEST</div>
  <p>Your ZWO files use FTP-based power targets. Without your FTP number, use RPE (Rate of Perceived
  Exertion) from the zone chart instead. After your Week 1 FTP test, update your FTP in Zwift/TrainerRoad/Garmin
  and all workout targets will calibrate automatically.</p></div>
"""

    return f"""<section id="section-6" class="gg-section">
  <h2>6 &middot; Workout Execution</h2>
  {no_ftp_note}
  <h3>The Execution Gap</h3>
  <p><strong>The plan says:</strong> "4x4min at 110% FTP with 4min recovery."</p>
  <p><strong>What actually happens:</strong></p>
  <ul>
  <li>First interval: nailed it, felt strong</li>
  <li>Second interval: still good, maybe went a bit hard</li>
  <li>Third interval: struggling, cut 30 seconds short</li>
  <li>Fourth interval: abandoned or at 95% FTP instead of 110%</li>
  </ul>
  <p><strong>Result:</strong> You did a Zone 3-4 workout instead of a Zone 5 workout.
  Different stimulus, different adaptation, wrong training effect.</p>

  <h3>Universal Execution Rules</h3>

  <div class="data-card">
    <div class="data-card__header">RULE 1: START CONSERVATIVE</div>
    <div class="data-card__content">
      <p>First interval of every set should feel slightly too easy. If the plan says 110% FTP,
      start the first rep at 105%. Build into it. The goal is completing ALL intervals at target power,
      not crushing the first one and failing the rest.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">RULE 2: QUALITY OVER QUANTITY</div>
    <div class="data-card__content">
      <p>If you can't hold target power, STOP the workout. 3 good intervals at 110% FTP are
      worth more than 5 intervals where the last two are at 95%. Bad reps don't count &mdash; they
      just create fatigue.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">RULE 3: RECOVERY MEANS RECOVERY</div>
    <div class="data-card__content">
      <p>Between intervals, drop to Zone 1. Not Zone 2, not "easy Zone 3." Zone 1.
      Full recovery ensures the next interval hits the right energy system.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">RULE 4: CADENCE MATTERS</div>
    <div class="data-card__content">
      <p>Alternate between high cadence (95-105 rpm) and low cadence (60-75 rpm) intervals.
      High cadence trains the cardiovascular system; low cadence builds muscular force.
      A complete rider develops both &mdash; the range to spin smoothly when fresh and to
      push a big gear when the road tilts up.</p>
    </div>
  </div>

  <h3>Indoor vs Outdoor Workouts</h3>
  <p><strong>Best done indoors:</strong> Short intervals (VO2max, anaerobic), FTP tests,
  cadence drills, recovery spins.</p>
  <p><strong>Best done outdoors:</strong> Long rides, tempo efforts, race simulations,
  skills practice, group rides.</p>
  <p><strong>Balance:</strong> Aim for at least 1-2 outdoor rides per week. Indoor training is
  efficient but doesn't prepare you for real-world race conditions &mdash; wind, terrain changes,
  group dynamics, and the mental challenge of a long day in the saddle.</p>

  <h3>When and How to Modify Workouts</h3>
  <ul>
  <li><strong>Feeling great:</strong> Don't add volume or intensity. Stick to the plan. Save the good legs for the next hard day.</li>
  <li><strong>Feeling tired:</strong> Drop intensity by 5% but keep duration. If that's still too much, convert to Zone 2.</li>
  <li><strong>Feeling terrible:</strong> Convert to easy spin or take the day off. One missed workout doesn't matter. Two weeks of subpar training does.</li>
  <li><strong>Missed workout rule:</strong> Never try to make up a missed workout. Just move forward in the plan.</li>
  </ul>
</section>"""


def _section_recovery_protocol(tier: str, profile: Dict, store_mode: bool = False):
    sleep = profile.get("health", {}).get("sleep_quality", "moderate")
    stress = profile.get("health", {}).get("stress_level", "moderate")

    # Personalized post-workout targets from body weight — store_mode has no
    # real athlete behind the profile's weight, so it always takes the
    # generic (already-existing) fallback below instead of a fake number.
    weight_lbs = None if store_mode else profile.get("demographics", {}).get("weight_lbs")
    if weight_lbs:
        try:
            weight_kg = float(weight_lbs) / 2.205
            protein_g = round(weight_kg * 0.4)  # 0.4g/kg recovery dose
            carb_lo = round(weight_kg * 1.0)     # 1.0g/kg low end
            carb_hi = round(weight_kg * 1.2)     # 1.2g/kg high end
            recovery_line = f"{protein_g}g protein + {carb_lo}-{carb_hi}g carbs within 30 minutes (based on your {round(weight_kg)}kg body weight)"
        except (ValueError, TypeError):
            recovery_line = "30g protein + 60-90g carbs within 30 minutes"
    else:
        recovery_line = "30g protein + 60-90g carbs within 30 minutes"

    # store_mode: never present fake health-questionnaire data ("You
    # reported...") as if a real buyer answered it.
    stress_note = ""
    if not store_mode and stress in ("high", "very_high"):
        stress_note = """<div class="gg-module gg-alert">
    <div class="gg-label">HIGH LIFE STRESS DETECTED</div>
    <p>You reported high stress levels. Life stress and training stress use the same recovery systems.
    During high-stress periods, reduce training volume by 20% and eliminate all Zone 4+ work.
    This is not weakness &mdash; it's smart resource management.</p>
  </div>"""

    return f"""<section id="section-7" class="gg-section">
  <h2>7 &middot; Recovery Protocol</h2>

  <p>Adaptation happens during recovery, not during training. The workout is the stimulus.
  Recovery is where you actually get faster.</p>

  {stress_note}

  <h3>Daily Recovery Protocol</h3>

  <div class="data-card">
    <div class="data-card__header">IMMEDIATELY POST-RIDE</div>
    <div class="data-card__content">
      <ul>
        <li>{recovery_line}</li>
        <li>Rehydrate: 150% of fluid lost (weigh before/after)</li>
        <li>Compression garments for rides > 3 hours</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">EVENING</div>
    <div class="data-card__content">
      <ul>
        <li>8+ hours sleep (non-negotiable)</li>
        <li>No screens 60 min before bed</li>
        <li>Cool room (65-68&deg;F / 18-20&deg;C)</li>
        <li>Light stretching or foam rolling (10 min max)</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">AFTER HARD SESSIONS</div>
    <div class="data-card__content">
      <ul>
        <li>10-minute cooldown spin (mandatory)</li>
        <li>Extra 200-300 calories in recovery meal</li>
        <li>No hard training for 48 hours</li>
        <li>Next day should be easy or rest</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">RECOVERY WEEKS</div>
    <div class="data-card__content">
      <ul>
        <li>Volume drops 30-40%</li>
        <li>No Zone 4+ intensity</li>
        <li>Extra sleep if possible</li>
        <li>This is where fitness consolidates</li>
      </ul>
    </div>
  </div>

  <h3>HRV: What It Is and How to Use It</h3>
  <p>Heart Rate Variability (HRV) measures the time between heartbeats. Higher variability = better recovery.
  Lower variability = accumulated stress.</p>
  <ul>
  <li><strong>Good for:</strong> Tracking long-term recovery trends (7-day rolling average), identifying overtraining before it happens</li>
  <li><strong>Not good for:</strong> Making single-day training decisions, replacing how you feel</li>
  <li><strong>How to use:</strong> Measure every morning before getting out of bed. If your 7-day average drops more than 10% below baseline, take an extra recovery day.</li>
  <li><strong>Apps:</strong> HRV4Training, Elite HRV, Whoop</li>
  </ul>

  <h3>Signs You Need More Recovery</h3>
  <ul>
  <li>Resting heart rate elevated 5+ bpm above normal</li>
  <li>Can't hit power targets despite feeling "fine"</li>
  <li>Motivation drops for more than 3 consecutive days</li>
  <li>Sleep quality declining despite good sleep hygiene</li>
  <li>Persistent muscle soreness beyond 48 hours</li>
  <li>Getting sick more than usual</li>
  </ul>
</section>"""


def _section_equipment_checklist(profile: Dict, race_data: Dict):
    trainer = profile.get("equipment", {}).get("trainer_type", "")
    has_trainer = trainer and trainer != "no"

    surface_hazards = race_data.get("race_specific", {}).get("surface_hazards", [])
    hazard_items = "\n".join(f"<li>{h}</li>" for h in surface_hazards) if surface_hazards else ""

    return f"""<section id="section-8" class="gg-section">
  <h2>8 &middot; Equipment Checklist</h2>

  <h3>Training Equipment</h3>

  <div class="data-card">
    <div class="data-card__header">MANDATORY</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Bike</strong> &mdash; gravel or similar, in good working order</li>
        <li><strong>Helmet</strong> &mdash; every outdoor ride, no exceptions</li>
        {'<li><strong>Indoor trainer</strong> &mdash; for interval sessions and bad weather days</li>' if has_trainer else ''}
        <li><strong>Water bottles / hydration pack</strong> &mdash; two bottles for anything over 90 minutes outdoors; one within reach on the trainer</li>
        <li><strong>Repair kit (outdoor rides)</strong> &mdash; spare tube, CO2, tire lever, multi-tool</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">RECOMMENDED</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Power meter</strong> &mdash; the single best training tool you can buy</li>
        <li><strong>Heart rate monitor</strong> &mdash; chest strap preferred (wrist is less accurate)</li>
        <li><strong>Cycling computer</strong> &mdash; for tracking intervals and zones in real-time</li>
        <li><strong>Foam roller</strong> &mdash; for daily recovery</li>
      </ul>
    </div>
  </div>

  <h3>Race Day Equipment</h3>
  <ul>
    <li><strong>Tires:</strong> Test your race tires at least 3 weeks before race day. No new equipment on race day.</li>
    <li><strong>Nutrition:</strong> Same bottles, same food, same pockets as your dress rehearsal ride</li>
    <li><strong>Clothing:</strong> Weather-appropriate layers tested in training</li>
    <li><strong>Spares:</strong> Two spare tubes, tire plugs, CO2 cartridges (minimum 2), multi-tool</li>
    <li><strong>Lights:</strong> If there's any chance of finishing after dark</li>
  </ul>

  {f'<h3>Course-Specific Hazards</h3><ul>{hazard_items}</ul>' if hazard_items else ''}

  <div class="gg-module gg-blackpill">
    <div class="gg-label">NOTHING NEW ON RACE DAY</div>
    <p>No new shoes, no new saddle, no new nutrition, no new tires. Everything you use on race day
    must have been tested in training. This includes your exact nutrition plan &mdash; same brands,
    same quantities, same timing.</p>
  </div>
</section>"""


def _section_nutrition(race_data: Dict, tier: str, race_distance, profile: Dict = None, plan_duration: int = 12,
                       store_mode: bool = False):
    if profile is None:
        profile = {}
    mods = race_data.get("workout_modifications", {})
    fuel = mods.get("fueling", {})

    aggressive_note = ""
    if fuel and fuel.get("aggressive"):
        aggressive_note = f"""<div class="gg-module gg-alert"><div class="gg-label">AGGRESSIVE FUELING REQUIRED</div>
<p>{fuel.get('note', 'Practice race-day nutrition weekly during long rides.')}</p></div>"""

    # Duration-scaled fueling targets — deterministic from questionnaire data.
    # Source: gravel-god-nutrition framework (Jeukendrup 2014, van Loon 2001, GSSI).
    # No AI mediation. Pure math.
    try:
        from pipeline.nutrition import compute_fueling_for_guide
    except ImportError:
        compute_fueling_for_guide = None  # Coaching pipeline provides nutrition via fueling.yaml

    personalized_html = ""
    daily_macros_html = ""
    # store_mode has no real athlete behind the profile's weight — always
    # take the generic (already-existing) per-kg guidance below rather than
    # presenting a fake individual's numbers as "personalized".
    weight_lbs = None if store_mode else profile.get("demographics", {}).get("weight_lbs")
    weight_kg = 0
    if weight_lbs and compute_fueling_for_guide:
        try:
            fueling = compute_fueling_for_guide(race_distance, race_data, profile)
            weight_kg = fueling.get("weight_kg", float(weight_lbs) / 2.205)
            carb_lo = fueling["carb_rate_lo"]
            carb_hi = fueling["carb_rate_hi"]
            est_hours = fueling["hours"]
            total_lo = fueling["carbs_total_lo"]
            total_hi = fueling["carbs_total_hi"]
            bracket_label = fueling["label"]
            gut_weeks = fueling["gut_training_weeks"]
            dist = int(race_distance) if race_distance else 0
            fluid_target = 600 if dist >= 100 else 500
            sodium_target = 500

            # Gut training builds from conservative to race rate
            gut_base_hi = min(50, carb_lo)
            gut_build_lo = gut_base_hi
            gut_build_hi = min(carb_lo + 10, carb_hi)

            total_html = ""
            if est_hours > 0:
                total_html = f"""
        <div class="stat-card">
          <div class="stat-card__value">{total_lo}-{total_hi}g</div>
          <div class="stat-card__label">Total Race Carbs</div>
        </div>"""

            personalized_html = f"""
  <div class="data-card">
    <div class="data-card__header">YOUR PERSONALIZED FUELING TARGETS</div>
    <div class="data-card__content">
      <p>Based on your body weight ({weight_lbs} lbs / {weight_kg:.0f} kg), race distance ({f"{race_distance} miles" if race_distance else "unknown"}),
      and estimated duration (~{est_hours} hours &mdash; {bracket_label}).</p>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card__value">{carb_lo}-{carb_hi}g/hr</div>
          <div class="stat-card__label">Hourly Carbs</div>
        </div>{total_html}
        <div class="stat-card">
          <div class="stat-card__value">{fluid_target}ml/hr</div>
          <div class="stat-card__label">Hourly Fluid</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__value">{sodium_target}mg/hr</div>
          <div class="stat-card__label">Hourly Sodium</div>
        </div>
      </div>
      <h4>Gut Training Progression</h4>
      <p>Gut training starts from Week 1 and ramps through your plan phases. SGLT1 transporters double
      in ~2 weeks (GSSI), but full adaptation to your race-day carb rate takes 6-12 weeks.
      Start conservative, build steadily.</p>
      <table>
      <thead><tr><th>Plan Phase</th><th>Target</th><th>Focus</th></tr></thead>
      <tbody>
      <tr><td><strong>Base</strong></td><td>40-{gut_base_hi}g/hr</td><td>Build tolerance &mdash; real food on easy rides</td></tr>
      <tr><td><strong>Build</strong></td><td>{gut_build_lo}-{gut_build_hi}g/hr</td><td>Increase absorption &mdash; mix liquids and solids at tempo</td></tr>
      <tr><td><strong>Peak</strong></td><td>{carb_lo}-{carb_hi}g/hr</td><td>Race-rate practice with race-day products only</td></tr>
      <tr class="race-day-row"><td><strong>Race</strong></td><td>{carb_lo}-{carb_hi}g/hr</td><td>Execute your fueling plan &mdash; nothing new</td></tr>
      </tbody>
      </table>
      <p><strong>Based on your {carb_lo}-{carb_hi}g/hr target:</strong> ~{round(carb_lo / 25, 1)}-{round(carb_hi / 25, 1)} gels per hour
      (or equivalent liquid/solid carbs). Practice this exact strategy during long training rides.</p>
    </div>
  </div>"""
        except (ValueError, TypeError):
            pass

    # Personalized daily macro targets (all from body weight — no AI)
    if weight_kg:
        wkg = weight_kg
        daily_macros_html = f"""
  <div class="data-card">
    <div class="data-card__header">YOUR DAILY MACRO TARGETS ({weight_lbs} lbs / {wkg:.0f} kg)</div>
    <div class="data-card__content">
      <table>
      <thead><tr><th>Macro</th><th>Daily Target</th><th>Why</th></tr></thead>
      <tbody>
      <tr><td><strong>Protein</strong></td><td>{round(wkg * 1.6)}-{round(wkg * 2.2)}g/day</td>
        <td>Rebuilds muscle tissue damaged during training. Spread across 4 meals (25-40g each).</td></tr>
      <tr><td><strong>Carbs (easy day)</strong></td><td>{round(wkg * 3)}-{round(wkg * 4)}g</td>
        <td>Z2 endurance, rest days. Just restock glycogen.</td></tr>
      <tr><td><strong>Carbs (hard day)</strong></td><td>{round(wkg * 5)}-{round(wkg * 7)}g</td>
        <td>Interval days, long rides. Fuel the work, recover for the next session.</td></tr>
      <tr><td><strong>Fat</strong></td><td>{round(wkg * 0.8)}-{round(wkg * 1.2)}g/day</td>
        <td>Hormones, cell membranes, vitamin absorption. Moderate and consistent.</td></tr>
      </tbody>
      </table>
      <p><strong>Sources:</strong> Protein from meat, fish, eggs, dairy, legumes. Carbs from rice, potatoes,
      oats, bread, pasta, fruit &mdash; real food first. Fat from olive oil, nuts, avocados, fatty fish, eggs.</p>
      <p><strong>The rule:</strong> Match carb intake to training load. Don't carb-load on rest days.
      Don't under-fuel hard training blocks.</p>
    </div>
  </div>"""

    # Pre-workout carb target based on body weight
    pre_workout_carbs = f"{round(weight_kg * 1)}-{round(weight_kg * 2)}g carbs" if weight_kg else "1-2g carbs per kg bodyweight"
    pre_race_carbs = f"{round(weight_kg * 2)}-{round(weight_kg * 3)}g carbs" if weight_kg else "2-3g carbs per kg bodyweight"
    post_carbs = f"{round(weight_kg * 1)}-{round(weight_kg * 1.5)}g carbs" if weight_kg else "1-1.5g carbs per kg bodyweight"

    return f"""<section id="section-9" class="gg-section">
  <h2>9 &middot; Nutrition Strategy</h2>

  <p>You can have perfect training, a dialed bike, and excellent pacing strategy. None of it matters if
  you run out of fuel halfway through your race.</p>
  <p>Fueling errors are the most common preventable cause of bad race days &mdash; the difference
  between finishing strong and crawling to the line.</p>

  {aggressive_note}
  {personalized_html}

  <h3>The Reality Check</h3>
  <p>The cycling nutrition industry wants you to believe you need seventeen different products, each
  with proprietary blend ratios and specific timing windows measured in seconds. You don't.</p>
  <p>You need carbohydrates during exercise. You need protein and carbs after exercise. You need
  reasonable daily nutrition that supports training. That's 95% of it. Everything else is optimization
  you can worry about after you've nailed the basics.</p>

  <h3>Daily Nutrition for Training</h3>
  <p>Your body is either recovering from the last workout or preparing for the next one.
  Daily nutrition supports both.</p>

  {daily_macros_html}

  <h3>Timing That Actually Matters</h3>

  <div class="data-card">
    <div class="data-card__header">PRE-WORKOUT (2-3 HOURS BEFORE)</div>
    <div class="data-card__content">
      <p><strong>If training hard (threshold, VO2max):</strong></p>
      <ul>
        <li>{pre_workout_carbs}</li>
        <li>Low fiber, low fat, moderate protein</li>
        <li>Examples: oatmeal with banana and honey, or toast with peanut butter</li>
      </ul>
      <p><strong>If training easy (Z2 endurance):</strong></p>
      <ul>
        <li>Eat normally, don't stress timing</li>
        <li>Can even train fasted if under 90 minutes</li>
      </ul>
      <p><strong>The rule:</strong> Hard sessions need fuel. Easy sessions are flexible.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">POST-WORKOUT (0-90 MINUTES AFTER)</div>
    <div class="data-card__content">
      <p><strong>If workout was long (2.5+ hours) AND hard, AND you have another hard session within 24-36 hours:</strong></p>
      <ul>
        <li>20-30g protein</li>
        <li>{post_carbs}</li>
        <li>Liquid is fine (protein shake, chocolate milk)</li>
      </ul>
      <p><strong>If workout was easy, short, or your next hard session is 48+ hours away:</strong></p>
      <ul>
        <li>Just eat your next meal normally</li>
        <li>Recovery nutrition is optional</li>
      </ul>
      <p><strong>The rule:</strong> The more frequently you train hard, the more critical recovery nutrition becomes.</p>
    </div>
  </div>

  <h3>Supplements</h3>
  <p>Most supplements are placebo at best, actively harmful at worst.</p>

  <div class="data-card">
    <div class="data-card__header">WORTH TAKING</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Vitamin D</strong> (2000-4000 IU daily): Supports bone health, immune function, recovery. Most people are deficient. Get levels tested.</li>
        <li><strong>Creatine monohydrate</strong> (5g daily): Improves high-intensity repeatability. Useful for VO2max and sprint work. Cheap, well-researched, safe.</li>
        <li><strong>Caffeine</strong> (3-6mg/kg before hard sessions): Proven performance enhancer. Coffee works, pills work, gels work. Tolerance builds &mdash; cycle off occasionally.</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">NOT WORTH TAKING</div>
    <div class="data-card__content">
      <ul>
        <li><strong>BCAAs:</strong> Complete waste if you eat adequate protein</li>
        <li><strong>Testosterone boosters:</strong> Scams</li>
        <li><strong>Fat burners:</strong> Scams with side effects</li>
        <li><strong>Recovery drinks with proprietary blends:</strong> Overpriced protein + carbs</li>
      </ul>
      <p><strong>The rule:</strong> If you're deficient in something (Vitamin D, iron), fix it. If you're considering
      a supplement to &ldquo;optimize,&rdquo; ask yourself if you've already nailed sleep, nutrition basics,
      and training consistency. If not, fix those first.</p>
    </div>
  </div>

  <h3>Fueling During Workouts</h3>
  <p>This is where races are won or lost.</p>
  <p>For any ride over 90 minutes at moderate-to-high intensity (Z3+), you need 60-80g of
  carbohydrates per hour. Your gut can absorb approximately 60g of glucose per hour through
  SGLT1 transporters. Add fructose (which uses different transporters) and you can push to 90g total.
  The target for most athletes is 70-75g per hour &mdash; enough to fuel hard efforts without GI distress.</p>

  <div class="data-card">
    <div class="data-card__header">WORKOUT-SPECIFIC FUELING</div>
    <div class="data-card__content">
      <table>
      <thead><tr><th>Workout Type</th><th>Duration</th><th>Carbs/Hour</th><th>Notes</th></tr></thead>
      <tbody>
      <tr><td><strong>Z2 Endurance</strong></td><td>2-4 hours</td><td>40-60g</td>
        <td>Low intensity burns fat. Real food works great &mdash; PB&amp;J, bananas, bars.</td></tr>
      <tr><td><strong>Tempo / G Spot</strong></td><td>2-3 hours</td><td>60-80g</td>
        <td>Start fueling at 30-45 min, not 90. Mix liquids and solids.</td></tr>
      <tr><td><strong>Threshold / VO2max</strong></td><td>60-90 min</td><td>Pre-meal sufficient</td>
        <td>Not depleting glycogen in 60 min. Maybe one gel mid-session.</td></tr>
      <tr><td><strong>Race Simulation</strong></td><td>4-6 hours</td><td>70-80g</td>
        <td>Practice your exact race-day fueling. Test products, timing, combinations.</td></tr>
      </tbody>
      </table>
      <p><strong>The rule:</strong> The longer and harder the ride, the more critical fueling becomes.
      Easy rides are forgiving. Race-pace efforts are not.</p>
    </div>
  </div>

  <h3>Duration-Scaled Race Fueling</h3>
  <p>This is the key insight most nutrition advice gets wrong: <strong>carb intake should scale DOWN
  with race duration, not up.</strong> At lower intensities (longer races), your body shifts toward fat oxidation.
  Forcing 90g/hr of carbs into a system running at 44% VO2max exceeds physiological absorption
  capacity and causes GI distress.</p>
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Race Duration</th><th>Carbs/Hour</th><th>Fluid/Hour</th><th>Physiology</th></tr></thead>
  <tbody>
  <tr><td>2-4 hours</td><td>80-100g</td><td>600-800ml</td><td>High intensity, carbs are dominant fuel</td></tr>
  <tr><td>4-8 hours</td><td>60-90g</td><td>700-900ml</td><td>Classic endurance range (Jeukendrup 2014); racing hard with a trained gut justifies the top end</td></tr>
  <tr><td>8-12 hours</td><td>50-70g</td><td>700-900ml</td><td>Fat oxidation increasing, GI risk climbing</td></tr>
  <tr><td>12-16 hours</td><td>40-60g</td><td>750-1000ml</td><td>Reverse crossover point &mdash; fat is primary fuel</td></tr>
  <tr><td>16+ hours</td><td>30-50g</td><td>750-1000ml</td><td>GI tolerance is the limiter, not energy</td></tr>
  </tbody>
  </table>
  </div>

  <h3>Hydration</h3>
  <p>You lose 0.5-2 liters of fluid per hour depending on temperature, humidity, and effort.
  Dehydration of 2-3% bodyweight impairs performance{f" &mdash; for you at {weight_lbs} lbs, that is {round(float(weight_lbs) * 0.02 * 0.45, 1)}-{round(float(weight_lbs) * 0.03 * 0.45, 1)} liters" if weight_lbs else ""}.</p>
  <ul>
    <li><strong>Aim for:</strong> 500-750ml per hour (16-25 oz). More in heat, less in cold.</li>
    <li><strong>Short rides (&lt;90 min):</strong> Water is fine</li>
    <li><strong>Long rides (2+ hours):</strong> Electrolyte drink with sodium (500-1000mg sodium/hour through sweat)</li>
    <li><strong>Don't overthink</strong> potassium, magnesium, or trace minerals. Sodium is 90% of what matters for performance.</li>
  </ul>

  <div class="gg-module gg-tactical">
    <div class="gg-label">CRAMPING</div>
    <p>Cramps are NOT caused by electrolyte deficiency (despite what the supplement industry tells you).
    Cramps are caused by neuromuscular fatigue &mdash; your muscles are tired and misfiring. Salt tabs
    might help by changing neuromuscular excitability, but the real fix is better pacing and better training.</p>
  </div>

  <h3>Training Your Gut</h3>
  <p>Your gut is trainable just like your muscles. If you never eat during training rides,
  your gut won't tolerate eating during races. SGLT1 transporters double in ~2 weeks of
  training (GSSI), but full adaptation takes 6-12 weeks.</p>
  <ul>
    <li><strong>Base phase:</strong> Practice eating real food on easy rides. 40-50g carbs/hour, mostly solid. Build tolerance gradually.</li>
    <li><strong>Build phase:</strong> Increase to 60-70g carbs/hour. Mix liquids and solids. Practice eating at tempo pace.</li>
    <li><strong>Peak phase:</strong> Hit your race-day target. Race nutrition only (gels, drink, bars you'll use on race day). Practice at race pace.</li>
    <li><strong>Race week:</strong> Stick with what worked in training. No new products. Trust your gut (literally).</li>
  </ul>

  <h3>Race-Day Nutrition Execution</h3>
  <p>Everything you practiced in training gets executed under stress.</p>

  <div class="data-card">
    <div class="data-card__header">PRE-RACE MEAL (3-4 HOURS BEFORE START)</div>
    <div class="data-card__content">
      <p><strong>Goal:</strong> Top off glycogen. Don't experiment.</p>
      <ul>
        <li>{pre_race_carbs}</li>
        <li>Moderate protein, low fat, low fiber</li>
        <li>Familiar foods only</li>
        <li>Examples: oatmeal with banana and honey, toast with jam and peanut butter, rice with eggs</li>
        <li>Drink 500ml water with your meal</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">STARTING LINE (30-60 MIN BEFORE START)</div>
    <div class="data-card__content">
      <p>Take one gel (24g carbs) with 200ml water. You're not adding meaningful glycogen &mdash;
      you're making sure blood glucose is stable as the race starts.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">THE FUELING TIMELINE</div>
    <div class="data-card__content">
      <p><strong>The most common mistake:</strong> waiting until you're hungry to start eating. By the time you
      feel hungry, your glycogen is already depleted and your brain is glucose-starved. You're in a hole
      you can't climb out of.</p>
      <table>
      <thead><tr><th>Window</th><th>Action</th></tr></thead>
      <tbody>
      <tr><td><strong>0-30 min</strong></td><td>Focus on pacing and positioning. Sip on drink, don't force nutrition yet.</td></tr>
      <tr><td><strong>30-60 min</strong></td><td>First gel or equivalent (24g carbs). Start your fueling clock.</td></tr>
      <tr><td><strong>Every 30 min after</strong></td><td>Consume carbs consistently. Gel every 30 min (48g/hr) + drink mix (20-30g/hr) = 70-80g total.</td></tr>
      <tr><td><strong>Aid stations</strong></td><td>Top off bottles. Grab food if needed. Keep moving &mdash; you're not on a picnic.</td></tr>
      </tbody>
      </table>
      <p><strong>Set a timer.</strong> Seriously. Your brain will be stupid. It will forget to eat. It will lie
      to you and say &ldquo;I'm fine, I'll eat at the next aid station.&rdquo; The timer removes decision-making.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">WHEN YOUR STOMACH REBELS</div>
    <div class="data-card__content">
      <p>It will. At some point in a long race, your gut will protest. High-intensity exercise diverts blood
      from your GI system to working muscles. Food sits there, undigested.</p>
      <ol>
        <li><strong>Back off intensity for 5-10 minutes.</strong> Drop to Z2 pace. Let gut blood flow recover.</li>
        <li><strong>Switch to liquid calories temporarily.</strong> Easier to digest than solids. Sports drink or cola at aid stations.</li>
        <li><strong>Small sips, not big gulps.</strong> Easier on the stomach, less sloshing.</li>
        <li><strong>Don't panic and stop eating entirely.</strong> You'll bonk 30 minutes later. Maintain some carb intake even if reduced.</li>
      </ol>
      <p><strong>What NOT to do:</strong> Hammer harder while nauseous. You'll either vomit or shut down completely.</p>
    </div>
  </div>

  <h3>Weight Management vs Performance</h3>
  <p>You want to be lean for racing. But chasing leanness during a training block is self-sabotage.</p>
  <div class="gg-module gg-tactical">
    <div class="gg-label">THE TRAINING BLOCK RULE</div>
    <p>During your training build, your job is to train hard and recover well. Not cut weight.
    Energy deficit impairs recovery. Under-fueled training produces inferior workouts.</p>
    <p><strong>When to cut weight:</strong> After your race. During the off-season. When training volume is
    low and intensity is moderate. A 500-calorie daily deficit over 8-12 weeks can drop 4-6kg
    without destroying your fitness.</p>
    <p><strong>The rule:</strong> Chase performance metrics, not scale numbers. If your FTP and climbing
    times improve, your weight is fine. If they're declining, eat more.</p>
  </div>

  <div class="gg-module gg-tactical">
    <div class="gg-label">THE RACE DAY FUELING RULE</div>
    <p>On race day, eat what you've practiced. If you haven't tested a gel brand in training,
    don't eat it in the race. GI distress at mile 60 of a {race_distance}-mile race is a
    DNF-level problem that is 100% preventable.</p>
  </div>
</section>"""


def _section_mental_preparation(race_data: Dict, race_distance, tier: str):
    psych = race_data.get("race_specific", {}).get("psychological_landmarks", [])
    dark_mile = race_data.get("race_hooks", {}).get("dark_mile", "") if isinstance(race_data.get("race_hooks"), dict) else ""

    landmark_html = ""
    if psych:
        items = []
        for p in psych:
            if isinstance(p, dict):
                stage = p.get("stage", "")
                miles = p.get("miles", "")
                emotion = p.get("emotion", "")
                strategy = p.get("strategy", "")
                items.append(
                    f"<tr><td><strong>{stage}</strong></td><td>{miles}</td>"
                    f"<td>{emotion}</td><td>{strategy}</td></tr>"
                )
        if items:
            landmark_html = f"""<h3>Psychological Landmarks</h3>
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Stage</th><th>Miles</th><th>Emotion</th><th>Strategy</th></tr></thead>
  <tbody>{''.join(items)}</tbody>
  </table>
  </div>"""

    return f"""<section id="section-10" class="gg-section">
  <h2>10 &middot; Mental Preparation</h2>

  <p>A {race_distance}-mile race is as much a mental challenge as a physical one.
  Your body will want to quit before it needs to. Your brain will lie to you about how bad it is.
  Having a mental strategy is not optional.</p>

  {f'<div class="gg-module gg-blackpill"><div class="gg-label">THE DARK MILE</div><p>Around mile {dark_mile}, most riders hit their lowest point. This is normal. It passes. Have a plan for it.</p></div>' if dark_mile else ''}

  <h3>The 6-2-7 Breathing Technique</h3>
  <p>When things get hard (and they will), use this breathing pattern:</p>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-card__value">6s</div>
      <div class="stat-card__label">Inhale</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">2s</div>
      <div class="stat-card__label">Hold</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">7s</div>
      <div class="stat-card__label">Exhale</div>
    </div>
  </div>

  <p>Deep belly breath through the nose. Brief pause at the top. Slow, controlled exhale through
  the mouth. Longer exhale = parasympathetic activation.</p>
  <p><strong>When to use:</strong> Before the start, during long climbs, when you want to quit, at aid stations, during the dark mile.</p>

  <h3>Process Goals vs Outcome Goals</h3>
  <ul>
  <li><strong>Bad goal:</strong> "Finish in under 8 hours." (You can't control weather, mechanicals, or how you feel.)</li>
  <li><strong>Good goal:</strong> "Fuel every 30 minutes. Stay in my zones. Ride my race." (100% within your control.)</li>
  </ul>
  <p>On race day, focus exclusively on process goals. Check in every 30 minutes: Am I fueling? Am I hydrating? Am I in my zone? If yes, you're having a perfect race regardless of the clock.</p>

  <h3>Mantras That Work</h3>
  <p>Pick 2-3 short phrases and practice them in training. Say them out loud on hard efforts.</p>
  <ul>
  <li>"This is what I trained for."</li>
  <li>"One pedal stroke at a time."</li>
  <li>"I've done harder things than this."</li>
  <li>"Fuel, hydrate, breathe. Repeat."</li>
  </ul>

  {landmark_html}

  <h3>The Quit Test</h3>
  <p>When you want to quit during the race (you will), ask yourself these three questions:</p>
  <ol>
  <li><strong>Have I eaten in the last 30 minutes?</strong> If no, eat first. You might just be bonking.</li>
  <li><strong>Have I been drinking?</strong> If no, drink 500ml. Dehydration mimics exhaustion.</li>
  <li><strong>Am I actually injured or just uncomfortable?</strong> Discomfort is part of the race. Actual injury (sharp pain, swelling) is a reason to stop.</li>
  </ol>
  <p>If you've eaten, hydrated, and aren't injured &mdash; keep going. The feeling will pass.</p>
</section>"""


def _section_race_week(race_data: Dict, tier: str, race_name: str, derived: Dict = None):
    # Coach review (Jun 2026): NO day-by-day race-week schedule here — the
    # taper schedule lives in the training plan. This section is the
    # checklist and the principles.
    return f"""<section id="section-11" class="gg-section">
  <h2>11 &middot; Race Week</h2>

  <p>Race week is about arriving at the start line fresh, confident, and prepared.
  You cannot gain fitness in the last week. You CAN lose it by doing too much.
  Your plan has the taper schedule &mdash; follow it. The principles below are what the
  schedule is protecting.</p>

  <h3>Race Week Principles</h3>
  <ul>
  <li><strong>No fitness tests.</strong> The urge to "check the legs" with one more hard effort spends race-day matches. Heavy legs mid-week are the taper working, not fitness leaving.</li>
  <li><strong>Nothing new.</strong> No new equipment, food, or routines. Race week is execution, not experimentation.</li>
  <li><strong>Front-load the logistics.</strong> Bike serviced, gear laid out, and bags packed early in the week &mdash; the night before is for sleeping, not wrenching.</li>
  <li><strong>Sleep is cumulative.</strong> Bank 8-9 hours per night all week. The night before the race is usually bad for everyone &mdash; it also matters least if the week was good.</li>
  </ul>

  <h3>Pre-Race Checklist</h3>
  <ul>
  <li>Bike serviced and in race-ready condition (do this by mid-week, not the night before)</li>
  <li>Tire pressure set for conditions (lower for gravel: 30-40 PSI depending on tire width)</li>
  <li>Nutrition packed and tested (same brands/products used in training)</li>
  <li>Bottles filled with your tested hydration mix</li>
  <li>Drop bags prepared (if applicable)</li>
  <li>Race number attached to bike or person</li>
  <li>Phone charged, emergency contacts accessible</li>
  <li>Weather checked &mdash; have a Plan B for layers</li>
  <li>Know aid station locations and what they provide</li>
  <li>Alarm set with buffer time (be at the start 45 minutes early)</li>
  </ul>

  <div class="gg-module gg-tactical">
    <div class="gg-label">CARB LOADING DONE RIGHT</div>
    <p>Carb loading starts 2-3 days before the race. Increase carb intake to 8-10g/kg body weight.
    This isn't "eat everything in sight" &mdash; it's strategically increasing the carb portion of normal meals.
    Rice, pasta, bread, potatoes, fruit. Reduce fiber and fat intake to avoid GI issues.</p>
  </div>
</section>"""

def _section_race_day(race_data: Dict, tier: str, race_distance, race_name: str, weekly_hours: str = ""):
    dr_hours = race_data.get("dress_rehearsal_hours", {})
    tier_dr = dr_hours.get(tier)

    # Cap dress rehearsal to what the athlete can actually do
    _, max_hrs = _parse_hours_range(weekly_hours)
    lr_ceiling = max_hrs * 0.6 if max_hrs > 0 else 0  # generous ceiling for a one-off big effort

    dr_html = ""
    if tier_dr:
        if lr_ceiling > 0 and tier_dr > lr_ceiling:
            # Dress rehearsal exceeds what's realistic — reframe
            realistic_hrs = f"{lr_ceiling:.0f}-{min(lr_ceiling + 1, tier_dr):.0f}"
            dr_html = f"""<div class="gg-module gg-alert"><div class="gg-label">DRESS REHEARSAL</div>
<p>Before taper, complete your <strong>longest training ride ({realistic_hrs} hours)</strong>
simulating race conditions. Your weekly budget limits ride length, so make this ride count:
same nutrition plan, same pacing strategy, same equipment you'll use on race day.
Practice your exact fueling protocol at race-day intensity. If something fails in the
dress rehearsal, fix it before race day.</p></div>"""
        else:
            dr_html = f"""<div class="gg-module gg-alert"><div class="gg-label">DRESS REHEARSAL</div>
<p>Before taper, complete a {tier_dr}-hour ride
simulating race conditions. Same nutrition, same pacing, same equipment.
If something fails in the dress rehearsal, fix it before race day.</p></div>"""

    decisions = race_data.get("race_specific", {}).get("in_race_decision_tree", {})
    decision_cards = []
    for scenario, advice in decisions.items():
        label = scenario.replace("_", " ").title()
        if isinstance(advice, dict):
            action = advice.get("action", str(advice))
        elif isinstance(advice, list):
            action = '</li><li>'.join(str(a) for a in advice)
            action = f'<ol><li>{action}</li></ol>'
        else:
            action = str(advice)
        decision_cards.append(f'  <div class="data-card"><div class="data-card__header">IF: {label.upper()}</div><div class="data-card__content"><p>{action}</p></div></div>')
    decision_html = "\n".join(decision_cards) if decision_cards else ""

    return f"""<section id="section-12" class="gg-section">
  <h2>12 &middot; Race Day</h2>

  {dr_html}

  <h3>Race Morning Timeline</h3>
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Time</th><th>Action</th></tr></thead>
  <tbody>
  <tr><td><strong>3 hours before</strong></td><td>Wake up. Pre-race meal: 400-600 cal, low fiber/fat. Coffee if you normally drink it.</td></tr>
  <tr><td><strong>2 hours before</strong></td><td>Sip 500ml water + electrolytes. Get dressed. Apply sunscreen and chamois cream.</td></tr>
  <tr><td><strong>1 hour before</strong></td><td>Arrive at start. Check tire pressure. Warm up: 10-15 min easy spin with 2x30sec openers.</td></tr>
  <tr><td><strong>30 min before</strong></td><td>Final bathroom stop. Eat a gel or banana. Get in position.</td></tr>
  <tr><td><strong>10 min before</strong></td><td>6-2-7 breathing. Visualize your process goals. You're ready.</td></tr>
  <tr class="race-day-row"><td><strong>GO</strong></td><td>Start conservative. First hour at 5% below target. Let others blow up &mdash; you'll pass them later.</td></tr>
  </tbody>
  </table>
  </div>

  <h3>Race Execution Strategy</h3>
  <ul>
  <li><strong>First 25% of race:</strong> Hold back. Ride 5% below target power/effort. Bank energy.</li>
  <li><strong>Middle 50% of race:</strong> Settle into target effort. Fuel relentlessly. Every 20-30 minutes.</li>
  <li><strong>Final 25% of race:</strong> If you feel good, increase effort slightly. If you're struggling, maintain. Do not blow up.</li>
  <li><strong>Fueling alarm:</strong> Set a recurring timer for every 20 minutes. Eat whether you feel like it or not.</li>
  </ul>

  <div class="gg-module gg-blackpill">
    <div class="gg-label">THE GOLDEN RULE</div>
    <p>Start slower than you think you should.
    Every experienced endurance racer will tell you the same thing: the race doesn't start until
    the last third. Everyone goes out too hard. Be the one who doesn't.</p>
  </div>

  {f'<h3>In-Race Decision Tree</h3><p>When things go wrong (and something always does), use these protocols:</p>{decision_html}' if decision_html else ''}

  <h3>Post-Race</h3>
  <ul>
  <li>Drink 1L fluid within 30 minutes of finishing</li>
  <li>Eat a real meal within 60 minutes (protein + carbs + fat)</li>
  <li>Light walking to keep blood flowing</li>
  <li>No training for 3-5 days minimum</li>
  <li>Celebrate. You just raced {_race_display(race_name, race_distance)}. That's not nothing.</li>
  </ul>
</section>"""


def _section_skills(race_data: Dict, discipline: str = "gravel") -> str:
    """Skills chapter — dispatched by discipline so a road athlete gets road
    skills, not gravel-cornering drills."""
    disc = (discipline or "gravel").lower()
    if disc == "road":
        return _section_road_skills(race_data)
    if disc == "mtb":
        return _section_mtb_skills(race_data)
    return _section_gravel_skills(race_data)


def _section_mtb_skills(race_data: Dict) -> str:
    """Section 13: mountain-bike skills — singletrack-specific handling. An MTB
    racer needs trail technique (line choice, drops, switchbacks, braking
    traction), not gravel-road cornering or road pack craft."""
    return """<section id="section-13" class="gg-section">
  <h2>13 &middot; Mountain Bike Skills</h2>

  <p>Cross-country racing is won on the technical sections as much as the climbs. A rider who
  carries speed through rock gardens and rails switchbacks saves matches that a stronger but
  clumsy rider burns. Trail skills are trainable &mdash; ride the hard features deliberately
  until they stop costing you watts.</p>

  <h3>Body Position &amp; Vision</h3>
  <div class="data-card">
    <div class="data-card__header">THE ATTACK POSITION</div>
    <div class="data-card__content">
      <ul>
        <li>Out of the saddle on descents and techy ground: knees and elbows bent, weight centred, heels dropped.</li>
        <li>Let the bike move beneath you &mdash; stay loose so the suspension and tyres can track the trail.</li>
        <li>Look 3&ndash;5 seconds ahead to the exit of a feature, never down at the front wheel. The bike goes where you look.</li>
        <li>Pick your line early and commit. Hesitation in a rock garden is how you wash out.</li>
      </ul>
    </div>
  </div>

  <h3>Braking &amp; Traction</h3>
  <div class="data-card">
    <div class="data-card__header">CONTROL ON LOOSE GROUND</div>
    <div class="data-card__content">
      <ul>
        <li>Brake BEFORE the feature, not in it. Set your speed early, then roll through off the brakes.</li>
        <li>One or two fingers on each lever &mdash; modulate, don't grab. A locked wheel slides; a rolling wheel steers.</li>
        <li>Favour the front brake for stopping power, but ease it on loose or steep ground to keep the front from washing.</li>
        <li>On climbs, stay seated for rear-wheel traction and meter your power so the tyre doesn't spin.</li>
      </ul>
    </div>
  </div>

  <h3>Switchbacks &amp; Cornering</h3>
  <div class="data-card">
    <div class="data-card__header">TIGHT TURNS AT SPEED</div>
    <div class="data-card__content">
      <ul>
        <li>Outside foot down and weighted; drive your weight through the outside pedal to load the tyres.</li>
        <li>Look through the corner to the exit. Lean the bike more than your body on flat, loose turns.</li>
        <li>On tight switchbacks, set up wide, brake before the apex, then pivot the front wheel and accelerate out.</li>
        <li>Use any berm &mdash; it's free grip. Stay high on the entry and let the banking turn you.</li>
      </ul>
    </div>
  </div>

  <h3>Drops, Roots &amp; Rock Gardens</h3>
  <div class="data-card">
    <div class="data-card__header">CARRYING SPEED THROUGH CHATTER</div>
    <div class="data-card__content">
      <ul>
        <li>Speed is your friend in rough ground &mdash; momentum carries you over chatter that traps a slow wheel.</li>
        <li>Approach roots and rocks square-on where you can; a wet root hit at an angle is the classic crash.</li>
        <li>For small drops, push the bars forward and let the bike come to you &mdash; land both wheels or rear-first, never nose-down.</li>
        <li>Ratchet your pedals (half-strokes) through tight rocky sections to avoid clipping a pedal.</li>
      </ul>
    </div>
  </div>

  <h3>Trail Drills</h3>
  <p>Fifteen minutes of skills per week builds race-day confidence.</p>
  <ul>
    <li><strong>Track stand:</strong> balance stationary on a slight rise &mdash; builds the slow-speed control that saves techy climbs.</li>
    <li><strong>Front-wheel lifts:</strong> manual the front wheel up over a line on flat ground; the foundation for clearing roots and ledges.</li>
    <li><strong>Cornering laps:</strong> a known loose bend, increasing entry speed each lap until the tyres start to drift.</li>
    <li><strong>Repeat the feature:</strong> session the one rock garden or switchback that scares you until it's automatic.</li>
  </ul>
</section>"""


def _section_road_skills(race_data: Dict) -> str:
    """Section 13: road-racing skills — the road counterpart to the gravel
    skills chapter. Pack craft, descending, and cornering on tarmac."""
    return """<section id="section-13" class="gg-section">
  <h2>13 &middot; Road Skills</h2>

  <p>Road racing rewards bike-handling and positioning as much as fitness. A rider who can
  hold a wheel, corner at speed, and read a group will beat a stronger rider who burns matches
  fighting for position. These skills are trainable &mdash; practice them deliberately.</p>

  <h3>Riding in the Pack</h3>
  <div class="data-card">
    <div class="data-card__header">HOLDING A WHEEL</div>
    <div class="data-card__content">
      <ul>
        <li>Sit 30&ndash;60cm off the wheel in front &mdash; close enough to draft (20&ndash;30% energy saving), far enough to react.</li>
        <li>Look through and past the rider ahead, not at their wheel. Your bike follows your eyes.</li>
        <li>Match speed with the brakes feathered, not grabbed &mdash; surging and braking is how gaps and crashes start.</li>
        <li>Never overlap your front wheel with someone's rear wheel. A small swerve takes you down.</li>
      </ul>
    </div>
  </div>
  <div class="data-card">
    <div class="data-card__header">POSITIONING &amp; CROSSWINDS</div>
    <div class="data-card__content">
      <ul>
        <li>Stay in the front third before climbs, corners, and crosswind sections &mdash; moving up costs energy, getting shelled costs the race.</li>
        <li>In a crosswind the draft is diagonal: shelter sits behind and to the leeward side, forming echelons. Know which side the wind is from.</li>
        <li>Move up on the sheltered side and at the front of surges, not by fighting through the gutter.</li>
      </ul>
    </div>
  </div>

  <h3>Cornering on Tarmac</h3>
  <div class="data-card">
    <div class="data-card__header">THE FAST LINE</div>
    <div class="data-card__content">
      <ul>
        <li>Brake in a straight line BEFORE the corner; be off the brakes by the apex.</li>
        <li>Outside-in-outside: enter wide, clip the apex, drift out. Outside foot down and weighted.</li>
        <li>Look at the exit, not the apex. In a group, hold your line &mdash; predictability keeps everyone upright.</li>
        <li>In the wet, brake earlier and lean less; paint, manhole covers, and oil are ice.</li>
      </ul>
    </div>
  </div>

  <h3>Descending</h3>
  <div class="data-card">
    <div class="data-card__header">SPEED WITH CONTROL</div>
    <div class="data-card__content">
      <ul>
        <li>Hands in the drops &mdash; lower centre of gravity and full brake leverage.</li>
        <li>Feather both brakes before corners; trail off as you tip in. Don't brake mid-corner.</li>
        <li>Relax your upper body. A tense rider fights the bike; a loose rider lets it track.</li>
        <li>On a known descent, scout the tight corners. On an unknown one, ride within sight lines.</li>
      </ul>
    </div>
  </div>

  <h3>Handling Drills</h3>
  <p>Ten minutes of drills per week builds race-day confidence.</p>
  <ul>
    <li><strong>Bottle grabs:</strong> reach for your bottle while holding a straight line. Both hands, eyes up.</li>
    <li><strong>Shoulder rubs:</strong> with a trusted rider, lean shoulder-to-shoulder on grass at low speed &mdash; contact stops being scary.</li>
    <li><strong>Cornering laps:</strong> a quiet bend, increasing entry speed each lap until you find the limit. No traffic, no heroics.</li>
    <li><strong>Paceline rotation:</strong> with a small group, practise smooth through-and-off so pulls are even and seamless.</li>
  </ul>
</section>"""


def _section_gravel_skills(race_data: Dict) -> str:
    """Section 15: Gravel-specific skills and technique guidance."""
    terrain = race_data.get("race_characteristics", {}).get("terrain", "gravel")
    tech_diff = race_data.get("race_characteristics", {}).get("technical_difficulty", "moderate")
    surface_hazards = race_data.get("race_specific", {}).get("surface_hazards", [])

    hazard_html = ""
    if surface_hazards:
        items = "\n".join(f"<li>{h}</li>" for h in surface_hazards)
        hazard_html = f"""<h3>Course-Specific Surface Hazards</h3>
  <ul>{items}</ul>"""

    return f"""<section id="section-13" class="gg-section">
  <h2>13 &middot; Gravel Skills</h2>

  <p>Gravel racing rewards skill as much as fitness. A technically proficient rider at 3.5 W/kg
  will beat a 4.0 W/kg rider who can't handle loose corners or descents. These skills are
  trainable &mdash; but only if you practice them deliberately, not just ride through them.</p>

  <h3>Cornering on Loose Surfaces</h3>

  <div class="data-card">
    <div class="data-card__header">THE WEIGHT SHIFT</div>
    <div class="data-card__content">
      <p>On loose gravel, your front tire has less grip than on pavement. To corner safely:</p>
      <ul>
        <li>Drop your outside foot to 6 o'clock position</li>
        <li>Load the outside pedal &mdash; it does 60-70% of the work. Hands stay quiet; the inside hand should feel almost empty</li>
        <li>Keep the bike more upright than you would on pavement</li>
        <li>Look where you want to go &mdash; not at the obstacle you want to avoid</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">SPEED MANAGEMENT</div>
    <div class="data-card__content">
      <p>All braking happens BEFORE the corner, not in it. On gravel:</p>
      <ul>
        <li>Brake early and progressively &mdash; no grabbing</li>
        <li>Release brakes before the apex</li>
        <li>Use both brakes &mdash; roughly 70/30 front-to-rear on hardpack, 65/35 on loose gravel; only mud and deep sand approach 50/50</li>
        <li>If the rear slides, do NOT grab the front brake</li>
      </ul>
    </div>
  </div>

  <h3>Descending on Gravel</h3>

  <div class="data-card">
    <div class="data-card__header">BODY POSITION</div>
    <div class="data-card__content">
      <ul>
        <li>Hands in the drops &mdash; maximum brake leverage and control</li>
        <li>Elbows and knees slightly bent &mdash; act as suspension</li>
        <li>Weight shifted back on steep descents (hips behind saddle)</li>
        <li>One finger on each brake lever &mdash; maintain modulation</li>
        <li>Eyes scanning 15-20 feet ahead, not right in front of the tire</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">LINE SELECTION</div>
    <div class="data-card__content">
      <ul>
        <li>Smoother surface = faster, even if it's a longer line</li>
        <li>Avoid loose marbles on hardpack &mdash; ride the packed line</li>
        <li>On washboard: either go fast enough to float or slow enough to absorb</li>
        <li>Ruts: commit to being in or out &mdash; straddling a rut is how you crash</li>
      </ul>
    </div>
  </div>

  <h3>Climbing on Gravel</h3>

  <div class="data-card">
    <div class="data-card__header">TRACTION MANAGEMENT</div>
    <div class="data-card__content">
      <p>Loose climbs are where most riders lose time. The key is steady, smooth power:</p>
      <ul>
        <li>Stay seated as long as possible &mdash; standing reduces rear traction</li>
        <li>Smooth pedal stroke &mdash; no surges, no mashing</li>
        <li>Higher cadence (75-85 rpm) reduces torque spikes that break traction</li>
        <li>Shift BEFORE you need to &mdash; shifting under load on gravel causes chain drops</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">WHEN TO STAND</div>
    <div class="data-card__content">
      <ul>
        <li>Only on hardpack or very short steep pitches</li>
        <li>When standing: keep weight forward, hands light on bars</li>
        <li>Shift to a harder gear before standing to maintain momentum</li>
        <li>If rear tire spins, sit immediately &mdash; you've lost traction</li>
      </ul>
    </div>
  </div>

  <h3>Bike Handling Drills</h3>
  <p>Practice these weekly during easy rides. 10 minutes of drills per ride builds race-day confidence.</p>
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Drill</th><th>How</th><th>Why</th><th>Time</th></tr></thead>
  <tbody>
  <tr><td><strong>Slow Speed Balance</strong></td><td>Ride as slowly as possible without putting a foot down. Figure-8s in a parking lot.</td><td>Balance and core stability at low speeds &mdash; critical for technical sections.</td><td>3 min</td></tr>
  <tr><td><strong>One-Hand Riding</strong></td><td>Ride with one hand on the bars, other on your thigh. Alternate every 30 seconds.</td><td>Eating, drinking, and adjusting kit while riding gravel requires single-hand confidence.</td><td>2 min each hand</td></tr>
  <tr><td><strong>Bunny Hops</strong></td><td>Practice lifting both wheels over a stick or line on the ground. Don't need height &mdash; just timing.</td><td>Clearing obstacles (sticks, rocks, cattle guards) without stopping or swerving.</td><td>3 min</td></tr>
  <tr><td><strong>Emergency Stop</strong></td><td>Ride at moderate speed, then stop as quickly as possible using both brakes. Practice on gravel and pavement.</td><td>Knowing your stopping distance on different surfaces. Muscle memory for panic stops.</td><td>2 min</td></tr>
  <tr><td><strong>Track Stand</strong></td><td>Come to a stop and balance without putting a foot down. Start with slight uphill.</td><td>Group rides, aid stations, and intersections without unclipping.</td><td>2 min</td></tr>
  </tbody>
  </table>
  </div>

  {hazard_html}

  <h3>Tire Pressure for Gravel</h3>
  <p>Tire pressure is the single biggest performance variable on gravel &mdash; more impactful than
  any component upgrade you can buy.</p>

  <div class="data-card">
    <div class="data-card__header">GENERAL GUIDELINES</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Tubeless:</strong> Always run tubeless for gravel. Period.</li>
        <li><strong>38-42mm tires:</strong> 28-35 PSI for most riders</li>
        <li><strong>45-50mm tires:</strong> 25-30 PSI for most riders</li>
        <li><strong>Lighter riders (&lt;150 lbs):</strong> 2-4 PSI less than above</li>
        <li><strong>Heavier riders (&gt;180 lbs):</strong> 2-4 PSI more than above</li>
        <li><strong>Rear tire:</strong> 2-3 PSI more than front (more weight)</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">CONDITIONS ADJUSTMENTS</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Wet/muddy:</strong> Drop 2-3 PSI for grip</li>
        <li><strong>Dry hardpack:</strong> Can run 2-3 PSI higher for speed</li>
        <li><strong>Rocky/chunky:</strong> Drop 2-3 PSI to absorb impacts and prevent pinch flats</li>
        <li><strong>Mixed surface:</strong> Optimize for the worst surface you'll encounter</li>
      </ul>
    </div>
  </div>

  <div class="gg-module gg-alert">
    <div class="gg-label">TEST YOUR PRESSURE BEFORE RACE DAY</div>
    <p>Find your sweet spot by testing different pressures during long training rides. Drop 2 PSI
    at a time and note how the bike feels. Too low = squirmy in corners, too high = harsh and bouncy.
    The right pressure feels fast AND confident. Write it down. Use that pressure on race day.</p>
  </div>

  <h3>Mechanical Skills</h3>
  <p>You must be self-sufficient on gravel. There are no team cars. Practice these before race day:</p>
  <ul>
    <li><strong>Flat repair:</strong> Fix a flat (tube or tubeless) in under 5 minutes. Practice at home.</li>
    <li><strong>Chain repair:</strong> Know how to use a chain tool. Carry a quick link.</li>
    <li><strong>Derailleur adjustment:</strong> Know how to adjust limit screws if your derailleur gets hit.</li>
    <li><strong>Tire plug:</strong> Practice plugging a tubeless tire with a plug kit. It takes 30 seconds once you've done it.</li>
  </ul>

  <div class="gg-module gg-tactical">
    <div class="gg-label">THE 5-MINUTE RULE</div>
    <p>If you can't fix it in 5 minutes, you can't fix it on the course. The skills above cover
    95% of mechanicals. The other 5% (cracked frame, destroyed wheel) require a ride to the nearest
    aid station. Carry a phone and know the course map.</p>
  </div>

  <h3>What to Carry on Race Day</h3>
  <p>Pack these the night before. Check them at the start line. No exceptions.</p>

  <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
    <div class="data-card">
      <div class="data-card__header">ON THE BIKE</div>
      <div class="data-card__content">
        <ul>
          <li>2 water bottles (filled with electrolyte mix)</li>
          <li>Frame bag or saddle bag with repair kit</li>
          <li>Cycling computer with route loaded</li>
        </ul>
      </div>
    </div>
    <div class="data-card">
      <div class="data-card__header">REPAIR KIT</div>
      <div class="data-card__content">
        <ul>
          <li>Spare tube (correct size and valve type)</li>
          <li>Tubeless plug kit (Dynaplug or similar)</li>
          <li>2x CO2 cartridges + inflator head</li>
          <li>Tire lever (just one is fine)</li>
          <li>Multi-tool with chain breaker</li>
          <li>Quick link for your chain</li>
        </ul>
      </div>
    </div>
    <div class="data-card">
      <div class="data-card__header">NUTRITION</div>
      <div class="data-card__content">
        <ul>
          <li>Gels/chews for first 2 hours (tested in training)</li>
          <li>Solid food for hours 3+ (rice cakes, bars)</li>
          <li>Electrolyte tabs for refills at aid stations</li>
          <li>Emergency caffeine gel for the final push</li>
        </ul>
      </div>
    </div>
    <div class="data-card">
      <div class="data-card__header">SAFETY</div>
      <div class="data-card__content">
        <ul>
          <li>Fully charged phone in waterproof case</li>
          <li>Emergency contact card in jersey pocket</li>
          <li>Cash or card (some aid stations are gas stations)</li>
          <li>Sunscreen applied before the start</li>
        </ul>
      </div>
    </div>
  </div>
</section>"""



def _section_masters_training(profile: Dict, derived: Dict, section_num: int = 17) -> str:
    """Masters training — conditional on age >= 40.
    Content sourced from gravel-plans-experimental Compete Masters template
    and existing masters plan guides. Section number is dynamic."""
    age = profile.get("demographics", {}).get("age", 50)
    is_masters = derived.get("is_masters", False)  # age >= 50

    # Recovery spacing recommendation based on age
    if int(age) >= 55:
        hard_spacing = "72 hours minimum"
        recovery_freq = "every 2-3 weeks"
        muscle_loss = f"~{int(age) - 39}% cumulative since age 40"
    elif int(age) >= 50:
        hard_spacing = "48-72 hours"
        recovery_freq = "every 3 weeks"
        muscle_loss = f"~{int(age) - 39}% cumulative since age 40"
    else:
        hard_spacing = "48 hours minimum"
        recovery_freq = "every 3 weeks (rather than the standard 4)"
        muscle_loss = "beginning to accelerate"

    hrmax_est = round(211 - (0.64 * int(age)))

    return f"""<section id="section-{section_num}" class="gg-section">
  <h2>{section_num} &middot; Masters Training Considerations</h2>

  <p>At {age}, your physiology is different from a 25-year-old's. Not worse &mdash; different. Understanding
  these differences is the key to training smarter and racing faster than athletes who ignore them.</p>

  <p>Masters athletes can build exceptional race fitness. But the path there requires adjusting <em>how</em>
  you train, not <em>how much</em>.</p>

  <div class="gg-module gg-blackpill">
    <div class="gg-label">THE MASTERS REALITY</div>
    <p>Don't chase numbers from 10 years ago. Today's FTP is your training anchor. Progress is progress,
    regardless of absolute watts. The athlete who trains consistently at their current level will always
    beat the one who overreaches trying to recapture past glory.</p>
    <p>And you can't wing it anymore &mdash; that's the real change. At 25 you could skip sleep, skip the
    warm-up, ride hard three days straight, and get away with it. Past 50 the margin is gone: repair runs
    slower, and one careless week compounds. The riders who stay fast aren't the most talented &mdash;
    they're the ones who stopped improvising. This plan is the not-winging-it. Run the system;
    don't negotiate with it.</p>
  </div>

  <h3>What Changes After 40</h3>

  <div class="data-card">
    <div class="data-card__header">RECOVERY</div>
    <div class="data-card__content">
      <p>This is the single biggest change. Recovery takes longer &mdash; not dramatically, but meaningfully.</p>
      <ul>
        <li><strong>Hard session spacing:</strong> {hard_spacing} between high-intensity sessions (vs. 24-48 for younger athletes)</li>
        <li><strong>Recovery weeks:</strong> {recovery_freq}</li>
        <li><strong>Sleep:</strong> 8+ hours is non-negotiable for adaptation. Your body no longer bounces back from 6-hour nights.</li>
        <li><strong>Two easy days between hard sessions</strong> is often optimal. Don't feel guilty about easy days &mdash; they're building fitness.</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">MUSCLE MASS &amp; STRENGTH</div>
    <div class="data-card__content">
      <p>Muscle mass declines approximately 1% per year after age 40. At {age}, that's {muscle_loss}.
      This affects power output, bone density, metabolic rate, and injury resilience.</p>
      <p><strong>Strength training is not optional for masters athletes &mdash; it's mandatory.</strong></p>
      <ul>
        <li>2x/week minimum during base phase, 1x/week during build/peak</li>
        <li>Focus on: single-leg work (lunges, step-ups), deadlifts, squats, core stability</li>
        <li>Heavy enough to challenge (6-10 rep range), not bodyweight circuits</li>
        <li>Benefits beyond power: improved hormone regulation, insulin sensitivity, bone density, body composition</li>
      </ul>
      <p>If you're 40+, strength training isn't optional &mdash; it's mandatory for long-term athletic health.
      Your future self &mdash; the one still racing at 50, 60, 70 &mdash; will thank you.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">VO2MAX &amp; CARDIOVASCULAR</div>
    <div class="data-card__content">
      <p>VO2max declines ~1% per year after 30, but this rate is <strong>trainable</strong>. Masters athletes
      who maintain high-intensity training lose VO2max at roughly half the rate of sedentary peers.</p>
      <ul>
        <li><strong>Keep intensity in the plan:</strong> You need fewer hard sessions, but you still need them</li>
        <li><strong>Quality over quantity:</strong> 2 hard sessions/week is typically optimal (vs. 3-4 for younger athletes)</li>
        <li><strong>VO2max intervals remain critical:</strong> 3-5 minute efforts at 106-120% FTP maintain top-end fitness</li>
        <li><strong>Estimated HRmax at age {age}:</strong> ~{hrmax_est} bpm (formula: 211 - 0.64 &times; age). Use actual measured max if available.</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">FUELING, ALCOHOL &amp; HEAT</div>
    <div class="data-card__content">
      <p>Recovery past 50 isn't just spacing and sleep &mdash; it's what you give the repair process to work with.</p>
      <ul>
        <li><strong>Protein, spread out:</strong> aim for 1.6&ndash;2.0 g per kg of bodyweight daily, split across
        meals rather than crammed at dinner. Older muscle responds less to small doses &mdash; each meal needs a
        real serving. Prioritize it after strength days and long rides.</li>
        <li><strong>Drink less. Blunt on purpose:</strong> alcohol hits masters athletes twice &mdash; it wrecks the
        deep sleep recovery depends on and blunts the overnight repair you now need more of, not less. You don't
        have to be a monk, but the nightly-glasses habit quietly taxes every hard session you do. Race-month
        sobriety is the cheapest upgrade in this guide.</li>
        <li><strong>Respect heat more than you used to:</strong> thermoregulation declines quietly with age. On hot
        training days and hot races, drink earlier, ease pace sooner, and treat cooling as part of the workout
        &mdash; not an admission of anything.</li>
      </ul>
    </div>
  </div>

  <h3>Training Approach: HRV-Guided Polarized</h3>
  <p>The recommended approach for masters athletes is polarized training with HRV-guided intensity:
  80% easy, 20% hard, with recovery driving the schedule.</p>

  <div class="data-card">
    <div class="data-card__header">HOW THIS WORKS IN PRACTICE</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Easy means truly easy.</strong> Zone 1-2 only. If you can't hold a conversation, you're going too hard.
        Polarized only works if easy days are truly easy.</li>
        <li><strong>Hard means genuinely hard.</strong> When you do go hard, commit fully. Zone 4-5. No "moderate" efforts.</li>
        <li><strong>Skip the gray zone.</strong> Zone 3 (tempo) is recovery-expensive for masters athletes. Use it strategically, not constantly.
        Threshold work costs more recovery than it's worth in most training weeks.</li>
        <li><strong>High cadence on intensity:</strong> 95-105 rpm on hard efforts reduces muscular strain and improves recovery.
        This matters more as you age &mdash; grinding at 70 rpm creates more muscle damage per watt.</li>
        <li><strong>Listen to HRV trends:</strong> If your 7-day HRV average drops more than 10% below baseline,
        convert the next hard session to easy. Your body is telling you it hasn't recovered.</li>
      </ul>
    </div>
  </div>

  <h3>Practical Adjustments</h3>

  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Area</th><th>Under 40</th><th>Masters (40+)</th></tr></thead>
  <tbody>
  <tr><td><strong>Hard sessions/week</strong></td><td>3-4</td><td>2 (occasionally 3 if well-recovered)</td></tr>
  <tr><td><strong>Days between hard sessions</strong></td><td>1-2</td><td>2-3</td></tr>
  <tr><td><strong>Recovery week frequency</strong></td><td>Every 4 weeks</td><td>Every 3 weeks</td></tr>
  <tr><td><strong>Sleep requirement</strong></td><td>7-8 hours</td><td>8+ hours (non-negotiable)</td></tr>
  <tr><td><strong>Strength training</strong></td><td>Recommended</td><td>Mandatory (2x/week)</td></tr>
  <tr><td><strong>Cadence on intervals</strong></td><td>Self-selected</td><td>High (95-105 rpm)</td></tr>
  <tr><td><strong>Zone 3 usage</strong></td><td>Moderate</td><td>Minimal (recovery-expensive)</td></tr>
  <tr><td><strong>Warmup duration</strong></td><td>10-15 min</td><td>15-20 min (longer warmup, better performance)</td></tr>
  <tr><td><strong>Daily protein</strong></td><td>Whatever happens</td><td>1.6-2.0 g/kg, spread across meals</td></tr>
  <tr><td><strong>Alcohol</strong></td><td>Costs you a little</td><td>Costs you double &mdash; minimal in training, near-zero race month</td></tr>
  </tbody>
  </table>
  </div>

  <div class="gg-module gg-tactical">
    <div class="gg-label">THE MASTERS ADVANTAGE</div>
    <p>You have something younger athletes don't: decades of experience, mental toughness, and the discipline
    to actually follow a plan. Masters athletes are typically more consistent, better at pacing, and less
    likely to do something stupid on race day. Your body may recover slower, but your brain makes better
    decisions. Use that.</p>
  </div>

  <h3>Injury Prevention</h3>
  <ul>
    <li><strong>Warmup is mandatory:</strong> 15-20 minutes progressive warmup before any intensity. Cold muscles + age = injury risk.</li>
    <li><strong>Mobility work:</strong> 10 minutes daily. Hip flexors, hamstrings, thoracic spine. Cycling creates tightness that compounds with age.</li>
    <li><strong>Don't ignore pain:</strong> "Working through it" is for 20-year-olds. At {age}, persistent pain means something needs attention.
    Address it early or it becomes a season-ending problem.</li>
    <li><strong>Bike fit review:</strong> Bodies change. A fit from 5 years ago may no longer be optimal. Get reassessed annually.</li>
  </ul>

  <h3>The Bottom Line</h3>
  <p>Train smarter, not just harder. Prioritize recovery. Lift heavy things. Sleep more.
  Don't compare yourself to your 25-year-old self &mdash; compare yourself to other {age}-year-olds, and
  you'll realize how far ahead you are just by having a structured plan.</p>
  <p>The athletes who race well into their 50s, 60s, and 70s are the ones who respect what their body
  needs today, not what it could handle a decade ago.</p>
</section>"""


def _section_altitude_training(race_data: Dict, race_name: str, elevation, section_num: int = 15) -> str:
    """Altitude training — conditional on elevation > 5000ft. Section number is dynamic."""
    meta = race_data.get("race_metadata", {})
    start_elev = meta.get("start_elevation_feet", 0) or 0
    avg_elev = meta.get("avg_elevation_feet", start_elev) or start_elev
    # The `elevation` arg is total CLIMBING — never use it as altitude.
    if not (start_elev or avg_elev):
        return ""  # no real altitude data: render nothing rather than nonsense

    # Power loss formula: ~1% per 1,000 feet above 3,000ft
    power_loss = round(max(0, (max(start_elev, avg_elev) - 3000) / 1000) * 1.0, 1)

    return f"""<section id="section-{section_num}" class="gg-section">
  <h2>{section_num} &middot; Altitude Training</h2>

  <p>{race_name} takes place at significant altitude. The start elevation is around {start_elev or avg_elev} feet,
  with racing at {avg_elev or start_elev}+ feet. This has real, measurable effects on performance that you
  cannot ignore.</p>

  <div class="gg-module gg-blackpill">
    <div class="gg-label">THE ALTITUDE REALITY</div>
    <p>At {avg_elev or start_elev} feet, expect approximately <strong>{power_loss}% reduction in FTP</strong> compared to sea level.
    Your heart rate will run higher at the same power output. RPE becomes unreliable &mdash; use a power meter.
    Recovery between efforts takes longer. Sleep quality may suffer for the first 2-3 nights.</p>
  </div>

  <h3>The Physiology</h3>
  <div class="data-card">
    <div class="data-card__header">WHAT ALTITUDE DOES TO YOUR BODY</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Reduced oxygen availability:</strong> At 7,000 ft, there's ~22% less oxygen per breath compared to sea level</li>
        <li><strong>Higher heart rate:</strong> Your heart pumps faster to compensate, running 5-15 bpm higher at same effort</li>
        <li><strong>Faster lactate accumulation:</strong> You reach threshold sooner with less absolute power</li>
        <li><strong>Impaired recovery:</strong> Between intervals, between efforts, between days &mdash; everything takes longer</li>
        <li><strong>Dehydration risk:</strong> Dry mountain air + increased respiration rate = faster fluid loss</li>
        <li><strong>Increased calorie burn:</strong> Your body works harder at altitude, burning 5-10% more calories</li>
      </ul>
    </div>
  </div>

  <h3>Power Loss by Elevation</h3>
  <div style="overflow-x: auto;">
  <table>
  <thead><tr><th>Elevation</th><th>FTP Reduction</th><th>Impact</th></tr></thead>
  <tbody>
  <tr><td>Sea level - 3,000 ft</td><td>0%</td><td>No significant effect</td></tr>
  <tr><td>3,000 - 5,000 ft</td><td>1-2%</td><td>Barely noticeable for most athletes</td></tr>
  <tr class="race-day-row"><td>5,000 - 7,000 ft</td><td>2-4%</td><td>Noticeable on hard efforts</td></tr>
  <tr class="race-day-row"><td>7,000 - 9,000 ft</td><td>4-6%</td><td>Significant &mdash; requires pacing adjustment</td></tr>
  <tr><td>9,000 - 11,000 ft</td><td>6-8%</td><td>Major impact &mdash; acclimatization critical</td></tr>
  <tr><td>11,000+ ft</td><td>8-12%+</td><td>Severe &mdash; multi-week acclimatization needed</td></tr>
  </tbody>
  </table>
  </div>

  <h3>Acclimatization Protocol</h3>

  <div class="data-card">
    <div class="data-card__header">IF YOU CAN ARRIVE EARLY (IDEAL: 10-14 DAYS BEFORE)</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Days 1-3:</strong> Easy activity only. Walk, light spin. Let your body adjust to breathing.</li>
        <li><strong>Days 4-7:</strong> Light training at reduced intensity (80% of normal power targets).</li>
        <li><strong>Days 8-14:</strong> Gradually return to normal training intensity. You'll feel closer to normal.</li>
        <li><strong>Key:</strong> Hydrate aggressively (3-4L/day), sleep extra, avoid alcohol.</li>
      </ul>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">IF YOU CAN'T ARRIVE EARLY (THE REALISTIC OPTION)</div>
    <div class="data-card__content">
      <p>Most athletes can't take 2 weeks off before a race. Here's how to mitigate:</p>
      <ul>
        <li><strong>Arrive as late as possible</strong> &mdash; 24-48 hours before is better than 3-5 days. The worst window is 2-5 days at altitude (past the adrenaline boost, before any adaptation).</li>
        <li><strong>Heat training provides crossover benefits:</strong> 10-14 days of heat exposure increases plasma volume and hemoglobin, partially mimicking altitude adaptation.</li>
        <li><strong>Pace conservatively:</strong> Start 10% below target power. Altitude punishes going too hard early more than sea-level racing does.</li>
        <li><strong>Hydrate aggressively:</strong> Start hydrating 48 hours before the race. Drink 500ml+ more than normal daily.</li>
      </ul>
    </div>
  </div>

  <h3>Heat Acclimatization Protocol (Altitude Crossover)</h3>
  <p>Heat acclimatization delivers <strong>5-8% performance improvements</strong> through plasma volume expansion,
  enhanced sweating, and reduced cardiovascular strain. Some of these adaptations directly help at altitude.</p>

  <div class="data-card">
    <div class="data-card__header">10-14 DAY HEAT PROTOCOL (WEEKS 6-10 OF YOUR PLAN)</div>
    <div class="data-card__content">
      <ul>
        <li><strong>Days 1-5:</strong> Fastest cardiovascular adaptations &mdash; plasma volume expands 4-15%, heart rate drops 8-20 bpm, sweating begins earlier.</li>
        <li><strong>Days 6-10:</strong> Thermoregulatory adaptations mature &mdash; sweat rate increases 10-25%, core temp drops 0.2-0.5&deg;C during exercise.</li>
        <li><strong>Beyond 10-14 days:</strong> Hemoglobin mass may increase 3-4%, similar to altitude training benefits.</li>
      </ul>
      <p><strong>How to do it:</strong> Train indoors with the fan off or reduced. Wear extra layers. Sauna post-ride (15-20 min, working up gradually). These adaptations decay at ~2.5% per day without exposure.</p>
    </div>
  </div>

  <h3>Race Day at Altitude</h3>
  <div class="gg-module gg-alert">
    <div class="gg-label">ALTITUDE PACING RULES</div>
    <ul>
      <li>Start 10% below your sea-level target power</li>
      <li>Use power meter, not RPE &mdash; RPE is unreliable at altitude</li>
      <li>Recovery between hard efforts takes 20-30% longer</li>
      <li>Be judicious with matches early &mdash; altitude limits recovery</li>
      <li>Fuel and hydrate more aggressively than at sea level (5-10% more calories, 500ml+ more fluid)</li>
      <li>Expect your heart rate to be 5-15 bpm higher at the same power</li>
    </ul>
  </div>
</section>"""


def _section_women_specific(profile: Dict, race_data: Dict, race_name: str, section_num: int = 16) -> str:
    """Women-specific training considerations — conditional on sex == female. Section number is dynamic."""
    demo = profile.get("demographics", {})
    weight_lbs = demo.get("weight_lbs", "")
    weight_kg = round(float(weight_lbs) / 2.205, 1) if weight_lbs else ""

    # Carb targets based on body weight
    carb_training = f"{round(weight_kg * 6)}-{round(weight_kg * 7)}g" if weight_kg else "5-7g/kg"
    carb_long = f"{round(weight_kg * 8)}-{round(weight_kg * 10)}g" if weight_kg else "8-10g/kg"

    return f"""<section id="section-{section_num}" class="gg-section">
  <h2>{section_num} &middot; Women-Specific Considerations</h2>

  <p>If you're a woman training for gravel racing, your physiology is different from men's in ways that
  actually affect training and performance. This isn't patronizing &mdash; it's honest acknowledgment of
  real differences that matter.</p>
  <p>The good news: these differences are trainable and manageable. The bad news: if you ignore them,
  you're making things harder than they need to be.</p>

  <h3>Menstrual Cycle &amp; Training</h3>
  <p>Your menstrual cycle affects training capacity. Not as an excuse to skip workouts, but as a
  variable to monitor and work with.</p>

  <div class="data-card">
    <div class="data-card__header">FOLLICULAR PHASE (DAYS 1-14, START OF PERIOD TO OVULATION)</div>
    <div class="data-card__content">
      <p><strong>What's happening:</strong> Estrogen rises, body temperature is lower, insulin sensitivity is higher.</p>
      <p><strong>Training impact:</strong> This is typically your power window. You'll recover faster, handle intensity better,
      and feel stronger. Days 5-14 are often your best training days of the month.</p>
      <p><strong>How to use it:</strong> Schedule your hardest interval sessions, longest rides, and FTP tests during
      this phase when possible. Your body is primed for high-quality work.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">LUTEAL PHASE (DAYS 15-28, OVULATION TO NEXT PERIOD)</div>
    <div class="data-card__content">
      <p><strong>What's happening:</strong> Progesterone dominates, body temperature rises (~0.5&deg;F), metabolism shifts
      toward fat burning, inflammation increases.</p>
      <p><strong>Training impact:</strong> Recovery takes longer. Interval quality might decline. You might feel flat even
      when doing everything right. Heart rate runs 5-10 bpm higher at same effort. Carb cravings increase
      (because your body actually needs more carbs &mdash; progesterone reduces glycogen storage efficiency).</p>
      <p><strong>How to use it:</strong> This is not the time to test FTP or push for breakthrough sessions. Focus on base
      miles, maintenance intervals, and recovery. Listen to your body more carefully. If a training week falls
      during late luteal phase and you feel like garbage despite perfect execution, that's normal &mdash; it's
      hormones, not fitness loss.</p>
    </div>
  </div>

  <div class="gg-module gg-alert">
    <div class="gg-label">IRON CONSIDERATIONS</div>
    <p><strong>Monthly blood loss means monthly iron loss.</strong> Women who menstruate need roughly 18mg of iron
    daily (vs. 8mg for men). Athletes need even more due to foot-strike hemolysis, GI losses, and
    increased red blood cell turnover.</p>
    <p><strong>Low iron = compromised training:</strong> Fatigue, inability to hit power targets, poor recovery,
    elevated heart rate, shortness of breath during efforts you should handle easily.</p>
    <ul>
      <li>Get bloodwork annually (ferritin, serum iron, hemoglobin, hematocrit)</li>
      <li>Target ferritin >50 ng/mL for athletes (many docs say >15 is "normal" &mdash; that's too low for performance)</li>
      <li>Iron-rich foods: red meat, dark leafy greens, lentils, fortified cereals</li>
      <li>Consider supplementation if levels are low (but get tested first &mdash; too much iron is also a problem)</li>
      <li>Take iron with vitamin C (aids absorption), avoid taking with calcium (blocks absorption)</li>
    </ul>
    <p><strong>Your period is not an excuse to skip workouts, but it IS a variable to monitor.</strong> Track your
    cycle. Notice patterns. Adjust expectations during luteal phase. Capitalize on follicular phase.
    This is performance optimization, not weakness.</p>
  </div>

  <h3>Fueling Differences</h3>
  <p>Women's bodies process fuel differently than men's, especially during exercise.</p>

  <div class="data-card">
    <div class="data-card__header">CARBOHYDRATE NEEDS</div>
    <div class="data-card__content">
      <p><strong>Women need MORE carbs relative to body weight than men.</strong> Despite often being told to eat less,
      female athletes actually need aggressive carbohydrate intake to support training and maintain hormonal health.</p>
      <p><strong>Why:</strong> Women's bodies preferentially spare carbohydrate and burn more fat at rest. Sounds great,
      except during high-intensity efforts (which is most of gravel racing), you NEED carbs. If you're
      chronically under-fueling carbs, your body will:</p>
      <ul>
        <li>Downregulate thyroid function (slower metabolism, more fatigue)</li>
        <li>Disrupt menstrual cycle (late periods, missed periods, longer cycles)</li>
        <li>Compromise bone density</li>
        <li>Tank performance</li>
      </ul>
      <p><strong>Your training day target:</strong> {carb_training} carbs ({f'{weight_kg}kg x 6-7g/kg' if weight_kg else '5-7g per kg body weight'}).
      More on long ride days: {carb_long} ({f'{weight_kg}kg x 8-10g/kg' if weight_kg else '8-10g per kg body weight'}).</p>
      <p><strong>Racing target:</strong> 60-80g carbs per hour for rides over 90 minutes at moderate-to-high intensity
      (scaled down for longer durations &mdash; see Nutrition Strategy section). Don't under-fuel trying to "stay lean" &mdash;
      that strategy kills performance AND health.</p>
    </div>
  </div>

  <div class="data-card">
    <div class="data-card__header">HEAT &amp; HYDRATION</div>
    <div class="data-card__content">
      <p>Women thermoregulate differently than men. This matters for gravel events.</p>
      <p><strong>Women sweat less than men</strong> at the same relative intensity. Sounds like an advantage (less fluid
      loss), but it's not &mdash; it means core temperature rises faster because evaporative cooling is less efficient.</p>
      <p><strong>The result:</strong> Women reach critical core temperature thresholds earlier in hot conditions, leading to
      earlier performance decline, higher perceived exertion at same power, greater cardiovascular strain,
      and increased risk of heat illness.</p>
      <ul>
        <li><strong>Pre-cooling is critical:</strong> Cold water immersion, ice vests, cold drinks before start</li>
        <li><strong>Aggressive cooling during race:</strong> Ice in jersey pockets, cold water over head/neck at aid stations</li>
        <li><strong>Heat acclimatization training:</strong> See the Altitude Training section &mdash; heat protocol provides critical benefits</li>
        <li><strong>Monitor core temp signals:</strong> Goosebumps, chills, confusion, nausea = pull back immediately</li>
      </ul>
    </div>
  </div>

  <h3>Recovery Needs</h3>

  <div class="data-card">
    <div class="data-card__header">WHY WOMEN MAY NEED MORE RECOVERY</div>
    <div class="data-card__content">
      <p><strong>Women often need MORE recovery than men at the same relative training intensity.</strong>
      This isn't weakness &mdash; it's physiology.</p>
      <ul>
        <li>Estrogen has anti-inflammatory properties, but it also affects tissue repair timing</li>
        <li>Lower testosterone means slower muscle protein synthesis</li>
        <li>Higher Type I muscle fiber percentage means different recovery demands</li>
        <li>Hormonal fluctuations (especially luteal phase) increase baseline inflammation</li>
      </ul>
      <p><strong>What to do:</strong></p>
      <ul>
        <li>Pay closer attention to RHR and HRV trends</li>
        <li>Don't try to match training partners if they're recovering faster &mdash; train YOUR body, not theirs</li>
        <li>Prioritize sleep (7-9 hours minimum, non-negotiable)</li>
        <li>Don't skip rest weeks</li>
        <li>Back-to-back hard days might wreck you more &mdash; you might need an extra rest day per week</li>
      </ul>
    </div>
  </div>

  <h3>Pregnancy &amp; Postpartum</h3>
  <div class="gg-module gg-blackpill">
    <div class="gg-label">IMPORTANT</div>
    <p>This plan is NOT designed for pregnant or postpartum athletes.</p>
    <p><strong>If you're pregnant:</strong> Stop this plan immediately. Consult your physician before continuing
    ANY structured training. Racing is off the table, but moderate training may be safe with medical clearance.</p>
    <p><strong>Postpartum:</strong> Wait at least 6 months before attempting race-specific training.
    Get clearance from OB/GYN and ideally a pelvic floor physical therapist. Rebuild base fitness
    gradually &mdash; don't jump back into high-intensity work.</p>
  </div>

  <h3>Equipment Considerations</h3>
  <ul>
    <li><strong>Sports bra:</strong> Non-negotiable. Test on long rides, not just in the store. If it's uncomfortable
    for 30 minutes, it'll be unbearable at mile {race_data.get("distance_miles", 100)}. High-impact support is
    essential &mdash; you're bouncing on gravel for hours.</li>
    <li><strong>Chamois:</strong> Women's anatomy requires women-specific design. This is not marketing &mdash; the padding
    placement and shape are different. A men's chamois will cause problems. Test multiple brands if needed.
    Numbness, chafing, or pain means wrong fit.</li>
    <li><strong>Saddle:</strong> Proper bike fit and saddle selection are critical. Women's sit bone width is often
    (but not always) wider than men's. Get a professional fit if you're experiencing numbness, pain, or
    discomfort. These issues don't resolve with more miles &mdash; they require equipment changes.</li>
  </ul>

  <h3>The Bottom Line</h3>
  <p>Your body is different. Not worse, not weaker &mdash; different. Train accordingly.</p>
  <ul>
    <li>Track your cycle. Work with it, not against it.</li>
    <li>Fuel aggressively. Don't under-eat trying to stay lean.</li>
    <li>Take heat management seriously. You're at higher risk in hot conditions.</li>
    <li>Prioritize recovery. You might need more than male training partners.</li>
    <li>Get proper equipment. Generic gear won't cut it.</li>
  </ul>
  <p>Racing gravel is hard for everyone. Being a woman doesn't make it harder &mdash; but ignoring female
  physiology makes it unnecessarily difficult. Do the work. Respect your body's signals. Show up prepared.</p>
</section>"""


# ══════════════════════════════════════════════════════════════
# CSS — Gravel God Brand System
# ══════════════════════════════════════════════════════════════

def _css(brand="gravel"):
    # Same token NAMES, brand-specific VALUES — every var(--gg-*) in the guide
    # follows automatically. Road athletes get the Roadie Labs newsprint/
    # charcoal monochrome identity; gravel/MTB keep Gravel God brown. Fonts are
    # shared (Sometype Mono + Source Serif), so this is a pure palette swap.
    if (brand or "gravel").lower() == "road":
        _colors = """  --gg-color-dark-brown: #000000;
  --gg-color-primary-brown: #1a1a1a;
  --gg-color-secondary-brown: #333333;
  --gg-color-warm-brown: #555555;
  --gg-color-tan: #d0d0c8;
  --gg-color-sand: #e8e8e2;
  --gg-color-warm-paper: #f5f5f0;
  --gg-color-gold: #1a1a1a;
  --gg-color-light-gold: #777777;
  --gg-color-teal: #333333;
  --gg-color-light-teal: #555555;
  --gg-color-near-black: #1a1a1a;
  --gg-color-white: #ffffff;
  --gg-color-error: #8b1a1a;"""
    else:
        _colors = """  --gg-color-dark-brown: #3a2e25;
  --gg-color-primary-brown: #59473c;
  --gg-color-secondary-brown: #8c7568;
  --gg-color-warm-brown: #A68E80;
  --gg-color-tan: #d4c5b9;
  --gg-color-sand: #ede4d8;
  --gg-color-warm-paper: #f5efe6;
  --gg-color-gold: #B7950B;
  --gg-color-light-gold: #c9a92c;
  --gg-color-teal: #1A8A82;
  --gg-color-light-teal: #4ECDC4;
  --gg-color-near-black: #1a1613;
  --gg-color-white: #ffffff;
  --gg-color-error: #c0392b;"""
    return """<style>
/* === Brand Tokens === */
:root {
  /* color */
""" + _colors + """

  /* font */
  --gg-font-data: 'Sometype Mono', monospace;
  --gg-font-editorial: 'Source Serif 4', Georgia, serif;

  /* spacing */
  --gg-spacing-2xs: 4px;
  --gg-spacing-xs: 8px;
  --gg-spacing-sm: 12px;
  --gg-spacing-md: 16px;
  --gg-spacing-lg: 24px;
  --gg-spacing-xl: 32px;
  --gg-spacing-2xl: 48px;
  --gg-spacing-3xl: 64px;

  /* border */
  --gg-border-radius: 0;
}

/* === Reset === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; -webkit-font-smoothing: antialiased; scroll-behavior: smooth; }

/* === Base === */
body {
  margin: 32px auto 64px auto;
  padding: 0 20px;
  max-width: 1120px;
  background: var(--gg-color-sand);
  color: var(--gg-color-dark-brown);
  font-family: var(--gg-font-editorial);
  font-size: 16px;
  line-height: 1.75;
  overflow-x: hidden;
}

main.gg-guide-page { width: 100%; }

/* === Layout === */
.gg-guide-layout {
  display: grid;
  grid-template-columns: minmax(0, 260px) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  min-width: 0;
  max-width: 100%;
  grid-template-rows: auto 1fr;
}

@media (max-width: 900px) {
  .gg-guide-layout { grid-template-columns: minmax(0, 1fr); }
}

/* === Header === */
header.guide-header {
  grid-column: 1 / -1;
  border-bottom: 4px double var(--gg-color-dark-brown);
  padding-bottom: 16px;
  margin-bottom: 32px;
}

h1 {
  font-family: var(--gg-font-editorial);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--gg-color-dark-brown);
  padding-bottom: 12px;
  border-bottom: 4px double var(--gg-color-dark-brown);
  margin-top: 0;
}

.guide-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-family: var(--gg-font-data);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--gg-color-secondary-brown);
  margin-top: 12px;
}

.guide-meta span {
  border: 2px solid var(--gg-color-dark-brown);
  padding: 4px 8px;
  background: var(--gg-color-warm-paper);
}

/* === Typography === */
h2 {
  font-family: var(--gg-font-editorial);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--gg-color-dark-brown);
  margin: 1.6rem 0 0.6rem 0;
  padding-bottom: 8px;
  border-bottom: 4px double var(--gg-color-dark-brown);
}

h3 {
  font-family: var(--gg-font-data);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--gg-color-gold);
  margin: 1.4rem 0 0.5rem 0;
  line-height: 1.2;
}

h4 {
  font-family: var(--gg-font-data);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--gg-color-secondary-brown);
  margin: 1.4rem 0 0.5rem 0;
  line-height: 1.2;
}

p {
  margin: 0 0 1rem 0;
  max-width: 65ch;
}

strong { font-weight: 600; }

ul, ol { margin: 0.3rem 0 1rem 1.4rem; padding: 0; }
li { margin: 0 0 0.4rem 0; line-height: 1.6; }

hr { border: none; border-top: 4px double var(--gg-color-dark-brown); margin: 2.5rem 0; }

a { color: var(--gg-color-teal); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--gg-color-light-teal); }

/* === TOC === */
nav.gg-guide-toc {
  position: sticky;
  top: 16px;
  border: 3px solid var(--gg-color-dark-brown);
  padding: 16px;
  background: var(--gg-color-warm-paper);
  max-width: 260px;
  overflow-x: hidden;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  grid-row: 2;
}

nav.gg-guide-toc h2 {
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  color: var(--gg-color-gold);
  margin-top: 0;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--gg-color-tan);
}

nav.gg-guide-toc ol {
  margin-left: 1.2rem;
  font-family: var(--gg-font-data);
  font-size: 12px;
}

nav.gg-guide-toc a {
  color: var(--gg-color-primary-brown);
  text-decoration: none;
  border-left: 2px solid transparent;
  padding-left: 8px;
  margin-left: -8px;
  display: inline-block;
  transition: border-color 0.3s, color 0.3s;
}

nav.gg-guide-toc a:hover {
  color: var(--gg-color-dark-brown);
  border-left-color: var(--gg-color-gold);
}

/* === Content Area === */
.gg-guide-content {
  word-break: break-word;
  max-width: 100%;
  overflow-x: hidden;
  min-width: 0;
  overflow-wrap: break-word;
  grid-row: 2;
}

section.gg-section {
  margin-bottom: 3rem;
  max-width: 100%;
  overflow-x: hidden;
}

/* === Data Cards === */
.data-card {
  background: var(--gg-color-warm-paper);
  border: 3px solid var(--gg-color-dark-brown);
  padding: var(--gg-spacing-lg);
  margin-bottom: var(--gg-spacing-lg);
}

.data-card__header {
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--gg-color-gold);
  margin-bottom: var(--gg-spacing-sm);
  padding-bottom: var(--gg-spacing-xs);
  border-bottom: 2px solid var(--gg-color-tan);
}

.data-card__content {
  font-family: var(--gg-font-editorial);
  font-size: 16px;
  line-height: 1.7;
}

/* === Stats Grid === */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--gg-spacing-md);
  margin-bottom: var(--gg-spacing-lg);
}

.stat-card {
  background: var(--gg-color-warm-paper);
  border: 3px solid var(--gg-color-dark-brown);
  padding: var(--gg-spacing-md);
  text-align: center;
}

.stat-card__value {
  font-family: var(--gg-font-editorial);
  font-size: 28px;
  font-weight: 700;
  color: var(--gg-color-dark-brown);
  line-height: 1.1;
}

.stat-card__label {
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gg-color-secondary-brown);
  margin-top: var(--gg-spacing-xs);
}

/* === Phase Indicators === */
.phase-indicator {
  display: inline-block;
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  padding: 4px 8px;
  border: 2px solid;
}

.phase-indicator--base { color: var(--gg-color-secondary-brown); border-color: var(--gg-color-secondary-brown); }
.phase-indicator--build { color: var(--gg-color-teal); border-color: var(--gg-color-teal); }
.phase-indicator--peak { color: var(--gg-color-gold); border-color: var(--gg-color-gold); }
.phase-indicator--taper { color: var(--gg-color-warm-brown); border-color: var(--gg-color-warm-brown); }
.phase-indicator--race { color: var(--gg-color-warm-paper); background: var(--gg-color-gold); border-color: var(--gg-color-gold); }

/* === Modules / Callouts === */
.gg-module {
  border: 3px solid var(--gg-color-dark-brown);
  border-left-width: 6px;
  padding: 16px 20px;
  margin: 1.5rem 0;
  background: var(--gg-color-warm-paper);
}

.gg-alert { border-left-color: var(--gg-color-gold); }
.gg-tactical { border-left-color: var(--gg-color-teal); }
.gg-info { border-left-color: var(--gg-color-secondary-brown); }
.gg-blackpill { background: var(--gg-color-sand); border-left-width: 8px; border-left-color: var(--gg-color-dark-brown); }

.gg-label {
  display: inline-block;
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  border: 2px solid var(--gg-color-dark-brown);
  padding: 4px 8px;
  margin-bottom: 10px;
  color: var(--gg-color-gold);
}

/* === Tables === */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0 1.5rem 0;
  border: 3px solid var(--gg-color-dark-brown);
}

th, td {
  border: 1px solid var(--gg-color-tan);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

th {
  font-family: var(--gg-font-data);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  background: var(--gg-color-dark-brown);
  color: var(--gg-color-warm-paper);
  border-bottom: 4px double var(--gg-color-dark-brown);
}

td {
  font-family: var(--gg-font-data);
  font-size: 13px;
}

tbody tr:nth-child(even) { background: rgba(212, 197, 185, 0.15); }
tbody tr:hover { background: rgba(183, 149, 11, 0.08); }

tr.race-day-row td { background: rgba(183, 149, 11, 0.15); font-weight: 600; }

/* === Footer === */
footer.guide-footer {
  grid-column: 1 / -1;
  border-top: 4px double var(--gg-color-dark-brown);
  margin-top: 48px;
  padding-top: 24px;
  text-align: center;
}

.footer-logo {
  font-family: var(--gg-font-data);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--gg-color-gold);
}

.footer-tagline {
  font-family: var(--gg-font-editorial);
  font-size: 14px;
  font-style: italic;
  color: var(--gg-color-secondary-brown);
  margin-top: 8px;
}

/* === Print ===
   Chromium cannot fragment the two-column grid: content gets squeezed
   into the 260px TOC track (one-word-per-line titles, vertically wrapped
   table headers) and the sticky TOC prints on top of body text. Print
   must flatten the layout to a single block column. */
@media print {
  @page { size: letter; margin: 0.6in 0.7in; }

  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body {
    margin: 0;
    padding: 0;
    max-width: 100%;
    background: #fff;
    font-size: 11pt;
    line-height: 1.55;
  }

  /* Flatten the grid; the sticky TOC is useless on paper */
  .gg-guide-layout { display: block; }
  nav.gg-guide-toc { display: none; }
  .gg-guide-content { max-width: 100%; }

  /* Cover header gets its own page */
  header.guide-header { page-break-after: always; border-bottom: none; padding-top: 2in; }
  h1 { font-size: 26pt; }
  .guide-meta { margin-top: 24px; }
  .guide-meta span { white-space: nowrap; }

  /* Never split a component across pages */
  .data-card, .stat-card, .gg-module, .race-day-row, .guide-meta,
  table, figure, svg, blockquote {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .stats-grid { break-inside: avoid; }

  /* Headings stay with their content. Sections flow naturally — forcing
     every h2 onto a new page left half-empty pages between sections. */
  h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
  h2 { font-size: 16pt; margin-top: 28pt; }
  .gg-section { margin-top: 18pt; }

  /* Tables: full width, readable, headers never wrap letter-by-letter */
  table { width: 100%; font-size: 9pt; }
  th { white-space: nowrap; }
  td, th { padding: 5pt 7pt; }

  /* Prose can use the full page on paper */
  p { max-width: none; }

  /* No interactive affordances on paper */
  a { color: inherit; text-decoration: none; }
  [onclick] { pointer-events: none; }
}

/* === Mobile === */
@media (max-width: 700px) {
  body { padding: 16px; }
  nav.gg-guide-toc { position: static; margin-bottom: 32px; max-height: none; max-width: 100%; }
  h1 { font-size: 24px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>"""


# ══════════════════════════════════════════════════════════════
# SVG HELPERS
# ══════════════════════════════════════════════════════════════

def _methodology_display(methodology_yaml: dict) -> dict:
    """Build the guide's methodology section from the ACTUAL selection so it
    can never contradict the plan. Name is verbatim; description +
    progression are derived from the real intensity distribution, not a
    tier default."""
    if not methodology_yaml:
        return {}
    name = (methodology_yaml.get("selected_methodology")
            or methodology_yaml.get("methodology_id", "")).strip()
    if not name:
        return {}
    cfg = methodology_yaml.get("configuration", {}) or {}
    dist = cfg.get("intensity_distribution", {})
    dist = dist if isinstance(dist, dict) else {}
    z1 = dist.get("z1_z2")
    emphasis = (cfg.get("emphasis") or "").strip()

    # Lead with what the plan ACTUALLY emphasizes (the workouts genuinely
    # reflect the method), and frame VOLUME honestly. We deliberately do NOT
    # state a precise tempo/hard split: the plan is compliance-bound to mostly
    # easy riding, so an exact "X% tempo / Y% hard" was aspirational and could
    # contradict the calendar. "Roughly N% easy by volume" is true; the
    # emphasis describes where the hard work actually goes.
    if emphasis:
        desc = (f"Your {name} plan is built around {emphasis}.")
        if z1 is not None:
            desc += (f" By volume most of your riding stays genuinely easy "
                     f"(roughly {z1*100:.0f}%) &mdash; that's what builds the "
                     f"engine; the hard days are where this plan does its "
                     f"specific work.")
        desc += " Matched to your hours and experience."
    elif z1 is not None:
        desc = (f"Your {name} plan keeps most riding genuinely easy (roughly "
                f"{z1*100:.0f}% by volume), with the hard days focused where "
                f"they count. Matched to your hours and experience.")
    else:
        desc = f"Your plan follows the {name} methodology, matched to your hours and experience."
    prog_style = (cfg.get("progression_style", "") or "").replace("_", " ")
    progression = (f"Progression: {prog_style}." if prog_style
                   else "Each block builds on the last; recovery weeks lock in the gains.")
    return {"name": name, "description": desc, "progression": progression}


def _meta_badges(race_name, race_distance, elevation, duration_est,
                 plan_duration, location, gain_display=None) -> str:
    """Cover badges — empty values are dropped, never rendered as bare
    units ('FT') or empty chips.

    gain_display: optional override (store_mode only, from
    vitals.gain_display) for races whose total climbing gain is unverified
    or only a partial sum — e.g. "Varies" or "7,100+ ft (named climbs)".
    Rendered verbatim (no " ft" appended) instead of the numeric elevation
    badge when present. Athlete-mode guides never pass this.
    """
    def has(v) -> bool:
        return v not in (None, '', 0, '0') and str(v).strip() not in ('', '—', '-', 'TBD', 'None')

    badges = [race_name if has(race_name) else None]
    if has(race_distance):
        badges.append(f"{race_distance} miles")
    if has(gain_display):
        badges.append(str(gain_display))
    elif has(elevation):
        badges.append(f"{elevation} ft")
    badges.append(duration_est if has(duration_est) else f"{plan_duration}-week plan")
    if has(location):
        badges.append(location)
    return '\n'.join(f'          <span>{b}</span>' for b in badges if b)


def _cross_reference_race_date(race_name: str, athlete_date: str) -> dict:
    """Verify the athlete's race date against the real race database.

    Returns {matched, date_match, date_specific} for the guide's
    verification card. matched=False -> race not in DB (athlete data
    stands). date_match True/False -> the athlete's date agrees with the
    database (or not). Tolerant: same day = match.
    """
    try:
        from known_races import match_race
    except Exception:
        return {}
    hit = match_race(race_name)
    if not hit:
        return {"matched": False, "date_match": None, "date_specific": ""}
    info = hit[1]
    db_date = info.get("date")
    if not db_date or not athlete_date:
        return {"matched": True, "date_match": None, "date_specific": db_date or ""}
    return {
        "matched": True,
        "date_match": (str(db_date)[:10] == str(athlete_date)[:10]),
        "date_specific": db_date,
    }


def _resolve_race_data(race_name, race_data_dirs):
    """Load a race's JSON from the gravel-race-automation DB, keyed off the
    VERIFIED matcher so the venue we render always belongs to the race we
    name. Returns (race_data_dict, verified_location_or_None).

    The old loader guessed the file via slug.split('-')[0] (first token) and
    a `slug[:10] in stem` substring glob — both could load an UNRELATED
    race's JSON, putting a wrong venue (e.g. "Niseko, Hokkaido" on a Greek
    gran fondo) in the guide. A wrong venue destroys athlete trust; a blank
    one merely omits. We match exactly, fall back to a tight prefix only, and
    overlay the matcher's authoritative location when no file is found.
    """
    name_slug = (race_name or "").lower().replace(' ', '-').replace("'", '')

    canonical_slug = None
    verified_location = None
    try:
        from known_races import match_race
        _hit = match_race(race_name)
        if _hit:
            _key = _hit[0]
            canonical_slug = _key.split(':', 1)[1] if ':' in _key else _key
            verified_location = _hit[1].get('location') or None
    except Exception:
        pass

    # Known canonical-slug → race-data-filename mismatches (matcher key and
    # the gravel-race-automation filename diverged historically).
    _slug_aliases = {
        'sbt-grvl': 'steamboat-gravel',
        'sbt_grvl': 'steamboat-gravel',
        'big-horn-gravel': 'bighorn-gravel',
    }
    candidate_slugs = [s for s in [
        canonical_slug,
        canonical_slug.replace('_', '-') if canonical_slug else None,
        _slug_aliases.get(canonical_slug or ''),
        _slug_aliases.get((canonical_slug or '').replace('_', '-')),
        name_slug,
        _slug_aliases.get(name_slug),
        name_slug.replace('-gravel', ''),
    ] if s]

    race_data = {}
    for race_data_dir in race_data_dirs:
        if not race_data_dir.exists():
            continue
        # exact slug match only — no first-token or arbitrary-substring guessing
        for cand in candidate_slugs:
            race_file = race_data_dir / f'{cand}.json'
            if race_file.exists():
                with open(race_file) as f:
                    race_data = json.load(f)
                break
        # tight prefix-only fallback (e.g. belgian-waffle-ride →
        # belgian-waffle-ride-kansas) — NEVER an arbitrary substring match
        if not race_data and len(name_slug) >= 8:
            for rf in sorted(race_data_dir.glob('*.json')):
                if rf.stem.startswith(name_slug):
                    with open(rf) as f:
                        race_data = json.load(f)
                    break
        if race_data:
            break
    return race_data, verified_location


def _flatten_race_data(race_data: Dict) -> Dict:
    """Unwrap raw race-data JSON ({"race": {...}}) into the flat shape the
    guide builder (and step_07/select_methodology) expect.

    CRITICAL: vitals["elevation_ft"] is total CLIMBING GAIN, not altitude
    above sea level (Big Sugar's 9500 is feet climbed; Bentonville itself
    sits at ~1,300ft ASL). The altitude trigger in `_conditional_triggers`
    reads `race_metadata["avg_elevation_feet"]` / `["start_elevation_feet"]`
    — those MUST be sourced from the schema's distinct `*_elevation_asl_ft`
    fields, never from elevation_ft/elevation_gain_ft. Before this function
    existed, race_metadata never carried avg/start_elevation_feet at all, so
    the altitude section silently never fired for any race, mountain or not.
    """
    if 'race' in race_data and isinstance(race_data['race'], dict):
        inner = race_data['race']
        # Merge race-level fields to top level for step_07 compatibility
        race_data = {**race_data, **inner}
        # Also flatten vitals to top level
        vitals = inner.get('vitals', {})
        race_data.setdefault('distance_miles', vitals.get('distance_mi'))
        race_data.setdefault('elevation_feet', vitals.get('elevation_ft'))
        race_data.setdefault('elevation_gain_feet', vitals.get('elevation_ft'))
        # gain_display: optional vitals override for races whose total
        # climbing gain is unverified or only a partial (named-climbs) sum
        # — see _meta_badges. Never touched unless the JSON sets it.
        race_data.setdefault('gain_display', vitals.get('gain_display'))
        race_data.setdefault('location', vitals.get('location'))
        race_data.setdefault('city', vitals.get('location', '').split(',')[0].strip() if vitals.get('location') else '')
        race_data.setdefault('state', vitals.get('location', '').split(',')[-1].strip() if vitals.get('location') else '')
        # Create race_metadata for step_07 compatibility. avg/start_elevation_feet
        # are ASL figures sourced ONLY from vitals.*_elevation_asl_ft — never
        # from the gain field above.
        start_asl = vitals.get('start_elevation_asl_ft', 0) or 0
        avg_asl = vitals.get('avg_elevation_asl_ft', 0) or start_asl or 0
        race_data.setdefault('race_metadata', {
            'location': vitals.get('location', ''),
            'elevation_feet': vitals.get('elevation_ft', 0),
            'start_elevation_feet': start_asl,
            'avg_elevation_feet': avg_asl,
        })
        # Create race_characteristics for terrain/climate
        terrain = inner.get('terrain', {})
        climate = inner.get('climate', {})
        race_data.setdefault('race_characteristics', {
            'terrain': terrain.get('primary', ''),
            'climate': climate.get('summary', '') if isinstance(climate, dict) else str(climate),
        })
    return race_data


def generate_training_guide(athlete_id: str, output_path=None, store_mode: bool = False):
    """
    CURRENT GUIDE BUILDER — produces the branded training guide with:
    - Radar chart, non-negotiables, phase badges
    - Week-by-week ATP table (from ZWO files)
    - Athlete goals + blindspots (from questionnaire)
    - Fueling targets (from fueling.yaml)
    - Strength program (from profile)
    - Race-specific content (from race database)

    This is the production guide builder. It replaces generate_html_guide.py.

    store_mode: True for marketplace/store SKU guides generated from a
    generic base intake (no real athlete behind the numbers, e.g. the Big
    Sugar pilot SKUs). Suppresses the personal YOUR PROFILE block and
    1:1-questionnaire framing throughout. Real 1:1 customer guides (the
    default, called from generate_athlete_package.py) are unaffected.
    """
    import yaml
    import json
    from pathlib import Path

    # Resolve paths
    scripts_dir = Path(__file__).parent
    athletes_dir = scripts_dir.parent
    athlete_dir = athletes_dir / athlete_id

    if output_path is None:
        output_path = athlete_dir / 'training_guide.html'
    else:
        output_path = Path(output_path)

    # Load athlete data
    with open(athlete_dir / 'profile.yaml') as f:
        profile = yaml.safe_load(f)
    with open(athlete_dir / 'derived.yaml') as f:
        derived = yaml.safe_load(f)

    plan_dates = {}
    pd_path = athlete_dir / 'plan_dates.yaml'
    if pd_path.exists():
        with open(pd_path) as f:
            plan_dates = yaml.safe_load(f)

    # The guide's methodology section must reflect the ACTUALLY-SELECTED
    # methodology, not the tier default. (The judge caught guides telling a
    # MAF/Sweet-Spot athlete they're on "Traditional Pyramidal".)
    methodology_yaml = {}
    meth_path = athlete_dir / 'methodology.yaml'
    if meth_path.exists():
        with open(meth_path) as f:
            methodology_yaml = yaml.safe_load(f) or {}
    derived['_methodology_display'] = _methodology_display(methodology_yaml)

    fueling = {}
    fuel_path = athlete_dir / 'fueling.yaml'
    if fuel_path.exists():
        with open(fuel_path) as f:
            fueling = yaml.safe_load(f)

    # ── Adapt profile fields ──
    if (not profile.get('fitness')) and profile.get('fitness_markers'):
        profile['fitness'] = profile['fitness_markers']
    if (not profile.get('schedule')) and profile.get('weekly_availability'):
        sc = profile.get('schedule_constraints', {})
        off = sc.get('preferred_off_days', [])
        long = sc.get('preferred_long_day', 'saturday')
        profile['schedule'] = {
            'weekly_hours': str(profile['weekly_availability'].get('cycling_hours_target', 9)),
            'off_days': off,
            'long_ride_days': [long],
            'interval_days': [],
        }
    # Ensure demographics exist (step_07 reads weight/height from here)
    if not profile.get('demographics'):
        fm = profile.get('fitness_markers', {})
        weight_kg = fm.get('weight_kg', profile.get('weight_kg', 0))
        height_cm = fm.get('height_cm', profile.get('height_cm', 0))
        total_inches = height_cm / 2.54 if height_cm else 0
        profile['demographics'] = {
            'weight_lbs': round(weight_kg * 2.205) if weight_kg else 0,
            'weight_kg': weight_kg,
            'height_cm': height_cm,
            'height_ft': int(total_inches // 12) if total_inches else '',
            'height_in': int(total_inches % 12) if total_inches else '',
            'age': profile.get('health_factors', {}).get('age', 0),
            'sex': fm.get('sex', 'unknown'),
        }
    # Ensure training_history has years_cycling
    th = profile.get('training_history', {})
    if th and not th.get('years_cycling'):
        th['years_cycling'] = th.get('years_structured', '')
    # Ensure health_factors accessible as 'health'
    if not profile.get('health') and profile.get('health_factors'):
        profile['health'] = profile['health_factors']
    # Fix strength bool → string
    strength = profile.get('strength', {})
    if isinstance(strength.get('include_in_plan'), bool):
        strength['include_in_plan'] = 'yes' if strength['include_in_plan'] else 'no'

    # ── Adapt derived fields ──
    target_race = profile.get('target_race', {})
    derived.setdefault('race_name', target_race.get('name', 'Your Race'))
    derived.setdefault('race_distance_miles', target_race.get('distance_miles', 0))
    derived.setdefault('race_date', plan_dates.get('race_date', ''))
    derived.setdefault('elevation_feet', target_race.get('elevation_ft', 0))
    derived.setdefault('level', 'Intermediate')
    derived.setdefault('weekly_hours', str(profile.get('weekly_availability', {}).get('cycling_hours_target', 9)))

    # ── Plan duration (needed by schedule builder AND plan_config) ──
    plan_duration = derived.get('plan_weeks', 12)

    # ── Build schedule from block-builder plan (actual workout assignments) ──
    # Use the block-builder's first load week to determine the weekly pattern.
    # This shows what the athlete actually DOES, not just slot types.
    schedule = {'days': {}}
    try:
        from archetype import determine_archetype
        from block_chain import chain_blocks

        sc = profile.get('schedule_constraints', {})
        _DAY_NORM = {'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed',
                     'thursday': 'Thu', 'friday': 'Fri', 'saturday': 'Sat', 'sunday': 'Sun'}
        bb_off = [_DAY_NORM.get(d.lower(), d) for d in sc.get('preferred_off_days', ['monday'])]
        bb_long = _DAY_NORM.get(sc.get('preferred_long_day', 'saturday').lower(), 'Sat')
        bb_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', 9)
        bb_arch = determine_archetype(bb_hours)

        bb_plan = chain_blocks(
            total_weeks=min(6, plan_duration), archetype=bb_arch,
            weeks_to_race=plan_duration, max_level=6, max_intensity=3,
            off_days=bb_off, long_ride_day=bb_long,
            starting_level=1, hours_per_week=bb_hours,
        )
        # Use week 1 (first load week) as the template
        if bb_plan.get('weeks'):
            w1 = bb_plan['weeks'][0]
            _ABBREV_TO_FULL = {'Mon': 'monday', 'Tue': 'tuesday', 'Wed': 'wednesday',
                               'Thu': 'thursday', 'Fri': 'friday', 'Sat': 'saturday', 'Sun': 'sunday'}
            for day_data in w1.get('days', []):
                day_full = _ABBREV_TO_FULL.get(day_data['day'], day_data['day'].lower())
                role = day_data.get('role', 'filler')
                name = day_data.get('name', '')
                if role == 'off' or name == 'OFF':
                    schedule['days'][day_full] = {'session': 'rest'}
                elif role == 'long_ride':
                    schedule['days'][day_full] = {'session': 'long_ride'}
                elif role == 'intensity':
                    # Use actual workout name for intensity days
                    schedule['days'][day_full] = {'session': 'intervals', 'label': name}
                elif name == 'Rest Day':
                    schedule['days'][day_full] = {'session': 'rest'}
                else:
                    schedule['days'][day_full] = {'session': 'easy_ride'}
    except Exception as _sched_err:
        # Fallback to weekly_structure.yaml
        import traceback; traceback.print_exc()
        ws_path = athlete_dir / 'weekly_structure.yaml'
        if ws_path.exists():
            with open(ws_path) as f:
                ws = yaml.safe_load(f)
            raw_days = ws.get('days', {})
            for day_name, info in raw_days.items():
                am = info.get('am')
                pm = info.get('pm')
                is_off = info.get('max_duration', 0) == 0 and not am and not pm
                if is_off:
                    schedule['days'][day_name] = {'session': 'rest'}
                elif am == 'long_ride' or pm == 'long_ride':
                    schedule['days'][day_name] = {'session': 'long_ride'}
                elif info.get('is_key_day'):
                    schedule['days'][day_name] = {'session': 'intervals'}
                else:
                    schedule['days'][day_name] = {'session': pm or am or 'easy_ride'}

    # ── Build plan_config ──
    plan_duration = derived.get('plan_weeks', 12)
    plan_config = {
        'plan_duration': plan_duration,
        'plan_start_date': plan_dates.get('plan_start', ''),
        'race_date': plan_dates.get('race_date', ''),
        'template': {},
        'ftp_test_weeks': [],
    }

    # ── Load race data from gravel-race-automation (if available) ──
    race_name = derived['race_name']
    race_data, verified_location = _resolve_race_data(race_name, [
        scripts_dir.parent.parent.parent / 'gravel-race-automation' / 'race-data',
        Path.home() / 'Documents' / 'GravelGod' / 'gravel-race-automation' / 'race-data',
    ])

    race_data = _flatten_race_data(race_data)

    # Overlay the verified venue from the race DB so a missing JSON file
    # still renders the CORRECT location (matched to race_name) rather than
    # a blank or stale one. The matcher's location is authoritative.
    if verified_location:
        _rm = race_data.setdefault('race_metadata', {})
        if not _rm.get('location'):
            _rm['location'] = verified_location
        if not race_data.get('location'):
            race_data['location'] = verified_location

    # ── Generate the guide ──
    html = _build_full_guide(
        athlete_name=profile.get('name', athlete_id),
        race_name=race_name,
        race_distance=derived['race_distance_miles'],
        tier=derived.get('tier', 'finisher'),
        level=derived.get('level', 'Intermediate'),
        plan_duration=plan_duration,
        profile=profile,
        derived=derived,
        schedule=schedule,
        plan_config=plan_config,
        race_data=race_data,
        # Verify the athlete's date against the real race DB (was hardcoded
        # empty here, so every guide showed "not in database").
        date_xref=_cross_reference_race_date(race_name, derived.get('race_date', '')),
        store_mode=store_mode,
    )

    # ── Post-process: inject coaching-pipeline-specific sections ──
    import re

    # ATP/week-by-week table injection REMOVED per coach review (Jun 2026):
    # the schedule lives in the training plan, not the guide. Do not re-add.

    # 2. Inject Goals & Blindspots AFTER section 1 (Training Plan Brief)
    goals_html = _build_goals_section(profile, store_mode=store_mode)
    if goals_html:
        html = html.replace('</section>\n\n  <section id="section-2"',
                           f'</section>\n\n{goals_html}\n\n  <section id="section-2"', 1)
        # Fallback if exact match fails
        if goals_html not in html:
            html = html.replace('<section id="section-2"',
                               f'{goals_html}\n\n<section id="section-2"', 1)

    # 3. Inject personalized fueling.yaml targets INTO the nutrition section
    # (section-10). Previously this REPLACED the entire science-rich section
    # with a 3-stat card — customers lost the fueling framework. Now the
    # personalized card leads and the framework follows. store_mode
    # suppresses this entirely (see _build_nutrition_section docstring).
    nutrition_html = _build_nutrition_section(fueling, profile, store_mode=store_mode)
    if nutrition_html and fueling:
        nutrition_anchor = '<h2>9 &middot; Nutrition Strategy</h2>'
        if nutrition_anchor in html:
            html = html.replace(nutrition_anchor,
                                f'{nutrition_anchor}\n{nutrition_html}', 1)

    # Clean up redundant distance in titles (e.g., "Unbound Gravel 200 200mi")
    rd = derived.get('race_distance_miles', 0)
    rn = derived.get('race_name', '')
    if rd and str(rd) in rn:
        html = html.replace(f'{rd}mi Training Guide', 'Training Guide')
        html = html.replace(f'{rd}mi &ndash;', '&ndash;')
        html = html.replace(f'{rd}mi training plan', 'training plan')
        html = html.replace(f'{rd}mi successfully', 'successfully')
        html = html.replace(f' {rd}mi</td>', '</td>')  # Stat card: just show number

    output_path.write_text(html, encoding='utf-8')
    return output_path


def _build_goals_section(profile, store_mode: bool = False) -> str:
    """Build goals + blindspots from questionnaire data.

    store_mode: no real athlete filled a questionnaire, so self-assessed
    "strengths"/"blindspots" (a personal training-history judgment) are
    dropped and the framing sentence stops claiming this came from the
    buyer's own answers. The goal/obstacle text is tier-level race framing
    and is kept.
    """
    racing = profile.get('racing', {})
    success = racing.get('success_metrics', '')
    obstacles = racing.get('obstacles', '')

    training_hist = profile.get('training_history', {})
    strengths = '' if store_mode else training_hist.get('strengths', '')
    weaknesses = '' if store_mode else training_hist.get('weaknesses', '')

    if not any([success, obstacles, strengths, weaknesses]):
        return ''

    items = []
    if success:
        items.append(f'<div style="margin:12px 0;padding:12px 16px;background:#fff;border-left:3px solid var(--gg-color-teal)"><strong>Success looks like:</strong> {success}</div>')
    if obstacles:
        items.append(f'<div style="margin:12px 0;padding:12px 16px;background:#fff;border-left:3px solid var(--gg-color-gold)"><strong>Obstacles to overcome:</strong> {obstacles}</div>')
    if strengths:
        items.append(f'<div style="margin:12px 0;padding:12px 16px;background:#fff;border-left:3px solid var(--gg-color-teal)"><strong>Your strengths:</strong> {strengths}</div>')
    if weaknesses:
        items.append(f'<div style="margin:12px 0;padding:12px 16px;background:#fff;border-left:3px solid var(--gg-color-error)"><strong>Your blindspots:</strong> {weaknesses}</div>')

    heading = "Goals &amp; Watch-Outs" if store_mode else "Your Goals &amp; Blindspots"
    framing = ("What this plan is built toward, and what it watches out for." if store_mode
               else "From your questionnaire — this is what we're building toward and what we're watching out for.")

    return f'''
    <section style="margin:40px 0">
      <h2 style="font-family:'Sometype Mono',monospace;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:var(--gg-color-primary-brown);border-bottom:2px solid var(--gg-color-primary-brown);padding-bottom:8px">
        {heading}
      </h2>
      <p style="font-family:'Source Serif 4',Georgia,serif;color:#555">{framing}</p>
      {"".join(items)}
    </section>'''


def _build_nutrition_section(fueling, profile, store_mode: bool = False) -> str:
    """Build nutrition targets from fueling.yaml.

    store_mode: fueling.yaml numbers for a store SKU are computed from the
    fake base-intake body weight (identical for every buyer of that tier),
    so they are never shown as "Your Personalized Targets" — suppressed
    entirely rather than presented as if unique to the buyer.
    """
    if store_mode:
        return ''
    if not fueling:
        return ''

    carbs = fueling.get('carbohydrates', {})
    hourly = carbs.get('hourly_target', 0)
    hourly_range = carbs.get('hourly_range', [])
    total = carbs.get('total_grams', 0)

    recs = fueling.get('recommendations', {})
    hydration = recs.get('hydration', {})

    if not hourly:
        return ''

    range_str = f"{hourly_range[0]}-{hourly_range[1]}g/hr" if len(hourly_range) == 2 else f"{hourly}g/hr"

    return f'''
    <div style="margin:24px 0">
      <h3 style="font-family:'Sometype Mono',monospace;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:var(--gg-color-primary-brown);border-bottom:2px solid var(--gg-color-primary-brown);padding-bottom:8px">
        Your Personalized Targets
      </h3>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:20px 0">
        <div style="padding:20px;background:#fff;border:2px solid var(--gg-color-primary-brown)">
          <div style="font-family:'Sometype Mono',monospace;font-size:28px;font-weight:700;color:var(--gg-color-primary-brown)">{hourly}g/hr</div>
          <div style="font-family:'Sometype Mono',monospace;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px">Carb Target</div>
        </div>
        <div style="padding:20px;background:#fff;border:2px solid var(--gg-color-primary-brown)">
          <div style="font-family:'Sometype Mono',monospace;font-size:28px;font-weight:700;color:var(--gg-color-primary-brown)">{total}g</div>
          <div style="font-family:'Sometype Mono',monospace;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px">Total Race Carbs</div>
        </div>
      </div>

      <div style="padding:16px;background:#fff;border-left:3px solid var(--gg-color-gold);margin:16px 0">
        <strong>Race-day range:</strong> {range_str}<br>
        <strong>Hydration:</strong> {hydration.get('target_ml_per_hour', 600)}ml/hr with {hydration.get('electrolytes', '500-1000mg sodium/hr')}<br>
        <strong>Pre-race meal:</strong> 3-4 hours before start, high carb, moderate protein, low fat/fiber
      </div>
    </div>'''


# ── Entry point when called as script ──
if __name__ == '__main__':
    import sys
    args = [a for a in sys.argv[1:] if a != '--store-mode']
    store_mode = '--store-mode' in sys.argv[1:]
    if len(args) < 1:
        print("Usage: python3 training_guide_builder.py <athlete_id> [output_path] [--store-mode]")
        sys.exit(1)
    athlete_id = args[0]
    output = args[1] if len(args) > 1 else None
    path = generate_training_guide(athlete_id, output, store_mode=store_mode)
    print(f"✅ Training guide: {path}")
