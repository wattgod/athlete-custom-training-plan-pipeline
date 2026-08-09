# Improvement backlog — 2026-08-09

**Quality -1.65** · avg coach 5.0/10 · contract pass 75% · load 17.88/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/ambitious_first_timer, gravel/masters_returner)
> Table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a gravel Gran Fondo plan for an athlete whose goal is simply to finish; road racing category pathway content is completely wrong discipline and audience, and is embarrassing to send to a paying customer

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Fueling carb figure is almost certainly wrong for this athlete. The plan JSON specifies 64g/hr over a 7-hour race (448g total), which is already on the lower end for a podium-level 109-mile effort, but the guide text does not state this number at all in the truncated section visible — meaning the nutrition strategy section either omits it or may state a different value. More critically, 64g/hr is calibrated in the JSON but a 45-year-old female racing 7 hours at FTP 250W will need 80-100g/hr with a multi-carb blend to compete for a podium. If the guide echoes 64g/hr as a hard recommendation to a podium chaser, it is dangerously low and potentially race-ruining. This must be verified and corrected before send.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the guide includes sections titled 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway.' This athlete is training for an MTB gran fondo, not a road race. Road-racing tactics, road cornering cues, and a Cat 5→1 upgrade pathway are irrelevant and embarrassing content that signals the wrong template was partially applied.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Race countdown is wrong. The plan states '56 days from today' but the plan start date is 2026-08-10 and the race is 2026-10-04 — that is 55 days from the start date, and the actual days-from-today figure depends on generation date, not the start date. Hard-coding '56 days' without confirming the generation date risks being factually wrong the moment the email is opened.

### 5. [critical] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED in preview_checks but the guide never acknowledges or corrects it. Sending a plan with a known zone distribution error is professionally unacceptable — the prescribed time-in-zone breakdown may be wrong for this athlete.

### 6. [critical] ×1  (gravel/masters_returner)
> Table of contents lists 'Road Skills' and 'Road Race Strategy' as chapters — even if the road skills section contains generic bike-handling content, labeling it 'Road Race Strategy' is wrong for a gravel event and signals the guide was not cleaned of road-racing boilerplate

### 7. [critical] ×1  (road/time_crunched_parent)
> A 'Gravel Skills' section appears in the table of contents (and presumably the body) of a plan for a road racer. The Bowral Classic is a road event. Gravel skills content — cornering on loose surfaces, tire-pressure selection for gravel, etc. — is wrong-discipline material that would confuse or embarrass us in front of this athlete.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — table of contents and body text include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is an MTB rider doing a gran fondo (a road/paved event in this database entry), but even if treated as road, the Cat 5-to-Cat 1 racing pathway is completely irrelevant to a first-timer whose only goal is to finish. These sections should not exist in this plan.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> FTP displayed as weight — the 'Your Profile' box reads '126 lbs Weight (57.1 kg)' AND '126W FTP' as two separate fields, but the athlete's FTP (126W) and an assumed body weight (126 lbs) happen to share the same number. The plan data shows ftp_known=false and only 126W listed; there is NO weight data in the athlete JSON. The plan has fabricated a body weight of 126 lbs / 57.1 kg that does not exist in the source data — this is a hallucinated data field that could mislead or offend the athlete.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Road Skills section is listed in the table of contents. For an MTB athlete (discipline=mtb), road cornering or road-specific skills content is the wrong discipline entirely. MTB-specific skills (trail braking, body position on descents, loose surface cornering) should be present instead.

### 11. [critical] ×1  (gravel/ambitious_first_timer)
> FTP value (126 W) is printed in the 'Weight' field as '126 lbs (57.1 kg)'. The athlete's actual weight was never collected — the template has substituted the FTP wattage into the weight slot. This is factually wrong and will confuse or embarrass the athlete immediately.

### 12. [critical] ×1  (gravel/ambitious_first_timer)
> The preview check flags Zone Distribution as FAIL. The guide text does not surface or resolve this failure — meaning the actual weekly workouts likely have an incorrect zone split (e.g., too much Zone 3 'grey zone' riding) that conflicts with the Pyramidal methodology promise of ~75% easy riding. Sending a plan whose zone distribution is known-bad undermines the core methodology claim.

### 13. [critical] ×1  (road/weekend_warrior)
> The 'Category 5 to Category 1 Pathway' section listed in the Contents is completely wrong for this athlete. She is a weekend warrior with a finish goal on a 44-mile gran fondo-style ride — a USA Cycling racing license category progression guide is irrelevant, mismatched to the discipline context, and embarrassing to send.

### 14. [critical] ×1  (road/weekend_warrior)
> Long-ride duration ceiling is stated as 1.5 hours, but the race is 44 miles with an estimated ~2.8-hour finish time. The plan then immediately contradicts itself by recommending 'a single 3-4 hour ride' in the coaching callout box. The prescribed long-ride cap is far too short and the two figures are in direct conflict with each other — one of them must be wrong and neither is reconciled.

### 15. [major] ×1  (gravel/veteran_podium_chaser)
> FTP test zone-lock duration stated as '6 weeks' ('The test result sets ALL your training zones for the next 6 weeks') inside a 9-week plan that likely has only 1-2 FTP tests. For an athlete starting in Week 1 and retesting mid-plan, a 6-week lock-in is plausible, but the FTP Test Frequency check returned WARN in the preview — suggesting the retest cadence may be off. The '6 weeks' figure should either be reconciled with the actual retest schedule shown in the calendar or removed to avoid confusion.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> The 'Gravel Skills' section is listed in the table of contents. Gravel-specific skills content (cornering on loose surfaces, descending gravel, tire pressure management, bike handling in rough terrain) is appropriate here — but the excerpt was cut before that section appeared. Given this is confirmed a gravel race, this section must be verified to contain gravel-specific content and NOT road-racing or general cycling drills that were copy-pasted incorrectly. The discipline match cannot be confirmed from the truncated text.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> Off days listed as Saturday AND Sunday, but long rides are scheduled on Tuesday. For a typical working athlete this is an unusual and unexplained structure (weekdays as hard days, both weekend days off). No rationale is given, and it contradicts the normal expectation that long MTB rides happen on weekends. If the athlete's schedule genuinely requires this, it needs an explicit explanation; otherwise it reads as a template error.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> No MTB-specific content anywhere in the visible guide. For an MTB gran fondo there should be references to trail skills, technical descending, climbing on loose terrain, tire pressure management, and outdoor MTB ride priorities. The guide reads as a generic road/indoor plan with MTB swapped into the title only.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> Weekly Volume and Zone Distribution both flagged WARN in the automated preview checks, yet the guide text makes no acknowledgment of these flags or any coaching note explaining why the volume or zone split may look unusual. Sending a plan with unresolved WARN flags without annotation is a quality-control failure.

### 20. [major] ×1  (gravel/masters_returner)
> Title and header read 'Avatar 202608092' — a raw system ID, not the athlete's name. This should never reach a paying customer.

### 21. [major] ×1  (gravel/masters_returner)
> Off days are listed as 'Wednesday, Monday' in that order in the 'At a Glance' box. Monday is conventionally the first day of the week and should be listed first; more importantly, listing Monday as an off day while the plan_start_date is 2026-08-17 (a Monday) needs to be verified against the calendar — if Week 1 Day 1 is a Monday and Monday is an off day, the first training day is Tuesday, which should be stated explicitly to avoid athlete confusion.

### 22. [major] ×1  (gravel/masters_returner)
> Fueling recommends 56 g carbs/hour for a projected 9.1-hour effort (Bowral Classic 94 mi). Current sports-science guidance for efforts of this duration recommends 80–90 g/hour (glucose:fructose blend) for trained athletes. 56 g/hour is significantly below optimum and risks the athlete bonking on a 94-mile, 7,851 ft gravel race.

### 23. [minor] ×2  (gravel/masters_returner, road/weekend_warrior)
> FTP Test Frequency check returned WARN but the guide text gives no indication of how many tests are scheduled or when; a masters returner with an unverified FTP (ftp_known: false) especially needs clarity on retest timing.

### 24. [major] ×1  (gravel/masters_returner)
> Weekly Volume check flagged WARN in preview and was never resolved or explained in the guide — the coach note field is silent on whether 9h/week is too high, too low, or borderline for this athlete; a paying customer deserves transparency or a corrected volume target

### 25. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency flagged WARN in preview with no explanation or mitigation in the guide text — for a 9-week plan a single retest may be insufficient or the timing may be poorly placed; this needs to be addressed or acknowledged
