# Improvement backlog — 2026-07-26

**Quality -0.48** · avg coach 5.62/10 · contract pass 50% · load 15.25/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Zone 2 lower bound is listed as '101W' but 56% of FTP 182W = 101.9W — that rounds correctly. However, Zone 1 upper bound is shown as '100W' and Zone 2 lower as '101W', which implies a 1-watt gap that is fine arithmetically, but the Zone 2 label reads '101-136W' while 75% of 182W = 136.5W — acceptable rounding. The real critical error: the profile box displays 'FTP: 172 lbs Weight' line directly above '182W FTP' — the layout places '172' immediately after '53 Age', making it visually read as if FTP = 172W, when the athlete's actual FTP is 182W. Any athlete scanning the profile box could misread their FTP and train in wrong zones for 8 weeks.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> The plan labels the athlete as 'Intermediate level' in the methodology rationale ('15 years of cycling experience at Intermediate level'), yet the persona is 'veteran_podium_chaser' — an experienced racer. This is a factual contradiction that will erode athlete trust immediately.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> A 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' section are listed in the Table of Contents. This athlete is racing gravel, not a UCI road category event. Road-racing category progression content is wrong-discipline filler that has no place in a gravel plan.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> The preview check flags Zone Distribution as FAIL, yet the guide text shows no acknowledgment, correction, or coach note about this. Sending a plan with a known failed quality check — especially one about the core training stimulus distribution — is not acceptable.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the guide includes a 'Gravel Skills' section (visible in the table of contents) for an athlete racing a mountain bike event. MTB-specific skills (trail braking, switchback technique, technical climbing, body position on roots/rocks) are what this athlete needs — gravel skills content is wrong-discipline filler that would embarrass the business and give the athlete irrelevant advice.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: The guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This athlete is a gravel racer targeting a finish at L'Etape Poland — road race categories (Cat 5–1) are a USA Cycling / British Cycling road racing construct that is completely irrelevant and potentially confusing for a gravel event. This is the most embarrassing error in the document.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: The 'Road Skills' section (listed in the table of contents) is inappropriate for a gravel-specific plan. The athlete needs gravel-specific skills content — loose surface cornering, technical descending on mixed terrain, tyre pressure management, and mechanical self-sufficiency — not a road skills module.

### 8. [critical] ×1  (gravel/masters_returner)
> Section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the table of contents for a GRAVEL gran fondo athlete. Cat 5-to-Cat 1 is a USA Cycling road racing licensing framework — it is completely irrelevant to a gravel event and will confuse or embarrass the customer.

### 9. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section heading in the table of contents is discipline-ambiguous at best, but paired with 'Road Race Strategy' it strongly implies road-racing content was copy-pasted into a gravel plan. Gran Fondo Eilat is a gravel event; cornering, descending, and skills content must be gravel-specific (loose surface, variable terrain, navigation) — not road criterium or road race tactics.

### 10. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' is listed as a table-of-contents section and appears in the guide. This is a USA Cycling road-racing category ladder concept that has zero relevance to a granfondo athlete whose goal is simply to 'finish strong.' It implies competitive category upgrades, which will confuse or mislead this customer and looks like copied boilerplate from a different plan template.

### 11. [critical] ×1  (road/weekend_warrior)
> Zone Distribution check FAILED (per preview_checks). The guide's written explanation claims 'roughly 70% of riding stays genuinely easy' as the Time-Crunched distribution, but the actual weekly workouts (not shown in full) apparently violate this. A zone distribution failure means the athlete could be prescribed too much Z3/Z4 relative to the stated methodology, directly undermining the 'no junk miles' promise made in the text.

### 12. [critical] ×1  (road/masters_returner)
> A 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full document. This athlete is a masters gran fondo participant whose stated goal is 'Finish' — not a road racer pursuing USAC upgrade points. This section is flatly wrong for the discipline and persona and is embarrassing content that must be removed.

### 13. [critical] ×1  (road/masters_returner)
> Zone Distribution automated check is FAIL. The guide claims '~65% of riding stays genuinely easy' but the system found the actual prescribed distribution does not match. If the written methodology promise contradicts the actual workout zones, the plan is internally inconsistent and cannot be sent.

### 14. [major] ×2  (gravel/masters_returner, road/masters_returner)
> Long ride duration range is given as '2.7–4.5 hours' in the Weekly Structure section. For an 85-mile gravel gran fondo with an implied finish time around 5–6 hours (consistent with the fueling data: 5.7 h duration), a peak long ride of only 4.5 hours is on the low end and the guide makes no acknowledgement of this gap or why it is sufficient. This risks leaving the athlete undertrained for event duration.

### 15. [major] ×2  (road/masters_returner, road/weekend_warrior)
> 'Road Race Strategy' is listed as a table-of-contents section. A granfondo is a non-competitive mass-participation ride, not a road race. Tactics like race strategy, positioning, and attacking are irrelevant and could actively mislead the athlete about the nature of his event.

### 16. [major] ×1  (gravel/masters_returner)
> TSS Progression check returned WARN in the automated preview but no explanation or mitigation is surfaced anywhere in the guide text. A coach-authored plan should acknowledge or address a flagged progression anomaly, even briefly — its silent omission is a QA gap.

### 17. [major] ×1  (gravel/masters_returner)
> The guide states 'Long rides: 2.1–3.5 hours' in the Weekly Structure section. For a 7h/week athlete targeting a ~6-hour gravel event, a 3.5-hour ceiling on the long ride is on the low side and should be explicitly justified (e.g., due to the masters recovery constraint or weekly hour cap), otherwise it creates doubt about race-readiness.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> The Sparkassen Münsterland Giro is a well-known professional one-day road race in Münster, Germany. The verified race DB lists it here as a 78-mile *gravel* event. If this is genuinely a gravel variant/edition that exists in the DB, the guide should clarify this explicitly, because the race's strong public identity as a pro road race will confuse the athlete and undermine credibility.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> Long ride duration is described as '2.6–4.3 hours' in the Weekly Structure section. The fueling data puts expected race duration at 3.7 h for 78 miles, so a peak long ride of 4.3 h is plausible, but the low end of 2.6 h in Week 1 should be contextualised relative to the athlete's current fitness — as written it reads like a boilerplate range pasted in without athlete-specific grounding.

### 20. [major] ×1  (mtb/ambitious_first_timer)
> FTP-known contradiction: the plan JSON states ftp_known=false, yet the guide confidently displays '204W FTP' in the athlete profile header and uses it to build all training zones without any caveat that this is an estimated value. Either the number should be flagged as an estimate (with an early FTP test prescribed) or the ftp_known flag is wrong — as written, the discrepancy will confuse the athlete and undermine trust in the zones.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> Experience-level label inconsistency: the persona is 'ambitious_first_timer' and the athlete has 1 year of riding, yet the guide body refers to the athlete as 'Intermediate level.' A first-timer with 1 year of experience is a beginner; labelling them Intermediate mis-sets expectations, could push them toward harder workouts than appropriate, and contradicts the persona the business sold them on.

### 22. [major] ×1  (gravel/ambitious_first_timer)
> Zone Distribution automated check is marked FAIL in the preview_checks JSON, yet the guide is being prepared for delivery. A pyramidal plan must have ~75% Z1-Z2, ~15-20% Z3-tempo, and only ~5-10% Z4+. A FAIL here means the prescribed workout distribution does not match the stated methodology, which is a core coaching error that undermines the entire plan rationale.

### 23. [major] ×1  (gravel/ambitious_first_timer)
> The long ride duration range cited in the Weekly Structure section is '2.6-4.3 hours.' The upper bound of 4.3 hours exceeds the race's estimated completion time of ~3.7 hours and also conflicts with the Per-Day Duration Caps check (which passed). While the cap check passed, quoting 4.3h to a first-timer whose race will take ~3.7h is misleading and inconsistent with the Long Ride vs Race Duration PASS — the numbers should align visibly in the text.

### 24. [major] ×1  (gravel/masters_returner)
> The Zone Distribution preview check returned WARN but no explanation or caveat is surfaced anywhere in the guide text provided. For a G Spot methodology plan the zone distribution is the core promise; a silent warn with no coach commentary leaves a QA gap that could mean the prescribed distribution doesn't actually match the methodology's stated ~65% easy split.

### 25. [major] ×1  (road/weekend_warrior)
> Long ride duration range cited as '2.1–3.5 hours.' For a 68.8-mile granfondo with 7,451 ft of climbing, realistic race time for this athlete (205W FTP, finish goal) is likely 5–6+ hours. A peak long ride of only 3.5 hours is significantly under-preparing him for time-on-bike and fueling demands, and contradicts the fueling section's own 5.0 h race duration assumption.
