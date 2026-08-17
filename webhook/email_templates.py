"""Customer-facing follow-up email copy for training plan orders.

This module is the single source of truth for the day-1/3/7 post-purchase
sequence. It has zero dependencies so it can be imported by app.py and by
tests without pulling in Flask.

WIRING (one-line app.py change, owned by the app.py executor):
    Replace the inline FOLLOWUP_SEQUENCE constant in webhook/app.py
    (the list defined under "POST-PURCHASE FOLLOW-UP EMAIL SEQUENCE")
    with:

        from email_templates import FOLLOWUP_SEQUENCE

    Nothing else changes — the shape (day / subject / template with a
    {first_name} placeholder) matches what process_followup_emails()
    already consumes.

Copy rules (enforced by webhook/tests/test_email_templates.py):
- Coach-to-athlete voice. Direct, specific, numbers where possible.
- No hype, no exclamation-point subjects, no emoji, no AI-slop phrases.
- One clear next action per email.
- Facts must match the actual delivery: workouts are pre-loaded on the
  athlete's TrainingPeaks calendar (coach attach), the training guide is
  attached to the delivery email. There is NO .zwo import step for the
  customer — the old day-1 copy got this wrong.
- Day 3 carries no generic marketing links (the template only knows
  {first_name}, so per-event race-page links are not possible here).
- Day 7 carries exactly one link: the coaching page.
"""

SIGNATURE = (
    "— Matti\n"
    "Gravel God Coaching\n"
    "gravelgodcycling.com"
)

FOLLOWUP_SEQUENCE = [
    {
        'day': 1,
        'subject': 'Your plan: the one thing to do first',
        'template': (
            "Hey {first_name},\n\n"
            "Your plan went out yesterday: the training guide (attached to "
            "that email) plus every workout loaded on your TrainingPeaks "
            "calendar, day by day through race week.\n\n"
            "One thing to do first: open the guide and read the phase "
            "overview. Five minutes. It explains why the weeks are built "
            "the way they are, so nothing later comes as a surprise.\n\n"
            "Then do today's workout as written. Week 1 runs easier than "
            "you'd expect. That's calibration, not a mistake.\n\n"
            "If anything looks wrong — workouts missing from your "
            "calendar, zones that feel off — reply to this email and "
            "I'll fix it.\n\n"
            + SIGNATURE
        ),
    },
    {
        'day': 3,
        'subject': 'Three days in — two things to check',
        'template': (
            "Hey {first_name},\n\n"
            "Three days in. Two things worth checking:\n\n"
            "1. Open TrainingPeaks and confirm the full plan is on your "
            "calendar through race week. If anything is missing, reply and "
            "I'll fix it today.\n"
            "2. How did the first quality session feel? If your FTP was "
            "estimated, the zones can run hot or cold — week 1 has a "
            "test built in to correct that. Ride the test honestly and the "
            "rest of the plan calibrates itself.\n\n"
            "One rule that saves more plans than any workout: if you miss "
            "a day, skip it. Don't stack it onto tomorrow. The plan absorbs "
            "a missed session. It doesn't absorb doubled ones.\n\n"
            "If something about your week isn't working — schedule, "
            "zones, a session that made no sense — reply with the "
            "specifics. I read these.\n\n"
            + SIGNATURE
        ),
    },
    {
        'day': 7,
        'subject': "Week 1 done — what changes in week 2",
        'template': (
            "Hey {first_name},\n\n"
            "Week 1 was calibration. Week 2 is where the load starts: "
            "intervals get longer, the weekend ride grows, and the plan "
            "begins stacking stress on purpose. Feeling more tired than "
            "last week means it's working.\n\n"
            "Two numbers that matter more than any single workout:\n"
            "1. Sessions completed per week. Five okay days beat one "
            "heroic one.\n"
            "2. Hours of sleep. The plan assumes you're recovering "
            "between sessions.\n\n"
            "One more thing. The plan you have is static — it can't "
            "see a bad night's sleep, a work trip, or a breakthrough ride. "
            "Coaching can. Weekly adjustments to what actually happened, "
            "plus direct access to me for race strategy and the questions "
            "between workouts. Details: "
            "https://gravelgodcycling.com/coaching/ (from $199 every 4 weeks). "
            "If the plan alone is enough, that's a fine answer too.\n\n"
            "Questions — about coaching or about week 2 — reply to this "
            "email.\n\n"
            + SIGNATURE
        ),
    },
]


# =============================================================================
# CONSULT-ENGINE copy (docs/CONSULT_ENGINE_SPEC.md)
#
# Athlete-facing copy for the post-pay consult flow: the welcome email sent
# right after checkout, plus the state-conditional nudges fired by
# process_consult_followups() (webhook/app.py). Coach-facing copy (order
# notifications, needs_attention alerts, the plan-of-action reminder) stays
# inline in app.py, matching the existing coaching/consulting notification
# pattern — it's operational, not brand voice.
#
# Same copy rules as FOLLOWUP_SEQUENCE above: plain language, no jargon, no
# hype, one clear next action. Never invent a number the athlete didn't
# give — "don't know" stays "don't know."
# =============================================================================

TP_INVITE_LINK = "https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU"

CONSULT_ADDON_TERMS = (
    "You also bought the custom plan add-on: a 12-week plan built from "
    "this consult plus your data, delivered on TrainingPeaks within 7 "
    "days of the call, with one adjustment round in the 14 days after.\n\n"
)

CONSULT_WELCOME_SUBJECT = "Your consult is booked — here's what happens next"

CONSULT_WELCOME_TEMPLATE = (
    "Hey {first_name},\n\n"
    "Your consult is booked. Here's exactly what to do next.\n\n"
    "1. Book your time: {booking_link}\n"
    "Pick whatever slot works for you.\n\n"
    "2. Fill in the intake form, about 10 minutes: {intake_link}\n"
    "The more specific you are, the more useful the call is. If you "
    "don't know a number — FTP, LTHR, whatever — say so. \"Don't know\" "
    "is a fine answer.\n\n"
    "3. Connect TrainingPeaks: {tp_invite_link}\n"
    "That link attaches your account to mine as coach. Nothing to "
    "confirm on your end — once you click it, I can pull your training "
    "history into the read before we talk.\n"
    "Don't use TrainingPeaks? Reply to this email and tell me what you "
    "do use instead. I'll work with what you've got.\n\n"
    "{addon_clause}"
    "Questions before the call? Reply here.\n\n"
    + SIGNATURE
)

CONSULT_INTAKE_NUDGE_SUBJECT = "Quick thing before your consult"

CONSULT_INTAKE_NUDGE_TEMPLATE = (
    "Hey {first_name},\n\n"
    "Haven't seen your intake form yet. It's the difference between the "
    "call being a get-to-know-you chat and it being useful.\n\n"
    "About 10 minutes: {intake_link}\n\n"
    "If a question stumps you, answer \"don't know\" and move on. That's "
    "useful information too.\n\n"
    + SIGNATURE
)

CONSULT_TP_NUDGE_SUBJECT = "One more thing before we talk"

CONSULT_TP_NUDGE_TEMPLATE = (
    "Hey {first_name},\n\n"
    "Haven't seen a TrainingPeaks connection yet. If you use TP, this "
    "link attaches your account to mine as coach — nothing to confirm "
    "on your end: {tp_invite_link}\n\n"
    "Don't use TrainingPeaks? No problem. Reply and tell me what you do "
    "use instead — Strava, a bike computer export, or just your memory. "
    "I'll work with what you've got.\n\n"
    + SIGNATURE
)

CONSULT_ADDON_OFFER_SUBJECT = "Add a plan to your consult — 7 days only"

CONSULT_ADDON_OFFER_TEMPLATE = (
    "Hey {first_name},\n\n"
    "Now that we've talked, here's the offer: a custom 12-week plan "
    "built from everything we covered on the call plus your data — $100, "
    "delivered on TrainingPeaks within 7 days, with one adjustment round "
    "in the two weeks after.\n\n"
    "Reply to this email and I'll send the checkout link. This offer is "
    "open for 7 days after the call.\n\n"
    "If the consult alone gave you what you needed, that's a fine answer "
    "too.\n\n"
    + SIGNATURE
)


CONSULT_RUNNER_ALARM_SUBJECT = "[GG] Consult runner needs attention"

CONSULT_RUNNER_ALARM_TEMPLATE = (
    "The consult runner (~/gg-consult-runner) hasn't checked in.\n\n"
    "{detail}\n"
    "Heartbeat age: {age}\n\n"
    "Likely causes: the TrainingPeaks Chrome session expired (re-login + "
    "MFA on the Mac), the launchd job stopped, or the network dropped. "
    "Check the Mac before consult analyses back up.\n"
)


def build_consult_runner_alarm_email(detail: str, age: str) -> tuple:
    """Subject + plain-text body for the coach alarm fired when the consult
    runner heartbeat (POST /api/consult/runner/heartbeat) goes stale or
    reports ok=false. See process_consult_followups() in app.py."""
    body = CONSULT_RUNNER_ALARM_TEMPLATE.format(
        detail=detail or 'No detail supplied.',
        age=age,
    )
    return CONSULT_RUNNER_ALARM_SUBJECT, body


def build_consult_welcome_email(
    first_name: str,
    booking_link: str,
    intake_link: str,
    plan_addon_bought: bool = False,
    tp_invite_link: str = TP_INVITE_LINK,
) -> tuple:
    """Subject + plain-text body for the post-checkout consult welcome."""
    body = CONSULT_WELCOME_TEMPLATE.format(
        first_name=first_name or 'there',
        booking_link=booking_link or '(booking link not yet configured — reply and I will send it)',
        intake_link=intake_link or '(intake link not yet available — reply and I will send it)',
        tp_invite_link=tp_invite_link,
        addon_clause=CONSULT_ADDON_TERMS if plan_addon_bought else '',
    )
    return CONSULT_WELCOME_SUBJECT, body
