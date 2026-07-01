# Improvement backlog — 2026-07-01

**Quality 4.18** · avg coach 6.88/10 · contract pass 100% · load 9.25/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/time_crunched_parent)
> A 'Gravel Skills' section appears in the table of contents (and presumably in the body) of a plan for a road discipline event. This is the wrong content for this athlete's discipline and would undermine confidence in the entire plan's specificity. It must be removed or replaced with road-appropriate skills content (e.g., criterium cornering, peloton positioning, descending technique).

### 2. [critical] ×1  (road/time_crunched_parent)
> The 'at a glance' off-days list reads 'Thursday, Tuesday, Monday' — three days — which is inconsistent with a 4-training-day week (which implies only 3 off days if a 7-day week is assumed, but listing them out of calendar order and including Monday alongside Thursday and Tuesday suggests a copy-paste or generation error. The ordering is illogical and the combination needs to be verified against the actual calendar before sending.

### 3. [critical] ×1  (road/time_crunched_parent)
> Off days are listed as 'Wednesday, Monday' in the At-a-Glance block. Monday is conventionally the first day of the week and naming it second (after Wednesday) is confusing, but more importantly the JSON preview checks show Off Days Respected = PASS with no Monday/Wednesday specification — if the calendar uses different off days, the guide text contradicts the actual schedule. This must be reconciled with the calendar before sending.

### 4. [critical] ×1  (gravel/masters_returner)
> The zone chart header displays '199W FTP' correctly, but the introductory sentence just before it reads 'Your FTP: 199W .' — acceptable — yet the Zone 2 lower bound is listed as 110W which implies ~55% FTP. Standard 56% of 199W = 111W; this is a rounding non-issue. However, Zone 1 upper bound is 109W (54.8% FTP) and Zone 2 starts at 110W — these are internally consistent. The real critical error is elsewhere: the plan header on page 1 states the athlete's FTP as 199W but the zone narrative intro line reads 'Your FTP: 199W' with a stray period and trailing space, which is cosmetic. The actual critical issue: the Athlete Profile block lists '188 lbs / 85.3 kg' and '5'8"' — none of these figures appear anywhere in the source JSON (the JSON only provides age 53, FTP 199, hours 6). Weight and height were not supplied by the athlete; the plan has fabricated these biometric values. Presenting invented body metrics to a paying customer as if they came from their questionnaire is a factual error that could seriously embarrass the business.

### 5. [critical] ×1  (road/masters_returner)
> Athlete profile displays '150 lbs Weight' — this is the athlete's FTP (150W) being misread or mislabeled as body weight. The plan JSON contains no weight field; the generator has fabricated or cross-contaminated this value. The actual body weight used in recovery calculations (68 kg ≈ 150 lbs) suggests the system may have back-converted FTP watts to a pound figure, which is a nonsensical and confusing error.

### 6. [major] ×2  (gravel/time_crunched_parent, road/time_crunched_parent)
> Long ride duration range stated as '2.5–4.2 hours' in the Weekly Structure section but the plan JSON does not surface those caps explicitly; the upper bound of 4.2 h should be cross-checked against the per-day duration cap pass to confirm it doesn't exceed what was validated — as written it could raise an eyebrow for a 7 h/week athlete (4.2 h is 60% of weekly budget in one ride).

### 7. [major] ×1  (road/time_crunched_parent)
> Off days listed as Thursday, Wednesday, AND Saturday — that is three off days, leaving only four training days, but the text simultaneously says '4 training days, 3 of which are key sessions.' Three off days in a 7 h/week plan is borderline feasible, but listing Wednesday and Thursday as back-to-back off days mid-week while Saturday is also off is an unusual and unexplained structure that will confuse the athlete and may contradict the actual calendar. This needs to be consistent with the calendar or explicitly justified.

### 8. [major] ×1  (road/time_crunched_parent)
> The High Life Stress protocol instructs the athlete to 'eliminate all Zone 4+ work' during high-stress periods. For a Time-Crunched athlete, Zone 4+ intervals ARE the plan — removing them collapses the methodology entirely. The correct guidance for this persona should be to reduce volume and shorten intervals, not eliminate intensity, or at minimum acknowledge the tension with the methodology.

### 9. [major] ×1  (road/time_crunched_parent)
> The zone chart omits %FTP boundaries for Zone 1 (Active Recovery) and the LTHR column is blank for Zones 1 and 6 without explanation. While some coaches omit LTHR for Zone 6, Zone 1 having no %FTP range listed (only a raw wattage) is inconsistent with every other zone row and will confuse athletes who retest and need to rescale.

### 10. [major] ×1  (road/time_crunched_parent)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks.' The plan is only 12 weeks long and the JSON confirms FTP Test Frequency = PASS, implying more than one test. A 6-week validity window is inconsistent with a plan that likely retests mid-plan and will confuse the athlete about when to retest.

### 11. [major] ×1  (road/time_crunched_parent)
> The athlete's stated goal is 'podium,' but the Goals & Blindspots section renders it as 'Success looks like: Compete.' 'Compete' is a generic placeholder that directly contradicts the athlete's A-race ambition of a podium finish — this is both factually wrong and demoralising to a motivated racer.

### 12. [major] ×1  (gravel/masters_returner)
> The Gravel Skills section is listed in the Table of Contents but is entirely absent from the truncated guide text provided for review. For a gravel-discipline athlete this is a material omission — if the section is missing or placeholder-empty in the final document, the plan ships with a gap specific to the discipline it was sold for.

### 13. [major] ×1  (gravel/masters_returner)
> Masters Training Considerations is listed in the Table of Contents but likewise does not appear in the provided text. For a 53-year-old returning athlete this section is especially important (extended recovery windows, hormone-related adaptation differences, injury-risk management) and its absence — or failure to render — would be a notable coaching gap for this specific persona.

### 14. [major] ×1  (road/masters_returner)
> Profile lists '5'8" Height' and '23 Years Riding' — neither field exists in the athlete JSON. These values have been hallucinated by the generator. Sending fabricated personal data to a paying customer undermines trust and could cause confusion or complaints.

### 15. [major] ×1  (road/masters_returner)
> Zone Distribution and FTP Test Frequency both flagged WARN in preview checks but are not addressed or explained in the guide. A WARN on zone distribution for a pyramidal plan targeting a masters returner with a finish goal warrants at least a coaching note; ignoring it silently is a quality gap.

### 16. [major] ×1  (road/weekend_warrior)
> Long-ride duration claim is undersized and potentially misleading. The guide states long rides reach '1.5-2 hours' for a 4 h/week athlete targeting a 65-mile gran fondo with an expected finish time of ~4+ hours. Even within a Time-Crunched framework the longest ride in Build/Peak should push toward 2.5-3 hours to provide any meaningful durability base. Capping the stated peak long ride at 2 hours for a 4-hour event is a coaching red flag and contradicts the 'YOUR BIGGEST OPPORTUNITY' callout that immediately follows it — the plan says 3-4 hours is worth more, yet never prescribes it.

### 17. [major] ×1  (road/weekend_warrior)
> Zone distribution preview check flagged WARN and Taper Intensity flagged WARN, but neither warning is addressed or explained anywhere in the guide text. A paying customer receiving a plan with unresolved automated warnings — especially one tied to taper intensity for an A-priority race — is an embarrassment risk. At minimum the guide should either resolve these or note any intentional deviation.

### 18. [major] ×1  (road/time_crunched_parent)
> '7 Years Riding' appears in the athlete profile card and is then referenced in the methodology rationale ('7 years of cycling experience at Intermediate level'). The JSON has no years-riding field, so this number appears to be fabricated or defaulted — if it is wrong it misrepresents the athlete's background and undermines trust in the profile section.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Off days are listed as 'Wednesday, Friday, Thursday' — three days named in an odd, non-chronological order (Wed, Fri, Thu). For a 5 h/week athlete the plan has 4 training days, which means only 3 off days in a 7-day week. Listing three off days is plausible, but the out-of-order presentation strongly suggests a copy-paste or generation error that will confuse the athlete and erode confidence in the plan's polish.

### 20. [minor] ×1  (road/time_crunched_parent)
> The post-ride recovery callout is truncated in the provided text ('34g protein + 85-102g carbs w') — if this truncation carries into the delivered PDF it would look unprofessional, though this may be a preview artifact.

### 21. [minor] ×1  (road/time_crunched_parent)
> The long-ride duration range cited in the Weekly Structure section ('2.7–4.5 hours') should be cross-checked against the race's expected finish time (~5.2 h per the fueling data). The upper bound of 4.5 h is notably shorter than the projected race duration; while the plan passes the automated 'Long Ride vs Race Duration' check, a coach would normally note this gap explicitly so the athlete isn't surprised on race day.

### 22. [minor] ×1  (road/time_crunched_parent)
> The guide text is truncated mid-sentence in the Recovery Protocol ('150% of f…'), so the rehydration guideline is incomplete. Even if this is a display artefact, the coach cannot confirm the recovery section is correct without seeing the full text.

### 23. [minor] ×1  (road/time_crunched_parent)
> Long ride duration is quoted as '2.7-4.5 hours' in the Weekly Structure section. For an 8h/week athlete targeting a ~3.5h race, 4.5 hours is at the very high end and should be verified against the actual calendar caps (Per-Day Duration Caps = PASS in JSON), but the wide range without context may set incorrect expectations.

### 24. [minor] ×1  (gravel/masters_returner)
> The plan states '13 years of cycling experience at Intermediate level' in the methodology rationale, but the source JSON lists only 'masters_returner' as the persona with no explicit years-of-experience field. If '13 years' was inferred or fabricated rather than taken from the questionnaire, it could be wrong and should be verified against the actual athlete intake data.

### 25. [minor] ×1  (gravel/masters_returner)
> The weekly structure section describes '4 training days, 3 of which are key sessions,' but the at-a-glance schedule lists off days on Monday, Wednesday, and Thursday — leaving Tuesday, Friday, Saturday, and Sunday as training days (4 days). The count is consistent, but having three consecutive off days mid-week is an unusual Time-Crunched pattern that is never explained or justified for this athlete; a brief rationale would prevent athlete confusion.
