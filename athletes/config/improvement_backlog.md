# Improvement backlog — 2026-09-16

**Quality 0.67** · avg coach 5.62/10 · contract pass 75% · load 13.62/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — wrong discipline entirely. This is a gravel gran fondo, not a criterium or road circuit race. Sending a gravel athlete a Cat 5-to-Cat 1 upgrade pathway is not only irrelevant, it signals the plan was generated from a road-racing template and will destroy credibility instantly.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents also lists 'Road Skills' as a standalone section. Gravel-specific skills (loose surface cornering, soft-surface braking, technical descending, tire pressure management) are what this athlete needs — generic road skills content is wrong for the discipline.

### 3. [critical] ×1  (road/masters_returner)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to FINISH a gran fondo — there is no category racing context whatsoever. This content is plainly copy-pasted from a road-racing template and is wrong for this athlete. It will confuse and undermine trust in the entire plan.

### 4. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content — the Table of Contents includes 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway.' This athlete is a GRAVEL racer with a goal of 'finish.' Road race tactics and a Cat 5-to-Cat 1 upgrade pathway are completely irrelevant and will confuse or embarrass the athlete. Gravel-specific content (navigation, terrain management, gravel cornering, self-sufficiency) is absent.

### 5. [critical] ×1  (gravel/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the guide contents. This is a road racing/USA Cycling licensing concept with zero relevance to a masters gravel athlete whose only goal is to finish a gran fondo. It signals the template was not properly filtered for discipline and goal type — a serious credibility killer.

### 6. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content: the ToC and body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is racing GRAVEL (Atlas Gran Fondo). Cat 5-to-Cat 1 is a road-racing licensing construct with zero relevance to a gravel gran fondo. This is the most embarrassing possible content mismatch for a paying customer.

### 7. [critical] ×1  (gravel/masters_returner)
> Weekly Volume check FAILED per preview_checks. The guide claims '9 hours/week' throughout but the automated gate flagged volume as non-conformant. If prescribed weekly hours don't actually sum to ~9 h, every TSS, load, and long-ride duration reference in the plan is untrustworthy. Cannot send until resolved.

### 8. [critical] ×1  (gravel/masters_returner)
> Zone Distribution FAILED per preview_checks. A Pyramidal plan lives or dies on ~75% Z1-2 / ~20% Z3 / ~5% Z4+. If the zone split is wrong, the core methodology promise made to the athlete is broken.

### 9. [critical] ×1  (road/weekend_warrior)
> Table of contents and apparent body section include 'Category 5 to Category 1 Pathway' — this is a USA Cycling road racing category upgrade pathway, which is completely irrelevant to a gran fondo finisher goal. A paying customer whose goal is 'finish' will be confused or misled; it also signals the wrong discipline context (race category competition vs. mass-participation event).

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — athlete is MTB but the guide includes 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' section. These sections are entirely wrong for mountain biking and will confuse or mislead the athlete.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Equipment checklist specifies 'road bike, in good working order' as the mandatory training bike. The athlete's discipline is MTB; prescribing a road bike is flatly incorrect and embarrassing.

### 12. [major] ×2  (gravel/veteran_podium_chaser, road/weekend_warrior)
> Long ride duration range is stated as '2.2-3.8 hours' in the Weekly Structure section — the upper bound of 3.8 hours is plausible for a 7 h/week athlete targeting a ~4.7-hour race, but the lower bound of 2.2 hours in early base feels low for race preparation context; a brief note explaining the progression from that floor would prevent athlete confusion.

### 13. [major] ×1  (road/weekend_warrior)
> The plan header states 'plan_weeks is the plan LENGTH; the plan ends on race day' — but the plan start date is 2026-09-21 and the race is 2026-11-30, which is exactly 10 weeks and 2 days, not 11 full weeks. If the calendar was generated as 11 calendar weeks from Sept 21 it ends Dec 6, overshooting the race by 6 days. The guide text needs to confirm the final week terminates on Nov 30, or the start date should be Sept 28 for a clean 11-week block ending on race day.

### 14. [major] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is included in the table of contents and apparently in the body. This athlete's goal is simply to FINISH a gran fondo — a category upgrade racing pathway is completely irrelevant to a weekend warrior with a finish goal and could confuse or mislead them about what this plan is for.

### 15. [major] ×1  (road/masters_returner)
> The preview check flagged 'Taper Intensity: WARN' and this was never resolved or explained in the guide. For a 63-year-old masters returner targeting an A-race, taper intensity is a patient-safety and performance concern, not a cosmetic flag. Either the taper sessions must be corrected or the plan must explicitly address why the taper is structured as it is. Sending a plan with an unresolved WARN on taper intensity is not acceptable.

### 16. [major] ×1  (road/masters_returner)
> The off-days listed in the 'At a Glance' box are Saturday and Sunday, but the long ride day is stated as Thursday. For a 7 h/week Time-Crunched athlete, having the long ride mid-week (Thursday) while both weekend days are off is an unusual and unexplained structure that conflicts with how most athletes' schedules work and with standard Time-Crunched conventions. No justification is offered, and it risks athlete non-compliance or confusion.

### 17. [major] ×1  (gravel/masters_returner)
> Zone distribution check flagged FAIL and Weekly Volume flagged WARN in the preview checks, yet the guide text contains no acknowledgment or mitigation of these issues. A coach sending a plan with known failed checks should at minimum address them — silently ignoring them is not acceptable.

### 18. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency flagged WARN. The guide mentions only a single Week 1 HR field test as the anchor but provides no guidance on whether or when a re-test is planned across the 9-week block. For a masters returner with unknown FTP, a mid-plan retest point (e.g., after Base phase) is standard practice and its absence or non-acknowledgment is a gap.

### 19. [major] ×1  (gravel/masters_returner)
> The Equipment Checklist lists 'road bike, in good working order' as the mandatory bike under MANDATORY. The athlete is preparing for a gravel race (Atlas Gran Fondo). A gravel bike with appropriate tires is the correct equipment call; defaulting to 'road bike' is factually wrong for the discipline and could lead to a dangerous equipment mismatch on gravel terrain.

### 20. [major] ×1  (gravel/masters_returner)
> Off days listed as Saturday, Wednesday, AND Sunday (three days off) for an athlete with a 9 h/week target. Three full off days leaves only four training days, which is plausible but the guide simultaneously states '4 training days, 2 of which are key sessions' — that arithmetic is fine, but Saturday as an off day conflicts with a gravel gran fondo community where Saturday long rides are the norm, and more importantly the long-ride day is listed as Friday. No explanation is given for this unusual structure, and it may confuse the athlete.

### 21. [major] ×1  (gravel/masters_returner)
> TSS Progression flagged WARN and FTP Test Frequency flagged WARN by automated checks. With no FTP anchor and a masters returner, a single Week 1 HR/RPE test may be insufficient if the plan runs 9 weeks — the guide should address mid-plan re-testing or explicitly justify why one test suffices.

### 22. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section listed in ToC is ambiguous — if it contains road-specific cornering, peloton positioning, or criterium tactics rather than gravel-specific skills (loose surface descending, tire pressure management, navigation), it is wrong discipline content.

### 23. [major] ×1  (gravel/masters_returner)
> Athlete weight (141 lbs / 63.9 kg) and height (5'6") appear in the guide but are NOT present in the athlete JSON — the source data shows only age, sex, hours_target, and null FTP. These figures were either fabricated by the generator or pulled from a profile not surfaced here. Presenting made-up biometrics to a paying customer is a trust-breaking error.

### 24. [major] ×1  (road/weekend_warrior)
> 'Road Race Strategy' is listed as a standalone section in the TOC. A UCI Gran Fondo is not a road race in the competitive sense — it is a mass-participation event. Strategy content should be gran-fondo-specific (pacing, fueling stops, group dynamics in a non-draft or controlled-draft format) not road-race tactics. This is a content/discipline mismatch for the athlete's event and goal.

### 25. [major] ×1  (road/weekend_warrior)
> Off days listed as Saturday, Tuesday, and Thursday — with a long ride on Sunday and intervals mid-week — leaves only Monday, Wednesday, and Friday as training days (3 days). The plan claims '4 training days, 3 of which are key sessions' in the Weekly Structure section. That is internally contradictory: 3 off days + 4 training days = 7 days, which is correct mathematically, but the listed off days (Sat, Tue, Thu) plus long ride (Sun) leave only Mon/Wed/Fri as the remaining three days, not four. The count needs reconciliation.
