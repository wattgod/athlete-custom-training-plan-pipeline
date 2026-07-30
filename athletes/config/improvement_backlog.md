# Improvement backlog — 2026-07-30

**Quality 0.96** · avg coach 6.0/10 · contract pass 88% · load 14.5/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/ambitious_first_timer)
> FTP value (118 W) is printed as the athlete's weight in the profile card ('118 lbs Weight (53.5 kg)'), while the actual weight field appears to have been populated with the FTP number. These are completely different data points from different fields — this is a template variable substitution error that is both factually wrong and deeply embarrassing to send to a paying customer.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway' are listed as content sections in the table of contents. This is an MTB athlete targeting GFNY Chile, which is a mountain bike gran fondo. Road racing categories and road cornering/pack-riding skills content are wrong-discipline material that has no place in this plan.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> GFNY Chile is consistently described and contextualized as a road event (road race strategy, road skills). GFNY Chile is a mountain bike event held in Casablanca, Valparaíso — the race_in_verified_db flag and race_db_location confirm this. MTB-specific skills (technical descending, trail braking, body position, singletrack cornering) are absent while road-specific content is present.

### 4. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is USA Cycling criterium/road-race category progression content — it is completely irrelevant and potentially confusing for an athlete whose stated goal is simply to *finish* a gran fondo. It signals the guide was assembled from generic road-racing boilerplate without proper filtering for event type and goal.

### 5. [critical] ×1  (road/masters_returner)
> 'Road Race Strategy' section is also listed in the table of contents. GFNY Chile is a mass-participation gran fondo, not a road race with tactics, breakaways, or field sprints. Road race strategy content (attacking, sitting in the peloton, sprint finishes) is wrong-discipline material for a finish-goal gran fondo athlete and could actively mislead training priorities.

### 6. [critical] ×1  (road/weekend_warrior)
> "Gravel Skills" appears as a named section in the Table of Contents. This athlete is registered for a road event (Prosecco Cycling, road discipline). Gravel-specific skills content has no place in a road racing plan and will confuse or undermine confidence in the entire guide.

### 7. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution preview check FAILED and the guide does not address or acknowledge it. A failed zone distribution means the plan's prescribed zone mix is wrong — likely too much Zone 3 'gray zone' — yet the guide ships to the athlete with no correction. This directly undermines the central training-zones coaching message the guide itself preaches.

### 8. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full guide. This is a USA Cycling road-racing licence progression framework that is completely irrelevant to a 41-year-old time-crunched parent whose sole goal is to finish a 102-mile gran fondo. It signals the wrong sport context, could confuse the athlete, and is embarrassing boilerplate bleed-through.

### 9. [critical] ×1  (road/time_crunched_parent)
> Long ride duration ceiling described as '1.5–2.5 hours' is dangerously mismatched to a 102-mile event estimated at ~6.6 hours. Even with the honesty box ('your long rides are shorter than ideal'), prescribing a structural cap of 2.5 h as the peak long ride in a plan targeting a 6.6-hour race is a methodology failure. The guide should show a pathway to at least one 4–5 h ride, not cap at 2.5 h and hope the warning covers it.

### 10. [critical] ×1  (road/veteran_podium_chaser)
> Table of contents and implied content includes a 'Category 5 to Category 1 Pathway' section. This athlete is a 43-year-old veteran podium chaser — not a beginner seeking a USA Cycling upgrade pathway. This content is for the wrong persona entirely and is embarrassing to send to an experienced racer.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline label is 'mtb' yet the plan body contains no MTB-specific execution content — no trail skills, no technical descending, no body position, no line choice, no brake modulation. The ToC lists a 'Gravel Skills' section, not 'MTB Skills,' which suggests a template discipline mismatch. For a Lake District MTB event, technical trail riding is a core race requirement, not a footnote.

### 12. [critical] ×1  (mtb/ambitious_first_timer)
> The event is called JUST.GRAVEL and is classified as discipline 'mtb' in the JSON. The plan must clearly resolve whether this is a gravel bike event or an MTB event — the ToC section title 'Gravel Skills' combined with the discipline tag 'mtb' indicates the system may have blended two templates. Wrong skills content for the wrong bike/discipline will embarrass the business and give the athlete bad advice.

### 13. [major] ×2  (gravel/veteran_podium_chaser, road/masters_returner)
> FTP test section states 'The test result sets ALL your training zones for the next 6 weeks.' The plan is only 8 weeks long; depending on when the test falls this phrasing is either inaccurate (could be fewer than 6 weeks remaining) or implies a second test that isn't referenced. This is a copy-paste error from a longer plan template and will confuse the athlete.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> The plan states '1 Years Riding' and 'Intermediate level' in the same breath — these are contradictory. One year of riding is beginner/novice, not intermediate. If the athlete self-reported intermediate, that should be noted with appropriate skepticism; if the system assigned it, it is wrong and will mislead the athlete about their fitness ceiling.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> TSS Progression flagged WARN in the preview checks, but the guide contains no acknowledgment of this or coaching guidance around it. A WARN on TSS progression is a meaningful signal (risk of too-steep a ramp) and the coach's voice should address it somewhere in the plan.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> The fueling section references a 5.5-hour race duration and 52 g carbs/hour, but this data never surfaces in the body of the truncated guide text in a meaningful way — the 'race-pace fueling practice' instruction is generic and does not tell the athlete what to actually consume. For an athlete whose goal is simply to finish a ~5.5 h MTB event, concrete on-bike nutrition guidance is a primary deliverable.

### 17. [major] ×1  (road/masters_returner)
> Zone 1 row in the zone chart is missing its % FTP range (only watts are shown: 0-97 W). Every other zone lists a % FTP column value. The omission is visually inconsistent and makes it look like a data error to the athlete.

### 18. [major] ×1  (road/masters_returner)
> Long ride duration range stated as '3.8-6.2 hours' in the Weekly Structure section. For an 8-week plan targeting a 79.5-mile gran fondo with a finish goal, a 6.2-hour long ride is excessive and inconsistent with the Per-Day Duration Cap passing its automated check. Even if technically within cap, stating 6.2 h in the guide text without qualification will alarm a masters returner and contradicts measured, conservative volume build-up for this persona.

### 19. [major] ×1  (road/weekend_warrior)
> Zone 1 power range is listed as '0-102W' but the % FTP column for Zone 1 is left blank. At FTP=186W, Zone 1 should be labeled ≤55% FTP (≤102W is actually correct numerically, but the missing % label is inconsistent with every other zone row and reads as an error/omission).

### 20. [major] ×1  (road/weekend_warrior)
> The Zone Distribution preview check returned WARN. The guide text never acknowledges or resolves this warning — it simply states '~70% easy' without addressing what the actual flagged imbalance is. A paying customer who notices the WARN will have no explanation and may lose trust in the plan.

### 21. [major] ×1  (gravel/veteran_podium_chaser)
> Two preview checks flagged WARN (Weekly Volume and Zone Distribution) but the guide text gives no indication of what triggered those warnings. Before sending, a human coach must confirm the weekly TSS/hours actually average close to 14 h and that the zone distribution genuinely reflects a pyramidal ~75/15/10 split. If the generated calendar contradicts either, the guide text's claims are misleading.

### 22. [major] ×1  (road/time_crunched_parent)
> Taper Intensity flagged as WARN in preview checks but the guide's taper section contains no specific guidance on what 'short, sharp efforts' means in terms of duration, zone, or frequency during the taper. A time-crunched athlete with high stress and limited hours needs explicit taper-week structure, not a single vague sentence.

### 23. [major] ×1  (road/time_crunched_parent)
> 'Masters Training Considerations' is listed in the table of contents but the truncated guide shows no evidence of age-appropriate content for a 41-year-old (e.g. extended recovery windows, HRV guidance, sleep prioritisation beyond the generic note). If this section is a stub or generic filler it should not be listed as a chapter.

### 24. [major] ×1  (road/time_crunched_parent)
> The 'Strength training: Included (dumbbells)' callout and strength session type are described, but the guide provides zero specifics — no exercises, sets, reps, or phase-by-phase progression. For a time-crunched athlete allocating scarce training hours to strength, this is an unfulfilled promise.

### 25. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution check flagged WARN in the preview but the guide contains zero explanation or acknowledgment of this warning. A paying athlete receiving a plan with a known zone-distribution concern deserves either a corrected distribution or an explicit coach's note explaining why it is acceptable.
