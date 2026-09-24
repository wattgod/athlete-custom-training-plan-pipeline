# Improvement backlog — 2026-09-24

**Quality 1.32** · avg coach 5.62/10 · contract pass 100% · load 13.25/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/weekend_warrior, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably elaborated later in the guide. This is a USA Cycling road racing licensure concept that is completely irrelevant to a gravel event and to a weekend-warrior athlete whose goal is simply to finish. It would confuse and mislead the athlete.

### 2. [critical] ×1  (gravel/masters_returner)
> Wrong-discipline content: The table of contents and guide body include 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is training for a gravel event. Road-race category advancement pathways are irrelevant and confusing — gravel riders do not race in USA Cycling road categories. This is the clearest sign the template was not correctly filtered for discipline.

### 3. [critical] ×1  (gravel/masters_returner)
> Equipment checklist specifies 'road bike, in good working order' as the mandatory training bike. The event is the Lake Taupo Cycle Challenge, a gravel/mixed-surface event. The checklist should reference a gravel bike and mention appropriate tyre width, tubeless setup, and gravel-specific spares (tyre plugs are mentioned for race day but the training bike specification is wrong).

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: athlete is MTB but the Equipment Checklist specifies a 'road bike in good working order' as mandatory, and the table of contents lists 'Road Skills' and 'Road Race Strategy' sections — content that is wrong and potentially dangerous for a mountain-bike gran fondo on a course with 9,462 ft of climbing. MTB-specific equipment (dropper post, tubeless setup, trail tires, MTB helmet considerations) and skills (technical descending, switchback cornering, trail braking) are entirely absent.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Taper Intensity flagged WARN in preview checks and the guide text never explicitly addresses or resolves it — the taper section says only 'short, sharp efforts keep the engine awake' with no concrete RPE or zone guidance, leaving the athlete without actionable taper-week prescriptions during the most sensitive period before their A-race.

### 6. [critical] ×1  (gravel/weekend_warrior)
> 'Road Race Strategy' section appears in the table of contents. This athlete is racing a gravel event (L'Étape Ciudad de México), not a criterium or road race. Road-race-specific tactical advice (e.g., positioning in a peloton, field sprint tactics) is wrong-discipline content that should never appear in a gravel plan.

### 7. [critical] ×1  (road/weekend_warrior)
> Long-ride duration is described as peaking at '1.5–2 hours' but the race is 68 miles with an estimated finish time of ~4.67 hours. Even accounting for the Time-Crunched constraint, the guide itself flags this as a problem yet never resolves it — a paying athlete reading this will reasonably conclude the plan cannot prepare her for the event. The copy needs to honestly set a higher long-ride ceiling target (e.g., one or two 3-hour rides) or explicitly explain the trade-off without undercutting confidence.

### 8. [critical] ×1  (gravel/time_crunched_parent)
> Wrong discipline content — the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is racing GRAVEL (Tour de Tucson is a gravel/road gran fondo, not a USA Cycling category road race). Cat 5–1 licensing pathway content is completely irrelevant and will confuse or embarrass the customer.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> Athlete weight (177 lbs / 80.3 kg / 5'10") is displayed in the profile card but the intake questionnaire data provided contains no weight or height fields — these numbers were fabricated or pulled from a wrong athlete's record. Presenting invented biometric data to a paying customer is a serious data integrity failure.

### 10. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a GRAVEL plan. These sections are wrong-discipline content that will immediately erode athlete trust and embarrass the business.

### 11. [critical] ×1  (gravel/veteran_podium_chaser)
> FTP test protocol states the result 'sets ALL your training zones for the next 6 weeks' — but the entire plan is only 8 weeks long. This is a direct numerical contradiction that a detail-oriented podium-chasing athlete will catch.

### 12. [major] ×2  (gravel/masters_returner, gravel/time_crunched_parent)
> FTP Test Frequency flagged WARN in preview checks but the issue is unresolved in the guide text. The guide should either explicitly acknowledge the spacing of tests is constrained by the 9-week window and explain the rationale, or the test protocol should be adjusted. Sending a plan with an unresolved automated warning is a quality-gate failure.

### 13. [major] ×1  (gravel/masters_returner)
> No gravel-specific skills or terrain content anywhere in the guide. For a 99-mile gravel event, cornering on loose surfaces, descending technique, tyre pressure management, and nutrition on rough terrain are material coaching topics. The omission is conspicuous given that road-race strategy content (wrong discipline) was included instead.

### 14. [major] ×1  (gravel/time_crunched_parent)
> Section titled 'Road Skills / Road Race Strategy' is included in the table of contents for a GRAVEL event. This is the wrong discipline content — a gran fondo on gravel terrain needs gravel-specific skills (loose surface cornering, rough descending, singletrack or doubletrack technique, tyre pressure management) not road race tactical content. Sending road-race strategy to a gravel athlete is embarrassing and undermines coaching credibility.

### 15. [major] ×1  (gravel/time_crunched_parent)
> Fueling strategy lists 55 g carbs/hour, but the estimated race duration is ~5.7 hours (verified from plan JSON). The guide should clearly communicate total carbohydrate need (~315 g over the race) and flag that 55 g/h is a conservative figure appropriate for a finish-goal athlete — however, no in-ride fueling table or per-hour cue is visible in the truncated text. Given the race length, under-fueling is the single biggest DNF risk and deserves explicit, prominent treatment rather than being buried or absent.

### 16. [minor] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> TSS Progression and Taper Intensity both flagged WARN in the preview checks. The guide text does not acknowledge or mitigate these warnings for the athlete — a brief coach's note explaining why the TSS ramp is intentionally compressed (only 11 weeks, time-crunched methodology) and what 'sharp but short' taper efforts look like would remove any ambiguity and reinforce trust.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> The Gran Fondo Guadeloupe is verified as a Guadeloupe event with 9,462 ft of climbing over 78 miles — it is almost certainly a road or gravel gran fondo, NOT an MTB event. The plan JSON says discipline='mtb' yet the verified race DB describes what appears to be a paved/gravel gran fondo. This contradiction must be resolved before sending; if the race is road/gravel, the entire discipline framing, equipment list, and skills sections need to change.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Experience is listed as '1 Years Riding at Intermediate level' in the methodology rationale, but the profile card says '1 Years Riding' with the persona label 'Ambitious first-timer.' Calling a one-year rider 'Intermediate' is an inconsistency that will undermine athlete trust.

### 19. [major] ×1  (gravel/weekend_warrior)
> The 'YOUR BIGGEST OPPORTUNITY' callout tells the athlete her long rides are 'shorter than ideal for a race of this distance' and recommends 3-4 hour rides, yet the plan's own per-day duration caps and weekly hour budget (5 h) make those rides structurally impossible without blowing the plan. This is internally contradictory and erodes trust in the plan's design.

### 20. [major] ×1  (road/weekend_warrior)
> Weekly session count is internally contradictory: the guide states 'Your week has 3 training days, 3 of which are key sessions' — every training day is called a key session, which makes the distinction meaningless and reads like a copy-paste error.

### 21. [major] ×1  (road/weekend_warrior)
> The Taper Intensity check returned WARN in the automated gate, yet the guide's taper section contains no concrete guidance about what 'short, sharp efforts' look like in terms of duration or RPE for this athlete. For a 46-year-old with high life stress, leaving taper intensity undefined is a meaningful coaching gap.

### 22. [major] ×1  (road/weekend_warrior)
> 'Women-Specific Considerations' appears in the table of contents but is not visible in the truncated text supplied for review. If this section is present, it must be verified that it does not contain generic filler or, worse, content copied from a male-athlete template. Given the other template-blending errors found, this is a real risk.

### 23. [major] ×1  (road/veteran_podium_chaser)
> The 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This content is inappropriate and potentially embarrassing for a self-described podium-chasing veteran of 9 years — it is boilerplate aimed at raw beginners and implies the athlete is a Cat 5 novice. It should be removed or replaced with race-category-appropriate strategy content.

### 24. [major] ×1  (road/veteran_podium_chaser)
> The athlete profile displays '142 lbs / 5'4"' — but the athlete's weight and height were not provided in the plan JSON (no such fields exist). These numbers appear to have been fabricated or pulled from a default template. Sending invented biometric data to a paying customer is a credibility-destroying error if the figures are wrong.

### 25. [major] ×1  (gravel/time_crunched_parent)
> The equipment checklist lists 'road bike' as the mandatory bike for a gravel race. A gravel-specific bike (or at minimum 'gravel or road bike with appropriate tires') should be specified, and gravel-specific equipment (tubeless setup, wider tires, frame bag/feed bag for a 102-mile event) is entirely absent.
