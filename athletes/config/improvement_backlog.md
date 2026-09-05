# Improvement backlog — 2026-09-05

**Quality 1.09** · avg coach 5.88/10 · contract pass 88% · load 13.88/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/time_crunched_parent, road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. That is USA Cycling road racing category content, entirely irrelevant to a gran fondo competitor whose goal is a podium finish at GFNY Cozumel. It signals to the athlete that this is a generic, poorly filtered template.

### 2. [critical] ×2  (gravel/ambitious_first_timer, road/weekend_warrior)
> Weekly Volume preview check is flagged WARN and Taper Intensity is flagged WARN, but the guide text never acknowledges or explains these warnings. A paying customer will receive a guide that implicitly has known unresolved issues — the coach must either fix the underlying numbers or explicitly note the trade-off in the plan brief.

### 3. [critical] ×2  (road/time_crunched_parent, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section listed in the Table of Contents is completely wrong for this event. L'Étape Ciudad de México is a mass-participation gran fondo — there are no USA Cycling or equivalent category upgrade pathways. This content belongs in a road racing plan, not a fondо plan, and will confuse and embarrass the business in front of a paying customer.

### 4. [critical] ×1  (road/weekend_warrior)
> Table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete is a 54-year-old weekend warrior targeting a gran fondo finish — Cat 5–1 is a USA Cycling road racing licensing/upgrade pathway that is completely irrelevant here and will confuse or mislead the athlete. It must be removed before sending.

### 5. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution check FAILED (per preview_checks) but the guide never acknowledges or corrects it. Sending a plan with a known failed zone-distribution check means the athlete will be training in the wrong zones — the single biggest risk to plan effectiveness, and one the guide itself identifies as catastrophic.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> The table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is doing a gravel gran fondo with a goal of 'finish' — road race category progression is completely irrelevant and will confuse or mislead her. This content is for a different discipline/persona template and was not stripped out.

### 7. [critical] ×1  (road/time_crunched_parent)
> plan_weeks (13) is greater than weeks_until_race (12), yet the plan_start_date is given as 2026-09-07 and race date is 2026-11-30. Counting from Sep 7 to Nov 30 is exactly 12 weeks and 2 days — a 13-week plan starting Sep 7 overshoots the race date by roughly one week. The plan_note explanation ('athlete simply starts later') does not apply here because 13 > 12; the plan cannot start later and still fit. Either the plan length or start date is wrong and must be reconciled before sending.

### 8. [critical] ×1  (road/weekend_warrior)
> Weight (157 lbs / 71.2 kg) and height (5'8") appear in the athlete profile but are NOT present in the plan JSON — these values were fabricated by the generator. Sending invented biometric data to a real customer is a serious trust and accuracy failure.

### 9. [critical] ×1  (gravel/masters_returner)
> Discipline mismatch — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections are listed in the Table of Contents and appear to be present in the guide. This is a GRAVEL gran fondo, not a road criterium or road race. Road race tactics (drafting dynamics, field sprint positioning, upgrade categories) are irrelevant and potentially misleading for a gravel event. These sections must be replaced with gravel-specific content (surface transitions, self-supported pacing, gravel cornering, nutrition carries, etc.).

### 10. [critical] ×1  (gravel/masters_returner)
> The 'Road Skills' section is flagged in the ToC for a gravel athlete — gravel-specific skills (off-camber corners, loose surface descending, tire pressure management) are what this athlete needs, not road-peloton skills. Sending road skills content to a gravel racer is a coaching credibility failure.

### 11. [major] ×2  (gravel/masters_returner, road/time_crunched_parent)
> Taper Intensity is flagged WARN in the preview checks and is never resolved or explained in the guide text provided. A known quality-gate warning must either be corrected in the plan or explicitly addressed with a coaching rationale before the document is sent to a customer.

### 12. [major] ×1  (road/weekend_warrior)
> Long ride duration range stated as '1.5–2.5 hours' in the Weekly Structure section. For a 71-mile gran fondo with an estimated ~4.5-hour finish time, peak long rides of only 2.5 hours would leave a significant durability gap. The guide itself later correctly urges 3–4 hour rides in the 'Biggest Opportunity' callout — the 1.5–2.5 h figure in the session-type description directly contradicts that good advice and should be updated to reflect the recommended ceiling.

### 13. [major] ×1  (road/weekend_warrior)
> 'Women-Specific Considerations' appears in the table of contents but is not present in the truncated guide body text provided for review. If this section is missing or is a stub, it is a broken promise to a female athlete who may specifically look for it — verify it is complete in the full document.

### 14. [major] ×1  (road/time_crunched_parent)
> Elevation is stated as '650 ft' for GFNY Cozumel 96 miles. The actual GFNY Cozumel course is essentially flat (Cozumel is a flat Caribbean island); 650 ft is suspiciously low but plausible — however if this figure came from the verified DB it should be flagged for confirmation, and the guide should not present it as authoritative without a source note, especially given the Status line already tells the athlete to 'confirm distance and elevation on the official race page.'

### 15. [major] ×1  (road/time_crunched_parent)
> The countdown '64 days from today' is a hard-coded static string. The plan start date is 2026-09-07 and race date is 2026-11-08, which is 62 days — not 64. This discrepancy will immediately undermine athlete trust and suggests the number was not dynamically calculated.

### 16. [major] ×1  (road/time_crunched_parent)
> The off-day list reads 'Thursday, Wednesday, Saturday' — listing days out of calendar order (Wednesday before Thursday) looks like a rendering or data-assembly bug. More importantly, Saturday is listed as an off day yet the plan also states 'Long rides: Sunday.' For a time-crunched athlete targeting a 96-mile race, losing Saturday as a potential longer-ride day needs explicit justification that is absent here.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks.' In a 9-week plan with one FTP test (confirmed by FTP Test Frequency: WARN), this claim is factually wrong — the zones would govern more or fewer than 6 weeks depending on when the test falls, and the hardcoded '6 weeks' appears to be a copy-paste artifact from a longer plan template.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> FTP Test Frequency is flagged WARN, meaning the plan likely has only one retest in 9 weeks (or placement is suboptimal), yet the guide gives no explanation or justification to the athlete. For an ambitious first-timer whose FTP may shift meaningfully over 9 weeks, this gap needs a coach note.

### 19. [major] ×1  (gravel/ambitious_first_timer)
> The 'YOUR WEEK, AT A GLANCE' section lists off days as 'Tuesday, Monday' — listing Tuesday before Monday is confusing and likely a templating error. More importantly, the guide elsewhere references 5 training days and 2 key sessions but the off-day count (2 days) should be cross-checked; with 11h/week and 5 training days the per-day average is 2.2h which is plausible, but the disordered day listing erodes trust in the document's accuracy.

### 20. [minor] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> The long-ride duration range cited in the Weekly Structure section ('3.2–5.3 hours') should be verified against the race's expected finish time (~4.6h). A long ride exceeding race duration (5.3h) is fine for a gran fondo prep but should be explicitly framed as intentional rather than appearing as a raw template number.

### 21. [major] ×1  (road/time_crunched_parent)
> The athlete's stated goal is 'podium.' For a mass-participation gran fondo with thousands of entrants this is almost certainly an age-group podium aspiration, yet the guide never acknowledges, contextualises, or sets realistic expectations around this goal. A coach would flag what 'podium' means in this event context and whether 6 h/week over 13 weeks is realistically aligned with that ambition — silence here reads as either blind validation or sloppy copy.

### 22. [major] ×1  (road/veteran_podium_chaser)
> The guide labels the athlete as 'Intermediate level' in the methodology rationale section, but the athlete has 18 years of riding experience and a 305W FTP — the persona is explicitly 'veteran podium chaser / Experienced racer.' Calling them Intermediate is factually wrong relative to their own submitted data and risks insulting a serious, paying athlete.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Three preview checks are flagged WARN (Weekly Volume, FTP Test Frequency, Taper Intensity) and none are explained or resolved in the guide text provided. For a 14h/week athlete targeting a podium, unresolved volume or taper warnings are not cosmetic — they represent potential training load errors that could compromise race-day readiness.

### 24. [major] ×1  (road/weekend_warrior)
> Preview check 'Taper Intensity' flagged WARN. A taper intensity problem in a 10-week plan with an A-race is a meaningful structural issue; the guide text says nothing to address it, and it cannot be passed over as cosmetic.

### 25. [major] ×1  (road/weekend_warrior)
> 'Road Race Strategy' and implied race-tactics content (referenced in ToC) is discipline-adjacent but potentially misleading for a gran fondo, which is a timed participation event, not a mass-start road race with tactics. Content should be gran-fondo/sportive specific (pacing, aid stations, climbing strategy) not criterium/peloton race strategy.
