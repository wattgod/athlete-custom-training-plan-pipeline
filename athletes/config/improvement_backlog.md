# Improvement backlog — 2026-09-01

**Quality 0.05** · avg coach 5.5/10 · contract pass 75% · load 14.88/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/time_crunched_parent, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' is listed as a content section in the Table of Contents and presumably appears in the full guide. This is USA Cycling road-racing category content that is entirely irrelevant to a time-crunched parent targeting a mass-participation century event (El Tour de Tucson is a gran fondo, not a USAC category race). It signals the guide was not properly filtered for this athlete's profile and will undermine trust.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Wrong discipline content: The table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' — none of which belong in an MTB gran fondo plan. An MTB athlete needs trail/technical skills, not road-racing tactics or USA Cycling road upgrade criteria. This is the most embarrassing possible error to send to a paying customer.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Race countdown math is wrong: The plan states '68 days from today' but the plan start date is 2026-09-07 and the race is 2026-11-08, which is 62 days — not 68. The number '68' appears to have been copied from the race distance (68 miles), which is a dangerous data-merge bug that erodes confidence in all other numbers.

### 4. [critical] ×1  (road/time_crunched_parent)
> Off-day list is internally contradictory: the guide states 'Off days: Tuesday, Saturday, Wednesday' — that is three off days, which contradicts the '4 training days' stated in the same section. More critically, Saturday is listed as an off day but the plan also states 'Long rides: Sunday,' which is fine — however listing Saturday as off while the athlete likely needs it for occasional extended rides, and listing three separate off days for a 5 h/week athlete who only has 4 training days, suggests the list was generated incorrectly. At minimum, listing Saturday as an off day will confuse any athlete who sees a long ride option there.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is MTB, but the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section — road racing categories are irrelevant and confusing for an MTB rider targeting GFNY Miami. MTB-specific skills (technical descending, trail braking, body position) are absent.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution check is flagged FAIL in the automated preview, yet the guide text contains no acknowledgment, correction, or explanation. Sending a plan with a known FAIL on zone distribution — the core methodology metric for a Pyramidal plan — is not acceptable.

### 7. [critical] ×1  (gravel/veteran_podium_chaser)
> Countdown says '68 days from today' but the plan start date is 2026-09-07 and race date is 2026-11-08 — that is 62 days from plan start, not 68. More importantly, the system date at generation is unknown, so a hardcoded '68 days' is almost certainly wrong for whenever the athlete reads this. A wrong countdown directly undermines the taper warning the document itself highlights.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> The guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This is a GRAVEL gran fondo — road race categorization (Cat 5–Cat 1) is a USA Cycling road licensing concept that is entirely irrelevant and potentially confusing for a gravel event, especially a UCI Gran Fondo in Brazil. This is wrong-discipline content and is embarrassing.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> The guide also lists 'Road Skills' in the table of contents. For a gravel race, this should be gravel-specific skills (loose surface cornering, gravel descending, mud/sand handling). Sending road skills content to a gravel racer is a discipline mismatch.

### 10. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is a USA Cycling road racing licensing progression — it is completely irrelevant and misleading for a gran fondo athlete whose stated goal is simply to finish. It implies competitive category racing, which is a different discipline context entirely and will confuse or mislead the customer.

### 11. [critical] ×1  (road/masters_returner)
> The race countdown reads '68 days from today' — but the plan start date is 2026-09-07 and race date is 2026-11-08, which is 62 days. The number 68 likely leaked from the race distance (68 miles) into the countdown field. This is a factual error that will immediately undermine customer trust.

### 12. [minor] ×3  (gravel/veteran_podium_chaser, mtb/ambitious_first_timer, road/masters_returner)
> The long-ride duration range cited in the guide ('3.1–5.2 hours') should be cross-checked against the 11 h/week target and the estimated race duration of ~4.6 hours; the upper bound of 5.2 h on a single day within an 11 h week leaves very little room for other sessions and may be unrealistic.

### 13. [major] ×1  (gravel/time_crunched_parent)
> The guide includes a 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' section (listed in the Table of Contents). This is a gravel gran fondo, not a road criterium or road race with USA Cycling categories. Cat 5–Cat 1 licensing pathways are irrelevant and potentially confusing or embarrassing for a gravel athlete — this content belongs in a road-racing plan and should be removed or replaced with gravel-specific race strategy.

### 14. [major] ×1  (gravel/time_crunched_parent)
> The equipment checklist under MANDATORY lists 'road bike, in good working order.' The athlete's discipline is gravel — the checklist should specify a gravel bike (or at minimum 'gravel or road bike suited for gravel terrain'). Sending a gravel athlete a plan that tells her to bring a road bike is an embarrassing discipline mismatch.

### 15. [major] ×1  (mtb/weekend_warrior)
> Zone distribution preview check FAILED but the guide text makes no acknowledgment of this. A failed zone distribution check means the prescribed time-in-zone may not match the stated '~70% easy' Time-Crunched split — yet the guide confidently asserts that distribution without qualification. Either the plan or the text needs to be corrected before sending.

### 16. [major] ×1  (mtb/weekend_warrior)
> TSS Progression flagged WARN in preview checks: no mention or mitigation appears in the guide. For a weekend warrior with high life stress this is a meaningful risk that a real coach would address explicitly.

### 17. [major] ×1  (mtb/weekend_warrior)
> Taper Intensity flagged WARN in preview checks: the guide's taper section gives only generic advice and does not address whatever specific issue the automated check detected. This should be reviewed and either fixed in the calendar or explained in the text.

### 18. [major] ×1  (mtb/weekend_warrior)
> The long-ride duration range stated in the guide ('2.1–3.5 hours') is inconsistently wide for a 6h/week athlete — a 3.5h long ride would consume nearly 60% of the weekly budget in one session, leaving almost nothing for interval work. This should be tightened or explained.

### 19. [major] ×1  (road/time_crunched_parent)
> Goal listed as 'podium' for El Tour de Tucson 102 miles. El Tour de Tucson is a large mass-participation gran fondo (thousands of riders) — a podium in an open GF with this athlete's profile (155 W FTP, 5 h/week) is not a realistic coaching target. The guide never addresses or contextualises this goal; a real coach would either reframe it (e.g., age-group podium, personal best, strong finish) or flag it. Leaving 'Compete' as the only elaboration under 'Success looks like' while the race fact sheet says 'podium' is an unresolved contradiction that will confuse the athlete.

### 20. [major] ×1  (road/time_crunched_parent)
> Zone distribution preview check flagged WARN but the guide text makes no mention of this warning or any corrective guidance. A paying athlete receiving a plan with a known zone distribution issue deserves at least an acknowledgment or explanation.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> Weekly Volume is WARN and Taper Intensity is WARN in the automated preview, but the guide body does not address or compensate for either flag. A coach reviewing this would expect some narrative adjustment or explicit note to the athlete.

### 22. [major] ×1  (mtb/ambitious_first_timer)
> FTP test section states the result 'sets ALL your training zones for the next 6 weeks' — but this is a 9-week plan. The number '6 weeks' is arbitrary boilerplate that contradicts the plan length and could cause the athlete to stop updating zones at the wrong time.

### 23. [major] ×1  (mtb/ambitious_first_timer)
> Zone 1 row in the zone chart is missing the % FTP and % LTHR columns — they are blank. Every other zone has these values. This looks like a template rendering failure and will confuse the athlete.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> The 'Road Skills' and 'Road Race Strategy' sections (visible in the table of contents) are discipline-wrong content for an MTB athlete. Even if GFNY Miami is a paved gran fondo, the athlete's discipline is listed as MTB and the plan should be built and labeled accordingly, or the discipline conflict must be explicitly reconciled.

### 25. [major] ×1  (road/weekend_warrior)
> Three automated pre-flight checks came back WARN (TSS Progression, FTP Test Frequency, Taper Intensity) and none are addressed or explained in the guide text. At minimum the coach QA layer must resolve whether these are acceptable deviations or genuine errors before sending — particularly Taper Intensity, which directly affects race-day freshness for the A-priority event.
