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
            "https://gravelgodcycling.com/coaching/ ($199 every 4 weeks). "
            "If the plan alone is enough, that's a fine answer too.\n\n"
            "Questions — about coaching or about week 2 — reply to this "
            "email.\n\n"
            + SIGNATURE
        ),
    },
]
