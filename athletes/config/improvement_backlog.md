# Improvement backlog — 2026-06-24

**Quality 3.35** · avg coach 6.25/10 · contract pass 100% · load 9.75/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Weight (138 lbs / 62.6 kg) and height (5'6") appear in the athlete profile section but are NOT present in the athlete data JSON. These values were fabricated by the generator. Sending invented biometric data to a paying customer is a serious credibility and trust issue — she will immediately notice if the numbers are wrong.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> FTP value (127 W) has been injected into the Weight field: the profile card reads '127 lbs Weight (57.6 kg)'. The athlete's actual weight is not known from the plan data; 127 is her FTP in watts. This is a direct, visible data-merge error that will confuse and embarrass the athlete on the very first page.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> The guide says 'Off days: Friday, Thursday' — listing two separate days in an odd order (Friday before Thursday) which reads as a templating artifact. More importantly, Friday is named first, implying it may be the primary off day, but Thursday is also listed — this conflicts with a 5-training-day week and needs to be verified against the actual calendar to ensure it isn't a copy-paste of two different conditional off-day options.

### 4. [critical] ×1  (gravel/weekend_warrior)
> Off days listed as Sunday, Saturday, AND Thursday — that is 3 rest days out of 7, leaving only 4 training days, which is plausible, but Saturday as a rest day is almost certainly wrong for a weekend warrior. The persona label explicitly calls out 'weekend warrior,' meaning Saturday is almost certainly their most available training day and the logical slot for the long ride. The guide separately says 'Long rides: Monday,' which is an unusual long-ride day for a working adult. This combination strongly suggests the day-assignment logic has swapped weekend days, and sending a plan that rests the athlete on their best available riding day is a material error.

### 5. [critical] ×1  (gravel/masters_returner)
> Off-days list is contradictory and nonsensical: the guide states 'Off days: Sunday, Tuesday, Monday' — that is three days listed out of weekly order, and Sunday + Monday + Tuesday would mean the athlete only trains Wed–Sat (4 days), yet the plan elsewhere says 4 training days. More importantly, listing Monday after Tuesday reads as a copy-paste or generation error and will confuse any athlete.

### 6. [critical] ×1  (gravel/masters_returner)
> FTP stated as 163 W in the athlete data but the zone-chart header reads 'Your FTP: 163W' — this is correct — however the intensity distribution listed ('70% easy / 10% tempo / 20% hard') contradicts the Time-Crunched methodology. Authentic Time-Crunched (Carmichael) calls for roughly 80% easy / 20% high-intensity with very little tempo (Zone 3). Assigning 10% tempo actively conflicts with the methodology the plan claims to follow and with the Zone 3 'gray zone' warning the plan itself issues two paragraphs later — a direct internal contradiction.

### 7. [major] ×1  (gravel/masters_returner)
> The Zone Distribution preview check is flagged WARN yet the guide presents the 65/25/10 split confidently with no caveat. The guide should either acknowledge that zone distribution will be monitored and adjusted, or the WARN must be resolved before sending — a mismatch between QA output and guide content is embarrassing if escalated.

### 8. [major] ×1  (gravel/masters_returner)
> Off days are listed as Thursday AND Saturday, but Saturday is a traditionally strong long-ride candidate for a 9 h/week athlete with a Sunday long ride. With both Thursday and Saturday off, the athlete has only 5 riding days (Mon/Tue/Wed/Fri/Sun), which compresses interval loading awkwardly mid-week. This deserves a coach note explaining why Saturday is an off day rather than the second long/easy ride day.

### 9. [major] ×1  (road/veteran_podium_chaser)
> FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan. That number is simply wrong and will confuse the athlete about when to retest or how long the zones are valid.

### 10. [major] ×1  (road/veteran_podium_chaser)
> The methodology rationale states '17 years of cycling experience at Intermediate level' — a rider with 17 years of experience should never be labeled Intermediate. This is either a data-pipeline error or a copy-paste contradiction and will undermine the athlete's confidence in the plan's personalisation.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> Experience level contradiction: the guide states '1 years of cycling experience at Intermediate level' in the methodology rationale. A first-timer with 1 year of riding should be labeled Beginner or Novice, not Intermediate. This is inconsistent with the 'ambitious_first_timer' persona and could lead the athlete to misjudge their training readiness and push too hard.

### 12. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 (Active Recovery) row in the zone chart is missing HRmax % and RPE columns — the table shows '0-100W' for power but leaves the HRmax and RPE cells blank (they appear as empty or just narrative text). Every other zone has all columns populated. An incomplete zone table undermines credibility and makes the chart ambiguous for a new athlete.

### 13. [major] ×1  (road/veteran_podium_chaser)
> Methodology contradiction: The guide states Polarized (80/20) keeps the gray zone 'deliberately minimal rather than eliminated' and promises 'targeted tempo efforts in the Build phase.' Pure polarized methodology explicitly avoids Zone 3 (tempo) as the defining feature. The zone chart itself correctly warns Zone 3 is the gray zone to avoid. The plan cannot simultaneously be 'Polarized 80/20' and routinely prescribe tempo — this will confuse an experienced racer and undermine trust in the methodology label.

### 14. [major] ×1  (road/veteran_podium_chaser)
> FTP test result stated to 'set ALL your training zones for the next 6 weeks' — but the plan is only 10 weeks total. Depending on when the test falls, '6 weeks' could run past race day or contradict a second retest. This is a copy-paste artifact that needs to be calibrated to the actual plan length.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> The athlete's height (5'8") appears in the profile card but is not present in any of the source JSON data — it is fabricated filler. Presenting invented personal data to a paying customer is unacceptable, even if it seems harmless.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> The guide states '2 Years Riding' and 'Intermediate level' in the profile and methodology sections, but neither years of experience nor an 'Intermediate' label appears anywhere in the athlete JSON. These values have been assumed or hallucinated and should not be stated as facts in a personalised plan.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Long ride duration is stated as '3.4-5.8 hours' in the Weekly Structure section. The fueling block gives an estimated race duration of 4.9 h, and the plan is a finish-goal plan — peak long rides approaching or slightly exceeding 5.8 h may be appropriate, but the lower bound of 3.4 h (presented as if it applies throughout) is inconsistently low and the range is never explained. This figure needs to be reconciled with the actual calendar peaks.

### 18. [major] ×1  (gravel/weekend_warrior)
> Zone 1 (Active Recovery) power range is listed as '0-103W' with no lower-bound FTP percentage label, while all other zones show a '% FTP' column entry. More importantly, 103W as the Z1 ceiling equals ~54% FTP — that is slightly high for a true active recovery ceiling (typically ≤55% is the outer edge, so it is borderline acceptable), but the missing percentage annotation is inconsistent and could confuse an athlete using a power meter.

### 19. [major] ×1  (gravel/weekend_warrior)
> The guide states '2 Years Riding' and calls this 'Intermediate level' in the methodology rationale, but the persona is 'weekend_warrior' — a category that does not automatically map to Intermediate. If the athlete self-reported 2 years but is truly a casual weekend rider, labelling them Intermediate may set incorrect expectations about workout execution difficulty and could lead to overreaching on interval sessions.

### 20. [major] ×1  (gravel/masters_returner)
> Long ride duration range given as '2.7–4.5 hours' for a 7 h/week athlete. A 4.5-hour ride is 64% of the weekly hour budget in a single session — plausible for a peak week, but presenting it as a casual range without qualification will alarm the athlete and may conflict with the per-day duration caps that supposedly passed the preview check. The lower bound of 2.7 h also seems oddly precise without explanation.

### 21. [major] ×1  (gravel/masters_returner)
> Intensity distribution percentages (70/10/20) are presented as a hard fact of the Time-Crunched methodology, but no source or rationale is given, and as noted above the numbers do not match published Time-Crunched distributions. If an experienced athlete Googles this they will find a discrepancy, undermining trust in the entire guide.

### 22. [major] ×1  (gravel/masters_returner)
> The plan says '19 Years Riding' and classifies the athlete as 'Intermediate level' — for a 61-year-old with 19 years of cycling experience, 'Intermediate' is almost certainly a mislabel. The persona is 'masters_returner' (returning after a layoff), which should be reflected in the experience-level language. Calling a 19-year veteran 'Intermediate' reads as a template error and could offend the athlete.

### 23. [minor] ×1  (gravel/masters_returner)
> The guide states '25 Years Riding' and 'Intermediate level' in the same breath — 25 years of experience would typically be classified as experienced/advanced, not intermediate. This internal inconsistency could confuse the athlete about how her experience was assessed.

### 24. [minor] ×1  (gravel/masters_returner)
> The HRmax percentages in the zone chart for Zone GS (G Spot) show '92-96% HRmax' overlapping with Zone 3's upper bound of '84-94% HRmax' — the ranges overlap at 92-94%, which is a minor but visible inconsistency that a detail-oriented athlete will notice.

### 25. [minor] ×1  (gravel/masters_returner)
> The Recovery Protocol prescribes '25g protein + 63-75g carbs within 30 minutes (based on your 63kg body weight)' — the 63 kg figure is internally derived from the fabricated 138 lbs weight. If the weight is corrected, this calculation must also be updated.
