# Improvement backlog — 2026-07-02

**Quality 3.16** · avg coach 6.25/10 · contract pass 88% · load 9.62/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/time_crunched_parent, road/veteran_podium_chaser)
> A 'Gravel Skills' section appears in the table of contents (and presumably in the full document) for a road-racing athlete targeting a podium. This is entirely the wrong discipline and will confuse or alarm the athlete — it signals the plan was templated from a gravel product without being properly cleaned.

### 2. [major] ×3  (gravel/time_crunched_parent, gravel/veteran_podium_chaser, mtb/ambitious_first_timer)
> Long ride duration range cited as '2.6–4.3 hours' in the Weekly Structure section — the upper bound (4.3 h) matches the fueling estimate for race duration, which is reasonable, but the lower bound of 2.6 h in Week 1 may be high for a base-phase opener for a time-crunched parent at 8 h/week total. This should be confirmed against the actual calendar week 1 long ride duration.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> The automated preview check explicitly flags 'Weekly Volume: FAIL' — this must be diagnosed and resolved before sending. The guide claims 15h/week throughout but if the calendar weeks violate the volume cap or undershoot targets in a way the preview caught, athletes will receive a plan whose narrative promises don't match the actual schedule. This is the single biggest risk to putting your name on this.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Discipline mismatch — the race is the Chequamegon MTB 40, a mountain bike event on singletrack and forest roads, but the plan contains a dedicated 'Gravel Skills' section. MTB-specific skills (technical singletrack, root/rock navigation, MTB body position, short punchy climbs) are what this athlete needs. Sending a gravel skills section to an MTB racer is both wrong and embarrassing.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: The athlete's discipline is 'mtb' yet the plan is titled 'Montana Gravel Challenge 65mi Training Guide,' includes a 'Gravel Skills' section heading, and is oriented around a gravel event. The race is in the verified DB as a gravel event in Huson, MT. Either the athlete was mis-tagged as MTB when they are actually entering a gravel race, or a gravel plan was generated for an MTB athlete. This must be resolved before sending — skills content, terrain-specific cues, and event framing will all be wrong for one of those two scenarios.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Experience level contradiction: The athlete profile states '1 Years Riding' and the text calls this 'Intermediate level,' but a rider with only 1 year of experience is not intermediate — this is either a labeling error in the template or the persona ('ambitious_first_timer') was misapplied. Calling a 1-year rider intermediate could lead them to underestimate recovery needs and overestimate their ability to handle the prescribed 11h/week load.

### 7. [major] ×1  (gravel/veteran_podium_chaser)
> The plan references 'Road Skills' as a section in the Table of Contents. This is a gravel race — the section should be 'Gravel/Off-Road Skills' covering surface reading, loose-surface cornering, descending on gravel, and pacing on variable terrain. 'Road Skills' language is copy-paste bleed from a road plan template and is wrong for this discipline.

### 8. [major] ×1  (gravel/veteran_podium_chaser)
> Long ride duration range is stated as '4.1–6.8 hours' in the Weekly Structure section. The race is 92 miles; for a podium-chasing athlete the expected finish time is roughly 4–5 hours. A peak long ride of 6.8 hours is disproportionately long relative to race duration and inconsistent with the 'Long Ride vs Race Duration: PASS' preview check — the numbers need to be reconciled.

### 9. [major] ×1  (road/veteran_podium_chaser)
> The TSS Progression check returned WARN in the automated preview. The guide contains no explanation or coaching rationale for the flagged progression anomaly, meaning a paying athlete has no context if weeks feel inconsistent, and the coach cannot stand behind the periodisation without understanding why the flag was raised.

### 10. [major] ×1  (road/veteran_podium_chaser)
> Long ride duration is stated as '5.2-8.8 hours,' but at 13 h/week a single ride of 8.8 hours would consume 68% of the weekly budget, leaving almost nothing for interval and easy sessions. This range appears auto-generated and not sense-checked against the weekly hour target — it risks alarming or misleading the athlete.

### 11. [major] ×1  (road/veteran_podium_chaser)
> The plan guide never references the race distance of 137 miles or estimates finish time, yet the fueling section elsewhere in the JSON specifies an 8.6-hour race duration. No estimated finish window, no race-day pacing guidance, and no acknowledgement that at the athlete's FTP/profile this is a long, multi-hour effort — critical omissions for a podium-chaser.

### 12. [major] ×1  (gravel/time_crunched_parent)
> Off days are listed as 'Saturday, Friday' — the ordering is reversed (Friday comes before Saturday in a week), which reads as a copy/template error. More critically, listing Friday AND Saturday as off days for an 8 h/week athlete with a Sunday long ride compresses all training into a Mon–Thu window, which is an unusual and potentially unworkable schedule that should be verified against the actual calendar before sending.

### 13. [major] ×1  (gravel/time_crunched_parent)
> The FTP Test Frequency automated check returned WARN but no explanation or mitigation is surfaced in the guide text. For a 10-week plan the guide states 'the test result sets ALL your training zones for the next 6 weeks,' implying potentially only one test — this should be addressed transparently (e.g., confirming when a mid-plan retest is or is not scheduled) so the athlete isn't confused.

### 14. [major] ×1  (gravel/time_crunched_parent)
> Athlete weight discrepancy — the plan displays '154 lbs (69.8 kg)' in the profile, but no weight was provided in the athlete JSON. The plan has fabricated or defaulted a weight figure that may not match the athlete, which undermines trust in every weight-based recommendation (recovery nutrition, hydration targets).

### 15. [major] ×1  (gravel/time_crunched_parent)
> Goal field renders as 'Compete' under 'Success looks like' — the athlete's goal is 'podium.' Either the goal was not passed through correctly or was overridden by a generic fallback. A podium goal carries meaningfully different intensity prescription and mental-prep framing than a completion goal.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> Off-day contradiction: the 'Your Week at a Glance' section lists Saturday AND Wednesday as off days, but also lists Sunday as the long ride day. That gives the athlete only 4 training days (Mon, Tue, Thu, Fri) yet the guide says 'Your week has 5 training days.' One of these must be wrong — either an off day is mis-stated or the training day count is wrong. This will confuse the athlete immediately.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> TSS Progression check returned WARN in the preview gate. The guide text never acknowledges or explains a non-standard TSS ramp — for a masters athlete (age 43, sleep 'fair', stress 'moderate') an unexplained TSS spike is a real injury/overtraining risk that a coach should flag or justify in the Phase Progression section.

### 18. [major] ×1  (gravel/masters_returner)
> Weight (156 lbs / 70.7 kg) and height (5'2") appear in the Your Profile box but are NOT present in the athlete data JSON — these values were fabricated or pulled from nowhere. Sending invented biometric data to a paying athlete is a trust-destroying error if she notices the numbers are wrong.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> Fueling strategy is absent from the truncated guide despite fueling data being present in the plan JSON (70g carbs/hr, 5.4h race duration). The nutrition section heading appears in the table of contents but no fueling numbers are surfaced in the visible guide text. If the Nutrition Strategy section is similarly incomplete or omitted, the athlete receives no race-day fueling guidance — a significant gap for a 5+ hour effort.

### 20. [minor] ×1  (gravel/veteran_podium_chaser)
> The guide labels the athlete's experience level as 'Intermediate' in the methodology rationale ('7 years of cycling experience at Intermediate level'). A 32-year-old with 7 years of riding, 15h/week, and an FTP of 285W chasing a podium at an A-priority race should be classified as Advanced or Expert — calling this athlete Intermediate undersells the plan's demands and may confuse the athlete about their training level.

### 21. [minor] ×1  (gravel/veteran_podium_chaser)
> The countdown reads '94 days from today' but the plan start date is 2026-07-13 and race date is 2026-10-04 — that is 83 days from plan start to race day. The countdown figure appears to be calculated from an earlier reference date (possibly generation date) and will look stale or wrong to the athlete when they read it. A dynamic or plan-relative countdown should be used, or the field removed.

### 22. [minor] ×1  (road/veteran_podium_chaser)
> The persona is 'Experienced racer chasing a podium' but the guide twice calls the experience level 'Intermediate.' These labels contradict each other and could undermine athlete confidence in the plan's personalisation.

### 23. [minor] ×1  (road/veteran_podium_chaser)
> The guide's 'Success looks like: Compete' is a truncated placeholder — the goal field was clearly not populated beyond a single word, leaving the athlete's stated goal ('podium') unacknowledged in the motivational framing.

### 24. [minor] ×1  (road/veteran_podium_chaser)
> Weight is shown as '154 lbs (69.8 kg)' but 154 lbs converts to 69.85 kg — acceptable rounding — however the recovery protocol then references '70kg body weight' internally. The inconsistency across sections (154 lbs vs 70 kg) looks sloppy even if numerically close.

### 25. [minor] ×1  (road/veteran_podium_chaser)
> Cool room temperature is given as '65-68°F / 18-20°C' but 68°F = 20°C while 65°F = 18.3°C — the Fahrenheit range doesn't precisely map to the Celsius range stated, a minor but noticeable error in a detail-oriented coaching document.
