# Improvement backlog — 2026-06-26

**Quality 3.58** · avg coach 6.12/10 · contract pass 88% · load 8.25/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Zone chart is missing the power watt ranges for Zone 1 and the LTHR% columns for Zones 1 and 6, AND — more critically — the Zone 2 lower bound (93W) implies an FTP of ~166W while the stated FTP is 168W; the upper bound (126W) equates to 75% of 168W = 126W which is fine, but Zone 1 upper bound of 92W = 55% of 168W = 92W which is correct. This is marginally acceptable, BUT the Zone chart header lists 'Power % FTP' yet omits the actual percentage column values for Zones 1 and 6, creating an incomplete and potentially confusing chart that a paying customer cannot reliably use.

### 2. [critical] ×1  (gravel/masters_returner)
> The 'Road Skills' section is listed in the Table of Contents for a GRAVEL discipline athlete. Gravel-specific skills (loose surface cornering, descent technique on gravel, obstacle clearance, tubeless repair) should be covered instead of generic road skills content — this is a discipline mismatch that is embarrassing for a gravel-specific plan.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the guide includes a dedicated 'Gravel Skills' section (visible in the table of contents and confirmed by section heading). This is an MTB event. Gravel-specific skills content (gravel cornering, loose-surface handling cues written for drop-bar gravel bikes) is wrong for an MTB racer and will confuse and potentially mislead the athlete.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> The table of contents and guide body include a 'Gravel Skills' section. This is a road racing plan — gravel-specific skills content (cornering on loose surfaces, line selection on gravel, etc.) is the wrong discipline entirely and is embarrassing to send to a road racer.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Off days listed as Thursday, Sunday, AND Tuesday — that is three off days in a 7-day week leaving only four training days, which is consistent with the plan, but Tuesday is a mid-week day typically reserved for intervals in a time-crunched pyramidal plan. More importantly, the guide simultaneously says 'Intervals: Mid-week' while listing Tuesday as an off day — a direct internal contradiction that will confuse the athlete about when to do interval sessions.

### 6. [major] ×1  (gravel/weekend_warrior)
> Zone 2 power floor is wrong. The zone chart lists Zone 2 as '91-123W' but with FTP=165W, Zone 2 at 56-75% FTP should be approximately 92-124W — the lower bound of 91W corresponds to ~55% FTP, not 56%. More critically, Zone 1 is listed as '0-90W', implying Active Recovery tops out at 90W (54.5% FTP), yet the percentage column for Zone 1 is left blank. These absolute watt values appear auto-calculated and are slightly misaligned with the stated percentages, which could send the athlete training at the wrong intensity.

### 7. [major] ×1  (gravel/weekend_warrior)
> Zone Distribution check FAILED in the automated preview. The truncated guide text describes the distribution as 'roughly 70% easy' but the underlying plan apparently does not deliver that ratio. A failed zone distribution check on a Time-Crunched plan — where polarised/pyramidal balance is central to the methodology — is a meaningful red flag that must be resolved before sending.

### 8. [major] ×1  (gravel/masters_returner)
> The guide states '16 Years Riding' at an 'Intermediate level' in the methodology rationale. A male cyclist with 16 years of riding experience should not be labeled Intermediate — this internal contradiction will undermine the athlete's confidence in the plan's personalization.

### 9. [major] ×1  (gravel/masters_returner)
> The long ride duration range given in the Weekly Structure section ('2.7–4.5 hours') is presented without context anchoring it to any specific phase or week, and the upper bound of 4.5 hours for an 8h/week athlete is very high (over 56% of weekly volume in a single ride). While not impossible, no explanation is provided, which risks the athlete over-extending early in the plan.

### 10. [major] ×1  (mtb/ambitious_first_timer)
> Experience level is mislabeled or contradictory. The guide states '1 years of cycling experience at Intermediate level.' One year of experience is beginner, not intermediate. The label will undermine the athlete's trust if they notice it, and it may mean the plan was generated under the wrong persona assumptions.

### 11. [major] ×1  (mtb/ambitious_first_timer)
> Zone Distribution check returned WARN but the guide is being sent without any acknowledgment or resolution. A pyramidal plan that fails its own zone-distribution check may be delivering too much Zone 3 (gray-zone) riding — exactly the mistake the guide itself warns against at length. This must be investigated and corrected before sending.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> The Zone chart omits power percentages for Zones 1 and 2 in the '% FTP' column (cells appear blank in the truncated text). Zone 1 and Zone 2 boundaries must show explicit % FTP values so the athlete can set their head unit correctly, especially since the guide instructs them to update zones after every retest.

### 13. [minor] ×2  (gravel/ambitious_first_timer, mtb/ambitious_first_timer)
> The long-ride duration range cited ('3.2-5.3 hours') should be sense-checked against the race's expected finish time. For a 62-mile MTB event the upper end of ~5.3 hours is reasonable, but the lower anchor of 3.2 hours in the Base phase should be confirmed against the weekly hours cap (10 h) to ensure it doesn't crowd out other sessions.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 (Active Recovery) row in the zone table is missing the % FTP and % LTHR columns entirely — only a power range (0-116W) and RPE are shown. Zone 3 (Tempo) and the GS 'G Spot' row also lack explicit LTHR percentage entries in the excerpt, making the table inconsistent and potentially confusing for an athlete without a power meter who relies on HR.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> The zone table header lists '% FTP' and '% LTHR' columns but Zone 1 shows no percentages at all, and the GS zone lists '92-96% LTHR' which overlaps with Z3's stated '84-94% LTHR' upper bound — the LTHR ranges are not cleanly delineated and could send the athlete into the wrong zone when using heart rate.

### 16. [major] ×1  (road/veteran_podium_chaser)
> The athlete's weight (154 lbs / 69.8 kg) and height (5'2") appear nowhere in the questionnaire JSON yet are stated as fact in the profile. These figures look auto-populated from a placeholder or another athlete's record. If wrong, every body-weight-based recommendation (recovery nutrition, hydration) is calibrated to the wrong person.

### 17. [major] ×1  (road/veteran_podium_chaser)
> The guide states '9 Years Riding' and labels the athlete 'Intermediate level' in the same breath as the persona label 'Experienced racer chasing a podium.' Nine years and podium ambitions with a 310 W FTP is not an intermediate rider — the label contradicts the persona and could undermine the athlete's confidence in the plan.

### 18. [major] ×1  (gravel/time_crunched_parent)
> Zone 1 (Active Recovery) power range is listed as '0-106W' but no percentage-of-FTP anchor is given (unlike every other zone), making it harder for the athlete to adjust after a retest. Zone 3 (Tempo) similarly omits power watts entirely — only '145-167W' appears in the Power column but the cell appears truncated/missing in the rendered table, which must be verified before sending.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Three preview checks flagged WARN (Weekly Volume, TSS Progression, Taper Intensity) but the guide text contains no acknowledgement or mitigation. If the calendar backing this guide has volume or taper problems, the guide copy alone cannot paper over them — the underlying calendar weeks must be reviewed and either fixed or the WARNs explained before this is sent to a paying athlete.

### 20. [minor] ×1  (gravel/weekend_warrior)
> FTP Test Frequency is flagged as WARN. Over a 9-week plan with a known FTP, the guide states test results 'set zones for the next 6 weeks,' which may not account for a mid-plan retest that the WARN flag suggests is either missing or poorly timed.

### 21. [minor] ×1  (gravel/weekend_warrior)
> Off-days listed as 'Tuesday, Monday, Sunday' in the at-a-glance section — listing them out of calendar order (Tuesday before Monday) reads as a generation artifact and looks sloppy to the athlete.

### 22. [minor] ×1  (gravel/masters_returner)
> The post-ride carbohydrate recovery target (74–89g) is stated but the derivation (per kg formula) is not shown; a masters athlete tracking recovery nutrition would benefit from the calculation being transparent rather than appearing as an arbitrary range.

### 23. [minor] ×1  (mtb/ambitious_first_timer)
> The guide refers to '6 training days, 3 of which are key sessions' but the athlete's off days are listed only as Wednesday. Six training days with one off day leaves only one rest day per week for a first-timer with 1 year of experience — this deserves an explicit note or cross-check against the actual calendar to confirm a second rest day exists.

### 24. [minor] ×1  (gravel/ambitious_first_timer)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 10-week plan with apparently one scheduled retest. Saying '6 weeks' is an arbitrary number that doesn't match the plan length and may confuse the athlete about when to retest.

### 25. [minor] ×1  (gravel/ambitious_first_timer)
> Zone distribution preview check flagged WARN and FTP Test Frequency flagged WARN — neither issue is addressed or explained anywhere in the guide text provided, leaving a known automated concern unacknowledged for the reviewer (though these may be handled elsewhere in the calendar).
