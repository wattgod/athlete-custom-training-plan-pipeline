# Improvement backlog — 2026-08-06

**Quality 2.14** · avg coach 6.29/10 · contract pass 75% · load 11.62/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the plan body. This is USA Cycling road-racing category content that is entirely irrelevant to a granfondo participant. It signals the wrong athlete profile was partially merged into this document and is embarrassing to send.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> Section titled 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' are listed in the Table of Contents and apparently included in the guide. This is a GRAVEL event (GFNY Miami), not a road criterium or road race. Cat 1–5 categorization is a USA Cycling road racing construct with zero relevance to a gravel mass-participation event. Sending this to a gravel athlete is embarrassing and undermines trust in the entire plan.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> Zone chart is missing power watt ranges for Zone 1 (Active Recovery) and Zone 6 (Anaerobic). Every other zone shows explicit watt ranges (e.g., Zone 2: 98–132W), but Z1 and Z6 show only '0-97W' and '>213W' labels without the full formatted row — the athlete cannot use the chart to set their head unit or trainer for these zones without guessing.

### 4. [critical] ×1  (gravel/masters_returner)
> Off days listed as 'Tuesday, Monday' — Monday is named second, implying it may be a mid-week off day rather than the start-of-week rest day. The ordering is confusing and potentially wrong; the calendar is described as the source of truth, but this text contradicts a logical weekly structure and will alarm the athlete.

### 5. [critical] ×1  (road/masters_returner)
> "Category 5 to Category 1 Pathway" section is listed in the table of contents. This is a USA Cycling road-racing category upgrade pathway, which is irrelevant and actively misleading for an athlete whose sole goal is to FINISH a gran fondo (L'Étape). It implies competitive category racing that has nothing to do with this event or this athlete's objective, and it could seriously confuse or alarm a masters returner.

### 6. [critical] ×1  (road/masters_returner)
> Off days are listed as Saturday, Sunday, AND Monday — three consecutive days off — while the long ride falls on Tuesday. For an 8 h/week plan with only 4 training days, clustering all rest at the weekend and then starting the training week on Tuesday is an unusual structure that is never explained or justified. Combined with the Zone Distribution WARN flag, this raises a real concern that the weekly pattern may be misaligned, and the guide never addresses the WARN.

### 7. [critical] ×1  (road/veteran_podium_chaser)
> Athlete is labelled 'Intermediate level' in the methodology justification section despite the plan data showing 18 years of riding and a 370 W FTP. This is factually wrong and will destroy credibility with an experienced racer chasing a podium. The label must be corrected to reflect his actual experience tier.

### 8. [major] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> Long ride duration range cited as '3.2–5.3 hours' in the Weekly Structure section but the fueling section projects race duration at 4.6 hours. A peak long ride of 5.3 hours would exceed the expected race duration by ~45 minutes — plausible for over-distance training, but the guide never explains this intent, which may confuse a first-timer who thinks they need to ride longer than the race.

### 9. [major] ×1  (road/weekend_warrior)
> The Table of Contents includes 'Road Skills', 'Road Race Strategy', and — most problematically — 'Category 5 to Category 1 Pathway'. This athlete is a 48-year-old weekend warrior whose only goal is to finish a gran fondo (mass-participation event), not race a USA Cycling category ladder. The Cat 5→1 pathway section is completely irrelevant and could confuse or mislead the athlete about what they are training for.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> Zone Distribution preview check explicitly FAILED yet the guide contains no acknowledgment of this or corrective guidance. A failed zone distribution is a meaningful training quality issue; shipping the plan without a coach note explaining the deviation (or confirming it is intentional) leaves the athlete training in the wrong distribution with no awareness.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check returned WARN. No explanation or caveat appears in the visible guide text. For an ambitious first-timer who may not self-regulate, a TSS progression anomaly (too steep a ramp, or a dip that breaks continuity) should be flagged explicitly so the athlete understands what to expect week-to-week.

### 12. [major] ×1  (gravel/masters_returner)
> Zone Distribution pre-check flagged WARN. The guide text never acknowledges or resolves this warning. If zone distribution is off (e.g., too much Z3 'gray zone'), the plan could undermine the very pyramidal principles the guide lectures about at length — this needs to be confirmed acceptable or corrected before sending.

### 13. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency pre-check flagged WARN. The guide states the FTP test result 'sets ALL your training zones for the next 6 weeks' — in a 9-week plan with an unresolved frequency warning, this claim may be inaccurate (e.g., if only one test is scheduled early, zones may be stale for the final weeks including peak/taper). The stated 6-week horizon should be reconciled with actual test scheduling.

### 14. [major] ×1  (gravel/masters_returner)
> The athlete has ftp_known=false, yet the plan opens with '171W FTP' presented as a confirmed figure and builds all zone power numbers from it. The guide never instructs the athlete that this FTP is estimated/assumed and must be validated with the Week 1 ramp or 20-minute test before trusting the zone chart — this could lead to 9 weeks of miscalibrated training.

### 15. [major] ×1  (road/masters_returner)
> The plan is 16 weeks but the race is 17 weeks away; the guide never explains to the athlete when to start (i.e., one week from now they simply begin Week 1). The plan_note exists in the JSON for internal use, but the athlete-facing guide contains no instruction on what to do in the gap week, leaving a paying customer confused about their start date.

### 16. [major] ×1  (road/masters_returner)
> "Road Skills" and "Road Race Strategy" sections appear in the table of contents. While road skills are appropriate, the framing must be gran-fondo/sportive specific (climbing, fueling on the move, managing effort over 68 miles). If the generated content mirrors a road-racing skills section (criterium cornering, drafting tactics for pack racing, etc.) rather than a mass-participation fondo context, it is wrong for this athlete. The presence of the Cat 5–Cat 1 pathway in the same list strongly suggests the template is pulling race-oriented content.

### 17. [major] ×1  (road/masters_returner)
> Strength training is listed as 'Included (bodyweight)' in the at-a-glance summary and mentioned generically in section 4, but no actual exercises, sets, reps, or progression are shown in the truncated guide. For a 57-year-old masters athlete — where strength work is especially important — omitting the specifics (or promising them without delivering) is a meaningful gap.

### 18. [major] ×1  (gravel/time_crunched_parent)
> Long-ride duration cap is severely understated: the guide tells the athlete peak long rides are '1.5–2.5 hours,' then in the very next callout admits a 3–4 hour ride is worth far more for a 109-mile race. For a ~9.5-hour event, even within a Time-Crunched framework the plan should be targeting at least one 3–4 hour long ride at peak, not 2.5 hours. Stating 2.5 hours as the top of the range, then contradicting it in the same paragraph, is confusing and undersells the event demands.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Zone 2 power band is missing its lower bound percentage. The table shows '56–75% FTP' in the % column but Zone 1 has no % FTP values at all, and Zone 2's lower bound (56%) implies 129 W, yet the power column reads '127–172 W' — a minor arithmetic inconsistency (56% of 230 = 128.8 W, rounds to 129, not 127). The 127 W figure suggests a different formula was used. Small but embarrassing if a data-literate athlete checks the math.

### 20. [major] ×1  (gravel/time_crunched_parent)
> The guide's stated 5-training-days-per-week / 3-key-sessions structure is never reconciled with the 6 h/week cap for a time-crunched athlete. Five days at 6 h total averages only 72 min per session — workable, but the guide should explicitly state average session lengths so the athlete knows what to expect. As written it could imply a much larger weekly commitment than the athlete signed up for.

### 21. [major] ×1  (road/veteran_podium_chaser)
> Weekly volume check flagged WARN and Zone Distribution flagged WARN by the automated preview, yet no coaching note addresses these warnings. For an 11 h/week veteran targeting a podium at a ~4-hour mountainous granfondo, any deviation from expected volume or zone mix needs an explicit rationale in the guide, or the numbers need correcting.

### 22. [major] ×1  (road/veteran_podium_chaser)
> Athlete is described as 'Intermediate level' in the methodology rationale ('11 years of cycling experience at Intermediate level'). The persona is 'veteran_podium_chaser' (Experienced racer) — 11 years is not intermediate. This is a direct contradiction of the athlete's own data and will undermine trust.

### 23. [major] ×1  (road/veteran_podium_chaser)
> The table of contents includes 'Road Race Strategy' as a standalone section. Gran Fondo Hincapie is a gran fondo, not a road race. Gran fondo tactics (managing effort over 83 miles, not attacking in a peloton) are meaningfully different. If this section contains road criterium or road race peloton tactics, it is wrong-discipline content for this athlete.

### 24. [minor] ×1  (road/weekend_warrior)
> The long-ride peak duration is stated as '2.5–4.2 hours' in the Weekly Structure section. For a 68-mile event at finish-goal pace (~4.7 h estimated), a peak long ride ceiling of 4.2 hours is on the low end but arguably acceptable for Time-Crunched; however, the range reads as a static fact rather than a progression endpoint, which may confuse athletes in early weeks who see 2.5 h as a ceiling.

### 25. [minor] ×1  (road/weekend_warrior)
> The guide notes 'Strength training: Included (dumbbells)' in the at-a-glance summary, but the truncated text does not show any strength-specific guidance tailored to masters cyclists (e.g., notes on recovery overlap with bike sessions for a 48-year-old). If the full guide lacks this, it's a gap for a 48-year-old athlete where strength-bike session sequencing matters more than for younger riders.
