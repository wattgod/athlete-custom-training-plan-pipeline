# Improvement backlog — 2026-09-18

**Quality 0.59** · avg coach 5.38/10 · contract pass 88% · load 13.88/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (gravel/ambitious_first_timer, gravel/time_crunched_parent)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full guide body) — this is a road-racing construct that is completely wrong for a gravel gran fondo. UCI Gran Fondo Loutraki is a mass-participation timed event, not a categorized road race. This content is from the wrong discipline template and will confuse or embarrass the athlete.

### 2. [critical] ×2  (gravel/masters_returner, gravel/weekend_warrior)
> Table of contents includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' chapters. This athlete is doing a gravel gran fondo with a goal of 'finish' — road racing categories (Cat 5 to Cat 1) are entirely irrelevant, belong to a different discipline template, and will confuse and undermine trust with this customer.

### 3. [critical] ×1  (gravel/masters_returner)
> Table of contents lists 'Road Skills' as a chapter. A gravel gran fondo requires gravel/off-road skill content (loose surface cornering, variable terrain, tire pressure management, etc.), not generic road skills. Wrong discipline content in the guide.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section is listed without qualification — if it contains road-racing cornering or peloton skills content (likely given the template bleed-through), it is inappropriate for a solo gravel gran fondo where the athlete's goal is simply to finish. Gravel-specific technical skills (loose surface cornering, gear selection on climbs, self-sufficient nutrition carry) should be here instead.

### 5. [critical] ×1  (road/time_crunched_parent)
> The guide contains a 'Category 5 to Category 1 Pathway' section. This athlete is a 38-year-old time-crunched parent doing a Gran Fondo with a goal of 'finish.' Cat 5→1 upgrade pathways are a road racing / criterium licensing concept that is completely irrelevant to a Gran Fondo and to this athlete's stated goal. Sending this would be confusing and embarrassing — it signals the plan was not properly tailored.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> "Road Skills" section is also listed in the TOC. A gravel-specific guide should cover gravel-specific skills (loose surface cornering, descent technique on unpaved roads, tire pressure management, navigation). Generic road skills content is wrong-discipline filler for this event.

### 7. [critical] ×1  (gravel/weekend_warrior)
> Zone 1 power boundary is listed as '0-85W' with no lower FTP percentage anchor, and Zone 2 starts at 86W / 56% FTP — but 56% of 155W is 87W, not 86W. More importantly, Zone 1 upper bound of 85W is 55% FTP, yet the chart omits the % FTP column for Zone 1 entirely, creating an inconsistency that undermines the athlete's ability to use the chart on a power meter.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section is listed in the table of contents. Gravel-specific skills (loose surface cornering, off-camber braking, gravel descending, surface reading) should replace or supplement road skills content. Sending road-skills coaching to a gravel racer is a credibility-damaging error.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete is a veteran gran fondo racer chasing a podium — road racing categories are irrelevant and will confuse or alienate a paying customer. It signals a template bleed-through from a different persona/discipline and is the kind of thing that destroys trust in a bespoke plan.

### 10. [major] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> The preview check flagged 'Taper Intensity: WARN' but the guide contains no acknowledgement, explanation, or corrective guidance for the athlete about taper intensity expectations. A flagged warning that is silently passed through to the customer without context is a coaching failure — the athlete deserves to know what to expect or what to watch for.

### 11. [major] ×1  (gravel/masters_returner)
> Fueling carb rate is listed as 55g/hour. For a ~5.7-hour effort at a goal of 'finish' (steady endurance pace), current sports nutrition consensus supports 60–90g/hour for trained athletes. 55g/hour is on the low end and may leave this athlete under-fuelled late in a long desert event; the number should at minimum be flagged or explained, not silently prescribed below standard guidance.

### 12. [major] ×1  (gravel/masters_returner)
> Zone distribution and TSS progression both flagged WARN in preview checks, and Taper Intensity is also WARN — three simultaneous warnings suggest the generated schedule may have meaningful structural issues (e.g. too much Z3 'grey zone' riding, irregular TSS ramp, or insufficient taper sharpness). These were not resolved before the plan reached QA and the guide text does not acknowledge or address them.

### 13. [major] ×1  (gravel/masters_returner)
> The guide refers to 'Road Race Strategy' content in the body (visible in TOC). Gravel gran fondo racing strategy is meaningfully different — pacing on variable surfaces, managing rough terrain fatigue, aid station strategy in a desert environment — none of which will be covered if this is a recycled road template.

### 14. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression check returned WARN and was not resolved before sending. A paying athlete should not receive a plan with a known flagged issue left unaddressed — either the progression ramp was fixed, or the guide should explain the deliberate deviation (e.g., a spike week followed by a recovery week). Neither explanation appears in the truncated guide.

### 15. [major] ×1  (gravel/time_crunched_parent)
> Fueling section references 53 g carbs/hour for an estimated race duration of ~4.65 hours, implying ~246 g total — but no explicit race-day fueling plan (products, timing, on-bike carry for a 70-mile gravel event) is visible in the truncated guide. For a gravel gran fondo with potential aid station uncertainty, omitting practical on-bike fueling logistics is a meaningful gap for a finish-goal athlete.

### 16. [major] ×1  (road/time_crunched_parent)
> The automated Zone Distribution check returned FAIL and there is no evidence in the guide text that this was corrected or overridden with a coaching justification. The guide claims 'roughly 70%' of riding stays in Z1-Z2, but if the calendar sessions underlying this guide do not actually achieve that distribution, the narrative description is false and misleading to the athlete.

### 17. [major] ×1  (road/time_crunched_parent)
> The FTP Test Frequency check returned WARN. With a 9-week plan and an athlete who has no known FTP, a single Week 1 field test may be insufficient. The guide never addresses a mid-plan re-test or explains why one test is adequate for the full 9 weeks. At minimum, a coaching rationale for the single-test approach should appear in the guide so the athlete isn't left wondering.

### 18. [minor] ×2  (gravel/ambitious_first_timer, road/time_crunched_parent)
> The long-ride duration range given in the guide ('2.1–3.5 hours') represents only 35–58% of the estimated 6.7-hour race duration. While this is expected for a time-crunched athlete, the guide does not explain this gap or reassure the athlete that the shorter long rides are sufficient preparation — a likely source of anxiety for a first-time Gran Fondo finisher.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Post-ride nutrition sentence is visibly cut off mid-sentence: '…0.3-0.4g protein/kg + 1.0-1.2g carbs/kg aft' — the guide is being sent truncated. A paying customer will see an incomplete instruction, which looks unprofessional and leaves them without the complete recovery fueling guidance.

### 20. [major] ×1  (gravel/time_crunched_parent)
> The TSS Progression preview check is flagged WARN but there is no explanation or caveat anywhere in the guide text acknowledging this. Given the athlete's high-stress flag and the 12-week compressed timeline, a coach note about the TSS ramp should appear — its omission means the athlete has no context if a week feels harder than expected.

### 21. [major] ×1  (gravel/weekend_warrior)
> Table of contents lists 'Road Skills' — acceptable for gravel — but immediately followed by 'Road Race Strategy', suggesting the road-racing template sections were not stripped out. Even if the Road Skills section itself is gravel-appropriate, its proximity to Category 5-1 pathway content signals a template bleed-through that needs a full audit of those sections before sending.

### 22. [major] ×1  (gravel/weekend_warrior)
> plan_weeks is 11 but weeks_until_race is 10, meaning the plan starts one week before the noted start date of 2026-09-21 — or the plan actually begins 2026-09-21 and runs to 2026-11-30 (70 days = exactly 10 weeks). The guide header says '11 weeks' and the brief confirms '11 weeks', but the math from 2026-09-21 to 2026-11-30 is 10 weeks and 2 days. This discrepancy should be resolved so the athlete isn't confused about when to start.

### 23. [major] ×1  (gravel/weekend_warrior)
> The 'GS G Spot' zone label ('The G Spot between tempo and threshold') is unprofessional and potentially off-putting for a paying customer receiving a formal training document. A label like 'Sweet Spot' is the standard industry term and should be used instead.

### 24. [major] ×1  (gravel/ambitious_first_timer)
> plan_weeks (11) exceeds weeks_until_race (10), meaning the plan start date of 2026-09-21 places Week 1 before the athlete would normally begin — yet the guide never flags or explains this overlap. The plan_note clarifies this is not a contradiction only if the plan ends on race day, but the guide should make this timeline explicit so the athlete is not confused about when to start.

### 25. [major] ×1  (road/veteran_podium_chaser)
> The zone chart is incomplete: Zone 1 shows only a watt range (0-145W) with no % FTP or % LTHR columns filled in, and Zone 2 shows watts (146-198W) and LTHR but the % FTP field appears blank or inconsistently populated. For a power-based athlete with a known FTP of 265W this omission undermines the entire 'power > HR > RPE' instruction given later.
