# Improvement backlog — 2026-08-12

**Quality 0.09** · avg coach 5.29/10 · contract pass 75% · load 14.25/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Discipline mismatch — the guide explicitly includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This is a gravel event (GFNY Cozumel). Cat 5–Cat 1 upgrade pathways are a USA Cycling road-racing concept with zero relevance to gravel. This content is embarrassing and wrong for this athlete.

### 2. [critical] ×1  (gravel/masters_returner)
> Weekly Volume check FAILED in automated preview but the plan was still passed to QA without resolution. The guide claims 9h/week and describes a 4-day week with long rides of 3.8–6.2 hours, but no corrective note or explanation is present. Either the volume is miscalculated or the cap logic is broken — either way it must be resolved before sending.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> FTP value is listed as both watts (149W, correct) AND as body weight in lbs (149 lbs) in the 'Your Profile' section. The athlete's actual weight is not in the intake data, so 149 was pulled from the FTP field and incorrectly stamped into the weight field. This is factually wrong and looks like a system error to any reader.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline is MTB but the guide includes road-racing-specific sections: 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' are listed in the table of contents. These sections are irrelevant and inappropriate for a mountain bike athlete — they signal the template was not correctly filtered for discipline.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> GFNY Miami is a road gran fondo (tarmac), yet the athlete's discipline is recorded as 'mtb.' If the race truly is a road event, the discipline tag is wrong and MTB-specific content (trail skills, etc.) would be mismatched. If the athlete is genuinely an MTB rider doing a road event, the plan still must not include MTB-specific off-road skills content. Either way, the discipline/event mismatch must be resolved before sending.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Road-discipline content in an MTB plan: the guide includes a 'Road Skills' section and a 'Road Race Strategy — Category 5 to Category 1 Pathway' section (visible in the Table of Contents). This athlete is training for a mountain-bike gran fondo, not a road criterium or road race. Cat 5-to-Cat 1 upgrade pathways are USA Cycling road-race constructs that are irrelevant and confusing here. This content must be replaced with MTB-specific skills (trail braking, switchback technique, technical descending, singletrack line choice) before sending.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Fueling numbers are missing from the visible guide. The plan JSON specifies 55 g carbs/hour for a ~4.6-hour event, but the truncated 'Nutrition Strategy' section shows no race-day or on-bike fueling prescription visible to the athlete. If the Nutrition Strategy section in the full document also omits these figures, the athlete has no actionable fueling plan for a multi-hour MTB event — a significant safety and performance gap. Must verify the full section contains the 55 g/h target and practical product/timing guidance.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> Profile card lists '135 lbs Weight' AND '135W FTP' — the athlete's FTP value (135 W) has been mis-populated into the weight field. The athlete's actual weight was never collected (ftp_known=false context), so a fabricated weight number matching the FTP has been inserted. This is factually wrong and will confuse the athlete about which number is which.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably in the body. El Tour de Tucson is a mass-participation gran fondo/century ride, not a USAC-licensed criterium or road race with cat upgrade points. This section is discipline- and event-type wrong for this athlete and goal, and undermines credibility.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> Race date countdown of '65 days from today' is hardcoded and wrong. From the plan start date of 2026-08-24 to the race on 2026-10-16 is 53 days, and from a typical 'today' at time of generation it will be different still. A wrong countdown directly undermines the taper warning the plan itself emphasises.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the athlete profile is flagged as 'mtb' (discipline: mtb), yet L'Étape Ciudad de México by Tour de France is a verified road/gran fondo event (68 miles on pavement, Mexico City road course). The guide then compounds this by including 'Road Skills' and 'Road Race Strategy' sections AND a 'Category 5 to Category 1 Pathway' section visible in the table of contents. If the discipline field is wrong, the plan must be regenerated for road; if the event data is wrong, it must be corrected. Either way, the current combination is unsendable.

### 12. [critical] ×1  (mtb/ambitious_first_timer)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. This athlete's goal is simply to finish their first big event — they are not a licensed racer pursuing category upgrades. This section is irrelevant, potentially confusing, and undermines the credibility of the plan as a personalised document.

### 13. [major] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> TSS Progression check returned WARN in the preview checks but is not acknowledged anywhere in the guide. For a time-crunched athlete with high stress, a TSS progression anomaly (likely a week-over-week jump exceeding the 10% guideline) is a real injury-risk flag that should be noted or corrected, not silently passed through.

### 14. [major] ×1  (gravel/masters_returner)
> Zone 1 (Active Recovery) row in the zone chart is missing its % FTP range — the power column shows '0-88W' but the '% FTP' column is blank. Every other zone has a percentage listed. An athlete updating zones after an FTP retest needs that number.

### 15. [major] ×1  (gravel/masters_returner)
> Zone Distribution check is WARN, yet the guide states 'roughly 75%' of riding stays Zone 1-2 without any caveat or explanation of why the distribution may drift. For a Traditional/Pyramidal plan this is the defining promise — a warn here should at minimum be acknowledged or the distribution corrected.

### 16. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section is listed in the Table of Contents. For a gravel event this should contain gravel-specific skills (loose surface cornering, technical descending, tire pressure management, mud/sand handling) — if the content mirrors road criterium or peloton skills it is wrong for this discipline and athlete.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> Height is listed as 5'4" and weight as 149 lbs in the profile block, but neither height nor weight appear in the athlete JSON provided. These values were fabricated by the template — there is no source data to support them. Sending invented biometric data to a paying customer is a credibility risk.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> The Zone Distribution preview check is flagged as WARN, yet the guide text makes no mention of this or any corrective note. A WARN on zone distribution in a Pyramidal plan — where correct zone balance is the core methodology — should either be explained or resolved before sending.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> The fueling section (54g carbs/hr, 4.6h duration) is referenced in the plan JSON but does not appear in the truncated guide text shown. If the Nutrition Strategy section is missing or empty, this is a significant omission for a 71-mile, ~4.6-hour goal event where fueling is explicitly flagged as race-critical.

### 20. [major] ×1  (mtb/weekend_warrior)
> Zone 1 power range is listed as '0–90 W' but no percentage-of-FTP anchor is given, unlike every other zone. At FTP 165 W that ceiling is 55% FTP — reasonable, but the omission is inconsistent with the rest of the chart and leaves athletes with different FTPs unable to rescale easily. Add '< 56% FTP' to complete the row.

### 21. [major] ×1  (mtb/weekend_warrior)
> Off-days listed as 'Friday, Tuesday, Monday' in the 'At a Glance' section — three off-days — but the plan states 4 training days per week in the Weekly Structure section. Three off-days in a 7-day week leaves only 4 training days, which is consistent, but listing off-days as 'Friday, Tuesday, Monday' is an odd, non-chronological ordering that reads as a copy-paste error and will confuse athletes scanning their week. Should be presented in day order (Monday, Tuesday, Friday) or restructured for clarity.

### 22. [major] ×1  (road/veteran_podium_chaser)
> The plan JSON states ftp_known=false, yet the guide presents 135 W as a confirmed FTP and builds a full zone chart from it without flagging that this number is estimated or self-reported. The FTP test protocol section exists but the zone chart is presented as authoritative rather than provisional, which could send the athlete into 13 weeks of miscalibrated training.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Height listed as 5'4" — the athlete's height was not present in the plan JSON. This appears to be a fabricated or default value inserted into the profile card, which is an invented athlete fact not grounded in any supplied data.

### 24. [major] ×1  (road/veteran_podium_chaser)
> The table of contents includes a 'Women-Specific Considerations' section, which is appropriate, but also 'Road Skills' and 'Road Race Strategy' as separate entries alongside 'Category 5 to Category 1 Pathway.' For a 102-mile gran fondo with a podium goal, the strategy content should be fondo/mass-start specific (positioning in large field, aid station tactics, pacing over 100 miles), not generic road-race or upgrade-pathway content.

### 25. [major] ×1  (gravel/time_crunched_parent)
> Off days listed as 'Thursday, Wednesday, Saturday' — that is THREE off days, yet the Weekly Structure section states the athlete has '4 training days.' Three off days in a 7-day week leaves only 4 training days, which is internally consistent numerically, but listing Saturday as an off day conflicts with gravel athletes typically needing Saturday for long outdoor rides; more importantly the Long Ride Day preview check passed for Sunday, so Saturday being off is plausible — however naming three specific off days while the guide elsewhere says 'the calendar is the source of truth' creates confusion and risks the athlete skipping Saturday rides if the calendar actually schedules one.
