# Improvement backlog — 2026-07-22

**Quality 2.26** · avg coach 6.5/10 · contract pass 88% · load 12.5/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is a USA Cycling road racing category progression concept that is completely irrelevant to a masters gran fondo athlete whose only goal is to finish a 96-mile event. It signals the guide was not properly tailored and would badly erode trust.

### 2. [critical] ×1  (road/masters_returner)
> Long ride duration is capped at '1.5–2.5 hours' in the Weekly Structure section. For a 96-mile race with an estimated 6.1-hour finish time, this is dangerously low. Even accounting for the Time-Crunched methodology, the guide itself flags the shortfall but then fails to correct the stated cap upward — the number as written is misleading and potentially harmful to race-day preparation.

### 3. [critical] ×1  (gravel/masters_returner)
> FTP zone chart omits the % FTP column for Zone 1. Zone 1 is listed as '0–93W' with no % FTP range shown, while every other zone has one. This is incomplete and will confuse the athlete when they try to use the chart without a power meter.

### 4. [critical] ×1  (gravel/masters_returner)
> Weekly Volume automated check returned WARN but was not resolved before send. This flag must be investigated — if the prescribed weekly hours are outside an acceptable range for a 63-year-old masters returner on 9 h/week, the plan should not go out until the discrepancy is explained or corrected.

### 5. [critical] ×1  (gravel/masters_returner)
> Race name mismatch/confusion: the verified database lists this event as 'Sea Otter Ciclobrava' in Girona, Costa Brava, Spain, but 'Sea Otter' is a well-known brand associated with Monterey, CA. The plan header repeats the name without any clarification, which will likely confuse the athlete and erode trust. If the DB entry is correct this needs an explicit note distinguishing it from the California Sea Otter Classic.

### 6. [critical] ×1  (gravel/masters_returner)
> FTP test zones note states 'The test result sets ALL your training zones for the next 6 weeks' — but the plan is only 8 weeks long and an FTP test is expected at or near the start. Six weeks would carry through to week 7, contradicting the taper phase where zones should not change. The figure '6 weeks' appears to be boilerplate copied from a longer plan template and is factually wrong for this athlete's timeline.

### 7. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong-discipline content included: the table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' — sections that belong in a road-racing plan, not a gravel fondo guide. These are embarrassing and confusing for a gravel athlete chasing a podium at Gran Fondo Maryland.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> Experience level contradiction: the plan text labels the athlete as 'Intermediate level' despite 18 years of riding experience — the persona is 'veteran_podium_chaser.' This undermines credibility and may cause the athlete to distrust the entire plan.

### 9. [major] ×1  (gravel/ambitious_first_timer)
> Off days are listed as 'Wednesday, Tuesday' — listing Wednesday before Tuesday is almost certainly a copy-paste or generation error and reads as incoherent. This will confuse the athlete about which days are rest days and undermines trust in the document.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> The fueling section in the plan facts specifies 56g carbs/hour over a 7.4-hour estimated race duration, implying a race nutrition strategy, but the truncated guide text does not reference these numbers anywhere visible. More critically, if the Nutrition Strategy section (not shown) uses a different figure, there will be a contradiction. The 56g/h figure should be confirmed consistent with whatever appears in the Nutrition Strategy section — it is on the low end for a 186W athlete and should at minimum be flagged to the athlete as a conservative starting point.

### 11. [major] ×1  (road/masters_returner)
> The preview check shows a confirmed FAIL on Per-Day Duration Caps, yet the guide text contains no acknowledgment, caveat, or corrective instruction for the athlete. A paying customer should not receive a plan with a known hard FAIL without any explanation.

### 12. [major] ×1  (road/masters_returner)
> The preview check also shows a WARN on TSS Progression, but like the duration-cap FAIL, this is not surfaced or explained anywhere in the guide text provided. If a metric is flagged, the coach note should address it.

### 13. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' is listed as a table-of-contents section. Gran fondo racing strategy (pacing, fueling, self-seeding, managing a long solo effort) is fundamentally different from criterium/road-race tactics. Including generic road-race strategy content for a finisher-goal gran fondo athlete is a content mismatch that reads as template bleed-through.

### 14. [major] ×1  (gravel/weekend_warrior)
> Zone 1 power range is wrong. The chart lists Zone 1 as '0–101W' but with FTP=185 W, Zone 1 should be ≤55% FTP = ≤101 W — that upper bound is actually correct, but the percentage column for Zone 1 is conspicuously blank (no '< 55% FTP' label), while all other zones show a % FTP band. This is inconsistent and will confuse athletes using a power meter without the watts column.

### 15. [major] ×1  (gravel/weekend_warrior)
> Long-ride duration ceiling of '1.5–2 hours' is stated explicitly in the guide, but for a 60-mile gravel race estimated at ~5.5 hours the plan itself acknowledges this is short and asks the athlete to extend voluntarily. For a finish-goal weekend warrior, the coached plan should prescribe at least one 3-hour long ride rather than capping guidance at 2 hours and offloading responsibility to the athlete — this risks leaving them underprepared on race day and reflects poorly on the plan's completeness.

### 16. [major] ×1  (gravel/masters_returner)
> Off days are listed as Saturday, Wednesday, AND Thursday — that is 3 full rest days in a 7-day week. Combined with 4 training days this totals only 4 riding days, yet the text simultaneously says 'Your week has 4 training days, 3 of which are key sessions.' Three key sessions in 4 days is aggressive for a masters returner and conflicts with the rest-day count (losing both Wed and Thu mid-week breaks up any sensible interval/recovery rhythm).

### 17. [major] ×1  (gravel/masters_returner)
> Long-ride duration range cited as '3.4–5.8 hours.' At 9 h/week total, a single ride of 5.8 hours would consume 64% of the weekly budget in one session, leaving only 3.2 hours for all other days — inconsistent with the stated 4-session week and suspicious for a masters athlete targeting a 'finish' goal on a 55-mile course.

### 18. [major] ×1  (gravel/masters_returner)
> The fueling section (truncated in the guide) prescribes 56 g carbs/hour for a race estimated at 5.0 hours. The plan text must clearly tie this recommendation to race day and distinguish it from training fueling — if the guide presents 56 g/h as a general training target without that caveat, it is under-fueling for a 5-hour effort (current sports science supports 80–120 g/h for trained athletes in events ≥ 2.5 h with gut training).

### 19. [major] ×1  (road/veteran_podium_chaser)
> "Category 5 to Category 1 Pathway" section is listed in the TOC. This athlete is a veteran podium-chaser targeting a gran fondo — not a USA Cycling road criterium/circuit racer working through licensing categories. Cat 5→1 pathway content is irrelevant and potentially confusing or embarrassing for this customer.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume check returned WARN but no explanation or mitigation appears in the visible guide text. At 15h/week for a 100-mile gran fondo, volume could be fine, but the plan should acknowledge and justify the flagged figure rather than silently pass it to the athlete.

### 21. [minor] ×2  (gravel/veteran_podium_chaser, road/veteran_podium_chaser)
> Long ride duration range given as '3.4–5.8 hours' in the Weekly Structure section. For a 100-mile gran fondo that the fueling section pegs at 5.0h race duration, a ceiling of 5.8h on the long ride is plausible but should be explicitly tied to race duration context; as written it appears as an unexplained range that could confuse the athlete.

### 22. [major] ×1  (gravel/masters_returner)
> The long-ride duration range cited in the Weekly Structure section ('2.7–4.5 hours') is inconsistent with the athlete's 8 h/week target and an 8.3-hour race. A peak long ride of only 4.5 hours is marginal for race-preparation confidence on an all-day gravel event, and the lower bound of 2.7 hours in the same sentence undersells the base-phase rides — the range reads like it was pulled from a shorter-plan template.

### 23. [major] ×1  (gravel/masters_returner)
> The plan's TSS Progression check returned WARN (flagged by the automated preview), yet the guide text contains no acknowledgment of this warning, no explanation of the non-standard progression, and no coaching rationale for why it is acceptable. A paying masters athlete deserves transparency, especially given the known risk of overreaching.

### 24. [major] ×1  (gravel/masters_returner)
> 'Gravel Skills' appears as a named section in the Table of Contents but is not included in the truncated guide text supplied for review. If that section contains road-racing-specific drills (e.g., criterium cornering, echelon riding) rather than gravel-appropriate skills (loose-surface cornering, singletrack line choice, tubeless repair), it would be a discipline mismatch. The section must be audited before sending.

### 25. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN in preview but the guide never addresses or justifies this. At 12 h/week for an experienced female master, 12 hours is within reason, but the document must either resolve the flag (e.g., explain that early-phase weeks are intentionally lower) or the underlying volume issue must be fixed before sending.
