# Improvement backlog — 2026-06-29

**Quality 2.96** · avg coach 6.75/10 · contract pass 88% · load 11.38/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/masters_returner, road/weekend_warrior)
> Off days are listed as 'Thursday, Tuesday, Wednesday' in the at-a-glance section. Three off days out of seven leaves only four training days, which is plausible for 7h/week — but listing three named off days in a single sentence reads as if all three are always off simultaneously, which contradicts a 4-training-day week and may confuse the athlete. The phrasing needs clarification (e.g., 'two of the following days are off each week').

### 2. [critical] ×1  (road/veteran_podium_chaser)
> Zone Distribution check FAILED in the preview gate. The guide states '~65% easy' but the actual calendar distribution apparently does not meet this target. This is the single most important methodological constraint of the G Spot methodology and must be verified and corrected before sending — wrong zone distribution undermines every adaptation claim in the guide.

### 3. [critical] ×1  (gravel/masters_returner)
> FTP is listed as '177W' in the zone chart and athlete profile, which is correct — but the plan_facts confirm ftp_known=true (177W is provided). However, the zone chart omits the lower bound % FTP for Zone 1 and Zone 2 is labeled '56-75% FTP' (98-132W). At 177W FTP, 56% = ~99W and 75% = ~133W, so the upper bound of Zone 2 should be ~133W, not 132W — a minor rounding artifact that could confuse a power-meter user trying to reconcile the chart.

### 4. [critical] ×1  (road/time_crunched_parent)
> A 'Gravel Skills' section is listed in the Table of Contents and presumably present in the full document. This athlete is a road racer; gravel-specific cornering, surface-reading, and bike-handling drills are irrelevant and signals to the athlete that the plan was not built for them — the most damaging impression possible for a paying customer.

### 5. [critical] ×1  (road/time_crunched_parent)
> The countdown reads '68 days from today' which — if 'today' is near the guide's generation date of ~late June 2026 — places race day around early September 2026, which is consistent. However, the plan start date is 2026-07-13 (8 weeks before 2026-09-05), meaning the athlete is expected to wait ~2 weeks before starting. The guide never explains this gap and the countdown figure will confuse the athlete about when to begin, directly contradicting the plan_note that the gap is intentional.

### 6. [critical] ×1  (road/time_crunched_parent)
> Off-day structure is incoherent: the guide states 'Off days: Saturday, Sunday' with the long ride on Wednesday — meaning both weekend days are completely rest days. For a time-crunched parent with only 6 h/week, sacrificing both weekend days is almost certainly wrong. Weekends are typically the only realistic slot for the long ride (1.5–2.5 h). Placing the long ride mid-week on a Wednesday and blocking out both weekend days will make this plan unexecutable for the stated persona and will likely confuse or frustrate the athlete on first read.

### 7. [critical] ×1  (gravel/veteran_podium_chaser)
> Body weight contradiction in the Recovery Protocol: the post-ride nutrition prescription references '56kg body weight' but the athlete profile lists '123 lbs (55.8 kg)' — these are essentially consistent with each other, BUT the protein/carb numbers (22g protein, 56-67g carbs) appear calibrated to a much lighter athlete. Standard evidence-based recovery targets for a ~56 kg athlete are 0.3-0.4g protein/kg (~17-22g protein, borderline acceptable) and 1.0-1.2g carbs/kg (~56-67g carbs, acceptable). This is actually marginally defensible, but the rounding and presentation should be cross-checked against the actual formula used — if the system used a different weight at calculation time it could be wrong.

### 8. [major] ×1  (road/veteran_podium_chaser)
> Experience level contradiction: the plan states '10 Years Riding' and calls the athlete 'Intermediate level' in the same breath ('10 years of cycling experience at Intermediate level'). A 46-year-old with 10 years of riding and a 280 W FTP targeting a podium is not Intermediate — the persona is 'veteran_podium_chaser.' This label will undermine athlete confidence and suggests the methodology-selection copy was not properly personalised.

### 9. [major] ×1  (road/veteran_podium_chaser)
> The guide includes a 'Road Skills' section in the table of contents. For a road gran fondo this is fine in principle, but the section must be verified to contain road-specific content only (e.g., cornering on tarmac, descending, peloton positioning) — not gravel or MTB skills, which would be embarrassing given the discipline is road.

### 10. [major] ×1  (gravel/masters_returner)
> The 'Road Skills' section appears in the table of contents for a GRAVEL discipline athlete. Road skills content (e.g., criterium cornering, peloton positioning) would be discipline-mismatched. Even if the section covers general bike handling, the label 'Road Skills' is inappropriate for a gravel gran fondo plan and should be 'Gravel Skills' or 'Bike Handling.'.

### 11. [major] ×1  (gravel/masters_returner)
> The plan states the athlete has '10 Years Riding' experience but the persona is 'masters_returner' (returning after a layoff). The guide never acknowledges the layoff context — it treats the athlete as continuously active. This is a meaningful gap: a returner needs explicit guidance on not over-relying on historical fitness, managing the first weeks conservatively, and watching for injury risk from deconditioning. The layoff is central to the persona and is invisible in the guide text.

### 12. [major] ×1  (road/time_crunched_parent)
> Zone 2 power range is missing its lower % FTP label in the zone table (the '56-75% FTP' entry has no lower-bound percentage shown in the 'Power % FTP' column alongside the watt range), creating an inconsistency a detail-oriented athlete will notice and question.

### 13. [major] ×1  (road/time_crunched_parent)
> The guide states the long ride peak duration is '2.1–3.5 hours.' The upper bound of 3.5 hours exceeds what is achievable in a 6 h/week Time-Crunched plan on a single day without consuming more than half the weekly budget in one ride — plausible only in the peak week, but presenting it as a general range without context is misleading and likely to cause athletes to over-extend early long rides.

### 14. [major] ×1  (road/time_crunched_parent)
> The automated gate flagged FTP Test Frequency as WARN, but the guide never acknowledges or explains this to the athlete. A 17-week plan should include at least two FTP tests; the guide mentions 6-week zone validity but if the plan only has one test (triggering the warning), the athlete will be training on stale zones for the back half of the plan without being told. The warning needs to be resolved or disclosed.

### 15. [major] ×1  (road/time_crunched_parent)
> The guide says 'Your week has 5 training days, 3 of which are key sessions,' but with Saturday and Sunday listed as off days that leaves only 5 weekdays — placing all training Monday–Friday. For a parent with work constraints, 5 consecutive weekday sessions with zero weekend riding is implausible for the persona and contradicts the 'time-crunched parent' archetype, which universally relies on at least one weekend session.

### 16. [major] ×1  (gravel/weekend_warrior)
> Zone 1 Active Recovery row is missing its % FTP and % LTHR columns — only the watt range (0-78 W) and RPE are shown. Every other zone has those columns populated. An athlete using a heart rate monitor has no LTHR anchor for Z1, which is the most-used zone in a Time-Crunched plan's easy days.

### 17. [major] ×1  (gravel/weekend_warrior)
> The off-day callout reads 'Off days: Thursday, Monday, Tuesday' — three consecutive or near-consecutive off days in a 4-training-day week. Combined with the long ride on Saturday and mid-week intervals, this clusters all rest at the start of the week and may leave a new athlete confused about why Monday and Tuesday are both off after a Saturday long ride. The guide text should either explain the rationale (post-long-ride recovery block) or the calendar structure needs a brief justification here so the athlete doesn't assume it's a typo.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> The plan describes the athlete as 'Intermediate level' despite the persona being 'veteran_podium_chaser' with 14 years of riding experience. A 38-year-old with 14 years of riding targeting a podium at an A-race should never be labeled Intermediate — this is misleading and could undermine athlete confidence or cause a coach embarrassment if the athlete notices.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> Zone Distribution flagged WARN in the automated preview checks, but the guide text makes no acknowledgment or explanation of this. For a paying athlete reviewing their plan, a zone distribution that fails the automated check without any coach note is a gap — either the plan text should explain why the distribution is intentional (e.g., pyramidal skews Z2-heavy early) or the check result needs to be resolved before sending.

### 20. [major] ×1  (road/weekend_warrior)
> Long ride peak duration bracket quoted as '2.7–4.5 hours' in the Weekly Structure section. For a 7h/week athlete targeting a ~4.3h race, a 4.5h long ride is at the extreme upper end and the lower bound of 2.7h seems low for a week-1 long ride. More importantly, the range is stated as a flat fact without context — no week number, no phase — making it hard for the athlete to know if any given week's long ride is on track.

### 21. [major] ×1  (road/weekend_warrior)
> Strength training is listed as 'full gym' in the weekly glance, but the guide later describes it as 'cycling-specific strength work' under 60 minutes. 'Full gym' implies a comprehensive resistance program, which may be misleading or inappropriate for a weekend warrior with only 7h/week — a full gym program competes for recovery resources. The description should be consistent.

### 22. [major] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete's experience level as 'Intermediate' ('15 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser' — an experienced racer with 15 years of riding is emphatically not Intermediate. This label contradicts both the persona and the years-riding data and would embarrass us with this athlete.

### 23. [major] ×1  (road/veteran_podium_chaser)
> TSS Progression flagged WARN in preview checks, yet the guide contains no acknowledgment of or guidance around the TSS ramp anomaly. For a podium-chasing veteran who will scrutinize their plan, a silent WARN on progression is a liability — at minimum the recovery-week copy should absorb this, or the calendar weeks need review before sending.

### 24. [minor] ×1  (road/veteran_podium_chaser)
> The VO2max interval example in the Execution Gap section cites '110% FTP' repeatedly as the target for a 4×4 min set, which is correct, but the plan guide also says 'start the first rep at 105%' as a universal rule. For a podium-chasing veteran, starting 5% under on VO2 efforts may not create sufficient stimulus on rep 1 — this is a coaching judgment call but edges toward overly conservative advice for this persona.

### 25. [minor] ×1  (road/veteran_podium_chaser)
> The Zone 2 description reads 'The bulk of your riding lives here' (Zone 2 = Endurance), but the G Spot methodology's easy volume can legitimately be Zone 1–2. This is not wrong, but combined with the Zone Distribution FAIL it may indicate the guide text is over-promising Z2 volume that the calendar does not actually deliver.
