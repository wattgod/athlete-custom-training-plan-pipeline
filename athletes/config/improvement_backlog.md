# Improvement backlog — 2026-07-11

**Quality 3.54** · avg coach 6.88/10 · contract pass 88% · load 10.25/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (gravel/veteran_podium_chaser, mtb/ambitious_first_timer, road/veteran_podium_chaser)
> Long ride duration range cited as '3.6-6 hours' in the Weekly Structure section. The upper bound of 6 hours seems high relative to an expected race duration of ~5 hours for 80 miles at podium pace, and the preview check 'Long Ride vs Race Duration' returned PASS — the 6-hour figure should be verified against the actual calendar to ensure it doesn't exceed the cap or alarm the athlete unnecessarily.

### 2. [critical] ×1  (road/time_crunched_parent)
> 'Gravel Skills' appears as a named section in the Table of Contents for a road discipline athlete. This is the wrong discipline content and would immediately undermine athlete confidence and the business's credibility.

### 3. [critical] ×1  (road/time_crunched_parent)
> The automated Zone Distribution check explicitly FAILED. The guide text does not acknowledge or correct this — meaning the zone prescriptions sent to the athlete may be miscalibrated, directly harming training quality.

### 4. [critical] ×1  (gravel/masters_returner)
> FTP zone table is missing the power watt ranges for Zones 1 and 2 in the lower boundary context — Zone 1 shows '0-90W' but Zone 2 shows only '91-123W' with no % FTP listed in the power column, while Zone 3 onward includes % FTP. More critically, Zone 2 lower bound of 91 W is 55% of 164 W, which rounds correctly, but the upper bound of 123 W is 75% of 164 W = 123 W — this is fine. However Zone 1 upper bound of 90 W = 55% of 164 W = 90.2 W — borderline acceptable. Real issue: the % FTP column for Zone 1 is entirely blank in the rendered text, which looks like a rendering/data gap that will confuse the athlete.

### 5. [critical] ×1  (gravel/masters_returner)
> The plan states the athlete's weight as '163 lbs' and height as '5'8"' — but neither weight nor height appear anywhere in the supplied athlete JSON. These values were either fabricated by the generator or pulled from a different athlete's profile. Sending fabricated biometric data to a paying customer is a significant trust and accuracy problem.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is MTB, but L'Etape Poland by Tour de France is a road gran fondo held on tarmac in Zakopane. The plan header, methodology, and all content treat this as a road event — yet the JSON discipline tag says 'mtb'. One of these is wrong and must be reconciled before sending. If the race is correct (road), the discipline tag is wrong and any MTB-specific content (trail skills, MTB handling drills) must be removed. If the athlete truly rides MTB, the race entry is wrong.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> A 'Road Skills' section appears in the table of contents for what is supposedly an MTB plan. Road cornering, group riding, and peloton dynamics are irrelevant — and potentially dangerous advice — for an MTB-tagged athlete expecting trail/technical skills guidance.

### 8. [major] ×1  (road/masters_returner)
> The Zone 1 (Active Recovery) row in the zone chart is missing its FTP % and LTHR % columns — only the absolute watt range (0-96 W) and RPE appear. Every other zone shows '% FTP' and '% LTHR'. This looks like a template rendering gap and will confuse athletes who train by heart rate or percentage.

### 9. [major] ×1  (road/masters_returner)
> The guide states long rides will reach '1.5-2.5 hours' and the 'YOUR BIGGEST OPPORTUNITY' box recommends a ceiling of '3-4 hours.' For a 66-mile L'Etape-style gran fondo in mountainous terrain (Campos do Jordão) this athlete will likely be on the bike 4-5+ hours. The plan's own math acknowledges this is short, but the prescribed ceiling of 3-4 h is still presented as aspirational rather than the minimum — a 62-year-old finisher-goal rider needs at least one confirmed long ride closer to 3 h to de-risk the race-day duration.

### 10. [major] ×1  (road/time_crunched_parent)
> The plan states '5 Years Riding' and 'Intermediate level' but neither field appears in the provided athlete JSON — these values have been fabricated or hallucinated by the generator and cannot be verified.

### 11. [major] ×1  (road/time_crunched_parent)
> The guide lists the athlete's weight as '153 lbs / 69.4 kg' and height as '5'6"' — neither of these fields exist in the athlete data JSON. These numbers are invented and could be wrong or offensive if they don't match the real athlete.

### 12. [major] ×1  (road/time_crunched_parent)
> The countdown reads '99 days from today' — this is a dynamic render-time value that is almost certainly stale or incorrect depending on when the PDF is actually sent; it should either be omitted or locked to a specific reference date.

### 13. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level mislabelled: the athlete has 14 years of riding and is tagged as 'veteran_podium_chaser', yet the guide explicitly calls them 'Intermediate level' ('14 years of cycling experience at Intermediate level'). A 14-year racer chasing a podium should be described as experienced/advanced. This is factually wrong and will undermine the athlete's confidence in the plan's personalisation.

### 14. [major] ×1  (gravel/veteran_podium_chaser)
> Zone 1 power range is missing from the zone chart. The table lists Zone 1 as '0-203W' but omits the % FTP column entry and the LTHR column entry, leaving blank cells. Every other zone has these fields. For a power-first athlete at 370W FTP this is a conspicuous gap (Zone 1 should read <55% FTP / <69% LTHR).

### 15. [major] ×1  (gravel/masters_returner)
> Three preview checks flagged WARN — Zone Distribution, TSS Progression, and Taper Intensity — and none are explained or mitigated in the guide text. Taper Intensity WARN is especially concerning for a masters athlete: if taper intensity is miscalibrated, a 63-year-old risks arriving at the start line either flat or fatigued. These warnings should be resolved before sending, not papered over.

### 16. [major] ×1  (gravel/masters_returner)
> The off-day callout reads 'Off days: Saturday, Thursday' — Saturday is listed as an off day, yet the guide simultaneously tells the athlete that the long ride is on Sunday and strongly encourages adding occasional 3-4 hour long rides. For a masters athlete with only 6 h/week, losing Saturday as a potential long-ride overflow day is a real constraint that contradicts the 'clear a Saturday morning' suggestion in the Biggest Opportunity box. This is internally inconsistent and will confuse the athlete.

### 17. [major] ×1  (gravel/masters_returner)
> The guide text is truncated mid-sentence in the Recovery Protocol section ('Recovery is where…'), meaning the athlete will receive an incomplete document. Content completeness must be verified before sending.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Zone 1 (Active Recovery) power range is listed as '0-104W' but no % FTP range is given, while all other zones show % FTP. This inconsistency will confuse athletes who use a power meter and want to set a ceiling for recovery rides.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> The 'Masters Training Considerations' section is listed in the table of contents but the truncated text never surfaces its content for review. At age 40, this section is directly relevant; if it contains generic or contradictory advice (e.g. recommending high-intensity frequency unsuitable for masters recovery), it could undermine the plan. This section must be verified before sending.

### 20. [minor] ×1  (road/masters_returner)
> The 'GS G Spot' zone label (between Tempo and Threshold) is non-standard nomenclature. While not wrong physiologically, its informal/branded name could confuse the athlete when cross-referencing with their head unit, Zwift, or any external resource — a parenthetical clarification (e.g., 'Sweet Spot') would reduce friction.

### 21. [minor] ×1  (road/masters_returner)
> The profile card says '25 Years Riding' but the methodology justification then calls the athlete 'Intermediate level.' A rider with 25 years of experience is almost certainly not intermediate — this label mismatch could undermine the athlete's confidence in the plan or suggest the system mis-classified them. Even if questionnaire-driven, the copy should reconcile or caveat the discrepancy.

### 22. [minor] ×1  (road/masters_returner)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 10-week plan with (per the preview checks) properly spaced FTP tests. If a retest occurs mid-plan, zones may reset earlier than 6 weeks; the hard-coded '6 weeks' figure is potentially misleading in this specific plan context.

### 23. [minor] ×1  (road/time_crunched_parent)
> Long ride duration is described as '1.5–2.2 hours' which is very short for a 94-mile target event (~6 h race day). While the plan acknowledges the gap, the ceiling figure of 2.2 h should be higher or the athlete should be more strongly directed to extend it.

### 24. [minor] ×1  (road/time_crunched_parent)
> The goal field in the JSON is 'podium' — an ambitious, specific goal — but the guide only references 'Compete' under 'Success looks like,' which misrepresents and undersells the athlete's stated ambition.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> The '5-minute hard opener' in the FTP test protocol is described as 'RPE 8-9' and 'hard but NOT all-out.' The standard Coggan protocol uses this effort to pre-fatigue the anaerobic system, but RPE 8-9 risks fatiguing the athlete before the 20-minute effort. The instruction should clarify it is a hard aerobic effort (~RPE 8, roughly 105-110% FTP) — the current wording is ambiguous and could cause an athlete to go too hard and tank the test.
