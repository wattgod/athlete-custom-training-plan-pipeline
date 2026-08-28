# Improvement backlog — 2026-08-28

**Quality 0.14** · avg coach 5.88/10 · contract pass 88% · load 16.25/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/veteran_podium_chaser, road/weekend_warrior)
> "Category 5 to Category 1 Pathway" appears as a section in the Table of Contents. This athlete is described as an experienced racer chasing a podium — not a Cat 5 beginner seeking upgrade points. A Cat 1 upgrade pathway section is irrelevant at best and actively misleading for a veteran podium chaser. It also raises the question of whether content from a beginner template was inadvertently merged into this plan.

### 2. [critical] ×1  (gravel/masters_returner)
> Road-racing 'Category 5 to Category 1 Pathway' section appears in the table of contents and (implied) body of a gravel plan. This is entirely wrong-discipline content that would confuse and embarrass — GFNY Cozumel is a gravel gran fondo, not a USA Cycling road criterium/road race category ladder event.

### 3. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' section is listed in the table of contents. This athlete is preparing for a gravel gran fondo — gravel-specific pacing, terrain management, and self-supported strategy content should replace road race tactics.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the Contents list includes a 'Gravel Skills' section, and the Equipment Checklist recommends a 'gravel or similar' bike. This is an MTB race (Iceman Cometh is a point-to-point singletrack/two-track MTB event). Gravel skills content is irrelevant and potentially harmful advice (e.g., gravel cornering vs. MTB technical descending); the bike recommendation should specify a hardtail or full-suspension mountain bike with appropriate tires.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED in automated preview. The guide text is not transparent about this failure, and no corrective note appears. Sending a plan with a known zone distribution flaw — especially for a pyramidal methodology where zone balance is the entire premise — is indefensible without a manual review and fix of the underlying weekly workouts.

### 6. [critical] ×1  (road/weekend_warrior)
> Off-day list is internally inconsistent and almost certainly wrong: 'Monday, Friday, Tuesday' lists THREE off days for a 4-hour/week athlete who should have only 3-4 training days — but listing two non-consecutive weekdays plus Friday as 'off' is an odd, unexplained pattern that reads like a generation artifact. More importantly, Tuesday is listed AFTER Friday, suggesting a copy-paste or ordering error. This is the first thing an athlete reads about their weekly structure and it will cause immediate confusion.

### 7. [critical] ×1  (road/weekend_warrior)
> Long ride duration of 1.5 hours is flagged as 'shorter than ideal' while simultaneously recommending 'a single 3-4 hour ride' — but the athlete's TOTAL weekly budget is 4 hours. A 3-4 hour single ride is impossible within a 4-hour weekly cap without eliminating every other session. This contradicts the athlete's own stated constraint and will erode trust in the entire plan.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents for a GRAVEL gran fondo athlete. Road race tactics (field positioning, criterium-style category upgrades) are irrelevant and wrong-discipline content for a gravel finisher. This is embarrassing and will confuse the athlete.

### 9. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section is listed (TOC) for a gravel discipline — should be Gravel-specific skills (loose surface cornering, terrain reading, gravel descending). Sending road-specific skills content to a gravel racer is a direct content mismatch.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> Section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the table of contents and plan body. This athlete is racing GFNY Miami, a gravel gran fondo — not a criterium or road race. Road racing tactics (pack dynamics, Cat upgrade pathway) are irrelevant and confusing; they signal the plan was assembled from a road-racing template without proper discipline filtering.

### 11. [critical] ×1  (gravel/time_crunched_parent)
> A 'Road Skills' section is listed in the table of contents in place of gravel-specific skills (e.g., loose-surface cornering, gravel descending, rough terrain bike handling). For a gravel discipline this is a meaningful content gap and a discipline mismatch that a paying customer will immediately notice.

### 12. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and apparently appears in the full document. This is entirely irrelevant — the athlete is a time-crunched 47-year-old parent targeting a gran fondo with a goal of 'finish,' not a USA Cycling cat upgrade pathway. It is the wrong discipline context (cat racing vs. open granfondo), wrong goal, and will confuse or alienate the customer.

### 13. [critical] ×1  (mtb/ambitious_first_timer)
> 'Gravel Skills' appears as a named section in the Table of Contents for an MTB athlete. This is the wrong discipline entirely — gravel cornering/handling drills are not MTB trail skills. This would immediately undermine athlete confidence and is embarrassing for the business.

### 14. [major] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> Long-ride duration range stated as '1.5–2.2 hours' peak, which is grossly undersized for a 96-mile gravel race projected at ~6 hours. Even under Time-Crunched methodology the guide itself acknowledges a 3–4 hour ride is worth more than two 1.5-hour rides, yet the prescribed peak cap contradicts that advice within the same document.

### 15. [major] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> Taper Intensity flagged WARN by the automated preview check but no corrective action is visible in the guide text. A masters athlete (52 yo) needs correct taper intensity guidance — sending with a known unresolved warning is unacceptable.

### 16. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section in the table of contents is ambiguous/misplaced — for a gravel event this should explicitly cover gravel-specific skills (loose surface cornering, technical descending, flat repair, hydration pack use) not generic road-racing skills.

### 17. [major] ×1  (road/veteran_podium_chaser)
> The persona label and JSON say 'Experienced racer / veteran podium chaser' with 14 years riding, but the guide refers to their experience level as 'Intermediate level' in the methodology rationale section ('14 years of cycling experience at Intermediate level'). 14-year veteran is not Intermediate — this label contradiction undermines athlete confidence and coach credibility.

### 18. [major] ×1  (mtb/weekend_warrior)
> Weight and height appear in the guide (133 lbs / 5'2") but the athlete JSON contains no weight or height fields. These values were either hallucinated or injected from an unknown source and cannot be verified. Using fabricated biometric data in a paid plan is a trust and liability risk.

### 19. [major] ×1  (mtb/weekend_warrior)
> Taper Intensity flagged WARN in preview but the guide's Taper section gives only generic language ('short, sharp efforts keep the engine awake') with no acknowledgment of any concern. If the automated check flagged this, the guide should either resolve the issue in the workout calendar or add a coach note explaining the taper intensity rationale.

### 20. [major] ×1  (mtb/weekend_warrior)
> Weekly Volume flagged WARN in preview. The guide claims 4 training days per week for a 7h/week athlete, but no sanity-check note or caveat appears. For a 10-week MTB plan peaking near race week, volume distribution should be explicitly justified or corrected — not silently flagged and shipped.

### 21. [major] ×1  (road/weekend_warrior)
> Fueling recommendation of 57 g carbs/hour appears in the plan JSON but the estimated race duration is ~2.84 hours (plausible for 44 miles). The guide does not surface or contextualize this number in the visible nutrition section — leaving the athlete without a concrete race-day carbohydrate target despite the data being available.

### 22. [major] ×1  (road/weekend_warrior)
> The taper section states 'You cannot gain fitness now — you can only show up fresh or show up tired.' While directionally correct, the plan's own FTP Test Frequency check flagged WARN, and the taper warning is overstated for a finish-goal weekend warrior — language this absolute is more appropriate for a competitive athlete and may cause the athlete to panic-rest and under-prepare mentally.

### 23. [major] ×1  (road/weekend_warrior)
> The 'Road Race Strategy' and 'Road Skills' sections are listed in the table of contents. The Cycling Shimanami is a point-to-point sportive/gran fondo across the Nishiseto Expressway island-hopping bridges — it is not a road race with tactics, pack dynamics, or category racing. Including road race strategy content (and implicitly, content like attacking, positioning in a peloton) is wrong for this event and persona.

### 24. [major] ×1  (gravel/ambitious_first_timer)
> Athlete profile says '1 Years Riding' but is simultaneously labeled 'Intermediate level.' A 1-year rider is a beginner, not intermediate. This contradiction could lead to under-recovery or unrealistic self-assessment and undermines trust in the auto-generation system.

### 25. [major] ×1  (gravel/ambitious_first_timer)
> The Zone Distribution and Taper Intensity checks both flagged WARN in the preview and are unresolved. No explanation or coach note is provided to the athlete about why these flagged — they either need to be fixed or acknowledged with a rationale in the guide.
