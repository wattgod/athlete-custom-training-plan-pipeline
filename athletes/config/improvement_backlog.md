# Improvement backlog — 2026-08-16

**Quality -1.31** · avg coach 5.0/10 · contract pass 62% · load 16.38/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (gravel/weekend_warrior, mtb/ambitious_first_timer, road/veteran_podium_chaser)
> Long ride duration range cited as '2.1-3.5 hours' in the Weekly Structure section. For a 7 h/week athlete targeting a ~5.5 h race, a 3.5 h cap on the longest training ride is on the low side and the gap to race duration (5.5 h) should be briefly acknowledged so the athlete isn't surprised by the jump on race day — especially since the Long Ride vs Race Duration check passed, suggesting the calendar may reach closer to race duration than the text implies.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> La Ruta de los Conquistadores is a multi-day mountain bike stage race (3 days, ~162 miles total across jungle, volcano, and coast terrain), NOT a road race. The plan disciplines it as road, includes 'Road Skills' and 'Road Race Strategy' sections, and the entire execution context (road cornering, group dynamics, road race tactics) is wrong for this event. An experienced podium chaser targeting this race would immediately know the plan was generated for the wrong discipline.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the guide. This is USA Cycling road racing categorization and is entirely irrelevant — La Ruta is an off-road/mountain bike stage race with no such category structure. This content should not exist in this plan at all.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> The plan explicitly states '10 years of cycling experience at Intermediate level.' The persona is 'veteran_podium_chaser' / 'Experienced racer chasing a podium' — describing a veteran podium chaser as Intermediate level is a direct contradiction of the persona and will undermine athlete confidence in the plan immediately.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the athlete's discipline is 'mtb' but the race (Flanders Legacy Gravel) is a gravel event. The plan header, persona label ('Ambitious first-timer'), and the included 'Gravel Skills' section confirm the race is gravel, yet the JSON persona is tagged MTB. The plan must be generated for the correct discipline. Sending an MTB plan to a gravel racer (or vice versa) is a fundamental product error.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Fueling math is wrong. The plan states '45 g/hr × race duration = 310 g total race carbs.' At 45 g/hr over 6.9 hours the correct figure is 310.5 g — that rounds correctly, BUT the race-day range card says '38–52 g/hr' and the low end over 6.9 h = ~262 g while the high end = ~359 g; neither bound remotely equals 310 g when stated as a single 'Total Race Carbs' figure without qualification, which will confuse the athlete. More importantly, 45 g/hr is notably low for a 6.9-hour event — current sports-science consensus (and the plan's own 'optimization' framing) puts the trained ceiling at 60–90 g/hr for multi-hour events. Prescribing 45 g/hr as the headline target for a ~7-hour race risks the athlete hitting the wall; this number needs coach review before sending.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: The plan JSON declares discipline='mtb', but the race 'Gravelista' is a verified gravel event in Victoria, Australia, and the guide itself contains a 'Gravel Skills' chapter and gravel-specific equipment notes. The plan header, methodology framing, and skill content all need to be consistently gravel — either the discipline tag is wrong and everything is fine, or the guide is mislabelled and was built on the wrong template. As written, the athlete receives a plan that calls itself MTB while coaching them for a gravel race, which is contradictory and unprofessional.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution automated check is a hard FAIL. The guide never explains or corrects this — it ships with a known failed quality gate. If the pyramidal distribution (≈75% Z1-2) is not being enforced in the actual calendar workouts, the methodology claim is false.

### 9. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete profile is tagged 'mtb' but the entire guide — section headers, equipment list, skills section ('Gravel Skills'), and methodology framing — is written for a gravel racer. The race itself IS a gravel event (Gravel Revival, verified DB), so either the athlete tag is wrong or this person was enrolled in the wrong plan. Either way the guide contradicts itself and will confuse or alarm the athlete.

### 10. [critical] ×1  (mtb/weekend_warrior)
> 'Gravel Skills' section is called out in the table of contents for what is tagged as an MTB athlete. MTB-specific skills (technical descending, switchbacks, rock gardens, rooty singletrack cornering) are absent. If the athlete is truly MTB, this content is wrong; if they are gravel, the athlete tag is wrong. The inconsistency must be resolved before sending.

### 11. [critical] ×1  (road/time_crunched_parent)
> Table of contents and plan body include a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road racing licence pathway concept that is completely irrelevant to a time-crunched parent whose sole goal is to finish a gran fondo. It implies competitive racing ambitions the athlete never expressed and could confuse or mislead her. Must be removed before sending.

### 12. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: The athlete is flagged as 'mtb' discipline but the entire plan — including the race itself ('Wild Gravel'), skills section title ('Gravel Skills'), and likely all skills/technique content — is oriented toward gravel riding. Either the discipline field is wrong or the plan template is wrong. This must be resolved before sending: if the athlete truly rides MTB, gravel-specific cornering/skills drills and race framing are incorrect; if the race is genuinely a gravel event, the discipline tag and any MTB-specific content should be corrected.

### 13. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution check FAILED in automated preview and is unresolved. A pyramidal plan with a failing zone distribution is a foundational methodology contradiction — the plan's central promise (roughly 75% Zone 1-2) is likely not being delivered in the actual calendar workouts. This cannot be sent without diagnosing and fixing the calendar.

### 14. [critical] ×1  (gravel/time_crunched_parent)
> Off days listed as 'Tuesday, Monday' — two days listed but the order (Tuesday before Monday) is almost certainly a rendering/sort bug, and listing Monday as an off day while also implying a mid-week interval day may be internally contradictory. For a 5 h/week athlete with 4 training days this needs to be verified against the actual calendar and corrected before sending — if Monday is truly off, the week structure description must reflect that unambiguously.

### 15. [major] ×1  (gravel/weekend_warrior)
> Zone Distribution check FAILED in pre-send QA, but the guide text never acknowledges this or corrects for it. If zone distribution is wrong in the calendar, the pyramidal promise ('roughly 75% easy') stated in the guide is misleading and could mean the athlete is systematically over-cooking intensity. This needs to be resolved before sending.

### 16. [major] ×1  (gravel/weekend_warrior)
> Off-day schedule states 'Off days: Tuesday, Saturday' — but Saturday is the traditional long-ride or hard-day slot for a weekend warrior whose entire persona is built around weekend availability. Putting an off day on Saturday and the long ride on Sunday is plausible but directly contradicts the persona's likely real-world constraints and is not explained or justified anywhere in the text.

### 17. [major] ×1  (gravel/weekend_warrior)
> Race fueling figure inconsistency: the plan JSON specifies 54 g carbs/hour over a 5.5 h event (≈297 g total), but current sports-science guidance for a finish-goal athlete over 5+ hours is typically 60-90 g/hour. 54 g/hour is on the low end and may underserve this athlete on race day; if the nutrition section (not shown in the truncated text) cites a different number it risks contradicting the JSON-derived figure used elsewhere.

### 18. [minor] ×2  (gravel/time_crunched_parent, gravel/weekend_warrior)
> FTP Test Frequency check returned WARN. For a 9-week plan there should be at most one mid-plan retest; the guide says 'The test result sets ALL your training zones for the next 6 weeks' — in a 9-week plan that phrasing implies a second test would only leave 3 weeks, which is too short to benefit. The guide should clarify the actual retest cadence for this specific plan length.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The guide's 'Race Day' and 'Race Week' sections (referenced in the table of contents) presumably treat the race as a single-day event. La Ruta is a 3-day stage race; race week strategy and race day execution for a stage race are fundamentally different (daily recovery between stages, stage pacing, overnight fueling, gear transitions). This content is wrong for the event type.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Fueling is prescribed at 61 g carbs/hour for a 9.0-hour duration. La Ruta is a stage race — the total duration across 3 days is far longer and the per-stage duration varies. Presenting a single 9-hour fueling block is misleading and potentially dangerous for an athlete who might interpret it as a single-day effort.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> The 'Gravel Skills' section (listed in the Contents) should not exist in a plan labelled MTB discipline. Conversely, if the plan is correctly for a gravel race, the discipline tag in the system must be corrected to gravel — either way the discipline metadata and content are inconsistent and one of them is wrong.

### 22. [major] ×1  (mtb/ambitious_first_timer)
> The 'Women-Specific Considerations' section is listed in the Contents but never appears in the truncated guide text. If it is genuinely missing from the generated document (not just cut off in the preview), it is an incomplete plan delivered to a paying female athlete who likely expects that section.

### 23. [major] ×1  (mtb/ambitious_first_timer)
> Experience level contradiction: The profile states '1 Years Riding' yet labels the athlete 'Intermediate level.' For a 'Pyramidal / ambitious first-timer' persona these two descriptors are inconsistent and will erode athlete trust. Either the label or the years figure is wrong.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency flagged WARN by the automated gate, but the guide does not acknowledge or mitigate this. For a 10-week plan with an unknown FTP baseline, the athlete deserves clarity on when (and whether) a second test occurs — the guide only mentions the Week 1 test.

### 25. [major] ×1  (mtb/ambitious_first_timer)
> The 'G Spot' zone label (between Tempo and Threshold) is non-standard jargon that appears with no prior explanation of its origin or purpose. For a first-timer this is confusing and risks the guide reading as auto-generated rather than coach-crafted.
