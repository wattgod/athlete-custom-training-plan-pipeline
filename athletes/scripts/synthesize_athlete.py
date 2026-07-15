#!/usr/bin/env python3
"""
Synthetic athlete generator — realistic, never-identical avatars.

Produces webhook-shaped intake dicts (the same payload the real
questionnaire posts) so synthetic athletes flow through the EXACT
production path: _questionnaire_to_markdown -> intake_to_plan -> plan.

Design goals:
  - REALISTIC: every athlete is a coherent person (FTP plausible for sex
    and weight, race far enough out to build a plan, days that don't
    conflict, masters athletes skew older, etc.)
  - VARIED: persona library × randomized specifics = effectively infinite
    distinct athletes
  - REPRODUCIBLE: seeded by (date, index) so a given day is repeatable but
    no two days are the same. (Python random is seeded explicitly here —
    we never rely on wall-clock randomness.)

Usage:
    from synthesize_athlete import synthesize
    intake = synthesize(seed="2026-06-16", index=0)   # webhook intake dict

    # or from the CLI, print one as JSON:
    python3 synthesize_athlete.py 2026-06-16 0
"""

import json
import random
import sys
from datetime import date, datetime, timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_IDX = {d: i for i, d in enumerate(DAYS)}

# Synthetic athletes race REAL events drawn from the 1,184-race snapshot
# (real_races). Discipline maps to which database the race comes from; mtb
# events live in the gravel DB, so mtb athletes draw gravel races.
RACE_DISCIPLINE = {"gravel": "gravel", "road": "road", "mtb": "gravel"}

# Personas — each constrains the randomized specifics into a coherent person.
PERSONAS = [
    {
        "key": "time_crunched_parent",
        "label": "Time-crunched parent fitting training around work + kids",
        "age": (35, 48), "hours": (5, 8), "ftp_known": 0.8,
        "ftp_wkg": (2.4, 3.4), "years": (3, 12), "disciplines": ["gravel", "road"],
        "goal": ["Finish Strong", "Compete"], "stress": ["moderate", "high"],
        "strength_want": 0.6, "off_days": (2, 3), "race_mi": (40, 110),
    },
    {
        "key": "masters_returner",
        "label": "Masters athlete returning after a layoff",
        "age": (50, 63), "hours": (6, 9), "ftp_known": 0.4,
        "ftp_wkg": (2.2, 3.1), "years": (8, 25), "disciplines": ["gravel", "road"],
        "goal": ["Finish Strong", "Finish"], "stress": ["low", "moderate"],
        "strength_want": 0.7, "off_days": (2, 3), "race_mi": (40, 100),
    },
    {
        "key": "ambitious_first_timer",
        "label": "Ambitious first-timer chasing their first big event",
        "age": (27, 40), "hours": (7, 11), "ftp_known": 0.2,
        "ftp_wkg": (2.3, 3.2), "years": (1, 3), "disciplines": ["gravel", "mtb"],
        "goal": ["Finish Strong", "Finish"], "stress": ["moderate"],
        "strength_want": 0.4, "off_days": (1, 2), "race_mi": (35, 90),
    },
    {
        "key": "veteran_podium_chaser",
        "label": "Experienced racer chasing a podium",
        "age": (30, 46), "hours": (10, 15), "ftp_known": 0.95,
        "ftp_wkg": (3.4, 4.6), "years": (6, 18), "disciplines": ["gravel", "road"],
        "goal": ["Podium", "Compete"], "stress": ["low", "moderate"],
        "strength_want": 0.7, "off_days": (1, 2), "race_mi": (55, 165),
    },
    {
        "key": "weekend_warrior",
        "label": "Weekend warrior wanting to finish strong without overhauling life",
        "age": (38, 55), "hours": (4, 7), "ftp_known": 0.6,
        "ftp_wkg": (2.2, 3.2), "years": (2, 15), "disciplines": ["gravel", "road", "mtb"],
        "goal": ["Finish Strong", "Finish"], "stress": ["moderate", "high"],
        "strength_want": 0.5, "off_days": (2, 3), "race_mi": (30, 80),
    },
]

STRENGTH_EQUIP = ["full gym", "home gym", "dumbbells", "minimal", "bodyweight"]


def _rng(seed: str, index: int) -> random.Random:
    return random.Random(f"{seed}::{index}")


def _persona_by_key(key):
    for p in PERSONAS:
        if p["key"] == key:
            return p
    return None


def synthesize(seed: str, index: int = 0, today: str = None,
               persona_key: str = None, race: dict = None) -> dict:
    """Return a realistic, reproducible webhook intake dict.

    seed: stable per-day key (e.g. an ISO date). index: distinct athlete
    within the day. today: ISO date the plan is built relative to (race
    dates are placed comfortably in the future from here).

    persona_key: force a specific persona (else random). race: force a
    specific target race (a real_races dict with name/date/distance_mi/
    elevation_ft/discipline) instead of a random pick — used by the coverage
    sweep to build the main personas against EACH race in the database.
    """
    r = _rng(seed, index)
    base_day = (datetime.strptime(today, "%Y-%m-%d").date() if today
                else date(2026, 6, 16))

    persona = _persona_by_key(persona_key) or r.choice(PERSONAS)
    sex = r.choice(["Male", "Male", "Female"])  # ~1/3 female
    age = r.randint(*persona["age"])

    # weight coherent with sex
    weight = r.randint(150, 195) if sex == "Male" else r.randint(118, 158)
    weight_kg = weight / 2.205
    height_ft = 5
    height_in = r.randint(6, 11) if sex == "Male" else r.randint(2, 8)

    # FTP from a plausible W/kg band for the persona
    wkg = round(r.uniform(*persona["ftp_wkg"]), 2)
    ftp = int(round(weight_kg * wkg / 5) * 5)
    ftp_known = r.random() < persona["ftp_known"]
    # Athletes who don't know their FTP express it two ways IRL: they type
    # "unknown"/"N/A", or they just leave the field BLANK. The blank case once
    # hard-failed intake validation and refunded a real customer, so the
    # fleet must exercise it — half of unknown-FTP avatars submit "" not
    # "unknown". (Both must estimate FTP from weight, never block.)
    ftp_value = (ftp if ftp_known
                 else ("" if r.random() < 0.5 else "unknown"))

    hours = r.randint(*persona["hours"])
    years = r.randint(*persona["years"])

    discipline = r.choice(persona["disciplines"])

    # Pick a REAL race from the snapshot, matched to discipline + far enough
    # out to build a plan. Fall back to a plausible invented race only if the
    # snapshot is missing (e.g. not yet built). A forced `race` (coverage
    # sweep) skips the pick and drives discipline from the race itself.
    if race is not None:
        discipline = race.get("discipline") or discipline
    else:
        from real_races import pick as pick_race
        race_mi_lo, race_mi_hi = persona.get("race_mi", (35, 130))
        race = pick_race(r, discipline=RACE_DISCIPLINE[discipline],
                         min_weeks=8, max_weeks=28, today=base_day.isoformat(),
                         min_mi=race_mi_lo, max_mi=race_mi_hi)
    if race:
        race_name = race["name"]
        race_date = race["date"]
        distance = int(round(float(race["distance_mi"])))
        elevation = int(race.get("elevation_ft") or distance * 70)
        weeks_out = round((datetime.strptime(race_date, "%Y-%m-%d").date()
                           - base_day).days / 7)
    else:
        race_name = f"Synthetic {discipline.title()} Classic"
        distance = r.choice([40, 65, 100, 130])
        elevation = distance * r.randint(40, 130)
        weeks_out = r.randint(8, 24)
        race_date = (base_day + timedelta(weeks=weeks_out)).isoformat()

    goal = r.choice(persona["goal"])

    # Days: a coherent training week — off days, ONE long-ride day, two
    # interval days that are NOT adjacent to the long ride or to each other
    # (the engine bans back-to-back hard days; the questionnaire shouldn't
    # request an impossible layout).
    n_off = r.randint(*persona["off_days"])
    off_days = r.sample(DAYS, n_off)
    remaining = [d for d in DAYS if d not in off_days]
    long_day = r.choice([d for d in ("Saturday", "Sunday") if d in remaining]
                        or remaining)

    def _adjacent(a, b):
        return abs(_DAY_IDX[a] - _DAY_IDX[b]) == 1

    interval_days = []
    candidates = [d for d in remaining if d != long_day and not _adjacent(d, long_day)]
    r.shuffle(candidates)
    for d in candidates:
        if len(interval_days) >= 2:
            break
        if all(not _adjacent(d, chosen) for chosen in interval_days):
            interval_days.append(d)

    want_strength = r.random() < persona["strength_want"]

    intake = {
        "name": f"Avatar {seed.replace('-', '')}{index}",
        "email": f"avatar-{seed}-{index}@synthetic.local",
        "sex": sex,
        "age": age,
        "weight": weight,
        "height_ft": height_ft,
        "height_in": height_in,
        "ftp": ftp_value,
        "years_cycling": str(years),
        "priorPlanExperience": str(min(years, r.randint(0, 4))),
        "hours_per_week": str(hours),
        "trainer_access": r.choice(["smart trainer", "smart trainer", "none"]),
        "long_ride_days": [long_day],
        "interval_days": interval_days,
        "off_days": off_days,
        "strength_current": r.choice(["none", "occasional", "1x/week", "2x/week"]),
        "strength_want": "yes" if want_strength else "no",
        "strength_equipment": r.choice(STRENGTH_EQUIP) if want_strength else "minimal",
        "sleep_quality": r.choice(["fair", "good", "good", "excellent"]),
        "stress_level": r.choice(persona["stress"]),
        "injuries": r.choice(["None", "None", "None", "occasional knee niggle",
                              "tight lower back"]),
        "notes": f"[synthetic:{persona['key']}]",
        "races": [{
            "name": race_name, "date": race_date,
            "distance": f"{distance} miles", "priority": "A", "goal": goal,
        }],
        # carried for the judge/report, not consumed by the questionnaire
        "_meta": {
            "persona": persona["key"], "persona_label": persona["label"],
            "discipline": discipline, "weeks_out": weeks_out,
            "wkg": wkg, "ftp_known": ftp_known,
        },
    }
    return intake


if __name__ == "__main__":
    seed = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(json.dumps(synthesize(seed, idx), indent=2))
