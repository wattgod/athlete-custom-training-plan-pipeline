"""Weekly calendar notes as a story, in the coach's voice.

Matti (Aug 23 2026): "a training plan is a story. They need to feel my
voice along the way." Before this, every week got the same three template
paragraphs with a workout name swapped in.

VOICE AUTHORITY: endure-coaching-ops/skills/coaching-reviews/references/
voice-and-rapport.md (compression treatment, first-person presence, insight
over summary, humor rules, adversarial voice test). athletes/config/
voice_rules.yaml is only the machine-checkable subset of that guide.

Each Monday note has three beats (athletes/config/voice_rules.yaml):
  1. position  -- week N of M, the phase, what this week is FOR, and how it
                  sits against last week / next week;
  2. key work  -- the week's key sessions BY NAME, each with one sentence on
                  why it exists (family-level coaching, not a description);
  3. notice    -- one thing to watch or one rule for the week.
Plus, at most once per plan per aside, a dry one-liner -- the wink, not the
bit. No headings, no bold, <=130 words, and no sentence repeats across the
plan's notes (post_render_validator enforces all of that).

Everything is derived from PlanIR; nothing is free-typed per athlete, so the
notes stay truthful when the plan changes. Register: product surface.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Family-level coaching lines. Keyed on archetype_id / title patterns. Each
# family has several phrasings; the plan cycles through them so the same
# family across weeks never reads identically.
# ---------------------------------------------------------------------------
_FAMILY_RULES: List[Tuple[re.Pattern, str, List[str]]] = [
    (re.compile(r"ftp test", re.I), "ftp_test", [
        "{name} {day}: your numbers for the rest of the plan come from this. Rested, fueled, no heroics in the warm-up.",
        "{name} {day}. Ride it like a race you have to finish: even, then everything in the last five minutes.",
    ]),
    (re.compile(r"anaerobic test", re.I), "anaerobic_test", [
        "{name} {day} tells me how much snap you have above threshold. It will hurt for three minutes; that is the whole test.",
    ]),
    (re.compile(r"openers|tune-up|tune up", re.I), "openers", [
        "{name} {day}: short, sharp, and done before you feel like you have started. The point is to wake the legs, not test them.",
        "{name} {day}: a handful of efforts to remind the body what fast feels like. Finish wanting more.",
    ]),
    (re.compile(r"30[-/ ]?15|30[-/ ]?30|40[-/ ]?20|billat|r[oø]nnestad|vo2", re.I), "vo2", [
        "{name} {day}. The short recoveries are the trick: you never fully recover, so the oxygen system stays pinned without the legs blowing up.",
        "{name} {day} is the hardest thing this week. Start the first rep at the number, not above it, and let the set get hard on its own.",
        "{name} {day}. If the power fades more than ten percent, the set is over. Ending early is correct; grinding out junk reps is not.",
    ]),
    (re.compile(r"threshold|over[- ]?under|tte|float", re.I), "threshold", [
        "{name} {day}: sustained work at the edge. Hold the number, do not chase it; the last interval should feel like the first, only later.",
        "{name} {day}. This is where race pace gets rehearsed. Steady, seated, breathing hard but not ragged.",
    ]),
    (re.compile(r"sweet spot|g-?spot|tempo", re.I), "tempo", [
        "{name} {day}: hard enough to matter, easy enough to repeat. This is the work that adds up quietly.",
        "{name} {day}. Comfortably hard, nothing more. If you are grimacing, you are over it.",
        "{name} {day}: the middle gear of the plan. Not easy, not a test, done with something left.",
    ]),
    (re.compile(r"cadence|sfr|torque|stomp|big[- ]gear", re.I), "cadence", [
        "{name} {day}: power stays flat, the gear changes. Low rungs load the legs, high rungs teach them to spin. Watch the knees on the low stuff.",
        "{name} {day} is skill work, not fitness work. Smooth circles at every cadence; the rpm targets are in the workout.",
        "{name} {day} again. Same rungs, and by now the low-cadence ones should feel like strength, not struggle.",
    ]),
    (re.compile(r"sprint|anaerobic|killers|glycolytic|stars in your eyes|microburst", re.I), "anaerobic", [
        "{name} {day}: short, all-out, full recovery between. Quality over quantity; the fifth good sprint beats the eighth sloppy one.",
        "{name} {day}. Fast first, then tired. Start each effort committed or skip it.",
    ]),
    (re.compile(r"race sim|simulation|dress rehearsal", re.I), "race_sim", [
        "{name} {day} is the spine of the race, rehearsed: the decisive efforts, the tempo between them, the fueling at race rate. Ride it like {race}.",
        "{name} {day}. Same fuel, same bottles, same clothing as race day. Anything you have not practiced by now is a gamble.",
    ]),
    (re.compile(r"heat", re.I), "heat", [
        "{name} {day} is about the heat, not the watts. Keep the power honest and let the temperature do the work.",
    ]),
    (re.compile(r"fatmax|durability|tired|fatigued", re.I), "durability", [
        "{name} {day}: the quality comes late, on tired legs. That is the point. Fuel early so you are still there for it.",
    ]),
    (re.compile(r"endurance|z2|base|long|blocks|surges|spin", re.I), "endurance", [
        "{name} {day} is the long one. Boring on purpose. Fuel from the first twenty minutes, not when you get hungry.",
        "{name} {day}: steady, conversational, and longer than feels necessary. This is the aerobic work everything else sits on.",
        "{name} {day}. Keep it easy enough that tomorrow is not compromised. If you finish wondering whether it was too easy, it was right.",
    ]),
]

_NOTICE: Dict[str, List[str]] = {
    "pre_plan": [
        "Nothing to prove this week. Turn up Monday rested and with the bike working.",
    ],
    "testing": [
        "This week sets the numbers. Do not train through the tests; show up fresh.",
    ],
    "load": [
        "Watch the easy days. If they creep up in pace, the hard days will start falling short.",
        "Sleep is the variable you control. Seven hours minimum this week, more after the hard days.",
        "Missed work stays missed. Do not stack two hard days to make up a session.",
        "If a hard session falls apart, stop and message me. One bad workout is data; two is a pattern.",
        "Fuel the long ride like it matters, because it does. Under-eating on Sunday shows up on Tuesday.",
        "Two good hard days beat three average ones. If the third is not there, make it easy.",
        "Check the tyres and the chain this week. Mechanicals are the only bad luck you can schedule out.",
        "The easy days are not optional filler. They are where the hard days come from.",
        "Notice how the warm-ups feel. When they start feeling short, the fitness is moving.",
        "Keep the hard days hard and the easy days embarrassing. That gap is the whole method.",
    ],
    "recovery": [
        "Fatigue should drop noticeably by Thursday. If it does not, say so before the weekend.",
        "Easy means easy. The recovery week fails when the easy rides get competitive.",
    ],
    "taper": [
        "Feeling sluggish in a taper is normal. Feeling sharp by the weekend is the goal. Do not add work to fix a bad day.",
    ],
    "race": [
        "Nothing new this week: no new food, no new position, no new kit. Sleep well Thursday; Friday night rarely cooperates.",
    ],
}

_ASIDES: List[str] = [
    "Yes, the easy days are supposed to be that easy.",
    "Nobody has ever regretted an early night before a hard session.",
    "The plan works if you do the boring parts.",
    "Rest days count. Strava does not.",
    "The fitness is in the weeks you don't notice.",
]

# AE-9.3 / AE-9.4 (2026-08-24 TP review, round-2 addendum): two fixed-form
# coach templates, verbatim per the ruling -- never rotated, reworded, or
# word-trimmed like the notes above. voice_lint.py's fixed-template
# allowlist (keyed on these exact titles) exempts them from the cross-week
# sentence-dupe check and the weekly word cap for the same reason: they are
# not freely-authored coach prose, they are a fixed protocol.
SELF_REVIEW_TITLE = "Week Self Review - 3 Qs"
SELF_REVIEW_BODY = (
    "Tell me:\n"
    "1. What went well and why?\n"
    "2. What went badly and why?\n"
    "3. ONE thing you can DO next week that's:\n"
    " a) In your control\n"
    " b) Not too big of a lift\n"
    " c) Impactful\n\n"
    "Please complete this at the end of every week and put your answers in "
    "the comments on this note. It will greatly improve you as an athlete "
    "and help me coach you better."
)

COMMENT_PROTOCOL_TITLE = "How To Comment On Workouts"
COMMENT_PROTOCOL_BODY = (
    "As a reminder, do your workout comments going forward like this:\n\n"
    "1. Workout Readiness - (e.g. 6/10; couldn't fall asleep bc of stress)\n"
    "2. Workout Execution - (e.g. 5/10; skipped last set after going too "
    "hard in the first set)\n"
    "3. Nutrition - (e.g. 5/10; didn't eat during my hard 2 hour interval "
    "ride, but did eat before and after)\n"
    "4. Misc - (e.g. lower back acting up again)\n\n"
    "1-3: Rate out of 10 (10 is the best); add details if possible; e.g., "
    "\"I ate two 50g carbohydrate bars\" or \"Felt sluggish to start\" etc.\n"
    "Misc: Have at it, or don't."
)


# ---------------------------------------------------------------------------
# Public-preview product copy
# ---------------------------------------------------------------------------

_DESCRIPTION_HEADING = re.compile(r"(?m)^([A-Z][A-Z -]+):\s*$")


def _description_section(description: str, heading: str) -> str:
    """Return one real section from an engine-rendered workout description.

    Public previews must show the workout the athlete will actually receive,
    not a second, hand-written approximation of it.  The Nate renderer owns
    PURPOSE and EXECUTION; this helper only projects that checked-in copy into
    the bounded public card contract.
    """
    text = str(description or "").replace("\r\n", "\n").strip()
    wanted = str(heading or "").strip().upper()
    matches = list(_DESCRIPTION_HEADING.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip().upper() != wanted:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        lines = [re.sub(r"^\s*[-*]\s*", "", line).strip()
                 for line in body.splitlines()]
        return " ".join(line for line in lines if line)
    return ""


def _bounded_product_copy(text: str, maximum: int) -> str:
    """Normalize whitespace and avoid cutting a public card mid-sentence."""
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) <= maximum:
        return normalized
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    kept: List[str] = []
    for sentence in sentences:
        candidate = " ".join(kept + [sentence])
        if len(candidate) > maximum:
            break
        kept.append(sentence)
    if kept:
        return " ".join(kept)
    return normalized[:maximum].rstrip(" ,;:-")


def _assert_product_voice(copy: Dict[str, str]) -> None:
    """Apply the same Git-tracked voice contract used on TP calendar notes."""
    # Local import avoids making voice_lint part of story-note module startup.
    if __package__:
        from .voice_lint import check_copy, load_rules
    else:
        from voice_lint import check_copy, load_rules

    rules = load_rules()
    findings: List[str] = []
    for field, text in copy.items():
        findings.extend(check_copy(text, rules=rules, where=f"preview {field}"))
    if findings:
        raise ValueError("preview copy failed the coaching voice contract: "
                         + "; ".join(findings))


def render_preview_workout_copy(
    session: Any, *, description: str, day: str, race_name: str,
) -> Dict[str, str]:
    """Project real workout copy plus the canonical product-surface voice.

    PURPOSE is copied from the exact engine-rendered workout.  The coach note
    uses the same family lines as the delivered weekly story.  If a new
    workout family has no authored line yet, its real EXECUTION section is
    shown instead; we fail closed if neither source exists rather than invent
    generic marketing copy.
    """
    purpose = _description_section(description, "PURPOSE")
    if not purpose:
        raise ValueError("engine-rendered workout has no PURPOSE section")

    title = _clean_title(str(_get(session, "title") or "Workout"))
    family = _family(session)
    if family:
        _, phrasings = family
        coach_note = phrasings[0].format(
            name=title, day=day, race=race_name)
    else:
        execution = _description_section(description, "EXECUTION")
        if not execution:
            raise ValueError(
                "workout has neither a canonical family line nor EXECUTION copy")
        coach_note = f"{title} {day}. {execution}"

    result = {
        "purpose": _bounded_product_copy(purpose, 260),
        "coach_note": _bounded_product_copy(coach_note, 420),
    }
    _assert_product_voice(result)
    return result


def render_preview_strength_copy(
    *, title: str, focus: str, day: str, race_name: str,
) -> Dict[str, str]:
    """Canonical product-surface framing for a library strength session."""
    clean_focus = str(focus or "Cycling-specific strength").strip().rstrip(".")
    result = {
        "purpose": _bounded_product_copy(f"{clean_focus}.", 260),
        "coach_note": _bounded_product_copy(
            f"{title} {day}. I want two clean reps left in reserve. This supports "
            f"the riding for {race_name}; if it starts competing with it, stop.",
            420,
        ),
        "fueling_guidance": (
            "Eat normally beforehand. Pair protein with carbohydrate within the hour after."
        ),
    }
    _assert_product_voice(result)
    return result


def render_preview_race_copy(race_name: str) -> Dict[str, str]:
    """Canonical race-card copy used by the public TrainingPeaks preview."""
    result = {
        "purpose": _bounded_product_copy(
            f"Execute the pacing, fueling, equipment, and decision plan built for {race_name}.",
            260,
        ),
        "coach_note": (
            "First third patient. Middle third useful work only. Final third: "
            "race what is left. Solve the next problem without borrowing from the finish."
        ),
    }
    _assert_product_voice(result)
    return result

# AE-9.1 (2026-08-24 TP review): the Monday note is the floor, not the
# ceiling -- 1-2 short mid-week notes per week, speaking to how the athlete
# is likely feeling at that point in the block. Unlike _NOTICE (which wraps
# via modulo), these SKIP once the pool is exhausted rather than repeat --
# same choice _FAMILY_RULES makes ("the athlete knows this family by now;
# say nothing new") -- so voice_lint's cross-week sentence-dupe check can
# never fail here regardless of plan length.
_MIDWEEK_LOAD_FEEL: List[str] = [
    "Legs heavy today is the load landing, not a warning sign.",
    "If today feels flat, that is the last two hard days still in your legs. Normal.",
    "A dead-legs day mid-week is the training working, not the training gone wrong.",
    "Slower than usual today is expected here. The adaptation happens on the rest day, not this one.",
    "A grey day mid-week is the block doing its job. Ride it, do not chase it.",
    "If the legs are asking questions today, that is the load talking. Answer with pace, not power.",
    "Nothing wrong with a sluggish Thursday in a week like this. Show up, keep it honest, move on.",
    "A heavy Wednesday in a week like this one is the bill for Monday and Tuesday, not a setback.",
]

_MIDWEEK_LONG_RIDE_FUEL: List[str] = [
    "Fuel the long ride from hour zero, not when you get hungry.",
    "Bottles mixed and food counted before you roll out for the long one.",
    "Start eating on the long ride before you want to. By the time you are hungry, you are behind.",
    "The long ride's fuel plan starts at the door, not at mile twenty.",
    "Pre-load fluids the night before the long ride; do not try to catch up on the bike.",
    "Lay out the long ride's food tonight so tomorrow morning is not a scramble.",
    "Set a fuel timer for the long ride. Do not rely on feeling hungry to remind you.",
    "The long ride rewards the rider who eats early. Start the first bar before you think you need it.",
    # AE-9.1b (2026-08-24 TP review, addendum): a repeated theme owns the
    # repeat in the coach's voice instead of pretending novelty. These sit
    # AFTER the first-instance variants above so they only fire once the
    # athlete has actually seen the earlier ones -- the self-reference has
    # to be true, not just funny.
    "This fuel note again. Eat early on the long ride; you've heard it before because it keeps not sticking.",
    "Same reminder, new week: bottles and food sorted before you roll out. Some lessons need saying more than once.",
    "Fuel the long ride early -- yes, still. If it were sinking in on the first pass, this note would stop showing up.",
]

_MIDWEEK_WEEKDAY_PREFERENCE = (3, 2, 1, 4)  # Thursday, Wednesday, Tuesday, Friday


def _midweek_feel_date(dated: List[Any]) -> Optional[date]:
    """The load week's own Thu/Wed/Tue/Fri, in that order of preference --
    whichever weekday the plan actually scheduled a session on this week."""
    by_weekday = {_as_date(_get(s, "date")).weekday(): _as_date(_get(s, "date")) for s in dated}
    for weekday in _MIDWEEK_WEEKDAY_PREFERENCE:
        if weekday in by_weekday:
            return by_weekday[weekday]
    return None


def _midweek_long_ride(dated: List[Any]) -> Optional[Any]:
    """This week's genuine long ride (bike, >=90min), or None."""
    bikes = [s for s in dated if str(_get(s, "tp_kind") or "") == "bike"
             and int(_get(s, "duration_s") or 0) >= 5400]
    return max(bikes, key=lambda s: int(_get(s, "duration_s") or 0)) if bikes else None

_WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _seed(*parts: Any) -> int:
    joined = "\x1f".join("" if p is None else str(p) for p in parts)
    return int(hashlib.sha256(joined.encode("utf-8")).hexdigest(), 16)


def _family(session: Any) -> Optional[Tuple[str, List[str]]]:
    probe = " ".join(str(_get(session, k) or "") for k in ("archetype_id", "title"))
    if _get(session, "is_field_test"):
        probe = "ftp test " + probe
    if _get(session, "is_simulation") or _get(session, "is_dress_rehearsal"):
        probe = "race sim " + probe
    if int(_get(session, "duration_s") or 0) >= 5400 and re.search(r"z2|endurance|long|blocks", probe, re.I):
        return next((k, l) for _, k, l in _FAMILY_RULES if k == "endurance")
    for pattern, key, lines in _FAMILY_RULES:
        if pattern.search(probe):
            return key, lines
    return None


def _clean_title(title: str) -> str:
    return re.sub(r"\s*\(\d+ of \d+\)\s*$", "", str(title or "")).strip()


def _is_key(session: Any) -> bool:
    if str(_get(session, "tp_kind") or "") != "bike":
        return False
    if _get(session, "is_field_test") or _get(session, "is_simulation") or _get(session, "is_dress_rehearsal"):
        return True
    fam = _family(session)
    if not fam:
        return False
    return fam[0] not in {"endurance", "heat"} or int(_get(session, "duration_s") or 0) >= 2 * 3600


_PHASE_LINES: Dict[str, List[str]] = {
    "base": [
        "Base. Nothing flashy; I want steady work and the point is accumulation.",
        "Base, still. The same shape as last week with a little more in it. That is how base works.",
        "Base, and the deepest week of it. Volume does the talking now; keep the intensity honest.",
    ],
    "build": [
        "Build. The intensity is specific now and the long rides have a purpose I have chosen. This is where the race gets made.",
        "Build, second week. The sessions repeat on purpose; the progression is in how they feel, not what they say.",
        "Build, and the heaviest of it. Everything on the calendar has a reason; nothing on it is filler.",
    ],
    "peak": [
        "Peak. The work is race-specific now and the margins are small; execute, do not experiment.",
        "Peak, second pass. Sharper, not longer. Freshness matters as much as the work from here.",
    ],
}


def _position_line(number: int, total: int, phase: str, week_type: str,
                   prev_type: Optional[str], next_type: Optional[str],
                   race_name: str, weeks_to_race: Optional[int],
                   phase_use: int = 0, legs_heavy_callback: bool = False) -> str:
    """``legs_heavy_callback`` is AE-9.1c: true only when an earlier week's
    ``_MIDWEEK_LOAD_FEEL`` note already told this athlete their legs would
    feel heavy, and this is the first fresh-legs-after-recovery week since --
    the payoff has to follow its own setup or it is not a callback, it is a
    non sequitur."""
    phase = (phase or "").replace("_", " ")
    if number == 0 or phase == "pre plan":
        return f"Week 0. The plan starts Monday. Arrive rested: sleep, normal riding if you have it, nothing heroic."
    if week_type == "testing":
        return f"Week {number} of {total}. Testing week: two assessments, everything else easy. I build the rest of the plan from what you do here."
    if week_type == "race":
        return f"Race week. {race_name} is {_race_day_phrase(weeks_to_race)}. The work is done; this week is about arriving fresh."
    if week_type == "taper":
        return f"Week {number} of {total}. Taper. I have dropped the volume and kept a little sharpness; fatigue leaves faster than fitness does."
    if week_type == "recovery":
        return f"Week {number} of {total}. Recovery week, and I mean it: the last block gets absorbed now, not later."
    if prev_type == "recovery":
        if legs_heavy_callback:
            return (f"Week {number} of {total}. Back into {phase} with fresh legs — the heavy ones "
                     "from a few weeks back are exactly why this feels good now.")
        return f"Week {number} of {total}. Back into {phase} with fresh legs. I want controlled work out of them, not a hero week."
    if next_type == "recovery":
        return f"Week {number} of {total}. Last load week of this block. I want the key sessions done properly; a reset follows."
    variants = _PHASE_LINES.get(phase) or _PHASE_LINES["base"]
    return f"Week {number} of {total}. " + variants[phase_use % len(variants)]


def _race_week_lines(plan_ir: Any, week: Any, sessions: List[Any]) -> List[str]:
    """Race-week copy. Keeps the coach-approved sentences from the Aug 2026
    template renderer: the A event is named from `events` (never invented
    from the snapshot when events exist), a B event is rendered only when it
    has a name, `mandatory` decides the mode sentence, and the fuel line
    uses the plan's race fuel range."""
    events = list(_get(plan_ir, "events") or [])
    snapshot = _get(plan_ir, "race_snapshot") or {}
    a_event = next((e for e in events if str(_get(e, "priority") or "").upper() == "A"), {})
    b_event = next((e for e in events if str(_get(e, "priority") or "").upper() == "B"), {})
    a_name = str(_get(a_event, "name") or _get(snapshot, "name") or "the A race")
    a_date = _as_date(_get(a_event, "date") or _get(snapshot, "date"))
    a_day = _WEEKDAY[a_date.weekday()] if a_date else "Race day"
    b_name = str(_get(b_event, "name") or "").strip()
    b_date = _as_date(_get(b_event, "date"))
    b_day = _WEEKDAY[b_date.weekday()] if b_date else "The B race"
    off_days = [
        _WEEKDAY[_as_date(_get(x, "date")).weekday()]
        for x in sessions
        if str(_get(x, "tp_kind") or "") == "day_off" and _as_date(_get(x, "date"))
    ]
    off_text = ", ".join(off_days) or "The written rest days"
    fuel_range = list(_get(_get(plan_ir, "fueling") or {}, "race_range_g_per_hour") or [])
    lines: List[str] = []
    choice_tail = ""
    if b_name:
        mandatory_b = bool(_get(b_event, "mandatory"))
        if mandatory_b:
            lines.append(f"Race week. {off_text} off. Openers before {a_name}. "
                         f"{b_name} is mandatory; {a_day} decides the mode.")
            choice_tail = f" {b_day}: normal legs, race it; heavy legs, completion mode."
        else:
            lines.append(f"Race week. {off_text} off. Openers before {a_name}. "
                         f"{b_name} is optional; {a_day} gets first claim on your legs.")
            choice_tail = f" {b_day} requires normal legs; otherwise skip it."
        event_fuel = f"{a_name} and {b_name}"
    else:
        lines.append(f"Race week. {off_text} off. Openers before {a_name}. {a_day} is the assignment.")
        event_fuel = a_name
    fuel = (f" Fuel {event_fuel} with familiar products at {fuel_range[0]}-{fuel_range[-1]} g/hr."
            if len(fuel_range) >= 2 else "")
    lines.append("No bonus miles or make-up work. Keep the openers controlled." + fuel)
    lines.append(re.sub(r"\s+", " ", "Inside or out—keep the written RPE smooth." + choice_tail
                        + " Pain, illness, or changed function: stop and tell me.").strip())
    lines.append(_NOTICE["race"][0])
    return lines


def _race_day_phrase(weeks_to_race: Optional[int]) -> str:
    return "Saturday" if weeks_to_race is not None and weeks_to_race <= 0 else "this weekend"


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _self_review_note(dated: List[Any]) -> Dict[str, str]:
    """AE-9.3: every week's Sunday -- or the week's final day, when the plan
    ends mid-week -- carries the fixed self-review template. A week's dated
    sessions never run past its own Sunday, so the week's own last dated day
    already IS "Sunday, or the final day if the plan ends mid-week": a full
    week's last session lands on Sunday, a partial closing week's last
    session lands wherever the plan actually stops (post-race Sunday
    included, when the race week runs the full Mon-Sun span)."""
    review_date = max(_as_date(_get(s, "date")) for s in dated)
    return {
        "date": review_date.isoformat(),
        "title": SELF_REVIEW_TITLE,
        "body": SELF_REVIEW_BODY,
    }


def render_story_notes(plan_ir: Any, *, max_words: int = 100) -> List[Dict[str, str]]:
    """One Monday note per plan week. Deterministic for a given PlanIR."""
    weeks = [w for w in (_get(plan_ir, "weeks") or []) if _get(w, "sessions")]
    if not weeks:
        return []
    athlete_id = str(_get(_get(plan_ir, "athlete"), "id") or "athlete")
    snapshot = _get(plan_ir, "race_snapshot") or {}
    a_event = next((e for e in (_get(plan_ir, "events") or [])
                    if str(_get(e, "priority") or "").upper() == "A"), {})
    race_name = str(_get(a_event, "name") or _get(snapshot, "name") or "race day")
    race_date = _as_date(_get(a_event, "date") or _get(snapshot, "date"))
    total = max(int(_get(w, "number") or 0) for w in weeks)

    family_use: Dict[str, int] = {}
    notice_use: Dict[str, int] = {}
    aside_order = sorted(range(len(_ASIDES)), key=lambda i: _seed(athlete_id, "aside", i))
    aside_cursor = 0
    focus_said = False
    phase_use: Dict[str, int] = {}
    midweek_feel_use = 0
    midweek_fuel_use = 0
    notes: List[Dict[str, str]] = []

    # AE-9.4 (2026-08-24 TP review, addendum): Day 1 of the plan -- the
    # earliest dated session across every week, pre-plan included when one
    # exists -- carries the comment-protocol note. One per plan. This date
    # is always shared with that week's own Monday note (Day 1 IS a Monday);
    # fulfillment_manifest.py's per-date collision handling (mirroring the
    # per-date handling it already does for workouts) is what lets both
    # coexist on the calendar rather than one silently clobbering the other.
    plan_first_date = min(
        (_as_date(_get(s, "date")) for w in weeks for s in (_get(w, "sessions") or [])
         if _as_date(_get(s, "date"))),
        default=None,
    )
    if plan_first_date:
        notes.append({
            "date": plan_first_date.isoformat(),
            "title": COMMENT_PROTOCOL_TITLE,
            "body": COMMENT_PROTOCOL_BODY,
        })

    # AE-9.1c (2026-08-24 TP review, addendum): notes are a thread, not
    # islands -- rendered in chronological order (the loop below), each one
    # aware of what an earlier note already told this athlete. `thread`
    # accumulates promises/themes as they are actually emitted; a callback
    # can only read a key here after the note that set it has already been
    # appended to `notes`, so a payoff can never precede its setup.
    thread: Dict[str, Any] = {"legs_heavy_setup_week": None, "legs_heavy_payoff_used": False}

    for idx, week in enumerate(weeks):
        sessions = list(_get(week, "sessions") or [])
        dated = [s for s in sessions if _as_date(_get(s, "date"))]
        if not dated:
            continue
        start = min(_as_date(_get(s, "date")) for s in dated)
        number = int(_get(week, "number") or idx)
        phase = str(_get(week, "phase") or "")
        week_type = str(_get(week, "week_type") or "").lower()
        if not week_type:
            # PlanIR weeks without an explicit type: the phase decides
            week_type = phase.lower() if phase.lower() in {"race", "taper", "recovery"} else "load"
        if number == 0 or phase == "pre_plan":
            week_type = "pre_plan"
        elif number == 1 and any(_get(s, "is_field_test") for s in sessions):
            week_type = "testing"
        prev_type = str(_get(weeks[idx - 1], "week_type") or "").lower() if idx else None
        next_type = str(_get(weeks[idx + 1], "week_type") or "").lower() if idx + 1 < len(weeks) else None
        weeks_to_race = ((race_date - start).days // 7) if race_date else None

        if week_type == "race":
            body = "\n\n".join(_race_week_lines(plan_ir, week, sessions))
            notes.append({"date": start.isoformat(), "title": f"Week {number}: Race Week", "body": body})
            notes.append(_self_review_note(dated))
            continue

        plain = week_type in {"load", "uber_load"} and prev_type != "recovery" and next_type != "recovery"
        legs_heavy_callback = bool(
            prev_type == "recovery"
            and thread["legs_heavy_setup_week"] is not None
            and not thread["legs_heavy_payoff_used"]
        )
        lines: List[str] = [_position_line(number, total, phase, week_type, prev_type, next_type,
                                           race_name, weeks_to_race,
                                           phase_use=phase_use.get(phase, 0) if plain else 0,
                                           legs_heavy_callback=legs_heavy_callback)]
        if legs_heavy_callback:
            thread["legs_heavy_payoff_used"] = True
        if plain:
            phase_use[phase] = phase_use.get(phase, 0) + 1
        focus = str(_get(_get(plan_ir, "coached_block") or {}, "focus") or "").strip().rstrip(".")
        if focus and not focus_said:
            lines.append(f"This block: {focus}.")
            focus_said = True

        key_sessions = [s for s in sorted(dated, key=lambda s: _as_date(_get(s, "date"))) if _is_key(s)]
        seen_families: set = set()
        for session in key_sessions[:2]:
            fam = _family(session)
            if not fam:
                continue
            key, phrasings = fam
            if key in seen_families:
                continue
            seen_families.add(key)
            use = family_use.get(key, 0)
            if use >= len(phrasings):
                continue  # the athlete knows this family by now; say nothing new
            family_use[key] = use + 1
            day = _WEEKDAY[_as_date(_get(session, "date")).weekday()]
            line = phrasings[use % len(phrasings)].format(
                name=_clean_title(_get(session, "title")), day=day, race=race_name)
            lines.append(line)

        # One dry line at most, and never the last word: the note ends on the
        # decision rule (voice-and-rapport.md: finish on pressure, permission,
        # a decision, or a direct request).
        if week_type in {"load", "testing"} and aside_cursor < len(aside_order) and idx % 2 == 1:
            lines.append(_ASIDES[aside_order[aside_cursor]])
            aside_cursor += 1

        pool = _NOTICE.get(week_type) or _NOTICE["load"]
        n_use = notice_use.get(week_type, 0)
        notice_use[week_type] = n_use + 1
        lines.append(pool[n_use % len(pool)])

        body = "\n\n".join(lines)
        while _word_count(body) > max_words and len(lines) > 2:
            lines.pop(-2)  # drop the aside, then key sessions from the end; keep the closing rule
            body = "\n\n".join(lines)

        label = {"pre_plan": "Pre-Plan", "testing": "Testing", "recovery": "Recovery", "taper": "Taper", "race": "Race Week"}.get(
            week_type, phase.replace("_", " ").title() or "Training")
        notes.append({
            "date": start.isoformat(),
            "title": f"Week {number}: {label}",
            "body": body,
        })

        # AE-9.1 (2026-08-24 TP review): the Monday note is the floor, not
        # the ceiling. 1-2 short mid-week notes, gated so they only fire
        # where they're actually true for this week -- never landing on a
        # date another note already claims (fulfillment_manifest keys a
        # native note by date; two notes on one date would collide).
        used_dates = {start.isoformat()}
        if (week_type in {"load", "uber_load"}
                and midweek_feel_use < len(_MIDWEEK_LOAD_FEEL)):
            feel_date = _midweek_feel_date(dated)
            if feel_date and feel_date.isoformat() not in used_dates:
                notes.append({
                    "date": feel_date.isoformat(),
                    "title": f"Week {number}: Midweek",
                    "body": _MIDWEEK_LOAD_FEEL[midweek_feel_use],
                })
                midweek_feel_use += 1
                used_dates.add(feel_date.isoformat())
                if thread["legs_heavy_setup_week"] is None:
                    thread["legs_heavy_setup_week"] = number
        if (week_type not in {"pre_plan", "testing"}
                and midweek_fuel_use < len(_MIDWEEK_LONG_RIDE_FUEL)):
            long_ride = _midweek_long_ride(dated)
            if long_ride:
                fuel_date = _as_date(_get(long_ride, "date")) - timedelta(days=1)
                if fuel_date and fuel_date.isoformat() not in used_dates:
                    notes.append({
                        "date": fuel_date.isoformat(),
                        "title": f"Week {number}: Fuel The Long Ride",
                        "body": _MIDWEEK_LONG_RIDE_FUEL[midweek_fuel_use],
                    })
                    midweek_fuel_use += 1
                    used_dates.add(fuel_date.isoformat())

        # AE-9.3: every trained week gets a Sunday self-review; week 0
        # (pre-plan, nothing trained yet) does not.
        if week_type != "pre_plan":
            notes.append(_self_review_note(dated))
    return notes
