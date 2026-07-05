# Improvement backlog — 2026-07-05

**Quality 0.7** · avg coach 5.5/10 · contract pass 75% · load 13.25/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/ambitious_first_timer)
> FTP listed as '123 lbs Weight' in the athlete profile card — the plan has conflated the athlete's FTP (123 W) with her body weight, printing '123 lbs Weight (55.8 kg)'. The athlete's actual weight was never provided in the questionnaire data (ftp_known is false for the weight field context, but FTP=123 W is confirmed). This is a factual error that will confuse the athlete and looks like a serious template bug.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> ftp_known is false, yet the plan confidently states 'Your FTP: 123W' in the zones chapter without any caveat that this is an estimated or assumed value. For an athlete whose FTP is not yet confirmed, the guide must clearly label this as an estimate and direct the athlete to complete the scheduled FTP test before trusting the zone numbers.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> Body weight is stated as 118 lbs / 53.5 kg in the profile, but the recovery protocol uses '54kg body weight' for protein calculation (21g protein + 54-64g carbs). The weight itself (118 lbs = ~53.5 kg, rounded to 54 kg) is defensible as rounding, but the profile line reads '118 lbs (53.5 kg)' while the recovery section writes 54 kg — a small but visible internal inconsistency that erodes trust. More critically, 21g protein post-ride is on the low end even for 54 kg; standard guidance is 0.4 g/kg = ~22 g, which is close but the carb range (54-64g) implies a 1:2.5–3 ratio which is reasonable. The real issue is the displayed weight in the athlete profile: the JSON does not include a weight field at all — this figure (118 lbs / 5'8") appears to have been fabricated or pulled from a default template, as no weight was provided by the athlete. Sending a plan that states a specific body weight the athlete never gave is embarrassing and potentially wrong.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Weekly Volume check is a confirmed FAIL in the preview metadata. The guide text itself acknowledges long rides of only '1.5-2 hours,' which is grossly insufficient for a 62-mile MTB event estimated at ~5+ hours. For a 4h/week athlete this is a known structural constraint, but the plan must explicitly reconcile the volume shortfall rather than shipping with a hard FAIL flag — the customer is paying for a plan that won't prepare them adequately without acknowledgment and mitigation baked into the weekly schedule text.

### 5. [critical] ×1  (mtb/weekend_warrior)
> The table of contents and plan body include a 'Gravel Skills' section. This athlete is racing an MTB discipline event (Back Forty Highlander MTB). Gravel cornering, gravel-specific handling drills, or any gravel-framed skills content is wrong-discipline content and is embarrassing to send to an MTB racer.

### 6. [critical] ×1  (road/time_crunched_parent)
> 'Gravel Skills' appears as a chapter in the table of contents. This athlete is a road racer (discipline: road). Gravel skills content — cornering on loose surfaces, bike handling on dirt, etc. — is wrong discipline content and would immediately erode trust in the entire plan.

### 7. [critical] ×1  (road/time_crunched_parent)
> The Zone Distribution preview check is flagged FAIL in the plan facts, yet the guide is about to be sent to a paying customer with no acknowledgement, explanation, or correction of that failure. A failed zone distribution check means the prescribed training stimulus may not match the stated methodology (65% easy, G-Spot/threshold work, VO2 top-end) — this is a core coaching integrity issue.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the plan metadata is flagged as 'mtb' but the Sparkassen Münsterland Giro is a mass-participation road gran fondo held in Münster, Germany. The guide even includes a 'Road Skills' chapter — a direct internal contradiction. Any MTB-specific content (trail skills, technical descending, singletrack drills implied by the discipline tag) is wrong for this athlete and event.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> The guide's own contents list includes a 'Road Skills' section, confirming the event is on-road, yet the plan was built under the MTB discipline flag. One of these is wrong and must be resolved before sending — if the workout calendar contains MTB-specific drills or trail-handling sessions they will be entirely inappropriate.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is 'mtb' but the plan is structured and written as a gravel plan. The race 'Wild Gravel' is in the verified database and the discipline flag from the persona JSON is MTB — these may genuinely conflict, but the plan never resolves it. Sending a plan titled around gravel riding to an MTB athlete (or vice versa) is a fundamental coaching error and acutely embarrassing.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> 'Gravel Skills' section is explicitly listed in the Table of Contents. Gravel-specific cornering, surface-reading, or bike-handling drills are discipline-incorrect content for an MTB athlete and should be replaced with MTB-specific technical skills (trail braking, body position on singletrack, rock gardens, switchbacks, etc.). This is the clearest signal that the wrong template was used.

### 12. [major] ×1  (gravel/ambitious_first_timer)
> Height ('5'8"') and weight ('123 lbs / 55.8 kg') appear in the profile card but neither field exists in the athlete JSON — these values were fabricated by the generator. Weight especially matters because the recovery nutrition recommendation ('based on your 56 kg body weight') is built on a made-up number, which could meaningfully mis-prescribe post-ride fueling.

### 13. [major] ×1  (gravel/ambitious_first_timer)
> Recovery nutrition specifics ('22g protein + 56-67g carbs within 30 minutes (based on your 56 kg body weight)') are derived from the fabricated weight above. Since the real weight is unknown, these gram targets are unsubstantiated and should either be expressed as per-kg guidelines or omitted until weight is collected.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> Zone distribution flagged WARN in the automated preview checks, but the guide text offers no explanation or coach-note acknowledging this. A paying athlete reading the guide has no visibility into why her zone split may look non-standard, which can cause confusion or distrust.

### 15. [minor] ×2  (gravel/ambitious_first_timer)
> Long ride duration range cited as '2.2-3.7 hours' in the weekly structure section — the upper bound (3.7 h) seems high relative to a 43.5-mile gravel finish goal with a ~2.7 h estimated race duration; the peak long ride should cap closer to race duration or modestly above it, not 37% longer. This could set unrealistic expectations or lead to over-reaching in training.

### 16. [major] ×1  (road/veteran_podium_chaser)
> Experience level mislabeled: the guide text says '13 years of cycling experience at Intermediate level' but the persona is 'veteran_podium_chaser' — someone with 13 years chasing podiums is not an intermediate. This is factually inconsistent with the athlete's profile and looks sloppy to an experienced racer.

### 17. [major] ×1  (road/veteran_podium_chaser)
> Long-ride duration range '3.4–5.8 hours' is implausibly wide and the upper bound is suspect. For a 76-mile gran fondo at podium pace (likely ~3–3.5 h finish time) a peak long ride of 5.8 h would be excessive overreach; the lower bound of 3.4 h is more defensible. The range needs to be tightened and justified, or it will confuse the athlete and raise credibility concerns.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> Experience contradiction: the athlete has 1 year of riding but the text labels them 'Intermediate level' — a 1-year rider is a beginner/novice, not intermediate. This mislabeling could mislead the athlete about how hard to push and undercuts trust if they notice it.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The 'Road Skills' section (referenced in the table of contents) is not shown in the truncated text, but its mere presence alongside a 'gravel cornering'-type risk is worth flagging: for a UCI Gran Fondo road event the skills content must be road-specific (pack riding, criterium-style cornering, descent braking). If the template injected any gravel, MTB, or cyclocross skill content it would be wrong discipline content for this athlete.

### 20. [major] ×1  (mtb/weekend_warrior)
> The long-ride duration language is internally contradictory and misleading. The 'Session Types' section states peak long rides are '1.5-2 hours,' then the 'Your Biggest Opportunity' callout urges the athlete to find '3-4 hour' rides — but the Per-Day Duration Caps check passed, implying the calendar never actually schedules those longer rides. The guide is effectively telling the athlete to self-prescribe beyond the plan, which is a liability and a coaching credibility issue.

### 21. [major] ×1  (mtb/weekend_warrior)
> TSS Progression is flagged as WARN in the preview checks, but the guide text contains no acknowledgment of or guidance around this warning. A paying athlete receiving a plan with a known progression anomaly deserves transparency and a coaching rationale or corrective instruction.

### 22. [major] ×1  (road/time_crunched_parent)
> The 'At a Glance' section lists THREE off days (Friday, Thursday, Monday) but the Weekly Structure section states the athlete has 4 training days. Three off-days in a 7-day week leaves only 4 training days, which is consistent, but listing Monday, Thursday, AND Friday as off-days in the same breath is confusingly phrased and likely to cause scheduling errors. More importantly, having Friday and Monday both off sandwiches the weekend rides correctly, but Thursday off mid-week alongside Friday off means two consecutive rest days mid-week — this should be explicitly explained, not left for the athlete to decode.

### 23. [major] ×1  (road/time_crunched_parent)
> Long ride duration is cited as '3.3-5.5 hours' in the Weekly Structure section. For an 8h/week time-crunched parent, a 5.5-hour long ride would consume nearly 70% of the weekly hour budget in a single session, leaving almost nothing for other sessions. This upper bound appears inconsistent with the persona and weekly hours constraint and will alarm the athlete.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> The long-ride duration bracket cited ('3.4–5.8 hours') is oddly wide for a 78-mile road event estimated at ~4.9 h. The low end (3.4 h) is only 69% of race duration, which is borderline acceptable, but the range should be stated more precisely so the athlete knows what the peak long ride actually targets.

### 25. [major] ×1  (mtb/ambitious_first_timer)
> The Zone 2 power range (103–140 W) shows no lower bound percentage of FTP in the table — the % FTP column for Zone 1 and Zone 2 is blank/missing (only Zones 3–6 show % FTP). Athletes without a power meter cannot anchor these zones, and the omission looks like a rendering or generation error.
