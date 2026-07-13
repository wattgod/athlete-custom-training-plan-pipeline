# Improvement backlog — 2026-07-13

**Quality 4.64** · avg coach 6.88/10 · contract pass 88% · load 7.5/plan · 3 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Off days listed as 'Saturday, Friday' — Saturday is a critical gravel-prep day for most athletes and listing it as an off day is almost certainly a generation error. More importantly, Friday AND Saturday off leaves only 5 days available, which must be cross-checked against the calendar; if the calendar contradicts this, the guide is internally inconsistent and will confuse the athlete immediately.

### 2. [critical] ×1  (road/time_crunched_parent)
> Zone 1 (Active Recovery) is listed with a power range of '0-123W' but NO percentage-of-FTP bounds are shown in the table, while every other zone has them. At FTP 225 W, Zone 1 should be ≤55% FTP (≤123 W) — the absolute wattage is correct, but the missing % column entry is inconsistent and will confuse athletes who retest and need to rescale their zones. This is the only zone missing its % FTP anchor.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the guide includes a 'Road Skills' section. This is an MTB athlete preparing for a gran fondo held on mountain-bike terrain. Road skills content (e.g., road cornering, peloton positioning, bunch riding) is wrong for this discipline and will undermine athlete trust. The section must be replaced with MTB-specific technical skills content (trail braking, switchback cornering, loose-surface descending, etc.).

### 4. [major] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> The preview check flagged TSS Progression as WARN, but there is no acknowledgment or mitigation in the guide text. If the TSS ramp is irregular or too steep, the plan may carry an overtraining or staleness risk that should either be corrected in the calendar or briefly explained in the Phase Progression section.

### 5. [major] ×1  (gravel/masters_returner)
> Long ride duration stated as '2.7–4.5 hours' in the Weekly Structure section, but the race is 75 miles on gravel for a finisher-goal athlete likely taking 6+ hours (fueling plan already references 6.2 h). The peak long ride ceiling of 4.5 h may be intentional given the 8 h/week budget, but it is never explained — without justification the athlete will reasonably conclude the plan under-prepares her for a 6-hour day.

### 6. [major] ×1  (gravel/masters_returner)
> The guide includes a 'Gravel Skills' section (listed in the Table of Contents) but the truncated text does not show its content — for a gravel-discipline plan this section must be reviewed to confirm it contains gravel-specific content (loose surface cornering, descending on gravel, bike handling in variable terrain) and not road or MTB content accidentally inserted.

### 7. [major] ×1  (gravel/masters_returner)
> 'Countdown: 68 days from today' is a dynamic field that appears to have been calculated at generation time. The plan start date is 2026-07-27 and race date is 2026-09-19 — that is 54 days, not 68. If 68 days is calculated from an earlier draft date this is stale data that will undermine athlete trust in the plan's accuracy.

### 8. [major] ×1  (road/veteran_podium_chaser)
> Zone 'GS G Spot' is an unprofessional and non-standard label that will confuse and possibly embarrass the athlete. No recognised coaching methodology uses this term. It should be renamed (e.g. 'Sweet Spot' or 'High Tempo') before sending.

### 9. [minor] ×2  (road/veteran_podium_chaser)
> The long-ride duration range cited ('3.1–5.2 hours') is unusually wide and the upper bound of 5.2 hours seems high relative to a 70-mile event expected to take roughly 3.2 hours for a podium-level female athlete. This could send the athlete on unnecessarily long rides in the base phase and should be checked against the actual calendar sessions.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> Zone chart LTHR column is missing for Zone 1 (Active Recovery) — the % LTHR cell is blank. Every other zone has an LTHR range. This looks like a generation dropout and will confuse athletes using heart rate.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> Zone 4 (Threshold) upper boundary is listed as 180W (105% FTP at 172W = 181W), but Zone 5 (VO2max) starts at 181W — this creates a 1-watt overlap/gap ambiguity. More importantly, the Zone 4 label says '94–105% FTP' which by definition includes FTP itself; the upper watt figure (180W) should be 181W to be consistent with the stated percentage ceiling, or the percentage ceiling should be reduced to ~104% FTP. Either way it needs to be airtight.

### 12. [major] ×1  (gravel/ambitious_first_timer)
> FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan and there is only one FTP test (confirmed by preview checks: FTP Test Frequency PASS). Telling the athlete their zones are set for 6 weeks when the plan is 8 weeks is confusing and could cause the athlete to think they need a second test or that the guide is wrong about their plan length.

### 13. [major] ×1  (gravel/veteran_podium_chaser)
> The guide describes the athlete as 'Intermediate level' (in the methodology-selection rationale: '17 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser' — an experienced racer with 17 years of riding should never be labeled Intermediate. This label will undermine athlete confidence and reads as a data-merge error.

### 14. [major] ×1  (gravel/veteran_podium_chaser)
> The automated preview flagged TSS Progression as WARN, yet there is no acknowledgment, mitigation note, or coach override rationale anywhere in the guide. Sending a plan with a known progression warning and no explanation is a quality-control gap that could expose the business to athlete complaints if the load spike causes injury or burnout.

### 15. [minor] ×2  (gravel/veteran_podium_chaser, mtb/ambitious_first_timer)
> The long-ride duration range cited in the Weekly Structure section ('3.4-5.8 hours') is oddly specific and appears to be a raw template variable that was not contextualized or explained — a 5.8-hour peak long ride for a 10h/week athlete is at the high end of plausible and deserves a brief rationale so the athlete doesn't balk.

### 16. [major] ×1  (road/time_crunched_parent)
> The 'Week at a Glance' lists off days as Sunday, Wednesday, and Saturday, with the long ride on Monday. For a time-crunched parent persona, placing the long ride on a Monday (a workday for most people) and making Saturday an off day is backwards — the long ride almost universally belongs on a weekend day. This layout contradicts the persona and is likely to cause the athlete to immediately distrust or ignore the calendar structure.

### 17. [major] ×1  (road/time_crunched_parent)
> The fueling section (from plan JSON) targets 90 g carbs/hour for a 3.6-hour estimated race duration, but the guide text's long-ride range tops out at 5.5 hours. The guide never instructs the athlete to apply the 90 g/h fueling strategy during long training rides that exceed the race duration — leaving a meaningful gap in nutrition guidance for the longest training days.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Zone Distribution preview check explicitly FAILED, yet the guide text contains no acknowledgment, workaround, or corrective note. Sending a plan with a known failed distribution check — without flagging it to the athlete or adjusting the plan — is a coaching error. Either the zone distribution must be corrected in the calendar or the guide must explain the deviation.

### 19. [minor] ×1  (gravel/masters_returner)
> The athlete's weight (145 lbs / 65.8 kg) and height (5'2") appear in the profile section but were not listed in the supplied athlete JSON — these values cannot be verified and may be fabricated defaults rather than athlete-reported data, which is a trust and liability risk.

### 20. [minor] ×1  (gravel/masters_returner)
> TSS Progression check returned WARN in the preview checks — this is not addressed or explained anywhere in the guide. A masters returner with a 'WARN' on TSS ramp should ideally have a brief note (e.g., one week exceeds recommended ramp rate but is followed by a recovery week) so the coach can stand behind it.

### 21. [minor] ×1  (road/veteran_podium_chaser)
> Zone 1 (Active Recovery) and Zone 6 (Anaerobic) are missing % FTP columns in the zone chart — only power wattages are shown. Every other zone has explicit % FTP values. This inconsistency will confuse athletes who update their FTP and need to rescale zones.

### 22. [minor] ×1  (road/veteran_podium_chaser)
> The plan states '6 training days, 3 of which are key sessions' but only two key session types are explicitly described as interval-type (Intervals + Long Ride). Clarity on what the third key session is (e.g. a second interval day or a race-simulation ride) would prevent athlete confusion.

### 23. [minor] ×1  (road/veteran_podium_chaser)
> Zone 1 row in the Zone Chart is missing the % FTP and % LTHR columns (only shows 0-214W and RPE 1-2) — every other zone has those columns filled, making Zone 1 look like a formatting error or data gap that could confuse the athlete

### 24. [minor] ×1  (road/veteran_podium_chaser)
> Athlete is described as 'Intermediate level' in the methodology rationale ('7 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser / Experienced racer chasing a podium' — calling a 7-year racer chasing a podium 'Intermediate' undersells the athlete and is inconsistent with the persona label

### 25. [minor] ×1  (road/veteran_podium_chaser)
> The preview check flagged FTP Test Frequency as WARN — the guide does not surface or address this caveat anywhere; for a 17-week plan a brief note explaining how many tests are scheduled and why the frequency was chosen would resolve the warning and add transparency
