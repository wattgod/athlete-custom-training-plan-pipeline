# Improvement backlog — 2026-06-25

**Quality 5.98** · avg coach 7.38/10 · contract pass 75% · load 4.75/plan · 1 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/time_crunched_parent)
> The guide explicitly states 'your peak duration of 1.5 hours' for the long ride, then immediately follows with advice to do '3–4 hour rides' for race-day durability. For a 69.6-mile gravel race likely taking 3.5–5 hours, capping the long ride at 1.5 hours is internally contradictory and factually wrong for the event — this will confuse and underserve the athlete.

### 2. [major] ×1  (road/masters_returner)
> Off days listed as Sunday AND Monday, but long rides are listed as Saturday. For a 7 h/week athlete with 5 training days that leaves only 4 weekdays for all interval, easy, and strength sessions — tight but not impossible. However, the plan explicitly states '5 training days, 3 of which are key sessions,' which is internally consistent only if Sunday is a training day OR Monday is a training day, not both. Two consecutive off days at the start of every week is an unusual structure that contradicts the '5 training days' claim (7 days − 2 off = 5, so the arithmetic holds, but listing Sunday off AND Monday off means the athlete has Tue–Sat to fit 5 sessions with no buffer day mid-week). This needs to be verified against the actual calendar — if the calendar shows a different off-day pattern, the guide text is wrong and will confuse the athlete.

### 3. [major] ×1  (road/masters_returner)
> The zone table omits the % FTP column values for Zone 1 (Active Recovery) and Zone 6 (Anaerobic). Zone 1 shows only the absolute watt range (0–88W) with no % FTP listed, which is inconsistent with every other row. For a masters athlete without a strong power background this gap in the reference table is a usability issue and looks like a generation error.

### 4. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' appears as a section heading in the table of contents. This is a gravel discipline plan; the section should reference Gravel Skills (cornering on loose surfaces, technical descending, singletrack, etc.). Road Skills content sent to a gravel racer is a discipline mismatch and looks like a template error.

### 5. [major] ×1  (gravel/veteran_podium_chaser)
> Athlete experience is labeled 'Intermediate level' in the Performance Expectations paragraph, but the persona is 'veteran_podium_chaser' with 6 years of riding — this should read 'experienced' or 'advanced/experienced racer'. Calling a podium-chasing veteran 'Intermediate' is factually wrong and will undermine the athlete's confidence in the plan.

### 6. [major] ×1  (gravel/veteran_podium_chaser)
> The Weekly Volume automated check returned WARN and was not resolved before this guide reached QA. The guide text claims 15 h/week is matched to the Traditional (Pyramidal) approach, but if actual scheduled weekly hours deviate significantly from 15 h this is a coaching credibility issue. The underlying calendar must be audited to confirm volumes are consistent with the 15 h target before sending.

### 7. [major] ×1  (gravel/ambitious_first_timer)
> Zone Distribution check FAILED in preview. The guide text simultaneously claims '~70% easy riding' (consistent with a polarized model) while prescribing a Time-Crunched methodology, which should skew harder with more Zone 4–5 density and less pure Zone 2 volume. These two claims contradict each other and signal that the actual week-by-week zone allocation may be miscalibrated. A Time-Crunched plan at 7 h/week does NOT produce a 70/30 polarized split — intensity proportion should be higher. This needs to be reconciled before sending.

### 8. [major] ×1  (gravel/ambitious_first_timer)
> Taper Intensity flagged WARN in preview. The guide describes the taper as 'volume drops sharply; short, sharp efforts keep the engine awake' — correct in principle — but the WARN flag suggests the actual calendar workouts may not be executing this correctly (e.g., intensity dropping too far or not far enough). Since the taper directly determines whether the athlete arrives fresh to their A-race, this must be confirmed and corrected in the calendar before sending.

### 9. [minor] ×1  (road/veteran_podium_chaser)
> The profile states '12 Years Riding' and calls the athlete 'Intermediate level,' but the persona is 'veteran_podium_chaser / Experienced racer.' Labeling a 12-year rider with a podium goal as 'Intermediate' undersells the athlete and could feel dismissive or inaccurate to a paying customer.

### 10. [minor] ×1  (road/veteran_podium_chaser)
> The off-days listed ('Off days: Friday, Tuesday') are somewhat unusual for an athlete training 5 days/week, but more importantly the guide mentions '5 training days, 3 of which are key sessions' — that arithmetic (5 training + 2 off = 7) is fine, but having two non-consecutive mid-week off days (Tuesday and Friday) means three consecutive riding days (Wed–Thu–Sat or similar) which deserves at least a brief acknowledgment rather than silent assumption.

### 11. [minor] ×1  (road/veteran_podium_chaser)
> The fueling section in the plan JSON specifies 90g carbs/hour for a 4.2-hour expected race duration, but the truncated guide text visible here does not confirm that race-day fueling guidance (90g/hr) appears in the Nutrition Strategy section. If it is absent from the full document, that is a gap for an athlete with a 4.2-hour race.

### 12. [minor] ×1  (road/veteran_podium_chaser)
> The '101 days from today' countdown is dynamically generated and assumes 'today' is approximately June 25, 2026 (plan start reference date 2026-07-06 is in the JSON). If generation date differs, this number will be wrong in the delivered PDF — a minor but potentially embarrassing factual error to a customer who checks the math.

### 13. [minor] ×1  (road/masters_returner)
> The guide text is truncated mid-sentence ('Extra 200-300 calories in recover...') in the recovery section. This appears to be a rendering/truncation artifact in the document rather than a coaching error, but if it reaches the athlete in this state it looks unprofessional.

### 14. [minor] ×1  (road/masters_returner)
> Weight is stated as '150 lbs (68.0 kg)' but this was not present in the provided athlete JSON — the JSON contains no weight field. The plan has either inferred or fabricated this value. 150 lbs / 68 kg is plausible for a 5'10" masters male but it is an assumed number; if the questionnaire did not capture it, the post-ride recovery macro recommendation ('27g protein + 68–82g carbs based on your 68kg body weight') is built on an unverified figure and should be flagged to the athlete.

### 15. [minor] ×1  (gravel/time_crunched_parent)
> The guide says the athlete is at 'Intermediate level' but the source data only lists '12 years riding' — no explicit experience-level field is shown. Labeling someone as Intermediate after 12 years is plausible but the inference is not acknowledged; a coach would note this is assumed.

### 16. [minor] ×1  (gravel/time_crunched_parent)
> Zone 1 power floor is listed as '0–113W' but no lower bound percentage of FTP is given, while all other zones show a % FTP column — the table is inconsistently filled for Zone 1, which may confuse athletes using a power meter.

### 17. [minor] ×1  (gravel/veteran_podium_chaser)
> The Long Ride duration range cited in the Weekly Structure section ('2.4-4 hours') is oddly precise on the low end and potentially misleading — for a ~3.4h race, a long ride ceiling of 4 hours is fine, but the 2.4h floor figure appears to be a generated artifact rather than a round, coach-natural number. A real coach would write '2.5–4 hours' or simply 'up to 4 hours.'

### 18. [minor] ×1  (road/veteran_podium_chaser)
> The long ride duration ceiling is stated as '4.6-7.6 hours' in the Weekly Structure section. The race is 102 miles — at a competitive pace for a podium-chasing female with 255W FTP that's roughly 4.5-5.5 hours, so 7.6 hours as a ceiling significantly overstates what a peak long ride should be and could alarm or mislead the athlete. The lower bound of 4.6 h (matching the fueling data) is correct; the upper bound needs review.

### 19. [minor] ×1  (road/veteran_podium_chaser)
> The athlete's weight (145 lbs / 65.8 kg / 66 kg) appears in the profile and recovery section but was not listed in the supplied athlete JSON — it was either inferred or fabricated by the generator. If the athlete never provided weight, displaying a specific number is a data-integrity risk and could embarrass the business if the figure is wrong.

### 20. [minor] ×1  (gravel/ambitious_first_timer)
> The long ride duration range cited in the guide ('2.1–3.5 hours') peaks at 3.5 hours for a 7 h/week athlete with a ~6.2-hour race target. A single long ride of 3.5 h is only 56% of race duration — acceptable for a finish-goal first-timer using Time-Crunched, but the guide never explicitly acknowledges or justifies this gap. A brief coaching note explaining why the long ride intentionally undershoots race duration would prevent athlete anxiety and is standard practice.

### 21. [minor] ×1  (gravel/ambitious_first_timer)
> The guide states 'the test result sets ALL your training zones for the next 6 weeks' in the FTP testing section, but this is a 15-week plan with (per the preview) correctly spaced FTP tests. Six weeks between tests is plausible but should align with the actual retest cadence shown in the calendar. If retests are scheduled more frequently, this statement is inaccurate and will confuse the athlete.
