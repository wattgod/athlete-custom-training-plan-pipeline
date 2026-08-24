# Improvement backlog — 2026-08-24

**Quality -0.62** · avg coach 5.88/10 · contract pass 50% · load 16.25/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/veteran_podium_chaser)
> Table of contents includes 'Category 5 to Category 1 Pathway' — a racing-license progression section that is completely irrelevant to a masters athlete whose stated goal is simply to finish a 99-mile gran fondo. This content is clearly boilerplate carried in from a racing-focused template and would confuse and potentially embarrass this customer.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete persona/discipline is tagged 'mtb', yet the race (Gravelista, Victoria AU) is a verified gravel event, and the guide includes a 'Gravel Skills' section. The plan must be one or the other — an MTB plan with gravel skills bolted on is incoherent and embarrassing to send.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> The equipment checklist says 'Bike — gravel or similar' which directly contradicts the 'mtb' discipline tag. If this is truly an MTB plan the equipment guidance is wrong; if it is a gravel plan the discipline metadata is wrong. Either way, the athlete receives contradictory guidance on what bike to bring to their race.

### 4. [critical] ×1  (road/masters_returner)
> Plan start date mismatch: The JSON states plan_start_date = 2026-08-31, but the guide header says the plan is 13 weeks and the race is 2026-11-28. Counting back 13 weeks from 2026-11-28 gives a start of ~2026-09-01, not 2026-08-31. One day off is minor, but the guide also references '96 days from today,' which is an un-rendered dynamic placeholder that will print a wrong or stale number for any reader who opens the PDF after generation day — this is embarrassing and must be resolved before sending.

### 5. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This is a racing-license progression framework for competitive road racers — it is completely irrelevant and potentially confusing for a weekend warrior whose stated goal is simply to finish. It is the wrong discipline-persona content and would undermine credibility with a paying customer.

### 6. [critical] ×1  (road/weekend_warrior)
> Zone Distribution check FAILED in the automated preview but the plan was still passed to QA without the underlying issue being resolved. The guide text states '~70% Zone 1-2' which may contradict the actual week-by-week distribution. A zone-distribution failure on a Time-Crunched plan (which relies on polarised/intensity-dense structure) is a meaningful methodology error, not a cosmetic one.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> Weekly Volume check FAILED (preview_checks). The guide text does not surface or explain this discrepancy — an 8 h/week athlete receiving a plan with incorrect weekly volumes is the most fundamental coaching error and must be resolved before sending.

### 8. [critical] ×1  (gravel/time_crunched_parent)
> Discipline mismatch: the guide includes a 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This is a GRAVEL event (UCI Gran Fondo Loutraki). Road-racing category progression and road race tactics are wrong-discipline content that would confuse and embarrass the coach in front of a paying gravel athlete.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> Per-Day Duration Caps check is flagged FAIL in the preview checks, meaning at least one day in the calendar exceeds the permitted session length for a 15 h/week athlete. The guide text does not acknowledge or correct this — if sent as-is, the athlete will receive a day with an illegal (likely injury-risk) duration that the automated gate already flagged.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Section titled 'Gravel Skills' appears in the Table of Contents for an MTB athlete. This is a discipline mismatch — the athlete is racing the Walburg Dirty 30 on an MTB, not a gravel bike. Gravel-specific skills content (e.g., gravel cornering, loose-over-hard surface technique framed as gravel riding) does not belong here. The section must be replaced with MTB-specific trail skills (singletrack cornering, technical climbing, drop/rooted-section technique, etc.).

### 11. [critical] ×1  (mtb/weekend_warrior)
> Wrong discipline content: The ToC and guide body include 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is an MTB gran fondo rider. Road racing categories, road cornering/pack-riding skills, and a Cat 5→1 upgrade pathway are irrelevant and will actively confuse her. MTB-specific skills (technical descending, climbing traction, trail braking, singletrack positioning) are absent.

### 12. [critical] ×1  (mtb/weekend_warrior)
> Long ride ceiling of 1.5 hours is grossly inadequate for a ~5.75-hour race. The plan itself acknowledges this gap but only as a soft 'YOUR BIGGEST OPPORTUNITY' note, then lists 1.5 h as the peak long ride duration. For a finish-goal weekend warrior at 4 h/week, the long ride should reach at least 2.5–3 h during peak. Sending this athlete to a 78-mile mountain ride with a longest training ride of 1.5 h is a coaching failure.

### 13. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED pre-flight and the problem is visible in the text: the guide states '~70% Zone 2' for a Time-Crunched methodology, but Time-Crunched (Carmichael-style) is characteristically high-intensity-dense with a lower Z2 percentage than traditional periodisation. The stated distribution contradicts the declared methodology and will mislead the athlete about how hard her interval days need to be.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> Race name in the plan header and throughout is 'Gravelista 80mi' — the discipline is unambiguously gravel, yet the JSON persona discipline is 'mtb'. This suggests the template used is the wrong one for the discipline, meaning MTB-specific content (e.g. technical trail skills, suspension setup) may be absent or substituted with gravel content inappropriately.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency flagged WARN in preview checks but is not addressed or explained anywhere in the guide text provided. For an athlete with no known FTP on an 8-week plan, a single Week 1 test with no mid-plan retest could mean 7 weeks of potentially drifting zone targets — the guide should acknowledge this and provide guidance.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> Weight (152 lbs / 68.9 kg) and height (5'2") appear in the guide, but the athlete JSON contains no weight or height fields — these values appear to have been fabricated or pulled from a wrong profile. Sending a plan with invented biometric data to a paying customer is a serious error.

### 17. [major] ×1  (road/masters_returner)
> Long-ride cap described as '1.5–2.5 hours' in the Weekly Structure section. For a ~6.7-hour race (per the fueling data), this ceiling is dangerously low. The plan itself acknowledges the gap ('your long rides are shorter than ideal') but then only suggests 3–4 hour rides as a fix — which still falls well short of adequate race-specific preparation for a 99-mile event. The contradiction between the stated cap and the recommended fix, and the failure to resolve it within the plan's own structure, should be corrected rather than just flagged to the athlete.

### 18. [major] ×1  (road/masters_returner)
> Fueling recommendation of 56 g carbs/hour is on the low end for a ~6.7-hour effort at goal intensity, but more importantly the guide text shown does not surface a concrete race-day fueling plan tied to the verified 6.7-hour estimated duration — a critical omission for a finish-goal masters athlete doing a 99-mile event.

### 19. [major] ×1  (road/weekend_warrior)
> The long ride is described as peaking at '1.5 hours' — for a 68-mile race with an estimated finish time of ~4.6 hours, this is a severe mismatch. The plan acknowledges the shortfall but only vaguely suggests the athlete 'try to fit in 1-3 longer rides per month.' A coach-authored plan should provide concrete guidance (e.g., specific weeks where a 2.5–3 hour ride is programmed) rather than hand-waving the single most important endurance stimulus.

### 20. [major] ×1  (road/weekend_warrior)
> Off days listed as 'Tuesday, Monday, Wednesday' — three separate days listed in a non-chronological, confusing order for a 4-hour/week athlete who presumably rides 3-4 days. If the athlete truly has Monday, Tuesday, AND Wednesday off, that means all riding is compressed into Thursday–Sunday, which is an unusual and unexplained structure that should be explicitly justified.

### 21. [minor] ×2  (road/veteran_podium_chaser, road/weekend_warrior)
> 'Road Skills' and 'Road Race Strategy' sections are listed in the table of contents. While road-appropriate, the content should be verified to contain gran fondo-specific guidance (pacing, neutralised starts, aid stations, bunch dynamics at a mass-participation event) rather than generic criterium or road race tactics that don't apply to this event type.

### 22. [major] ×1  (gravel/time_crunched_parent)
> Taper Intensity flagged WARN. The guide's taper description ('volume drops sharply; short, sharp efforts keep the engine awake') is generic and does not specify the intensity or duration of those efforts. For a goal-finish athlete this should be explicit enough to execute without ambiguity, and the WARN must be resolved or acknowledged.

### 23. [major] ×1  (gravel/time_crunched_parent)
> Zone Distribution flagged WARN. The guide claims 'roughly 75%' in Zone 1-2 (pyramidal), but the preview check raised a warning. If the actual weekly TSS/time distribution in the calendar does not match the stated 75% easy / pyramidal promise, the text is making a claim the plan cannot back up.

### 24. [major] ×1  (road/veteran_podium_chaser)
> Countdown math is wrong or misleading. The plan states '76 days from today' on a plan start date of 2026-08-31 with a race date of 2026-11-08. August 31 to November 8 is 69 days, not 76. A hardcoded or mis-rendered date delta will undermine athlete trust in the plan's accuracy, especially given the guide's own warning that 'a wrong date means your entire taper and peak will be off.'

### 25. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity is flagged WARN in the preview checks. The guide's taper description ('short, sharp efforts keep the engine awake') is generic and gives no specifics about what intensity or volume is prescribed during taper. For a podium-chasing athlete this ambiguity is a meaningful coaching gap that should be resolved before sending.
