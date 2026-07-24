# Improvement backlog — 2026-07-24

**Quality 0.76** · avg coach 6.12/10 · contract pass 62% · load 14.0/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/veteran_podium_chaser)
> Experience level contradiction: the guide states '15 years of cycling experience at Intermediate level.' A 15-year rider targeting a podium is unambiguously advanced/experienced, not intermediate. This label will insult and confuse the athlete and undermines trust in the entire plan.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> Weight mismatch: the guide displays '193 lbs / 87.5 kg' in the profile but then uses '88 kg' as the basis for post-ride nutrition calculations one section later. These should be the same number; 87.5 kg ≠ 88 kg is a minor rounding issue, but the profile showing 193 lbs = 87.5 kg while the nutrition section says 88 kg looks like a data error to the athlete.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents. This athlete is a veteran podium chaser with 8 years of experience targeting a UCI Gran Fondo podium — a Cat 5 development pathway is completely wrong for this persona, embarrassing, and suggests content was pulled from a beginner template.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> The automated preview check flags 'Weekly Volume: FAIL'. The guide never explains or resolves this — if prescribed weekly hours don't actually hit the 15 h target, every TSS, load, and adaptation claim in the guide is built on a broken foundation and cannot be sent to a paying athlete.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Long-ride duration stated as 'peak of 1.5 hours' — for a 94-mile gravel event with an estimated finish time of ~9 hours (per the fueling data: duration_h=9.1), a 1.5-hour peak long ride is grossly inadequate and will leave the athlete catastrophically underprepared. The guide itself contradicts this by correctly advising '3-4 hour rides' in the callout box, creating an internal contradiction. The calendar number (1.5 h) is the one athletes will act on and it must be corrected.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Zone Distribution check flagged FAIL in the preview but the guide text never addresses or resolves it. Sending a plan with a known zone distribution failure — where the prescribed zone breakdown is wrong — means the athlete could be training in the wrong zones for weeks. This needs to be corrected before delivery.

### 7. [critical] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED in the automated preview but the plan text is sent unchanged — no coach note, no explanation, and no correction. This is the single gate that failed and it passes silently to the customer. Whatever the underlying distribution error is (likely too much Zone 3 / gray-zone volume in the calendar), it must be diagnosed and fixed before sending.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the plan includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is riding an MTB event (L'Etape Poland is run on roads but is marketed as a gran fondo/cyclosportive, not a road race with categories). Neither road-race tactics nor a cat-upgrade pathway belongs in a plan sold to a 54-year-old weekend warrior riding to 'finish strong.' These sections will read as copy-paste filler and destroy credibility.

### 9. [critical] ×1  (mtb/weekend_warrior)
> 'Road Skills' section appears in the table of contents. For an MTB-flagged discipline this should be MTB-specific trail/technical skills content, or omitted entirely. Sending road-cornering or peloton-positioning content to an MTB rider targeting a gran fondo is a clear content error.

### 10. [critical] ×1  (gravel/veteran_podium_chaser)
> Recovery protocol states '21g protein + 54-64g carbs within 30 minutes (based on your 54kg body weight)' — but the athlete's profile lists weight as 118 lbs / 53.5 kg, which rounds to 54 kg, so the weight reference is correct. HOWEVER, the carb recommendation of 54-64 g is inconsistent with the fueling section's 62 g/hour figure for a ~4.1 h event; more importantly, the post-ride carb window figure appears to be derived from the athlete's body weight (roughly 1 g/kg = 54 g) rather than the workout duration/intensity, which is a legitimate methodology but the plan never explains the basis — this is confusing and potentially under-fuels recovery after long rides. Flag for review.

### 11. [critical] ×1  (gravel/veteran_podium_chaser)
> The plan describes the athlete as '11 Years Riding' at 'Intermediate level' in the methodology rationale, but the persona is 'veteran_podium_chaser / Experienced racer chasing a podium.' Labeling an 11-year veteran as 'Intermediate level' is contradictory and could undermine athlete confidence and plan credibility. The experience label must be reconciled — either the years are wrong or the level descriptor needs to be updated to 'Advanced/Experienced.'

### 12. [major] ×2  (gravel/veteran_podium_chaser, road/veteran_podium_chaser)
> Long ride duration range cited in the Weekly Structure section is '2.3-3.8 hours,' but the race is estimated at 3.3 hours. A peak long ride ceiling of only 3.8 h is acceptable but borderline thin for a podium goal; the guide should at minimum confirm the upper end of long rides reaches or exceeds race duration, which the 'Long Ride vs Race Duration: PASS' check implies is fine — the text should reflect that more confidently rather than leaving the range ambiguous.

### 13. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' appears as a section in the Table of Contents. This is a USA Cycling road-racing category upgrade pathway — it is irrelevant and inappropriate for a gran fondo athlete whose goal is a podium finish, not a license upgrade. It reads as boilerplate left in from a different plan template and will confuse the athlete.

### 14. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume flagged WARN in preview checks but no acknowledgment or explanation appears in the guide. For a 14 h/week athlete this should either be resolved or explicitly noted (e.g., if peak weeks approach 16 h, a coach comment is warranted). Sending a guide with a known volume warning and no explanation is a quality gap.

### 15. [major] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency flagged WARN in preview checks. The guide states 'The test result sets ALL your training zones for the next 6 weeks' but does not explain what happens when a 9-week plan may only include one test. The WARN should prompt either a second test being called out in the text or an explanation of why one test suffices — neither is present.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> Off days are listed as 'Saturday, Friday' — this ordering is reversed chronologically and unusual. More importantly, listing Saturday as an off day while Sunday is the long-ride day means the athlete has no recovery day after the longest session of the week. For a 40-year-old at 9h/week this is a meaningful recovery concern and could reflect a generation error where the off-day and long-ride day assignments conflict.

### 17. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity is flagged as WARN by the preview checks. For a podium-chasing 43-year-old, taper execution is especially critical; the guide should either reflect corrected taper intensity prescriptions or the underlying calendar issue must be fixed before sending.

### 18. [major] ×1  (road/veteran_podium_chaser)
> The guide labels this athlete as 'Intermediate level' in the methodology rationale ('8 years of cycling experience at Intermediate level'), yet the persona is explicitly 'Experienced racer chasing a podium.' Calling a veteran podium chaser 'Intermediate' is inaccurate and undermines credibility with a sophisticated customer.

### 19. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression is flagged WARN and is not acknowledged anywhere in the guide. At minimum, a coach note should flag the irregular ramp and explain why it is intentional (or fix the underlying schedule).

### 20. [major] ×1  (gravel/time_crunched_parent)
> The guide states the long ride day is Sunday and off days are Monday and Saturday, giving a 5-day training week — but with only 5 hours/week target, a 5-day schedule averages just 1 hour per session including the long ride. Combined with the 1.5-hour long ride cap this makes the weekly volume breakdown implausible and should be reconciled explicitly.

### 21. [major] ×1  (gravel/masters_returner)
> Plan length vs race countdown mismatch creates a confusing customer experience. The plan is 11 weeks but the race is 12 weeks away (start date 2026-08-03, race 2026-10-16 = 74 days / ~10.5 weeks from start, yet the JSON states weeks_until_race = 12). The plan_note explains the logic, but the guide itself never tells the athlete when to START or that they should wait one week before beginning. A paying customer will open this and not know what to do with Week 1.

### 22. [major] ×1  (gravel/masters_returner)
> Race-date countdown '84 days from today' is a hard-coded string, not derived from the athlete's plan start date or the actual send date. It will be wrong the moment this email is sent on any day other than the day it was generated, and it directly contradicts the plan_start_date of 2026-08-03 (which is ~74 days before race day). An embarrassing factual error on the very first page.

### 23. [major] ×1  (mtb/weekend_warrior)
> Race-day countdown says '67 days from today' — the plan start date is 2026-08-03 and race date is 2026-09-29, which is 57 days from plan start. The '67 days' figure implies the document was generated or last computed on approximately 2026-07-24, yet the plan start is Aug 3. This inconsistency will confuse the athlete and erode trust in the date-verification claim.

### 24. [major] ×1  (mtb/weekend_warrior)
> Off days listed as 'Wednesday, Saturday, Friday' — listing three non-consecutive off days for a 5 h/week athlete who has only 4 training days is internally inconsistent (4 training days + 3 off days = 7, which works mathematically, but calling out Saturday as an off day while the long ride is on Sunday is fine only if Saturday is explicitly not the long-ride day; the ordering 'Wednesday, Saturday, Friday' is also non-chronological and reads sloppily).

### 25. [major] ×1  (mtb/weekend_warrior)
> FTP test note states 'The test result sets ALL your training zones for the next 6 weeks.' With a 9-week plan and a single retest cadence flagged as WARN in the preview checks, telling the athlete zones are locked for 6 weeks is potentially misleading and inconsistent with the plan's own test scheduling.
