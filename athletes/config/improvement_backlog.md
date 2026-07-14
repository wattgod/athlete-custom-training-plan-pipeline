# Improvement backlog — 2026-07-14

**Quality 4.24** · avg coach 6.38/10 · contract pass 88% · load 7.25/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Table of contents lists a 'Gravel Skills' chapter. This is an MTB event (Walburg Dirty 30). Gravel-specific skills content is wrong-discipline material and should be 'MTB Skills' or 'Trail Skills.' Sending this to an MTB athlete is embarrassing and undermines plan credibility.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Off-days section reads 'Off days: Thursday, Wednesday, Saturday' — that is THREE off days listed in a 5 h/week, 4-training-day plan. A plan with 4 riding days can only have 3 off days per 7-day week, but listing all three in one breath makes it look like an error (and conflicts with 'Long rides: Sunday' and 'Intervals: Mid-week' implying Tuesday/Thursday are active). The day listing needs to be audited against the actual calendar and stated consistently.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is MTB, but the entire guide — title, race name, skills section header ('Gravel Skills'), fueling strategy, and all contextual language — is written for a gravel event (Sea Otter Europe Gravel). The plan was generated for the wrong discipline template. MTB-specific content (technical descending, trail braking, body position on singletrack, MTB equipment checks) is entirely absent.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Race name and framing reinforce the wrong discipline: the document repeatedly calls this the 'Sea Otter Europe Gravel 75mi' plan. Per the verified race database the event is indeed a gravel race, but the athlete's persona/discipline field is 'mtb'. Either the athlete entered the wrong race or the wrong discipline was tagged — either way, the mismatch must be resolved before sending. Sending a gravel plan to an MTB athlete (or vice versa) is a fundamental coaching error.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> Table of contents includes a 'Gravel Skills' chapter. This is a road-discipline plan for a road race (Cyclotour du Léman). Gravel skills content has no place here and is a clear content-bleed error from another plan template — it will immediately destroy credibility with the athlete.

### 6. [major] ×2  (gravel/time_crunched_parent, mtb/weekend_warrior)
> Zone 1 power range is listed as '0-104W' but no percentage-of-FTP column entry is shown for Zone 1 (the % FTP column appears blank for that row in the excerpt). Every other zone has a % FTP figure. This is inconsistent and looks like a template rendering error — Zone 1 should show '<55% FTP' or similar.

### 7. [major] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> The Zone Distribution preview check returned WARN. The plan text does not explain or acknowledge this warning anywhere — e.g., whether the distribution skews slightly toward Zone 3 in certain weeks and how the athlete should interpret that. Given the G Spot methodology's explicit warning against gray-zone accumulation, a brief acknowledgment would strengthen coach credibility.

### 8. [major] ×1  (mtb/weekend_warrior)
> Fueling section states duration_h = 2.5 hours and the plan data shows hourly_carbs = 70 g/h, but the guide text excerpt ends before the fueling recommendation appears — however the plan JSON flags a 2.5 h fueling window. For a 30-mile MTB race with a 'finish' goal, a 2.5 h race duration estimate may be reasonable but must be explicitly stated in the guide so the athlete understands why 70 g/h is prescribed for that window, not the whole event. If the guide simply says '70 g carbs per hour' without anchoring it to a race-duration estimate, the athlete has no context.

### 9. [major] ×1  (mtb/ambitious_first_timer)
> Weekly Volume and TSS Progression flagged WARN in preview checks, yet the guide text makes no acknowledgement of these warnings or any compensating explanation. At 11 h/week for a first-timer over only 8 weeks, the volume level warrants at minimum a coach note; ignoring the flags risks overtraining for this persona.

### 10. [major] ×1  (mtb/ambitious_first_timer)
> Fueling section references a 6.2-hour race duration (from plan JSON) but the guide body does not surface this number to the athlete in the visible excerpt. The 70 g/h carbohydrate target is never explained or contextualised for the athlete — a first-timer needs explicit race-day fueling guidance tied to expected duration.

### 11. [major] ×1  (mtb/ambitious_first_timer)
> 'Gravel Skills' is listed as a section header in the table of contents. For an MTB athlete this section would need to cover MTB-specific technical skills (rock gardens, drops, switchbacks, MTB cornering). Sending a 'Gravel Skills' module to an MTB racer is both wrong and embarrassing.

### 12. [major] ×1  (gravel/time_crunched_parent)
> Weight (130 lbs / 59 kg) appears in the profile summary but is NOT present anywhere in the athlete's input JSON — the persona data contains no weight field. This number was either hallucinated or pulled from a default. If wrong, the post-ride nutrition prescription (24g protein + 59-71g carbs) is also wrong, and the athlete will notice the discrepancy immediately.

### 13. [major] ×1  (gravel/time_crunched_parent)
> The guide includes a 'Road Skills' section in the table of contents. This athlete is a GRAVEL rider targeting the Gran Fondo Hincapie, so any road-specific cornering, peloton, or criterium content in that section would be discipline-wrong. The truncated text prevents full verification, but the section title alone is a red flag that must be checked before sending.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 and Zone 2 power ranges are missing from the zone table. Zone 1 shows '0–114W' but Zone 2 shows only '115–156W' with no lower-bound confirmation, and critically the % FTP column for Zone 1 is blank — it should read '< 55% FTP'. A paying athlete using a power meter cannot calibrate Zone 1 from this table. This is a real usability gap, not a formatting issue.

### 15. [major] ×1  (road/veteran_podium_chaser)
> The methodology section labels the athlete as 'Intermediate level' despite the profile showing 18 years of riding experience and a podium-chaser persona. This is a factual contradiction of the athlete's own data and reads as a generic, un-personalized copy-paste error.

### 16. [minor] ×1  (mtb/weekend_warrior)
> The guide references the athlete's weight as '148 lbs / 67.1 kg' and height as '5'4"' — neither of these fields appears in the athlete JSON provided. If these values were pulled from a questionnaire they should be correct, but they cannot be verified from plan facts and may be stale or default values left in the template.

### 17. [minor] ×1  (mtb/weekend_warrior)
> The 'G Spot' zone label (Zone GS between Tempo and Threshold) will read as unprofessional or inappropriate to some customers. A term like 'Sweet Spot' is the widely accepted industry label for this zone and avoids any risk of customer discomfort.

### 18. [minor] ×1  (mtb/ambitious_first_timer)
> The 'Ambitious first-timer' persona implies limited race experience, yet the plan prescribes 11 h/week — a substantial training load. The guide never flags or qualifies this for the athlete, which could set unrealistic expectations or cause early burnout.

### 19. [minor] ×1  (mtb/ambitious_first_timer)
> Off days are listed as 'Saturday, Tuesday' in the at-a-glance section, with Sunday as the long ride day. Saturday off + Sunday long ride is a workable structure, but for a first-timer with moderate stress levels, having the long ride the day after an off day and then returning to work on Monday is worth a brief coach note — it is absent.

### 20. [minor] ×1  (gravel/time_crunched_parent)
> TSS Progression check returned WARN in the preview checks. The guide text contains no acknowledgment of this — no caveat about a non-standard ramp rate or rationale for the deviation. A coach's guide should either reflect the warning or explain why it is acceptable for this athlete.

### 21. [minor] ×1  (gravel/ambitious_first_timer)
> The athlete profile lists height as 5'6" and weight as 184 lbs (83.4 kg). A 28-year-old male at 5'6" / 184 lbs with a 209 W FTP implies a W/kg of ~2.5 — unremarkable but not impossible. However, 184 lbs at 5'6" is borderline obese by BMI; if this came from the questionnaire it should be passed through as-is, but the plan nowhere acknowledges that weight management or saddle comfort over 5+ hours may be a relevant consideration for this athlete. Worth a single sentence in the health/blindspots section.

### 22. [minor] ×1  (road/veteran_podium_chaser)
> The 'What Makes This Plan Different' section says '18 years of cycling experience at Intermediate level' — the 'Intermediate level' tag directly contradicts both the persona label ('Experienced racer chasing a podium') and 18 years of experience; it should read 'Advanced' or 'Experienced' at minimum.

### 23. [minor] ×1  (road/veteran_podium_chaser)
> The long ride duration range cited in the Weekly Structure section ('3.4-5.8 hours') is oddly precise and unexplained inline — the upper bound of 5.8 h is plausible for a ~6.8 h race but should be framed relative to race duration so the athlete understands the rationale.
