# Improvement backlog — 2026-07-31

**Quality 1.1** · avg coach 5.86/10 · contract pass 62% · load 12.5/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/ambitious_first_timer)
> Zone 1 upper bound is listed as 96W but Zone 2 lower bound is listed as 97W, implying Zone 1 is 0–55% FTP (0–96W). However no percentage range is shown for Zone 1 in the chart, making it inconsistent with the other zones. More importantly, the Zone 2 range shown is 97–131W (56–75% FTP) — this is correct — but the Zone 1 ceiling of 96W equates to ~55% FTP, which is standard. The real error is that the zone table omits the % FTP column entry for Zone 1 entirely, which will confuse athletes without a power meter trying to use RPE/HR to calibrate Zone 1.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the Table of Contents lists a 'Gravel Skills' chapter in a plan for an MTB athlete racing Fairfield Harvest Rush. This is wrong content for the wrong discipline — MTB skills (cornering, braking, technical descending, body position) should replace or supplement any skills section, not gravel-specific technique. This would embarrass the business immediately.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete's discipline is MTB, yet the plan is titled and framed entirely as a gravel plan ('JUST.GRAVEL 50mi Training Guide'), contains a dedicated 'Gravel Skills' section (visible in the table of contents), and uses gravel-specific language throughout. JUST.GRAVEL is the race name, not the athlete's discipline. MTB-specific skills content (technical descending, rooty/rocky trail handling, body position, etc.) is absent; gravel cornering and surface-reading drills are irrelevant to an MTB athlete's preparation.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Long-ride duration is contradictory and misleading: the 'Session Types' section states the peak long ride is 1.5 hours ('don't jump to your peak duration of 1.5 hours in Week 1'), yet the very next 'Biggest Opportunity' call-out urges the athlete to target 3–4 hour rides. A 1.5-hour ceiling is also incoherent for a ~4.8-hour race (the fueling section confirms a 4.8 h estimated duration). The plan cannot simultaneously cap long rides at 1.5 h and recommend 3–4 h rides without explaining the discrepancy.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the athlete is an MTB rider but the guide contains a 'Gravel Skills' section (visible in the table of contents). MTB-specific skills (rock gardens, switchbacks, drop technique, line selection, body-position drills) are absent or replaced with gravel/road content. Sending a gravel skills section to an MTB racer is embarrassing and potentially dangerous if the athlete relies on it.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Race name is 'Wild Gravel' and the database location is Gnowangerup, WA — yet the athlete's discipline is recorded as 'mtb'. Either the discipline tag is wrong (it is a gravel event and the plan should be a gravel plan) or the race entry is wrong. This contradiction must be resolved before sending; the plan cannot coherently serve both disciplines simultaneously.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED in preview but the guide proceeds as if nothing is wrong. No corrective note, no explanation. A flagged zone-distribution failure means the prescribed time-in-zone balance may not match the stated 70/30 polarised intent — the athlete could be systematically trained in the wrong zones for 11 weeks.

### 8. [critical] ×1  (road/masters_returner)
> Table of contents and plan body include a 'Gravel Skills' section. This athlete is a road racer (discipline: road). Gravel cornering, surface-reading, and gravel-specific handling content has no place in a road cycling plan and is actively wrong — it could mislead the athlete and is deeply embarrassing for a paid product.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> The table of contents and guide body contain a 'Road Race Strategy — Category 5 to Category 1 Pathway' section. This athlete is racing a UCI Gran Fondo (gravel), not a road criterium or road race. Cat 5→Cat 1 upgrade pathway content is completely wrong for this discipline and event, and would confuse or embarrass a podium-level gravel racer.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> The guide states '1 Years Riding' and then also describes the athlete as 'Intermediate level' — these two claims contradict each other. One year of riding experience is squarely beginner, not intermediate. Calling a 1-year rider intermediate in the same document is an inconsistency that undermines credibility.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> The TSS Progression check returned WARN in the preview, yet the guide contains no acknowledgment or coaching note about this. If TSS ramps too aggressively the athlete is at injury/overtraining risk; a coach reviewing this would want at least an internal flag or a softened week built in, not silence.

### 12. [minor] ×2  (gravel/ambitious_first_timer, gravel/veteran_podium_chaser)
> The long ride duration range cited in the Weekly Structure section is '2.1–3.5 hours.' For a 7h/week athlete targeting a ~6-hour race, a ceiling of 3.5 hours for the long ride is on the low side and may not adequately prepare the athlete for race duration. This should either be explained (e.g., 'your weekly hour budget limits this') or the upper bound nudged upward if the calendar supports it.

### 13. [major] ×1  (mtb/weekend_warrior)
> Long-ride ceiling of 1.5 hours is grossly insufficient for a 55-mile MTB race projected at ~4.9 hours, and the plan's own callout box only weakly suggests 3-4 hour rides as optional upside rather than treating the gap as a genuine risk. For a 'finish' goal on a 55-mile course, the absence of at least one ride approaching 2.5-3 hours is a structural problem that should be flagged much more forcefully or resolved in the calendar.

### 14. [major] ×1  (mtb/weekend_warrior)
> The zone chart section opens with 'Your FTP: 205W' which is correct, but the narrative description of Zone 2 lists '113-153W' without showing the percentage band (56-75% FTP), creating an inconsistency: 56% of 205 = 115 W, not 113 W. The lower bound of Zone 1 ('0-112W') is therefore also off by ~2 W. Minor in isolation, but the zone chart is the document athletes reference constantly — incorrect numbers erode trust.

### 15. [major] ×1  (mtb/weekend_warrior)
> Three preview checks flagged WARN (Zone Distribution, TSS Progression, Taper Intensity) and none of them are acknowledged or explained in the guide text provided. A paying athlete who notices the WARN flags — or whose coach reviews this — will have no context. At minimum the taper intensity WARN needs a human-readable explanation since taper execution is where age-groupers most commonly go wrong.

### 16. [minor] ×2  (mtb/weekend_warrior, road/masters_returner)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan with (per the FTP Tests: PASS check) presumably one test. '6 weeks' is an oddly specific and potentially inaccurate number that appears to be boilerplate copy-pasted from a different plan length and was not updated.

### 17. [major] ×1  (mtb/weekend_warrior)
> Race-discipline vocabulary is wrong for MTB: terms like 'race-pace fueling practice on long rides' and 'road tilts up' are generic or gravel-coded. An MTB 50-miler in the Southern Lake District involves technical singletrack, likely significant hike-a-bike, and very different pacing dynamics than a gravel race — none of this is acknowledged.

### 18. [major] ×1  (mtb/weekend_warrior)
> Weekly structure says '5 training days, 3 key sessions' but the athlete's hours target is only 5 h/week. For a Time-Crunched plan that is plausible only if individual sessions are very short (~1 h each), yet the plan never reconciles session count with the hour budget, leaving the athlete unable to sanity-check their week.

### 19. [major] ×1  (mtb/weekend_warrior)
> TSS Progression check returned WARN and is never acknowledged or explained to the athlete. If the TSS ramp is too steep it is an injury/overtraining risk; if too flat it is a wasted opportunity. The guide should either confirm it is acceptable or flag it for the athlete.

### 20. [major] ×1  (mtb/weekend_warrior)
> Long ride duration figures are vague and internally inconsistent: the guide mentions '1.6-2.8 hours' as the peak long-ride range, then in the same section recommends 'a single 3-4 hour ride' as more valuable. For a 60-mile race estimated at ~5.5 hours, the 1.6-2.8 h ceiling is almost certainly inadequate and the two figures contradict each other without explanation.

### 21. [major] ×1  (mtb/weekend_warrior)
> Fueling section prescribes 57 g carbs/hour for a 5.5-hour effort. For a masters athlete (48 yr) at a finish-goal pace this is on the low end of current guidance (typically 60-90 g/h for events >2.5 h), but more importantly the race is labelled 'Wild Gravel' with MTB discipline — aid station availability and carrying capacity differ significantly between disciplines and neither is addressed.

### 22. [major] ×1  (road/masters_returner)
> The automated preview check flagged 'Zone Distribution: FAIL' and this is unresolved in the guide text. The methodology section claims ~65% easy volume, but no corrective action or acknowledgment appears. Sending a plan with a known failed zone-distribution check without explanation is a coaching error.

### 23. [major] ×1  (road/masters_returner)
> The TSS Progression check returned 'WARN' and is also unresolved. For a masters returner (58, returning after a layoff), a poorly ramped TSS progression is a meaningful injury and overtraining risk. The guide should either confirm the progression is intentional or show it has been corrected.

### 24. [major] ×1  (road/masters_returner)
> Off days are listed as Sunday AND Saturday, giving a 5-day training week on 8 hours/week — which is plausible but means most sessions are only ~96 minutes. Yet the long ride range cited is 2.9–4.8 hours. A 4.8-hour ride on a weekday (Friday) for a masters athlete with 'fair sleep' and 'moderate stress' is a significant demand that is not flagged or contextualised anywhere in the visible guide text.

### 25. [major] ×1  (gravel/veteran_podium_chaser)
> The methodology rationale states '16 years of cycling experience at Intermediate level.' A rider with 16 years of experience chasing a podium at a UCI-sanctioned event is not 'Intermediate' — this label undersells the athlete and contradicts the persona ('veteran_podium_chaser'). It should read 'Advanced' or 'Expert/Elite' to match the persona and the aggressive goal.
