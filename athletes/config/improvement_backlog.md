# Improvement backlog — 2026-08-08

**Quality 1.16** · avg coach 6.25/10 · contract pass 88% · load 14.62/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (road/masters_returner, road/veteran_podium_chaser)
> A 'Category 5 to Category 1 Pathway' section appears in the table of contents and, presumably, in the full guide body. This athlete is a 44-year-old veteran gran fondo racer (persona: veteran_podium_chaser), not a criterium/road-license racer working through USA Cycling categories. Cat upgrade pathways are entirely wrong for this discipline context and would confuse or embarrass a paying customer.

### 2. [critical] ×1  (gravel/time_crunched_parent)
> Zone 2 lower bound is missing its power percentage in the zone chart — the row shows '135-183W' for power but the '%FTP' column is listed as '56-75% FTP' while Zone 1 has no %FTP shown at all. More critically, Zone 1 is defined as '0-134W' with no %FTP label, yet 134W is only 55% of 245W FTP — this is correct numerically but the chart omits the percentage entirely for Z1, which is inconsistent and will confuse the athlete when they update zones after a retest.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents. These are road-racing constructs (USA Cycling cat upgrade logic) and have zero relevance to a gravel event. Sending this to a gravel racer is embarrassing and undermines trust in the entire plan.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' section is listed in the contents. Gravel racing demands different skills (loose-surface cornering, technical descending, tire-pressure management, self-sufficiency). Road skills content is wrong-discipline material for this athlete.

### 5. [critical] ×1  (gravel/ambitious_first_timer)
> Experience contradiction: the profile simultaneously lists '1 Years Riding' and labels the athlete 'Intermediate level.' One year of riding is a beginner, not intermediate. This inconsistency will confuse the athlete and undermines trust in the whole document.

### 6. [critical] ×1  (gravel/weekend_warrior)
> Weight (124 lbs / 56.2 kg) and height (5'4") appear in the athlete profile section but are NOT present in the provided athlete JSON. The plan has fabricated biometric data for a paying customer — if these are wrong it is both embarrassing and potentially affects any w/kg or nutrition calculations downstream.

### 7. [critical] ×1  (gravel/weekend_warrior)
> Weekly structure contradiction: the guide states 'Your week has 2 training days, 2 of which are key sessions' — meaning zero non-key training days — yet separately lists Long Ride, Intervals, Easy Ride, and Strength as four distinct session types. A 4 h/week athlete almost certainly has more than 2 riding days; the copy-paste number is internally inconsistent and will confuse the athlete.

### 8. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content: the table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is racing GFNY Cozumel — a gravel gran fondo — not a criterium or road race. Cat 5–Cat 1 upgrade pathway content is irrelevant, confusing, and undermines credibility with a paying customer targeting a gravel podium.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> Long-ride duration cap is grossly mismatched to the event. The guide explicitly states the athlete's 'peak duration' long ride is 1.5 hours for a 96-mile gravel race with an estimated ~4.4-hour finish time. Even for a time-crunched athlete, publishing 1.5 hours as the peak long ride against a race that is nearly 3× that length will alarm and mislead the athlete. The Pre-checks flagged Per-Day Duration Caps as FAIL — this is the likely source and it was not resolved before sending.

### 10. [major] ×2  (gravel/time_crunched_parent, road/masters_returner)
> The guide states 'The test result sets ALL your training zones for the next 6 weeks' in the FTP testing warning box — but this is an 8-week plan and FTP tests are presumably scheduled near the start. Saying '6 weeks' is a copy-paste artifact from a longer plan template and is factually wrong for this athlete's timeline.

### 11. [major] ×2  (road/masters_returner, road/veteran_podium_chaser)
> The FTP Test Frequency preview check returned WARN, yet the guide text says 'the test result sets ALL your training zones for the next 6 weeks' without acknowledging the flagged issue. If tests are spaced incorrectly (too close or too far apart) the athlete deserves a plain-language note, not a buried warning swallowed by boilerplate.

### 12. [major] ×2  (gravel/ambitious_first_timer, gravel/weekend_warrior)
> Long ride duration range cited as '2.2–3.8 hours' in the Weekly Structure section. For a 7 h/week athlete targeting a ~4.8 h race, a peak long ride of only 3.8 h is on the low end but defensible — however the figure appears without any context tying it back to the race duration, which could leave the athlete uncertain about race-readiness.

### 13. [major] ×1  (gravel/time_crunched_parent)
> The nutrition section is cut off mid-sentence ('150% of flu—') in the reviewed text. While this may be a truncation artifact of the preview, if the delivered PDF is similarly incomplete this is a significant omission for an athlete racing 3.6 hours who has a specific fueling target of 65g carbs/hour — the fueling strategy is one of the most race-critical sections.

### 14. [major] ×1  (gravel/veteran_podium_chaser)
> The plan describes the athlete as 'Intermediate level' in the methodology rationale ('16 years of cycling experience at Intermediate level'). A rider with 16 years of experience and an FTP of 285 W targeting a podium is clearly an advanced/experienced racer — the persona label itself says 'veteran podium chaser.' This is a direct internal contradiction.

### 15. [major] ×1  (gravel/veteran_podium_chaser)
> The Weekly Volume automated check returned WARN but the guide text contains no acknowledgement, explanation, or mitigation of this flag. At 15 h/week the volume is on the high end for some weeks; a coach would at minimum note why the flag is acceptable or how volume is managed — leaving it silently unaddressed is a QA gap.

### 16. [major] ×1  (road/veteran_podium_chaser)
> The guide simultaneously labels the athlete as '18 Years Riding' (long-time veteran) but the methodology justification calls her 'Intermediate level.' These directly contradict each other — 18 years of riding experience should never be labeled Intermediate, and a customer will notice.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 (Active Recovery) row in the zone chart is missing both % FTP and % LTHR columns — they are blank. Every other zone has these anchors. For an athlete without deep zone knowledge this is a usability gap, especially for recovery spins between intervals.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> The 'Zone Distribution WARN' and 'TSS Progression WARN' flags from the automated preview checks are unresolved and unexplained anywhere in the guide. If a paying athlete saw these flags they would be alarmed; the guide should either address why they are acceptable or the underlying issue should be corrected.

### 19. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section is listed in the ToC. Cycling Shimanami is a gran fondo / sportive, not a mass-start road race. Tactical race-strategy content (attacking, sitting in the bunch, sprint positioning) is inappropriate and misleading for a finish-goal athlete on this course.

### 20. [major] ×1  (road/masters_returner)
> The athlete is described as having '20 Years Riding' yet is labeled 'Intermediate level' in the methodology justification. 20 years of cycling experience is not Intermediate — this internal contradiction will undermine the athlete's trust in the plan's personalization.

### 21. [major] ×1  (road/masters_returner)
> Zone 1 (Active Recovery) has no FTP% range listed in the zone chart — the power column shows '0–94W' but the '% FTP' column is blank. Every other zone has an explicit FTP% and LTHR%. This looks like a data rendering failure and reads as an error.

### 22. [major] ×1  (gravel/weekend_warrior)
> Off-day listing reads 'Off days: Tuesday, Monday' — Monday is listed second, which implies it may be a copy error (likely should be Monday and Tuesday, or some other pair). The reversed/awkward order suggests a template population bug and could mislead the athlete about which days are rest days.

### 23. [major] ×1  (gravel/weekend_warrior)
> Taper Intensity flagged WARN by the automated preview but no compensating coach note or explanation appears in the truncated guide. For a finish-goal athlete this is unlikely to be dangerous, but the WARN should either be resolved in the plan or acknowledged — sending without addressing it is a quality gap.

### 24. [major] ×1  (gravel/weekend_warrior)
> Zone Distribution flagged WARN by preview. Given that the guide explicitly emphasises ~70% Zone 2 and warns against Zone 3 'grey zone,' a distribution warning suggests the actual calendar workouts may contradict the stated methodology. This needs resolution before sending — the text says one thing, the numbers say another.

### 25. [major] ×1  (gravel/weekend_warrior)
> FTP Test Frequency flagged WARN. The zone table states 'The test result sets ALL your training zones for the next 6 weeks,' but a 9-week plan with only one test (or an unexpected test cadence) conflicts with that statement and with the preview warning — the athlete could be training off stale zones for the back half of the plan.
