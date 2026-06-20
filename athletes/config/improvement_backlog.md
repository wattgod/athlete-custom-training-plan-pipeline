# Improvement backlog — 2026-06-20

**Quality 3.33** · avg coach 6.43/10 · contract pass 75% · load 9.0/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/weekend_warrior)
> Off days listed as 'Tuesday, Saturday, Wednesday' — that is THREE off days in a 7-day week against a plan that targets 4 training days, leaving only 4 riding days. That arithmetic works, but Saturday is listed as an off day while Sunday is listed as the long ride day, which is internally fine — HOWEVER the JSON confirms 'Off Days Respected: PASS' for only the expected rest days. The real problem is purely logical: listing three off days and simultaneously stating '4 training days, 3 of which are key sessions' is self-consistent only if the count is right, but Saturday as an off day is unexpected for a gravel athlete and may simply be a generation error. More critically, three off days in the same sentence reads as two midweek days (Tuesday, Wednesday) PLUS Saturday, giving only Mon/Thu/Fri/Sun as ride days — that collapses the midweek interval structure. This must be verified and corrected before sending.

### 2. [critical] ×1  (gravel/masters_returner)
> Off days listed as 'Saturday, Friday' — Saturday is also listed as the long ride day ('Long rides: Sunday'). These two statements directly contradict each other. One of the most prominent at-a-glance facts in the plan is internally inconsistent and will immediately confuse the athlete.

### 3. [critical] ×1  (gravel/masters_returner)
> Zone distribution check flagged FAIL in the preview checks, yet the guide text presents the intensity distribution as correct and validated. A FAIL on zone distribution means the actual calendar workouts likely don't match the stated 50/35/15 split. Sending a guide that claims a correct distribution while the calendar violates it is misleading.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete profile and race (L'Étape Ciudad de México by Tour de France) is a ROAD gran fondo event, but the plan JSON specifies 'mtb' as the discipline. The guide includes a 'Road Skills' section heading — if MTB-specific content (trail cornering, technical descending, body position on loose terrain) appears in the full guide, it is entirely wrong for this event. Conversely, if the guide correctly addresses road skills, the discipline tag 'mtb' is erroneous and any MTB-specific drills or equipment recommendations elsewhere will be wrong.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Long ride peak duration of 1.5 hours is cited as the maximum in the weekly structure section ('peak duration of 1.5 hours'). The race is 68.35 miles with an estimated finish time of ~4.3 hours (per the fueling block). A peak long ride of 1.5 hours is grossly inadequate for race-day durability at this distance — this number will alarm and mislead the athlete, and it contradicts the 'YOUR BIGGEST OPPORTUNITY' callout that wisely recommends 3-4 hour rides.

### 6. [critical] ×1  (road/time_crunched_parent)
> Gravel Skills section listed in the Table of Contents for a road discipline athlete. Eroica Germania is a road/vintage cycling event; gravel-specific cornering and handling skills content has no place in this plan and is an embarrassing discipline mismatch that undermines credibility.

### 7. [major] ×1  (gravel/weekend_warrior)
> Zone distribution described as '50% easy / 35% tempo / 15% hard' does not match Sweet Spot / Threshold methodology. True Sweet Spot / Threshold (as opposed to polarized) typically runs something like 60-70% easy, 20-30% sweet spot/threshold, and minimal Z5+. Calling 35% of weekly time 'tempo' and only 15% 'hard' undersells the sweet-spot band and mislabels it. The preview check flagged Zone Distribution as WARN, and this narrative description is likely the source — it will confuse an athlete trying to reconcile the guide text with their actual calendar zones.

### 8. [major] ×1  (gravel/masters_returner)
> The guide includes a 'Road Skills' section in the table of contents — this is a gravel discipline athlete. Gravel-specific skills (loose surface cornering, technical descending, route navigation, singletrack handling) should be featured instead of generic road skills content. This is a wrong-discipline content flag.

### 9. [major] ×1  (gravel/masters_returner)
> Taper Intensity flagged WARN in preview checks, yet the Taper phase description in the guide gives no concrete guidance on what 'short, sharp efforts' means in terms of zone or duration. For a masters returner (age 53), under-specified taper intensity is a real risk — the guide should either quantify this or explicitly acknowledge the warning.

### 10. [major] ×1  (gravel/masters_returner)
> TSS Progression flagged WARN in preview checks but the guide contains no mention of TSS at all — not even a brief explanation of why weekly load is structured the way it is. For a methodology-forward plan that explains zones and adaptation in detail, omitting any acknowledgment of the TSS progression concern is an oversight that leaves the athlete without context if load spikes feel wrong.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> Zone Distribution flagged WARN in preview checks but the guide never surfaces or explains this to the athlete or coach. A 50/35/15 split that triggered a warning could mean too much time in Zone 3 (the very 'gray zone' the guide warns against) or insufficient Zone 2 — either way the guide silently ships a plan that its own QC flagged. This must be resolved or at minimum acknowledged.

### 12. [major] ×1  (gravel/ambitious_first_timer)
> Long-ride duration ceiling of '1.6–2.8 hours' is stated in the Weekly Structure section. For a 69.6-mile gravel race with a projected ~4.3-hour finish, a 2.8-hour maximum long ride is materially short and contradicts the fueling section's own 4.3 h duration figure. The 'BIGGEST OPPORTUNITY' callout softens this but does not fix it — the guide should prescribe at least one 3–3.5 h ride in the Peak phase rather than just suggesting the athlete 'clear a Saturday morning.'

### 13. [major] ×1  (mtb/weekend_warrior)
> Off days are listed as 'Thursday, Saturday, Wednesday' — three days, which is consistent with a 4-day training week, but the order is non-chronological and Wednesday appears after Saturday, which reads as a copy-paste or generation error. A real coach would list days in weekly order (Wednesday, Thursday, Saturday). Minor in isolation but signals a generation artifact that erodes trust.

### 14. [major] ×1  (mtb/weekend_warrior)
> The 'Road Skills' chapter heading appears in the table of contents for what should be an MTB plan (per the discipline tag). If the guide was generated as MTB but contains road skills content, it is wrong for the discipline. If the event is correctly a road gran fondo, then the discipline tag is wrong and any MTB-specific content in the full guide (trail skills, suspension setup, tubeless tire pressure, singletrack cornering) would be sent to a road rider — either way this is a discipline coherence failure.

### 15. [major] ×1  (road/time_crunched_parent)
> Zone 1 (Active Recovery) is missing its %FTP and %HRmax columns in the zone chart — every other zone has them. This is inconsistent and will confuse athletes trying to calibrate easy riding by HR or power percentage.

### 16. [major] ×1  (road/time_crunched_parent)
> Zone GS (Sweet Spot) HRmax range is listed as 92-96%, and Zone 4 (Threshold) starts at 95% HRmax — these overlap by one percentage point. The zone boundary is contradictory and could send athletes training in the wrong zone.

### 17. [major] ×1  (road/time_crunched_parent)
> Fueling section references 70g carbs/hr over 6.8 hours (from the plan JSON), implying a ~476g total carbohydrate target for race day. The truncated guide does not appear to surface this race-duration-specific fueling plan clearly to the athlete. For an 81-mile goal-finish event that will take nearly 7 hours, explicit race-day fueling guidance anchored to that duration is essential and must not be buried or absent.

### 18. [minor] ×1  (gravel/weekend_warrior)
> Post-ride recovery protocol states '34g protein + 85-102g carbs … based on your 85kg body weight,' but the athlete profile lists 187 lbs which converts to 84.8 kg — the rounding to 85 kg is fine, but the carb range (85-102g) implies a 1.0-1.2 g/kg calculation that is reasonable. The inconsistency is that the guide header states the weight as '187 lbs (84.8 kg)' while the recovery section rounds to 85 kg without acknowledgment; this is cosmetically sloppy and could erode athlete trust in the precision of other numbers.

### 19. [minor] ×1  (gravel/masters_returner)
> The 'Strength training: Included (full gym)' callout in the at-a-glance section is assertive, but no information about what the athlete's actual gym access or preference is appears in the athlete data. For a masters returner, prescribing 'full gym' strength work without confirmation risks mismatch with the athlete's real setup.

### 20. [minor] ×1  (gravel/masters_returner)
> The recovery protocol specifies '65-68°F / 18-20°C' for sleep room temperature, but the athlete is based in (or racing in) Tallinn, Estonia — a northern European climate where ambient temperatures in June-August will naturally be in that range or cooler. The advice isn't wrong, but it reads as a generic copy-paste rather than coach-aware guidance.

### 21. [minor] ×1  (gravel/masters_returner)
> The guide text is cut off mid-sentence ('This is where fitness c...') — while truncation may be a rendering artifact, if this reflects the actual delivered document, the Recovery Weeks section is incomplete.

### 22. [minor] ×1  (gravel/ambitious_first_timer)
> The Zone chart is missing the HRmax % column for Zone 1 (Active Recovery) — all other zones have it, creating an obvious blank that looks like a template rendering error.

### 23. [minor] ×1  (gravel/ambitious_first_timer)
> The guide states '2 Years Riding' and calls the athlete 'Intermediate level' in the methodology rationale, but the persona label is 'Ambitious first-timer chasing their first big event.' These are not contradictory but the juxtaposition may confuse the athlete — a one-sentence clarification (e.g., 'first big A-race, not a beginner') would prevent confusion.

### 24. [minor] ×1  (gravel/ambitious_first_timer)
> The FTP test note says 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 9-week plan with (per Phase Progression) tests presumably spaced accordingly. '6 weeks' appears to be boilerplate copy-paste that does not match the actual plan length and could mislead the athlete about retest timing.

### 25. [minor] ×1  (mtb/weekend_warrior)
> TSS Progression check returned WARN in the preview checks — the guide does not acknowledge or explain this to the athlete anywhere, and the coaching text does not address how the progression was adjusted to resolve it. A coach should either fix the progression or transparently note why it deviates.
