# Improvement backlog — 2026-07-06

**Quality 4.46** · avg coach 6.75/10 · contract pass 88% · load 7.62/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Profile card states FTP = 113 W but then immediately lists it correctly — however the zone chart upper boundary for Zone 4 is 118 W (105% of 113 W = ~119 W, and the card independently lists '118 lbs Weight' on the same line, strongly suggesting the weight value of 118 lbs has been copy-pasted or confused into the FTP row or vice-versa). More concretely: the athlete's weight (118 lbs) appears in the profile card on what reads as the same visual row/field as FTP, creating an almost certain data-swap embarrassment. This must be audited and corrected — sending a plan that appears to conflate the athlete's body weight with her FTP is a credibility-destroying error.

### 2. [critical] ×1  (mtb/weekend_warrior)
> 'Gravel Skills' appears as a named chapter in the Table of Contents for a mountain bike plan. Gravel cornering and handling content is wrong-discipline material for an MTB racer on singletrack in Bentonville, AR. The chapter must be renamed 'MTB Skills / Trail Skills' and its content audited to ensure it covers MTB-specific technique (body position on descents, braking on loose terrain, switchbacks, rock gardens) rather than gravel-specific skills.

### 3. [critical] ×1  (gravel/weekend_warrior)
> The athlete profile displays FTP as 176W (correct) but also shows '167 lbs / 75.7 kg' weight and '5'8" height' — neither of these fields appears in the athlete data JSON provided (which contains only age 54, FTP 176, hours_target 5). These numbers were either fabricated by the generator or pulled from a different athlete's record. Sending made-up biometric data to a paying customer is embarrassing and erodes trust.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Off days listed as 'Saturday, Thursday' — Saturday is a prime long-ride day for most athletes with 7h/week, and burying the long ride on Sunday while blocking Saturday off is an unusual structure that contradicts the very next line ('Long rides: Sunday'). More critically, the plan gives no rationale, and if the calendar actually uses Saturday as an off day the athlete loses the most available training window. This needs verification against the calendar and a coherent explanation.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the guide includes a 'Road Skills' section (visible in the table of contents) for an MTB athlete. GFNY Pittsburgh is a mountain bike event; road cornering, road group-riding dynamics, and road-specific skills content is wrong for this athlete and undermines credibility.

### 6. [major] ×1  (gravel/ambitious_first_timer)
> Zone 2 lower bound is missing its power percentage label in the zone chart (the '%FTP' column shows '56-75% FTP' for Zone 2 but Zone 1 shows no % FTP value at all — '0-148W' with blank % column). More critically, 148W is only 54.8% of 270W FTP, yet the Zone 2 lower bound is listed as 149W / 56% FTP. These two figures are internally inconsistent: 56% of 270W = 151W, not 149W. Small but the zone chart is a document athletes reference constantly, and a 2W error at the Z1/Z2 boundary will cause confusion on a power meter.

### 7. [major] ×1  (gravel/ambitious_first_timer)
> Zone 3 (Tempo) upper bound is 234W = 86.7% FTP, yet the chart labels it '76-87% FTP' — that is consistent. However the 'GS G Spot' zone is labelled '88-93% FTP' with a range of 235-251W. 88% of 270W = 237.6W, not 235W. The lower boundary of the G Spot zone is 2-3W too low, creating a 2-watt overlap/gap with Zone 3 that will confuse athletes using a power meter.

### 8. [major] ×1  (mtb/weekend_warrior)
> The plan is 12 weeks long starting 2026-07-20, which places the plan end date at approximately 2026-10-11 — correctly aligned with race day. However, the guide tells the athlete her off days are 'Sunday, Saturday, Wednesday' while simultaneously stating 'Long rides: Monday.' For a weekend-warrior persona, placing the long ride on a Monday (a workday for most) while blocking both weekend days as off days is a highly unusual and athlete-hostile structure that should be flagged or explained. No rationale is provided, and no caveat is given that the athlete confirmed this preference.

### 9. [major] ×1  (gravel/weekend_warrior)
> The 'Countdown: 61 days from today' is a dynamic field that will freeze at generation time. If the PDF is opened even a week later it will show a stale, incorrect countdown. The guide should either omit the countdown or clearly label it as 'as of plan generation date' to avoid confusing the athlete.

### 10. [major] ×1  (gravel/weekend_warrior)
> The Zone 1 Active Recovery power range shows '0-96W' but no %FTP label is given, while all other zones include a %FTP column. Worse, Zone 1 upper bound of 96W is 55% of 176W — technically correct as '<55%' but the omission of the %FTP cell will look like a table rendering error and undermine confidence in the zone chart.

### 11. [major] ×1  (mtb/ambitious_first_timer)
> Experience label contradiction: the athlete has '1 Years Riding' but is described as 'Intermediate level' in the methodology section. One year of riding is beginner, not intermediate. This is either a data-mapping error or an incorrect label — either way it affects how the athlete perceives the plan's demands and could lead to overreaching.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Zone Distribution check flagged WARN and FTP Test Frequency flagged WARN in the automated preview, yet the guide text makes no acknowledgment or coach's note about these warnings. A paying athlete receiving a plan with known zone distribution concerns deserves an explanation, not silence.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> The 'Masters Training Considerations' section is listed in the table of contents for a 40-year-old athlete, but the truncated guide text contains no visible masters-specific content in the body. If this section is missing or empty in the final document it is a significant gap for a 40-year-old first-timer who specifically benefits from recovery-frequency guidance.

### 14. [major] ×1  (gravel/masters_returner)
> Experience-level language contradiction: the guide says '21 Years Riding' and calls the athlete 'Intermediate level' in the same breath. Someone with 21 years on the bike should be described as experienced or advanced, not intermediate. This will read as dismissive and inaccurate to the athlete.

### 15. [major] ×1  (gravel/masters_returner)
> Weight/height plausibility flag: 135 lbs (61.2 kg) at 5'2" is a reasonable BMI (~24.7), but the guide states the athlete is a 'masters returner after a layoff' — the weight figure appears to come from the questionnaire and is not contradicted by the JSON, but the height (5'2") is NOT present in the athlete JSON object. The guide is presenting a height field that has no verified source in the provided data, which risks displaying a fabricated or default value to the athlete.

### 16. [minor] ×1  (gravel/ambitious_first_timer)
> The athlete's stated weight of 193 lbs / 87.5 kg is displayed in the profile, but the recovery protocol anchors carb/protein targets to '88kg body weight' — a rounding inconsistency (87.5 kg vs 88 kg). Trivial nutritionally but looks like a data-pipeline rounding artifact that a sharp athlete will notice.

### 17. [minor] ×1  (gravel/ambitious_first_timer)
> The 'Gravel Skills' section is listed in the table of contents but the truncated guide text does not include it in the visible excerpt. If the section exists and contains gravel-appropriate content (cornering on loose surfaces, line choice, tire pressure, climbing out of saddle on gravel) it is fine — but this section must be verified to ensure it does not contain generic road or MTB skills content that would be off-discipline for a gravel event.

### 18. [minor] ×1  (gravel/ambitious_first_timer)
> The zone chart omits explicit power ranges for Zone 1 and the GS 'G Spot' zone upper boundary crosschecks: Zone 1 is listed as '0-107W' but 55% of 195W = 107.25W, so the boundary is fine — however Zone 1 has no %FTP column entry at all, which is an inconsistency in the table layout that could confuse athletes trying to calibrate a head unit.

### 19. [minor] ×1  (gravel/ambitious_first_timer)
> FTP test note says 'The test result sets ALL your training zones for the next 6 weeks' — but the plan is structured in 16 weeks and likely has 2 FTP tests (standard for this plan length). Saying '6 weeks' is an arbitrary and potentially misleading figure that doesn't map to any stated plan structure; a vague 'until your next retest' would be more accurate and less confusing.

### 20. [minor] ×1  (gravel/ambitious_first_timer)
> The recovery section instructs '150% of fluid lost (weigh before/after)' which is correct rehydration science, but immediately follows with 'Compression garments for rides > 3 hours' — for a Miami-based summer training block, compression garments in high heat/humidity may be counterproductive and this blanket recommendation could be flagged as uncomfortable or even harmful without a heat caveat.

### 21. [minor] ×1  (gravel/ambitious_first_timer)
> The athlete's FTP is known (195W, ftp_known: false in JSON is contradicted by the athlete object explicitly listing ftp: 195) — the guide correctly uses 195W throughout, but the ftp_known: false flag suggests the system may have generated an FTP-test protocol unnecessarily or inconsistently; worth verifying the calendar reflects an early FTP test before zones are applied.

### 22. [minor] ×1  (mtb/weekend_warrior)
> The FTP test protocol describes a '5-minute hard opener' but the guide's own introductory sentence says 'There is one maximal effort — the 20-minute test.' The 5-minute opener at RPE 8-9 could reasonably be interpreted by a novice as a near-maximal effort, creating confusion. The phrasing should clarify that the opener is a neuromuscular primer, not a second test effort, more explicitly.

### 23. [minor] ×1  (gravel/weekend_warrior)
> The guide lists 'Years Riding: 2' and labels the athlete 'Intermediate level' in the methodology justification. Two years of riding as a weekend warrior is typically beginner-to-novice; calling it Intermediate may set incorrect expectations about prescribed intensity tolerance, though it does not invalidate the plan structure.

### 24. [minor] ×1  (gravel/weekend_warrior)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan and the athlete already has a known FTP of 176W. This boilerplate language is inconsistent with the plan facts (ftp_known: true, plan_weeks: 8) and may confuse the athlete about when/whether to retest.

### 25. [minor] ×1  (mtb/ambitious_first_timer)
> The guide states '1 years of cycling experience at Intermediate level' — grammatically incorrect ('1 year') and the label inconsistency (beginner vs. intermediate) makes this doubly awkward.
