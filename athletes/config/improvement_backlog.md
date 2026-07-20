# Improvement backlog — 2026-07-20

**Quality -0.24** · avg coach 5.25/10 · contract pass 88% · load 15.62/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/veteran_podium_chaser)
> Table of Contents and apparent section content includes a 'Category 5 to Category 1 Pathway' section. This is entirely inappropriate for a veteran podium-chaser on a road KOM — it is beginner racing-category progression content that has no place in this athlete's plan and would be embarrassing to send to an experienced racer targeting a podium.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> FTP value (138W) is being displayed as the athlete's WEIGHT in pounds in the 'Your Profile' table ('138 lbs Weight'). The athlete's actual weight was never collected per the JSON data — this is a hallucinated number that happens to match her FTP, and it will confuse or mislead the athlete. A weight of 138 lbs / 62.6 kg / 5'2" implies a BMI of ~25, which may or may not be accurate but was never provided. The height (5'2") is also fabricated — it does not appear anywhere in the athlete JSON.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is 'mtb' (mountain bike), but the plan includes a 'Gravel Skills' section in the table of contents and is framed throughout as a gravel plan. The race 'Unravel Gravel' is indeed a gravel event in the verified DB — this exposes a deeper problem: either the athlete registered for a gravel race and was coded as MTB (the persona/discipline field is wrong), or the race assignment is wrong. Either way, the guide cannot go out with 'Gravel Skills' content and MTB discipline tagging simultaneously — this contradiction must be resolved before sending.

### 4. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full document. This is a road racing upgrade-pathway concept that is completely irrelevant to a masters female athlete whose sole goal is to FINISH a gran fondo. It will confuse or concern the athlete and signals the plan was not properly personalized.

### 5. [critical] ×1  (road/masters_returner)
> Long-ride duration ceiling of '1.5–2.5 hours' is stated as the peak long-ride range in the Weekly Structure section. For an 85-mile race with an estimated 5.7-hour finish time, a maximum long ride of 2.5 hours is grossly inadequate and contradicts the plan's own 'Biggest Opportunity' advisory. Even under Time-Crunched methodology, the athlete needs at least one 3–4 hour long ride approaching race day — which the advisory itself acknowledges but the structural cap undercuts.

### 6. [critical] ×1  (road/time_crunched_parent)
> Three off-days listed (Thursday, Saturday, Friday) but the plan specifies 4 training days per week, meaning only 3 off-days exist — listing all three on one line in an odd order (Thu, Sat, Fri) is both mathematically suspicious and reads as a template error. A 7-day week with 4 training days has exactly 3 rest days, but Saturday being sandwiched between two other off-days while Sunday is the long ride day implies Saturday may be a training day, not a rest day — this contradicts itself and will confuse the athlete.

### 7. [critical] ×1  (road/time_crunched_parent)
> Table of Contents includes 'Category 5 to Category 1 Pathway' — a USA Cycling road racing licensure progression section that is completely irrelevant to a gran fondo participant targeting a podium finish, not a racing license upgrade. This is wrong-discipline/wrong-goal content that would embarrass the business.

### 8. [critical] ×1  (road/masters_returner)
> A 'Gravel Skills' section appears in the Table of Contents and presumably in the full guide body. This athlete is a road racer — gravel cornering, surface-reading, or bike-handling drills for loose terrain have zero relevance and are actively wrong content for this discipline. This is the single most embarrassing error a coach can make.

### 9. [critical] ×1  (gravel/ambitious_first_timer)
> Table of contents and body contain a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section — this is a GRAVEL event, not a road criterium or road race. Cat 5–1 licensing categories are a USA Cycling road/criterium construct that is irrelevant and actively misleading for a gravel athlete. These sections must be replaced with gravel-specific content (pacing on mixed terrain, singletrack/dirt road technique, etc.).

### 10. [critical] ×1  (road/time_crunched_parent)
> Off days listed as Wednesday, Tuesday, AND Saturday — that is three off days in a 7-day week, leaving only four training days, but the Weekly Structure section says '4 training days, 3 of which are key sessions.' Three off days contradicts the standard time-crunched-parent profile and almost certainly reflects a generation error (Saturday should likely be a training day, not an off day, given Sunday is the long ride day).

### 11. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' appears in the Contents and presumably in the body. This is USA Cycling road-racing category language that is completely irrelevant to a New Zealand gran fondo (Lake Taupo Cycle Challenge is a mass-participation event, not a criterium/road-race series). It is wrong for the discipline context, wrong for the country, and wrong for the event type — embarrassing if sent.

### 12. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents of a plan for an MTB Gran Fondo athlete. Road racing categories and criterium/road-race tactics are irrelevant and embarrassing inclusions; they signal this is a recycled road template.

### 13. [critical] ×1  (mtb/weekend_warrior)
> The 'Road Skills' section in the TOC is ambiguous at best; for an MTB event it should be MTB-specific technical skills (trail braking, cornering on loose surfaces, climbing traction) — road cornering or peloton skills would be actively wrong content for this athlete.

### 14. [critical] ×1  (mtb/weekend_warrior)
> FTP test warmup protocol is self-contradictory: the 5-minute 'hard opener' is described as 'RPE 8-9, NOT all-out,' but the very next line calls it a 'hard opener' whose job is to clear the anaerobic system — then 10 minutes of Z1 recovery is prescribed before the 20-minute test. The 3-minute RPE-7 effort plus the 5-minute RPE 8-9 opener with only 1-minute easy in between is a non-standard and physiologically inconsistent sequence that will confuse the athlete and risk pre-fatiguing the test.

### 15. [major] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete as 'Intermediate level' ('10 years of cycling experience at Intermediate level') when 10 years of riding with a 315 W FTP and a podium goal clearly places this athlete at Advanced/Expert. This is a direct contradiction of the athlete's profile and undermines credibility.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> The TSS Progression check returned WARN in the preview checks, but the guide text contains no acknowledgment or coach note about the non-standard progression. A paying athlete deserves transparency if their ramp is unusual, and the absence of any mention means a known flag was silently suppressed.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> The athlete profile states '1 Years Riding' and the methodology section calls this 'Intermediate level' — one year of riding experience is typically beginner, not intermediate. Labeling a 1-year rider as intermediate may set inappropriate expectations about intensity tolerance and skill baseline, especially for an MTB/gravel discipline with technical demands.

### 18. [minor] ×2  (mtb/ambitious_first_timer, road/time_crunched_parent)
> Long ride duration range cited as '1.6-2.8 hours' for a 60-mile race estimated at 5.7 hours (per fueling data). While the plan acknowledges this gap in the 'Biggest Opportunity' callout, the maximum prescribed long ride of 2.8 hours represents under 50% of race duration — the callout is good but the underlying volume cap may be genuinely insufficient for the goal event, and the guide undersells the seriousness of this gap.

### 19. [major] ×1  (road/masters_returner)
> Post-ride fueling sentence is cut off mid-word: '23g protein + 57-69g carbs withi' — the recovery protocol is incomplete and unprofessional as delivered. Even if this is a truncation artifact, the plan as emailed would be missing critical nutrition guidance.

### 20. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' is listed as a table-of-contents section. Gran Fondo Eilat is a sportive/gran fondo, not a road race. Tactics like positioning, attacks, and race-craft are irrelevant and potentially confusing for a finish-goal athlete. Content should be gran-fondo-specific (pacing, aid stations, self-sufficiency).

### 21. [major] ×1  (road/masters_returner)
> The Zone 2 power range in the zone chart is shown without a lower bound (% FTP column reads '56-75% FTP' but Zone 1 shows no watts label in the truncated text, and Zone 2 shows '80-108W'). More importantly, Zone 1 shows '0-79W' with no %FTP listed — minor inconsistency, but the %FTP column for Zone 1 is blank, which looks like a template rendering failure.

### 22. [major] ×1  (road/time_crunched_parent)
> Zone Distribution check is flagged FAIL in the preview checks but the guide text never acknowledges or resolves this — the athlete is handed a plan with a known quality failure and no explanation. Either the guide should explain the deviation or the plan should be corrected before sending.

### 23. [major] ×1  (road/time_crunched_parent)
> The goal field is 'podium' but the guide's goals section only says 'Compete' — the most important and motivating athlete goal has been truncated or dropped, which is deflating and suggests a template population error.

### 24. [major] ×1  (road/masters_returner)
> The Zone 3 / pyramidal volume split percentage (stated as 'roughly 75% easy') is referenced in prose but the zone chart never actually shows a % Time column or pyramidal distribution breakdown for this athlete. For a methodology plan, the athlete needs to see what fraction of their 8 h/week lives in each zone. The number 75% appears once in passing and is never reinforced with concrete weekly minutes.

### 25. [major] ×1  (road/masters_returner)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is only an 8-week plan and the athlete already has a known FTP of 186W. The '6 weeks' figure is a generic copy-paste that contradicts the actual plan length and could confuse the athlete about when/whether to retest.
