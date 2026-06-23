# Improvement backlog — 2026-06-23

**Quality 2.05** · avg coach 6.5/10 · contract pass 75% · load 12.38/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/time_crunched_parent)
> Off days listed as 'Thursday, Tuesday, Saturday' — that is three off days in a 7-day week, leaving only four training days, but the text itself says 'Your week has 4 training days, 3 of which are key sessions.' Listing Saturday as an off day directly contradicts the Long Ride Day being on Sunday with no Saturday buffer issue, but more importantly this athlete has a 5h/week budget across only 4 days, which is tight but workable — the real problem is the off-day list reads as auto-generated noise that is internally inconsistent: Tuesday and Thursday off on the same week effectively clusters all riding into Mon/Wed/Fri/Sun. This needs to be verified against the actual calendar and stated clearly, not listed as three scattered days that may confuse the athlete.

### 2. [critical] ×1  (road/time_crunched_parent)
> Road Skills section is listed in the table of contents. This is a road cycling plan, which is correct, but the truncated text ends before that section appears — if it contains gravel-specific or MTB-specific cornering or trail content (a known auto-generation failure mode), it would be embarrassing. The section title alone is fine for road, but the content must be verified before sending.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Discipline is MTB but the guide's Road Skills section (visible in the table of contents) and the indoor/outdoor balance advice frame the plan entirely around road/group-ride dynamics ('wind, terrain changes, group dynamics'). MTB-specific skills — technical trail riding, cornering on loose surfaces, braking technique, body position on descents — are absent. A Gran Fondo Başkent on an MTB course demands trail-skills practice, not road-peloton framing.

### 4. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution preview check explicitly FAILED, yet the guide text nowhere acknowledges or corrects this. The stated distribution (65% easy / 25% tempo / 10% hard) may not match what the calendar actually prescribes. Sending a plan to a paying athlete where a known internal check has failed — without explanation or fix — is unacceptable.

### 5. [critical] ×1  (road/time_crunched_parent)
> Zone 1 (Active Recovery) row in the zone table is missing both a %FTP range and a %HRmax range. Zone 2 shows '56-75% FTP' but Zone 1 shows only '0-93W' with no percentage column filled. This is inconsistent and confusing — the athlete cannot use the table if they ride by percentage rather than absolute watts (e.g. after an FTP retest changes their zones).

### 6. [critical] ×1  (gravel/masters_returner)
> Zone Distribution is flagged FAIL in the preview checks, yet the guide states '70% easy / 10% tempo / 20% hard' as the Time-Crunched distribution without any acknowledgment or correction. Sending a plan with a known failing automated check — especially one about the core training stimulus — is unacceptable.

### 7. [critical] ×1  (road/masters_returner)
> Three off days are listed as 'Thursday, Saturday, Friday' — that is three days off in a 9 h/week plan, which contradicts the stated 4 training days, and the ordering (Thu, Sat, Fri) is non-chronological and almost certainly a generation artifact. A 9 h/week athlete typically has 2 rest days; listing three — and listing them out of calendar order — will confuse the athlete and may mean the calendar itself has the wrong structure.

### 8. [critical] ×1  (road/masters_returner)
> The athlete has 9 years of cycling experience yet is labelled a 'Masters returner after a layoff' with an Intermediate level — fine — but the guide states '9 Years Riding' as a raw data point while simultaneously treating the athlete as a relative beginner in tone and volume (4 training days, very cautious long-ride ceiling of 2.7-4.5 h for a 52-mile event). More importantly, the long-ride range of 2.7-4.5 hours is stated in the Weekly Structure section without any context tying it to this athlete's specific race duration estimate, making the upper bound feel arbitrary rather than coached.

### 9. [major] ×2  (road/time_crunched_parent)
> TSS Progression check returned WARN in the preview gates but the guide contains no acknowledgment or mitigation of this. If the TSS ramp is irregular or has a problematic spike, sending the plan without addressing it risks overtraining or an athlete injury — and it means we are knowingly shipping a flagged plan.

### 10. [major] ×2  (road/time_crunched_parent)
> Athlete weight (190 lbs / 86.2 kg) and height (5'8") appear in the profile but were NOT present in the plan facts JSON — these values were either pulled from a questionnaire not shown or fabricated by the generator. If fabricated, the post-ride nutrition numbers (34g protein, 86-103g carbs) derived from '86kg body weight' are built on an unverified figure. This must be confirmed against the athlete's actual questionnaire response before sending.

### 11. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN in preview but the guide provides no acknowledgment or explanation. At 15 h/week for a 9-week plan, if the generated calendar is under- or over-delivering on volume, the athlete receives no transparency about this discrepancy. The guide should either confirm what weekly volumes are prescribed or explain any intentional deviation.

### 12. [major] ×1  (gravel/veteran_podium_chaser)
> The athlete is described as 'Intermediate level' in the methodology justification section, which directly contradicts the persona label 'Experienced racer chasing a podium' with 6 years of riding and a 345 W FTP. This is factually inconsistent with the athlete's profile and undermines credibility if they notice it.

### 13. [major] ×1  (road/time_crunched_parent)
> '8 Years Riding' is displayed under 'Your Profile' and then cited in the methodology rationale ('8 years of cycling experience at Intermediate level'). The plan JSON shows hours_target = 8, not years riding. This strongly suggests the generator confused the hours field with a years-of-experience field. If the athlete actually has a different ride history, this is factually wrong and undermines trust.

### 14. [major] ×1  (gravel/masters_returner)
> Intensity distribution stated as '70% easy / 10% tempo / 20% hard' is wrong for Time-Crunched methodology. The canonical Time-Crunched distribution is polarised toward high intensity — typically ~50% easy / 0–5% tempo / 45–50% hard — not a pyramidal model. Sending a guide that misrepresents the methodology the athlete paid for undermines trust and will confuse them when they see the actual interval-heavy calendar.

### 15. [major] ×1  (gravel/masters_returner)
> Recovery section references '72kg body weight' for the post-ride nutrition calculation, but the athlete profile records weight as 158 lbs = 71.7 kg. The text then shows the protein/carb numbers calculated off 72 kg, which is close but the stated figure in the prose is '72kg' while the profile header correctly says '158 lbs (71.7 kg).' More critically, the truncated sentence ends mid-word ('flu—') suggesting a generation cut-off — the rehydration instruction is incomplete and must be verified as complete in the full document.

### 16. [major] ×1  (road/time_crunched_parent)
> The plan says 'The test result sets ALL your training zones for the next 6 weeks' in the FTP testing section. This is a boilerplate statement that does not match an 8-week plan — it should say something like 'the remainder of your plan' or reflect the actual retest schedule. Telling an athlete their test covers 6 weeks in an 8-week plan is confusing and undermines trust.

### 17. [major] ×1  (mtb/weekend_warrior)
> The Weekly Structure section states 'Your week has 2 training days, 2 of which are key sessions.' Two training days total with two key sessions leaves zero easy/recovery riding days in the weekly structure description — this is internally contradictory and will confuse the athlete. The schedule header mentions Saturday long ride plus mid-week intervals, implying at least 3 active days; the text needs to reconcile these numbers.

### 18. [major] ×1  (mtb/weekend_warrior)
> TSS Progression and Taper Intensity both flagged WARN in the preview checks, yet the guide text contains no acknowledgment or mitigation of these warnings. A plan emailed to a paying customer should either explain why the deviation is intentional or show how it is addressed — silently shipping two WARN flags is a quality gap.

### 19. [major] ×1  (road/time_crunched_parent)
> Fueling recommendation of 90 g carbs/hour is gated on race duration ≥ 3.5 hours (per the plan JSON). At 78 miles, a masters rider at 170 W FTP is likely to finish in ~3.0–3.5 hours — right on the boundary. The guide should either confirm the athlete's expected race duration or adjust the threshold language; blindly prescribing 90 g/h for a race that may be under 3.5 hours risks GI distress and contradicts standard practice.

### 20. [major] ×1  (road/time_crunched_parent)
> The goal field is 'podium' for a 78-mile German gran fondo — yet 'Success looks like: Compete' appears in the guide. These are contradictory. A podium goal requires a race-specific tactical and intensity strategy that 'Compete' framing actively undersells. Either the goal was not passed through correctly or it was silently overridden.

### 21. [major] ×1  (road/time_crunched_parent)
> Zone 2 %HRmax range is listed as '69-83%' but the corresponding Zone 3 (Tempo) starts at '84% HRmax', while the custom 'G Spot' zone shows '92-96% HRmax' overlapping with Zone 4 Threshold at '95-105% HRmax'. The GS and Z4 HR ranges overlap at 95-96% HRmax, which will confuse the athlete when training by heart rate.

### 22. [major] ×1  (gravel/masters_returner)
> Long-ride duration cap is described as '1.5–2.5 hours' in the Weekly Structure section. For a 68-mile gravel race estimated at ~5.7 hours, a 2.5-hour ceiling is far too low and will leave the athlete underprepared. The 'Biggest Opportunity' sidebar acknowledges the problem but contradicts itself by suggesting 3–4 hour rides, which exceed the stated cap — the body copy needs to be corrected and made consistent.

### 23. [major] ×1  (gravel/masters_returner)
> The Time-Crunched intensity split '70% easy / 10% tempo / 20% hard' is the opposite of what Time-Crunched methodology actually prescribes. TCTP (Carmichael) is a HIGH-intensity, low-volume model that typically runs closer to 50–60% easy and 40–50% hard/threshold — NOT polarized or pyramidal with only 20% hard. This is either the wrong methodology label or the wrong numbers, and it directly conflicts with the failed Zone Distribution check.

### 24. [major] ×1  (road/masters_returner)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 13-week plan and the FTP Test Frequency check passed, implying there is more than one test. Telling the athlete each test governs 6 weeks is internally inconsistent with a 13-week plan that likely has two tests (weeks ~1 and ~7). The number '6 weeks' will confuse athletes who see two test dates on their calendar.

### 25. [major] ×1  (road/masters_returner)
> The Zone Distribution automated check returned WARN, yet the guide text presents the 65/25/10 split as definitively correct with no caveat. A WARN means the actual calendar distribution deviates from the stated methodology target — the coach guide should not assert the split is correct when the system itself flagged a deviation. This is a credibility risk if the athlete scrutinises their calendar.
