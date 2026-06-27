# Improvement backlog — 2026-06-27

**Quality 2.55** · avg coach 6.5/10 · contract pass 75% · load 11.12/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/weekend_warrior)
> Long-ride ceiling stated as 1.5 hours. The guide explicitly says 'your peak duration of 1.5 hours' as the long-ride cap. For a 70-mile gravel race estimated at ~5.8 hours, a peak long ride of 1.5 h is woefully inadequate and will leave the athlete unprepared for race-day fatigue. Even a time-crunched plan for a 5 h race should target long rides of 2.5–3.5 h. This single number undermines race-day confidence and is factually wrong relative to the event demands.

### 2. [critical] ×1  (gravel/weekend_warrior)
> The 'Biggest Opportunity' callout then contradicts itself: it says 'a single 3–4 hour ride is worth more than two 1.5 hour rides,' implying 3–4 h is achievable, yet the plan's own long-ride guidance caps rides at 1.5 h. The plan cannot simultaneously cap long rides at 1.5 h and recommend 3–4 h rides — this is an internal contradiction that will confuse the athlete and destroy trust.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the JSON flags discipline as 'mtb' but the Granfondo Tre Valli Varesine is a road gran fondo (verified race DB confirms this). The plan's 'Road Skills' section header appears in the table of contents, which is the correct call for this event — but the persona and discipline tag of 'mtb' means any MTB-specific content elsewhere in the untruncated plan (trail skills, MTB cornering drills, tubeless setup advice, etc.) would be entirely wrong for a road event. This contradiction must be resolved before sending.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution preview check is flagged FAIL. The guide describes a Traditional (Pyramidal) distribution with ~75% Zone 1-2, yet the automated gate found the actual weekly zone breakdown in the calendar does not match this. Sending a guide that promises pyramidal distribution when the calendar delivers something different is a direct misrepresentation to the athlete.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check FAILED per the automated preview. The guide text never resolves this — if weekly volume targets stated in the calendar contradict the athlete's 15 h/week target, sending this plan means the athlete receives wrong volume prescriptions. This must be audited and corrected before delivery.

### 6. [critical] ×1  (road/weekend_warrior)
> Gravel Skills chapter included in a road-discipline plan. The table of contents explicitly lists 'Gravel Skills' — this is the wrong discipline content entirely. Eroica Dolomiti is a road/gran fondo event; gravel cornering and handling drills are irrelevant and will confuse or mislead the athlete.

### 7. [critical] ×1  (road/time_crunched_parent)
> Zone 2 power range is missing its lower watt value in the zone chart — it shows '94-127W' but the lower bound of Zone 1 is listed as '0-93W', so Zone 2 starts at 94W, which is correct, but the percentage column reads '56-75% FTP' implying 95W–128W. More critically, Zone 1 shows '0-93W' with NO percentage of FTP listed at all, breaking the chart's internal consistency and making it impossible for the athlete to calibrate if they only have a power meter. A coach would not send a zone chart with a missing column entry.

### 8. [major] ×1  (gravel/weekend_warrior)
> Off days listed as Sunday AND Wednesday. The race is on Sunday, August 30. Designating Sunday as a permanent off day conflicts with race day — the athlete will wonder whether they are supposed to rest on race day or if the schedule is wrong. The weekly structure note should exclude race day from the 'Sunday off' rule or flag the exception explicitly.

### 9. [major] ×1  (gravel/weekend_warrior)
> Weight (154 lbs / 69.8 kg) and height (5'10") appear in the profile, but these fields are not present anywhere in the athlete JSON provided. The plan appears to have fabricated or hallucinated demographic data not supplied by the athlete, which is a data-integrity violation and could be factually wrong.

### 10. [major] ×1  (mtb/ambitious_first_timer)
> The fueling section (truncated) cites 70g carbs/hour over an estimated 4.9-hour duration — totalling ~343g carbs for the race. The guide must clearly surface this in the Race Day and Nutrition sections and include a practice-fueling instruction tied to long rides; the truncated text does not confirm this is done, and for a first-timer this is the single highest-risk race-day failure point.

### 11. [major] ×1  (mtb/ambitious_first_timer)
> Off days listed as 'Saturday, Friday' in the weekly-at-a-glance block, with long rides on Sunday. Having both days flanking the weekend off (Friday + Saturday off, long ride Sunday) is an unusual structure that needs explicit justification — or it may be a template error where days were populated incorrectly (e.g. Friday should be an easy/active-recovery day, not fully off).

### 12. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level contradiction: the profile block states '14 Years Riding' but the methodology rationale immediately below labels the athlete 'Intermediate level.' 14 years of riding experience — especially for someone chasing a podium at an A-race — should read 'Advanced' or 'Experienced.' Sending this to a veteran podium chaser who reads that she is 'Intermediate' is embarrassing and undermines trust in the plan.

### 13. [major] ×1  (gravel/veteran_podium_chaser)
> Race date listed as 'Monday, September 07, 2026' but September 7, 2026 is a Sunday. Calling it a Monday is factually wrong. Gravel races almost always run on Sundays; this will alarm the athlete and erode confidence in the plan's accuracy. The date itself (2026-09-07) is correct — only the day-of-week label is wrong and must be corrected.

### 14. [major] ×1  (road/veteran_podium_chaser)
> Persona mislabel: the JSON persona is 'veteran_podium_chaser' (experienced racer), but the guide text describes the athlete as 'Intermediate level' ('9 years of cycling experience at Intermediate level'). A 9-year veteran gunning for a podium should not be labeled Intermediate — this will undermine athlete confidence and may produce under-loaded workouts.

### 15. [major] ×1  (road/veteran_podium_chaser)
> Long ride duration range cited as '3.7–6.2 hours' in the Weekly Structure section. For an 83-mile gran fondo with an implied finish time of roughly 4–5 hours for a podium contender, a 6.2-hour long ride cap is disproportionately high and inconsistent with a 15-week plan that should peak around race duration, not 60–90 minutes beyond it. This number needs verification against the actual calendar.

### 16. [major] ×1  (gravel/masters_returner)
> Zone 2 LTHR range is missing from the zone chart — the '56-75% FTP' power range is listed but the corresponding LTHR percentage column is blank for Zone 2, unlike every other zone. Athletes using HR as their primary metric will have no anchor for their most-used zone.

### 17. [major] ×1  (gravel/masters_returner)
> Zone GS (G Spot) LTHR range of '92-96% LTHR' overlaps Zone 3's upper bound of '94% LTHR' and sits below Zone 4's lower bound of '95% LTHR' — the LTHR column is internally inconsistent, making heart-rate-based execution of the plan's signature zone ambiguous.

### 18. [major] ×1  (road/weekend_warrior)
> Zone 2 is missing its lower power bound in the zone chart. The table shows '95-129W' for Zone 2 but omits the lower percentage label — more critically, Zone 1 shows '0-94W' with NO %FTP column filled in (the column is blank), which looks like a rendering gap and could confuse athletes trying to cross-reference their head unit. Every other zone has %FTP populated; Zone 1 does not.

### 19. [major] ×1  (road/weekend_warrior)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan, and based on the FTP Test Frequency check passing, there appears to be only one test. Telling the athlete their zones are locked for '6 weeks' in an 8-week plan is factually wrong and could cause confusion about when (or whether) to retest.

### 20. [minor] ×2  (road/time_crunched_parent, road/weekend_warrior)
> TSS Progression flagged WARN in the preview checks; the guide contains no acknowledgment or coaching note explaining to the athlete why week-to-week TSS may not rise linearly (e.g., a recovery week mid-plan). A brief callout would prevent athlete concern when they notice an easier week.

### 21. [major] ×1  (road/weekend_warrior)
> Countdown arithmetic is wrong and visible to the athlete. The guide states '70 days from today' with a plan start of 2026-07-06 and race date of 2026-09-05. That span is 61 days, not 70. If 'today' is meant to be the generation date rather than plan start, the hardcoded '70 days' will be stale and incorrect the moment the email is opened. A dynamic or omitted countdown is safer; a wrong one damages credibility.

### 22. [major] ×1  (road/weekend_warrior)
> Long ride ceiling is described as '1.5–2.5 hours' yet the race is projected at ~5.7 hours. Even with the 'Biggest Opportunity' caveat, the written ceiling of 2.5 hours for long rides is only ~44% of race duration — well below the threshold where an athlete can reasonably expect to 'finish strong.' The guide should prescribe at least one 3–4 hour ride explicitly, not just mention it as optional in a sidebar, especially for an A-priority event.

### 23. [major] ×1  (road/time_crunched_parent)
> Off days are listed as Friday, Tuesday, AND Saturday — that is three off days — but the plan states 4 training days per week. 7 days minus 3 off days = 4 training days, which is mathematically consistent, BUT listing Saturday as an off day when the long ride day is stated as Sunday means the athlete has back-to-back rest (Sat+any adjacent rest) without that being explained. More importantly for a 7h/week athlete with a 2.5–4.2h long ride on Sunday, having Saturday completely off is actually fine — but the guide never explains this intentional rest-before-long-ride design, which will confuse the athlete and may cause them to question the schedule.

### 24. [major] ×1  (road/time_crunched_parent)
> The race goal is 'podium' — a highly competitive objective — but the guide's 'Goals & Blindspots' section is truncated to just the word 'Compete,' suggesting the goal text was not correctly populated. Sending a plan to a podium-chasing athlete whose goal is rendered as the generic word 'Compete' is embarrassing and undermines trust in the personalization.

### 25. [minor] ×1  (gravel/weekend_warrior)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks,' but the plan is only 8 weeks long and tests are unlikely to be spaced exactly 6 weeks apart in an 8-week plan. This boilerplate figure is contextually misleading for this specific plan length.
