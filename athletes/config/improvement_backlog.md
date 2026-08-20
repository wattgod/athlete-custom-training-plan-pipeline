# Improvement backlog — 2026-08-20

**Quality 2.17** · avg coach 6.12/10 · contract pass 100% · load 12.38/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section appears in the Table of Contents and presumably in the full document. This is a USA Cycling road racing category progression framework — it is completely irrelevant and potentially confusing for a gran fondo athlete whose stated goal is simply to finish. A masters returner targeting a mass-participation event does not race in categories; this section likely contains content written for a different persona/discipline and was not scrubbed before assembly.

### 2. [critical] ×1  (gravel/masters_returner)
> Table of contents and apparent body content includes a 'Category 5 to Category 1 Pathway' section — this is a road racing licensing/category construct that has no relevance to a gravel athlete with a finish goal. It is wrong discipline content and would confuse or mislead the customer.

### 3. [critical] ×1  (road/weekend_warrior)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to finish a 68-mile gran fondo. A racing-licence upgrade pathway is irrelevant, potentially confusing, and embarrassing — it signals the wrong plan was partially merged or a generic template was not properly stripped.

### 4. [critical] ×1  (gravel/weekend_warrior)
> Wrong-discipline content included: a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section appear in the table of contents (and presumably in the full document). This is a gravel gran fondo plan — category upgrade pathways and road-race tactics are irrelevant and undermine credibility with a paying athlete.

### 5. [critical] ×1  (gravel/weekend_warrior)
> Long ride peak duration stated as only 1.5 hours against a ~4.6-hour race. The plan itself flags this as a gap, but the prescribed ceiling is never corrected upward. For a 'finish strong' goal at 68 miles, sending a plan with a 1.5-hour long-ride cap — without a concrete alternative prescription — is a coaching failure, not just a caveat.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — section headers 'Road Skills' and 'Road Race Strategy' appear in the table of contents for an MTB athlete. Gran Fondo Guadeloupe is the target event, but nothing in the plan addresses MTB-specific skills (technical descending, trail braking, body position, singletrack cornering). Sending road race strategy content to an MTB rider is a clear template error that undermines trust.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> 'Category 5 to Category 1 Pathway' section is road-racing licence progression content (USA Cycling or equivalent). It is completely irrelevant to a recreational MTB gran fondo first-timer whose sole goal is to finish. This content is copy-pasted from a road racing template and should not exist here.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Equipment checklist mandates a 'road bike' as the mandatory item for an MTB plan. An MTB athlete preparing for Gran Fondo Guadeloupe (a course with 9,462 ft of elevation in Guadeloupe's terrain) needs MTB-specific equipment guidance (mountain bike, MTB helmet, tubeless setup, dropper post, etc.). Telling them to race on a road bike could be dangerous.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> "Road Race Strategy" and "Category 5 to Category 1 Pathway" sections are included in the table of contents (and presumably in the full guide body). This is a GRAVEL event — road racing category progression (Cat 5→1) is a USA Cycling road-license concept with zero relevance to a gravel finisher goal. Sending this to a gravel athlete is both confusing and unprofessional.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> "Road Skills" section header also appears in the TOC. Gravel-specific skills (loose surface cornering, rough terrain descending, gravel-specific bike handling) are what this athlete needs. Generic road skills content is wrong-discipline filler.

### 11. [major] ×2  (gravel/masters_returner, gravel/time_crunched_parent)
> Weight (187 lbs / 84.8 kg) and height (5'6") appear in the athlete profile card but are absent from the athlete JSON supplied to the generator. These numbers are either fabricated or pulled from an undisclosed source; if wrong they undermine all per-kg nutrition prescriptions and erode trust.

### 12. [major] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> FTP Test Frequency flagged WARN in the preview checks, but no explanation or mitigation is visible in the truncated guide text. If the plan contains only one FTP test across 8 weeks for a 290W athlete, that may be acceptable, but the guide should acknowledge it rather than leaving the WARN unaddressed.

### 13. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' is listed as a section in the TOC. Gran Fondo Eilat is a non-drafting or semi-drafting mass-participation event, not a road race. Tactical content about attacking, sitting in a peloton, or racing strategy is mismatched to a goal=finish gran fondo athlete and could actively mislead him into burning matches unnecessarily.

### 14. [major] ×1  (gravel/masters_returner)
> The 'Weekly Volume: WARN' preview check is unresolved. The guide never acknowledges or explains to the athlete why volume may be flagged (e.g., weeks that exceed the 9 h target or fall short of useful minimums). A paying customer deserves either a corrected plan or a transparent note.

### 15. [major] ×1  (road/weekend_warrior)
> The guide explicitly warns that long rides are capped at 1.5 hours yet the race is projected at ~4.7 hours — a 3:1 gap. The guide acknowledges this as 'YOUR BIGGEST OPPORTUNITY' but then only suggests optional extra rides rather than structuring them into the plan. For a 5 h/week athlete targeting a finish goal, at least one 3-hour ride should be a plan requirement, not a suggestion, especially since the automated preview check 'Long Ride vs Race Duration' reportedly passed — that check result appears inconsistent with what the guide text reveals.

### 16. [major] ×1  (road/weekend_warrior)
> The guide references a 'Road Race Strategy' section in the table of contents. This is a gran fondo (L'Étape), not a road race with tactics, attacks, or field sprints. Race-strategy content should be gran-fondo/finisher-oriented (pacing, aid stations, elevation management), not road-race tactical content.

### 17. [major] ×1  (road/time_crunched_parent)
> The fueling section references a computed race duration of ~5.9 hours and 56 g carbs/hour, but the guide text visible to the athlete never explicitly states these numbers or explains the fueling strategy in the truncated section — the athlete needs to see '~56 g carbs per hour for an estimated ~6-hour effort' spelled out clearly, not left buried in JSON metadata.

### 18. [major] ×1  (road/time_crunched_parent)
> 'Road Race Strategy' section is listed in the table of contents. A gran fondo is not a road race — it has no pack tactics, no team strategy, no sprint finishes. Strategy content should be gran-fondo-specific (pacing, aid station management, climbing strategy for the 8,100 ft of gain) not criterium/road-race tactics.

### 19. [major] ×1  (gravel/weekend_warrior)
> Weekly structure lists Sunday as an off day, yet the race is on a Sunday (2026-11-08). No race-day exception or note is present in the visible text — the athlete could read this as a rest day through race week.

### 20. [major] ×1  (gravel/weekend_warrior)
> 'Road Skills' section in the TOC is ambiguous but tolerable for gravel; however, combined with the road-race/category-pathway sections, the document reads like a road-racing template was only partially adapted for gravel.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> Fueling section states '345g Total Race Carbs' based on a race duration of ~5.75 hours (60 g/hr × 5.75 h ≈ 345 g). However, 78 miles on a mountainous MTB course in Guadeloupe (9,462 ft gain) will take a first-timer considerably longer than 5h45m — more likely 6.5–8+ hours. The total carb figure is therefore understated and could contribute to a bonk. The hourly target is fine; the total and the implied duration are misleading.

### 22. [major] ×1  (mtb/ambitious_first_timer)
> Race countdown states '109 days from today,' which implies a generation date of approximately 2026-08-20. The plan start date is 2026-08-24 and race date is 2026-12-07, which is 105 days — not 109. This arithmetic inconsistency will confuse the athlete and erode confidence in the plan's accuracy.

### 23. [major] ×1  (gravel/time_crunched_parent)
> Total race carbs stated as 128 g is inconsistent with the plan's own data. At 45 g/hr over the computed duration of 2.84 hours, the correct total is ~128 g — that checks out mathematically — BUT the guide also states a race distance of 44 miles with an implied finishing time (~2.84 h) that assumes roughly 15.5 mph average. No pacing context or finishing-time estimate is given to the athlete to help them understand how 128 g was derived; without it the number appears arbitrary and erodes trust.

### 24. [minor] ×1  (road/masters_returner)
> Off days are listed as 'Thursday, Saturday, Wednesday' — three off days against 7 hours/week yields 4 riding days, which is plausible, but listing them non-chronologically (Thu, Sat, Wed) is slightly confusing; a coach would typically list them in calendar order (Wed, Thu, Sat).

### 25. [minor] ×1  (gravel/masters_returner)
> 'Road Race Strategy' appears as a table-of-contents section for a gravel event — even if the content inside is generic, the heading signals a discipline mismatch and should be renamed to 'Gravel Race Strategy'.
