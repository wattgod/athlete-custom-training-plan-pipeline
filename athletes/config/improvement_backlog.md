# Improvement backlog — 2026-08-26

**Quality -1.27** · avg coach 5.38/10 · contract pass 50% · load 16.62/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/veteran_podium_chaser)
> Taper Intensity is flagged WARN in the preview checks. For a podium-chasing veteran, taper execution is critical; a known taper-intensity anomaly must be resolved or explicitly reviewed by a human coach before the plan is sent.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents. This is generic beginner road-racing content that is completely inappropriate for a 42-year-old veteran with 11 years of experience and a podium goal — it is condescending, irrelevant, and would immediately erode trust in the entire plan.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> Three automated checks failed — Weekly Volume, Zone Distribution, and Per-Day Duration Caps — meaning the actual calendar numbers are demonstrably wrong or out of spec. Sending a guide whose referenced numbers are known to be broken is not acceptable regardless of how well the prose reads.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> The 'Category 5 to Category 1 Pathway' section appears in the table of contents — this is a road-racing category progression framework that is completely irrelevant and potentially insulting to a 40-year-old experienced racer targeting a gran fondo podium. Gran fondos are not USA Cycling category events. This content must be removed entirely.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check is flagged FAIL in the preview checks, meaning the generated plan does not meet the athlete's 13-hour weekly target. Sending a plan with a known failing volume check to an athlete paying for a 13h/week plan is unacceptable.

### 6. [critical] ×1  (road/masters_returner)
> Table of Contents includes a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to finish a gran fondo — she is not a licensed road racer pursuing a category upgrade. This section is entirely wrong for her plan and would confuse or alarm her.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: The JSON flags discipline as 'mtb', but GFNY Miami is a road gran fondo. The plan header and persona reference MTB, yet every piece of content (road race strategy, Category 5–1 road-racing pathway, road skills section) is road-specific. The plan needs to resolve which discipline is correct and be consistent throughout — as delivered it will read as internally contradictory to the athlete.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong-event content: The table of contents includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. GFNY Miami is a mass-participation gran fondo (finish-oriented, non-competitive category ladder). A Cat 5–1 racing pathway is irrelevant and potentially misleading for an athlete whose stated goal is simply to 'finish' their first big event.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> Race name and discipline contradiction in the document title: The guide is titled 'GFNY Miami 71mi Training Guide' and correctly references Miami, Florida — but GFNY Miami is a road cycling event, not MTB. If the athlete was profiled as MTB, either the event was mis-mapped or the discipline tag is wrong. Either way the inconsistency must be resolved before sending.

### 10. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is included in the table of contents and presumably in the full guide. This is road racing category progression content that is completely irrelevant — and potentially confusing or off-putting — to an athlete whose sole goal is to finish a gran fondo. It signals the guide was templated without proper filtering.

### 11. [critical] ×1  (road/masters_returner)
> Zone chart is missing the power watt ranges for Zone 1 (Active Recovery) and Zone 2 (Endurance). The guide repeatedly instructs the athlete to 'train by power first,' yet the two zones he will spend ~75% of his time in show no watt numbers. At FTP=170W, Z1 should be <94W and Z2 94-127W — these must be populated.

### 12. [critical] ×1  (gravel/ambitious_first_timer)
> Weekly Volume check is a confirmed FAIL per preview_checks. The plan claims '11 hours/week' throughout its narrative but the automated gate flagged volume as non-compliant. Sending a plan with a known volume error is the most basic quality failure — the athlete will either be chronically under- or over-trained relative to what the text promises.

### 13. [critical] ×1  (gravel/ambitious_first_timer)
> Section 'Road Race Strategy — Category 5 to Category 1 Pathway' appears in the table of contents. This is a road-racing-specific section that has no place in a gravel gran fondo plan. Gravel gran fondos are non-draft, non-categorized events; Cat 5–Cat 1 upgrade pathways are a USA Cycling road racing construct entirely irrelevant to this athlete and this event. This is the definition of wrong-discipline content and is embarrassing.

### 14. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and (presumably) the body. This is a gravel gran fondo plan for a goal-finisher, not a road racer pursuing licence upgrades. These sections are discipline-wrong and audience-wrong — they will confuse and undermine trust.

### 15. [major] ×2  (mtb/ambitious_first_timer, road/veteran_podium_chaser)
> Long ride duration range cited as '3.3–5.5 hours' in the Weekly Structure section. For a 99-mile race with an estimated finish around 4.75 h, the upper bound of 5.5 h is defensible, but the lower bound of 3.3 h appears inconsistent with what a 14 h/week polarized plan for a podium contender should prescribe — and it may be a direct symptom of the failing Per-Day Duration Caps check.

### 16. [major] ×1  (road/veteran_podium_chaser)
> The athlete is described in the methodology section as 'Intermediate level' despite the persona being 'veteran_podium_chaser' with 11 years of riding. This label contradiction within the same document signals a template merge error and will confuse or insult the athlete.

### 17. [major] ×1  (road/veteran_podium_chaser)
> TSS Progression check returned WARN. Combined with the Weekly Volume FAIL, there is a coherence risk that the plan's ramp rate is either too aggressive or too flat for a 13-week block — this must be resolved before delivery.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Off days are listed as 'Wednesday, Tuesday' — listing them out of calendar order (Wednesday before Tuesday) is confusing and likely indicates a generation artifact. The standard presentation should be 'Tuesday, Wednesday' and should be verified against the actual calendar.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The guide labels the athlete as 'Intermediate level' in the methodology rationale, but the persona is 'veteran_podium_chaser' with 11 years of riding. Calling an 11-year veteran with a 295W FTP who is chasing podiums an 'Intermediate' is factually wrong and undermines credibility with this athlete.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Fueling section references 68g carbs/hour and a 4.06-hour race duration (consistent with the plan JSON), but the visible guide text does not show whether these specific numbers appear correctly in the Nutrition Strategy section — the truncation cuts off before that section. Given the specificity of the data, this must be verified before send.

### 21. [major] ×1  (road/masters_returner)
> Off days listed as 'Monday, Thursday, Tuesday' — that is three off days for an athlete on an 8h/week, 4-training-day plan. The plan data confirms 4 training days and 3 off days, but listing three separate named off days mid-sentence reads as a copy error and is internally inconsistent with the '4 training days, 3 key sessions' statement in the Weekly Structure section.

### 22. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' appears in the ToC. This athlete is doing a gran fondo with a finish goal, not a road race. Gran fondo pacing strategy (self-paced, no tactical racing, fueling over 5+ hours in desert heat) is substantively different from road race tactics and the wrong section risks giving misleading advice.

### 23. [major] ×1  (mtb/ambitious_first_timer)
> Zone 1 upper bound is missing from the zone chart: Zone 1 shows '0–101W' but no percentage of FTP is listed (other zones show % FTP). Minor inconsistency but looks unfinished compared to the other rows.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> 'Road Skills' section appears in the table of contents for what is labelled an MTB plan. MTB skills (switchbacks, technical descending, rock gardens) are completely different from road skills. If this is truly an MTB plan the section content will be wrong; if it is a road plan the section name is acceptable but the discipline label in the persona must be corrected.

### 25. [major] ×1  (mtb/ambitious_first_timer)
> Estimated race duration used for fueling (4.56 hours) is not surfaced or explained to the athlete anywhere in the visible guide text. The athlete should be told the estimated finish time that underpins the 55 g/h carb recommendation so they can sanity-check it.
