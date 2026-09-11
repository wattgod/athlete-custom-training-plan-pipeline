# Improvement backlog — 2026-09-11

**Quality -0.94** · avg coach 5.12/10 · contract pass 62% · load 15.75/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (gravel/masters_returner, road/masters_returner, road/veteran_podium_chaser)
> Long ride duration range cited as '3.9-6.5 hours' in the Weekly Structure section. For an 85-mile gran fondo at a masters finishing pace the fueling model estimates ~5.7 hours of race duration — a peak long ride of 6.5 hours would be extremely aggressive for a 9h/week athlete with a 'finish' goal and a masters-returner profile. This number needs verification against the actual calendar.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This is a GRAVEL event (GFNY Miami). Road racing category progression is irrelevant and actively misleading for a gravel finisher — embarrassing if a paying customer reads it.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> Multiple preview checks flagged WARN (Weekly Volume, Zone Distribution, TSS Progression, FTP Test Frequency) with no explanation or mitigation in the guide text. Zone distribution and TSS progression warnings in particular could mean the actual week-by-week numbers are malformed — this needs resolution before the plan is sent, not just noted.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of Contents and plan body include a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section — both are road-racing constructs that are entirely wrong for a gravel discipline. Gravel events have no USA Cycling category licensing ladder and no road criterium/peloton tactics. Sending this to a gravel racer is embarrassing and undermines credibility.

### 5. [critical] ×1  (gravel/veteran_podium_chaser)
> Automated preview gate reports 'Weekly Volume: FAIL'. This means at least one week's prescribed hours breach the athlete's 13 h/week target (either over-cap or under-cap to a degree the checker flagged). The plan text has not been corrected before QA submission; the root cause must be identified and fixed before sending.

### 6. [critical] ×1  (road/masters_returner)
> Table of contents and plan body include a 'Category 5 to Category 1 Pathway' section. This athlete's goal is to FINISH a gran fondo — a mass-participation event with no racing categories. This content is completely irrelevant, implies the athlete is pursuing USA Cycling road racing licensing, and would confuse or mislead a paying customer.

### 7. [critical] ×1  (road/masters_returner)
> Weekly Volume check is flagged FAIL in the preview checks, but the guide text provides no explanation or caveat. Sending a plan with a known volume error to a customer without disclosure or correction is unacceptable.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section is listed in the Table of Contents and presumably present in the full document. This is a USA Cycling amateur road racing categorization system that has zero relevance to a UCI Gran Fondo — gran fondos have no such category structure. Including it is embarrassing, wrong-discipline content that undermines credibility with an experienced athlete.

### 9. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch in table of contents: 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway' sections appear in a plan for an MTB athlete targeting a gran fondo. Road racing licensing pathways and road race tactics are irrelevant and embarrassing content for this customer.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution preview check is flagged FAIL but the plan was allowed through. The guide text does not acknowledge or address this failure, meaning the athlete will train to a zone distribution that the system itself has already identified as wrong.

### 11. [critical] ×1  (mtb/weekend_warrior)
> Plan duration mismatch: the JSON states weeks_until_race = 12 but plan_weeks = 13, meaning the plan extends one week PAST race day. The plan_note explains this is intentional only when plan_weeks < weeks_until_race (athlete starts later). Here plan_weeks > weeks_until_race, which is a genuine contradiction — the plan would run through and beyond race day on December 7, 2026.

### 12. [critical] ×1  (road/time_crunched_parent)
> A 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full guide. This is USA Cycling road-racing category terminology and is completely irrelevant to a New Zealand gran fondo (Lake Taupo Cycle Challenge). The race has no licence categories — it is a mass-participation event. This section will confuse and embarrass.

### 13. [critical] ×1  (road/time_crunched_parent)
> The off-day layout lists Tuesday, Saturday, AND Sunday as off days, with the long ride on Monday. For a time-crunched parent, having the long ride (3.3–5.5 h) on a Monday — a weekday — is almost certainly a scheduling error. Saturday and Sunday are the natural long-ride days for this persona; the day assignment logic appears inverted.

### 14. [critical] ×1  (gravel/masters_returner)
> Discipline mismatch — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full document) for a GRAVEL athlete. Cat 5–1 is a USA Cycling road racing classification system with zero relevance to a gravel event or a 53-year-old masters returner whose goal is to finish. This is embarrassing and will confuse or alarm the customer.

### 15. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section listed in TOC is also mismatched — gravel-specific skills (loose surface cornering, descending on mixed terrain, tubeless repair, hydration pack use) should replace generic road skills content for a gravel discipline.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> Countdown says '58 days from today' but the plan_start_date is 2026-09-14 and race date is 2026-11-08 — that is 55 days, not 58. If 'today' is the generation date this number is auto-calculated and wrong, which will erode athlete trust immediately.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section header is visible in the table of contents. For a gravel event this should cover gravel-specific skills (loose surface cornering, off-camber descending, tire-pressure management, trail braking) — if the body of that section contains road-specific content (criterium positioning, bunch sprinting, etc.) it compounds the wrong-discipline problem.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> Taper Intensity flagged as 'WARN' by the automated gate. For a podium-chasing athlete at an A-race, taper intensity prescription is high-stakes. The guide text offers no specific taper intensity guidance beyond 'short, sharp efforts keep the engine awake,' which is insufficient to validate or dismiss the warning. This needs a coach review of the calendar data before sending.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> Table of Contents lists 'Road Skills' as a standalone section. While bike-handling content can be appropriate for gravel, a section titled 'Road Skills' without explicit gravel context (loose surface cornering, descending on gravel, rutted terrain) is methodology-mismatched and likely contains road-centric content given the other road-racing sections present.

### 20. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section is listed in the table of contents. A gran fondo is not a road race — there are no attack/cover/sprint dynamics. This content is wrong for the event and undermines credibility.

### 21. [major] ×1  (road/masters_returner)
> Taper Intensity is flagged WARN and TSS Progression is flagged WARN in preview checks. Neither issue is acknowledged or addressed anywhere in the visible guide text, leaving the athlete with a taper section that may be miscalibrated with no coaching context.

### 22. [major] ×1  (road/masters_returner)
> Off days listed as Friday, Monday, and Thursday — that is three off days in a 7-day week, leaving only 4 training days. Against a 9h/week target this is plausible, but the guide elsewhere says 'Your week has 4 training days, 2 of which are key sessions' which is consistent. However, having off days on Monday AND Thursday creates an awkward mid-week split that makes stacking a long ride Saturday + intervals sensibly very difficult — this should be explicitly justified for the athlete.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Off days are listed as 'Friday, Thursday' — the ordering is non-standard and potentially erroneous. More importantly, listing two named off days for a plan that claims 5 training days in a 7-day week should be 2 off days, but the names appear reversed/scrambled (Thursday comes before Friday chronologically). This needs verification against the actual calendar to ensure the week structure is coherent.

### 24. [major] ×1  (road/veteran_podium_chaser)
> The preview checks flagged WARN on Zone Distribution, TSS Progression, Taper Intensity, and FTP Test Frequency — none of these warnings are addressed or acknowledged anywhere in the visible guide text. A plan for a podium-chasing athlete with known taper-intensity and zone-distribution issues should either resolve them or explicitly explain the design rationale; sending a plan with silent pre-flight warnings is not acceptable.

### 25. [major] ×1  (mtb/weekend_warrior)
> Long ride duration described as '1.5–2.5 hours' in the Weekly Structure section, but the race is 78 miles with an estimated finish time of ~5.75 hours. The guide itself warns that longer rides are needed yet caps the described range far below what a gran fondo demands, which is contradictory and undersells the risk to the athlete.
