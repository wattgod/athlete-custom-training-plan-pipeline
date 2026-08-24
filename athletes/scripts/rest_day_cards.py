"""Rest-day cards: no blank calendar days.

Matti's rule (Aug 23 2026): a rest day is a scheduled day, not a hole. It
carries active-recovery work — mobility, a walk, sleep, eating like you
trained — in the product-surface voice. Every Day Off card the pipeline
emits gets its body here; `plan_ir._rest_session` is the single caller on
the canonical path, so custom and base plans cannot diverge.

Variants are chosen by calendar context (pre-plan, recovery week, race
week, day before/after the race, standard) and, within a context, rotated
deterministically on (athlete_seed, date) so an athlete never sees the same
standard card twice in a row and two athletes do not get identical
calendars. Copy is deliberately short (voice_rules.yaml rest_card_max_words).
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any, Dict, Optional

STANDARD = [
    (
        "Rest Day",
        "Off the bike, not off the plan.\n\n"
        "Ten minutes of hip and lower-back mobility, the stuff that gets skipped on ride days. "
        "A 20-30 minute walk if the legs feel like wood. Lights out thirty minutes earlier than usual.\n\n"
        "No riding. Tomorrow needs you.",
    ),
    (
        "Rest Day",
        "Off the bike. This week's work gets absorbed today, not added to.\n\n"
        "Foam roll quads and glutes, eight to ten minutes. One long walk. "
        "Eat like you trained; a rest day is not a diet day.\n\n"
        "If you feel great and want to ride, that is the point. Don't.",
    ),
    (
        "Rest Day",
        "Sleep is the assignment.\n\n"
        "Mobility: couch stretch 2 x 60 seconds per side, ten thoracic rotations each way, "
        "a 60-second dead hang if you have a bar. Then leave it alone.\n\n"
        "Normal life counts as recovery. Errands, kids, the lawn. No 'easy spin.'",
    ),
    (
        "Rest Day",
        "Nothing on the bike.\n\n"
        "Fifteen minutes on calves, hip flexors and lower back. An evening walk. An early night.\n\n"
        "Rest days are where the fitness shows up. Protect them like key sessions.",
    ),
]

RECOVERY_WEEK = [
    (
        "Rest Day",
        "Recovery-week rest day. Fatigue is supposed to drop this week; help it.\n\n"
        "Ten minutes of mobility, a nap if you can get one, an honest early bedtime. "
        "Eat enough. A recovery week is not a weight-loss week.\n\n"
        "Feeling flat today is normal. Still flat on Friday, message me.",
    ),
    (
        "Rest Day",
        "Reset day. The block lands now.\n\n"
        "A walk, a stretch, food on the plate. Nothing with a heart-rate strap.\n\n"
        "If you are itching to ride, good. Hold it. That itch is the fitness arriving.",
    ),
]

RACE_WEEK = (
    "Rest Day — Race Week",
    "Freshness is the work this week.\n\n"
    "Light mobility only: hips, back, calves, ten minutes. A short walk. Feet up. "
    "Pack and check the bike today so nothing happens tomorrow.\n\n"
    "No test efforts. No 'just checking the legs.'",
)

DAY_BEFORE_RACE = (
    "Day Off — Race Prep",
    "Travel, number pickup, bike check, feet up.\n\n"
    "Five minutes of mobility after the drive. Familiar food, carbs on the plate, nothing new. "
    "Early night even if you won't sleep well; lying down counts.\n\n"
    "Everything about today should be boring.",
)

DAY_AFTER_RACE = (
    "Day Off — Well Done",
    "Nothing today. Eat, drink, sleep, and let it land.\n\n"
    "A slow walk if the legs want one. No analysis yet; the file will still be there on Tuesday.\n\n"
    "Well done.",
)

PRE_PLAN = (
    "Pre-Plan Rest",
    "Plan starts tomorrow.\n\n"
    "Off the bike. Light stretching if you want it. Sleep, water, real food.\n\n"
    "Charge the head unit, check the tyres, know where the shoes are.",
)


def pre_plan_body(days_to_start: int) -> str:
    """Pre-plan week rest card; the day before the plan starts gets PRE_PLAN."""
    if int(days_to_start or 0) <= 1:
        return PRE_PLAN[1]
    return (
        f"Plan starts in {int(days_to_start)} days. Today is off.\n\n"
        "Ride if you normally would, easy. Otherwise a walk, some stretching, an early night.\n\n"
        "Nothing to bank this week. Arrive rested."
    )


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _rotate(options, athlete_seed: Any, ordinal: int) -> int:
    """Cycle through every variant before repeating (ordinal = how many rest
    days of this kind the athlete has already had), starting at an
    athlete-specific offset so two calendars do not look alike."""
    offset = int(hashlib.sha256(str(athlete_seed).encode("utf-8")).hexdigest(), 16)
    return (offset + int(ordinal or 0)) % len(options)


def rest_day_card(day: Any, *, week: Optional[Dict[str, Any]] = None,
                  race_date: Any = None, athlete_seed: Any = None,
                  ordinal: int = 0) -> Dict[str, str]:
    """Title + body for the Day Off card on `day`.

    `week` is the plan_dates week dict (keys used: week, phase,
    is_recovery_week, is_race_week). `athlete_seed` is the stable athlete
    identity used everywhere else for rotation; `ordinal` counts the rest
    days already emitted for this athlete so variants cycle, never repeat
    back to back."""
    current = _as_date(day)
    race = _as_date(race_date)
    week = week or {}
    if current and race:
        if current == race - timedelta(days=1):
            return {"title": DAY_BEFORE_RACE[0], "body": DAY_BEFORE_RACE[1]}
        if current == race + timedelta(days=1):
            return {"title": DAY_AFTER_RACE[0], "body": DAY_AFTER_RACE[1]}
    if int(week.get("week") or 0) == 0 or str(week.get("phase") or "") == "pre_plan":
        return {"title": PRE_PLAN[0], "body": PRE_PLAN[1]}
    if week.get("is_race_week") or str(week.get("phase") or "") == "race":
        return {"title": RACE_WEEK[0], "body": RACE_WEEK[1]}
    if week.get("is_recovery_week") or str(week.get("week_type") or "") == "recovery":
        title, body = RECOVERY_WEEK[_rotate(RECOVERY_WEEK, athlete_seed, ordinal)]
        return {"title": title, "body": body}
    title, body = STANDARD[_rotate(STANDARD, athlete_seed, ordinal)]
    return {"title": title, "body": body}
