# Improvement backlog — 2026-08-14

**Quality 2.92** · avg coach 6.57/10 · contract pass 75% · load 10.38/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the Contents and a dedicated section are titled 'Gravel Skills' — this is an MTB race (Walburg Dirty 30 is a dirt/MTB event). Gravel-specific cornering, bike-handling, and gear framing is wrong for the discipline and embarrassing if sent to an MTB rider.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Wrong-discipline content: The table of contents lists 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway'. This is an MTB gran fondo plan. Road racing categories, road race tactics, and road cornering/skills content are completely inappropriate and will confuse and mislead the athlete.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Long-ride duration is capped at 1.5 hours in the Weekly Structure section, yet the race is 68 miles with an estimated duration of ~4.6 hours. The plan itself flags this as a problem in the 'Biggest Opportunity' callout, but never resolves it — the prescribed peak long-ride length is less than a third of race duration, which is incoherent for a finish-goal athlete.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Fueling figure mismatch: The athlete data specifies 59 g carbs/hour over a 4.6-hour event, yet no fueling recommendation in the visible nutrition section references either of these numbers. If the Nutrition Strategy section uses a different figure it will directly contradict the athlete's personalised fueling calculation and could cause GI distress or bonking on race day.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' is listed in the Table of Contents. This section is completely inappropriate for a veteran podium chaser — he is not a Cat 5 needing a racing license pathway tutorial. It belongs in a beginner plan, not here, and would embarrass the business if sent to this athlete.

### 6. [critical] ×1  (road/time_crunched_parent)
> Race elevation is stated as '650 ft' in the header. GFNY Cozumel is a notoriously flat course (~650 ft is plausible for Cozumel, but this figure appears nowhere in the verified JSON data supplied — the plan has fabricated or assumed an elevation number. If it is wrong it will mislead the athlete's entire race-simulation and pacing strategy. Either source it from the verified DB or remove it.

### 7. [critical] ×1  (road/veteran_podium_chaser)
> "Category 5 to Category 1 Pathway" section heading appears in the Table of Contents for a 17-year veteran podium chaser. This is deeply wrong for the persona — it implies a novice racing license progression pathway that has zero relevance to an experienced racer targeting a podium at a gran fondo. It will destroy credibility immediately with this athlete and suggests content from a beginner template was spliced in.

### 8. [major] ×1  (mtb/weekend_warrior)
> Race countdown is wrong: the plan states '128 days from today' but the plan start date is 2026-08-24 and the race is 2026-12-20, which is approximately 118 days from plan start — and the actual gap from any plausible 'today' during QA differs further. A hard-coded, apparently miscalculated countdown number erodes trust in the automation.

### 9. [major] ×1  (mtb/weekend_warrior)
> FTP Test Frequency flagged WARN in preview checks but no explanation or mitigation is visible in the truncated guide. For a 17-week plan with a 4 h/week athlete, the number or spacing of FTP tests should be explicitly justified to the athlete, not silently suppressed.

### 10. [major] ×1  (mtb/weekend_warrior)
> Zone Distribution check flagged WARN in the preview checks but is never acknowledged or explained in the guide. Coaches reading this will be unable to verify whether the zone split is actually correct, and the athlete receives no guidance on the discrepancy.

### 11. [major] ×1  (mtb/weekend_warrior)
> Off-day logic appears inconsistent: the plan lists three off days (Tuesday, Monday, Saturday) in a 7-day week for a 4-training-day athlete, yet that totals only 4 riding days which is plausible — however listing Monday and Saturday as off days while Sunday is the long ride day means the day immediately before the long ride (Saturday) is already off, which is fine, but the ordering 'Tuesday, Monday, Saturday' is oddly listed non-chronologically and may indicate a template error in day assignment.

### 12. [major] ×1  (mtb/weekend_warrior)
> 'Plan_weeks is 11 but weeks_until_race is 12' — the guide never tells the athlete when to start. The plan_note explains this is intentional (athlete starts one week late), but the guide itself gives no start-date guidance, leaving the athlete to guess. The start date field shows 2026-08-24 but this should be surfaced explicitly in the Training Plan Brief.

### 13. [major] ×1  (gravel/ambitious_first_timer)
> Experience level contradiction: the guide states '1 years of cycling experience at Intermediate level' but the persona is 'ambitious_first_timer'. A first-timer is a beginner, not Intermediate. This mislabeling could undermine athlete trust and may reflect a template merge error.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> Race carb total is wrong: 63 g/hr × 7.2 h = 453.6 g, yet the guide rounds up and displays '454g Total Race Carbs' — that arithmetic is defensible — but the race-day duration of 7.2 hours is never communicated to the athlete anywhere in the visible text, leaving the '454g' figure floating without context. Athletes need to see the expected finish time to validate that number.

### 15. [major] ×1  (road/veteran_podium_chaser)
> The guide describes 16 years of experience as 'Intermediate level' in the methodology rationale. A veteran podium chaser with 16 years and a 335W FTP should be labeled Advanced or Experienced, not Intermediate. This directly contradicts the persona and will undermine the athlete's confidence in the plan.

### 16. [major] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' is listed as a content section in the Table of Contents. This is USA Cycling road-racing category terminology that is completely irrelevant to a gran fondo participant targeting a podium finish at GFNY Cozumel. It suggests content written for a different athlete archetype was pasted in, and it will confuse or undermine the athlete's confidence in the plan's specificity.

### 17. [major] ×1  (road/time_crunched_parent)
> Three off days are listed as 'Friday, Wednesday, Thursday' — that is three consecutive or near-consecutive off days in a 7-day week, which combined with 4 training days leaves a very compressed block. The JSON says 'Off Days Respected: PASS' but the prose description should reconcile with a coherent weekly rhythm; stating three specific named days without the full weekly schedule visible here makes it impossible to verify and may read as a copy-paste error to the athlete.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> The experience level label is internally inconsistent: the persona is 'veteran_podium_chaser' (Experienced racer chasing a podium) yet the guide text states '11 years of cycling experience at Intermediate level.' A 44-year-old with 11 years of riding history gunning for a UCI World Champs podium should never be described as Intermediate — this reads as a template placeholder that wasn't resolved and could undermine the athlete's confidence in the plan's personalisation.

### 19. [minor] ×2  (gravel/veteran_podium_chaser, road/veteran_podium_chaser)
> The long-ride duration range cited ('3.4-5.8 hours') in the Weekly Structure section cannot be verified from the truncated plan, but 5.8 hours on a 10 h/week budget is extremely high (58% of weekly volume in one ride) — worth confirming the calendar actually supports this without blowing per-day caps, even though Per-Day Duration Caps passed the automated check.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution automated check is flagged FAIL. The guide text describes a ~65% easy / meaningful G-Spot & threshold / VO2 split, but the system check failed — meaning the actual week-by-week prescribed distribution likely contradicts the stated methodology. This cannot be resolved from the guide text alone and must be corrected before sending.

### 21. [major] ×1  (road/veteran_podium_chaser)
> The guide states '17 Years Riding' but then characterises the athlete as 'Intermediate level' in the methodology rationale ('17 years of cycling experience at Intermediate level'). A 17-year riding veteran targeting a podium should not be labelled Intermediate — this is either a data-entry error in the questionnaire that was blindly echoed, or a template label that was never updated. Either way it reads as a mistake to the athlete.

### 22. [minor] ×1  (mtb/weekend_warrior)
> The plan says '3 training days, 3 of which are key sessions' — this is a tautology (all 3 of 3 are key) and likely a copy-paste error where the second number should be lower (e.g., '3 training days, 2 of which are key sessions'), which also conflicts with the Time-Crunched model that typically has 1 long + 1-2 intensity sessions.

### 23. [minor] ×1  (mtb/weekend_warrior)
> Athlete has 4 years riding experience but the guide labels this 'Intermediate level' without surfacing that label to the athlete — the plan note mentions it internally but the athlete-facing text never defines what intermediate means or how it shaped the plan, which can cause confusion.

### 24. [minor] ×1  (mtb/weekend_warrior)
> Long ride ceiling described as '1.5–2 hours' for a race estimated at 2.7 hours finish time is acknowledged as a limitation, but the plan never gives the athlete a concrete strategy to bridge that gap (e.g., a specific number of 'bonus' long rides or a target duration to hit at least once before race day).

### 25. [minor] ×1  (mtb/weekend_warrior)
> The 'Best done indoors / Best done outdoors' section recommends outdoor 'skills practice' generically but never specifies MTB-relevant skills (technical terrain, cornering on loose surfaces, braking on descents) — a missed opportunity and a sign the content may be partially road-derived.
