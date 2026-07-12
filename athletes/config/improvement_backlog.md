# Improvement backlog — 2026-07-12

**Quality 5.11** · avg coach 7.25/10 · contract pass 88% · load 7.25/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/time_crunched_parent)
> Peak long ride is stated as 1.5 hours for an 83-mile gravel race that will take most athletes 4-6 hours. Even with a Time-Crunched methodology and a 5 h/week budget, calling out 1.5 hours as the 'peak duration' without any stronger mitigation is professionally indefensible — a rider with a 1.5-hour long ride peak will suffer badly on race day. The 'YOUR BIGGEST OPPORTUNITY' callout partially addresses this but the stated number needs to be higher (the plan itself should target at least one 2.5-3 hour ride) or the methodology mismatch with this race distance must be more explicitly flagged as a hard limitation.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Zone Distribution preview check is FAIL. The guide claims ~65% of riding stays 'genuinely easy' to match the G Spot methodology, but the automated zone-distribution check failed. This means the actual weekly calendar workouts do not deliver the stated distribution — the guide's core training promise is contradicted by the calendar content. This cannot be sent until the calendar zones are corrected and the check passes.

### 3. [critical] ×1  (gravel/time_crunched_parent)
> The off-day list reads 'Friday, Thursday, Sunday' — three off days — but the athlete has only 5 h/week with 4 training days stated in the same section. Listing Sunday as an off day while also (implicitly) having it as a potential training day creates a direct contradiction visible to the athlete in one paragraph. At minimum, Sunday appears twice in different roles, and three off days in a 7-day week leaves only 4 riding days, which is inconsistent with how the week-at-a-glance is described.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Plan start date is given as 2026-07-20, but the race is 2026-11-08 — that is 111 days (≈15.9 weeks) away from July 20, not 16 weeks. The JSON notes that weeks_until_race (17) vs. plan_weeks (16) means the athlete starts one week late, which is fine — but the guide never communicates this 'you start one week from now' nuance. An athlete reading '119 days from today' in the race countdown alongside a July 20 start will be confused about when to actually begin.

### 5. [critical] ×1  (road/time_crunched_parent)
> Long ride peak duration is stated as 1.5 hours in the Weekly Structure section ('peak duration of 1.5 hours'). For a 78.3-mile gran fondo with an estimated race duration of ~3.6 hours, this is less than half the race distance in time. Even for a time-crunched athlete this number will alarm the athlete and undermine trust — it directly contradicts the 'Biggest Opportunity' paragraph that correctly urges 3-4 hour rides. The plan text must not anchor the athlete to 1.5 hours as the peak long-ride target.

### 6. [major] ×2  (gravel/time_crunched_parent)
> Zone 1 (Active Recovery) is missing its % FTP bounds in the zone chart — the power column shows '0-151W' but the % FTP column is blank. Every other zone has explicit % FTP values. This is an inconsistency that will confuse athletes and looks like a generation error.

### 7. [major] ×1  (gravel/time_crunched_parent)
> Off days are Friday AND Saturday, meaning the athlete has no full weekend day available for the long ride — Sunday is the designated long-ride day. For a time-crunched parent, losing Saturday entirely as a rest day wastes the most practical day for a longer outdoor ride. This is likely a configuration error in the scheduler; most athletes in this persona would prefer Saturday as the long-ride day and a mid-week off day instead.

### 8. [minor] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> Long ride duration range cited in the Weekly Structure section is '3.9-6.5 hours.' At 10h/week with off days, a 6.5-hour long ride would consume 65% of the weekly budget in one session, which seems aggressive even for a peak week. This number should be verified against the actual calendar to confirm it is not an overshoot that contradicts the per-day duration caps (which the automated gate marked PASS).

### 9. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level mislabeled: the guide states '16 years of cycling experience at Intermediate level' — 16 years of riding is clearly veteran/experienced, not Intermediate. For a persona explicitly labeled 'Experienced racer chasing a podium,' calling him Intermediate is factually wrong and will erode athlete trust immediately.

### 10. [major] ×1  (road/veteran_podium_chaser)
> Athlete weight (122 lbs / 55.3 kg) is displayed prominently in the profile but is NOT present anywhere in the input JSON — it appears to have been fabricated or pulled from a default. If the athlete did not supply this figure, showing a made-up weight in her personal plan is embarrassing and potentially trust-destroying. Must be verified against the actual questionnaire data or removed.

### 11. [major] ×1  (gravel/time_crunched_parent)
> The 'countdown' field states '119 days from today' but today's date is not defined in the guide, making this number unverifiable and potentially stale if the PDF is generated and read on different dates. A static countdown in a printed guide is an error waiting to happen — it should read 'Race Date: November 8, 2026' only, without a computed days-remaining figure.

### 12. [major] ×1  (road/time_crunched_parent)
> Fueling strategy references 90 g/hour carbs for a 3.6-hour duration event, but the guide text (truncated) does not appear to contextualize this against the athlete's actual estimated finish time or gut-training ramp-up. 90 g/hr requires multi-transporter carb sources and gut training — this needs an explicit callout in the nutrition section that this target requires practice and is not a day-one number, otherwise it is a liability for a masters athlete.

### 13. [minor] ×1  (gravel/time_crunched_parent)
> TSS Progression preview check returned WARN but no explanation or caveat appears anywhere in the visible guide text. For a paying athlete, a flagged TSS ramp issue should surface as at least a brief coach's note (e.g., 'Week X has a larger TSS jump than ideal — here's how to handle it'), otherwise the WARN is silently swallowed.

### 14. [minor] ×1  (gravel/time_crunched_parent)
> The goal field is 'podium' for a large mass-participation gran fondo — this is an ambitious goal that deserves at least a sentence of honest expectation-setting in the guide (e.g., top-category podium vs. age-group podium vs. overall). Leaving it unaddressed could set the athlete up for disappointment and reflects a missed coaching moment.

### 15. [minor] ×1  (gravel/veteran_podium_chaser)
> The guide includes a 'Road Skills' section in the table of contents. This athlete is a gravel racer — road skills content is discipline-adjacent but a dedicated road-skills section risks including road-specific drills (e.g., criterium cornering, road pack positioning) that are irrelevant or misleading for a gravel event. The truncated text prevents full verification, but the section heading itself is a flag.

### 16. [minor] ×1  (gravel/veteran_podium_chaser)
> The athlete has 13 years of riding experience yet the methodology rationale labels her 'Intermediate level.' A 13-year veteran chasing a podium should be described as 'Advanced' or 'Experienced racer.' The persona label itself ('veteran_podium_chaser') contradicts the Intermediate tag — this inconsistency would erode athlete trust.

### 17. [minor] ×1  (gravel/veteran_podium_chaser)
> Long Ride duration range given as '2.8-4.7 hours' in the Weekly Structure section. For a 55-mile gravel race estimated at ~3.4h, a ceiling of 4.7h (138% of race duration) is on the high side and may alarm the athlete or encourage over-reaching on long ride days. Should be tightened to align with race duration guidance (typically 100-120% of race duration as the peak long ride).

### 18. [minor] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency flagged WARN in preview checks but the guide text does not acknowledge or contextualise this for the athlete (e.g. 'you will retest at week X and week Y'). The athlete sees no explanation of how often she retests over 17 weeks, which is a meaningful gap for a podium-chaser who needs accurate zones throughout.

### 19. [minor] ×1  (road/veteran_podium_chaser)
> The 'Success looks like: Compete' line in the Goals & Blindspots section appears to be a truncated or placeholder value — 'Compete' alone is not a meaningful goal statement for an experienced racer whose stated goal is a podium finish. Should read something like 'Podium finish at UCI Gran Fondo Loutraki' or similar.

### 20. [minor] ×1  (road/time_crunched_parent)
> Plan length vs. weeks_until_race: the plan is 17 weeks but the race is 18 weeks away (start date 2026-07-20, race 2026-11-15). The plan_note explains this is intentional — athlete starts one week later. However, the guide never mentions this to the athlete. A time-crunched parent who reads '17-week plan' and counts 18 weeks to race day may panic or start immediately on the wrong week. A single sentence — 'Your plan starts 2026-07-20; that is one week after today's date, giving you a rest week before beginning' — would close this gap.

### 21. [minor] ×1  (road/time_crunched_parent)
> The Zone 1 power range in the zone chart is listed as '0-129W' with no %FTP or %LTHR columns filled in, while every other zone has them. This looks like a rendering gap from the template — not wrong, but slightly unprofessional and inconsistent.

### 22. [minor] ×1  (road/time_crunched_parent)
> The recovery nutrition section is cut off mid-sentence ('150% of fluid los—') in the truncated text. If this truncation reflects the actual document, the rehydration instruction is incomplete and should be verified before sending.

### 23. [minor] ×1  (road/time_crunched_parent)
> The athlete's goal is listed as 'podium' for a UCI Gran Fondo, which is an extremely ambitious target. The guide's 'Performance Expectations' section only says 'Execute consistently, fuel properly, and trust the process' and the Goals section just lists 'Compete.' There is no acknowledgement or management of the podium goal anywhere visible — a real coach would at least reference it to set honest expectations or affirm the plan is designed around it.

### 24. [minor] ×1  (gravel/time_crunched_parent)
> The athlete's weight (124 lbs / 56.2 kg) and height (5'4") appear in the profile section but are never referenced anywhere in the visible guide text — not in fueling calculations, not in power-to-weight context. Including biometric data that goes unused can feel like filler and raises questions about whether it was actually used in plan generation.

### 25. [minor] ×1  (road/time_crunched_parent)
> The 'Years Riding: 5' profile stat is listed but the methodology justification says 'Intermediate level' without ever defining what that means for this athlete — a minor coherence gap that could confuse a reader cross-referencing their questionnaire.
