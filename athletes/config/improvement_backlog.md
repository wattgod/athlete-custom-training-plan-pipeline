# Improvement backlog — 2026-06-19

**Quality 1.27** · avg coach 6.0/10 · contract pass 0% · load 9.33/plan · 2 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> HIIT-Focused methodology prescribes 30% easy / 20% tempo / 50% hard — but the preview check flags Zone Distribution as FAIL. This is the single most important structural feature of the plan and it is confirmed broken. A 50% hard distribution is also medically aggressive for a 61-year-old masters returner on 6 h/week; sending this before the distribution is fixed risks overtraining injury and coaching liability.

### 2. [critical] ×1  (gravel/masters_returner)
> Off days listed as Saturday, Wednesday, AND Friday — that is 3 rest days in a 7-day week, leaving only 4 training days. Yet the guide simultaneously states 'Your week has 4 training days, 3 of which are key sessions.' Three key sessions in 4 days on 6 h/week is extremely tight, and listing Saturday as an off-day conflicts with the race being on a Saturday (race day, 2026-08-29, is a Saturday). The taper/race week logic will be broken.

### 3. [major] ×1  (gravel/masters_returner)
> Fueling section references 'being on the bike for 6+ hours' as an indoor/outdoor balance example, yet the athlete's projected race duration is 4.4 hours (per fueling data) and the race is only 52.2 miles. '6+ hours' is factually wrong for this athlete and event and will cause confusion about pacing and nutrition targets.

### 4. [major] ×1  (gravel/masters_returner)
> The plan_weeks value is 9 but the guide text references 'the test result sets ALL your training zones for the next 6 weeks' — an unedited boilerplate figure that contradicts this athlete's 9-week plan and could cause the athlete to skip or mistrust a retest scheduled mid-plan.

### 5. [major] ×1  (gravel/masters_returner)
> Long Ride duration range stated as '1.9–3.2 hours' in the Weekly Structure section. For a 4.4-hour target race, a peak long ride of only 3.2 hours is borderline low (≈73% of race duration), and more importantly this figure must be verified against the actual calendar — if it is auto-generated boilerplate it may not match the real workouts, which would contradict the stated PASS on Long Ride vs Race Duration.

### 6. [minor] ×1  (gravel/masters_returner)
> The athlete's weight (122 lbs / 55.3 kg) and height (5'4") appear in the profile section but were not listed in the input JSON — if these are defaults or averages rather than values the athlete actually provided, presenting them as 'calibrated to your specific situation' is misleading and erodes trust.

### 7. [minor] ×1  (gravel/masters_returner)
> FTP Test Frequency preview check is WARN, yet the guide text does not acknowledge or explain this to the athlete. A 61-year-old returner deserves transparency about test scheduling, especially given the guide's own warning that an inaccurate test means weeks of wrong-zone training.

### 8. [minor] ×1  (gravel/masters_returner)
> 'Road Skills' appears as a chapter in the table of contents — this is a gravel event. The section title should be 'Gravel Skills' or 'Trail / Off-Road Skills' to match the discipline and avoid looking like a copy-paste from a road plan.
