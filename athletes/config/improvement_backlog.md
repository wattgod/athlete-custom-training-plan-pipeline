# Improvement backlog — 2026-07-29

**Quality 3.5** · avg coach 6.75/10 · contract pass 75% · load 9.38/plan · 3 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Wrong-discipline content: the guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is racing a gravel event with a goal of finishing — road racing categories and road race tactics are irrelevant and embarrassing to include. These sections must be replaced with gravel-specific content (loose surface cornering, gravel-pace management, aid station strategy, etc.) or removed entirely.

### 2. [critical] ×1  (road/time_crunched_parent)
> The Table of Contents and guide body include a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling amateur road-racing licence classification system — it has zero relevance to a gran fondo (GFNY Chile is a mass-participation event with no USA Cycling cat structure). Including it implies the athlete is a licensed road racer climbing through categories, which is both wrong for this event and potentially confusing or misleading to the customer.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> Table of contents and apparent plan content includes a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road racing licensing concept that is completely irrelevant to a Gran Fondo athlete — Gran Fondos are mass-participation events with no upgrade categories. This content is either hallucinated filler or copied from a criterium/road-race template and is embarrassing and confusing for this customer.

### 4. [major] ×2  (gravel/veteran_podium_chaser, road/veteran_podium_chaser)
> Weekly Volume check flagged WARN in the preview checks. The athlete targets 15h/week — an ambitious load — and no explanation or mitigation is visible in the truncated guide. If the generated plan under-delivers on volume without explanation, or overdelivers and breaches per-day caps, this needs resolution before sending.

### 5. [major] ×2  (road/time_crunched_parent, road/veteran_podium_chaser)
> The 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the plan body. This athlete's goal is simply to finish a gran fondo — there are no USA Cycling categories involved. This content is irrelevant, potentially confusing, and looks like a copy-paste artefact from a road-racing template. It undermines credibility.

### 6. [major] ×1  (gravel/time_crunched_parent)
> Preview check 'Zone Distribution' is flagged FAIL and the guide never resolves it. If the prescribed zone split doesn't actually deliver the stated ~70% easy / 30% hard distribution, the foundational methodology claim is undermined. The guide text asserts the distribution but the automated check says it isn't delivered — this contradiction must be fixed before sending.

### 7. [major] ×1  (gravel/time_crunched_parent)
> Long ride duration language is vague and undersized for the event. The guide says long rides peak at '1.5–2.5 hours' for a race likely to take 5–7+ hours. While the 'Biggest Opportunity' callout acknowledges this, the formal session-type description still lists 1.5–2.5 h as the peak — a customer reading quickly will anchor on that number. For a 75-mile gravel race the guide should recommend at least one 3–4 h long ride be attempted, stated more firmly than a soft suggestion.

### 8. [major] ×1  (gravel/time_crunched_parent)
> The fueling plan (58 g carbs/hour over a projected 6.9-hour race) is specified in the JSON but does not appear anywhere in the truncated guide's Nutrition Strategy section (that section is not shown). If it is absent from the full document, this is a significant omission for an A-priority race with a goal of 'finish' — 6.9 hours of fueling execution is race-critical and must be explicitly addressed.

### 9. [major] ×1  (gravel/masters_returner)
> Zone 1 power floor is missing from the zone table: Zone 1 is listed as '0-99W' with no lower % FTP anchor, while Zone 2 starts at '56% FTP' (100W). At 180W FTP, 56% = ~101W, which is consistent, but Zone 1 shows no % FTP column entry at all — the table is visually inconsistent and will confuse the athlete when cross-referencing head-unit zone setup.

### 10. [major] ×1  (gravel/masters_returner)
> The guide states the long ride peak duration is '2.1-3.5 hours.' For a 78-mile gravel race with an estimated finish time of ~5.1 hours (per the fueling data), a long ride ceiling of only 3.5 hours is low — it means the athlete's longest training ride is under 70% of race duration. While Time-Crunched methodology accepts compressed volume, this range should be explicitly acknowledged and justified so the athlete doesn't feel undertrained on race day; as written it reads like an oversight rather than a deliberate choice.

### 11. [major] ×1  (gravel/veteran_podium_chaser)
> Zone 1 (Active Recovery) has no lower or upper % FTP values listed in the zone chart (shows '0-97W' in watts but the % FTP column is blank), making it inconsistent with every other zone row and potentially confusing for a power-meter user trying to cross-reference.

### 12. [major] ×1  (road/time_crunched_parent)
> The off-day listing reads 'Off days: Tuesday, Monday, Thursday' — three off days listed out of order in a 4-training-day/week plan. This is either a rendering error or a genuine logic conflict (3 off days + 4 training days = 7, which is fine, but listing Monday before Tuesday mid-sentence reads as garbled and may confuse the athlete about which days are actually off).

### 13. [major] ×1  (road/time_crunched_parent)
> The TSS Progression preview check returned WARN but no explanation or mitigation is surfaced anywhere in the guide text. For a 46-year-old high-stress athlete, an unaddressed TSS ramp issue is a real injury/overtraining risk and should at minimum be acknowledged with a note to the athlete.

### 14. [major] ×1  (road/veteran_podium_chaser)
> Experience level labelled 'Intermediate' in the methodology rationale ('14 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser' — an experienced racer. Calling a 14-year veteran with a 305W FTP 'Intermediate' is factually wrong and will erode athlete trust immediately.

### 15. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution check FAILED in the automated preview and the guide text was apparently generated anyway. The failed check is never acknowledged or corrected anywhere in the visible guide text, meaning the zone distribution described (and any workout TSS split) may be wrong for this methodology.

### 16. [major] ×1  (gravel/weekend_warrior)
> Zone table is missing % FTP and % LTHR columns for Zone 1 (Active Recovery). Every other zone has them; Zone 1 shows only the wattage band (0-129W) and RPE. A paying athlete using heart rate or a power meter without a head-unit display will have no reference anchor for the most-used recovery zone. Fix by adding '<55% FTP / <68% LTHR' to the Zone 1 row before sending.

### 17. [major] ×1  (gravel/weekend_warrior)
> TSS Progression flagged WARN in preview checks but the guide text contains no acknowledgment or caveat about this. If the automated checker found a progression anomaly, either the plan should be corrected or the guide should explicitly coach the athlete through the irregular week (e.g., 'Week X is intentionally lower — treat it as an extra recovery stimulus'). Sending a plan with a silent WARN risks the athlete hitting an unexplained volume spike or dip and losing confidence in the plan.

### 18. [major] ×1  (road/veteran_podium_chaser)
> The athlete profile states '11 Years Riding' and then the methodology rationale calls it 'Intermediate level.' An athlete with 11 years of cycling experience and an FTP of 305W targeting a podium is unambiguously Advanced/Expert, not Intermediate. This mislabel undermines credibility.

### 19. [major] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency flagged WARN in preview with no mention in the guide. For a 10-week plan, test frequency matters — if the guide instructs the athlete that 'the test result sets ALL your training zones for the next 6 weeks' but the plan only has one test (or has tests placed poorly), that sentence is misleading or wrong and needs reconciliation.

### 20. [minor] ×1  (gravel/time_crunched_parent)
> FTP Test Frequency check returned WARN. With only 10 weeks, test cadence should be clearly stated. The guide says 'the test result sets ALL your training zones for the next 6 weeks' — but if there are two tests in a 10-week plan the math works; if there is only one, that statement is misleading. The rationale for test scheduling should be made explicit.

### 21. [minor] ×1  (gravel/time_crunched_parent)
> The guide says the plan is 10 weeks but the race is 12 weeks away. The plan_note explains this is intentional (athlete starts 2 weeks later), but the guide itself never tells the athlete this. A customer receiving this could be confused about when to start and might begin immediately, misaligning the taper with race day.

### 22. [minor] ×1  (gravel/masters_returner)
> The 'Road Skills' section heading is visible in the table of contents. For a gravel athlete this should read 'Gravel Skills' and cover surface-specific skills (loose gravel braking, tire pressure selection, rough terrain body position) rather than generic or road-oriented skills content.

### 23. [minor] ×1  (gravel/masters_returner)
> The recovery protocol prescribes '32g protein + 80-96g carbs within 30 minutes based on your 80kg body weight,' but the athlete's listed weight is 176 lbs (79.8 kg) — the rounding to 80 kg is fine, but the prescription should note it scales with ride duration/intensity; a flat number applied to all rides (including easy 45-min sessions) is nutritionally imprecise and could prompt unnecessary caloric surplus on light days.

### 24. [minor] ×1  (gravel/veteran_podium_chaser)
> The non-standard 'GS G Spot' zone (155-165W, 88-93% FTP) is inserted between Tempo and Threshold. While defensible as a training concept, it is not standard polarized nomenclature, is given an informal name that could read as unprofessional to some athletes, and is not referenced in the phase progression or workout execution sections — making it appear orphaned.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> Long ride duration range given as '4.7-7.8 hours' in the Weekly Structure section. At 15h/week with off days Wednesday and Friday, a 7.8-hour long ride is plausible but tight; however the fueling section (from plan JSON) targets 6.8h race duration, so a 7.8h long ride implied as a peak training ride slightly overshoots race duration without explanation — coach should confirm this is intentional race-simulation overshoot and note it explicitly.
