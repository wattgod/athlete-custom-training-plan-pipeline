# Improvement backlog — 2026-07-19

**Quality -0.85** · avg coach 5.25/10 · contract pass 75% · load 16.5/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/masters_returner, gravel/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and (implied) in the guide body. This is a road racing licensing/category construct (USA Cycling road cat system) that is completely irrelevant to a UCI Gran Fondo gravel event. It signals the template was partially pulled from a road racing plan and will confuse or embarrass the athlete.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road-racing categorical upgrade pathway — irrelevant and potentially embarrassing for an athlete whose goal is simply 'podium' at a mass-participation L'Étape event. L'Étape events have no category structure; this content appears to have leaked in from a different template and should be removed entirely.

### 3. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Race Strategy' section is listed in the contents and present in the guide. This athlete is racing a gravel gran fondo, not a criterium or road race. Tactics, positioning, and race-specific advice should be gravel/gran-fondo-specific (fueling stops, terrain management, self-paced effort, gravel-specific descending). Sending road race strategy to a gravel racer is a credibility-destroying error.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — Table of Contents includes 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This is an MTB plan; road racing skills, road race tactics, and a road-category upgrade pathway have zero relevance and will confuse or embarrass the athlete.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED in the automated preview. The guide text claims '~70% of riding stays genuinely easy' but the actual week-by-week prescription apparently contradicts this (flagged FAIL). Sending a plan whose internal zone logic is broken undermines the core methodology promise.

### 6. [critical] ×1  (gravel/masters_returner)
> Weekly Volume automated check is a hard FAIL — the guide must not be sent until that underlying volume error is identified and corrected, as it means prescribed hours/TSS are likely wrong for this athlete.

### 7. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' and 'Road Skills' are listed as dedicated sections in the table of contents. This is a gravel discipline plan — content should address gravel-specific skills (loose surface cornering, tire pressure management, rough terrain pacing) not road race tactics.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> Wrong discipline throughout: La Ruta de los Conquistadores is a multi-day mountain bike stage race (3 days), not a road race. The guide includes 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' section — all completely irrelevant and misleading for an MTB stage race athlete.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> The plan treats La Ruta as a single-day 162-mile event. La Ruta de los Conquistadores is a 3-day stage race (~162 miles total across stages). A single-day long-ride model and single race-day taper are structurally wrong; multi-day stage racing requires a completely different training stimulus (back-to-back long days, stage-recovery protocols).

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong discipline content — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections are listed in the table of contents. This athlete is racing an MTB granfondo, not a road criterium/road race with USA Cycling upgrade categories. Cat 5→Cat 1 pathway language is road-racing-specific, completely inapplicable here, and will confuse or embarrass the athlete.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong discipline content — 'Road Skills' section appears in the ToC. The target event is an MTB granfondo in mountainous Piedmont; relevant skills are MTB-specific (descending on gravel/singletrack, loose-surface braking, body position on climbs) — not road-race pack-riding or road cornering technique.

### 12. [critical] ×1  (gravel/time_crunched_parent)
> Long ride duration is catastrophically mismatched to the race. The guide states the athlete's long rides peak at '1.5 hours,' yet the race is 76 miles and the fueling data shows an expected finish time of ~7.3 hours. The guide itself acknowledges the gap ('your long rides are shorter than ideal') but frames a 3–4 hour ride as the fix — still less than half the race duration. For a finish-goal athlete on a 76-mile gravel event, this is a fundamental race-preparation failure that should be escalated, not soft-pedaled in a sidebar.

### 13. [major] ×1  (road/veteran_podium_chaser)
> The automated Weekly Volume check returned WARN and no explanation is provided in the plan facts. At 13 h/week for a 33-year-old with a 360 W FTP this is a high but plausible load; however the WARN has not been resolved or annotated. Before sending, confirm no individual week exceeds safe TSS ramp-rate thresholds or per-day duration caps that the per-day cap check may have missed at the weekly aggregate level.

### 14. [major] ×1  (road/veteran_podium_chaser)
> Long ride peak duration is cited as '2.3–3.8 hours' in the Weekly Structure section. The race is 68.35 miles; at a competitive pace for a podium-chasing 360 W FTP rider that is roughly 2.8–3.3 hours, so 2.3 h at the low end is marginally short for race-simulation specificity, and 3.8 h at the high end seems high relative to the fueling duration of 3.3 h noted in plan facts. The range should be tightened and reconciled with the fueling figure.

### 15. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section (also in contents) likely contains content appropriate for road criteriums/peloton riding rather than gravel. Even if partially applicable, it needs to be verified and rewritten for gravel-specific skills (loose surface cornering, mud/gravel descending, dropped-bar bike handling, tubeless flat management) before sending.

### 16. [major] ×1  (gravel/time_crunched_parent)
> Off days are listed as 'Tuesday, Monday' — the order is non-chronological mid-sentence, which is confusing but more importantly Monday is listed second despite being the first day of the week. This should read 'Monday, Tuesday' for clarity. While a separate gate checks formatting, this reads as a generation artifact that undermines coach credibility.

### 17. [major] ×1  (mtb/weekend_warrior)
> No MTB-specific skills content is visible (trail braking, cornering technique, technical climbing/descending, line choice) despite this being a mountain bike event. The skills section referenced in the ToC appears to be 'Road Skills,' the wrong discipline entirely.

### 18. [major] ×1  (mtb/weekend_warrior)
> TSS Progression is flagged WARN by the automated checker — a progression irregularity (likely a spike or plateau) is not addressed or explained anywhere in the visible guide text. For a 53-year-old masters athlete, TSS spikes carry injury/overtraining risk.

### 19. [major] ×1  (mtb/weekend_warrior)
> L'Etape Turkey is a road-format gran fondo (tarmac, road bikes) held in Beykoz, Istanbul — yet the plan discipline is coded 'mtb.' If the athlete actually intends to ride this on a road or gravel bike, the MTB-specific framing (and any MTB drills) would be wrong; if she truly races MTB, the event entry may be mismatched. This discipline vs. event conflict must be resolved before sending.

### 20. [major] ×1  (gravel/masters_returner)
> Zone 1 lower bound is listed as '0-94W' but the Zone 2 lower bound is '95-129W', implying Zone 1 tops out at 94W. At 172W FTP, 94W is 54.7% FTP — but the standard convention (and the chart's own % FTP column) shows Zone 2 starting at 56% FTP (≈96W). The Zone 1 ceiling should be ~95W (55% FTP), not 94W. Minor in isolation, but the chart omits the % FTP range for Zone 1 entirely, which is inconsistent with every other zone row and will confuse athletes using a power meter.

### 21. [major] ×1  (gravel/masters_returner)
> Countdown reads '62 days from today' but the plan start date is 2026-07-27 and race date is 2026-09-19. That is 54 days from plan start to race day (8 plan weeks × ~7 days). The '62 days' figure does not correspond to any meaningful date anchor provided in the plan facts (weeks_until_race = 9 × 7 = 63 days from plan-generation date, but the guide says 'from today' without anchoring what 'today' is). This will confuse athletes checking the math and could undermine trust in the entire document.

### 22. [major] ×1  (gravel/masters_returner)
> The guide states the off days are 'Saturday, Thursday, Friday' — that is three consecutive or near-consecutive off days per week, which leaves only four riding days. While four days is consistent with the plan facts, listing Saturday as an off day is odd for a Time-Crunched athlete whose long ride is placed on Sunday: Saturday rest before Sunday long ride is fine, but having Thursday AND Friday also off means intensity sessions are compressed into Monday–Wednesday only. This distribution should be explicitly justified in the guide or the off-day list should be re-checked against the actual calendar to ensure it was not auto-generated incorrectly.

### 23. [major] ×1  (gravel/masters_returner)
> The guide states '4 training days, 4 of which are key sessions' — this is logically contradictory (it implies all 4 days are key, leaving zero easy/recovery rides among the 4 days), and conflicts with a 9 h/week pyramidal plan that should have a majority of easy aerobic volume.

### 24. [major] ×1  (gravel/masters_returner)
> Off days listed as 'Saturday, Thursday, Tuesday' — three off days in a 9 h/week plan leaves only four riding days, which is plausible, but listing Saturday as an off day is unusual and potentially wrong for a masters athlete who typically does the long ride on Saturday or Sunday; more importantly the long ride is listed as Sunday which seems fine, but the off-day trio should be verified against the actual calendar since the guide contradicts itself by later implying Sunday is the long ride day.

### 25. [major] ×1  (gravel/masters_returner)
> Fueling section data (54g carbs/hour, 5.9h duration) is present in the plan JSON but the truncated guide text does not show it applied correctly in the Nutrition Strategy section — the race duration estimate of 5.9h for an 83-mile gravel event with 8,100 ft of climbing is reasonable for a 62-year-old masters athlete, but the guide must surface this clearly so the athlete knows to plan for ~319g total carbs; this cannot be verified from the truncated text.
